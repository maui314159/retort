"""
Brazilian Soccer MCP Server — Data Loader

Loads and normalizes all six Kaggle CSV datasets into a unified pandas
DataFrame layer.  Every public function returns plain Python dicts/lists
so the MCP tool layer never touches pandas directly.

Key design choices:
  • Team names are normalised by stripping state suffixes ("-SP", "-RJ" …)
    and lower-casing for matching.  The canonical (title-cased, suffix-free)
    form is stored alongside the original for display.
  • Dates are parsed per-dataset (ISO vs DD/MM/YYYY) and coerced to
    datetime64[ns]; unparseable rows get NaT.
  • All DataFrames are loaded once at import time (module-level singleton).

Context:
  TASK.md §"Provided Data" defines six CSV files in data/kaggle/.
  TASK.md §"Data Quality Notes" requires team-name normalisation and
  multi-format date handling.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"

# ---------------------------------------------------------------------------
# Team-name normalisation
# ---------------------------------------------------------------------------

# Brazilian state abbreviations that appear as suffixes in match data
_STATE_RE = re.compile(r"[-\s]\s*[A-Z]{2}$")

# Common full-name patterns that we strip down to the familiar short name
_SUFFIX_RE = re.compile(
    r"\s*("
    r"Esporte Clube|Clube de Regatas|Sport Club|Futebol Clube"
    r"|Atlético Clube|Associação|Associação Esportiva"
    r")\s*$",
    re.IGNORECASE,
)

# Known renames for the most common discrepancies across datasets
_CANONICAL: dict[str, str] = {
    # derived at load-time; populated by _build_canonical_map()
}


def normalize_team(name: str) -> str:
    """Return a canonical, suffix-free, title-cased team name.

    Examples:
        "Palmeiras-SP"   → "Palmeiras"
        "Flamengo-RJ"    → "Flamengo"
        "São Paulo-SP"   → "São Paulo"
        "Corinthians-SP" → "Corinthians"
    """
    if not isinstance(name, str):
        return ""
    s = name.strip()
    # Remove state suffix like "-SP" or " -RJ"
    s = _STATE_RE.sub("", s)
    # Remove trailing parenthetical like "(antigo Esporte Clube Barreira) - RJ"
    s = re.sub(r"\s*\(.*?\)", "", s)
    s = s.strip()
    # Known canonical override?
    low = s.lower()
    for pattern, canon in _CANONICAL.items():
        if low == pattern:
            return canon
    return s


def _team_key(name: str) -> str:
    """Lower-cased, normalised key for matching."""
    return normalize_team(name).lower().strip()


# ---------------------------------------------------------------------------
# Per-dataset loaders
# ---------------------------------------------------------------------------


def _load_brasileirao() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "Brasileirao_Matches.csv")
    df["competition"] = "Brasileirão Série A"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["round"] = pd.to_numeric(df["round"], errors="coerce").astype("Int64")
    return df[
        [
            "date", "competition", "season", "round",
            "home_team", "home_team_norm", "away_team", "away_team_norm",
            "home_goal", "away_goal",
        ]
    ]


def _load_copa_brasil() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "Brazilian_Cup_Matches.csv")
    df["competition"] = "Copa do Brasil"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df.rename(columns={"round": "round"}, inplace=True)
    return df[
        [
            "date", "competition", "season", "round",
            "home_team", "home_team_norm", "away_team", "away_team_norm",
            "home_goal", "away_goal",
        ]
    ]


def _load_libertadores() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "Libertadores_Matches.csv")
    df["competition"] = "Copa Libertadores"
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["home_team_norm"] = df["home_team"].apply(normalize_team)
    df["away_team_norm"] = df["away_team"].apply(normalize_team)
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    df["round"] = df["stage"].astype(str)
    return df[
        [
            "date", "competition", "season", "round",
            "home_team", "home_team_norm", "away_team", "away_team_norm",
            "home_goal", "away_goal",
        ]
    ]


def _load_br_football() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "BR-Football-Dataset.csv")
    df["competition"] = df["tournament"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["home_team_norm"] = df["home"].apply(normalize_team)
    df["away_team_norm"] = df["away"].apply(normalize_team)
    df["home_team"] = df["home"]
    df["away_team"] = df["away"]
    df["home_goal"] = pd.to_numeric(df["home_goal"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["away_goal"], errors="coerce")
    df["round"] = None
    # Try to extract season from date
    df["season"] = df["date"].dt.year.astype("Int64")
    # Keep extended stats
    for col in [
        "home_corner", "away_corner", "home_attack", "away_attack",
        "home_shots", "away_shots", "total_corners",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df.get(col), errors="coerce")
    cols = [
        "date", "competition", "season", "round",
        "home_team", "home_team_norm", "away_team", "away_team_norm",
        "home_goal", "away_goal",
    ]
    # Append extended stats if present
    for col in [
        "home_corner", "away_corner", "home_attack", "away_attack",
        "home_shots", "away_shots", "total_corners",
    ]:
        if col in df.columns:
            cols.append(col)
    return df[cols]


def _load_historico() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "novo_campeonato_brasileiro.csv")
    df["competition"] = "Brasileirão Série A (histórico)"
    # Date is DD/MM/YYYY
    df["date"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df["home_team_norm"] = df["Equipe_mandante"].apply(normalize_team)
    df["away_team_norm"] = df["Equipe_visitante"].apply(normalize_team)
    df["home_team"] = df["Equipe_mandante"]
    df["away_team"] = df["Equipe_visitante"]
    df["home_goal"] = pd.to_numeric(df["Gols_mandante"], errors="coerce")
    df["away_goal"] = pd.to_numeric(df["Gols_visitante"], errors="coerce")
    df["season"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")
    df["round"] = pd.to_numeric(df["Rodada"], errors="coerce").astype("Int64")
    df["stadium"] = df.get("Arena", pd.NA)
    df["winner"] = df.get("Vencedor", pd.NA)
    cols = [
        "date", "competition", "season", "round",
        "home_team", "home_team_norm", "away_team", "away_team_norm",
        "home_goal", "away_goal",
    ]
    if "stadium" in df.columns:
        cols.append("stadium")
    if "winner" in df.columns:
        cols.append("winner")
    return df[cols]


def _load_fifa() -> pd.DataFrame:
    df = pd.read_csv(_DATA_DIR / "fifa_data.csv", encoding="utf-8")
    # The CSV has a BOM column — drop it
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df.rename(columns=lambda c: c.strip(), inplace=True)
    # Coerce numeric columns
    for col in ["Overall", "Potential", "Age", "Jersey Number"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Build canonical name map from all match datasets
# ---------------------------------------------------------------------------

def _build_canonical_map(match_dfs: list[pd.DataFrame]) -> None:
    """Populate _CANONICAL with lower→title mappings from normalised names."""
    seen: dict[str, str] = {}
    for df in match_dfs:
        for col in ("home_team_norm", "away_team_norm"):
            for name in df[col].dropna().unique():
                low = name.lower().strip()
                if low not in seen:
                    seen[low] = name
    _CANONICAL.update(seen)


# ---------------------------------------------------------------------------
# Module-level singleton: load everything once
# ---------------------------------------------------------------------------

_brasileirao: pd.DataFrame = _load_brasileirao()
_copa_brasil: pd.DataFrame = _load_copa_brasil()
_libertadores: pd.DataFrame = _load_libertadores()
_br_football: pd.DataFrame = _load_br_football()
_historico: pd.DataFrame = _load_historico()
_fifa: pd.DataFrame = _load_fifa()

# Unified match DataFrame
_matches: pd.DataFrame = pd.concat(
    [_brasileirao, _copa_brasil, _libertadores, _br_football, _historico],
    ignore_index=True,
    sort=False,
)

# Build canonical map after loading all match data
_build_canonical_map([_brasileirao, _copa_brasil, _libertadores, _br_football, _historico])


# ---------------------------------------------------------------------------
# Public query API — returns plain dicts/lists, never DataFrames
# ---------------------------------------------------------------------------


def _row_to_dict(row: pd.Series) -> dict:
    """Convert a DataFrame row to a JSON-friendly dict."""
    d = {}
    for k, v in row.items():
        if pd.isna(v):
            d[k] = None
        elif isinstance(v, pd.Timestamp):
            d[k] = v.isoformat()[:10]
        elif hasattr(v, "item"):
            d[k] = v.item()
        else:
            d[k] = str(v)
    return d


def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search matches across all datasets with flexible filters.

    Args:
        team: Team name (matches home or away).
        opponent: Opponent team name (matches the other side).
        competition: Substring match on competition name.
        season: Year filter.
        date_from: ISO date string (inclusive).
        date_to: ISO date string (inclusive).
        limit: Maximum rows to return.

    Returns:
        List of match dicts sorted by date descending.
    """
    mask = pd.Series(True, index=_matches.index)

    if team:
        key = _team_key(team)
        mask &= (
            _matches["home_team_norm"].str.lower().str.contains(key, na=False)
            | _matches["away_team_norm"].str.lower().str.contains(key, na=False)
        )
    if opponent:
        okey = _team_key(opponent)
        mask &= (
            _matches["home_team_norm"].str.lower().str.contains(okey, na=False)
            | _matches["away_team_norm"].str.lower().str.contains(okey, na=False)
        )
    if competition:
        mask &= _matches["competition"].str.lower().str.contains(
            competition.lower(), na=False
        )
    if season is not None:
        mask &= _matches["season"] == season
    if date_from:
        mask &= _matches["date"] >= pd.Timestamp(date_from)
    if date_to:
        mask &= _matches["date"] <= pd.Timestamp(date_to)

    result = _matches.loc[mask].sort_values("date", ascending=False).head(limit)
    return [_row_to_dict(r) for _, r in result.iterrows()]


def get_team_stats(
    team: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Calculate win/draw/loss and goals for a team.

    Args:
        team: Team name (fuzzy-matched).
        competition: Optional competition filter.
        season: Optional season filter.

    Returns:
        Dict with matches, wins, draws, losses, goals_for, goals_against, win_rate.
    """
    key = _team_key(team)
    home = _matches["home_team_norm"].str.lower().str.contains(key, na=False)
    away = _matches["away_team_norm"].str.lower().str.contains(key, na=False)

    df = _matches.loc[home | away].copy()
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season is not None:
        df = df[df["season"] == season]

    total = len(df)
    if total == 0:
        return {"team": team, "matches": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "win_rate": 0.0}

    # Determine win/draw/loss from team's perspective
    wins = draws = losses = 0
    gf = ga = 0
    for _, row in df.iterrows():
        is_home = key in row["home_team_norm"].lower()
        hg = row["home_goal"] if pd.notna(row["home_goal"]) else 0
        ag = row["away_goal"] if pd.notna(row["away_goal"]) else 0
        if is_home:
            gf += hg
            ga += ag
            if hg > ag:
                wins += 1
            elif hg == ag:
                draws += 1
            else:
                losses += 1
        else:
            gf += ag
            ga += hg
            if ag > hg:
                wins += 1
            elif ag == hg:
                draws += 1
            else:
                losses += 1

    return {
        "team": team,
        "matches": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "win_rate": round(wins / total * 100, 1) if total else 0.0,
    }


def get_head_to_head(team_a: str, team_b: str, limit: int = 50) -> dict:
    """Compare two teams head-to-head across all match data.

    Returns:
        Dict with matches list and per-team win counts.
    """
    ka = _team_key(team_a)
    kb = _team_key(team_b)

    a_home = _matches["home_team_norm"].str.lower().str.contains(ka, na=False)
    a_away = _matches["away_team_norm"].str.lower().str.contains(ka, na=False)
    b_home = _matches["home_team_norm"].str.lower().str.contains(kb, na=False)
    b_away = _matches["away_team_norm"].str.lower().str.contains(kb, na=False)

    # A is home and B is away, or A is away and B is home
    mask = ((a_home & b_away) | (a_away & b_home))
    df = _matches.loc[mask].sort_values("date", ascending=False).head(limit)

    a_wins = b_wins = draws = 0
    matches = []
    for _, row in df.iterrows():
        hg = row["home_goal"] if pd.notna(row["home_goal"]) else 0
        ag = row["away_goal"] if pd.notna(row["away_goal"]) else 0
        is_a_home = ka in row["home_team_norm"].lower()

        if hg > ag:
            if is_a_home:
                a_wins += 1
            else:
                b_wins += 1
        elif hg < ag:
            if is_a_home:
                b_wins += 1
            else:
                a_wins += 1
        else:
            draws += 1

        matches.append(_row_to_dict(row))

    return {
        "team_a": team_a,
        "team_b": team_b,
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "total_matches": len(matches),
        "matches": matches,
    }


def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search FIFA player data with flexible filters.

    Args:
        name: Substring match on player name.
        nationality: Substring match on nationality.
        club: Substring match on club name.
        position: Substring match on position.
        min_overall: Minimum overall rating.
        limit: Max rows.

    Returns:
        List of player dicts sorted by Overall descending.
    """
    df = _fifa.copy()
    if name:
        df = df[df["Name"].str.lower().str.contains(name.lower(), na=False)]
    if nationality:
        df = df[df["Nationality"].str.lower().str.contains(nationality.lower(), na=False)]
    if club:
        df = df[df["Club"].str.lower().str.contains(club.lower(), na=False)]
    if position:
        df = df[df["Position"].str.lower().str.contains(position.lower(), na=False)]
    if min_overall is not None:
        df = df[df["Overall"] >= min_overall]

    df = df.sort_values("Overall", ascending=False).head(limit)

    cols = [
        "ID", "Name", "Age", "Nationality", "Overall", "Potential",
        "Club", "Position", "Jersey Number", "Height", "Weight",
    ]
    # Keep only columns that exist
    cols = [c for c in cols if c in df.columns]
    return [_row_to_dict(r) for _, r in df[cols].iterrows()]


def get_competition_standings(competition: str, season: int) -> list[dict]:
    """Calculate standings for a competition/season from match results.

    Uses 3-1-0 point system. Only works for round-robin leagues (Brasileirão).

    Args:
        competition: Competition name substring.
        season: Year.

    Returns:
        List of team standings sorted by points descending.
    """
    key = competition.lower()
    df = _matches[
        _matches["competition"].str.lower().str.contains(key, na=False)
        & (_matches["season"] == season)
    ]

    if df.empty:
        return []

    stats: dict[str, dict] = {}
    for _, row in df.iterrows():
        hg = row["home_goal"] if pd.notna(row["home_goal"]) else 0
        ag = row["away_goal"] if pd.notna(row["away_goal"]) else 0
        ht = row["home_team_norm"]
        at = row["away_team_norm"]
        if not ht or not at:
            continue

        for team, gf, ga, is_home in [(ht, hg, ag, True), (at, ag, hg, False)]:
            if team not in stats:
                stats[team] = {"team": team, "pts": 0, "w": 0, "d": 0, "l": 0,
                               "gf": 0, "ga": 0}
            s = stats[team]
            s["gf"] += int(gf)
            s["ga"] += int(ga)
            if gf > ga:
                s["w"] += 1
                s["pts"] += 3
            elif gf == ga:
                s["d"] += 1
                s["pts"] += 1
            else:
                s["l"] += 1

    standings = sorted(stats.values(), key=lambda x: (x["pts"], x["gf"] - x["ga"], x["gf"]), reverse=True)
    for i, s in enumerate(standings, 1):
        s["position"] = i
        s["goal_difference"] = s["gf"] - s["ga"]
        s["matches"] = s["w"] + s["d"] + s["l"]
    return standings


def get_statistics(
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Aggregate statistics across match data.

    Returns:
        Dict with avg_goals, home_win_rate, biggest_wins, total_matches.
    """
    df = _matches.copy()
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season is not None:
        df = df[df["season"] == season]

    # Drop rows without scores
    scored = df.dropna(subset=["home_goal", "away_goal"])
    total = len(scored)
    if total == 0:
        return {"total_matches": 0, "avg_goals": 0.0, "home_win_rate": 0.0, "biggest_wins": []}

    avg_goals = round((scored["home_goal"] + scored["away_goal"]).mean(), 2)
    home_wins = int((scored["home_goal"] > scored["away_goal"]).sum())
    home_win_rate = round(home_wins / total * 100, 1)

    # Biggest wins by goal difference
    scored_copy = scored.copy()
    scored_copy["goal_diff"] = (scored_copy["home_goal"] - scored_copy["away_goal"]).abs()
    top = scored_copy.nlargest(5, "goal_diff")
    biggest = []
    for _, row in top.iterrows():
        biggest.append({
            "date": row["date"].isoformat()[:10] if pd.notna(row["date"]) else None,
            "home": row["home_team_norm"],
            "away": row["away_team_norm"],
            "home_goal": int(row["home_goal"]),
            "away_goal": int(row["away_goal"]),
            "competition": row["competition"],
        })

    return {
        "total_matches": total,
        "avg_goals": avg_goals,
        "home_win_rate": home_win_rate,
        "biggest_wins": biggest,
    }


def list_teams(competition: str | None = None) -> list[str]:
    """Return sorted list of unique normalised team names."""
    df = _matches
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    teams = set()
    for col in ("home_team_norm", "away_team_norm"):
        for t in df[col].dropna().unique():
            if t:
                teams.add(t)
    return sorted(teams)


def list_competitions() -> list[str]:
    """Return sorted list of unique competition names."""
    return sorted(_matches["competition"].dropna().unique().tolist())


def list_seasons(competition: str | None = None) -> list[int]:
    """Return sorted list of seasons (years) available."""
    df = _matches
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    return sorted(
        int(s) for s in df["season"].dropna().unique() if pd.notna(s)
    )
