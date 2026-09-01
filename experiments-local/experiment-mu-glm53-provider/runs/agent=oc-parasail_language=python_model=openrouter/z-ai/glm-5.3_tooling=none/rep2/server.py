"""Brazilian Soccer MCP Server (stdio transport).

Exposes the soccer_mcp query engine as Model Context Protocol tools so an
LLM client can answer natural-language questions about Brazilian soccer:
matches, teams, players, competitions, statistics and the knowledge graph.

Run:
    python server.py            # stdio transport (for MCP clients)
    python server.py --info     # print tool inventory and exit

Every tool returns a JSON document containing a human-formatted
``summary`` (the answer format from the specification) plus structured
fields for programmatic use.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.mcpserver import MCPServer

from soccer_mcp.engine import get_engine

server = MCPServer(
    name="brazilian-soccer-mcp",
    title="Brazilian Soccer MCP Server",
    description=(
        "Knowledge-graph interface for Brazilian soccer data: Brasileirão "
        "Série A/B/C, Copa do Brasil, Copa Libertadores matches (2003-2023) "
        "and a FIFA 19 player database (18,207 players)."
    ),
    instructions=(
        "Query Brazilian soccer data. Team names are normalized across "
        "datasets (state suffixes, accents and naming variants are handled), "
        "so 'Flamengo', 'flamengo rj' and 'Flamengo-RJ' all match. "
        "Competitions: 'Série A', 'Série B', 'Série C', 'Copa do Brasil', "
        "'Libertadores'. Standings are calculated directly from match "
        "results. For team name disambiguation use list_clubs first."
    ),
)


def _json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@server.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    limit: int = 50,
) -> str:
    """Find matches by team, opponent, competition, season, date range or stage.

    Examples: matches between Flamengo and Fluminense; all Palmeiras
    matches in 2023; Copa do Brasil matches in May 2019; Libertadores
    finals (stage='final'). Dates use YYYY-MM-DD. Competition can be
    'Série A', 'Série B', 'Série C', 'Copa do Brasil' or 'Libertadores'.
    """
    return _json(
        get_engine().search_matches(
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            stage=stage,
            limit=limit,
        )
    )


@server.tool()
def head_to_head(team_a: str, team_b: str) -> str:
    """Compare two teams head-to-head: all their matches, wins/draws/losses and goals."""
    return _json(get_engine().head_to_head(team_a=team_a, team_b=team_b))


@server.tool()
def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> str:
    """Win/draw/loss record and goals for a team, optionally filtered by
    season, competition and venue ('home', 'away' or 'all')."""
    return _json(
        get_engine().team_stats(
            team=team, season=season, competition=competition, venue=venue
        )
    )


@server.tool()
def team_profile(team: str) -> str:
    """Cross-file profile of a team: competitions played, seasons, overall
    record, FIFA squad (if covered) and most recent match."""
    return _json(get_engine().team_profile(team=team))


@server.tool()
def best_records(
    venue: str = "home",
    competition: str | None = None,
    season: int | None = None,
    minimum_matches: int = 10,
    limit: int = 10,
) -> str:
    """Rank teams by win rate for a venue ('home', 'away' or 'all')."""
    return _json(
        get_engine().best_records(
            venue=venue,
            competition=competition,
            season=season,
            minimum_matches=minimum_matches,
            limit=limit,
        )
    )


@server.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> str:
    """Search the FIFA player database (FIFA 19 snapshot, 18,207 players)
    by name (substring), nationality, club, position or minimum rating."""
    return _json(
        get_engine().search_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            limit=limit,
        )
    )


@server.tool()
def top_players(
    nationality: str | None = None,
    club: str | None = None,
    limit: int = 10,
) -> str:
    """Highest-rated players by FIFA overall rating, optionally filtered by
    nationality (e.g. 'Brazil') or club."""
    return _json(get_engine().top_players(nationality=nationality, club=club, limit=limit))


@server.tool()
def players_at_brazilian_clubs() -> str:
    """Summary of Brazilian players at Brazilian clubs in the FIFA dataset."""
    return _json(get_engine().players_at_brazilian_clubs())


@server.tool()
def standings(competition: str, season: int) -> str:
    """League table calculated from match results (Série A, Série B or
    Série C). Returns champion, full table, relegation zone and a
    completeness note when the dataset only partially covers the season."""
    return _json(get_engine().standings(competition=competition, season=season))


@server.tool()
def competition_finals(competition: str) -> str:
    """All finals and winners for cup competitions (Copa do Brasil,
    Libertadores), including two-legged aggregates."""
    return _json(get_engine().competition_finals(competition=competition))


@server.tool()
def competition_info() -> str:
    """Coverage of each competition in the dataset: seasons, matches, sources."""
    return _json(get_engine().competition_info())


@server.tool()
def top_scoring_teams(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Teams with the most goals scored in a competition/season. Note:
    individual top scorers cannot be derived - the datasets record team
    goals only."""
    return _json(
        get_engine().top_scoring_teams(competition=competition, season=season, limit=limit)
    )


@server.tool()
def goal_averages(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Average goals per match plus home win, draw and away win rates."""
    return _json(get_engine().goal_averages(competition=competition, season=season))


@server.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Largest victory margins in the dataset."""
    return _json(get_engine().biggest_wins(competition=competition, season=season, limit=limit))


@server.tool()
def derbies(season: int | None = None, limit: int = 50) -> str:
    """Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista,
    Ba-Vi and other Brazilian derbies), optionally for one season."""
    return _json(get_engine().derbies(season=season, limit=limit))


@server.tool()
def graph_overview() -> str:
    """Knowledge graph summary: node and edge counts by type."""
    return _json(get_engine().graph_overview())


@server.tool()
def team_graph(team: str) -> str:
    """Knowledge-graph neighbourhood of a team: competitions (via match
    nodes), most frequent opponents and FIFA squad."""
    return _json(get_engine().team_graph(team=team))


@server.tool()
def graph_paths(entity_a: str, entity_b: str, max_hops: int = 4) -> str:
    """Shortest knowledge-graph connections between two entities (players,
    teams, competitions). E.g. how Neymar and Grêmio are connected."""
    return _json(
        get_engine().graph_paths(entity_a=entity_a, entity_b=entity_b, max_hops=max_hops)
    )


@server.tool()
def list_clubs(query: str | None = None, limit: int = 25) -> str:
    """List known clubs with their dataset presence; useful to
    disambiguate team names before other queries."""
    return _json(get_engine().list_clubs(query=query, limit=limit))


async def _print_info() -> None:
    tools = await server.list_tools()
    print(f"{server.name}: {len(tools)} tools")
    for tool in tools:
        print(f"  - {tool.name}: {(tool.description or '').splitlines()[0]}")
    engine = get_engine()
    print(
        f"data: {len(engine.matches)} matches, {len(engine.players)} players, "
        f"knowledge graph: {engine.kg.stats()['nodes']} nodes"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP Server")
    parser.add_argument("--info", action="store_true", help="print tool inventory and exit")
    args = parser.parse_args()

    if args.info:
        asyncio.run(_print_info())
        return

    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
