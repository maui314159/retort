"""MCP server exposing Brazilian soccer queries as tools."""

from __future__ import annotations

from functools import lru_cache

from mcp.server.mcpserver import MCPServer

from .data_loader import Dataset
from .queries import QueryEngine

INSTRUCTIONS = """\
Knowledge-graph style interface over Brazilian soccer datasets:
Brasileirão (2012-2022 + historical 2003-2019), Copa do Brasil (2012-2021),
Copa Libertadores (2013-2022), extended Serie A/B/C match statistics
(2014-2023), and a FIFA player database (18k players).

Start with search_matches / get_team_stats for match history, search_players
for FIFA player data, and get_standings for season tables computed from the
match results. Team names are normalized automatically ("Palmeiras-SP",
"Palmeiras", "Palmeiras FC" all work). Competitions accept aliases:
"Brasileirão", "Serie A", "Copa do Brasil", "Libertadores".\
"""


@lru_cache(maxsize=1)
def get_engine() -> QueryEngine:
    """Build the query engine once (dataset loads lazily on first use)."""
    return QueryEngine(Dataset())


def create_server() -> MCPServer:
    """Create the MCP server with all tools registered."""
    server = MCPServer(
        name="brazilian-soccer",
        version="1.0.0",
        instructions=INSTRUCTIONS,
    )
    engine = get_engine()
    register_tools(server, engine)
    return server


def register_tools(server: MCPServer, engine: QueryEngine) -> None:
    """Attach every query-engine capability as an MCP tool."""

    @server.tool(
        description=(
            "Find matches by team, opponent, competition, season, and/or date "
            "range. Team names are normalized (e.g. 'Palmeiras-SP' = "
            "'Palmeiras'). Competitions: Brasileirão, Serie B, Serie C, "
            "Copa do Brasil, Libertadores. Dates use YYYY-MM-DD or DD/MM/YYYY."
        )
    )
    def search_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        round_or_stage: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Search matches across all datasets."""
        return engine.search_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            round_or_stage=round_or_stage,
            limit=limit,
        )

    @server.tool(
        description=(
            "Win/draw/loss record, goals for/against, and win rate for one "
            "team, optionally filtered by competition, season, and venue "
            "('home' or 'away')."
        )
    )
    def get_team_stats(
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str | None = None,
    ) -> dict:
        """Aggregate record for a single team."""
        return engine.get_team_stats(
            team=team, competition=competition, season=season, venue=venue
        )

    @server.tool(
        description=(
            "Head-to-head record between two teams plus their most recent "
            "meetings. Detects classic rivalries (Fla-Flu, Gre-Nal, ...)."
        )
    )
    def head_to_head(team_a: str, team_b: str) -> dict:
        """Head-to-head comparison of two teams."""
        return engine.head_to_head(team_a=team_a, team_b=team_b)

    @server.tool(
        description=(
            "Search the FIFA player database by name, nationality, club, "
            "position (GK, CB, ST, ...), position category (goalkeeper, "
            "defender, midfielder, forward), and/or overall rating range. "
            "Results are sorted by overall rating (best first)."
        )
    )
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        position_category: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = 25,
    ) -> dict:
        """Search and rank FIFA player data."""
        return engine.search_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            position_category=position_category,
            min_overall=min_overall,
            max_overall=max_overall,
            limit=limit,
        )

    @server.tool(
        description=(
            "League standings calculated from match results for a competition "
            "and season (e.g. Brasileirão 2019). Marks the champion and, for "
            "20-team seasons, the relegation zone (bottom 4)."
        )
    )
    def get_standings(competition: str, season: int) -> dict:
        """Season table computed from results."""
        return engine.get_standings(competition=competition, season=season)

    @server.tool(
        description=(
            "Aggregate statistics for a competition and/or season: average "
            "goals per match, home/away win and draw rates, top scoring "
            "teams, and the biggest victories."
        )
    )
    def get_competition_stats(
        competition: str | None = None,
        season: int | None = None,
        top: int = 5,
    ) -> dict:
        """Competition-level aggregate statistics."""
        return engine.get_competition_stats(
            competition=competition, season=season, top=top
        )

    @server.tool(
        description=(
            "Rank teams by win rate at home or away (e.g. 'best away record'), "
            "optionally per competition and season."
        )
    )
    def get_best_records(
        venue: str = "home",
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 5,
        limit: int = 5,
    ) -> dict:
        """Best win-rate rankings for a venue."""
        return engine.get_best_records(
            venue=venue,
            competition=competition,
            season=season,
            min_matches=min_matches,
            limit=limit,
        )

    @server.tool(
        description=(
            "Find traditional derby matches (Fla-Flu, Clássico dos Milhões, "
            "Dérbi Paulista, Gre-Nal, Ba-Vi, ...) optionally filtered by "
            "season and competition."
        )
    )
    def search_derbies(
        season: int | None = None,
        competition: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Search rivalry matches."""
        return engine.search_derbies(
            season=season, competition=competition, limit=limit
        )

    @server.tool(
        description=(
            "List the competitions and seasons a team appears in across all "
            "match files."
        )
    )
    def get_team_competitions(team: str) -> dict:
        """Competitions and seasons for one team."""
        return engine.get_team_competitions(team=team)

    @server.tool(
        description=(
            "Cross-file club overview: all-time match record plus the FIFA "
            "squad for that club (players, average and top ratings)."
        )
    )
    def get_club_overview(team: str) -> dict:
        """Combined match + player view for a club."""
        return engine.get_club_overview(team=team)

    @server.tool(
        description=(
            "Aggregate statistics for a whole season across all competitions, "
            "including champions computed from standings."
        )
    )
    def get_season_summary(season: int) -> dict:
        """Season-wide aggregate statistics."""
        return engine.get_season_summary(season=season)

    @server.tool(
        description=(
            "Compare two seasons side by side (matches, goals, win rates, "
            "champions per competition)."
        )
    )
    def compare_seasons(season_a: int, season_b: int) -> dict:
        """Side-by-side season comparison."""
        return engine.compare_seasons(season_a=season_a, season_b=season_b)

    @server.tool(
        description="List teams present in the match data with match counts."
    )
    def list_teams(
        competition: str | None = None,
        limit: int | None = None,
    ) -> dict:
        """Discover team names."""
        return engine.list_teams(competition=competition, limit=limit)

    @server.tool(
        description=(
            "List competitions with match counts and season coverage "
            "(useful before filtering other queries)."
        )
    )
    def list_competitions() -> dict:
        """Discover competitions and seasons."""
        return engine.list_competitions()
