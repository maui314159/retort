"""MCP server exposing the Brazilian soccer query layer as tools.

Builds an ``MCPServer`` (mcp python SDK v2) served over stdio by the
``server.py`` entrypoint. Each tool maps 1:1 onto a function in
``soccer.queries`` so the same logic is unit-testable without the
protocol layer.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

import soccer.queries as q
from soccer.loader import DATA_DIR, SoccerData

_TOOL_KWARGS = {}  # placeholder for future shared options


def build_server(data: SoccerData | None = None, name: str = "brazilian-soccer") -> MCPServer:
    """Construct the MCP server; loads data lazily if not provided."""
    server = MCPServer(
        name=name,
        title="Brazilian Soccer Knowledge Server",
        description=(
            "Knowledge graph of Brazilian soccer: matches, teams, players and "
            "competitions from Kaggle datasets (Brasileirão, Copa do Brasil, "
            "Copa Libertadores, FIFA player database)."
        ),
    )
    if data is None:
        data = SoccerData.load(DATA_DIR)

    @server.tool(
        name="find_matches",
        description=(
            "Find matches by team, opponent, competition (Brasileirão, Copa do "
            "Brasil, Libertadores), season, date range (YYYY-MM-DD) or stage "
            "(e.g. final). Team names accept variants like 'Palmeiras-SP'."
        ),
    )
    def find_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        stage: str | None = None,
        limit: int = 50,
    ) -> dict:
        return q.find_matches(
            data, team, opponent, competition, season, date_from, date_to, stage, limit
        )

    @server.tool(
        name="head_to_head",
        description="Head-to-head record between two teams (wins/draws/losses and recent matches).",
    )
    def head_to_head(
        team_a: str, team_b: str, competition: str | None = None
    ) -> dict:
        return q.head_to_head(data, team_a, team_b, competition)

    @server.tool(
        name="last_match",
        description="Most recent match of a team, optionally versus a given opponent.",
    )
    def last_match(team: str, opponent: str | None = None) -> dict:
        return q.last_match(data, team, opponent)

    @server.tool(
        name="team_stats",
        description=(
            "Win/draw/loss record, goals and home/away splits for a team; "
            "optionally filtered by season, competition and venue."
        ),
    )
    def team_stats(
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str | None = None,
    ) -> dict:
        return q.team_stats(data, team, season, competition, venue)

    @server.tool(
        name="team_competitions",
        description="List the competitions a team has played in, with match counts.",
    )
    def team_competitions(team: str) -> dict:
        return q.team_competitions(data, team)

    @server.tool(
        name="standings",
        description="League table calculated from match results for a season (default Brasileirão).",
    )
    def standings(
        season: int, competition: str = "Brasileirão", limit: int | None = None
    ) -> dict:
        return q.standings(data, season, competition, limit)

    @server.tool(
        name="relegated",
        description="Bottom teams (relegation zone) for a season.",
    )
    def relegated(
        season: int, competition: str = "Brasileirão", n: int = 4
    ) -> dict:
        return q.relegated(data, season, competition, n)

    @server.tool(
        name="search_players",
        description=(
            "Search FIFA player data by name, nationality (e.g. Brazil), club "
            "(e.g. Flamengo), position (GK/ST/LW or forward/midfielder/"
            "defender/goalkeeper) and minimum overall rating."
        ),
    )
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int = 0,
        limit: int = 20,
    ) -> dict:
        return q.search_players(data, name, nationality, club, position, min_overall, limit)

    @server.tool(
        name="brazilian_players_by_club",
        description="Brazilian players grouped by Brazilian club, with counts and average ratings.",
    )
    def brazilian_players_by_club(limit: int = 15) -> dict:
        return q.brazilian_players_by_club(data, limit)

    @server.tool(
        name="biggest_wins",
        description="Largest goal-margin victories, optionally limited to one competition.",
    )
    def biggest_wins(competition: str | None = None, limit: int = 10) -> dict:
        return q.biggest_wins(data, competition, limit)

    @server.tool(
        name="goals_statistics",
        description=(
            "Average goals per match and home/away win rates, optionally for "
            "one competition."
        ),
    )
    def goals_statistics(competition: str | None = None) -> dict:
        return q.goals_statistics(data, competition)

    @server.tool(
        name="best_record",
        description="Teams with the best home or away record by win rate.",
    )
    def best_record(
        venue: str = "home",
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 10,
        limit: int = 10,
    ) -> dict:
        return q.best_record(data, venue, competition, season, min_matches, limit)

    @server.tool(
        name="season_comparison",
        description="Compare aggregate statistics between two seasons.",
    )
    def season_comparison(
        season_a: int, season_b: int, competition: str | None = None
    ) -> dict:
        return q.season_comparison(data, season_a, season_b, competition)

    @server.tool(
        name="find_derbies",
        description="Find derby matches between traditional rivals (Fla-Flu, Grenal, ...), optionally by season.",
    )
    def find_derbies(season: int | None = None, limit: int = 50) -> dict:
        return q.find_derbies(data, season, limit)

    @server.tool(
        name="list_teams",
        description="List all team names known to the server (normalized keys).",
    )
    def list_teams() -> dict:
        return {"teams": data.all_teams()}

    @server.tool(
        name="list_competitions",
        description="List competitions and the seasons covered in the data.",
    )
    def list_competitions() -> dict:
        comps: dict[str, set] = {}
        for m in data.matches:
            comps.setdefault(m.competition, set()).add(m.season)
        return {
            "competitions": [
                {
                    "competition": comp,
                    "seasons": sorted(s for s in seasons if s),
                    "matches": sum(1 for m in data.matches if m.competition == comp),
                }
                for comp, seasons in sorted(comps.items())
            ]
        }

    return server


def main() -> None:
    """Run the server over stdio."""
    build_server().run()


if __name__ == "__main__":
    main()
