"""Load and unify all Brazilian soccer CSV datasets.

The six Kaggle files are normalised into a single match table (with canonical
team names) and a player table.  Brasileirão data is built from the primary
`Brasileirao_Matches.csv` file for 2012+ and from the historical
campeonato file for 2003-2011 to avoid double-counting overlapping seasons.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from normalization import normalize_team_name, parse_date

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data" / "kaggle"

MATCH_COLS = [
    "competition",
    "season",
    "date",
    "home_team",
    "away_team",
    "home_goal",
    "away_goal",
    "round",
    "stage",
    "source",
]

PLAYER_COLS = [
    "id",
    "name",
    "age",
    "nationality",
    "overall",
    "potential",
    "club",
    "position",
    "jersey_number",
    "height",
    "weight",
]


def _to_numeric_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brasileirao_Matches.csv")
    df["source"] = "Brasileirao_Matches.csv"
    df = df.rename(
        columns={
            "datetime": "date",
            "home_team": "home_team",
            "away_team": "away_team",
            "home_goal": "home_goal",
            "away_goal": "away_goal",
            "season": "season",
            "round": "round",
        }
    )
    df["competition"] = "Brasileirão"
    df["stage"] = None
    return _clean_match_df(df)


def _load_novo_campeonato() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv")
    df["source"] = "novo_campeonato_brasileiro.csv"
    df = df.rename(
        columns={
            "Data": "date",
            "Ano": "season",
            "Rodada": "round",
            "Equipe_mandante": "home_team",
            "Equipe_visitante": "away_team",
            "Gols_mandante": "home_goal",
            "Gols_visitante": "away_goal",
        }
    )
    # Only use years not already covered by Brasileirao_Matches.csv (2012-2022).
    df = df[df["season"] <= 2011].copy()
    df["competition"] = "Brasileirão"
    df["stage"] = None
    return _clean_match_df(df)


def _load_brazilian_cup() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv")
    df["source"] = "Brazilian_Cup_Matches.csv"
    df = df.rename(
        columns={
            "datetime": "date",
            "home_team": "home_team",
            "away_team": "away_team",
            "home_goal": "home_goal",
            "away_goal": "away_goal",
            "season": "season",
            "round": "round",
        }
    )
    df["competition"] = "Copa do Brasil"
    df["stage"] = None
    return _clean_match_df(df)


def _load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Libertadores_Matches.csv")
    df["source"] = "Libertadores_Matches.csv"
    df = df.rename(
        columns={
            "datetime": "date",
            "home_team": "home_team",
            "away_team": "away_team",
            "home_goal": "home_goal",
            "away_goal": "away_goal",
            "season": "season",
            "stage": "stage",
        }
    )
    df["competition"] = "Copa Libertadores"
    df["round"] = None
    return _clean_match_df(df)


def _load_br_football() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BR-Football-Dataset.csv")
    df["source"] = "BR-Football-Dataset.csv"
    df = df.rename(
        columns={
            "tournament": "competition",
            "home": "home_team",
            "away": "away_team",
            "home_goal": "home_goal",
            "away_goal": "away_goal",
            "date": "date",
        }
    )
    df["season"] = pd.to_datetime(df["date"], errors="coerce").dt.year
    df["round"] = None
    df["stage"] = None
    return _clean_match_df(df)


def _clean_match_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = df["date"].apply(parse_date)
    df["home_team"] = df["home_team"].apply(normalize_team_name)
    df["away_team"] = df["away_team"].apply(normalize_team_name)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["round"] = df["round"].astype("string")
    df["stage"] = df["stage"].astype("string")
    df["source"] = df["source"].astype("string")
    return df


def load_matches() -> pd.DataFrame:
    """Return a unified, de-duplicated match DataFrame."""
    frames = [
        _load_brasileirao(),
        _load_novo_campeonato(),
        _load_brazilian_cup(),
        _load_libertadores(),
        _load_br_football(),
    ]
    df = pd.concat(frames, ignore_index=True)
    # Drop matches with missing critical fields.
    df = df.dropna(subset=["home_team", "away_team", "home_goal", "away_goal", "date"])
    # Coerce back to Int64 after dropna because numeric columns may still be floats.
    df["home_goal"] = df["home_goal"].astype("Int64")
    df["away_goal"] = df["away_goal"].astype("Int64")
    df["season"] = df["season"].astype("Int64")

    # Remove exact duplicates across datasets (same competition/season/teams/date/score).
    dedup_cols = [
        "competition", "season", "date", "home_team", "away_team",
        "home_goal", "away_goal",
    ]
    df = df.drop_duplicates(subset=dedup_cols, keep="first")

    return df[MATCH_COLS].sort_values(["date", "competition", "season"]).reset_index(drop=True)


def load_players() -> pd.DataFrame:
    """Return a cleaned player DataFrame from the FIFA dataset."""
    df = pd.read_csv(DATA_DIR / "fifa_data.csv")
    df = df.rename(
        columns={
            "ID": "id",
            "Name": "name",
            "Age": "age",
            "Nationality": "nationality",
            "Overall": "overall",
            "Potential": "potential",
            "Club": "club",
            "Position": "position",
            "Jersey Number": "jersey_number",
            "Height": "height",
            "Weight": "weight",
        }
    )
    for col in ["age", "overall", "potential", "jersey_number"]:
        df[col] = _to_numeric_int(df[col])

    df["club"] = df["club"].fillna("Unknown").astype(str)
    df["position"] = df["position"].fillna("Unknown").astype(str)
    df["nationality"] = df["nationality"].fillna("Unknown").astype(str)
    return df[PLAYER_COLS].copy()


class DataStore:
    """In-memory repository of matches and players."""

    def __init__(self) -> None:
        self.matches = load_matches()
        self.players = load_players()
