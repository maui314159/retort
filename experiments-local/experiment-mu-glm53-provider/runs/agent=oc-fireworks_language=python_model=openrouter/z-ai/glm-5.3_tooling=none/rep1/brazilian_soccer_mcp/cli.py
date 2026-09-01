"""
 brazilian_soccer_mcp / cli.py
 ==============================

 Why
 ---
 The MCP server is the primary interface, but a direct command line makes
 the same knowledge graph usable from a shell (smoke tests, demos, data
 exploration) without an LLM in the loop.

 What
 ---
 ``python -m brazilian_soccer_mcp.cli <command> [options]`` - one
 subcommand per MCP tool, same parameters, same rendered output.  Run
 with ``--data-dir`` to point at another copy of data/kaggle.  ``serve``
 and ``tools`` subcommands expose the server itself and the tool
 catalogue.  Exit code 0 on success (including empty-but-valid query
 results), 1 on query errors, 2 on usage errors (argparse).

 Test: ``tests/test_server.py`` spawns the MCP server; the CLI is
 exercised by the sample-question scenarios through the query layer it
 wraps.
=============================================================
"""

from __future__ import annotations

import argparse

from . import queries, render, tools
from .loader import load_dataset


def _add_query_arguments(
    parser: argparse.ArgumentParser, arguments: list[tuple[str, dict]]
) -> None:
    for name, kwargs in arguments:
        parser.add_argument(name, **kwargs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brazilian-soccer-mcp-cli",
        description="Query the Brazilian soccer knowledge graph directly.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Path to the directory containing the Kaggle CSVs.",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    def cmd(name: str, arguments: list[tuple[str, dict]]):
        subparser = sub.add_parser(name)
        _add_query_arguments(subparser, arguments)
        return subparser

    cmd(
        "search-matches",
        [
            ("--team", {"help": "Team name (any spelling)"}),
            ("--opponent", {"help": "Only matches vs this team"}),
            (
                "--competition",
                {
                    "help": "serie_a, serie_b, serie_c, copa_do_brasil, libertadores or all"
                },
            ),
            ("--season", {"type": int, "help": "Year, e.g. 2019"}),
            ("--stage", {"help": "final, semifinals, group stage or a round number"}),
            (
                "--from",
                {"dest": "date_from", "metavar": "DATE", "help": "ISO date, inclusive"},
            ),
            (
                "--to",
                {"dest": "date_to", "metavar": "DATE", "help": "ISO date, inclusive"},
            ),
            ("--limit", {"type": int, "default": 20}),
        ],
    )
    cmd(
        "last-match",
        [
            ("team_a", {"help": "First team"}),
            ("team_b", {"help": "Second team"}),
        ],
    )
    cmd(
        "h2h",
        [
            ("team_a", {"help": "First team"}),
            ("team_b", {"help": "Second team"}),
            ("--competition", {}),
            ("--season", {"type": int}),
            ("--limit", {"type": int, "default": 20}),
        ],
    )
    cmd(
        "team-stats",
        [
            ("team", {"help": "Team name"}),
            ("--season", {"type": int}),
            ("--competition", {}),
            ("--venue", {"choices": ["home", "away", "all"], "default": "all"}),
        ],
    )
    cmd("team-info", [("team", {"help": "Team name"})])
    cmd(
        "standings",
        [
            ("competition", {"help": "serie_a, serie_b or serie_c"}),
            ("season", {"type": int, "help": "Year"}),
        ],
    )
    cmd(
        "biggest-wins",
        [
            ("--competition", {}),
            ("--season", {"type": int}),
            ("--limit", {"type": int, "default": 10}),
        ],
    )
    cmd(
        "stats",
        [
            ("--competition", {}),
            ("--season", {"type": int}),
        ],
    )
    cmd(
        "best-records",
        [
            ("--venue", {"choices": ["home", "away", "all"], "default": "home"}),
            ("--competition", {}),
            ("--season", {"type": int}),
            (
                "--metric",
                {
                    "default": "win_rate",
                    "choices": [
                        "win_rate",
                        "points_per_game",
                        "goals_for",
                        "goals_against",
                        "avg_goals_for",
                    ],
                },
            ),
            ("--min-matches", {"type": int, "default": 10}),
            ("--limit", {"type": int, "default": 10}),
        ],
    )
    cmd(
        "derbies",
        [
            ("--season", {"type": int}),
            ("--limit-per-derby", {"type": int, "default": 5}),
        ],
    )
    cmd(
        "players",
        [
            ("--name", {}),
            ("--nationality", {}),
            ("--club", {}),
            ("--position", {}),
            ("--min-overall", {"type": int}),
            ("--max-age", {"type": int}),
            (
                "--order",
                {
                    "default": "overall",
                    "choices": ["overall", "potential", "age", "name", "value"],
                },
            ),
            ("--limit", {"type": int, "default": 20}),
        ],
    )
    cmd(
        "player-clubs",
        [
            ("--nationality", {}),
            ("--min-overall", {"type": int}),
        ],
    )
    cmd("competitions", [])
    cmd(
        "teams",
        [
            ("--competition", {}),
            ("--season", {"type": int}),
            ("--limit", {"type": int, "default": 100}),
        ],
    )
    sub.add_parser(
        "serve",
        help="Run the MCP stdio server (same as python -m brazilian_soccer_mcp).",
    )
    sub.add_parser("tools", help="List the MCP tools this package exposes.")
    return parser


_DISPATCH = {
    "search-matches": (queries.search_matches, render.render_search_matches),
    "last-match": (queries.last_match_between, render.render_last_match),
    "h2h": (queries.head_to_head, render.render_head_to_head),
    "team-stats": (queries.team_stats, render.render_team_stats),
    "team-info": (queries.team_profile, render.render_team_profile),
    "standings": (queries.standings, render.render_standings),
    "biggest-wins": (queries.biggest_wins, render.render_biggest_wins),
    "stats": (queries.competition_stats, render.render_competition_stats),
    "best-records": (queries.best_records, render.render_best_records),
    "derbies": (queries.derbies, render.render_derbies),
    "players": (queries.player_search, render.render_player_search),
    "player-clubs": (queries.player_club_report, render.render_player_club_report),
    "competitions": (queries.list_competitions, render.render_list_competitions),
    "teams": (queries.list_teams, render.render_list_teams),
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        from .server import serve as run_stdio_server

        run_stdio_server()
        return 0
    if args.command == "tools":
        print(tools.tool_summaries())
        return 0
    if not args.command:
        parser.print_help()
        return 2

    query, renderer = _DISPATCH[args.command]
    params = {
        k: v
        for k, v in vars(args).items()
        if k not in ("command", "data_dir") and v is not None
    }
    dataset = load_dataset(args.data_dir)
    result = query(dataset, **params)
    print(renderer(result))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
