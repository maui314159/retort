"""
soccer_mcp.data_loader -- CSV ingestion, team registry and dataset assembly.

CONTEXT
-------
The Brazilian Soccer MCP server (see TASK.md) must make six pre-downloaded
Kaggle CSV files queryable through one coherent in-memory dataset:

    data/kaggle/Brasileirao_Matches.csv      -- Série A 2012-2022 (dedicated file)
    data/kaggle/Brazilian_Cup_Matches.csv    -- Copa do Brasil 2012-2021 (dedicated)
    data/kaggle/Libertadores_Matches.csv     -- Libertadores 2013-2022 (dedicated)
    data/kaggle/BR-Football-Dataset.csv      -- Série A/B/C + Copa do Brasil 2014-2023
    data/kaggle/novo_campeonato_brasileiro.csv -- Série A 2003-2019 (historical)
    data/kaggle/fifa_data.csv                -- 18,207 FIFA players

Two hard problems are solved here:

1. TEAM NORMALIZATION.  Every raw club spelling is folded onto a canonical
   ``team_id`` (see ``normalize``).  Registration is two-pass: pass 1 parses
   every raw name that appears with an explicit state suffix and records
   ``base -> states``; pass 2 resolves every occurrence, letting bare
   spellings inherit the single observed state (or the famous-club hint).

2. DUPLICATE COVERAGE.  The same fixture exists in several files (e.g. Série A
   2019 is in all three Série A sources).  To avoid double counting, every
   (competition, season) is served from ONE default source chosen by a
   per-competition priority list; seasons whose top-priority source contains
   unusable rows ("NA" goals, missing dates) fall back to the next source.
   Example: Copa do Brasil 2021 is broken (unplayed round with "NA" goals) in
   the dedicated cup file, so it is served from BR-Football, which has the
   complete bracket including the December final.

Rows that cannot be scored (goals not numeric) are skipped and reported in
``SoccerData.data_quality``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

from .model import (
    CompetitionCoverage,
    Match,
    MatchStats,
    Player,
    SKILL_COLUMNS,
    TeamEntity,
    TeamResolution,
)
from .normalize import (
    COMPETITIONS,
    VALID_UFS,
    canonical_team_name,
    parse_date_any,
    parse_team_name,
    strip_accents,
    apply_aliases,
    text_key,
)

# ---------------------------------------------------------------------------
# Dataset / source registry
# ---------------------------------------------------------------------------

#: Repository root = parent of this package's parent (soccer_mcp/..).
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "kaggle"

#: Machine ids for the six files.
SRC_BRASILEIRAO = "brasileirao_matches"
SRC_CUP = "brazilian_cup_matches"
SRC_LIBERTADORES = "libertadores_matches"
SRC_BR_FOOTBALL = "br_football_dataset"
SRC_HISTORICO = "novo_campeonato_brasileiro"
SRC_FIFA = "fifa_players"

SOURCE_LABELS: dict[str, str] = {
    SRC_BRASILEIRAO: "Brasileirao_Matches.csv",
    SRC_CUP: "Brazilian_Cup_Matches.csv",
    SRC_LIBERTADORES: "Libertadores_Matches.csv",
    SRC_BR_FOOTBALL: "BR-Football-Dataset.csv",
    SRC_HISTORICO: "novo_campeonato_brasileiro.csv",
    SRC_FIFA: "fifa_data.csv",
}

#: Which file wins for a given (competition, season).  First complete source
#: in this order is used; see module docstring for the rationale.
SOURCE_PRIORITY: dict[str, list[str]] = {
    "serie_a": [SRC_BRASILEIRAO, SRC_HISTORICO, SRC_BR_FOOTBALL],
    "serie_b": [SRC_BR_FOOTBALL],
    "serie_c": [SRC_BR_FOOTBALL],
    "copa_do_brasil": [SRC_CUP, SRC_BR_FOOTBALL],
    "libertadores": [SRC_LIBERTADORES],
}

#: BR-Football tournament column values -> competition ids.
BR_FOOTBALL_COMPETITIONS = {
    "Serie A": "serie_a",
    "Serie B": "serie_b",
    "Serie C": "serie_c",
    "Copa do Brasil": "copa_do_brasil",
}

#: A source keeps priority for a season when it holds at least this fraction
#: of the best source's playable matches for that season.
_SOURCE_COMPLETENESS_RATIO = 0.85


# ---------------------------------------------------------------------------
# Team registry (two-pass canonicalization)
# ---------------------------------------------------------------------------


class TeamRegistry:
    """Registry of every club mentioned in the datasets.

    ``register_pass1`` observes raw spellings that carry an explicit state;
    ``register_pass2`` resolves a raw spelling to its final team id, letting
    bare spellings inherit the unique state observed for their base.
    """

    def __init__(self) -> None:
        self._states_by_base: dict[str, set[str]] = {}
        self.entities: dict[str, TeamEntity] = {}

    # -- pass 1 ---------------------------------------------------------------

    def observe(self, raw_name: str) -> None:
        """Record the state of a raw spelling (when it carries one)."""
        parsed = apply_aliases(parse_team_name(raw_name))
        if parsed.state:
            self._states_by_base.setdefault(parsed.base, set()).add(parsed.state)

    # -- pass 2 ---------------------------------------------------------------

    def _display_name(self, raw_name: str, team_id: str) -> str:
        """Human-friendly display: keep accents, avoid duplicated state marks."""
        parsed = parse_team_name(raw_name)
        display = raw_name.strip()
        state = parsed.state
        if state is None and " " in team_id and team_id.rsplit(" ", 1)[1] in VALID_UFS:
            state = team_id.rsplit(" ", 1)[1]
        if state:
            # only append "(XX)" when the raw spelling doesn't already carry it
            raw_folded = strip_accents(display).casefold()
            if not raw_folded.endswith(state) and not raw_folded.endswith(f"- {state}"):
                return f"{display} ({state.upper()})"
        return display

    def register(self, raw_name: str, source: str, *, weight: int = 1, is_club: bool = False) -> str:
        """Resolve ``raw_name`` to a team id, creating the entity if needed."""
        parsed = canonical_team_name(raw_name, registry_states=self._states_by_base)
        team_id = parsed.team_id
        entity = self.entities.get(team_id)
        if entity is None:
            entity = TeamEntity(
                team_id=team_id,
                base=parsed.base,
                state=parsed.state,
                country=parsed.country,
                display_name=self._display_name(raw_name, team_id),
            )
            self.entities[team_id] = entity
        entity.variants[raw_name] = entity.variants.get(raw_name, 0) + weight
        entity.sources.add(source)
        if is_club:
            entity.fifa_club_names.add(raw_name)
        return team_id

    def note_match(self, team_id: str, competition: str, season: str) -> None:
        entity = self.entities[team_id]
        entity.match_count += 1
        entity.competitions.setdefault(competition, set()).add(season)

    # -- resolution -----------------------------------------------------------

    def _by_base(self, base: str) -> list[TeamEntity]:
        return [e for e in self.entities.values() if e.base == base]

    def resolve(self, query: str) -> TeamResolution:
        """Resolve a user-supplied team name (exact, hint, fuzzy)."""
        from .normalize import FOREIGN_BARE_NAMES, NICKNAMES

        query = query.strip()
        nick = NICKNAMES.get(text_key(query))
        if nick and nick in self.entities:
            return TeamResolution(query=query, team=self.entities[nick])

        parsed = canonical_team_name(query, registry_states=self._states_by_base)
        if parsed.state or parsed.country:
            entity = self.entities.get(parsed.team_id)
            if entity is not None:
                # note other clubs sharing the base (e.g. Flamengo-PI)
                alts = [e for e in self._by_base(parsed.base) if e.team_id != entity.team_id]
                return TeamResolution(query=query, team=entity, alternatives=alts)
            # exact id unknown -> try the bare base before failing
            candidates = self._by_base(parsed.base)
            if len(candidates) == 1:
                return TeamResolution(query=query, team=candidates[0])
            if candidates:
                return TeamResolution(
                    query=query, team=None, alternatives=candidates,
                    error=f"No exact match for '{query}'.",
                )
            return self._fuzzy(query)

        candidates = self._by_base(parsed.base)
        if len(candidates) == 1:
            return TeamResolution(query=query, team=candidates[0])
        if len(candidates) > 1:
            # a famous foreign club whose base collides with a small Brazilian
            # club (River Plate / River Plate-SE): prefer the stateless entity
            if parsed.base in FOREIGN_BARE_NAMES:
                foreign = self.entities.get(parsed.base)
                if foreign is not None:
                    return TeamResolution(
                        query=query, team=foreign,
                        alternatives=[e for e in candidates if e.team_id != foreign.team_id],
                    )
            brazilian = [e for e in candidates if e.is_brazilian]
            if len(brazilian) == 1:
                return TeamResolution(
                    query=query, team=brazilian[0],
                    alternatives=[e for e in candidates if e.team_id != brazilian[0].team_id],
                )
            # ambiguous: famous hint should already have fired in
            # canonical_team_name; if we got here the base is genuinely ambiguous
            ordered = sorted(candidates, key=lambda e: -e.match_count)
            return TeamResolution(
                query=query,
                team=None,
                alternatives=ordered,
                error=(
                    f"'{query}' is ambiguous: it can refer to "
                    f"{', '.join(e.display_name for e in ordered[:5])}. "
                    "Include the state to disambiguate (e.g. 'Atletico-MG')."
                ),
            )
        return self._fuzzy(query)

    def _fuzzy(self, query: str) -> TeamResolution:
        key = text_key(query)
        hits = [
            e for e in self.entities.values()
            if key in e.team_id or key in text_key(e.display_name)
            or any(key in text_key(v) for v in e.variants)
        ]
        hits.sort(key=lambda e: (-e.match_count, e.team_id))
        if not hits:
            return TeamResolution(query=query, team=None, error=f"No team found matching '{query}'.")
        if len(hits) == 1 or (len(key) >= 4 and hits[0].match_count >= 10 * hits[1].match_count):
            return TeamResolution(query=query, team=hits[0], alternatives=hits[1:4], fuzzy=True)
        return TeamResolution(
            query=query, team=None, alternatives=hits[:6],
            error=f"No exact match for '{query}'. Closest candidates:",
        )


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------


def _to_int(value: str | None) -> int | None:
    """Coerce CSV goal/round fields; returns None for '', '-', 'NA'."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() == "NA" or text == "-":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


@dataclass
class _SourceCounters:
    rows: int = 0
    skipped: int = 0
    skipped_examples: list[str] = field(default_factory=list)

    def skip(self, reason: str) -> None:
        self.skipped += 1
        if len(self.skipped_examples) < 5:
            self.skipped_examples.append(reason)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_brasileirao(data_dir: Path, registry: TeamRegistry) -> tuple[list[Match], dict]:
    counters = _SourceCounters()
    matches: list[Match] = []
    for i, row in enumerate(_read_csv(data_dir / "Brasileirao_Matches.csv")):
        counters.rows += 1
        home = registry.register(row["home_team"], SRC_BRASILEIRAO)
        away = registry.register(row["away_team"], SRC_BRASILEIRAO)
        hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
        match_date = parse_date_any(row["datetime"])
        if hg is None or ag is None or not home or not away:
            counters.skip(f"row {i}: unusable score/teams")
            continue
        rnd = _to_int(row.get("round"))
        matches.append(Match(
            match_id=f"{SRC_BRASILEIRAO}:{i}",
            competition="serie_a",
            source=SRC_BRASILEIRAO,
            season=str(row["season"]).strip(),
            match_date=match_date,
            home_team=home,
            away_team=away,
            home_goals=hg,
            away_goals=ag,
            round_label=f"Round {rnd}" if rnd is not None else None,
            raw_home=row["home_team"],
            raw_away=row["away_team"],
        ))
        registry.note_match(home, "serie_a", str(row["season"]).strip())
        registry.note_match(away, "serie_a", str(row["season"]).strip())
    return matches, vars(counters)


def _load_cup(data_dir: Path, registry: TeamRegistry) -> tuple[list[Match], dict]:
    counters = _SourceCounters()
    matches: list[Match] = []
    for i, row in enumerate(_read_csv(data_dir / "Brazilian_Cup_Matches.csv")):
        counters.rows += 1
        hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
        if hg is None or ag is None:
            # keep the teams registered (they exist in this season) but the
            # fixture cannot be scored; recorded for source selection.
            registry.observe(row["home_team"])
            registry.observe(row["away_team"])
            counters.skip(f"{row.get('season')} round {row.get('round')}: {row['home_team']} vs {row['away_team']} (no score)")
            continue
        home = registry.register(row["home_team"], SRC_CUP)
        away = registry.register(row["away_team"], SRC_CUP)
        rnd = _to_int(row.get("round"))
        season = str(row["season"]).strip()
        matches.append(Match(
            match_id=f"{SRC_CUP}:{i}",
            competition="copa_do_brasil",
            source=SRC_CUP,
            season=season,
            match_date=parse_date_any(row["datetime"]),
            home_team=home,
            away_team=away,
            home_goals=hg,
            away_goals=ag,
            round_label=f"Round {rnd}" if rnd is not None else None,
            raw_home=row["home_team"],
            raw_away=row["away_team"],
        ))
        registry.note_match(home, "copa_do_brasil", season)
        registry.note_match(away, "copa_do_brasil", season)
    return matches, vars(counters)


def _load_libertadores(data_dir: Path, registry: TeamRegistry) -> tuple[list[Match], dict]:
    counters = _SourceCounters()
    matches: list[Match] = []
    for i, row in enumerate(_read_csv(data_dir / "Libertadores_Matches.csv")):
        counters.rows += 1
        hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
        season = str(row["season"]).strip()
        if hg is None or ag is None or season.upper() == "NA":
            counters.skip(f"{season} {row.get('stage')}: {row['home_team']} vs {row['away_team']} (no score/date)")
            continue
        home = registry.register(row["home_team"], SRC_LIBERTADORES)
        away = registry.register(row["away_team"], SRC_LIBERTADORES)
        stage = (row.get("stage") or "").strip()
        label = stage.title() if stage else None
        matches.append(Match(
            match_id=f"{SRC_LIBERTADORES}:{i}",
            competition="libertadores",
            source=SRC_LIBERTADORES,
            season=season,
            match_date=parse_date_any(row["datetime"]),
            home_team=home,
            away_team=away,
            home_goals=hg,
            away_goals=ag,
            round_label=label,
            stage=stage.lower() or None,
            raw_home=row["home_team"],
            raw_away=row["away_team"],
        ))
        registry.note_match(home, "libertadores", season)
        registry.note_match(away, "libertadores", season)
    return matches, vars(counters)


def _load_br_football(data_dir: Path, registry: TeamRegistry) -> tuple[list[Match], dict]:
    counters = _SourceCounters()
    matches: list[Match] = []
    for i, row in enumerate(_read_csv(data_dir / "BR-Football-Dataset.csv")):
        counters.rows += 1
        competition = BR_FOOTBALL_COMPETITIONS.get(row["tournament"].strip())
        if competition is None:
            counters.skip(f"row {i}: unknown tournament '{row['tournament']}'")
            continue
        hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
        if hg is None or ag is None:
            counters.skip(f"{row['date']} {row['home']} vs {row['away']} (no score)")
            continue
        home = registry.register(row["home"], SRC_BR_FOOTBALL)
        away = registry.register(row["away"], SRC_BR_FOOTBALL)
        match_date = parse_date_any(row["date"])
        # Season attribution: the file only has dates.  Copa do Brasil editions
        # start in Jan/Feb, so calendar year == season.  Série A/B/C run
        # Apr-Dec; matches in Jan-Mar are postponed spillover from the
        # previous season (notably the COVID-affected 2020 season finishing in
        # Feb 2021), so they roll back one year.
        if match_date is None:
            season = ""
        elif competition == "copa_do_brasil":
            season = str(match_date.year)
        else:
            season = str(match_date.year - 1) if match_date.month <= 3 else str(match_date.year)
        stats = MatchStats(
            home_corners=_to_int(row.get("home_corner")),
            away_corners=_to_int(row.get("away_corner")),
            total_corners=_to_int(row.get("total_corners")),
            home_shots=_to_int(row.get("home_shots")),
            away_shots=_to_int(row.get("away_shots")),
            home_attacks=_to_int(row.get("home_attack")),
            away_attacks=_to_int(row.get("away_attack")),
        )
        matches.append(Match(
            match_id=f"{SRC_BR_FOOTBALL}:{i}",
            competition=competition,
            source=SRC_BR_FOOTBALL,
            season=season,
            match_date=match_date,
            home_team=home,
            away_team=away,
            home_goals=hg,
            away_goals=ag,
            stats=stats,
            raw_home=row["home"],
            raw_away=row["away"],
        ))
        if season:
            registry.note_match(home, competition, season)
            registry.note_match(away, competition, season)
    return matches, vars(counters)


def _load_historico(data_dir: Path, registry: TeamRegistry) -> tuple[list[Match], dict]:
    counters = _SourceCounters()
    matches: list[Match] = []
    for i, row in enumerate(_read_csv(data_dir / "novo_campeonato_brasileiro.csv")):
        counters.rows += 1
        hg, ag = _to_int(row["Gols_mandante"]), _to_int(row["Gols_visitante"])
        if hg is None or ag is None:
            counters.skip(f"row {row.get('ID')}: unusable score")
            continue
        home = registry.register(row["Equipe_mandante"], SRC_HISTORICO)
        away = registry.register(row["Equipe_visitante"], SRC_HISTORICO)
        season = str(row["Ano"]).strip()
        rnd = _to_int(row.get("Rodada"))
        matches.append(Match(
            match_id=f"{SRC_HISTORICO}:{row.get('ID', i)}",
            competition="serie_a",
            source=SRC_HISTORICO,
            season=season,
            match_date=parse_date_any(row["Data"]),
            home_team=home,
            away_team=away,
            home_goals=hg,
            away_goals=ag,
            round_label=f"Round {rnd}" if rnd is not None else None,
            stadium=(row.get("Arena") or "").strip() or None,
            raw_home=row["Equipe_mandante"],
            raw_away=row["Equipe_visitante"],
        ))
        registry.note_match(home, "serie_a", season)
        registry.note_match(away, "serie_a", season)
    return matches, vars(counters)


def _load_fifa(data_dir: Path, registry: TeamRegistry) -> list[Player]:
    players: list[Player] = []
    for row in _read_csv(data_dir / "fifa_data.csv"):
        club = (row.get("Club") or "").strip()
        if club:
            registry.register(club, SRC_FIFA, is_club=True)
        skills: dict[str, int | None] = {}
        for column in SKILL_COLUMNS:
            skills[column] = _to_int(row.get(column))
        players.append(Player(
            player_id=_to_int(row.get("ID")) or 0,
            name=(row.get("Name") or "").strip(),
            age=_to_int(row.get("Age")),
            nationality=(row.get("Nationality") or "").strip(),
            overall=_to_int(row.get("Overall")) or 0,
            potential=_to_int(row.get("Potential")),
            club=club,
            position=(row.get("Position") or "").strip(),
            jersey_number=_to_int(row.get("Jersey Number")),
            height=(row.get("Height") or "").strip(),
            weight=(row.get("Weight") or "").strip(),
            preferred_foot=(row.get("Preferred Foot") or "").strip(),
            value=(row.get("Value") or "").strip(),
            wage=(row.get("Wage") or "").strip(),
            skills=skills,
        ))
    return players


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------


@dataclass
class SoccerData:
    """Fully loaded, normalized dataset."""

    data_dir: Path
    matches: list[Match]
    players: list[Player]
    registry: TeamRegistry
    data_quality: dict[str, dict]
    default_source: dict[tuple[str, str], str] = field(default_factory=dict)
    _by_team: dict[str, list[Match]] = field(default_factory=dict)
    _by_comp_season: dict[tuple[str, str], list[Match]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for match in self.matches:
            self._by_team.setdefault(match.home_team, []).append(match)
            self._by_team.setdefault(match.away_team, []).append(match)
            self._by_comp_season.setdefault((match.competition, match.season), []).append(match)

    # -- source selection -------------------------------------------------------

    def source_priority_for(self, competition: str, season: str) -> str | None:
        """Default source for one (competition, season).

        Sources are tried in ``SOURCE_PRIORITY`` order and the first one whose
        playable match count is at least 85% of the best available source is
        chosen.  This keeps the dedicated files in charge (round labels,
        cleaner names) while ensuring materially incomplete seasons fall back
        to a fuller source -- e.g. Série A 2022 (299 playable rows in
        Brasileirao_Matches.csv due to 'NA' scores) falls back to
        BR-Football's 379, and Copa do Brasil 2021 (unplayed round-of-16 with
        'NA' scores, and no final, in the dedicated cup file) falls back to
        BR-Football's complete bracket.
        """
        key = (competition, season)
        if key in self.default_source:
            return self.default_source[key]
        season_matches = self._by_comp_season.get(key, [])
        counts: dict[str, int] = {}
        for match in season_matches:
            counts[match.source] = counts.get(match.source, 0) + 1
        best = max(counts.values(), default=0)
        chosen = None
        if best:
            for source in SOURCE_PRIORITY.get(competition, []):
                if counts.get(source, 0) >= _SOURCE_COMPLETENESS_RATIO * best:
                    chosen = source
                    break
        self.default_source[key] = chosen
        return chosen

    # -- match iteration --------------------------------------------------------

    def iter_matches(
        self,
        *,
        competition: str | None = None,
        season: str | None = None,
        team: str | None = None,
        opponent: str | None = None,
        date_from=None,
        date_to=None,
        stage: str | None = None,
        source: str | None = None,
        dedupe: bool = True,
    ) -> list[Match]:
        """Query matches with deduplication across overlapping sources."""
        keys: list[tuple[str, str]] = []
        if competition or season:
            for key in self._by_comp_season:
                if competition and key[0] != competition:
                    continue
                if season and key[1] != str(season):
                    continue
                keys.append(key)
        else:
            keys = list(self._by_comp_season)

        candidates: list[Match] = []
        for key in sorted(keys):
            comp, season_key = key
            if source is not None:
                if not any(m.source == source for m in self._by_comp_season[key]):
                    continue
                chosen = source
            else:
                chosen = self.source_priority_for(comp, season_key)
            if chosen is None:
                continue
            candidates.extend(m for m in self._by_comp_season[key] if m.source == chosen)

        if stage:
            stage_key = stage.strip().casefold()

            def _stage_matches(match: Match) -> bool:
                labels = [
                    label for label in (match.round_label, match.stage) if label
                ]
                keys = [label.casefold() for label in labels]
                return stage_key in keys or any(
                    stage_key in key for key in keys
                )

            exact = [
                m for m in candidates
                if stage_key in [
                    label.casefold()
                    for label in (m.round_label, m.stage) if label
                ]
            ]
            # exact stage matches win; fall back to substring ("group" ->
            # "group stage", "semi" -> "semifinals") only when nothing matched
            # exactly, so "final" never drags in quarterfinals.
            candidates = exact or [m for m in candidates if _stage_matches(m)]

        result: list[Match] = []
        seen_fixtures: set[tuple[str | None, str, str]] = set()
        for match in sorted(candidates, key=_match_sort_key):
            if team and match.home_team != team and match.away_team != team:
                continue
            if opponent and not (
                match.home_team == opponent or match.away_team == opponent
            ):
                continue
            if date_from and (match.match_date is None or match.match_date < date_from):
                continue
            if date_to and (match.match_date is None or match.match_date > date_to):
                continue
            fixture = (match.match_date, match.home_team, match.away_team)
            if dedupe and fixture in seen_fixtures:
                continue
            seen_fixtures.add(fixture)
            result.append(match)
        return result

    def team_matches(self, team_id: str, **filters) -> list[Match]:
        return self.iter_matches(team=team_id, **filters)

    # -- coverage ---------------------------------------------------------------

    def competition_coverage(self, competition: str) -> CompetitionCoverage:
        comp = COMPETITIONS[competition]
        seasons = sorted({
            m.season for m in self.matches
            if m.competition == competition and m.season
        })
        sources: dict[str, int] = {}
        for match in self.matches:
            if match.competition == competition:
                sources[match.source] = sources.get(match.source, 0) + 1
        return CompetitionCoverage(
            competition=competition,
            display=comp.display,
            comp_type=comp.type,
            seasons=seasons,
            match_count=sum(sources.values()),
            sources=sources,
        )


def _match_sort_key(match: Match):
    return (match.match_date or date.min, match.competition, match.match_id)


# ---------------------------------------------------------------------------
# Top-level loader
# ---------------------------------------------------------------------------


def load_dataset(data_dir: str | Path | None = None) -> SoccerData:
    """Load all six CSV files and assemble the normalized dataset."""
    directory = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    if not directory.is_dir():
        raise FileNotFoundError(f"Data directory not found: {directory}")

    # Pass 0: observe every raw spelling (with states) across the match files.
    registry = TeamRegistry()
    for row in _read_csv(directory / "Brasileirao_Matches.csv"):
        registry.observe(row["home_team"])
        registry.observe(row["away_team"])
    for row in _read_csv(directory / "Brazilian_Cup_Matches.csv"):
        registry.observe(row["home_team"])
        registry.observe(row["away_team"])
    for row in _read_csv(directory / "Libertadores_Matches.csv"):
        registry.observe(row["home_team"])
        registry.observe(row["away_team"])
    for row in _read_csv(directory / "BR-Football-Dataset.csv"):
        registry.observe(row["home"])
        registry.observe(row["away"])
    for row in _read_csv(directory / "novo_campeonato_brasileiro.csv"):
        registry.observe(row["Equipe_mandante"])
        registry.observe(row["Equipe_visitante"])

    # Pass 1: load match files (registering teams + building matches).
    # ``data_quality`` records rows/skips per file for reporting.
    br_matches, br_q = _load_brasileirao(directory, registry)
    cup_matches, cup_q = _load_cup(directory, registry)
    lib_matches, lib_q = _load_libertadores(directory, registry)
    brf_matches, brf_q = _load_br_football(directory, registry)
    hist_matches, hist_q = _load_historico(directory, registry)
    quality = {
        SRC_BRASILEIRAO: br_q,
        SRC_CUP: cup_q,
        SRC_LIBERTADORES: lib_q,
        SRC_BR_FOOTBALL: brf_q,
        SRC_HISTORICO: hist_q,
    }

    # Pass 2: FIFA players (clubs join the same registry).
    players = _load_fifa(directory, registry)

    matches = br_matches + cup_matches + lib_matches + brf_matches + hist_matches
    return SoccerData(
        data_dir=directory,
        matches=matches,
        players=players,
        registry=registry,
        data_quality=quality,
    )


def _count_skipped_rows(path: Path) -> int:
    """Count rows with unusable scores in a match CSV (for quality reports)."""
    total = 0
    for row in _read_csv(path):
        if _to_int(row.get("home_goal")) is None or _to_int(row.get("away_goal")) is None:
            total += 1
    return total


@lru_cache(maxsize=4)
def _cached_dataset(data_dir_str: str) -> SoccerData:
    return load_dataset(Path(data_dir_str))


def get_dataset(data_dir: str | Path | None = None) -> SoccerData:
    """Process-wide cached dataset (CSVs are read once per data directory)."""
    directory = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    return _cached_dataset(str(directory.resolve()))
