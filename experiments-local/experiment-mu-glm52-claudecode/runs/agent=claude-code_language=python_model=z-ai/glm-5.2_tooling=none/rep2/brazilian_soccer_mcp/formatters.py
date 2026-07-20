"""Human-readable text formatters for query results.

Context
-------
TASK.md gives "example answer format" blocks for each query category.  These
functions turn the structured dicts returned by ``queries.SoccerQueries`` into
the multi-line text blocks the spec shows, so an LLM (or a human reading the
MCP tool output) gets nicely formatted answers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def format_match_list(
    matches: List[Dict[str, Any]],
    title: Optional[str] = None,
    show_count: int = 5,
) -> str:
    """Render a list of matches like the spec's "Fla-Flu derby" example."""
    if not matches:
        return (title or "No matches") + ":\n(none found in dataset)"
    lines: List[str] = []
    if title:
        lines.append(title)
    for m in matches[:show_count]:
        date = m.get("date") or "?"
        lines.append(
            f"- {date}: {m['home_team']} {m.get('score', '?')} {m['away_team']} "
            f"({m.get('competition', '?')}"
            + (f" Round {m['round']}" if m.get("round") else "")
            + (f", stage {m['stage']}" if m.get("stage") else "")
            + ")"
        )
    remaining = len(matches) - show_count
    if remaining > 0:
        lines.append(f"- ... ({remaining} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(h2h: Dict[str, Any]) -> str:
    """Render a head-to-head summary line."""
    return (
        f"Head-to-head in dataset: {h2h['team_a']} {h2h['team_a_wins']} wins, "
        f"{h2h['team_b']} {h2h['team_b_wins']} wins, {h2h['draws']} draws"
    )


def format_team_stats(stats: Dict[str, Any]) -> str:
    """Render team statistics like the spec's "Corinthians home record" example."""
    venue = stats.get("venue")
    venue_label = f" {venue} record" if venue else " record"
    season_part = f" ({stats['season']})" if stats.get("season") else ""
    comp_part = f" {stats['competition']}" if stats.get("competition") else ""
    header = f"{stats['team']}{venue_label}{season_part}{comp_part}"
    if stats["matches"] == 0:
        return header + ":\n(no matches in dataset for this filter)"
    win_rate_pct = round(stats["win_rate"] * 100, 1)
    return (
        f"{header}:\n"
        f"- Matches: {stats['matches']}\n"
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}\n"
        f"- Win rate: {win_rate_pct}%"
    )


def format_player_list(
    players: List[Dict[str, Any]],
    title: Optional[str] = None,
    show_count: int = 10,
) -> str:
    """Render a numbered list of players (rating / position / club)."""
    lines: List[str] = []
    if title:
        lines.append(title)
    for i, p in enumerate(players[:show_count], start=1):
        lines.append(
            f"{i}. {p['name']} - Overall: {p.get('overall', '?')}, "
            f"Position: {p.get('position', '?')}, Club: {p.get('club', '?')}"
        )
    remaining = len(players) - show_count
    if remaining > 0:
        lines.append(f"... ({remaining} more players)")
    return "\n".join(lines)


def format_standings(rows: List[Dict[str, Any]], competition: str, season: int) -> str:
    """Render a standings table with a champion marker on row 1."""
    if not rows:
        return f"{competition} {season}: (no matches in dataset)"
    lines = [f"{competition} {season} Standings (calculated from matches):"]
    for r in rows:
        champ = " - Champion" if r.get("position") == 1 else ""
        gd = r["goals_for"] - r["goals_against"]
        lines.append(
            f"{r['position']}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L, GD {gd:+d}){champ}"
        )
    return "\n".join(lines)


def format_biggest_wins(wins: List[Dict[str, Any]]) -> str:
    """Render the "biggest victories" example block."""
    if not wins:
        return "Biggest victories:\n(none found)"
    lines = ["Biggest victories in dataset:"]
    for i, w in enumerate(wins, start=1):
        lines.append(
            f"{i}. {w['date'] or '?'}: {w['winner']} {w['score']} {w['loser']} "
            f"({w['competition']}, margin {w['margin']})"
        )
    return "\n".join(lines)


def format_average_goals(stats: Dict[str, Any]) -> str:
    """Render the "average goals per match" example block."""
    return (
        f"Average goals per match: {stats['average_goals_per_match']}\n"
        f"Home win rate: {round(stats['home_win_rate'] * 100, 1)}%\n"
        f"Away win rate: {round(stats['away_win_rate'] * 100, 1)}%\n"
        f"Draw rate: {round(stats['draw_rate'] * 100, 1)}%\n"
        f"Matches: {stats['matches']}"
    )
