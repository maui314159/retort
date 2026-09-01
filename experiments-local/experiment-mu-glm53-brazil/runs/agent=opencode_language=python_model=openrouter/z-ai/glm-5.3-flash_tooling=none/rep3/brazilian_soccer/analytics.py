"""Statistical computations over normalized Match objects.

All functions are pure: they take lists of already-filtered matches (and
canonical team keys) and return plain dictionaries, ready to be serialized
by the MCP tool layer.

League standings assume a double round-robin (3 points per win, 1 per
draw) with the classic tiebreak order: points, wins, goal difference,
goals scored.  The 2019 Série A season computed from the union of the
three overlapping datasets reproduces exactly 380 matches and Flamengo as
champion, which the BDD suite asserts as a data-quality gate.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .models import Match


def team_record(matches: list[Match], key: str) -> dict:
    """Win/draw/loss record of one team across the given matches."""
    rec = {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
           "goals_for": 0, "goals_against": 0}
    for m in matches:
        if not m.has_result() or key not in (m.home_key, m.away_key):
            continue
        rec["matches"] += 1
        gf = m.home_goal if m.home_key == key else m.away_goal
        ga = m.away_goal if m.home_key == key else m.home_goal
        rec["goals_for"] += gf
        rec["goals_against"] += ga
        if gf > ga:
            rec["wins"] += 1
        elif gf < ga:
            rec["losses"] += 1
        else:
            rec["draws"] += 1
    rec["points"] = rec["wins"] * 3 + rec["draws"]
    total = rec["wins"] + rec["draws"] + rec["losses"]
    rec["win_rate"] = round(100.0 * rec["wins"] / total, 1) if total else 0.0
    return rec


def h2h_record(matches: list[Match], team_a: str, team_b: str) -> dict:
    """Head-to-head summary between two canonical keys."""
    rec = {team_a: 0, team_b: 0, "draws": 0}
    goals = {team_a: 0, team_b: 0}
    for m in matches:
        if not m.has_result():
            continue
        if m.home_key == team_a and m.away_key == team_b:
            goals[team_a] += m.home_goal
            goals[team_b] += m.away_goal
        elif m.home_key == team_b and m.away_key == team_a:
            goals[team_b] += m.home_goal
            goals[team_a] += m.away_goal
        else:
            continue
        w = m.winner_key()
        if w is None:
            rec["draws"] += 1
        else:
            rec[w] += 1
    return {
        "team_a_wins": rec[team_a],
        "team_b_wins": rec[team_b],
        "draws": rec["draws"],
        "team_a_goals": goals[team_a],
        "team_b_goals": goals[team_b],
    }


def standings_table(matches: list[Match]) -> list[dict]:
    """League table from a season's matches (double round-robin)."""
    rows: dict[str, dict] = {}
    for m in matches:
        if not m.has_result():
            continue
        for key, gf, ga in ((m.home_key, m.home_goal, m.away_goal),
                            (m.away_key, m.away_goal, m.home_goal)):
            row = rows.setdefault(key, {
                "team": key, "matches": 0, "wins": 0, "draws": 0,
                "losses": 0, "goals_for": 0, "goals_against": 0,
            })
            row["matches"] += 1
            row["goals_for"] += gf
            row["goals_against"] += ga
            if gf > ga:
                row["wins"] += 1
            elif gf < ga:
                row["losses"] += 1
            else:
                row["draws"] += 1
    table = []
    for r in rows.values():
        r["goal_difference"] = r["goals_for"] - r["goals_against"]
        r["points"] = r["wins"] * 3 + r["draws"]
        table.append(r)
    table.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"],
                              -r["goals_for"], r["team"]))
    for i, r in enumerate(table, start=1):
        r["position"] = i
    return table


def biggest_wins(matches: list[Match], top: int = 10) -> list[dict]:
    """Matches with the largest goal margin (winning side first)."""
    out = []
    for m in matches:
        if not m.has_result():
            continue
        margin = abs(m.home_goal - m.away_goal)
        if margin == 0:
            continue
        if m.home_goal > m.away_goal:
            winner, loser, wf, lf = m.home_key, m.away_key, m.home_goal, m.away_goal
        else:
            winner, loser, wf, lf = m.away_key, m.home_key, m.away_goal, m.home_goal
        out.append({"margin": margin, "winner": winner, "loser": loser,
                    "winner_goals": wf, "loser_goals": lf, "match": m})
    out.sort(key=lambda x: (-x["margin"], x["match"].date or date.min))
    return out[:top]


def aggregate_stats(matches: list[Match]) -> dict:
    """Average goals and home-advantage numbers for a set of matches."""
    played = [m for m in matches if m.has_result()]
    total = len(played)
    goals = sum(m.home_goal + m.away_goal for m in played)
    home_wins = sum(1 for m in played if m.home_goal > m.away_goal)
    away_wins = sum(1 for m in played if m.away_goal > m.home_goal)
    draws = total - home_wins - away_wins
    return {
        "matches": total,
        "goals": goals,
        "avg_goals_per_match": round(goals / total, 2) if total else 0.0,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(100.0 * home_wins / total, 1) if total else 0.0,
        "away_win_rate": round(100.0 * away_wins / total, 1) if total else 0.0,
        "draw_rate": round(100.0 * draws / total, 1) if total else 0.0,
    }


def best_venues(matches: list[Match], venue: str, top: int = 5,
                min_matches: int = 30) -> list[dict]:
    """Teams with the best home ('home') or away ('away') record."""
    per_team: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        if venue == "home":
            per_team[m.home_key].append(m)
        else:
            per_team[m.away_key].append(m)
    scored = []
    for key, ms in per_team.items():
        if len(ms) < min_matches:
            continue
        rec = team_record(ms, key)
        scored.append({"team": key, "record": rec})
    scored.sort(key=lambda x: (-x["record"]["win_rate"], -x["record"]["wins"]))
    return scored[:top]


def season_comparison(matches_by_season: dict[int, list[Match]]) -> list[dict]:
    """Compare aggregate statistics across seasons."""
    out = []
    for season in sorted(matches_by_season):
        stats = aggregate_stats(matches_by_season[season])
        stats["season"] = season
        out.append(stats)
    return out
