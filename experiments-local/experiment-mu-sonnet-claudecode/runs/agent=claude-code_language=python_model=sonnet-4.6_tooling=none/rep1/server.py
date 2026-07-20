#!/usr/bin/env python3
"""Brazilian Soccer MCP Server."""
import json
from mcp.server.fastmcp import FastMCP
import data_loader as dl
import pandas as pd

mcp = FastMCP("Brazilian Soccer")


def _fmt_match(row) -> str:
    date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row.get("date")) else "?"
    home = row.get("home_team", "?")
    away = row.get("away_team", "?")
    hg = int(row["home_goal"]) if pd.notna(row.get("home_goal")) else "?"
    ag = int(row["away_goal"]) if pd.notna(row.get("away_goal")) else "?"
    comp = row.get("competition", "")
    season = row.get("season", "")
    return f"{date_str}: {home} {hg}-{ag} {away} ({comp}, {season})"


@mcp.tool()
def find_matches(
    team: str,
    opponent: str = "",
    season: int = 0,
    competition: str = "",
    limit: int = 20,
) -> str:
    """Find matches for a team, optionally filtered by opponent, season, or competition.

    Args:
        team: Team name to search for (partial match supported)
        opponent: Optional opposing team name
        season: Optional year filter (e.g. 2023)
        competition: Optional competition name filter (e.g. "Brasileirão", "Libertadores")
        limit: Max results to return (default 20)
    """
    results = dl.find_team_matches(
        team=team,
        opponent=opponent or None,
        season=season or None,
        competition=competition or None,
    )
    if results.empty:
        return f"No matches found for '{team}'."
    total = len(results)
    lines = [f"Found {total} matches for '{team}'" + (f" vs '{opponent}'" if opponent else "") + ":"]
    for _, row in results.head(limit).iterrows():
        lines.append("  " + _fmt_match(row))
    if total > limit:
        lines.append(f"  ... ({total - limit} more)")
    return "\n".join(lines)


@mcp.tool()
def team_statistics(
    team: str,
    season: int = 0,
    competition: str = "",
) -> str:
    """Get win/loss/draw statistics for a team.

    Args:
        team: Team name to search for
        season: Optional year filter
        competition: Optional competition filter
    """
    matches = dl.find_team_matches(
        team=team,
        season=season or None,
        competition=competition or None,
    )
    if matches.empty:
        return f"No match data found for '{team}'."

    team_lower = team.lower()
    wins = draws = losses = goals_for = goals_against = 0

    for _, row in matches.iterrows():
        hg = row.get("home_goal")
        ag = row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg, ag = int(hg), int(ag)
        is_home = team_lower in str(row.get("home_team_norm", "")).lower()
        if is_home:
            gf, ga = hg, ag
        else:
            gf, ga = ag, hg
        goals_for += gf
        goals_against += ga
        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1

    played = wins + draws + losses
    win_rate = (wins / played * 100) if played else 0
    label = f"'{team}'" + (f" in {season}" if season else "") + (f" ({competition})" if competition else "")
    return (
        f"Statistics for {label}:\n"
        f"  Matches played: {played}\n"
        f"  Wins: {wins}, Draws: {draws}, Losses: {losses}\n"
        f"  Goals For: {goals_for}, Goals Against: {goals_against}\n"
        f"  Win rate: {win_rate:.1f}%"
    )


@mcp.tool()
def head_to_head(team1: str, team2: str, season: int = 0) -> str:
    """Compare two teams head-to-head.

    Args:
        team1: First team name
        team2: Second team name
        season: Optional year filter
    """
    matches = dl.find_team_matches(
        team=team1,
        opponent=team2,
        season=season or None,
    )
    if matches.empty:
        return f"No matches found between '{team1}' and '{team2}'."

    t1_wins = t2_wins = draws = 0
    t1_goals = t2_goals = 0

    for _, row in matches.iterrows():
        hg = row.get("home_goal")
        ag = row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg, ag = int(hg), int(ag)
        home_is_t1 = team1.lower() in str(row.get("home_team_norm", "")).lower()
        if home_is_t1:
            gf1, gf2 = hg, ag
        else:
            gf1, gf2 = ag, hg
        t1_goals += gf1
        t2_goals += gf2
        if gf1 > gf2:
            t1_wins += 1
        elif gf1 < gf2:
            t2_wins += 1
        else:
            draws += 1

    lines = [
        f"Head-to-head: {team1} vs {team2}" + (f" (season {season})" if season else ""),
        f"  Total matches: {len(matches)}",
        f"  {team1} wins: {t1_wins}",
        f"  {team2} wins: {t2_wins}",
        f"  Draws: {draws}",
        f"  Goals - {team1}: {t1_goals}, {team2}: {t2_goals}",
        "",
        "Recent matches:",
    ]
    for _, row in matches.head(10).iterrows():
        lines.append("  " + _fmt_match(row))
    return "\n".join(lines)


@mcp.tool()
def season_standings(season: int, competition: str = "Brasileirão") -> str:
    """Calculate standings for a season based on match results.

    Args:
        season: Year of the season (e.g. 2019)
        competition: Competition name (default: Brasileirão)
    """
    df = dl.get_matches()
    mask = (df["season"] == season) & df["competition"].str.lower().str.contains(competition.lower(), na=False)
    matches = df[mask]

    if matches.empty:
        return f"No data found for {competition} {season}."

    stats: dict[str, dict] = {}

    def ensure(team):
        if team not in stats:
            stats[team] = {"W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}

    for _, row in matches.iterrows():
        hg = row.get("home_goal")
        ag = row.get("away_goal")
        if pd.isna(hg) or pd.isna(ag):
            continue
        ht = dl._normalize_team_name(str(row.get("home_team", "")))
        at = dl._normalize_team_name(str(row.get("away_team", "")))
        hg, ag = int(hg), int(ag)
        ensure(ht)
        ensure(at)
        stats[ht]["GF"] += hg
        stats[ht]["GA"] += ag
        stats[at]["GF"] += ag
        stats[at]["GA"] += hg
        if hg > ag:
            stats[ht]["W"] += 1
            stats[ht]["Pts"] += 3
            stats[at]["L"] += 1
        elif hg < ag:
            stats[at]["W"] += 1
            stats[at]["Pts"] += 3
            stats[ht]["L"] += 1
        else:
            stats[ht]["D"] += 1
            stats[ht]["Pts"] += 1
            stats[at]["D"] += 1
            stats[at]["Pts"] += 1

    sorted_teams = sorted(stats.items(), key=lambda x: (x[1]["Pts"], x[1]["W"], x[1]["GF"] - x[1]["GA"]), reverse=True)
    lines = [f"{competition} {season} Standings (calculated):"]
    for i, (team, s) in enumerate(sorted_teams, 1):
        gd = s["GF"] - s["GA"]
        lines.append(f"  {i:2d}. {team:30s} {s['Pts']:3d} pts  ({s['W']}W {s['D']}D {s['L']}L)  GD: {gd:+d}")
    return "\n".join(lines)


@mcp.tool()
def find_players(
    name: str = "",
    nationality: str = "",
    club: str = "",
    position: str = "",
    min_overall: int = 0,
    limit: int = 20,
) -> str:
    """Search for players in the FIFA dataset.

    Args:
        name: Player name (partial match)
        nationality: Player nationality (e.g. "Brazil")
        club: Club name (partial match)
        position: Position (e.g. "GK", "ST", "CB")
        min_overall: Minimum overall rating
        limit: Max results (default 20)
    """
    df = dl.get_fifa()
    mask = pd.Series([True] * len(df), index=df.index)

    if name:
        mask &= df["Name"].str.lower().str.contains(name.lower(), na=False)
    if nationality:
        mask &= df["Nationality"].str.lower().str.contains(nationality.lower(), na=False)
    if club:
        mask &= df["Club"].str.lower().str.contains(club.lower(), na=False)
    if position:
        mask &= df["Position"].str.lower().str.contains(position.lower(), na=False)
    if min_overall:
        df_overall = pd.to_numeric(df["Overall"], errors="coerce")
        mask &= df_overall >= min_overall

    result = df[mask].copy()
    result["_overall"] = pd.to_numeric(result["Overall"], errors="coerce")
    result = result.sort_values("_overall", ascending=False)

    if result.empty:
        return "No players found matching the criteria."

    total = len(result)
    lines = [f"Found {total} players:"]
    for _, row in result.head(limit).iterrows():
        name_str = row.get("Name", "?")
        club_str = row.get("Club", "?")
        nat = row.get("Nationality", "?")
        pos = row.get("Position", "?")
        overall = row.get("Overall", "?")
        age = row.get("Age", "?")
        lines.append(f"  {name_str} | {pos} | Overall: {overall} | Age: {age} | Club: {club_str} | Nat: {nat}")
    if total > limit:
        lines.append(f"  ... ({total - limit} more)")
    return "\n".join(lines)


@mcp.tool()
def top_scorers_analysis(season: int = 0, competition: str = "") -> str:
    """Analyze which teams scored the most goals in a given context.

    Args:
        season: Optional season year filter
        competition: Optional competition filter
    """
    df = dl.get_matches()
    if season:
        df = df[df["season"] == season]
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    if df.empty:
        return "No data found."

    df = df.dropna(subset=["home_goal", "away_goal"])
    goals: dict[str, int] = {}

    for _, row in df.iterrows():
        ht = dl._normalize_team_name(str(row.get("home_team", "")))
        at = dl._normalize_team_name(str(row.get("away_team", "")))
        if ht:
            goals[ht] = goals.get(ht, 0) + int(row["home_goal"])
        if at:
            goals[at] = goals.get(at, 0) + int(row["away_goal"])

    sorted_goals = sorted(goals.items(), key=lambda x: x[1], reverse=True)
    label = (f" {season}" if season else "") + (f" {competition}" if competition else "")
    lines = [f"Top goal-scoring teams{label}:"]
    for i, (team, g) in enumerate(sorted_goals[:20], 1):
        lines.append(f"  {i:2d}. {team:30s} {g} goals")
    return "\n".join(lines)


@mcp.tool()
def biggest_wins(limit: int = 10, competition: str = "") -> str:
    """Find the biggest victory margins in the dataset.

    Args:
        limit: Number of results (default 10)
        competition: Optional competition filter
    """
    df = dl.get_matches().dropna(subset=["home_goal", "away_goal"]).copy()
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
    df = df.sort_values("margin", ascending=False)

    lines = [f"Biggest wins" + (f" in {competition}" if competition else "") + ":"]
    for i, (_, row) in enumerate(df.head(limit).iterrows(), 1):
        lines.append(f"  {i:2d}. " + _fmt_match(row) + f" (margin: {int(row['margin'])})")
    return "\n".join(lines)


@mcp.tool()
def match_averages(season: int = 0, competition: str = "") -> str:
    """Calculate average goals per match and home win rate.

    Args:
        season: Optional season year filter
        competition: Optional competition filter
    """
    df = dl.get_matches()
    if season:
        df = df[df["season"] == season]
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    df = df.dropna(subset=["home_goal", "away_goal"])
    if df.empty:
        return "No data found."

    total_matches = len(df)
    total_goals = int(df["home_goal"].sum() + df["away_goal"].sum())
    home_wins = int((df["home_goal"] > df["away_goal"]).sum())
    away_wins = int((df["away_goal"] > df["home_goal"]).sum())
    draws = int((df["home_goal"] == df["away_goal"]).sum())

    label = (f" {season}" if season else "") + (f" {competition}" if competition else "")
    return (
        f"Match statistics{label}:\n"
        f"  Total matches: {total_matches}\n"
        f"  Total goals: {total_goals}\n"
        f"  Avg goals/match: {total_goals/total_matches:.2f}\n"
        f"  Home wins: {home_wins} ({home_wins/total_matches*100:.1f}%)\n"
        f"  Away wins: {away_wins} ({away_wins/total_matches*100:.1f}%)\n"
        f"  Draws: {draws} ({draws/total_matches*100:.1f}%)"
    )


@mcp.tool()
def best_home_record(season: int = 0, competition: str = "", limit: int = 10) -> str:
    """Find teams with the best home win record.

    Args:
        season: Optional season year filter
        competition: Optional competition filter
        limit: Number of results (default 10)
    """
    df = dl.get_matches()
    if season:
        df = df[df["season"] == season]
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    df = df.dropna(subset=["home_goal", "away_goal"])
    stats: dict[str, dict] = {}

    for _, row in df.iterrows():
        ht = dl._normalize_team_name(str(row.get("home_team", "")))
        if not ht:
            continue
        if ht not in stats:
            stats[ht] = {"W": 0, "D": 0, "L": 0}
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        if hg > ag:
            stats[ht]["W"] += 1
        elif hg == ag:
            stats[ht]["D"] += 1
        else:
            stats[ht]["L"] += 1

    def win_rate(s):
        total = s["W"] + s["D"] + s["L"]
        return s["W"] / total if total >= 5 else -1

    sorted_teams = sorted(stats.items(), key=lambda x: win_rate(x[1]), reverse=True)
    label = (f" {season}" if season else "") + (f" {competition}" if competition else "")
    lines = [f"Best home records{label}:"]
    for i, (team, s) in enumerate(sorted_teams[:limit], 1):
        total = s["W"] + s["D"] + s["L"]
        wr = s["W"] / total * 100 if total else 0
        lines.append(f"  {i:2d}. {team:30s} {wr:.1f}% ({s['W']}W {s['D']}D {s['L']}L in {total} home games)")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
