"""FastMCP server exposing the Brazilian soccer knowledge graph as tools.

Run with stdio transport (default, for MCP clients such as Claude Desktop)::

    python -m brazilian_soccer_mcp.server

or over HTTP::

    python -m brazilian_soccer_mcp.server --transport streamable-http --port 8000
"""

from __future__ import annotations

import argparse

from fastmcp import FastMCP

from .data import DataStore
from .normalization import COMP_BRASILEIRAO_A
from .queries import QueryEngine

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge graph over Brazilian soccer data: Brasileirão Série A/B/C, "
        "Copa do Brasil, Copa Libertadores matches (2003-2023) and the FIFA "
        "player database. Team names are normalized across spellings "
        "('Palmeiras-SP', 'Palmeiras'); dates accept ISO or DD/MM/YYYY."
    ),
)

_store: DataStore | None = None
_engine: QueryEngine | None = None


def get_engine() -> QueryEngine:
    """Lazily load the datasets (once) and return the query engine."""
    global _store, _engine
    if _engine is None:
        _store = DataStore()
        _engine = QueryEngine(_store)
    return _engine


@mcp.tool
def dataset_overview() -> dict:
    """Overview of the loaded datasets: row counts per source file, seasons
    covered, number of teams/players and knowledge-graph statistics."""
    return get_engine().overview()


@mcp.tool
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> dict:
    """Find matches by criteria. Any filter can be combined.

    - team: team name in any spelling ("Flamengo", "Flamengo-RJ"); matches
      games where the team played home OR away.
    - opponent: second team, for fixtures between two specific teams.
    - competition: "Brasileirão", "Série A", "Copa do Brasil", "Libertadores".
    - season: 4-digit year, e.g. 2023.
    - date_from / date_to: ISO ("2023-01-01") or Brazilian ("01/01/2023").
    - limit: max matches returned (most recent first).
    """
    return get_engine().search_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        date_from=date_from, date_to=date_to, limit=limit,
    )


@mcp.tool
def head_to_head(team_a: str, team_b: str, limit: int = 10) -> dict:
    """Compare two teams: all matches between them plus wins/draws summary.
    Example: head_to_head("Palmeiras", "Santos")."""
    return get_engine().head_to_head(team_a, team_b, limit=limit)


@mcp.tool
def team_statistics(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss record, goals for/against and win rate for a team.
    Filter by season and/or competition; venue is "home", "away" or "all".
    Example: team_statistics("Corinthians", season=2022, venue="home")."""
    return get_engine().team_statistics(
        team, season=season, competition=competition, venue=venue
    )


@mcp.tool
def competition_standings(
    season: int,
    competition: str = COMP_BRASILEIRAO_A,
) -> dict:
    """League table for a season, calculated from match results (3 pts for a
    win, 1 for a draw). Returns champion and relegation zone when applicable.
    Example: competition_standings(2019) -> 2019 Brasileirão table."""
    return get_engine().standings(season, competition)


@mcp.tool
def team_competitions(team: str) -> dict:
    """Which competitions a team has played in (knowledge-graph traversal),
    plus the first/last season seen in the data."""
    return get_engine().team_competitions(team)


@mcp.tool
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 10,
) -> dict:
    """Search FIFA players by name, nationality, club, position and minimum
    overall rating. Results sorted by Overall rating (best first).
    Example: search_players(nationality="Brazil", club="Flamengo")."""
    return get_engine().search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, limit=limit,
    )


@mcp.tool
def top_rated_players(
    nationality: str | None = None,
    club: str | None = None,
    limit: int = 10,
) -> dict:
    """Highest-rated players, optionally filtered by nationality and/or club.
    Example: top_rated_players(nationality="Brazil", limit=5)."""
    return get_engine().top_players(nationality=nationality, club=club, limit=limit)


@mcp.tool
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict:
    """Largest victory margins in the dataset (optionally filtered)."""
    return get_engine().biggest_wins(competition=competition, season=season, limit=limit)


@mcp.tool
def competition_stats(
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Aggregate statistics: average goals per match, home/draw/away win
    rates and the biggest win. With no filters, covers the whole dataset."""
    return get_engine().competition_stats(competition=competition, season=season)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument("--transport", default="stdio",
                        choices=["stdio", "streamable-http", "sse"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
