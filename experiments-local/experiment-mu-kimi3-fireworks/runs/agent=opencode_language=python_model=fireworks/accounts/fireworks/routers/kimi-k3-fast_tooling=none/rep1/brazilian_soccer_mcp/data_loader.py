"""Load the six Kaggle CSV files into unified, queryable DataFrames.

Why: every file has its own schema, date format and team-naming
convention; the query layer needs one canonical match table plus one
player table.

What:
    - ``load_matches(data_dir)``  -> single DataFrame with columns
      date, home_team, away_team, home_key, away_key, home_goals,
      away_goals, competition, season, round, arena, source
      (deduplicated across overlapping files).
    - ``load_players(data_dir)``  -> FIFA player DataFrame with
      normalized club keys and a position_group column.
    - ``SoccerDataset``           -- convenience holder + team registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .normalization import TeamRegistry, parse_date_series, parse_team, team_base, team_key

DATA_SUBDIR = Path("data") / "kaggle"

BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
COPA_DO_BRASIL_FILE = "Brazilian_Cup_Matches.csv"
LIBERTADORES_FILE = "Libertadores_Matches.csv"
EXTENDED_FILE = "BR-Football-Dataset.csv"
HISTORICO_FILE = "novo_campeonato_brasileiro.csv"
FIFA_FILE = "fifa_data.csv"

# Canonical competition names used across the unified match table.
BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_EXTENDED_TOURNAMENTS = {
    "serie a": BRASILEIRAO_A,
    "serie b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
}

# Lower number = preferred source when the same fixture appears in
# several files (the ricardomattos05 files have the cleanest metadata).
_SOURCE_PRIORITY = {
    BRASILEIRAO_FILE: 0,
    COPA_DO_BRASIL_FILE: 0,
    LIBERTADORES_FILE: 0,
    HISTORICO_FILE: 1,
    EXTENDED_FILE: 2,
}

MATCH_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_base",
    "home_state",
    "away_base",
    "away_state",
    "home_goals",
    "away_goals",
    "competition",
    "season",
    "round",
    "arena",
    "source",
]

# Position group mapping for the FIFA player data.
POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"LB", "RB", "CB", "LCB", "RCB", "LWB", "RWB"},
    "midfielder": {"LM", "RM", "CM", "LCM", "RCM", "CDM", "CAM", "LDM", "RDM", "LAM", "RAM"},
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
}

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
    "Height",
    "Weight",
    "Value",
    "Wage",
    "Preferred Foot",
    "Finishing",
    "Dribbling",
    "ShortPassing",
    "BallControl",
    "SprintSpeed",
    "Strength",
]


def _read_csv(data_dir: Path, filename: str, **kwargs) -> pd.DataFrame:
    path = data_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Required dataset not found: {path}")
    return pd.read_csv(path, encoding="utf-8", **kwargs)


def _goals(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def _register_teams(df: pd.DataFrame, registry: TeamRegistry) -> pd.DataFrame:
    """Parse team names into base/state parts.

    Canonical keys are assigned later (``_assign_keys``) once every file
    has been seen, so that a name spelled without a state in one file
    ("4 de Julho EC") can adopt the state used for the same base in
    another file ("4 de Julho - PI").
    """
    df = df.copy()
    home = df["home_team"].map(parse_team)
    away = df["away_team"].map(parse_team)
    df["home_base"] = home.map(lambda t: t[0])
    df["home_state"] = home.map(lambda t: t[1])
    df["away_base"] = away.map(lambda t: t[0])
    df["away_state"] = away.map(lambda t: t[1])
    return df


def _assign_keys(matches: pd.DataFrame, registry: TeamRegistry) -> pd.DataFrame:
    """Assign canonical home/away keys and register display names.

    A state-less base adopts a state only when every occurrence of that
    base in the whole corpus agrees on exactly one state (so "América"
    stays ambiguous between MG and RN, but "4 de Julho" becomes PI).
    """
    states_by_base: dict[str, set[str]] = {}
    for base_col, state_col in (("home_base", "home_state"), ("away_base", "away_state")):
        for base, state in zip(matches[base_col], matches[state_col]):
            if base and state and not pd.isna(state):
                states_by_base.setdefault(base, set()).add(state)

    def finalize(base: str, state: object) -> str:
        if not base:
            return ""
        if state and not pd.isna(state):
            return f"{base} {state}"
        known = states_by_base.get(base)
        if known and len(known) == 1:
            return f"{base} {next(iter(known))}"
        return base

    matches = matches.copy()
    matches["home_key"] = [
        finalize(b, s) for b, s in zip(matches["home_base"], matches["home_state"])
    ]
    matches["away_key"] = [
        finalize(b, s) for b, s in zip(matches["away_base"], matches["away_state"])
    ]
    for raw, key, base in zip(matches["home_team"], matches["home_key"], matches["home_base"]):
        registry.register_key(raw, key, base)
    for raw, key, base in zip(matches["away_team"], matches["away_key"], matches["away_base"]):
        registry.register_key(raw, key, base)
    return matches.drop(columns=["home_state", "away_state"])


def _empty_frame(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[MATCH_COLUMNS]


def _load_brasileirao(data_dir: Path, registry: TeamRegistry) -> pd.DataFrame:
    raw = _read_csv(data_dir, BRASILEIRAO_FILE)
    df = pd.DataFrame(
        {
            "date": parse_date_series(raw["datetime"]),
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": _goals(raw["home_goal"]),
            "away_goals": _goals(raw["away_goal"]),
            "competition": BRASILEIRAO_A,
            "season": pd.to_numeric(raw["season"], errors="coerce").astype("Int64"),
            "round": raw["round"].astype("string"),
            "arena": pd.NA,
            "source": BRASILEIRAO_FILE,
        }
    )
    return _register_teams(df, registry)


def _load_copa_do_brasil(data_dir: Path, registry: TeamRegistry) -> pd.DataFrame:
    raw = _read_csv(data_dir, COPA_DO_BRASIL_FILE)
    df = pd.DataFrame(
        {
            "date": parse_date_series(raw["datetime"]),
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": _goals(raw["home_goal"]),
            "away_goals": _goals(raw["away_goal"]),
            "competition": COPA_DO_BRASIL,
            "season": pd.to_numeric(raw["season"], errors="coerce").astype("Int64"),
            "round": raw["round"].astype("string"),
            "arena": pd.NA,
            "source": COPA_DO_BRASIL_FILE,
        }
    )
    return _register_teams(df, registry)


def _load_libertadores(data_dir: Path, registry: TeamRegistry) -> pd.DataFrame:
    raw = _read_csv(data_dir, LIBERTADORES_FILE)
    df = pd.DataFrame(
        {
            "date": parse_date_series(raw["datetime"]),
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "home_goals": _goals(raw["home_goal"]),
            "away_goals": _goals(raw["away_goal"]),
            "competition": LIBERTADORES,
            "season": pd.to_numeric(raw["season"], errors="coerce").astype("Int64"),
            "round": raw["stage"].astype("string"),
            "arena": pd.NA,
            "source": LIBERTADORES_FILE,
        }
    )
    return _register_teams(df, registry)


def _load_extended(data_dir: Path, registry: TeamRegistry) -> pd.DataFrame:
    raw = _read_csv(data_dir, EXTENDED_FILE)
    competition = raw["tournament"].map(
        lambda t: _EXTENDED_TOURNAMENTS.get(str(t).strip().lower(), str(t).strip())
    )
    df = pd.DataFrame(
        {
            "date": parse_date_series(raw["date"]),
            "home_team": raw["home"],
            "away_team": raw["away"],
            "home_goals": _goals(raw["home_goal"]),
            "away_goals": _goals(raw["away_goal"]),
            "competition": competition,
            "season": pd.to_datetime(raw["date"], errors="coerce").dt.year.astype("Int64"),
            "round": pd.NA,
            "arena": pd.NA,
            "source": EXTENDED_FILE,
        }
    )
    return _register_teams(df, registry)


def _load_historico(data_dir: Path, registry: TeamRegistry) -> pd.DataFrame:
    raw = _read_csv(data_dir, HISTORICO_FILE)
    df = pd.DataFrame(
        {
            "date": parse_date_series(raw["Data"], dayfirst=True),
            "home_team": raw["Equipe_mandante"],
            "away_team": raw["Equipe_visitante"],
            "home_goals": _goals(raw["Gols_mandante"]),
            "away_goals": _goals(raw["Gols_visitante"]),
            "competition": BRASILEIRAO_A,
            "season": pd.to_numeric(raw["Ano"], errors="coerce").astype("Int64"),
            "round": raw["Rodada"].astype("string"),
            "arena": raw["Arena"],
            "source": HISTORICO_FILE,
        }
    )
    return _register_teams(df, registry)


def _fix_extended_seasons(matches: pd.DataFrame) -> pd.DataFrame:
    """Correct derived seasons for rows from the extended file.

    The extended file has no season column, so seasons are derived from
    the calendar year — but Brazilian league seasons never start before
    April (Jan-Mar league games are the previous season's tail, e.g. the
    COVID-delayed 2020 season ending in Feb 2021), and cup games in
    Jan-Mar 2021 can belong to the 2020 cup.  League rows get the
    month-based rule; cup rows adopt the authoritative cup file's season
    when the same fixture is found there.
    """
    matches = matches.copy()
    is_ext = matches["source"] == EXTENDED_FILE
    jan_mar = matches["date"].dt.month <= 3
    league = matches["competition"].isin([BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C])
    mask = is_ext & league & jan_mar
    matches.loc[mask, "season"] = (matches.loc[mask, "season"] - 1).astype("Int64")

    cup_rows = matches[matches["source"] == COPA_DO_BRASIL_FILE]
    lookup: dict[tuple, list[tuple[pd.Timestamp, int]]] = {}
    for r in cup_rows.itertuples():
        key = (r.home_key, r.away_key, int(r.home_goals), int(r.away_goals))
        lookup.setdefault(key, []).append((r.date, int(r.season)))
    cup_mask = is_ext & (matches["competition"] == COPA_DO_BRASIL) & jan_mar
    for r in matches[cup_mask].itertuples():
        key = (r.home_key, r.away_key, int(r.home_goals), int(r.away_goals))
        for date, season in lookup.get(key, []):
            if abs((r.date - date).days) <= 5:
                matches.loc[r.Index, "season"] = season
                break

    # Drop bogus ext league fixtures: when the authoritative files cover
    # a league season, a fixture where neither club plays in it is noise
    # (the ext file mislabels a few regional games as league matches).
    coverage: dict[tuple[str, int], set[str]] = {}
    non_ext = matches[~is_ext]
    for (comp, season), grp in non_ext.groupby(["competition", "season"]):
        coverage[(comp, season)] = set(grp["home_key"]) | set(grp["away_key"])
    drop_idx = []
    for r in matches[is_ext & league].itertuples():
        teams = coverage.get((r.competition, r.season))
        if teams and r.home_key not in teams and r.away_key not in teams:
            drop_idx.append(r.Index)
    return matches.drop(index=drop_idx)


def load_matches(data_dir: str | Path | None = None, *, dedupe: bool = True) -> pd.DataFrame:
    """Load all five match CSVs into one deduplicated match table.

    Rows without a final score (unplayed / missing data) are dropped.
    When files overlap (e.g. Série A 2012-2019 appears in three files),
    the first occurrence by source priority wins.
    """
    data_dir = _resolve_data_dir(data_dir)
    registry = TeamRegistry()
    loaders = (
        _load_brasileirao,
        _load_copa_do_brasil,
        _load_libertadores,
        _load_historico,
        _load_extended,
    )
    frames = [_empty_frame(loader(data_dir, registry), MATCH_COLUMNS) for loader in loaders]
    matches = pd.concat(frames, ignore_index=True)
    matches = matches.dropna(subset=["date", "home_goals", "away_goals"])
    matches["season"] = matches["season"].fillna(matches["date"].dt.year).astype("Int64")
    matches = _assign_keys(matches, registry)
    matches = matches[matches["home_key"] != ""]
    matches = matches[matches["away_key"] != ""]
    matches = _fix_extended_seasons(matches)
    matches = matches.sort_values("date", kind="stable").reset_index(drop=True)
    if dedupe:
        # Preferred source wins every pass (ordered by priority, then date).
        matches["_prio"] = matches["source"].map(_SOURCE_PRIORITY).fillna(9)
        matches = matches.sort_values(["_prio", "date"], kind="stable")
        # Pass 1: same-day duplicates across overlapping files.
        matches["_day"] = matches["date"].dt.date
        matches = matches.drop_duplicates(
            subset=["_day", "home_key", "away_key", "home_goals", "away_goals"],
            keep="first",
        ).drop(columns=["_day"])
        # Pass 2: the same pairing (same direction) with the same score in
        # the same season+competition is one match, even when files record
        # it on adjacent days (kick-off past midnight, data-entry drift).
        matches = matches.drop_duplicates(
            subset=["competition", "season", "home_key", "away_key", "home_goals", "away_goals"],
            keep="first",
        )
        # Pass 3: date-proximity safety net for adjacent-day recordings
        # of the same fixture (conflicting scores or season labels across
        # files).  A club never plays the same opponent in the same
        # competition, same direction, twice within 3 days.
        kept_dates: dict[tuple, list[pd.Timestamp]] = {}
        keep_mask = []
        for key, day in zip(
            zip(matches["competition"], matches["home_key"], matches["away_key"]),
            matches["date"],
        ):
            dates = kept_dates.setdefault(key, [])
            if any(abs((day - kept).days) <= 3 for kept in dates):
                keep_mask.append(False)
            else:
                dates.append(day)
                keep_mask.append(True)
        matches = matches[keep_mask].drop(columns=["_prio"])
        matches = matches.sort_values("date", kind="stable").reset_index(drop=True)
    return matches


def load_players(data_dir: str | Path | None = None) -> pd.DataFrame:
    """Load the FIFA player database with normalized club keys."""
    data_dir = _resolve_data_dir(data_dir)
    raw = _read_csv(data_dir, FIFA_FILE, low_memory=False)
    cols = [c for c in _PLAYER_COLUMNS if c in raw.columns]
    players = raw[cols].copy()
    players["Overall"] = pd.to_numeric(players["Overall"], errors="coerce")
    players["Potential"] = pd.to_numeric(players["Potential"], errors="coerce")
    players["Age"] = pd.to_numeric(players["Age"], errors="coerce")
    players["club_key"] = players["Club"].map(
        lambda c: team_key(c) if pd.notna(c) else ""
    )
    players["club_base"] = players["Club"].map(
        lambda c: team_base(c) if pd.notna(c) else ""
    )
    players["name_key"] = players["Name"].map(lambda n: str(n).strip().lower())
    players["position_group"] = players["Position"].map(_position_group)
    return players


def _position_group(position: object) -> str | None:
    if position is None or (isinstance(position, float) and pd.isna(position)):
        return None
    pos = str(position).strip().upper()
    for group, positions in POSITION_GROUPS.items():
        if pos in positions:
            return group
    return None


def _resolve_data_dir(data_dir: str | Path | None) -> Path:
    if data_dir is not None:
        return Path(data_dir)
    # Default: <repo root>/data/kaggle (two levels above this file).
    return Path(__file__).resolve().parent.parent / DATA_SUBDIR


@dataclass
class SoccerDataset:
    """Matches + players + team registry, loaded once and reused."""

    data_dir: str | Path | None = None
    matches: pd.DataFrame = field(init=False)
    players: pd.DataFrame = field(init=False)
    registry: TeamRegistry = field(init=False)

    def __post_init__(self) -> None:
        self.matches = load_matches(self.data_dir)
        self.players = load_players(self.data_dir)
        self.registry = TeamRegistry()
        for side in ("home", "away"):
            seen: set[tuple[str, str]] = set()
            for raw, key, base in zip(
                self.matches[f"{side}_team"],
                self.matches[f"{side}_key"],
                self.matches[f"{side}_base"],
            ):
                if (raw, key) not in seen:
                    self.registry.register_key(raw, key, base)
                    seen.add((raw, key))
        for club in self.players["Club"].dropna().unique():
            self.registry.register(club)

    def summary(self) -> dict[str, object]:
        return {
            "matches": int(len(self.matches)),
            "players": int(len(self.players)),
            "teams": len(self.registry.keys()),
            "competitions": sorted(self.matches["competition"].unique().tolist()),
            "seasons": [
                int(s) for s in sorted(self.matches["season"].dropna().unique().tolist())
            ],
        }


@lru_cache(maxsize=1)
def get_dataset(data_dir: str | None = None) -> SoccerDataset:
    """Process-wide cached dataset (loads the CSVs only once)."""
    return SoccerDataset(data_dir)
