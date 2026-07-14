"""
Brazilian Soccer MCP Server
============================
An MCP (Model Context Protocol) server that exposes Brazilian soccer data
through five tool categories: match queries, team queries, player queries,
competition queries, and statistical analysis.

Uses FastMCP from the `mcp` Python SDK. Data is loaded lazily from CSV
files via data_loader.SoccerData and served as structured JSON.

Run with:
    mcp dev server.py
or:
    python server.py
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from mcp.server.fastmcp import FastMCP

from data_loader import SoccerData, normalize_team

# ── Server + data ────────────────────────────────────────────────────

mcp = FastMCP("brazilian-soccer-mcp")
data = SoccerData()


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to JSON-safe records, handling NaN/NaT."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _team_stats(df: pd.DataFrame, team: str) -> dict[str, Any]:
    """Compute win/draw/loss + goals from a DataFrame of one team's matches."""
    t = normalize_team(team)
    home = df[df["home_team"] == t]
    away = df[df["away_team"] == t]

    wins = len(home[home["home_goal"] > home["away_goal"]]) + len(
        away[away["away_goal"] > away["home_goal"]]
    )
    draws = len(home[home["home_goal"] == home["away_goal"]]) + len(
        away[away["away_goal"] == away["home_goal"]]
    )
    losses = len(home[home["home_goal"] < home["away_goal"]]) + len(
        away[away["away_goal"] < away["home_goal"]]
    )
    gf = int(home["home_goal"].sum() + away["away_goal"].sum())
    ga = int(home["away_goal"].sum() + away["home_goal"].sum())
    total = wins + draws + losses

    return {
        "team": t,
        "matches": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "win_rate": round(wins / total, 3) if total else 0.0,
    }


# ═════════════════════════════════════════════════════════════════════
# 1. MATCH QUERIES
# ═════════════════════════════════════════════════════════════════════

@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    side: str = "either",
    limit: int = 50,
) -> str:
    """Search matches by team, opponent, competition, season, and/or date range.

    Args:
        team: Team name to search for.
        opponent: Opponent team name (finds matches where both team and opponent play).
        competition: Competition name (e.g. "Brasileirão", "Copa do Brasil", "Copa Libertadores").
        season: Year of the season.
        date_from: Start date (ISO format, e.g. "2023-01-01").
        date_to: End date (ISO format).
        side: "home", "away", or "either" (default).
        limit: Maximum number of matches to return (default 50).
    """
    all_m = data.all_matches()

    if team:
        t = normalize_team(team)
        if side == "home":
            mask = all_m["home_team"] == t
        elif side == "away":
            mask = all_m["away_team"] == t
        else:
            mask = (all_m["home_team"] == t) | (all_m["away_team"] == t)
        all_m = all_m[mask]

    if opponent:
        o = normalize_team(opponent)
        opp_mask = (all_m["home_team"] == o) | (all_m["away_team"] == o)
        all_m = all_m[opp_mask]

    if competition:
        comp_lower = competition.lower()
        all_m = all_m[all_m["competition"].str.lower().str.contains(comp_lower, na=False)]

    if season is not None:
        all_m = all_m[all_m["season"] == season]

    if date_from:
        all_m = all_m[all_m["date"] >= pd.Timestamp(date_from)]
    if date_to:
        all_m = all_m[all_m["date"] <= pd.Timestamp(date_to)]

    all_m = all_m.sort_values("date", ascending=False).head(limit)
    return json.dumps(_df_to_records(all_m), ensure_ascii=False, indent=2)


@mcp.tool()
def head_to_head(team_a: str, team_b: str) -> str:
    """Get head-to-head record between two teams across all competitions.

    Args:
        team_a: First team name.
        team_b: Second team name.
    """
    a = normalize_team(team_a)
    b = normalize_team(team_b)
    all_m = data.all_matches()
    matches = all_m[
        ((all_m["home_team"] == a) & (all_m["away_team"] == b))
        | ((all_m["home_team"] == b) & (all_m["away_team"] == a))
    ].sort_values("date", ascending=False)

    a_wins = 0
    b_wins = 0
    draws = 0
    for _, row in matches.iterrows():
        hg, ag = row["home_goal"], row["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        if hg == ag:
            draws += 1
        elif row["home_team"] == a and hg > ag:
            a_wins += 1
        elif row["away_team"] == a and ag > hg:
            a_wins += 1
        else:
            b_wins += 1

    result = {
        "team_a": a,
        "team_b": b,
        "total_matches": len(matches),
        f"{a}_wins": a_wins,
        f"{b}_wins": b_wins,
        "draws": draws,
        "matches": _df_to_records(matches.head(30)),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ═════════════════════════════════════════════════════════════════════
# 2. TEAM QUERIES
# ═════════════════════════════════════════════════════════════════════

@mcp.tool()
def team_statistics(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    side: str = "either",
) -> str:
    """Get win/draw/loss record, goals for/against, and win rate for a team.

    Args:
        team: Team name.
        competition: Optional competition filter.
        season: Optional season filter.
        side: "home", "away", or "either" (default).
    """
    matches = data.find_team_matches(team, side=side)

    if competition:
        comp_lower = competition.lower()
        matches = matches[matches["competition"].str.lower().str.contains(comp_lower, na=False)]

    if season is not None:
        matches = matches[matches["season"] == season]

    # Filter to matches with valid scores
    valid = matches.dropna(subset=["home_goal", "away_goal"])
    stats = _team_stats(valid, team)

    t = normalize_team(team)
    # Home/away breakdown
    home_m = valid[valid["home_team"] == t]
    away_m = valid[valid["away_team"] == t]
    stats["home"] = _team_stats(home_m, team) if len(home_m) else None
    stats["away"] = _team_stats(away_m, team) if len(away_m) else None

    return json.dumps(stats, ensure_ascii=False, indent=2)


@mcp.tool()
def top_teams_by_goals(
    competition: str | None = None,
    season: int | None = None,
    side: str = "either",
    limit: int = 10,
) -> str:
    """Rank teams by total goals scored.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        side: "home", "away", or "either" (default).
        limit: Number of top teams to return (default 10).
    """
    all_m = data.all_matches()
    if competition:
        comp_lower = competition.lower()
        all_m = all_m[all_m["competition"].str.lower().str.contains(comp_lower, na=False)]
    if season is not None:
        all_m = all_m[all_m["season"] == season]

    all_m = all_m.dropna(subset=["home_goal", "away_goal"])

    goal_map: dict[str, int] = {}
    for _, row in all_m.iterrows():
        ht, at = row["home_team"], row["away_team"]
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        if side in ("either", "home"):
            goal_map[ht] = goal_map.get(ht, 0) + hg
        if side in ("either", "away"):
            goal_map[at] = goal_map.get(at, 0) + ag

    ranked = sorted(goal_map.items(), key=lambda x: x[1], reverse=True)[:limit]
    return json.dumps(
        [{"team": t, "goals": g} for t, g in ranked],
        ensure_ascii=False, indent=2,
    )


# ═════════════════════════════════════════════════════════════════════
# 3. PLAYER QUERIES
# ═════════════════════════════════════════════════════════════════════

@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
) -> str:
    """Search FIFA player database by name, nationality, club, position, and/or rating.

    Args:
        name: Partial player name to search for.
        nationality: Nationality filter (e.g. "Brazil").
        club: Club name filter (partial match).
        position: Position filter (e.g. "ST", "GK", "LW").
        min_overall: Minimum overall rating.
        limit: Maximum results (default 20).
    """
    df = data.players.copy()

    if name:
        df = df[df["Name"].str.contains(name, case=False, na=False)]
    if nationality:
        df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
    if club:
        df = df[df["Club"].str.contains(club, case=False, na=False)]
    if position:
        df = df[df["Position"].str.contains(position, case=False, na=False)]
    if min_overall is not None:
        df = df[df["Overall"] >= min_overall]

    df = df.sort_values("Overall", ascending=False).head(limit)
    cols = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position"]
    available = [c for c in cols if c in df.columns]
    return json.dumps(_df_to_records(df[available]), ensure_ascii=False, indent=2)


@mcp.tool()
def players_at_club(club: str, nationality: str | None = None, limit: int = 30) -> str:
    """List players at a given club, optionally filtered by nationality.

    Args:
        club: Club name (partial match).
        nationality: Optional nationality filter.
        limit: Maximum results (default 30).
    """
    df = data.players[data.players["Club"].str.contains(club, case=False, na=False)]
    if nationality:
        df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
    df = df.sort_values("Overall", ascending=False).head(limit)
    cols = ["Name", "Age", "Nationality", "Overall", "Position", "Jersey Number"]
    available = [c for c in cols if c in df.columns]
    return json.dumps(_df_to_records(df[available]), ensure_ascii=False, indent=2)


# ═════════════════════════════════════════════════════════════════════
# 4. COMPETITION QUERIES
# ═════════════════════════════════════════════════════════════════════

@mcp.tool()
def competition_standings(competition: str, season: int) -> str:
    """Calculate league-style standings for a competition and season from match results.
    Uses 3 points for a win, 1 for a draw.

    Args:
        competition: Competition name (e.g. "Brasileirão").
        season: Season year.
    """
    all_m = data.all_matches()
    comp_lower = competition.lower()
    matches = all_m[
        all_m["competition"].str.lower().str.contains(comp_lower, na=False)
        & (all_m["season"] == season)
    ].dropna(subset=["home_goal", "away_goal"])

    if matches.empty:
        return json.dumps({"error": f"No matches found for {competition} {season}"})

    table: dict[str, dict[str, int]] = {}

    for _, row in matches.iterrows():
        ht, at = row["home_team"], row["away_team"]
        hg, ag = int(row["home_goal"]), int(row["away_goal"])

        for team in (ht, at):
            if team not in table:
                table[team] = {"points": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "played": 0}

        table[ht]["played"] += 1
        table[at]["played"] += 1
        table[ht]["gf"] += hg
        table[ht]["ga"] += ag
        table[at]["gf"] += ag
        table[at]["ga"] += hg

        if hg > ag:
            table[ht]["wins"] += 1
            table[ht]["points"] += 3
            table[at]["losses"] += 1
        elif hg < ag:
            table[at]["wins"] += 1
            table[at]["points"] += 3
            table[ht]["losses"] += 1
        else:
            table[ht]["draws"] += 1
            table[at]["draws"] += 1
            table[ht]["points"] += 1
            table[at]["points"] += 1

    ranked = sorted(table.items(), key=lambda x: (x[1]["points"], x[1]["gf"] - x[1]["ga"]), reverse=True)
    result = []
    for i, (team, stats) in enumerate(ranked, 1):
        result.append({
            "position": i,
            "team": team,
            **stats,
            "goal_difference": stats["gf"] - stats["ga"],
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def list_competitions() -> str:
    """List all competitions found in the dataset."""
    all_m = data.all_matches()
    comps = all_m["competition"].value_counts().to_dict()
    return json.dumps(comps, ensure_ascii=False, indent=2)


@mcp.tool()
def list_seasons(competition: str | None = None) -> str:
    """List available seasons, optionally filtered by competition.

    Args:
        competition: Optional competition name filter.
    """
    all_m = data.all_matches()
    if competition:
        comp_lower = competition.lower()
        all_m = all_m[all_m["competition"].str.lower().str.contains(comp_lower, na=False)]
    seasons = sorted(all_m["season"].dropna().unique().astype(int).tolist())
    return json.dumps(seasons)


# ═════════════════════════════════════════════════════════════════════
# 5. STATISTICAL ANALYSIS
# ═════════════════════════════════════════════════════════════════════

@mcp.tool()
def avg_goals_per_match(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Calculate average goals per match, optionally filtered.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
    """
    all_m = data.all_matches()
    if competition:
        comp_lower = competition.lower()
        all_m = all_m[all_m["competition"].str.lower().str.contains(comp_lower, na=False)]
    if season is not None:
        all_m = all_m[all_m["season"] == season]

    valid = all_m.dropna(subset=["home_goal", "away_goal"])
    total_goals = (valid["home_goal"] + valid["away_goal"]).sum()
    n = len(valid)

    home_wins = len(valid[valid["home_goal"] > valid["away_goal"]])
    away_wins = len(valid[valid["away_goal"] > valid["home_goal"]])
    draws = len(valid[valid["home_goal"] == valid["away_goal"]])

    result = {
        "total_matches": n,
        "total_goals": int(total_goals),
        "avg_goals_per_match": round(total_goals / n, 2) if n else 0,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / n, 3) if n else 0,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Find the biggest victories (largest goal difference).

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        limit: Number of results (default 10).
    """
    all_m = data.all_matches()
    if competition:
        comp_lower = competition.lower()
        all_m = all_m[all_m["competition"].str.lower().str.contains(comp_lower, na=False)]
    if season is not None:
        all_m = all_m[all_m["season"] == season]

    valid = all_m.dropna(subset=["home_goal", "away_goal"]).copy()
    valid["goal_diff"] = (valid["home_goal"] - valid["away_goal"]).abs()
    valid = valid.sort_values("goal_diff", ascending=False).head(limit)

    results = []
    for _, row in valid.iterrows():
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        results.append({
            "date": str(row["date"])[:10] if pd.notna(row["date"]) else None,
            "home": row["home_team"],
            "away": row["away_team"],
            "score": f"{hg}-{ag}",
            "goal_difference": int(row["goal_diff"]),
            "competition": row.get("competition", ""),
        })
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def home_vs_away(competition: str | None = None, season: int | None = None) -> str:
    """Compare home vs away performance: win rates, avg goals.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
    """
    all_m = data.all_matches()
    if competition:
        comp_lower = competition.lower()
        all_m = all_m[all_m["competition"].str.lower().str.contains(comp_lower, na=False)]
    if season is not None:
        all_m = all_m[all_m["season"] == season]

    valid = all_m.dropna(subset=["home_goal", "away_goal"])
    n = len(valid)
    if n == 0:
        return json.dumps({"error": "No matches found"})

    home_wins = len(valid[valid["home_goal"] > valid["away_goal"]])
    away_wins = len(valid[valid["away_goal"] > valid["home_goal"]])
    draws = n - home_wins - away_wins

    result = {
        "total_matches": n,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / n, 3),
        "away_win_rate": round(away_wins / n, 3),
        "avg_home_goals": round(valid["home_goal"].mean(), 2),
        "avg_away_goals": round(valid["away_goal"].mean(), 2),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Entry point ──────────────────────────────────────────────────────

def main():
    mcp.run()


if __name__ == "__main__":
    main()
