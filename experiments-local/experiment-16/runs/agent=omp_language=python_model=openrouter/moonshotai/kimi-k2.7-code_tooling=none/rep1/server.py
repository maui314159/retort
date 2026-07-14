"""
MCP server for Brazilian Soccer data.

Exposes tools that let an LLM answer natural-language questions about matches,
teams, players, competitions, and statistics from the provided Kaggle datasets.

Run with: python server.py
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from query_engine import (
    get_biggest_wins,
    get_goals_per_match,
    get_head_to_head,
    get_relegated_teams,
    get_standings,
    get_team_stats,
    get_top_scoring_teams,
    search_matches,
    search_players,
)

mcp = FastMCP("brazilian_soccer")


def _render_matches(result: dict[str, Any]) -> str:
    """Render a search_matches result as human-readable text."""
    if result.get("message"):
        return result["message"]
    lines: list[str] = []
    lines.append(f"Found {result['count']} match(es)")
    for m in result["matches"]:
        detail = f" ({m['detail']})" if m.get("detail") else ""
        lines.append(
            f"- {m['date']}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']}{detail}"
        )
    return "\n".join(lines)


@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str | None = None,
    limit: int = 50,
) -> str:
    """
    Find soccer matches by team, opponent, competition, season, or date range.

    Args:
        team: A team name (e.g. "Flamengo").
        opponent: Optional second team for head-to-head.
        competition: "Brasileirão", "Copa do Brasil", or "Copa Libertadores".
        season: Season year (e.g. 2023).
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
        venue: "home", "away", or omit for both.
        limit: Maximum number of matches to return.
    """
    result = search_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
        limit=limit,
    )
    return _render_matches(result)


@mcp.tool()
def team_statistics(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> str:
    """
    Return win/loss/draw record, goals, and win rate for a team.

    Args:
        team: Team name.
        competition: Optional competition filter.
        season: Optional season year.
        venue: "home", "away", or omit for all.
    """
    stats = get_team_stats(team, competition=competition, season=season, venue=venue)
    if "error" in stats:
        return stats["error"]

    venue_label = stats["venue"].capitalize()
    comp_label = stats["competition"] or "all competitions"
    season_label = stats["season"] or "all seasons"
    return (
        f"{stats['team']} {venue_label} record ({comp_label}, {season_label}):\n"
        f"- Matches: {stats['matches']}\n"
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}\n"
        f"- Win rate: {stats['win_rate']}%, Goal difference: {stats['goal_difference']}"
    )


@mcp.tool()
def head_to_head(
    team1: str,
    team2: str,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """
    Compare two teams and list all matches between them.

    Args:
        team1: First team name.
        team2: Second team name.
        competition: Optional competition filter.
        season: Optional season year.
    """
    result = get_head_to_head(team1, team2, competition=competition, season=season)
    if "error" in result:
        return result["error"]

    lines: list[str] = []
    lines.append(f"{result['team1']} vs {result['team2']}:")
    for m in result["matches"]:
        detail = f" ({m['detail']})" if m.get("detail") else ""
        lines.append(
            f"- {m['date']}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']}{detail}"
        )
    s = result["summary"]
    lines.append(
        f"\nHead-to-head: {result['team1']} {s.get(f'{result['team1']}_wins', 0)} wins, "
        f"{result['team2']} {s.get(f'{result['team2']}_wins', 0)} wins, {s['draws']} draws"
    )
    return "\n".join(lines)


@mcp.tool()
def find_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> str:
    """
    Search the FIFA player database.

    Args:
        name: Substring of player name.
        nationality: e.g. "Brazil".
        club: Club name substring.
        position: Position code or name (e.g. "ST", "GK").
        min_overall: Minimum FIFA overall rating.
        limit: Maximum players to return.
    """
    result = search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
    )
    lines: list[str] = [f"Found {result['count']} player(s)"]
    for p in result["players"]:
        lines.append(
            f"- {p['name']} (Overall: {p['overall']}, Position: {p['position']}, "
            f"Club: {p['club']}, Nationality: {p['nationality']})"
        )
    return "\n".join(lines)


@mcp.tool()
def competition_standings(competition: str, season: int) -> str:
    """
    Return calculated league standings for a competition season.

    Args:
        competition: Competition name.
        season: Season year.
    """
    result = get_standings(competition, season)
    if not result["standings"]:
        return result.get("message", "No standings available.")

    lines: list[str] = [f"{result['season']} {result['competition']} standings:"]
    for row in result["standings"]:
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L), "
            f"GD: {row['goal_difference']}"
        )
    return "\n".join(lines)


@mcp.tool()
def biggest_wins(competition: str | None = None, season: int | None = None, limit: int = 10) -> str:
    """
    Return the largest victories in the dataset.

    Args:
        competition: Optional competition filter.
        season: Optional season year.
        limit: Maximum results.
    """
    result = get_biggest_wins(competition=competition, season=season, limit=limit)
    lines: list[str] = [f"Top {len(result['matches'])} biggest wins:"]
    for m in result["matches"]:
        detail = f" ({m['detail']})" if m.get("detail") else ""
        lines.append(
            f"- {m['date']}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']}{detail}"
        )
    return "\n".join(lines)


@mcp.tool()
def goals_summary(competition: str | None = None, season: int | None = None) -> str:
    """
    Return average goals per match and home/away/draw split.

    Args:
        competition: Optional competition filter.
        season: Optional season year.
    """
    result = get_goals_per_match(competition=competition, season=season)
    return (
        f"Average goals per match: {result['average_goals_per_match']}\n"
        f"Total matches: {result['total_matches']}, Total goals: {result['total_goals']}\n"
        f"Home wins: {result['home_wins']}, Draws: {result['draws']}, "
        f"Away wins: {result['away_wins']}"
    )


@mcp.tool()
def top_scoring_teams(competition: str | None = None, season: int | None = None, limit: int = 10) -> str:
    """
    Return the teams with the most goals scored.

    Args:
        competition: Optional competition filter.
        season: Optional season year.
        limit: Maximum results.
    """
    result = get_top_scoring_teams(competition=competition, season=season, limit=limit)
    lines: list[str] = ["Top scoring teams:"]
    for item in result["teams"]:
        lines.append(f"- {item['team']}: {item['goals']} goals")
    return "\n".join(lines)


@mcp.tool()
def relegated_teams(season: int) -> str:
    """
    Return the bottom four teams of a Brasileirão season.

    Args:
        season: Season year.
    """
    result = get_relegated_teams(season)
    if "message" in result:
        return result["message"]
    return (
        f"Relegated from {result['season']} Brasileirão (positions "
        f"{', '.join(str(p) for p in result['positions'])}): "
        f"{', '.join(result['relegated'])}"
    )


@mcp.tool()
def raw_query_result(
    tool_name: str,
    parameters: str,
) -> str:
    """
    Execute another tool by name and return the raw JSON result.

    Useful for chaining or debugging. tool_name must be one of the registered
    tool names. parameters is a JSON object string.
    """
    tool_map = {
        "find_matches": find_matches,
        "team_statistics": team_statistics,
        "head_to_head": head_to_head,
        "find_players": find_players,
        "competition_standings": competition_standings,
        "biggest_wins": biggest_wins,
        "goals_summary": goals_summary,
        "top_scoring_teams": top_scoring_teams,
        "relegated_teams": relegated_teams,
    }
    if tool_name not in tool_map:
        return f"Unknown tool: {tool_name}"
    kwargs = json.loads(parameters)
    return str(tool_map[tool_name](**kwargs))


if __name__ == "__main__":
    mcp.run(transport="stdio")
