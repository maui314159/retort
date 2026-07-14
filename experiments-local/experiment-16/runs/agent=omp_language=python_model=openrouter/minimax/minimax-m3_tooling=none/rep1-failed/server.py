"""
server.py
=========

MCP (Model Context Protocol) server for the Brazilian Soccer dataset.

This server exposes the high-level query functions implemented in
:mod:`query_engine` as MCP tools.  Each tool accepts plain Python
types and returns a human-readable text response.  The server speaks
the MCP protocol over stdio and can be wired up to any MCP-compatible
client (e.g. Claude Desktop, an MCP inspector, or a custom client).

Tools
-----
* :func:`find_matches` — find matches by team, opponent, competition,
  season, date range, or venue.
* :func:`team_statistics` — per-team wins/draws/losses and goals.
* :func:`head_to_head` — every match between two teams plus a summary
  record.
* :func:`find_players` — search the FIFA player dataset.
* :func:`competition_standings` — calculated league standings.
* :func:`biggest_wins` — matches ordered by largest goal difference.
* :func:`goals_summary` — average goals per match and home/away/draw
  splits.
* :func:`top_scoring_teams` — teams ranked by total goals scored.
* :func:`relegated_teams` — the bottom four teams of a Brasileirão
  season.
* :func:`team_competition_history` — competitions a team has played
  in.
* :func:`brazilian_club_summary` — counts of Brazilian players at
  Brazilian clubs in the FIFA dataset.
* :func:`raw_query` — escape hatch that lets an MCP client invoke any
  of the above tools by name and receive the structured response as
  JSON.

Run with::

    python server.py
"""

from __future__ import annotations

import json
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

import query_engine

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Tools for answering natural-language questions about Brazilian "
        "soccer. Use `find_matches` and `head_to_head` for individual "
        "games, `team_statistics` and `competition_standings` for "
        "aggregates, and `find_players` for FIFA player lookups."
    ),
)


# ---------------------------------------------------------------------------
# Renderers (raw data -> human-readable text)
# ---------------------------------------------------------------------------

def _render_match_line(match: dict[str, Any]) -> str:
    """Render a single match as a one-line summary."""
    home = match.get("home_team", "?")
    away = match.get("away_team", "?")
    hg = match.get("home_goal")
    ag = match.get("away_goal")
    score = (
        f"{hg}-{ag}" if hg is not None and ag is not None else "vs"
    )
    detail_bits: list[str] = []
    competition = match.get("competition")
    if competition:
        detail_bits.append(str(competition))
    if match.get("round"):
        detail_bits.append(f"Round {match['round']}")
    if match.get("stage"):
        detail_bits.append(str(match["stage"]))
    detail = " ".join(detail_bits)
    date = match.get("date", "unknown")
    return f"- {date}: {home} {score} {away} ({detail})".rstrip()


def _render_matches(result: dict[str, Any]) -> str:
    """Render a search_matches result as human-readable text."""
    matches = result.get("matches", [])
    if not matches:
        return result.get("message", "No matches found.")
    total = result.get("count", len(matches))
    shown = len(matches)
    if total > shown:
        header = f"Showing {shown} of {total} matches:"
    else:
        header = f"Found {total} match{'es' if total != 1 else ''}:"
    return "\n".join([header, *[_render_match_line(m) for m in matches]])


def _render_team_stats(result: dict[str, Any]) -> str:
    """Render a get_team_stats result as human-readable text."""
    if "error" in result:
        return result["error"]
    parts: list[str] = []
    title_bits = [result.get("team", "")]
    if result.get("competition"):
        title_bits.append(str(result["competition"]))
    if result.get("season"):
        title_bits.append(f"Season {result['season']}")
    if result.get("venue") and result["venue"] != "all":
        title_bits.append(f"({result['venue']} only)")
    parts.append(" ".join(b for b in title_bits if b) + ":")
    parts.append(f"- Matches: {result.get('matches', 0)}")
    parts.append(
        f"- Wins: {result.get('wins', 0)}, Draws: {result.get('draws', 0)}, "
        f"Losses: {result.get('losses', 0)}"
    )
    parts.append(
        f"- Goals For: {result.get('goals_for', 0)}, "
        f"Goals Against: {result.get('goals_against', 0)}"
    )
    parts.append(f"- Goal Difference: {result.get('goal_difference', 0)}")
    parts.append(f"- Win rate: {result.get('win_rate', 0.0)}%")
    return "\n".join(parts)


def _render_head_to_head(result: dict[str, Any]) -> str:
    """Render a get_head_to_head result as human-readable text."""
    if "error" in result:
        return result["error"]
    matches = result.get("matches", [])
    summary = result.get("summary", {})
    parts: list[str] = []
    title = f"{result.get('team1', '?')} vs {result.get('team2', '?')}"
    if result.get("season"):
        title += f" (Season {result['season']})"
    if result.get("competition"):
        title += f" [{result['competition']}]"
    parts.append(title)
    if matches:
        parts.append("")
        parts.extend(_render_match_line(m) for m in matches)
    parts.append("")
    parts.append("Head-to-head summary:")
    for k, v in summary.items():
        label = k.replace("_", " ").capitalize()
        parts.append(f"- {label}: {v}")
    return "\n".join(parts)


def _render_players(result: dict[str, Any]) -> str:
    """Render a search_players result as human-readable text."""
    players = result.get("players", [])
    if not players:
        return "No players matched."
    total = result.get("count", len(players))
    shown = len(players)
    if total > shown:
        header = f"Showing {shown} of {total} matching players:"
    else:
        header = f"Found {total} matching player{'s' if total != 1 else ''}:"
    lines = [header]
    for idx, p in enumerate(players, start=1):
        bits = [
            f"{idx}. {p.get('name', '?')}",
            f"Overall: {p.get('overall', '?')}",
            f"Position: {p.get('position', '?')}",
        ]
        if p.get("age"):
            bits.append(f"Age: {p['age']}")
        if p.get("nationality"):
            bits.append(f"Nationality: {p['nationality']}")
        if p.get("club"):
            bits.append(f"Club: {p['club']}")
        lines.append(" - " + ", ".join(str(b) for b in bits))
    return "\n".join(lines)


def _render_standings(result: dict[str, Any]) -> str:
    """Render a get_standings result as human-readable text."""
    standings = result.get("standings", [])
    if not standings:
        return result.get("message", "No standings available.")
    parts: list[str] = []
    title = (
        f"{result.get('competition', '?')} {result.get('season', '?')} "
        "Final Standings"
    )
    parts.append(title)
    parts.append("")
    for row in standings:
        line = (
            f"{row.get('position', '?'):>2}. {row.get('team', '?')} "
            f"- {row.get('points', 0)} pts "
            f"({row.get('wins', 0)}W {row.get('draws', 0)}D "
            f"{row.get('losses', 0)}L, "
            f"GD {row.get('goal_difference', 0):+d})"
        )
        parts.append(line)
    return "\n".join(parts)


def _render_biggest_wins(result: dict[str, Any]) -> str:
    """Render a get_biggest_wins result as human-readable text."""
    matches = result.get("matches", [])
    if not matches:
        return "No matches found."
    parts = [f"Top {len(matches)} biggest wins (by goal difference):"]
    parts.extend(_render_match_line(m) for m in matches)
    return "\n".join(parts)


def _render_goals_summary(result: dict[str, Any]) -> str:
    """Render a get_goals_per_match result as human-readable text."""
    if result.get("total_matches", 0) == 0:
        return "No matches found."
    return "\n".join(
        [
            f"- Average goals per match: {result.get('average_goals_per_match', 0)}",
            f"- Total matches: {result.get('total_matches', 0)}",
            f"- Total goals: {result.get('total_goals', 0)}",
            f"- Home wins: {result.get('home_wins', 0)} ({result.get('home_win_pct', 0)}%)",
            f"- Draws: {result.get('draws', 0)} ({result.get('draw_pct', 0)}%)",
            f"- Away wins: {result.get('away_wins', 0)} ({result.get('away_win_pct', 0)}%)",
        ]
    )


def _render_top_scoring(result: dict[str, Any]) -> str:
    """Render a get_top_scoring_teams result as human-readable text."""
    teams = result.get("teams", [])
    if not teams:
        return "No teams found."
    parts = ["Top scoring teams:"]
    for idx, t in enumerate(teams, start=1):
        parts.append(f"  {idx}. {t.get('team', '?')}: {t.get('goals', 0)} goals")
    return "\n".join(parts)


def _render_relegated(result: dict[str, Any]) -> str:
    """Render a get_relegated_teams result as human-readable text."""
    if not result.get("relegated"):
        return result.get("message", "No data available.")
    parts = [f"Relegated teams ({result.get('competition', 'Brasileirão')} {result.get('season', '?')}):"]
    for t in result["relegated"]:
        parts.append(
            f"  {t.get('position', '?')}. {t.get('team', '?')} "
            f"({t.get('points', 0)} pts)"
        )
    return "\n".join(parts)


def _render_team_history(result: dict[str, Any]) -> str:
    """Render a get_team_competition_history result as human-readable text."""
    if "error" in result:
        return result["error"]
    parts = [f"Competition history for {result.get('team', '?')}:"]
    for c in result.get("competitions", []):
        parts.append(f"  - {c.get('competition', '?')}: {c.get('seasons', 0)} seasons")
    return "\n".join(parts)


def _render_brazilian_club_summary(result: dict[str, Any]) -> str:
    """Render a brazilian_club_summary result as human-readable text."""
    clubs = result.get("clubs", [])
    if not clubs:
        return "No Brazilian clubs found in the FIFA dataset."
    parts = ["Brazilian clubs in the FIFA dataset:"]
    for c in clubs:
        parts.append(
            f"  - {c.get('club', '?')}: {c.get('player_count', 0)} players, "
            f"avg rating {c.get('average_overall', 0)}"
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str | None = None,
    limit: int = 50,
) -> str:
    """
    Find matches matching the supplied criteria.

    Args:
        team: Team name (state suffixes and accents are normalized).
        opponent: Optional second team for head-to-head filtering.
        competition: Competition name or alias (e.g. ``Brasileirão``).
        season: Season year (e.g. ``2023``).
        date_from: ISO lower bound on the match date.
        date_to: ISO upper bound on the match date.
        venue: ``"home"``, ``"away"``, or omitted for both.
        limit: Maximum number of matches to return (default 50).
    """
    result = query_engine.search_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
        limit=limit,
    )
    return _render_matches(result)


@mcp.tool()
def team_statistics(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> str:
    """
    Return aggregate statistics for a single team.

    Args:
        team: Team name.
        competition: Optional competition filter.
        season: Optional season filter.
        venue: ``"home"``, ``"away"``, or omitted for both.
    """
    result = query_engine.get_team_stats(
        team=team, competition=competition, season=season, venue=venue
    )
    return _render_team_stats(result)


@mcp.tool()
def head_to_head(
    team1: str,
    team2: str,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """
    Return every match between two teams plus a summary record.

    Args:
        team1: First team name.
        team2: Second team name.
        competition: Optional competition filter.
        season: Optional season filter.
    """
    result = query_engine.get_head_to_head(
        team1=team1, team2=team2, competition=competition, season=season
    )
    return _render_head_to_head(result)


@mcp.tool()
def find_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_age: int | None = None,
    limit: int = 25,
) -> str:
    """
    Search the FIFA player dataset.

    Args:
        name: Player name substring.
        nationality: Nationality substring.
        club: Club name substring.
        position: Position substring (e.g. ``"GK"``).
        min_overall: Minimum overall rating.
        max_age: Maximum age.
        limit: Maximum number of results to return.
    """
    result = query_engine.search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        max_age=max_age,
        limit=limit,
    )
    return _render_players(result)


@mcp.tool()
def competition_standings(competition: str, season: int) -> str:
    """
    Compute league standings for a competition and season from match data.

    Args:
        competition: Competition name (e.g. ``"Brasileirão"``).
        season: Season year.
    """
    result = query_engine.get_standings(competition, season)
    return _render_standings(result)


@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """
    Return the matches with the largest goal difference.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        limit: Maximum number of results.
    """
    result = query_engine.get_biggest_wins(
        competition=competition, season=season, limit=limit
    )
    return _render_biggest_wins(result)


@mcp.tool()
def goals_summary(
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """
    Return average goals per match and home/away/draw splits.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
    """
    result = query_engine.get_goals_per_match(
        competition=competition, season=season
    )
    return _render_goals_summary(result)


@mcp.tool()
def top_scoring_teams(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """
    Return teams ranked by total goals scored.

    Args:
        competition: Optional competition filter.
        season: Optional season filter.
        limit: Maximum number of results.
    """
    result = query_engine.get_top_scoring_teams(
        competition=competition, season=season, limit=limit
    )
    return _render_top_scoring(result)


@mcp.tool()
def relegated_teams(season: int, bottom: int = 4) -> str:
    """
    Return the bottom ``bottom`` teams of a Brasileirão season.

    Args:
        season: Season year.
        bottom: Number of relegated teams to return (default 4).
    """
    result = query_engine.get_relegated_teams(season=season, bottom=bottom)
    return _render_relegated(result)


@mcp.tool()
def team_competition_history(team: str) -> str:
    """
    Return the competitions and season counts a team has played in.

    Args:
        team: Team name.
    """
    result = query_engine.get_team_competition_history(team)
    return _render_team_history(result)


@mcp.tool()
def brazilian_club_summary() -> str:
    """Return counts and average overall rating for Brazilian clubs in the FIFA dataset."""
    result = query_engine.brazilian_club_summary()
    return _render_brazilian_club_summary(result)


@mcp.tool()
def raw_query(tool: str, params: dict[str, Any] | None = None) -> str:
    """
    Invoke any query tool by name and receive the structured response as JSON.

    Args:
        tool: The query function name (``find_matches``, ``team_statistics``,
            ``head_to_head``, ``find_players``, ``competition_standings``,
            ``biggest_wins``, ``goals_summary``, ``top_scoring_teams``,
            ``relegated_teams``, ``team_competition_history``,
            ``brazilian_club_summary``).
        params: Optional dict of keyword arguments to pass to the tool.
    """
    callables: dict[str, Callable[..., dict[str, Any]]] = {
        "find_matches": query_engine.search_matches,
        "team_statistics": query_engine.get_team_stats,
        "head_to_head": query_engine.get_head_to_head,
        "find_players": query_engine.search_players,
        "competition_standings": query_engine.get_standings,
        "biggest_wins": query_engine.get_biggest_wins,
        "goals_summary": query_engine.get_goals_per_match,
        "top_scoring_teams": query_engine.get_top_scoring_teams,
        "relegated_teams": query_engine.get_relegated_teams,
        "team_competition_history": query_engine.get_team_competition_history,
        "brazilian_club_summary": query_engine.brazilian_club_summary,
    }
    if tool not in callables:
        return json.dumps(
            {"error": f"Unknown tool: {tool}", "available": list(callables.keys())}
        )
    return json.dumps(callables[tool](**(params or {})), default=str)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the MCP server on stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
