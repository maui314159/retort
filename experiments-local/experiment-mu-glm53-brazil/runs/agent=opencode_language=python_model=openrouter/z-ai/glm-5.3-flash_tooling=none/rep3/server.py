#!/usr/bin/env python3
"""Brazilian Soccer MCP server entry point.

Run with (stdio transport, the MCP default):

    ./venv/bin/python server.py

The server exposes these MCP tools backed by the six Kaggle datasets:

- ``search_matches``        matches by team/opponent/competition/season/
                            dates/stage
- ``get_head_to_head``      head-to-head record between two clubs
- ``get_team_stats``        a club's record (optionally per season,
                            competition and home/away)
- ``get_team_history``      every competition and season a club played
- ``list_teams``            clubs covered (optionally per competition)
- ``get_standings``         league table computed from match results
- ``search_players``        FIFA players filtered by name/nationality/
                            club/position/rating
- ``get_player``            one player's full profile
- ``search_players_at_club`` squad list with average rating
- ``get_competitions``      catalog of competitions, seasons, match counts
- ``get_statistics``        aggregates: avg goals, home win rate, biggest
                            wins, best home/away records
- ``compare_seasons``       season-vs-season aggregates and champions
- ``get_derbies``           traditional rivalry fixtures and records
- ``answer_question``       deterministic natural-language fallback router

Resources: ``soccer://status`` (dataset overview), ``soccer://teams``,
``soccer://competitions`` and ``soccer://derbies``.
"""

from __future__ import annotations

import argparse
import json

from mcp.server.fastmcp import FastMCP

from brazilian_soccer.store import NotFound, SoccerStore
from brazilian_soccer.tools import answer_question as route_question

mcp = FastMCP("brazilian-soccer")
store = SoccerStore()          # loaded once at startup (~0.6 s)


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _ok(**payload) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _safe(fn, *args, **kwargs) -> str:
    try:
        return _ok(**fn(*args, **kwargs))
    except NotFound as exc:
        return _err(str(exc))


# ----------------------------------------------------------------------
# match tools
# ----------------------------------------------------------------------

@mcp.tool()
def search_matches(team: str = "", opponent: str = "", competition: str = "",
                   season: int = 0, stage: str = "", date_from: str = "",
                   date_to: str = "", limit: int = 25,
                   order: str = "asc") -> str:
    """Search matches by team (home/away/either), opponent, competition
    (Brasileirão Serie A/B/C, Copa do Brasil, Copa Libertadores), season,
    cup/international stage (e.g. "final"), and/or date range (YYYY-MM-DD).
    order: "asc" (oldest first, default) or "desc" (most recent first)."""
    return _safe(store.search_matches,
                 team=team or None, opponent=opponent or None,
                 competition=competition or None,
                 season=season or None, stage=stage or None,
                 date_from=date_from or None, date_to=date_to or None,
                 limit=limit, order=order or "asc")


@mcp.tool()
def get_head_to_head(team_a: str, team_b: str, competition: str = "",
                     limit: int = 25) -> str:
    """Head-to-head record between two clubs (wins/draws/losses, goals,
    derby name if a traditional rivalry, recent fixtures)."""
    return _safe(store.head_to_head, team_a, team_b,
                 competition or None, limit)


@mcp.tool()
def get_team_stats(team: str, season: int = 0, competition: str = "",
                   venue: str = "") -> str:
    """A club's record: matches, wins, draws, losses, goals for/against,
    points and win rate.  Filter by season, competition and/or venue
    ("home"/"away")."""
    return _safe(store.team_stats, team, season or None,
                 competition or None, venue or None)


@mcp.tool()
def get_team_history(team: str) -> str:
    """Every competition and season a club played in the datasets, with its
    overall record."""
    return _safe(store.team_history, team)


@mcp.tool()
def list_teams(competition: str = "", season: int = 0) -> str:
    """Clubs covered by the datasets, with match counts; filter by
    competition and/or season."""
    return _safe(store.list_teams, competition or None, season or None)


# ----------------------------------------------------------------------
# competition tools
# ----------------------------------------------------------------------

@mcp.tool()
def get_competitions() -> str:
    """Catalog of competitions: seasons covered, match counts."""
    return _safe(store.competitions)


@mcp.tool()
def get_standings(competition: str, season: int, top: int = 0) -> str:
    """League standings computed from match results (3-1-0 points,
    tiebreak: points, wins, goal difference, goals).  Champion and Série A
    relegation zone included.  Only for league competitions."""
    return _safe(store.standings, competition, season, top or None)


@mcp.tool()
def compare_seasons(competition: str, season_a: int, season_b: int) -> str:
    """Compare two seasons of a competition: aggregates and champions."""
    return _safe(store.compare_seasons, competition, season_a, season_b)


# ----------------------------------------------------------------------
# player tools
# ----------------------------------------------------------------------

@mcp.tool()
def search_players(name: str = "", nationality: str = "", club: str = "",
                   position: str = "", min_overall: int = 0,
                   max_overall: int = 0, limit: int = 25) -> str:
    """Search the FIFA player database by name (substring), nationality,
    club, position (e.g. ST, GK) and/or Overall rating range, sorted by
    rating."""
    return _safe(store.search_players,
                 name=name or None, nationality=nationality or None,
                 club=club or None, position=position or None,
                 min_overall=min_overall or None,
                 max_overall=max_overall or None, limit=limit)


@mcp.tool()
def get_player(name: str) -> str:
    """Full profile of one player by (fuzzy) name: rating, potential,
    club, skills, height/weight, value/wage."""
    return _safe(store.get_player, name)


@mcp.tool()
def search_players_at_club(club: str, limit: int = 25) -> str:
    """Players of a club in the FIFA dataset, with average rating."""
    return _safe(store.players_at_club, club, limit)


# ----------------------------------------------------------------------
# statistics + derbies + NL fallback
# ----------------------------------------------------------------------

@mcp.tool()
def get_statistics(competition: str = "", season: int = 0) -> str:
    """Aggregate statistics: average goals per match, home/away win rates,
    biggest victories, best home and away records."""
    return _safe(store.statistics, competition or None, season or None)


@mcp.tool()
def get_derbies(season: int = 0, competition: str = "") -> str:
    """Traditional rivalry matches (Fla-Flu, Grenal, Dérbi Paulista, ...):
    records and recent fixtures."""
    return _safe(store.derbies, season or None, competition or None)


@mcp.tool()
def answer_question(question: str) -> str:
    """Best-effort natural-language fallback: routes a question about
    Brazilian soccer to the right structured query (matches, head-to-head,
    team stats, standings, players, statistics, derbies)."""
    try:
        return _ok(**route_question(store, question))
    except NotFound as exc:
        return _err(str(exc))


# ----------------------------------------------------------------------
# resources
# ----------------------------------------------------------------------

@mcp.resource("soccer://status")
def resource_status() -> str:
    return _ok(**store.status())


@mcp.resource("soccer://teams")
def resource_teams() -> str:
    return _ok(**store.list_teams())


@mcp.resource("soccer://competitions")
def resource_competitions() -> str:
    return _ok(**store.competitions())


@mcp.resource("soccer://derbies")
def resource_derbies() -> str:
    return _ok(**store.derbies())


# ----------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
