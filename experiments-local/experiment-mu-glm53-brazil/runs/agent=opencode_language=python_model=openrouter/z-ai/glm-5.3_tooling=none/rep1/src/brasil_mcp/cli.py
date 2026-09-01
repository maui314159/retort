"""Command line interface for the Brazilian soccer knowledge base.

Examples::

    brasil-soccer matches --team Flamengo --opponent Fluminense
    brasil-soccer standings --season 2019
    brasil-soccer stats --team Palmeiras --season 2023
    brasil-soccer players --nationality Brazil --min-overall 85
    brasil-soccer derbies --season 2023
    brasil-soccer serve
"""

from __future__ import annotations

import argparse
import json
import sys

from . import queries
from .store import SERIE_A


def _print(result: dict) -> None:
    print(result.get("summary", json.dumps(result, default=str, ensure_ascii=False)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brasil-soccer",
        description="Query the Brazilian soccer knowledge base (Kaggle datasets).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("find-team", help="Resolve a team name in any spelling")
    p.add_argument("name")

    p = subparsers.add_parser("matches", help="Search matches")
    p.add_argument("--team")
    p.add_argument("--opponent")
    p.add_argument("--competition")
    p.add_argument("--season", type=int)
    p.add_argument("--from", dest="date_from")
    p.add_argument("--to", dest="date_to")
    p.add_argument("--stage", help="e.g. final, round 22")
    p.add_argument("--venue", choices=["any", "home", "away"], default="any")
    p.add_argument("--limit", type=int, default=20)

    p = subparsers.add_parser("h2h", help="Head-to-head between two teams")
    p.add_argument("team_a")
    p.add_argument("team_b")
    p.add_argument("--competition")
    p.add_argument("--limit", type=int, default=20)

    p = subparsers.add_parser("stats", help="Team statistics")
    p.add_argument("team")
    p.add_argument("--season", type=int)
    p.add_argument("--competition")

    p = subparsers.add_parser("history", help="Season-by-season record of a team")
    p.add_argument("team")
    p.add_argument("--competition")
    p.add_argument("--limit", type=int, default=25)

    p = subparsers.add_parser("standings", help="League table for a season")
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--competition", default=SERIE_A)

    p = subparsers.add_parser("players", help="Search FIFA players")
    p.add_argument("--name")
    p.add_argument("--nationality")
    p.add_argument("--club")
    p.add_argument("--position")
    p.add_argument("--min-overall", type=int)
    p.add_argument("--max-overall", type=int)
    p.add_argument("--max-age", type=int)
    p.add_argument("--order-by", default="overall")
    p.add_argument("--limit", type=int, default=20)

    p = subparsers.add_parser("squad", help="FIFA squad of a team")
    p.add_argument("team")
    p.add_argument("--position")
    p.add_argument("--limit", type=int, default=25)

    p = subparsers.add_parser("competitions", help="Dataset coverage per competition")
    p.add_argument("--competition")
    p.add_argument("--season", type=int)

    p = subparsers.add_parser("derbies", help="Traditional derby matches")
    p.add_argument("--season", type=int)
    p.add_argument("--competition")
    p.add_argument("--limit", type=int, default=15)

    p = subparsers.add_parser("biggest-wins", help="Largest victories")
    p.add_argument("--competition")
    p.add_argument("--season", type=int)
    p.add_argument("--limit", type=int, default=10)

    p = subparsers.add_parser("goals", help="Goals and home/away analysis")
    p.add_argument("--competition")
    p.add_argument("--season", type=int)

    p = subparsers.add_parser("best-records", help="Teams ranked by points per game")
    p.add_argument("--competition")
    p.add_argument("--season", type=int)
    p.add_argument("--venue", choices=["overall", "home", "away"], default="overall")
    p.add_argument("--min-matches", type=int, default=10)
    p.add_argument("--limit", type=int, default=10)

    p = subparsers.add_parser("compare", help="Compare two teams")
    p.add_argument("team_a")
    p.add_argument("team_b")
    p.add_argument("--season", type=int)

    subparsers.add_parser("serve", help="Run the MCP server on stdio")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "find-team":
        _print(queries.find_team(args.name))
    elif args.command == "matches":
        _print(
            queries.search_matches(
                team=args.team,
                opponent=args.opponent,
                competition=args.competition,
                season=args.season,
                date_from=args.date_from,
                date_to=args.date_to,
                stage=args.stage,
                venue=args.venue,
                limit=args.limit,
            )
        )
    elif args.command == "h2h":
        _print(queries.head_to_head(args.team_a, args.team_b, competition=args.competition, limit=args.limit))
    elif args.command == "stats":
        _print(queries.team_stats(args.team, season=args.season, competition=args.competition))
    elif args.command == "history":
        _print(queries.team_season_history(args.team, competition=args.competition, limit=args.limit))
    elif args.command == "standings":
        _print(queries.standings(args.season, competition=args.competition))
    elif args.command == "players":
        _print(
            queries.search_players(
                name=args.name,
                nationality=args.nationality,
                club=args.club,
                position=args.position,
                min_overall=args.min_overall,
                max_overall=args.max_overall,
                max_age=args.max_age,
                order_by=args.order_by,
                limit=args.limit,
            )
        )
    elif args.command == "squad":
        _print(queries.team_players(args.team, position=args.position, limit=args.limit))
    elif args.command == "competitions":
        _print(queries.competition_info(args.competition, args.season))
    elif args.command == "derbies":
        _print(queries.derbies(season=args.season, competition=args.competition, limit=args.limit))
    elif args.command == "biggest-wins":
        _print(queries.biggest_wins(competition=args.competition, season=args.season, limit=args.limit))
    elif args.command == "goals":
        _print(queries.goals_analysis(competition=args.competition, season=args.season))
    elif args.command == "best-records":
        _print(
            queries.best_records(
                competition=args.competition,
                season=args.season,
                venue=args.venue,
                min_matches=args.min_matches,
                limit=args.limit,
            )
        )
    elif args.command == "compare":
        _print(queries.compare_teams(args.team_a, args.team_b, season=args.season))
    elif args.command == "serve":
        from .server import main as serve_main

        serve_main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
