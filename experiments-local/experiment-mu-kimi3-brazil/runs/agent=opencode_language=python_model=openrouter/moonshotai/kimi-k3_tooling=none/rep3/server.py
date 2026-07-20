"""MCP server for Brazilian soccer data.

Exposes the query engine over the Model Context Protocol (stdio transport)
so an LLM client can answer natural-language questions about Brazilian
soccer: matches, teams, players, competitions and statistics.

Run standalone with::

    python server.py

The server pre-loads the CSV datasets once at startup; every tool call is
then served from memory (lookups << 2 s, aggregates << 5 s).
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

import query_engine as qe
from soccer_data import get_store

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge-graph style interface to Brazilian soccer data: "
        "Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores "
        "matches (2003-2023) plus the FIFA player database. Team names are "
        "normalised across datasets, so 'Flamengo-RJ', 'Flamengo' and "
        "'CR Flamengo' style variants all match the same club."
    ),
)


# ---------------------------------------------------------------------------
# Match tools
# ---------------------------------------------------------------------------
@mcp.tool()
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Find matches by criteria. ``team`` matches home or away; combine with
    ``opponent`` for fixtures between two teams (e.g. Flamengo vs
    Fluminense). ``competition`` accepts 'Brasileirão', 'Série A/B/C',
    'Copa do Brasil' or 'Libertadores'. ``venue`` is 'home' or 'away'.
    ``stage`` filters tournament stages (e.g. 'final', 'semifinals',
    'group stage') or a round number. Dates are ISO ('2023-09-03').
    Results are returned most recent first."""
    return qe.find_matches(team=team, opponent=opponent,
                           competition=competition, season=season,
                           date_from=date_from, date_to=date_to,
                           venue=venue, stage=stage, limit=limit)


@mcp.tool()
def head_to_head(team1: str, team2: str, limit: int = 10) -> dict:
    """Compare two teams: every match between them in the datasets plus the
    overall win/draw/loss balance (e.g. Palmeiras vs Santos)."""
    return qe.head_to_head(team1, team2, limit=limit)


# ---------------------------------------------------------------------------
# Team tools
# ---------------------------------------------------------------------------
@mcp.tool()
def team_statistics(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: Optional[str] = None,
) -> dict:
    """Win/draw/loss record, goals scored/conceded and win rate for a team.
    Use venue='home' for a home record (e.g. 'Corinthians home record in
    2022'). Without a competition filter a per-competition breakdown is
    included."""
    return qe.team_statistics(team, season=season, competition=competition,
                              venue=venue)


@mcp.tool()
def list_teams(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """List team names present in the data, optionally restricted to a
    competition and/or season."""
    return qe.list_teams(competition=competition, season=season)


# ---------------------------------------------------------------------------
# Player tools
# ---------------------------------------------------------------------------
@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> dict:
    """Search the FIFA player database. Filters: ``name`` (partial,
    accent-insensitive), ``nationality`` (e.g. 'Brazil'), ``club``
    (partial, e.g. 'Flamengo', 'Grêmio'), ``position`` (a code like 'ST',
    'CB', 'GK' or a group: 'forward', 'midfielder', 'defender',
    'goalkeeper') and ``min_overall``. Results are sorted by overall
    rating."""
    return qe.search_players(name=name, nationality=nationality, club=club,
                             position=position, min_overall=min_overall,
                             limit=limit)


@mcp.tool()
def top_players(
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Highest-rated players, e.g. top Brazilian players
    (nationality='Brazil') or the best players at a club."""
    return qe.top_players(nationality=nationality, club=club,
                          position=position, limit=limit)


@mcp.tool()
def player_profile(name: str) -> dict:
    """Profile of a single player (e.g. 'Who is Neymar?'): ratings, club,
    position and key skill attributes."""
    return qe.player_profile(name)


# ---------------------------------------------------------------------------
# Competition tools
# ---------------------------------------------------------------------------
@mcp.tool()
def competition_standings(
    season: int,
    competition: str = "Brasileirão Série A",
) -> dict:
    """League table for a season, calculated from match results (3 pts for
    a win, 1 for a draw; tie-breaks: wins, goal difference, goals for).
    Answers 'Who won the 2019 Brasileirão?' and 'Which teams were
    relegated?' (bottom four)."""
    return qe.competition_standings(season=season, competition=competition)


@mcp.tool()
def top_scoring_teams(
    season: Optional[int] = None,
    competition: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Teams ranked by goals scored, e.g. 'Which team scored the most goals
    in Série A 2023?'."""
    return qe.top_scoring_teams(season=season, competition=competition,
                                limit=limit)


@mcp.tool()
def list_competitions() -> dict:
    """List the competitions in the store with season coverage and match
    counts."""
    return qe.list_competitions()


# ---------------------------------------------------------------------------
# Statistics tools
# ---------------------------------------------------------------------------
@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """Matches with the largest goal margin (biggest victories)."""
    return qe.biggest_wins(competition=competition, season=season,
                           limit=limit)


@mcp.tool()
def best_team_records(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
    limit: int = 10,
    min_matches: int = 5,
) -> dict:
    """Teams ranked by points per game — answers 'Which team has the best
    away record?' (venue='away') or 'best home record' (venue='home')."""
    return qe.best_team_records(competition=competition, season=season,
                                venue=venue, limit=limit,
                                min_matches=min_matches)


@mcp.tool()
def competition_overview(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict:
    """Aggregate statistics: matches played, average goals per match and
    home/draw/away win rates (e.g. 'average goals per match in the
    Brasileirão')."""
    return qe.competition_overview(competition=competition, season=season)


def main() -> None:
    # Warm the cache so the first tool call is fast.
    get_store()
    mcp.run()


if __name__ == "__main__":
    main()
