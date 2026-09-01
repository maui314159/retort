"""Brazilian Soccer MCP server.

CONTEXT
-------
Entry point for the Model Context Protocol server exposing the Brazilian
soccer knowledge base (six Kaggle datasets: Brasileirão 2012-2022,
historical Série A 2003-2019, Copa do Brasil, Copa Libertadores, extended
match statistics and the FIFA player database) as 14 query tools.

Run standalone (stdio transport, the default for local MCP clients)::

    python server.py

Or register with an MCP client, e.g.::

    claude mcp add brazilian-soccer -- python /path/to/server.py

The heavy CSV parsing happens once, lazily, on the first tool call
(`get_service`); every query afterwards is served from in-memory indexes.
"""

from __future__ import annotations

import threading
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from soccer_mcp import SoccerDataService, load_knowledge_base

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"

_service: SoccerDataService | None = None
_service_lock = threading.Lock()


def get_service() -> SoccerDataService:
    """Lazily load and cache the knowledge base (thread-safe singleton)."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                kb = load_knowledge_base(_DEFAULT_DATA_DIR)
                _service = SoccerDataService(kb)
    return _service


def build_server() -> MCPServer:
    """Create the MCP server with all Brazilian-soccer query tools."""
    server = MCPServer(
        name="brazilian-soccer",
        title="Brazilian Soccer Knowledge Base",
        description=(
            "Knowledge base over Brazilian soccer datasets: matches "
            "(Brasileirão Série A/B/C 2003-2023, Copa do Brasil, Copa "
            "Libertadores), team statistics, head-to-head records, league "
            "tables and FIFA player data."
        ),
        instructions=(
            "Query Brazilian soccer history with these tools. Team names "
            "are matched tolerantly (accents, state suffixes and full club "
            "names all work: 'palmeiras', 'Palmeiras-SP', 'Atletico "
            "Mineiro'). Competitions: 'Brasileirão Série A' (or 'serie a'), "
            "'Série B', 'Série C', 'Copa do Brasil', 'Libertadores'. "
            "Seasons are calendar years. For standings use league "
            "competitions; cups are knockout tournaments — use the finals "
            "tool for those."
        ),
    )

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    @server.tool()
    def list_competitions() -> str:
        """List available competitions, their season coverage and match counts.

        Use this first to discover what data can be queried.
        """
        return get_service().list_competitions()

    @server.tool()
    def list_teams(
        competition: str | None = None, season: int | None = None, limit: int = 40
    ) -> str:
        """List teams, optionally restricted to a competition and/or season.

        Args:
            competition: e.g. "Brasileirão Série A", "Copa do Brasil" (optional).
            season: calendar year, e.g. 2019 (optional).
            limit: maximum teams to return.
        """
        return get_service().list_teams(competition=competition, season=season, limit=limit)

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------

    @server.tool()
    def search_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        stage: str | None = None,
        limit: int = 20,
    ) -> str:
        """Search matches by team, opponent, competition, season, date range or stage.

        Examples: all "Flamengo" vs "Fluminense" matches; Palmeiras matches
        in season 2019; Libertadores "final" stage matches; matches between
        2023-05-01 and 2023-06-30. Results are newest-first and include a
        head-to-head summary when both team and opponent are given.

        Args:
            team: team name (matched tolerantly, e.g. "palmeiras", "Atletico Mineiro").
            opponent: restrict to matches against this team.
            competition: "Brasileirão Série A", "Série B", "Série C", "Copa do Brasil", "Libertadores".
            season: calendar year, e.g. 2022.
            date_from: ISO date "YYYY-MM-DD" (inclusive).
            date_to: ISO date "YYYY-MM-DD" (inclusive).
            stage: e.g. "final", "semifinal", "group stage" (cup competitions).
            limit: max matches to list (results include the total count).
        """
        return get_service().search_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            stage=stage,
            limit=limit,
        )

    @server.tool()
    def head_to_head(team_a: str, team_b: str, competition: str | None = None) -> str:
        """Compare two teams head-to-head: all matches, wins/draws/losses and goals.

        Args:
            team_a: first team name.
            team_b: second team name.
            competition: optional restriction, e.g. "Brasileirão Série A".
        """
        return get_service().head_to_head(team_a, team_b, competition=competition)

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------

    @server.tool()
    def team_stats(
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str = "all",
    ) -> str:
        """Win/draw/loss record and goals for a team, overall or per competition/season/venue.

        Args:
            team: team name (tolerant matching).
            competition: optional competition restriction.
            season: optional calendar year.
            venue: "all" (default), "home" or "away".
        """
        return get_service().team_stats(
            team, competition=competition, season=season, venue=venue
        )

    @server.tool()
    def team_profile(team: str) -> str:
        """Everything known about a team: competitions and seasons played,
        all-time record, titles won (computed from standings), biggest win
        and its FIFA squad.

        Args:
            team: team name (tolerant matching).
        """
        return get_service().team_profile(team)

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------

    @server.tool()
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = 20,
    ) -> str:
        """Search the FIFA player database by name, nationality, club, position and rating.

        Args:
            name: substring of the player name (accent-insensitive).
            nationality: e.g. "Brazil".
            club: substring of the club name, e.g. "Grêmio", "Liverpool".
            position: FIFA code ("ST", "CAM", "GK") or group ("FWD", "MID", "DEF", "GK").
            min_overall: minimum FIFA overall rating.
            max_overall: maximum FIFA overall rating.
            limit: max players to list.
        """
        return get_service().search_players(
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
        club: str | None = None,
        nationality: str | None = None,
        position: str | None = None,
        limit: int = 10,
    ) -> str:
        """Highest-rated players, optionally filtered by club, nationality or position.

        Answers questions like "who are the best Brazilian players?" or
        "highest-rated players at Grêmio".

        Args:
            club: substring of club name (optional).
            nationality: e.g. "Brazil" (optional).
            position: FIFA code or group "GK"/"DEF"/"MID"/"FWD" (optional).
            limit: number of players to return.
        """
        return get_service().top_players(
            club=club, nationality=nationality, position=position, limit=limit
        )

    @server.tool()
    def player_profile(name: str) -> str:
        """Full profile of one player: ratings, attributes, club, contract data.

        Args:
            name: player name as listed (e.g. "Neymar Jr"); falls back to a
                fuzzy search and suggests close matches.
        """
        return get_service().player_profile(name)

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------

    @server.tool()
    def standings(competition: str = "Brasileirão Série A", season: int | None = None) -> str:
        """League table computed from match results (3 pts/win), with champion and relegated teams.

        Works for league competitions (Brasileirão Série A/B/C). Knockout
        competitions (Copa do Brasil, Libertadores) explain how to query
        their finals instead.

        Args:
            competition: league competition name or alias ("brasileirao", "serie b", ...).
            season: calendar year, e.g. 2019.
        """
        return get_service().standings(competition=competition, season=season)

    @server.tool()
    def finals(competition: str | None = None, season: int | None = None) -> str:
        """List cup finals (Copa do Brasil and Libertadores) with two-leg aggregates and winners.

        Args:
            competition: "Copa do Brasil", "Libertadores" or None for both.
            season: calendar year (optional).
        """
        return get_service().finals(competition=competition, season=season)

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------

    @server.tool()
    def biggest_wins(
        competition: str | None = None, season: int | None = None, limit: int = 10
    ) -> str:
        """Largest victory margins in the dataset, most lopsided first.

        Args:
            competition: optional competition restriction.
            season: optional calendar year.
            limit: number of matches to return.
        """
        return get_service().biggest_wins(competition=competition, season=season, limit=limit)

    @server.tool()
    def stats(competition: str | None = None, season: int | None = None) -> str:
        """Aggregate statistics: average goals per match, home/away/draw rates,
        top-scoring teams and best home/away records.

        Args:
            competition: optional competition (default: all).
            season: optional calendar year (default: all seasons).
        """
        return get_service().stats(competition=competition, season=season)

    @server.tool()
    def derbies(season: int | None = None, competition: str | None = None) -> str:
        """Matches between classic rivals (Fla-Flu, Derby Paulista, Gre-Nal,
        Clássico Mineiro, Ba-Vi and more), grouped by derby name.

        Args:
            season: optional calendar year.
            competition: optional competition restriction.
        """
        return get_service().derbies(season=season, competition=competition)

    return server


# Module-level server instance so `mcp dev server.py` / client configs that
# import the module find it, plus a __main__ guard for direct execution.
server = build_server()


def main() -> None:
    """Run the server on stdio (standard transport for local MCP clients)."""
    server.run()


if __name__ == "__main__":
    main()
