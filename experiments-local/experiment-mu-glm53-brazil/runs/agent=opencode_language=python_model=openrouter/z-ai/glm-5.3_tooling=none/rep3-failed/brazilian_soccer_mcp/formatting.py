"""Human-readable answer formatting following the TASK.md answer formats."""

from __future__ import annotations

from typing import Iterable, Optional

from brazilian_soccer_mcp.derbies import Derby
from brazilian_soccer_mcp.models import (
    CompetitionStats,
    HeadToHead,
    Match,
    Player,
    StandingRow,
    TeamStats,
)
from brazilian_soccer_mcp.queries import (
    DerbyResult,
    MatchSearchResult,
    StandingsResult,
    TeamInfo,
)


def _fmt_date(value) -> str:
    return value.isoformat() if value else "date unknown"


def format_match_line(match: Match) -> str:
    """One line per match: date, teams, score and competition context."""
    context = match.competition
    if match.round:
        context += f", Round {match.round}"
    if match.stage:
        context += f", {match.stage.capitalize()}"
    if match.venue:
        context += f", {match.venue}"
    if match.played:
        score = f"{match.home_display} {match.home_goals}-{match.away_goals} {match.away_display}"
    else:
        score = f"{match.home_display} vs {match.away_display} (not played/score unavailable)"
    return f"- {_fmt_date(match.date)}: {score} ({context})"


def format_search_matches(result: MatchSearchResult, limit: int = 20) -> str:
    """Format a match search result as a match list with a summary."""
    lines = []
    header_parts = []
    if result.team_display and result.opponent_display:
        header_parts.append(f"{result.team_display} vs {result.opponent_display}")
    elif result.team_display:
        header_parts.append(f"{result.team_display} matches")
    else:
        header_parts.append("Matches")
    lines.append(header_parts[0] + ":")
    if not result.matches:
        lines.append("No matches found for these criteria.")
    for match in result.matches:
        lines.append(format_match_line(match))
    if result.total > len(result.matches):
        lines.append(f"... ({result.total - len(result.matches)} more matches in dataset)")
    if result.stage_note:
        lines.append(f"Note: {result.stage_note}")
    return "\n".join(lines)


def _derby_name_for_pair(team_a: str, team_b: str, derbies: Optional[Iterable[Derby]] = None):
    from brazilian_soccer_mcp.derbies import DERBIES

    for derby in DERBIES:
        if {derby.team_a, derby.team_b} == {team_a, team_b}:
            return derby.name
    return None


def format_head_to_head(h2h: HeadToHead) -> str:
    """Format a head-to-head summary with recent meetings."""
    derby_name = _derby_name_for_pair(h2h.team_a_key, h2h.team_b_key)
    title = f"{h2h.team_a_display} vs {h2h.team_b_display}"
    if derby_name:
        title += f" ({derby_name} derby)"
    lines = [title + ":"]
    if not h2h.matches:
        lines.append("No matches between these teams in the dataset.")
        return "\n".join(lines)
    for match in h2h.matches:
        lines.append(format_match_line(match))
    if h2h.total > len(h2h.matches):
        lines.append(
            f"... ({h2h.total - len(h2h.matches)} more matches in dataset)"
        )
    lines.append(
        f"Head-to-head in dataset: {h2h.team_a_display} {h2h.team_a_wins} wins, "
        f"{h2h.team_b_display} {h2h.team_b_wins} wins, {h2h.draws} draws "
        f"(goals: {h2h.goals_a}-{h2h.goals_b})"
    )
    return "\n".join(lines)


def format_team_stats(
    stats: TeamStats,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: str = "all",
) -> str:
    """Format team statistics like the TASK.md team query example."""
    scope = []
    if season:
        scope.append(str(season))
    if competition:
        scope.append(competition)
    if venue and venue != "all":
        scope.append(f"{venue} matches")
    scope_text = f" ({', '.join(scope)})" if scope else ""
    lines = [f"{stats.team_display} record{scope_text}:"]
    if stats.matches == 0:
        lines.append("No played matches found for these criteria.")
        return "\n".join(lines)
    lines.append(f"- Matches: {stats.matches}")
    lines.append(
        f"- Wins: {stats.wins}, Draws: {stats.draws}, Losses: {stats.losses}"
    )
    lines.append(
        f"- Goals For: {stats.goals_for}, Goals Against: {stats.goals_against} "
        f"(GD {stats.goal_difference:+d})"
    )
    lines.append(f"- Win rate: {stats.win_rate:.1%}")
    lines.append(f"- Points (3 per win): {stats.points}")
    return "\n".join(lines)


def format_standings(result: StandingsResult) -> str:
    """Format a calculated league table."""
    season = result.season if result.season is not None else "all seasons"
    lines = [f"{result.competition} {season} standings (calculated from matches):"]
    for row in result.rows:
        marker = ""
        if result.champion and row.position == 1:
            marker = " - Champion"
        elif result.relegated and row.team_display in result.relegated:
            marker = " - Relegated"
        lines.append(
            f"{row.position}. {row.team_display} - {row.points} pts "
            f"({row.wins}W, {row.draws}D, {row.losses}L, "
            f"GF {row.goals_for}, GA {row.goals_against}){marker}"
        )
    if result.champion:
        lines.append(f"Champion: {result.champion}")
    elif result.rows:
        lines.append(f"Leader (season incomplete in data): {result.rows[0].team_display}")
    if result.relegated:
        lines.append(f"Relegated: {', '.join(result.relegated)}")
    if result.note:
        lines.append(f"Note: {result.note}")
    lines.append(
        "Top scorers are not available: the provided datasets do not "
        "include per-goal scorer information."
    )
    return "\n".join(lines)


def _player_line(player: Player) -> str:
    parts = [f"{player.name} - Overall: {player.overall}"]
    if player.position:
        parts.append(f"Position: {player.position}")
    if player.age is not None:
        parts.append(f"Age: {player.age}")
    if player.club_display:
        parts.append(f"Club: {player.club_display}")
    if player.nationality:
        parts.append(f"Nationality: {player.nationality}")
    return " | ".join(parts)


def format_players(
    players: list[Player],
    title: str,
    total: Optional[int] = None,
    tail: Optional[str] = None,
) -> str:
    """Format a player list, optionally numbered like the examples."""
    lines = [title]
    if not players:
        lines.append("No players found for these criteria.")
        return "\n".join(lines)
    numbered = total is None or len(players) <= 30
    for index, player in enumerate(players, start=1):
        prefix = f"{index}. " if numbered else "- "
        lines.append(prefix + _player_line(player))
    if total is not None and total > len(players):
        lines.append(f"... ({total - len(players)} more players in dataset)")
    if tail:
        lines.append(tail)
    return "\n".join(lines)


def format_club_roster(club_display: str, players: list[Player]) -> str:
    """Format a club roster with average rating."""
    if not players:
        return (
            f"No {club_display} players found in the FIFA dataset "
            "(the dataset covers a subset of clubs)."
        )
    avg = sum(p.overall for p in players) / len(players)
    tail = f"Roster size: {len(players)} players, average rating: {avg:.1f}"
    return format_players(players, f"{club_display} players (FIFA dataset):", tail=tail)


def format_statistics(
    stats: CompetitionStats,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """Format aggregate statistics."""
    scope = []
    if competition:
        scope.append(competition)
    if season:
        scope.append(str(season))
    scope_text = f" ({', '.join(scope)})" if scope else " (all competitions in dataset)"
    lines = [f"Statistics{scope_text}:"]
    lines.append(f"- Matches: {stats.matches}")
    lines.append(f"- Average goals per match: {stats.avg_goals:.2f}")
    lines.append(
        f"- Home wins: {stats.home_wins} ({stats.home_win_rate:.1%}), "
        f"Draws: {stats.draws} ({stats.draw_rate:.1%}), "
        f"Away wins: {stats.away_wins} ({stats.away_win_rate:.1%})"
    )
    lines.append(
        f"- Average home goals: {stats.avg_home_goals:.2f}, "
        f"average away goals: {stats.avg_away_goals:.2f}"
    )
    if stats.biggest_home_win and stats.biggest_home_win.margin:
        m = stats.biggest_home_win
        lines.append(
            f"- Biggest home win: {_fmt_date(m.date)}: "
            f"{m.home_display} {m.home_goals}-{m.away_goals} {m.away_display}"
        )
    if stats.biggest_away_win and stats.biggest_away_win.margin:
        m = stats.biggest_away_win
        lines.append(
            f"- Biggest away win: {_fmt_date(m.date)}: "
            f"{m.home_display} {m.home_goals}-{m.away_goals} {m.away_display}"
        )
    return "\n".join(lines)


def format_biggest_wins(matches: list[Match], competition: Optional[str] = None) -> str:
    """Format the biggest winning margins."""
    scope = f" in {competition}" if competition else ""
    lines = [f"Biggest victories{scope} (provided data):"]
    for index, match in enumerate(matches, start=1):
        lines.append(
            f"{index}. {_fmt_date(match.date)}: {match.home_display} "
            f"{match.home_goals}-{match.away_goals} {match.away_display} "
            f"({match.competition}{', ' + str(match.season) if match.season else ''})"
        )
    return "\n".join(lines)


def format_derbies(results: list[DerbyResult]) -> str:
    """Format derby matches and records."""
    lines = []
    for result in results:
        derby: Derby = result.derby
        if result.total == 0:
            lines.append(f"{derby.name} ({derby.description}): no matches in dataset for these filters.")
            lines.append("")
            continue
        lines.append(
            f"{derby.name} ({derby.description}) - {result.total} matches in dataset:"
        )
        for match in result.matches:
            lines.append(format_match_line(match))
        if result.total > len(result.matches):
            lines.append(f"... ({result.total - len(result.matches)} more matches in dataset)")
        lines.append(
            f"Record: {result.team_a_display or derby.team_a} {result.team_a_wins} wins, "
            f"{result.team_b_display or derby.team_b} {result.team_b_wins} wins, {result.draws} draws"
        )
        lines.append("")
    return "\n".join(lines).rstrip()


def format_find_team(info: TeamInfo) -> str:
    """Format the find_team resolution report."""
    lines = [f"Team: {info.display} (canonical key: {info.key})"]
    if info.siblings:
        lines.append(
            "Other teams sharing the base name: " + ", ".join(info.siblings)
        )
    if info.variants:
        shown = ", ".join(info.variants[:8])
        more = "" if len(info.variants) <= 8 else f" (+{len(info.variants) - 8} more)"
        lines.append(f"Name variants found in the data: {shown}{more}")
    lines.append(f"Matches in dataset: {info.match_count}")
    if info.first_match and info.last_match:
        lines.append(
            f"Period covered: {info.first_match.isoformat()} to {info.last_match.isoformat()}"
        )
    if info.competitions:
        comp_text = ", ".join(
            f"{name}: {count}" for name, count in sorted(
                info.competitions.items(), key=lambda kv: -kv[1]
            )
        )
        lines.append(f"Competitions: {comp_text}")
    if info.player_count:
        lines.append(
            f"FIFA dataset: {info.player_count} players, average rating {info.avg_player_rating}"
        )
    else:
        lines.append(
            "FIFA dataset: no players at this club (the FIFA data covers a subset of clubs)."
        )
    return "\n".join(lines)


def format_competitions(overviews: list[dict]) -> str:
    """Format the competition overview list."""
    lines = ["Competitions available in the dataset:"]
    for overview in overviews:
        seasons = overview["seasons"]
        if len(seasons) > 12:
            season_text = f"{seasons[0]}-{seasons[-1]} ({len(seasons)} seasons)"
        else:
            season_text = ", ".join(str(s) for s in seasons)
        selected = ""
        if overview.get("selected_season") is not None:
            selected = f" (showing {overview['selected_season']})"
        lines.append(
            f"- {overview['competition']}{selected}: {overview['matches']} matches "
            f"({overview.get('total_rows', overview['matches'])} rows across all source files), "
            f"seasons {season_text}"
        )
        lines.append(f"  Sources: {', '.join(overview['sources'])}")
    lines.append(
        "Tip: standings are available for league competitions "
        "(Série A/B/C); use the standings tool with a season."
    )
    return "\n".join(lines)


def format_list_teams(teams: list[tuple[str, int]], competition: Optional[str], season: Optional[int]) -> str:
    scope = []
    if competition:
        scope.append(competition)
    if season:
        scope.append(str(season))
    scope_text = f" ({', '.join(scope)})" if scope else ""
    lines = [f"Teams{scope_text}:"]
    for name, count in teams:
        lines.append(f"- {name}: {count} matches")
    return "\n".join(lines)
