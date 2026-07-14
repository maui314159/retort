"""Brazilian Soccer MCP Server.

Exposes soccer data query tools via the Model Context Protocol.
"""

from __future__ import annotations


from pathlib import Path

import pandas as pd
from mcp.server.fastmcp import FastMCP
from data_loader import SoccerData

# Resolve data dir relative to this file's parent
DATA_DIR = str(Path(__file__).resolve().parent / "data" / "kaggle")
data = SoccerData(DATA_DIR)
mcp = FastMCP(
    "brazilian-soccer",
    instructions="MCP server for Brazilian soccer data — matches, teams, players, competitions, and statistics.",
)


# ── Tool: search_matches ────────────────────────────────────────────

@mcp.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
) -> str:
    """Search for matches by team, opponent, competition, season, or date range.

    Args:
        team: Team name (e.g. "Flamengo", "Palmeiras")
        opponent: Opponent team name for head-to-head lookups
        competition: Competition name substring (e.g. "Brasileirão", "Libertadores")
        season: Year of the season
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        home_only: Only home matches for the team
        away_only: Only away matches for the team
    """
    df = data.find_matches(
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        home_only=home_only,
        away_only=away_only,
    )
    if df.empty:
        return "No matches found."
    lines = [f"Found {len(df)} matches:"]
    for _, row in df.head(30).iterrows():
        date_str = str(row["date"].date()) if hasattr(row["date"], "date") and pd.notna(row["date"]) else "unknown"
        lines.append(
            f"- {date_str}: {row['home_team']} {row['home_goal']}-{row['away_goal']} {row['away_team']} ({row['competition']})"
        )
    if len(df) > 30:
        lines.append(f"... and {len(df) - 30} more matches")
    return "\n".join(lines)


# ── Tool: head_to_head ──────────────────────────────────────────────

@mcp.tool()
def head_to_head(team_a: str, team_b: str) -> str:
    """Compare two teams head-to-head across all competitions.

    Args:
        team_a: First team name
        team_b: Second team name
    """
    result = data.head_to_head(team_a, team_b)
    matches = result.pop("matches")
    lines = [
        f"{result['team_a']} vs {result['team_b']}:",
        f"- {result['team_a']} wins: {result['team_a_wins']}",
        f"- {result['team_b']} wins: {result['team_b_wins']}",
        f"- Draws: {result['draws']}",
        f"- Total matches: {result['total_matches']}",
        "",
        "Recent matches:",
    ]
    for _, row in matches.head(15).iterrows():
        date_str = str(row["date"].date()) if hasattr(row["date"], "date") and pd.notna(row["date"]) else "unknown"
        lines.append(
            f"- {date_str}: {row['home_team']} {row['home_goal']}-{row['away_goal']} {row['away_team']} ({row['competition']})"
        )
    return "\n".join(lines)


# ── Tool: team_stats ────────────────────────────────────────────────

@mcp.tool()
def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
) -> str:
    """Get statistics for a team: wins, draws, losses, goals.

    Args:
        team: Team name
        season: Optional season year filter
        competition: Optional competition name filter
    """
    stats = data.team_stats(team, season=season, competition=competition)
    return (
        f"{stats['team']}{' (' + str(stats['season']) + ')' if stats['season'] else ''}:\n"
        f"- Matches: {stats['matches']}\n"
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}\n"
        f"- Win rate: {stats['win_rate']}%"
    )


# ── Tool: standings ─────────────────────────────────────────────────

@mcp.tool()
def standings(season: int, competition: str = "Brasileirão") -> str:
    """Calculate league standings from match results for a given season.

    Args:
        season: Year of the season
        competition: Competition name (default: Brasileirão)
    """
    table = data.standings(season, competition)
    if not table:
        return f"No standings data found for {competition} {season}."
    lines = [f"{competition} {season} Standings:"]
    for i, row in enumerate(table, 1):
        gd = row["gf"] - row["ga"]
        champion = " - Champion" if i == 1 else ""
        relegated = " - Relegated" if i > len(table) - 4 else ""
        lines.append(
            f"{i}. {row['team']} - {row['pts']} pts "
            f"({row['w']}W, {row['d']}D, {row['l']}L) "
            f"GD: {gd:+d}{champion}{relegated}"
        )
    return "\n".join(lines)


# ── Tool: search_players ────────────────────────────────────────────

@mcp.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
) -> str:
    """Search FIFA player database by name, nationality, club, position, or rating.

    Args:
        name: Player name (substring match)
        nationality: Nationality (e.g. "Brazil")
        club: Club name (substring match)
        position: Position code (e.g. "ST", "LW", "GK", "CDM")
        min_overall: Minimum overall rating
        limit: Max results (default 20)
    """
    df = data.search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
        limit=limit,
    )
    if df.empty:
        return "No players found."
    lines = [f"Found {len(df)} players:"]
    for _, row in df.iterrows():
        lines.append(
            f"- {row['Name']} - Overall: {row['Overall']}, "
            f"Position: {row['Position']}, Club: {row['Club']}"
        )
    return "\n".join(lines)


# ── Tool: statistics ────────────────────────────────────────────────

@mcp.tool()
def statistics(
    competition: str | None = None,
    biggest_wins_limit: int = 10,
) -> str:
    """Calculate aggregate statistics: avg goals, home/away win rates, biggest victories.

    Args:
        competition: Optional competition filter
        biggest_wins_limit: Number of biggest wins to return (default 10)
    """
    avg = data.avg_goals(competition)
    wins = data.biggest_wins(limit=biggest_wins_limit, competition=competition)
    comp_label = competition or "All competitions"
    lines = [
        f"Statistics for {comp_label}:",
        f"- Total matches: {avg['total_matches']}",
        f"- Total goals: {avg['total_goals']}",
        f"- Average goals per match: {avg['avg_goals_per_match']}",
        f"- Home wins: {avg['home_wins']} ({avg['home_win_rate']}%)",
        f"- Away wins: {avg['away_wins']}",
        f"- Draws: {avg['draws']}",
        "",
        f"Biggest victories:",
    ]
    for i, w in enumerate(wins, 1):
        lines.append(f"  {i}. {w['date']}: {w['winner']} {w['winner_goals']}-{w['loser_goals']} {w['loser']} ({w['competition']})")
    return "\n".join(lines)


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
