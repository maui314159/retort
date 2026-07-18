# brazilian_soccer.queries
# -----------------------------------------------------------------------------
# Context:
#   The query engine sits between the data layer (loader.py) and the MCP tool
#   layer (server.py). It implements every query category required by TASK.md:
#     1. Match queries      - find matches by team / date range / competition / season
#     2. Team queries       - W/L/D records, goals, performance by competition
#     3. Player queries     - search by name / nationality / club / ratings
#     4. Competition queries- standings (calculated from results), schedules
#     5. Statistical analysis - goal averages, biggest wins, home vs away, H2H
#
#   All functions return plain dicts / lists of dicts so they can be returned
#   verbatim as MCP tool structured output. Team matching always goes through
#   team_key() so that "Palmeiras-SP", "Palmeiras" and "palmeiras" all resolve
#   to the same side. Season filtering tolerates the float dtype that pandas
#   produces from the CSV columns (season=2023.0 is treated as 2023).
# -----------------------------------------------------------------------------
from __future__ import annotations

from typing import Any

import pandas as pd

from .loader import load_matches, load_players
from .models import POSITION_GROUPS, Standing, TeamRecord
from .normalize import derby_name, normalize_team, team_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _season_filter(df: pd.DataFrame, season: int | None) -> pd.DataFrame:
    if season is None:
        return df
    return df[df["season"].apply(lambda s: s is not None and int(s) == int(season))]


def _competition_filter(df: pd.DataFrame, competition: str | None) -> pd.DataFrame:
    if not competition:
        return df
    comp_key = competition.strip().lower()
    return df[df["competition"].str.lower() == comp_key]


def _team_mask(df: pd.DataFrame, team: str, side: str = "either") -> pd.Series:
    """Build a boolean mask selecting rows where *team* plays on the given side.

    side: "home", "away", or "either". Matching is by team_key (accent-folded,
    suffix-stripped) so caller spelling does not need to match the data exactly.
    """
    tk = team_key(team)
    if side == "home":
        return df["home_key"] == tk
    if side == "away":
        return df["away_key"] == tk
    return (df["home_key"] == tk) | (df["away_key"] == tk)


def _match_row_to_dict(row: pd.Series) -> dict[str, Any]:
    """Project a DataFrame row into the JSON-serializable match dict."""
    return {
        "date": row["date"] if pd.notna(row["date"]) else None,
        "competition": row["competition"],
        "season": int(row["season"]) if pd.notna(row["season"]) else None,
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "home_goal": int(row["home_goal"]) if pd.notna(row["home_goal"]) else None,
        "away_goal": int(row["away_goal"]) if pd.notna(row["away_goal"]) else None,
        "round": row["round"] if pd.notna(row["round"]) else None,
        "stage": row["stage"] if pd.notna(row["stage"]) else None,
        "venue": row["venue"] if pd.notna(row["venue"]) else None,
        "source": row["source"],
        "home_corner": float(row["home_corner"]) if pd.notna(row.get("home_corner")) else None,
        "away_corner": float(row["away_corner"]) if pd.notna(row.get("away_corner")) else None,
        "home_shots": float(row["home_shots"]) if pd.notna(row.get("home_shots")) else None,
        "away_shots": float(row["away_shots"]) if pd.notna(row.get("away_shots")) else None,
    }


def _sort_by_date(df: pd.DataFrame, ascending: bool = True) -> pd.DataFrame:
    """Sort by date (NaNs last in either direction)."""
    return df.sort_values("date", ascending=ascending, na_position="last")


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------

def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    stage: str | None = None,
    limit: int | None = 50,
) -> list[dict[str, Any]]:
    """Find matches matching the given criteria.

    All filters are optional and combine with AND. ``team`` matches either home
    or away; ``opponent`` (if given) must be the *other* side. Dates are
    inclusive and accept any ISO-parseable string.
    """
    df = load_matches()
    if team:
        df = df[_team_mask(df, team, "either")]
    if opponent:
        df = df[_team_mask(df, opponent, "either")]
    if team and opponent:
        # Both specified: ensure they are playing *each other*.
        tk, ok = team_key(team), team_key(opponent)
        df = df[
            ((df["home_key"] == tk) & (df["away_key"] == ok))
            | ((df["home_key"] == ok) & (df["away_key"] == tk))
        ]
    if competition:
        df = _competition_filter(df, competition)
    if season is not None:
        df = _season_filter(df, season)
    if start_date:
        sd = pd.to_datetime(start_date, errors="coerce")
        if pd.notna(sd):
            dates = pd.to_datetime(df["date"], errors="coerce")
            df = df[dates.isna() | (dates >= sd)]
    if end_date:
        ed = pd.to_datetime(end_date, errors="coerce")
        if pd.notna(ed):
            dates = pd.to_datetime(df["date"], errors="coerce")
            df = df[dates.isna() | (dates <= ed)]
    if stage:
        df = df[df["stage"].astype("string").str.lower() == stage.lower()]

    df = _sort_by_date(df, ascending=False)
    if limit:
        df = df.head(limit)
    return [_match_row_to_dict(r) for _, r in df.iterrows()]


def head_to_head(
    team_a: str, team_b: str, limit: int = 50
) -> dict[str, Any]:
    """Return matches between two teams plus an aggregated H2H record."""
    matches = find_matches(team=team_a, opponent=team_b, limit=limit)
    ka, kb = team_key(team_a), team_key(team_b)
    a_wins = b_wins = draws = 0
    for m in matches:
        hg, ag = m["home_goal"], m["away_goal"]
        if hg is None or ag is None:
            continue
        home_is_a = team_key(m["home_team"]) == ka
        home_goals, away_goals = (hg, ag) if home_is_a else (ag, hg)
        if home_goals > away_goals:
            a_wins += 1
        elif home_goals < away_goals:
            b_wins += 1
        else:
            draws += 1
    derby = derby_name(team_a, team_b)
    return {
        "team_a": normalize_team(team_a),
        "team_b": normalize_team(team_b),
        "derby": derby,
        "matches_found": len(matches),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "matches": matches,
    }


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------

def _compute_record(df: pd.DataFrame, team: str) -> TeamRecord:
    tk = team_key(team)
    played = wins = draws = losses = gf = ga = 0
    for _, r in df.iterrows():
        hg, ag = r["home_goal"], r["away_goal"]
        if hg is None or ag is None:
            played += 1
            continue
        is_home = r["home_key"] == tk
        my, opp = (hg, ag) if is_home else (ag, hg)
        gf += int(my)
        ga += int(opp)
        if my > opp:
            wins += 1
        elif my < opp:
            losses += 1
        else:
            draws += 1
        played += 1
    return TeamRecord(
        team=normalize_team(team),
        played=played, wins=wins, draws=draws, losses=losses,
        goals_for=gf, goals_against=ga,
    )


def team_statistics(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> dict[str, Any]:
    """Return a team's W/L/D record and goals over a filtered match set.

    venue: "home", "away", or None (both).
    """
    df = load_matches()
    if competition:
        df = _competition_filter(df, competition)
    if season is not None:
        df = _season_filter(df, season)
    if venue == "home":
        df = df[_team_mask(df, team, "home")]
    elif venue == "away":
        df = df[_team_mask(df, team, "away")]
    else:
        df = df[_team_mask(df, team, "either")]
    rec = _compute_record(df, team)
    return rec.to_dict()


def team_competitions(team: str) -> list[dict[str, Any]]:
    """List every competition a team has appeared in, with per-competition record."""
    df = load_matches()
    df = df[_team_mask(df, team, "either")]
    results = []
    for comp in sorted(df["competition"].unique()):
        sub = df[df["competition"] == comp]
        rec = _compute_record(sub, team)
        d = rec.to_dict()
        d["competition"] = comp
        d["seasons"] = sorted(
            int(s) for s in sub["season"].dropna().unique()
        )
        results.append(d)
    return results


# ---------------------------------------------------------------------------
# 3. Player queries
# ---------------------------------------------------------------------------

def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    sort_by: str = "overall",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search the FIFA player database with flexible filters.

    ``position`` is an exact FIFA position code (ST, LW, GK, ...).
    ``position_group`` is one of GK/DEF/MID/FWD.
    """
    df = load_players()
    if name:
        nk = _ascii_lower(name)
        df = df[df["name_key"].str.contains(nk, na=False)]
    if nationality:
        df = df[df["Nationality"].str.lower() == nationality.strip().lower()]
    if club:
        ck = _ascii_lower(club)
        df = df[df["club_key"].str.contains(ck, na=False)]
    if position:
        df = df[df["Position"].str.upper() == position.strip().upper()]
    if position_group:
        codes = POSITION_GROUPS.get(position_group.upper())
        if codes:
            df = df[df["Position"].str.upper().isin(codes)]
    if min_overall is not None:
        df = df[df["Overall"].fillna(-1) >= min_overall]
    if max_overall is not None:
        df = df[df["Overall"].fillna(9999) <= max_overall]

    sort_col = sort_by if sort_by in df.columns else "Overall"
    df = df.sort_values(sort_col, ascending=False).head(limit)
    return [_player_row_to_dict(r) for _, r in df.iterrows()]


def _ascii_lower(s: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _player_row_to_dict(row: pd.Series) -> dict[str, Any]:
    skill_prefix = [
        "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling",
        "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility",
        "Reactions", "ShotPower", "Stamina", "Strength", "Vision", "Composure",
        "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
        "GKKicking", "GKPositioning", "GKReflexes",
    ]
    attrs = {}
    for c in skill_prefix:
        if c in row.index and pd.notna(row[c]):
            try:
                attrs[c] = float(row[c])
            except (TypeError, ValueError):
                pass
    return {
        "id": int(row["ID"]) if pd.notna(row.get("ID")) else None,
        "name": row["Name"],
        "age": int(row["Age"]) if pd.notna(row.get("Age")) else None,
        "nationality": row["Nationality"],
        "overall": int(row["Overall"]) if pd.notna(row.get("Overall")) else None,
        "potential": int(row["Potential"]) if pd.notna(row.get("Potential")) else None,
        "club": row["Club"],
        "position": row["Position"],
        "jersey_number": int(row["Jersey Number"]) if pd.notna(row.get("Jersey Number")) else None,
        "height": row["Height"],
        "weight": row["Weight"],
        "value": row["Value"],
        "wage": row["Wage"],
        "attributes": attrs,
    }


def top_players_at_club(club: str, limit: int = 10) -> list[dict[str, Any]]:
    return search_players(club=club, sort_by="Overall", limit=limit)


# ---------------------------------------------------------------------------
# 4. Competition queries
# ---------------------------------------------------------------------------

def competition_standings(
    competition: str, season: int, top: int | None = None
) -> list[dict[str, Any]]:
    """Calculate a league-style standings table from match results.

    Only league competitions (Brasileirão Série A/B/C) produce a meaningful
    table; for cups we still return a points-sorted summary. Three points for a
    win, one for a draw. Ties broken by goal difference, then goals for.
    """
    df = load_matches()
    df = _competition_filter(df, competition)
    df = _season_filter(df, season)
    # Only matches with scores contribute.
    df = df[df["home_goal"].notna() & df["away_goal"].notna()]

    teams = set(df["home_key"].unique()) | set(df["away_key"].unique())
    table: list[TeamRecord] = []
    for tk in teams:
        sub = df[(df["home_key"] == tk) | (df["away_key"] == tk)]
        # Recover a display name from the data.
        display = normalize_team(team_display(sub, tk))
        rec = _compute_record(sub, display)
        table.append(rec)

    table.sort(key=lambda r: (-r.points, -r.goal_difference, -r.goals_for, r.team))
    if top:
        table = table[:top]
    return [
        Standing(
            position=i + 1,
            team=r.team, played=r.played, wins=r.wins, draws=r.draws,
            losses=r.losses, goals_for=r.goals_for, goals_against=r.goals_against,
            goal_difference=r.goal_difference, points=r.points,
        ).to_dict()
        for i, r in enumerate(table)
    ]


def team_display(df: pd.DataFrame, tk: str) -> str:
    """Recover a display name for a team_key from the rows that mention it."""
    home = df.loc[df["home_key"] == tk, "home_team"]
    if len(home):
        return str(home.iloc[0])
    away = df.loc[df["away_key"] == tk, "away_team"]
    return str(away.iloc[0]) if len(away) else tk


def competition_champion(competition: str, season: int) -> dict[str, Any] | None:
    standings = competition_standings(competition, season, top=1)
    if not standings:
        return None
    champ = standings[0]
    return {"competition": competition, "season": season, "champion": champ["team"],
            "record": champ}


def relegated_teams(competition: str, season: int, n: int = 4) -> list[str] | None:
    """Return the bottom-n teams (default 4, matching Brasileirão relegation)."""
    standings = competition_standings(competition, season)
    if len(standings) < n:
        return None
    return [s["team"] for s in standings[-n:]]


# ---------------------------------------------------------------------------
# 5. Statistical analysis
# ---------------------------------------------------------------------------

def average_goals(
    competition: str | None = None, season: int | None = None
) -> dict[str, Any]:
    df = load_matches()
    if competition:
        df = _competition_filter(df, competition)
    if season is not None:
        df = _season_filter(df, season)
    scored = df[df["home_goal"].notna() & df["away_goal"].notna()]
    if scored.empty:
        return {"matches": 0, "avg_goals_per_match": 0.0}
    total_goals = (scored["home_goal"] + scored["away_goal"]).sum()
    n = len(scored)
    home_wins = int(((scored["home_goal"] > scored["away_goal"])).sum())
    away_wins = int(((scored["away_goal"] > scored["home_goal"])).sum())
    draws = int(((scored["home_goal"] == scored["away_goal"])).sum())
    return {
        "matches": n,
        "total_goals": int(total_goals),
        "avg_goals_per_match": round(float(total_goals) / n, 3),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / n, 4) if n else 0.0,
        "away_win_rate": round(away_wins / n, 4) if n else 0.0,
        "draw_rate": round(draws / n, 4) if n else 0.0,
    }


def biggest_wins(
    competition: str | None = None, season: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    df = load_matches()
    if competition:
        df = _competition_filter(df, competition)
    if season is not None:
        df = _season_filter(df, season)
    df = df[df["home_goal"].notna() & df["away_goal"].notna()].copy()
    df["goal_diff"] = (df["home_goal"] - df["away_goal"]).abs()
    df = df.sort_values(["goal_diff", "home_goal"], ascending=[False, False]).head(limit)
    return [
        {
            "date": r["date"],
            "competition": r["competition"],
            "season": int(r["season"]) if pd.notna(r["season"]) else None,
            "winner": r["home_team"] if r["home_goal"] > r["away_goal"] else r["away_team"],
            "loser": r["away_team"] if r["home_goal"] > r["away_goal"] else r["home_team"],
            "score": f"{int(r['home_goal'])}-{int(r['away_goal'])}",
            "goal_difference": int(r["goal_diff"]),
        }
        for _, r in df.iterrows()
    ]


def best_team_record(
    competition: str | None = None, season: int | None = None,
    venue: str | None = None, metric: str = "win_rate", top: int = 5,
) -> list[dict[str, Any]]:
    """Rank teams by win_rate, points, or goals_for over a filtered match set."""
    df = load_matches()
    if competition:
        df = _competition_filter(df, competition)
    if season is not None:
        df = _season_filter(df, season)
    if venue == "home":
        sub_teams = df["home_key"].unique()
        df = df[_team_mask(df, "", "home")] if False else df  # keep df intact
    # Compute per-team records over the (possibly venue-filtered) subset.
    records: list[TeamRecord] = []
    all_teams: set[str] = set()
    if venue == "home":
        all_teams = set(df["home_key"].unique())
    elif venue == "away":
        all_teams = set(df["away_key"].unique())
    else:
        all_teams = set(df["home_key"].unique()) | set(df["away_key"].unique())

    for tk in all_teams:
        if venue == "home":
            sub = df[df["home_key"] == tk]
        elif venue == "away":
            sub = df[df["away_key"] == tk]
        else:
            sub = df[(df["home_key"] == tk) | (df["away_key"] == tk)]
        if sub.empty:
            continue
        display = normalize_team(team_display(sub, tk))
        rec = _compute_record(sub, display)
        if rec.played == 0:
            continue
        records.append(rec)

    if metric == "points":
        records.sort(key=lambda r: (-r.points, -r.goal_difference))
    elif metric == "goals_for":
        records.sort(key=lambda r: -r.goals_for)
    else:
        records.sort(key=lambda r: (-r.win_rate, -r.played))
    return [r.to_dict() for r in records[:top]]


def derbies(season: int | None = None, competition: str | None = None) -> list[dict[str, Any]]:
    """Find derby matches in the dataset (uses the canonical DERBIES table)."""
    df = load_matches()
    if season is not None:
        df = _season_filter(df, season)
    if competition:
        df = _competition_filter(df, competition)
    # For each derby pair, find their matches against each other.
    from .normalize import DERBY_KEYS
    results: list[dict[str, Any]] = []
    seen_pairs: set[frozenset[str]] = set()
    for _, r in df.iterrows():
        pair = frozenset({r["home_key"], r["away_key"]})
        name = DERBY_KEYS.get(pair)
        if name and pair not in seen_pairs:
            seen_pairs.add(pair)
            sub = df[(df["home_key"].isin(pair)) & (df["away_key"].isin(pair))]
            sub = sub[
                (sub["home_key"].isin(pair) & sub["away_key"].isin(pair))
            ]
            results.append({
                "derby": name,
                "teams": sorted({
                    normalize_team(r["home_team"]), normalize_team(r["away_team"])
                }),
                "matches_found": len(sub),
            })
    return results


def data_summary() -> dict[str, Any]:
    from .loader import get_data_summary
    return get_data_summary()
