import os
import re
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "kaggle"


def _normalize_team_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    # Remove state suffix like "-SP", "-RJ"
    name = re.sub(r"-[A-Z]{2}$", "", name.strip())
    return name.strip()


def _load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df["competition"] = "Brasileirão Serie A"
    df["home_team_norm"] = df["home_team"].apply(_normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(_normalize_team_name)
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    return df


def _load_copa_brasil() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv")
    df["competition"] = "Copa do Brasil"
    df["home_team_norm"] = df["home_team"].apply(_normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(_normalize_team_name)
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    return df


def _load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv")
    df["competition"] = "Copa Libertadores"
    df["home_team_norm"] = df["home_team"].apply(_normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(_normalize_team_name)
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    return df


def _load_br_football() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df = df.rename(columns={"home": "home_team", "away": "away_team"})
    df["competition"] = df["tournament"].fillna("Unknown")
    df["home_team_norm"] = df["home_team"].apply(_normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(_normalize_team_name)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "season" not in df.columns:
        df["season"] = df["date"].dt.year
    return df


def _load_historico() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv", encoding="utf-8")
    df = df.rename(columns={
        "Equipe_mandante": "home_team",
        "Equipe_visitante": "away_team",
        "Gols_mandante": "home_goal",
        "Gols_visitante": "away_goal",
        "Ano": "season",
        "Rodada": "round",
    })
    df["competition"] = "Brasileirão Serie A (Histórico)"
    df["home_team_norm"] = df["home_team"].apply(_normalize_team_name)
    df["away_team_norm"] = df["away_team"].apply(_normalize_team_name)
    # Parse Brazilian date format DD/MM/YYYY
    df["date"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    return df


def _load_fifa() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "fifa_data.csv", low_memory=False)


_MATCHES: pd.DataFrame | None = None
_FIFA: pd.DataFrame | None = None


def get_matches() -> pd.DataFrame:
    global _MATCHES
    if _MATCHES is None:
        frames = [
            _load_brasileirao(),
            _load_copa_brasil(),
            _load_libertadores(),
            _load_br_football(),
            _load_historico(),
        ]
        common_cols = ["home_team", "away_team", "home_team_norm", "away_team_norm",
                       "home_goal", "away_goal", "season", "date", "competition"]
        normalized = []
        for df in frames:
            available = [c for c in common_cols if c in df.columns]
            normalized.append(df[available])
        _MATCHES = pd.concat(normalized, ignore_index=True)
        _MATCHES["home_goal"] = pd.to_numeric(_MATCHES["home_goal"], errors="coerce")
        _MATCHES["away_goal"] = pd.to_numeric(_MATCHES["away_goal"], errors="coerce")
        _MATCHES["season"] = pd.to_numeric(_MATCHES["season"], errors="coerce").astype("Int64")
    return _MATCHES


def get_fifa() -> pd.DataFrame:
    global _FIFA
    if _FIFA is None:
        _FIFA = _load_fifa()
    return _FIFA


def find_team_matches(
    team: str,
    opponent: str | None = None,
    season: int | None = None,
    competition: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
) -> pd.DataFrame:
    df = get_matches()
    team_lower = team.lower()

    home_mask = df["home_team_norm"].str.lower().str.contains(team_lower, na=False)
    away_mask = df["away_team_norm"].str.lower().str.contains(team_lower, na=False)

    if home_only:
        mask = home_mask
    elif away_only:
        mask = away_mask
    else:
        mask = home_mask | away_mask

    result = df[mask].copy()

    if opponent:
        opp_lower = opponent.lower()
        opp_home = result["home_team_norm"].str.lower().str.contains(opp_lower, na=False)
        opp_away = result["away_team_norm"].str.lower().str.contains(opp_lower, na=False)
        result = result[opp_home | opp_away]

    if season:
        result = result[result["season"] == season]

    if competition:
        result = result[result["competition"].str.lower().str.contains(competition.lower(), na=False)]

    return result.sort_values("date", ascending=False)
