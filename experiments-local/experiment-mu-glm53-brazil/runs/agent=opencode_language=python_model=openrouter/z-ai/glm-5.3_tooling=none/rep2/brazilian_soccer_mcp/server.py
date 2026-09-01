"""MCP server exposing the Brazilian soccer query service as tools.

Run with ``python run_server.py`` (stdio transport).  Each tool returns a
JSON-serializable dictionary so the connected LLM can render the answer.
"""

from __future__ import annotations

from .service import COMPETITIONS, get_service

try:
    from mcp.server.mcpserver import MCPServer
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ModuleNotFoundError(
        "The 'mcp' package is required to run the server. "
        "Install it with: pip install mcp"
    ) from exc

mcp: MCPServer = MCPServer(
    name="brazilian-soccer",
    title="Brazilian Soccer Knowledge Server",
    description=(
        "Natural-language-ready queries about Brazilian soccer: matches, "
        "teams, players, competitions (Brasileirão, Copa do Brasil, Copa "
        "Libertadores) and statistics from bundled Kaggle datasets."
    ),
    instructions=(
        "Use these tools to answer questions about Brazilian soccer. "
        "Team names are matched leniently (with or without state suffixes "
        "and accents). Seasons are calendar years. For standings a season "
        "is required. When a query names a competition, pass it as the "
        "'competition' argument (e.g. 'Brasileirão', 'Copa do Brasil', "
        "'Libertadores', 'Serie B')."
    ),
)


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    source: str | None = None,
    limit: int = 30,
) -> dict:
    """Search matches by team, opponent, competition, season, date range or
    stage (e.g. 'final').

    Use `team` alone for all matches of a team, or `team` + `opponent` for
    head-to-head fixtures (either venue). Dates use YYYY-MM-DD. Set
    `source` to 'br_football_stats' to include corner/shot/attack
    statistics for matches covered by the extended dataset.
    """
    return get_service().search_matches(
        team=team, opponent=opponent, competition=competition, season=season,
        date_from=date_from, date_to=date_to, stage=stage, source=source,
        limit=limit,
    )


@mcp.tool()
def head_to_head(
    team: str,
    opponent: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Compare two teams head-to-head: all their direct matches plus the
    win/draw/loss record between them."""
    return get_service().head_to_head(
        team=team, opponent=opponent, competition=competition, season=season
    )


@mcp.tool()
def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> dict:
    """Return a team's record: matches, wins, draws, losses, goals for and
    against, split overall/home/away and by competition.

    `venue` can be 'home' or 'away' to restrict the record.
    """
    return get_service().team_stats(
        team=team, season=season, competition=competition, venue=venue
    )


@mcp.tool()
def team_competitions(team: str) -> dict:
    """List the competitions, seasons and match counts a team appears in."""
    return get_service().team_competitions(team)


@mcp.tool()
def list_teams(
    query: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 50,
) -> dict:
    """List teams known to the datasets, optionally filtered by a name
    fragment, competition or season."""
    return get_service().list_teams(
        query=query, competition=competition, season=season, limit=limit
    )


@mcp.tool()
def resolve_team(name: str) -> dict:
    """Resolve a team name (any spelling variant) to the canonical team,
    listing alternatives when the name is ambiguous."""
    return get_service().resolve_team(name)


@mcp.tool()
def standings(competition: str = "Brasileirão Série A",
              season: int | None = None) -> dict:
    """Compute the league table for one season from match results.

    Returns positions, points, wins/draws/losses, goals, the champion and
    the relegated teams. Only league competitions (Brasileirão Série A/B/C)
    have standings; cups do not.
    """
    return get_service().standings(competition=competition, season=season)


@mcp.tool()
def competition_info(competition: str | None = None) -> dict:
    """Describe the available competitions: seasons covered, match counts
    and source datasets."""
    return get_service().competition_info(competition)


@mcp.tool()
def derby_matches(season: int | None = None,
                  competition: str | None = None) -> dict:
    """Find matches between traditional rivals (Fla-Flu, Gre-Nal, Majestoso,
    Choque-Rei, Ba-Vi and other classic Brazilian derbies)."""
    return get_service().derbies(season=season, competition=competition)


@mcp.tool()
def biggest_wins(competition: str | None = None,
                 season: int | None = None,
                 n: int = 10) -> dict:
    """Return the matches with the largest winning margins."""
    return get_service().biggest_wins(
        competition=competition, season=season, n=n
    )


@mcp.tool()
def league_statistics(competition: str | None = None,
                      season: int | None = None,
                      source: str | None = None) -> dict:
    """Aggregate statistics: average goals per match, home/away win rates,
    draw rate and the biggest win. Without filters, reports per-competition
    totals across the whole dataset."""
    return get_service().league_statistics(
        competition=competition, season=season, source=source
    )


@mcp.tool()
def best_records(competition: str | None = None,
                 season: int | None = None,
                 venue: str = "home",
                 min_matches: int = 20,
                 n: int = 10) -> dict:
    """Rank teams by win rate. `venue` is 'home', 'away' or 'overall'."""
    return get_service().best_records(
        competition=competition, season=season, venue=venue,
        min_matches=min_matches, n=n,
    )


@mcp.tool()
def search_players(
    name: str | None = None,
    club: str | None = None,
    nationality: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 30,
) -> dict:
    """Search FIFA player data by name, club, nationality, position (code
    like 'ST' or group like 'forward') and overall rating range."""
    return get_service().search_players(
        name=name, club=club, nationality=nationality, position=position,
        min_overall=min_overall, max_overall=max_overall, limit=limit,
    )


@mcp.tool()
def top_players(club: str | None = None,
                nationality: str | None = None,
                position: str | None = None,
                n: int = 10) -> dict:
    """Return the highest-rated players for a club, nationality or
    position (e.g. top Brazilian players)."""
    return get_service().top_players(
        club=club, nationality=nationality, position=position, n=n
    )


@mcp.tool()
def players_by_club(nationality: str = "Brazil") -> dict:
    """Aggregate players of one nationality playing at Brazilian clubs:
    counts, average ratings and notable names per club."""
    return get_service().players_by_club(nationality=nationality)


def main() -> None:
    """Run the MCP server over stdio."""
    get_service()
    mcp.run()


TOOL_NAMES = [
    "search_matches", "head_to_head", "team_stats", "team_competitions",
    "list_teams", "resolve_team", "standings", "competition_info",
    "derby_matches", "biggest_wins", "league_statistics", "best_records",
    "search_players", "top_players", "players_by_club",
]

__all__ = ["mcp", "main", "TOOL_NAMES", "COMPETITIONS"]
