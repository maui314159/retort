"""Query layer: the answer-engine the MCP tools delegate to.

Context
-------
This module turns the in-memory :class:`~brazilian_soccer_mcp.knowledge_graph.KnowledgeGraph`
into a small set of pure functions that produce plain-Python (JSON-friendly)
result dictionaries.  Every function returns ``dict`` / ``list`` only, so
the MCP tool layer can ``json.dumps`` the output verbatim and tests can
assert on structured data without parsing prose.

The functions are grouped by the five required capability categories from
``brazilian-soccer-mcp-guide.md``:

1. Match queries     — :func:`find_matches`, :func:`head_to_head`
2. Team queries      — :func:`team_stats`, :func:`team_info`
3. Player queries    — :func:`search_players`, :func:`player_info`,
                       :func:`top_players_at_club`
4. Competition       — :func:`competition_standings`, :func:`competition_info`
5. Statistical       — :func:`biggest_wins`, :func:`average_goals`,
                       :func:`home_advantage`, :func:`best_home_record`,
                       :func:`biggest_team_dataset`

All ``team``/``opponent``/``club`` arguments accept *any* spelling; the
knowledge-graph normalizer resolves them to the canonical club name, and
all downstream matching is plain string equality on that canonical name.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Optional

from .knowledge_graph import KnowledgeGraph
from .models import MatchRecord
from .normalize import _fold

# Cap on the number of match rows we surface by default so tool responses
# stay well within LLM context budgets.  Callers can raise it explicitly.
DEFAULT_MATCH_LIMIT = 50
DEFAULT_PLAYER_LIMIT = 25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _match_summary(m: MatchRecord, team_canon: Optional[str] = None) -> dict[str, Any]:
    """Compact, JSON-friendly summary of one match."""

    summary: dict[str, Any] = {
        "date": m.date.isoformat() if m.date else None,
        "season": m.season,
        "competition": m.competition,
        "home_team": m.home_team,
        "away_team": m.away_team,
        "score": {"home": m.home_goal, "away": m.away_goal},
    }
    if m.round:
        summary["round"] = m.round
    if m.stage:
        summary["stage"] = m.stage
    if m.venue:
        summary["venue"] = m.venue
    if team_canon is not None:
        summary["result"] = m.result_for(team_canon)
    return summary


def _canonical(kg: KnowledgeGraph, name: str) -> Optional[str]:
    return kg.dataset.normalizer.canonical(name)


def _competition_matches(actual: str, requested: str) -> bool:
    """Case/accent-insensitive competition name match."""

    return _fold(actual) == _fold(requested)


def _filter_matches(
    kg: KnowledgeGraph,
    *,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[MatchRecord]:
    """Low-level filter shared by match and head-to-head queries."""

    if team is not None:
        matches = kg.team_matches(team, role="either")
    else:
        matches = list(kg.dataset.matches)

    if opponent is not None:
        opp_canon = _canonical(kg, opponent)
        if opp_canon is None:
            return []
        matches = [
            m for m in matches
            if m.home_team == opp_canon or m.away_team == opp_canon
        ]

    if competition is not None:
        matches = [m for m in matches if _competition_matches(m.competition, competition)]

    if season is not None:
        matches = [m for m in matches if m.season == season]

    if start_date is not None:
        matches = [m for m in matches if m.date is not None and m.date >= start_date]
    if end_date is not None:
        matches = [m for m in matches if m.date is not None and m.date <= end_date]

    return matches


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------


def find_matches(
    kg: KnowledgeGraph,
    *,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = DEFAULT_MATCH_LIMIT,
) -> dict[str, Any]:
    """Find matches by team, opponent, competition, season and/or date range.

    Any filter left ``None`` is treated as "don't filter on this axis".
    """

    matches = _filter_matches(
        kg,
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        start_date=start_date,
        end_date=end_date,
    )
    # Most recent first when dates are available, otherwise stable order.
    matches.sort(key=lambda m: (m.date or date.min), reverse=True)
    total = len(matches)
    limited = matches[: limit if limit and limit > 0 else len(matches)]
    team_canon = _canonical(kg, team) if team else None
    return {
        "query": {
            "team": team,
            "opponent": opponent,
            "competition": competition,
            "season": season,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        "total": total,
        "returned": len(limited),
        "matches": [_match_summary(m, team_canon=team_canon) for m in limited],
    }


def head_to_head(
    kg: KnowledgeGraph,
    team_a: str,
    team_b: str,
    *,
    competition: Optional[str] = None,
    limit: int = DEFAULT_MATCH_LIMIT,
) -> dict[str, Any]:
    """Head-to-head record between two teams across the whole dataset."""

    matches = kg.head_to_head(team_a, team_b)
    if competition is not None:
        matches = [m for m in matches if _competition_matches(m.competition, competition)]
    canon_a = _canonical(kg, team_a) or team_a
    canon_b = _canonical(kg, team_b) or team_b
    wins_a = wins_b = draws = 0
    gf_a = gf_b = 0
    for m in matches:
        res_a = m.result_for(canon_a)
        if m.home_goal is not None and m.away_goal is not None:
            if m.home_team == canon_a:
                gf_a += m.home_goal
                gf_b += m.away_goal
            else:
                gf_a += m.away_goal
                gf_b += m.home_goal
        if res_a == "win":
            wins_a += 1
        elif res_a == "loss":
            wins_b += 1
        elif res_a == "draw":
            draws += 1
    total = len(matches)
    summary = [_match_summary(m) for m in matches[: limit if limit and limit > 0 else total]]
    return {
        "team_a": canon_a,
        "team_b": canon_b,
        "total_matches": total,
        "team_a_wins": wins_a,
        "team_b_wins": wins_b,
        "draws": draws,
        "team_a_goals": gf_a,
        "team_b_goals": gf_b,
        "matches": summary,
    }


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------


def _team_record(matches: list[MatchRecord], team_canon: str) -> dict[str, Any]:
    wins = losses = draws = 0
    gf = ga = 0
    home_w = home_d = home_l = 0
    away_w = away_d = away_l = 0
    for m in matches:
        res = m.result_for(team_canon)
        if res is None:
            continue
        if m.home_goal is not None and m.away_goal is not None:
            if m.home_team == team_canon:
                gf += m.home_goal
                ga += m.away_goal
                if res == "win":
                    home_w += 1
                elif res == "draw":
                    home_d += 1
                else:
                    home_l += 1
            else:
                gf += m.away_goal
                ga += m.home_goal
                if res == "win":
                    away_w += 1
                elif res == "draw":
                    away_d += 1
                else:
                    away_l += 1
        if res == "win":
            wins += 1
        elif res == "loss":
            losses += 1
        elif res == "draw":
            draws += 1
    played = wins + losses + draws
    return {
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "win_rate": round(wins / played, 4) if played else 0.0,
        "home": {"wins": home_w, "draws": home_d, "losses": home_l},
        "away": {"wins": away_w, "draws": away_d, "losses": away_l},
    }


def team_stats(
    kg: KnowledgeGraph,
    team: str,
    *,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: Optional[str] = None,
) -> dict[str, Any]:
    """Win/loss/draw record and goal tally for a team, with optional filters.

    ``venue`` accepts "home", "away" or "either" (default).
    """

    venue = (venue or "either").lower()
    role = {"home": "home", "away": "away"}.get(venue, "either")
    matches = kg.team_matches(team, role=role)
    if competition is not None:
        matches = [m for m in matches if _competition_matches(m.competition, competition)]
    if season is not None:
        matches = [m for m in matches if m.season == season]
    canon = _canonical(kg, team) or team
    record = _team_record(matches, canon)
    return {
        "team": canon,
        "filters": {"season": season, "competition": competition, "venue": venue},
        **record,
    }


def team_info(kg: KnowledgeGraph, team: str) -> dict[str, Any]:
    """Summary of what we know about a team: competitions, seasons, totals."""

    canon = _canonical(kg, team) or team
    matches = kg.team_matches(team, role="either")
    by_comp: dict[str, list[int]] = defaultdict(list)
    for m in matches:
        if m.season is not None:
            by_comp[m.competition].append(m.season)
    competitions = {
        comp: {
            "seasons": sorted(set(s for s in seasons if s is not None)),
            "matches": len(seasons),
        }
        for comp, seasons in by_comp.items()
    }
    node = kg.resolve_team(team)
    return {
        "team": canon,
        "total_matches": len(matches),
        "competitions": competitions,
        "players_in_fifa": len(node.players) if node else 0,
        "overall_record": _team_record(matches, canon),
    }


# ---------------------------------------------------------------------------
# 3. Player queries
# ---------------------------------------------------------------------------


def _player_summary(p) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "position": p.position,
        "jersey_number": p.jersey_number,
        "preferred_foot": p.preferred_foot,
    }


def search_players(
    kg: KnowledgeGraph,
    *,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = DEFAULT_PLAYER_LIMIT,
) -> dict[str, Any]:
    """Search FIFA players by name/nationality/club/position/rating."""

    players = kg.dataset.players
    if name is not None:
        needle = name.lower()
        players = [p for p in players if needle in (p.name or "").lower()]
    if nationality is not None:
        nat_fold = _fold(nationality)
        players = [p for p in players if _fold(p.nationality) == nat_fold]
    if club is not None:
        club_canon = _canonical(kg, club)
        if club_canon is not None:
            players = [p for p in players if _canonical(kg, p.club) == club_canon]
        else:
            club_fold = _fold(club)
            players = [p for p in players if club_fold in _fold(p.club or "")]
    if position is not None:
        pos = position.upper()
        players = [p for p in players if (p.position or "").upper() == pos]
    if min_overall is not None:
        players = [p for p in players if p.overall >= min_overall]

    players = sorted(players, key=lambda p: p.overall, reverse=True)
    total = len(players)
    limited = players[: limit if limit and limit > 0 else total]
    return {
        "query": {
            "name": name,
            "nationality": nationality,
            "club": club,
            "position": position,
            "min_overall": min_overall,
        },
        "total": total,
        "returned": len(limited),
        "players": [_player_summary(p) for p in limited],
    }


def player_info(kg: KnowledgeGraph, name: str) -> dict[str, Any]:
    """Full FIFA profile for the player(s) whose name matches *name*."""

    results = search_players(kg, name=name, limit=50)
    return {
        "query": name,
        "matches": results["total"],
        "players": results["players"],
    }


def top_players_at_club(
    kg: KnowledgeGraph,
    club: str,
    *,
    limit: int = 15,
) -> dict[str, Any]:
    """Highest-rated players at a given club (any spelling)."""

    return search_players(kg, club=club, limit=limit)


# ---------------------------------------------------------------------------
# 4. Competition queries
# ---------------------------------------------------------------------------


def competition_standings(
    kg: KnowledgeGraph,
    competition: str,
    season: Optional[int] = None,
    *,
    top: int = 20,
) -> dict[str, Any]:
    """Compute a league-style standings table from match results.

    Points: 3 for a win, 1 for a draw.  Sorted by points, then goal
    difference, then goals for.  Only competitions that look like a league
    (round-robin) produce meaningful standings; cup/knockout competitions
    will still produce a per-team aggregate but the "champion" tag is just
    the points leader.
    """

    comp_node = kg.competition(competition)
    if comp_node is None:
        return {
            "competition": competition,
            "season": season,
            "standings": [],
            "note": "unknown competition",
        }

    matches = comp_node.matches
    if season is not None:
        matches = [m for m in matches if m.season == season]

    table: dict[str, dict[str, int]] = defaultdict(
        lambda: {"played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "points": 0}
    )
    for m in matches:
        if m.home_goal is None or m.away_goal is None:
            continue
        h, a = m.home_team, m.away_team
        hg, ag = m.home_goal, m.away_goal
        table[h]["played"] += 1
        table[a]["played"] += 1
        table[h]["gf"] += hg
        table[h]["ga"] += ag
        table[a]["gf"] += ag
        table[a]["ga"] += hg
        if hg > ag:
            table[h]["wins"] += 1
            table[h]["points"] += 3
            table[a]["losses"] += 1
        elif hg < ag:
            table[a]["wins"] += 1
            table[a]["points"] += 3
            table[h]["losses"] += 1
        else:
            table[h]["draws"] += 1
            table[a]["draws"] += 1
            table[h]["points"] += 1
            table[a]["points"] += 1

    rows = []
    for team, stats in table.items():
        gd = stats["gf"] - stats["ga"]
        rows.append({"team": team, **stats, "goal_difference": gd})
    rows.sort(key=lambda r: (r["points"], r["goal_difference"], r["gf"]), reverse=True)
    rows = rows[: top if top and top > 0 else len(rows)]
    for i, row in enumerate(rows):
        row["position"] = i + 1
    if rows:
        rows[0]["champion"] = True
    return {
        "competition": comp_node.name,
        "season": season,
        "standings": rows,
    }


def competition_info(kg: KnowledgeGraph, competition: str) -> dict[str, Any]:
    """Summary of a competition: seasons, match count, teams."""

    comp_node = kg.competition(competition)
    if comp_node is None:
        return {"competition": competition, "note": "unknown"}
    seasons: set[int] = set()
    teams: set[str] = set()
    for m in comp_node.matches:
        if m.season is not None:
            seasons.add(m.season)
        teams.add(m.home_team)
        teams.add(m.away_team)
    return {
        "competition": comp_node.name,
        "total_matches": len(comp_node.matches),
        "seasons": sorted(seasons),
        "teams": sorted(teams),
    }


# ---------------------------------------------------------------------------
# 5. Statistical analysis
# ---------------------------------------------------------------------------


def average_goals(
    kg: KnowledgeGraph,
    *,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict[str, Any]:
    """Average goals per match, home win rate, and away win rate."""

    matches = _filter_matches(kg, competition=competition, season=season)
    valid = [m for m in matches if m.home_goal is not None and m.away_goal is not None]
    if not valid:
        return {
            "competition": competition,
            "season": season,
            "matches": 0,
            "average_goals": 0.0,
            "home_win_rate": 0.0,
            "away_win_rate": 0.0,
            "draw_rate": 0.0,
        }
    total_goals = sum(m.home_goal + m.away_goal for m in valid)
    home_wins = sum(1 for m in valid if m.home_goal > m.away_goal)
    away_wins = sum(1 for m in valid if m.away_goal > m.home_goal)
    draws = sum(1 for m in valid if m.home_goal == m.away_goal)
    n = len(valid)
    return {
        "competition": competition,
        "season": season,
        "matches": n,
        "total_goals": total_goals,
        "average_goals": round(total_goals / n, 3),
        "average_home_goals": round(sum(m.home_goal for m in valid) / n, 3),
        "average_away_goals": round(sum(m.away_goal for m in valid) / n, 3),
        "home_win_rate": round(home_wins / n, 4),
        "away_win_rate": round(away_wins / n, 4),
        "draw_rate": round(draws / n, 4),
    }


def biggest_wins(
    kg: KnowledgeGraph,
    *,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Largest goal-margin victories across the dataset."""

    matches = _filter_matches(kg, competition=competition, season=season)
    valid = [m for m in matches if m.home_goal is not None and m.away_goal is not None]
    valid.sort(
        key=lambda m: (abs(m.home_goal - m.away_goal), max(m.home_goal, m.away_goal)),
        reverse=True,
    )
    limited = valid[: limit if limit and limit > 0 else len(valid)]
    rows = []
    for m in limited:
        if m.home_goal > m.away_goal:
            winner, loser, wg, lg = m.home_team, m.away_team, m.home_goal, m.away_goal
        else:
            winner, loser, wg, lg = m.away_team, m.home_team, m.away_goal, m.home_goal
        rows.append({
            "date": m.date.isoformat() if m.date else None,
            "season": m.season,
            "competition": m.competition,
            "winner": winner,
            "loser": loser,
            "score": f"{wg}-{lg}",
            "margin": abs(m.home_goal - m.away_goal),
        })
    return {
        "competition": competition,
        "season": season,
        "count": len(rows),
        "biggest_wins": rows,
    }


def home_advantage(
    kg: KnowledgeGraph,
    *,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict[str, Any]:
    """Quantify home-field advantage: share of home wins vs away wins."""

    stats = average_goals(kg, competition=competition, season=season)
    return {
        "competition": stats["competition"],
        "season": stats["season"],
        "matches": stats["matches"],
        "home_win_rate": stats["home_win_rate"],
        "away_win_rate": stats["away_win_rate"],
        "draw_rate": stats["draw_rate"],
        "home_advantage_index": round(stats["home_win_rate"] - stats["away_win_rate"], 4),
    }


def best_home_record(
    kg: KnowledgeGraph,
    *,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Rank teams by home win rate within the given filters."""

    matches = _filter_matches(kg, competition=competition, season=season)
    by_team: dict[str, list[MatchRecord]] = defaultdict(list)
    for m in matches:
        if m.home_goal is None or m.away_goal is None:
            continue
        by_team[m.home_team].append(m)
    rows = []
    for team, tmatches in by_team.items():
        wins = sum(1 for m in tmatches if m.home_goal > m.away_goal)
        n = len(tmatches)
        rows.append({
            "team": team,
            "home_matches": n,
            "home_wins": wins,
            "home_win_rate": round(wins / n, 4) if n else 0.0,
        })
    rows.sort(key=lambda r: (r["home_win_rate"], r["home_wins"]), reverse=True)
    return {
        "competition": competition,
        "season": season,
        "best_home_records": rows[: limit if limit and limit > 0 else len(rows)],
    }


def biggest_team_dataset(kg: KnowledgeGraph, *, limit: int = 10) -> dict[str, Any]:
    """Teams with the most matches in the whole knowledge graph."""

    counts = sorted(
        ((name, len(node.matches)) for name, node in kg.teams.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    return {
        "most_active_teams": [{"team": n, "matches": c} for n, c in counts[:limit]],
    }
