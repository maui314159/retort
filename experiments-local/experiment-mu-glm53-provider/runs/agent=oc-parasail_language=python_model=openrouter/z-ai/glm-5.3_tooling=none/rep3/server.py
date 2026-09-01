"""Brazilian Soccer MCP server.

Run with::

    python server.py            # stdio transport (default)
    python server.py --http     # streamable-http on 127.0.0.1:8000

Exposes the unified Brazilian soccer knowledge base (6 Kaggle CSV files:
matches from Brasileirão, Copa do Brasil, Libertadores, Serie B/C, plus
the FIFA player database) as MCP tools so an LLM can answer natural
language questions about players, teams, matches, competitions and
statistics.

Tool categories (see the spec, "Required Capabilities"):

* Match queries     - search_matches, head_to_head, last_match_between
* Team queries      - team_stats, team_profile, team_competitions, search_teams
* Player queries    - search_players, player_details
* Competition       - standings, champion, competition_finals, list_competitions
* Statistics       - biggest_wins, competition_stats, best_records,
                      compare_seasons, derbies
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Make the package importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from brazilian_soccer import load_soccer_data
from brazilian_soccer.analysis import AnalysisError
from brazilian_soccer.loader import DEFAULT_DATA_DIR, SoccerData

SERVER_NAME = "brazilian-soccer"
SERVER_INSTRUCTIONS = (
    "Knowledge base of Brazilian soccer (Brasileirão 2003-2023, Copa do "
    "Brasil 2012-2023, Copa Libertadores 2013-2022, Série B/C 2014-2023 "
    "and an 18k-player FIFA database). Team names are normalized across "
    "datasets, so queries like 'Palmeiras', 'palmeiras-sp' or 'Athletico' "
    "all work. Use the tools to answer questions about matches, teams, "
    "players, standings, head-to-head records and statistics."
)

_DATA_CACHE: Optional[SoccerData] = None


def _get_data() -> SoccerData:
    """Load the dataset once per process (module-level cache)."""
    global _DATA_CACHE
    if _DATA_CACHE is None:
        _DATA_CACHE = load_soccer_data(DEFAULT_DATA_DIR)
    return _DATA_CACHE


def _friendly(message: str) -> str:
    return f"Could not answer: {message}"


def build_server(data: Optional[SoccerData] = None):
    """Construct the MCP server; used by both the CLI and the tests."""
    from mcp.server.mcpserver import MCPServer

    if data is None:
        data = _get_data()

    import brazilian_soccer.analysis as an
    import brazilian_soccer.formatting as fmt

    server = MCPServer(
        name=SERVER_NAME,
        version="1.0.0",
        instructions=SERVER_INSTRUCTIONS,
    )

    # ------------------------------------------------------------------
    # Match queries
    # ------------------------------------------------------------------

    @server.tool()
    def search_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Search matches by team, opponent, competition, season or date range.

        Team names are matched flexibly (accents, state suffixes and full
        names all work). 'competition' accepts: Brasileirão, Copa do Brasil,
        Libertadores, Serie B, Serie C. Dates use YYYY-MM-DD. Use opponent
        together with team for head-to-head listings.
        """
        try:
            result = an.search_matches(
                data,
                team=team,
                opponent=opponent,
                competition=competition,
                season=season,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
            )
            return fmt.format_search_matches(result)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """All matches between two teams plus their win/draw/loss record.

        Example: team_a='Flamengo', team_b='Fluminense' returns every
        Fla-Flu in the dataset and who won the head-to-head.
        """
        try:
            result = an.head_to_head(data, team_a, team_b, competition=competition, limit=limit)
            return fmt.format_head_to_head(result)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def last_match_between(team_a: str, team_b: str) -> str:
        """The most recent match between two teams, with score and stats."""
        try:
            match = an.last_match_between(data, team_a, team_b)
            display_a = an.resolve_team(data, team_a).display
            display_b = an.resolve_team(data, team_b).display
            return fmt.format_last_match(match, display_a, display_b)
        except AnalysisError as exc:
            return _friendly(str(exc))

    # ------------------------------------------------------------------
    # Team queries
    # ------------------------------------------------------------------

    @server.tool()
    def team_stats(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> str:
        """Win/draw/loss record, goals scored/conceded and home/away splits.

        Leave season and competition empty for the all-time record, e.g.
        team='Corinthians', season=2022 for its 2022 Brasileirão record.
        """
        try:
            result = an.team_stats(data, team, season=season, competition=competition)
            return fmt.format_team_stats(result)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def team_profile(team: str) -> str:
        """Everything about one team: name variants, competitions played,
        seasons, all-time record and its FIFA player squad (cross-file)."""
        try:
            result = an.team_profile(data, team)
            return fmt.format_team_profile(result)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def team_competitions(team: str) -> str:
        """Which competitions and seasons a team appears in, with records."""
        try:
            result = an.team_profile(data, team)
            return fmt.format_team_profile(result)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def search_teams(query: str, limit: int = 10) -> str:
        """Resolve a team name (fuzzy) and show its canonical variants.

        Use this when unsure how a club is spelled, e.g. query='athletico'
        lists Athletico Paranaense and its name variants.
        """
        try:
            teams = an.search_teams(data, query, limit=limit)
            return fmt.format_team_search(teams, query)
        except AnalysisError as exc:
            return _friendly(str(exc))

    # ------------------------------------------------------------------
    # Player queries
    # ------------------------------------------------------------------

    @server.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        sort_by: str = "overall",
        limit: int = 20,
    ) -> str:
        """Search the FIFA player database (18,207 players).

        Filter by name substring, nationality (e.g. 'Brazil'), club,
        position (e.g. 'ST', 'LW', or a group like 'forward') and minimum
        overall rating. sort_by: overall (default), potential, age, name.
        Example: nationality='Brazil', sort_by='overall' for the best
        Brazilian players.
        """
        try:
            result = an.search_players(
                data,
                name=name,
                nationality=nationality,
                club=club,
                position=position,
                min_overall=min_overall,
                max_overall=max_overall,
                sort_by=sort_by,
                limit=limit,
            )
            return fmt.format_players(result)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def player_details(name: str) -> str:
        """Full profile for a player: ratings, club, position, skills.

        Example: name='Neymar' returns Neymar Jr's complete FIFA attributes.
        """
        try:
            players = an.player_details(data, name)
            return fmt.format_player_details(players)
        except AnalysisError as exc:
            return _friendly(str(exc))

    # ------------------------------------------------------------------
    # Competition queries
    # ------------------------------------------------------------------

    @server.tool()
    def standings(competition: str, season: int) -> str:
        """League table calculated from match results (3 points per win).

        Marks the champion and the relegation zone (bottom four).
        Example: competition='Brasileirão', season=2019.
        """
        try:
            table, notes = an.standings(data, competition, season)
            return fmt.format_standings(table, notes)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def champion(competition: str, season: int) -> str:
        """Who won a competition in a given season.

        Leagues: top of the calculated table. Cups: winner of the final.
        Example: competition='Copa do Brasil', season=2019.
        """
        try:
            result = an.champion(data, competition, season)
            return fmt.format_champion(result)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def competition_finals(
        competition: str,
        season: Optional[int] = None,
    ) -> str:
        """Final-round matches of cup competitions (with winners).

        Leave season empty to list every recorded final.
        Example: competition='Libertadores' lists all Libertadores finals.
        """
        try:
            finals = an.competition_finals(data, competition, season=season)
            return fmt.format_finals(finals)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def list_competitions() -> str:
        """Competitions available, with season coverage and match counts."""
        comps = an.list_competitions(data)
        return fmt.format_competitions(comps)

    # ------------------------------------------------------------------
    # Statistical analysis
    # ------------------------------------------------------------------

    @server.tool()
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Largest victory margins in the dataset (or one competition)."""
        try:
            matches = an.biggest_wins(data, competition=competition, season=season, limit=limit)
            scope = competition or "all competitions"
            if season:
                scope += f" {season}"
            return fmt.format_biggest_wins(matches, scope)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def competition_stats(
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        """Average goals per match, home/away win rates and draw rate.

        Example: competition='Brasileirão' for the league's scoring stats.
        """
        try:
            stats = an.competition_stats(data, competition=competition, season=season)
            return fmt.format_competition_stats(stats)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def best_records(
        venue: str = "home",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 10,
        limit: int = 10,
    ) -> str:
        """Teams ranked by win rate at a venue: 'home' or 'away'."""
        try:
            ranked = an.best_records(
                data,
                venue=venue,
                competition=competition,
                season=season,
                min_matches=min_matches,
                limit=limit,
            )
            scope = competition or "all competitions"
            if season:
                scope += f" {season}"
            return fmt.format_best_records(ranked, venue, scope)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def derbies(
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> str:
        """Matches between traditional rivals (Fla-Flu, Grenal, Majestoso...).

        Example: season=2023 for the 2023 derbies across competitions.
        """
        try:
            results = an.derbies(data, season=season, competition=competition)
            scope = competition or "all competitions"
            if season:
                scope += f" {season}"
            return fmt.format_derbies(results, scope)
        except AnalysisError as exc:
            return _friendly(str(exc))

    @server.tool()
    def compare_seasons(
        season_a: int,
        season_b: int,
        competition: str = "Brasileirão",
    ) -> str:
        """Compare two seasons side by side: champions, goals, home rates."""
        try:
            result = an.compare_seasons(data, season_a, season_b, competition=competition)
            return fmt.format_compare_seasons(result)
        except AnalysisError as exc:
            return _friendly(str(exc))

    # ------------------------------------------------------------------
    # Resource: dataset overview
    # ------------------------------------------------------------------

    @server.resource("brazilian-soccer://datasets")
    def datasets_resource() -> str:
        """Overview of the loaded datasets (files, rows, coverage)."""
        report = data.report
        lines = ["Brazilian soccer dataset (6 files):"]
        for filename, rows in report["files"].items():
            lines.append(f"- {filename}: {rows} rows")
        lines.append(f"- fifa_data.csv: {report['players']} players")
        lines.append(
            f"Unified: {report['unified_matches']} matches, {report['teams']} teams"
        )
        return "\n".join(lines)

    return server


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport to serve (default: stdio)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="HTTP host (streamable-http only)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="HTTP port (streamable-http only)"
    )
    args = parser.parse_args(argv)

    server = build_server()
    if args.transport == "stdio":
        server.run("stdio")
    else:
        server.run("streamable-http", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
