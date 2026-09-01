"""Load and unify the six Brazilian soccer CSV datasets.

The six files overlap heavily (e.g. the 2012-2019 Brasileirão appears in
three of them), so this module merges them into one clean in-memory model:

* every raw team name is folded to a canonical key (see ``normalize``);
* each competition keeps **one source per season** — the source with the
  most scored matches, preferring the dedicated competition file whenever
  it covers at least 80% of the best source (documented "coverage rule");
* rows without a parseable date or score are skipped (and counted in the
  load report) — e.g. the abandoned 2015 Boca-River Libertadores tie;
* BR-Football league rows dated January-March are re-bucketed to the
  previous season, because COVID-shifted Brazilian seasons ran into the
  following calendar year (Série A 2020 finished in February 2021);
* matches chosen from a non-statistical source are enriched with
  corners/shots/attacks and stadium where the same fixture is found in
  BR-Football-Dataset or the historical file.

The result is a ``SoccerData`` object with indexes for team, competition
and player lookups, plus a transparency report of what was loaded.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .models import (
    CompetitionInfo,
    Match,
    MatchStats,
    Player,
    position_group,
)
from .normalize import TeamRegistry, build_registry, team_key

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

FILES = {
    "brasileirao_matches": "Brasileirao_Matches.csv",
    "brazilian_cup_matches": "Brazilian_Cup_Matches.csv",
    "libertadores_matches": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "novo_campeonato": "novo_campeonato_brasileiro.csv",
    "fifa": "fifa_data.csv",
}

# Competitions produced by each source file (order = preference order).
COMPETITION_SOURCES: dict[str, list[tuple[str, str, str]]] = {
    # competition_id -> [(source_id, tournament-in-file, display label)]
    "brasileirao": [
        ("brasileirao_matches", "", "Brasileirão Serie A"),
        ("novo_campeonato", "", "Brasileirão Serie A"),
        ("br_football", "Serie A", "Brasileirão Serie A"),
    ],
    "copadobrasil": [
        ("brazilian_cup_matches", "", "Copa do Brasil"),
        ("br_football", "Copa do Brasil", "Copa do Brasil"),
    ],
    "libertadores": [
        ("libertadores_matches", "", "Copa Libertadores"),
    ],
    "serieb": [
        ("br_football", "Serie B", "Brasileirão Serie B"),
    ],
    "seriec": [
        ("br_football", "Serie C", "Brasileirão Serie C"),
    ],
}

COMPETITION_KIND = {
    "brasileirao": "league",
    "serieb": "league",
    "seriec": "league",
    "copadobrasil": "cup",
    "libertadores": "cup",
}

COMPETITION_DISPLAY = {
    "brasileirao": "Brasileirão Serie A",
    "serieb": "Brasileirão Serie B",
    "seriec": "Brasileirão Serie C",
    "copadobrasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
}

COVERAGE_RULE = 0.8  # prefer dedicated file if it has >= 80% of best source

_SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
    "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle",
    "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
]

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d/%m/%Y %H:%M")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_date(value: str) -> Optional[date]:
    """Parse the date formats used across the datasets.

    Handles ISO dates with or without time ("2012-05-19 18:30:00") and the
    Brazilian day-first format ("29/03/2003").
    """
    if not value:
        return None
    text = value.strip()
    if not text or text.upper() in {"NA", "N/A", "-"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(value) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "-", "NONE"}:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def parse_str(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "-", "NONE"}:
        return None
    return text


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------
# Raw match records
# ---------------------------------------------------------------------------


@dataclass
class RawMatch:
    source: str
    tournament: str
    season: Optional[int]
    match_date: Optional[date]
    home_raw: str
    away_raw: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    round_number: Optional[int] = None
    stage: Optional[str] = None
    stadium: Optional[str] = None
    kickoff: Optional[str] = None
    stats: Optional[MatchStats] = None
    state_home: Optional[str] = None
    state_away: Optional[str] = None


def _rebucket_season(row_date: Optional[date], calendar_year: Optional[int], league: bool) -> Optional[int]:
    """Assign the correct *season* year.

    Brazilian leagues run roughly April-December; because of COVID the
    2020 Série A/B/C seasons finished in January-February 2021, so
    BR-Football league rows dated Jan-Mar belong to the previous season.
    Cup competitions keep their calendar-year label (the dedicated Copa file
    already carries authoritative season labels for 2012-2021).
    """
    if row_date is None or calendar_year is None:
        return None
    if league and row_date.month <= 3:
        return calendar_year - 1
    return calendar_year


def load_brasileirao_matches(path: Path) -> list[RawMatch]:
    rows = _read_csv(path)
    out = []
    for row in rows:
        out.append(
            RawMatch(
                source="Brasileirao_Matches.csv",
                tournament="",
                season=parse_int(row.get("season")),
                match_date=parse_date(row.get("datetime", "")),
                home_raw=row.get("home_team", ""),
                away_raw=row.get("away_team", ""),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                round_number=parse_int(row.get("round")),
                state_home=parse_str(row.get("home_team_state")),
                state_away=parse_str(row.get("away_team_state")),
            )
        )
    return out


def load_brazilian_cup(path: Path) -> list[RawMatch]:
    rows = _read_csv(path)
    out = []
    for row in rows:
        out.append(
            RawMatch(
                source="Brazilian_Cup_Matches.csv",
                tournament="",
                season=parse_int(row.get("season")),
                match_date=parse_date(row.get("datetime", "")),
                home_raw=row.get("home_team", ""),
                away_raw=row.get("away_team", ""),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                round_number=parse_int(row.get("round")),
            )
        )
    return out


def load_libertadores(path: Path) -> list[RawMatch]:
    rows = _read_csv(path)
    out = []
    for row in rows:
        stage = parse_str(row.get("stage")) or ""
        out.append(
            RawMatch(
                source="Libertadores_Matches.csv",
                tournament="",
                season=parse_int(row.get("season")),
                match_date=parse_date(row.get("datetime", "")),
                home_raw=row.get("home_team", ""),
                away_raw=row.get("away_team", ""),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                stage=stage,
            )
        )
    return out


def load_novo(path: Path) -> list[RawMatch]:
    rows = _read_csv(path)
    out = []
    for row in rows:
        out.append(
            RawMatch(
                source="novo_campeonato_brasileiro.csv",
                tournament="",
                season=parse_int(row.get("Ano")),
                match_date=parse_date(row.get("Data", "")),
                home_raw=row.get("Equipe_mandante", ""),
                away_raw=row.get("Equipe_visitante", ""),
                home_goals=parse_int(row.get("Gols_mandante")),
                away_goals=parse_int(row.get("Gols_visitante")),
                round_number=parse_int(row.get("Rodada")),
                stadium=parse_str(row.get("Arena")),
                state_home=parse_str(row.get("Mandante_UF")),
                state_away=parse_str(row.get("Visitante_UF")),
            )
        )
    return out


def load_br_football(path: Path) -> list[RawMatch]:
    rows = _read_csv(path)
    out = []
    for row in rows:
        tournament = parse_str(row.get("tournament")) or ""
        league = tournament in {"Serie A", "Serie B", "Serie C"}
        match_date = parse_date(row.get("date", ""))
        season = _rebucket_season(match_date, parse_int(row.get("date", "")[:4]), league)
        kickoff = parse_str(row.get("time"))
        stats = MatchStats(
            corners_home=parse_int(row.get("home_corner")),
            corners_away=parse_int(row.get("away_corner")),
            shots_home=parse_int(row.get("home_shots")),
            shots_away=parse_int(row.get("away_shots")),
            attacks_home=parse_int(row.get("home_attack")),
            attacks_away=parse_int(row.get("away_attack")),
            ht_result_home=parse_str(row.get("ht_result")),
            ht_result_away=parse_str(row.get("at_result")),
        )
        out.append(
            RawMatch(
                source="BR-Football-Dataset.csv",
                tournament=tournament,
                season=season,
                match_date=match_date,
                home_raw=row.get("home", ""),
                away_raw=row.get("away", ""),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                stadium=None,
                kickoff=kickoff,
                stats=stats,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------


def load_players(path: Path) -> list[Player]:
    rows = _read_csv(path)
    players = []
    for row in rows:
        club = parse_str(row.get("Club")) or ""
        position = parse_str(row.get("Position")) or ""
        skills = {}
        for col in _SKILL_COLUMNS:
            value = parse_int(row.get(col))
            if value is not None:
                skills[col] = value
        players.append(
            Player(
                player_id=str(row.get("ID") or ""),
                name=parse_str(row.get("Name")) or "",
                age=parse_int(row.get("Age")),
                nationality=parse_str(row.get("Nationality")) or "",
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club=club,
                club_key=team_key(club) if club else "",
                position=position,
                position_group=position_group(position),
                jersey=parse_int(row.get("Jersey Number")),
                height=parse_str(row.get("Height")),
                weight=parse_str(row.get("Weight")),
                preferred_foot=parse_str(row.get("Preferred Foot")),
                value=parse_str(row.get("Value")),
                wage=parse_str(row.get("Wage")),
                skills=skills,
            )
        )
    return players


# ---------------------------------------------------------------------------
# Unified dataset
# ---------------------------------------------------------------------------


@dataclass
class SourceChoice:
    competition_id: str
    season: Optional[int]
    chosen: str
    counts: dict[str, int] = field(default_factory=dict)


@dataclass
class SoccerData:
    """In-memory unified dataset with lookup indexes."""

    matches: list[Match] = field(default_factory=list)
    players: list[Player] = field(default_factory=list)
    registry: TeamRegistry = field(default_factory=TeamRegistry)
    competitions: dict[str, CompetitionInfo] = field(default_factory=dict)
    by_team: dict[str, list[Match]] = field(default_factory=dict)
    by_competition: dict[str, list[Match]] = field(default_factory=dict)
    players_by_club: dict[str, list[Player]] = field(default_factory=dict)
    source_choices: list[SourceChoice] = field(default_factory=list)
    report: dict = field(default_factory=dict)

    # -- match lookups ---------------------------------------------------

    def matches_for_team(self, key: str) -> list[Match]:
        return self.by_team.get(key, [])

    def matches_for_competition(self, competition_id: str) -> list[Match]:
        return self.by_competition.get(competition_id, [])

    def seasons_for(self, competition_id: str) -> list[int]:
        return self.competitions[competition_id].seasons

    # -- player lookups ----------------------------------------------------

    def players_for_club(self, club_key: str) -> list[Player]:
        return self.players_by_club.get(club_key, [])

    def find_players_by_name(self, query: str) -> list[Player]:
        from .normalize import compact

        needle = compact(query)
        if not needle:
            return []
        exact, partial = [], []
        for player in self.players:
            hay = compact(player.name)
            if hay == needle:
                exact.append(player)
            elif needle in hay:
                partial.append(player)
        return exact + partial


# The dedicated Copa do Brasil file numbers rounds inconsistently between
# seasons (the 2012 final is round 6, the 2016 final round 7, 2013-2020
# round 8), so finals are detected per season: the highest round of a
# season played over exactly two legs.
_LIBERTADORES_STAGE_LABELS = {
    "group stage": "Group Stage",
    "round of 16": "Round of 16",
    "quarterfinals": "Quarterfinals",
    "semifinals": "Semifinals",
    "final": "Final",
}


def _stage_label(raw: RawMatch) -> str:
    if raw.source == "Libertadores_Matches.csv" and raw.stage:
        return _LIBERTADORES_STAGE_LABELS.get(raw.stage.lower(), raw.stage.title())
    if raw.round_number is not None:
        return f"Round {raw.round_number}"
    return ""


def _label_cup_file_finals(matches: list[Match]) -> None:
    """Mark two-legged finals in seasons sourced from the dedicated cup file."""
    by_season: dict[int, dict[int, list[Match]]] = defaultdict(lambda: defaultdict(list))
    for m in matches:
        if m.season is not None and m.round_number is not None and m.source != "BR-Football-Dataset.csv":
            by_season[m.season][m.round_number].append(m)
    for season, rounds in by_season.items():
        max_round = max(rounds)
        games = rounds[max_round]
        # A truncated season (e.g. the 2021 file ends at the round of 16)
        # must not have its last round mislabeled as a final.
        if len(games) == 2:
            for m in games:
                m.stage = "Final"


def _label_brf_cup_finals(matches: list[Match]) -> None:
    """Mark final-round matches in BR-Football cup seasons (no round data).

    The final is the two-team pairing played on the last two distinct
    match dates of the season (two-legged finals).
    """
    by_season: dict[int, list[Match]] = defaultdict(list)
    for m in matches:
        if m.season is not None and m.source == "BR-Football-Dataset.csv":
            by_season[m.season].append(m)
    for season, season_matches in by_season.items():
        dated = [m for m in season_matches if m.date is not None]
        if len(dated) < 2:
            continue
        dates = sorted({m.date for m in dated})
        last_day = [m for m in dated if m.date == dates[-1]]
        if not last_day:
            continue
        first = last_day[0].home_key
        opponent = last_day[0].away_key
        finalists = {first, opponent}
        last_two_days = {dates[-1], dates[-2]}
        for m in dated:
            if {m.home_key, m.away_key} == finalists and m.date in last_two_days:
                m.stage = "Final"


def _select_source(
    competition_id: str,
    season: Optional[int],
    per_source: dict[str, list[RawMatch]],
    preference: list[str],
) -> tuple[str, dict[str, int]]:
    """Pick the source used for one season of a competition.

    The dedicated file wins whenever it covers at least 80% of the best
    source's scored-match count; otherwise the biggest source wins.
    """
    counts = {}
    for source_id in preference:
        rows = per_source.get(source_id, [])
        counts[source_id] = sum(
            1
            for r in rows
            if r.season == season
            and r.match_date is not None
            and r.home_goals is not None
            and r.away_goals is not None
        )
    best = max(counts.values(), default=0)
    if best == 0:
        return "", counts
    for source_id in preference:
        if counts.get(source_id, 0) >= COVERAGE_RULE * best:
            return source_id, counts
    # No preferred source reached the coverage threshold.
    top = max(preference, key=lambda s: counts.get(s, 0))
    return top, counts


def build_competition(
    competition_id: str,
    raw_by_source: dict[str, list[RawMatch]],
    preference: list[tuple[str, str, str]],
    registry: TeamRegistry,
) -> tuple[list[Match], list[SourceChoice]]:
    display = COMPETITION_DISPLAY[competition_id]
    source_ids = [sid for sid, _tournament, _label in preference]
    tournament_filter = {sid: _tournament for sid, _tournament, _label in preference}
    season_rows: dict[Optional[int], dict[str, list[RawMatch]]] = defaultdict(lambda: defaultdict(list))
    for source_id in source_ids:
        wanted = tournament_filter.get(source_id) or ""
        for raw in raw_by_source.get(source_id, []):
            if wanted and raw.tournament != wanted:
                continue
            season_rows[raw.season][source_id].append(raw)

    # Enrichment maps from the other files.
    stats_join: dict[tuple, MatchStats] = {}
    for raw in raw_by_source.get("br_football", []):
        if raw.match_date and raw.home_goals is not None and raw.away_goals is not None:
            stats_join[(raw.match_date, team_key(raw.home_raw), team_key(raw.away_raw))] = raw.stats
    arena_join: dict[tuple, str] = {}
    for raw in raw_by_source.get("novo_campeonato", []):
        if raw.match_date and raw.stadium:
            arena_join[(raw.match_date, team_key(raw.home_raw), team_key(raw.away_raw))] = raw.stadium

    matches: list[Match] = []
    choices: list[SourceChoice] = []
    seen_ids: set[str] = set()

    seasons = sorted(s for s in season_rows if s is not None)
    for season in seasons:
        per_source = dict(season_rows[season])
        chosen, counts = _select_source(competition_id, season, per_source, source_ids)
        choices.append(
            SourceChoice(
                competition_id=competition_id,
                season=season,
                chosen=chosen,
                counts={k: v for k, v in counts.items() if v},
            )
        )
        if not chosen:
            continue
        rows = per_source.get(chosen, [])
        for raw in rows:
            if raw.match_date is None or raw.home_goals is None or raw.away_goals is None:
                continue  # unplayed / abandoned fixtures
            home_key = team_key(raw.home_raw)
            away_key = team_key(raw.away_raw)
            if not home_key or not away_key or home_key == away_key:
                continue
            dup = (raw.match_date, home_key, away_key, raw.home_goals, raw.away_goals)
            if dup in seen_ids:
                continue
            seen_ids.add(dup)
            stats = raw.stats
            if stats is None:
                stats = stats_join.get((raw.match_date, home_key, away_key))
            stadium = raw.stadium or arena_join.get((raw.match_date, home_key, away_key))
            match_id = f"{competition_id}-{season}-{len(matches) + 1:05d}"
            matches.append(
                Match(
                    match_id=match_id,
                    competition_id=competition_id,
                    competition=display,
                    season=season,
                    date=raw.match_date,
                    home_key=home_key,
                    home_team=registry_display(registry, home_key, raw.home_raw),
                    away_key=away_key,
                    away_team=registry_display(registry, away_key, raw.away_raw),
                    home_goals=raw.home_goals,
                    away_goals=raw.away_goals,
                    stage=_stage_label(raw),
                    round_number=raw.round_number,
                    kickoff=raw.kickoff,
                    stadium=stadium,
                    state_home=raw.state_home,
                    state_away=raw.state_away,
                    stats=stats,
                    source=raw.source,
                )
            )
    matches.sort(key=lambda m: (m.season or 0, m.date or date.min))
    if competition_id == "copadobrasil":
        _label_cup_file_finals(matches)
        _label_brf_cup_finals(matches)
    return matches, choices


def registry_display(registry: TeamRegistry, key: str, fallback: str) -> str:
    info = registry.get(key)
    if info and info.display:
        return info.display
    return fallback.strip()


def load_soccer_data(data_dir: str | Path = DEFAULT_DATA_DIR) -> SoccerData:
    """Load every dataset and build the unified in-memory model."""
    data_dir = Path(data_dir)
    paths = {key: data_dir / filename for key, filename in FILES.items()}
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing data files: {', '.join(missing)} (looked in {data_dir})")

    # --- load raw sources -------------------------------------------------
    raw_matches: dict[str, list[RawMatch]] = {
        "brasileirao_matches": load_brasileirao_matches(paths["brasileirao_matches"]),
        "brazilian_cup_matches": load_brazilian_cup(paths["brazilian_cup_matches"]),
        "libertadores_matches": load_libertadores(paths["libertadores_matches"]),
        "novo_campeonato": load_novo(paths["novo_campeonato"]),
        "br_football": load_br_football(paths["br_football"]),
    }
    players = load_players(paths["fifa"])

    # --- team registry from every raw name -------------------------------
    registry_names: list[tuple[str, str]] = []
    for source_id, rows in raw_matches.items():
        for raw in rows:
            registry_names.append((raw.home_raw, FILES[source_id]))
            registry_names.append((raw.away_raw, FILES[source_id]))
    for player in players:
        if player.club:
            registry_names.append((player.club, FILES["fifa"]))
    registry = build_registry(registry_names)

    # --- build unified competitions ---------------------------------------
    data = SoccerData(players=players, registry=registry)
    team_counter: Counter = Counter()
    for competition_id, preference in COMPETITION_SOURCES.items():
        matches, choices = build_competition(competition_id, raw_matches, preference, registry)
        data.matches.extend(matches)
        data.by_competition[competition_id] = matches
        data.source_choices.extend(choices)
        for m in matches:
            team_counter[m.home_key] += 1
            team_counter[m.away_key] += 1
        teams = {m.home_key for m in matches} | {m.away_key for m in matches}
        seasons = sorted({m.season for m in matches if m.season is not None})
        sources = sorted({m.source for m in matches})
        data.competitions[competition_id] = CompetitionInfo(
            competition_id=competition_id,
            display=COMPETITION_DISPLAY[competition_id],
            kind=COMPETITION_KIND[competition_id],
            seasons=seasons,
            match_count=len(matches),
            team_count=len(teams),
            sources=sources,
        )
    data.registry.match_counts(team_counter)

    # --- indexes ------------------------------------------------------------
    data.matches.sort(key=lambda m: (m.date or date.min, m.competition_id))
    for m in data.matches:
        data.by_team.setdefault(m.home_key, []).append(m)
        data.by_team.setdefault(m.away_key, []).append(m)
    for key in data.by_team:
        data.by_team[key].sort(key=lambda m: (m.date or date.min, m.competition_id))
    data.players_by_club = defaultdict(list)
    for player in players:
        if player.club_key:
            data.players_by_club[player.club_key].append(player)
    for club_players in data.players_by_club.values():
        club_players.sort(key=lambda p: (-(p.overall or 0), p.name))

    # --- load report ---------------------------------------------------------
    scored = sum(
        1
        for rows in raw_matches.values()
        for r in rows
        if r.match_date is not None and r.home_goals is not None and r.away_goals is not None
    )
    data.report = {
        "files": {FILES[k]: len(v) for k, v in raw_matches.items()},
        "players_file": FILES["fifa"],
        "raw_rows_total": sum(len(v) for v in raw_matches.values()),
        "raw_scored_rows": scored,
        "unified_matches": len(data.matches),
        "players": len(players),
        "teams": len(data.registry),
        "source_choices": [
            {
                "competition": c.competition_id,
                "season": c.season,
                "chosen": c.chosen,
                "scored_counts": c.counts,
            }
            for c in data.source_choices
        ],
    }
    return data
