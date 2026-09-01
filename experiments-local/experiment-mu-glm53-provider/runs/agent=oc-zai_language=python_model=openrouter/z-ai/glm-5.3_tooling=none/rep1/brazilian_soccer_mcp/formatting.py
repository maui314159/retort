"""
Rendering of query results into the human-readable answer formats from TASK.md.

Context (Why): TASK.md shows exact "Example answer format" blocks for match
queries, team queries, player queries, competition queries and statistical
analysis. MCP tools return text to the LLM, so results should arrive
pre-formatted in that style - the LLM can then quote or lightly rephrase
them when answering natural-language questions.

What: one ``format_*`` function per result type from service.py. All output
is plain text with simple line structure, dates as YYYY-MM-DD, and scores in
"Home 2-1 Away" form. Truncation is always announced ("... (N more matches
in dataset)") exactly like the spec examples.

Test: tests/test_*_queries.py assert key substrings of the formatted output;
tests/test_server.py checks the MCP tools emit them end-to-end.
Spec reference: every "Example answer format" block in TASK.md.
"""

from __future__ import annotations

from typing import Optional

from .models import Match, Player, TeamRecord
from .normalizer import DERBIES
from .service import (
    CompetitionStats,
    HeadToHead,
    MatchSearchResult,
    SquadResult,
    Standings,
    TeamStats,
)

MAX_LISTED = 15  # how many lines to show before "... (N more)"


def _clip(items: list[str], total: int) -> str:
    """Join lines, appending the spec's ellipsis when truncated."""
    shown = items[:MAX_LISTED]
    text = "\n".join(shown)
    if total > len(shown):
        text += f"\n... ({total - len(shown)} more in dataset)"
    return text


def format_match_line(match: Match) -> str:
    """"- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A Round 22)"."""
    line = f"- {match.date_str()}: {match.home_display} {match.score_str()} {match.away_display}"
    detail = match.detail_label()
    return f"{line} ({detail})" if detail else line


def format_match_search(result: MatchSearchResult) -> str:
    """Match listing, in the style of the 'Fla-Flu' example in TASK.md."""
    title_parts: list[str] = []
    if result.team and result.opponent:
        derby = next(
            (
                name
                for a, b, name in DERBIES
                if {a, b} == {result.team.team_id, result.opponent.team_id}
            ),
            None,
        )
        label = f"{result.team.display} vs {result.opponent.display}"
        if derby:
            label += f" ({derby})"
        title_parts.append(label)
    elif result.team:
        title_parts.append(f"Matches involving {result.team.display}")
    elif result.opponent:
        title_parts.append(f"Matches involving {result.opponent.display}")
    else:
        title_parts.append("Matches")

    lines = [format_match_line(m) for m in result.matches]
    body = _clip(lines, result.total)
    head = title_parts[0]
    if not lines:
        return f"{head}: no matches found in the dataset."
    return f"{head}:\n{body}"


def format_head_to_head(h2h: HeadToHead) -> str:
    """Match list + 'Head-to-head in dataset: A X wins, B Y wins, Z draws'."""
    a, b = h2h.team_a, h2h.team_b
    derby = next(
        (name for x, y, name in DERBIES if {x, y} == {a.team_id, b.team_id}), None
    )
    title = f"{a.display} vs {b.display}" + (f" ({derby})" if derby else "")
    scope = []
    if h2h.competition:
        scope.append(h2h.competition)
    if h2h.season:
        scope.append(str(h2h.season))
    if scope:
        title += f" - {' '.join(scope)}"

    if not h2h.matches:
        return f"{title}: no matches between these teams in the dataset."

    lines = [format_match_line(m) for m in h2h.matches]
    body = _clip(lines, len(h2h.matches))
    summary = (
        f"Head-to-head in dataset: {a.display} {h2h.a_wins} wins, "
        f"{b.display} {h2h.b_wins} wins, {h2h.draws} draws"
        f" (goals: {a.display} {h2h.a_goals}, {b.display} {h2h.b_goals})"
    )
    return f"{title}:\n{body}\n\n{summary}"


def format_team_stats(stats: TeamStats) -> str:
    """Corinthians-style record block from TASK.md section 2."""
    record: TeamRecord = stats.record
    scope = []
    if stats.season:
        scope.append(str(stats.season))
    if stats.competition:
        scope.append(stats.competition)
    venue_label = {"all": "", "home": "home ", "away": "away "}[stats.venue]
    title = f"{stats.team.display} {venue_label}record"
    if scope:
        title += f" ({' '.join(scope)})"

    lines = [
        f"- Matches: {record.matches}",
        f"- Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}",
        f"- Goals For: {record.goals_for}, Goals Against: {record.goals_against}",
        f"- Points: {record.points}",
    ]
    if record.matches:
        lines.append(f"- Win rate: {record.win_rate * 100:.1f}%")
    else:
        return f"{title}: no matches found in the dataset."

    if stats.venue == "all" and stats.home_record and stats.away_record:
        h, a = stats.home_record, stats.away_record
        if h.matches or a.matches:
            lines.append(
                f"- Split: home {h.wins}W {h.draws}D {h.losses}L / "
                f"away {a.wins}W {a.draws}D {a.losses}L"
            )
    return f"{title}:\n" + "\n".join(lines)


def format_standings(table: Standings, relegation_zone: int = 4) -> str:
    """'2019 Brasileirão Final Standings (calculated from matches)' block."""
    if not table.table:
        scope = f"{table.season or ''} {table.competition}".strip()
        return f"No standings could be calculated for {scope}."

    season = f"{table.season} " if table.season else ""
    title = f"{season}{table.competition} Standings (calculated from matches):"
    lines = []
    total = len(table.table)
    for idx, row in enumerate(table.table, start=1):
        line = (
            f"{idx}. {row.display} - {row.points} pts "
            f"({row.wins}W, {row.draws}D, {row.losses}L, "
            f"GF {row.goals_for}, GA {row.goals_against})"
        )
        if idx == 1:
            line += " - Champion"
        elif idx > total - relegation_zone:
            line += " - Relegation zone"
        lines.append(line)
    body = title + "\n" + _clip(lines, len(lines))
    matches_played = sum(r.matches for r in table.table) // 2
    if table.season and matches_played:
        full = {20: 380, 22: 420, 24: 552}  # teams -> full double round-robin
        expected = full.get(total)
        if expected and matches_played < expected:
            body += (
                f"\nNote: based on {matches_played} played matches in the dataset "
                f"(a complete {total}-team season has {expected}); "
                "later rounds were not recorded."
            )
    return body


def format_competition_stats(stats: CompetitionStats) -> str:
    """Aggregate stats block from TASK.md section 5."""
    scope = " ".join(
        part for part in [str(stats.season or ""), stats.competition or "all competitions"] if part
    )
    if not stats.matches:
        return f"No played matches found for {scope}."
    lines = [
        f"Statistics for {scope}:",
        f"- Matches: {stats.matches}",
        f"- Goals: {stats.goals}",
        f"- Average goals per match: {stats.avg_goals}",
        f"- Home win rate: {stats.home_win_rate}%",
        f"- Draw rate: {stats.draw_rate}%",
        f"- Away win rate: {stats.away_win_rate}%",
    ]
    return "\n".join(lines)


def format_biggest_wins(matches: list[Match], scope: Optional[str] = None) -> str:
    """Numbered 'biggest victories' list from TASK.md section 5."""
    if not matches:
        return "No played matches found" + (f" for {scope}" if scope else "") + "."
    title = f"Biggest victories {scope or 'in the dataset'}:"
    lines = [
        f"{i}. {m.date_str()}: {m.home_display} {m.score_str()} {m.away_display} ({m.competition})"
        for i, m in enumerate(matches, start=1)
    ]
    return title + "\n" + _clip(lines, len(matches))


def format_best_records(records: list[TeamRecord], venue: str, scope: str) -> str:
    if not records:
        return f"No teams with enough matches found for {scope}."
    lines = [f"Best {venue} records {scope}:"]
    for i, r in enumerate(records, start=1):
        lines.append(
            f"{i}. {r.display} - {r.win_rate * 100:.1f}% win rate "
            f"({r.wins}W {r.draws}D {r.losses}L in {r.matches} {venue} matches)"
        )
    return "\n".join(lines[:16])


def format_player(p: Player, rank: Optional[int] = None) -> str:
    """'1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain'."""
    prefix = f"{rank}. " if rank else ""
    return (
        f"{prefix}{p.name} - Overall: {p.overall}, Position: {p.position}, "
        f"Club: {p.club or 'free agent'}, Age: {p.age}, "
        f"Nationality: {p.nationality}"
    )


def format_players(players: list[Player], title: str) -> str:
    if not players:
        return f"{title}: no players found."
    lines = [format_player(p, rank=i) for i, p in enumerate(players, start=1)]
    return f"{title}:\n" + _clip(lines, len(players))


def format_squad(squad: SquadResult) -> str:
    if not squad.in_fifa:
        return (
            f"No FIFA squad data for {squad.team.display} in this dataset "
            "(the FIFA snapshot covers only some Brazilian clubs)."
        )
    title = f"{squad.team.display} squad (FIFA dataset, {len(squad.players)} players):"
    avg = (
        round(sum(p.overall or 0 for p in squad.players) / len(squad.players), 1)
        if squad.players
        else None
    )
    lines = [format_player(p, rank=i) for i, p in enumerate(squad.players, start=1)]
    body = _clip(lines, len(squad.players))
    if avg is not None:
        body += f"\nAverage overall rating: {avg}"
    return f"{title}\n{body}"


def format_brazilians_at_clubs(rows: list[tuple[str, int, float]]) -> str:
    if not rows:
        return "No Brazilian players at Brazilian clubs found."
    lines = [f"- {club}: {count} players (avg rating: {avg})" for club, count, avg in rows]
    return "Brazilian players at Brazilian clubs (FIFA dataset):\n" + "\n".join(lines)


def format_derbies(derbies: list[tuple[str, Match]]) -> str:
    if not derbies:
        return "No derby matches found for the requested filter."
    lines = [f"- [{name}] {format_match_line(m)[2:]}" for name, m in derbies]
    return f"Derby matches ({len(derbies)}):\n" + _clip(lines, len(derbies))


def format_relegated(records: list[TeamRecord], competition: str, season: Optional[int]) -> str:
    if not records:
        return f"No standings found for {competition} {season or ''}".strip()
    season_txt = f" {season}" if season else ""
    lines = [
        f"{i}. {r.display} - {r.points} pts ({r.wins}W, {r.draws}D, {r.losses}L)"
        for i, r in enumerate(records, start=1)
    ]
    return f"Relegation zone, {competition}{season_txt}:\n" + "\n".join(lines)
