"""MCP server exposing the Brazilian soccer knowledge graph as tools.

The server uses the ``mcp`` 2.x SDK (``mcp.server.mcpserver.MCPServer``) and
exposes one tool per high-level capability required by the specification.  Each
tool delegates to the query layer in :mod:`brazilian_soccer_mcp.queries`, which
operates on the in-memory data loaded by
:func:`brazilian_soccer_mcp.data_loader.load_all`.

Run with::

    python -m brazilian_soccer_mcp.server
    python -m brazilian_soccer_mcp.server --transport streamable-http
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from mcp.server.mcpserver import MCPServer

from . import __version__
from .queries import (
    average_goals,
    biggest_wins,
    champions,
    compare_teams,
    competitions_for_team,
    derbies,
    find_matches,
    head_to_head,
    home_away_balance,
    players_for_club,
    relegated_teams,
    search_players,
    standings,
    team_stats,
    top_brazilian_players,
    top_clubs_by_nationality,
)


def _json_default(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def _dumps(obj) -> str:
    return json.dumps(obj, default=_json_default, ensure_ascii=False, indent=2)


_server = MCPServer(
    name="brazilian-soccer-mcp",
    version=__version__,
    instructions=(
        "Brazilian soccer knowledge graph. Use the tools to answer natural "
        "language questions about players, teams, matches and competitions "
        "sourced from the bundled Kaggle datasets (Brasileirão, Copa do "
        "Brasil, Copa Libertadores, BR-Football extended stats, the "
        "2003-2019 historical Brasileirão and the FIFA player database)."
    ),
)


@_server.tool(
    name="find_matches",
    description=(
        "Find matches by team, opponent, competition, season and/or date "
        "range. Pass a team name to get all of its matches; pass both team "
        "and opponent to get head-to-head fixtures. Competition accepts "
        "aliases such as 'Brasileirão', 'Copa do Brasil', 'Libertadores'."
    ),
)
def tool_find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> str:
    return _dumps(find_matches(
        team=team, opponent=opponent, competition=competition,
        season=season, start_date=start_date, end_date=end_date, limit=limit,
    ))


@_server.tool(
    name="head_to_head",
    description=(
        "Return the head-to-head record (wins/draws/losses, goals, match list) "
        "between two teams, optionally filtered by competition or season."
    ),
)
def tool_head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    return _dumps(head_to_head(team_a, team_b, competition=competition, season=season))


@_server.tool(
    name="team_stats",
    description=(
        "Return a team's win/loss/draw record, goals scored and conceded, and "
        "per-competition breakdown. Optionally filter by season, competition "
        "and venue ('home' or 'away')."
    ),
)
def tool_team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> str:
    return _dumps(team_stats(team, season=season, competition=competition, venue=venue))


@_server.tool(
    name="compare_teams",
    description="Compare two teams' overall records and head-to-head history.",
)
def tool_compare_teams(team_a: str, team_b: str, season: int | None = None) -> str:
    return _dumps(compare_teams(team_a, team_b, season=season))


@_server.tool(
    name="competitions_for_team",
    description="List all competitions a team has appeared in, with match counts.",
)
def tool_competitions_for_team(team: str) -> str:
    return _dumps(competitions_for_team(team))


@_server.tool(
    name="search_players",
    description=(
        "Search the FIFA player database by name, nationality, club, "
        "position and/or overall rating range. Results are sorted by overall "
        "rating by default."
    ),
)
def tool_search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 50,
    sort_by: str = "Overall",
) -> str:
    return _dumps(search_players(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, max_overall=max_overall, limit=limit,
        sort_by=sort_by,
    ))


@_server.tool(
    name="top_brazilian_players",
    description="Return the highest-rated Brazilian players in the FIFA dataset.",
)
def tool_top_brazilian_players(limit: int = 20) -> str:
    return _dumps(top_brazilian_players(limit=limit))


@_server.tool(
    name="players_for_club",
    description="Return all players attached to a club plus the average overall rating.",
)
def tool_players_for_club(club: str) -> str:
    return _dumps(players_for_club(club))


@_server.tool(
    name="top_clubs_by_nationality",
    description=(
        "Rank clubs by how many players of a given nationality they employ "
        "(defaults to Brazilian players), including average rating."
    ),
)
def tool_top_clubs_by_nationality(nationality: str = "Brazil", limit: int = 20) -> str:
    return _dumps(top_clubs_by_nationality(nationality=nationality, limit=limit))


@_server.tool(
    name="standings",
    description=(
        "Compute a league-style standings table from match results. Defaults "
        "to Brasileirão Serie A; pass a season (e.g. 2019) to get that year's "
        "table. The top team is flagged as champion."
    ),
)
def tool_standings(competition: str = "Brasileirão Serie A", season: int | None = None) -> str:
    return _dumps(standings(competition, season=season))


@_server.tool(
    name="champions",
    description="Return the champion of every season present in a competition.",
)
def tool_champions(competition: str = "Brasileirão Serie A") -> str:
    return _dumps(champions(competition=competition))


@_server.tool(
    name="relegated_teams",
    description="Return the bottom n teams (relegation zone) for a competition/season.",
)
def tool_relegated_teams(
    competition: str = "Brasileirão Serie A",
    season: int | None = None,
    n: int = 4,
) -> str:
    return _dumps(relegated_teams(competition, season=season, n=n))


@_server.tool(
    name="average_goals",
    description=(
        "Return average goals-per-match plus home/away win and draw rates, "
        "optionally filtered by competition and/or season."
    ),
)
def tool_average_goals(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    return _dumps(average_goals(competition=competition, season=season))


@_server.tool(
    name="biggest_wins",
    description="Return the highest-margin victories, optionally filtered.",
)
def tool_biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    return _dumps(biggest_wins(competition=competition, season=season, limit=limit))


@_server.tool(
    name="home_away_balance",
    description="Return per-team home vs away performance breakdown.",
)
def tool_home_away_balance(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    return _dumps(home_away_balance(competition=competition, season=season))


@_server.tool(
    name="derbies",
    description="Return matches between traditional rival teams (derbies).",
)
def tool_derbies(
    season: int | None = None,
    competition: str | None = None,
) -> str:
    return _dumps(derbies(season=season, competition=competition))


def get_server() -> MCPServer:
    return _server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="brazilian-soccer-mcp")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"],
                        default=os.environ.get("MCP_TRANSPORT", "stdio"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    _server.run(transport=args.transport)


if __name__ == "__main__":
    main(sys.argv[1:])
