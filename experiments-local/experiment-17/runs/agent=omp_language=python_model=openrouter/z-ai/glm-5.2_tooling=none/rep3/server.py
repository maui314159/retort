"""MCP server exposing the Brazilian soccer query engine to LLMs.

Context: This module wraps :class:`queries.QueryEngine` as a set of MCP tools
and resources so an LLM client (Claude, etc.) can answer natural-language
questions about Brazilian soccer. Each tool returns a compact text rendering of
the structured query result so the LLM can cite concrete figures; the
underlying structured payload is also embedded as JSON for callers that want
to parse it. The data store loads once per process (see
:func:`data_loader.get_store`) and is shared by the test suite.

Run as a stdio MCP server::

    python server.py

or register the ``mcp`` console script with your MCP client pointing at this
file. The server is read-only: no tool mutates the underlying CSVs.
"""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

import data_loader
import queries


# ---------------------------------------------------------------------------
# Server + engine wiring
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Brazilian Soccer MCP",
    instructions=(
        "Query Brazilian soccer data (Brasileirão, Copa do Brasil, Copa "
        "Libertadores, Serie B/C, historical Brasileirão 2003-2019 and FIFA "
        "players). Use search_matches for fixture lookups, team_stats for "
        "win/loss/goal records, head_to_head to compare two teams, "
        "search_players / top_players for FIFA player data, "
        "competition_standings for league tables, and biggest_wins / "
        "average_goals / best_record for analytics. Team names accept any "
        "variant (e.g. 'Flamengo', 'Flamengo-RJ', 'Palmeiras-SP')."
    ),
)


def _engine() -> queries.QueryEngine:
    """Return a process-cached engine (loads CSVs once)."""
    return queries.QueryEngine(data_loader.get_store())


def _render(title: str, payload: dict, bullets: list[str]):
    """Render a compact text answer with an embedded JSON payload tail.

    The LLM-facing text is the human-readable ``title`` + ``bullets``; the
    JSON tail lets tooling that wants structured data parse it without
    re-querying.
    """
    lines = [title, ""]
    lines.extend(bullets)
    lines.append("")
    lines.append("--- structured payload (json) ---")
    lines.append(json.dumps(payload, ensure_ascii=False, default=str))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------
@mcp.tool()
def search_matches(team: Optional[str] = None,
opponent: Optional[str] = None,
competition: Optional[str] = None,
season: Optional[int] = None,
venue: Optional[str] = None,
date_from: Optional[str] = None,
date_to: Optional[str] = None,
limit: int = 50,):
    """Find matches by team, opponent, competition, season, venue or date range.

    Args:
        team: Team name (any variant, e.g. "Flamengo", "Palmeiras-SP").
        opponent: Opponent team name (use with team for head-to-head listings).
        competition: "Brasileirão", "Copa do Brasil", "Libertadores",
            "Serie A", "Serie B", "Serie C", or "Historical Brasileirão".
        season: Year, e.g. 2019.
        venue: "home", "away", or "either" (default).
        date_from: ISO date "YYYY-MM-DD" (inclusive).
        date_to: ISO date "YYYY-MM-DD" (inclusive).
        limit: Max matches to return (default 50).
    """
    eng = _engine()
    res = eng.search_matches(team=team, opponent=opponent,
                             competition=competition, season=season,
                             venue=venue, date_from=date_from, date_to=date_to,
                             limit=limit)
    bullets = [f"Total matches in dataset: {res['count']} "
               f"(showing {res['returned']})"]
    for m in res["matches"]:
        hg = m["home_goal"] if m["home_goal"] is not None else "?"
        ag = m["away_goal"] if m["away_goal"] is not None else "?"
        side = f" [{m['team_side']}]" if m.get("team_side") else ""
        bullets.append(
            f"- {m['date'] or 'unknown date'}: {m['home_team']} {hg}-{ag} "
            f"{m['away_team']} ({m['competition']}, {m['stage']}){side}")
    title = "Matches"
    if team:
        title += f" for {team}"
    if opponent:
        title += f" vs {opponent}"
    extras = []
    if competition:
        extras.append(competition)
    if season:
        extras.append(str(season))
    if extras:
        title += f" [{', '.join(extras)}]"
    return _render(title, res, bullets)


@mcp.tool()
def head_to_head(team_a: str, team_b: str,
                 competition: Optional[str] = None,
                 season: Optional[int] = None):
    """Compare two teams head-to-head across the dataset.

    Returns matches played, wins/draws/losses for each side, goals, and the
    individual match list.
    """
    eng = _engine()
    res = eng.head_to_head(team_a, team_b, competition=competition,
                           season=season)
    bullets = [
        f"Matches played: {res['matches_played']}",
        f"{res['team_a']}: {res['team_a_wins']} wins, "
        f"{res['team_b_goals']} goals for",
        f"{res['team_b']}: {res['team_b_wins']} wins, "
        f"{res['team_a_goals']} goals for",
        f"Draws: {res['draws']}",
    ]
    for m in res["matches"][:50]:
        hg = m["home_goal"] if m["home_goal"] is not None else "?"
        ag = m["away_goal"] if m["away_goal"] is not None else "?"
        bullets.append(f"- {m['date'] or 'unknown'}: {m['home_team']} {hg}-{ag} "
                       f"{m['away_team']} ({m['competition']})")
    if len(res["matches"]) > 50:
        bullets.append(f"... ({len(res['matches']) - 50} more)")
    return _render(f"{team_a} vs {team_b} — head-to-head", res, bullets)


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------
@mcp.tool()
def team_stats(team: str, season: Optional[int] = None,
               competition: Optional[str] = None,
               venue: Optional[str] = None):
    """Return win/loss/draw records and goals for a team.

    Args:
        team: Team name (any variant).
        season: Optional year filter.
        competition: Optional competition filter.
        venue: "home", "away", or "either" (default).
    """
    eng = _engine()
    res = eng.team_stats(team, season=season, competition=competition,
                         venue=venue)
    bullets = [
        f"Matches: {res['matches']}",
        f"Wins: {res['wins']}, Draws: {res['draws']}, Losses: {res['losses']}",
        f"Goals For: {res['goals_for']}, Goals Against: {res['goals_against']}",
        f"Win rate: {res['win_rate']}%",
    ]
    if res["by_competition"]:
        bullets.append("By competition:")
        for comp, b in res["by_competition"].items():
            bullets.append(f"  - {comp}: {b['matches']} matches "
                           f"({b['wins']}W {b['draws']}D {b['losses']}L)")
    scope = []
    if season:
        scope.append(str(season))
    if competition:
        scope.append(competition)
    if venue and venue != "either":
        scope.append(venue)
    suffix = f" ({', '.join(scope)})" if scope else ""
    return _render(f"{team} record{suffix}", res, bullets)


@mcp.tool()
def team_competitions(team: str):
    """List all competitions and seasons a team appears in across the dataset."""
    eng = _engine()
    res = eng.team_competitions(team)
    bullets = [f"{team} appears in {len(res['competitions'])} competitions:"]
    for comp, info in res["competitions"].items():
        seasons = ", ".join(str(s) for s in info["seasons"]) or "n/a"
        bullets.append(f"  - {comp}: {info['matches']} matches "
                       f"(seasons: {seasons})")
    return _render(f"Competitions for {team}", res, bullets)


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------
@mcp.tool()
def search_players(name: Optional[str] = None,
                   nationality: Optional[str] = None,
                   club: Optional[str] = None,
                   position: Optional[str] = None,
                   min_overall: Optional[int] = None,
                   limit: int = 25):
    """Search FIFA player data by name, nationality, club, position or rating.

    Args:
        name: Substring of player name (e.g. "Neymar").
        nationality: Country (e.g. "Brazil").
        club: Club name substring (e.g. "Flamengo", "Real Madrid").
        position: FIFA position code (ST, LW, CDM, GK, ...).
        min_overall: Minimum FIFA overall rating.
        limit: Max players to return (default 25).
    """
    eng = _engine()
    res = eng.search_players(name=name, nationality=nationality, club=club,
                             position=position, min_overall=min_overall,
                             limit=limit)
    bullets = [f"Found {res['count']} players (showing {res['returned']}):"]
    for p in res["players"]:
        bullets.append(
            f"- {p['name']} (OVR {p['overall']}, {p['position']}, "
            f"{p['nationality']}, {p['club'] or 'no club'})")
    return _render("Player search", res, bullets)


@mcp.tool()
def top_players(nationality: Optional[str] = None,
                club: Optional[str] = None, limit: int = 10):
    """Return the highest-rated FIFA players, optionally filtered.

    Args:
        nationality: Country filter (e.g. "Brazil").
        club: Club name substring.
        limit: Number of players (default 10).
    """
    eng = _engine()
    res = eng.top_players(nationality=nationality, club=club, limit=limit)
    bullets = [f"Top {res['returned']} players"
               + (f" from {nationality}" if nationality else "")
               + (f" at {club}" if club else "") + ":"]
    for i, p in enumerate(res["players"], 1):
        bullets.append(f"{i}. {p['name']} - Overall {p['overall']}, "
                       f"{p['position']}, {p['club']}")
    return _render("Top players", res, bullets)


@mcp.tool()
def brazilian_players_by_club(limit: Optional[int] = None):
    """Summarize Brazilian players grouped by their club.

    Useful for "which Brazilian clubs have Brazilian players in the FIFA data".
    """
    eng = _engine()
    res = eng.brazilian_players_by_club(limit=limit)
    bullets = [f"Brazilian players across {len(res['clubs'])} clubs:"]
    for c in res["clubs"]:
        bullets.append(f"- {c['club']}: {c['players']} players "
                       f"(avg rating {c['avg_overall']}, top: {c['top']})")
    return _render("Brazilian players by club", res, bullets)


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------
@mcp.tool()
def competition_standings(competition: str,
                          season: Optional[int] = None,
                          top: Optional[int] = None):
    """Calculate league standings from match results.

    Args:
        competition: e.g. "Brasileirão", "Serie B", "Copa do Brasil".
        season: Year. When omitted, aggregates all seasons.
        top: Limit to top N teams.
    """
    eng = _engine()
    res = eng.competition_standings(competition, season=season, top=top)
    bullets = []
    if res["champion"]:
        bullets.append(f"Champion: {res['champion']}")
    bullets.append(f"{'Pos':>3} Team{'':<24} Pts  P  W  D  L  GF GA")
    for s in res["standings"]:
        bullets.append(
            f"{s['position']:>3} {s['team']:<28} {s['points']:>3} "
            f"{s['played']:>2} {s['wins']:>2} {s['draws']:>2} "
            f"{s['losses']:>2} {s['goals_for']:>3} {s['goals_against']:>3}")
    scope = f" {season}" if season else " (all seasons)"
    return _render(f"{competition}{scope} standings", res, bullets)


@mcp.tool()
def competition_seasons(competition: str):
    """List the seasons available for a competition."""
    eng = _engine()
    res = eng.competition_seasons(competition)
    bullets = [f"{res['competition']}: {', '.join(str(s) for s in res['seasons'])}"]
    return _render(f"Seasons for {competition}", res, bullets)


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------
@mcp.tool()
def biggest_wins(competition: Optional[str] = None,
                 season: Optional[int] = None, limit: int = 10):
    """Return the largest victory margins in the dataset."""
    eng = _engine()
    res = eng.biggest_wins(competition=competition, season=season, limit=limit)
    bullets = [f"Biggest wins ({res['count']} shown):"]
    for w in res["biggest_wins"]:
        bullets.append(f"- {w['date'] or 'unknown'}: {w['winner']} "
                       f"{w['winner_goals']}-{w['loser_goals']} {w['loser']} "
                       f"(margin {w['margin']}, {w['competition']})")
    return _render("Biggest wins", res, bullets)


@mcp.tool()
def average_goals(competition: Optional[str] = None,
                  season: Optional[int] = None):
    """Compute average goals per match and home/away/draw win rates."""
    eng = _engine()
    res = eng.average_goals(competition=competition, season=season)
    bullets = [
        f"Matches: {res['matches']}",
        f"Total goals: {res['total_goals']}",
        f"Average goals per match: {res['average_goals_per_match']}",
        f"Home win rate: {res['home_win_rate']}%",
        f"Away win rate: {res['away_win_rate']}%",
        f"Draw rate: {res['draw_rate']}%",
    ]
    scope = f" {competition}" if competition else " (all competitions)"
    scope += f" {season}" if season else ""
    return _render(f"Average goals{scope}", res, bullets)


@mcp.tool()
def best_record(venue: str = "home",
                competition: Optional[str] = None,
                season: Optional[int] = None, limit: int = 10):
    """Rank teams by win rate for a given venue (home/away).

    Args:
        venue: "home" or "away".
        competition: Optional competition filter.
        season: Optional season filter.
        limit: Number of teams (default 10).
    """
    eng = _engine()
    res = eng.best_record(venue=venue, competition=competition,
                          season=season, limit=limit)
    bullets = [f"Best {venue} records ({len(res['teams'])} shown):"]
    for t in res["teams"]:
        bullets.append(f"- {t['team']}: {t['win_rate']}% win rate "
                       f"({t['wins']}W {t['draws']}D {t['losses']}L over "
                       f"{t['matches']} matches)")
    return _render(f"Best {venue} record", res, bullets)


@mcp.tool()
def derbies(season: Optional[int] = None,
            competition: Optional[str] = None,
            limit: Optional[int] = None):
    """List traditional Brazilian derby matches (Fla-Flu, Gre-Nal, etc.)."""
    eng = _engine()
    res = eng.derbies(season=season, competition=competition, limit=limit)
    bullets = [f"{res['count']} derbies found (showing {res['returned']}):"]
    for d in res["derbies"]:
        hg = d["home_goal"] if d["home_goal"] is not None else "?"
        ag = d["away_goal"] if d["away_goal"] is not None else "?"
        bullets.append(f"- {d['date'] or 'unknown'}: {d['home_team']} {hg}-{ag} "
                       f"{d['away_team']} ({d['competition']})")
    return _render("Derbies", res, bullets)


# ---------------------------------------------------------------------------
# Catalog resource
# ---------------------------------------------------------------------------
@mcp.tool()
def catalog():
    """Return a catalog of available competitions, seasons, team and player counts."""
    eng = _engine()
    res = eng.catalog()
    bullets = [
        f"Competitions: {', '.join(res['competitions'])}",
        f"Matches: {res['match_count']}",
        f"Teams: {res['team_count']}",
        f"Players: {res['player_count']}",
        "Seasons by competition:",
    ]
    for comp, seasons in res["seasons_by_competition"].items():
        bullets.append(f"  - {comp}: {', '.join(str(s) for s in seasons)}")
    return _render("Brazilian Soccer data catalog", res, bullets)


@mcp.resource("brasileirao://catalog")
def catalog_resource():
    """Static resource exposing the data catalog."""
    return catalog()


@mcp.resource("brasileirao://competitions")
def competitions_resource():
    """Static resource listing all competitions and their seasons."""
    eng = _engine()
    res = eng.catalog()
    lines = [f"{c}: {', '.join(str(s) for s in res['seasons_by_competition'][c])}"
             for c in res["competitions"]]
    return "\n".join(lines)


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
