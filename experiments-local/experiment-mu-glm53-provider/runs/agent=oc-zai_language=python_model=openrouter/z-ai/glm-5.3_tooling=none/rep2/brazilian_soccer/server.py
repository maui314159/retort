"""MCP server exposing the Brazilian soccer query engine.

Every MCP tool wraps one query function, formats the result into the
human-readable style shown in the specification, and converts query errors
into helpful messages for the calling LLM rather than raising.

Run with ``python main.py`` (stdio transport) or instantiate
:func:`create_server` in tests.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from brazilian_soccer import query
from brazilian_soccer.data import (
    COMPETITION_DISPLAY,
    STAGE_DISPLAY,
    load_dataset,
)
from brazilian_soccer.normalize import DERBY_PAIRS
from brazilian_soccer.query import QueryError

INSTRUCTIONS = """Brazilian soccer knowledge server.

Datasets: Brasileirão Série A (2003-2023), Série B and Série C (2014-2023),
Copa do Brasil (2012-2023), Copa Libertadores (2013-2022), and a FIFA player
database (18,207 players).  Team names are matched leniently ("Palmeiras-SP",
"Palmeiras" and "palmeiras" all work); ambiguous names like "atletico" return
the list of candidates.  Dates accept YYYY-MM-DD or DD/MM/YYYY.  Standings
and statistics are computed from match results, always from a single
canonical source per competition/season to avoid double counting overlapping
datasets.
"""


def _score(match: dict) -> str:
    if match["home_goals"] is None or match["away_goals"] is None:
        return "N/A"
    return f"{match['home_goals']}-{match['away_goals']}"


def _context(match: dict) -> str:
    parts = [match["competition"]]
    if match["stage"]:
        parts.append(STAGE_DISPLAY.get(match["stage"], match["stage"].title()))
    elif match["round"]:
        parts.append(f"Round {match['round']}")
    return " ".join(parts)


def _match_line(match: dict) -> str:
    date = match["date"] or "unknown date"
    return f"- {date}: {match['home']} {_score(match)} {match['away']} ({_context(match)})"


def _more_line(result: dict) -> str:
    hidden = result["total"] - result["shown"]
    if hidden > 0:
        return f"... and {hidden} more matches in dataset (total {result['total']})"
    return f"Total: {result['total']} matches"


def _error(error: Exception) -> str:
    if isinstance(error, query.AmbiguousTeamError):
        joined = ", ".join(error.candidates)
        return (
            f"Ambiguous team name '{error.name}'. Candidates: {joined}. "
            f"Please be more specific."
        )
    if isinstance(error, query.TeamNotFoundError):
        suggestion = error.suggestion or "Check the spelling (e.g. 'Flamengo', 'Palmeiras')."
        return f"Team not found: '{error.name}'. {suggestion}"
    return f"Error: {error}"


def create_server(dataset=None) -> MCPServer:
    """Build the MCPServer with all tools registered."""
    ds = dataset or load_dataset()
    mcp = MCPServer(
        name="brazilian-soccer",
        title="Brazilian Soccer MCP",
        instructions=INSTRUCTIONS,
        version="1.0.0",
    )

    @mcp.tool()
    def search_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        stage: str | None = None,
        team_side: str = "any",
        limit: int = 20,
    ) -> str:
        """Search matches by team, opponent, competition, season, date range or stage.

        Args:
            team: team name (home, away or either depending on team_side).
            opponent: restrict to matches against this team.
            competition: "Serie A"/"Brasileirão", "Serie B", "Serie C",
                "Copa do Brasil" or "Libertadores".
            season: year, e.g. 2023.
            from_date: inclusive start date (YYYY-MM-DD or DD/MM/YYYY; a bare
                year also works).
            to_date: inclusive end date.
            stage: "final", "semifinal", "quarterfinal", "round of 16" or
                "group stage" (cups only).
            team_side: "any", "home" or "away" for the team filter.
            limit: maximum matches to list.
        """
        try:
            result = query.search_matches(
                ds, team=team, opponent=opponent, competition=competition,
                season=season, from_date=from_date, to_date=to_date,
                stage=stage, team_side=team_side, limit=limit,
            )
        except QueryError as exc:
            return _error(exc)
        filters = result["filters"]
        labels = []
        if filters["team"]:
            name = filters["team"]
            if filters["opponent"]:
                labels.append(f"{name} vs {filters['opponent']}")
            else:
                labels.append(name)
        elif filters["opponent"]:
            labels.append(f"vs {filters['opponent']}")
        if filters["competition"]:
            labels.append(filters["competition"])
        if filters["season"]:
            labels.append(str(filters["season"]))
        if filters["stage"]:
            labels.append(STAGE_DISPLAY.get(filters["stage"], filters["stage"]))
        title = "Matches" + (f" — {', '.join(labels)}" if labels else " (all)")
        if filters["team"] and filters["opponent"]:
            derby = DERBY_PAIRS.get(frozenset((
                query.resolve_team(ds, filters["team"]),
                query.resolve_team(ds, filters["opponent"]),
            )))
            if derby:
                title += f" ({derby})"
        lines = [title + ":"]
        for match in result["matches"]:
            lines.append(_match_line(match))
        lines.append(_more_line(result))
        return "\n".join(lines)

    @mcp.tool()
    def last_match_between(team_a: str, team_b: str) -> str:
        """When did one team last play another, and what was the score?"""
        try:
            result = query.last_match_between(ds, team_a, team_b)
        except QueryError as exc:
            return _error(exc)
        if result["match"] is None:
            return (
                f"No matches between {result['team_a']} and {result['team_b']} "
                f"in the dataset."
            )
        match = result["match"]
        return (
            f"Last {result['team_a']} vs {result['team_b']} match "
            f"({result['all_matches_between']} meetings in dataset):\n"
            + _match_line(match)
        )

    @mcp.tool()
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> str:
        """Head-to-head record between two teams (wins, draws, goals, matches)."""
        try:
            result = query.head_to_head(
                ds, team_a, team_b, competition=competition, season=season, limit=limit,
            )
        except QueryError as exc:
            return _error(exc)
        a, b = result["team_a"], result["team_b"]
        title = f"{a} vs {b} head-to-head"
        derby = DERBY_PAIRS.get(frozenset((
            query.resolve_team(ds, team_a), query.resolve_team(ds, team_b),
        )))
        if derby:
            title += f" ({derby})"
        if result["competition"]:
            title += f" — {result['competition']}"
        if result["season"]:
            title += f" {result['season']}"
        lines = [title + ":"]
        for match in result["matches"]:
            lines.append(_match_line(match))
        if result["total"] > len(result["matches"]):
            lines.append(f"... and {result['total'] - len(result['matches'])} more matches")
        lines.append(
            f"Head-to-head in dataset: {a} {result['wins_a']} wins, "
            f"{b} {result['wins_b']} wins, {result['draws']} draws "
            f"({result['total']} matches, goals {result['goals_a']}-{result['goals_b']})"
        )
        return "\n".join(lines)

    @mcp.tool()
    def team_stats(
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str = "all",
    ) -> str:
        """Win/draw/loss record for a team; filter by competition, season and venue.

        Args:
            team: team name.
            competition: "Serie A", "Serie B", "Serie C", "Copa do Brasil" or
                "Libertadores" (default: all).
            season: year (default: all).
            venue: "all", "home" or "away".
        """
        try:
            result = query.team_stats(
                ds, team, competition=competition, season=season, venue=venue,
            )
        except QueryError as exc:
            return _error(exc)
        venue_label = {"all": "", "home": " home", "away": " away"}[result["venue"]]
        scope = result["competition"]
        if result["season"]:
            scope += f" {result['season']}"
        lines = [
            f"{result['team']}{venue_label} record ({scope}):",
            f"- Matches: {result['played']}",
            f"- Wins: {result['wins']}, Draws: {result['draws']}, Losses: {result['losses']}",
            f"- Goals For: {result['goals_for']}, Goals Against: {result['goals_against']}",
        ]
        if result["win_rate"] is not None:
            lines.append(f"- Win rate: {result['win_rate']}%")
        if result["unscored_matches"]:
            lines.append(
                f"- Note: {result['unscored_matches']} fixture(s) in the dataset have no "
                f"recorded score and are excluded from the totals."
            )
        return "\n".join(lines)

    @mcp.tool()
    def best_records(
        competition: str | None = None,
        season: int | None = None,
        venue: str = "all",
        min_matches: int = 10,
        limit: int = 5,
    ) -> str:
        """Rank teams by win rate (e.g. best home record, best away record)."""
        try:
            result = query.best_records(
                ds, competition=competition, season=season, venue=venue,
                min_matches=min_matches, limit=limit,
            )
        except QueryError as exc:
            return _error(exc)
        venue_label = {"all": "overall", "home": "home", "away": "away"}[result["venue"]]
        scope = result["competition"]
        if result["season"]:
            scope += f" {result['season']}"
        lines = [f"Best {venue_label} records ({scope}, min {result['min_matches']} matches):"]
        for index, record in enumerate(result["records"], start=1):
            lines.append(
                f"{index}. {record['team']} - {record['win_rate']}% win rate "
                f"({record['wins']}W, {record['draws']}D, {record['losses']}L, "
                f"goals {record['goals_for']}-{record['goals_against']})"
            )
        return "\n".join(lines)

    @mcp.tool()
    def team_competitions(team: str) -> str:
        """Which competitions and seasons has a team played in (across all files)?"""
        try:
            result = query.team_competitions(ds, team)
        except QueryError as exc:
            return _error(exc)
        lines = [f"{result['team']} in the dataset ({result['total_matches']} matches):"]
        for comp in result["competitions"]:
            seasons = comp["seasons"]
            if len(seasons) > 6:
                span = f"{comp['first_season']}-{comp['last_season']}"
            else:
                span = ", ".join(str(s) for s in seasons)
            lines.append(f"- {comp['competition']}: {comp['matches']} matches ({span})")
        return "\n".join(lines)

    @mcp.tool()
    def team_profile(team: str, players_limit: int = 5) -> str:
        """Combined view of a team: record, competitions, and its players in the FIFA data."""
        try:
            result = query.team_profile(ds, team, players_limit=players_limit)
        except QueryError as exc:
            return _error(exc)
        record = result["record"]
        lines = [
            f"{result['team']} — profile",
            f"Dataset record: {record['played']} matches, {record['wins']}W "
            f"{record['draws']}D {record['losses']}L, goals {record['goals_for']}-"
            f"{record['goals_against']}"
            + (f", win rate {record['win_rate']}%" if record["win_rate"] is not None else ""),
            "Competitions: " + ", ".join(
                f"{c['competition']} ({c['first_season']}-{c['last_season']})"
                for c in result["competitions"]
            ),
        ]
        if result["top_players"]:
            lines.append(f"Top-rated players in FIFA data ({result['players_at_club']} total):")
            for player in result["top_players"]:
                lines.append(_player_line(player))
        else:
            lines.append("No players from this club in the FIFA dataset (it only covers selected clubs).")
        return "\n".join(lines)

    def _player_line(player: dict) -> str:
        bits = [f"{player['name']} - Overall: {player['overall']}"]
        if player["position"]:
            bits.append(f"Position: {player['position']}")
        if player["club"]:
            bits.append(f"Club: {player['club']}")
        if player["age"]:
            bits.append(f"Age: {player['age']}")
        return ", ".join(bits)

    @mcp.tool()
    def search_players(
        name: str | None = None,
        club: str | None = None,
        nationality: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = 20,
    ) -> str:
        """Search the FIFA player database (18,207 players).

        Args:
            name: substring of the player name.
            club: club name (Brazilian clubs included: Grêmio, Santos,
                Internacional, Botafogo, Fluminense, Cruzeiro, Bahia, ...).
            nationality: e.g. "Brazil".
            position: FIFA code (ST, LW, GK, ...) or group (forward,
                midfielder, defender, goalkeeper).
            min_overall / max_overall: rating bounds.
            limit: maximum players to list.
        """
        try:
            result = query.search_players(
                ds, name=name, club=club, nationality=nationality,
                position=position, min_overall=min_overall,
                max_overall=max_overall, limit=limit,
            )
        except QueryError as exc:
            return _error(exc)
        filters = result["filters"]
        labels = [
            f"{key.replace('_', ' ')}: {value}"
            for key, value in filters.items() if value is not None
        ]
        title = "Players" + (f" ({'; '.join(labels)})" if labels else " (all)")
        if not result["players"]:
            return title + ": no players found in the FIFA dataset."
        lines = [title + f" — {result['total']} found, showing {result['shown']}:"]
        for index, player in enumerate(result["players"], start=1):
            lines.append(f"{index}. {_player_line(player)}")
        return "\n".join(lines)

    @mcp.tool()
    def top_players(
        club: str | None = None,
        nationality: str | None = None,
        position: str | None = None,
        limit: int = 10,
    ) -> str:
        """Highest-rated players by club, nationality or position (e.g. top Brazilians)."""
        try:
            result = query.top_players(
                ds, club=club, nationality=nationality, position=position, limit=limit,
            )
        except QueryError as exc:
            return _error(exc)
        scope = []
        if nationality:
            scope.append(nationality)
        if club:
            scope.append(club)
        if position:
            scope.append(position)
        title = "Top-rated players" + (f" ({', '.join(scope)})" if scope else "")
        if not result["players"]:
            return title + ": no players found in the FIFA dataset."
        lines = [title + ":"]
        for index, player in enumerate(result["players"], start=1):
            lines.append(f"{index}. {_player_line(player)}")
        return "\n".join(lines)

    @mcp.tool()
    def players_by_club(
        nationality: str | None = "Brazil",
        limit: int = 15,
    ) -> str:
        """Aggregate players per club (default: Brazilian players at Brazilian clubs)."""
        try:
            result = query.players_by_club(ds, nationality=nationality, limit=limit)
        except QueryError as exc:
            return _error(exc)
        label = result["nationality"] or "all"
        lines = [f"{label} players at Brazilian clubs (FIFA data):"]
        for club in result["clubs"]:
            lines.append(
                f"- {club['club']}: {club['players']} players "
                f"(avg rating: {club['avg_overall']}, best: {club['best_player']})"
            )
        return "\n".join(lines)

    @mcp.tool()
    def standings(competition: str = "Serie A", season: int | None = None) -> str:
        """League standings computed from match results (default: latest Serie A season).

        For cups (Copa do Brasil, Libertadores) use champion or bracket instead.
        The bottom 4 of Serie A/Serie B are marked as the relegation zone.
        """
        try:
            result = query.standings(ds, competition, season)
        except QueryError as exc:
            return _error(exc)
        lines = [
            f"{result['competition']} {result['season']} standings "
            f"(calculated from {result['scored_matches']} scored matches in dataset):"
        ]
        for row in result["table"]:
            marks = []
            if row["champion"]:
                marks.append("Champion")
            if row["relegated"]:
                marks.append("Relegated")
            suffix = f" - {', '.join(marks)}" if marks else ""
            lines.append(
                f"{row['rank']}. {row['team']} - {row['points']} pts "
                f"({row['wins']}W, {row['draws']}D, {row['losses']}L, "
                f"goals {row['goals_for']}:{row['goals_against']}){suffix}"
            )
        return "\n".join(lines)

    @mcp.tool()
    def champion(competition: str, season: int | None = None) -> str:
        """Who won a competition in a season? Leagues: top of the table; cups: final result."""
        try:
            result = query.champion(ds, competition, season)
        except QueryError as exc:
            return _error(exc)
        header = f"{result['competition']} {result['season']}:"
        if result.get("champion") is None:
            note = result.get("method") or result.get("note") or "not determinable from the dataset"
            return f"{header} champion {note}"
        lines = [f"{header} champion: {result['champion']} (via {result['method']})."]
        if "record" in result:
            lines.append(
                f"Record: {result['points']} pts, {result['record']}; "
                f"runner-up: {result['runner_up']}."
            )
            if result.get("relegated"):
                lines.append(f"Relegated: {', '.join(result['relegated'])}.")
        if "legs" in result:
            for leg in result["legs"]:
                lines.append(
                    f"Final leg ({leg['date']}): {leg['home']} {leg['score']} {leg['away']}"
                )
            lines.append(
                f"Aggregate: {result['team_a']} {result['goals_a']} - "
                f"{result['goals_b']} {result['team_b']}"
            )
        if result.get("scored_matches"):
            lines.append(f"Calculated from {result['scored_matches']} scored matches in dataset.")
        return "\n".join(lines)

    @mcp.tool()
    def bracket(competition: str, season: int) -> str:
        """Knockout bracket for a cup (round of 16, quarterfinals, semifinals, final)."""
        try:
            result = query.bracket(ds, competition, season)
        except QueryError as exc:
            return _error(exc)
        if not result["rounds"]:
            return (
                f"{result['competition']} {result['season']}: "
                f"no knockout-stage matches in the dataset for this season."
            )
        lines = [f"{result['competition']} {result['season']} bracket:"]
        for round_ in result["rounds"]:
            lines.append(f"{round_['stage_display']}:")
            for tie in round_["ties"]:
                winner = tie["winner"] or "decided on penalties (not in dataset)"
                lines.append(
                    f"- {tie['team_a']} vs {tie['team_b']}: {tie['aggregate']} "
                    f"aggregate -> {winner}"
                )
        return "\n".join(lines)

    @mcp.tool()
    def competition_overview() -> str:
        """List available competitions, season coverage and dataset sizes."""
        result = query.competition_overview(ds)
        lines = [
            f"Datasets: {result['total_matches']} matches, {result['players']} players, "
            f"{result['teams']} teams."
        ]
        for comp in result["competitions"]:
            lines.append(
                f"- {comp['competition']} ({comp['kind']}): {comp['matches']} matches, "
                f"seasons {comp['first_season']}-{comp['last_season']}"
            )
        return "\n".join(lines)

    @mcp.tool()
    def average_goals(
        competition: str | None = None,
        season: int | None = None,
        team: str | None = None,
    ) -> str:
        """Average goals per match plus home/draw/away outcome rates."""
        try:
            result = query.average_goals(ds, competition=competition, season=season, team=team)
        except QueryError as exc:
            return _error(exc)
        scope = result["competition"]
        if result["season"]:
            scope += f" {result['season']}"
        if result["team"]:
            scope += f", {result['team']} matches"
        return (
            f"Goals per match ({scope}, {result['matches']} matches):\n"
            f"- Average goals per match: {result['avg_goals']}\n"
            f"- Home win rate: {result['home_win_rate']}%\n"
            f"- Draw rate: {result['draw_rate']}%\n"
            f"- Away win rate: {result['away_win_rate']}%\n"
            f"- Average home goals: {result['avg_home_goals']}, away goals: {result['avg_away_goals']}"
        )

    @mcp.tool()
    def biggest_wins(
        competition: str | None = None,
        season: int | None = None,
        team: str | None = None,
        limit: int = 5,
    ) -> str:
        """Biggest victory margins in the dataset."""
        try:
            result = query.biggest_wins(
                ds, competition=competition, season=season, team=team, limit=limit,
            )
        except QueryError as exc:
            return _error(exc)
        scope = result["competition"]
        if result["season"]:
            scope += f" {result['season']}"
        if result["team"]:
            scope += f", {result['team']} matches"
        lines = [f"Biggest victories ({scope}):"]
        for index, match in enumerate(result["wins"], start=1):
            lines.append(f"{index}. {_match_line(match)[2:]} (margin {match['margin']})")
        return "\n".join(lines)

    @mcp.tool()
    def derbies(
        season: int | None = None,
        team: str | None = None,
        limit: int = 30,
    ) -> str:
        """Matches between traditional rivals (Fla-Flu, Gre-Nal, Majestoso, Ba-Vi...)."""
        try:
            result = query.derbies(ds, season=season, team=team, limit=limit)
        except QueryError as exc:
            return _error(exc)
        scope = f" in {result['season']}" if result["season"] else ""
        if result["team"]:
            scope += f" involving {result['team']}"
        if not result["matches"]:
            return f"No derby matches found{scope}."
        lines = [f"Derby matches{scope} ({result['total']} found):"]
        for match in result["matches"]:
            lines.append(f"- [{match['derby']}] {_match_line(match)[2:]}")
        lines.append(
            "Known derbies: " + ", ".join(d["derby"] for d in result["known_derbies"])
        )
        return "\n".join(lines)

    @mcp.tool()
    def season_comparison(competition: str, season_a: int, season_b: int) -> str:
        """Compare two seasons of a competition (goals, home advantage, champion, biggest win)."""
        try:
            result = query.season_comparison(ds, competition, season_a, season_b)
        except QueryError as exc:
            return _error(exc)
        lines = [f"{result['competition']}: {season_a} vs {season_b}"]
        for summary in result["seasons"]:
            champion = summary.get("champion") or "n/a"
            biggest = summary.get("biggest_win")
            biggest_text = "n/a"
            if biggest:
                biggest_text = (
                    f"{biggest['home']} {biggest['home_goals']}-{biggest['away_goals']} "
                    f"{biggest['away']}"
                )
            lines.append(
                f"- {summary['season']}: {summary['matches']} matches, "
                f"{summary['avg_goals']} goals/match, home wins {summary['home_win_rate']}%, "
                f"champion {champion}, biggest win {biggest_text}"
            )
        return "\n".join(lines)

    return mcp
