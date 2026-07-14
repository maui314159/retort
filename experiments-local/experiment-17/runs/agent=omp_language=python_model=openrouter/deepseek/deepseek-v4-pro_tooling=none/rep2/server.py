#!/usr/bin/env python3
"""
Brazilian Soccer MCP Server — knowledge-graph interface for Brazilian soccer data.

Provides MCP tools enabling natural-language queries about:
  - Matches (by team, date, competition, season)
  - Teams (stats, head-to-head, performance)
  - Players (FIFA ratings, by nationality/club/position)
  - Competitions (standings, top scorers)
  - Statistical analysis (averages, trends, extremes)

Data: 6 Kaggle datasets bundled in data/kaggle/, all CC-licensed.
Server: FastMCP (Python) over stdio transport.

Usage:
    python server.py          # stdio transport (default)
    python server.py --http   # streamable HTTP on port 8000
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

from data_loader import load_all, clear_cache

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("brazilian_soccer_mcp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches_for_team(matches: List[Dict], team: str) -> List[Dict]:
    """Return matches where the given team played (home or away)."""
    t = team.lower()
    return [
        m for m in matches
        if (m["home_team"] and m["home_team"].lower() == t)
        or (m["away_team"] and m["away_team"].lower() == t)
    ]


def _team_stats(matches: List[Dict], team: str) -> Dict[str, Any]:
    """Compute W/D/L and goals for a team across a list of matches."""
    t = team.lower()
    wins = draws = losses = 0
    gf = ga = 0
    for m in matches:
        is_home = m["home_team"] and m["home_team"].lower() == t
        is_away = m["away_team"] and m["away_team"].lower() == t
        if not (is_home or is_away):
            continue
        hg = m["home_goal"]
        ag = m["away_goal"]
        if is_home:
            gf += hg
            ga += ag
            if hg > ag:
                wins += 1
            elif hg < ag:
                losses += 1
            else:
                draws += 1
        else:
            gf += ag
            ga += hg
            if ag > hg:
                wins += 1
            elif ag < hg:
                losses += 1
            else:
                draws += 1
    return {"matches": wins + draws + losses, "wins": wins, "draws": draws,
            "losses": losses, "goals_for": gf, "goals_against": ga}


def _head_to_head(matches: List[Dict], team_a: str, team_b: str) -> Dict[str, Any]:
    """Compute H2H record between two teams."""
    ta = team_a.lower()
    tb = team_b.lower()
    a_wins = a_losses = b_wins = b_losses = draws = 0
    a_gf = a_ga = 0
    h2h_matches: List[Dict] = []
    for m in matches:
        ht = (m["home_team"] or "").lower()
        at = (m["away_team"] or "").lower()
        if {ht, at} != {ta, tb}:
            continue
        h2h_matches.append(m)
        hg = m["home_goal"]
        ag = m["away_goal"]
        if ht == ta:
            a_gf += hg
            a_ga += ag
            if hg > ag:
                a_wins += 1
                b_losses += 1
            elif hg < ag:
                a_losses += 1
                b_wins += 1
            else:
                draws += 1
        else:
            a_gf += ag
            a_ga += hg
            if ag > hg:
                a_wins += 1
                b_losses += 1
            elif ag < hg:
                a_losses += 1
                b_wins += 1
            else:
                draws += 1
    return {
        "team_a": team_a, "team_b": team_b,
        "team_a_wins": a_wins, "team_b_wins": b_wins, "draws": draws,
        "team_a_goals": a_gf, "team_b_goals": a_ga,
        "total_matches": len(h2h_matches),
        "matches": sorted(h2h_matches, key=lambda m: m["date"] or datetime.min, reverse=True),
    }


def _fstr(v: Any) -> str:
    """Format a value for display, handling None."""
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def _date_str(d: Optional[datetime]) -> str:
    if d is None:
        return "?"
    return d.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class MatchSearchInput(BaseModel):
    """Search matches by team, competition, season, date range."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    team: Optional[str] = Field(
        default=None,
        description="Team name to search for (home or away). Case-insensitive, handles variations like 'Flamengo', 'Flamengo-RJ'.",
        min_length=1, max_length=100,
    )
    opponent: Optional[str] = Field(
        default=None,
        description="Opponent team name for head-to-head filtering.",
        min_length=1, max_length=100,
    )
    competition: Optional[str] = Field(
        default=None,
        description="Competition name: 'Brasileirão', 'Copa do Brasil', or 'Libertadores'.",
        min_length=1, max_length=50,
    )
    season: Optional[int] = Field(
        default=None,
        description="Season year (e.g. 2023).",
        ge=2000, le=2030,
    )
    date_from: Optional[str] = Field(
        default=None,
        description="Start date (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    date_to: Optional[str] = Field(
        default=None,
        description="End date (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    stage: Optional[str] = Field(
        default=None,
        description="Filter by stage (e.g. 'final', 'group stage', 'semi-final').",
        min_length=1, max_length=50,
    )
    limit: int = Field(default=50, description="Maximum results to return.", ge=1, le=200)
    response_format: str = Field(
        default="markdown",
        description="'markdown' for human-readable or 'json' for machine-readable.",
        pattern=r"^(markdown|json)$",
    )

    @field_validator("team", "opponent")
    @classmethod
    def _lower_strip(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().lower() if v else None


class TeamStatsInput(BaseModel):
    """Get aggregated statistics for a team."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    team: str = Field(..., description="Team name.", min_length=1, max_length=100)
    competition: Optional[str] = Field(
        default=None,
        description="Filter by competition: 'Brasileirão', 'Copa do Brasil', 'Libertadores'.",
    )
    season: Optional[int] = Field(default=None, description="Filter by season year.", ge=2000, le=2030)
    home_away: Optional[str] = Field(
        default=None,
        description="'home' for home-only, 'away' for away-only, omit for both.",
        pattern=r"^(home|away)$",
    )
    response_format: str = Field(default="markdown", description="'markdown' or 'json'.", pattern=r"^(markdown|json)$")

    @field_validator("team")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()


class HeadToHeadInput(BaseModel):
    """Compare two teams head-to-head."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    team_a: str = Field(..., description="First team name.", min_length=1, max_length=100)
    team_b: str = Field(..., description="Second team name.", min_length=1, max_length=100)
    competition: Optional[str] = Field(default=None, description="Filter by competition.")
    response_format: str = Field(default="markdown", description="'markdown' or 'json'.", pattern=r"^(markdown|json)$")

    @field_validator("team_a", "team_b")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()


class PlayerSearchInput(BaseModel):
    """Search FIFA player database."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: Optional[str] = Field(default=None, description="Player name (partial match).", min_length=1, max_length=100)
    nationality: Optional[str] = Field(default=None, description="Nationality (e.g. 'Brazil').", min_length=1, max_length=50)
    club: Optional[str] = Field(default=None, description="Club name (partial match).", min_length=1, max_length=100)
    position: Optional[str] = Field(default=None, description="Position (e.g. 'ST', 'LW', 'GK').", min_length=1, max_length=10)
    min_overall: Optional[int] = Field(default=None, description="Minimum overall rating.", ge=0, le=100)
    max_overall: Optional[int] = Field(default=None, description="Maximum overall rating.", ge=0, le=100)
    sort_by: str = Field(default="overall", description="Sort field: 'overall', 'potential', 'age', 'name'.", pattern=r"^(overall|potential|age|name)$")
    sort_desc: bool = Field(default=True, description="Sort descending.")
    limit: int = Field(default=20, description="Maximum results.", ge=1, le=100)
    response_format: str = Field(default="markdown", description="'markdown' or 'json'.", pattern=r"^(markdown|json)$")

    @field_validator("name", "nationality", "club", "position")
    @classmethod
    def _strip(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else None


class StandingsInput(BaseModel):
    """Calculate competition standings from match results."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    competition: str = Field(
        default="Brasileirão",
        description="Competition: 'Brasileirão', 'Copa do Brasil', or 'Libertadores'.",
        min_length=1, max_length=50,
    )
    season: int = Field(..., description="Season year.", ge=2000, le=2030)
    stage: Optional[str] = Field(default=None, description="Optional stage filter for Libertadores.", min_length=1, max_length=50)
    limit: int = Field(default=20, description="Top N teams to return.", ge=1, le=50)
    response_format: str = Field(default="markdown", description="'markdown' or 'json'.", pattern=r"^(markdown|json)$")

    @field_validator("competition")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()


class StatsAnalysisInput(BaseModel):
    """Run statistical analysis on match data."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    analysis_type: str = Field(
        ...,
        description="Analysis type: 'averages', 'biggest_wins', 'home_away', 'goal_trends', 'top_scorers'.",
        pattern=r"^(averages|biggest_wins|home_away|goal_trends|top_scorers)$",
    )
    competition: Optional[str] = Field(default=None, description="Filter by competition.")
    season: Optional[int] = Field(default=None, description="Filter by season.", ge=2000, le=2030)
    team: Optional[str] = Field(default=None, description="Optional team filter.", min_length=1, max_length=100)
    limit: int = Field(default=10, description="Max results for ranked lists.", ge=1, le=50)
    response_format: str = Field(default="markdown", description="'markdown' or 'json'.", pattern=r"^(markdown|json)$")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="soccer_search_matches",
    annotations={
        "title": "Search Soccer Matches",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def soccer_search_matches(params: MatchSearchInput) -> str:
    """Search Brazilian soccer matches by team, opponent, competition, season, date range, or stage.

    Searches across all loaded datasets: Brasileirão, Copa do Brasil, Libertadores,
    and the extended BR-Football dataset. Team names are normalized across datasets.

    Args:
        params: Validated MatchSearchInput with optional team, opponent, competition,
                season, date_from, date_to, stage, limit, and response_format.

    Returns:
        Markdown table or JSON list of matches with date, teams, score, competition, and round/stage.
    """
    data = load_all()
    matches = data["matches"]

    # Filters
    results = matches
    if params.team:
        results = [m for m in results
                   if params.team in (m["home_team"] or "").lower()
                   or params.team in (m["away_team"] or "").lower()]
    if params.opponent:
        results = [m for m in results
                   if {params.team, params.opponent} & {
                       (m["home_team"] or "").lower(), (m["away_team"] or "").lower()} == {params.team, params.opponent}]
    if params.competition:
        comp = params.competition.lower()
        results = [m for m in results if comp in m["competition"].lower()]
    if params.season is not None:
        results = [m for m in results if m["season"] == params.season]
    if params.date_from:
        try:
            df = datetime.strptime(params.date_from, "%Y-%m-%d")
            results = [m for m in results if m["date"] and m["date"] >= df]
        except ValueError:
            pass
    if params.date_to:
        try:
            dt = datetime.strptime(params.date_to, "%Y-%m-%d")
            results = [m for m in results if m["date"] and m["date"] <= dt]
        except ValueError:
            pass
    if params.stage:
        st = params.stage.lower()
        results = [m for m in results if st in (m.get("stage") or "").lower()]

    # Sort by date descending
    results.sort(key=lambda m: m["date"] or datetime.min, reverse=True)

    total = len(results)
    results = results[:params.limit]

    if not results:
        return "No matches found matching the given criteria."

    if params.response_format == "json":
        out = []
        for m in results:
            out.append({
                "date": _date_str(m["date"]),
                "home_team": m["home_team"],
                "away_team": m["away_team"],
                "score": f"{m['home_goal']}-{m['away_goal']}",
                "home_goal": m["home_goal"],
                "away_goal": m["away_goal"],
                "competition": m["competition"],
                "season": m["season"],
                "round": m.get("round") or m.get("stage") or "",
            })
        return json.dumps({"total": total, "shown": len(out), "matches": out}, indent=2, ensure_ascii=False)

    # Markdown
    lines = [f"# Match Results ({total} total, showing {len(results)})", ""]
    lines.append("| Date | Home | Score | Away | Competition | Round/Stage |")
    lines.append("|------|------|-------|------|-------------|-------------|")
    for m in results:
        rnd = m.get("round") or m.get("stage") or ""
        lines.append(
            f"| {_date_str(m['date'])} | {m['home_team']} | "
            f"{m['home_goal']}-{m['away_goal']} | {m['away_team']} | "
            f"{m['competition']} | {rnd} |"
        )
    return "\n".join(lines)


@mcp.tool(
    name="soccer_team_stats",
    annotations={
        "title": "Team Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def soccer_team_stats(params: TeamStatsInput) -> str:
    """Get aggregated win/loss/draw statistics for a team across competitions and seasons.

    Supports filtering by competition, season, and home/away split.

    Args:
        params: Validated TeamStatsInput with team name, optional competition, season, home_away.

    Returns:
        Markdown summary or JSON with matches, wins, draws, losses, goals for/against, and win rate.
    """
    data = load_all()
    matches = data["matches"]

    # Filter by team
    team_matches = _matches_for_team(matches, params.team)
    if not team_matches:
        return f"No matches found for team '{params.team}'."

    # Competition filter
    if params.competition:
        comp = params.competition.lower()
        team_matches = [m for m in team_matches if comp in m["competition"].lower()]

    # Season filter
    if params.season is not None:
        team_matches = [m for m in team_matches if m["season"] == params.season]

    # Home/away filter
    t = params.team.lower()
    if params.home_away == "home":
        team_matches = [m for m in team_matches if m["home_team"] and m["home_team"].lower() == t]
    elif params.home_away == "away":
        team_matches = [m for m in team_matches if m["away_team"] and m["away_team"].lower() == t]

    stats = _team_stats(team_matches, params.team)
    total = stats["matches"]
    if total == 0:
        return f"No matches found for '{params.team}' with the given filters."

    win_rate = (stats["wins"] / total * 100) if total > 0 else 0.0

    if params.response_format == "json":
        return json.dumps({
            "team": params.team,
            "matches": total,
            "wins": stats["wins"],
            "draws": stats["draws"],
            "losses": stats["losses"],
            "goals_for": stats["goals_for"],
            "goals_against": stats["goals_against"],
            "goal_difference": stats["goals_for"] - stats["goals_against"],
            "win_rate_pct": round(win_rate, 1),
        }, indent=2, ensure_ascii=False)

    # Markdown
    lines = [
        f"# {params.team.title()} Statistics",
        "",
        f"- **Matches**: {total}",
        f"- **Wins**: {stats['wins']}",
        f"- **Draws**: {stats['draws']}",
        f"- **Losses**: {stats['losses']}",
        f"- **Goals For**: {stats['goals_for']}",
        f"- **Goals Against**: {stats['goals_against']}",
        f"- **Goal Difference**: {stats['goals_for'] - stats['goals_against']}",
        f"- **Win Rate**: {win_rate:.1f}%",
    ]
    return "\n".join(lines)


@mcp.tool(
    name="soccer_head_to_head",
    annotations={
        "title": "Head-to-Head Comparison",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def soccer_head_to_head(params: HeadToHeadInput) -> str:
    """Compare two teams' head-to-head record across all competitions.

    Computes wins, draws, losses, and goals for each side, plus lists recent matches.

    Args:
        params: Validated HeadToHeadInput with team_a, team_b, optional competition filter.

    Returns:
        Markdown summary or JSON with H2H record and recent matches.
    """
    data = load_all()
    matches = data["matches"]

    # Competition filter
    if params.competition:
        comp = params.competition.lower()
        pool = [m for m in matches if comp in m["competition"].lower()]
    else:
        pool = matches

    h2h = _head_to_head(pool, params.team_a, params.team_b)

    if h2h["total_matches"] == 0:
        return f"No head-to-head matches found between '{params.team_a}' and '{params.team_b}'."

    if params.response_format == "json":
        out = {
            "team_a": h2h["team_a"],
            "team_b": h2h["team_b"],
            "team_a_wins": h2h["team_a_wins"],
            "team_b_wins": h2h["team_b_wins"],
            "draws": h2h["draws"],
            "team_a_goals": h2h["team_a_goals"],
            "team_b_goals": h2h["team_b_goals"],
            "total_matches": h2h["total_matches"],
            "recent_matches": [
                {
                    "date": _date_str(m["date"]),
                    "home_team": m["home_team"],
                    "away_team": m["away_team"],
                    "score": f"{m['home_goal']}-{m['away_goal']}",
                    "competition": m["competition"],
                }
                for m in h2h["matches"][:20]
            ],
        }
        return json.dumps(out, indent=2, ensure_ascii=False)

    # Markdown
    ta = h2h["team_a"].title()
    tb = h2h["team_b"].title()
    lines = [
        f"# {ta} vs {tb} — Head-to-Head",
        "",
        f"**Total Matches**: {h2h['total_matches']}",
        "",
        f"|  | {ta} | {tb} |",
        f"|---|------|------|",
        f"| Wins | {h2h['team_a_wins']} | {h2h['team_b_wins']} |",
        f"| Goals | {h2h['team_a_goals']} | {h2h['team_b_goals']} |",
        f"| Draws | {h2h['draws']} | {h2h['draws']} |",
        "",
        "## Recent Matches",
        "",
        "| Date | Home | Score | Away | Competition |",
        "|------|------|-------|------|-------------|",
    ]
    for m in h2h["matches"][:20]:
        lines.append(
            f"| {_date_str(m['date'])} | {m['home_team']} | "
            f"{m['home_goal']}-{m['away_goal']} | {m['away_team']} | "
            f"{m['competition']} |"
        )
    return "\n".join(lines)


@mcp.tool(
    name="soccer_search_players",
    annotations={
        "title": "Search FIFA Players",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def soccer_search_players(params: PlayerSearchInput) -> str:
    """Search FIFA player database by name, nationality, club, position, or rating range.

    Returns player profiles with overall/potential ratings, position, club, age, and key attributes.

    Args:
        params: Validated PlayerSearchInput with optional filters and sort options.

    Returns:
        Markdown list or JSON array of matching players.
    """
    data = load_all()
    players = data["players"]

    results = players
    if params.name:
        n = params.name.lower()
        results = [p for p in results if n in p["name"].lower()]
    if params.nationality:
        nat = params.nationality.lower()
        results = [p for p in results if nat in p["nationality"].lower()]
    if params.club:
        c = params.club.lower()
        results = [p for p in results if c in p["club"].lower()]
    if params.position:
        pos = params.position.upper()
        results = [p for p in results if pos in p["position"].upper()]
    if params.min_overall is not None:
        results = [p for p in results if p["overall"] >= params.min_overall]
    if params.max_overall is not None:
        results = [p for p in results if p["overall"] <= params.max_overall]

    # Sort
    sort_key = params.sort_by
    results.sort(key=lambda p: p.get(sort_key, 0) or 0, reverse=params.sort_desc)

    total = len(results)
    results = results[:params.limit]

    if not results:
        return "No players found matching the given criteria."

    if params.response_format == "json":
        out = []
        for p in results:
            out.append({
                "name": p["name"],
                "nationality": p["nationality"],
                "club": p["club"],
                "position": p["position"],
                "overall": p["overall"],
                "potential": p["potential"],
                "age": p["age"],
                "preferred_foot": p["preferred_foot"],
                "value": p["value"],
                "wage": p["wage"],
            })
        return json.dumps({"total": total, "shown": len(out), "players": out}, indent=2, ensure_ascii=False)

    # Markdown
    lines = [f"# Player Search Results ({total} total, showing {len(results)})", ""]
    for i, p in enumerate(results, 1):
        lines.append(
            f"{i}. **{p['name']}** — Overall: {p['overall']}, Potential: {p['potential']}, "
            f"Position: {p['position']}, Club: {p['club']}, Age: {p['age']}, "
            f"Nationality: {p['nationality']}"
        )
    return "\n".join(lines)


@mcp.tool(
    name="soccer_competition_standings",
    annotations={
        "title": "Competition Standings",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def soccer_competition_standings(params: StandingsInput) -> str:
    """Calculate competition standings from match results for a given season.

    Awards 3 points for a win, 1 for a draw. Sorted by points, then goal difference, then goals scored.

    Args:
        params: Validated StandingsInput with competition, season, optional stage.

    Returns:
        Markdown table or JSON with position, team, points, W/D/L, GF/GA/GD.
    """
    data = load_all()
    matches = data["matches"]

    comp = params.competition.lower()
    season_matches = [
        m for m in matches
        if comp in m["competition"].lower() and m["season"] == params.season
    ]
    if params.stage:
        st = params.stage.lower()
        season_matches = [m for m in season_matches if st in (m.get("stage") or "").lower()]

    if not season_matches:
        return f"No matches found for {params.competition} season {params.season}."

    # Aggregate per team
    teams: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        "pts": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "played": 0,
    })

    for m in season_matches:
        ht = m["home_team"]
        at = m["away_team"]
        if not ht or not at:
            continue
        hg = m["home_goal"]
        ag = m["away_goal"]

        teams[ht]["played"] += 1
        teams[ht]["gf"] += hg
        teams[ht]["ga"] += ag
        if hg > ag:
            teams[ht]["pts"] += 3
            teams[ht]["w"] += 1
        elif hg < ag:
            teams[ht]["l"] += 1
        else:
            teams[ht]["pts"] += 1
            teams[ht]["d"] += 1

        teams[at]["played"] += 1
        teams[at]["gf"] += ag
        teams[at]["ga"] += hg
        if ag > hg:
            teams[at]["pts"] += 3
            teams[at]["w"] += 1
        elif ag < hg:
            teams[at]["l"] += 1
        else:
            teams[at]["pts"] += 1
            teams[at]["d"] += 1

    # Sort: pts desc, gd desc, gf desc
    ranking = sorted(teams.items(), key=lambda kv: (
        -kv[1]["pts"],
        -(kv[1]["gf"] - kv[1]["ga"]),
        -kv[1]["gf"],
    ))

    ranking = ranking[:params.limit]

    if params.response_format == "json":
        out = []
        for pos, (team, s) in enumerate(ranking, 1):
            out.append({
                "position": pos,
                "team": team,
                "played": s["played"],
                "points": s["pts"],
                "wins": s["w"],
                "draws": s["d"],
                "losses": s["l"],
                "goals_for": s["gf"],
                "goals_against": s["ga"],
                "goal_difference": s["gf"] - s["ga"],
            })
        return json.dumps({"competition": params.competition, "season": params.season,
                          "standings": out}, indent=2, ensure_ascii=False)

    # Markdown
    lines = [
        f"# {params.competition} {params.season} Standings",
        "",
        "| # | Team | P | W | D | L | GF | GA | GD | Pts |",
        "|---|------|---|---|---|---|----|----|----|-----|",
    ]
    for pos, (team, s) in enumerate(ranking, 1):
        gd = s["gf"] - s["ga"]
        lines.append(
            f"| {pos} | {team} | {s['played']} | {s['w']} | {s['d']} | {s['l']} | "
            f"{s['gf']} | {s['ga']} | {gd:+d} | {s['pts']} |"
        )
    return "\n".join(lines)


@mcp.tool(
    name="soccer_stats_analysis",
    annotations={
        "title": "Statistical Analysis",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def soccer_stats_analysis(params: StatsAnalysisInput) -> str:
    """Perform statistical analysis on match data: averages, biggest wins, home/away split, goal trends, top scorers.

    Args:
        params: Validated StatsAnalysisInput with analysis_type, optional filters.

    Returns:
        Markdown or JSON with statistical findings.
    """
    data = load_all()
    matches = data["matches"]

    # Apply filters
    pool = matches
    if params.competition:
        comp = params.competition.lower()
        pool = [m for m in pool if comp in m["competition"].lower()]
    if params.season is not None:
        pool = [m for m in pool if m["season"] == params.season]
    if params.team:
        pool = _matches_for_team(pool, params.team)

    if not pool:
        return "No match data available for the given filters."

    total = len(pool)
    total_goals = sum(m["home_goal"] + m["away_goal"] for m in pool)
    avg_goals = total_goals / total if total else 0.0

    home_wins = sum(1 for m in pool if m["home_goal"] > m["away_goal"])
    away_wins = sum(1 for m in pool if m["away_goal"] > m["home_goal"])
    draws = sum(1 for m in pool if m["home_goal"] == m["away_goal"])

    if params.response_format == "json":
        base = {
            "total_matches": total,
            "total_goals": total_goals,
            "avg_goals_per_match": round(avg_goals, 2),
            "home_win_pct": round(home_wins / total * 100, 1) if total else 0,
            "away_win_pct": round(away_wins / total * 100, 1) if total else 0,
            "draw_pct": round(draws / total * 100, 1) if total else 0,
        }
    else:
        base = {}

    atype = params.analysis_type

    if atype == "averages":
        if params.response_format == "json":
            return json.dumps(base, indent=2, ensure_ascii=False)
        lines = [
            "# Match Averages",
            "",
            f"- **Total Matches**: {total}",
            f"- **Total Goals**: {total_goals}",
            f"- **Average Goals/Match**: {avg_goals:.2f}",
            f"- **Home Win Rate**: {home_wins / total * 100:.1f}%",
            f"- **Away Win Rate**: {away_wins / total * 100:.1f}%",
            f"- **Draw Rate**: {draws / total * 100:.1f}%",
        ]
        return "\n".join(lines)

    elif atype == "biggest_wins":
        # Sort by goal difference descending
        sorted_matches = sorted(pool, key=lambda m: abs(m["home_goal"] - m["away_goal"]), reverse=True)
        top = sorted_matches[:params.limit]
        if params.response_format == "json":
            out = []
            for m in top:
                out.append({
                    "date": _date_str(m["date"]),
                    "home_team": m["home_team"],
                    "away_team": m["away_team"],
                    "score": f"{m['home_goal']}-{m['away_goal']}",
                    "difference": abs(m["home_goal"] - m["away_goal"]),
                    "competition": m["competition"],
                })
            return json.dumps({"biggest_wins": out}, indent=2, ensure_ascii=False)
        lines = ["# Biggest Victories", ""]
        lines.append("| # | Date | Home | Score | Away | Diff | Competition |")
        lines.append("|---|------|------|-------|------|------|-------------|")
        for i, m in enumerate(top, 1):
            diff = abs(m["home_goal"] - m["away_goal"])
            lines.append(
                f"| {i} | {_date_str(m['date'])} | {m['home_team']} | "
                f"{m['home_goal']}-{m['away_goal']} | {m['away_team']} | "
                f"{diff} | {m['competition']} |"
            )
        return "\n".join(lines)

    elif atype == "home_away":
        # Best home / away records
        home_records: Dict[str, Dict[str, int]] = defaultdict(lambda: {"p": 0, "w": 0, "gf": 0, "ga": 0})
        away_records: Dict[str, Dict[str, int]] = defaultdict(lambda: {"p": 0, "w": 0, "gf": 0, "ga": 0})

        for m in pool:
            ht = m["home_team"]
            at = m["away_team"]
            if not ht or not at:
                continue
            hg = m["home_goal"]
            ag = m["away_goal"]

            home_records[ht]["p"] += 1
            home_records[ht]["gf"] += hg
            home_records[ht]["ga"] += ag
            if hg > ag:
                home_records[ht]["w"] += 1

            away_records[at]["p"] += 1
            away_records[at]["gf"] += ag
            away_records[at]["ga"] += hg
            if ag > hg:
                away_records[at]["w"] += 1

        best_home = sorted(
            [(t, r) for t, r in home_records.items() if r["p"] >= 5],
            key=lambda x: x[1]["w"] / x[1]["p"] if x[1]["p"] else 0, reverse=True,
        )[:10]
        best_away = sorted(
            [(t, r) for t, r in away_records.items() if r["p"] >= 5],
            key=lambda x: x[1]["w"] / x[1]["p"] if x[1]["p"] else 0, reverse=True,
        )[:10]

        if params.response_format == "json":
            return json.dumps({
                "best_home": [
                    {"team": t, "played": r["p"],
                     "win_rate": round(r["w"] / r["p"] * 100, 1) if r["p"] else 0}
                    for t, r in best_home
                ],
                "best_away": [
                    {"team": t, "played": r["p"],
                     "win_rate": round(r["w"] / r["p"] * 100, 1) if r["p"] else 0}
                    for t, r in best_away
                ],
            }, indent=2, ensure_ascii=False)

        lines = ["# Best Home Records", ""]
        lines.append("| # | Team | Played | Wins | Win Rate |")
        lines.append("|---|------|--------|------|----------|")
        for i, (t, r) in enumerate(best_home, 1):
            wr = r["w"] / r["p"] * 100 if r["p"] else 0
            lines.append(f"| {i} | {t} | {r['p']} | {r['w']} | {wr:.1f}% |")

        lines.extend(["", "# Best Away Records", ""])
        lines.append("| # | Team | Played | Wins | Win Rate |")
        lines.append("|---|------|--------|------|----------|")
        for i, (t, r) in enumerate(best_away, 1):
            wr = r["w"] / r["p"] * 100 if r["p"] else 0
            lines.append(f"| {i} | {t} | {r['p']} | {r['w']} | {wr:.1f}% |")

        return "\n".join(lines)

    elif atype == "goal_trends":
        # Goals per season
        season_goals: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"goals": 0, "matches": 0})
        for m in pool:
            s = m["season"]
            season_goals[s]["goals"] += m["home_goal"] + m["away_goal"]
            season_goals[s]["matches"] += 1

        trends = sorted(season_goals.items())

        if params.response_format == "json":
            out = []
            for s, v in trends:
                out.append({
                    "season": s,
                    "matches": v["matches"],
                    "total_goals": v["goals"],
                    "avg_goals": round(v["goals"] / v["matches"], 2) if v["matches"] else 0,
                })
            return json.dumps({"goal_trends": out}, indent=2, ensure_ascii=False)

        lines = ["# Goal Trends by Season", ""]
        lines.append("| Season | Matches | Total Goals | Avg/Match |")
        lines.append("|--------|---------|-------------|-----------|")
        for s, v in trends:
            avg = v["goals"] / v["matches"] if v["matches"] else 0
            lines.append(f"| {s} | {v['matches']} | {v['goals']} | {avg:.2f} |")
        return "\n".join(lines)

    elif atype == "top_scorers":
        # Aggregate goals by team (since we don't have individual scorers, show highest-scoring teams)
        team_totals: Dict[str, int] = defaultdict(int)
        for m in pool:
            ht = m["home_team"]
            at = m["away_team"]
            if ht:
                team_totals[ht] += m["home_goal"]
            if at:
                team_totals[at] += m["away_goal"]

        top = sorted(team_totals.items(), key=lambda x: x[1], reverse=True)[:params.limit]

        if params.response_format == "json":
            out = [{"team": t, "goals": g} for t, g in top]
            return json.dumps({"top_scoring_teams": out}, indent=2, ensure_ascii=False)

        lines = ["# Top Scoring Teams", ""]
        lines.append("| # | Team | Goals |")
        lines.append("|---|------|-------|")
        for i, (t, g) in enumerate(top, 1):
            lines.append(f"| {i} | {t} | {g} |")
        return "\n".join(lines)

    return "Unknown analysis type."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Pre-load data so it's cached before the server starts
    load_all()

    if "--http" in sys.argv:
        mcp.run(transport="streamable_http", port=8000)
    else:
        mcp.run()
