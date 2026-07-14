"""Brazilian Soccer MCP Server using FastMCP."""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
import pandas as pd

from data_loader import (
    get_matches_df,
    get_players_df,
    normalize_team_name,
    normalize_date,
    clear_cache,
)

mcp = FastMCP("Brazilian Soccer MCP Server")


def _format_match_row(row: pd.Series) -> str:
    """Format a single match row for output."""
    date = row.get("date", "")
    home = row.get("home_team", "")
    away = row.get("away_team", "")
    home_g = row.get("home_goals", "-")
    away_g = row.get("away_goals", "-")
    comp = row.get("competition", "")
    round_num = row.get("round", "")
    
    round_str = f" (Round {round_num})" if round_num else ""
    return f"- {date}: {home} {home_g}-{away_g} {away} [{comp}{round_str}]"


@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    Search for soccer matches based on various criteria.
    
    Args:
        team: Team name (matches home or away). Normalized automatically.
        home_team: Home team name.
        away_team: Away team name.
        competition: Competition name (e.g., "Brasileirão", "Copa do Brasil", "Libertadores").
        season: Year/season (e.g., "2023").
        date_from: Start date in YYYY-MM-DD format.
        date_to: End date in YYYY-MM-DD format.
        limit: Maximum number of results to return.
    """
    df = get_matches_df().copy()
    
    if team:
        norm_team = normalize_team_name(team)
        mask = df["home_team"].str.contains(norm_team, case=False, na=False) | \
               df["away_team"].str.contains(norm_team, case=False, na=False)
        df = df[mask]
    
    if home_team:
        norm_home = normalize_team_name(home_team)
        df = df[df["home_team"].str.contains(norm_home, case=False, na=False)]
    
    if away_team:
        norm_away = normalize_team_name(away_team)
        df = df[df["away_team"].str.contains(norm_away, case=False, na=False)]
    
    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    
    if season:
        df = df[df["season"].astype(str) == str(season)]
    
    if date_from:
        df = df[df["date"] >= date_from]
    
    if date_to:
        df = df[df["date"] <= date_to]
    
    # Sort by date descending
    df = df.sort_values("date", ascending=False).head(limit)
    
    if df.empty:
        return "No matches found matching the criteria."
    
    total_matches = len(df)
    lines = [f"Found {total_matches} match(es):", ""]
    for _, row in df.iterrows():
        lines.append(_format_match_row(row))
    
    return "\n".join(lines)


@mcp.tool()
def get_team_stats(
    team: str,
    season: Optional[str] = None,
    competition: Optional[str] = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """
    Get statistics for a specific team.
    
    Args:
        team: Team name to get stats for.
        season: Filter by season/year.
        competition: Filter by competition.
        home_only: Only include matches where team played at home.
        away_only: Only include matches where team played away.
    """
    df = get_matches_df().copy()
    norm_team = normalize_team_name(team)
    
    # Filter by team
    home_mask = df["home_team"].str.contains(norm_team, case=False, na=False)
    away_mask = df["away_team"].str.contains(norm_team, case=False, na=False)
    
    # Fill NA goals with 0 for safe comparison
    df["home_goals"] = df["home_goals"].fillna(0).astype(int)
    df["away_goals"] = df["away_goals"].fillna(0).astype(int)
    
    if home_only:
        df = df[home_mask].copy()
        df["result"] = df.apply(lambda r: "W" if r["home_goals"] > r["away_goals"] else
                                          ("D" if r["home_goals"] == r["away_goals"] else "L"), axis=1)
    elif away_only:
        df = df[away_mask].copy()
        df["result"] = df.apply(lambda r: "W" if r["away_goals"] > r["home_goals"] else
                                          ("D" if r["away_goals"] == r["home_goals"] else "L"), axis=1)
    else:
        df = df[home_mask | away_mask].copy()
        df["result"] = df.apply(
            lambda r: "W" if (r["home_team"].lower() == norm_team and r["home_goals"] > r["away_goals"]) or
                             (r["away_team"].lower() == norm_team and r["away_goals"] > r["home_goals"]) else
                     ("D" if r["home_goals"] == r["away_goals"] else "L"), axis=1
        )
        df["is_home"] = df["home_team"].str.contains(norm_team, case=False, na=False)
    
    if season:
        df = df[df["season"].astype(str) == str(season)]
    
    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    
    if df.empty:
        return f"No matches found for {team} with the given criteria."
    
    total_matches = len(df)
    wins = (df["result"] == "W").sum()
    draws = (df["result"] == "D").sum()
    losses = (df["result"] == "L").sum()
    
    goals_for = 0
    goals_against = 0
    for _, row in df.iterrows():
        if home_only or (not away_only and row.get("is_home", False)):
            goals_for += row["home_goals"] if pd.notna(row["home_goals"]) else 0
            goals_against += row["away_goals"] if pd.notna(row["away_goals"]) else 0
        else:
            goals_for += row["away_goals"] if pd.notna(row["away_goals"]) else 0
            goals_against += row["home_goals"] if pd.notna(row["home_goals"]) else 0
    
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
    
    lines = [
        f"Statistics for {team.title()}:",
        f"- Total Matches: {total_matches}",
        f"- Record: {wins}W - {draws}D - {losses}L",
        f"- Goals For: {goals_for}, Goals Against: {goals_against}",
        f"- Win Rate: {win_rate:.1f}%",
    ]
    
    return "\n".join(lines)


@mcp.tool()
def get_head_to_head(
    team1: str,
    team2: str,
    limit: int = 10,
) -> str:
    """
    Get head-to-head record and recent matches between two teams.
    
    Args:
        team1: First team name.
        team2: Second team name.
        limit: Maximum number of recent matches to show.
    """
    df = get_matches_df().copy()
    norm_t1 = normalize_team_name(team1)
    norm_t2 = normalize_team_name(team2)
    
    # Find matches where either team is involved
    t1_home = df["home_team"].str.contains(norm_t1, case=False, na=False)
    t1_away = df["away_team"].str.contains(norm_t1, case=False, na=False)
    t2_home = df["home_team"].str.contains(norm_t2, case=False, na=False)
    t2_away = df["away_team"].str.contains(norm_t2, case=False, na=False)
    
    # Matches between the two teams
    h2h_mask = (t1_home & t2_away) | (t2_home & t1_away)
    h2h_df = df[h2h_mask].copy()
    
    if h2h_df.empty:
        return f"No head-to-head matches found between {team1} and {team2}."
    
    # Calculate stats
    t1_wins = 0
    t2_wins = 0
    draws = 0
    
    for _, row in h2h_df.iterrows():
        if row["home_goals"] == row["away_goals"]:
            draws += 1
        elif (row["home_team"].lower() == norm_t1 and row["home_goals"] > row["away_goals"]) or \
             (row["away_team"].lower() == norm_t1 and row["away_goals"] > row["home_goals"]):
            t1_wins += 1
        else:
            t2_wins += 1
    
    # Recent matches
    recent_df = h2h_df.sort_values("date", ascending=False).head(limit)
    
    lines = [
        f"Head-to-Head: {team1.title()} vs {team2.title()}",
        f"- Total Matches: {len(h2h_df)}",
        f"- {team1.title()} Wins: {t1_wins}",
        f"- {team2.title()} Wins: {t2_wins}",
        f"- Draws: {draws}",
        "",
        f"Recent {min(limit, len(recent_df))} matches:",
    ]
    
    for _, row in recent_df.iterrows():
        lines.append(_format_match_row(row))
    
    return "\n".join(lines)


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    min_overall: Optional[int] = None,
    position: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    Search for soccer players based on various criteria.
    
    Args:
        name: Player name (partial match).
        nationality: Country/nationality.
        club: Club name (partial match).
        min_overall: Minimum overall rating.
        position: Playing position (e.g., "GK", "ST", "LW").
        limit: Maximum number of results to return.
    """
    df = get_players_df().copy()
    
    if name:
        df = df[df["Name"].str.contains(name, case=False, na=False)]
    
    if nationality:
        df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
    
    if club:
        norm_club = normalize_team_name(club)
        df = df[df["Club_normalized"].str.contains(norm_club, case=False, na=False) | 
                df["Club"].str.contains(club, case=False, na=False)]
    
    if min_overall is not None:
        df = df[df["Overall"] >= min_overall]
    
    if position:
        df = df[df["Position"].str.contains(position, case=False, na=False, regex=False)]
    
    # Sort by overall rating descending
    df = df.sort_values("Overall", ascending=False).head(limit)
    
    if df.empty:
        return "No players found matching the criteria."
    
    lines = [f"Found {len(df)} player(s):", ""]
    for _, row in df.iterrows():
        name = row.get("Name", "Unknown")
        age = row.get("Age", "")
        nationality = row.get("Nationality", "")
        club = row.get("Club", "")
        overall = row.get("Overall", "")
        position = row.get("Position", "")
        lines.append(f"- {name} (Age: {age}, {nationality}) | {position} @ {club} | Overall: {overall}")
    
    return "\n".join(lines)


@mcp.tool()
def get_competition_standings(
    competition: str,
    season: str,
) -> str:
    """
    Calculate and return standings for a competition and season.
    
    Args:
        competition: Competition name (e.g., "Brasileirão Serie A").
        season: Year/season (e.g., "2023").
    """
    df = get_matches_df().copy()
    
    # Filter
    df = df[df["competition"].str.contains(competition, case=False, na=False)]
    df = df[df["season"].astype(str) == str(season)]
    
    if df.empty:
        return f"No matches found for {competition} in season {season}."
    
    # Calculate standings
    standings = {}
    
    for _, row in df.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        home_g = row["home_goals"] if pd.notna(row["home_goals"]) else 0
        away_g = row["away_goals"] if pd.notna(row["away_goals"]) else 0
        
        for team in [home, away]:
            if team not in standings:
                standings[team] = {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "points": 0}
            
            standings[team]["played"] += 1
        
        standings[home]["gf"] += home_g
        standings[home]["ga"] += away_g
        
        standings[away]["gf"] += away_g
        standings[away]["ga"] += home_g
        
        if home_g > away_g:
            standings[home]["won"] += 1
            standings[home]["points"] += 3
            standings[away]["lost"] += 1
        elif home_g < away_g:
            standings[away]["won"] += 1
            standings[away]["points"] += 3
            standings[home]["lost"] += 1
        else:
            standings[home]["drawn"] += 1
            standings[home]["points"] += 1
            standings[away]["drawn"] += 1
            standings[away]["points"] += 1
    
    # Sort by points, then goal difference, then goals for
    sorted_teams = sorted(
        standings.items(),
        key=lambda x: (x[1]["points"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
        reverse=True
    )
    
    lines = [f"{competition} - Season {season} Standings:", ""]
    lines.append(f"{'#':<3} {'Team':<25} {'P':<3} {'W':<3} {'D':<3} {'L':<3} {'GF':<3} {'GA':<3} {'GD':<4} {'Pts':<4}")
    lines.append("-" * 55)
    
    for i, (team, stats) in enumerate(sorted_teams, 1):
        gd = stats["gf"] - stats["ga"]
        gd_str = f"+{gd}" if gd > 0 else str(gd)
        lines.append(
            f"{i:<3} {team.title():<25} {stats['played']:<3} {stats['won']:<3} "
            f"{stats['drawn']:<3} {stats['lost']:<3} {stats['gf']:<3} {stats['ga']:<3} "
            f"{gd_str:<4} {stats['points']:<4}"
        )
    
    return "\n".join(lines)


@mcp.tool()
def get_statistical_analysis(
    metric: str = "all",
    competition: Optional[str] = None,
    season: Optional[str] = None,
) -> str:
    """
    Get statistical analysis of matches.
    
    Args:
        metric: Metric to analyze ("all", "avg_goals", "home_advantage", "biggest_wins").
        competition: Optional competition filter.
        season: Optional season filter.
    """
    df = get_matches_df().copy()
    
    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    
    if season:
        df = df[df["season"].astype(str) == str(season)]
    
    if df.empty:
        return "No matches found for the given criteria."
    
    lines = []
    
    if metric in ["all", "avg_goals"]:
        total_goals = (df["home_goals"].fillna(0) + df["away_goals"].fillna(0)).sum()
        avg_goals = total_goals / len(df) if len(df) > 0 else 0
        lines.append(f"Average Goals per Match: {avg_goals:.2f}")
    
    if metric in ["all", "home_advantage"]:
        home_wins = (df["home_goals"] > df["away_goals"]).sum()
        draws = (df["home_goals"] == df["away_goals"]).sum()
        away_wins = (df["home_goals"] < df["away_goals"]).sum()
        total = len(df)
        lines.append(f"Home Win Rate: {home_wins/total*100:.1f}%")
        lines.append(f"Draw Rate: {draws/total*100:.1f}%")
        lines.append(f"Away Win Rate: {away_wins/total*100:.1f}%")
    
    if metric in ["all", "biggest_wins"]:
        df["goal_diff"] = (df["home_goals"] - df["away_goals"]).abs()
        biggest = df.nlargest(5, "goal_diff")
        lines.append("")
        lines.append("Biggest victories:")
        for _, row in biggest.iterrows():
            winner = row["home_team"] if row["home_goals"] > row["away_goals"] else row["away_team"]
            loser = row["away_team"] if row["home_goals"] > row["away_goals"] else row["home_team"]
            lines.append(f"- {row['date']}: {winner} {row['home_goals']}-{row['away_goals']} {loser} ({row['competition']})")
    
    return "\n".join(lines)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
