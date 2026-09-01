"""
MCP server for Brazilian soccer data (FastMCP, stdio transport).

Context block
-------------
Why:
    TASK.md asks for an MCP server an LLM can query in natural language.
    FastMCP (``mcp.server.fastmcp``) lets us expose the query service as
    typed tools with schema-bearing docstrings; the LLM picks tools and
    arguments, the service does the rest.

What:
    ``build_server`` wires 17 tools onto a ``FastMCP`` instance:
      Match queries     - search_matches, head_to_head, last_match,
                          derby_matches
      Team queries      - team_record, team_profile, list_teams, resolve_team
      Player queries    - find_players, top_players, players_at_club
      Competitions      - standings, champion, bracket, competition_info
      Statistics        - season_averages, biggest_wins, match_statistics
    Every tool delegates to ``brazilian_soccer_mcp.service`` and returns
    JSON-serializable structures.  ``main()`` runs the stdio server; the
    dataset is loaded lazily on first tool call (and cached process-wide)
    so importing the module stays cheap for tests.

Test:
    ``tests/test_server.py`` asserts the tool registry, JSON-serializability
    of every tool response, and a full stdio JSON-RPC round trip.

Spec references:
    TASK.md "Overview" (MCP server connected to an LLM), "Required
    Capabilities" 1-5, "Success Criteria" (query performance via the
    in-memory dataset).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

try:  # mcp v1.x
    from mcp.server.fastmcp import FastMCP
except ImportError:  # mcp 2.x renamed FastMCP -> MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP

try:  # ToolError keeps its message in tool results; plain exceptions don't.
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # mcp v1.x location
    from mcp.server.fastmcp.exceptions import ToolError

from . import service
from .dataset import Dataset, load_dataset

_DATASET: Dataset | None = None


def _ds() -> Dataset:
    """Lazily load and cache the dataset for the server process."""
    global _DATASET
    if _DATASET is None:
        _DATASET = load_dataset()
    return _DATASET


T = TypeVar("T", bound=Callable[..., Any])


def _friendly_errors(fn: T) -> T:
    """Convert expected ValueErrors into ToolError so their message reaches
    the LLM client (the MCP SDK hides unexpected-exception details)."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc

    return wrapper  # type: ignore[return-value]


def list_registered_tools(server: FastMCP) -> list[Any]:
    """Return the registered tools, abstracting sync/async list_tools()."""
    result = server.list_tools()
    if inspect.isawaitable(result):
        import asyncio

        result = asyncio.run(result)
    return result


def build_server(name: str = "brazilian-soccer") -> FastMCP:
    """Construct the FastMCP application with all tools registered."""
    mcp: FastMCP = FastMCP(
        name,
        instructions=(
            "Knowledge base of Brazilian soccer covering 2003-2023: Brasileirão "
            "Serie A/B/C, Copa do Brasil and Copa Libertadores matches plus a "
            "FIFA player database (18,207 players). Ask about matches between "
            "teams, team records, standings and champions, players, head-to-head "
            "and derby histories, or aggregate statistics."
        ),
    )

    # ------------------------------------------------------------------
    # Match queries
    # ------------------------------------------------------------------

    @mcp.tool()
    @_friendly_errors
    def search_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        stage: str | None = None,
        limit: int = 50,
    ) -> dict:
        """Search matches by team, opponent, competition, season, date range or
        Libertadores stage.

        Examples: all Flamengo vs Fluminense fixtures; every Palmeiras match
        in 2023; Copa do Brasil matches between 2020-05-01 and 2020-12-31.
        Competitions: 'Brasileirão Serie A', 'Brasileirão Serie B',
        'Brasileirão Serie C', 'Copa do Brasil', 'Copa Libertadores'.
        Dates use YYYY-MM-DD. Returns matches with date, teams, score,
        competition, round/stage and source, plus the total count.
        """
        return service.search_matches(
            _ds(),
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            stage=stage,
            limit=limit,
        )

    @mcp.tool()
    @_friendly_errors
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 100,
    ) -> dict:
        """Head-to-head history between two teams: every fixture plus the
        wins/draws/losses and goals summary from each side's perspective,
        optionally restricted to one competition or season.

        Example: compare Palmeiras and Santos across all competitions.
        """
        return service.head_to_head(
            _ds(),
            team_a=team_a,
            team_b=team_b,
            competition=competition,
            season=season,
            limit=limit,
        )

    @mcp.tool()
    @_friendly_errors
    def last_match(team: str, opponent: str | None = None) -> dict:
        """Most recent match of a team in the dataset (optionally against a
        specific opponent), with date, score and competition.

        Example: when did Flamengo last play Corinthians, and what was the
        score?
        """
        return service.last_match(_ds(), team=team, opponent=opponent)

    @mcp.tool()
    @_friendly_errors
    def derby_matches(
        season: int | None = None,
        competition: str | None = None,
        limit: int = 100,
    ) -> dict:
        """Matches between famous rival pairs: Fla-Flu, Clássico dos
        Milhões, Gre-Nal, Choque-Rei, Derby Paulista, Majestoso, Clássico
        Mineiro, Ba-Vi and Atletiba. Optionally filter by season or
        competition.
        """
        return service.derby_matches(_ds(), season=season, competition=competition, limit=limit)

    # ------------------------------------------------------------------
    # Team queries
    # ------------------------------------------------------------------

    @mcp.tool()
    @_friendly_errors
    def team_record(
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str | None = None,
    ) -> dict:
        """Win/draw/loss record, goals for/against and win rate for a team,
        overall or filtered by competition, season and venue ('home' or
        'away').

        Examples: Corinthians' home record in 2022; Palmeiras' overall
        record in the 2023 Brasileirão.
        """
        return service.team_record(_ds(), team=team, competition=competition, season=season, venue=venue)

    @mcp.tool()
    @_friendly_errors
    def team_profile(team: str) -> dict:
        """Cross-file profile of a club: alternate spellings, every
        competition and season it appears in, all-time record, biggest wins
        and its players in the FIFA database.

        Example: what competitions has Palmeiras played in, and who are its
        players?
        """
        return service.team_profile(_ds(), team=team)

    @mcp.tool()
    @_friendly_errors
    def list_teams(
        competition: str | None = None,
        season: int | None = None,
    ) -> dict:
        """Teams present in a competition and/or season, with match counts.

        Example: which teams played the 2019 Brasileirão?
        """
        return service.list_teams(_ds(), competition=competition, season=season)

    @mcp.tool()
    @_friendly_errors
    def resolve_team(name: str) -> dict:
        """Resolve a team name (any spelling: 'Flamengo', 'Flamengo-RJ',
        'Sport Club do Recife', 'Athletico') to the canonical club, listing
        alternate matches, state, dataset appearances and spelling variants.
        Use this to disambiguate before deeper queries.
        """
        return service.resolve_team_info(_ds(), name=name)

    # ------------------------------------------------------------------
    # Player queries
    # ------------------------------------------------------------------

    @mcp.tool()
    @_friendly_errors
    def find_players(
        name: str | None = None,
        club: str | None = None,
        nationality: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = 50,
    ) -> dict:
        """Search the FIFA player database (18,207 players) by name (substring,
        case/accent-insensitive), club, nationality, position and overall
        rating range. Position accepts codes (ST, CAM, GK...) or groups
        ('forward', 'midfielder', 'defender', 'goalkeeper').

        Examples: 'Gabriel' at Flamengo; Brazilian forwards with overall >= 80.
        """
        return service.find_players(
            _ds(),
            name=name,
            club=club,
            nationality=nationality,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
            limit=limit,
        )

    @mcp.tool()
    @_friendly_errors
    def top_players(
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Highest-rated players by FIFA overall rating, filterable by
        nationality, club and position.

        Example: the top Brazilian players; the best players at Grêmio.
        """
        return service.top_players(_ds(), nationality=nationality, club=club, position=position, limit=limit)

    @mcp.tool()
    @_friendly_errors
    def players_at_club(club: str, limit: int = 100) -> dict:
        """Roster of a club in the FIFA database: players, average overall
        rating and positional breakdown.

        Example: which players play for Grêmio?
        """
        return service.players_at_club(_ds(), club=club, limit=limit)

    # ------------------------------------------------------------------
    # Competition queries
    # ------------------------------------------------------------------

    @mcp.tool()
    @_friendly_errors
    def standings(
        competition: str,
        season: int,
        venue: str | None = None,
    ) -> dict:
        """League table computed from match results (leagues only): rank,
        matches, wins, draws, losses, goals, goal difference and points
        (3 per win), ordered by CBF criteria (points, wins, GD, GF). venue=
        'home' or 'away' produces a home/away-only table.

        Examples: the 2019 Brasileirão standings; which teams were relegated
        in 2020; the best away record in 2022. For cups use champion() or
        bracket().
        """
        return service.standings(_ds(), competition=competition, season=season, venue=venue)

    @mcp.tool()
    @_friendly_errors
    def champion(competition: str, season: int) -> dict:
        """Winner of a competition in a season. Leagues: the top of the
        computed table. Cups: the final(s) with the aggregate score.

        Examples: who won the 2019 Brasileirão; who won the 2019 Copa
        Libertadores; who won the 2017 Copa do Brasil.
        """
        return service.champion(_ds(), competition=competition, season=season)

    @mcp.tool()
    @_friendly_errors
    def bracket(competition: str, season: int) -> dict:
        """Knockout rounds of a cup competition (final first): Copa do Brasil
        rounds and Copa Libertadores stages (round of 16, quarterfinals,
        semifinals, final) with every match.

        Example: the 2018 Copa Libertadores bracket; all Copa do Brasil
        finals (query the seasons you care about, or use competition_info).
        """
        return service.bracket(_ds(), competition=competition, season=season)

    @mcp.tool()
    @_friendly_errors
    def competition_info(competition: str | None = None) -> dict:
        """Seasons covered for one or all competitions, with match counts,
        data sources and computed champions per season.

        Example: which seasons of the Copa Libertadores are available?
        """
        return service.competition_info(_ds(), competition=competition)

    # ------------------------------------------------------------------
    # Statistical analysis
    # ------------------------------------------------------------------

    @mcp.tool()
    @_friendly_errors
    def season_averages(
        competition: str,
        season: int | None = None,
    ) -> dict:
        """Aggregate scoring statistics: average goals per match, average
        home/away goals, and home win / draw / away win rates. Without a
        season, aggregates the whole competition history.

        Example: average goals per match in the Brasileirão.
        """
        return service.season_averages(_ds(), competition=competition, season=season)

    @mcp.tool()
    @_friendly_errors
    def biggest_wins(
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> dict:
        """Largest victory margins in the dataset, with dates, scores and
        competitions. Optionally filter by competition or season.

        Example: the biggest wins in Brasileirão history (2003-2023).
        """
        return service.biggest_wins(_ds(), competition=competition, season=season, limit=limit)

    @mcp.tool()
    @_friendly_errors
    def match_statistics(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 50,
    ) -> dict:
        """Extended per-match statistics from the BR-Football dataset
        (2014-2023): corners, shots, attacks, half-time result and kickoff
        time.

        Example: corner and shot statistics for Flamengo matches in 2023.
        """
        return service.match_statistics(
            _ds(),
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            limit=limit,
        )

    return mcp


def main() -> None:
    """Run the MCP server over stdio (entry point for the console script)."""
    mcp = build_server()
    mcp.run()


if __name__ == "__main__":
    main()
