"""Brazilian Soccer MCP Server.

Exposes the soccer datasets as MCP tools so an LLM can answer natural
language questions about Brazilian players, teams, matches, and
competitions.

Run with:
    python server.py            # stdio transport
"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))

from brazilian_soccer import SoccerData, SoccerQueries

mcp = FastMCP("brazilian-soccer")

_data = SoccerData()
_q = SoccerQueries(_data)


@mcp.tool()
def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 25,
) -> str:
    """Find matches by team, opponent, competition, season, or date range.

    Dates use ISO format (YYYY-MM-DD). Competition can be e.g.
    'Brasileirão', 'Copa do Brasil', or 'Libertadores'. Returns formatted
    match lines with date, score, and competition.
    """
    matches = _q.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return _q.format_match_list(matches)


@mcp.tool()
def head_to_head(team_a: str, team_b: str, limit: int = 20) -> str:
    """Get the head-to-head record between two teams across all datasets."""
    matches = _q.find_matches(team=team_a, opponent=team_b, limit=limit)
    summary = _q.head_to_head_summary(team_a, team_b)
    lines = [f"{team_a} vs {team_b}:"]
    lines.append(_q.format_match_list(matches, total=summary["matches"]))
    lines.append(
        f"\nHead-to-head in dataset: {team_a} {summary['team_a_wins']} wins, "
        f"{team_b} {summary['team_b_wins']} wins, {summary['draws']} draws"
    )
    return "\n".join(lines)


@mcp.tool()
def last_match_between(team_a: str, team_b: str) -> str:
    """Find the most recent match between two teams."""
    m = _q.last_match_between(team_a, team_b)
    if not m:
        return f"No matches found between {team_a} and {team_b}."
    return _q.format_match_list([m])


@mcp.tool()
def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> str:
    """Get a team's win/loss/draw record and goals.

    venue: 'home', 'away', or omitted for all matches.
    """
    stats = _q.team_stats(team=team, season=season, competition=competition, venue=venue)
    return _q.format_team_stats(stats)


@mcp.tool()
def compare_teams(team_a: str, team_b: str) -> str:
    """Compare two teams' overall records and head-to-head history."""
    sa = _q.team_stats(team_a)
    sb = _q.team_stats(team_b)
    h2h = _q.head_to_head_summary(team_a, team_b)
    return "\n\n".join(
        [
            _q.format_team_stats(sa),
            _q.format_team_stats(sb),
            (
                f"Head-to-head: {team_a} {h2h['team_a_wins']} wins, "
                f"{team_b} {h2h['team_b_wins']} wins, {h2h['draws']} draws "
                f"in {h2h['matches']} matches"
            ),
        ]
    )


@mcp.tool()
def standings(competition: str, season: int) -> str:
    """Calculate and return the league table for a competition and season.

    Uses 3 points per win. Works for Brasileirão seasons.
    """
    rows = _q.standings(competition, season)
    return _q.format_standings(rows, competition, season)


@mcp.tool()
def champion(competition: str, season: int) -> str:
    """Return the champion (top of calculated standings) for a season."""
    rows = _q.standings(competition, season)
    if not rows:
        return f"No data for {competition} {season}."
    top = rows[0]
    return (
        f"{competition} {season} champion (calculated): {top['team']} - "
        f"{top['points']} pts ({top['wins']}W, {top['draws']}D, {top['losses']}L)"
    )


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    limit: int = 20,
) -> str:
    """Search FIFA player data by name, nationality, club, or position.

    Results are ordered by Overall rating (descending).
    """
    players = _q.search_players(
        name=name, nationality=nationality, club=club, position=position, limit=limit
    )
    return _q.format_players(players)


@mcp.tool()
def top_players_at_club(club: str, limit: int = 10) -> str:
    """List the highest-rated players at a club."""
    players = _q.search_players(club=club, limit=limit)
    if not players:
        return f"No players found for club {club}."
    return f"Top-rated players at {players[0].get('Club')}:\n" + _q.format_players(players)


@mcp.tool()
def team_competitions(team: str) -> str:
    """List which competitions a team has matches in, with counts."""
    summary = _q.matches_per_team_summary(team)
    if not summary["competitions"]:
        return f"No matches found for {team}."
    lines = [f"{team} matches by competition:"]
    for comp, count in sorted(summary["competitions"].items(), key=lambda kv: -kv[1]):
        lines.append(f"- {comp}: {count} matches")
    return "\n".join(lines)


@mcp.tool()
def competition_stats(competition: str | None = None, season: int | None = None) -> str:
    """Aggregate statistics: average goals per match, home/away win rates."""
    s = _q.competition_stats(competition=competition, season=season)
    label = f"{s['competition']}" + (f" {s['season']}" if s["season"] else "")
    return (
        f"{label}:\n"
        f"- Matches: {s['matches']}\n"
        f"- Average goals per match: {s['avg_goals_per_match']}\n"
        f"- Home wins: {s['home_wins']} ({s['home_win_rate']}%)\n"
        f"- Away wins: {s['away_wins']}\n"
        f"- Draws: {s['draws']}"
    )


@mcp.tool()
def biggest_wins(competition: str | None = None, limit: int = 10) -> str:
    """Show the biggest victories (largest goal margins) in the dataset."""
    return _q.format_biggest_wins(_q.biggest_wins(competition=competition, limit=limit))


@mcp.tool()
def best_team_record(venue: str = "home", competition: str | None = None, min_matches: int = 50) -> str:
    """Rank teams by win rate at a venue ('home' or 'away')."""
    ranked = _q.best_team_record(venue=venue, competition=competition, min_matches=min_matches)
    if not ranked:
        return "No teams met the minimum match threshold."
    lines = [f"Best {venue} records:"]
    for i, r in enumerate(ranked[:10], 1):
        lines.append(f"{i}. {r['team']} - {r['win_rate']}% ({r['wins']}W / {r['matches']} matches)")
    return "\n".join(lines)


@mcp.tool()
def dataset_overview() -> str:
    """Overview of loaded datasets: match counts and competitions."""
    lines = [f"Matches loaded: {len(_data.matches)}", f"Players loaded: {len(_data.players)}", "Competitions:"]
    for comp in _data.competitions():
        count = sum(1 for m in _data.matches if m.competition == comp)
        lines.append(f"- {comp}: {count} matches")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
