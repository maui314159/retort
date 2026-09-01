"""MCP server exposing the Brazilian soccer knowledge graph.

Built on the official Model Context Protocol Python SDK.  The server runs
over stdio by default (``python -m brazilian_soccer_mcp``) and exposes the
query engine as MCP tools:

========================  ==================================================
Tool                      Capability
========================  ==================================================
search_matches            Match queries (team, opponent, dates, competition)
head_to_head              Statistical analysis (pairwise records)
team_statistics           Team queries (records, goals, home/away splits)
team_comparison           Team queries (side-by-side + head-to-head)
team_overview             Cross-file queries (matches + FIFA squad)
league_standings          Competition queries (tables computed from results)
competition_statistics    Statistical analysis (averages, win rates)
biggest_wins              Statistical analysis (largest margins)
search_players            Player queries (FIFA database filters)
player_profile            Player queries (full attributes + skills)
search_knowledge_graph    Knowledge-graph node search
graph_neighbors           Knowledge-graph relationship exploration
========================  ==================================================

Datasets are loaded once at startup; every tool responds from the indexed
in-memory model, keeping simple lookups well under the 2-second budget from
the specification.
"""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from .queries import QueryEngine

_engine: QueryEngine | None = None


def get_engine() -> QueryEngine:
    """Lazily build the default query engine (loads all six datasets)."""
    global _engine
    if _engine is None:
        _engine = QueryEngine()
    return _engine


def _json(result: dict) -> str:
    """Serialize a query result to pretty JSON (the tool response body)."""
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def create_app(engine: QueryEngine | None = None) -> MCPServer:
    """Build the MCP server application, binding tools to ``engine``."""
    qe = engine if engine is not None else get_engine()
    app = MCPServer(
        name="brazilian-soccer",
        title="Brazilian Soccer Knowledge Graph",
        description=(
            "Natural-language-ready interface over Brazilian soccer data: "
            "Brasileirão matches (2003-2021), Copa do Brasil, Copa Libertadores, "
            "extended match statistics and a FIFA player database."
        ),
        instructions=(
            "Use search_matches for fixtures, head_to_head for pairwise records, "
            "team_statistics/team_comparison/team_overview for team questions, "
            "league_standings/competition_statistics/biggest_wins for competitions, "
            "search_players/player_profile for FIFA player data, and "
            "search_knowledge_graph/graph_neighbors to explore entities and relations."
        ),
    )

    def guarded(fn):
        def wrapper(*args, **kwargs):
            try:
                return _json(fn(*args, **kwargs))
            except Exception as exc:  # keep tool failures protocol-visible
                return _json({"error": str(exc), "summary": f"Query failed: {exc}"})

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        wrapper.__annotations__ = fn.__annotations__
        return wrapper

    @app.tool()
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
        """Find matches by team, opponent, competition, season, stage or date range.

        Team names accept any common variant ("Flamengo-RJ", "Sao Paulo", "Grêmio").
        Competitions: "Brasileirão Série A", "Brasileirão Série B",
        "Brasileirão Série C", "Copa do Brasil", "Copa Libertadores".
        Dates are ISO "YYYY-MM-DD" and ranges are inclusive.  When both team and
        opponent are given, a head-to-head record is included.
        """
        return guarded(qe.search_matches)(
            team=team, opponent=opponent, competition=competition, season=season,
            date_from=date_from, date_to=date_to, stage=stage, limit=limit,
        )

    @app.tool()
    def head_to_head(team_a: str, team_b: str, competition: str | None = None, season: int | None = None) -> str:
        """Head-to-head record between two teams: wins, draws, losses and goals."""
        return guarded(qe.head_to_head)(team_a, team_b, competition, season)

    @app.tool()
    def team_statistics(
        team: str, competition: str | None = None, season: int | None = None, venue: str | None = None
    ) -> str:
        """Team record: played/wins/draws/losses, goals for/against, win rate.

        Optionally scope by competition, season, and venue ("home" or "away").
        Includes separate home and away splits.
        """
        return guarded(qe.team_statistics)(team, competition, season, venue)

    @app.tool()
    def team_comparison(
        team_a: str, team_b: str, competition: str | None = None, season: int | None = None
    ) -> str:
        """Side-by-side statistics for two teams plus their head-to-head record."""
        return guarded(qe.team_comparison)(team_a, team_b, competition, season)

    @app.tool()
    def team_overview(team: str) -> str:
        """Cross-file overview of a team: match record, competitions, seasons and FIFA-squad players."""
        return guarded(qe.team_overview)(team)

    @app.tool()
    def league_standings(competition: str, season: int) -> str:
        """League standings for a season, computed from match results.

        For the Brasileirão Série A the champion (1st) and the four relegated
        teams are annotated.
        """
        return guarded(qe.league_standings)(competition, season)

    @app.tool()
    def competition_statistics(competition: str, season: int | None = None) -> str:
        """Aggregate statistics for a competition: averages, home/away/draw rates."""
        return guarded(qe.competition_statistics)(competition, season)

    @app.tool()
    def biggest_wins(competition: str | None = None, season: int | None = None, limit: int = 10) -> str:
        """Largest winning margins in the dataset, optionally scoped to a competition or season."""
        return guarded(qe.biggest_wins)(competition, season, limit)

    @app.tool()
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_age: int | None = None,
        limit: int = 20,
    ) -> str:
        """Search the FIFA player database by name, nationality, club, position, rating or age.

        Results are ordered by overall rating.  Example filters:
        nationality="Brazil", club="Flamengo", position="ST", min_overall=85.
        """
        return guarded(qe.search_players)(
            name=name, nationality=nationality, club=club, position=position,
            min_overall=min_overall, max_age=max_age, limit=limit,
        )

    @app.tool()
    def player_profile(player_name: str) -> str:
        """Full profile for one player: attributes, skills and contract details."""
        return guarded(qe.player_profile)(player_name)

    @app.tool()
    def search_knowledge_graph(
        query: str, node_types: list[str] | None = None, limit: int = 20
    ) -> str:
        """Search knowledge-graph nodes by name.

        Node types: "Team", "Player", "Club", "Competition", "Match".
        """
        return guarded(qe.graph_search)(query, node_types, limit)

    @app.tool()
    def graph_neighbors(node_name: str, edge_types: list[str] | None = None, limit: int = 50) -> str:
        """Explore relationships around a node (played, beat, plays_for, participates_in, ...)."""
        return guarded(qe.graph_neighbors)(node_name, edge_types, limit)

    return app


def main() -> None:
    """Entry point: load the datasets and serve MCP over stdio."""
    engine = get_engine()
    app = create_app(engine)
    app.run()
