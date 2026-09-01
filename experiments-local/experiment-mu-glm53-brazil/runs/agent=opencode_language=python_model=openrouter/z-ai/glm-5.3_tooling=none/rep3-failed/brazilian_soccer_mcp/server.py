"""MCP server exposing the Brazilian soccer knowledge tools.

Run with ``python -m brazilian_soccer_mcp`` (stdio transport) or point an
MCP client at ``brazilian_soccer_mcp.server:main``.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from brazilian_soccer_mcp import __version__
from brazilian_soccer_mcp.formatting import (
    format_biggest_wins,
    format_club_roster,
    format_competitions,
    format_derbies,
    format_find_team,
    format_head_to_head,
    format_list_teams,
    format_players,
    format_search_matches,
    format_standings,
    format_statistics,
    format_team_stats,
)
from brazilian_soccer_mcp.normalize import TeamNotFoundError
from brazilian_soccer_mcp.queries import QueryEngine, QueryError, get_engine

SERVER_INSTRUCTIONS = """
This server answers questions about Brazilian soccer using local Kaggle
datasets: Brasileirão Série A (2003-2023), Série B and Série C (2014-2023),
Copa do Brasil (2012-2023), Copa Libertadores (2013-2022) and a FIFA player
database (~18k players).

Team names may be given in any variant (Palmeiras, Palmeiras-SP, Timão);
they are normalized automatically. Competitions accept common aliases
(Brasileirão, Serie A, Libertadores, Copa do Brasil...).
"""


def _guard(action):
    """Run an engine action and turn known errors into helpful text."""
    try:
        return action()
    except TeamNotFoundError as error:
        message = f"Team not found: {error.query!r}."
        if error.suggestions:
            message += f" Did you mean: {', '.join(error.suggestions)}?"
        return message
    except QueryError as error:
        return f"Cannot answer: {error}"
    except (ValueError, KeyError) as error:
        return f"Cannot answer: {error}"


def build_server(engine: Optional[QueryEngine] = None, data_dir: Optional[str] = None):
    """Create the MCPServer with all tools wired to the query engine."""
    from mcp.server.mcpserver import MCPServer

    if engine is None:
        engine = get_engine(data_dir)
    server = MCPServer(
        name="brazilian-soccer-mcp",
        title="Brazilian Soccer Knowledge Server",
        description=(
            "Knowledge graph interface over Brazilian soccer datasets: "
            "matches, teams, players, competitions and statistics."
        ),
        instructions=SERVER_INSTRUCTIONS.strip(),
        version=__version__,
    )

    @server.tool()
    def list_competitions(competition: Optional[str] = None, season: Optional[int] = None) -> str:
        """List competitions available in the datasets with their seasons,
        match counts and source files. Optional competition filter
        (e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores')."""
        return _guard(lambda: format_competitions(
            engine.competition_overview(competition, season)
        ))

    @server.tool()
    def find_team(name: str) -> str:
        """Resolve a team name (any variant, e.g. 'Palmeiras-SP', 'Timão',
        'Atlético Mineiro') to a canonical team and report its variants,
        match counts, competitions and FIFA players."""
        return _guard(lambda: format_find_team(engine.find_team(name)))

    @server.tool()
    def list_teams(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        """List teams in a competition (optionally for one season) with match
        counts. Example: competition='Série B', season=2023."""
        return _guard(lambda: format_list_teams(
            engine.list_teams(competition, season), competition, season
        ))

    @server.tool()
    def search_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        stage: Optional[str] = None,
        venue: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Search matches by team, opponent, competition, season, date range
        (YYYY-MM-DD) or stage ('final', 'semifinal', 'quarterfinal',
        'round of 16', 'group stage' for Libertadores/Copa do Brasil).
        Example: team='Flamengo', opponent='Fluminense'."""
        result = _guard(lambda: engine.search_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            stage=stage,
            venue=venue,
            limit=limit,
        ))
        if isinstance(result, str):
            return result
        return format_search_matches(result, limit)

    @server.tool()
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Head-to-head record between two teams: wins, draws, losses, goals
        and recent meetings. Example: team_a='Palmeiras', team_b='Santos'."""
        result = _guard(lambda: engine.head_to_head(
            team_a, team_b, competition=competition, season=season, limit=limit
        ))
        if isinstance(result, str):
            return result
        return format_head_to_head(result)

    @server.tool()
    def team_stats(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",
    ) -> str:
        """Win/draw/loss record and goals for a team, optionally filtered by
        season, competition and venue ('home' or 'away'). Example:
        team='Corinthians', season=2022, venue='home'."""
        stats = _guard(lambda: engine.team_stats(
            team, season=season, competition=competition, venue=venue
        ))
        if isinstance(stats, str):
            return stats
        scope = engine.competition_label(competition)
        return format_team_stats(stats, season=season, competition=scope, venue=venue)

    @server.tool()
    def standings(season: int, competition: str = "Brasileirão Série A") -> str:
        """League table calculated from match results: positions, points,
        champion and relegated teams. Works for Série A (2003-2023),
        Série B and Série C (2014-2023). Example: season=2019."""
        result = _guard(lambda: engine.standings(season, competition))
        if isinstance(result, str):
            return result
        return format_standings(result)

    @server.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        order_by: str = "overall",
        limit: int = 20,
    ) -> str:
        """Search the FIFA player database (~18k players). Filter by name
        (partial match), nationality (e.g. 'Brazil'), club, position (FIFA
        code like 'ST' or group like 'forward'), and rating range. Sort with
        order_by ('overall', 'potential', 'age', 'name')."""
        players = _guard(lambda: engine.search_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
            order_by=order_by,
            limit=limit,
        ))
        if isinstance(players, str):
            return players
        total = len(players)
        title_parts = ["Players"]
        if name:
            title_parts.append(f"matching {name!r}")
        if nationality:
            title_parts.append(f"from {nationality}")
        if club:
            title_parts.append(f"at {club}")
        if position:
            title_parts.append(f"playing {position}")
        title = " ".join(title_parts) + ":"
        return format_players(players, title, total=total if total > len(players) else None)

    @server.tool()
    def club_players(club: str) -> str:
        """Full roster of a club from the FIFA database with ratings.
        Example: club='Fluminense'."""
        players = _guard(lambda: engine.club_players(club))
        if isinstance(players, str):
            return players
        club_name = players[0].club_display if players else club
        return format_club_roster(club_name, players)

    @server.tool()
    def statistics(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> str:
        """Aggregate statistics: average goals per match, home/draw/away win
        rates and biggest wins. Optional competition and season filters.
        Example: competition='Brasileirão', season=2019."""
        stats = _guard(lambda: engine.statistics(competition=competition, season=season))
        if isinstance(stats, str):
            return stats
        scope = engine.competition_label(competition)
        return format_statistics(stats, competition=scope, season=season)

    @server.tool()
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Biggest winning margins in the dataset, optionally filtered by
        competition and season."""
        matches = _guard(lambda: engine.biggest_wins(
            competition=competition, season=season, limit=limit
        ))
        if isinstance(matches, str):
            return matches
        return format_biggest_wins(matches, engine.competition_label(competition))

    @server.tool()
    def derbies(
        derby: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 5,
    ) -> str:
        """Matches between traditional rivals: Fla-Flu, Gre-Nal, Choque-Rei,
        Majestoso, San-São, Clássico Mineiro, Ba-Vi, Atletiba, Clássico dos
        Milhões, Clássico dos Gigantes. Without a derby name, shows all."""
        results = _guard(lambda: engine.derbies(
            derby=derby, competition=competition, season=season, limit=limit
        ))
        if isinstance(results, str):
            return results
        return format_derbies(results)

    return server


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    server = build_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
