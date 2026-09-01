"""Render analysis results as the human-readable answer format from the spec.

Each function takes a result object from :mod:`brazilian_soccer.analysis`
and returns plain text shaped like the examples in the specification::

    Flamengo vs Fluminense (Fla-Flu derby):
    - 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)
    ...
    Head-to-head in dataset: Flamengo 12 wins, Fluminense 8 wins, 7 draws
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from .analysis import (
    CupFinalResult,
    DerbyResult,
    HeadToHeadResult,
    MatchSearchResult,
    PlayerSearchResult,
    TeamProfileResult,
    TeamStatsResult,
)
from .models import Match, Player

__all__ = [
    "format_match",
    "format_matches",
    "format_search_matches",
    "format_head_to_head",
    "format_last_match",
    "format_team_stats",
    "format_team_profile",
    "format_players",
    "format_player_details",
    "format_standings",
    "format_champion",
    "format_finals",
    "format_biggest_wins",
    "format_competition_stats",
    "format_best_records",
    "format_derbies",
    "format_compare_seasons",
    "format_team_search",
    "format_competitions",
]


def _date(m: Match) -> str:
    return m.date.isoformat() if m.date else "unknown date"


def format_match(m: Match, index: Optional[int] = None) -> str:
    """One line per match: '- 2023-09-03: Flamengo 2-1 Fluminense (Comp Stage)'."""
    parts = [f"{_date(m)}: {m.score}"]
    bits = [m.competition]
    if m.stage:
        bits.append(m.stage)
    elif m.season is not None:
        bits.append(f"season {m.season}")
    parts.append(f"({', '.join(bits)})")
    line = "- " + " ".join(parts)
    if m.stadium:
        line += f" [{m.stadium}]"
    return line


def _match_lines(matches: Iterable[Match]) -> list[str]:
    return [format_match(m) for m in matches]


def format_matches(
    matches: Iterable[Match],
    total: int,
    header: str,
    shown: Optional[int] = None,
) -> str:
    """A header, then match lines, then a '(N more...)' note."""
    lines = [f"{header}:"] if not header.endswith(":") else [header]
    match_list = list(matches)
    lines.extend(_match_lines(match_list))
    shown = shown if shown is not None else len(match_list)
    if total > shown:
        lines.append(f"... ({total - shown} more matches in dataset)")
    return "\n".join(lines)


def format_search_matches(result: MatchSearchResult) -> str:
    title_bits: list[str] = []
    if result.team and result.opponent:
        title_bits.append(f"{result.team.display} vs {result.opponent.display}")
    elif result.team:
        title_bits.append(result.team.display)
    elif result.opponent:
        title_bits.append(result.opponent.display)
    else:
        title_bits.append("Matches")
    if result.competition_id:
        from .loader import COMPETITION_DISPLAY

        title_bits.append(COMPETITION_DISPLAY[result.competition_id])
    if result.season is not None:
        title_bits.append(f"season {result.season}")
    if result.date_from or result.date_to:
        frm = result.date_from.isoformat() if result.date_from else "beginning"
        to = result.date_to.isoformat() if result.date_to else "now"
        title_bits.append(f"from {frm} to {to}")
    header = " ".join(title_bits)
    if result.total == 0:
        return f"{header}: no matches found in the dataset."
    lines = [f"{header} ({result.total} matches in dataset):"]
    lines.extend(_match_lines(result.matches))
    if result.truncated:
        lines.append(f"... ({result.total - len(result.matches)} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(result: HeadToHeadResult) -> str:
    a, b = result.team_a.display, result.team_b.display
    if result.total == 0:
        return f"{a} vs {b}: no matches between these teams in the dataset."
    lines = [f"{a} vs {b} (head-to-head):"]
    lines.extend(_match_lines(result.matches))
    if result.total > len(result.matches):
        lines.append(f"... ({result.total - len(result.matches)} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {a} {result.wins_a} wins, "
        f"{b} {result.wins_b} wins, {result.draws} draws "
        f"(goals: {a} {result.goals_a} - {result.goals_b} {b})"
    )
    if result.per_competition:
        lines.append("By competition:")
        for comp in sorted(result.per_competition):
            stats = result.per_competition[comp]
            lines.append(
                f"  - {comp}: {stats['matches']} matches "
                f"({a} {stats[f'wins_{result.team_a.key}']}W, "
                f"{b} {stats[f'wins_{result.team_b.key}']}W, {stats['draws']}D)"
            )
    return "\n".join(lines)


def format_last_match(m: Optional[Match], team_a: str, team_b: str) -> str:
    if m is None:
        return f"No match between {team_a} and {team_b} found in the dataset."
    lines = [
        f"Last {team_a} vs {team_b} match in dataset:",
        format_match(m),
    ]
    if m.stats:
        s = m.stats
        extras = []
        if s.shots_home is not None:
            extras.append(f"shots {s.shots_home}-{s.shots_away}")
        if s.corners_home is not None:
            extras.append(f"corners {s.corners_home}-{s.corners_away}")
        if s.ht_result_home:
            extras.append(f"half-time: {s.ht_result_home}/{s.ht_result_away}")
        if extras:
            lines.append("  Extra stats: " + ", ".join(extras))
    return "\n".join(lines)


def _record_lines(rec, label: str) -> list[str]:
    return [
        f"- {label} - Matches: {rec.matches}",
        f"  Wins: {rec.wins}, Draws: {rec.draws}, Losses: {rec.losses}",
        f"  Goals For: {rec.goals_for}, Goals Against: {rec.goals_against}, "
        f"Win rate: {rec.win_rate * 100:.1f}%",
    ]


def format_team_stats(result: TeamStatsResult) -> str:
    from .loader import COMPETITION_DISPLAY

    scope_bits = []
    if result.competition_id:
        scope_bits.append(COMPETITION_DISPLAY[result.competition_id])
    if result.season is not None:
        scope_bits.append(f"season {result.season}")
    scope = ", ".join(scope_bits) if scope_bits else "all competitions, all seasons"
    lines = [f"{result.team.display} record ({scope}):"]
    lines.extend(_record_lines(result.overall, "Overall"))
    lines.extend(_record_lines(result.home, "Home"))
    lines.extend(_record_lines(result.away, "Away"))
    return "\n".join(lines)


def format_team_profile(result: TeamProfileResult) -> str:
    t = result.team
    lines = [f"{t.display} (team profile):"]
    if t.variants:
        shown = ", ".join(sorted(set(t.variants))[:6])
        lines.append(f"Name variants in dataset: {shown}")
    lines.append(
        f"Seasons in dataset: {result.first_season}-{result.last_season} "
        f"({result.overall.matches} matches, "
        f"{result.overall.wins}W {result.overall.draws}D {result.overall.losses}L, "
        f"GF {result.overall.goals_for}, GA {result.overall.goals_against})"
    )
    lines.append("By competition:")
    for entry in result.entries:
        lines.append(
            f"- {entry.competition}: {len(entry.seasons)} seasons "
            f"({entry.seasons[0]}-{entry.seasons[-1]}), "
            f"{entry.record.matches} matches, {entry.record.wins}W "
            f"{entry.record.draws}D {entry.record.losses}L"
        )
    if result.squad:
        top = ", ".join(
            f"{p.name} ({p.overall})" for p in result.squad[:5] if p.overall
        )
        lines.append(
            f"FIFA dataset squad: {len(result.squad)} players (avg rating "
            f"{_avg_overall(result.squad):.1f}); top: {top}"
        )
    else:
        lines.append(
            "FIFA dataset squad: no players recorded for this club "
            "(the FIFA file only covers part of the Brazilian league)."
        )
    return "\n".join(lines)


def _avg_overall(players: list[Player]) -> float:
    ratings = [p.overall for p in players if p.overall is not None]
    return sum(ratings) / len(ratings) if ratings else 0.0


def _player_line(p: Player, rank: Optional[int] = None) -> str:
    prefix = f"{rank}. " if rank else "- "
    bits = [f"{p.name} - Overall: {p.overall}", f"Position: {p.position}"]
    if p.club:
        bits.append(f"Club: {p.club}")
    if p.age is not None:
        bits.append(f"Age: {p.age}")
    if p.nationality:
        bits.append(f"Nationality: {p.nationality}")
    return prefix + ", ".join(bits)


def format_players(result: PlayerSearchResult) -> str:
    header = "Players"
    if result.club:
        header += f" at {result.club.display}"
    filters = result.filters
    if filters.get("nationality"):
        header += f" from {filters['nationality']}"
    if filters.get("position"):
        header += f" playing {filters['position']}"
    if filters.get("name"):
        header += f" matching '{filters['name']}'"
    if result.total == 0:
        return (
            f"{header}: no players found in the FIFA dataset. Note that the "
            "FIFA file covers only part of the Brazilian league."
        )
    lines = [f"{header} ({result.total} players in dataset):"]
    for i, p in enumerate(result.players, start=1):
        lines.append(_player_line(p, i))
    if result.truncated:
        lines.append(f"... ({result.total - len(result.players)} more players)")
    return "\n".join(lines)


def format_player_details(players: list[Player]) -> str:
    blocks = []
    for p in players:
        lines = [f"{p.name} (FIFA dataset):"]
        rows = [
            ("Overall rating", p.overall),
            ("Potential", p.potential),
            ("Position", p.position),
            ("Club", p.club),
            ("Nationality", p.nationality),
            ("Age", p.age),
            ("Jersey number", p.jersey),
            ("Height", p.height),
            ("Weight", p.weight),
            ("Preferred foot", p.preferred_foot),
            ("Market value", p.value),
            ("Wage", p.wage),
        ]
        for label, value in rows:
            if value not in (None, ""):
                lines.append(f"- {label}: {value}")
        if p.skills:
            top = sorted(p.skills.items(), key=lambda kv: -kv[1])[:6]
            lines.append("- Top skills: " + ", ".join(f"{k} {v}" for k, v in top))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def format_standings(table: Any, notes: list[str]) -> str:
    lines = [f"{table.competition} {table.season} standings (calculated from matches):"]
    lines.append(
        f"{'Pos':>3}  {'Team':<28} {'P':>3} {'W':>3} {'D':>3} {'L':>3} "
        f"{'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}"
    )
    for row in table.rows:
        marker = ""
        if row.position == 1:
            marker = " - Champion"
        elif row in table.relegated:
            marker = " - Relegated"
        lines.append(
            f"{row.position:>3}  {row.team:<28} {row.played:>3} {row.wins:>3} "
            f"{row.draws:>3} {row.losses:>3} {row.goals_for:>4} {row.goals_against:>4} "
            f"{row.goal_diff:>+4} {row.points:>4}{marker}"
        )
    if notes:
        lines.extend(f"Note: {n}" for n in notes)
    return "\n".join(lines)


def format_champion(result: dict) -> str:
    lines = [
        f"{result['season']} {result['competition']} champion: {result['champion']}"
    ]
    if result.get("record"):
        lines.append(f"Determined by {result['method']}: {result['record']}")
    else:
        lines.append(f"Determined by {result['method']}")
    for note in result.get("notes") or []:
        if note:
            lines.append(f"Note: {note}")
    return "\n".join(lines)


def format_finals(finals: list[CupFinalResult]) -> str:
    if not finals:
        return "No finals found for this competition in the dataset."
    blocks = []
    for f in finals:
        lines = [f"{f.competition} {f.season} final:"]
        for m in f.matches:
            lines.append(format_match(m))
        if f.winner_display:
            lines.append(f"Winner: {f.winner_display}")
        elif f.note:
            lines.append(f"No outright winner: {f.note}")
        if f.note and f.winner_display:
            lines.append(f"Note: {f.note}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def format_biggest_wins(matches: list[Match], scope: str) -> str:
    lines = [f"Biggest victories in {scope} (provided data):"]
    for i, m in enumerate(matches, start=1):
        lines.append(f"{i}. {_date(m)}: {m.score} ({m.competition} {m.stage or m.season})")
    return "\n".join(lines)


def format_competition_stats(stats: dict) -> str:
    label = stats["label"]
    if stats["season"]:
        label += f" {stats['season']}"
    lines = [
        f"{label} statistics:",
        f"- Matches: {stats['matches']}",
        f"- Average goals per match: {stats['avg_goals']:.2f}",
        f"- Home wins: {stats['home_wins']} ({stats['home_win_pct']:.1f}%)",
        f"- Away wins: {stats['away_wins']} ({stats['away_win_pct']:.1f}%)",
        f"- Draws: {stats['draws']} ({stats['draw_pct']:.1f}%)",
        f"- Average home goals: {stats['avg_home_goals']:.2f}, average away goals: {stats['avg_away_goals']:.2f}",
    ]
    return "\n".join(lines)


def format_best_records(ranked: list, venue: str, scope: str) -> str:
    if not ranked:
        return f"No teams with enough matches found for a {venue} record in {scope}."
    lines = [f"Best {venue} records in {scope}:"]
    for i, (info, rec, rate) in enumerate(ranked, start=1):
        lines.append(
            f"{i}. {info.display} - {rec.wins}W {rec.draws}D {rec.losses}L "
            f"({rec.matches} matches), win rate {rate * 100:.1f}%"
        )
    return "\n".join(lines)


def format_derbies(results: list[DerbyResult], scope: str) -> str:
    if not results:
        return f"No derby matches found in {scope}."
    blocks = []
    for d in results:
        lines = [f"{d.label} ({d.matches[0].home_team} vs {d.matches[0].away_team}) - {len(d.matches)} matches:"]
        for m in d.matches[:5]:
            lines.append(format_match(m))
        if len(d.matches) > 5:
            lines.append(f"... ({len(d.matches) - 5} more)")
        blocks.append("\n".join(lines))
    header = f"Derbies in {scope}:"
    return header + "\n\n" + "\n\n".join(blocks)


def format_compare_seasons(result: dict) -> str:
    a, b = result["stats_a"], result["stats_b"]
    comp = result["competition"]
    lines = [f"{comp}: {result['season_a']} vs {result['season_b']}"]

    def champ_line(champ):
        if champ:
            return f"{champ['champion']} ({champ.get('record', '')})"
        return "not determined"

    lines.append(f"- Champion {result['season_a']}: {champ_line(result['champion_a'])}")
    lines.append(f"- Champion {result['season_b']}: {champ_line(result['champion_b'])}")
    lines.append(f"- Matches: {a['matches']} vs {b['matches']}")
    lines.append(f"- Goals: {a['goals']} vs {b['goals']}")
    lines.append(f"- Avg goals per match: {a['avg_goals']:.2f} vs {b['avg_goals']:.2f}")
    lines.append(f"- Home win rate: {a['home_win_pct']:.1f}% vs {b['home_win_pct']:.1f}%")
    for label, key in ((result["season_a"], "top_scoring_team_a"), (result["season_b"], "top_scoring_team_b")):
        top = result[key]
        if top:
            lines.append(f"- Top scoring team {label}: {top['team']} ({top['goals_for']} goals)")
    return "\n".join(lines)


def format_team_search(teams: list, query: str) -> str:
    if not teams:
        return f"No teams matching '{query}' found."
    lines = [f"Teams matching '{query}':"]
    for info in teams:
        variants = ", ".join(sorted(set(info.variants))[:4])
        lines.append(
            f"- {info.display} ({info.match_count} matches)"
            + (f" [variants: {variants}]" if variants else "")
        )
    return "\n".join(lines)


def format_competitions(comps: Iterable) -> str:
    lines = ["Competitions in dataset:"]
    for c in comps:
        seasons = f"{c.seasons[0]}-{c.seasons[-1]}" if c.seasons else "none"
        lines.append(
            f"- {c.display} ({c.kind}): {c.match_count} matches, "
            f"{c.team_count} teams, seasons {seasons}"
        )
    lines.append(
        "Sources: Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv, "
        "Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, "
        "BR-Football-Dataset.csv (+ fifa_data.csv for players)"
    )
    return "\n".join(lines)
