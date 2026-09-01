"""Statistical engine over the unified match dataset.

Pure functions that take lists of :class:`models.Match` and produce the
aggregates required by the MCP tools:

* :func:`team_record` — win/draw/loss lines with home/away splits
* :func:`head_to_head` — paired head-to-head record between two teams
* :func:`standings` — full league table computed from match results,
  plus champion and relegated teams
* :func:`biggest_wins` — matches ranked by goal margin
* :func:`competition_aggregates` — average goals, home/draw/away win rates
* :func:`best_records` — teams ranked by points or win rate over a match set
* :func:`derby_matches` — matches between classic rival pairs

Everything here is deterministic and requires no state, so the MCP layer
can freely mix and match these building blocks.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from models import Match, TeamRecord
from normalize import DERBY_PAIRS, team_display_name


def _only_scored(matches: list[Match]) -> list[Match]:
    return [m for m in matches if m.home_goals is not None and m.away_goals is not None]


def team_record(matches: list[Match], team_key: str) -> TeamRecord:
    """Aggregate a team's record over the given matches."""
    record = TeamRecord(team_key=team_key)
    for match in _only_scored(matches):
        is_home = match.home_key == team_key
        is_away = match.away_key == team_key
        if not (is_home or is_away):
            continue
        own = match.home_goals if is_home else match.away_goals
        opp = match.away_goals if is_home else match.home_goals
        record.matches += 1
        record.goals_for += own
        record.goals_against += opp
        prefix = "home" if is_home else "away"
        if own > opp:
            record.wins += 1
            setattr(record, f"{prefix}_wins", getattr(record, f"{prefix}_wins") + 1)
        elif own == opp:
            record.draws += 1
            setattr(record, f"{prefix}_draws", getattr(record, f"{prefix}_draws") + 1)
        else:
            record.losses += 1
            setattr(record, f"{prefix}_losses", getattr(record, f"{prefix}_losses") + 1)
    return record


def head_to_head(
    matches: list[Match], key_a: str, key_b: str
) -> dict:
    """Head-to-head record between two canonical team keys."""
    played = [
        m
        for m in matches
        if (m.home_key == key_a and m.away_key == key_b)
        or (m.home_key == key_b and m.away_key == key_a)
    ]
    scored = _only_scored(played)
    record_a = TeamRecord(key_a)
    for match in scored:
        own_a = match.home_goals if match.home_key == key_a else match.away_goals
        own_b = match.home_goals if match.home_key == key_b else match.away_goals
        record_a.matches += 1
        record_a.goals_for += own_a
        record_a.goals_against += own_b
        if own_a > own_b:
            record_a.wins += 1
        elif own_a == own_b:
            record_a.draws += 1
        else:
            record_a.losses += 1
    return {
        "matches": sorted(scored, key=lambda m: m.date or date.min),
        "total_meetings": len(scored),
        "team_a": key_a,
        "team_b": key_b,
        "team_a_wins": record_a.wins,
        "team_b_wins": record_a.losses,
        "draws": record_a.draws,
        "team_a_goals": record_a.goals_for,
        "team_b_goals": record_a.goals_against,
    }


def standings(matches: list[Match]) -> list[dict]:
    """Compute a league table (points, W/D/L, goals) from match results."""
    records: dict[str, TeamRecord] = {}
    for match in _only_scored(matches):
        for key in (match.home_key, match.away_key):
            if key not in records:
                records[key] = TeamRecord(team_key=key)
        home, away = records[match.home_key], records[match.away_key]
        home.matches += 1
        away.matches += 1
        home.goals_for += match.home_goals
        home.goals_against += match.away_goals
        away.goals_for += match.away_goals
        away.goals_against += match.home_goals
        if match.home_goals > match.away_goals:
            home.wins += 1
            away.losses += 1
        elif match.home_goals < match.away_goals:
            away.wins += 1
            home.losses += 1
        else:
            home.draws += 1
            away.draws += 1
    table = sorted(
        records.values(),
        key=lambda r: (-r.points, -r.wins, -r.goal_difference, -r.goals_for, r.team_key),
    )
    return [
        {
            "position": i + 1,
            "team": team_display_name(r.team_key),
            "team_key": r.team_key,
            "points": r.points,
            "wins": r.wins,
            "draws": r.draws,
            "losses": r.losses,
            "goals_for": r.goals_for,
            "goals_against": r.goals_against,
            "goal_difference": r.goal_difference,
            "matches": r.matches,
        }
        for i, r in enumerate(table)
    ]


def champion_and_relegated(
    table: list[dict], relegated_count: int = 4
) -> dict:
    return {
        "champion": table[0]["team"] if table else None,
        "runner_up": table[1]["team"] if len(table) > 1 else None,
        "relegated": [row["team"] for row in table[-relegated_count:]]
        if len(table) >= relegated_count
        else [],
    }


def biggest_wins(matches: list[Match], limit: int = 10) -> list[dict]:
    """Matches with the largest goal margins (ties broken by total goals)."""
    scored = _only_scored(matches)
    ranked = sorted(
        scored,
        key=lambda m: (-abs(m.home_goals - m.away_goals), -(m.total_goals or 0)),
    )
    return [
        {
            "date": m.date.isoformat() if m.date else None,
            "home_team": team_display_name(m.home_key),
            "away_team": team_display_name(m.away_key),
            "score": m.score,
            "margin": abs(m.home_goals - m.away_goals),
            "competition": m.competition,
            "season": m.season,
        }
        for m in ranked[:limit]
    ]


def competition_aggregates(matches: list[Match]) -> dict:
    """Average goals and result distribution over a set of matches."""
    scored = _only_scored(matches)
    total = len(scored)
    if total == 0:
        return {
            "matches": 0,
            "avg_goals_per_match": None,
            "home_win_rate_pct": None,
            "draw_rate_pct": None,
            "away_win_rate_pct": None,
        }
    goals = sum(m.total_goals or 0 for m in scored)
    home_wins = sum(1 for m in scored if m.home_goals > m.away_goals)
    draws = sum(1 for m in scored if m.home_goals == m.away_goals)
    away_wins = total - home_wins - draws
    return {
        "matches": total,
        "avg_goals_per_match": round(goals / total, 2),
        "home_win_rate_pct": round(home_wins / total * 100, 1),
        "draw_rate_pct": round(draws / total * 100, 1),
        "away_win_rate_pct": round(away_wins / total * 100, 1),
        "total_goals": goals,
    }


def best_records(
    matches: list[Match],
    metric: str = "points",
    limit: int = 10,
    venue: str = "all",
) -> list[dict]:
    """Rank teams by points, win rate, or goals over the given matches."""
    by_team: dict[str, list[Match]] = defaultdict(list)
    for match in matches:
        if venue == "home" and match.home_key:
            by_team[match.home_key].append(match)
        elif venue == "away" and match.away_key:
            by_team[match.away_key].append(match)
        else:
            if match.home_key:
                by_team[match.home_key].append(match)
            if match.away_key:
                by_team[match.away_key].append(match)
    records = [team_record(ms, key) for key, ms in by_team.items()]
    if metric == "goals":
        records.sort(key=lambda r: (-r.goals_for, -r.matches))
    elif metric in {"win_rate", "win rate"}:
        records.sort(key=lambda r: (-(r.win_rate or 0), -r.matches))
    else:
        records.sort(key=lambda r: (-r.points, -r.goal_difference))
    return [
        {
            **r.to_dict(),
            "team": team_display_name(r.team_key),
            "team_key": r.team_key,
        }
        for r in records[:limit]
    ]


def derby_matches(matches: list[Match], season: int | None = None) -> list[dict]:
    """Matches between classic Brazilian rival pairs, optionally by season."""
    derby_keys = {
        frozenset((a, b)): name for a, b, name in DERBY_PAIRS
    }
    results = []
    for match in matches:
        pair = frozenset((match.home_key, match.away_key))
        name = derby_keys.get(pair)
        if not name:
            continue
        if season is not None and match.season != season:
            continue
        results.append(
            {
                "derby": name,
                "date": match.date.isoformat() if match.date else None,
                "home_team": team_display_name(match.home_key),
                "away_team": team_display_name(match.away_key),
                "score": match.score,
                "competition": match.competition,
                "season": match.season,
            }
        )
    results.sort(key=lambda r: (r["date"] or "", r["derby"]))
    return results


def finals(matches: list[Match]) -> list[Match]:
    """Final-round matches: Libertadores stage 'final' and cup round 'Final'."""
    return [
        m
        for m in matches
        if (m.stage and m.stage.strip().lower() == "final")
        or (m.round and m.round.strip().lower() == "final")
    ]
