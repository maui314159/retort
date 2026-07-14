"""FastMCP server exposing Brazilian-soccer query tools.

CONTEXT
-------
This module wraps the pure query functions in :mod:`brazilian_soccer.queries`
as MCP tools that return human-readable, formatted text (matching the
answer formats in the specification).  The heavy lifting -- data loading,
team-name normalisation, statistics -- lives in the data/query layers; the
server only formats.

Run with ``python -m brazilian_soccer`` (stdio transport) or import
:data:`mcp` to embed the server elsewhere.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import queries as Q
from .data_loader import get_data

# Single shared Data instance (cached on disk via lru_cache in data_loader).
_data = get_data()

mcp: FastMCP = FastMCP("brazilian-soccer")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _score(m: dict) -> str:
    hg = m.get("home_goals")
    ag = m.get("away_goals")
    if hg is None or ag is None:
        return "(not played)"
    return f"{hg}-{ag}"


def _match_line(m: dict) -> str:
    date = m.get("date") or "?"
    bits = [f"- {date}: {m['home']} {_score(m)} {m['away']}"]
    ctx = []
    if m.get("competition"):
        ctx.append(m["competition"])
    if m.get("round"):
        ctx.append(f"Round {m['round']}")
    if m.get("stage"):
        ctx.append(m["stage"])
    if ctx:
        bits.append(f"({', '.join(ctx)})")
    return " ".join(bits)


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------

@mcp.tool(structured_output=False)
def search_matches(team: Optional[str] = None, opponent: Optional[str] = None,
                   competition: Optional[str] = None,
                   season: Optional[int] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   venue: str = "either", limit: int = 50) -> str:
    """Search matches by team, opponent, competition, season and/or date.

    Args:
        team: Team name (home, away or either per `venue`).
        opponent: Opponent team name.
        competition: e.g. "Brasileirão", "Copa do Brasil", "Libertadores".
        season: Year (e.g. 2023).
        start_date / end_date: ISO dates "YYYY-MM-DD".
        venue: "home", "away" or "either" (default).
        limit: Max matches to return (0 = no cap).
    """
    matches = Q.search_matches(_data, team=team, opponent=opponent,
                               competition=competition, season=season,
                               start_date=start_date, end_date=end_date,
                               venue=venue, limit=limit)
    if not matches:
        return "No matches found for the given criteria."
    lines = [f"{len(matches)} match(es) found:"]
    lines.extend(_match_line(m) for m in matches)
    if limit and len(matches) == limit:
        lines.append(f"... (capped at {limit}; more may exist)")
    return "\n".join(lines)


@mcp.tool(structured_output=False)
def last_match_between(team_a: str, team_b: str) -> str:
    """Return the most recent match between two teams."""
    m = Q.last_match(_data, team_a, team_b)
    if not m:
        return f"No matches found between {team_a} and {team_b}."
    return _match_line(m)


@mcp.tool(structured_output=False)
def head_to_head(team_a: str, team_b: str,
                 competition: Optional[str] = None,
                 season: Optional[int] = None) -> str:
    """Head-to-head record between two teams (optionally filtered)."""
    h = Q.head_to_head(_data, team_a, team_b, competition=competition,
                       season=season)
    if h["matches"] == 0:
        return f"No matches found between {h['team_a']} and {h['team_b']}."
    lines = [
        f"Head-to-head: {h['team_a']} vs {h['team_b']}",
        f"- Matches: {h['matches']}",
        (f"- {h['team_a']} wins: {h['team_a_wins']}, "
         f"{h['team_b']} wins: {h['team_b_wins']}, draws: {h['draws']}"),
        (f"- Goals: {h['team_a']} {h['team_a_goals']}, "
         f"{h['team_b']} {h['team_b_goals']}"),
        "Recent:",
    ]
    for m in h["matches_list"][:10]:
        lines.append("  " + _match_line(m).lstrip("- "))
    if len(h["matches_list"]) > 10:
        lines.append(f"  ... ({len(h['matches_list']) - 10} more)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------

@mcp.tool(structured_output=False)
def get_team_stats(team: str, season: Optional[int] = None,
                   competition: Optional[str] = None,
                   venue: Optional[str] = None) -> str:
    """Aggregate record (wins/draws/losses, goals, win rate) for a team.

    Args:
        team: Team name.
        season: Optional year filter.
        competition: Optional competition filter.
        venue: None (all), "home" or "away".
    """
    st = Q.team_stats(_data, team, season=season, competition=competition,
                      venue=venue)
    label = st["team"]
    scope = []
    if season:
        scope.append(str(season))
    if competition:
        scope.append(competition)
    if venue:
        scope.append(f"{venue} only")
    title = f"{label} record" + (f" ({', '.join(scope)})" if scope else "")
    lines = [
        title,
        f"- Matches: {st['matches']}",
        f"- Wins: {st['wins']}, Draws: {st['draws']}, Losses: {st['losses']}",
        f"- Goals For: {st['goals_for']}, Goals Against: {st['goals_against']}",
        f"- Points: {st['points']}, Win rate: {st['win_rate']:.1%}",
    ]
    if "home" in st:
        h, a = st["home"], st["away"]
        lines.append(f"- Home: {h['wins']}W {h['draws']}D {h['losses']}L "
                     f"({h['win_rate']:.1%})")
        lines.append(f"- Away: {a['wins']}W {a['draws']}D {a['losses']}L "
                     f"({a['win_rate']:.1%})")
    return "\n".join(lines)


@mcp.tool(structured_output=False)
def team_competitions(team: str) -> str:
    """List the competitions a team has matches in, with counts."""
    comps = Q.team_competitions(_data, team)
    if not comps:
        return f"No matches found for {team}."
    lines = [f"Competitions for {_data_team_name(_data, team)}:"]
    lines.extend(f"- {c}: {n} matches" for c, n in comps.items())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------

@mcp.tool(structured_output=False)
def competition_standings(competition: str, season: int,
                          top: int = 20) -> str:
    """Calculate league standings for a competition+season (3 pts/win)."""
    table = Q.competition_standings(_data, competition, season, top=top)
    if not table:
        return (f"No data for {competition} {season}.")
    lines = [f"{competition} {season} standings ({len(table)} teams):"]
    for i, r in enumerate(table, 1):
        champ = " - Champion" if i == 1 else ""
        lines.append(
            f"{i}. {r['team']} - {r['points']} pts "
            f"({r['wins']}W, {r['draws']}D, {r['losses']}L, "
            f"GF {r['goals_for']}, GA {r['goals_against']}){champ}")
    return "\n".join(lines)


@mcp.tool(structured_output=False)
def competition_champion(competition: str, season: int) -> str:
    """Return the champion (standings leader) of a competition+season."""
    champ = Q.competition_champion(_data, competition, season)
    if not champ:
        return f"No data for {competition} {season}."
    return f"{competition} {season} champion: {champ}"


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

@mcp.tool(structured_output=False)
def biggest_wins(competition: Optional[str] = None,
                 season: Optional[int] = None, limit: int = 10) -> str:
    """Largest goal-margin victories, biggest first."""
    wins = Q.biggest_wins(_data, competition=competition, season=season,
                          limit=limit)
    if not wins:
        return "No finished matches found for the given criteria."
    lines = ["Biggest victories:"]
    for i, w in enumerate(wins, 1):
        lines.append(f"{i}. {w['date']}: {w['home']} {w['home_goals']}-"
                     f"{w['away_goals']} {w['away']} ({w['competition']}, "
                     f"margin {w['margin']})")
    return "\n".join(lines)


@mcp.tool(structured_output=False)
def average_goals(competition: Optional[str] = None,
                  season: Optional[int] = None) -> str:
    """Average goals per match plus home/away/draw win rates."""
    s = Q.average_goals(_data, competition=competition, season=season)
    if s["matches"] == 0:
        return "No finished matches found for the given criteria."
    return (f"Statistics ({s['matches']} matches):\n"
            f"- Average goals per match: {s['avg_goals']}\n"
            f"- Total goals: {s['total_goals']}\n"
            f"- Home win rate: {s['home_win_rate']:.1%}\n"
            f"- Away win rate: {s['away_win_rate']:.1%}\n"
            f"- Draw rate: {s['draw_rate']:.1%}")


@mcp.tool(structured_output=False)
def best_record(venue: str = "home", competition: Optional[str] = None,
                season: Optional[int] = None, limit: int = 5,
                min_matches: int = 10) -> str:
    """Rank teams by win rate in a venue ('home' or 'away')."""
    rows = Q.best_record(_data, venue=venue, competition=competition,
                         season=season, limit=limit, min_matches=min_matches)
    if not rows:
        return "No teams meet the minimum-match threshold."
    lines = [f"Best {venue} record:"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['team']} - {r['win_rate']:.1%} "
                     f"({r['wins']}W {r['draws']}D {r['losses']}L "
                     f"in {r['matches']} matches)")
    return "\n".join(lines)


@mcp.tool(structured_output=False)
def derby_matches(season: Optional[int] = None,
                  competition: Optional[str] = None) -> str:
    """List matches between traditional rival pairs (derbies)."""
    derbs = Q.derby_matches(_data, season=season, competition=competition)
    if not derbs:
        return "No derby matches found for the given criteria."
    lines = [f"{len(derbs)} derby match(es):"]
    for m in derbs[:50]:
        lines.append(f"- [{m.get('derby', '?')}] {m['date']}: "
                     f"{m['home']} {_score(m)} {m['away']} ({m['competition']})")
    if len(derbs) > 50:
        lines.append(f"... ({len(derbs) - 50} more)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

@mcp.tool(structured_output=False)
def search_players(name: Optional[str] = None,
                   nationality: Optional[str] = None,
                   club: Optional[str] = None,
                   position: Optional[str] = None,
                   position_group: Optional[str] = None,
                   min_overall: Optional[int] = None,
                   limit: int = 50) -> str:
    """Search FIFA players by name, nationality, club, position or rating."""
    players = Q.search_players(_data, name=name, nationality=nationality,
                               club=club, position=position,
                               position_group_name=position_group,
                               min_overall=min_overall, limit=limit)
    if not players:
        return "No players found for the given criteria."
    lines = [f"{len(players)} player(s) found:"]
    for p in players:
        bits = [f"- {p['Name']} (Overall {p['Overall']}"]
        if p.get("Position"):
            bits.append(f", {p['Position']}")
        bits.append(f", {p['Nationality']}, {p['Club']})")
        lines.append("".join(bits))
    return "\n".join(lines)


@mcp.tool(structured_output=False)
def top_players(nationality: Optional[str] = None,
                club: Optional[str] = None,
                position_group: Optional[str] = None,
                limit: int = 10) -> str:
    """Top-rated players by FIFA Overall (optionally filtered)."""
    players = Q.top_players(_data, nationality=nationality, club=club,
                            position_group_name=position_group, limit=limit)
    if not players:
        return "No players found for the given criteria."
    lines = ["Top-rated players:"]
    for i, p in enumerate(players, 1):
        lines.append(f"{i}. {p['Name']} - Overall {p['Overall']}, "
                     f"{p.get('Position') or '?'}, {p['Club']} "
                     f"({p['Nationality']})")
    return "\n".join(lines)


@mcp.tool(structured_output=False)
def players_at_club(club: str, position_group: Optional[str] = None,
                    limit: int = 50) -> str:
    """List players at a club, highest-rated first."""
    players = Q.players_at_club(_data, club, position_group_name=position_group,
                                limit=limit)
    if not players:
        return f"No players found at {club} (the FIFA dataset may not cover it)."
    lines = [f"Players at {players[0]['Club']} ({len(players)}):"]
    for p in players:
        lines.append(f"- {p['Name']} (Overall {p['Overall']}, "
                     f"{p.get('Position') or '?'})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extended match statistics
# ---------------------------------------------------------------------------

@mcp.tool(structured_output=False)
def match_statistics(team: Optional[str] = None,
                     opponent: Optional[str] = None,
                     season: Optional[int] = None, limit: int = 20) -> str:
    """Matches with extended stats (corners, shots) from the stats dataset."""
    rows = Q.match_statistics(_data, team=team, opponent=opponent,
                              season=season, limit=limit)
    if not rows:
        return "No extended-stat matches found for the given criteria."
    lines = [f"{len(rows)} match(es) with extended stats:"]
    for r in rows:
        lines.append(
            f"- {r['date']}: {r['home']} {r['home_goals']}-{r['away_goals']} "
            f"{r['away']} | corners {r['home_corners']}-{r['away_corners']}, "
            f"shots {r['home_shots']}-{r['away_shots']} ({r['competition']})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------

@mcp.tool(structured_output=False)
def list_teams(competition: Optional[str] = None, season: Optional[int] = None,
               limit: int = 50) -> str:
    """List teams (with match counts), most active first."""
    teams = Q.list_teams(_data, competition=competition, season=season,
                         limit=limit)
    if not teams:
        return "No teams found for the given criteria."
    lines = [f"{len(teams)} team(s):"]
    for t in teams:
        lines.append(f"- {t['team']} ({t['matches']} matches)")
    return "\n".join(lines)


@mcp.tool(structured_output=False)
def list_competitions() -> str:
    """List all competitions available in the dataset."""
    return "Competitions: " + ", ".join(Q.list_competitions(_data))


# Internal helper used by team_competitions formatter.
def _data_team_name(data, team: str) -> str:
    return data.team_name(data.resolve_team(team))


if __name__ == "__main__":
    mcp.run()
