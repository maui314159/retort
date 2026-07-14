"""
Brazilian Soccer MCP Server
Provides natural language query interface for Brazilian soccer data.
"""

import asyncio
import sys
import pandas as pd
from mcp.server.fastmcp import FastMCP
from data_loader import SoccerDataLoader, normalize_team_name

# Initialize the MCP server
mcp = FastMCP("Brazilian Soccer Data")

# Initialize data loader
loader = SoccerDataLoader()
loader.load_all()

print("Brazilian Soccer MCP Server initialized", file=sys.stderr)
print(f"Loaded datasets:", file=sys.stderr)
print(f"  - Brasileirão matches: {len(loader.brasileirao_matches) if loader.brasileirao_matches is not None else 0}", file=sys.stderr)
print(f"  - Brazilian Cup matches: {len(loader.brazilian_cup_matches) if loader.brazilian_cup_matches is not None else 0}", file=sys.stderr)
print(f"  - Libertadores matches: {len(loader.libertadores_matches) if loader.libertadores_matches is not None else 0}", file=sys.stderr)
print(f"  - BR Football dataset: {len(loader.br_football) if loader.br_football is not None else 0}", file=sys.stderr)
print(f"  - Historical Brasileirão: {len(loader.historical_brasileirao) if loader.historical_brasileirao is not None else 0}", file=sys.stderr)
print(f"  - FIFA players: {len(loader.fifa_players) if loader.fifa_players is not None else 0}", file=sys.stderr)


@mcp.tool()
def search_matches(
    team: str = None,
    competition: str = None,
    season: int = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50
) -> str:
    """
    Search for matches by various criteria.

    Args:
        team: Team name (e.g., "Flamengo", "Palmeiras")
        competition: Competition name ("Brasileirão", "Copa do Brasil", "Libertadores")
        season: Year of the season (e.g., 2023)
        date_from: Start date (YYYY-MM-DD format)
        date_to: End date (YYYY-MM-DD format)
        limit: Maximum number of results (default: 50)

    Returns:
        Formatted match results
    """
    matches = loader.search_matches(
        team=team,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to
    )

    if matches.empty:
        return "No matches found matching the criteria."

    # Limit results
    matches = matches.head(limit)

    result = f"Found {len(matches)} matches:\n\n"

    for _, row in matches.iterrows():
        date = row.get('match_date', 'Unknown date')
        if pd.notna(date):
            date = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)

        home = row.get('home_team', 'Unknown')
        away = row.get('away_team', 'Unknown')
        home_goals = row.get('home_goals', row.get('home_goal', '?'))
        away_goals = row.get('away_goals', row.get('away_goal', '?'))
        comp = row.get('competition', 'Unknown')

        result += f"{date}: {home} {home_goals}-{away_goals} {away} ({comp})\n"

    return result


@mcp.tool()
def get_team_stats(team: str, season: int = None) -> str:
    """
    Get team statistics including wins, losses, goals, etc.

    Args:
        team: Team name (e.g., "Corinthians", "Palmeiras")
        season: Optional season year to filter by

    Returns:
        Formatted team statistics
    """
    stats = loader.get_team_stats(team, season)

    if "error" in stats:
        return stats["error"]

    result = f"## {stats['team']} Statistics"
    if season:
        result += f" ({season})"
    result += "\n\n"

    result += f"**Matches Played:** {stats['matches_played']}\n"
    result += f"**Record:** {stats['wins']}W - {stats['draws']}D - {stats['losses']}L\n"
    result += f"**Points:** {stats['points']}\n"
    result += f"**Win Rate:** {stats['win_rate']:.1f}%\n"
    result += f"**Goals For:** {stats['goals_for']}\n"
    result += f"**Goals Against:** {stats['goals_against']}\n"
    result += f"**Goal Difference:** {stats['goals_for'] - stats['goals_against']}\n\n"

    result += f"**Home Matches:** {stats['home_matches']}\n"
    result += f"**Away Matches:** {stats['away_matches']}\n"

    return result


@mcp.tool()
def head_to_head(team1: str, team2: str) -> str:
    """
    Get head-to-head record between two teams.

    Args:
        team1: First team name
        team2: Second team name

    Returns:
        Formatted head-to-head statistics and match list
    """
    result = loader.head_to_head(team1, team2)

    if "error" in result:
        return result["error"]

    output = f"## Head-to-Head: {result['team1']} vs {result['team2']}\n\n"
    output += f"**Total Matches:** {result['total_matches']}\n"
    output += f"**{result['team1']} Wins:** {result['team1_wins']}\n"
    output += f"**{result['team2']} Wins:** {result['team2_wins']}\n"
    output += f"**Draws:** {result['draws']}\n\n"

    output += "**Recent Matches:**\n\n"
    # Show last 20 matches
    for match in result['matches'][-20:]:
        output += f"- {match['date'][:10]}: {match['home']} {match['score']} {match['away']} ({match['competition']})\n"

    return output


@mcp.tool()
def search_players(
    name: str = None,
    nationality: str = None,
    club: str = None,
    min_overall: int = None,
    limit: int = 50
) -> str:
    """
    Search for players in the FIFA database.

    Args:
        name: Player name (partial match supported)
        nationality: Player nationality (e.g., "Brazil", "Argentina")
        club: Current club name
        min_overall: Minimum overall rating
        limit: Maximum number of results

    Returns:
        Formatted player list
    """
    players = loader.search_players(
        name=name,
        nationality=nationality,
        club=club,
        min_overall=min_overall
    )

    if players.empty:
        return "No players found matching the criteria."

    players = players.head(limit)

    result = f"Found {len(players)} players:\n\n"

    for _, row in players.iterrows():
        name = row.get('Name', 'Unknown')
        nationality = row.get('Nationality', 'Unknown')
        club = row.get('Club', 'Unknown')
        overall = row.get('Overall', '?')
        position = row.get('Position', '?')

        result += f"**{name}** - Overall: {overall}, Position: {position}, Nationality: {nationality}, Club: {club}\n"

    return result


@mcp.tool()
def get_competition_standings(competition: str, season: int) -> str:
    """
    Get competition standings for a specific season.

    Args:
        competition: Competition name ("Brasileirão", "Copa do Brasil", etc.)
        season: Season year

    Returns:
        Formatted standings table
    """
    result = loader.get_competition_standings(competition, season)

    if "error" in result:
        return result["error"]

    output = f"## {result['competition']} {result['season']} Standings\n\n"
    output += "| Pos | Team | MP | W | D | L | GF | GA | GD | Pts |\n"
    output += "|-----|------|----|---|---|---|----|----|----|----|\n"

    for idx, team in enumerate(result['standings'], 1):
        gd = team['goals_for'] - team['goals_against']
        gd_sign = "+" if gd >= 0 else ""
        output += f"| {idx} | {team['team']} | {team['matches']} | {team['wins']} | {team['draws']} | {team['losses']} | {team['goals_for']} | {team['goals_against']} | {gd_sign}{gd} | {team['points']} |\n"

    return output


@mcp.tool()
def get_biggest_wins(team: str = None, limit: int = 20) -> str:
    """
    Find the biggest wins in the dataset.

    Args:
        team: Optional team name to filter by
        limit: Number of results to return

    Returns:
        List of biggest wins
    """
    matches = loader.get_all_matches()

    if matches.empty:
        return "No match data available."

    # Calculate goal difference for each match
    matches = matches.copy()
    matches['goal_diff'] = abs(
        matches.get('home_goals', matches.get('home_goal', 0)) -
        matches.get('away_goals', matches.get('away_goal', 0))
    )

    # Filter by team if specified
    if team:
        team_norm = normalize_team_name(team)
        matches = matches[
            (matches['home_team_norm'] == team_norm) |
            (matches['away_team_norm'] == team_norm)
        ]

    # Sort by goal difference
    matches = matches.sort_values('goal_diff', ascending=False).head(limit)

    result = f"## Biggest Wins"
    if team:
        result += f" for {team}"
    result += "\n\n"

    for idx, (_, row) in enumerate(matches.iterrows(), 1):
        date = row.get('match_date', 'Unknown')
        if pd.notna(date):
            date = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)

        home = row.get('home_team', 'Unknown')
        away = row.get('away_team', 'Unknown')
        home_goals = row.get('home_goals', row.get('home_goal', '?'))
        away_goals = row.get('away_goals', row.get('away_goal', '?'))
        diff = row['goal_diff']

        result += f"{idx}. {date}: {home} {home_goals}-{away_goals} {away} (GD: {diff})\n"

    return result


@mcp.tool()
def compare_teams(team1: str, team2: str, season: int = None) -> str:
    """
    Compare two teams' statistics.

    Args:
        team1: First team name
        team2: Second team name
        season: Optional season year

    Returns:
        Comparison of team statistics
    """
    stats1 = loader.get_team_stats(team1, season)
    stats2 = loader.get_team_stats(team2, season)

    if "error" in stats1:
        return f"Error getting stats for {team1}: {stats1['error']}"
    if "error" in stats2:
        return f"Error getting stats for {team2}: {stats2['error']}"

    result = f"## Comparison: {stats1['team']} vs {stats2['team']}"
    if season:
        result += f" ({season})"
    result += "\n\n"

    result += "| Metric | " + stats1['team'] + " | " + stats2['team'] + " |\n"
    result += "|--------|" + "-" * (len(stats1['team']) + 2) + "|" + "-" * (len(stats2['team']) + 2) + "|\n"
    result += f"| Matches | {stats1['matches_played']} | {stats2['matches_played']} |\n"
    result += f"| Wins | {stats1['wins']} | {stats2['wins']} |\n"
    result += f"| Draws | {stats1['draws']} | {stats2['draws']} |\n"
    result += f"| Losses | {stats1['losses']} | {stats2['losses']} |\n"
    result += f"| Points | {stats1['points']} | {stats2['points']} |\n"
    result += f"| Win Rate | {stats1['win_rate']:.1f}% | {stats2['win_rate']:.1f}% |\n"
    result += f"| Goals For | {stats1['goals_for']} | {stats2['goals_for']} |\n"
    result += f"| Goals Against | {stats1['goals_against']} | {stats2['goals_against']} |\n"
    result += f"| Goal Diff | {stats1['goals_for'] - stats1['goals_against']} | {stats2['goals_for'] - stats2['goals_against']} |\n"

    return result


@mcp.tool()
def get_average_goals(competition: str = None, season: int = None) -> str:
    """
    Calculate average goals per match.

    Args:
        competition: Optional competition filter
        season: Optional season filter

    Returns:
        Average goals statistics
    """
    matches = loader.search_matches(competition=competition, season=season)

    if matches.empty:
        return "No matches found."

    total_goals = 0
    total_matches = len(matches)

    for _, row in matches.iterrows():
        home_goals = row.get('home_goals', row.get('home_goal', 0))
        away_goals = row.get('away_goals', row.get('away_goal', 0))

        if pd.notna(home_goals) and pd.notna(away_goals):
            total_goals += home_goals + away_goals

    avg_goals = total_goals / total_matches if total_matches > 0 else 0

    result = "## Average Goals Per Match\n\n"
    if competition:
        result += f"**Competition:** {competition}\n"
    if season:
        result += f"**Season:** {season}\n"
    result += f"\n"
    result += f"**Total Matches:** {total_matches}\n"
    result += f"**Total Goals:** {total_goals}\n"
    result += f"**Average Goals Per Match:** {avg_goals:.2f}\n"

    return result


@mcp.tool()
def get_competitions() -> str:
    """
    List all available competitions in the dataset.

    Returns:
        List of competitions with match counts
    """
    matches = loader.get_all_matches()

    if matches.empty:
        return "No match data available."

    comp_counts = matches['competition'].value_counts()

    result = "## Available Competitions\n\n"

    for comp, count in comp_counts.items():
        seasons = matches[matches['competition'] == comp]['season'].unique()
        seasons = sorted([s for s in seasons if pd.notna(s)])

        result += f"**{comp}**\n"
        result += f"  - Matches: {count}\n"
        if seasons:
            result += f"  - Seasons: {min(seasons)}-{max(seasons) if len(seasons) > 1 else seasons[0]}\n"
        result += "\n"

    return result


@mcp.tool()
def get_seasons(competition: str = None) -> str:
    """
    List all available seasons.

    Args:
        competition: Optional competition to filter by

    Returns:
        List of seasons
    """
    matches = loader.get_all_matches()

    if matches.empty:
        return "No match data available."

    if competition:
        matches = matches[matches['competition'].str.contains(competition, case=False, na=False)]

    seasons = sorted([s for s in matches['season'].unique() if pd.notna(s)])

    result = "## Available Seasons\n\n"
    if competition:
        result += f"For competition: {competition}\n\n"

    for season in seasons:
        season_matches = matches[matches['season'] == season]
        result += f"- **{season}**: {len(season_matches)} matches\n"

    return result


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
