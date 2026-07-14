"""Data ingestion and normalization for Brazilian Soccer MCP Server."""

import re
from pathlib import Path
from typing import Optional
import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Common team name mappings to normalize variations
TEAM_NAME_MAPPINGS = {
    "sport club corinthians paulista": "corinthians",
    "corinthians": "corinthians",
    "sociedade esportiva palmeiras": "palmeiras",
    "palmeiras": "palmeiras",
    "clube de regatas do flamengo": "flamengo",
    "flamengo": "flamengo",
    "são paulo futebol clube": "são paulo",
    "sao paulo": "são paulo",
    "são paulo": "são paulo",
    "grêmio foot-ball porto alegrense": "grêmio",
    "gremio": "grêmio",
    "grêmio": "grêmio",
    "clube atlético mineiro": "atlético-mg",
    "atletico-mg": "atlético-mg",
    "atlético-mg": "atlético-mg",
    "cruzeiro esporte clube": "cruzeiro",
    "cruzeiro": "cruzeiro",
    "sport club do recife": "sport",
    "sport": "sport",
    "clube náutico capibaribe": "náutico",
    "nautico": "náutico",
    "náutico": "náutico",
    "botafogo de futebol e regatas": "botafogo",
    "botafogo": "botafogo",
    "cr vasco da gama": "vasco",
    "vasco": "vasco",
    "fluminense football club": "fluminense",
    "fluminense": "fluminense",
    "santos futebol clube": "santos",
    "santos": "santos",
    "goiás esporte clube": "goiás",
    "goias": "goiás",
    "goiás": "goiás",
    "coritiba foot ball club": "coritiba",
    "coritiba": "coritiba",
    "esporte clube bahia": "bahia",
    "bahia": "bahia",
    "esporte clube vitória": "vitória",
    "vitoria": "vitória",
    "vitória": "vitória",
    "fORTALEZA": "fortaleza",
    "fortaleza": "fortaleza",
    "internacional": "internacional",
    "athletico paranaense": "athletico-pr",
    "athletico-pr": "athletico-pr",
    "atletico paranaense": "athletico-pr",
    "atletico-pr": "athletico-pr",
    "ceará": "ceará",
    "ceara": "ceará",
    "red bull bragantino": "bragantino",
    "bragantino": "bragantino",
    "américa mineiro": "américa-mg",
    "america-mg": "américa-mg",
    "américa-mg": "américa-mg",
    "avai": "avaí",
    "avaí": "avaí",
    "figueirense": "figueirense",
    "chapecoense": "chapecoense",
    "ponte preta": "ponte preta",
    "guarani": "guarani",
    "nautico-pe": "náutico",
    "nautico": "náutico",
    "paysandu": "paysandu",
    "américa - mg": "américa-mg",
    "america - mg": "américa-mg",
    "boavista sport club (antigo esporte clube barreira) - rj": "boavista",
    "boavista sport club (antigo esporte clube barreira)": "boavista",
}
def normalize_team_name(name: str) -> str:
    """Normalize team names for consistent matching across datasets."""
    if pd.isna(name):
        return ""
    name = str(name).strip().lower()
    
    # Check exact mappings FIRST before any stripping
    if name in TEAM_NAME_MAPPINGS:
        return TEAM_NAME_MAPPINGS[name]
    
    # Remove common state suffixes like "-sp", "-rj", " - mg", etc.
    name = re.sub(r"\s*-\s*[a-z]{2}$", "", name)
    name = re.sub(r"\s+-\s*[a-z]{2}$", "", name)
    name = name.strip()
    
    # Check mappings again after stripping
    if name in TEAM_NAME_MAPPINGS:
        return TEAM_NAME_MAPPINGS[name]
    
    # Fallback: return cleaned name
    return name


def normalize_date(date_str: str) -> str:
    """Normalize various date formats to YYYY-MM-DD."""
    if pd.isna(date_str):
        return ""
    date_str = str(date_str).strip()
    
    # Try parsing with pandas
    try:
        # Handle DD/MM/YYYY format explicitly to avoid warnings
        if len(date_str) == 10 and date_str[2] == "/" and date_str[5] == "/":
            parsed = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
        else:
            parsed = pd.to_datetime(date_str, errors="coerce")
        
        if pd.notna(parsed):
            return parsed.strftime("%Y-%m-%d")
    except Exception:
        pass
    
    return date_str


def extract_season(date_str: str, existing_season: Optional[str] = None) -> str:
    """Extract season (year) from date string."""
    if existing_season and str(existing_season).strip():
        return str(existing_season).strip()
    
    try:
        if "/" in str(date_str):
            parsed = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
        else:
            parsed = pd.to_datetime(date_str, errors="coerce")
        if pd.notna(parsed):
            return str(parsed.year)
    except Exception:
        pass
    
    return ""


def load_match_data() -> pd.DataFrame:
    """Load and normalize all match datasets into a unified schema."""
    dfs = []
    
    # 1. Brasileirao_Matches.csv
    filepath = DATA_DIR / "Brasileirao_Matches.csv"
    if filepath.exists():
        df = pd.read_csv(filepath, dtype=str)
        df["date"] = df["datetime"].apply(normalize_date)
        df["home_team"] = df["home_team"].apply(normalize_team_name)
        df["away_team"] = df["away_team"].apply(normalize_team_name)
        df["home_goals"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64")
        df["away_goals"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64")
        df["season"] = df["season"].apply(lambda x: extract_season(x))
        df["competition"] = "Brasileirão Serie A"
        df = df[["date", "home_team", "away_team", "home_goals", "away_goals", "season", "competition", "round"]]
        dfs.append(df)
    
    # 2. Brazilian_Cup_Matches.csv
    filepath = DATA_DIR / "Brazilian_Cup_Matches.csv"
    if filepath.exists():
        df = pd.read_csv(filepath, dtype=str)
        df["date"] = df["datetime"].apply(normalize_date)
        df["home_team"] = df["home_team"].apply(normalize_team_name)
        df["away_team"] = df["away_team"].apply(normalize_team_name)
        df["home_goals"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64")
        df["away_goals"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64")
        df["season"] = df["season"].apply(lambda x: extract_season(x))
        df["competition"] = "Copa do Brasil"
        df = df[["date", "home_team", "away_team", "home_goals", "away_goals", "season", "competition", "round"]]
        dfs.append(df)
    
    # 3. Libertadores_Matches.csv
    filepath = DATA_DIR / "Libertadores_Matches.csv"
    if filepath.exists():
        df = pd.read_csv(filepath, dtype=str)
        df["date"] = df["datetime"].apply(normalize_date)
        df["home_team"] = df["home_team"].apply(normalize_team_name)
        df["away_team"] = df["away_team"].apply(normalize_team_name)
        df["home_goals"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64")
        df["away_goals"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64")
        df["season"] = df["season"].apply(lambda x: extract_season(x))
        df["competition"] = "Copa Libertadores"
        df["round"] = df.get("stage", "")
        df = df[["date", "home_team", "away_team", "home_goals", "away_goals", "season", "competition", "round"]]
        dfs.append(df)
    
    # 4. BR-Football-Dataset.csv
    filepath = DATA_DIR / "BR-Football-Dataset.csv"
    if filepath.exists():
        df = pd.read_csv(filepath, dtype=str)
        df["date"] = df["date"].apply(normalize_date)
        df["home_team"] = df["home"].apply(normalize_team_name)
        df["away_team"] = df["away"].apply(normalize_team_name)
        df["home_goals"] = pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64")
        df["away_goals"] = pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64")
        df["season"] = df["date"].apply(lambda x: extract_season(x))
        df["competition"] = df["tournament"].fillna("Unknown")
        df["round"] = ""
        df = df[["date", "home_team", "away_team", "home_goals", "away_goals", "season", "competition", "round"]]
        dfs.append(df)
    
    # 5. novo_campeonato_brasileiro.csv
    filepath = DATA_DIR / "novo_campeonato_brasileiro.csv"
    if filepath.exists():
        df = pd.read_csv(filepath, dtype=str)
        df["date"] = df["Data"].apply(normalize_date)
        df["home_team"] = df["Equipe_mandante"].apply(normalize_team_name)
        df["away_team"] = df["Equipe_visitante"].apply(normalize_team_name)
        df["home_goals"] = pd.to_numeric(df["Gols_mandante"], errors="coerce").astype("Int64")
        df["away_goals"] = pd.to_numeric(df["Gols_visitante"], errors="coerce").astype("Int64")
        df["season"] = df["Ano"].fillna("").astype(str)
        df["competition"] = "Brasileirão Serie A"
        df["round"] = df["Rodada"].fillna("")
        df = df[["date", "home_team", "away_team", "home_goals", "away_goals", "season", "competition", "round"]]
        dfs.append(df)
    
    if not dfs:
        raise FileNotFoundError(f"No match data files found in {DATA_DIR}")
    
    combined = pd.concat(dfs, ignore_index=True)
    return combined


def load_player_data() -> pd.DataFrame:
    """Load and normalize player dataset."""
    filepath = DATA_DIR / "fifa_data.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"Player data file not found: {filepath}")
    
    # Use encoding='utf-8-sig' to handle BOM in some CSVs
    df = pd.read_csv(filepath, encoding="utf-8-sig", dtype=str)
    
    # Keep only relevant columns to reduce memory
    keep_cols = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential",
        "Club", "Value", "Wage", "Position", "Jersey Number",
        "Height", "Weight", "Preferred Foot"
    ]
    
    existing_cols = [c for c in keep_cols if c in df.columns]
    df = df[existing_cols].copy()
    
    # Normalize club names and nationalities for consistent matching
    df["Club_normalized"] = df["Club"].apply(normalize_team_name)
    df["Nationality"] = df["Nationality"].fillna("").astype(str)
    df["Overall"] = pd.to_numeric(df["Overall"], errors="coerce").astype("Int64")
    df["Potential"] = pd.to_numeric(df["Potential"], errors="coerce").astype("Int64")
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").astype("Int64")
    
    return df


# Global cache for dataframes
_matches_df: Optional[pd.DataFrame] = None
_players_df: Optional[pd.DataFrame] = None


def get_matches_df() -> pd.DataFrame:
    """Get cached matches dataframe."""
    global _matches_df
    if _matches_df is None:
        _matches_df = load_match_data()
    return _matches_df


def get_players_df() -> pd.DataFrame:
    """Get cached players dataframe."""
    global _players_df
    if _players_df is None:
        _players_df = load_player_data()
    return _players_df


def clear_cache():
    """Clear cached dataframes (useful for testing)."""
    global _matches_df, _players_df
    _matches_df = None
    _players_df = None
