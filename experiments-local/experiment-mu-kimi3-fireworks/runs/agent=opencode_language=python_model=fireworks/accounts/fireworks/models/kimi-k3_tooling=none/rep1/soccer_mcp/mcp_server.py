"""FastMCP wiring: expose the tools API as MCP tools.

Run over stdio (default) with::

    python server.py

or programmatically::

    from soccer_mcp.mcp_server import create_server
    server = create_server()
    server.run()
"""

from __future__ import annotations

from fastmcp import FastMCP

from . import tools_api

SERVER_NAME = "brazilian-soccer"

TOOL_FUNCTIONS = [
    tools_api.dataset_summary,
    tools_api.list_competitions,
    tools_api.list_teams,
    tools_api.search_matches,
    tools_api.head_to_head,
    tools_api.last_match,
    tools_api.find_derbies,
    tools_api.team_stats,
    tools_api.team_competitions,
    tools_api.standings,
    tools_api.top_scoring_teams,
    tools_api.competition_stats,
    tools_api.biggest_wins,
    tools_api.best_home_records,
    tools_api.best_away_records,
    tools_api.compare_seasons,
    tools_api.search_players,
    tools_api.top_players,
    tools_api.player_profile,
]


def create_server() -> FastMCP:
    """Build the MCP server with every query tool registered."""
    server = FastMCP(
        SERVER_NAME,
        instructions=(
            "Knowledge-graph interface for Brazilian soccer: Brasileirão "
            "Série A/B/C, Copa do Brasil, Copa Libertadores (matches, "
            "standings, head-to-head, derbies, statistics) and a FIFA "
            "player database (ratings, clubs, nationalities). Team and "
            "competition names are normalized, so informal spellings like "
            "'Palmeiras-SP', 'Gremio' or 'brasileirao' all work."
        ),
    )
    for fn in TOOL_FUNCTIONS:
        server.tool(fn)
    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
