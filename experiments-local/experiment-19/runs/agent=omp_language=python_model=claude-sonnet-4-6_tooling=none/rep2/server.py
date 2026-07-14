"""
Brazilian Soccer MCP Server

Exposes Brazilian soccer data (Brasileirão, Copa do Brasil, Copa Libertadores,
FIFA player stats) as MCP tools so an LLM can answer natural-language questions.

Run with:  python server.py
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from data_loader import SoccerDataLoader
from query_engine import QueryEngine

# Singleton loader — data is read once on first tool invocation
_loader = SoccerDataLoader()
_engine = QueryEngine(_loader)

mcp = FastMCP(
    "Brazilian Soccer",
    instructions=(
        "This server provides data about Brazilian soccer: "
        "Brasileirão Serie A, Copa do Brasil, and Copa Libertadores matches, "
        "plus FIFA player ratings. "
        "Use the available tools to search for matches, teams, players, and statistics."
    ),
)


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def _fmt_match(m: dict) -> str:
    """Format a single match record into a readable line."""
    comp = m.get("competition", "")
    round_val = m.get("round", "")
    stage = m.get("stage", "")
    detail = stage or (f"Round {round_val}" if round_val else "")
    detail_str = f" ({comp}" + (f", {detail}" if detail else "") + ")"
    return (
        f"{m['date']}: {m['home_team_raw']} {m['home_goal']}–{m['away_goal']} "
        f"{m['away_team_raw']}{detail_str}"
    )


def _fmt_player(p: dict) -> str:
    overall = p.get("Overall", "?")
    potential = p.get("Potential", "?")
    club = p.get("Club", "?")
    pos = p.get("Position", "?")
    nat = p.get("Nationality", "?")
    age = p.get("Age", "?")
    return (
        f"{p['Name']} | {nat} | {pos} | Overall: {overall} "
        f"(Potential: {potential}) | Club: {club} | Age: {age}"
    )


# ------------------------------------------------------------------ #
# Tools                                                               #
# ------------------------------------------------------------------ #


@mcp.tool()
def search_matches(
    team: str,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 20,
) -> str:
    """
    Search for matches by team name with optional filters.

    Args:
        team: Team name to search for, e.g. "Flamengo", "Palmeiras", "Santos"
        opponent: Optional second team for head-to-head filtering, e.g. "Fluminense"
        competition: Optional competition filter: "Brasileirão", "Copa do Brasil",
                     "Copa Libertadores"
        season: Optional season year, e.g. 2023
        limit: Max results to return (default 20, max 100)

    Returns:
        Formatted list of matches sorted newest-first.
    """
    limit = max(1, min(int(limit), 100))
    matches = _engine.search_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        limit=limit,
    )

    if not matches:
        filters = []
        if opponent:
            filters.append(f"vs {opponent}")
        if competition:
            filters.append(f"in {competition}")
        if season:
            filters.append(f"season {season}")
        desc = ", ".join(filters) if filters else ""
        return f"No matches found for {team}" + (f" ({desc})" if desc else "") + "."

    lines = [f"Matches for {team}" + (f" vs {opponent}" if opponent else "") + ":"]
    for m in matches:
        lines.append("  " + _fmt_match(m))

    lines.append(f"\n({len(matches)} result(s) shown)")
    return "\n".join(lines)


@mcp.tool()
def get_team_stats(
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: str = "both",
) -> str:
    """
    Get win/draw/loss record and goals for a team.

    Args:
        team: Team name, e.g. "Corinthians", "Grêmio"
        competition: Optional competition filter
        season: Optional season year
        venue: "home" | "away" | "both" (default "both")

    Returns:
        Formatted statistics summary.
    """
    stats = _engine.get_team_stats(
        team=team,
        competition=competition,
        season=season,
        venue=venue,
    )

    if stats["matches"] == 0:
        return f"No matches found for {team}."

    title_parts = [team]
    if competition:
        title_parts.append(competition)
    if season:
        title_parts.append(str(season))
    if venue != "both":
        title_parts.append(f"{venue} only")

    lines = [
        f"Stats for {' | '.join(title_parts)}:",
        f"  Matches:     {stats['matches']}",
        f"  Wins:        {stats['wins']}",
        f"  Draws:       {stats['draws']}",
        f"  Losses:      {stats['losses']}",
        f"  Goals For:   {stats['goals_for']}",
        f"  Goals Agst:  {stats['goals_against']}",
        f"  Goal Diff:   {stats['goal_diff']:+d}",
        f"  Win Rate:    {stats['win_rate']}%",
    ]
    return "\n".join(lines)


@mcp.tool()
def head_to_head(
    team1: str,
    team2: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """
    Head-to-head record and match history between two teams.

    Args:
        team1: First team name
        team2: Second team name
        competition: Optional competition filter
        season: Optional season year

    Returns:
        H2H summary with win counts and recent match list.
    """
    result = _engine.head_to_head(
        team1=team1,
        team2=team2,
        competition=competition,
        season=season,
    )

    if result["total_matches"] == 0:
        return f"No matches found between {team1} and {team2}."

    lines = [
        f"Head-to-Head: {team1} vs {team2}",
        f"  Total matches: {result['total_matches']}",
        f"  {team1} wins: {result['team1_wins']}",
        f"  {team2} wins: {result['team2_wins']}",
        f"  Draws: {result['draws']}",
        "",
        "Recent matches:",
    ]
    for m in result["matches"][:20]:
        lines.append("  " + _fmt_match(m))
    if len(result["matches"]) > 20:
        lines.append(f"  ... ({len(result['matches']) - 20} more not shown)")

    return "\n".join(lines)


@mcp.tool()
def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> str:
    """
    Search FIFA player database by name, nationality, club, or position.

    Args:
        name: Player name substring, e.g. "Neymar", "Gabriel"
        nationality: Nationality, e.g. "Brazil", "Argentina"
        club: Club name substring, e.g. "Flamengo", "Santos"
        position: Position code or substring, e.g. "ST", "GK", "CAM"
        min_overall: Minimum FIFA Overall rating, e.g. 80
        limit: Max results (default 20)

    Returns:
        Formatted player list sorted by overall rating (highest first).
    """
    limit = max(1, min(int(limit), 100))
    players = _engine.search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
    )

    if not players:
        filters = []
        if name:
            filters.append(f"name='{name}'")
        if nationality:
            filters.append(f"nationality='{nationality}'")
        if club:
            filters.append(f"club='{club}'")
        if position:
            filters.append(f"position='{position}'")
        if min_overall:
            filters.append(f"min_overall={min_overall}")
        return "No players found" + (
            f" matching {', '.join(filters)}." if filters else "."
        )

    lines = [f"Players ({len(players)} result(s)):"]
    for i, p in enumerate(players, 1):
        lines.append(f"  {i}. {_fmt_player(p)}")
    return "\n".join(lines)


@mcp.tool()
def get_standings(
    competition: str,
    season: int,
) -> str:
    """
    Get competition standings (calculated from match results).

    Args:
        competition: "Brasileirão", "Copa do Brasil", or "Copa Libertadores"
        season: Season year, e.g. 2019, 2022

    Returns:
        Standings table sorted by points (3 for win, 1 for draw, 0 for loss).
    """
    standings = _engine.get_standings(competition=competition, season=int(season))

    if not standings:
        return f"No data found for {competition} {season}."

    lines = [f"{competition} {season} Standings (calculated from match results):"]
    lines.append(
        f"  {'Pos':>3}  {'Team':<30}  {'Pts':>4}  {'P':>4}  "
        f"{'W':>3}  {'D':>3}  {'L':>3}  {'GF':>4}  {'GA':>4}  {'GD':>4}"
    )
    lines.append("  " + "-" * 75)
    for i, s in enumerate(standings, 1):
        lines.append(
            f"  {i:>3}. {s['team']:<30}  {s['points']:>4}  {s['played']:>4}  "
            f"{s['wins']:>3}  {s['draws']:>3}  {s['losses']:>3}  "
            f"{s['goals_for']:>4}  {s['goals_against']:>4}  {s['goal_diff']:>+4}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_match_statistics(
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    """
    Get aggregated match statistics (goals per match, home win rate, etc.).

    Args:
        competition: Optional competition filter
        season: Optional season year

    Returns:
        Summary statistics for the filtered dataset.
    """
    stats = _engine.get_global_stats(competition=competition, season=season)

    if "error" in stats:
        return stats["error"]

    title_parts = []
    if competition:
        title_parts.append(competition)
    if season:
        title_parts.append(str(season))
    title = " ".join(title_parts) if title_parts else "All competitions"

    lines = [
        f"Match statistics — {title}:",
        f"  Total matches:       {stats['total_matches']}",
        f"  Total goals:         {stats['total_goals']}",
        f"  Avg goals/match:     {stats['avg_goals_per_match']}",
        f"  Home wins:           {stats['home_wins']} ({stats['home_win_rate']}%)",
        f"  Away wins:           {stats['away_wins']} ({stats['away_win_rate']}%)",
        f"  Draws:               {stats['draws']} ({stats['draw_rate']}%)",
    ]
    return "\n".join(lines)


@mcp.tool()
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """
    List matches with the largest winning margins.

    Args:
        competition: Optional competition filter
        season: Optional season year
        limit: Number of results (default 10)

    Returns:
        Matches ordered by goal difference (largest first).
    """
    limit = max(1, min(int(limit), 50))
    matches = _engine.biggest_wins(
        competition=competition, season=season, limit=limit
    )

    if not matches:
        return "No matches found."

    title_parts = []
    if competition:
        title_parts.append(competition)
    if season:
        title_parts.append(str(season))
    title = " | ".join(title_parts) if title_parts else "All competitions"

    lines = [f"Biggest wins — {title}:"]
    for i, m in enumerate(matches, 1):
        margin = abs(m["home_goal"] - m["away_goal"])
        lines.append(f"  {i:>2}. {_fmt_match(m)}  (margin: {margin})")
    return "\n".join(lines)


@mcp.tool()
def top_scorers_by_team(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> str:
    """
    Rank teams by total goals scored.

    Args:
        competition: Optional competition filter
        season: Optional season year
        limit: Number of teams to return (default 10)

    Returns:
        Teams ranked by goals scored (highest first).
    """
    limit = max(1, min(int(limit), 50))
    teams = _engine.top_scoring_teams(
        competition=competition, season=season, limit=limit
    )

    if not teams:
        return "No data found."

    title_parts = []
    if competition:
        title_parts.append(competition)
    if season:
        title_parts.append(str(season))
    title = " | ".join(title_parts) if title_parts else "All competitions"

    lines = [f"Top scoring teams — {title}:"]
    for i, t in enumerate(teams, 1):
        lines.append(f"  {i:>2}. {t['team']} — {t['goals_scored']} goals")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
