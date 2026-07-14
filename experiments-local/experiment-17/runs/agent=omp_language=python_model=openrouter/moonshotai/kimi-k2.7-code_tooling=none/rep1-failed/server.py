"""MCP server exposing Brazilian soccer data as knowledge graph tools.

Run with either:

    python server.py

or the MCP CLI:

    mcp run server.py

The server loads all six CSV files at startup and answers questions about
matches, teams, players, competitions, and statistics.
"""

from __future__ import annotations

import json
import re

from mcp.server.fastmcp import FastMCP

from data_loader import DataStore
from queries import (
    average_goals_per_match,
    best_home_record,
    biggest_wins,
    competition_standings,
    find_matches,
    head_to_head,
    list_competitions,
    list_seasons,
    search_players,
    team_competitions,
    team_stats,
    top_players,
)

mcp = FastMCP("brazilian-soccer")
store = DataStore()


def _competition_year(question: str, default: str | None = None):
    """Extract a 4-digit year and a competition keyword from a question."""
    year_match = re.search(r"\b(20\d{2})\b", question)
    year = int(year_match.group(1)) if year_match else None
    comp = default
    q = question.lower()
    if "libertadores" in q:
        comp = "Copa Libertadores"
    elif "copa do brasil" in q or "brazilian cup" in q:
        comp = "Copa do Brasil"
    elif "brasileirão" in q or "brasileirao" in q or "serie a" in q:
        comp = "Brasileirão"
    return comp, year


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> str:
    """Find soccer matches filtered by team, opponent, competition, season or date range."""
    results = find_matches(
        store,
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    if not results:
        return "No matches found for those criteria."
    lines = [f"Found {len(results)} match(es):"]
    for m in results:
        extra = ""
        if m["round"]:
            extra += f" Round {m['round']}"
        if m["stage"]:
            extra += f" {m['stage']}"
        lines.append(
            f"- {m['date']}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({m['competition']} {m['season']}{extra})"
        )
    return "\n".join(lines)


@mcp.tool()
def get_team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> str:
    """Get a team's record, goals and win rate. Optionally filter by season, competition and venue."""
    stats = team_stats(store, team, season=season, competition=competition, venue=venue)
    if stats["matches"] == 0:
        return f"No matches found for {team} with the requested filters."
    venue_note = f" ({venue} only)" if venue else ""
    season_note = f" {season}" if season else ""
    comp_note = f" {competition}" if competition else ""
    return (
        f"{team}{venue_note}{season_note}{comp_note}:\n"
        f"- Matches: {stats['matches']}\n"
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}\n"
        f"- Win rate: {stats['win_rate']}%"
    )


@mcp.tool()
def get_head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 20,
) -> str:
    """Return match history and summary between two teams."""
    h2h = head_to_head(store, team_a, team_b, competition=competition, season=season, limit=limit)
    if h2h["matches"] == 0:
        return f"No matches found between {team_a} and {team_b}."
    lines = [
        f"{team_a} vs {team_b} — {h2h['matches']} matches",
        f"- {team_a} wins: {h2h['team_a_wins']}",
        f"- {team_b} wins: {h2h['team_b_wins']}",
        f"- Draws: {h2h['draws']}",
        f"- Goals: {team_a} {h2h['team_a_goals']} - {h2h['team_b_goals']} {team_b}",
        "",
        f"Most recent {len(h2h['match_list'])} matches:",
    ]
    for m in h2h["match_list"]:
        lines.append(
            f"- {m['date']}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({m['competition']} {m['season']})"
        )
    return "\n".join(lines)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 10,
) -> str:
    """Search FIFA player data by name, nationality, club or position."""
    results = search_players(
        store,
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        max_overall=max_overall,
        limit=limit,
    )
    if not results:
        return "No players found."
    lines = [f"Found {len(results)} player(s):"]
    for p in results:
        lines.append(
            f"- {p['name']} (OVR {p['overall']}, POS {p['position']}, "
            f"Club {p['club']}, Nat {p['nationality']})"
        )
    return "\n".join(lines)


@mcp.tool()
def get_top_players(
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> str:
    """Return the highest-rated players filtered by nationality, club or position."""
    results = top_players(store, nationality=nationality, club=club, position=position, limit=limit)
    if not results:
        return "No players found."
    lines = [f"Top {len(results)} player(s):"]
    for i, p in enumerate(results, 1):
        lines.append(
            f"{i}. {p['name']} - Overall: {p['overall']}, "
            f"Position: {p['position']}, Club: {p['club']}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_competition_standings(competition: str, season: int) -> str:
    """Calculate league standings (points, wins, draws, losses) for a competition and season."""
    standings = competition_standings(store, competition, season)
    if not standings:
        return f"No matches found for {competition} in {season}."
    lines = [f"{competition} {season} standings (calculated from matches):"]
    for row in standings:
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L) "
            f"GF {row['goals_for']} GA {row['goals_against']}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_biggest_wins(competition: str | None = None, season: int | None = None, limit: int = 10) -> str:
    """Return the biggest wins by goal margin, optionally filtered by competition or season."""
    results = biggest_wins(store, competition=competition, season=season, limit=limit)
    if not results:
        return "No matches found."
    lines = [f"Biggest victories ({len(results)} shown):"]
    for m in results:
        lines.append(
            f"- {m['date']}: {m['home_team']} {m['home_goal']}-{m['away_goal']} "
            f"{m['away_team']} ({m['competition']} {m['season']})"
        )
    return "\n".join(lines)


@mcp.tool()
def get_average_goals(competition: str | None = None, season: int | None = None) -> str:
    """Return average goals per match and the home-win percentage."""
    stats = average_goals_per_match(store, competition=competition, season=season)
    label = f" {competition}" if competition else ""
    label += f" {season}" if season else ""
    return (
        f"Dataset averages{label}:\n"
        f"- Matches: {stats['matches']}\n"
        f"- Average goals per match: {stats['average_goals']}\n"
        f"- Home win rate: {stats['home_win_rate']}%"
    )


@mcp.tool()
def get_best_home_record(competition: str | None = None) -> str:
    """Return the team with the best home record (minimum 5 home games)."""
    rec = best_home_record(store, competition=competition)
    if rec["matches"] == 0:
        return "No qualifying home records found."
    return (
        f"Best home record{' for ' + competition if competition else ''}: {rec['team']}\n"
        f"- Home matches: {rec['matches']}\n"
        f"- Wins: {rec['wins']}, Draws: {rec['draws']}, Losses: {rec['losses']}\n"
        f"- Goals For: {rec['goals_for']}, Goals Against: {rec['goals_against']}\n"
        f"- Win rate: {rec['win_rate']}%"
    )


@mcp.tool()
def get_team_competitions(team: str) -> str:
    """List the competitions and seasons a team has appeared in."""
    comps = team_competitions(store, team)
    if not comps:
        return f"No competitions found for {team}."
    lines = [f"{team} appears in:"]
    for c in comps:
        lines.append(f"- {c['competition']} {c['season']}: {c['matches']} matches")
    return "\n".join(lines)


@mcp.tool()
def list_competitions() -> str:
    """List all available competitions in the match data."""
    comps = list_competitions(store)
    return "Available competitions:\n" + "\n".join(f"- {c}" for c in comps)


@mcp.tool()
def list_seasons(competition: str | None = None) -> str:
    """List all seasons, optionally filtered to one competition."""
    seasons = list_seasons(store, competition=competition)
    if not seasons:
        return "No seasons found."
    header = f"Seasons{' for ' + competition if competition else ''}:"
    return header + " " + ", ".join(str(s) for s in seasons)


@mcp.tool()
def answer_question(question: str) -> str:
    """Natural-language facade for common Brazilian soccer questions.

    Tries to map the question to the structured tools above. For questions that
    are not recognised, returns a hint about the available tools.
    """
    q = question.lower()

    # Standings / champion / relegation
    if re.search(r"\b(won|standings|table)\b", q):
        comp, year = _competition_year(question)
        if comp and year:
            standings = competition_standings(store, comp, year)
            if not standings:
                return f"No matches found for {comp} in {year}."
            champion = standings[0]["team"]
            lines = [f"{comp} {year champion: {champion}"]
            for row in standings[:5]:
                lines.append(
                    f"{row['position']}. {row['team']} - {row['points']} pts "
                    f"({row['wins']}W, {row['draws']}D, {row['losses']}L)"
                )
            if "releg" in q and len(standings) >= 4:
                lines.append("Relegation zone:")
                for row in standings[-4:]:
                    lines.append(f"- {row['team']} ({row['points']} pts)")
            return "\n".join(lines)

    # Head-to-head
    verses = re.findall(
        r"(?:between|vs\.?|versus)\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s\-]+?)(?:\s+(?:and|&)\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s\-]+))?(?:\s+in\s+(\d{4}))?",
        question,
    )
    if not verses:
        # Try "A vs B" pattern
        m = re.search(r"([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s]+)\s+(?:vs\.?|versus)\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s]+)", question)
        if m:
            verses = [(m.group(1), m.group(2), None)]

    if verses and verses[0][0] and verses[0][1]:
        a = verses[0][0].strip(" ?")
        b = verses[0][1].strip(" ?")
        year = int(verses[0][2]) if verses[0][2] and verses[0][2].isdigit() else None
        comp, _ = _competition_year(question)
        return get_head_to_head(a, b, competition=comp, season=year)

    # Team stats
    team_match = re.search(
        r"(?:record|stats|statistics|performance)\s+(?:for\s+)?([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s\-]+?)(?:\s+in\s+(\d{4}))?",
        q,
    ) or re.search(
        r"([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s\-]+?)\s+(?:home record|away record|record)",
        q,
    )
    if team_match:
        team = team_match.group(1).strip(" ?")
        year = int(team_match.group(2)) if team_match.lastindex >= 2 and team_match.group(2) else None
        venue = None
        if "home" in q:
            venue = "home"
        elif "away" in q:
            venue = "away"
        comp, _ = _competition_year(question)
        return get_team_stats(team, season=year, competition=comp, venue=venue)

    # Player queries
    if "brazilian players" in q or "players from brazil" in q:
        limit = int(re.search(r"\btop\s+(\d+)", q).group(1)) if re.search(r"\btop\s+(\d+)", q) else 10
        return get_top_players(nationality="Brazil", limit=limit)

    if re.search(r"players?\s+(?:at|for|of|from)\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s\-]+)", q):
        club = re.search(r"players?\s+(?:at|for|of|from)\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s\-]+)", q).group(1).strip(" ?")
        return get_top_players(club=club, limit=10)

    if re.search(r"who\s+is\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s\-]+)", q):
        name = re.search(r"who\s+is\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\s\-]+)", q).group(1).strip(" ?")
        return search_players(name=name, limit=5)

    if re.search(r"top\s+brazilian\s+players", q):
        limit = int(re.search(r"\btop\s+(\d+)", q).group(1)) if re.search(r"\btop\s+(\d+)", q) else 10
        return get_top_players(nationality="Brazil", limit=limit)

    # Averages / biggest wins
    if re.search(r"average\s+goals", q):
        comp, year = _competition_year(question)
        return get_average_goals(competition=comp, season=year)

    if re.search(r"biggest\s+wins?", q):
        comp, year = _competition_year(question)
        return get_biggest_wins(competition=comp, season=year, limit=10)

    return (
        "I'm not sure how to answer that directly. Try the dedicated tools:\n"
        "- search_matches\n"
        "- get_team_stats\n"
        "- get_head_to_head\n"
        "- search_players / get_top_players\n"
        "- get_competition_standings\n"
        "- get_biggest_wins / get_average_goals"
    )


if __name__ == "__main__":
    mcp.run()
