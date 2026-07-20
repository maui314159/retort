"""Human-readable rendering of query results.

The MCP tools return plain text in the shapes shown in the specification
(e.g. ``2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)``).
"""

from __future__ import annotations

from typing import Any


def _match_line(match: dict[str, Any]) -> str:
    stage = f", {match['stage']}" if match.get("stage") else ""
    return (
        f"- {match['date']}: {match['home_team']} {match['home_goals']}-"
        f"{match['away_goals']} {match['away_team']} ({match['competition']}{stage})"
    )


def format_matches(result: dict[str, Any]) -> str:
    if result["total"] == 0:
        return "No matches found for the given criteria."
    header = f"Found {result['total']} match(es)"
    if result.get("team"):
        header += f" involving {result['team']}"
    shown = result["matches"]
    lines = [header + f"; showing {len(shown)} most recent:"]
    lines.extend(_match_line(m) for m in shown)
    if result["total"] > len(shown):
        lines.append(f"... ({result['total'] - len(shown)} more matches in dataset)")
    return "\n".join(lines)


def format_head_to_head(result: dict[str, Any]) -> str:
    a, b = result["team_a"], result["team_b"]
    if result["total"] == 0:
        return f"No matches between {a} and {b} found in the dataset."
    lines = [f"{a} vs {b}:"]
    lines.extend(_match_line(m) for m in result["matches"])
    if result["total"] > len(result["matches"]):
        lines.append(f"... ({result['total'] - len(result['matches'])} more matches in dataset)")
    lines.append("")
    lines.append(
        f"Head-to-head in dataset: {a} {result['wins_a']} wins, "
        f"{b} {result['wins_b']} wins, {result['draws']} draws "
        f"(goals: {result['goals_a']}-{result['goals_b']})"
    )
    return "\n".join(lines)


def format_team_stats(result: dict[str, Any]) -> str:
    scope = result["competition"] or "all competitions"
    season = f" {result['season']}" if result["season"] else ""
    venue = {"all": "", "home": " home", "away": " away"}[result["venue"]]
    lines = [
        f"{result['team']}{venue} record ({scope}{season}):",
        f"- Matches: {result['matches']}",
        f"- Wins: {result['wins']}, Draws: {result['draws']}, Losses: {result['losses']}",
        f"- Goals For: {result['goals_for']}, Goals Against: {result['goals_against']} "
        f"(GD {result['goal_difference']:+d})",
        f"- Win rate: {result['win_rate']}%",
    ]
    if len(result["by_competition"]) > 1:
        breakdown = ", ".join(
            f"{comp}: {count}" for comp, count in sorted(result["by_competition"].items())
        )
        lines.append(f"- Matches by competition: {breakdown}")
    return "\n".join(lines)


def format_standings(result: dict[str, Any]) -> str:
    table = result["table"]
    if not table:
        return (
            f"No matches found for {result['competition']} "
            f"season {result['season']}."
        )
    lines = [
        f"{result['season']} {result['competition']} standings "
        f"(calculated from {sum(r['played'] for r in table) // 2} matches):"
    ]
    for row in table:
        marker = " - Champion" if row["champion"] else (" - Relegated" if row["relegated"] else "")
        lines.append(
            f"{row['position']:>2}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L, "
            f"GD {row['goal_difference']:+d}){marker}"
        )
    return "\n".join(lines)


def _player_line(rank: int, player: dict[str, Any]) -> str:
    club = player["club"] or "No club"
    position = player["position"] or "?"
    return (
        f"{rank}. {player['name']} - Overall: {player['overall']}, "
        f"Position: {position}, Club: {club} ({player['nationality']}, "
        f"age {player['age']})"
    )


def format_players(result: dict[str, Any]) -> str:
    if result["total"] == 0:
        return "No players found for the given criteria."
    shown = result["players"]
    lines = [f"Found {result['total']} player(es); top {len(shown)} by overall rating:"]
    lines.extend(_player_line(i + 1, p) for i, p in enumerate(shown))
    return "\n".join(lines)


def format_club_summary(result: dict[str, Any]) -> str:
    if result["player_count"] == 0:
        return f"No players found for club {result['club']!r} in the FIFA dataset."
    clubs = ", ".join(result["matched_clubs"])
    lines = [
        f"{clubs}: {result['player_count']} players "
        f"(avg rating: {result['avg_overall']}, avg age: {result['avg_age']}, "
        f"Brazilian: {result['brazilian_count']})",
        "Top players:",
    ]
    lines.extend(_player_line(i + 1, p) for i, p in enumerate(result["players"]))
    return "\n".join(lines)


def format_biggest_wins(result: dict[str, Any]) -> str:
    if result["total"] == 0:
        return "No matches found for the given criteria."
    lines = ["Biggest victories in dataset:"]
    for i, win in enumerate(result["biggest_wins"], start=1):
        lines.append(
            f"{i}. {win['date']}: {win['winner']} {win['score']} {win['loser']} "
            f"({win['competition']})"
        )
    return "\n".join(lines)


def format_competition_stats(result: dict[str, Any]) -> str:
    if result["matches"] == 0:
        return "No matches found for the given criteria."
    scope = result["competition"] or "all competitions"
    season = f" {result['season']}" if result["season"] else ""
    lines = [
        f"Statistics for {scope}{season} ({result['matches']} matches):",
        f"- Average goals per match: {result['avg_goals_per_match']}",
        f"- Home win rate: {result['home_win_rate']}% "
        f"({result['home_wins']} of {result['matches']})",
        f"- Draw rate: {result['draw_rate']}% ({result['draws']})",
        f"- Away win rate: {result['away_win_rate']}% ({result['away_wins']})",
    ]
    if not result["season"] and len(result["per_season"]) > 1:
        lines.append("- Per season:")
        lines.extend(
            f"  {row['season']}: {row['matches']} matches, "
            f"{row['avg_goals']} goals/match"
            for row in result["per_season"]
        )
    return "\n".join(lines)


def format_competitions(result: dict[str, Any]) -> str:
    lines = ["Competitions in dataset:"]
    for comp in result["competitions"]:
        seasons = (
            f"seasons {comp['seasons'][0]}-{comp['seasons'][1]}"
            if comp["seasons"]
            else "no season info"
        )
        lines.append(
            f"- {comp['competition']}: {comp['matches']} matches, "
            f"{comp['teams']} teams, {seasons}"
        )
    return "\n".join(lines)


def format_dataset_summary(result: dict[str, Any]) -> str:
    lines = [
        "Dataset summary:",
        f"- Total matches (deduplicated): {result['total_matches']}",
        f"- Total players: {result['total_players']}",
        f"- Competitions: {', '.join(result['competitions'])}",
        f"- Date range: {result['date_range'][0]} to {result['date_range'][1]}",
        "- Per source file:",
    ]
    for name, stats in result["files"].items():
        dupes = stats.get("duplicates_dropped", 0)
        if name == "*dedupe*":
            lines.append(
                f"  (cross-file dedupe): {dupes} duplicate fixtures removed "
                f"across files"
            )
            continue
        lines.append(
            f"  {name}: {stats['rows_usable']} usable rows "
            f"({stats['rows_dropped']} unusable)"
        )
    return "\n".join(lines)
