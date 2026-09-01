"""Human-facing answer formatting, following the spec's answer formats.

Each formatter turns query-engine output into the plain-text shapes shown
in the specification, e.g.::

    Flamengo vs Fluminense (Fla-Flu derby):
    - 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)

    Head-to-head in dataset: Flamengo 12 wins, Fluminense 8 wins, 7 draws

All output is UTF-8 Brazilian Portuguese friendly (accents preserved).
"""

from __future__ import annotations

from .data import COMPETITIONS
from .models import Match, Player, TableRow

_MAX_LISTED = 10


def _stage_text(match: Match) -> str:
    """Stage suffix: 'Round 22', 'final', 'group stage', or ''."""
    stage = (match.stage or "").strip()
    if not stage:
        return ""
    if stage.isdigit():
        if match.competition == "copa_do_brasil" and stage == "8":
            return " Final"  # the Copa do Brasil dataset numbers the final as round 8
        return f" Round {stage}"
    return f" {stage}"


def format_match(match: Match) -> str:
    """One line: ``- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)``."""
    date_text = match.date.isoformat() if match.date else (match.date_text or "unknown date")
    return (
        f"- {date_text}: {match.home_display} {match.score_text} {match.away_display} "
        f"({match.competition_display}{_stage_text(match)})"
    )


def format_matches(matches: list[Match], title: str) -> str:
    """Match list with a "... (N more)" trailer, per the spec's example."""
    if not matches:
        return f"{title}\nNo matches found in the dataset."
    lines = [f"{title}:"]
    for match in matches[:_MAX_LISTED]:
        lines.append(format_match(match))
    hidden = len(matches) - _MAX_LISTED
    if hidden > 0:
        lines.append(f"... ({hidden} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(h2h: dict) -> str:
    """Head-to-head summary block."""
    matches = h2h["matches"]
    lines = [f"{h2h['team_a_display']} vs {h2h['team_b_display']} head-to-head:"]
    lines.append("")
    lines.extend(format_match(m)[2:] for m in matches[:_MAX_LISTED])
    hidden = len(matches) - _MAX_LISTED
    if hidden > 0:
        lines.append(f"... ({hidden} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {h2h['team_a_display']} {h2h['wins_a']} wins, "
        f"{h2h['team_b_display']} {h2h['wins_b']} wins, {h2h['draws']} draws "
        f"({h2h['goals_a']}-{h2h['goals_b']} goals)"
    )
    return "\n".join(lines)


def _record_block(label: str, stats: dict) -> list[str]:
    played = stats["matches"] - stats["unplayed"]
    lines = [
        f"{label}:",
        f"- Matches: {stats['matches']}",
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}",
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}",
    ]
    if played:
        lines.append(f"- Win rate: {stats['win_rate']:.1f}%")
    else:
        lines.append("- Win rate: n/a (no scored matches)")
    return lines


def format_team_stats(stats: dict) -> str:
    """Team record block, e.g. the Corinthians home-record example."""
    scope = []
    if stats["season"] is not None:
        scope.append(str(stats["season"]))
    if stats["competition"]:
        scope.append(COMPETITIONS[stats["competition"]])
    scope_text = f" ({', '.join(scope)})" if scope else ""
    lines = [f"{stats['display']}{scope_text} record in dataset:"]
    lines.append("")
    lines.extend(_record_block("Overall", stats["overall"]))
    lines.append("")
    lines.extend(_record_block("Home", stats["home"]))
    lines.append("")
    lines.extend(_record_block("Away", stats["away"]))
    return "\n".join(lines)


def format_last_match(match: Match | None, team: str) -> str:
    if match is None:
        return f"No match found for {team} in the dataset."
    return f"Last recorded match involving {team}:\n{format_match(match)[2:]}"


def format_standings(table: list[TableRow], competition_display: str, season: int) -> str:
    """Numbered table with the champion marked, per the spec example."""
    lines = [f"{season} {competition_display} Final Standings (calculated from matches):"]
    relegated_from = max(0, len(table) - 3)
    for row in table:
        marker = " - Champion" if row.position == 1 else ""
        if row.position == relegated_from:
            lines.append("... relegation zone:")
        lines.append(
            f"{row.position}. {row.display} - {row.points} pts "
            f"({row.win}W, {row.draw}D, {row.loss}L){marker}"
        )
    return "\n".join(lines)


def format_relegation(rows: list[TableRow], competition_display: str, season: int) -> str:
    lines = [f"{season} {competition_display} relegated teams (bottom of the table):"]
    for row in rows:
        lines.append(
            f"- {row.display} - {row.points} pts ({row.win}W, {row.draw}D, {row.loss}L, "
            f"{row.goals_for}:{row.goals_against} goals)"
        )
    return "\n".join(lines)


def format_competition_info(info: dict) -> str:
    if "competitions" in info:  # all-competitions summary
        lines = ["Competitions in the dataset:"]
        for comp in info["competitions"]:
            seasons = f"{comp['first_season']}-{comp['last_season']}" if comp["seasons"] else "n/a"
            lines.append(
                f"- {comp['display']}: {comp['matches']} matches, {comp['teams']} teams, "
                f"seasons {seasons}. {comp['note']}"
            )
        return "\n".join(lines)
    seasons = f"{info['first_season']}-{info['last_season']}" if info["seasons"] else "n/a"
    return (
        f"{info['display']}: {info['matches']} matches, {info['teams']} teams, "
        f"seasons {seasons}.\n{info['note']}"
    )


def format_player(player: Player, rank: int | None = None) -> str:
    """One line: ``1. Neymar Jr - Overall: 92, Position: LW, Club: ...``."""
    club = player.club or "Free agent"
    prefix = f"{rank}. " if rank else "- "
    extras = []
    if player.age:
        extras.append(f"Age: {player.age}")
    if player.potential:
        extras.append(f"Potential: {player.potential}")
    if player.value:
        extras.append(f"Value: {player.value}")
    extra_text = (", " + ", ".join(extras)) if extras else ""
    return (
        f"{prefix}{player.name} - Overall: {player.overall}, Position: {player.position or 'n/a'}, "
        f"Nationality: {player.nationality}, Club: {club}{extra_text}"
    )


def format_players(players: list[Player], title: str) -> str:
    if not players:
        return f"{title}\nNo players matched. Loosen the filters (e.g. drop min_overall)."
    lines = [f"{title}:"]
    for rank, player in enumerate(players[:_MAX_LISTED], start=1):
        lines.append(format_player(player, rank))
    hidden = len(players) - _MAX_LISTED
    if hidden > 0:
        lines.append(f"... ({hidden} more players)")
    return "\n".join(lines)


def format_club_overview(groups: list[dict], nationality: str = "Brazil") -> str:
    if not groups:
        return (
            f"No {nationality} players found at Brazilian clubs in this FIFA snapshot. "
            "Note: the snapshot (~FIFA 19) omits some clubs (e.g. Flamengo, Palmeiras, "
            "Corinthians, Sao Paulo and Vasco are absent). Present Brazilian clubs are "
            "listed by search_players(club=...)."
        )
    lines = [f"{nationality} players at Brazilian clubs in the dataset:"]
    for group in groups[:_MAX_LISTED]:
        lines.append(
            f"- {group['display']}: {group['count']} players "
            f"(avg rating: {group['avg_overall']:.0f}; best: {group['best'].name} {group['best'].overall})"
        )
    hidden = len(groups) - _MAX_LISTED
    if hidden > 0:
        lines.append(f"... ({hidden} more clubs)")
    return "\n".join(lines)


def format_stats(stats: dict, label: str) -> str:
    if not stats["matches"]:
        return f"{label}: no scored matches in the dataset."
    return (
        f"{label}:\n"
        f"- Matches with scores: {stats['matches']}\n"
        f"- Average goals per match: {stats['avg_goals']:.2f}\n"
        f"- Home win rate: {stats['home_win_rate']:.1f}%\n"
        f"- Draw rate: {stats['draw_rate']:.1f}%\n"
        f"- Away win rate: {stats['away_win_rate']:.1f}%"
    )


def format_biggest_wins(matches: list[Match], title: str) -> str:
    if not matches:
        return f"{title}\nNo scored matches found."
    lines = [f"{title}:"]
    for rank, match in enumerate(matches[:_MAX_LISTED], start=1):
        lines.append(f"{rank}. {format_match(match)[2:]}")
    return "\n".join(lines)


def format_best_records(ranked: list[dict], venue: str, label: str) -> str:
    if not ranked:
        return f"Best {venue} records ({label}): no teams with enough matches."
    venue_text = {"home": "home", "away": "away", "all": "overall"}[venue]
    lines = [f"Best {venue_text} records ({label}):"]
    for rank, row in enumerate(ranked[:_MAX_LISTED], start=1):
        lines.append(
            f"{rank}. {row['display']} - {row['wins']}W {row['draws']}D {row['losses']}L "
            f"({row['win_rate']:.1f}% win rate, {row['matches']} matches)"
        )
    return "\n".join(lines)


def format_derbies(groups: list[tuple[str, list[Match]]], season: int | None) -> str:
    if not groups:
        scope = f" in {season}" if season else ""
        return f"No derby matches found{scope}."
    scope = f" ({season})" if season else ""
    lines = [f" Derby/classico matches in the dataset{scope} ".strip() + ":"]
    for derby_name, matches in groups:
        lines.append("")
        lines.append(f"{derby_name}:")
        for match in matches[:5]:
            lines.append(format_match(match))
        hidden = len(matches) - 5
        if hidden > 0:
            lines.append(f"... ({hidden} more {derby_name} matches)")
    return "\n".join(lines)


def format_team_competitions(rows: list[dict], display: str) -> str:
    lines = [f"{display} has played in these competitions (dataset coverage):"]
    for row in rows:
        seasons = f"{row['first_season']}-{row['last_season']}" if row["first_season"] else "n/a"
        lines.append(f"- {row['display']}: {row['matches']} matches (seasons {seasons})")
    return "\n".join(lines)


def format_data_summary(summary: dict) -> str:
    lines = [
        "Brazilian soccer dataset summary:",
        f"- Matches: {summary['total_matches']}",
        f"- Players (FIFA database): {summary['total_players']} from {summary['player_nationalities']} nationalities "
        f"({summary['brazilian_players']} Brazilians)",
        f"- Distinct teams: {summary['total_teams']}",
        f"- Match dates: {summary['match_date_range'][0]} to {summary['match_date_range'][1]}",
        "Competitions:",
    ]
    for info in summary["competitions"].values():
        seasons = f"{info['first_season']}-{info['last_season']}" if info["seasons"] else "n/a"
        lines.append(
            f"- {info['display']}: {info['matches']} matches, {info['teams']} teams ({seasons})"
        )
    return "\n".join(lines)


__all__ = [
    "format_matches",
    "format_head_to_head",
    "format_team_stats",
    "format_last_match",
    "format_standings",
    "format_relegation",
    "format_competition_info",
    "format_players",
    "format_club_overview",
    "format_stats",
    "format_biggest_wins",
    "format_best_records",
    "format_derbies",
    "format_team_competitions",
    "format_data_summary",
]
