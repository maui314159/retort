"""
Brazilian Soccer MCP Server.

Exposes tools for querying Brazilian soccer data (matches, teams, players,
standings, and statistics) via the Model Context Protocol.

Run with:
    python server.py
Or via MCP runner / Claude Desktop config.
"""

from __future__ import annotations

import json
from typing import Optional

import pandas as pd
from mcp.server.fastmcp import FastMCP

from data_loader import (
    load_all_matches,
    load_players,
    normalize_team,
    team_matches,
)

mcp = FastMCP(
    "Brazilian Soccer",
    instructions=(
        "Provides structured data about Brazilian soccer: "
        "matches, team statistics, player info, standings, and analysis."
    ),
)

# Pre-warm caches at import time so first tool call isn't slow.
def _warm():
    load_all_matches()
    load_players()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMP_ALIASES: dict[str, str] = {
    "brasileirao": "Brasileirao",
    "serie a": "Brasileirao",
    "campeonato brasileiro": "Brasileirao",
    "copa do brasil": "Copa do Brasil",
    "copa brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
    "br-football": "br-football",
}


def _resolve_competition(name: str) -> str | None:
    return _COMP_ALIASES.get(name.lower().strip())


def _df_to_match_rows(df: pd.DataFrame, limit: int = 50) -> list[dict]:
    rows = []
    for _, r in df.head(limit).iterrows():
        date_str = r["date"].strftime("%Y-%m-%d") if pd.notna(r["date"]) else "unknown"
        rows.append({
            "date": date_str,
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "home_goal": int(r["home_goal"]) if pd.notna(r["home_goal"]) else None,
            "away_goal": int(r["away_goal"]) if pd.notna(r["away_goal"]) else None,
            "competition": r.get("competition", ""),
            "season": int(r["season"]) if pd.notna(r.get("season")) else None,
            "round": str(r.get("round", "")),
        })
    return rows


# ---------------------------------------------------------------------------
# Tool: search_matches
# ---------------------------------------------------------------------------

@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    team2: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 30,
) -> str:
    """
    Search for matches by team(s), competition, season, or date range.

    Args:
        team: Team name (partial match, e.g. "Flamengo").
        team2: Second team for head-to-head search (e.g. "Fluminense").
        competition: "Brasileirao", "Copa do Brasil", or "Copa Libertadores".
        season: Four-digit year (e.g. 2023).
        date_from: Start date ISO format "YYYY-MM-DD".
        date_to: End date ISO format "YYYY-MM-DD".
        limit: Maximum matches to return (default 30, max 200).

    Returns:
        JSON string with matched matches and summary statistics.
    """
    limit = min(limit, 200)
    df = load_all_matches()
    mask = pd.Series([True] * len(df), index=df.index)

    if team:
        nt = normalize_team(team)
        mask &= (
            df["home_norm"].str.contains(nt, case=False, na=False)
            | df["away_norm"].str.contains(nt, case=False, na=False)
        )

    if team2:
        nt2 = normalize_team(team2)
        mask &= (
            df["home_norm"].str.contains(nt2, case=False, na=False)
            | df["away_norm"].str.contains(nt2, case=False, na=False)
        )

    if competition:
        resolved = _resolve_competition(competition)
        if resolved and resolved != "br-football":
            mask &= df["competition"] == resolved
        elif resolved == "br-football":
            pass  # BR-Football-Dataset uses descriptive tournament names
        else:
            mask &= df["competition"].str.contains(competition, case=False, na=False)

    if season:
        mask &= df["season"] == season

    if date_from:
        mask &= df["date"] >= pd.to_datetime(date_from)

    if date_to:
        mask &= df["date"] <= pd.to_datetime(date_to)

    filtered = df[mask].sort_values("date", ascending=False)
    total = len(filtered)
    matches = _df_to_match_rows(filtered, limit)

    # Head-to-head summary when both teams specified
    h2h = None
    if team and team2:
        nt = normalize_team(team)
        nt2 = normalize_team(team2)
        t1_home = filtered[
            filtered["home_norm"].str.contains(nt, case=False, na=False)
        ]
        t1_wins = int((t1_home["home_goal"] > t1_home["away_goal"]).sum())
        t2_home = filtered[
            filtered["home_norm"].str.contains(nt2, case=False, na=False)
        ]
        t2_wins = int((t2_home["home_goal"] > t2_home["away_goal"]).sum())
        draws_total = int((filtered["home_goal"] == filtered["away_goal"]).sum())
        h2h = {
            f"{team}_wins": t1_wins,
            f"{team2}_wins": t2_wins,
            "draws": draws_total,
            "total_matches": total,
        }

    result: dict = {
        "total_found": total,
        "showing": len(matches),
        "matches": matches,
    }
    if h2h:
        result["head_to_head"] = h2h

    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tool: get_team_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """
    Get win/draw/loss record, goals scored/conceded for a team.

    Args:
        team: Team name (partial match).
        competition: Filter by competition name.
        season: Filter by year.
        home_only: Only count home matches.
        away_only: Only count away matches.

    Returns:
        JSON with team stats.
    """
    df = load_all_matches()
    nt = normalize_team(team)

    if competition:
        resolved = _resolve_competition(competition)
        if resolved and resolved != "br-football":
            df = df[df["competition"] == resolved]
        else:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]

    if season:
        df = df[df["season"] == season]

    home_mask = df["home_norm"].str.contains(nt, case=False, na=False)
    away_mask = df["away_norm"].str.contains(nt, case=False, na=False)

    if home_only:
        rows = df[home_mask]
    elif away_only:
        rows = df[away_mask]
    else:
        rows = df[home_mask | away_mask]

    if rows.empty:
        return json.dumps({"error": f"No matches found for '{team}'"})

    home_rows = rows[rows["home_norm"].str.contains(nt, case=False, na=False)]
    away_rows = rows[rows["away_norm"].str.contains(nt, case=False, na=False)]

    hw = int((home_rows["home_goal"] > home_rows["away_goal"]).sum())
    hd = int((home_rows["home_goal"] == home_rows["away_goal"]).sum())
    hl = int((home_rows["home_goal"] < home_rows["away_goal"]).sum())
    hgf = int(home_rows["home_goal"].sum())
    hga = int(home_rows["away_goal"].sum())

    aw = int((away_rows["away_goal"] > away_rows["home_goal"]).sum())
    ad = int((away_rows["away_goal"] == away_rows["home_goal"]).sum())
    al = int((away_rows["away_goal"] < away_rows["home_goal"]).sum())
    agf = int(away_rows["away_goal"].sum())
    aga = int(away_rows["home_goal"].sum())

    total = len(rows)
    wins = hw + aw
    draws = hd + ad
    losses = hl + al
    gf = hgf + agf
    ga = hga + aga
    pts = wins * 3 + draws
    win_rate = round(wins / total * 100, 1) if total else 0

    competitions_played = rows["competition"].value_counts().to_dict()

    return json.dumps({
        "team": team,
        "filters": {
            "competition": competition,
            "season": season,
            "home_only": home_only,
            "away_only": away_only,
        },
        "total_matches": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": pts,
        "win_rate_pct": win_rate,
        "home": {"matches": len(home_rows), "wins": hw, "draws": hd, "losses": hl,
                 "goals_for": hgf, "goals_against": hga},
        "away": {"matches": len(away_rows), "wins": aw, "draws": ad, "losses": al,
                 "goals_for": agf, "goals_against": aga},
        "competitions": competitions_played,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: get_standings
# ---------------------------------------------------------------------------

@mcp.tool()
def get_standings(
    season: int,
    competition: str = "Brasileirao",
) -> str:
    """
    Calculate league standings for a given season from match results.

    Args:
        season: Four-digit year (e.g. 2019).
        competition: "Brasileirao" (default), "Copa do Brasil", or "Copa Libertadores".

    Returns:
        JSON with sorted standings table.
    """
    df = load_all_matches()
    resolved = _resolve_competition(competition) or competition
    df = df[(df["competition"] == resolved) & (df["season"] == season)]

    if df.empty:
        return json.dumps({"error": f"No data for {competition} {season}"})

    table: dict[str, dict] = {}

    def _ensure(t: str):
        if t not in table:
            table[t] = {"team": t, "P": 0, "W": 0, "D": 0, "L": 0,
                        "GF": 0, "GA": 0, "GD": 0, "Pts": 0}

    for _, r in df.iterrows():
        ht = r["home_team"]
        at = r["away_team"]
        hg = r["home_goal"]
        ag = r["away_goal"]
        _ensure(ht)
        _ensure(at)

        table[ht]["P"] += 1
        table[ht]["GF"] += hg
        table[ht]["GA"] += ag
        table[at]["P"] += 1
        table[at]["GF"] += ag
        table[at]["GA"] += hg

        if hg > ag:
            table[ht]["W"] += 1
            table[ht]["Pts"] += 3
            table[at]["L"] += 1
        elif hg < ag:
            table[at]["W"] += 1
            table[at]["Pts"] += 3
            table[ht]["L"] += 1
        else:
            table[ht]["D"] += 1
            table[ht]["Pts"] += 1
            table[at]["D"] += 1
            table[at]["Pts"] += 1

    for t in table.values():
        t["GD"] = t["GF"] - t["GA"]

    sorted_table = sorted(
        table.values(),
        key=lambda x: (x["Pts"], x["GD"], x["GF"]),
        reverse=True,
    )
    for i, row in enumerate(sorted_table, 1):
        row["position"] = i

    return json.dumps({
        "competition": resolved,
        "season": season,
        "teams": len(sorted_table),
        "standings": sorted_table,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: get_biggest_wins
# ---------------------------------------------------------------------------

@mcp.tool()
def get_biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """
    Return matches with the largest goal margin.

    Args:
        competition: Filter by competition.
        season: Filter by year.
        limit: Number of results (default 10).

    Returns:
        JSON list of biggest wins sorted by goal difference.
    """
    df = load_all_matches()

    if competition:
        resolved = _resolve_competition(competition)
        if resolved and resolved != "br-football":
            df = df[df["competition"] == resolved]
        else:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]

    if season:
        df = df[df["season"] == season]

    df = df.copy()
    df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
    top = df.nlargest(limit, "margin")

    results = []
    for _, r in top.iterrows():
        date_str = r["date"].strftime("%Y-%m-%d") if pd.notna(r["date"]) else "unknown"
        results.append({
            "date": date_str,
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "score": f"{int(r['home_goal'])}-{int(r['away_goal'])}",
            "margin": int(r["margin"]),
            "competition": r["competition"],
            "season": int(r["season"]) if pd.notna(r.get("season")) else None,
        })

    return json.dumps({"biggest_wins": results}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: get_competition_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_competition_stats(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """
    Get aggregate statistics: goals per match, home win rate, draw rate.

    Args:
        competition: Filter by competition name.
        season: Filter by year.

    Returns:
        JSON with aggregated statistics.
    """
    df = load_all_matches()

    if competition:
        resolved = _resolve_competition(competition)
        if resolved and resolved != "br-football":
            df = df[df["competition"] == resolved]
        else:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]

    if season:
        df = df[df["season"] == season]

    if df.empty:
        return json.dumps({"error": "No data for the given filters"})

    total = len(df)
    home_wins = int((df["home_goal"] > df["away_goal"]).sum())
    away_wins = int((df["home_goal"] < df["away_goal"]).sum())
    draws = int((df["home_goal"] == df["away_goal"]).sum())
    total_goals = float(df["home_goal"].sum() + df["away_goal"].sum())
    avg_goals = round(total_goals / total, 2)

    seasons_covered = sorted(df["season"].dropna().unique().tolist())

    return json.dumps({
        "filters": {"competition": competition, "season": season},
        "total_matches": total,
        "total_goals": int(total_goals),
        "avg_goals_per_match": avg_goals,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate_pct": round(home_wins / total * 100, 1),
        "away_win_rate_pct": round(away_wins / total * 100, 1),
        "draw_rate_pct": round(draws / total * 100, 1),
        "seasons_covered": [int(s) for s in seasons_covered if pd.notna(s)],
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: search_players
# ---------------------------------------------------------------------------

@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """
    Search FIFA player database by name, nationality, club, or position.

    Args:
        name: Partial player name (case-insensitive).
        nationality: e.g. "Brazil", "Brazilian".
        club: Club name (partial match, e.g. "Flamengo").
        position: e.g. "GK", "ST", "CAM", "LW".
        min_overall: Minimum overall rating.
        limit: Max results (default 20).

    Returns:
        JSON list of matching players.
    """
    limit = min(limit, 200)
    df = load_players()
    mask = pd.Series([True] * len(df), index=df.index)

    if name:
        mask &= df["name_norm"].str.contains(name.lower(), na=False)

    if nationality:
        nat_lower = nationality.lower().replace("brazilian", "brazil")
        mask &= df["nationality_norm"].str.contains(nat_lower, na=False)

    if club:
        mask &= df["club_norm"].str.contains(club.lower(), na=False)

    if position:
        mask &= df["Position"].str.contains(position.upper(), na=False)

    if min_overall is not None:
        mask &= df["Overall"] >= min_overall

    filtered = df[mask].sort_values("Overall", ascending=False)
    total = len(filtered)

    cols = ["Name", "Age", "Nationality", "Overall", "Potential",
            "Club", "Position", "Jersey Number"]
    cols = [c for c in cols if c in filtered.columns]

    players = []
    for _, r in filtered.head(limit).iterrows():
        p = {c: r[c] for c in cols}
        # Clean up NaN
        for k, v in p.items():
            if isinstance(v, float) and pd.isna(v):
                p[k] = None
        players.append(p)

    return json.dumps({
        "total_found": total,
        "showing": len(players),
        "players": players,
    }, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tool: get_best_teams
# ---------------------------------------------------------------------------

@mcp.tool()
def get_best_teams(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    metric: str = "win_rate",
    limit: int = 10,
) -> str:
    """
    Rank teams by win rate, goals scored, or points.

    Args:
        competition: Filter by competition.
        season: Filter by year.
        metric: "win_rate", "goals_scored", "points", or "away_win_rate".
        limit: Number of teams to return (default 10).

    Returns:
        JSON ranked team list.
    """
    df = load_all_matches()

    if competition:
        resolved = _resolve_competition(competition)
        if resolved and resolved != "br-football":
            df = df[df["competition"] == resolved]
        else:
            df = df[df["competition"].str.contains(competition, case=False, na=False)]

    if season:
        df = df[df["season"] == season]

    if df.empty:
        return json.dumps({"error": "No data for the given filters"})

    table: dict[str, dict] = {}

    def _ensure(t):
        if t not in table:
            table[t] = {"team": t, "matches": 0, "wins": 0, "draws": 0,
                        "losses": 0, "goals_for": 0, "goals_against": 0,
                        "pts": 0, "home_matches": 0, "home_wins": 0,
                        "away_matches": 0, "away_wins": 0}

    for _, r in df.iterrows():
        ht, at = r["home_team"], r["away_team"]
        hg, ag = r["home_goal"], r["away_goal"]
        _ensure(ht)
        _ensure(at)

        table[ht]["matches"] += 1
        table[ht]["home_matches"] += 1
        table[ht]["goals_for"] += hg
        table[ht]["goals_against"] += ag

        table[at]["matches"] += 1
        table[at]["away_matches"] += 1
        table[at]["goals_for"] += ag
        table[at]["goals_against"] += hg

        if hg > ag:
            table[ht]["wins"] += 1
            table[ht]["home_wins"] += 1
            table[ht]["pts"] += 3
            table[at]["losses"] += 1
        elif hg < ag:
            table[at]["wins"] += 1
            table[at]["away_wins"] += 1
            table[at]["pts"] += 3
            table[ht]["losses"] += 1
        else:
            table[ht]["draws"] += 1
            table[ht]["pts"] += 1
            table[at]["draws"] += 1
            table[at]["pts"] += 1

    for t in table.values():
        m = t["matches"]
        t["win_rate"] = round(t["wins"] / m * 100, 1) if m else 0
        am = t["away_matches"]
        t["away_win_rate"] = round(t["away_wins"] / am * 100, 1) if am else 0

    sort_key = {
        "win_rate": "win_rate",
        "goals_scored": "goals_for",
        "points": "pts",
        "away_win_rate": "away_win_rate",
    }.get(metric, "win_rate")

    sorted_teams = sorted(table.values(), key=lambda x: x[sort_key], reverse=True)[:limit]

    return json.dumps({
        "competition": competition,
        "season": season,
        "metric": metric,
        "teams": sorted_teams,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool: list_competitions
# ---------------------------------------------------------------------------

@mcp.tool()
def list_competitions() -> str:
    """
    List all competitions and seasons available in the dataset.

    Returns:
        JSON with competitions and year ranges.
    """
    df = load_all_matches()
    result = {}
    for comp, group in df.groupby("competition"):
        seasons = sorted(group["season"].dropna().unique().tolist())
        result[comp] = {
            "matches": len(group),
            "seasons": [int(s) for s in seasons if pd.notna(s)],
        }

    return json.dumps({"competitions": result}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _warm()
    mcp.run()
