"""
Brazilian Soccer MCP Server - Data Loader
===========================================
Loads and normalizes all provided CSV datasets for querying.

Datasets:
  1. Brasileirao_Matches.csv       - Serie A (2012-2022)
  2. Brazilian_Cup_Matches.csv     - Copa do Brasil
  3. Libertadores_Matches.csv      - Copa Libertadores
  4. BR-Football-Dataset.csv       - Extended match stats
  5. novo_campeonato_brasileiro.csv - Historical Brasileirao (2003-2019)
  6. fifa_data.csv                 - FIFA player database

Handles:
  - Team name normalization (state suffixes, abbreviations, accents)
  - Multiple date formats (ISO, Brazilian DD/MM/YYYY, datetime)
  - UTF-8 character encoding
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"


# ---------------------------------------------------------------------------
# Team name normalization
# ---------------------------------------------------------------------------
_COMMON_TEAM_FIXES: dict[str, str] = {
    "athletico paranaense": "athletico-pr",
    "athletico-pr": "athletico-pr",
    "atletico paranaense": "athletico-pr",
    "atlético paranaense": "athletico-pr",
    "atl. paranaense": "athletico-pr",
    "atl pr": "athletico-pr",
    "atletico mineiro": "atletico-mg",
    "atlético mineiro": "atletico-mg",
    "atletico-mg": "atletico-mg",
    "atlético-mg": "atletico-mg",
    "atl. mineiro": "atletico-mg",
    "atl mg": "atletico-mg",
    "america mg": "america-mg",
    "américa mg": "america-mg",
    "américa-mg": "america-mg",
    "america-mg": "america-mg",
    "sao paulo": "sao-paulo",
    "são paulo": "sao-paulo",
    "são paulo fc": "sao-paulo",
    "corinthians": "corinthians",
    "corinthians-sp": "corinthians",
    "palmeiras": "palmeiras",
    "palmeiras-sp": "palmeiras",
    "flamengo": "flamengo",
    "flamengo-rj": "flamengo",
    "fluminense": "fluminense",
    "fluminense-rj": "fluminense",
    "vasco": "vasco",
    "vasco da gama": "vasco",
    "vasco da gama-rj": "vasco",
    "vasco-rj": "vasco",
    "gremio": "gremio",
    "grêmio": "gremio",
    "gremio-rs": "gremio",
    "grêmio-rs": "gremio",
    "internacional": "internacional",
    "internacional-rs": "internacional",
    "santos": "santos",
    "santos-sp": "santos",
    "cruzeiro": "cruzeiro",
    "cruzeiro-mg": "cruzeiro",
    "botafogo": "botafogo",
    "botafogo-rj": "botafogo",
    "botafogo rj": "botafogo",
    "fortaleza": "fortaleza",
    "fortaleza-ce": "fortaleza",
    "fortaleza fc": "fortaleza",
    "fortaleza ec": "fortaleza",
    "bahia": "bahia",
    "bahia-ba": "bahia",
    "ec bahia": "bahia",
    "cuiaba": "cuiaba",
    "cuiabá": "cuiaba",
    "bragantino": "bragantino",
    "rb bragantino": "bragantino",
    "bragantino-sp": "bragantino",
    "athletico pr": "athletico-pr",
    "atletico goianiense": "atletico-go",
    "atlético goianiense": "atletico-go",
    "atletico-go": "atletico-go",
    "atl go": "atletico-go",
    "ceara": "ceara",
    "ceará": "ceara",
    "ceara sc": "ceara",
    "ceará sc": "ceara",
    "goias": "goias",
    "goiás": "goias",
    "sport": "sport",
    "sport recife": "sport",
    "sport-pe": "sport",
    "sport recife-pe": "sport",
    "nautico": "nautico",
    "náutico": "nautico",
    "nautico-pe": "nautico",
    "náutico-pe": "nautico",
    "coritiba": "coritiba",
    "coritiba-pr": "coritiba",
    "avai": "avai",
    "avaí": "avai",
    "avai-sc": "avai",
    "figueirense": "figueirense",
    "figueirense-sc": "figueirense",
    "ponte preta": "ponte-preta",
    "ponte preta-sp": "ponte-preta",
    "ponte-preta": "ponte-preta",
    "juventude": "juventude",
    "juventude-rs": "juventude",
    "vitoria": "vitoria",
    "vitória": "vitoria",
    "vitória-ba": "vitoria",
    "vitoria-ba": "vitoria",
    "vitoria ec": "vitoria",
    "criciuma": "criciuma",
    "criciúma": "criciuma",
    "criciuma-sc": "criciuma",
    "chapecoense": "chapecoense",
    "chapecoense-sc": "chapecoense",
    "parana": "parana",
    "paraná": "parana",
    "parana clube": "parana",
    "guarani": "guarani",
    "guarani-sp": "guarani",
    "ituano": "ituano",
    "ituano-sp": "ituano",
    "novorizontino": "novorizontino",
    "gremio novorizontino": "novorizontino",
    "mirassol": "mirassol",
    "mirassol-sp": "mirassol",
    "sao bernardo": "sao-bernardo",
    "são bernardo": "sao-bernardo",
    "sao caetano": "sao-caetano",
    "são caetano": "sao-caetano",
    "ponte preta": "ponte-preta",
    "sao bento": "sao-bento",
    "são bento": "sao-bento",
    "operario pr": "operario-pr",
    "operario-pr": "operario-pr",
    "operario ferroviario": "operario-pr",
    "londrina": "londrina",
    "londrina-pr": "londrina",
    "csa": "csa",
    "crb": "crb",
    "abc": "abc",
    "abc rn": "abc",
    "abc-rn": "abc",
    "sampaio correa": "sampaio-correa",
    "sampaio corrêa": "sampaio-correa",
    "sampaio-correa": "sampaio-correa",
    "vila nova": "vila-nova",
    "vila nova-go": "vila-nova",
    "vila-nova": "vila-nova",
    "confianca": "confianca",
    "confiança": "confianca",
    "confianca-se": "confianca",
    "remo": "remo",
    "remo-pa": "remo",
    "paysandu": "paysandu",
    "paysandu-pa": "paysandu",
    "america rn": "america-rn",
    "américa rn": "america-rn",
    "america-rn": "america-rn",
    "américa-rn": "america-rn",
    "ypiranga": "ypiranga",
    "ypiranga rs": "ypiranga",
    "tombense": "tombense",
    "tombense mg": "tombense",
    "volta redonda": "volta-redonda",
    "volta-redonda": "volta-redonda",
    "botafogo sp": "botafogo-sp",
    "botafogo-sp": "botafogo-sp",
    "ferroviario": "ferroviario",
    "ferroviário": "ferroviario",
    "ferroviario-ce": "ferroviario",
    "manaus": "manaus",
    "manaus-am": "manaus",
    "santa cruz": "santa-cruz",
    "santa cruz-pe": "santa-cruz",
    "santa-cruz": "santa-cruz",
    "joinville": "joinville",
    "joinville-sc": "joinville",
    "portuguesa": "portuguesa",
    "portuguesa-sp": "portuguesa",
    "portuguesa rj": "portuguesa-rj",
    "sao jose": "sao-jose",
    "são josé": "sao-jose",
    "santo andre": "santo-andre",
    "santo andré": "santo-andre",
}


def _strip_state_suffix(name: str) -> str:
    """Remove state suffix patterns like '-SP', '-RJ', ' - SP', ' (SP)'."""
    name = re.sub(r"\s*-\s*[A-Z]{2}$", "", name)
    name = re.sub(r"\s*\(\s*[A-Z]{2}\s*\)$", "", name)
    return name.strip()


import unicodedata as _ucd


def _strip_accents(s: str) -> str:
    """Strip accents while preserving base characters (NFD decomposition)."""
    return "".join(
        c for c in _ucd.normalize("NFD", s)
        if not _ucd.category(c).startswith("M")
    )


def normalize_team(name: str) -> str:
    """Normalize a team name to its canonical form."""
    if not isinstance(name, str):
        return ""
    name = name.strip().lower()
    # Remove state suffix
    name = _strip_state_suffix(name)
    # Try direct lookup in fixes
    if name in _COMMON_TEAM_FIXES:
        return _COMMON_TEAM_FIXES[name]
    # Try with accent-stripped version
    name_no_accents = _strip_accents(name)
    if name_no_accents in _COMMON_TEAM_FIXES:
        return _COMMON_TEAM_FIXES[name_no_accents]
    # If still no match, return a cleaned version
    # Remove common suffixes like "futebol clube", "esporte clube", etc.
    cleaned = re.sub(r"\s+(futebol\s+)?clube(\s+esporte)?$", "", name_no_accents)
    cleaned = re.sub(r"\s+esporte\s+clube$", "", cleaned)
    cleaned = cleaned.strip()
    # Replace spaces with hyphens for consistency
    cleaned = cleaned.replace(" ", "-")
    return cleaned


def _parse_date(val: str) -> Optional[datetime]:
    """Parse a date from multiple possible formats. Returns datetime or None."""
    if not isinstance(val, str):
        return None
    val = val.strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",   # 2012-05-19 18:30:00
        "%Y-%m-%d",             # 2023-09-24
        "%d/%m/%Y",             # 29/03/2003
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_csv(path: str, **kwargs) -> pd.DataFrame:
    """Load a CSV with UTF-8 encoding and common parsing options."""
    return pd.read_csv(
        path,
        encoding="utf-8",
        encoding_errors="replace",
        on_bad_lines="skip",
        low_memory=False,
        **kwargs
    )


def load_brasileirao() -> pd.DataFrame:
    """Load Brasileirao Serie A matches (2012-2022)."""
    path = DATA_DIR / "Brasileirao_Matches.csv"
    df = _load_csv(str(path))
    df.columns = [c.strip() for c in df.columns]
    df["competition"] = "Brasileirao"
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["date"] = df["datetime"].apply(_parse_date)
    df["season"] = pd.to_numeric(df["season"], errors="coerce").fillna(0).astype(int)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").fillna(0).astype(int)
    df["round"] = pd.to_numeric(df["round"], errors="coerce").fillna(0).astype(int)
    return df


def load_copa_brasil() -> pd.DataFrame:
    """Load Copa do Brasil matches."""
    path = DATA_DIR / "Brazilian_Cup_Matches.csv"
    df = _load_csv(str(path))
    df.columns = [c.strip() for c in df.columns]
    df["competition"] = "Copa do Brasil"
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["date"] = df["datetime"].apply(_parse_date)
    df["season"] = pd.to_numeric(df["season"], errors="coerce").fillna(0).astype(int)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").fillna(0).astype(int)
    return df


def load_libertadores() -> pd.DataFrame:
    """Load Copa Libertadores matches."""
    path = DATA_DIR / "Libertadores_Matches.csv"
    df = _load_csv(str(path))
    df.columns = [c.strip() for c in df.columns]
    df["competition"] = "Libertadores"
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["date"] = df["datetime"].apply(_parse_date)
    df["season"] = pd.to_numeric(df["season"], errors="coerce").fillna(0).astype(int)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce").fillna(0).astype(int)
    return df


def load_br_football() -> pd.DataFrame:
    """Load BR-Football-Dataset (extended match statistics)."""
    path = DATA_DIR / "BR-Football-Dataset.csv"
    df = _load_csv(str(path))
    df.columns = [c.strip() for c in df.columns]
    # Standardize tournament name
    df["competition"] = df["tournament"].replace({
        "Copa do Brasil": "Copa do Brasil",
        "Brasileirao": "Brasileirao",
        "Campeonato Brasileiro": "Brasileirao",
        "Serie A": "Brasileirao",
        "Serie B": "Brasileirao",
        "Serie C": "Brasileirao",
    })
    # Map to standard column names
    df["home_team"] = df["home"]
    df["away_team"] = df["away"]
    df["home_team_norm"] = df["home"].apply(normalize_team)
    df["away_team_norm"] = df["away"].apply(normalize_team)
    df["date"] = df["date"].apply(_parse_date)
    # Try to extract season from date
    df["season"] = df["date"].apply(lambda d: d.year if d is not None else 0)
    # Goals as numeric
    for col in ["home_goal", "away_goal"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def load_historico() -> pd.DataFrame:
    """Load historical Brasileirao (2003-2019)."""
    path = DATA_DIR / "novo_campeonato_brasileiro.csv"
    df = _load_csv(str(path))
    df.columns = [c.strip() for c in df.columns]
    df["competition"] = "Brasileirao"
    # Rename columns to match standard format
    df["home_team"] = df["Equipe_mandante"]
    df["away_team"] = df["Equipe_visitante"]
    df["home_goal"] = pd.to_numeric(df["Gols_mandante"], errors="coerce").fillna(0).astype(int)
    df["away_goal"] = pd.to_numeric(df["Gols_visitante"], errors="coerce").fillna(0).astype(int)
    df["season"] = pd.to_numeric(df["Ano"], errors="coerce").fillna(0).astype(int)
    df["date"] = df["Data"].apply(_parse_date)
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["round"] = pd.to_numeric(df["Rodada"], errors="coerce").fillna(0).astype(int)
    df["arena"] = df.get("Arena", "")
    return df


def load_fifa() -> pd.DataFrame:
    """Load FIFA player database."""
    path = DATA_DIR / "fifa_data.csv"
    df = _load_csv(str(path))
    df.columns = [c.strip() for c in df.columns]
    df["Name"] = df["Name"].fillna("")
    df["Nationality"] = df["Nationality"].fillna("")
    df["Club"] = df["Club"].fillna("")
    df["Position"] = df["Position"].fillna("")
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce").fillna(0).astype(int)
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce").fillna(0).astype(int)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(0).astype(int)
    df["club_norm"] = df["Club"].apply(normalize_team)
    return df


# ---------------------------------------------------------------------------
# Unified match data
# ---------------------------------------------------------------------------

MATCH_COLUMNS = [
    "date", "season", "competition",
    "home_team", "away_team",
    "home_team_norm", "away_team_norm",
    "home_goal", "away_goal",
    "round", "stage", "arena",
]


def load_all_matches() -> pd.DataFrame:
    """Load and merge all match datasets into one unified DataFrame."""
    datasets = []

    # 1. Brasileirao
    br = load_brasileirao()
    br["stage"] = ""
    br["arena"] = ""
    datasets.append(br[MATCH_COLUMNS])

    # 2. Copa do Brasil
    cb = load_copa_brasil()
    cb["stage"] = cb.get("round", "")
    cb["arena"] = ""
    datasets.append(cb[MATCH_COLUMNS])

    # 3. Libertadores
    lb = load_libertadores()
    lb["round"] = ""
    lb["arena"] = ""
    datasets.append(lb[MATCH_COLUMNS])

    # 4. BR-Football extended
    bf = load_br_football()
    bf["round"] = ""
    bf["stage"] = ""
    bf["arena"] = ""
    datasets.append(bf[MATCH_COLUMNS])

    # 5. Historical Brasileirao
    hb = load_historico()
    hb["stage"] = ""
    datasets.append(hb[MATCH_COLUMNS])

    all_matches = pd.concat(datasets, ignore_index=True)
    # Remove rows without valid dates
    all_matches = all_matches[all_matches["date"].notna()].copy()
    # Ensure numeric goals
    for col in ["home_goal", "away_goal"]:
        all_matches[col] = pd.to_numeric(all_matches[col], errors="coerce").fillna(0).astype(int)
    all_matches["season"] = all_matches["season"].astype(int)
    return all_matches


# Cache for lazy loading
_matches_cache: pd.DataFrame | None = None
_players_cache: pd.DataFrame | None = None


def get_matches() -> pd.DataFrame:
    """Get the unified match DataFrame (lazy loaded)."""
    global _matches_cache
    if _matches_cache is None:
        _matches_cache = load_all_matches()
    return _matches_cache


def get_players() -> pd.DataFrame:
    """Get the FIFA player DataFrame (lazy loaded)."""
    global _players_cache
    if _players_cache is None:
        _players_cache = load_fifa()
    return _players_cache
