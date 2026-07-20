"""MCP server exposing the Brazilian soccer knowledge base.

Run over stdio (the MCP default)::

    python -m brazilian_soccer_mcp.server
    # or, after ``pip install .``:
    brazilian-soccer-mcp

Every tool returns human-readable text ready to be shown to a user.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import formatting, queries
from .data import BRASILEIRAO_A, get_kb

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge graph over Brazilian soccer data: Brasileirão Série A/B/C, "
        "Copa do Brasil, Copa Libertadores matches (2003-2023) plus a FIFA "
        "player database. Team names are normalized across datasets, so "
        "'Palmeiras-SP', 'Palmeiras' and 'palmeiras' all match the same team."
    ),
)


def _guard(fn, *args, **kwargs) -> str:
    """Run a query+format pair, converting lookup errors into friendly text."""
    try:
        return fn(*args, **kwargs)
    except (queries.TeamNotFoundError, ValueError) as exc:
        return str(exc)


@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    stage: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> str:
    """Find matches by team, opponent, competition, season, stage or dates.

    Filter by team (optionally against a specific ``opponent``), competition
    (e.g. "Brasileirão", "Copa do Brasil", "Libertadores"), season (e.g.
    2023), stage (e.g. "Final", "Round 8", "Group Stage") and/or an ISO date
    range.  Answers questions like "Show me all Flamengo vs Fluminense
    matches", "What matches did Palmeiras play in 2023?" or "Find all Copa
    Libertadores finals" (leave ``team`` empty for competition-wide searches).
    """
    return _guard(
        lambda: formatting.format_matches(
            queries.find_matches(
                team=team,
                opponent=opponent,
                competition=competition,
                season=season,
                stage=stage,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
            )
        )
    )


@mcp.tool()
def head_to_head(team_a: str, team_b: str, competition: str | None = None) -> str:
    """Compare two teams head-to-head: all meetings plus win/draw summary.

    Answers "Compare Palmeiras and Santos head-to-head".
    """
    return _guard(
        lambda: formatting.format_head_to_head(
            queries.head_to_head(team_a, team_b, competition=competition)
        )
    )


@mcp.tool()
def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> str:
    """Win/draw/loss record, goals and win rate for a team.

    ``venue`` may be "home", "away" or "all".  Answers "What is Corinthians'
    home record in 2022?" or "Which competitions has Palmeiras played in?"
    (leave ``competition`` empty to get a per-competition breakdown).
    """
    return _guard(
        lambda: formatting.format_team_stats(
            queries.team_stats(team, season=season, competition=competition, venue=venue)
        )
    )


@mcp.tool()
def league_standings(season: int, competition: str = BRASILEIRAO_A) -> str:
    """League table for a season, calculated from match results (3/1/0 pts).

    Marks the champion and the relegation zone.  Answers "Who won the 2019
    Brasileirão?" or "Which teams were relegated in 2020?".
    """
    return _guard(
        lambda: formatting.format_standings(
            queries.standings(season, competition=competition)
        )
    )


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    limit: int = 10,
) -> str:
    """Search the FIFA player database.

    ``position`` is an exact code (e.g. "ST", "CDM", "GK");
    ``position_group`` is one of "forward", "midfielder", "defender",
    "goalkeeper".  Answers "Who is Gabriel Barbosa?", "Find all Brazilian
    players", "Show me all forwards from Santos".
    """
    return _guard(
        lambda: formatting.format_players(
            queries.search_players(
                name=name,
                nationality=nationality,
                club=club,
                position=position,
                position_group=position_group,
                min_overall=min_overall,
                limit=limit,
            )
        )
    )


@mcp.tool()
def club_players(club: str, limit: int = 10) -> str:
    """Roster overview for a club: squad size, average rating, top players.

    Answers "Who are the highest-rated players at Grêmio?".
    """
    return _guard(
        lambda: formatting.format_club_summary(queries.club_summary(club, limit=limit))
    )


@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Largest victory margins in the dataset, optionally filtered.

    Answers "Show me the biggest wins in the dataset".
    """
    return _guard(
        lambda: formatting.format_biggest_wins(
            queries.biggest_wins(competition=competition, season=season, limit=limit)
        )
    )


@mcp.tool()
def competition_statistics(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Goals averages, home/draw/away win rates for a competition or season.

    Answers "What's the average goals per match in the Brasileirão?" or
    "Compare the 2018 and 2019 seasons" (call once per season).
    """
    return _guard(
        lambda: formatting.format_competition_stats(
            queries.competition_stats(competition=competition, season=season)
        )
    )


@mcp.tool()
def list_competitions() -> str:
    """List the competitions covered by the dataset with match counts."""
    return _guard(lambda: formatting.format_competitions(queries.list_competitions()))


@mcp.tool()
def list_teams(filter: str | None = None) -> str:
    """List all known team names; ``filter`` narrows by substring.

    Useful for resolving name variants before running other tools.
    """
    result = queries.list_teams(filter=filter)
    teams = result["teams"]
    shown = teams[:100]
    suffix = f"\n... ({len(teams) - 100} more)" if len(teams) > 100 else ""
    return f"{result['total']} team(s):\n" + "\n".join(f"- {t}" for t in shown) + suffix


@mcp.tool()
def dataset_summary() -> str:
    """Row counts per source CSV, deduplication totals and coverage."""
    return _guard(lambda: formatting.format_dataset_summary(queries.dataset_summary()))


def main() -> None:
    """Start the MCP server on stdio transport."""
    # Warm the cache so the first tool call is fast.
    get_kb()
    mcp.run()


if __name__ == "__main__":
    main()
