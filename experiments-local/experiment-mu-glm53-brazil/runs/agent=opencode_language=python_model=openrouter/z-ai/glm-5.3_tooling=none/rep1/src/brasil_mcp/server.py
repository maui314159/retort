"""MCP server exposing the Brazilian soccer knowledge tools.

Run with::

    python -m brasil_mcp.server        # stdio transport (for MCP clients)
    brasil-soccer-mcp                  # installed console script

Each tool returns a dict with a ready-to-display ``summary`` string plus
structured data, so any MCP client (Claude, other LLMs) can answer natural
language questions about Brazilian soccer.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import queries
from .store import SERIE_A


def build_server() -> MCPServer:
    """Construct the MCPServer with all soccer tools registered."""
    server = MCPServer(
        name="brazilian-soccer-mcp",
        title="Brazilian Soccer Knowledge Server",
        description=(
            "Knowledge graph of Brazilian soccer: matches (Brasileirão Série A/B/C, "
            "Copa do Brasil, Copa Libertadores, 2003-2023), FIFA player data "
            "(18,207 players), standings, head-to-head records and statistics."
        ),
    )

    @server.tool()
    def find_team(name: str) -> dict:
        """Resolve a team name in any spelling variant and describe it.

        Use this first when unsure how a team is spelled. Returns aliases,
        total matches, seasons, competitions and FIFA squad info.
        """
        return queries.find_team(name)

    @server.tool()
    def search_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        stage: str | None = None,
        venue: str = "any",
        limit: int = 20,
    ) -> dict:
        """Search matches by team, opponent, competition, season, date range,
        stage (e.g. 'final', 'round 22') or venue ('any', 'home', 'away').

        Dates use YYYY-MM-DD. Competition accepts 'Brasileirão'/'Série A'/
        'Série B'/'Série C'/'Copa do Brasil'/'Libertadores'.
        """
        return queries.search_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            stage=stage,
            venue=venue,
            limit=limit,
        )

    @server.tool()
    def head_to_head(team_a: str, team_b: str, competition: str | None = None, limit: int = 20) -> dict:
        """Head-to-head record between two teams: matches, wins/draws/losses and goals."""
        return queries.head_to_head(team_a, team_b, competition=competition, limit=limit)

    @server.tool()
    def team_stats(team: str, season: int | None = None, competition: str | None = None) -> dict:
        """Win/draw/loss record of a team with goals, home/away splits and
        per-competition breakdown, optionally for one season or competition."""
        return queries.team_stats(team, season=season, competition=competition)

    @server.tool()
    def team_season_history(team: str, competition: str | None = None, limit: int = 25) -> dict:
        """Season-by-season performance trend of a team (matches, W/D/L, goals, points)."""
        return queries.team_season_history(team, competition=competition, limit=limit)

    @server.tool()
    def standings(season: int, competition: str = SERIE_A) -> dict:
        """League table computed from match results: full table, champion and
        relegation zone. For Libertadores, returns the stage-by-stage bracket."""
        return queries.standings(season, competition)

    @server.tool()
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        max_age: int | None = None,
        order_by: str = "overall",
        limit: int = 20,
    ) -> dict:
        """Search FIFA players by name, nationality, club, position or rating.

        Club accepts Brazilian team spellings ('Athletico-PR', 'Grêmio').
        Position accepts codes ('ST', 'LW', 'GK') or groups ('forward',
        'midfielder', 'defender', 'goalkeeper').
        """
        return queries.search_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
            max_age=max_age,
            order_by=order_by,
            limit=limit,
        )

    @server.tool()
    def team_players(team: str, position: str | None = None, limit: int = 25) -> dict:
        """The FIFA squad of a team, highest rated first. Reports which
        Brazilian clubs have squads when the team is missing from the data."""
        return queries.team_players(team, position=position, limit=limit)

    @server.tool()
    def competition_info(competition: str | None = None, season: int | None = None) -> dict:
        """What competitions, seasons, teams and match counts the datasets cover."""
        return queries.competition_info(competition, season)

    @server.tool()
    def derbies(season: int | None = None, competition: str | None = None, limit: int = 15) -> dict:
        """Matches between traditional rivals: Fla-Flu, Grenal, Majestoso,
        Choque-Rei, Ba-Vi, Atletiba, Clássico-Rei and more."""
        return queries.derbies(season=season, competition=competition, limit=limit)

    @server.tool()
    def biggest_wins(competition: str | None = None, season: int | None = None, limit: int = 10) -> dict:
        """Largest goal-margin victories, optionally filtered by competition or season."""
        return queries.biggest_wins(competition=competition, season=season, limit=limit)

    @server.tool()
    def goals_analysis(competition: str | None = None, season: int | None = None) -> dict:
        """Average goals per match, home/away win rates and draw rate."""
        return queries.goals_analysis(competition=competition, season=season)

    @server.tool()
    def best_records(
        competition: str | None = None,
        season: int | None = None,
        venue: str = "overall",
        min_matches: int = 10,
        limit: int = 10,
    ) -> dict:
        """Rank teams by points per game, overall or filtered to home/away records."""
        return queries.best_records(
            competition=competition,
            season=season,
            venue=venue,
            min_matches=min_matches,
            limit=limit,
        )

    @server.tool()
    def compare_teams(team_a: str, team_b: str, season: int | None = None) -> dict:
        """Compare two teams side by side: records, head-to-head and squad ratings."""
        return queries.compare_teams(team_a, team_b, season=season)

    return server


def main() -> None:
    """Run the MCP server on stdio (the standard transport for MCP clients)."""
    build_server().run("stdio")


if __name__ == "__main__":
    main()
