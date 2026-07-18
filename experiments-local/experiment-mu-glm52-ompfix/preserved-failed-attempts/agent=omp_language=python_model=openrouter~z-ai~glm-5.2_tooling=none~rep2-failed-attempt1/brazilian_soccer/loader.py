# brazilian_soccer.loader
# -----------------------------------------------------------------------------
# Context:
#   Loads the six bundled Kaggle CSVs from data/kaggle/ into one unified, deduplicated
#   match table plus a player table. Each source uses different column names, date
#   formats, goal dtypes (the Libertadores file stores goals as quoted strings) and
#   team-naming conventions; this module normalizes all of them onto the Match model.
#
#   Cross-source duplication is real and deliberate to handle:
#     * Brasileirao_Matches.csv (2012-2023) overlaps novo_campeonato_brasileiro.csv
#       (2003-2019) for 2012-2019, and overlaps BR-Football-Dataset "Serie A"
#       (2020-2023) for 2020-2023.
#     * Brazilian_Cup_Matches.csv overlaps BR-Football-Dataset "Copa do Brasil".
#   We dedupe on (home_key, away_key, date, home_goal, away_goal) so league tables
#   and head-to-head counts are never double counted. The row with the richest
#   stats (corners/shots) wins on collision.
#
# Public API:
#   DATA_DIR            - resolved path to data/kaggle/
#   load_matches()      - pandas.DataFrame of all matches (deduplicated)
#   load_players()      - pandas.DataFrame of FIFA players
#   get_data_summary()  - quick inventory dict (counts per source/competition)
# -----------------------------------------------------------------------------
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .models import COMPETITIONS, Match
from .normalize import normalize_team, team_key

# Resolve data/kaggle relative to this file so the package works regardless of
# the caller's working directory (tests, MCP server, CLI, ...).
_THIS_DIR = Path(__file__).resolve().parent
# repo root is two levels up: brazilian_soccer/ -> <root>
_REPO_ROOT = _THIS_DIR.parent
DATA_DIR = _REPO_ROOT / "data" / "kaggle"


def _to_int(value) -> int | None:
    """Coerce a goal/score value (int/float/str) to int, or None if not parseable."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip()
            if value == "" or value.lower() == "nan":
                return None
        f = float(value)
        if pd.isna(f):
            return None
        return int(f)
    except (TypeError, ValueError):
        return None


def _parse_iso_date(value) -> str | None:
    """Parse an ISO-ish datetime/date string and return YYYY-MM-DD, or None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        ts = pd.to_datetime(value, errors="coerce")
    except (TypeError, ValueError):
        return None
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d")


def _safe_year(value) -> int | None:
    y = _to_int(value)
    return y


# ---------------------------------------------------------------------------
# Per-source loaders. Each returns a list[Match] (not yet deduplicated).
# ---------------------------------------------------------------------------

def _load_brasileirao(path: Path) -> list[Match]:
    df = pd.read_csv(path)
    matches: list[Match] = []
    for _, r in df.iterrows():
        matches.append(Match(
            date=_parse_iso_date(r.get("datetime")),
            competition=COMPETITIONS["BRASILEIRAO_SERIE_A"],
            season=_safe_year(r.get("season")),
            home_team=normalize_team(r.get("home_team")),
            away_team=normalize_team(r.get("away_team")),
            home_goal=_to_int(r.get("home_goal")),
            away_goal=_to_int(r.get("away_goal")),
            round=str(r.get("round")) if pd.notna(r.get("round")) else None,
            stage=None,
            venue=None,
            source="Brasileirao_Matches.csv",
        ))
    return matches


def _load_copa_do_brasil(path: Path) -> list[Match]:
    df = pd.read_csv(path)
    matches: list[Match] = []
    for _, r in df.iterrows():
        matches.append(Match(
            date=_parse_iso_date(r.get("datetime")),
            competition=COMPETITIONS["COPA_DO_BRASIL"],
            season=_safe_year(r.get("season")),
            home_team=normalize_team(r.get("home_team")),
            away_team=normalize_team(r.get("away_team")),
            home_goal=_to_int(r.get("home_goal")),
            away_goal=_to_int(r.get("away_goal")),
            round=str(r.get("round")) if pd.notna(r.get("round")) else None,
            stage=None,
            venue=None,
            source="Brazilian_Cup_Matches.csv",
        ))
    return matches


def _load_libertadores(path: Path) -> list[Match]:
    df = pd.read_csv(path)
    matches: list[Match] = []
    for _, r in df.iterrows():
        matches.append(Match(
            date=_parse_iso_date(r.get("datetime")),
            competition=COMPETITIONS["COPA_LIBERTADORES"],
            season=_safe_year(r.get("season")),
            home_team=normalize_team(r.get("home_team")),
            away_team=normalize_team(r.get("away_team")),
            home_goal=_to_int(r.get("home_goal")),
            away_goal=_to_int(r.get("away_goal")),
            round=None,
            stage=str(r.get("stage")) if pd.notna(r.get("stage")) else None,
            venue=None,
            source="Libertadores_Matches.csv",
        ))
    return matches


def _load_br_football(path: Path) -> list[Match]:
    df = pd.read_csv(path)
    # Map the free-text tournament column onto canonical competitions.
    tour_map = {
        "Serie A": COMPETITIONS["BRASILEIRAO_SERIE_A"],
        "Serie B": COMPETITIONS["BRASILEIRAO_SERIE_B"],
        "Serie C": COMPETITIONS["BRASILEIRAO_SERIE_C"],
        "Copa do Brasil": COMPETITIONS["COPA_DO_BRASIL"],
    }
    matches: list[Match] = []
    for _, r in df.iterrows():
        raw_tour = str(r.get("tournament")).strip()
        competition = tour_map.get(raw_tour)
        if competition is None:
            continue  # unknown tournament; skip rather than mislabel
        d = _parse_iso_date(r.get("date"))
        season = int(d[:4]) if d else None
        matches.append(Match(
            date=d,
            competition=competition,
            season=season,
            home_team=normalize_team(r.get("home")),
            away_team=normalize_team(r.get("away")),
            home_goal=_to_int(r.get("home_goal")),
            away_goal=_to_int(r.get("away_goal")),
            round=None,
            stage=None,
            venue=None,
            source="BR-Football-Dataset.csv",
            home_corner=_num(r.get("home_corner")),
            away_corner=_num(r.get("away_corner")),
            home_shots=_num(r.get("home_shots")),
            away_shots=_num(r.get("away_shots")),
            home_attack=_num(r.get("home_attack")),
            away_attack=_num(r.get("away_attack")),
            total_corners=_num(r.get("total_corners")),
        ))
    return matches


def _num(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        f = float(value)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def _load_historical(path: Path) -> list[Match]:
    df = pd.read_csv(path)
    matches: list[Match] = []
    for _, r in df.iterrows():
        # "Data" is DD/MM/YYYY (Brazilian day-first format).
        d = _parse_dayfirst_date(r.get("Data"))
        matches.append(Match(
            date=d,
            competition=COMPETITIONS["BRASILEIRAO_SERIE_A"],
            season=_safe_year(r.get("Ano")),
            home_team=normalize_team(r.get("Equipe_mandante")),
            away_team=normalize_team(r.get("Equipe_visitante")),
            home_goal=_to_int(r.get("Gols_mandante")),
            away_goal=_to_int(r.get("Gols_visitante")),
            round=str(r.get("Rodada")) if pd.notna(r.get("Rodada")) else None,
            stage=None,
            venue=str(r.get("Arena")) if pd.notna(r.get("Arena")) else None,
            source="novo_campeonato_brasileiro.csv",
        ))
    return matches


def _parse_dayfirst_date(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        ts = pd.to_datetime(value, dayfirst=True, errors="coerce")
    except (TypeError, ValueError):
        return None
    if pd.isna(ts):
        return None
    return ts.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Unified, deduplicated match table
# ---------------------------------------------------------------------------

_MATCH_COLUMNS = [
    "date", "competition", "season", "home_team", "away_team",
    "home_goal", "away_goal", "round", "stage", "venue", "source",
    "home_key", "away_key",
    "home_corner", "away_corner", "home_shots", "away_shots",
    "home_attack", "away_attack", "total_corners",
]


@lru_cache(maxsize=1)
def load_matches() -> pd.DataFrame:
    """Load every match source, normalize, and return a deduplicated DataFrame.

    Dedup key: (home_key, away_key, date, home_goal, away_goal). When two rows
    collide we keep the one carrying advanced stats (corners/shots), so the
    BR-Football enrichment survives the merge with the dedicated competition files.
    """
    files = {
        "Brasileirao_Matches.csv": _load_brasileirao,
        "Brazilian_Cup_Matches.csv": _load_copa_do_brasil,
        "Libertadores_Matches.csv": _load_libertadores,
        "BR-Football-Dataset.csv": _load_br_football,
        "novo_campeonato_brasileiro.csv": _load_historical,
    }
    rows: list[dict] = []
    for fname, fn in files.items():
        p = DATA_DIR / fname
        if not p.exists():
            continue
        for m in fn(p):
            d = m.to_dict()
            d["home_key"] = team_key(m.home_team)
            d["away_key"] = team_key(m.away_team)
            rows.append(d)

    df = pd.DataFrame(rows, columns=_MATCH_COLUMNS + ["home_key", "away_key"])
    # The columns list above lists home_key/away_key twice defensively; drop dup.
    df = df.loc[:, ~df.columns.duplicated()]

    # Deduplicate. Prefer rows that carry advanced stats: assign a "richness"
    # score and keep the max within each duplicate group.
    df["_richness"] = (
        df["home_corner"].notna().astype(int)
        + df["home_shots"].notna().astype(int)
        + df["home_attack"].notna().astype(int)
    )
    # Stable sort so the first occurrence (dedicated competition file) wins ties.
    df = df.sort_values("_richness", ascending=False, kind="mergesort")
    dedup_cols = ["home_key", "away_key", "date", "home_goal", "away_goal"]
    # Rows with a null date can't be safely deduped; keep them all.
    mask_has_date = df["date"].notna()
    df_dated = df[mask_has_date].drop_duplicates(subset=dedup_cols, keep="first")
    df = pd.concat([df_dated, df[~mask_has_date]], ignore_index=True)
    df = df.drop(columns=["_richness"]).reset_index(drop=True)
    return df


@lru_cache(maxsize=1)
def load_players() -> pd.DataFrame:
    """Load the FIFA player database, projected to useful columns.

    The CSV carries a stray unnamed index column and a UTF-8 BOM; both are
    handled. Club/Nationality are normalized to plain strings (no NaN).
    """
    path = DATA_DIR / "fifa_data.csv"
    df = pd.read_csv(path, encoding="utf-8-sig")
    # Drop the unnamed leading index column if present.
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(columns=df.columns[0])

    keep = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club",
        "Position", "Jersey Number", "Height", "Weight", "Value", "Wage",
    ]
    skill_cols = [
        "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
        "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
        "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
        "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
        "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
        "Composure", "Marking", "StandingTackle", "SlidingTackle",
        "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
    ]
    cols = [c for c in keep if c in df.columns] + [
        c for c in skill_cols if c in df.columns
    ]
    df = df[cols].copy()
    # Normalize text columns to clean strings (NaN -> "").
    for c in ("Name", "Nationality", "Club", "Position", "Height", "Weight",
              "Value", "Wage"):
        if c in df.columns:
            df[c] = df[c].astype("string").fillna("").str.strip()
    # Add an accent-folded club key for robust matching ("FC Barcelona" etc.).
    df["club_key"] = df["Club"].map(
        lambda s: __import__("unicodedata").normalize("NFKD", str(s))
        .encode("ascii", "ignore").decode().lower()
    )
    df["name_key"] = df["Name"].map(
        lambda s: __import__("unicodedata").normalize("NFKD", str(s))
        .encode("ascii", "ignore").decode().lower()
    )
    return df.reset_index(drop=True)


def get_data_summary() -> dict:
    """Return a quick inventory of what was loaded (counts per source/competition)."""
    df = load_matches()
    by_source = df["source"].value_counts().to_dict()
    by_comp = df["competition"].value_counts().to_dict()
    seasons = sorted(
        s for s in df["season"].dropna().unique().tolist() if s is not None
    )
    players = load_players()
    return {
        "matches_total": int(len(df)),
        "matches_by_source": {k: int(v) for k, v in by_source.items()},
        "matches_by_competition": {k: int(v) for k, v in by_comp.items()},
        "seasons": [int(s) for s in seasons],
        "players_total": int(len(players)),
        "nationalities": int(players["Nationality"].nunique()),
        "brazilian_players": int((players["Nationality"] == "Brazil").sum()),
    }


def clear_cache() -> None:
    """Reset the lru_cache'd frames (used by tests and CLI reloads)."""
    load_matches.cache_clear()
    load_players.cache_clear()
