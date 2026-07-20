"""FastMCP server exposing Brazilian-soccer knowledge-graph tools.

Context
-------
This module is the LLM-facing surface of the project.  It wraps the pure
query functions in :mod:`brazilian_soccer_mcp.queries` as MCP tools so that
a Model Context Protocol client (e.g. an LLM agent) can answer natural-
language questions about Brazilian soccer by calling tools such as
``find_matches``, ``head_to_head``, ``team_stats``, ``competition_standings``
and ``search_players``.

The :class:`~brazilian_soccer_mcp.knowledge_graph.KnowledgeGraph` is built
once at server start (loading all six CSV files, deduplicating cross-file
overlaps) and kept in a module-level singleton so repeated tool calls pay
the load cost only once.  Tool functions are thin adapters: they parse
optional string filters (dates come in as ISO ``YYYY-MM-DD`` strings) into
the typed arguments the query layer expects and return JSON-serializable
dicts.

Run with ``python -m brazilian_soccer_mcp`` (stdio transport) — see
``__main__.py``.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from . import queries
from .knowledge_graph import KnowledgeGraph
from .loader import load_dataset
from .normalize import parse_date


# Singleton knowledge graph built on first use.  Loading ~17k deduplicated
# matches + 18k players takes a couple of seconds; we cache it so tool calls
# are sub-second afterwards (spec requires <2s for simple lookups, <5s for
# aggregate queries).
_KG: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Return the process-wide knowledge graph, building it on first call."""

    global _KG
    if _KG is None:
        _KG = KnowledgeGraph(load_dataset())
    return _KG


def _parse_optional_date(value: Optional[str]) -> Optional[date]:
    if value is None or value == "":
        return None
    d = parse_date(value)
    return d


# Build the MCP server and register every tool.  We keep the construction in
# a function so tests can spin up a fresh server without importing side
# effects, and so ``__main__`` can control the transport.
def build_server() -> FastMCP:
    mcp = FastMCP(
        "brazilian-soccer-mcp",
        instructions=(
            "A knowledge graph of Brazilian soccer: matches (Brasileirão "
            "Série A, Copa do Brasil, Copa Libertadores, Série B/C, "
            "historical 2003-2019), teams, and FIFA players. Team names "
            "accept any spelling (state suffix, accents, long forms) and "
            "are normalized automatically. Use the list_* tools to "
            "discover competitions, seasons and teams before querying."
        ),
    )

    # ------------------------------------------------------------------
    # Discovery tools
    # ------------------------------------------------------------------

    @mcp.tool()
    def list_competitions() -> str:
        """List every competition known to the knowledge graph."""

        kg = get_knowledge_graph()
        return json.dumps({"competitions": kg.list_competitions()}, ensure_ascii=False)

    @mcp.tool()
    def list_seasons(competition: Optional[str] = None) -> str:
        """List seasons, optionally scoped to one competition."""

        kg = get_knowledge_graph()
        if competition:
            node = kg.competition(competition)
            if node is None:
                return json.dumps({"competition": competition, "seasons": []})
            seasons = sorted({m.season for m in node.matches if m.season is not None})
            return json.dumps({"competition": node.name, "seasons": seasons}, ensure_ascii=False)
        all_seasons = sorted({m.season for m in kg.dataset.matches if m.season is not None})
        return json.dumps({"seasons": all_seasons}, ensure_ascii=False)

    @mcp.tool()
    def list_teams(competition: Optional[str] = None, limit: int = 200) -> str:
        """List teams, optionally scoped to one competition."""

        kg = get_knowledge_graph()
        if competition:
            node = kg.competition(competition)
            if node is None:
                return json.dumps({"competition": competition, "teams": []})
            teams = sorted({m.home_team for m in node.matches} | {m.away_team for m in node.matches})
            return json.dumps({"competition": node.name, "teams": teams[:limit]}, ensure_ascii=False)
        return json.dumps({"teams": kg.list_teams()[:limit]}, ensure_ascii=False)

    @mcp.tool()
    def normalize_team_name(name: str) -> str:
        """Return the canonical display name for any team spelling."""

        kg = get_knowledge_graph()
        canon = kg.dataset.normalizer.canonical(name)
        return json.dumps(
            {"input": name, "canonical": canon, "raw_spellings": kg.dataset.normalizer.raw_spellings(name)},
            ensure_ascii=False,
        )

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------

    @mcp.tool()
    def find_matches(
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """Find matches by team, opponent, competition, season and/or date range.

        Dates are ISO ``YYYY-MM-DD`` strings.  Leave any filter unset to
        skip it.  Results are newest-first.
        """

        result = queries.find_matches(
            get_knowledge_graph(),
            team=team,
            opponent=opponent,
            competition=competition,
            season=season,
            start_date=_parse_optional_date(start_date),
            end_date=_parse_optional_date(end_date),
            limit=limit,
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def head_to_head(
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """Head-to-head record between two teams across all competitions."""

        result = queries.head_to_head(
            get_knowledge_graph(),
            team_a,
            team_b,
            competition=competition,
            limit=limit,
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------

    @mcp.tool()
    def team_stats(
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> str:
        """Win/loss/draw record and goal tally for a team.

        ``venue`` accepts "home", "away" or "either".
        """

        result = queries.team_stats(
            get_knowledge_graph(),
            team,
            season=season,
            competition=competition,
            venue=venue,
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def team_info(team: str) -> str:
        """Competitions, seasons, FIFA players and overall record for a team."""

        result = queries.team_info(get_knowledge_graph(), team)
        return json.dumps(result, ensure_ascii=False, default=str)

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------

    @mcp.tool()
    def search_players(
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 25,
    ) -> str:
        """Search FIFA players by name/nationality/club/position/rating.

        ``position`` is a FIFA position code (ST, LW, CDM, GK, ...).
        Results are sorted by overall rating, highest first.
        """

        result = queries.search_players(
            get_knowledge_graph(),
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            limit=limit,
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def player_info(name: str) -> str:
        """Full FIFA profile for the player(s) whose name matches *name*."""

        result = queries.player_info(get_knowledge_graph(), name)
        return json.dumps(result, ensure_ascii=False, default=str)

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------

    @mcp.tool()
    def competition_standings(competition: str, season: Optional[int] = None, top: int = 20) -> str:
        """Compute league standings from match results (3-1-0 points)."""

        result = queries.competition_standings(
            get_knowledge_graph(), competition, season=season, top=top
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def competition_info(competition: str) -> str:
        """Summary of a competition: seasons, match count, teams."""

        result = queries.competition_info(get_knowledge_graph(), competition)
        return json.dumps(result, ensure_ascii=False, default=str)

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------

    @mcp.tool()
    def average_goals(
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        """Average goals per match plus home/away win rates."""

        result = queries.average_goals(
            get_knowledge_graph(), competition=competition, season=season
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def biggest_wins(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Largest goal-margin victories across the dataset."""

        result = queries.biggest_wins(
            get_knowledge_graph(), competition=competition, season=season, limit=limit
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def home_advantage(
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        """Quantify home-field advantage (home win rate minus away win rate)."""

        result = queries.home_advantage(
            get_knowledge_graph(), competition=competition, season=season
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def best_home_record(
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Rank teams by home win rate within the given filters."""

        result = queries.best_home_record(
            get_knowledge_graph(), competition=competition, season=season, limit=limit
        )
        return json.dumps(result, ensure_ascii=False, default=str)

    return mcp


# A module-level server instance for the stdio entry point.
mcp = build_server()
