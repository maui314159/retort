"""MCP tool registry: JSON schemas and dispatch for the query layer.

Context: this module is the bridge between the MCP protocol layer
(protocol.py) and the query functions (queries.py). Each tool is declared
with a JSON Schema for its arguments plus a handler function that receives
the parsed arguments and returns a JSON-serialisable dict. Handlers may
raise QueryError, which the protocol layer converts into an isError tool
result so the connected LLM can retry with corrected arguments.
"""

from __future__ import annotations

from . import queries
from .repository import DataRepository

_MATCHES_DESCRIPTION = """Search matches across all curated datasets.

Filter by team (either side, or force home/away with home_team/away_team),
opponent, competition (Brasileirão Serie A/B/C, Copa do Brasil, Copa
Libertadores), season, date range, Libertadores stage (e.g. "final",
"quarterfinals") or Copa do Brasil round. Set source to a CSV filename to
search the raw per-file data instead of the curated view. Examples:
"Flamengo vs Fluminense matches", "all Palmeiras matches in 2023",
"Copa do Brasil matches in May 2019"."""


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}


def _limit_schema(default: int, maximum: int) -> dict:
    return {"type": "integer", "default": default, "minimum": 1, "maximum": maximum}


def build_tool_registry(repo: DataRepository) -> list[dict]:
    """Return the list of MCP tool descriptors bound to a repository."""

    def tool(name: str, description: str, schema: dict, handler) -> dict:
        return {
            "name": name,
            "description": description,
            "inputSchema": schema,
            "handler": handler,
        }

    return [
        tool(
            "search_matches",
            _MATCHES_DESCRIPTION,
            _schema(
                {
                    "team": _STR,
                    "opponent": _STR,
                    "home_team": _STR,
                    "away_team": _STR,
                    "competition": _STR,
                    "season": _INT,
                    "date_from": {"type": "string", "format": "date"},
                    "date_to": {"type": "string", "format": "date"},
                    "stage": _STR,
                    "round": _INT,
                    "venue": {"type": "string", "enum": ["home", "away"]},
                    "source": _STR,
                    "limit": _limit_schema(25, 200),
                    "sort": {"type": "string", "enum": ["date_desc", "date_asc"]},
                }
            ),
            lambda args: queries.search_matches(repo, **args),
        ),
        tool(
            "head_to_head",
            "Head-to-head record between two teams: wins, draws, goals and the "
            "match list. Use team spellings like 'Flamengo', 'Palmeiras-SP' or "
            "'America-MG'. Example: compare Palmeiras and Santos.",
            _schema(
                {
                    "team_a": _STR,
                    "team_b": _STR,
                    "competition": _STR,
                    "season": _INT,
                    "limit": _limit_schema(25, 200),
                },
                ["team_a", "team_b"],
            ),
            lambda args: queries.head_to_head(repo, **args),
        ),
        tool(
            "team_stats",
            "Win/draw/loss record, goals scored and conceded, home/away splits and "
            "per-competition breakdowns for one team. Examples: Corinthians home "
            "record in 2022 (team='Corinthians', season=2022, venue handled by the "
            "home section), Palmeiras record in the 2019 Brasileirão.",
            _schema(
                {
                    "team": _STR,
                    "season": _INT,
                    "competition": _STR,
                    "limit_recent": {"type": "integer", "default": 5, "minimum": 0},
                },
                ["team"],
            ),
            lambda args: queries.team_stats(repo, **args),
        ),
        tool(
            "team_rankings",
            "Rank all teams by an aggregate metric over the (optionally filtered) "
            "match set: points, wins, away_wins, away_points, goals_for, win_rate, "
            "home_win_rate, away_win_rate, etc. Example: best away record in the "
            "Brasileirão (metric='away_points').",
            _schema(
                {
                    "competition": _STR,
                    "season": _INT,
                    "metric": {
                        "type": "string",
                        "default": "points",
                        "enum": [
                            "points", "wins", "draws", "losses", "matches",
                            "goals_for", "goals_against", "goal_diff", "win_rate",
                            "home_wins", "home_points", "home_win_rate",
                            "away_wins", "away_points", "away_win_rate",
                        ],
                    },
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
                }
            ),
            lambda args: queries.team_rankings(repo, **args),
        ),
        tool(
            "find_team",
            "Resolve any team spelling ('Palmeiras-SP', 'Grêmio', 'Atlético "
            "Paranaense', 'Fla') to the club entities in the datasets, with match "
            "and player counts. Use it to disambiguate names like 'America' "
            "(America-MG vs America-RN) or 'Atletico' (MG, GO, PR).",
            _schema({"query": _STR}, ["query"]),
            lambda args: queries.find_team(repo, **args),
        ),
        tool(
            "search_players",
            "Search the FIFA player database by name, nationality ('Brazil'), "
            "club, position (FIFA code like 'ST' or group like 'forward', "
            "'goalkeeper'), minimum overall rating or maximum age. Examples: all "
            "Brazilian players, highest-rated players at Grêmio, forwards from "
            "Santos.",
            _schema(
                {
                    "name": _STR,
                    "nationality": _STR,
                    "club": _STR,
                    "position": _STR,
                    "min_overall": _INT,
                    "max_age": _INT,
                    "sort": {"type": "string", "enum": ["overall", "potential", "age", "name"]},
                    "limit": _limit_schema(25, 200),
                }
            ),
            lambda args: queries.search_players(repo, **args),
        ),
        tool(
            "player_detail",
            "Full FIFA profile (ratings, skills, contract, physical attributes) "
            "for one player by name or FIFA id. Example: 'Gabriel Barbosa'.",
            _schema({"name": _STR, "id": _INT}),
            lambda args: queries.player_detail(repo, player_id=args.pop("id", None), **args),
        ),
        tool(
            "standings",
            "League table calculated from match results for one competition "
            "season, with champion and (for Serie A) the relegation zone. "
            "Examples: 2019 Brasileirão (competition='Brasileirão Serie A', "
            "season=2019), who was relegated in 2020.",
            _schema({"competition": _STR, "season": _INT}, ["competition", "season"]),
            lambda args: queries.standings(repo, **args),
        ),
        tool(
            "competition_info",
            "Describe the competitions in the datasets: seasons covered, match "
            "counts, source files. Call without arguments to list everything.",
            _schema({"competition": _STR}),
            lambda args: queries.competition_info(repo, **args) if args else queries.competition_info(repo),
        ),
        tool(
            "biggest_wins",
            "Largest victory margins in the dataset, optionally filtered by "
            "competition and season.",
            _schema(
                {
                    "competition": _STR,
                    "season": _INT,
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
                }
            ),
            lambda args: queries.biggest_wins(repo, **args),
        ),
        tool(
            "stats_summary",
            "Aggregate statistics: average goals per match, home/away win rates, "
            "draws, biggest win. Filter by competition and season to compare "
            "e.g. the 2018 and 2019 Brasileirão seasons.",
            _schema({"competition": _STR, "season": _INT}),
            lambda args: queries.stats_summary(repo, **args),
        ),
        tool(
            "derby_matches",
            "Matches between traditional rivals (Fla-Flu, Grenal, Majestoso, "
            "Choque-Rei, Derby Paulista, Ba-Vi, Atletiba...). Example: all "
            "derbies in 2023.",
            _schema(
                {
                    "season": _INT,
                    "competition": _STR,
                    "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 200},
                }
            ),
            lambda args: queries.derby_matches(repo, **args),
        ),
    ]


def call_tool(tools: list[dict], name: str, arguments: dict) -> dict:
    """Dispatch a tools/call request; raises KeyError for unknown tools."""
    for entry in tools:
        if entry["name"] == name:
            return entry["handler"](arguments or {})
    raise KeyError(name)
