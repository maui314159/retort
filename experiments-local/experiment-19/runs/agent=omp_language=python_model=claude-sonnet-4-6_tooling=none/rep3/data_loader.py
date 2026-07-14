"""
Load and normalize all Brazilian soccer CSV datasets into a unified format.
"""

from __future__ import annotations

import os
import re
import pandas as pd
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# ---------------------------------------------------------------------------
# Team name normalisation
# ---------------------------------------------------------------------------

# Strip "-XX" state suffix, e.g. "Palmeiras-SP" → "Palmeiras"
_STATE_SUFFIX = re.compile(r"-[A-Z]{2}$")

# Known long-name → short-name mappings that appear in various datasets
_TEAM_ALIASES: dict[str, str] = {
    "sport club corinthians paulista": "Corinthians",
    "boavista sport club (antigo esporte clube barreira)": "Boavista",
    "atletico": "Atlético Mineiro",  # ambiguous but common in older data
    "atletico-mg": "Atlético Mineiro",
    "atletico mineiro": "Atlético Mineiro",
    "atletico-pr": "Athletico Paranaense",
    "athletico-pr": "Athletico Paranaense",
    "athletico paranaense": "Athletico Paranaense",
    "atlético paranaense": "Athletico Paranaense",
    "sao paulo": "São Paulo",
    "gremio": "Grêmio",
    "america": "América Mineiro",
    "america-mg": "América Mineiro",
    "america mg": "América Mineiro",
    "america mineiro": "América Mineiro",
    "vasco": "Vasco da Gama",
    "vasco da gama": "Vasco da Gama",
    "sport": "Sport Recife",
    "sport-pe": "Sport Recife",
    "sport recife": "Sport Recife",
    "nautico": "Náutico",
    "nautico-pe": "Náutico",
    "ponte preta": "Ponte Preta",
    "ponte preta-sp": "Ponte Preta",
    "figueirense": "Figueirense",
    "figueirense-sc": "Figueirense",
}


def normalize_team(name: str) -> str:
    """Return a canonical team name, stripping state suffix and resolving aliases."""
    if not isinstance(name, str):
        return str(name)
    name = name.strip()
    # strip trailing " - XX" (with spaces around dash)
    name = re.sub(r"\s+-\s+[A-Z]{2}$", "", name)
    # strip "-XX" state suffix
    name = _STATE_SUFFIX.sub("", name)
    # look up lower-cased alias
    lower = name.lower()
    if lower in _TEAM_ALIASES:
        return _TEAM_ALIASES[lower]
    return name


def _parse_date(val: object) -> Optional[str]:
    """Return ISO date string (YYYY-MM-DD) or None on failure."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    # Brazilian format DD/MM/YYYY — check this first to avoid dayfirst ambiguity warning
    if re.match(r"\d{2}/\d{2}/\d{4}", s):
        try:
            return pd.to_datetime(s, format="%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            pass
    # ISO format or ISO with time (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return None


def _to_int(val: object) -> Optional[int]:
    try:
        return int(float(str(val)))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Individual loaders
# ---------------------------------------------------------------------------

def _load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv", encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": _parse_date(r.get("datetime")),
            "home_team": normalize_team(str(r["home_team"])),
            "away_team": normalize_team(str(r["away_team"])),
            "home_goals": _to_int(r.get("home_goal")),
            "away_goals": _to_int(r.get("away_goal")),
            "competition": "Brasileirão Série A",
            "season": _to_int(r.get("season")),
            "round": str(r["round"]) if not pd.isna(r.get("round")) else None,
            "stage": None,
        })
    return pd.DataFrame(rows)


def _load_copa_brasil() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv", encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": _parse_date(r.get("datetime")),
            "home_team": normalize_team(str(r["home_team"])),
            "away_team": normalize_team(str(r["away_team"])),
            "home_goals": _to_int(r.get("home_goal")),
            "away_goals": _to_int(r.get("away_goal")),
            "competition": "Copa do Brasil",
            "season": _to_int(r.get("season")),
            "round": str(r["round"]) if not pd.isna(r.get("round")) else None,
            "stage": None,
        })
    return pd.DataFrame(rows)


def _load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv", encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": _parse_date(r.get("datetime")),
            "home_team": normalize_team(str(r["home_team"])),
            "away_team": normalize_team(str(r["away_team"])),
            "home_goals": _to_int(r.get("home_goal")),
            "away_goals": _to_int(r.get("away_goal")),
            "competition": "Copa Libertadores",
            "season": _to_int(r.get("season")),
            "round": None,
            "stage": str(r["stage"]) if not pd.isna(r.get("stage")) else None,
        })
    return pd.DataFrame(rows)


def _load_br_football() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv", encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        date_val = _parse_date(r.get("date"))
        season = None
        if date_val:
            try:
                season = int(date_val[:4])
            except Exception:
                pass
        rows.append({
            "date": date_val,
            "home_team": normalize_team(str(r["home"])),
            "away_team": normalize_team(str(r["away"])),
            "home_goals": _to_int(r.get("home_goal")),
            "away_goals": _to_int(r.get("away_goal")),
            "competition": str(r["tournament"]) if not pd.isna(r.get("tournament")) else "Unknown",
            "season": season,
            "round": None,
            "stage": None,
            # extended stats
            "home_corners": _to_int(r.get("home_corner")),
            "away_corners": _to_int(r.get("away_corner")),
            "home_shots": _to_int(r.get("home_shots")),
            "away_shots": _to_int(r.get("away_shots")),
            "home_attacks": _to_int(r.get("home_attack")),
            "away_attacks": _to_int(r.get("away_attack")),
        })
    return pd.DataFrame(rows)


def _load_historico() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8")
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": _parse_date(r.get("Data")),
            "home_team": normalize_team(str(r["Equipe_mandante"])),
            "away_team": normalize_team(str(r["Equipe_visitante"])),
            "home_goals": _to_int(r.get("Gols_mandante")),
            "away_goals": _to_int(r.get("Gols_visitante")),
            "competition": "Brasileirão Série A",
            "season": _to_int(r.get("Ano")),
            "round": str(r["Rodada"]) if not pd.isna(r.get("Rodada")) else None,
            "stage": None,
            "stadium": str(r["Arena"]) if not pd.isna(r.get("Arena")) else None,
        })
    return pd.DataFrame(rows)


def _load_fifa() -> pd.DataFrame:
    # BOM-prefixed CSV
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", encoding="utf-8-sig")
    # Drop unnamed first column if present
    unnamed = [c for c in df.columns if c.startswith("Unnamed")]
    if unnamed:
        df = df.drop(columns=unnamed)
    return df


# ---------------------------------------------------------------------------
# Public API: load everything once
# ---------------------------------------------------------------------------

class DataStore:
    """All datasets loaded into memory."""

    def __init__(self) -> None:
        self.brasileirao = _load_brasileirao()
        self.copa_brasil = _load_copa_brasil()
        self.libertadores = _load_libertadores()
        self.br_football = _load_br_football()
        self.historico = _load_historico()
        self.fifa = _load_fifa()

        # Combined match frame (all competitions).
        # Keep only the core columns so concat works cleanly.
        core = ["date", "home_team", "away_team", "home_goals", "away_goals",
                "competition", "season", "round", "stage"]
        frames = []
        for src in (self.brasileirao, self.copa_brasil, self.libertadores,
                    self.br_football, self.historico):
            sub = src.reindex(columns=core)
            frames.append(sub)
        self.all_matches = pd.concat(frames, ignore_index=True)
        # Drop rows with both goals missing
        self.all_matches = self.all_matches.dropna(subset=["home_goals", "away_goals"])
        self.all_matches["home_goals"] = self.all_matches["home_goals"].astype(int)
        self.all_matches["away_goals"] = self.all_matches["away_goals"].astype(int)


_store: DataStore | None = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore()
    return _store
