"""FastMCP server exposing Brazilian soccer query tools.

Why: the specification asks for an MCP server that lets an LLM answer
natural-language questions about Brazilian soccer using the bundled
Kaggle datasets.

What: each tool wraps a function from `queries.py` and returns
JSON-serializable results (records plus a human-readable ``summary``
in the format suggested by the specification).

Run with:  python -m brazilian_soccer_mcp.server   (stdio transport)
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from . import queries
from .data import get_dataset

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Query interface over Brazilian soccer datasets: Brasileirão Série A/B/C, "
        "Copa do Brasil, Copa Libertadores matches and a FIFA player database. "
        "Team names are normalized across sources, so plain names like "
        "'Flamengo' or 'Palmeiras' work everywhere."
    ),
)


@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str | None = None,
    round: int | None = None,
    stage: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Find matches by team, opponent, competition, season, date range or stage.

    Examples: team="Flamengo", opponent="Fluminense" lists Fla-Flu derbies;
    competition="Copa do Brasil", stage="final" lists cup finals;
    team="Palmeiras", season=2023 lists Palmeiras' 2023 matches.
    `venue` may be "home" or "away"; `stage` accepts e.g. "final",
    "semifinals", "group stage".
    """
    return queries.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
        round=round,
        stage=stage,
        limit=limit,
    )


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Compare two teams: every match between them plus wins/draws balance.

    Example: team_a="Palmeiras", team_b="Santos".
    """
    return queries.head_to_head(team_a, team_b, competition=competition, limit=limit)


@mcp.tool()
def team_statistics(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> dict[str, Any]:
    """Win/draw/loss record, goals and win rate for a team.

    Example: team="Corinthians", season=2022, venue="home" gives
    Corinthians' 2022 home record.
    """
    return queries.team_statistics(team, season=season, competition=competition, venue=venue)


@mcp.tool()
def team_competitions(team: str) -> dict[str, Any]:
    """List every competition a team has played in, with match counts."""
    return queries.team_competitions(team)


@mcp.tool()
def standings(season: int, competition: str = "Brasileirão Série A") -> dict[str, Any]:
    """League table for a season, calculated from match results (3/1/0 points).

    Example: season=2019 returns the 2019 Brasileirão table with
    Flamengo as champion.
    """
    return queries.standings(season=season, competition=competition)


@mcp.tool()
def list_competitions() -> dict[str, Any]:
    """List all competitions in the dataset with match counts and seasons."""
    return queries.list_competitions()


@mcp.tool()
def list_teams(competition: str | None = None, season: int | None = None) -> dict[str, Any]:
    """List all team names, optionally filtered by competition/season."""
    return queries.list_teams(competition=competition, season=season)


@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Largest goal-margin victories in the dataset."""
    return queries.biggest_wins(competition=competition, season=season, limit=limit)


@mcp.tool()
def competition_overview(
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Aggregate statistics: average goals per match, home/draw/away win rates."""
    return queries.competition_overview(competition=competition, season=season)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search FIFA players by name, nationality, club, position or rating.

    `position` accepts a code ("ST", "CDM", "GK") or a group
    ("forward", "midfielder", "defender", "goalkeeper").
    Example: name="Neymar", or nationality="Brazil", position="forward".
    """
    return queries.search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
    )


@mcp.tool()
def top_players(
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Highest-rated players, e.g. top Brazilian players or a club's best."""
    return queries.top_players(
        nationality=nationality, club=club, position=position, limit=limit
    )


@mcp.tool()
def players_by_club(nationality: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Player count and average FIFA rating per club (e.g. Brazilians per club)."""
    return queries.players_by_club(nationality=nationality, limit=limit)


@mcp.tool()
def dataset_info() -> dict[str, Any]:
    """Row counts per source file and competition (data coverage check)."""
    return get_dataset().info()


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
