"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : brazilian_soccer.server
Purpose : FastMCP server that exposes the SoccerGraph query engine as MCP tools
          so an LLM client can answer natural-language questions about Brazilian
          soccer (matches, teams, players, competitions, statistics).

Tools (one per spec capability, plus formatted-text variants):
  search_matches          - filter matches by team/opponent/competition/season/date
  head_to_head            - W/D/L summary + match list between two teams
  team_record             - W/D/L and goals for a team (season/competition/venue)
  search_players          - players by name/nationality/club/position/rating
  standings               - league table for a competition+season
  average_goals           - goals/match and home/away/draw rates
  biggest_wins            - largest-margin matches
  best_records            - teams ranked by win rate (home/away/all)
  answer                  - human-readable text answers for the common questions

The graph is loaded lazily on first use (get_graph) and cached, so the process
starts instantly and the data cost is paid once. Run with:  python -m
brazilian_soccer.server  (stdio transport, the MCP default).
================================================================================
"""

from __future__ import annotations

from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from .graph import SoccerGraph
from .loader import load_graph

mcp = FastMCP("brazilian-soccer")

_GRAPH: Optional[SoccerGraph] = None


def get_graph() -> SoccerGraph:
    """Return the process-wide SoccerGraph, loading it on first call."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = load_graph()
    return _GRAPH


def set_graph(graph: SoccerGraph) -> None:
    """Inject a pre-built graph (used by tests to avoid reloading CSVs)."""
    global _GRAPH
    _GRAPH = graph


# -- Tools ------------------------------------------------------------------


@mcp.tool()
def search_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    venue: str = "all",
    limit: int = 20,
) -> dict:
    """Find matches by team, opponent, competition, season and/or date range.

    venue is "all", "home" or "away" (relative to *team*). Returns the most
    recent matches first.
    """
    g = get_graph()
    matches = g.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        start_date=start_date,
        end_date=end_date,
        home_only=venue == "home",
        away_only=venue == "away",
        limit=limit,
    )
    return {"count": len(matches), "matches": [g.match_to_dict(m) for m in matches]}


@mcp.tool()
def head_to_head(
    team_a: str, team_b: str, competition: Optional[str] = None
) -> dict:
    """Head-to-head record (wins/draws) and match list between two teams."""
    return get_graph().head_to_head(team_a, team_b, competition)


@mcp.tool()
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss and goals-for/against record for a team.

    venue is "all", "home" or "away".
    """
    return get_graph().team_record(team, season, competition, venue).as_dict()


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> dict:
    """Search FIFA players by name, nationality, club, position and/or rating."""
    g = get_graph()
    players = g.find_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
    )
    return {"count": len(players), "players": [g.player_to_dict(p) for p in players]}


@mcp.tool()
def standings(competition: str, season: int, limit: int = 20) -> dict:
    """League standings computed from match results for a competition+season."""
    table = get_graph().standings(competition, season)
    return {
        "competition": competition,
        "season": season,
        "table": [r.as_dict() for r in table[:limit]],
    }


@mcp.tool()
def average_goals(
    competition: Optional[str] = None, season: Optional[int] = None
) -> dict:
    """Average goals per match plus home/away/draw rates over a subset."""
    return get_graph().average_goals(competition, season)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """Matches with the largest goal margin in the (optional) subset."""
    g = get_graph()
    matches = g.biggest_wins(competition, season, limit)
    return {"count": len(matches), "matches": [g.match_to_dict(m) for m in matches]}


@mcp.tool()
def best_records(
    venue: str = "all",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 5,
    limit: int = 10,
) -> dict:
    """Teams ranked by win rate over the subset. venue: all|home|away."""
    table = get_graph().best_records(
        venue=venue,
        competition=competition,
        season=season,
        min_matches=min_matches,
        limit=limit,
    )
    return {"teams": [r.as_dict() for r in table]}


@mcp.tool()
def answer(question: str) -> str:
    """Best-effort natural-language answer for common question shapes.

    A lightweight router for clients that prefer text over structured tool
    calls. It is intentionally simple; the structured tools above are the
    primary interface.
    """
    return answer_question(get_graph(), question)


# -- Plain-text formatting (also exercised by tests) -------------------------


def _fmt_match(m_dict: dict) -> str:
    d = m_dict["date"] or "????-??-??"
    score = (
        f"{m_dict['home_goal']}-{m_dict['away_goal']}"
        if m_dict["home_goal"] is not None and m_dict["away_goal"] is not None
        else "vs"
    )
    tail = m_dict["competition"]
    if m_dict.get("round"):
        tail += f" Round {m_dict['round']}"
    elif m_dict.get("stage"):
        tail += f" {m_dict['stage']}"
    return f"- {d}: {m_dict['home_team']} {score} {m_dict['away_team']} ({tail})"


def answer_question(graph: SoccerGraph, question: str) -> str:
    """Route a free-text question to a formatted answer (keyword heuristics)."""
    q = question.lower()

    # Player lookup: "who is X" / "find ... players"
    if q.startswith("who is "):
        name = question[7:].strip().rstrip("?")
        players = graph.find_players(name=name, limit=5)
        if not players:
            return f"No player matching '{name}' found in the dataset."
        lines = [f"Players matching '{name}':"]
        for p in players:
            lines.append(
                f"- {p.name} — Overall: {p.overall}, Position: {p.position}, Club: {p.club}"
            )
        return "\n".join(lines)

    return (
        "I can answer with the structured tools: search_matches, head_to_head, "
        "team_record, search_players, standings, average_goals, biggest_wins, "
        "best_records."
    )


def main() -> None:
    """Entry point: start the MCP server over stdio."""
    get_graph()  # warm the cache before serving
    mcp.run()


if __name__ == "__main__":
    main()
