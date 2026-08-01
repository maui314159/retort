"""Render structured query results as LLM-friendly plain text.

The formats follow the examples in the specification (score lines,
head-to-head summaries, standings tables, ...).
"""

from __future__ import annotations

from typing import Any


def match_line(m: dict[str, Any]) -> str:
    score = (
        f"{m['home_goals']}-{m['away_goals']}"
        if m.get("home_goals") is not None
        else "vs (scheduled)"
    )
    comp = m.get("competition") or ""
    detail = comp
    if m.get("stage"):
        detail += f" {m['stage']}"
    elif m.get("round"):
        detail += f" Round {m['round']}"
    date = m.get("date") or "unknown date"
    return f"- {date}: {m['home_team']} {score} {m['away_team']} ({detail.strip()})"


def format_matches(result: dict[str, Any], title: str | None = None) -> str:
    lines = [title] if title else []
    if not result["matches"]:
        lines.append("No matches found.")
        return "\n".join(lines)
    for m in result["matches"]:
        lines.append(match_line(m))
    remaining = result["total"] - len(result["matches"])
    if remaining > 0:
        lines.append(f"... ({remaining} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(result: dict[str, Any]) -> str:
    t1, t2 = result["team1"], result["team2"]
    derby = f" ({result['derby']} derby)" if result.get("derby") else ""
    title = f"{t1} vs {t2}{derby}:"
    text = format_matches(
        {"matches": result["matches"], "total": result["total_matches"]}, title
    )
    summary = (
        f"\nHead-to-head in dataset: {t1} {result['team1_wins']} wins, "
        f"{t2} {result['team2_wins']} wins, {result['draws']} draws "
        f"(goals: {result['team1_goals']}-{result['team2_goals']})"
    )
    return text + summary


def format_team_stats(stats: dict[str, Any]) -> str:
    venue = {"home": " home", "away": " away"}.get(stats.get("venue"), "")
    scope = " ".join(
        str(x) for x in (stats.get("season"), stats.get("competition")) if x
    )
    lines = [
        f"{stats['team']}{venue} record ({scope}):",
        f"- Matches: {stats['matches']}",
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}",
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}",
        f"- Win rate: {stats['win_rate']}%",
    ]
    return "\n".join(lines)


def format_standings(result: dict[str, Any]) -> str:
    lines = [
        f"{result['season']} {result['competition']} Standings "
        f"(calculated from {result['matches']} matches):"
    ]
    for row in result["standings"]:
        flags = ""
        if row.get("champion"):
            flags = " - Champion"
        elif row.get("relegated"):
            flags = " - Relegated"
        lines.append(
            f"{row['position']:>2}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L) "
            f"GD {row['goal_difference']:+d}{flags}"
        )
    return "\n".join(lines)


def format_players(result: dict[str, Any], title: str) -> str:
    lines = [title]
    if not result["players"]:
        lines.append("No players found.")
        return "\n".join(lines)
    for i, p in enumerate(result["players"], start=1):
        lines.append(
            f"{i}. {p['name']} - Overall: {p['overall']}, "
            f"Position: {p['position']}, Club: {p['club']}, "
            f"Nationality: {p['nationality']}"
        )
    if result["total"] > len(result["players"]):
        lines.append(f"... ({result['total'] - len(result['players'])} more players)")
    return "\n".join(lines)


def format_player_profile(p: dict[str, Any]) -> str:
    lines = [
        f"{p['name']} ({p['nationality']})",
        f"- Club: {p['club']}, Position: {p['position']}, Age: {p['age']}",
        f"- Overall: {p['overall']}, Potential: {p['potential']}",
    ]
    if p.get("jersey_number") is not None:
        lines.append(f"- Jersey: #{p['jersey_number']}")
    if p.get("preferred_foot"):
        lines.append(f"- Preferred foot: {p['preferred_foot']}")
    if p.get("skills"):
        top = sorted(p["skills"].items(), key=lambda kv: -kv[1])[:6]
        lines.append("- Top skills: " + ", ".join(f"{k} {v}" for k, v in top))
    return "\n".join(lines)


def format_competition_stats(stats: dict[str, Any]) -> str:
    season = f" {stats['season']}" if stats.get("season") else ""
    return "\n".join([
        f"{stats['competition']}{season} statistics:",
        f"- Matches: {stats['matches']}",
        f"- Total goals: {stats['total_goals']}",
        f"- Average goals per match: {stats['avg_goals_per_match']}",
        f"- Home win rate: {stats['home_win_rate']}%",
        f"- Draw rate: {stats['draw_rate']}%",
        f"- Away win rate: {stats['away_win_rate']}%",
    ])


def format_top_scoring(result: dict[str, Any], title: str) -> str:
    lines = [title]
    for i, t in enumerate(result["teams"], start=1):
        lines.append(
            f"{i}. {t['team']} - {t['goals']} goals in {t['matches']} matches "
            f"({t['goals_per_match']} per match)"
        )
    if not result["teams"]:
        lines.append("No data.")
    return "\n".join(lines)


def format_biggest_wins(result: dict[str, Any], title: str) -> str:
    lines = [title]
    for i, m in enumerate(result["matches"], start=1):
        comp = m.get("competition") or ""
        lines.append(
            f"{i}. {m['date']}: {m['home_team']} {m['home_goals']}-"
            f"{m['away_goals']} {m['away_team']} ({comp})"
        )
    if not result["matches"]:
        lines.append("No matches found.")
    return "\n".join(lines)


def format_records(result: dict[str, Any], title: str) -> str:
    lines = [title]
    for i, t in enumerate(result["teams"], start=1):
        lines.append(
            f"{i}. {t['team']} - {t['win_rate']}% win rate "
            f"({t['wins']}W {t['draws']}D {t['losses']}L, "
            f"{t['goals_for']} GF / {t['goals_against']} GA)"
        )
    if not result["teams"]:
        lines.append("No data.")
    return "\n".join(lines)
