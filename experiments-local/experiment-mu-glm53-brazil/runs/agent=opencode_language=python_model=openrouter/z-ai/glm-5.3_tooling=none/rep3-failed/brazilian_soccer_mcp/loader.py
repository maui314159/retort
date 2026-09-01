"""Loading and parsing of the six Kaggle CSV datasets."""

from __future__ import annotations

import csv
import os
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from brazilian_soccer_mcp.models import Match, Player
from brazilian_soccer_mcp.normalize import TeamNameRegistry, strip_accents

BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

SOURCE_BRASILEIRAO = "Brasileirao_Matches.csv"
SOURCE_CUP = "Brazilian_Cup_Matches.csv"
SOURCE_LIBERTADORES = "Libertadores_Matches.csv"
SOURCE_BR_FOOTBALL = "BR-Football-Dataset.csv"
SOURCE_NOVO = "novo_campeonato_brasileiro.csv"
SOURCE_FIFA = "fifa_data.csv"

SOURCE_PRIORITY = [
    SOURCE_BRASILEIRAO,
    SOURCE_CUP,
    SOURCE_NOVO,
    SOURCE_LIBERTADORES,
    SOURCE_BR_FOOTBALL,
]

PRIMARY_SOURCE_TOLERANCE = 0.9

_EMPTY_VALUES = {"", "na", "-", "nan", "none"}

_SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
]


def parse_date(value: str) -> Optional[date]:
    """Parse the date formats used across the datasets."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _EMPTY_VALUES:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_goal(value) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in _EMPTY_VALUES:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_int(value) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in _EMPTY_VALUES:
        return None
    if "+" in text:
        text = text.split("+")[0]
    try:
        return int(float(text))
    except ValueError:
        return None


def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_brasileirao(path: Path) -> list[Match]:
    rows = _read_csv(path)
    matches = []
    for row in rows:
        dt = row.get("datetime", "")
        matches.append(
            Match(
                date=parse_date(dt),
                time=dt.split(" ")[1] if " " in dt else None,
                home_display=row["home_team"],
                away_display=row["away_team"],
                home_key=row["home_team"],
                away_key=row["away_team"],
                home_goals=parse_goal(row.get("home_goal")),
                away_goals=parse_goal(row.get("away_goal")),
                competition=BRASILEIRAO_A,
                season=parse_int(row.get("season")),
                round=str(row.get("round", "") or "") or None,
                stage=None,
                venue=None,
                source=SOURCE_BRASILEIRAO,
            )
        )
    return matches


def _load_cup(path: Path) -> list[Match]:
    rows = _read_csv(path)
    matches = []
    for row in rows:
        dt = row.get("datetime", "")
        matches.append(
            Match(
                date=parse_date(dt),
                time=dt.split(" ")[1] if " " in dt else None,
                home_display=row["home_team"],
                away_display=row["away_team"],
                home_key=row["home_team"],
                away_key=row["away_team"],
                home_goals=parse_goal(row.get("home_goal")),
                away_goals=parse_goal(row.get("away_goal")),
                competition=COPA_DO_BRASIL,
                season=parse_int(row.get("season")),
                round=str(row.get("round", "") or "") or None,
                stage=None,
                venue=None,
                source=SOURCE_CUP,
            )
        )
    return matches


def _load_libertadores(path: Path) -> list[Match]:
    rows = _read_csv(path)
    matches = []
    for row in rows:
        dt = row.get("datetime", "")
        matches.append(
            Match(
                date=parse_date(dt),
                time=dt.split(" ")[1] if " " in dt else None,
                home_display=row["home_team"],
                away_display=row["away_team"],
                home_key=row["home_team"],
                away_key=row["away_team"],
                home_goals=parse_goal(row.get("home_goal")),
                away_goals=parse_goal(row.get("away_goal")),
                competition=LIBERTADORES,
                season=parse_int(row.get("season")),
                round=None,
                stage=(row.get("stage") or None),
                venue=None,
                source=SOURCE_LIBERTADORES,
            )
        )
    return matches


def _load_br_football(path: Path) -> list[Match]:
    rows = _read_csv(path)
    tournament_map = {
        "Serie A": BRASILEIRAO_A,
        "Serie B": BRASILEIRAO_B,
        "Serie C": BRASILEIRAO_C,
        "Copa do Brasil": COPA_DO_BRASIL,
    }
    matches = []
    for row in rows:
        competition = tournament_map.get(row.get("tournament", ""))
        if competition is None:
            continue
        matches.append(
            Match(
                date=parse_date(row.get("date")),
                time=(row.get("time") or None),
                home_display=row["home"],
                away_display=row["away"],
                home_key=row["home"],
                away_key=row["away"],
                home_goals=parse_goal(row.get("home_goal")),
                away_goals=parse_goal(row.get("away_goal")),
                competition=competition,
                season=parse_int((row.get("date") or "")[:4]),
                round=None,
                stage=None,
                venue=None,
                source=SOURCE_BR_FOOTBALL,
                home_corners=parse_int(row.get("home_corner")),
                away_corners=parse_int(row.get("away_corner")),
                home_shots=parse_int(row.get("home_shots")),
                away_shots=parse_int(row.get("away_shots")),
                home_attacks=parse_int(row.get("home_attack")),
                away_attacks=parse_int(row.get("away_attack")),
            )
        )
    return matches


def _load_novo(path: Path) -> list[Match]:
    rows = _read_csv(path)
    matches = []
    for row in rows:
        matches.append(
            Match(
                date=parse_date(row.get("Data")),
                time=None,
                home_display=row["Equipe_mandante"],
                away_display=row["Equipe_visitante"],
                home_key=row["Equipe_mandante"],
                away_key=row["Equipe_visitante"],
                home_goals=parse_goal(row.get("Gols_mandante")),
                away_goals=parse_goal(row.get("Gols_visitante")),
                competition=BRASILEIRAO_A,
                season=parse_int(row.get("Ano")),
                round=str(row.get("Rodada", "") or "") or None,
                stage=None,
                venue=(row.get("Arena") or None),
                source=SOURCE_NOVO,
                match_id=(row.get("ID") or None),
            )
        )
    return matches


def _load_fifa(path: Path, registry: TeamNameRegistry) -> list[Player]:
    rows = _read_csv(path)
    players = []
    for row in rows:
        club_display = (row.get("Club") or "").strip() or None
        club_key = None
        if club_display:
            club_key = registry.canonical_key(club_display, context="players")
        skills = {}
        for column in _SKILL_COLUMNS:
            value = parse_int(row.get(column))
            if value is not None:
                skills[column] = value
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        players.append(
            Player(
                player_id=parse_int(row.get("ID")) or 0,
                name=name,
                name_norm=strip_accents(name).lower(),
                age=parse_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=parse_int(row.get("Overall")) or 0,
                potential=parse_int(row.get("Potential")) or 0,
                club_display=club_display,
                club_key=club_key,
                position=(row.get("Position") or "").strip() or None,
                jersey_number=(row.get("Jersey Number") or "").strip() or None,
                preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                value=(row.get("Value") or "").strip() or None,
                wage=(row.get("Wage") or "").strip() or None,
                height=(row.get("Height") or "").strip() or None,
                weight=(row.get("Weight") or "").strip() or None,
                international_reputation=parse_int(row.get("International Reputation")),
                skills=skills,
            )
        )
    return players


class LoadedData:
    """Everything parsed from the six CSV files, ready for querying."""

    def __init__(
        self,
        matches: list[Match],
        players: list[Player],
        registry: TeamNameRegistry,
        primary_sources: dict[tuple[str, Optional[int]], str],
        data_dir: Path,
    ):
        self.matches = matches
        self.players = players
        self.registry = registry
        self.primary_sources = primary_sources
        self.data_dir = data_dir


LEAGUE_COMPETITIONS = frozenset({BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C})


def _compute_primary_sources(matches: list[Match]) -> dict[tuple[str, Optional[int]], str]:
    """Pick the authoritative source per (competition, season).

    Several files overlap (e.g. two files both contain the 2012-2019
    Brasileirão), so without a rule the same fixture would appear twice in
    standings and searches.  For league competitions a source is only
    considered structurally valid when no pair of teams meets more than
    twice in the season; this rejects sources where Copa do Brasil fixtures
    were mislabelled as league matches.  Among valid sources the one with
    the most played matches wins (priority breaks ties).  For cups the
    highest-priority source covering at least 90% of the best coverage wins.
    """
    counts: dict[tuple[str, Optional[int]], Counter] = defaultdict(Counter)
    pair_counts: dict[tuple[str, Optional[int]], dict[str, Counter]] = defaultdict(dict)
    for match in matches:
        if not match.played:
            continue
        key = (match.competition, match.season)
        counts[key][match.source] += 1
        if match.competition in LEAGUE_COMPETITIONS:
            source_pairs = pair_counts[key].setdefault(match.source, Counter())
            source_pairs[frozenset((match.home_key, match.away_key))] += 1
    primary = {}
    for key, source_counts in counts.items():
        competition = key[0]
        if competition in LEAGUE_COMPETITIONS:
            valid = [
                source
                for source, pairs in pair_counts[key].items()
                if all(count <= 2 for count in pairs.values())
            ]
            pool = valid or list(source_counts)
            priority_rank = {s: -i for i, s in enumerate(SOURCE_PRIORITY)}
            primary[key] = max(
                pool, key=lambda s: (source_counts[s], priority_rank.get(s, -99))
            )
        else:
            best = max(source_counts.values())
            for source in SOURCE_PRIORITY:
                if source_counts.get(source, 0) >= best * PRIMARY_SOURCE_TOLERANCE:
                    primary[key] = source
                    break
            else:
                primary[key] = source_counts.most_common(1)[0][0]
    return primary


def load_data(data_dir: str | os.PathLike) -> LoadedData:
    """Load all six datasets and build the team-name registry."""
    root = Path(data_dir)
    registry = TeamNameRegistry()

    raw_matches: list[Match] = []
    raw_matches += _load_brasileirao(root / SOURCE_BRASILEIRAO)
    raw_matches += _load_cup(root / SOURCE_CUP)
    raw_matches += _load_libertadores(root / SOURCE_LIBERTADORES)
    raw_matches += _load_br_football(root / SOURCE_BR_FOOTBALL)
    raw_matches += _load_novo(root / SOURCE_NOVO)

    for match in raw_matches:
        registry.observe(match.home_display)
        registry.observe(match.away_display)
    registry.finalize()

    matches = []
    for match in raw_matches:
        home_key = registry.canonical_key(match.home_display, context="matches")
        away_key = registry.canonical_key(match.away_display, context="matches")
        matches.append(
            Match(
                date=match.date,
                time=match.time,
                home_display=match.home_display,
                away_display=match.away_display,
                home_key=home_key,
                away_key=away_key,
                home_goals=match.home_goals,
                away_goals=match.away_goals,
                competition=match.competition,
                season=match.season,
                round=match.round,
                stage=match.stage,
                venue=match.venue,
                source=match.source,
                match_id=match.match_id,
                home_corners=match.home_corners,
                away_corners=match.away_corners,
                home_shots=match.home_shots,
                away_shots=match.away_shots,
                home_attacks=match.home_attacks,
                away_attacks=match.away_attacks,
            )
        )
        registry.register_display(home_key, match.home_display)
        registry.register_display(away_key, match.away_display)

    players = _load_fifa(root / SOURCE_FIFA, registry)
    primary_sources = _compute_primary_sources(matches)
    return LoadedData(matches, players, registry, primary_sources, root)
