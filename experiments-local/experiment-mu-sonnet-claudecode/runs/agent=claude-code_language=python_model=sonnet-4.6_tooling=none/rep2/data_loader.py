import re
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "kaggle"

# Common team name aliases for normalization
_TEAM_ALIASES = {
    "atletico mineiro": ["atletico-mg", "atlético-mg", "atlético mineiro", "atletico mg", "galo"],
    "atletico paranaense": ["athletico-pr", "athletico pr", "atletico-pr", "atlético paranaense", "atletico paranaense", "furacão"],
    "atletico goianiense": ["atletico-go", "atletico go", "atlético goianiense"],
    "flamengo": ["flamengo-rj", "cr flamengo", "clube de regatas flamengo", "fla"],
    "fluminense": ["fluminense-rj", "flu"],
    "vasco": ["vasco-rj", "cr vasco da gama", "vasco da gama"],
    "botafogo": ["botafogo-rj"],
    "palmeiras": ["palmeiras-sp", "se palmeiras"],
    "sao paulo": ["são paulo", "sao paulo-sp", "são paulo-sp", "são paulo fc", "spfc"],
    "corinthians": ["sport club corinthians paulista", "corinthians-sp", "timão"],
    "santos": ["santos-sp", "santos fc"],
    "gremio": ["grêmio", "gremio-rs", "grêmio-rs", "grêmio fbpa"],
    "internacional": ["internacional-rs", "inter"],
    "cruzeiro": ["cruzeiro-mg"],
    "sport": ["sport-pe", "sport club do recife"],
    "bahia": ["bahia-ba", "esporte clube bahia"],
    "ceara": ["ceará", "ceara-ce", "ceará-ce"],
    "fortaleza": ["fortaleza-ce", "fortaleza ec"],
    "goias": ["goiás", "goias-go", "goiás-go"],
    "coritiba": ["coritiba-pr"],
    "avai": ["avaí", "avai-sc", "avaí-sc"],
    "chapecoense": ["chapecoense-sc"],
    "bragantino": ["rb bragantino", "red bull bragantino", "bragantino-sp", "red bull bragantino-sp"],
    "cuiaba": ["cuiabá", "cuiaba-mt", "cuiabá-mt"],
    "america mineiro": ["america-mg", "américa-mg", "américa mineiro"],
}

def _build_alias_map():
    m = {}
    for canonical, aliases in _TEAM_ALIASES.items():
        m[canonical] = canonical
        for a in aliases:
            m[a.lower()] = canonical
    return m

_ALIAS_MAP = _build_alias_map()


def normalize_team(name: str) -> str:
    if not name or not isinstance(name, str):
        return name
    cleaned = name.strip().lower()
    # Remove state suffix like "-SP", "-RJ", etc.
    cleaned_no_state = re.sub(r'-[a-z]{2}$', '', cleaned).strip()
    # Remove parenthetical suffixes like "(antigo ...)"
    cleaned_no_state = re.sub(r'\s*\(.*\)', '', cleaned_no_state).strip()
    return _ALIAS_MAP.get(cleaned_no_state, _ALIAS_MAP.get(cleaned, cleaned_no_state))


def _parse_dates(series: pd.Series) -> pd.Series:
    def _try_parse(val):
        if pd.isna(val):
            return pd.NaT
        s = str(val).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return pd.to_datetime(s, format=fmt)
            except Exception:
                pass
        try:
            return pd.to_datetime(s)
        except Exception:
            return pd.NaT
    return series.apply(_try_parse)


def load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv", encoding="utf-8")
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["competition"] = "Brasileirao Serie A"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_copa_brasil() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv", encoding="utf-8")
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["competition"] = "Copa do Brasil"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv", encoding="utf-8")
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["competition"] = "Copa Libertadores"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_br_football() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv", encoding="utf-8")
    df = df.rename(columns={"home": "home_team", "away": "away_team", "date": "datetime"})
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["competition"] = df.get("tournament", pd.Series(["Brazilian Football"] * len(df)))
    return df


def load_historico() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8")
    df = df.rename(columns={
        "Data": "datetime",
        "Ano": "season",
        "Rodada": "round",
        "Equipe_mandante": "home_team",
        "Equipe_visitante": "away_team",
        "Gols_mandante": "home_goal",
        "Gols_visitante": "away_goal",
        "Mandante_UF": "home_team_state",
        "Visitante_UF": "away_team_state",
        "Vencedor": "winner",
        "Arena": "arena",
    })
    df["datetime"] = _parse_dates(df["datetime"])
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["competition"] = "Brasileirao Serie A"
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    return df


def load_fifa() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "fifa_data.csv", encoding="utf-8")
    # Strip BOM from first column name if present
    df.columns = [c.lstrip('﻿').strip() for c in df.columns]
    df["Overall"] = pd.to_numeric(df.get("Overall", pd.Series()), errors="coerce")
    df["Age"] = pd.to_numeric(df.get("Age", pd.Series()), errors="coerce")
    return df


def load_all_matches() -> pd.DataFrame:
    """Return a unified match DataFrame from all sources."""
    frames = []
    for loader in [load_brasileirao, load_copa_brasil, load_libertadores, load_br_football, load_historico]:
        try:
            df = loader()
            frames.append(df[["datetime", "home_team", "away_team", "home_goal", "away_goal",
                               "competition", "home_team_norm", "away_team_norm",
                               *([c for c in df.columns if c in ("season", "round", "stage")])]])
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
