"""
MCP tool surface: the Brazilian Soccer MCP server.

Context (Why): TASK.md requires "an MCP server connected to an LLM for query
processing". The LLM turns natural-language questions into typed tool calls,
so each tool below mirrors one capability family from the spec: match
queries, team queries, player queries, competition queries and statistical
analysis (plus discovery helpers). Tools return pre-formatted text in the
"Example answer format" style of TASK.md so the LLM can quote them directly.

What:
    * Uses the official `mcp` SDK v2.x class ``MCPServer`` (FastMCP was
      renamed in SDK 2.x) over stdio.
    * ``get_service()`` builds the SoccerService once (single ~1 s CSV load)
      and caches it; ``BRAZILIAN_SOCCER_DATA_DIR`` can point elsewhere.
    * Every tool wraps its service call in a friendly error handler so a
      bad team name or unknown competition returns guidance text instead of
      killing the session.
    * Tool docstrings double as LLM prompts: they name the natural-language
      questions each tool answers (from TASK.md "Sample Questions").

Test: tests/test_server.py exercises the tools through an in-memory MCP
client session (list_tools + call_tool) end-to-end.
Spec reference: TASK.md "Required Capabilities", "Sample Questions and
Expected Behaviors", "Success Criteria" (performance budget).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer

from . import __version__, formatting as fmt
from .loaders import load_all
from .service import MatchSearchResult, SoccerService

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


@lru_cache(maxsize=1)
def get_service() -> SoccerService:
    """Build (once) the data-backed service used by every MCP tool."""
    data_dir = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR") or _DEFAULT_DATA_DIR
    return SoccerService(load_all(data_dir))


def _guard(call):  # noqa: ANN001 - small local helper
    """Run a tool body, converting expected errors into helpful text."""
    try:
        return call()
    except (ValueError, LookupError) as exc:
        return f"Could not answer: {exc}"


def build_server(service: Optional[SoccerService] = None) -> MCPServer:
    """Wire all MCP tools onto a MCPServer instance (injectable for tests)."""
    svc = service or get_service()
    mcp = MCPServer(
        name="brazilian-soccer-mcp",
        title="Brazilian Soccer MCP Server",
        description=(
            "Knowledge server for Brazilian soccer: matches (Brasileirão "
            "Séries A/B/C, Copa do Brasil, Copa Libertadores), teams, "
            "standings and FIFA player data."
        ),
        version=__version__,
    )

    # ------------------------------------------------------------------
    # Match queries (TASK.md "Required Capabilities" #1)
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "Search matches by team, opponent, competition, season, date range "
            "or stage. Answers questions like 'Show me all Flamengo vs "
            "Fluminense matches', 'What matches did Palmeiras play in 2023?', "
            "'Which teams did Santos face in the 2019 Libertadores?'. "
            "Dates use YYYY-MM-DD."
        )
    )
    def search_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        stage: Optional[str] = None,
        limit: int = 30,
    ) -> str:
        return _guard(
            lambda: fmt.format_match_search(
                svc.search_matches(
                    team=team,
                    opponent=opponent,
                    competition=competition,
                    season=season,
                    date_from=date_from,
                    date_to=date_to,
                    stage=stage,
                    limit=limit,
                )
            )
        )

    @mcp.tool(
        description=(
            "Head-to-head record between two teams: all their matches plus "
            "wins/draws/goals each. Answers 'Compare Palmeiras and Santos "
            "head-to-head', 'Who wins the Fla-Flu derby more?'"
        )
    )
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        return _guard(
            lambda: fmt.format_head_to_head(
                svc.head_to_head(team_a, team_b, competition=competition, season=season)
            )
        )

    @mcp.tool(
        description=(
            "Find final matches of a competition, e.g. 'Find all Copa do "
            "Brasil finals', 'Show the 2019 Copa Libertadores final'."
        )
    )
    def finals(competition: str, season: Optional[int] = None) -> str:
        def render() -> str:
            matches = svc.finals(competition, season)
            return fmt.format_match_search(
                MatchSearchResult(matches=matches, total=len(matches))
            )

        return _guard(render)

    # ------------------------------------------------------------------
    # Team queries (TASK.md "Required Capabilities" #2)
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "Win/draw/loss record and goals for a team, optionally filtered by "
            "season, competition and venue (home/away). Answers 'What is "
            "Corinthians' home record in 2022?', 'How did Grêmio do in the "
            "2023 Série A?'"
        )
    )
    def team_record(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",
    ) -> str:
        return _guard(
            lambda: fmt.format_team_stats(
                svc.team_record(team, season=season, competition=competition, venue=venue)
            )
        )

    @mcp.tool(
        description=(
            "Everything known about one team across all datasets: name "
            "variants, competitions and seasons played, all-time record, and "
            "its FIFA squad (cross-file player+match data). Answers 'What "
            "competitions has Palmeiras played in?'."
        )
    )
    def team_overview(team: str) -> str:
        def render() -> str:
            info = svc.team_overview(team)
            team_ref = info["team"]
            record = info["record"]
            lines = [f"{team_ref.display} (canonical id: {team_ref.team_id})"]
            if info["variants"]:
                lines.append(
                    "Name variants in data: " + ", ".join(info["variants"][:8])
                )
            comps = info["competitions"]
            if comps:
                lines.append("Competitions played:")
                for comp, seasons in comps.items():
                    if len(seasons) > 6:
                        seasons_txt = f"{seasons[0]}-{seasons[-1]} ({len(seasons)} seasons)"
                        lines.append(f"- {comp}: {seasons_txt}")
                    else:
                        lines.append(f"- {comp}: {', '.join(map(str, seasons))}")
            lines.append(
                f"All-time record in match data: {record.summary_line()}"
            )
            if info["squad_in_fifa"]:
                lines.append(
                    f"FIFA squad: {info['squad_size']} players (see club_squad tool)"
                )
            else:
                lines.append(
                    "FIFA squad: not in the FIFA snapshot for this team"
                )
            return "\n".join(lines)

        return _guard(render)

    # ------------------------------------------------------------------
    # Competition queries (TASK.md "Required Capabilities" #4)
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "League standings calculated from match results, with champion and "
            "relegation zone marked. Answers 'Show the 2019 Brasileirão "
            "table', 'How did Fortaleza finish in 2023?'"
        )
    )
    def standings(competition: str, season: Optional[int] = None) -> str:
        return _guard(
            lambda: fmt.format_standings(svc.standings(competition, season))
        )

    @mcp.tool(
        description=(
            "Who won a competition in a season: league champion from the "
            "calculated table, or cup winner from the finals. Answers 'Who "
            "won the 2019 Brasileirão?', 'Who won the 2020 Copa Libertadores?'"
        )
    )
    def champion(competition: str, season: Optional[int] = None) -> str:
        return _guard(lambda: svc.champion(competition, season))

    @mcp.tool(
        description=(
            "Bottom teams (relegation zone) of a league season. Answers "
            "'Which teams were relegated in 2019?'."
        )
    )
    def relegated(competition: str, season: Optional[int] = None, n: int = 4) -> str:
        def render() -> str:
            canonical = svc.resolve_competition(competition)
            return fmt.format_relegated(
                svc.relegated(canonical, season, n), canonical, season
            )

        return _guard(render)

    # ------------------------------------------------------------------
    # Statistical analysis (TASK.md "Required Capabilities" #5)
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "Aggregate statistics: average goals per match and home/draw/away "
            "win rates. Answers 'What's the average goals per match in the "
            "Brasileirão?', 'Compare home advantage across competitions'."
        )
    )
    def competition_stats(
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        return _guard(
            lambda: fmt.format_competition_stats(
                svc.competition_stats(competition=competition, season=season)
            )
        )

    @mcp.tool(
        description=(
            "Biggest winning margins in the dataset. Answers 'Show me the "
            "biggest wins in the dataset', 'Largest victory in the 2012 "
            "Libertadores?'."
        )
    )
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        return _guard(
            lambda: fmt.format_biggest_wins(
                svc.biggest_wins(competition=competition, season=season, limit=limit),
                scope=" ".join(
                    p for p in [str(season or ""), competition or ""] if p
                ) or None,
            )
        )

    @mcp.tool(
        description=(
            "Teams with the best home or away records (by win rate). Answers "
            "'Which team has the best away record?', 'Best home team of "
            "2022?'."
        )
    )
    def best_records(
        venue: str = "home",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 10,
    ) -> str:
        def render() -> str:
            records = svc.best_records(
                venue=venue, competition=competition, season=season,
                min_matches=min_matches,
            )
            scope = " ".join(p for p in [str(season or ""), competition or ""] if p)
            scope_txt = f"in {scope}" if scope else "in the dataset"
            return fmt.format_best_records(records, venue, scope_txt)

        return _guard(render)

    @mcp.tool(
        description=(
            "Matches between famous rival pairs (Fla-Flu, Grenal, Derby "
            "Paulista, Ba-Vi, Clássico-Rei and more). Answers 'Show me all "
            "derbies in 2023'."
        )
    )
    def derbies(season: Optional[int] = None, competition: Optional[str] = None) -> str:
        return _guard(
            lambda: fmt.format_derbies(svc.derby_matches(season=season, competition=competition))
        )

    @mcp.tool(
        description=(
            "Side-by-side aggregate comparison of two seasons of a "
            "competition. Answers 'Compare the 2018 and 2019 Brasileirão "
            "seasons'."
        )
    )
    def compare_seasons(competition: str, season_a: int, season_b: int) -> str:
        return _guard(lambda: svc.compare_seasons(competition, season_a, season_b))

    # ------------------------------------------------------------------
    # Player queries (TASK.md "Required Capabilities" #3)
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "Search FIFA player data by name, nationality, club, position, "
            "minimum overall rating or maximum age. Answers 'Find all "
            "Brazilian players', 'Show me all forwards from São Paulo FC', "
            "'Highest-rated players at Santos?'."
        )
    )
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_age: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        def render() -> str:
            players = svc.search_players(
                name=name,
                nationality=nationality,
                club=club,
                position=position,
                min_overall=min_overall,
                max_age=max_age,
                limit=limit,
            )
            criteria = ", ".join(
                f"{k}={v}"
                for k, v in [
                    ("name", name), ("nationality", nationality), ("club", club),
                    ("position", position), ("min_overall", min_overall),
                    ("max_age", max_age),
                ]
                if v is not None
            ) or "no filter"
            return fmt.format_players(players, f"Players matching {criteria}")

        return _guard(render)

    @mcp.tool(
        description=(
            "Full profile of one player including ratings and top skills. "
            "Answers 'Who is Gabriel Barbosa?', 'How good is Neymar?'."
        )
    )
    def player_profile(name: str) -> str:
        def render() -> str:
            p = svc.player_profile(name)
            lines = [
                f"{p.name} ({p.nationality})",
                f"- Club: {p.club or 'free agent'}",
                f"- Position: {p.position}, Jersey: {p.jersey_number}",
                f"- Age: {p.age}",
                f"- Overall/Potential: {p.overall}/{p.potential}",
                f"- Preferred foot: {p.preferred_foot}",
            ]
            if p.height_cm or p.weight_kg:
                lines.append(f"- Physique: {p.height_cm or '?'} cm, {p.weight_kg or '?'} kg")
            if p.attrs:
                top = sorted(p.attrs.items(), key=lambda kv: -kv[1])[:5]
                lines.append("- Top skills: " + ", ".join(f"{k} {v}" for k, v in top))
            return "\n".join(lines)

        return _guard(render)

    @mcp.tool(
        description=(
            "The FIFA squad of a club, bridging match data and player data. "
            "Answers 'Which players play for Santos?', 'Who are the "
            "highest-rated players at Grêmio?'. Note: the FIFA snapshot only "
            "covers some Brazilian clubs."
        )
    )
    def club_squad(club: str) -> str:
        return _guard(lambda: fmt.format_squad(svc.club_squad(club)))

    @mcp.tool(
        description=(
            "Highest-rated Brazilian players in the FIFA dataset. Answers "
            "'Who are the top Brazilian players?'."
        )
    )
    def top_brazilian_players(limit: int = 10) -> str:
        return _guard(
            lambda: fmt.format_players(
                svc.top_brazilian_players(limit), "Top-rated Brazilian players in dataset"
            )
        )

    @mcp.tool(
        description=(
            "Counts and average ratings of Brazilian players at Brazilian "
            "clubs. Answers 'How many Brazilians play at Santos on average "
            "rating?'."
        )
    )
    def brazilians_at_brazilian_clubs(limit: int = 15) -> str:
        return _guard(
            lambda: fmt.format_brazilians_at_clubs(svc.brazilians_at_brazilian_clubs(limit))
        )

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "List all competitions available in the dataset with season "
            "coverage. Use it when unsure what can be queried."
        )
    )
    def list_competitions() -> str:
        lines = []
        for comp in svc.competitions():
            seasons = svc.seasons(comp)
            if seasons:
                lines.append(f"- {comp}: {seasons[0]}-{seasons[-1]} ({len(seasons)} seasons)")
            else:
                lines.append(f"- {comp}")
        return "Competitions in dataset:\n" + "\n".join(lines)

    @mcp.tool(
        description="List seasons available for a competition (or all seasons).")
    def list_seasons(competition: Optional[str] = None) -> str:
        def render() -> str:
            comp = svc.resolve_competition(competition) if competition else None
            seasons = svc.seasons(comp)
            label = comp or "all competitions"
            return f"Seasons for {label}: {', '.join(map(str, seasons))}"

        return _guard(render)

    return mcp


def main() -> None:
    """Entrypoint: run the MCP server over stdio."""
    server = build_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
