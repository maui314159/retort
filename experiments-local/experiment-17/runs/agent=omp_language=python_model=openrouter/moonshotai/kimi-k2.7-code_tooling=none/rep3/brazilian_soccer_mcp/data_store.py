"""
Brazilian Soccer MCP - Data Store.

This module loads and normalizes the six CSV datasets that ship with the
project.  It produces a single, query-friendly collection of pandas
DataFrames:

    - matches: a unified view of every match across all competition files
    - players: the FIFA player dataset

Team names are normalized to canonical keys and dates are parsed into
``datetime64[ns]`` values.  The data store is intentionally lazy: files are
loaded once and cached until ``reload()`` is called.

All paths are resolved relative to the repository root so that the server
works regardless of the current working directory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from brazilian_soccer_mcp.team_normalizer import (
    canonical_team_names,
    normalize_team_name,
)


# Repository root is two levels above this file (data_store.py lives under
# brazilian_soccer_mcp/).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO_ROOT / "data" / "kaggle"

# Mapping of competition labels used inside the unified matches table.
_COMP_BRASILEIRAO = "Brasileirao"
_COMP_COPA_BRASIL = "Copa do Brasil"
_COMP_LIBERTADORES = "Copa Libertadores"


class DataStore:
    """Loads, normalizes and caches Brazilian soccer datasets."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else _DATA_DIR
        self._matches: pd.DataFrame | None = None
        self._players: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------
    @property
    def matches(self) -> pd.DataFrame:
        """Return the unified matches DataFrame (loaded lazily)."""
        if self._matches is None:
            self._load_all()
        return self._matches  # type: ignore[return-value]

    @property
    def players(self) -> pd.DataFrame:
        """Return the normalized players DataFrame (loaded lazily)."""
        if self._players is None:
            self._load_all()
        return self._players  # type: ignore[return-value]

    def reload(self) -> None:
        """Force a reload of all datasets on the next access."""
        self._matches = None
        self._players = None

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------
    def _load_all(self) -> None:
        """Load and unify every dataset."""
        brasileirao = self._load_brasileirao()
        copa = self._load_copa_brasil()
        libertadores = self._load_libertadores()
        extended = self._load_extended()
        historical = self._load_historical()

        unified = pd.concat(
            [brasileirao, copa, libertadores, extended, historical],
            ignore_index=True,
            sort=False,
        )

        # Drop rows that could not be parsed meaningfully.
        unified = unified.dropna(subset=["home_team", "away_team", "date"]).copy()

        # Some datasets contain missing goal values.  Treat missing goals as 0
        # for display/derived columns, but keep the original NaN where present.
        home_goal_safe = unified["home_goal"].fillna(0).astype(int)
        away_goal_safe = unified["away_goal"].fillna(0).astype(int)

        # Build a display string and a numeric goal-difference column.
        unified["score"] = home_goal_safe.astype(str) + "-" + away_goal_safe.astype(str)
        unified["goal_difference"] = (home_goal_safe - away_goal_safe).astype(int)

        # Sort chronologically.
        unified = unified.sort_values(
            by=["date", "competition", "round"], ascending=[False, True, True]
        ).reset_index(drop=True)

        self._matches = unified
        self._players = self._load_players()

    def _read_csv(self, filename: str, **kwargs: Any) -> pd.DataFrame:
        """Read a CSV from the data directory with forgiving encoding."""
        path = self._data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")

        encodings = ["utf-8-sig", "utf-8", "latin1"]
        for encoding in encodings:
            try:
                return pd.read_csv(path, encoding=encoding, **kwargs)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(path, encoding="latin1", **kwargs)

    # ------------------------------------------------------------------
    # Per-file loaders -> normalized columns
    # ------------------------------------------------------------------
    def _load_brasileirao(self) -> pd.DataFrame:
        """Load Brasileirao_Matches.csv."""
        df = self._read_csv("Brasileirao_Matches.csv")
        df = self._rename_and_coerce(
            df,
            {
                "datetime": "date",
                "home_team": "home_team_raw",
                "away_team": "away_team_raw",
                "home_goal": "home_goal",
                "away_goal": "away_goal",
                "season": "season",
                "round": "round",
            },
        )
        df["competition"] = _COMP_BRASILEIRAO
        df["stage"] = None
        return self._normalize_match_df(df)

    def _load_copa_brasil(self) -> pd.DataFrame:
        """Load Brazilian_Cup_Matches.csv."""
        df = self._read_csv("Brazilian_Cup_Matches.csv")
        df = self._rename_and_coerce(
            df,
            {
                "datetime": "date",
                "home_team": "home_team_raw",
                "away_team": "away_team_raw",
                "home_goal": "home_goal",
                "away_goal": "away_goal",
                "season": "season",
                "round": "round",
            },
        )
        df["competition"] = _COMP_COPA_BRASIL
        df["stage"] = None
        return self._normalize_match_df(df)

    def _load_libertadores(self) -> pd.DataFrame:
        """Load Libertadores_Matches.csv."""
        df = self._read_csv("Libertadores_Matches.csv")
        df = self._rename_and_coerce(
            df,
            {
                "datetime": "date",
                "home_team": "home_team_raw",
                "away_team": "away_team_raw",
                "home_goal": "home_goal",
                "away_goal": "away_goal",
                "season": "season",
                "stage": "stage",
            },
        )
        df["competition"] = _COMP_LIBERTADORES
        df["round"] = df.get("stage")
        return self._normalize_match_df(df)

    def _load_extended(self) -> pd.DataFrame:
        """Load BR-Football-Dataset.csv."""
        df = self._read_csv("BR-Football-Dataset.csv")
        df = self._rename_and_coerce(
            df,
            {
                "date": "date",
                "home": "home_team_raw",
                "away": "away_team_raw",
                "home_goal": "home_goal",
                "away_goal": "away_goal",
                "tournament": "competition",
            },
        )
        # Infer season from the match date.
        df["season"] = pd.to_datetime(df["date"], errors="coerce").dt.year
        df["round"] = None
        df["stage"] = None
        return self._normalize_match_df(df)

    def _load_historical(self) -> pd.DataFrame:
        """Load novo_campeonato_brasileiro.csv."""
        df = self._read_csv("novo_campeonato_brasileiro.csv")
        df = self._rename_and_coerce(
            df,
            {
                "Data": "date",
                "Equipe_mandante": "home_team_raw",
                "Equipe_visitante": "away_team_raw",
                "Gols_mandante": "home_goal",
                "Gols_visitante": "away_goal",
                "Ano": "season",
                "Rodada": "round",
                "Arena": "venue",
            },
        )
        df["competition"] = _COMP_BRASILEIRAO
        df["stage"] = None
        return self._normalize_match_df(df)

    def _load_players(self) -> pd.DataFrame:
        """Load and normalize fifa_data.csv."""
        df = self._read_csv("fifa_data.csv")
        # The first column is often an unnamed index.
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])

        df = df.rename(
            columns={
                "Name": "name",
                "Age": "age",
                "Nationality": "nationality",
                "Overall": "overall",
                "Potential": "potential",
                "Club": "club_raw",
                "Position": "position",
                "Jersey Number": "jersey_number",
            }
        )

        # Coerce numeric columns safely.
        for col in ["age", "overall", "potential", "jersey_number"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Normalize club names when possible; keep raw value otherwise.
        df["club"] = df["club_raw"].apply(
            lambda x: normalize_team_name(x) if pd.notna(x) else ""
        )
        df["is_brazilian"] = df["nationality"].astype(str).str.strip().str.lower() == "brazil"

        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------
    def _rename_and_coerce(
        self, df: pd.DataFrame, mapping: dict[str, str]
    ) -> pd.DataFrame:
        """Rename columns and coerce goal columns to numeric."""
        df = df.rename(columns=mapping)
        for col in ["home_goal", "away_goal"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def _normalize_match_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply team-name normalization and date parsing to a match DataFrame."""
        for col in ["home_team_raw", "away_team_raw"]:
            if col not in df.columns:
                df[col] = ""

        df["home_team"] = df["home_team_raw"].apply(
            lambda x: normalize_team_name(x) if pd.notna(x) else ""
        )
        df["away_team"] = df["away_team_raw"].apply(
            lambda x: normalize_team_name(x) if pd.notna(x) else ""
        )

        df["date"] = df["date"].apply(self._parse_date)
        df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")

        # Round can be a number or a stage label.
        if "round" in df.columns:
            df["round"] = df["round"].astype(str).replace("nan", "")
        else:
            df["round"] = ""

        # Keep only the unified columns we care about.
        keep = [
            "date",
            "home_team",
            "away_team",
            "home_team_raw",
            "away_team_raw",
            "home_goal",
            "away_goal",
            "competition",
            "season",
            "round",
            "stage",
        ]
        for extra in ["venue", "home_team_state", "away_team_state"]:
            if extra in df.columns:
                keep.append(extra)
        return df[[c for c in keep if c in df.columns]].copy()

    def _parse_date(self, value: Any) -> pd.Timestamp | pd.NaT:
        """Parse a date from multiple textual formats."""
        if isinstance(value, pd.Timestamp):
            return value
        if pd.isna(value):
            return pd.NaT

        text = str(value).strip()
        if not text:
            return pd.NaT

        # Brazilian format DD/MM/YYYY - check first to avoid ambiguous parser warnings.
        if re.match(r"\d{2}/\d{2}/\d{4}", text):
            try:
                return pd.to_datetime(text, format="%d/%m/%Y", errors="raise")
            except (ValueError, TypeError):
                pass

        # Try ISO datetime next.
        try:
            return pd.to_datetime(text, errors="raise")
        except (ValueError, TypeError):
            pass

        # Loose parser as a last resort.
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
        return parsed if pd.notna(parsed) else pd.NaT

    # ------------------------------------------------------------------
    # Statistics helpers used by the query engine
    # ------------------------------------------------------------------
    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str | None = None,
    ) -> dict[str, Any]:
        """Compute basic statistics for a canonical team.

        ``venue`` may be ``"home"``, ``"away"`` or ``None`` for both.
        """
        df = self.matches.copy()
        df = df[df["home_team"].eq(team) | df["away_team"].eq(team)]
        if season is not None:
            df = df[df["season"] == season]
        if competition is not None:
            df = df[df["competition"].str.lower() == competition.lower()]

        if venue == "home":
            df = df[df["home_team"].eq(team)]
        elif venue == "away":
            df = df[df["away_team"].eq(team)]

        stats: dict[str, Any] = {
            "team": team,
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        if df.empty:
            return stats

        def _result(row: pd.Series) -> str:
            is_home = row["home_team"] == team
            gf = row["home_goal"] if is_home else row["away_goal"]
            ga = row["away_goal"] if is_home else row["home_goal"]
            if gf > ga:
                return "win"
            if gf < ga:
                return "loss"
            return "draw"

        df = df.copy()
        df["result"] = df.apply(_result, axis=1)
        df["goals_for"] = df.apply(
            lambda r: r["home_goal"] if r["home_team"] == team else r["away_goal"],
            axis=1,
        )
        df["goals_against"] = df.apply(
            lambda r: r["away_goal"] if r["home_team"] == team else r["home_goal"],
            axis=1,
        )

        stats["matches"] = int(len(df))
        stats["wins"] = int((df["result"] == "win").sum())
        stats["draws"] = int((df["result"] == "draw").sum())
        stats["losses"] = int((df["result"] == "loss").sum())
        stats["goals_for"] = int(df["goals_for"].sum())
        stats["goals_against"] = int(df["goals_against"].sum())
        stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]
        stats["win_rate"] = (
            round(stats["wins"] / stats["matches"] * 100, 1)
            if stats["matches"]
            else 0.0
        )
        return stats

    def standings(
        self, season: int, competition: str | None = None
    ) -> pd.DataFrame:
        """Compute league-style standings for a season.

        Points are awarded as 3 for a win, 1 for a draw, 0 for a loss.
        Returns a DataFrame sorted by points descending.
        """
        df = self.matches.copy()
        df = df[df["season"] == season]
        if competition is not None:
            df = df[df["competition"].str.lower() == competition.lower()]

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "team",
                    "points",
                    "wins",
                    "draws",
                    "losses",
                    "goals_for",
                    "goals_against",
                    "goal_difference",
                ]
            )

        records: dict[str, dict[str, int]] = {}

        def _ensure(team: str) -> None:
            if team not in records:
                records[team] = {
                    "team": team,
                    "points": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                }

        for _, row in df.iterrows():
            home = row["home_team"]
            away = row["away_team"]
            if not home or not away:
                continue
            hg = row["home_goal"]
            ag = row["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            _ensure(home)
            _ensure(away)
            records[home]["goals_for"] += int(hg)
            records[home]["goals_against"] += int(ag)
            records[away]["goals_for"] += int(ag)
            records[away]["goals_against"] += int(hg)

            if hg > ag:
                records[home]["wins"] += 1
                records[home]["points"] += 3
                records[away]["losses"] += 1
            elif hg < ag:
                records[away]["wins"] += 1
                records[away]["points"] += 3
                records[home]["losses"] += 1
            else:
                records[home]["draws"] += 1
                records[home]["points"] += 1
                records[away]["draws"] += 1
                records[away]["points"] += 1

        standings_df = pd.DataFrame.from_records(list(records.values()))
        standings_df["goal_difference"] = (
            standings_df["goals_for"] - standings_df["goals_against"]
        )
        standings_df = standings_df.sort_values(
            by=["points", "goal_difference", "goals_for"],
            ascending=[False, False, False],
        ).reset_index(drop=True)
        return standings_df

    def top_scorers(
        self, season: int | None = None, limit: int = 10
    ) -> pd.DataFrame:
        """Return the teams with the most goals scored.

        Individual player top scorers cannot be inferred reliably from the
        match-level data, so this aggregates goals by team.
        """
        df = self.matches.copy()
        if season is not None:
            df = df[df["season"] == season]

        home = (
            df.groupby("home_team")["home_goal"]
            .sum()
            .rename("goals")
            .reset_index()
            .rename(columns={"home_team": "team"})
        )
        away = (
            df.groupby("away_team")["away_goal"]
            .sum()
            .rename("goals")
            .reset_index()
            .rename(columns={"away_team": "team"})
        )
        totals = (
            pd.concat([home, away], ignore_index=True)
            .groupby("team")["goals"]
            .sum()
            .reset_index()
            .sort_values("goals", ascending=False)
            .head(limit)
            .reset_index(drop=True)
        )
        return totals


# Module-level singleton for convenient import.
_store: DataStore | None = None


def get_data_store() -> DataStore:
    """Return the global DataStore singleton."""
    global _store
    if _store is None:
        _store = DataStore()
    return _store
