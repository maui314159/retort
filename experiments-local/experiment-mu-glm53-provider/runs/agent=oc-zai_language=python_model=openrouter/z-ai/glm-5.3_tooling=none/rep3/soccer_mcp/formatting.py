"""
soccer_mcp.formatting -- turn query results into the spec's answer formats.

CONTEXT
-------
TASK.md defines explicit "Example answer format" blocks for every query
category, e.g.:

    Flamengo vs Fluminense (Fla-Flu derby):
    - 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)
    ...
    Head-to-head in dataset: Flamengo 12 wins, Fluminense 8 wins, 7 draws

    Corinthians home record (2022 Brasileirão):
    - Matches: 19
    - Wins: 11, Draws: 5, Losses: 3
    - Goals For: 28, Goals Against: 15
    - Win rate: 57.9%

This module renders every structured query result from ``soccer_mcp.queries``
into that plain-text style so the MCP tools return LLM-friendly answers.
"""

from __future__ import annotations

from .data_loader import SOURCE_LABELS, SoccerData
from .model import (
    CompetitionCoverage,
    FinalResult,
    KnockoutTie,
    Match,
    Player,
    TeamEntity,
    TeamRecord,
)
from .normalize import COMPETITIONS
from .queries import (
    Aggregates,
    ChampionResult,
    HeadToHeadResult,
    MatchSearchResult,
    StandingsResult,
    TeamStatsResult,
)


def team_name(ds: SoccerData, team_id: str) -> str:
    """Display name for a canonical team id."""
    entity = ds.registry.entities.get(team_id)
    return entity.display_name if entity else team_id


def comp_name(comp_id: str) -> str:
    comp = COMPETITIONS.get(comp_id)
    return comp.display if comp else comp_id


def _match_line(ds: SoccerData, match: Match) -> str:
    date_str = match.match_date.isoformat() if match.match_date else "date unknown"
    parts = [
        f"{date_str}: {team_name(ds, match.home_team)} "
        f"{match.home_goals}-{match.away_goals} {team_name(ds, match.away_team)}"
    ]
    label = comp_name(match.competition)
    if match.season:
        label += f" {match.season}"
    if match.round_label:
        label += f" {match.round_label}"
    parts.append(f"({label})")
    line = " ".join(parts)
    if match.stadium:
        line += f" [{match.stadium}]"
    return line


def _record_line(record: TeamRecord) -> str:
    return (
        f"- Matches: {record.matches}\n"
        f"- Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}\n"
        f"- Goals For: {record.goals_for}, Goals Against: {record.goals_against}\n"
        f"- Win rate: {record.win_rate * 100:.1f}%"
    )


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------


def format_match_search(ds: SoccerData, result: MatchSearchResult, limit: int | None) -> str:
    """Format a match list, with head-to-head summary when both sides given."""
    lines: list[str] = []
    if result.team and result.opponent:
        lines.append(
            f"{result.team.display_name} vs {result.opponent.display_name} -- "
            f"matches found in dataset: {result.total}"
        )
    elif result.team:
        scope = []
        if result.competition:
            scope.append(comp_name(result.competition))
        if result.season:
            scope.append(f"season {result.season}")
        scope_txt = f" ({', '.join(scope)})" if scope else ""
        lines.append(
            f"{result.team.display_name} matches{scope_txt} -- found in dataset: {result.total}"
        )
    else:
        scope = []
        if result.competition:
            scope.append(comp_name(result.competition))
        if result.season:
            scope.append(f"season {result.season}")
        scope_txt = f" ({', '.join(scope)})" if scope else ""
        lines.append(f"Matches{scope_txt} -- found in dataset: {result.total}")

    for match in result.matches:
        lines.append(f"- {_match_line(ds, match)}")

    shown = len(result.matches)
    if result.total > shown:
        lines.append(f"... ({result.total - shown} more matches in dataset)")

    if result.team and result.opponent:
        from .queries import head_to_head

        h2h = head_to_head(
            ds,
            result.team.team_id,
            result.opponent.team_id,
            competition=result.competition,
            season=result.season,
        )
        lines.append("")
        lines.append(_h2h_summary(h2h))
    return "\n".join(lines)


def _h2h_summary(h2h: HeadToHeadResult) -> str:
    scope = []
    if h2h.competition:
        scope.append(comp_name(h2h.competition))
    if h2h.season:
        scope.append(f"season {h2h.season}")
    scope_txt = f" ({', '.join(scope)})" if scope else ""
    return (
        f"Head-to-head in dataset{scope_txt}: "
        f"{h2h.team_a.display_name} {h2h.wins_a} wins, "
        f"{h2h.team_b.display_name} {h2h.wins_b} wins, {h2h.draws} draws "
        f"(goals: {h2h.goals_a}-{h2h.goals_b})"
    )


def format_last_match(ds: SoccerData, match: Match | None, team: TeamEntity) -> str:
    if match is None:
        return f"No matches found for {team.display_name} in the dataset."
    return (
        f"Last {team.display_name} match in dataset:\n- {_match_line(ds, match)}\n"
        f"Result: {'Draw' if match.is_draw else team_name(ds, match.winner or '') + ' won'}"
    )


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------


def format_team_stats(ds: SoccerData, stats: TeamStatsResult) -> str:
    scope = []
    if stats.competition:
        scope.append(comp_name(stats.competition))
    if stats.season:
        scope.append(f"season {stats.season}")
    scope_txt = f" ({', '.join(scope)})" if scope else " (all competitions in dataset)"
    header = f"{stats.team.display_name} record{scope_txt}:"
    if stats.overall.matches == 0:
        return header + "\n- No matches found for this filter."

    lines = [
        header,
        "Overall:",
        _record_line(stats.overall),
        "",
        f"Home record ({stats.home.matches} matches):",
        _record_line(stats.home),
        "",
        f"Away record ({stats.away.matches} matches):",
        _record_line(stats.away),
    ]
    if stats.per_competition:
        lines.append("")
        lines.append("By competition:")
        for comp_id, record in stats.per_competition:
            lines.append(
                f"- {comp_name(comp_id)}: {record.matches} matches, "
                f"{record.wins}W {record.draws}D {record.losses}L, "
                f"GF {record.goals_for}, GA {record.goals_against}"
            )
    if stats.first_match and stats.last:
        first = stats.first_match.match_date.isoformat() if stats.first_match.match_date else "?"
        last = stats.last.match_date.isoformat() if stats.last.match_date else "?"
        lines.append("")
        lines.append(f"Dataset coverage: {first} to {last} ({stats.match_count} matches)")
    return "\n".join(lines)


def format_head_to_head(h2h: HeadToHeadResult, ds: SoccerData, limit: int = 15) -> str:
    lines = [
        f"{h2h.team_a.display_name} vs {h2h.team_b.display_name} "
        f"(matches in dataset: {len(h2h.matches)})",
        _h2h_summary(h2h),
        "",
        "Most recent meetings:",
    ]
    if not h2h.matches:
        lines.append("- No matches between these teams in the dataset.")
        return "\n".join(lines)
    recent = sorted(h2h.matches, key=lambda m: m.match_date, reverse=True)[:limit]
    for match in recent:
        lines.append(f"- {_match_line(ds, match)}")
    if len(h2h.matches) > len(recent):
        lines.append(f"... ({len(h2h.matches) - len(recent)} earlier matches in dataset)")
    return "\n".join(lines)


def format_compare(
    stats_a: TeamStatsResult, stats_b: TeamStatsResult, h2h: HeadToHeadResult
) -> str:
    a, b = stats_a.overall, stats_b.overall
    lines = [
        f"{stats_a.team.display_name} vs {stats_b.team.display_name} "
        f"(all matches in dataset):",
        "",
        f"{'':28} {stats_a.team.display_name:>18} {stats_b.team.display_name:>18}",
        f"{'Matches':28} {a.matches:>18} {b.matches:>18}",
        f"{'Wins':28} {a.wins:>18} {b.wins:>18}",
        f"{'Draws':28} {a.draws:>18} {b.draws:>18}",
        f"{'Losses':28} {a.losses:>18} {b.losses:>18}",
        f"{'Goals for':28} {a.goals_for:>18} {b.goals_for:>18}",
        f"{'Goals against':28} {a.goals_against:>18} {b.goals_against:>18}",
        f"{'Win rate':28} {a.win_rate * 100:>17.1f}% {b.win_rate * 100:>17.1f}%",
        "",
        _h2h_summary(h2h),
    ]
    return "\n".join(lines)


def format_ranking(
    ds: SoccerData, ranked: list[tuple[TeamRecord, TeamEntity]], venue: str, scope: str
) -> str:
    venue_txt = {"overall": "overall", "home": "home", "away": "away"}[venue]
    lines = [f"Best {venue_txt} records {scope}:"]
    if not ranked:
        lines.append("- No teams meet the minimum match threshold.")
    for i, (record, entity) in enumerate(ranked, start=1):
        lines.append(
            f"{i}. {entity.display_name} - {record.matches} matches, "
            f"{record.wins}W {record.draws}D {record.losses}L "
            f"({record.win_rate * 100:.1f}% wins)"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------


def _player_line(player: Player, rank: int | None = None) -> str:
    prefix = f"{rank}. " if rank else "- "
    club = player.club or "Free agent"
    position = player.position or "N/A"
    return (
        f"{prefix}{player.name} - Overall: {player.overall}, "
        f"Position: {position}, Club: {club}, Age: {player.age or 'N/A'}, "
        f"Nationality: {player.nationality}"
    )


def format_players(players: list[Player], title: str) -> str:
    lines = [title]
    if not players:
        lines.append("- No players found for this filter in the FIFA dataset.")
        return "\n".join(lines)
    for i, player in enumerate(players, start=1):
        lines.append(_player_line(player, rank=i))
    return "\n".join(lines)


def format_player_detail(player: Player) -> str:
    skills = [
        f"{column}: {value}"
        for column, value in player.skills.items()
        if value is not None
    ]
    skill_txt = ", ".join(skills[:12])
    lines = [
        f"{player.name} ({player.nationality})",
        f"- Overall: {player.overall}, Potential: {player.potential or 'N/A'}",
        f"- Position: {player.position or 'N/A'}, Jersey: {player.jersey_number or 'N/A'}",
        f"- Club: {player.club or 'Free agent'}",
        f"- Age: {player.age or 'N/A'}, Height: {player.height or 'N/A'}, "
        f"Weight: {player.weight or 'N/A'}, Preferred foot: {player.preferred_foot or 'N/A'}",
        f"- Value: {player.value or 'N/A'}, Wage: {player.wage or 'N/A'}",
    ]
    if skill_txt:
        lines.append(f"- Key attributes: {skill_txt}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------


def format_standings(ds: SoccerData, result: StandingsResult, limit: int | None = None) -> str:
    title = f"{comp_name(result.competition)} {result.season} Final Standings (calculated from matches):"
    if not result.rows:
        return title + "\n- No matches found for this season in the dataset."
    lines = [title]
    relegated_ids = {row.team_id for row in result.relegated}
    rows = result.rows if limit is None else result.rows[:limit]
    for row in rows:
        marker = " - Champion" if row.position == 1 else ""
        if row.team_id in relegated_ids:
            marker += " (relegation zone)"
        lines.append(
            f"{row.position}. {team_name(ds, row.team_id)} - {row.points} pts "
            f"({row.wins}W, {row.draws}D, {row.losses}L), "
            f"GF {row.goals_for}, GA {row.goals_against}{marker}"
        )
    if limit is not None and len(result.rows) > len(rows):
        lines.append(f"... ({len(result.rows) - len(rows)} more teams)")
    top_scorer = max(result.rows, key=lambda r: r.goals_for)
    lines.append("")
    lines.append(
        f"Most goals scored: {team_name(ds, top_scorer.team_id)} ({top_scorer.goals_for})"
    )
    lines.append(f"Note: table {'; '.join(result.notes)}.")
    return "\n".join(lines)


def _tie_line(ds: SoccerData, tie: KnockoutTie) -> str:
    legs = " / ".join(
        f"{team_name(ds, leg.home_team)} {leg.home_goals}-{leg.away_goals} "
        f"{team_name(ds, leg.away_team)}" for leg in tie.legs
    )
    if len(tie.legs) == 1:
        agg = ""
    else:
        goals_a = sum(
            leg.home_goals if leg.home_team == tie.team_a else leg.away_goals for leg in tie.legs
        )
        goals_b = sum(
            leg.away_goals if leg.home_team == tie.team_a else leg.home_goals for leg in tie.legs
        )
        agg = f" -- aggregate {team_name(ds, tie.team_a)} {goals_a}-{goals_b} {team_name(ds, tie.team_b)}"
    return f"- {legs}{agg}"


def format_finals(ds: SoccerData, results: list[FinalResult]) -> str:
    lines = [f"{comp_name(results[0].competition)} finals in dataset:"]
    for result in results:
        if not result.ties:
            note = result.note or "no final recorded"
            lines.append(f"{result.season}: {note}")
            continue
        for tie in result.ties:
            suffix = ""
            if len(tie.legs) > 1:
                if tie.winner:
                    suffix = f" -- {team_name(ds, tie.winner)} won on aggregate"
                else:
                    suffix = " -- level on aggregate (decided on penalties, not in dataset)"
            else:
                suffix = (
                    f" -- {team_name(ds, tie.winner)} won"
                    if tie.winner
                    else " -- draw (decided on penalties, not in dataset)"
                )
            lines.append(f"{result.season}: {_tie_line(ds, tie)}{suffix}")
    return "\n".join(lines)


def format_champion(ds: SoccerData, result: ChampionResult) -> str:
    if result.comp_type == "league" and result.winner and result.standings:
        top = result.standings.champion
        return (
            f"{result.display} {result.season} champion: {result.winner.display_name}\n"
            f"- {top.points} pts ({top.wins}W, {top.draws}D, {top.losses}L)\n"
            f"- Runner-up: {team_name(ds, result.standings.rows[1].team_id)} "
            f"({result.standings.rows[1].points} pts)"
        )
    if result.final:
        lines = [f"{result.display} {result.season} final:"]
        for tie in result.final.ties:
            lines.append(_tie_line(ds, tie))
        if result.winner:
            lines.append(f"Champion: {result.winner.display_name}")
        elif result.decided_on_penalties:
            lines.append(
                "Final level on aggregate -- decided on penalties "
                "(shootout result not recorded in the dataset)."
            )
        return "\n".join(lines)
    return (
        f"{result.display} {result.season}: {result.note}"
        if result.note
        else f"No champion determinable for {result.display} {result.season}."
    )


def format_knockout(ds: SoccerData, bracket: dict[str, list[KnockoutTie]]) -> str:
    if not bracket:
        return "No knockout-stage matches found for this competition and season."
    lines = []
    for stage, ties in bracket.items():
        lines.append(f"{stage}:")
        for tie in ties:
            lines.append(_tie_line(ds, tie))
        lines.append("")
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def format_aggregates(agg: Aggregates, scope: str) -> str:
    if agg.matches == 0:
        return f"No matches found for {scope}."
    return (
        f"Statistics for {scope} ({agg.matches} matches):\n"
        f"- Average goals per match: {agg.avg_goals:.2f}\n"
        f"- Home win rate: {agg.home_win_rate * 100:.1f}%\n"
        f"- Draw rate: {agg.draw_rate * 100:.1f}%\n"
        f"- Away win rate: {agg.away_win_rate * 100:.1f}%\n"
        f"- Average home goals: {agg.home_goals / agg.matches:.2f}\n"
        f"- Average away goals: {agg.away_goals / agg.matches:.2f}"
    )


def format_biggest_wins(ds: SoccerData, matches: list[Match], scope: str) -> str:
    lines = [f"Biggest victories {scope}:"]
    if not matches:
        lines.append("- No matches found.")
        return "\n".join(lines)
    for i, match in enumerate(matches, start=1):
        lines.append(f"{i}. {_match_line(ds, match)}")
    return "\n".join(lines)


def format_derbies(ds: SoccerData, items: list[tuple[str, Match]]) -> str:
    lines = [f"Derby matches found in dataset: {len(items)}"]
    if not items:
        return "\n".join(lines + ["- No derby matches found for this filter."])
    for label, match in items:
        lines.append(f"- [{label}] {_match_line(ds, match)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entity / listing formats
# ---------------------------------------------------------------------------


def format_team_entity(entity: TeamEntity) -> str:
    lines = [f"{entity.display_name} (canonical id: {entity.team_id})"]
    if entity.state:
        lines.append(f"- State: {entity.state.upper()}")
    if entity.country:
        lines.append(f"- Country tag: {entity.country.upper()}")
    lines.append(f"- Matches in dataset: {entity.match_count}")
    if entity.competitions:
        lines.append("- Competitions played (seasons):")
        for comp_id in sorted(entity.competitions):
            seasons = sorted(entity.competitions[comp_id])
            lines.append(f"  - {comp_name(comp_id)}: {', '.join(seasons)}")
    if entity.fifa_club_names:
        lines.append(
            "- FIFA database club name(s): " + ", ".join(sorted(entity.fifa_club_names))
        )
    if entity.variants:
        top_variants = sorted(entity.variants.items(), key=lambda kv: -kv[1])[:6]
        lines.append(
            "- Name variants seen in the data: "
            + ", ".join(repr(v) for v, _ in top_variants)
        )
    return "\n".join(lines)


def format_competitions(coverages: list[CompetitionCoverage]) -> str:
    lines = ["Competitions in the dataset:"]
    for coverage in coverages:
        seasons = (
            f"{coverage.seasons[0]}-{coverage.seasons[-1]}" if coverage.seasons else "none"
        )
        src = ", ".join(
            f"{SOURCE_LABELS.get(source_id, source_id)} ({count})"
            for source_id, count in sorted(coverage.sources.items())
        )
        lines.append(
            f"- {coverage.display} ({coverage.comp_type}): {coverage.match_count} matches, "
            f"seasons {seasons}\n  sources: {src}"
        )
    return "\n".join(lines)


def format_teams(entities: list[TeamEntity], scope: str) -> str:
    lines = [f"Teams {scope}: {len(entities)}"]
    for entity in entities:
        lines.append(f"- {entity.display_name} ({entity.match_count} matches)")
    return "\n".join(lines)
