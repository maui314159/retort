import pandas as pd
import re
from pathlib import Path
from functools import lru_cache

DATA_DIR = Path("data/kaggle")

def normalize_team_name(name: str) -> str:
    if pd.isna(name):
        return ""
    name = str(name).strip()
    # Remove parenthesis content
    name = re.sub(r'\s*\([^)]*\)', '', name)
    # Remove trailing state codes like " - SP", "-SP", or " SP"
    name = re.sub(r'\s*-\s*[A-Z]{2,3}\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+[A-Z]{2,3}\s*$', '', name, flags=re.IGNORECASE)
    
    normalized = name.lower().strip()
    
    aliases = {
        "athletico pr": "athletico paranaense",
        "atletico pr": "athletico paranaense",
        "athletico-paranaense": "athletico paranaense",
        "vasco": "vasco da gama",
        "vasco da gama": "vasco da gama",
        "atletico mg": "atletico mineiro",
        "atletico-mg": "atletico mineiro",
        "atletico mineiro": "atletico mineiro",
        "sao paulo fc": "sao paulo",
        "sao paulo": "são paulo",
        "sport club corinthians paulista": "corinthians",
        "corinthians sp": "corinthians",
        "flamengo rj": "flamengo",
        "palmeiras sp": "palmeiras",
        "gremio": "grêmio",
        "grêmio": "grêmio",
        "atletico": "atletico mineiro",
        "goias": "goiás",
        "goiás": "goiás",
        "ceara": "ceará",
        "ceará": "ceará",
        "avai": "avaí",
        "avaí": "avaí",
    }
    return aliases.get(normalized, normalized)

@lru_cache(maxsize=1)
def load_brasileirao_matches() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df['competition'] = 'Brasileirão'
    df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
    df['away_team_norm'] = df['away_team'].apply(normalize_team_name)
    df['datetime'] = pd.to_datetime(df['datetime'], format='mixed', utc=True)
    df['season'] = pd.to_numeric(df['season'], errors='coerce').astype('Int64')
    return df

@lru_cache(maxsize=1)
def load_copa_brasil_matches() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv")
    df['competition'] = 'Copa do Brasil'
    df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
    df['away_team_norm'] = df['away_team'].apply(normalize_team_name)
    df['datetime'] = pd.to_datetime(df['datetime'], format='mixed', utc=True)
    df['season'] = pd.to_numeric(df['season'], errors='coerce').astype('Int64')
    return df

@lru_cache(maxsize=1)
def load_libertadores_matches() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv")
    df['competition'] = 'Copa Libertadores'
    df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
    df['away_team_norm'] = df['away_team'].apply(normalize_team_name)
    df['datetime'] = pd.to_datetime(df['datetime'], format='mixed', utc=True)
    df['season'] = pd.to_numeric(df['season'], errors='coerce').astype('Int64')
    return df

@lru_cache(maxsize=1)
def load_br_football_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df.rename(columns={
        'tournament': 'competition', 
        'home': 'home_team', 
        'away': 'away_team', 
        'date': 'datetime'
    }, inplace=True)
    df['competition'] = df['competition'].fillna('Unknown')
    df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
    df['away_team_norm'] = df['away_team'].apply(normalize_team_name)
    df['datetime'] = pd.to_datetime(df['datetime'], format='mixed', utc=True)
    df['season'] = pd.to_datetime(df['datetime']).dt.year.astype('Int64')
    return df

@lru_cache(maxsize=1)
def load_novo_campeonato() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv")
    df.rename(columns={
        'Equipe_mandante': 'home_team',
        'Equipe_visitante': 'away_team',
        'Gols_mandante': 'home_goal',
        'Gols_visitante': 'away_goal',
        'Ano': 'season',
        'Data': 'datetime'
    }, inplace=True)
    df['competition'] = 'Brasileirão (Histórico)'
    df['datetime'] = pd.to_datetime(df['datetime'], format='%d/%m/%Y', utc=True)
    df['home_team_norm'] = df['home_team'].apply(normalize_team_name)
    df['away_team_norm'] = df['away_team'].apply(normalize_team_name)
    df['season'] = pd.to_numeric(df['season'], errors='coerce').astype('Int64')
    return df

@lru_cache(maxsize=1)
def load_fifa_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "fifa_data.csv")
    if 'Unnamed: 0' in df.columns:
        df = df.drop(columns=['Unnamed: 0'])
    df['Name_norm'] = df['Name'].apply(lambda x: str(x).lower().strip() if pd.notna(x) else "")
    df['Club_norm'] = df['Club'].apply(normalize_team_name)
    df['Nationality_norm'] = df['Nationality'].apply(lambda x: str(x).lower().strip() if pd.notna(x) else "")
    return df

def get_all_matches() -> pd.DataFrame:
    return pd.concat([
        load_brasileirao_matches(),
        load_copa_brasil_matches(),
        load_libertadores_matches(),
        load_br_football_dataset(),
        load_novo_campeonato()
    ], ignore_index=True)