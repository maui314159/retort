"""
 brazilian_soccer_mcp / tools.py
 ===============================

 Why
 ---
 The MCP server and the tests need one authoritative catalogue of the
 server's tools: names, human descriptions, JSON-Schema input schemas and
 the dispatch from a tool call to a query result plus rendered text.
 Defining it here keeps server.py a pure protocol layer.

 What
 ---
 * :data:`TOOLS`            - tool descriptors for MCP ``tools/list``.
 * :func:`call_tool`        - dispatch (name, arguments) -> result dict
                              (``{"content", "structuredContent",
                              "isError"}``), raising :class:`ToolError`
                              for unknown tools / bad arguments.
 * :func:`tool_summaries`   - one-line help text for README/CLI.

 Tools (one per TASK.md capability):
   search_matches, last_match_between, head_to_head, team_stats,
   team_profile, standings, biggest_wins, competition_stats,
   best_records, derbies, player_search, player_club_report,
   list_competitions, list_teams

 Test: ``tests/test_server.py`` (descriptor shapes + dispatch).
=====================================================================
"""

from __future__ import annotations

from . import queries, render
from .loader import Dataset


class ToolError(Exception):
    """Raised for unknown tools or malformed arguments (protocol error)."""


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


_STR = {"type": "string"}
_INT = {"type": "integer", "minimum": 1}


TOOLS: list[dict] = [
    {
        "name": "search_matches",
        "description": (
            "Search Brazilian soccer fixtures by team (any side), opponent, "
            "competition (serie_a, serie_b, serie_c, copa_do_brasil, "
            "libertadores, or 'all'), season, stage/round (e.g. 'final', "
            "'semifinals', 'group stage', or a numeric round) and date range "
            "(ISO YYYY-MM-DD). Returns newest-first matches with date, score, "
            "competition and phase. Handles every team-name spelling used by "
            "the datasets (e.g. 'Palmeiras-SP' = 'Palmeiras')."
        ),
        "inputSchema": _schema(
            {
                "team": {"type": "string", "description": "Team name (any spelling)"},
                "opponent": {
                    "type": "string",
                    "description": "Restrict to fixtures vs this team",
                },
                "competition": {
                    "type": "string",
                    "description": "Competition id or alias",
                },
                "season": {"type": "integer", "description": "Year, e.g. 2019"},
                "stage": {
                    "type": "string",
                    "description": "'final', 'semifinals', 'group stage' or round number",
                },
                "date_from": {"type": "string", "description": "ISO date, inclusive"},
                "date_to": {"type": "string", "description": "ISO date, inclusive"},
                "limit": {
                    **_INT,
                    "maximum": 200,
                    "description": "Max matches to return (default 20)",
                },
            }
        ),
    },
    {
        "name": "last_match_between",
        "description": (
            "Most recent played fixture between two teams (date, score, "
            "competition), plus any later scheduled-but-unplayed fixture."
        ),
        "inputSchema": _schema(
            {
                "team_a": {**_STR, "description": "First team"},
                "team_b": {**_STR, "description": "Second team"},
            },
            required=["team_a", "team_b"],
        ),
    },
    {
        "name": "head_to_head",
        "description": (
            "Head-to-head record between two teams: meetings, wins/draws/losses, "
            "goals, and the fixture list (optionally scoped to a competition "
            "and season)."
        ),
        "inputSchema": _schema(
            {
                "team_a": {**_STR, "description": "First team"},
                "team_b": {**_STR, "description": "Second team"},
                "competition": _STR,
                "season": {"type": "integer"},
                "limit": _INT,
            },
            required=["team_a", "team_b"],
        ),
    },
    {
        "name": "team_stats",
        "description": (
            "Win/draw/loss record and goals for one team, scoped by season, "
            "competition and venue ('home', 'away', 'all'). Includes home/away "
            "splits and per-competition breakdowns."
        ),
        "inputSchema": _schema(
            {
                "team": {**_STR, "description": "Team name (any spelling)"},
                "season": {"type": "integer"},
                "competition": _STR,
                "venue": {"type": "string", "enum": ["home", "away", "all"]},
            },
            required=["team"],
        ),
    },
    {
        "name": "team_profile",
        "description": (
            "Everything known about one club: canonical id, state, every name "
            "spelling seen in the data, competitions and seasons played, "
            "all-time record, and FIFA-database player presence. Answers "
            "'what competitions has Palmeiras played in?'."
        ),
        "inputSchema": _schema(
            {
                "team": {**_STR, "description": "Team name (any spelling)"},
            },
            required=["team"],
        ),
    },
    {
        "name": "standings",
        "description": (
            "League table computed from match results (3 pts/win, CBF "
            "tie-breaks) with champion and relegated (bottom four) teams. "
            "League competitions only - cups have no table."
        ),
        "inputSchema": _schema(
            {
                "competition": {
                    **_STR,
                    "description": "serie_a, serie_b or serie_c (or alias)",
                },
                "season": {"type": "integer", "description": "Year, e.g. 2019"},
            },
            required=["competition", "season"],
        ),
    },
    {
        "name": "biggest_wins",
        "description": (
            "Largest victory margins in the dataset (all competitions or one, "
            "optionally one season), ranked by goal margin then total goals."
        ),
        "inputSchema": _schema(
            {
                "competition": _STR,
                "season": {"type": "integer"},
                "limit": _INT,
            }
        ),
    },
    {
        "name": "competition_stats",
        "description": (
            "Aggregate statistics: matches, average goals per match, home/draw/"
            "away win rates - for one competition (+season) or overall with a "
            "per-competition breakdown."
        ),
        "inputSchema": _schema(
            {
                "competition": _STR,
                "season": {"type": "integer"},
            }
        ),
    },
    {
        "name": "best_records",
        "description": (
            "Rank teams by performance for a venue: win_rate, points_per_game, "
            "goals_for, goals_against or avg_goals_for (home/away/all). "
            "Answers 'which team has the best away record?'."
        ),
        "inputSchema": _schema(
            {
                "venue": {"type": "string", "enum": ["home", "away", "all"]},
                "competition": _STR,
                "season": {"type": "integer"},
                "metric": {
                    "type": "string",
                    "enum": [
                        "win_rate",
                        "points_per_game",
                        "goals_for",
                        "goals_against",
                        "avg_goals_for",
                    ],
                },
                "min_matches": {"type": "integer", "minimum": 1},
                "limit": _INT,
            }
        ),
    },
    {
        "name": "derbies",
        "description": (
            "Classic Brazilian derbies (Fla-Flu, Gre-Nal, Derby Paulista, "
            "Ba-Vi, ...) with all-time head-to-head records and fixtures, "
            "optionally for one season. Answers 'show me all derbies in 2023'."
        ),
        "inputSchema": _schema(
            {
                "season": {"type": "integer"},
                "limit_per_derby": _INT,
            }
        ),
    },
    {
        "name": "player_search",
        "description": (
            "Search the FIFA player database (18,207 players): name substring, "
            "nationality (e.g. Brazil), club, position (code like ST/LW/GK or "
            "group DEF/MID/FWD), minimum overall rating, maximum age. Ordered "
            "by overall/potential/age/name/value."
        ),
        "inputSchema": _schema(
            {
                "name": _STR,
                "nationality": _STR,
                "club": _STR,
                "position": _STR,
                "min_overall": {"type": "integer", "minimum": 0, "maximum": 99},
                "max_age": {"type": "integer", "minimum": 15, "maximum": 60},
                "order": {
                    "type": "string",
                    "enum": ["overall", "potential", "age", "name", "value"],
                },
                "limit": _INT,
            }
        ),
    },
    {
        "name": "player_club_report",
        "description": (
            "Players grouped by club: counts, average and best ratings, "
            "flagging clubs the match data knows as Brazilian. Answers "
            "'Brazilian players at Brazilian clubs'."
        ),
        "inputSchema": _schema(
            {
                "nationality": _STR,
                "min_overall": {"type": "integer", "minimum": 0, "maximum": 99},
            }
        ),
    },
    {
        "name": "list_competitions",
        "description": "List every competition with seasons covered and match counts.",
        "inputSchema": _schema({}),
    },
    {
        "name": "list_teams",
        "description": (
            "Team directory: all clubs, or participants of one competition "
            "and season, with match counts and canonical ids."
        ),
        "inputSchema": _schema(
            {
                "competition": _STR,
                "season": {"type": "integer"},
                "limit": _INT,
            }
        ),
    },
]

TOOL_NAMES = {tool["name"] for tool in TOOLS}

_RENDERERS = {
    "search_matches": render.render_search_matches,
    "last_match_between": render.render_last_match,
    "head_to_head": render.render_head_to_head,
    "team_stats": render.render_team_stats,
    "team_profile": render.render_team_profile,
    "standings": render.render_standings,
    "biggest_wins": render.render_biggest_wins,
    "competition_stats": render.render_competition_stats,
    "best_records": render.render_best_records,
    "derbies": render.render_derbies,
    "player_search": render.render_player_search,
    "player_club_report": render.render_player_club_report,
    "list_competitions": render.render_list_competitions,
    "list_teams": render.render_list_teams,
}

_DISPATCH = {
    "search_matches": queries.search_matches,
    "last_match_between": queries.last_match_between,
    "head_to_head": queries.head_to_head,
    "team_stats": queries.team_stats,
    "team_profile": queries.team_profile,
    "standings": queries.standings,
    "biggest_wins": queries.biggest_wins,
    "competition_stats": queries.competition_stats,
    "best_records": queries.best_records,
    "derbies": queries.derbies,
    "player_search": queries.player_search,
    "player_club_report": queries.player_club_report,
    "list_competitions": queries.list_competitions,
    "list_teams": queries.list_teams,
}


def tool_summaries() -> str:
    """One line per tool (for README and CLI help)."""
    return "\n".join(
        f"- {t['name']}: {t['description'].splitlines()[0]}" for t in TOOLS
    )


def call_tool(ds: Dataset, name: str, arguments: dict | None) -> dict:
    """
    Execute a tool call.  Returns an MCP tool result:
    ``{"content": [{"type": "text", "text": ...}], "structuredContent": ...}``
    plus ``"isError": True`` when the query itself failed (unknown team,
    bad competition, ...).  Unknown tool names or arguments raise
    :class:`ToolError` (a protocol-level error, per the MCP spec).
    """
    if name not in TOOL_NAMES:
        raise ToolError(
            f"Unknown tool: {name}. Available tools: {', '.join(sorted(TOOL_NAMES))}"
        )
    query = _DISPATCH[name]
    arguments = dict(arguments or {})
    try:
        result = query(ds, **arguments)
    except TypeError as exc:
        # Bad keyword argument for this tool's signature.
        message = str(exc)
        if "keyword argument" in message or "positional argument" in message:
            raise ToolError(f"Invalid arguments for tool '{name}': {message}") from exc
        raise
    if not isinstance(result, dict) or "ok" not in result:
        raise ToolError(f"Tool '{name}' returned an unexpected result")
    text = _RENDERERS[name](result)
    payload = {"content": [{"type": "text", "text": text}], "structuredContent": result}
    if not result.get("ok"):
        payload["isError"] = True
    return payload
