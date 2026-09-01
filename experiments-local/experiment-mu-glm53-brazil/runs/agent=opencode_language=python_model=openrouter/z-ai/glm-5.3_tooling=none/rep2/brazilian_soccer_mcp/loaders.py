"""Loaders converting the six Kaggle CSV files into raw match/player rows.

Every loader returns plain dictionaries with normalized field names plus the
raw team display names (and state hints where available).  Canonical team
keys are assigned later by :mod:`brazilian_soccer_mcp.service`, once the
team registry has observed every mention across all files.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import parse_date, parse_int

DATA_FILES = {
    "brasileirao_matches": "Brasileirao_Matches.csv",
    "copa_do_brasil_matches": "Brazilian_Cup_Matches.csv",
    "libertadores_matches": "Libertadores_Matches.csv",
    "br_football_stats": "BR-Football-Dataset.csv",
    "campeonato_2003_2019": "novo_campeonato_brasileiro.csv",
    "fifa_data": "fifa_data.csv",
}

SOURCE_LABELS = {
    "brasileirao_matches": "Brasileirão Matches (Kaggle: jogos-do-campeonato-brasileiro)",
    "copa_do_brasil_matches": "Brazilian Cup Matches (Kaggle: jogos-do-campeonato-brasileiro)",
    "libertadores_matches": "Libertadores Matches (Kaggle: jogos-do-campeonato-brasileiro)",
    "br_football_stats": "BR Football Dataset (Kaggle: brazilian-football-matches)",
    "campeonato_2003_2019": "Campeonato Brasileiro 2003-2019 (Kaggle)",
    "fifa_data": "FIFA Players (Kaggle: fifa-players-data)",
}

BR_FOOTBALL_COMPETITIONS = {
    "Serie A": ("brasileirao-serie-a", "Brasileirão Série A"),
    "Serie B": ("brasileirao-serie-b", "Brasileirão Série B"),
    "Serie C": ("brasileirao-serie-c", "Brasileirão Série C"),
    "Copa do Brasil": ("copa-do-brasil", "Copa do Brasil"),
}


@dataclass
class RawMatch:
    """A match row before team keys have been assigned."""

    competition_key: str
    competition: str
    source: str
    date: object | None
    home_display: str
    away_display: str
    home_uf: str | None
    away_uf: str | None
    home_goals: int | None
    away_goals: int | None
    season: int | None
    round_label: str | None = None
    stage: str | None = None
    venue: str | None = None
    time: str | None = None
    stats: dict = field(default_factory=dict)


@dataclass
class RawPlayer:
    """A player row before its club has been resolved to a team key."""

    id: int
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    height: str
    weight: str
    preferred_foot: str
    value: str
    wage: str


def _read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_brasileirao_matches(path: Path) -> list[RawMatch]:
    """Load Brasileirão Serie A matches (2012-2022)."""
    rows = []
    for row in _read_rows(path):
        rows.append(RawMatch(
            competition_key="brasileirao-serie-a",
            competition="Brasileirão Série A",
            source="brasileirao_matches",
            date=parse_date(row["datetime"]),
            home_display=row["home_team"],
            away_display=row["away_team"],
            home_uf=row.get("home_team_state") or None,
            away_uf=row.get("away_team_state") or None,
            home_goals=parse_int(row["home_goal"]),
            away_goals=parse_int(row["away_goal"]),
            season=parse_int(row["season"]),
            round_label=(
                f"Round {int(row['round'])}" if parse_int(row["round"]) else None
            ),
            time=str(row["datetime"]).split(" ", 1)[1]
            if " " in str(row["datetime"]) else None,
        ))
    return rows


def load_copa_do_brasil_matches(path: Path) -> list[RawMatch]:
    """Load Copa do Brasil matches (2012-2021)."""
    rows = []
    for row in _read_rows(path):
        round_number = parse_int(row["round"])
        rows.append(RawMatch(
            competition_key="copa-do-brasil",
            competition="Copa do Brasil",
            source="copa_do_brasil_matches",
            date=parse_date(row["datetime"]),
            home_display=row["home_team"],
            away_display=row["away_team"],
            home_uf=None,
            away_uf=None,
            home_goals=parse_int(row["home_goal"]),
            away_goals=parse_int(row["away_goal"]),
            season=parse_int(row["season"]),
            round_label=f"Round {round_number}" if round_number else None,
        ))
    return rows


def load_libertadores_matches(path: Path) -> list[RawMatch]:
    """Load Copa Libertadores matches (2013-2022)."""
    rows = []
    for row in _read_rows(path):
        rows.append(RawMatch(
            competition_key="copa-libertadores",
            competition="Copa Libertadores",
            source="libertadores_matches",
            date=parse_date(row["datetime"]),
            home_display=row["home_team"],
            away_display=row["away_team"],
            home_uf=None,
            away_uf=None,
            home_goals=parse_int(row["home_goal"]),
            away_goals=parse_int(row["away_goal"]),
            season=parse_int(row["season"]),
            stage=(row.get("stage") or "").strip() or None,
        ))
    return rows


def load_br_football_matches(path: Path) -> list[RawMatch]:
    """Load the extended statistics dataset (Serie A/B/C and Copa do Brasil)."""
    rows = []
    for row in _read_rows(path):
        comp_key, comp_display = BR_FOOTBALL_COMPETITIONS.get(
            row["tournament"], (None, None)
        )
        if comp_key is None:
            continue
        match_date = parse_date(row["date"])
        stats = {
            "home_corners": parse_int(row.get("home_corner")),
            "away_corners": parse_int(row.get("away_corner")),
            "home_shots": parse_int(row.get("home_shots")),
            "away_shots": parse_int(row.get("away_shots")),
            "home_attacks": parse_int(row.get("home_attack")),
            "away_attacks": parse_int(row.get("away_attack")),
            "halftime_result": (row.get("ht_result") or "").strip() or None,
        }
        rows.append(RawMatch(
            competition_key=comp_key,
            competition=comp_display,
            source="br_football_stats",
            date=match_date,
            home_display=row["home"],
            away_display=row["away"],
            home_uf=None,
            away_uf=None,
            home_goals=parse_int(row["home_goal"]),
            away_goals=parse_int(row["away_goal"]),
            season=match_date.year if match_date else None,
            round_label=None,
            time=(row.get("time") or "").strip() or None,
            stats=stats,
        ))
    return rows


def load_historical_brasileirao(path: Path) -> list[RawMatch]:
    """Load the historical Brasileirão dataset (2003-2019)."""
    rows = []
    for row in _read_rows(path):
        rows.append(RawMatch(
            competition_key="brasileirao-serie-a",
            competition="Brasileirão Série A",
            source="campeonato_2003_2019",
            date=parse_date(row["Data"]),
            home_display=row["Equipe_mandante"],
            away_display=row["Equipe_visitante"],
            home_uf=(row.get("Mandante_UF") or "").strip() or None,
            away_uf=(row.get("Visitante_UF") or "").strip() or None,
            home_goals=parse_int(row["Gols_mandante"]),
            away_goals=parse_int(row["Gols_visitante"]),
            season=parse_int(row["Ano"]),
            round_label=(
                f"Round {int(row['Rodada'])}" if parse_int(row["Rodada"]) else None
            ),
            venue=(row.get("Arena") or "").strip() or None,
        ))
    return rows


def load_fifa_players(path: Path) -> list[RawPlayer]:
    """Load the FIFA player database."""
    players = []
    for row in _read_rows(path):
        players.append(RawPlayer(
            id=parse_int(row.get("ID")) or 0,
            name=(row.get("Name") or "").strip(),
            age=parse_int(row.get("Age")),
            nationality=(row.get("Nationality") or "").strip(),
            overall=parse_int(row.get("Overall")),
            potential=parse_int(row.get("Potential")),
            club=(row.get("Club") or "").strip(),
            position=(row.get("Position") or "").strip(),
            jersey_number=parse_int(row.get("Jersey Number")),
            height=(row.get("Height") or "").strip(),
            weight=(row.get("Weight") or "").strip(),
            preferred_foot=(row.get("Preferred Foot") or "").strip(),
            value=(row.get("Value") or "").strip(),
            wage=(row.get("Wage") or "").strip(),
        ))
    return players


def load_all(data_dir: str | Path) -> tuple[list[RawMatch], list[RawPlayer]]:
    """Load every dataset from *data_dir* into raw rows."""
    data_dir = Path(data_dir)
    matches: list[RawMatch] = []
    matches += load_brasileirao_matches(data_dir / DATA_FILES["brasileirao_matches"])
    matches += load_copa_do_brasil_matches(data_dir / DATA_FILES["copa_do_brasil_matches"])
    matches += load_libertadores_matches(data_dir / DATA_FILES["libertadores_matches"])
    matches += load_br_football_matches(data_dir / DATA_FILES["br_football_stats"])
    matches += load_historical_brasileirao(data_dir / DATA_FILES["campeonato_2003_2019"])
    players = load_fifa_players(data_dir / DATA_FILES["fifa_data"])
    return matches, players
