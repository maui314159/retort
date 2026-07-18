"""
brazilian_soccer_mcp.data_loader
================================

Loads the six bundled Kaggle CSV files into normalised :class:`Match` and
:class:`Player` records.

Context
-------
Each source file has its own schema, date format, goal-column type (int vs
float vs str), and team-name convention. This module hides all of that behind
one function — :func:`load_datasets` — which returns a :class:`LoadedData`
bundle ready to be handed to the knowledge graph.

Source files (all under ``data/kaggle/``)
-----------------------------------------
* ``Brasileirao_Matches.csv``      -> competition "Brasileirão Serie A" (2012-2022)
* ``novo_campeonato_brasileiro.csv`` -> "Brasileirão Serie A" (2003-2011 only;
  seasons 2012-2019 are dropped because they overlap with Brasileirao_Matches
  and would double-count matches in standings)
* ``Brazilian_Cup_Matches.csv``    -> "Copa do Brasil"
* ``Libertadores_Matches.csv``     -> "Copa Libertadores"
* ``BR-Football-Dataset.csv``      -> per-tournament (Serie A/B/C, Copa do Brasil)
* ``fifa_data.csv``                -> player records

Date handling
-------------
* ISO datetime ("2012-05-19 18:30:00") and ISO date ("2023-09-24") are parsed
  by ``pandas.to_datetime``.
* Brazilian-format dates ("29/03/2003") in the novo file are parsed with the
  explicit ``%d/%m/%Y`` format to avoid US-style month/day ambiguity.

All files are read as UTF-8 (the FIFA file has a BOM, handled with
``utf-8-sig``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

from .models import Match, Player
from .normalize import TeamNormalizer

# ---------------------------------------------------------------------------
# Competition canonicalisation
# ---------------------------------------------------------------------------

BR_FOOTBALL_TOURNAMENT_MAP: dict[str, str] = {
    "Serie A": "Brasileirão Serie A",
    "Serie B": "Brasileirão Serie B",
    "Serie C": "Brasileirão Serie C",
    "Copa do Brasil": "Copa do Brasil",
}

COMPETITION_BRASILEIRAO_A = "Brasileirão Serie A"
COMPETITION_COPA_DO_BRASIL = "Copa do Brasil"
COMPETITION_LIBERTADORES = "Copa Libertadores"


# ---------------------------------------------------------------------------
# Default data location
# ---------------------------------------------------------------------------


def default_data_dir() -> Path:
    """Locate the ``data/kaggle`` directory.

    Resolution order:
      1. ``$BRA_SOCCER_DATA_DIR`` environment variable
      2. ``<repo_root>/data/kaggle`` (repo root = two parents up from this file)
    """
    env = os.environ.get("BRA_SOCCER_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "kaggle"


@dataclass
class LoadedData:
    """Bundle of loaded records plus the shared team normaliser."""

    matches: list[Match] = field(default_factory=list)
    players: list[Player] = field(default_factory=list)
    normalizer: Optional[TeamNormalizer] = None
    data_dir: Path = field(default_factory=lambda: default_data_dir())

    @property
    def teams_index(self) -> dict[str, set[str]]:
        """Canonical team name -> set of source competitions (built lazily)."""
        idx: dict[str, set[str]] = {}
        for m in self.matches:
            idx.setdefault(m.home_team, set()).add(m.competition)
            idx.setdefault(m.away_team, set()).add(m.competition)
        return idx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_int(value) -> Optional[int]:
    """Coerce a CSV cell to int; return ``None`` when missing/blank."""
    if value is None:
        return None
    if isinstance(value, float):
        if pd.isna(value):
            return None
        return int(value)
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(f):
        return None
    return f


def _safe_str(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() == "nan":
        return ""
    return s


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV as UTF-8 (BOM-tolerant for the FIFA file)."""
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=True)


def _collect_raw_team_names(data_dir: Path) -> list[str]:
    """First pass: gather every raw team string across the match files.

    The FIFA ``Club`` column is also included so the normaliser can link
    FIFA full names ("Atlético Mineiro") to match-data short forms.
    """
    names: list[str] = []

    def add(col) -> None:
        for v in col.dropna().unique():
            names.append(str(v))

    bra = data_dir / "Brasileirao_Matches.csv"
    if bra.exists():
        df = _read_csv(bra)
        add(df["home_team"]); add(df["away_team"])
    cup = data_dir / "Brazilian_Cup_Matches.csv"
    if cup.exists():
        df = _read_csv(cup)
        add(df["home_team"]); add(df["away_team"])
    lib = data_dir / "Libertadores_Matches.csv"
    if lib.exists():
        df = _read_csv(lib)
        add(df["home_team"]); add(df["away_team"])
    brf = data_dir / "BR-Football-Dataset.csv"
    if brf.exists():
        df = _read_csv(brf)
        add(df["home"]); add(df["away"])
    novo = data_dir / "novo_campeonato_brasileiro.csv"
    if novo.exists():
        df = _read_csv(novo)
        add(df["Equipe_mandante"]); add(df["Equipe_visitante"])
    fifa = data_dir / "fifa_data.csv"
    if fifa.exists():
        df = _read_csv(fifa)
        add(df["Club"])
    return names


def _load_brasileirao(df: pd.DataFrame, normalizer: TeamNormalizer, source: str) -> list[Match]:
    matches: list[Match] = []
    for i, row in df.iterrows():
        dt = pd.to_datetime(row["datetime"], errors="coerce")
        matches.append(
            Match(
                id=f"brasileirao:{i}",
                competition=COMPETITION_BRASILEIRAO_A,
                season=_to_int(row.get("season")),
                date=dt.date() if pd.notna(dt) else None,
                datetime=dt.to_pydatetime() if pd.notna(dt) else None,
                home_team=normalizer.canonical(row["home_team"]),
                away_team=normalizer.canonical(row["away_team"]),
                home_goals=_to_int(row.get("home_goal")),
                away_goals=_to_int(row.get("away_goal")),
                round=str(row.get("round")) if pd.notna(row.get("round")) else None,
                source_file=source,
            )
        )
    return matches


def _load_novo(df: pd.DataFrame, normalizer: TeamNormalizer, source: str) -> list[Match]:
    """Historical Brasileirão 2003-2019.

    Only seasons < 2012 are kept: seasons 2012-2019 overlap with
    Brasileirao_Matches.csv and keeping both would double-count matches and
    corrupt standings. This gives a single clean Brasileirão Serie A series
    spanning 2003-2022.
    """
    matches: list[Match] = []
    for i, row in df.iterrows():
        season = _to_int(row.get("Ano"))
        if season is not None and season >= 2012:
            continue
        dt = pd.to_datetime(row["Data"], format="%d/%m/%Y", errors="coerce")
        matches.append(
            Match(
                id=f"novo:{row.get('ID', i)}",
                competition=COMPETITION_BRASILEIRAO_A,
                season=season,
                date=dt.date() if pd.notna(dt) else None,
                datetime=dt.to_pydatetime() if pd.notna(dt) else None,
                home_team=normalizer.canonical(row["Equipe_mandante"]),
                away_team=normalizer.canonical(row["Equipe_visitante"]),
                home_goals=_to_int(row.get("Gols_mandante")),
                away_goals=_to_int(row.get("Gols_visitante")),
                round=str(row.get("Rodada")) if pd.notna(row.get("Rodada")) else None,
                arena=_safe_str(row.get("Arena")) or None,
                source_file=source,
            )
        )
    return matches


def _load_cup(df: pd.DataFrame, normalizer: TeamNormalizer, source: str) -> list[Match]:
    matches: list[Match] = []
    for i, row in df.iterrows():
        dt = pd.to_datetime(row["datetime"], errors="coerce")
        matches.append(
            Match(
                id=f"cup:{i}",
                competition=COMPETITION_COPA_DO_BRASIL,
                season=_to_int(row.get("season")),
                date=dt.date() if pd.notna(dt) else None,
                datetime=dt.to_pydatetime() if pd.notna(dt) else None,
                home_team=normalizer.canonical(row["home_team"]),
                away_team=normalizer.canonical(row["away_team"]),
                home_goals=_to_int(row.get("home_goal")),
                away_goals=_to_int(row.get("away_goal")),
                round=_safe_str(row.get("round")) or None,
                source_file=source,
            )
        )
    return matches


def _load_libertadores(df: pd.DataFrame, normalizer: TeamNormalizer, source: str) -> list[Match]:
    matches: list[Match] = []
    for i, row in df.iterrows():
        dt = pd.to_datetime(row["datetime"], errors="coerce")
        matches.append(
            Match(
                id=f"libertadores:{i}",
                competition=COMPETITION_LIBERTADORES,
                season=_to_int(row.get("season")),
                date=dt.date() if pd.notna(dt) else None,
                datetime=dt.to_pydatetime() if pd.notna(dt) else None,
                home_team=normalizer.canonical(row["home_team"]),
                away_team=normalizer.canonical(row["away_team"]),
                home_goals=_to_int(row.get("home_goal")),
                away_goals=_to_int(row.get("away_goal")),
                stage=_safe_str(row.get("stage")) or None,
                round=_safe_str(row.get("stage")) or None,
                source_file=source,
            )
        )
    return matches


def _load_br_football(
    df: pd.DataFrame,
    normalizer: TeamNormalizer,
    source: str,
    existing_pairs: set[tuple[str, int]],
) -> list[Match]:
    """Load BR-Football matches, skipping (competition, season) pairs already
    provided by a primary source.

    BR-Football overlaps Brasileirao_Matches (Serie A, 2014-2022) and
    Brazilian_Cup_Matches (Copa do Brasil, 2014-2021). Keeping both would
    double-count matches and corrupt standings, so those overlapping seasons
    are dropped here. BR-Football still contributes its unique value: full
    Serie B / Serie C coverage, extended stats (corners/shots/attacks), and
    seasons beyond the primary files (e.g. Serie A 2023).
    """
    matches: list[Match] = []
    for i, row in df.iterrows():
        raw_tourn = _safe_str(row.get("tournament"))
        competition = BR_FOOTBALL_TOURNAMENT_MAP.get(raw_tourn, raw_tourn or "Unknown")
        dt = pd.to_datetime(row.get("date"), errors="coerce")
        season = _to_int(row.get("season"))
        if season is None and pd.notna(dt):
            season = dt.year
        if season is not None and (competition, season) in existing_pairs:
            continue
        matches.append(
            Match(
                id=f"brfootball:{i}",
                competition=competition,
                season=season,
                date=dt.date() if pd.notna(dt) else None,
                datetime=dt.to_pydatetime() if pd.notna(dt) else None,
                home_team=normalizer.canonical(row["home"]),
                away_team=normalizer.canonical(row["away"]),
                home_goals=_to_int(row.get("home_goal")),
                away_goals=_to_int(row.get("away_goal")),
                home_corners=_to_float(row.get("home_corner")),
                away_corners=_to_float(row.get("away_corner")),
                home_shots=_to_float(row.get("home_shots")),
                away_shots=_to_float(row.get("away_shots")),
                home_attacks=_to_float(row.get("home_attack")),
                away_attacks=_to_float(row.get("away_attack")),
                source_file=source,
            )
        )
    return matches


def _load_fifa(df: pd.DataFrame) -> list[Player]:
    players: list[Player] = []
    # The first column is an unnamed index ("Unnamed: 0"); ignore it.
    for _, row in df.iterrows():
        players.append(
            Player(
                id=_to_int(row.get("ID")) or 0,
                name=_safe_str(row.get("Name")),
                age=_to_int(row.get("Age")),
                nationality=_safe_str(row.get("Nationality")),
                overall=_to_int(row.get("Overall")),
                potential=_to_int(row.get("Potential")),
                club=_safe_str(row.get("Club")),
                position=_safe_str(row.get("Position")),
                jersey_number=_to_int(row.get("Jersey Number")),
                height=_safe_str(row.get("Height")) or None,
                weight=_safe_str(row.get("Weight")) or None,
                preferred_foot=_safe_str(row.get("Preferred Foot")) or None,
                crossing=_to_int(row.get("Crossing")),
                finishing=_to_int(row.get("Finishing")),
                dribbling=_to_int(row.get("Dribbling")),
                short_passing=_to_int(row.get("ShortPassing")),
                heading_accuracy=_to_int(row.get("HeadingAccuracy")),
                shot_power=_to_int(row.get("ShotPower")),
                value=_safe_str(row.get("Value")) or None,
                wage=_safe_str(row.get("Wage")) or None,
            )
        )
    return players


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def load_datasets(data_dir: Optional[Path] = None) -> LoadedData:
    """Load all six CSV files into normalised records.

    Args:
        data_dir: directory containing the Kaggle CSVs. Defaults to
            :func:`default_data_dir`.

    Returns:
        A :class:`LoadedData` bundle with ``matches``, ``players`` and a
        fitted :class:`TeamNormalizer`.
    """
    data_dir = Path(data_dir) if data_dir else default_data_dir()

    # Pass 1: fit the team normaliser on the full universe of raw names.
    normalizer = TeamNormalizer(_collect_raw_team_names(data_dir))

    matches: list[Match] = []

    bra = data_dir / "Brasileirao_Matches.csv"
    if bra.exists():
        matches += _load_brasileirao(_read_csv(bra), normalizer, "Brasileirao_Matches.csv")

    novo = data_dir / "novo_campeonato_brasileiro.csv"
    if novo.exists():
        matches += _load_novo(_read_csv(novo), normalizer, "novo_campeonato_brasileiro.csv")

    cup = data_dir / "Brazilian_Cup_Matches.csv"
    if cup.exists():
        matches += _load_cup(_read_csv(cup), normalizer, "Brazilian_Cup_Matches.csv")

    lib = data_dir / "Libertadores_Matches.csv"
    if lib.exists():
        matches += _load_libertadores(_read_csv(lib), normalizer, "Libertadores_Matches.csv")

    # Build the set of (competition, season) pairs already covered by primary
    # sources so BR-Football can skip overlapping seasons (see _load_br_football).
    existing_pairs: set[tuple[str, int]] = {
        (m.competition, m.season) for m in matches if m.season is not None
    }

    brf = data_dir / "BR-Football-Dataset.csv"
    if brf.exists():
        matches += _load_br_football(
            _read_csv(brf), normalizer, "BR-Football-Dataset.csv", existing_pairs
        )

    players: list[Player] = []
    fifa = data_dir / "fifa_data.csv"
    if fifa.exists():
        players = _load_fifa(_read_csv(fifa))

    return LoadedData(matches=matches, players=players, normalizer=normalizer, data_dir=data_dir)
