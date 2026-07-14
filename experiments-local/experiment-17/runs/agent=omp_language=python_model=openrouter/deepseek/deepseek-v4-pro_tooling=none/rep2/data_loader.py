"""
Brazilian Soccer MCP Server - Data Loader

Loads and normalizes all 6 CSV datasets for use by the MCP server tools.
Handles:
  - Multiple date formats (ISO, DD/MM/YYYY, datetime strings)
  - Team name normalization across datasets
  - UTF-8 character encoding (accents, cedilla)
  - Missing / mixed-type columns

Dataset sources (all CC-licensed, non-commercial demo use):
  Brasileirao_Matches.csv      — CC BY 4.0
  Brazilian_Cup_Matches.csv    — CC BY 4.0
  Libertadores_Matches.csv     — CC BY 4.0
  BR-Football-Dataset.csv      — CC0 Public Domain
  novo_campeonato_brasileiro.csv — CC BY 4.0
  fifa_data.csv                — Apache 2.0
"""

from __future__ import annotations

import re
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# ---------------------------------------------------------------------------
# Team name normalization
# ---------------------------------------------------------------------------

_STATE_SUFFIX_RE = re.compile(
    r"\s*-\s*(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\s*$",
    re.IGNORECASE,
)

TEAM_NAME_MAP: Dict[str, str] = {
    "athletico paranaense": "Athletico-PR",
    "athletico-pr": "Athletico-PR",
    "atletico paranaense": "Athletico-PR",
    "atletico-pr": "Athletico-PR",
    "athletico": "Athletico-PR",
    "atletico mineiro": "Atlético-MG",
    "atletico-mg": "Atlético-MG",
    "atlético-mg": "Atlético-MG",
    "atletico goianiense": "Atlético-GO",
    "atletico-go": "Atlético-GO",
    "america mg": "América-MG",
    "america-mg": "América-MG",
    "américa-mg": "América-MG",
    "america rn": "América-RN",
    "america-rn": "América-RN",
    "américa-rn": "América-RN",
    "sao paulo": "São Paulo",
    "são paulo": "São Paulo",
    "gremio": "Grêmio",
    "botafogo rj": "Botafogo",
    "botafogo-rj": "Botafogo",
    "avai": "Avaí",
    "avai-sc": "Avaí",
    "ceara": "Ceará",
    "ceara-ce": "Ceará",
    "ec bahia": "Bahia",
    "bahia-ba": "Bahia",
    "chapecoense-sc": "Chapecoense",
    "chapecoense": "Chapecoense",
    "sport recife": "Sport",
    "sport-pe": "Sport",
    "vitoria": "Vitória",
    "vitoria-ba": "Vitória",
    "fortaleza-ce": "Fortaleza",
    "goias": "Goiás",
    "goias-go": "Goiás",
    "nautico": "Náutico",
    "nautico-pe": "Náutico",
    "parana": "Paraná",
    "parana-pr": "Paraná",
    "paraná": "Paraná",
    "figueirense-sc": "Figueirense",
    "ponte preta-sp": "Ponte Preta",
    "joinville-sc": "Joinville",
    "santa cruz-pe": "Santa Cruz",
    "portuguesa-sp": "Portuguesa",
    "guarani-sp": "Guarani",
    "bragantino-sp": "Bragantino",
    "rb bragantino": "Bragantino",
    "red bull bragantino": "Bragantino",
    "vasco da gama": "Vasco",
    "vasco-rj": "Vasco",
    "corinthians-sp": "Corinthians",
    "cruzeiro-mg": "Cruzeiro",
    "fluminense-rj": "Fluminense",
    "flamengo-rj": "Flamengo",
    "internacional-rs": "Internacional",
    "gremio-rs": "Grêmio",
    "santos-sp": "Santos",
    "palmeiras-sp": "Palmeiras",
    "juventude-rs": "Juventude",
    "coritiba-pr": "Coritiba",
    "cuiaba": "Cuiabá",
    "cuiaba-mt": "Cuiabá",
}


def normalize_team_name(name: Any) -> str:
    """Normalize a team name to canonical form for cross-dataset matching."""
    if not isinstance(name, str):
        return ""
    name = name.strip()
    if not name:
        return ""
    # Check direct map first (preserves names with hyphens like Atlético-MG)
    lower = name.lower()
    if lower in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[lower]
    # Strip state suffix and try again
    stripped = _STATE_SUFFIX_RE.sub("", name).strip()
    if stripped.lower() != lower:
        lower2 = stripped.lower()
        if lower2 in TEAM_NAME_MAP:
            return TEAM_NAME_MAP[lower2]
    # Fallback: title-case
    return stripped.title()


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y",
    "%Y-%m-%d %H:%M",
]

def parse_date(value: Any) -> Optional[datetime]:
    """Parse a date string in any of the known formats. Always returns datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    s = str(value).strip()
    if not s or s.lower() == "na" or s == "-":
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(s).to_pydatetime()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------

def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def _load_brasileirao() -> List[Dict[str, Any]]:
    """Load Brasileirao_Matches.csv."""
    df = pd.read_csv(
        DATA_DIR / "Brasileirao_Matches.csv",
        dtype={"home_goal": float, "away_goal": float, "season": float, "round": float},
    )
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        dt = parse_date(row.get("datetime"))
        records.append({
            "competition": "Brasileirão",
            "date": dt,
            "season": _safe_int(row.get("season")),
            "round": _safe_int(row.get("round")),
            "home_team": normalize_team_name(row.get("home_team")),
            "away_team": normalize_team_name(row.get("away_team")),
            "home_goal": _safe_int(row.get("home_goal")),
            "away_goal": _safe_int(row.get("away_goal")),
            "home_team_state": str(row.get("home_team_state", "")).strip(),
            "away_team_state": str(row.get("away_team_state", "")).strip(),
            "stage": "",
        })
    return records


def _load_copa_brasil() -> List[Dict[str, Any]]:
    """Load Brazilian_Cup_Matches.csv."""
    df = pd.read_csv(
        DATA_DIR / "Brazilian_Cup_Matches.csv",
        dtype={"home_goal": float, "away_goal": float, "season": float},
    )
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        dt = parse_date(row.get("datetime"))
        records.append({
            "competition": "Copa do Brasil",
            "date": dt,
            "season": _safe_int(row.get("season")),
            "round": 0,
            "home_team": normalize_team_name(row.get("home_team")),
            "away_team": normalize_team_name(row.get("away_team")),
            "home_goal": _safe_int(row.get("home_goal")),
            "away_goal": _safe_int(row.get("away_goal")),
            "home_team_state": "",
            "away_team_state": "",
            "stage": str(row.get("round", "")).strip(),
        })
    return records


def _load_libertadores() -> List[Dict[str, Any]]:
    """Load Libertadores_Matches.csv (has "-" placeholders and NA rows)."""
    df = pd.read_csv(
        DATA_DIR / "Libertadores_Matches.csv",
        dtype=str,
        keep_default_na=False,
        na_values=[],
    )
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        dt = parse_date(row.get("datetime"))
        season_val = str(row.get("season", "")).strip()
        season = _safe_int(season_val) if season_val.lower() != "na" else 0
        records.append({
            "competition": "Libertadores",
            "date": dt,
            "season": season,
            "round": 0,
            "home_team": normalize_team_name(row.get("home_team")),
            "away_team": normalize_team_name(row.get("away_team")),
            "home_goal": _safe_int(row.get("home_goal")),
            "away_goal": _safe_int(row.get("away_goal")),
            "home_team_state": "",
            "away_team_state": "",
            "stage": str(row.get("stage", "")).strip(),
        })
    return records


def _load_br_football() -> List[Dict[str, Any]]:
    """Load BR-Football-Dataset.csv."""
    df = pd.read_csv(
        DATA_DIR / "BR-Football-Dataset.csv",
        dtype={
            "home_goal": float, "away_goal": float,
            "home_corner": float, "away_corner": float,
            "home_attack": float, "away_attack": float,
            "home_shots": float, "away_shots": float,
        },
    )
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        dt = parse_date(row.get("date"))
        if dt is None:
            continue
        records.append({
            "competition": str(row.get("tournament", "")).strip(),
            "date": dt,
            "season": dt.year,
            "round": 0,
            "home_team": normalize_team_name(row.get("home")),
            "away_team": normalize_team_name(row.get("away")),
            "home_goal": _safe_int(row.get("home_goal")),
            "away_goal": _safe_int(row.get("away_goal")),
            "home_team_state": "",
            "away_team_state": "",
            "stage": "",
            "home_corner": _safe_float(row.get("home_corner")),
            "away_corner": _safe_float(row.get("away_corner")),
            "home_shots": _safe_float(row.get("home_shots")),
            "away_shots": _safe_float(row.get("away_shots")),
        })
    return records


def _load_novo_brasileirao() -> List[Dict[str, Any]]:
    """Load novo_campeonato_brasileiro.csv."""
    df = pd.read_csv(
        DATA_DIR / "novo_campeonato_brasileiro.csv",
        dtype={"Gols_mandante": float, "Gols_visitante": float, "Ano": float, "Rodada": float},
    )
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        dt = parse_date(row.get("Data"))
        records.append({
            "competition": "Brasileirão",
            "date": dt,
            "season": _safe_int(row.get("Ano")),
            "round": _safe_int(row.get("Rodada")),
            "home_team": normalize_team_name(row.get("Equipe_mandante")),
            "away_team": normalize_team_name(row.get("Equipe_visitante")),
            "home_goal": _safe_int(row.get("Gols_mandante")),
            "away_goal": _safe_int(row.get("Gols_visitante")),
            "home_team_state": str(row.get("Mandante_UF", "")).strip(),
            "away_team_state": str(row.get("Visitante_UF", "")).strip(),
            "stage": "",
            "winner": str(row.get("Vencedor", "")).strip(),
            "arena": str(row.get("Arena", "")).strip(),
        })
    return records


def _load_fifa_players() -> List[Dict[str, Any]]:
    """Load fifa_data.csv."""
    df = pd.read_csv(DATA_DIR / "fifa_data.csv")
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        records.append({
            "id": _safe_int(row.get("ID")),
            "name": str(row.get("Name", "")).strip(),
            "age": _safe_int(row.get("Age")),
            "nationality": str(row.get("Nationality", "")).strip(),
            "overall": _safe_int(row.get("Overall")),
            "potential": _safe_int(row.get("Potential")),
            "club": str(row.get("Club", "")).strip(),
            "position": str(row.get("Position", "")).strip(),
            "jersey_number": _safe_int(row.get("Jersey Number")),
            "height": str(row.get("Height", "")).strip(),
            "weight": str(row.get("Weight", "")).strip(),
            "preferred_foot": str(row.get("Preferred Foot", "")).strip(),
            "weak_foot": _safe_int(row.get("Weak Foot")),
            "skill_moves": _safe_int(row.get("Skill Moves")),
            "value": str(row.get("Value", "")).strip(),
            "wage": str(row.get("Wage", "")).strip(),
            "crossing": _safe_int(row.get("Crossing")),
            "finishing": _safe_int(row.get("Finishing")),
            "dribbling": _safe_int(row.get("Dribbling")),
            "short_passing": _safe_int(row.get("ShortPassing")),
            "long_passing": _safe_int(row.get("LongPassing")),
            "ball_control": _safe_int(row.get("BallControl")),
            "shot_power": _safe_int(row.get("ShotPower")),
            "stamina": _safe_int(row.get("Stamina")),
            "strength": _safe_int(row.get("Strength")),
            "aggression": _safe_int(row.get("Aggression")),
            "interceptions": _safe_int(row.get("Interceptions")),
            "positioning": _safe_int(row.get("Positioning")),
            "vision": _safe_int(row.get("Vision")),
            "penalties": _safe_int(row.get("Penalties")),
            "composure": _safe_int(row.get("Composure")),
        })
    return records


# ---------------------------------------------------------------------------
# Unified loader
# ---------------------------------------------------------------------------

_cache: Optional[Dict[str, Any]] = None


def load_all() -> Dict[str, Any]:
    """Load all datasets and return a dict with match records and player records."""
    global _cache
    if _cache is not None:
        return _cache

    all_matches: List[Dict[str, Any]] = []
    all_matches.extend(_load_brasileirao())
    all_matches.extend(_load_copa_brasil())
    all_matches.extend(_load_libertadores())
    all_matches.extend(_load_br_football())
    all_matches.extend(_load_novo_brasileirao())

    players = _load_fifa_players()

    teams: set[str] = set()
    for m in all_matches:
        if m["home_team"]:
            teams.add(m["home_team"])
        if m["away_team"]:
            teams.add(m["away_team"])

    _cache = {"matches": all_matches, "players": players, "teams": teams}
    return _cache


def clear_cache() -> None:
    """Clear the data cache (useful for testing)."""
    global _cache
    _cache = None
