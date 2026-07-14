"""
Context
=======
Module: brazilian_soccer_mcp.server
Purpose: FastMCP server exposing the :class:`KnowledgeBase` query engine as MCP
         tools so an LLM client can answer natural-language questions about
         Brazilian soccer.

Each tool maps to one spec capability category, accepts plain scalar arguments
(MCP-friendly), calls the engine, and returns a formatted text block from
:mod:`.formatting`. The knowledge base is constructed once at import time and
shared across tool invocations (read-only, thread-safe for our purposes).

Run
---
    python -m brazilian_soccer_mcp.server      # stdio MCP server

Set ``BRAZIL_SOCCER_DATA_DIR`` to point at a non-default data directory.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from . import formatting
from .knowledge import KnowledgeBase

_data_dir = os.environ.get("BRAZIL_SOCCER_DATA_DIR")
kb = KnowledgeBase(_data_dir)

mcp = FastMCP("brazilian-soccer")


@mcp.tool()
def dataset_overview() -> str:
    """Summarize what data is loaded: match/player counts, competitions, seasons."""
    s = kb.summary()
    return (
        f"Brazilian Soccer knowledge base:\n"
        f"- Matches: {s['total_matches']}\n"
        f"- Players: {s['total_players']}\n"
        f"- Competitions: {', '.join(s['competitions'])}\n"
        f"- Seasons: {s['season_range'][0]}–{s['season_range'][1]}"
    )


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
) -> str:
    """Find matches by team, opponent, competition, season, or date range.

    Team names may be partial and need not include state suffixes
    (e.g. "Flamengo" matches "Flamengo-RJ"). Dates are ISO ``YYYY-MM-DD``.
    """
    rows = kb.find_matches(team, opponent, competition, season, date_from, date_to, limit)
    bits = [b for b in (team, ("vs " + opponent) if opponent else None) if b]
    title = (" ".join(bits) + " matches:") if bits else "Matches:"
    return formatting.format_matches(rows, title)


@mcp.tool()
def head_to_head(team_a: str, team_b: str) -> str:
    """Head-to-head record between two teams across all competitions in the data."""
    return formatting.format_head_to_head(kb.head_to_head(team_a, team_b))


@mcp.tool()
def team_record(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> str:
    """Win/draw/loss record, goals and win rate for a team.

    ``venue`` is one of "all", "home", "away".
    """
    return formatting.format_team_stats(kb.team_stats(team, season, competition, venue))


@mcp.tool()
def team_competitions(team: str) -> str:
    """List the competitions a team appears in, with match counts and season spans."""
    return formatting.format_competitions(kb.competitions_for_team(team), team)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> str:
    """Search FIFA player data by name, nationality, club, position, or min rating.

    Results are sorted by Overall rating descending. Use nationality="Brazil"
    for Brazilian players.
    """
    rows = kb.find_players(name, nationality, club, position, min_overall, limit)
    return formatting.format_players(rows, "Players:")


@mcp.tool()
def players_by_club(nationality: str = "Brazil", top: int = 15) -> str:
    """Per-club player counts and average ratings for a given nationality."""
    return formatting.format_club_summary(kb.players_by_club_summary(nationality, top), nationality)


@mcp.tool()
def league_standings(competition: str, season: int) -> str:
    """Compute a league table (3-1-0 points) for a competition and season from
    match results. Best for round-robin leagues (Brasileirão Série A/B/C)."""
    return formatting.format_standings(kb.standings(competition, season), competition, season)


@mcp.tool()
def competition_statistics(competition: str | None = None, season: int | None = None) -> str:
    """Aggregate stats: average goals per match, home/away/draw rates."""
    return formatting.format_competition_stats(kb.competition_stats(competition, season))


@mcp.tool()
def biggest_wins(competition: str | None = None, season: int | None = None, limit: int = 10) -> str:
    """List the matches with the largest goal margins."""
    return formatting.format_biggest_wins(kb.biggest_wins(competition, season, limit))


@mcp.tool()
def top_scoring_teams(competition: str | None = None, season: int | None = None, limit: int = 10) -> str:
    """Rank teams by total goals scored in the filtered slice of matches."""
    return formatting.format_top_scoring(kb.top_scoring_teams(competition, season, limit))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
