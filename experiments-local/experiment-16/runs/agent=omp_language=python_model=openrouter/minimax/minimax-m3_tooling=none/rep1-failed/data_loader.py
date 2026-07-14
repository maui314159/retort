"""
data_loader.py
==============

CSV ingestion and normalization for the Brazilian Soccer MCP server.

The match datasets shipped under ``data/kaggle`` are heterogeneous: they
use different team-name conventions, date formats, and column names.  This
module hides that complexity behind a single ``load_matches()`` function
that returns a unified :class:`pandas.DataFrame` keyed by canonical team
names.

Responsibilities
----------------
* Load each match CSV and align its columns.
* Normalize team names (state suffixes, accents, parenthetical notes,
  country codes, etc.).
* Parse dates from ISO and Brazilian (``DD/MM/YYYY``) formats.
* Deduplicate matches that show up in more than one source dataset.
  Within each (competition, season, sorted-pair) group we cluster
  matches that occur within 7 days of each other; the home and away
  legs of a fixture are always months apart, so a 7-day cluster
  window reliably identifies duplicate reports of the same match.
* Provide light-weight helpers for resolving free-text team and
  competition queries against the loaded data.
* Load the FIFA player dataset with derived lookup keys.

The match DataFrame exposes the following canonical columns::

    match_id, competition, season, round, stage, date,
    home_team_display, away_team_display,
    home_team_state, away_team_state,
    home_goal, away_goal,
    home_team_key, away_team_key

The player DataFrame exposes::

    player_id, name, age, nationality, overall, potential,
    club, position, jersey_number, height, weight,
    name_key, club_key, nationality_key
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Final

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR: Final[Path] = Path(__file__).resolve().parent / "data" / "kaggle"

MATCH_FILES: Final[dict[str, Path]] = {
    "brasileirao": DATA_DIR / "Brasileirao_Matches.csv",
    "copa_brasil": DATA_DIR / "Brazilian_Cup_Matches.csv",
    "libertadores": DATA_DIR / "Libertadores_Matches.csv",
    "br_football": DATA_DIR / "BR-Football-Dataset.csv",
    "novo_brasileirao": DATA_DIR / "novo_campeonato_brasileiro.csv",
}

PLAYER_FILE: Final[Path] = DATA_DIR / "fifa_data.csv"

# ---------------------------------------------------------------------------
# Competition aliases
# ---------------------------------------------------------------------------

COMPETITION_ALIASES: Final[dict[str, list[str]]] = {
    "Brasileirão": [
        "brasileirao",
        "brasileirão",
        "serie a",
        "série a",
        "campeonato brasileiro",
        "brasileirao serie a",
    ],
    "Copa do Brasil": [
        "copa do brasil",
        "copa brasil",
        "brazilian cup",
    ],
    "Copa Libertadores": [
        "libertadores",
        "copa libertadores",
        "libertadores da america",
    ],
}

_BR_FOOTBALL_COMPETITION_MAP: Final[dict[str, str]] = {
    "Serie A": "Brasileirão",
    "Copa do Brasil": "Copa do Brasil",
}

# Post-strip aliases: applied AFTER the state/country suffix is stripped.
_TEAM_ALIASES: Final[dict[str, str]] = {
    "atletico-mg": "atletico mineiro",
    "atletico mineiro": "atletico mineiro",
    "atletico": "atletico mineiro",
    "america-mg": "america mineiro",
    "america mineiro": "america mineiro",
    "vasco da gama": "vasco",
    "vasco da gama rj": "vasco",
    "sao paulo-sp": "sao paulo",
    "sao paulo": "sao paulo",
    "botafogo rj": "botafogo",
    "fortaleza fc": "fortaleza",
    "fortaleza-ce": "fortaleza",
    "ec bahia": "bahia",
    "bahia-ba": "bahia",
    "gremio rs": "gremio",
    "gremio-rs": "gremio",
    "internacional rs": "internacional",
    "internacional-rs": "internacional",
    "corinthians sp": "corinthians",
    "corinthians-sp": "corinthians",
    "palmeiras sp": "palmeiras",
    "palmeiras-sp": "palmeiras",
    "santos sp": "santos",
    "santos-sp": "santos",
    "flamengo rj": "flamengo",
    "flamengo-rj": "flamengo",
    "fluminense rj": "fluminense",
    "fluminense-rj": "fluminense",
    "cruzeiro mg": "cruzeiro",
    "cruzeiro-mg": "cruzeiro",
    "sport pe": "sport",
    "sport-pe": "sport",
    "ceara ce": "ceara",
    "ceara-ce": "ceara",
    "goias go": "goias",
    "goias-go": "goias",
    "csa al": "csa",
    "csa-al": "csa",
    "chapecoense sc": "chapecoense",
    "chapecoense-sc": "chapecoense",
    "atletico paranaense": "athletico paranaense",
    "athletico": "athletico paranaense",
    "athletico pr": "athletico paranaense",
}

# Pre-strip aliases: applied to the team name BEFORE the state/country
# suffix is stripped.
_TEAM_ALIASES_PRE: Final[dict[str, str]] = {
    "atletico-pr": "athletico paranaense",
    "athletico-pr": "athletico paranaense",
    "atletico-mg": "atletico mineiro",
    "atletico-go": "atletico goianiense",
}


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _strip_accents(value: str) -> str:
    """Fold diacritics off a string (e.g. ``São`` -> ``Sao``)."""
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _strip_parenthetical(value: str) -> str:
    """Remove parenthetical suffixes such as ``(URU)`` or ``(antigo ...)``."""
    return re.sub(r"\s*\([^)]*\)", "", value)


def _strip_state_suffix(value: str) -> str:
    """Remove trailing state tags like ``-SP``, `` - RJ``, or ``-EQU``."""
    value = re.sub(r"\s*-\s*[A-Za-z]{2,3}$", "", value)
    value = re.sub(r"-[A-Za-z]{2,3}$", "", value)
    return value


def normalize_team_name(name: object) -> str:
    """
    Return a canonical lookup key for a team name.

    Transformations applied (in order):

    1. Drop parenthetical suffixes such as ``(URU)``.
    2. Apply pre-strip aliases (e.g. ``atletico-pr`` ->
       ``athletico paranaense``) so state-suffix disambiguation is
       preserved before it is lost.
    3. Drop trailing state/country tags such as ``-SP`` or `` - EQU``.
    4. Fold diacritics.
    5. Collapse whitespace and lowercase.
    6. Map post-strip aliases (e.g. ``vasco da gama rj`` -> ``vasco``).
    """
    if not isinstance(name, str):
        return ""
    cleaned = _strip_parenthetical(name)
    pre_candidate = _strip_accents(cleaned)
    pre_candidate = re.sub(r"\s+", " ", pre_candidate).strip().lower()
    if pre_candidate in _TEAM_ALIASES_PRE:
        return _TEAM_ALIASES_PRE[pre_candidate]

    cleaned = _strip_state_suffix(cleaned)
    cleaned = _strip_accents(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    key = cleaned.lower()
    return _TEAM_ALIASES.get(key, key)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS: Final[tuple[str, ...]] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M:%S",
)


def _parse_date(value: object) -> pd.Timestamp | pd.NaT:
    """Parse dates stored as ISO strings or Brazilian ``DD/MM/YYYY``."""
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    for fmt in _DATE_FORMATS:
        try:
            return pd.to_datetime(text, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.to_datetime(text, dayfirst=True, errors="coerce")


# ---------------------------------------------------------------------------
# Match loaders
# ---------------------------------------------------------------------------

_CANONICAL_COLS: Final[list[str]] = [
    "competition",
    "season",
    "round",
    "stage",
    "date",
    "raw_date",
    "home_team_display",
    "away_team_display",
    "home_team_state",
    "away_team_state",
    "home_goal",
    "away_goal",
    "_source",
]


def _empty_match_frame() -> pd.DataFrame:
    """Return an empty matches DataFrame with the canonical schema."""
    return pd.DataFrame(columns=_CANONICAL_COLS + ["_source_priority"])


def load_brasileirao() -> pd.DataFrame:
    """Load the modern Brasileirão (2012-2022) dataset."""
    path = MATCH_FILES["brasileirao"]
    if not path.exists():
        return _empty_match_frame()
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "datetime": "raw_date",
            "home_team": "home_team_display",
            "away_team": "away_team_display",
        }
    )
    df["competition"] = "Brasileirão"
    df["stage"] = None
    df["_source"] = "brasileirao"
    df["date"] = df["raw_date"].apply(_parse_date)
    return df


def load_copa_brasil() -> pd.DataFrame:
    """Load the Copa do Brasil dataset."""
    path = MATCH_FILES["copa_brasil"]
    if not path.exists():
        return _empty_match_frame()
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "round": "round",
            "datetime": "raw_date",
            "home_team": "home_team_display",
            "away_team": "away_team_display",
        }
    )
    df["competition"] = "Copa do Brasil"
    df["stage"] = None
    df["home_team_state"] = None
    df["away_team_state"] = None
    df["_source"] = "copa_brasil"
    df["date"] = df["raw_date"].apply(_parse_date)
    return df


def load_libertadores() -> pd.DataFrame:
    """Load the Copa Libertadores dataset."""
    path = MATCH_FILES["libertadores"]
    if not path.exists():
        return _empty_match_frame()
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "datetime": "raw_date",
            "home_team": "home_team_display",
            "away_team": "away_team_display",
        }
    )
    df["competition"] = "Copa Libertadores"
    df["round"] = None
    df["home_team_state"] = None
    df["away_team_state"] = None
    df["_source"] = "libertadores"
    df["date"] = df["raw_date"].apply(_parse_date)
    return df


def load_br_football() -> pd.DataFrame:
    """Load the BR-Football-Dataset (Serie A/B/C plus Copa do Brasil)."""
    path = MATCH_FILES["br_football"]
    if not path.exists():
        return _empty_match_frame()
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "tournament": "competition",
            "home": "home_team_display",
            "away": "away_team_display",
            "date": "raw_date",
        }
    )
    df["competition"] = (
        df["competition"].map(_BR_FOOTBALL_COMPETITION_MAP).fillna(df["competition"])
    )
    df["round"] = None
    df["stage"] = None
    df["home_team_state"] = None
    df["away_team_state"] = None
    df["_source"] = "br_football"
    df["date"] = df["raw_date"].apply(_parse_date)
    return df


def load_novo_brasileirao() -> pd.DataFrame:
    """Load the historical 2003-2019 Brasileirão dataset."""
    path = MATCH_FILES["novo_brasileirao"]
    if not path.exists():
        return _empty_match_frame()
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "Data": "raw_date",
            "Ano": "season",
            "Rodada": "round",
            "Equipe_mandante": "home_team_display",
            "Equipe_visitante": "away_team_display",
            "Gols_mandante": "home_goal",
            "Gols_visitante": "away_goal",
            "Mandante_UF": "home_team_state",
            "Visitante_UF": "away_team_state",
        }
    )
    df["competition"] = "Brasileirão"
    df["stage"] = None
    df["_source"] = "novo_brasileirao"
    df["date"] = df["raw_date"].apply(_parse_date)
    return df


# Source priority for deduplication.  BR-Football has the richest
# statistics; keep its rows when the same match shows up in multiple
# sources.  Brasileirao is preferred over novo_brasileirao for the
# same reason.
_SOURCE_PRIORITY: Final[dict[str, int]] = {
    "br_football": 0,
    "brasileirao": 1,
    "novo_brasileirao": 2,
}


def _finalize_matches(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Apply shared type/cleanup logic to a list of per-dataset frames."""
    normalized: list[pd.DataFrame] = []
    for frame in frames:
        for col in _CANONICAL_COLS:
            if col not in frame.columns:
                frame[col] = pd.NA
        normalized.append(frame[_CANONICAL_COLS].copy())

    if not normalized:
        return _empty_match_frame()

    unified = pd.concat(normalized, ignore_index=True, sort=False)

    # Numeric score columns.
    unified["home_goal"] = pd.to_numeric(unified["home_goal"], errors="coerce")
    unified["away_goal"] = pd.to_numeric(unified["away_goal"], errors="coerce")

    # Season column: keep explicit value, fall back to year of the date.
    unified["season"] = pd.to_numeric(unified["season"], errors="coerce").astype("Int64")
    year_from_date = pd.to_datetime(unified["date"], errors="coerce").dt.year
    unified["season"] = unified["season"].fillna(
        pd.Series(year_from_date, index=unified.index).astype("Int64")
    )

    # Display names (trimmed) and canonical keys.
    unified["home_team_display"] = unified["home_team_display"].astype(str).str.strip()
    unified["away_team_display"] = unified["away_team_display"].astype(str).str.strip()
    unified["home_team_key"] = unified["home_team_display"].apply(normalize_team_name)
    unified["away_team_key"] = unified["away_team_display"].apply(normalize_team_name)

    # Sorted team pair so "A vs B" and "B vs A" map to the same key.
    pair_a = unified["home_team_key"].astype(str)
    pair_b = unified["away_team_key"].astype(str)
    unified["_sorted_pair"] = (
        pair_a.where(pair_a <= pair_b, pair_b)
        + "::"
        + pair_b.where(pair_a <= pair_b, pair_a)
    )
    unified["_date_only"] = pd.to_datetime(
        unified["date"], errors="coerce"
    ).dt.normalize()
    unified["_source_priority"] = (
        unified["_source"].map(_SOURCE_PRIORITY).fillna(99).astype(int)
    )

    # Sort by (competition, season, pair, date) so the rolling 7-day
    # cluster walk sees rows in chronological order within each group.
    unified = unified.sort_values(
        ["competition", "season", "_sorted_pair", "_date_only", "_source_priority"],
        kind="stable",
        na_position="last",
    )

    def _cluster(group: pd.DataFrame) -> pd.Series:
        """Assign a cluster id that increments when the date gap exceeds 7 days."""
        dates = group["_date_only"].tolist()
        if not dates or all(pd.isna(d) for d in dates):
            return pd.Series([0] * len(dates), index=group.index)
        cluster = [0]
        for prev, curr in zip(dates[:-1], dates[1:]):
            if pd.isna(curr) or pd.isna(prev):
                cluster.append(cluster[-1])
                continue
            gap = (curr - prev).days
            cluster.append(cluster[-1] + 1 if gap > 7 else cluster[-1])
        return pd.Series(cluster, index=group.index)

    cluster_ids = (
        unified.groupby(
            ["competition", "season", "_sorted_pair"], group_keys=False
        )
        .apply(_cluster, include_groups=False)
    )
    unified["_cluster"] = (
        cluster_ids.reindex(unified.index).fillna(0).astype(int)
    )

    # Within each (competition, season, pair, cluster), keep only the
    # highest-priority source's row.
    unified = unified.sort_values("_source_priority", kind="stable")
    unified = unified.drop_duplicates(
        subset=["competition", "season", "_sorted_pair", "_cluster"],
        keep="first",
    )
    unified = unified.drop(
        columns=[
            "_cluster",
            "_source_priority",
            "_source",
            "_sorted_pair",
            "_date_only",
        ]
    )

    # Stable identifiers.
    unified["match_id"] = (
        unified["competition"].astype(str)
        + "|"
        + unified["season"].astype(str)
        + "|"
        + unified.index.astype(str)
    )

    unified = unified.sort_values("date", ascending=False, na_position="last")
    return unified.reset_index(drop=True)


@lru_cache(maxsize=1)
def load_matches() -> pd.DataFrame:
    """Load and merge every match dataset into a single DataFrame."""
    return _finalize_matches(
        [
            load_br_football(),
            load_brasileirao(),
            load_novo_brasileirao(),
            load_copa_brasil(),
            load_libertadores(),
        ]
    )


# ---------------------------------------------------------------------------
# Player loader
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_players() -> pd.DataFrame:
    """Load the FIFA player dataset with derived lookup keys."""
    if not PLAYER_FILE.exists():
        return pd.DataFrame(
            columns=[
                "player_id",
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
                "name_key",
                "club_key",
                "nationality_key",
            ]
        )

    df = pd.read_csv(PLAYER_FILE)
    keep = [
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

    df["name_key"] = df["name"].astype(str).str.lower().apply(_strip_accents)
    df["club_key"] = df["club"].astype(str).apply(normalize_team_name)
    df["nationality_key"] = (
        df["nationality"].astype(str).str.lower().apply(_strip_accents)
    )
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

def resolve_competition(query: str | None) -> list[str] | None:
    """Map a free-text competition query to canonical competition names."""
    if query is None:
        return None
    key = normalize_team_name(query)
    if not key:
        return None

    matches: list[str] = []
    for canonical, aliases in COMPETITION_ALIASES.items():
        alias_keys = [normalize_team_name(a) for a in aliases] + [
            normalize_team_name(canonical)
        ]
        if key in alias_keys or any(k.startswith(key) for k in alias_keys):
            matches.append(canonical)
            continue
        if key in normalize_team_name(canonical):
            matches.append(canonical)

    return matches or None


def resolve_team_name(
    query: str | None,
    matches_df: pd.DataFrame,
) -> str | None:
    """Map a free-text team query to the most common canonical key."""
    if not query:
        return None
    query_key = normalize_team_name(query)
    if not query_key:
        return None

    if matches_df.empty:
        return None

    home_keys = matches_df["home_team_key"].dropna()
    away_keys = matches_df["away_team_key"].dropna()
    home_display = matches_df["home_team_display"].dropna()
    away_display = matches_df["away_team_display"].dropna()

    all_keys = pd.concat([home_keys, away_keys], ignore_index=True)
    all_display = pd.concat([home_display, away_display], ignore_index=True)

    if all_keys.empty:
        return None

    unique_keys = all_keys.unique()
    if query_key in unique_keys:
        return str(query_key)

    normalized_display = all_display.astype(str).apply(normalize_team_name)
    for idx, norm in normalized_display.items():
        if not norm:
            continue
        if query_key in norm or norm in query_key:
            return str(all_keys.iloc[idx])

    return None


def display_name_for_key(team_key: str, matches_df: pd.DataFrame) -> str:
    """Return the most common display name for a canonical team key."""
    if not team_key or matches_df.empty:
        return team_key
    names = pd.concat(
        [
            matches_df.loc[matches_df["home_team_key"] == team_key, "home_team_display"],
            matches_df.loc[matches_df["away_team_key"] == team_key, "away_team_display"],
        ],
        ignore_index=True,
    )
    if names.empty:
        return team_key
    return str(names.value_counts().index[0])


def clear_cache() -> None:
    """Reset the internal loaders (useful for tests and offline tooling)."""
    load_matches.cache_clear()
    load_players.cache_clear()


# ---------------------------------------------------------------------------
# CLI diagnostic
# ---------------------------------------------------------------------------

def _main() -> None:  # pragma: no cover - manual diagnostic
    matches = load_matches()
    players = load_players()
    print("Matches shape:", matches.shape)
    print("Competitions:", matches["competition"].value_counts().to_dict())
    if matches["season"].notna().any():
        print(
            "Seasons covered:",
            int(matches["season"].min()),
            "->",
            int(matches["season"].max()),
        )
    print("Players shape:", players.shape)
    print(
        "Brazilian players:",
        int((players["nationality"] == "Brazil").sum()),
    )


if __name__ == "__main__":
    _main()
