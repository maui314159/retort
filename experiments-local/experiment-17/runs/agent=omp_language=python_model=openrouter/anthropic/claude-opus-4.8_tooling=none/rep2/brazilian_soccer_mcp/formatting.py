"""
Context
=======
Module: brazilian_soccer_mcp.formatting
Purpose: Render the structured dicts/lists returned by :class:`KnowledgeBase`
         into the human-readable text blocks shown in the spec's "Example answer
         format" sections. MCP tools return these strings so the connected LLM
         receives ready-to-quote prose.

These functions are pure (structured input -> str) and never touch the data
layer, keeping rendering independently testable.
"""

from __future__ import annotations

from typing import Any


def _score_line(m: dict[str, Any]) -> str:
    stage = f" ({m['competition']}" + (f" {m['stage']}" if m.get("stage") else "") + ")"
    date = m.get("date") or "????-??-??"
    return (
        f"- {date}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
        f"{m['away_team']}{stage}"
    )


def format_matches(matches: list[dict[str, Any]], title: str | None = None) -> str:
    if not matches:
        return "No matches found for the given criteria."
    lines = []
    if title:
        lines.append(title)
    lines.extend(_score_line(m) for m in matches)
    return "\n".join(lines)


def format_head_to_head(h2h: dict[str, Any]) -> str:
    if h2h["matches"] == 0:
        return f"No matches found between {h2h['team_a']} and {h2h['team_b']}."
    lines = [
        f"{h2h['team_a']} vs {h2h['team_b']} — head-to-head in dataset:",
        *[_score_line(m) for m in h2h["fixtures"]],
    ]
    extra = h2h["matches"] - len(h2h["fixtures"])
    if extra > 0:
        lines.append(f"- ... ({extra} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Record: {h2h['team_a']} {h2h['team_a_wins']} wins, "
        f"{h2h['team_b']} {h2h['team_b_wins']} wins, {h2h['draws']} draws "
        f"(goals {h2h['team_a_goals']}-{h2h['team_b_goals']})"
    )
    return "\n".join(lines)


def format_team_stats(s: dict[str, Any]) -> str:
    scope = []
    if s.get("season") is not None:
        scope.append(str(s["season"]))
    if s.get("competition"):
        scope.append(s["competition"])
    venue = "" if s["venue"] == "all" else f" {s['venue']}"
    header = f"{s['team']}{venue} record"
    if scope:
        header += f" ({' '.join(scope)})"
    return "\n".join([
        f"{header}:",
        f"- Matches: {s['matches']}",
        f"- Wins: {s['wins']}, Draws: {s['draws']}, Losses: {s['losses']}",
        f"- Goals For: {s['goals_for']}, Goals Against: {s['goals_against']} "
        f"(GD {s['goal_difference']:+d})",
        f"- Points: {s['points']}",
        f"- Win rate: {s['win_rate']}%",
    ])


def format_players(players: list[dict[str, Any]], title: str | None = None) -> str:
    if not players:
        return "No players found for the given criteria."
    lines = [title] if title else []
    for i, p in enumerate(players, 1):
        lines.append(
            f"{i}. {p['name']} - Overall: {p['overall']}, "
            f"Position: {p['position']}, Club: {p['club']}"
            + (f", Nationality: {p['nationality']}" if p.get("nationality") else "")
        )
    return "\n".join(lines)


def format_club_summary(rows: list[dict[str, Any]], nationality: str) -> str:
    if not rows:
        return f"No {nationality} players found."
    lines = [f"{nationality} players by club:"]
    for r in rows:
        lines.append(f"- {r['club']}: {r['players']} players (avg rating: {r['avg_overall']})")
    return "\n".join(lines)


def format_standings(rows: list[dict[str, Any]], competition: str, season: int) -> str:
    if not rows:
        return f"No data for {competition} {season}."
    lines = [f"{season} {competition} standings (calculated from matches):"]
    for r in rows:
        tag = " - Champion" if r["position"] == 1 else ""
        lines.append(
            f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L) "
            f"GF {r['goals_for']} GA {r['goals_against']}{tag}"
        )
    return "\n".join(lines)


def format_competitions(rows: list[dict[str, Any]], team: str) -> str:
    if not rows:
        return f"No competitions found for {team}."
    lines = [f"Competitions {team} has played in (provided data):"]
    for r in rows:
        seasons = r["seasons"]
        span = f"{seasons[0]}-{seasons[-1]}" if len(seasons) > 1 else str(seasons[0])
        lines.append(f"- {r['competition']}: {r['matches']} matches ({span})")
    return "\n".join(lines)


def format_competition_stats(s: dict[str, Any]) -> str:
    if s["matches"] == 0:
        return "No matches found for the given criteria."
    scope = []
    if s.get("competition"):
        scope.append(s["competition"])
    if s.get("season") is not None:
        scope.append(str(s["season"]))
    header = "Statistics" + (f" — {' '.join(scope)}" if scope else "")
    return "\n".join([
        f"{header}:",
        f"- Matches: {s['matches']}",
        f"- Total goals: {s['total_goals']}",
        f"- Average goals per match: {s['avg_goals_per_match']}",
        f"- Home win rate: {s['home_win_rate']}%",
        f"- Away win rate: {s['away_win_rate']}%",
        f"- Draw rate: {s['draw_rate']}%",
    ])


def format_biggest_wins(rows: list[dict[str, Any]], title: str | None = None) -> str:
    if not rows:
        return "No matches found for the given criteria."
    lines = [title or "Biggest victories (provided data):"]
    for i, m in enumerate(rows, 1):
        lines.append(
            f"{i}. {m['date']}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({m['competition']}, margin {m['margin']})"
        )
    return "\n".join(lines)


def format_top_scoring(rows: list[dict[str, Any]], title: str | None = None) -> str:
    if not rows:
        return "No matches found for the given criteria."
    lines = [title or "Top scoring teams (provided data):"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['team']} - {r['goals']} goals in {r['matches']} matches")
    return "\n".join(lines)
