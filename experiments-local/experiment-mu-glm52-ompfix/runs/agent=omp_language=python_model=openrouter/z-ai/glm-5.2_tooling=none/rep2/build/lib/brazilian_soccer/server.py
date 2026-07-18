# brazilian_soccer.server
# -----------------------------------------------------------------------------
# MCP server entrypoint. Registers one tool per query category required by
# TASK.md so an LLM client can answer natural-language questions about
# Brazilian soccer by calling these tools.
#
# Tools exposed (every requirement from FEEDBACK.md is covered):
#   find_matches          R3/R4/R5  matches by team, date range, season, competition
#   head_to_head          R11       head-to-head W/L/D between two teams
#   team_statistics       R6        team W/L/D record + goals for/against
#   team_competitions               per-competition breakdown for a team
#   search_players        R7/R8     players by name / nationality / club / ratings
#   top_players_at_club             convenience wrapper around search_players
#   competition_standings R9        standings calculated from match results
#   competition_champion            season champion from standings
#   relegated_teams                 bottom-n teams from standings
#   average_goals         R10       aggregate goal + home/away/draw rates
#   biggest_wins          R10       largest goal-difference victories
#   best_team_record      R10       ranking by win_rate / points / goals_for
#   derbies                         canonical Brazilian derby matches
#   data_summary                    inventory of loaded datasets
#
# The server also exposes a read-only resource (data://summary) for quick
# discovery of what data is available.
# -----------------------------------------------------------------------------
from __future__ import annotations

from fastmcp import FastMCP

from .loader import get_data_summary
from .queries import (
    average_goals,
    best_team_record,
    biggest_wins,
    competition_champion,
    competition_standings,
    data_summary,
    derbies,
    find_matches,
    head_to_head,
    relegated_teams,
    search_players,
    team_competitions,
    team_statistics,
    top_players_at_club,
)

mcp = FastMCP(
    "brazilian-soccer-mcp",
    instructions=(
        "Brazilian Soccer MCP server. Query match, team, player, and "
        "competition data from bundled Kaggle datasets (Brasileirão, "
        "Copa do Brasil, Copa Libertadores, FIFA players). Use the tools "
        "to answer natural-language questions about Brazilian soccer."
    ),
)


# ---------------------------------------------------------------------------
# Match queries (R3, R4, R5)
# ---------------------------------------------------------------------------

@mcp.tool
def tool_find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    stage: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Find matches matching the given criteria (all filters optional, AND-combined).

    - team: match team name (home or away); accepts name variants like
      "Palmeiras-SP" or "palmeiras".
    - opponent: the other team (use with team for head-to-head match lists).
    - competition: one of "Brasileirão Série A", "Brasileirão Série B",
      "Brasileirão Série C", "Copa do Brasil", "Copa Libertadores".
    - season: year, e.g. 2023.
    - start_date / end_date: ISO dates (YYYY-MM-DD), inclusive.
    - stage: Libertadores stage (e.g. "group stage", "final").
    - limit: max results (default 50).
    """
    return find_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        start_date=start_date, end_date=end_date, stage=stage, limit=limit,
    )


@mcp.tool
def tool_head_to_head(team_a: str, team_b: str, limit: int = 50) -> dict:
    """Return head-to-head matches and aggregated W/L/D record between two teams.

    Also returns the derby name if the pair is a recognized Brazilian rivalry.
    """
    return head_to_head(team_a, team_b, limit=limit)


# ---------------------------------------------------------------------------
# Team queries (R6)
# ---------------------------------------------------------------------------

@mcp.tool
def tool_team_statistics(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> dict:
    """Return a team's win/loss/draw record and goals for/against.

    - venue: "home", "away", or None (both).
    - competition / season: optional filters.
    """
    return team_statistics(
        team=team, competition=competition, season=season, venue=venue,
    )


@mcp.tool
def tool_team_competitions(team: str) -> list[dict]:
    """List every competition a team has appeared in, with per-competition record."""
    return team_competitions(team)


# ---------------------------------------------------------------------------
# Player queries (R7, R8)
# ---------------------------------------------------------------------------

@mcp.tool
def tool_search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    sort_by: str = "overall",
    limit: int = 20,
) -> list[dict]:
    """Search the FIFA player database with flexible filters.

    - name: substring search (accent-insensitive), e.g. "neymar".
    - nationality: exact country name, e.g. "Brazil".
    - club: substring search (accent-insensitive), e.g. "santos".
    - position: exact FIFA position code (ST, LW, GK, ...).
    - position_group: one of GK, DEF, MID, FWD.
    - min_overall / max_overall: rating range.
    - sort_by: column to sort by (default "overall").
    """
    return search_players(
        name=name, nationality=nationality, club=club, position=position,
        position_group=position_group, min_overall=min_overall,
        max_overall=max_overall, sort_by=sort_by, limit=limit,
    )


@mcp.tool
def tool_top_players_at_club(club: str, limit: int = 10) -> list[dict]:
    """Return the highest-rated players at a given club."""
    return top_players_at_club(club=club, limit=limit)


# ---------------------------------------------------------------------------
# Competition queries (R9)
# ---------------------------------------------------------------------------

@mcp.tool
def tool_competition_standings(
    competition: str, season: int, top: int | None = None,
) -> list[dict]:
    """Calculate a league-style standings table from match results.

    Three points for a win, one for a draw. Ties broken by goal difference,
    then goals for. Only league competitions produce a meaningful table.
    """
    return competition_standings(competition, season, top=top)


@mcp.tool
def tool_competition_champion(competition: str, season: int) -> dict | None:
    """Return the champion (top of standings) for a competition and season."""
    return competition_champion(competition, season)


@mcp.tool
def tool_relegated_teams(
    competition: str, season: int, n: int = 4,
) -> list[str] | None:
    """Return the bottom-n teams (default 4) from the standings."""
    return relegated_teams(competition, season, n=n)


# ---------------------------------------------------------------------------
# Statistical analysis (R10)
# ---------------------------------------------------------------------------

@mcp.tool
def tool_average_goals(
    competition: str | None = None, season: int | None = None,
) -> dict:
    """Compute average goals per match plus home/away/draw rates."""
    return average_goals(competition=competition, season=season)


@mcp.tool
def tool_biggest_wins(
    competition: str | None = None, season: int | None = None, limit: int = 10,
) -> list[dict]:
    """Return the matches with the largest goal difference."""
    return biggest_wins(competition=competition, season=season, limit=limit)


@mcp.tool
def tool_best_team_record(
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
    metric: str = "win_rate",
    top: int = 5,
) -> list[dict]:
    """Rank teams by win_rate, points, or goals_for over a filtered match set."""
    return best_team_record(
        competition=competition, season=season, venue=venue,
        metric=metric, top=top,
    )


@mcp.tool
def tool_derbies(
    season: int | None = None, competition: str | None = None,
) -> list[dict]:
    """Find canonical Brazilian derby matches in the dataset."""
    return derbies(season=season, competition=competition)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@mcp.tool
def tool_data_summary() -> dict:
    """Return an inventory of the loaded datasets (match/player counts)."""
    return data_summary()


@mcp.resource("data://summary")
def summary_resource() -> dict:
    """Quick inventory of what datasets are loaded and queryable."""
    return get_data_summary()


def main() -> None:
    """Entry point for the ``brazilian-soccer-mcp`` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
