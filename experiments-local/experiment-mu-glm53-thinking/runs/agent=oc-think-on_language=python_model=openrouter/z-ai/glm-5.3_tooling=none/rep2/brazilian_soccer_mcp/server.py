"""MCP server exposing the Brazilian soccer knowledge base.

Builds an MCP (Model Context Protocol) server over :class:`SoccerQueryService`
using the official Python SDK (``mcp`` package).  Each tool maps to one of
the query categories required by the specification:

- Match queries: ``search_matches``, ``head_to_head``, ``last_meeting``,
  ``find_finals``, ``derbies``
- Team queries: ``team_record``, ``team_profile``, ``list_teams``,
  ``best_records``
- Player queries: ``search_players``, ``top_players``, ``club_squad``,
  ``brazilian_players_by_club``
- Competition queries: ``competition_info``, ``standings``
- Statistics: ``stats_summary``, ``biggest_wins``, ``season_comparison``

Run the server over stdio with::

    python -m brazilian_soccer_mcp
"""

from __future__ import annotations

from typing import Any, Optional

from .loader import SoccerData
from .service import SoccerQueryService

SERVER_NAME = "brazilian-soccer-mcp"
SERVER_INSTRUCTIONS = (
    "Knowledge base of Brazilian soccer (Brasileirão 2003-2023, Copa do "
    "Brasil, Copa Libertadores, and a FIFA player database). Ask about "
    "matches, teams, head-to-head records, standings, derbies, players and "
    "statistics. Team names can be given in any common spelling "
    "('Flamengo', 'Flamengo-RJ', 'Palmeiras-SP', ...)."
)


def build_server(data: Optional[SoccerData] = None) -> Any:
    """Create the MCP server with every tool registered."""
    from mcp.server.mcpserver import MCPServer

    service = SoccerQueryService(data if data is not None else SoccerData.load())
    server: MCPServer = MCPServer(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
    )

    @server.tool()
    def search_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        stage: Optional[str] = None,
        venue: str = "any",
        limit: int = 25,
    ) -> dict:
        """Find matches by team, opponent, competition, season, date range or stage.

        Examples: "What matches did Palmeiras play in 2023?",
        "Show me all Flamengo vs Fluminense matches",
        "Find Copa do Brasil quarterfinals from 2015",
        "Palmeiras home matches between 2019-01-01 and 2019-12-31".

        Args:
            team: Team name in any spelling (e.g. "Flamengo", "Flamengo-RJ").
            opponent: Restrict to matches against this opponent.
            competition: "Brasileirão Série A" (or "Serie A"), "Série B",
                "Série C", "Copa do Brasil" or "Copa Libertadores".
            season: Year, e.g. 2019.
            date_from: Inclusive start date (YYYY-MM-DD).
            date_to: Inclusive end date (YYYY-MM-DD).
            stage: Text that must appear in the round/stage label
                (e.g. "final", "semifinal", "Round 22", "group stage").
            venue: "any", "home" or "away" (relative to `team`).
            limit: Maximum matches to return (default 25).
        """
        return service.find_matches(
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
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        """Head-to-head record between two teams: all meetings plus wins/draws/losses.

        Examples: "Compare Palmeiras and Santos head-to-head",
        "Flamengo vs Fluminense record".

        Args:
            team_a: First team, any spelling.
            team_b: Second team, any spelling.
            competition: Optional competition filter.
            limit: Maximum matches to list (default 25).
        """
        return service.head_to_head(team_a, team_b, competition=competition, limit=limit)

    @server.tool()
    def last_meeting(team_a: str, team_b: str) -> dict:
        """Most recent match between two teams, including the score.

        Example: "When did Flamengo last play Corinthians and what was the score?"
        """
        return service.last_meeting(team_a, team_b)

    @server.tool()
    def find_finals(competition: str, season: Optional[int] = None, limit: int = 50) -> dict:
        """Find final-round matches of a competition.

        Examples: "Find all Copa do Brasil finals",
        "Show the Libertadores finals from 2019".

        Args:
            competition: "Copa do Brasil", "Copa Libertadores", etc.
            season: Optional season filter.
            limit: Maximum matches to return.
        """
        return service.find_matches(
            competition=competition, season=season, stage="final", limit=limit
        )

    @server.tool()
    def derbies(competition: Optional[str] = None, season: Optional[int] = None) -> dict:
        """Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, ...).

        Example: "Show me all derbies in 2023".
        """
        return service.derbies(competition=competition, season=season)

    @server.tool()
    def team_record(
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "all",
    ) -> dict:
        """Win/draw/loss record, goals and win rate for a team.

        Examples: "What is Corinthians' home record in 2022?",
        "Palmeiras record in the 2019 Brasileirão".

        Args:
            team: Team name in any spelling.
            competition: Optional competition filter.
            season: Optional season filter.
            venue: "all" (default), "home" or "away".
        """
        return service.team_record(
            team=team, competition=competition, season=season, venue=venue
        )

    @server.tool()
    def team_profile(team: str) -> dict:
        """Everything known about one club: records, competitions, seasons, squad.

        Example: "Tell me about Palmeiras", "What competitions has Palmeiras played in?"
        """
        return service.team_profile(team)

    @server.tool()
    def list_teams(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """List teams known to the knowledge base, optionally per competition/season.

        Example: "Which teams played in Série A in 2019?"
        """
        return service.list_teams(competition=competition, season=season)

    @server.tool()
    def best_records(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "home",
        limit: int = 10,
    ) -> dict:
        """Teams ranked by win rate, home or away.

        Examples: "Which team has the best home record?",
        "Which team has the best away record in Série B?".

        Args:
            competition: Optional competition filter.
            season: Optional season filter.
            venue: "home" or "away".
            limit: Maximum teams to return.
        """
        return service.best_records(
            competition=competition, season=season, venue=venue, limit=limit
        )

    @server.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        limit: int = 25,
    ) -> dict:
        """Search the FIFA player database (18,207 players).

        Examples: "Who is Neymar Jr?", "Find all Brazilian players",
        "Show me all forwards from Santos", "Highest-rated players at Grêmio".

        Args:
            name: Case-insensitive substring of the player name.
            nationality: Country, e.g. "Brazil".
            club: Club name in any spelling.
            position: FIFA position code (GK, CB, LB, RB, CDM, CM, LM, RM,
                CAM, LW, RW, CF, ST, ...).
            min_overall / max_overall: FIFA overall rating bounds.
            limit: Maximum players to return (default 25).
        """
        return service.search_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
            limit=limit,
        )

    @server.tool()
    def top_players(
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Highest-rated players, optionally filtered.

        Example: "Who are the top Brazilian players?"
        """
        return service.top_players(
            nationality=nationality, club=club, position=position, limit=limit
        )

    @server.tool()
    def club_squad(club: str, limit: int = 200) -> dict:
        """All FIFA players at a club plus the average rating.

        Example: "Which players play for Grêmio?"
        """
        return service.club_squad(club, limit=limit)

    @server.tool()
    def brazilian_players_by_club(limit: int = 20) -> dict:
        """Brazilian players grouped by club, with counts and average ratings."""
        return service.brazilian_players_by_club(limit=limit)

    @server.tool()
    def competition_info(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """List competitions and seasons available in the datasets.

        Example: "What data do you have?", "Which seasons of the Copa Libertadores?"
        """
        return service.competition_info(competition=competition, season=season)

    @server.tool()
    def standings(competition: str, season: int, relegated_count: int = 4) -> dict:
        """League table computed from match results, with champion and relegated teams.

        Examples: "Who won the 2019 Brasileirão?",
        "Which teams were relegated in 2020?",
        "Show the 2018 Série B table".

        Args:
            competition: e.g. "Brasileirão Série A", "Série B".
            season: Year.
            relegated_count: How many bottom teams to flag (default 4).
        """
        return service.standings(competition, season, relegated_count=relegated_count)

    @server.tool()
    def stats_summary(
        competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """Goals per match, home win rate, draw rate and away win rate.

        Example: "What's the average goals per match in the Brasileirão?"
        """
        return service.stats_summary(competition=competition, season=season)

    @server.tool()
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> dict:
        """Largest goal-margin victories in the dataset.

        Example: "Show me the biggest wins in the dataset".
        """
        return service.biggest_wins(competition=competition, season=season, limit=limit)

    @server.tool()
    def season_comparison(
        first_season: int,
        second_season: int,
        competition: Optional[str] = None,
    ) -> dict:
        """Compare aggregate statistics between two seasons.

        Example: "Compare the 2018 and 2019 Brasileirão seasons".
        """
        return service.season_comparison(first_season, second_season, competition)

    return server


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
