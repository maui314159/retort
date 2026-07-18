"""
mcp_server.py
=============

MCP (Model Context Protocol) server for Brazilian soccer data.

Context block
-------------
This module exposes the query layer implemented in ``soccer_data.py`` as a
set of MCP *tools* that an LLM client can call to answer natural-language
questions about Brazilian soccer. It uses the FastMCP high-level SDK
(``mcp.server.fastmcp.FastMCP``) so each tool is a plain Python function
decorated with ``@mcp.tool()``.

Tools provided
--------------
* ``search_matches``       – find matches by team/opponent/competition/season/date
* ``last_match``           – most recent match between two (or one) teams
* ``head_to_head``         – full head-to-head record between two teams
* ``team_stats``           – win/draw/loss & goals for a team, optionally by venue
* ``team_competitions``    – competitions a team has played in
* ``standings``            – computed standings table for a competition+season
* ``biggest_wins``         – largest goal-difference victories
* ``average_goals``        – average goals/match and home-win rate
* ``best_record``          – teams ranked by win rate (home/away/overall)
* ``derbies``              – matches between traditional Brazilian rival pairs
* ``player_search``        – search FIFA player database by name/nationality/club/position
* ``top_players``          – top-rated players by overall (with filters)
* ``brazilians_at_brazilian_clubs`` – Brazilian players at domestic clubs
* ``list_competitions``    – all competitions present in the dataset
* ``list_seasons``         – seasons available for a competition

Running
-------
    python mcp_server.py                 # stdio transport (default)
    python mcp_server.py --transport sse --port 8000   # SSE transport

The CSV datasets under ``data/kaggle/`` are loaded once on first use and
cached for the lifetime of the process via ``soccer_data.get_store()``.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from soccer_data import get_store

# ---------------------------------------------------------------------------
# Server + store
# ---------------------------------------------------------------------------

mcp = FastMCP("brazilian-soccer")


def _store():
    """Lazy accessor for the cached SoccerStore (loads CSVs on first call)."""
    return get_store()


# ---------------------------------------------------------------------------
# Match tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int = 50,
) -> str:
    """Search matches across all Brazilian soccer datasets.

    Optional filters:
      team        – team name (home or away). Suffix variants ("Palmeiras-SP")
                    and accents are normalized automatically.
      opponent    – restrict to matches against this team.
      competition – one of: Brasileirão, Brasileirão (2003-2019),
                    Copa do Brasil, Copa Libertadores, Serie A, Serie B, Serie C.
      season      – year (e.g. 2023).
      start / end – ISO date bounds (YYYY-MM-DD).
      limit       – max matches to return (default 50).

    Returns JSON: a list of match objects with date, home, away, scores,
    competition, season and stage.
    """
    matches = _store().search_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        start=start, end=end, limit=limit,
    )
    return json.dumps(matches, ensure_ascii=False, indent=2)


@mcp.tool()
def last_match(team: str, opponent: str | None = None) -> str:
    """Return the most recent match involving ``team`` (optionally vs ``opponent``).

    Returns JSON with date, home, away, scores, competition, season, stage,
    or an empty-object JSON string when no match is found.
    """
    res = _store().last_match(team=team, opponent=opponent)
    return json.dumps(res or {}, ensure_ascii=False, indent=2)


@mcp.tool()
def head_to_head(team_a: str, team_b: str) -> str:
    """Full head-to-head record between two teams across all datasets.

    Returns JSON: wins/draws for each side, goals, and the list of matches.
    """
    res = _store().head_to_head(team_a, team_b)
    return json.dumps(res, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Team tools
# ---------------------------------------------------------------------------


@mcp.tool()
def team_stats(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> str:
    """Win/draw/loss record and goals for a team.

    venue – "home", "away", or None (both, default).
    competition/season – optional filters.
    """
    res = _store().team_stats(team=team, competition=competition, season=season, venue=venue)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def team_competitions(team: str) -> str:
    """List every competition a team has matches in, with match counts."""
    res = _store().team_competitions(team=team)
    return json.dumps(res, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Competition tools
# ---------------------------------------------------------------------------


@mcp.tool()
def standings(competition: str, season: int) -> str:
    """Compute the standings table for a competition+season from match results.

    3 pts per win, 1 per draw. Teams are ranked by points, then wins, then
    goal difference, then goals for. Returns JSON with the full table.
    """
    res = _store().standings(competition=competition, season=season)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Largest goal-difference victories, optionally filtered."""
    res = _store().biggest_wins(competition=competition, season=season, limit=limit)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def average_goals(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Average goals per match and home-win rate for a filter."""
    res = _store().average_goals(competition=competition, season=season)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def best_record(
    venue: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Rank teams by win rate. venue – home/away/overall."""
    res = _store().best_record(venue=venue, competition=competition, season=season, limit=limit)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def derbies(season: int | None = None, limit: int = 50) -> str:
    """Matches between traditional Brazilian rival clubs (Fla-Flu, Derby
    Paulista, Grenal, ...), optionally filtered by season."""
    res = _store().derbies(season=season, limit=limit)
    return json.dumps(res, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Player tools
# ---------------------------------------------------------------------------


@mcp.tool()
def player_search(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
    sort_by: str = "Overall",
    desc: bool = True,
) -> str:
    """Search the FIFA player database.

    All filters optional and combined (AND). sort_by defaults to "Overall".
    Returns JSON list of player dicts (name, overall, potential, club, position...).
    """
    res = _store().player_search(
        name=name, nationality=nationality, club=club, position=position,
        min_overall=min_overall, limit=limit, sort_by=sort_by, desc=desc,
    )
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def top_players(
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> str:
    """Top-rated players by FIFA Overall, with optional nationality/club/position filters."""
    res = _store().top_players(nationality=nationality, club=club, position=position, limit=limit)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def brazilians_at_brazilian_clubs(limit: int = 25) -> str:
    """Brazilian players whose club is a Brazilian club present in the match data."""
    res = _store().brazilians_at_brazilian_clubs(limit=limit)
    return json.dumps(res, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Introspection tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_competitions() -> str:
    """All competition names present in the loaded datasets."""
    res = _store().list_competitions()
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def list_seasons(competition: str | None = None) -> str:
    """Seasons available for a competition (or all seasons when omitted)."""
    res = _store().list_seasons(competition=competition)
    return json.dumps(res, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument(
        "--transport", choices=["stdio", "sse"], default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE transport")
    args = parser.parse_args()

    # Eagerly load the store so the first tool call is fast and any data
    # errors surface at startup rather than mid-session.
    _store()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
