"""FastMCP server for Brazilian soccer queries."""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from data_loader import get_data
from queries import (
    best_attack,
    best_away_record,
    best_home_record,
    biggest_wins,
    competition_stats,
    find_matches,
    head_to_head,
    relegated_teams,
    search_players,
    season_standings,
    team_stats,
    top_players_by_club,
)

mcp = FastMCP("brazilian_soccer_mcp")


def _text_response(obj) -> list:
    """Serialize a result object as pretty-printed JSON for the LLM."""
    return [{"type": "text", "text": json.dumps(obj, indent=2, ensure_ascii=False)}]


@mcp.tool()
def list_competitions() -> list:
    """Return the names of all competitions available in the dataset."""
    data = get_data()
    competitions = sorted(set(data.matches["competition"].dropna()))
    return _text_response({"competitions": competitions})


@mcp.tool()
def list_teams(limit: Optional[int] = 100) -> list:
    """Return a list of canonical team names available in the match data."""
    data = get_data()
    teams = sorted(set(data.matches["home_team"].dropna()) | set(data.matches["away_team"].dropna()))
    return _text_response({"teams": teams[:limit], "total": len(teams)})


@mcp.tool()
def find_matches_tool(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> list:
    """Find matches by team, opponent, competition, season, or date range."""
    data = get_data()
    result = find_matches(
        data,
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return _text_response({"matches": result, "count": len(result)})


@mcp.tool()
def head_to_head_tool(team_a: str, team_b: str, limit: int = 50) -> list:
    """Return the match history and aggregate record between two teams."""
    data = get_data()
    return _text_response(head_to_head(data, team_a, team_b, limit=limit))


@mcp.tool()
def team_stats_tool(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
) -> list:
    """Return a team's win/loss/draw record and goals under the given filters.

    ``venue`` may be 'home', 'away', or omitted for all matches.
    """
    data = get_data()
    return _text_response(team_stats(data, team, competition=competition, season=season, venue=venue))


@mcp.tool()
def best_attack_tool(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    top_n: int = 5,
) -> list:
    """Return the top scoring teams for a competition/season."""
    data = get_data()
    return _text_response({"top_scorers": best_attack(data, competition=competition, season=season, top_n=top_n)})


@mcp.tool()
def search_players_tool(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> list:
    """Search the FIFA player database by name, nationality, club, position, or rating."""
    data = get_data()
    return _text_response(search_players(
        data,
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
    ))


@mcp.tool()
def top_players_by_club_tool(club: Optional[str] = None, top_n: int = 5) -> list:
    """Return the highest-overall players, optionally filtered to a club."""
    data = get_data()
    return _text_response(top_players_by_club(data, club=club, top_n=top_n))


@mcp.tool()
def season_standings_tool(competition: str, season: int, top_n: Optional[int] = None) -> list:
    """Compute the final league table for a competition and season."""
    data = get_data()
    return _text_response({"standings": season_standings(data, competition, season, top_n=top_n)})


@mcp.tool()
def relegated_teams_tool(competition: str, season: int, bottom_n: int = 4) -> list:
    """Return the bottom N teams in the league table for a season."""
    data = get_data()
    return _text_response({"relegated": relegated_teams(data, competition, season, bottom_n=bottom_n)})


@mcp.tool()
def competition_stats_tool(competition: Optional[str] = None) -> list:
    """Return aggregated match statistics (avg goals, win/draw rates)."""
    data = get_data()
    return _text_response(competition_stats(data, competition=competition))


@mcp.tool()
def biggest_wins_tool(competition: Optional[str] = None, top_n: int = 10) -> list:
    """Return the largest goal-margin victories."""
    data = get_data()
    return _text_response({"biggest_wins": biggest_wins(data, competition=competition, top_n=top_n)})


@mcp.tool()
def best_home_record_tool(competition: Optional[str] = None, min_matches: int = 5) -> list:
    """Return teams with the best home win rate."""
    data = get_data()
    return _text_response({"best_home_records": best_home_record(data, competition=competition, min_matches=min_matches)})


@mcp.tool()
def best_away_record_tool(competition: Optional[str] = None, min_matches: int = 5) -> list:
    """Return teams with the best away win rate."""
    data = get_data()
    return _text_response({"best_away_records": best_away_record(data, competition=competition, min_matches=min_matches)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
