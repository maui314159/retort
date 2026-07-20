"""Dataset loading.

Loads the six Kaggle CSV files bundled under ``data/kaggle/`` into two
in-memory frames:

* ``matches`` – every match from all five match files unified into a single
  schema, with team names normalized and cross-file duplicates removed
  (the Série A files overlap heavily for 2012-2019).
* ``players`` – the FIFA player database.

Loading a couple of hundred thousand cells takes well under a second, so
everything is kept in memory and cached in :func:`get_kb`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .normalization import clean_team_name, team_key

# Canonical competition labels used across the unified match frame.
BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

MATCH_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_key",
    "away_key",
    "home_goals",
    "away_goals",
    "competition",
    "season",
    "stage",
    "source",
    "home_corners",
    "away_corners",
    "home_shots",
    "away_shots",
]

_PLAYER_COLUMNS = [
    "ID",
    "Name",
    "Age",
    "Nationality",
    "Overall",
    "Potential",
    "Club",
    "Position",
    "Jersey Number",
]


@dataclass(frozen=True)
class KnowledgeBase:
    """In-memory view over all datasets."""

    matches: pd.DataFrame
    players: pd.DataFrame
    load_report: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def competitions(self) -> list[str]:
        return sorted(self.matches["competition"].unique().tolist())


def default_data_dir() -> Path:
    """Locate ``data/kaggle`` (env override ``BRAZILIAN_SOCCER_DATA``)."""
    env = os.environ.get("BRAZILIAN_SOCCER_DATA")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "kaggle"


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Required dataset not found: {path}. "
            "Set BRAZILIAN_SOCCER_DATA to the directory containing the CSV files."
        )
    return path


def _standardize(
    df: pd.DataFrame,
    *,
    competition: str,
    source: str,
    report: dict[str, int],
) -> pd.DataFrame:
    """Normalize raw columns into the unified match schema."""
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df["date"], errors="coerce").dt.normalize(),
            "home_team": df["home_team"].map(clean_team_name),
            "away_team": df["away_team"].map(clean_team_name),
            "home_key": df["home_team"].map(team_key),
            "away_key": df["away_team"].map(team_key),
            "home_goals": pd.to_numeric(df["home_goals"], errors="coerce").astype("Int64"),
            "away_goals": pd.to_numeric(df["away_goals"], errors="coerce").astype("Int64"),
            "competition": competition,
            "season": pd.to_numeric(df["season"], errors="coerce").astype("Int64"),
            "stage": df["stage"].astype("string").fillna(""),
            "source": source,
        }
    )
    report["rows_read"] = int(len(out))
    usable = out.dropna(subset=["date", "home_goals", "away_goals"])
    usable = usable[(usable["home_key"] != "") & (usable["away_key"] != "")].copy()
    report["rows_usable"] = int(len(usable))
    report["rows_dropped"] = report["rows_read"] - report["rows_usable"]
    for col in ("home_corners", "away_corners", "home_shots", "away_shots"):
        usable[col] = pd.NA
    # NOTE: original index is preserved on purpose — _load_br_football maps
    # extra columns back through it, and load_kb re-indexes after concat.
    return usable


def _load_brasileirao(path: Path, report: dict[str, int]) -> pd.DataFrame:
    raw = pd.read_csv(_require(path))
    df = pd.DataFrame(
        {
            "date": raw["datetime"],
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": raw["home_goal"],
            "away_goals": raw["away_goal"],
            "season": raw["season"],
            "stage": "Round " + raw["round"].astype("string"),
        }
    )
    return _standardize(df, competition=BRASILEIRAO_A, source=path.name, report=report)


def _load_cup(path: Path, report: dict[str, int]) -> pd.DataFrame:
    raw = pd.read_csv(_require(path))
    df = pd.DataFrame(
        {
            "date": raw["datetime"],
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": raw["home_goal"],
            "away_goals": raw["away_goal"],
            "season": raw["season"],
            "stage": "Round " + raw["round"].astype("string"),
        }
    )
    return _standardize(df, competition=COPA_DO_BRASIL, source=path.name, report=report)


def _load_libertadores(path: Path, report: dict[str, int]) -> pd.DataFrame:
    raw = pd.read_csv(_require(path))
    df = pd.DataFrame(
        {
            "date": raw["datetime"],
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": raw["home_goal"],
            "away_goals": raw["away_goal"],
            "season": raw["season"],
            "stage": raw["stage"].astype("string").str.title(),
        }
    )
    return _standardize(df, competition=LIBERTADORES, source=path.name, report=report)


_BR_TOURNAMENT_MAP = {
    "Serie A": BRASILEIRAO_A,
    "Serie B": BRASILEIRAO_B,
    "Serie C": BRASILEIRAO_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


def _load_br_football(path: Path, report: dict[str, int]) -> pd.DataFrame:
    raw = pd.read_csv(_require(path))
    raw = raw[raw["tournament"].isin(_BR_TOURNAMENT_MAP)]
    df = pd.DataFrame(
        {
            "date": raw["date"],
            "home_team": raw["home"],
            "away_team": raw["away"],
            "home_goals": raw["home_goal"],
            "away_goals": raw["away_goal"],
            # Tournament column is per-match; resolved after standardization.
            "season": pd.to_datetime(raw["date"], errors="coerce").dt.year,
            "stage": "",
        }
    )
    out = _standardize(df, competition="", source=path.name, report=report)
    out["competition"] = raw.loc[out.index, "tournament"].map(_BR_TOURNAMENT_MAP).to_numpy()
    for src, dst in (
        ("home_corner", "home_corners"),
        ("away_corner", "away_corners"),
        ("home_shots", "home_shots"),
        ("away_shots", "away_shots"),
    ):
        out[dst] = pd.to_numeric(raw.loc[out.index, src], errors="coerce")
    return out


def _load_novo(path: Path, report: dict[str, int]) -> pd.DataFrame:
    raw = pd.read_csv(_require(path))
    df = pd.DataFrame(
        {
            # Brazilian DD/MM/YYYY — must be parsed explicitly, otherwise
            # pandas assumes month-first for ambiguous days.
            "date": pd.to_datetime(raw["Data"], format="%d/%m/%Y", errors="coerce"),
            "home_team": raw["Equipe_mandante"],
            "away_team": raw["Equipe_visitante"],
            "home_goals": raw["Gols_mandante"],
            "away_goals": raw["Gols_visitante"],
            "season": raw["Ano"],
            "stage": "Round " + raw["Rodada"].astype("string"),
        }
    )
    return _standardize(df, competition=BRASILEIRAO_A, source=path.name, report=report)


def _load_players(path: Path, report: dict[str, int]) -> pd.DataFrame:
    raw = pd.read_csv(_require(path), low_memory=False)
    players = raw[[c for c in _PLAYER_COLUMNS if c in raw.columns]].copy()
    players["Overall"] = pd.to_numeric(players["Overall"], errors="coerce").astype("Int64")
    players["Potential"] = pd.to_numeric(players["Potential"], errors="coerce").astype("Int64")
    players["Age"] = pd.to_numeric(players["Age"], errors="coerce").astype("Int64")
    report["rows_read"] = int(len(players))
    report["rows_usable"] = int(players["Name"].notna().sum())
    report["rows_dropped"] = report["rows_read"] - report["rows_usable"]
    return players


def _most_common_display(matches: pd.DataFrame) -> dict[str, str]:
    """Pick the preferred display variant per team key.

    Accent-preserving variants (``Grêmio``, ``São Paulo``) are preferred over
    ASCII-fallback ones (``Gremio``), with frequency as the tie-breaker.
    """
    names = pd.concat(
        [
            matches[["home_key", "home_team"]].rename(
                columns={"home_key": "key", "home_team": "name"}
            ),
            matches[["away_key", "away_team"]].rename(
                columns={"away_key": "key", "away_team": "name"}
            ),
        ]
    )
    counts = names.groupby(["key", "name"]).size().reset_index(name="n")
    counts["accents"] = counts["name"].map(lambda s: sum(ord(c) > 127 for c in s))
    counts = counts.sort_values(["accents", "n"], ascending=False, kind="stable")
    best = counts.drop_duplicates("key")
    return dict(zip(best["key"], best["name"]))


def load_kb(data_dir: Path | str | None = None) -> KnowledgeBase:
    """Load all datasets from *data_dir* into a :class:`KnowledgeBase`."""
    root = Path(data_dir) if data_dir is not None else default_data_dir()
    report: dict[str, dict[str, int]] = {}

    loaders = [
        ("Brasileirao_Matches.csv", _load_brasileirao, 0),
        ("Brazilian_Cup_Matches.csv", _load_cup, 0),
        ("Libertadores_Matches.csv", _load_libertadores, 0),
        # BR-Football carries corners/shots, so it outranks the historical
        # file but not the dedicated competition files.
        ("BR-Football-Dataset.csv", _load_br_football, 1),
        ("novo_campeonato_brasileiro.csv", _load_novo, 2),
    ]

    frames: list[pd.DataFrame] = []
    for filename, loader, priority in loaders:
        file_report: dict[str, int] = {}
        frame = loader(root / filename, file_report)
        frame["_priority"] = priority
        file_report["duplicates_dropped"] = 0
        report[filename] = file_report
        frames.append(frame)

    matches = pd.concat(frames, ignore_index=True)
    before = len(matches)
    matches = matches.sort_values("_priority", kind="stable")
    # Pass 1: exact fixture duplicates across files (same date + teams).
    matches = matches.drop_duplicates(subset=["date", "home_key", "away_key"], keep="first")
    # Pass 2: same fixture recorded with slightly different dates across
    # files (the historical file is off by a day for ~10% of late-season
    # matches).  Within one competition+season a home/away pairing occurs at
    # most once, so this is safe.
    matches = (
        matches.drop_duplicates(
            subset=["competition", "season", "home_key", "away_key"], keep="first"
        )
        .drop(columns="_priority")
        .sort_values("date", kind="stable")
        .reset_index(drop=True)
    )
    for col in ("home_corners", "away_corners", "home_shots", "away_shots"):
        matches[col] = pd.to_numeric(matches[col], errors="coerce")
    duplicated = before - len(matches)
    report["*dedupe*"] = {
        "rows_read": int(before),
        "rows_usable": int(len(matches)),
        "rows_dropped": 0,
        "duplicates_dropped": int(duplicated),
    }

    display = _most_common_display(matches)
    from .normalization import canonical_display

    def _display(key: str, fallback: str) -> str:
        return canonical_display(key, display.get(key, fallback))

    matches["home_team"] = [
        _display(k, n) for k, n in zip(matches["home_key"], matches["home_team"])
    ]
    matches["away_team"] = [
        _display(k, n) for k, n in zip(matches["away_key"], matches["away_team"])
    ]

    player_report: dict[str, int] = {}
    players = _load_players(root / "fifa_data.csv", player_report)
    report["fifa_data.csv"] = player_report

    return KnowledgeBase(matches=matches, players=players, load_report=report)


@lru_cache(maxsize=1)
def get_kb(data_dir: str | None = None) -> KnowledgeBase:
    """Process-wide cached :class:`KnowledgeBase`."""
    return load_kb(data_dir)
