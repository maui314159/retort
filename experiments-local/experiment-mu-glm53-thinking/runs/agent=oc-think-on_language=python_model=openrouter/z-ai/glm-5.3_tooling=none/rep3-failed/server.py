"""Brazilian Soccer MCP server.

Exposes the query layer in ``brazilian_soccer.queries`` as MCP tools over
stdio JSON-RPC, so an LLM client can answer natural-language questions
about Brazilian soccer using the provided Kaggle datasets.

Run:
    python server.py            (stdio transport, for an MCP client)
    python server.py --health   (load data, print summary, exit)

Configure in an MCP client (e.g. Claude Desktop / opencode):
    {"mcpServers": {"brazilian-soccer": {
        "command": "python",
        "args": ["/absolute/path/to/server.py"]
    }}}
"""

from __future__ import annotations

import asyncio
import sys

from mcp.server.mcpserver import MCPServer

from brazilian_soccer import load_soccer_data
from brazilian_soccer import queries as q
from brazilian_soccer.queries import QueryError

data = load_soccer_data()

mcp = MCPServer(
    name="brazilian-soccer-mcp",
    title="Brazilian Soccer Knowledge Base",
    description=(
        "Knowledge base over Brazilian soccer datasets: Brasileirão Série A/B/C, "
        "Copa do Brasil, Copa Libertadores matches (2003-2023) and a FIFA player "
        "database (18,207 players)."
    ),
    instructions=(
        "Query Brazilian soccer history and players. Team names can be given in "
        "any common spelling (e.g. 'Flamengo', 'Palmeiras-SP', 'Athletico "
        "Paranaense'); ambiguous bases like 'Atletico' resolve to the most "
        "prominent club and list alternatives. Competitions: 'Brasileirão Série "
        "A' (aliases: 'Serie A', 'Brasileirao'), 'Brasileirão Série B', "
        "'Brasileirão Série C', 'Copa do Brasil', 'Copa Libertadores'. "
        "Dates are ISO (YYYY-MM-DD)."
    ),
    version="1.0.0",
)


def _tool_error(exc: QueryError) -> dict:
    """Convert a QueryError into a structured, LLM-friendly payload."""
    return {"error": str(exc)}


# --------------------------------------------------------------------------- #
# Match queries
# --------------------------------------------------------------------------- #


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    limit: int = 20,
) -> dict:
    """Find matches by team, opponent, competition, season, date range or stage.

    Use for questions like "What matches did Palmeiras play in 2023?" or
    "Show me all Flamengo vs Fluminense matches" (team + opponent covers both
    home and away orderings). Results are most recent first.
    """
    try:
        return q.search_matches(
            data, team=team, opponent=opponent, competition=competition,
            season=season, date_from=date_from, date_to=date_to,
            stage=stage, limit=limit,
        )
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    limit: int = 20,
) -> dict:
    """Head-to-head record between two teams with win/draw/loss summary."""
    try:
        return q.head_to_head(data, team_a, team_b, competition=competition, limit=limit)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def last_meeting(
    team_a: str,
    team_b: str,
    competition: str | None = None,
) -> dict:
    """Most recent match between two teams, with score and date."""
    try:
        return q.last_meeting(data, team_a, team_b, competition=competition)
    except QueryError as exc:
        return _tool_error(exc)


# --------------------------------------------------------------------------- #
# Team queries
# --------------------------------------------------------------------------- #


@mcp.tool()
def team_record(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss record, goals for/against and biggest win for a team.

    venue: 'all', 'home' or 'away' (e.g. Corinthians' home record in 2022).
    """
    try:
        return q.team_record(data, team, competition=competition, season=season, venue=venue)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def team_profile(team: str) -> dict:
    """Full team overview: all-time record, per-competition splits and squad
    from the FIFA dataset (cross-file query)."""
    try:
        return q.team_profile(data, team)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def search_teams(query: str, limit: int = 10) -> dict:
    """Search team names to disambiguate spellings ('atletico', 'America',
    'Sport'). Returns canonical names with dataset appearance counts."""
    return q.search_teams(data, query, limit=limit)


# --------------------------------------------------------------------------- #
# Player queries
# --------------------------------------------------------------------------- #


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    order_by: str = "overall",
    limit: int = 20,
) -> dict:
    """Search FIFA players by name, nationality, club, position or ratings.

    Examples: Brazilian players (nationality='Brazil'), forwards at São Paulo
    (club + position='ST'), highest-rated players at Flamengo.
    """
    try:
        return q.search_players(
            data, name=name, nationality=nationality, club=club,
            position=position, min_overall=min_overall, max_overall=max_overall,
            order_by=order_by, limit=limit,
        )
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def player_profile(name: str) -> dict:
    """Full FIFA profile for a player: ratings, attributes, club, value."""
    try:
        return q.player_profile(data, name)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def top_players(
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> dict:
    """Highest-rated FIFA players, optionally filtered (e.g. top Brazilian
    players, best players at Grêmio)."""
    try:
        return q.search_players(
            data, nationality=nationality, club=club, position=position,
            order_by="overall", limit=limit,
        )
    except QueryError as exc:
        return _tool_error(exc)


# --------------------------------------------------------------------------- #
# Competition queries
# --------------------------------------------------------------------------- #


@mcp.tool()
def standings(competition: str, season: int) -> dict:
    """League table computed from match results (points, W/D/L, goals).

    Example: standings of the 2019 Brasileirão; the leader is the champion.
    """
    try:
        return q.standings(data, competition, season)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def champion(competition: str, season: int) -> dict:
    """Champion of a league season (top of the table) or of a cup (final).

    Works for Brasileirão Série A/B/C, Copa do Brasil (two-legged final
    aggregated) and Copa Libertadores."""
    try:
        return q.champion(data, competition, season)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def finals(competition: str, season: int | None = None) -> dict:
    """Final matches of a cup competition (Copa do Brasil or Libertadores),
    optionally for a single season, with the aggregate winner."""
    try:
        return q.finals(data, competition, season)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def relegated(competition: str, season: int, count: int = 4) -> dict:
    """Bottom teams of a league season (relegation zone)."""
    try:
        return q.relegated(data, competition, season, count=count)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def list_competitions() -> dict:
    """Competitions available with their seasons, match counts and sources."""
    return q.list_competitions(data)


# --------------------------------------------------------------------------- #
# Statistical analysis
# --------------------------------------------------------------------------- #


@mcp.tool()
def league_averages(
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Average goals per match plus home-win / away-win / draw rates."""
    try:
        return q.league_averages(data, competition=competition, season=season)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 10,
) -> dict:
    """Largest winning margins in the dataset (biggest victories)."""
    try:
        return q.biggest_wins(data, competition=competition, season=season, team=team, limit=limit)
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def best_records(
    competition: str | None = None,
    season: int | None = None,
    venue: str = "all",
    min_matches: int = 10,
    limit: int = 10,
) -> dict:
    """Rank teams by win rate; use venue='home' or 'away' for the best
    home / away record (e.g. 'Which team has the best away record?')."""
    try:
        return q.best_records(
            data, competition=competition, season=season, venue=venue,
            min_matches=min_matches, limit=limit,
        )
    except QueryError as exc:
        return _tool_error(exc)


@mcp.tool()
def derbies(
    season: int | None = None,
    competition: str | None = None,
) -> dict:
    """Matches between traditional rivals (Fla-Flu, Choque-Rei, Gre-Nal,
    Majestoso, Ba-Vi, Atletiba, Re-Pa, ...), optionally by season."""
    try:
        return q.derbies(data, season=season, competition=competition)
    except QueryError as exc:
        return _tool_error(exc)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def _health_check() -> None:
    summary = q.list_competitions(data)
    print("Brazilian Soccer MCP server - data loaded:")
    for comp in summary["competitions"]:
        print(
            f"  {comp['competition']}: {comp['matches']} matches, "
            f"seasons {comp['season_range'][0]}-{comp['season_range'][1]}"
        )
    print(f"  Players: {summary['players_dataset']['players']}")
    print(f"  Known teams: {len(data.teams)}")


def main() -> None:
    if "--health" in sys.argv:
        _health_check()
        return
    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
