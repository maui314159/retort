"""Flat string-returning functions backing the MCP tools.

Kept separate from the FastMCP wiring so they can be unit-tested and reused
without a running MCP server. Every function accepts plain strings/ints
(team/competition names are normalized internally) and returns formatted
text following the specification's answer formats.
"""

from __future__ import annotations

from . import formatting as fmt
from . import queries as q
from .data import get_store


def dataset_summary() -> str:
    """Summarize the loaded datasets: row counts per source CSV, total
    matches/players/teams, competitions and seasons covered."""
    summary = q.dataset_summary(get_store())
    lines = ["Dataset summary:", "- Source files:"]
    for name, count in summary["sources"].items():
        lines.append(f"  - {name}: {count} rows")
    lines += [
        f"- Unified matches (deduplicated): {summary['unified_matches']} "
        f"({summary['played_matches']} with scores)",
        f"- Players: {summary['players']}",
        f"- Teams: {summary['teams']}",
        "- Competitions and seasons:",
    ]
    for comp, seasons in summary["seasons_by_competition"].items():
        lines.append(f"  - {comp}: {seasons[0]}-{seasons[-1]} ({len(seasons)} seasons)")
    return "\n".join(lines)


def list_competitions() -> str:
    """List every competition in the dataset with its seasons and match count."""
    result = q.list_competitions(get_store())
    lines = ["Competitions in dataset:"]
    for c in result["competitions"]:
        seasons = c["seasons"]
        span = f"{seasons[0]}-{seasons[-1]}" if seasons else "unknown"
        lines.append(
            f"- {c['competition']}: {c['matches']} matches, seasons {span}"
        )
    return "\n".join(lines)


def list_teams(competition: str | None = None, season: int | None = None) -> str:
    """List canonical team names, optionally for one competition/season.

    Args:
        competition: e.g. "Brasileirão", "Serie A", "Copa do Brasil",
            "Libertadores" (optional).
        season: e.g. 2019 (optional).
    """
    result = q.list_teams(get_store(), competition, season)
    scope = []
    if competition:
        scope.append(str(competition))
    if season:
        scope.append(str(season))
    header = f"Teams ({', '.join(scope)}):" if scope else "Teams:"
    return "\n".join([header, ", ".join(result["teams"]),
                      f"Total: {result['total']}"])


def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str = "any",
    stage: str | None = None,
    limit: int = 20,
) -> str:
    """Find matches by team, opponent, competition, season, date range or
    stage (e.g. "final", "semifinals", "group stage").

    Args:
        team: team name in any form ("Flamengo", "Flamengo-RJ", ...).
        opponent: second team for head-to-head style searches.
        competition: "Brasileirão"/"Serie A", "Serie B", "Serie C",
            "Copa do Brasil" or "Copa Libertadores".
        season: year, e.g. 2023.
        date_from / date_to: "YYYY-MM-DD", "DD/MM/YYYY" or "YYYY".
        venue: "any", "home" or "away".
        stage: e.g. "final", "semifinals", "quarterfinals", "group stage".
        limit: max matches to return (default 20).
    """
    result = q.search_matches(get_store(), team, opponent, competition, season,
                              date_from, date_to, venue, stage, limit)
    title_bits = [b for b in (team, f"vs {opponent}" if opponent else None,
                              competition, str(season) if season else None,
                              stage) if b]
    title = "Matches " + " ".join(title_bits) + ":" if title_bits else "Matches:"
    return fmt.format_matches(result, title)


def head_to_head(
    team1: str,
    team2: str,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """All matches between two teams plus the aggregate W/D/L record.
    Detects classic derbies (Fla-Flu, Gre-Nal, ...)."""
    result = q.head_to_head(get_store(), team1, team2, competition, season)
    return fmt.format_head_to_head(result)


def last_match(team1: str, team2: str) -> str:
    """The most recent match (date, score, competition) between two teams."""
    m = q.last_match(get_store(), team1, team2)
    return "Most recent match:\n" + fmt.match_line(m)


def find_derbies(season: int | None = None, competition: str | None = None) -> str:
    """Find matches between traditional rivals (Fla-Flu, Gre-Nal, Majestoso,
    Choque-Rei, Ba-Vi, ...) in a season/competition."""
    result = q.find_derbies(get_store(), season, competition)
    title = f"Derbies{f' in {season}' if season else ''}:"
    lines = [title]
    for m in result["matches"]:
        lines.append(fmt.match_line(m) + f" [{m['derby']}]")
    if not result["matches"]:
        lines.append("No derby matches found.")
    elif result["total"] > len(result["matches"]):
        lines.append(f"... ({result['total'] - len(result['matches'])} more)")
    return "\n".join(lines)


def team_stats(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "any",
) -> str:
    """Win/draw/loss record, goals for/against and win rate for a team.

    Args:
        team: team name in any form.
        competition: optional competition filter.
        season: optional year filter.
        venue: "any", "home" or "away".
    """
    stats = q.team_stats(get_store(), team, competition, season, venue)
    return fmt.format_team_stats(stats)


def team_competitions(team: str) -> str:
    """Which competitions and seasons a team has played in."""
    result = q.team_competitions(get_store(), team)
    lines = [f"{result['team']} competitions ({result['total_matches']} matches):"]
    for c in result["competitions"]:
        seasons = c["seasons"]
        span = f"{seasons[0]}-{seasons[-1]}" if seasons else "?"
        lines.append(f"- {c['competition']}: {c['matches']} matches ({span})")
    return "\n".join(lines)


def standings(season: int, competition: str = "serie a") -> str:
    """League table for a season, calculated from match results (3-1-0
    points, CBF tie-breakers). Marks the champion and relegation zone for
    Série A."""
    result = q.standings(get_store(), season, competition)
    return fmt.format_standings(result)


def top_scoring_teams(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Teams ranked by goals scored (optionally per competition/season)."""
    result = q.top_scoring_teams(get_store(), competition, season, limit)
    scope = " ".join(str(x) for x in (competition, season) if x) or "all competitions"
    return fmt.format_top_scoring(result, f"Top scoring teams ({scope}):")


def competition_stats(competition: str | None = None, season: int | None = None) -> str:
    """Goals averages and home/draw/away win rates for a competition/season
    (or the whole dataset when no filters are given)."""
    stats = q.competition_stats(get_store(), competition, season)
    return fmt.format_competition_stats(stats)


def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 10,
) -> str:
    """Largest victory margins in the dataset (optionally filtered)."""
    result = q.biggest_wins(get_store(), competition, season, team, limit)
    scope = " ".join(str(x) for x in (competition, season, team) if x) or "dataset"
    return fmt.format_biggest_wins(result, f"Biggest victories ({scope}):")


def best_home_records(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Teams with the best home win rate (min 5 home matches)."""
    result = q.best_home_records(get_store(), competition, season, 5, limit)
    scope = " ".join(str(x) for x in (competition, season) if x) or "all competitions"
    return fmt.format_records(result, f"Best home records ({scope}):")


def best_away_records(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Teams with the best away win rate (min 5 away matches)."""
    result = q.best_away_records(get_store(), competition, season, 5, limit)
    scope = " ".join(str(x) for x in (competition, season) if x) or "all competitions"
    return fmt.format_records(result, f"Best away records ({scope}):")


def compare_seasons(competition: str, season_a: int, season_b: int) -> str:
    """Compare aggregate stats (avg goals, home win rate, ...) between two
    seasons of a competition."""
    result = q.season_comparison(get_store(), competition, season_a, season_b)
    a, b = result["season_a"], result["season_b"]
    return "\n".join([
        f"{result['competition']}: {a['season']} vs {b['season']}",
        f"- Matches: {a['matches']} vs {b['matches']}",
        f"- Avg goals per match: {a['avg_goals_per_match']} vs "
        f"{b['avg_goals_per_match']} (delta {result['avg_goals_delta']:+})",
        f"- Home win rate: {a['home_win_rate']}% vs {b['home_win_rate']}%",
        f"- Draw rate: {a['draw_rate']}% vs {b['draw_rate']}%",
    ])


def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
) -> str:
    """Search FIFA players by name, nationality, club, position (e.g. "ST",
    "CB") or position group ("forward", "midfielder", "defender",
    "goalkeeper"), sorted by overall rating."""
    result = q.search_players(get_store(), name, nationality, club, position,
                              position_group, min_overall, limit)
    filters = [f"{k}={v}" for k, v in (
        ("name", name), ("nationality", nationality), ("club", club),
        ("position", position), ("group", position_group),
        ("min_overall", min_overall)) if v]
    title = "Players (" + ", ".join(filters) + "):" if filters else "Players:"
    return fmt.format_players(result, title)


def top_players(
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    limit: int = 10,
) -> str:
    """Highest-rated FIFA players, optionally filtered by nationality, club
    or position/group."""
    result = q.top_players(get_store(), nationality, club, position,
                           position_group, limit)
    filters = [str(v) for v in (nationality, club, position or position_group) if v]
    title = "Top-rated players" + (f" ({', '.join(filters)})" if filters else "") + ":"
    return fmt.format_players(result, title)


def player_profile(name: str) -> str:
    """Full profile for one player: club, position, ratings and top skills.
    Accepts partial names (e.g. "Gabriel Barbosa")."""
    return fmt.format_player_profile(q.player_profile(get_store(), name))
