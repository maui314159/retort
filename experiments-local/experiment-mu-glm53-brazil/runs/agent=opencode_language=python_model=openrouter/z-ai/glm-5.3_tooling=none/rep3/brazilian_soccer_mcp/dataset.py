"""
Dataset loading and assembly for the Brazilian Soccer MCP server.

Context block
-------------
Why:
    Five match CSVs and one player CSV overlap and disagree: the same
    Brasileirão fixture appears in up to three files with different team
    spellings and occasionally different dates, and BR-Football-Dataset
    even contains duplicated rows.  Naive concatenation would double-count
    matches, skew standings and break head-to-head records, so the data is
    assembled into a *canonical* match index before any query runs.

What:
    * ``load_matches`` / ``load_players`` - parse the six CSVs into typed
      records (``Match`` / ``Player``), tolerating every observed quirk:
      float-formatted goals ("1.0"), "NA" scores, DD/MM/YYYY vs ISO dates,
      state-suffixed team names, UTF-8 accents.
    * ``Dataset`` - the assembled knowledge graph:
        - ``registry``  : every team spelling -> ``Club`` entity,
        - ``raw_matches``: all parsed rows from the five match files,
        - ``matches``    : canonical index - for each (competition, season)
          only the highest-priority source is kept (dedicated files first,
          then novo 2003-2011 history, then BR-Football for 2022-2023),
          which removes cross-file double counting,
        - ``players``    : the FIFA database, joined to clubs by registry.
    * ``load_dataset`` - builds and caches the ``Dataset`` (loading is
      ~1s; queries then run in-memory, meeting the TASK.md performance
      targets of <2s simple / <5s aggregate lookups).

Test:
    BDD GWT scenarios in ``tests/test_dataset.py``: file coverage counts,
    canonical-source selection, absence of duplicate fixtures per season,
    and club resolution of every canonical match.

Spec references:
    TASK.md "Provided Data" (all six files must be loadable and queryable),
    "Success Criteria" -> "Data Coverage" ("All 6 CSV files are loadable
    and queryable", "Cross-file queries work").
"""

from __future__ import annotations

import csv
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .models import Match, MatchStats, Player
from .normalize import (
    TeamName,
    parse_date,
    parse_int,
    resolve_competition,
)
from .registry import ClubRegistry

DATA_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "data" / "kaggle"

#: Lower number = higher preference when several sources cover the same
#: (competition, season).  Dedicated competition files beat the historical
#: novo file (overlaps 2012-2019 with shifted dates) which beats the
#: BR-Football aggregate (incomplete early seasons, duplicated 2021 rows).
SOURCE_PRIORITY: dict[str, int] = {
    "Brasileirao_Matches": 0,
    "Brazilian_Cup_Matches": 0,
    "Libertadores_Matches": 0,
    "novo_campeonato_brasileiro": 1,
    "BR-Football-Dataset": 2,
}

#: FIFA skill rating columns exposed on each player record.
_SKILL_COLUMNS = (
    "Crossing",
    "Finishing",
    "HeadingAccuracy",
    "ShortPassing",
    "Volleys",
    "Dribbling",
    "Curve",
    "FKAccuracy",
    "LongPassing",
    "BallControl",
    "Acceleration",
    "SprintSpeed",
    "Agility",
    "Reactions",
    "Balance",
    "ShotPower",
    "Jumping",
    "Stamina",
    "Strength",
    "LongShots",
    "Aggression",
    "Interceptions",
    "Positioning",
    "Vision",
    "Penalties",
    "Composure",
    "StandingTackle",
    "SlidingTackle",
)


@dataclass
class Dataset:
    """Assembled, deduplicated soccer knowledge base."""

    registry: ClubRegistry = field(default_factory=ClubRegistry)
    raw_matches: list[Match] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)  # canonical index
    players: list[Player] = field(default_factory=list)
    #: (competition, season) -> {"source": str, "matches": int}
    season_sources: dict[tuple[str, int | None], dict] = field(default_factory=dict)
    #: per-file load statistics
    file_stats: dict[str, dict] = field(default_factory=dict)

    # -- club helpers ----------------------------------------------------

    def club_display(self, team: TeamName) -> str:
        club = self.registry.get(team)
        return club.display if club else (team.base or "?")

    def club_id(self, team: TeamName) -> str:
        club = self.registry.get(team)
        return club.id if club else team.key

    def matches_for_club(self, club_id: str, *, canonical_only: bool = True) -> list[Match]:
        pool = self.matches if canonical_only else self.raw_matches
        return [m for m in pool if (m._home_club == club_id) or (m._away_club == club_id)]


# --------------------------------------------------------------------------
# CSV loaders
# --------------------------------------------------------------------------


def _iter_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _clean_raw_name(value: str) -> str:
    return (value or "").strip()


def _make_match(
    *,
    source: str,
    date: object,
    home_raw: str,
    away_raw: str,
    home_goals: object,
    away_goals: object,
    competition: str,
    season: object,
    round_label: str | None = None,
    stage: str | None = None,
    stadium: str | None = None,
    stats: MatchStats | None = None,
) -> Match:
    from .normalize import normalize_team

    home_raw = _clean_raw_name(home_raw)
    away_raw = _clean_raw_name(away_raw)
    return Match(
        date=parse_date(date),
        home_name=home_raw,
        away_name=away_raw,
        home_team=normalize_team(home_raw),
        away_team=normalize_team(away_raw),
        home_goals=parse_int(home_goals),
        away_goals=parse_int(away_goals),
        competition=competition,
        season=parse_int(season),
        round=round_label,
        stage=stage,
        source=source,
        stadium=stadium,
        stats=stats,
    )


def _load_brasileirao(data_dir: Path) -> list[Match]:
    rows = _iter_csv(data_dir / "Brasileirao_Matches.csv")
    return [
        _make_match(
            source="Brasileirao_Matches",
            date=r.get("datetime"),
            home_raw=r.get("home_team", ""),
            away_raw=r.get("away_team", ""),
            home_goals=r.get("home_goal"),
            away_goals=r.get("away_goal"),
            competition="Brasileirão Serie A",
            season=r.get("season"),
            round_label=str(r.get("round") or "") or None,
        )
        for r in rows
    ]


def _load_cup(data_dir: Path) -> list[Match]:
    rows = _iter_csv(data_dir / "Brazilian_Cup_Matches.csv")
    return [
        _make_match(
            source="Brazilian_Cup_Matches",
            date=r.get("datetime"),
            home_raw=r.get("home_team", ""),
            away_raw=r.get("away_team", ""),
            home_goals=r.get("home_goal"),
            away_goals=r.get("away_goal"),
            competition="Copa do Brasil",
            season=r.get("season"),
            round_label=str(r.get("round") or "") or None,
        )
        for r in rows
    ]


def _load_libertadores(data_dir: Path) -> list[Match]:
    rows = _iter_csv(data_dir / "Libertadores_Matches.csv")
    return [
        _make_match(
            source="Libertadores_Matches",
            date=r.get("datetime"),
            home_raw=r.get("home_team", ""),
            away_raw=r.get("away_team", ""),
            home_goals=r.get("home_goal"),
            away_goals=r.get("away_goal"),
            competition="Copa Libertadores",
            season=r.get("season"),
            stage=(r.get("stage") or "").strip() or None,
        )
        for r in rows
    ]


def _load_novo(data_dir: Path) -> list[Match]:
    rows = _iter_csv(data_dir / "novo_campeonato_brasileiro.csv")
    out: list[Match] = []
    for r in rows:
        out.append(
            _make_match(
                source="novo_campeonato_brasileiro",
                date=r.get("Data"),
                home_raw=r.get("Equipe_mandante", ""),
                away_raw=r.get("Equipe_visitante", ""),
                home_goals=r.get("Gols_mandante"),
                away_goals=r.get("Gols_visitante"),
                competition="Brasileirão Serie A",
                season=r.get("Ano"),
                round_label=str(r.get("Rodada") or "") or None,
                stadium=(r.get("Arena") or "").strip() or None,
            )
        )
    return out


def _load_br_football(data_dir: Path) -> list[Match]:
    rows = _iter_csv(data_dir / "BR-Football-Dataset.csv")
    out: list[Match] = []
    for r in rows:
        tournament = (r.get("tournament") or "").strip()
        competition = resolve_competition(tournament) or tournament
        stats = MatchStats(
            home_corners=parse_int(r.get("home_corner")),
            away_corners=parse_int(r.get("away_corner")),
            home_shots=parse_int(r.get("home_shots")),
            away_shots=parse_int(r.get("away_shots")),
            home_attacks=parse_int(r.get("home_attack")),
            away_attacks=parse_int(r.get("away_attack")),
            home_ht_result=(r.get("ht_result") or "").strip() or None,
            away_ht_result=(r.get("at_result") or "").strip() or None,
            kickoff_time=(r.get("time") or "").strip() or None,
        )
        out.append(
            _make_match(
                source="BR-Football-Dataset",
                date=r.get("date"),
                home_raw=r.get("home", ""),
                away_raw=r.get("away", ""),
                home_goals=r.get("home_goal"),
                away_goals=r.get("away_goal"),
                competition=competition,
                season=(r.get("date") or "")[:4] or None,
                stats=stats,
            )
        )
    return out


def load_matches(data_dir: Path = DATA_DIR_DEFAULT) -> tuple[list[Match], dict[str, int]]:
    """Load all five match CSVs; returns (raw matches, per-file row counts)."""
    loaders = {
        "Brasileirao_Matches": _load_brasileirao,
        "Brazilian_Cup_Matches": _load_cup,
        "Libertadores_Matches": _load_libertadores,
        "novo_campeonato_brasileiro": _load_novo,
        "BR-Football-Dataset": _load_br_football,
    }
    raw: list[Match] = []
    counts: dict[str, int] = {}
    for name, loader in loaders.items():
        matches = loader(data_dir)
        counts[name] = len(matches)
        raw.extend(matches)
    return raw, counts


def load_players(data_dir: Path = DATA_DIR_DEFAULT) -> list[Player]:
    """Load the FIFA player database."""
    rows = _iter_csv(data_dir / "fifa_data.csv")
    players: list[Player] = []
    for r in rows:
        name = (r.get("Name") or "").strip()
        if not name:
            continue
        overall = parse_int(r.get("Overall")) or 0
        potential = parse_int(r.get("Potential")) or overall
        skills: dict[str, int] = {}
        for col in _SKILL_COLUMNS:
            value = parse_int(r.get(col))
            if value is not None:
                skills[col.lower()] = value
        players.append(
            Player(
                player_id=parse_int(r.get("ID")) or 0,
                name=name,
                age=parse_int(r.get("Age")),
                nationality=(r.get("Nationality") or "").strip(),
                overall=overall,
                potential=potential,
                club=(r.get("Club") or "").strip(),
                position=(r.get("Position") or "").strip() or None,
                jersey_number=parse_int(r.get("Jersey Number")),
                preferred_foot=(r.get("Preferred Foot") or "").strip() or None,
                value=(r.get("Value") or "").strip() or None,
                wage=(r.get("Wage") or "").strip() or None,
                height=(r.get("Height") or "").strip() or None,
                weight=(r.get("Weight") or "").strip() or None,
                skills=skills,
            )
        )
    return players


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def _build_canonical(
    raw: list[Match], dataset: Dataset
) -> tuple[list[Match], dict[tuple[str, int | None], dict]]:
    """Pick one authoritative source per (competition, season) and dedup.

    Guarantees a fixture (date, home club, away club) appears at most once
    within a competition-season even if the chosen source repeats it.
    """
    groups: dict[tuple[str, int | None], list[Match]] = {}
    for m in raw:
        if not m.home_team.base and not m.away_team.base:
            continue  # unparseable row (no teams at all)
        groups.setdefault((m.competition, m.season), []).append(m)

    canonical: list[Match] = []
    season_sources: dict[tuple[str, int | None], dict] = {}
    for key, candidates in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
        best_source = min(
            {m.source for m in candidates},
            key=lambda s: SOURCE_PRIORITY.get(s, 99),
        )
        chosen = [m for m in candidates if m.source == best_source]
        seen: set[tuple] = set()
        deduped: list[Match] = []
        for m in sorted(chosen, key=lambda x: (x.date is None, x.date or "")):
            ident = (m.date, m._home_club, m._away_club)
            if ident in seen:
                continue
            seen.add(ident)
            deduped.append(m)
        season_sources[key] = {"source": best_source, "matches": len(deduped)}
        canonical.extend(deduped)

    canonical.sort(key=lambda m: (m.date is None, m.date or "", m.competition))
    return canonical, season_sources


def _attach_extended_stats(dataset: Dataset) -> None:
    """Join BR-Football extended stats onto canonical matches.

    BR-Football is the only source with corners/shots/attacks and half-time
    labels; when it is not the authoritative source for a season the stats
    are attached to the canonical record by (date, home club, away club).
    """
    by_key: dict[tuple, MatchStats] = {}
    for m in dataset.raw_matches:
        if m.source != "BR-Football-Dataset" or m.stats is None:
            continue
        if not m.date:
            continue
        key = (m.date, m._home_club, m._away_club)
        if key not in by_key:
            by_key[key] = m.stats
    attached = 0
    for m in dataset.matches:
        if m.stats is not None or not m.date:
            continue
        stats = by_key.get((m.date, m._home_club, m._away_club))
        if stats is not None:
            m.stats = stats
            attached += 1
    dataset.file_stats["extended_stats_attached"] = {"matches": attached}


def build_dataset(data_dir: Path = DATA_DIR_DEFAULT) -> Dataset:
    """Load everything and assemble the knowledge base."""
    dataset = Dataset()
    raw, counts = load_matches(data_dir)
    dataset.file_stats.update({name: {"rows": n} for name, n in counts.items()})
    dataset.raw_matches = raw
    players = load_players(data_dir)
    dataset.players = players
    dataset.file_stats["fifa_data"] = {"rows": len(players)}

    # 1. Register every team spelling from the match files.
    for m in raw:
        if m.home_team.base:
            dataset.registry.register(m.home_name)
        if m.away_team.base:
            dataset.registry.register(m.away_name)

    # 2. Count match appearances per club (drives merge dominance).
    for m in raw:
        if m.home_team.base:
            dataset.registry.add_match_count(m.home_team)
        if m.away_team.base:
            dataset.registry.add_match_count(m.away_team)

    # 3. Register FIFA club strings so they join the same graph.
    for p in players:
        if p.club:
            dataset.registry.register(p.club)

    # 4. Merge state-less variants into dominant state-qualified clubs.
    dataset.registry.finalize()

    # 5. Resolve club ids on every raw match (used by canonical build).
    for m in raw:
        m._home_club = dataset.club_id(m.home_team)
        m._away_club = dataset.club_id(m.away_team)

    # 6. Canonical index + extended-stat join.
    dataset.matches, dataset.season_sources = _build_canonical(raw, dataset)
    _attach_extended_stats(dataset)

    # 7. Attach players to clubs and set display names on canonical matches.
    for p in players:
        from .normalize import normalize_team

        if p.club:
            p._club_team = normalize_team(p.club)
            club = dataset.registry.get(p._club_team)
            if club is not None:
                p._club_id = club.id
                club.player_count += 1
    for m in dataset.matches:
        m.home_name = dataset.club_display(m.home_team)
        m.away_name = dataset.club_display(m.away_team)

    return dataset


# --------------------------------------------------------------------------
# Cached singleton access
# --------------------------------------------------------------------------

_lock = threading.Lock()
_cache: dict[Path, Dataset] = {}


def load_dataset(data_dir: Path | str | None = None) -> Dataset:
    """Return the cached ``Dataset`` for ``data_dir`` (default: bundled data)."""
    path = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
    path = path.resolve()
    with _lock:
        if path not in _cache:
            _cache[path] = build_dataset(path)
        return _cache[path]
