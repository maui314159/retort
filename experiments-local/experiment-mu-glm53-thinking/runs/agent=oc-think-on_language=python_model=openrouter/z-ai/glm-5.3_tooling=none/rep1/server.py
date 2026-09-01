"""Brazilian Soccer MCP server.

A Model Context Protocol server exposing the six Kaggle datasets in
data/kaggle/ as queryable tools. Run over stdio:

    python server.py

or register in an MCP client (e.g. Claude Desktop / opencode) with:

    {"mcpServers": {"brazilian-soccer": {"command": "python", "args": ["<abs path>/server.py"]}}}

Requires mcp>=2 (the MCPServer API; FastMCP was renamed in SDK v2).
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from brazilian_soccer import queries as q
from brazilian_soccer.data import get_soccer_data
from brazilian_soccer.normalize import TeamResolutionError

mcp = MCPServer(
    name="brazilian-soccer",
    title="Brazilian Soccer Knowledge Server",
    description=(
        "Natural-language-ready tools over Brazilian soccer datasets: "
        "Brasileirão Série A/B/C (2003-2023), Copa do Brasil (2012-2023), "
        "Copa Libertadores (2013-2022) and a FIFA player database "
        "(18,207 players). Team names are normalized across files, so "
        "'Palmeiras-SP', 'Palmeiras' and 'Sociedade Esportiva Palmeiras' all "
        "resolve to the same club."
    ),
    version="1.0.0",
)


def _safe(fn, **kwargs):
    """Run a query, converting resolution errors into structured tool output."""
    data = get_soccer_data()
    try:
        return fn(data, **kwargs)
    except TeamResolutionError as exc:
        return {"error": str(exc)}


@mcp.tool()
def list_competitions() -> dict:
    """List every competition in the datasets with its seasons and match counts."""
    return q.competitions_overview(get_soccer_data())


@mcp.tool()
def resolve_team(name: str) -> dict:
    """Resolve a team name to its canonical club and show every spelling
    variant found across the datasets (handles 'Palmeiras-SP', 'Palmeiras',
    full legal names, accented and unaccented forms)."""
    return _safe(q.resolve_team_info, name=name)


@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    round: int | None = None,
    limit: int = 25,
) -> dict:
    """Find matches by team, opponent, competition, season, date range
    (YYYY-MM-DD), Libertadores stage (e.g. 'final', 'semifinals') or round
    number. Combine team+opponent for head-to-head fixtures."""
    return _safe(
        q.search_matches,
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        stage=stage,
        round=round,
        limit=limit,
    )


@mcp.tool()
def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Head-to-head record between two teams: wins, draws, goals, all matches
    and the latest meeting."""
    return _safe(q.head_to_head, team_a=team_a, team_b=team_b, competition=competition, season=season)


@mcp.tool()
def get_team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss record and goals for a team. Filter by season and
    competition; venue can be 'all', 'home' or 'away'. Without a season,
    per-season and per-competition breakdowns are included."""
    return _safe(
        q.team_stats,
        team=team,
        season=season,
        competition=competition,
        venue=venue,
    )


@mcp.tool()
def get_club_overview(club: str) -> dict:
    """Cross-file club profile: overall record, competitions played and the
    FIFA-database squad when the club is covered there."""
    return _safe(q.club_overview, club=club)


@mcp.tool()
def get_standings(competition: str, season: int) -> dict:
    """League table for a season, calculated from match results (3 points per
    win). Marks the champion and the bottom-four relegation zone. Example:
    get_standings(competition='Brasileirão Série A', season=2019)."""
    return _safe(q.standings, competition=competition, season=season)


@mcp.tool()
def get_relegation(competition: str, season: int) -> dict:
    """Bottom four teams of a league season (the relegation zone in modern
    Brasileirão seasons)."""
    return _safe(q.relegated_teams, competition=competition, season=season)


@mcp.tool()
def find_finals(competition: str, season: int | None = None) -> dict:
    """Final matches of cup competitions: Libertadores finals by stage, Copa
    do Brasil finals by highest round. Omit season for every season."""
    return _safe(q.find_finals, competition=competition, season=season)


@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    min_potential: int | None = None,
    limit: int = 20,
    sort: str = "overall",
) -> dict:
    """Search the FIFA player database. Filters: name (substring),
    nationality (e.g. 'Brazil'), club, position ('ST', 'GK', ...),
    position_group ('forwards'|'midfielders'|'defenders'|'goalkeepers'),
    min/max overall, min potential. Sort by overall, potential, age, value or
    name."""
    return _safe(
        q.search_players,
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        position_group=position_group,
        min_overall=min_overall,
        max_overall=max_overall,
        min_potential=min_potential,
        limit=limit,
        sort=sort,
    )


@mcp.tool()
def get_competition_stats(competition: str, season: int | None = None) -> dict:
    """Aggregate statistics for a competition and optional season: average
    goals per match, home/away win rates, biggest win, date range."""
    return _safe(q.competition_stats, competition=competition, season=season)


@mcp.tool()
def get_biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict:
    """Largest winning margins in the dataset, optionally filtered by
    competition and season."""
    return _safe(q.biggest_wins, competition=competition, season=season, limit=limit)


@mcp.tool()
def get_derby_matches(
    derby: str | None = None,
    season: int | None = None,
    competition: str | None = None,
    limit: int = 50,
) -> dict:
    """Matches between traditional rivals (Fla-Flu, Gre-Nal, Derby Paulista,
    ...). Omit derby to sweep all rivalries; filter by season or competition."""
    return _safe(
        q.derby_matches,
        derby=derby,
        season=season,
        competition=competition,
        limit=limit,
    )


@mcp.tool()
def search_match_stats(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 20,
) -> dict:
    """Extended per-match statistics (corners, shots, attacks, half-time
    score) from the BR-Football dataset (Série A/B/C and Copa do Brasil,
    2014-2023)."""
    return _safe(
        q.search_match_stats,
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        limit=limit,
    )


@mcp.tool()
def best_home_records(competition: str, season: int, limit: int = 5) -> dict:
    """Teams with the best home records in a league season, by home win
    rate."""
    return _safe(
        q.best_home_records, competition=competition, season=season, limit=limit
    )


if __name__ == "__main__":
    mcp.run()
