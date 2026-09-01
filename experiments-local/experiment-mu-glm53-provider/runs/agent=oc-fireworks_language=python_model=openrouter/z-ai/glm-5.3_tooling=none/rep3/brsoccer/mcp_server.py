"""MCP (Model Context Protocol) server exposing the soccer query engine.

Built on the official ``mcp`` SDK (v2.x, ``mcp.server.mcpserver.MCPServer``)
over stdio.  Every tool returns a pre-formatted plain-text answer (see
:mod:`brsoccer.formatting`) so an LLM can relay it directly; friendly
error text is returned instead of protocol errors for bad arguments.

Run with::

    python server.py            # stdio MCP server (default transport)

The datasets are located via :func:`brsoccer.data.find_data_dir`
(``BRSOCCER_DATA_DIR`` env var, ``./data/kaggle``, or the repo layout)
and loaded once, lazily, on the first tool call.
"""

from __future__ import annotations

import sys
import threading
from functools import wraps

from mcp.server.mcpserver import MCPServer

from . import formatting as fmt
from . import queries as q
from .data import COMPETITIONS, SoccerData, load_default

_DATA: SoccerData | None = None
_LOAD_LOCK = threading.Lock()


def _soccer_data() -> SoccerData:
    """Load the datasets once (thread-safe, lazy)."""
    global _DATA
    if _DATA is None:
        with _LOAD_LOCK:
            if _DATA is None:
                print("[brsoccer] loading datasets ...", file=sys.stderr, flush=True)
                _DATA = load_default()
                print(
                    f"[brsoccer] loaded {_DATA.matches and len(_DATA.matches)} matches, "
                    f"{len(_DATA.players)} players, {len(_DATA.registry.entries)} teams",
                    file=sys.stderr,
                    flush=True,
                )
    return _DATA


def _note_for(name: str | None) -> str:
    """Append disambiguation note when a team query matched several clubs."""
    if not name:
        return ""
    note = q.alternatives_note(_soccer_data(), name)
    return f"\n{note}" if note else ""


def _friendly_errors(fn):
    """Turn QueryError into guidance text instead of a protocol error."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except q.QueryError as err:
            return f"Cannot answer this question with the available data: {err}"

    return wrapper


def build_server(data: SoccerData | None = None) -> MCPServer:
    """Construct the MCPServer with all tools registered."""
    if data is not None:
        global _DATA
        _DATA = data

    server = MCPServer(
        name="brazilian-soccer",
        title="Brazilian Soccer Knowledge Server",
        description=(
            "Natural-language-ready queries about Brazilian soccer: matches, teams, "
            "players, competitions and statistics, from Kaggle datasets covering the "
            "Brasileirao (2003-2023), Copa do Brasil (2012-2023), Copa Libertadores "
            "(2013-2022) and a FIFA player database."
        ),
    )

    def register(fn):
        """Combined decorator: friendly errors + MCP registration."""
        return server.tool()(_friendly_errors(fn))

    # ------------------------------------------------------------ team tools

    @register
    def find_team(name: str) -> str:
        """Resolve a team name (any spelling variant) to its canonical form.

        Handles 'Palmeiras-SP', 'ATHLETICO PARANAENSE', 'Red Bull Bragantino',
        accented and unaccented spellings. Use this to disambiguate before
        other queries; also lists other clubs matching an ambiguous name.
        """
        sd = _soccer_data()
        results = sd.registry.resolve(name, limit=8)
        if not results or sd.registry.entry_of(results[0].key) is None:
            return f"No team found for '{name}'."
        lines = [f"Teams matching '{name}':"]
        for rank, res in enumerate(results, start=1):
            exact = " (exact match)" if res.exact else ""
            lines.append(f"{rank}. {res.display} - {res.match_count} matches in dataset{exact}")
        return "\n".join(lines)

    @register
    def search_matches(
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        stage: str | None = None,
        limit: int = 30,
    ) -> str:
        """Search matches by team, opponent, competition, season, date range or stage.

        competition: 'serie_a'/'serie_b'/'serie_c'/'copa_do_brasil'/'libertadores'
        (aliases like 'brasileirao' or 'copa' also work). date_from/date_to:
        'YYYY-MM-DD'. stage: round number or cup stage, e.g. 'final' for
        Libertadores finals, '8' (the Final) for Copa do Brasil.
        Examples: all Flamengo vs Fluminense matches; Palmeiras games in 2023.
        """
        sd = _soccer_data()
        matches = q.find_matches(
            sd,
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            stage=stage,
            limit=max(1, min(limit, 200)),
        )
        title_bits = []
        if team:
            title_bits.append(sd.team_display(q.resolve_team(sd, team)))
        if opponent:
            title_bits.append("vs " + sd.team_display(q.resolve_team(sd, opponent)))
        title_bits.append("matches")
        if season:
            title_bits.append(str(season))
        if competition:
            code = q._resolve_competition(competition)
            title_bits.append(COMPETITIONS.get(code, competition))
        text = fmt.format_matches(matches, " ".join(title_bits))
        return text + _note_for(team)

    @register
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: str | None = None,
        season: int | None = None,
    ) -> str:
        """Head-to-head record between two teams (wins/draws/goals + matches)."""
        sd = _soccer_data()
        h2h = q.head_to_head(sd, team_a, team_b, competition=competition, season=season)
        return fmt.format_head_to_head(h2h) + _note_for(team_a) + _note_for(team_b)

    @register
    def team_stats(
        team: str,
        season: int | None = None,
        competition: str | None = None,
    ) -> str:
        """Win/draw/loss record and goals for a team, with home and away splits.

        Filter by season (e.g. 2022) and/or competition. Answers questions
        like 'What is Corinthians' home record in 2022?' (see the home block).
        """
        sd = _soccer_data()
        stats = q.team_stats(sd, team, season=season, competition=competition)
        return fmt.format_team_stats(stats) + _note_for(team)

    @register
    def last_match(team: str, opponent: str | None = None) -> str:
        """Most recent recorded match of a team (optionally vs an opponent)."""
        sd = _soccer_data()
        match = q.last_match(sd, team, opponent=opponent)
        display = sd.team_display(q.resolve_team(sd, team))
        return fmt.format_last_match(match, display) + _note_for(team)

    @register
    def team_competitions(team: str) -> str:
        """Competitions a team has played in (Brasileirao, Copa, Libertadores...)."""
        sd = _soccer_data()
        rows = q.team_competitions(sd, team)
        return fmt.format_team_competitions(rows, sd.team_display(q.resolve_team(sd, team))) + _note_for(team)

    # ---------------------------------------------------- competition tools

    @register
    def standings(competition: str = "serie_a", season: int | None = None) -> str:
        """League table computed from match results; defaults to latest season.

        Only league competitions have standings (serie_a, serie_b, serie_c).
        The leader is marked 'Champion'. For cups, use search_matches with
        stage='final' instead.
        """
        sd = _soccer_data()
        code = q._resolve_competition(competition, default="serie_a")
        table = q.standings(sd, competition, season)
        chosen = season if season is not None else sd.seasons_for(code)[-1]
        return fmt.format_standings(table, COMPETITIONS[code], chosen)

    @register
    def relegation(competition: str = "serie_a", season: int | None = None, n: int = 4) -> str:
        """Bottom N teams of a league table (the relegated zone, default 4)."""
        sd = _soccer_data()
        rows = q.relegation(sd, competition, season, n=n)
        code = q._resolve_competition(competition, default="serie_a")
        chosen = season if season is not None else sd.seasons_for(code)[-1]
        return fmt.format_relegation(rows, COMPETITIONS[code], chosen)

    @register
    def competition_info(competition: str | None = None) -> str:
        """Coverage summary: seasons, match counts and teams per competition.

        Call without arguments for an overview of all competitions.
        """
        sd = _soccer_data()
        return fmt.format_competition_info(q.competition_info(sd, competition))

    # ------------------------------------------------------- statistics tools

    @register
    def competition_stats(
        competition: str | None = None,
        season: int | None = None,
    ) -> str:
        """Aggregate stats: average goals per match, home/draw/away win rates.

        Without arguments this covers the whole dataset (all competitions).
        """
        sd = _soccer_data()
        stats = q.competition_stats(sd, competition, season)
        label = "Dataset-wide statistics" if not competition else COMPETITIONS[q._resolve_competition(competition)]
        if season:
            label += f" {season}"
        return fmt.format_stats(stats, label)

    @register
    def biggest_wins(
        competition: str | None = None,
        season: int | None = None,
        team: str | None = None,
        limit: int = 10,
    ) -> str:
        """Largest goal-margin victories (optionally for one competition/team)."""
        sd = _soccer_data()
        matches = q.biggest_wins(sd, competition, season, team=team, limit=limit)
        label = "Biggest victories" + (f" - {team}" if team else "")
        return fmt.format_biggest_wins(matches, label) + _note_for(team)

    @register
    def best_records(
        venue: str = "home",
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 10,
    ) -> str:
        """Rank teams by win rate at a venue: 'home', 'away' or 'all'.

        Answers 'Which team has the best away record?' style questions.
        """
        sd = _soccer_data()
        ranked = q.best_records(sd, venue=venue, competition=competition, season=season, min_matches=min_matches)
        label = ""
        if season:
            label += f" {season}"
        if competition:
            label += f" {COMPETITIONS[q._resolve_competition(competition)]}"
        return fmt.format_best_records(ranked, venue, label.strip() or "whole dataset")

    @register
    def derbies(season: int | None = None, competition: str | None = None) -> str:
        """Famous derby matches (Fla-Flu, GreNal, Majestoso, Ba-Vi, ...).

        Filter by season and/or competition.
        """
        sd = _soccer_data()
        groups = q.derbies(sd, season=season, competition=competition)
        return fmt.format_derbies(groups, season)

    # ---------------------------------------------------------- player tools

    @register
    def search_players(
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = 20,
    ) -> str:
        """Search the FIFA player database (18,207 players).

        Filter by name (substring), nationality (e.g. 'Brazil'), club
        (Brazilian club names in any spelling work), position (FIFA codes:
        ST, LW, CAM, GK, ...) and overall rating. At least one filter is
        required. Results are sorted by Overall descending.
        """
        sd = _soccer_data()
        players = q.search_players(
            sd,
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
            limit=max(1, min(limit, 100)),
        )
        title_bits = ["Players"]
        if nationality:
            title_bits.insert(1, f"from {nationality}")
        if club:
            title_bits.insert(1, f"at {club}")
        if position:
            title_bits.insert(1, f"playing {position}")
        text = fmt.format_players(players, " ".join(title_bits))
        if club and not players:
            club_key = sd.registry.key_of(club)
            if sd.registry.entry_of(club_key) is not None:
                text = (
                    f"No players found at {club} in the FIFA player snapshot (~FIFA 19 era). "
                    "That snapshot omits several Brazilian clubs -- Flamengo, Palmeiras, "
                    "Corinthians, Sao Paulo and Vasco have no squads in it. Brazilian clubs "
                    "that ARE present include Gremio, Atletico Mineiro, Cruzeiro, Fluminense, "
                    "Santos, Internacional, Botafogo and Bahia (see club_overview)."
                )
        return text + _note_for(club or "")

    @register
    def club_overview(nationality: str = "Brazil") -> str:
        """Players of a nationality grouped by their Brazilian clubs.

        Answers 'Find all Brazilian players in the dataset' with a
        per-club breakdown (count + average rating).
        """
        sd = _soccer_data()
        groups = q.club_overview(sd, nationality=nationality)
        return fmt.format_club_overview(groups, nationality)

    # ------------------------------------------------------------- meta tools

    @register
    def data_summary() -> str:
        """Overview of the loaded datasets: match counts, seasons, player counts."""
        return fmt.format_data_summary(q.data_summary(_soccer_data()))

    return server


def main() -> None:
    """Run the MCP server over stdio (the standard MCP transport)."""
    server = build_server()
    # Touch the data so the server is warm before the first request.
    _soccer_data()
    server.run("stdio")


__all__ = ["build_server", "main"]
