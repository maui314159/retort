"""Loaders for the six Kaggle CSV datasets.

CONTEXT
-------
Every file uses different column names, date formats ("2023-09-24",
"29/03/2003", "2012-05-19 18:30:00"), goal encodings (int, "1.0", "NA",
"-") and team-name conventions.  This module turns them all into
:class:`~soccer_mcp.models.Match` / :class:`~soccer_mcp.models.Player`
objects and deduplicates fixtures that appear in several files
(e.g. the 2012-2019 Brasileirão is present in *both*
``Brasileirao_Matches.csv`` and ``novo_campeonato_brasileiro.csv``, and
``BR-Football-Dataset.csv`` overlaps both).

Dedup rules
-----------
* key: ``(competition, season, home_key, away_key)`` — leagues meet twice
  per season with swapped venues, cups swap legs, so the ordered pair is
  unique within a season.
* the first-loaded row wins (file order = trust order); missing fields
  (score, venue, stats) are filled from later duplicates, which repairs
  e.g. the 81 unrecorded 2022 Brasileirão scores via BR-Football data.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .models import Match, MatchStats, Player
from .normalize import TeamRegistry

# --------------------------------------------------------------------------
# Canonical competition names
# --------------------------------------------------------------------------

COMPETITIONS: dict[str, str] = {
    "brasileirao": "Brasileirão Série A",
    "brasileirão série a": "Brasileirão Série A",
    "serie a": "Brasileirão Série A",
    "série a": "Brasileirão Série A",
    "serie b": "Brasileirão Série B",
    "série b": "Brasileirão Série B",
    "serie c": "Brasileirão Série C",
    "série c": "Brasileirão Série C",
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
}

#: Competitions played as a league (a standings table is meaningful).
LEAGUE_COMPETITIONS = {"Brasileirão Série A", "Brasileirão Série B", "Brasileirão Série C"}

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M")


def parse_date(value: str) -> tuple[date | None, str | None]:
    """Parse a date(datetime) string in any of the dataset formats.

    Returns ``(date, kickoff_time)``; both are ``None`` for "NA"/empty.
    """
    text = (value or "").strip()
    if not text or text.upper() in ("NA", "N/A", "-"):
        return None, None
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            kickoff = parsed.strftime("%H:%M") if fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M") else None
            return parsed.date(), kickoff
        except ValueError:
            continue
    return None, None


def parse_int(value: str) -> int | None:
    """Parse a goal count tolerant of int, float ("1.0"), "NA", "-", empty."""
    text = (value or "").strip()
    if not text or text.upper() in ("NA", "N/A", "-"):
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Raw rows
# --------------------------------------------------------------------------


@dataclass
class RawMatch:
    competition: str
    season: int | None
    date: date | None
    kickoff: str | None
    home_raw: str
    away_raw: str
    home_goals: int | None
    away_goals: int | None
    round_label: str | None
    stage: str | None
    venue: str | None
    halftime: str | None
    stats: MatchStats | None


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------
# Per-file parsers
# --------------------------------------------------------------------------


def _load_brasileirao(path: Path) -> list[RawMatch]:
    rows: list[RawMatch] = []
    for r in _read_rows(path):
        when, kickoff = parse_date(r.get("datetime", ""))
        rows.append(
            RawMatch(
                competition="Brasileirão Série A",
                season=parse_int(r.get("season", "")),
                date=when,
                kickoff=kickoff,
                home_raw=r.get("home_team", ""),
                away_raw=r.get("away_team", ""),
                home_goals=parse_int(r.get("home_goal", "")),
                away_goals=parse_int(r.get("away_goal", "")),
                round_label=f"Round {r.get('round', '').strip()}" if r.get("round", "").strip() else None,
                stage=None,
                venue=None,
                halftime=None,
                stats=None,
            )
        )
    return rows


_CUP_FINAL_ROUNDS = {"7": "Semifinal", "8": "Final"}


def _load_copa_do_brasil(path: Path) -> list[RawMatch]:
    rows: list[RawMatch] = []
    for r in _read_rows(path):
        when, kickoff = parse_date(r.get("datetime", ""))
        rnd = (r.get("round") or "").strip()
        rows.append(
            RawMatch(
                competition="Copa do Brasil",
                season=parse_int(r.get("season", "")),
                date=when,
                kickoff=kickoff,
                home_raw=r.get("home_team", ""),
                away_raw=r.get("away_team", ""),
                home_goals=parse_int(r.get("home_goal", "")),
                away_goals=parse_int(r.get("away_goal", "")),
                round_label=_CUP_FINAL_ROUNDS.get(rnd, f"Round {rnd}" if rnd else None),
                stage=None,
                venue=None,
                halftime=None,
                stats=None,
            )
        )
    return rows


_LIB_STAGES = {
    "group stage": "Group Stage",
    "round of 16": "Round of 16",
    "quarterfinals": "Quarterfinals",
    "semifinals": "Semifinals",
    "final": "Final",
}


def _load_libertadores(path: Path) -> list[RawMatch]:
    rows: list[RawMatch] = []
    for r in _read_rows(path):
        when, kickoff = parse_date(r.get("datetime", ""))
        stage = (r.get("stage") or "").strip().lower()
        rows.append(
            RawMatch(
                competition="Copa Libertadores",
                season=parse_int(r.get("season", "")),
                date=when,
                kickoff=kickoff,
                home_raw=r.get("home_team", ""),
                away_raw=r.get("away_team", ""),
                home_goals=parse_int(r.get("home_goal", "")),
                away_goals=parse_int(r.get("away_goal", "")),
                round_label=_LIB_STAGES.get(stage, stage or None),
                stage=stage or None,
                venue=None,
                halftime=None,
                stats=None,
            )
        )
    return rows


def _load_novo_brasileirao(path: Path) -> list[RawMatch]:
    rows: list[RawMatch] = []
    for r in _read_rows(path):
        when, _ = parse_date(r.get("Data", ""))
        rnd = (r.get("Rodada") or "").strip()
        rows.append(
            RawMatch(
                competition="Brasileirão Série A",
                season=parse_int(r.get("Ano", "")),
                date=when,
                kickoff=None,
                home_raw=r.get("Equipe_mandante", ""),
                away_raw=r.get("Equipe_visitante", ""),
                home_goals=parse_int(r.get("Gols_mandante", "")),
                away_goals=parse_int(r.get("Gols_visitante", "")),
                round_label=f"Round {rnd}" if rnd else None,
                stage=None,
                venue=(r.get("Arena") or "").strip() or None,
                halftime=None,
                stats=None,
            )
        )
    return rows


def _load_br_football(path: Path) -> list[RawMatch]:
    rows: list[RawMatch] = []
    for r in _read_rows(path):
        tournament = (r.get("tournament") or "").strip()
        competition = COMPETITIONS.get(tournament.lower(), tournament)
        # Known source-data error: "Serie A, Brasilia FC vs CA Taguatinga,
        # 2016-01-30" is a Copa Verde fixture mislabeled as Série A in the
        # Kaggle file (neither club ever played Série A).  Drop it.
        if (
            competition == "Brasileirão Série A"
            and (r.get("date") or "").startswith("2016-01-30")
            and (r.get("home") or "").strip() == "Brasilia FC"
        ):
            continue
        when, _ = parse_date(r.get("date", ""))
        ht = (r.get("ht_result") or "").strip().upper() or None
        stats = MatchStats(
            home_corners=parse_int(r.get("home_corner", "")),
            away_corners=parse_int(r.get("away_corner", "")),
            home_shots=parse_int(r.get("home_shots", "")),
            away_shots=parse_int(r.get("away_shots", "")),
            home_attacks=parse_int(r.get("home_attack", "")),
            away_attacks=parse_int(r.get("away_attack", "")),
        )
        rows.append(
            RawMatch(
                competition=competition,
                season=int(when.year) if when else None,
                date=when,
                kickoff=(r.get("time") or "").strip()[:5] or None,
                home_raw=r.get("home", ""),
                away_raw=r.get("away", ""),
                home_goals=parse_int(r.get("home_goal", "")),
                away_goals=parse_int(r.get("away_goal", "")),
                round_label=None,
                stage=None,
                venue=None,
                halftime=ht if ht in ("WON", "DRAW", "LOST") else None,
                stats=None if stats.is_empty else stats,
            )
        )
    return rows


# --------------------------------------------------------------------------
# FIFA players
# --------------------------------------------------------------------------

_SKILL_COLUMNS = (
    "Crossing Finishing HeadingAccuracy ShortPassing Volleys Dribbling Curve "
    "FKAccuracy LongPassing BallControl Acceleration SprintSpeed Agility "
    "Reactions Balance ShotPower Jumping Stamina Strength LongShots Aggression "
    "Interceptions Positioning Vision Penalties Composure Marking "
    "StandingTackle SlidingTackle GKDiving GKHandling GKKicking GKPositioning "
    "GKReflexes"
).split()


def _load_players(path: Path) -> list[Player]:
    players: list[Player] = []
    for r in _read_rows(path):
        get = lambda key: (r.get(key) or "").strip()  # noqa: E731
        skills: dict[str, int] = {}
        for col in _SKILL_COLUMNS:
            value = parse_int(get(col))
            if value is not None:
                skills[col] = value
        players.append(
            Player(
                id=get("ID"),
                name=get("Name"),
                age=parse_int(get("Age")),
                nationality=get("Nationality"),
                overall=parse_int(get("Overall")),
                potential=parse_int(get("Potential")),
                club=get("Club"),
                position=get("Position") or None,
                jersey=parse_int(get("Jersey Number")),
                height=get("Height") or None,
                weight=get("Weight") or None,
                foot=get("Preferred Foot") or None,
                value=get("Value") or None,
                wage=get("Wage") or None,
                skills=skills,
            )
        )
    return players


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


@dataclass
class KnowledgeBase:
    """Everything the MCP server needs: registry + matches + players."""

    registry: TeamRegistry
    matches: list[Match]
    players: list[Player]


def _source_label(path: Path) -> str:
    return path.name


def load_knowledge_base(data_dir: str | Path) -> KnowledgeBase:
    """Load all six CSVs, build the team registry and deduplicate matches.

    Args:
        data_dir: directory containing the ``*.csv`` files (default
            ``data/kaggle`` relative to the repo root).

    Returns:
        A :class:`KnowledgeBase` with a finalized registry, the unified
        match list (newest season sources fill gaps in older ones) and
        the FIFA player list.
    """
    data = Path(data_dir)

    # File order = trust order for conflicting scores; later files still
    # donate missing fields (stats, venue, scores) to earlier duplicates.
    raw: list[RawMatch] = []
    raw += _load_brasileirao(data / "Brasileirao_Matches.csv")
    raw += _load_novo_brasileirao(data / "novo_campeonato_brasileiro.csv")
    raw += _load_copa_do_brasil(data / "Brazilian_Cup_Matches.csv")
    raw += _load_libertadores(data / "Libertadores_Matches.csv")
    raw += _load_br_football(data / "BR-Football-Dataset.csv")

    # Phase 1 - registry from all raw team names.
    name_counts: Counter[str] = Counter()
    for row in raw:
        if row.home_raw.strip():
            name_counts[row.home_raw.strip()] += 1
        if row.away_raw.strip():
            name_counts[row.away_raw.strip()] += 1
    registry = TeamRegistry()
    for name, count in name_counts.items():
        registry.add_name(name, count)
    registry.finalize()

    # Phase 2 - map rows to entity keys.
    from .normalize import canonical_key

    # Precompute: base -> most prominent region entity with that base.
    stateless_target: dict[str, tuple[str, str | None]] = {}
    for team in registry.teams:  # sorted by match_count desc
        if team.region is not None and team.base not in stateless_target:
            stateless_target[team.base] = (team.base, team.region)

    def key_of(raw_name: str) -> tuple[str, str | None]:
        base, region = canonical_key(raw_name)
        if region is None and base in stateless_target:
            return stateless_target[base]
        return base, region

    # Phase 3 - dedup + assemble.
    #
    # Primary key: (competition, season, home, away) for leagues - the
    # ordered pair is unique per season, and round labels differ between
    # files so they must NOT be part of the key.  Cup competitions include
    # the round/stage because the same ordered pair can legitimately meet
    # twice in one season (e.g. Libertadores group stage *and* round of 16).
    # Secondary pass: same competition/pair whose dates differ by <= 3 days
    # are the same fixture recorded in another file - this catches league
    # rows whose recorded dates differ by a day and cup rows recorded under
    # a different season (the COVID-delayed 2020 Copa do Brasil final, played
    # Feb/Mar 2021).
    seen: dict[tuple, Match] = {}
    by_pair: dict[tuple[str, str, str], list[Match]] = {}
    matches: list[Match] = []

    def _merge(existing: Match, row: RawMatch) -> None:
        # Fill missing fields from the duplicate (repairs unrecorded 2022
        # scores and attaches BR-Football stats to league matches).
        if existing.home_goals is None and row.home_goals is not None:
            existing.home_goals = row.home_goals
            existing.away_goals = row.away_goals
        if existing.venue is None and row.venue:
            existing.venue = row.venue
        if existing.round_label is None and row.round_label:
            existing.round_label = row.round_label
        if existing.stage is None and row.stage:
            existing.stage = row.stage
        if existing.kickoff is None and row.kickoff:
            existing.kickoff = row.kickoff
        if existing.halftime is None and row.halftime:
            existing.halftime = row.halftime
        if existing.stats is None and row.stats is not None:
            existing.stats = row.stats

    for row in raw:
        home_base, home_region = key_of(row.home_raw)
        away_base, away_region = key_of(row.away_raw)
        home_key = f"{home_base}|{home_region}" if home_region else f"{home_base}|"
        away_key = f"{away_base}|{away_region}" if away_region else f"{away_base}|"
        if home_key == away_key:
            # Source-data error: a club cannot play itself (e.g. two 2019
            # Copa do Brasil rows recorded as "Bragantino - PA" vs
            # "Bragantino - PA").  Drop rather than produce nonsense stats.
            continue
        if row.competition in LEAGUE_COMPETITIONS:
            dedup_key: tuple = (row.competition, row.season, home_key, away_key)
        else:
            dedup_key = (row.competition, row.season, home_key, away_key, row.round_label, row.stage)
        if dedup_key in seen:
            _merge(seen[dedup_key], row)
            continue
        if row.date is not None:
            near = next(
                (
                    m
                    for m in by_pair.get((row.competition, home_key, away_key), [])
                    if m.date is not None and abs((m.date - row.date).days) <= 3
                ),
                None,
            )
            if near is not None:
                _merge(near, row)
                continue
        match = Match(
            competition=row.competition,
            season=row.season,
            date=row.date,
            home=home_key,
            away=away_key,
            home_goals=row.home_goals,
            away_goals=row.away_goals,
            round_label=row.round_label,
            stage=row.stage,
            venue=row.venue,
            kickoff=row.kickoff,
            halftime=row.halftime,
            stats=row.stats,
        )
        seen[dedup_key] = match
        by_pair.setdefault((row.competition, home_key, away_key), []).append(match)
        matches.append(match)

    # Sort: competition, season, date (matches without dates last within group).
    matches.sort(
        key=lambda m: (
            m.competition,
            m.season if m.season is not None else 0,
            m.date is None,
            m.date,
            m.away,
        )
    )

    # FIFA players + cross-file club attribution.
    players = _load_players(data / "fifa_data.csv")
    club_counts = Counter(p.club for p in players if p.club)
    for club, count in club_counts.items():
        registry.add_players(club, count)

    return KnowledgeBase(registry=registry, matches=matches, players=players)
