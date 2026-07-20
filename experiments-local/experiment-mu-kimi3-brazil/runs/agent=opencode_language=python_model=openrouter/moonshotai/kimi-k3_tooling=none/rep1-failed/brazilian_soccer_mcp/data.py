"""Dataset loading for the Brazilian soccer MCP server.

Why: the six Kaggle CSVs use different schemas, date formats and team
spellings; queries need one unified, de-duplicated match table plus the
FIFA player table.

What: `Dataset` reads every CSV from ``data/kaggle`` (or a given
directory), normalizes each source into a common match schema
(competition, date, season, round, stage, teams, goals, source) and
exposes ``matches`` and ``players`` DataFrames. `get_dataset` caches a
process-wide default instance so tool calls stay fast.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pandas as pd

from .normalization import normalize_team, strip_accents

BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_MATCH_COLUMNS = [
    "competition",
    "date",
    "season",
    "round",
    "stage",
    "home_team",
    "away_team",
    "home_canon",
    "away_canon",
    "home_goals",
    "away_goals",
    "source",
]

# Load order doubles as de-duplication priority: dedicated competition
# files win over the extended/historical catch-all files.
_SOURCES = (
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "novo_campeonato_brasileiro.csv",
    "BR-Football-Dataset.csv",
)


def _parse_mixed_datetime(values: pd.Series, dayfirst: bool = False) -> pd.Series:
    """Parse datetimes tolerating ISO and DD/MM/YYYY formats."""
    return pd.to_datetime(values, format="mixed", dayfirst=dayfirst, errors="coerce")


def _load_brasileirao(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "Brasileirao_Matches.csv")
    out = pd.DataFrame(
        {
            "competition": BRASILEIRAO_A,
            "date": _parse_mixed_datetime(df["datetime"]),
            "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
            "round": pd.to_numeric(df["round"], errors="coerce").astype("Int64"),
            "stage": pd.NA,
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_goals": pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64"),
            "away_goals": pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64"),
            "source": "Brasileirao_Matches.csv",
        }
    )
    return out


def _load_copa_do_brasil(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "Brazilian_Cup_Matches.csv")
    out = pd.DataFrame(
        {
            "competition": COPA_DO_BRASIL,
            "date": _parse_mixed_datetime(df["datetime"]),
            "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
            "round": pd.to_numeric(df["round"], errors="coerce").astype("Int64"),
            "stage": pd.NA,
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_goals": pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64"),
            "away_goals": pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64"),
            "source": "Brazilian_Cup_Matches.csv",
        }
    )
    return out


def _load_libertadores(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "Libertadores_Matches.csv")
    out = pd.DataFrame(
        {
            "competition": LIBERTADORES,
            "date": _parse_mixed_datetime(df["datetime"]),
            "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
            "round": pd.Series(pd.NA, index=df.index, dtype="Int64"),
            "stage": df["stage"].astype("string"),
            "home_team": df["home_team"],
            "away_team": df["away_team"],
            "home_goals": pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64"),
            "away_goals": pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64"),
            "source": "Libertadores_Matches.csv",
        }
    )
    return out


def _load_historico(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "novo_campeonato_brasileiro.csv")
    out = pd.DataFrame(
        {
            "competition": BRASILEIRAO_A,
            "date": _parse_mixed_datetime(df["Data"], dayfirst=True),
            "season": pd.to_numeric(df["Ano"], errors="coerce").astype("Int64"),
            "round": pd.to_numeric(df["Rodada"], errors="coerce").astype("Int64"),
            "stage": pd.NA,
            "home_team": df["Equipe_mandante"],
            "away_team": df["Equipe_visitante"],
            "home_goals": pd.to_numeric(df["Gols_mandante"], errors="coerce").astype("Int64"),
            "away_goals": pd.to_numeric(df["Gols_visitante"], errors="coerce").astype("Int64"),
            "source": "novo_campeonato_brasileiro.csv",
        }
    )
    return out


_BR_TOURNAMENT_MAP = {
    "serie a": BRASILEIRAO_A,
    "serie b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
}


def _load_br_football(data_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(data_dir / "BR-Football-Dataset.csv")
    tournaments = df["tournament"].map(
        lambda t: _BR_TOURNAMENT_MAP.get(strip_accents(str(t)).lower().strip(), str(t))
    )
    out = pd.DataFrame(
        {
            "competition": tournaments,
            "date": _parse_mixed_datetime(df["date"]),
            "season": _parse_mixed_datetime(df["date"]).dt.year.astype("Int64"),
            "round": pd.Series(pd.NA, index=df.index, dtype="Int64"),
            "stage": pd.NA,
            "home_team": df["home"],
            "away_team": df["away"],
            "home_goals": pd.to_numeric(df["home_goal"], errors="coerce").astype("Int64"),
            "away_goals": pd.to_numeric(df["away_goal"], errors="coerce").astype("Int64"),
            "source": "BR-Football-Dataset.csv",
        }
    )
    return out


class Dataset:
    """Unified view over the six Kaggle CSV files.

    Attributes:
        matches: one row per match, de-duplicated across sources.
        players: the FIFA player table with extra ``name_norm`` and
            ``club_canon`` helper columns.
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = self._resolve_data_dir(data_dir)
        self.matches = self._build_matches()
        self.players = self._build_players()

    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_data_dir(data_dir: str | Path | None) -> Path:
        if data_dir is not None:
            path = Path(data_dir)
            if not path.is_dir():
                raise FileNotFoundError(f"data directory not found: {path}")
            return path
        # Walk up from this file looking for data/kaggle.
        for parent in Path(__file__).resolve().parents:
            candidate = parent / "data" / "kaggle"
            if candidate.is_dir():
                return candidate
        raise FileNotFoundError("could not locate data/kaggle directory")

    # ------------------------------------------------------------------
    def _build_matches(self) -> pd.DataFrame:
        loaders = {
            "Brasileirao_Matches.csv": _load_brasileirao,
            "Brazilian_Cup_Matches.csv": _load_copa_do_brasil,
            "Libertadores_Matches.csv": _load_libertadores,
            "novo_campeonato_brasileiro.csv": _load_historico,
            "BR-Football-Dataset.csv": _load_br_football,
        }
        frames = [loaders[name](self.data_dir) for name in _SOURCES]
        matches = pd.concat(frames, ignore_index=True)

        matches["home_canon"] = matches["home_team"].map(normalize_team)
        matches["away_canon"] = matches["away_team"].map(normalize_team)

        # Drop rows that cannot be scored or dated, and self-play rows
        # (source data errors, e.g. "Bragantino - PA vs Bragantino - PA").
        matches = matches.dropna(subset=["date", "home_goals", "away_goals"])
        matches = matches[matches["home_canon"] != ""]
        matches = matches[matches["away_canon"] != ""]
        matches = matches[matches["home_canon"] != matches["away_canon"]]
        return self._deduplicate(matches)[_MATCH_COLUMNS]

    @staticmethod
    def _deduplicate(matches: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate fixtures across the overlapping sources.

        The extended BR-Football file duplicates matches already present
        in the dedicated competition files, but its dates are sometimes
        off by one day (timezone artifacts). De-duplication therefore
        works in two passes:

        1. exact: same competition, calendar day and both clubs
        2. tolerant: same competition and fixture (home/away clubs) with
           dates at most 2 days apart

        Within each duplicate cluster the row from the highest-priority
        source (load order in ``_SOURCES``) wins.
        """
        df = matches.copy()
        df["_day"] = df["date"].dt.normalize()
        df["_rank"] = df["source"].map({name: i for i, name in enumerate(_SOURCES)})

        # Pass 1: exact duplicates.
        df = df.sort_values("_rank")
        df = df.drop_duplicates(
            subset=["competition", "_day", "home_canon", "away_canon"], keep="first"
        )

        # Pass 2: same fixture within a 2-day window -> one cluster.
        df = df.sort_values(["competition", "home_canon", "away_canon", "_day"])
        df["_ord"] = df["_day"].map(pd.Timestamp.toordinal)
        within = df.groupby(["competition", "home_canon", "away_canon"], sort=False)
        gap = within["_ord"].diff().fillna(9999)
        df["_cluster"] = (gap > 2).groupby(
            [df["competition"], df["home_canon"], df["away_canon"]], sort=False
        ).cumsum()
        best = df.groupby(
            ["competition", "home_canon", "away_canon", "_cluster"], sort=False
        )["_rank"].transform("min")
        df = df[df["_rank"] == best]
        # A cluster may still hold several rows from its best source
        # (e.g. two-legged knockout ties): keep only distinct days.
        df = df.drop_duplicates(
            subset=["competition", "_day", "home_canon", "away_canon"], keep="first"
        )

        df = df.sort_values("date").reset_index(drop=True)
        return df.drop(columns=["_day", "_rank", "_ord", "_cluster"])

    # ------------------------------------------------------------------
    def _build_players(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "fifa_data.csv", low_memory=False)
        players = df.copy()
        players["name_norm"] = players["Name"].map(
            lambda n: strip_accents(str(n)).lower().strip()
        )
        players["club_canon"] = players["Club"].map(
            lambda c: normalize_team(c) if pd.notna(c) else ""
        )
        return players

    # ------------------------------------------------------------------
    def info(self) -> dict:
        """Row counts per source file / competition (data coverage check)."""
        per_source = (
            self.matches.groupby("source").size().sort_index().to_dict()
        )
        per_competition = (
            self.matches.groupby("competition").size().sort_index().to_dict()
        )
        seasons = self.matches["season"].dropna()
        return {
            "data_dir": str(self.data_dir),
            "total_matches": int(len(self.matches)),
            "matches_by_source": {k: int(v) for k, v in per_source.items()},
            "matches_by_competition": {k: int(v) for k, v in per_competition.items()},
            "total_players": int(len(self.players)),
            "season_range": [int(seasons.min()), int(seasons.max())]
            if len(seasons)
            else None,
        }


_DEFAULT: Dataset | None = None
_LOCK = threading.Lock()


def get_dataset(data_dir: str | Path | None = None) -> Dataset:
    """Return a cached process-wide Dataset (loads CSVs only once)."""
    global _DEFAULT
    if data_dir is not None:
        return Dataset(data_dir)
    if _DEFAULT is None:
        with _LOCK:
            if _DEFAULT is None:
                _DEFAULT = Dataset()
    return _DEFAULT
