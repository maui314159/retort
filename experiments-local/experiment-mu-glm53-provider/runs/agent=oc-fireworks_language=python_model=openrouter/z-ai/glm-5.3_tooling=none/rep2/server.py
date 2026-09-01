"""MCP server exposing the Brazilian soccer knowledge graph.

Run with stdio transport (the standard way an MCP host launches a server):

    python server.py

Tools exposed (each maps to a capability in the specification):

- search_matches       - by team, opponent, competition, season, stage, dates
- head_to_head         - aggregate record between two teams
- team_stats           - W/D/L, goals, win rate (per season/venue/competition)
- team_profile         - everything known about one team
- league_standings     - computed tables, champions, relegated teams
- finals               - cup finals with aggregate scores and winners
- biggest_wins         - largest victory margins
- competition_info     - seasons, average goals, home/away win rates
- search_players       - FIFA database queries (name/club/position/rating)
- players_by_club      - squad aggregates per club
- derby_matches        - famous clássicos (Fla-Flu, Gre-Nal, ...)
"""

from __future__ import annotations

from brazilian_soccer import SoccerData, SoccerService
from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name="brazilian-soccer",
    instructions=(
        "Natural-language questions about Brazilian soccer (2003-2023): "
        "matches, teams, players (FIFA dataset), competitions, standings, "
        "derbies and statistics. Team names are matched leniently across "
        "spellings ('Palmeiras-SP' == 'Palmeiras')."
    ),
)

_service = SoccerService(SoccerData())


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    stage: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 15,
) -> str:
    """Find matches by team, opponent, competition, season, stage/round or
    date range. Dates accept 'YYYY-MM-DD' or 'DD/MM/YYYY'. Stage examples:
    'final', 'semifinals', 'group', 'Round 22'. Results are most recent
    first."""
    return _service.search_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        stage=stage,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@mcp.tool()
def head_to_head(
    team_a: str, team_b: str, competition: str | None = None, limit: int = 10
) -> str:
    """Head-to-head record between two teams (all competitions or one),
    with recent matches and win/draw/loss aggregate."""
    return _service.head_to_head(team_a, team_b, competition=competition, limit=limit)


@mcp.tool()
def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> str:
    """Win/draw/loss record, goals and win rate for a team. Filter by
    season, competition ('Brasileirão', 'Copa do Brasil', 'Libertadores',
    'Série B', 'Série C') and venue ('home', 'away' or 'all')."""
    return _service.team_stats(
        team=team, season=season, competition=competition, venue=venue
    )


@mcp.tool()
def team_profile(team: str) -> str:
    """Everything known about a team: competitions and seasons played,
    all-time record, biggest win, FIFA squad summary."""
    return _service.team_profile(team)


@mcp.tool()
def league_standings(
    competition: str = "Brasileirão",
    season: int | None = None,
    venue: str = "all",
) -> str:
    """League table computed from match results (default: latest Serie A
    season). Marks the champion and, for Serie A/B, the four relegated
    teams. venue='home'/'away' ranks home/away records only."""
    return _service.league_standings(
        competition=competition, season=season, venue=venue
    )


@mcp.tool()
def finals(competition: str) -> str:
    """Finals of a cup competition ('Copa do Brasil' or 'Libertadores')
    for every season in the dataset, with aggregate scores and winners."""
    return _service.finals(competition)


@mcp.tool()
def biggest_wins(
    competition: str | None = None, season: int | None = None, limit: int = 10
) -> str:
    """Biggest victory margins in the dataset, optionally filtered by
    competition and season."""
    return _service.biggest_wins(competition=competition, season=season, limit=limit)


@mcp.tool()
def competition_info(competition: str | None = None, season: int | None = None) -> str:
    """Overview of a competition (or all competitions): match counts,
    seasons covered, average goals per match, home/draw/away win rates."""
    return _service.competition_info(competition=competition, season=season)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    sort: str = "overall",
    limit: int = 15,
) -> str:
    """Search the FIFA player database (18,207 players). Filter by name
    (substring), nationality ('Brazil'), club, position (code like 'ST' or
    role like 'Forward') and overall rating; sort by overall/potential/age."""
    return _service.search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        max_overall=max_overall,
        sort=sort,
        limit=limit,
    )


@mcp.tool()
def players_by_club(
    nationality: str | None = "Brazil",
    brazilian_clubs_only: bool = True,
    limit: int = 20,
) -> str:
    """Player counts and average ratings per club, optionally restricted
    to one nationality and to Brazilian league clubs."""
    return _service.players_by_club(
        nationality=nationality,
        brazilian_clubs_only=brazilian_clubs_only,
        limit=limit,
    )


@mcp.tool()
def derby_matches(
    derby: str | None = None, season: int | None = None, limit: int = 10
) -> str:
    """With no argument, list the known derbies (Fla-Flu, Gre-Nal, Derby
    Paulista, ...). With a derby name, show its matches (optionally one
    season) and the head-to-head record."""
    return _service.derby_matches(derby=derby, season=season, limit=limit)


if __name__ == "__main__":
    mcp.run()
