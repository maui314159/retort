"""
Data loader for Brazilian soccer datasets.
Loads all 6 CSV files, normalizes team names and dates into unified DataFrames.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from functools import lru_cache

import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"


# ---------------------------------------------------------------------------
# Team-name normalisation
# ---------------------------------------------------------------------------

# Remove state suffixes like "-SP", "-RJ", "- SP", " (CE)"
_STATE_SUFFIX_RE = re.compile(
    r"\s*[-–]\s*[A-Z]{2}\b"          # " - SP" or "-SP"
    r"|\s*\([A-Z]{2}\)\s*$"           # " (CE)"
    r"|\s*\([A-Z]{3}\)\s*$",          # " (URU)" – international teams
    re.IGNORECASE,
)

# Mapping from common partial/variant names → canonical
_ALIAS: dict[str, str] = {
    "atletico mineiro": "atletico-mg",
    "atlético mineiro": "atletico-mg",
    "atletico": "atletico-mg",
    "atletico mg": "atletico-mg",
    "atletico-mg": "atletico-mg",
    "atletico paranaense": "athletico-pr",
    "athletico paranaense": "athletico-pr",
    "athletico-pr": "athletico-pr",
    "athletico pr": "athletico-pr",
    "atletico pr": "athletico-pr",
    "atletico-pr": "athletico-pr",
    "sport recife": "sport",
    "sport club recife": "sport",
    "fluminense fc": "fluminense",
    "botafogo de futebol e regatas": "botafogo",
    "club atletico mineiro": "atletico-mg",
    "sao paulo fc": "sao paulo",
    "são paulo fc": "sao paulo",
    "são paulo": "sao paulo",
    "sport club corinthians paulista": "corinthians",
    "corinthians paulista": "corinthians",
    "se palmeiras": "palmeiras",
    "gremio fbpa": "gremio",
    "grêmio": "gremio",
    "cruzeiro ec": "cruzeiro",
    "internacional fc": "internacional",
    "internacional rs": "internacional",
    "ceara sc": "ceara",
    "ceará": "ceara",
    "fortaleza ec": "fortaleza",
    "avai fc": "avai",
    "avaí": "avai",
    "santos fc": "santos",
    "vasco da gama": "vasco",
    "cr vasco da gama": "vasco",
    "flamengo rj": "flamengo",
    "clube de regatas do flamengo": "flamengo",
    "barueri": "gremio barueri",
}


def _strip_accents(text: str) -> str:
    """Normalise unicode to NFC then fold to ASCII for fuzzy comparison."""
    return unicodedata.normalize("NFC", text)


def normalize_team(name: str) -> str:
    """Return a lowercased, suffix-stripped canonical name."""
    if not isinstance(name, str):
        return ""
    cleaned = _STATE_SUFFIX_RE.sub("", name).strip()
    lower = cleaned.lower()
    # strip common suffixes like " fc", " sc", " ec" for look-ups
    return _ALIAS.get(lower, lower)


def team_matches(name: str, query: str) -> bool:
    """Return True if *query* is found in the normalised team name."""
    nq = normalize_team(query)
    nn = normalize_team(name)
    return nq in nn or nn in nq


# ---------------------------------------------------------------------------
# Date normalisation
# ---------------------------------------------------------------------------

def _parse_date(val) -> pd.Timestamp | pd.NaT:
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, pd.Timestamp):
        return val
    s = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(s, infer_datetime_format=True)
    except Exception:
        return pd.NaT


# ---------------------------------------------------------------------------
# Individual loaders
# ---------------------------------------------------------------------------

def _load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv", encoding="utf-8")
    df.columns = df.columns.str.strip()
    df["date"] = df["datetime"].apply(_parse_date)
    df["home_norm"] = df["home_team"].apply(normalize_team)
    df["away_norm"] = df["away_team"].apply(normalize_team)
    df["competition"] = "Brasileirao"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["round"] = df["round"].astype(str)
    return df[["date", "home_team", "away_team", "home_norm", "away_norm",
               "home_goal", "away_goal", "season", "round", "competition"]]


def _load_copa_brasil() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv", encoding="utf-8")
    df.columns = df.columns.str.strip()
    df["date"] = df["datetime"].apply(_parse_date)
    df["home_norm"] = df["home_team"].apply(normalize_team)
    df["away_norm"] = df["away_team"].apply(normalize_team)
    df["competition"] = "Copa do Brasil"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["round"] = df["round"].astype(str)
    return df[["date", "home_team", "away_team", "home_norm", "away_norm",
               "home_goal", "away_goal", "season", "round", "competition"]]


def _load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv", encoding="utf-8")
    df.columns = df.columns.str.strip()
    df["date"] = df["datetime"].apply(_parse_date)
    df["home_norm"] = df["home_team"].apply(normalize_team)
    df["away_norm"] = df["away_team"].apply(normalize_team)
    df["competition"] = "Copa Libertadores"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["round"] = df.get("stage", pd.Series([""] * len(df))).astype(str)
    return df[["date", "home_team", "away_team", "home_norm", "away_norm",
               "home_goal", "away_goal", "season", "round", "competition"]]


def _load_br_football() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv", encoding="utf-8")
    df.columns = df.columns.str.strip()
    df["date"] = df["date"].apply(_parse_date)
    df = df.rename(columns={"home": "home_team", "away": "away_team",
                             "tournament": "competition"})
    df["home_norm"] = df["home_team"].apply(normalize_team)
    df["away_norm"] = df["away_team"].apply(normalize_team)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = df["date"].dt.year.astype("Int64")
    df["round"] = ""
    # keep extra stats columns if present
    extras = [c for c in ["home_corner", "away_corner", "home_attack",
                           "away_attack", "home_shots", "away_shots",
                           "total_corners"] if c in df.columns]
    return df[["date", "home_team", "away_team", "home_norm", "away_norm",
               "home_goal", "away_goal", "season", "round", "competition"] + extras]


def _load_novo_brasileiro() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8")
    df.columns = df.columns.str.strip()
    df["date"] = df["Data"].apply(_parse_date)
    df = df.rename(columns={
        "Equipe_mandante": "home_team",
        "Equipe_visitante": "away_team",
        "Gols_mandante": "home_goal",
        "Gols_visitante": "away_goal",
        "Ano": "season",
        "Rodada": "round",
    })
    df["home_norm"] = df["home_team"].apply(normalize_team)
    df["away_norm"] = df["away_team"].apply(normalize_team)
    df["competition"] = "Brasileirao"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["round"] = df["round"].astype(str)
    extra = [c for c in ["Arena", "Vencedor"] if c in df.columns]
    return df[["date", "home_team", "away_team", "home_norm", "away_norm",
               "home_goal", "away_goal", "season", "round", "competition"] + extra]


# ---------------------------------------------------------------------------
# Unified match dataframe
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_all_matches() -> pd.DataFrame:
    """Load and concatenate all match datasets."""
    frames = [
        _load_brasileirao(),
        _load_copa_brasil(),
        _load_libertadores(),
        _load_br_football(),
        _load_novo_brasileiro(),
    ]
    df = pd.concat(frames, ignore_index=True, sort=False)
    df = df.dropna(subset=["home_goal", "away_goal"])
    df["goal_diff"] = (df["home_goal"] - df["away_goal"]).abs()
    return df


@lru_cache(maxsize=1)
def load_players() -> pd.DataFrame:
    """Load FIFA player data."""
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    # Unnamed first col is an index
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce")
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce")
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["name_norm"] = df["Name"].str.lower().str.strip()
    df["club_norm"] = df["Club"].fillna("").str.lower().str.strip()
    df["nationality_norm"] = df["Nationality"].fillna("").str.lower().str.strip()
    return df
