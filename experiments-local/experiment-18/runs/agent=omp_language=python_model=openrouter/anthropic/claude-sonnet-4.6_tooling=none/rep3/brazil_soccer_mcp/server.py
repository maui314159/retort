"""
================================================================================
brazil_soccer_mcp.server
================================================================================
Context:
    The MCP entry point. Builds the knowledge graph once at import/startup and
    exposes the spec's query categories as MCP tools over stdio (the default
    transport an LLM client connects to). Each tool returns a formatted text
    block from brazil_soccer_mcp.formatting.

Tools (grouped by spec category):
    Match        : find_matches, last_meeting
    Team         : team_record, head_to_head, best_record
    Player       : search_player, players_at_club, top_players, brazilian_clubs
    Competition  : standings, champion, list_competitions, list_seasons
    Statistics   : league_stats, biggest_wins

Run:
    python -m brazil_soccer_mcp.server      # stdio MCP server
    (or the console script `brazil-soccer-mcp` after `pip install -e .`)

The graph is process-global and read-only, so tools are safe to call
concurrently and meet the spec's latency targets without rebuilds.
================================================================================
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import formatting as fmt
from .graph import KnowledgeGraph, build_graph

mcp = FastMCP("brazilian-soccer")


@lru_cache(maxsize=1)
def get_graph() -> KnowledgeGraph:
    """Build (once) and return the shared knowledge graph."""
    return build_graph()


# --------------------------------------------------------------------------- #
# Match queries
# --------------------------------------------------------------------------- #
@mcp.tool(description="Find matches by team, opponent, competition, season, or date range.")
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: Optional[str] = None,
    limit: int = 30,
) -> str:
    """`venue` may be 'home' or 'away' to restrict to that side for `team`."""
    g = get_graph()
    home_only = (venue or "").lower() == "home"
    away_only = (venue or "").lower() == "away"
    matches = g.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        home_only=home_only,
        away_only=away_only,
        limit=limit,
    )
    h2h = None
    if team and opponent:
        h2h = g.head_to_head(team, opponent, competition=competition)
    title_bits = [b for b in [team, ("vs " + opponent) if opponent else None] if b]
    title = (" ".join(title_bits) + " matches:") if title_bits else "Matches:"
    return fmt.format_matches(g, matches, title=title, head_to_head=h2h)


@mcp.tool(description="Most recent match between two teams (date, score, competition).")
def last_meeting(team_a: str, team_b: str) -> str:
    g = get_graph()
    matches = g.find_matches(team=team_a, opponent=team_b)
    if not matches:
        return f"No matches found between {team_a} and {team_b}."
    last = matches[-1]
    return "Most recent meeting:\n" + fmt.format_match_line(last)


# --------------------------------------------------------------------------- #
# Team queries
# --------------------------------------------------------------------------- #
@mcp.tool(description="Win/draw/loss and goal record for a team, optionally by season/competition/venue.")
def team_record(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: Optional[str] = None,
) -> str:
    g = get_graph()
    home_only = (venue or "").lower() == "home"
    away_only = (venue or "").lower() == "away"
    res = g.team_stats(
        team,
        season=season,
        competition=competition,
        home_only=home_only,
        away_only=away_only,
    )
    if res is None:
        return f"Team '{team}' not found in match data."
    key, rec = res
    scope_bits = [
        str(season) if season else None,
        competition,
        (venue.lower() + " only") if venue else None,
    ]
    scope = ", ".join(b for b in scope_bits if b)
    return fmt.format_team_record(g.team_display(key), rec, scope=scope)


@mcp.tool(description="Head-to-head summary and recent meetings between two teams.")
def head_to_head(team_a: str, team_b: str, competition: Optional[str] = None) -> str:
    g = get_graph()
    h = g.head_to_head(team_a, team_b, competition=competition)
    if h is None:
        return f"Could not resolve one of '{team_a}' / '{team_b}'."
    return fmt.format_head_to_head(g, h)


@mcp.tool(description="Teams ranked by win rate (optionally by competition/season/venue).")
def best_record(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
    limit: int = 10,
) -> str:
    g = get_graph()
    home_only = (venue or "").lower() == "home"
    away_only = (venue or "").lower() == "away"
    rows = g.best_record(
        competition=competition,
        season=season,
        home_only=home_only,
        away_only=away_only,
    )
    label_bits = [competition, str(season) if season else None, venue]
    label = ", ".join(b for b in label_bits if b) or "all data"
    return fmt.format_best_record(g, rows[:limit], label=label)


# --------------------------------------------------------------------------- #
# Player queries
# --------------------------------------------------------------------------- #
@mcp.tool(description="Search FIFA players by (partial) name.")
def search_player(name: str, limit: int = 10) -> str:
    g = get_graph()
    players = g.search_players(name, limit=limit)
    if len(players) == 1:
        return fmt.format_player_detail(players[0])
    return fmt.format_players(players, title=f"Players matching '{name}':")


@mcp.tool(description="List players whose club matches the given name (e.g. 'Flamengo').")
def players_at_club(club: str, limit: int = 25) -> str:
    g = get_graph()
    players = g.players_by_club(club, limit=limit)
    return fmt.format_players(players, title=f"Players at clubs matching '{club}':")


@mcp.tool(description="Top-rated players, optionally filtered by nationality, club, or position.")
def top_players(
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    limit: int = 10,
) -> str:
    g = get_graph()
    players = g.top_players(
        nationality=nationality, club=club, position=position, limit=limit
    )
    bits = [nationality, club, position]
    label = ", ".join(b for b in bits if b) or "all players"
    return fmt.format_players(players, title=f"Top players ({label}):", show=limit)


@mcp.tool(description="Brazilian players grouped by Brazilian club, with counts and average ratings.")
def brazilian_clubs(limit: int = 15) -> str:
    g = get_graph()
    summary = g.brazilian_clubs_summary(top=limit)
    if not summary:
        return "No Brazilian players at Brazilian clubs found in dataset."
    lines = ["Brazilian players at Brazilian clubs:"]
    for row in summary:
        lines.append(
            f"- {row['club']}: {row['count']} players "
            f"(avg rating: {row['avg_rating']})"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Competition queries
# --------------------------------------------------------------------------- #
@mcp.tool(description="Final league standings for a competition and season (points table).")
def standings(competition: str, season: int, limit: int = 20) -> str:
    g = get_graph()
    rows = g.standings(competition, season)
    return fmt.format_standings(g, _comp_label(g, competition), season, rows, show=limit)


@mcp.tool(description="Champion (top of the points table) of a competition for a season.")
def champion(competition: str, season: int) -> str:
    g = get_graph()
    res = g.champion(competition, season)
    if res is None:
        return f"No data for {competition} {season}."
    key, rec = res
    return (
        f"{season} {_comp_label(g, competition)} champion: "
        f"{g.team_display(key)} - {rec.points} pts "
        f"({rec.wins}W, {rec.draws}D, {rec.losses}L, "
        f"GF {rec.goals_for}, GA {rec.goals_against})"
    )


@mcp.tool(description="List the competitions available in the dataset.")
def list_competitions() -> str:
    g = get_graph()
    return "Competitions in dataset:\n" + "\n".join(
        f"- {c}" for c in g.competitions()
    )


@mcp.tool(description="List the seasons available, optionally for one competition.")
def list_seasons(competition: Optional[str] = None) -> str:
    g = get_graph()
    seasons = g.seasons(competition)
    label = competition or "all competitions"
    return f"Seasons for {label}: " + ", ".join(str(s) for s in seasons)


# --------------------------------------------------------------------------- #
# Statistical analysis
# --------------------------------------------------------------------------- #
@mcp.tool(description="Aggregate stats (avg goals/match, home/away win rates) for a competition/season.")
def league_stats(competition: Optional[str] = None, season: Optional[int] = None) -> str:
    g = get_graph()
    stats = g.aggregate_stats(competition=competition, season=season)
    label_bits = [competition or "all competitions", str(season) if season else None]
    return fmt.format_aggregate(stats, ", ".join(b for b in label_bits if b))


@mcp.tool(description="Biggest victories by goal margin (optionally by competition/season).")
def biggest_wins(
    competition: Optional[str] = None, season: Optional[int] = None, limit: int = 10
) -> str:
    g = get_graph()
    matches = g.biggest_wins(competition=competition, season=season, limit=limit)
    label_bits = [competition or "all data", str(season) if season else None]
    return fmt.format_biggest_wins(matches, ", ".join(b for b in label_bits if b))


def _comp_label(g: KnowledgeGraph, competition: str) -> str:
    from .normalize import normalize_competition

    return normalize_competition(competition)


def main() -> None:
    """Console entry point: build the graph then serve over stdio."""
    get_graph()  # warm the cache so the first query is fast
    mcp.run()


if __name__ == "__main__":
    main()
