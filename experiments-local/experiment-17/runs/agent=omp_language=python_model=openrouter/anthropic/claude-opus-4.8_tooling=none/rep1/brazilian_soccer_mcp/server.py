"""
Context
=======
Module: brazilian_soccer_mcp.server

The MCP entry point. Exposes the query layer (queries.py) as FastMCP tools an
LLM client can call to answer natural-language questions about Brazilian
soccer. This module is intentionally thin: each tool validates/forwards
arguments to a `queries` function and returns its JSON-serialisable dict. All
real logic and matching lives in `queries`/`data_loader`/`normalize`, which
are unit-tested without the protocol in the way.

The `KnowledgeBase` is loaded once at import via the process-cached
`get_knowledge_base()` so the first tool call is already warm and every
subsequent call is a pure in-memory pandas operation - comfortably inside the
spec's <2s simple / <5s aggregate latency budget.

Run it:

    python -m brazilian_soccer_mcp.server        # stdio transport (default)

or via the console script `brazilian-soccer-mcp` (see pyproject.toml). Point
the data directory elsewhere with the BR_SOCCER_DATA_DIR env var.

Tool surface (one per spec capability area):
  match queries     : find_matches
  team queries      : team_record, compare_teams (head-to-head)
  player queries    : find_players, players_by_club
  competition       : league_standings, list_competitions
  statistics        : competition_statistics, biggest_wins, best_team_record
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import queries
from .data_loader import get_knowledge_base

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge graph of Brazilian soccer: ~16.8k matches across "
        "Brasileirão Série A/B/C, Copa do Brasil and Copa Libertadores, plus "
        "the FIFA player database. Use these tools to answer questions about "
        "matches, teams, players, competition standings and statistics. Team "
        "names are normalised, so 'Flamengo', 'Flamengo-RJ' and 'Flamengo RJ' "
        "all resolve to the same club. Competition names accept 'Brasileirão', "
        "'Série A/B/C', 'Copa do Brasil', 'Libertadores'."
    ),
)


def _kb():
    """Return the cached KnowledgeBase (loaded on first use)."""
    return get_knowledge_base()


@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "either",
    limit: int = 50,
) -> dict[str, Any]:
    """Find matches by team, opponent, competition, season, and venue.

    Args:
        team: Team name (any spelling). Matches where this team played.
        opponent: Restrict to matches against this second team.
        competition: 'Brasileirão'/'Série A', 'Série B', 'Série C',
            'Copa do Brasil', or 'Libertadores'. Omit for all competitions.
        season: Four-digit year (e.g. 2019). Omit for all seasons.
        venue: 'home', 'away', or 'either' (relative to `team`).
        limit: Max matches returned (most recent first). Total count is always
            reported even when truncated.
    """
    return queries.find_matches(
        _kb(), team, opponent, competition, season, venue, limit
    )


@mcp.tool()
def team_record(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "either",
) -> dict[str, Any]:
    """Win/draw/loss record, goals and points for a team.

    Args:
        team: Team name (any spelling).
        competition: Optional competition filter.
        season: Optional year filter.
        venue: 'home', 'away', or 'either'.
    """
    return queries.team_record(_kb(), team, competition, season, venue)


@mcp.tool()
def compare_teams(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Head-to-head record and match list between two teams.

    Args:
        team_a: First team.
        team_b: Second team.
        competition: Optional competition filter.
        season: Optional year filter.
    """
    return queries.head_to_head(_kb(), team_a, team_b, competition, season)


@mcp.tool()
def find_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search FIFA players by name, nationality, club, position or rating.

    Results are sorted by Overall rating descending. All filters combine (AND).

    Args:
        name: Substring of the player's name (e.g. 'Neymar').
        nationality: Country (e.g. 'Brazil').
        club: Club name substring.
        position: Exact position code (e.g. 'ST', 'GK', 'CB').
        min_overall: Minimum FIFA Overall rating.
        limit: Max players returned (total count is always reported).
    """
    return queries.find_players(
        _kb(), name, nationality, club, position, min_overall, limit
    )


@mcp.tool()
def players_by_club(
    nationality: str | None = "Brazil", top_n: int = 10
) -> dict[str, Any]:
    """Group players by club: player count and average rating per club.

    Args:
        nationality: Restrict to one nationality (default 'Brazil'); pass an
            empty string for all players.
        top_n: Number of clubs to return (ordered by player count).
    """
    return queries.players_by_club_summary(_kb(), nationality or None, top_n)


@mcp.tool()
def league_standings(
    competition: str, season: int, top_n: int | None = None
) -> dict[str, Any]:
    """Compute a final league table for a competition+season from results.

    Points = 3*win + draw; tie-break on goal difference then goals for. Best
    suited to round-robin leagues (Série A/B/C).

    Args:
        competition: 'Brasileirão'/'Série A', 'Série B', or 'Série C'.
        season: Four-digit year.
        top_n: Limit to the top N positions (omit for the full table).
    """
    return queries.standings(_kb(), competition, season, top_n)


@mcp.tool()
def competition_statistics(
    competition: str | None = None, season: int | None = None
) -> dict[str, Any]:
    """Aggregate stats: goals/match, home/away/draw win rates.

    Args:
        competition: Optional competition filter.
        season: Optional year filter.
    """
    return queries.competition_stats(_kb(), competition, season)


@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Largest goal-margin victories in the (optionally filtered) data.

    Args:
        competition: Optional competition filter.
        season: Optional year filter.
        limit: Number of matches to return.
    """
    return queries.biggest_wins(_kb(), competition, season, limit)


@mcp.tool()
def best_team_record(
    competition: str | None = None,
    season: int | None = None,
    venue: str = "either",
    metric: str = "win_rate",
    min_matches: int = 5,
    limit: int = 10,
) -> dict[str, Any]:
    """Rank teams by a record metric (best home/away record, most points, ...).

    Args:
        competition: Optional competition filter.
        season: Optional year filter.
        venue: 'home', 'away', or 'either' - use 'home'/'away' for
            "best home/away record" questions.
        metric: 'win_rate', 'points', 'wins', or 'goal_difference'.
        min_matches: Exclude teams with fewer matches (avoids small-sample noise).
        limit: Number of teams to return.
    """
    return queries.best_record(
        _kb(), competition, season, venue, metric, min_matches, limit
    )


@mcp.tool()
def list_competitions() -> dict[str, Any]:
    """List the competitions and seasons available in the knowledge base."""
    kb = _kb()
    return {
        "competitions": kb.competitions,
        "seasons": kb.seasons,
        "total_matches": int(len(kb.matches)),
        "total_players": int(len(kb.players)),
    }


def main() -> None:
    """Console-script / module entry point. Warms the KB, then serves stdio."""
    get_knowledge_base()  # fail fast on missing data before opening the channel
    mcp.run()


if __name__ == "__main__":
    main()
