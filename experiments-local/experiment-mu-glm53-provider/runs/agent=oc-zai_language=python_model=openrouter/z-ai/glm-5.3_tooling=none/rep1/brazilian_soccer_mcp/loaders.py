"""
CSV ingestion for the six Kaggle datasets.

Context (Why): TASK.md "Provided Data" specifies 5 match datasets + 1 FIFA
player dataset that MUST all be loadable and queryable (success criterion
"All 6 CSV files are loadable and queryable"). The files disagree on date
formats ("2023-09-24", "29/03/2003", "2012-05-19 18:30:00", "NA"), on team
naming (see normalizer.py), on score formats (int vs float vs quoted string
vs "NA") and on encoding (UTF-8 Portuguese accents must survive).

What (load_all pipeline):
    1. Read + stage the 5 match CSVs, registering every team name with the
       TeamRegistry (provisional ids).
    2. Register FIFA club names too - BEFORE finalizing - so that player
       clubs and match teams resolve to the same canonical identities
       (cross-file queries requirement).
    3. ``registry.finalize()`` fixes ambiguities (e.g. bare "Flamengo" ->
       flamengo-rj) and yields the provisional -> canonical id remap.
    4. Build unified Match rows (final ids + display names), skipping
       broken rows (missing teams, or no date AND no score).
    5. Deduplicate matches that two sources both recorded (Série A
       2012-2019 is in BOTH Brasileirao_Matches.csv and
       novo_campeonato_brasileiro.csv; Copa do Brasil 2014-2021 is in both
       Brazilian_Cup_Matches.csv and BR-Football-Dataset.csv), keeping the
       most authoritative source's copy.
    6. Build the FIFA Player list and a team -> matches index so simple
       lookups stay fast (spec: simple lookups < 2 s; in practice < 100 ms).

Test: tests/test_loaders.py asserts file coverage, row survival, date-format
handling and deduplication against the real CSVs.
Spec reference: TASK.md "Provided Data", "Data Quality Notes" -> "Date
Formats" / "Character Encoding", "Success Criteria" -> "Data Coverage".
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .models import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    LIBERTADORES,
    Match,
    Player,
)
from .normalizer import TeamRegistry, parse_name

# Files, in descending authority for cross-source deduplication.
MATCH_FILES: list[str] = [
    "Brasileirao_Matches.csv",
    "Libertadores_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "novo_campeonato_brasileiro.csv",
    "BR-Football-Dataset.csv",
]
PLAYER_FILE = "fifa_data.csv"

_TEAM_COLUMNS = (
    "home_team", "away_team", "home", "away",
    "Equipe_mandante", "Equipe_visitante",
)

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y")


# ---------------------------------------------------------------------------
# Small tolerant parsers
# ---------------------------------------------------------------------------

def parse_date(raw: Optional[str]) -> Optional[date]:
    """Parse every date format found in the datasets; NA/blank -> None.

    Spec reference: TASK.md "Data Quality Notes" -> "Date Formats".
    """
    if raw is None:
        return None
    text = str(raw).strip().strip('"')
    if not text or text.upper() in {"NA", "N/A", "NULL", "NONE"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def to_int(raw: Optional[str]) -> Optional[int]:
    """int() tolerant of floats ("2.0"), quotes, blanks and NA."""
    if raw is None:
        return None
    text = str(raw).strip().strip('"')
    if not text or text.upper() in {"NA", "N/A", "NULL", "NONE"}:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def parse_height_cm(raw: Optional[str]) -> Optional[int]:
    """FIFA height "5'9" (feet'inches") -> centimeters."""
    if not raw:
        return None
    text = str(raw).strip()
    try:
        feet, inches = text.split("'")
        return round(int(feet) * 30.48 + int(inches) * 2.54)
    except (ValueError, AttributeError):
        return None


def parse_weight_kg(raw: Optional[str]) -> Optional[int]:
    """FIFA weight "150lbs" -> kilograms."""
    if not raw:
        return None
    text = str(raw).strip().lower().replace("lbs", "").replace("lb", "")
    try:
        return round(int(text) * 0.45359237)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Loaded bundle
# ---------------------------------------------------------------------------

@dataclass
class SoccerData:
    """Everything loaded from data/kaggle, ready for the service layer."""

    matches: list[Match] = field(default_factory=list)
    players: list[Player] = field(default_factory=list)
    registry: TeamRegistry = field(default_factory=TeamRegistry)
    # canonical team id -> matches involving that team (either side)
    matches_by_team: dict[str, list[Match]] = field(default_factory=dict)
    # canonical team id -> raw FIFA club strings (cross-file bridge)
    fifa_clubs_by_team: dict[str, list[str]] = field(default_factory=dict)
    # raw FIFA club string -> players
    players_by_club: dict[str, list[Player]] = field(default_factory=dict)
    skipped_rows: int = 0
    duplicates_removed: int = 0
    source_row_counts: dict[str, int] = field(default_factory=dict)
    # (competition, season) -> {source: raw match count} BEFORE dedup.
    # Used to pick the single authoritative source for standings/records so
    # overlapping datasets never double-count a fixture.
    source_counts_by_season: dict[tuple[str, Optional[int]], dict[str, int]] = field(
        default_factory=dict
    )


# ---------------------------------------------------------------------------
# Per-file row -> Match builders
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _mk(date_val, home_id, away_id, hg, ag, competition, season, round_no,
        source, display_for, stage=None, venue=None, **stats) -> Optional[Match]:
    if not home_id or not away_id or home_id == "?" or away_id == "?":
        return None
    if date_val is None and hg is None and ag is None:
        return None  # fully broken row (e.g. Libertadores all-"NA" row)
    return Match(
        date=date_val,
        home_id=home_id,
        away_id=away_id,
        home_display=display_for(home_id),
        away_display=display_for(away_id),
        home_goals=hg,
        away_goals=ag,
        competition=competition,
        season=season,
        round_no=round_no,
        stage=stage,
        venue=venue,
        source=source,
        **stats,
    )


def _from_brasileirao(row, cid, disp, source) -> Optional[Match]:
    return _mk(
        parse_date(row.get("datetime")),
        cid(row.get("home_team", "")),
        cid(row.get("away_team", "")),
        to_int(row.get("home_goal")),
        to_int(row.get("away_goal")),
        BRASILEIRAO_A,
        to_int(row.get("season")),
        str(to_int(row.get("round")) or "") or None,
        source,
        disp,
    )


def _from_copa(row, cid, disp, source) -> Optional[Match]:
    return _mk(
        parse_date(row.get("datetime")),
        cid(row.get("home_team", "")),
        cid(row.get("away_team", "")),
        to_int(row.get("home_goal")),
        to_int(row.get("away_goal")),
        COPA_DO_BRASIL,
        to_int(row.get("season")),
        (row.get("round") or "").strip() or None,
        source,
        disp,
    )


def _from_libertadores(row, cid, disp, source) -> Optional[Match]:
    return _mk(
        parse_date(row.get("datetime")),
        cid(row.get("home_team", "")),
        cid(row.get("away_team", "")),
        to_int(row.get("home_goal")),
        to_int(row.get("away_goal")),
        LIBERTADORES,
        to_int(row.get("season")),
        None,
        source,
        disp,
        stage=(row.get("stage") or "").strip() or None,
    )


def _from_historic(row, cid, disp, source) -> Optional[Match]:
    return _mk(
        parse_date(row.get("Data")),
        cid(row.get("Equipe_mandante", "")),
        cid(row.get("Equipe_visitante", "")),
        to_int(row.get("Gols_mandante")),
        to_int(row.get("Gols_visitante")),
        BRASILEIRAO_A,
        to_int(row.get("Ano")),
        str(to_int(row.get("Rodada")) or "") or None,
        source,
        disp,
        venue=(row.get("Arena") or "").strip() or None,
    )


_BRFB_COMPETITIONS = {
    "Serie A": BRASILEIRAO_A,
    "Serie B": BRASILEIRAO_B,
    "Serie C": BRASILEIRAO_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


def _from_brfootball(row, cid, disp, source) -> Optional[Match]:
    competition = _BRFB_COMPETITIONS.get((row.get("tournament") or "").strip())
    if competition is None:
        return None
    match_date = parse_date(row.get("date"))
    return _mk(
        match_date,
        cid(row.get("home", "")),
        cid(row.get("away", "")),
        to_int(row.get("home_goal")),
        to_int(row.get("away_goal")),
        competition,
        match_date.year if match_date else None,
        None,
        source,
        disp,
        home_corners=to_int(row.get("home_corner")),
        away_corners=to_int(row.get("away_corner")),
        home_shots=to_int(row.get("home_shots")),
        away_shots=to_int(row.get("away_shots")),
        home_attacks=to_int(row.get("home_attack")),
        away_attacks=to_int(row.get("away_attack")),
        half_time_diff=to_int(row.get("ht_diff")),
        half_time_label=(row.get("ht_result") or "").strip() or None,
    )


_BUILDERS = {
    "Brasileirao_Matches.csv": _from_brasileirao,
    "Brazilian_Cup_Matches.csv": _from_copa,
    "Libertadores_Matches.csv": _from_libertadores,
    "novo_campeonato_brasileiro.csv": _from_historic,
    "BR-Football-Dataset.csv": _from_brfootball,
}


# ---------------------------------------------------------------------------
# FIFA players
# ---------------------------------------------------------------------------

_SKILL_COLUMNS = [
    "Crossing", "Finishing", "ShortPassing", "Volleys", "Dribbling", "Curve",
    "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed",
    "Agility", "Reactions", "Balance", "ShotPower", "Jumping", "Stamina",
    "Strength", "LongShots", "Aggression", "Interceptions", "Positioning",
    "Vision", "Penalties", "Composure", "DefensiveAwareness", "StandingTackle",
    "SlidingTackle", "GKDiving", "GKHandling", "GKKicking", "GKPositioning",
    "GKReflexes",
]

_MISSING = {"", "NA", "N/A", "None", "NULL", "-"}


def _club_ok(club: Optional[str]) -> bool:
    return bool(club) and club.strip() not in _MISSING


def _build_player(row: dict[str, str]) -> Optional[Player]:
    name = (row.get("Name") or "").strip()
    if not name:
        return None
    club = (row.get("Club") or "").strip()
    attrs: dict[str, object] = {}
    for col in _SKILL_COLUMNS:
        value = to_int(row.get(col))
        if value is not None:
            attrs[col] = value
    return Player(
        player_id=to_int(row.get("ID")) or 0,
        name=name,
        age=to_int(row.get("Age")),
        nationality=(row.get("Nationality") or "").strip(),
        overall=to_int(row.get("Overall")),
        potential=to_int(row.get("Potential")),
        club=club if _club_ok(club) else "",
        position=(row.get("Position") or "").strip() or None,
        jersey_number=to_int(row.get("Jersey Number")),
        preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
        height_raw=(row.get("Height") or "").strip() or None,
        weight_raw=(row.get("Weight") or "").strip() or None,
        height_cm=parse_height_cm(row.get("Height")),
        weight_kg=parse_weight_kg(row.get("Weight")),
        attrs=attrs,
    )


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _dedupe(matches: list[Match]) -> tuple[list[Match], int]:
    """Drop fixtures recorded by several sources, keeping the most authoritative.

    Key is fixture identity - (competition, season, home, away, home_goals,
    away_goals) WITHOUT the date - because the sources frequently record
    different dates for the same fixture (scheduled vs actually-played date),
    which an exact-date key would miss. The input list is pre-ordered by
    source authority, so the FIRST occurrence wins. Repeats of the same key
    within one source are kept: a competition can legitimately stage the same
    pairing with the same score twice in a season (e.g. Serie C group +
    knockout rounds).
    """
    seen: dict[tuple, str] = {}
    unique: list[Match] = []
    removed = 0
    for match in matches:
        key = (
            match.competition,
            match.season,
            match.home_id,
            match.away_id,
            match.home_goals,
            match.away_goals,
        )
        first_source = seen.get(key)
        if first_source is not None and first_source != match.source:
            removed += 1
            continue
        if first_source is None:
            seen[key] = match.source
        unique.append(match)
    return unique, removed


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def load_all(data_dir: str | Path) -> SoccerData:
    """Load every dataset under ``data_dir`` (default ./data/kaggle layout)."""
    root = Path(data_dir)
    registry = TeamRegistry()
    data = SoccerData(registry=registry)

    # Phase 1: stage match rows + register match team names
    staged: dict[str, list[dict[str, str]]] = {}
    name_to_pid: dict[str, str] = {}
    for file_name in MATCH_FILES:
        rows = _read_csv(root / file_name)
        data.source_row_counts[file_name] = len(rows)
        staged[file_name] = rows
        for row in rows:
            for col in _TEAM_COLUMNS:
                raw = (row.get(col) or "").strip()
                if not raw:
                    continue
                if raw not in name_to_pid:
                    name_to_pid[raw] = registry.register(raw)
                else:
                    registry.register(raw)  # keep counting occurrences

    # Phase 2: pre-register FIFA club names so clubs and match teams share
    # canonical identities (required for cross-file player+match queries)
    fifa_rows = _read_csv(root / PLAYER_FILE)
    data.source_row_counts[PLAYER_FILE] = len(fifa_rows)
    club_to_pid: dict[str, str] = {}
    for row in fifa_rows:
        club = (row.get("Club") or "").strip()
        if _club_ok(club):
            if club not in club_to_pid:
                club_to_pid[club] = registry.register(club)
            else:
                registry.register(club)

    # Phase 3: resolve ambiguities
    remap = registry.finalize()

    def canonical(raw_name: str) -> str:
        pid = name_to_pid.get(raw_name)
        if pid is None:
            parsed = parse_name(raw_name)
            pid = (
                f"{parsed.base}-{parsed.foreign}" if parsed.foreign
                else f"{parsed.base}-{parsed.state}" if parsed.state
                else parsed.base
            )
        return remap.get(pid, pid)

    def display_for(team_id: str) -> str:
        return registry.display(team_id)

    # Phase 4: build unified matches (source-authority order)
    for file_name in MATCH_FILES:
        builder = _BUILDERS[file_name]
        for row in staged[file_name]:
            match = builder(row, canonical, display_for, file_name)
            if match is None:
                data.skipped_rows += 1
            else:
                data.matches.append(match)
                season_counts = data.source_counts_by_season.setdefault(
                    (match.competition, match.season), {}
                )
                season_counts[match.source] = season_counts.get(match.source, 0) + 1

    # Phase 5: cross-source deduplication
    data.matches, data.duplicates_removed = _dedupe(data.matches)

    # Phase 6: FIFA players + club bridges
    for row in fifa_rows:
        player = _build_player(row)
        if player is None:
            data.skipped_rows += 1
            continue
        data.players.append(player)
        if player.club:
            data.players_by_club.setdefault(player.club, []).append(player)
            pid = club_to_pid[player.club]
            team_id = remap.get(pid, pid)
            if player.club not in data.fifa_clubs_by_team.setdefault(team_id, []):
                data.fifa_clubs_by_team[team_id].append(player.club)

    # Phase 7: team -> matches index, sorted chronologically
    for match in data.matches:
        for team_id in (match.home_id, match.away_id):
            data.matches_by_team.setdefault(team_id, []).append(match)
    for matches in data.matches_by_team.values():
        matches.sort(key=lambda m: (m.date is None, m.date or date.min))

    return data
