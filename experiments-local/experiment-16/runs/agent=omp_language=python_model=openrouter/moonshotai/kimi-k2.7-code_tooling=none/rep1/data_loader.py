"""
Data loader for Brazilian Soccer MCP Server.

Loads match and player CSVs from data/kaggle/, normalizes team names and dates,
and exposes unified DataFrames for the query engine.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Final

import pandas as pd

DATA_DIR: Final[Path] = Path(__file__).parent / "data" / "kaggle"

DATA_FILES: Final[dict[str, Path]] = {
    "brasileirao": DATA_DIR / "Brasileirao_Matches.csv",
    "copa_brasil": DATA_DIR / "Brazilian_Cup_Matches.csv",
    "libertadores": DATA_DIR / "Libertadores_Matches.csv",
    "br_football": DATA_DIR / "BR-Football-Dataset.csv",
    "novo_brasileirao": DATA_DIR / "novo_campeonato_brasileiro.csv",
}

PLAYER_FILE: Final[Path] = DATA_DIR / "fifa_data.csv"

COMPETITION_ALIASES: Final[dict[str, list[str]]] = {
    "Brasileirão": ["brasileirao", "brasileirão", "serie a", "série a", "campeonato brasileiro"],
    "Copa do Brasil": ["copa do brasil", "brazilian cup"],
    "Copa Libertadores": ["copa libertadores", "libertadores"],
}


def _remove_accents(value: str) -> str:
    """Return an ASCII-folding of the input while preserving base letters."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", value)
        if unicodedata.category(ch) != "Mn"
    )


def normalize_team_name(name: str | None) -> str:
    """
    Convert a team name into a canonical key for matching.

    Handles accented characters, state suffixes (e.g. '-SP'), parenthetical
    country codes (e.g. '(URU)'), and extra whitespace.
    """
    if not isinstance(name, str):
        return ""

    # Remove parenthetical suffixes such as (URU), (antigo ...)
    name = re.sub(r"\s*\([^)]*\)", "", name)
    # Remove trailing state suffix like " - RJ" or "-SP"
    name = re.sub(r"\s*-\s*[A-Z]{2}$", "", name)
    name = re.sub(r"\s+-\s+[A-Z]{2}$", "", name)
    # Remove accents and normalize whitespace
    name = _remove_accents(name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.lower()


def _parse_date(value: str | float) -> pd.Timestamp | pd.NaT:
    """Parse dates in ISO or Brazilian DD/MM/YYYY formats."""
    if pd.isna(value):
        return pd.NaT
    value = str(value).strip()
    if not value:
        return pd.NaT
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return pd.to_datetime(value, format=fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(value, dayfirst=True, errors="coerce")
    except Exception:
        return pd.NaT


def load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILES["brasileirao"])
    df = df.rename(
        columns={
            "datetime": "raw_datetime",
            "home_team": "home_team",
            "home_team_state": "home_team_state",
            "away_team": "away_team",
            "away_team_state": "away_team_state",
            "home_goal": "home_goal",
            "away_goal": "away_goal",
            "season": "season",
            "round": "round",
        }
    )
    df["competition"] = "Brasileirão"
    df["stage"] = None
    df["date"] = df["raw_datetime"].apply(_parse_date)
    return df


def load_copa_brasil() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILES["copa_brasil"])
    df = df.rename(
        columns={
            "round": "round",
            "datetime": "raw_datetime",
            "home_team": "home_team",
            "away_team": "away_team",
            "home_goal": "home_goal",
            "away_goal": "away_goal",
            "season": "season",
        }
    )
    df["competition"] = "Copa do Brasil"
    df["stage"] = None
    df["home_team_state"] = None
    df["away_team_state"] = None
    df["date"] = df["raw_datetime"].apply(_parse_date)
    return df


def load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILES["libertadores"])
    df = df.rename(
        columns={
            "datetime": "raw_datetime",
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
    df["home_team_state"] = None
    df["away_team_state"] = None
    df["date"] = df["raw_datetime"].apply(_parse_date)
    return df


def load_br_football() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILES["br_football"])
    df = df.rename(
        columns={
            "tournament": "competition",
            "home": "home_team",
            "away": "away_team",
            "home_goal": "home_goal",
            "away_goal": "away_goal",
            "time": "time",
            "date": "raw_date",
        }
    )
    # Map common English names to Portuguese competition names used elsewhere.
    competition_map = {
        "Serie A": "Brasileirão",
        "Copa do Brasil": "Copa do Brasil",
    }
    df["competition"] = df["competition"].map(competition_map).fillna(df["competition"])
    df["round"] = None
    df["stage"] = None
    df["home_team_state"] = None
    df["away_team_state"] = None
    df["date"] = df["raw_date"].apply(_parse_date)
    return df


def load_novo_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILES["novo_brasileirao"])
    df = df.rename(
        columns={
            "ID": "match_id",
            "Data": "raw_date",
            "Ano": "season",
            "Rodada": "round",
            "Equipe_mandante": "home_team",
            "Equipe_visitante": "away_team",
            "Gols_mandante": "home_goal",
            "Gols_visitante": "away_goal",
            "Mandante_UF": "home_team_state",
            "Visitante_UF": "away_team_state",
            "Arena": "stage",
        }
    )
    df["competition"] = "Brasileirão"
    df["date"] = df["raw_date"].apply(_parse_date)
    # Arena was borrowed for stage temporarily; set stage to None because the
    # historical dataset does not have a meaningful stage column.
    df["stage"] = None
    return df


def load_matches() -> pd.DataFrame:
    """
    Load all match CSVs and concatenate them into a unified DataFrame.

    The returned DataFrame contains normalized team-name keys as well as the
    original display names.
    """
    frames = [
        load_brasileirao(),
        load_copa_brasil(),
        load_libertadores(),
        load_br_football(),
        load_novo_brasileirao(),
    ]

    unified = pd.concat(frames, ignore_index=True, sort=False)
    # Ensure numeric score columns and seasons. Infer season from date when absent.
    unified["home_goal"] = pd.to_numeric(unified["home_goal"], errors="coerce")
    unified["away_goal"] = pd.to_numeric(unified["away_goal"], errors="coerce")
    unified["season"] = pd.to_numeric(unified["season"], errors="coerce").astype("Int64")
    unified["season"] = unified["season"].fillna(unified["date"].dt.year).astype("Int64")

    # Keep a display version of the name and add canonical keys.
    unified["home_team_display"] = unified["home_team"].astype(str).str.strip()
    unified["away_team_display"] = unified["away_team"].astype(str).str.strip()
    unified["home_team_key"] = unified["home_team_display"].apply(normalize_team_name)
    unified["away_team_key"] = unified["away_team_display"].apply(normalize_team_name)

    # Build a stable unique identifier for each row.
    unified["match_id"] = (
        unified["competition"].astype(str) + "_"
        + unified["season"].astype(str) + "_"
        + unified.index.astype(str)
    )

    # Sort by date for predictable output.
    unified = unified.sort_values("date", ascending=False, na_position="last")
    return unified.reset_index(drop=True)


def load_players() -> pd.DataFrame:
    """Load and lightly normalize the FIFA player dataset."""
    df = pd.read_csv(PLAYER_FILE)
    keep = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential",
        "Club", "Position", "Jersey Number", "Height", "Weight",
    ]
    df = df[[c for c in keep if c in df.columns]].copy()
    df = df.rename(
        columns={
            "ID": "player_id",
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
    df["overall"] = pd.to_numeric(df["overall"], errors="coerce")
    df["potential"] = pd.to_numeric(df["potential"], errors="coerce")
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["name_key"] = df["name"].astype(str).str.lower().apply(_remove_accents)
    df["club_key"] = df["club"].astype(str).apply(normalize_team_name)
    df["nationality_key"] = df["nationality"].astype(str).str.lower().apply(_remove_accents)
    return df


def resolve_competition(query: str | None) -> list[str] | None:
    """Return canonical competition names matching a free-text query."""
    if query is None:
        return None
    key = normalize_team_name(query)
    for canonical, aliases in COMPETITION_ALIASES.items():
        if key == normalize_team_name(canonical) or key in aliases:
            return [canonical]
    # Fall back to substring matching across all canonical names.
    matches = [c for c in COMPETITION_ALIASES if key in normalize_team_name(c)]
    return matches or None


def resolve_team_name(query: str, matches_df: pd.DataFrame) -> str | None:
    """
    Resolve a user-provided team name to the most common canonical key.

    Uses strict key equality first, then substring matching on display names.
    """
    query_key = normalize_team_name(query)
    home_keys = matches_df["home_team_key"].dropna()
    away_keys = matches_df["away_team_key"].dropna()
    home_display = matches_df["home_team_display"].dropna()
    away_display = matches_df["away_team_display"].dropna()

    all_keys = pd.concat([home_keys, away_keys], ignore_index=True)
    all_display = pd.concat([home_display, away_display], ignore_index=True)

    # Exact key match.
    if query_key in all_keys.unique():
        return query_key

    # Substring matching on normalized display names.
    normalized_display = all_display.apply(normalize_team_name)
    for idx, norm in normalized_display.items():
        if query_key in norm or norm in query_key:
            return all_keys.iloc[idx]

    return None


if __name__ == "__main__":
    matches = load_matches()
    players = load_players()
    print("Matches:", matches.shape)
    print("Competitions:", matches["competition"].value_counts().to_dict())
    print("Players:", players.shape)
