"""
================================================================================
brazil_soccer_mcp.formatting
================================================================================
Context:
    Renders query results from the knowledge graph into the human-readable text
    blocks shown in the specification's "Example answer format" sections. The
    MCP tools call these so an LLM receives clean, consistent prose rather than
    raw structures.

Each renderer takes already-computed data (the graph does the work) plus the
KnowledgeGraph for display-name lookups, and returns a string.
================================================================================
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .graph import KnowledgeGraph, TeamRecord
from .loaders import Match, Player


def _score(m: Match) -> str:
    h = "?" if m.home_goal is None else str(m.home_goal)
    a = "?" if m.away_goal is None else str(m.away_goal)
    return f"{h}-{a}"


def _round_label(m: Match) -> str:
    parts = [m.competition]
    if m.stage:
        parts.append(m.stage.title())
    elif m.round:
        parts.append(f"Round {m.round}")
    if m.season:
        parts.append(str(m.season))
    return " ".join(parts)


def format_match_line(m: Match) -> str:
    d = m.date.isoformat() if m.date else "unknown date"
    return f"- {d}: {m.home} {_score(m)} {m.away} ({_round_label(m)})"


def format_matches(
    graph: KnowledgeGraph,
    matches: List[Match],
    title: Optional[str] = None,
    show: int = 15,
    head_to_head: Optional[dict] = None,
) -> str:
    if not matches:
        return (title + "\n" if title else "") + "No matches found."
    lines: List[str] = []
    if title:
        lines.append(title)
    for m in matches[:show]:
        lines.append(format_match_line(m))
    if len(matches) > show:
        lines.append(f"- ... ({len(matches) - show} more matches in dataset)")
    if head_to_head:
        h = head_to_head
        lines.append("")
        lines.append(
            f"Head-to-head in dataset: {h['team_a']} {h['a_wins']} wins, "
            f"{h['team_b']} {h['b_wins']} wins, {h['draws']} draws "
            f"(goals {h['a_goals']}-{h['b_goals']})"
        )
    return "\n".join(lines)


def format_team_record(
    team: str, rec: TeamRecord, scope: str = ""
) -> str:
    header = f"{team} record{(' (' + scope + ')') if scope else ''}:"
    return "\n".join(
        [
            header,
            f"- Matches: {rec.matches}",
            f"- Wins: {rec.wins}, Draws: {rec.draws}, Losses: {rec.losses}",
            f"- Goals For: {rec.goals_for}, Goals Against: {rec.goals_against} "
            f"(diff {rec.goal_difference:+d})",
            f"- Points: {rec.points}",
            f"- Win rate: {rec.win_rate * 100:.1f}%",
        ]
    )


def format_head_to_head(graph: KnowledgeGraph, h: dict, show: int = 10) -> str:
    lines = [f"{h['team_a']} vs {h['team_b']} head-to-head:"]
    played = [m for m in h["meetings"] if m.home_goal is not None]
    for m in played[-show:]:
        lines.append(format_match_line(m))
    if len(played) > show:
        lines.append(f"- ... ({len(played) - show} earlier meetings)")
    lines.append("")
    lines.append(
        f"Total: {h['team_a']} {h['a_wins']}W, {h['team_b']} {h['b_wins']}W, "
        f"{h['draws']} draws. Goals: {h['a_goals']}-{h['b_goals']} "
        f"over {len(played)} decided matches."
    )
    return "\n".join(lines)


def format_standings(
    graph: KnowledgeGraph,
    competition: str,
    season: int,
    rows: List[Tuple[str, TeamRecord]],
    show: int = 20,
) -> str:
    if not rows:
        return f"No standings available for {competition} {season}."
    lines = [f"{season} {competition} Standings (calculated from matches):"]
    for i, (key, rec) in enumerate(rows[:show], start=1):
        tag = " - Champion" if i == 1 else ""
        lines.append(
            f"{i}. {graph.team_display(key)} - {rec.points} pts "
            f"({rec.wins}W, {rec.draws}D, {rec.losses}L)"
            f"{tag}"
        )
    return "\n".join(lines)


def format_players(
    players: List[Player], title: Optional[str] = None, show: int = 15
) -> str:
    if not players:
        return (title + "\n" if title else "") + "No players found."
    lines: List[str] = []
    if title:
        lines.append(title)
    for i, p in enumerate(players[:show], start=1):
        bits = [f"Overall: {p.overall}"] if p.overall is not None else []
        if p.position:
            bits.append(f"Position: {p.position}")
        if p.club:
            bits.append(f"Club: {p.club}")
        if p.nationality:
            bits.append(f"Nationality: {p.nationality}")
        lines.append(f"{i}. {p.name} - " + ", ".join(bits))
    if len(players) > show:
        lines.append(f"... ({len(players) - show} more)")
    return "\n".join(lines)


def format_player_detail(p: Player) -> str:
    return "\n".join(
        [
            f"{p.name}",
            f"- Age: {p.age}  Nationality: {p.nationality}",
            f"- Club: {p.club}  Position: {p.position}  "
            f"Jersey: {p.jersey or 'n/a'}",
            f"- Overall: {p.overall}  Potential: {p.potential}",
            f"- Height: {p.height}  Weight: {p.weight}",
        ]
    )


def format_aggregate(stats: dict, label: str) -> str:
    return "\n".join(
        [
            f"Aggregate statistics ({label}):",
            f"- Matches: {stats['matches']}",
            f"- Total goals: {stats['total_goals']}",
            f"- Average goals per match: {stats['avg_goals_per_match']}",
            f"- Home win rate: {stats['home_win_rate'] * 100:.1f}%",
            f"- Away win rate: {stats['away_win_rate'] * 100:.1f}%",
            f"- Draw rate: {stats['draw_rate'] * 100:.1f}%",
        ]
    )


def format_biggest_wins(matches: List[Match], label: str) -> str:
    if not matches:
        return f"No matches found for {label}."
    lines = [f"Biggest victories ({label}):"]
    for i, m in enumerate(matches, start=1):
        margin = abs((m.home_goal or 0) - (m.away_goal or 0))
        lines.append(
            f"{i}. {m.date.isoformat() if m.date else '?'}: "
            f"{m.home} {_score(m)} {m.away} "
            f"({m.competition}{(' ' + str(m.season)) if m.season else ''}, "
            f"margin {margin})"
        )
    return "\n".join(lines)


def format_best_record(
    graph: KnowledgeGraph,
    rows: List[Tuple[str, TeamRecord]],
    label: str,
    show: int = 10,
) -> str:
    if not rows:
        return f"No records found for {label}."
    lines = [f"Best records ({label}):"]
    for i, (key, rec) in enumerate(rows[:show], start=1):
        lines.append(
            f"{i}. {graph.team_display(key)} - win rate "
            f"{rec.win_rate * 100:.1f}% "
            f"({rec.wins}W, {rec.draws}D, {rec.losses}L in {rec.matches})"
        )
    return "\n".join(lines)
