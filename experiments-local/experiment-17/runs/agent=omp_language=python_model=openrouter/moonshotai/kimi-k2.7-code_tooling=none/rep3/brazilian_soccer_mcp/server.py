"""
Brazilian Soccer MCP Server.

This module exposes a Model Context Protocol (MCP) server built with
FastMCP.  It provides tools for querying Brazilian football matches,
teams, players, competitions and statistics across the six Kaggle
datasets included in the repository.

The server communicates over stdio by default, making it suitable for
use as a local MCP tool with any MCP-compatible client.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

from brazilian_soccer_mcp.data_store import DataStore, get_data_store
from brazilian_soccer_mcp import queries


# ---------------------------------------------------------------------------
# Server initialization
# ---------------------------------------------------------------------------
mcp = FastMCP("brazilian_soccer_mcp")


# ---------------------------------------------------------------------------
# Shared enums and base models
# ---------------------------------------------------------------------------
class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class Venue(str, Enum):
    """Venue filter for team statistics."""

    ALL = "all"
    HOME = "home"
    AWAY = "away"


class _BaseInput(BaseModel):
    """Common input fields shared by many tools."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable text or 'json' for structured data",
    )


# ---------------------------------------------------------------------------
# Tool input models
# ---------------------------------------------------------------------------
class FindMatchesInput(_BaseInput):
    """Input model for finding matches by flexible filters."""

    team: Optional[str] = Field(
        default=None,
        description="Team name (home, away or either).  Name variations are normalized automatically.",
    )
    opponent: Optional[str] = Field(
        default=None,
        description="Opponent team name.  Both team and opponent must appear in the match.",
    )
    date_from: Optional[str] = Field(
        default=None,
        description="Start date (YYYY-MM-DD).  Inclusive.",
    )
    date_to: Optional[str] = Field(
        default=None,
        description="End date (YYYY-MM-DD).  Inclusive.",
    )
    competition: Optional[str] = Field(
        default=None,
        description="Competition name, e.g. 'Brasileirao', 'Copa do Brasil', 'Copa Libertadores'",
    )
    season: Optional[int] = Field(
        default=None,
        description="Season year, e.g. 2023",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of matches to return",
    )


class HeadToHeadInput(_BaseInput):
    """Input model for head-to-head comparisons."""

    team_a: str = Field(
        ...,
        min_length=1,
        description="First team name",
    )
    team_b: str = Field(
        ...,
        min_length=1,
        description="Second team name",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum matches to return",
    )


class TeamStatsInput(_BaseInput):
    """Input model for team statistics."""

    team: str = Field(
        ...,
        min_length=1,
        description="Team name (variations normalized automatically)",
    )
    season: Optional[int] = Field(
        default=None,
        description="Season year filter",
    )
    competition: Optional[str] = Field(
        default=None,
        description="Competition filter",
    )
    venue: Venue = Field(
        default=Venue.ALL,
        description="Filter by venue: 'all', 'home' or 'away'",
    )

    @field_validator("venue", mode="before")
    @classmethod
    def _coerce_venue(cls, value: Any) -> str:
        if value is None:
            return "all"
        return str(value).lower()


class SearchPlayersInput(_BaseInput):
    """Input model for player search."""

    name: Optional[str] = Field(
        default=None,
        description="Player name substring",
    )
    nationality: Optional[str] = Field(
        default=None,
        description="Nationality, e.g. 'Brazil'",
    )
    club: Optional[str] = Field(
        default=None,
        description="Club name (variations normalized automatically)",
    )
    position: Optional[str] = Field(
        default=None,
        description="Playing position substring, e.g. 'ST', 'LW', 'GK'",
    )
    min_overall: Optional[int] = Field(
        default=None,
        ge=1,
        le=99,
        description="Minimum FIFA overall rating",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum players to return",
    )


class TopBrazilianPlayersInput(_BaseInput):
    """Input model for top Brazilian players."""

    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of players to return",
    )
    at_brazilian_club: bool = Field(
        default=False,
        description="Only include players currently at a Brazilian club",
    )


class SeasonInput(_BaseInput):
    """Input model for queries that require a season."""

    season: int = Field(
        ...,
        description="Season year",
    )
    competition: Optional[str] = Field(
        default=None,
        description="Competition filter",
    )


class BiggestWinsInput(_BaseInput):
    """Input model for biggest wins query."""

    competition: Optional[str] = Field(
        default=None,
        description="Competition filter",
    )
    season: Optional[int] = Field(
        default=None,
        description="Season filter",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of results",
    )


class TopScorersInput(_BaseInput):
    """Input model for top-scoring teams query."""

    season: Optional[int] = Field(
        default=None,
        description="Season filter",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of teams to return",
    )


class CompareSeasonsInput(_BaseInput):
    """Input model for comparing two seasons."""

    season_a: int = Field(
        ...,
        description="First season year",
    )
    season_b: int = Field(
        ...,
        description="Second season year",
    )
    competition: Optional[str] = Field(
        default=None,
        description="Competition filter",
    )


class AverageGoalsInput(_BaseInput):
    """Input model for average goals query."""

    competition: Optional[str] = Field(
        default=None,
        description="Competition filter",
    )
    season: Optional[int] = Field(
        default=None,
        description="Season filter",
    )


# ---------------------------------------------------------------------------
# Helper to format results consistently
# ---------------------------------------------------------------------------
def _format_result(data: Any, response_format: ResponseFormat) -> str:
    """Serialize a result to either markdown or JSON."""
    if response_format == ResponseFormat.JSON:
        import json
        return json.dumps(data, indent=2, default=str)
    if isinstance(data, str):
        return data
    return str(data)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
@mcp.tool(
    name="brazilian_soccer_find_matches",
    annotations={
        "title": "Find Matches",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_find_matches(params: FindMatchesInput) -> str:
    """Search for matches across all Brazilian soccer datasets.

    Filters can be combined: team, opponent, date range, competition and
    season.  Team names are normalized, so "Palmeiras" and "Palmeiras-SP"
    match the same records.

    Args:
        params (FindMatchesInput): Search filters and output format.

    Returns:
        str: Markdown list of matches or JSON with the full records.
    """
    result = queries.find_matches(
        team=params.team,
        opponent=params.opponent,
        date_from=params.date_from,
        date_to=params.date_to,
        competition=params.competition,
        season=params.season,
        limit=params.limit,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_head_to_head",
    annotations={
        "title": "Head-to-Head",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_head_to_head(params: HeadToHeadInput) -> str:
    """Return the historical head-to-head record between two teams.

    Args:
        params (HeadToHeadInput): Two team names and output format.

    Returns:
        str: Match history with win/draw/loss counts.
    """
    result = queries.get_head_to_head(
        team_a=params.team_a,
        team_b=params.team_b,
        limit=params.limit,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_team_stats",
    annotations={
        "title": "Team Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_team_stats(params: TeamStatsInput) -> str:
    """Get wins, draws, losses, goals and win rate for a team.

    Args:
        params (TeamStatsInput): Team name with optional season, competition
            and venue filters.

    Returns:
        str: Summary statistics in markdown or JSON.
    """
    venue_value = params.venue.value if params.venue != Venue.ALL else None
    result = queries.get_team_stats(
        team=params.team,
        season=params.season,
        competition=params.competition,
        venue=venue_value,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_list_teams",
    annotations={
        "title": "List Teams",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_list_teams(params: _BaseInput) -> str:
    """List all teams present in the match datasets.

    Args:
        params (_BaseInput): Output format.

    Returns:
        str: Sorted list of canonical team names.
    """
    result = queries.list_teams(response_format=params.response_format.value)
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_search_players",
    annotations={
        "title": "Search Players",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_search_players(params: SearchPlayersInput) -> str:
    """Search the FIFA player dataset by name, nationality, club, position or rating.

    Args:
        params (SearchPlayersInput): Player search filters.

    Returns:
        str: Matching players sorted by overall rating.
    """
    result = queries.search_players(
        name=params.name,
        nationality=params.nationality,
        club=params.club,
        position=params.position,
        min_overall=params.min_overall,
        limit=params.limit,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_top_brazilian_players",
    annotations={
        "title": "Top Brazilian Players",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_top_brazilian_players(
    params: TopBrazilianPlayersInput,
) -> str:
    """Return the highest-rated Brazilian players in the FIFA dataset.

    Args:
        params (TopBrazilianPlayersInput): Limit and whether to restrict to
            Brazilian clubs.

    Returns:
        str: Top Brazilian players sorted by overall rating.
    """
    result = queries.top_brazilian_players(
        limit=params.limit,
        at_brazilian_club=params.at_brazilian_club,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_standings",
    annotations={
        "title": "League Standings",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_standings(params: SeasonInput) -> str:
    """Calculate league-style standings for a season.

    Standings are computed from match results using 3 points for a win and
    1 point for a draw.

    Args:
        params (SeasonInput): Season and optional competition filter.

    Returns:
        str: Standings table in markdown or JSON.
    """
    result = queries.get_standings(
        season=params.season,
        competition=params.competition,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_competition_winner",
    annotations={
        "title": "Competition Winner",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_competition_winner(params: SeasonInput) -> str:
    """Return the team with the most points in a season/competition.

    For knockout competitions this reports the leader by match points, which
    is most meaningful for league-format seasons.

    Args:
        params (SeasonInput): Season and optional competition filter.

    Returns:
        str: Winner summary.
    """
    result = queries.get_competition_winners(
        season=params.season,
        competition=params.competition,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_biggest_wins",
    annotations={
        "title": "Biggest Wins",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_biggest_wins(params: BiggestWinsInput) -> str:
    """Return the biggest victories by goal margin.

    Args:
        params (BiggestWinsInput): Optional competition/season filters and
            result limit.

    Returns:
        str: Largest-margin matches.
    """
    result = queries.get_biggest_wins(
        competition=params.competition,
        season=params.season,
        limit=params.limit,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_average_goals",
    annotations={
        "title": "Average Goals",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_average_goals(params: AverageGoalsInput) -> str:
    """Return average goals per match and home win rate.

    Args:
        params (AverageGoalsInput): Optional competition/season filters.

    Returns:
        str: Aggregate goal statistics.
    """
    result = queries.get_average_goals(
        competition=params.competition,
        season=params.season,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_top_scorers",
    annotations={
        "title": "Top Scoring Teams",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_top_scorers(params: TopScorersInput) -> str:
    """Return the teams with the most goals scored.

    Individual player top scorers cannot be inferred from the match-level
    data, so this aggregates goals by team.

    Args:
        params (TopScorersInput): Optional season filter and limit.

    Returns:
        str: Highest-scoring teams.
    """
    result = queries.get_top_scorers(
        season=params.season,
        limit=params.limit,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


@mcp.tool(
    name="brazilian_soccer_compare_seasons",
    annotations={
        "title": "Compare Seasons",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def brazilian_soccer_compare_seasons(params: CompareSeasonsInput) -> str:
    """Compare aggregate match statistics between two seasons.

    Args:
        params (CompareSeasonsInput): Two season years and optional
            competition filter.

    Returns:
        str: Side-by-side season statistics.
    """
    result = queries.compare_seasons(
        season_a=params.season_a,
        season_b=params.season_b,
        competition=params.competition,
        response_format=params.response_format.value,
    )
    return _format_result(result, params.response_format)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the Brazilian Soccer MCP server over stdio."""
    # Warm up the data store so that the first tool call is fast.
    get_data_store()
    mcp.run()


if __name__ == "__main__":
    main()
