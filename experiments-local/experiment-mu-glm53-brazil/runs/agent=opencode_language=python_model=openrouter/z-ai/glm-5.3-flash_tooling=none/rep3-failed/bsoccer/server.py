"""MCP server exposing the Brazilian soccer knowledge graph.

Run with:

    python server.py            # stdio transport (default)
    python server.py --http     # streamable-http transport on port 8000

The server answers natural-language questions about Brazilian soccer using
the six Kaggle datasets described in TASK.md. All tool parameters are plain
strings/ints so any MCP client can call them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .queries import KnowledgeBase

_knowledge_base: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base


server = MCPServer(
    name="brazilian-soccer",
    title="Brazilian Soccer Knowledge Graph",
    description=(
        "Answers natural-language questions about Brazilian soccer: matches, teams, "
        "players, standings and statistics, built from six Kaggle datasets "
        "(Brasileirão, Copa do Brasil, Copa Libertadores, BR-Football extended stats "
        "and the FIFA player database)."
    ),
    instructions=(
        "Use search_matches for match history questions, head_to_head for rivalries, "
        "team_statistics for team records, standings for season tables, "
        "search_players / player_profile for FIFA player data, team_overview for a "
        "cross-dataset team summary, competition_statistics / compare_seasons for "
        "aggregates, biggest_wins for notable results and list_teams to discover teams. "
        "Team names tolerate state suffixes ('Flamengo-RJ'), missing accents ('Sao Paulo') "
        "and partial spellings. Seasons are calendar years. Player data is the FIFA 19 "
        "(2018 season) dataset."
    ),
    version="1.0.0",
)


def _fmt_match(m: dict) -> str:
    parts = [m["date"] or "date unknown"]
    if m.get("time"):
        parts.append(m["time"])
    score = f"{m['home_team']} {m['home_goal']}-{m['away_goal']} {m['away_team']}"
    context = m["competition"]
    if m.get("season"):
        context += f" {m['season']}"
    if m.get("round"):
        context += f" Round {m['round']}"
    if m.get("stage"):
        context += f" ({m['stage']})"
    return f"- {parts[0]}: {score} ({context})"


def _fmt_matches(matches: list[dict], more: int = 0) -> str:
    lines = [_fmt_match(m) for m in matches]
    if more > 0:
        lines.append(f"- ... and {more} more matches in the dataset")
    return "\n".join(lines) if lines else "- (no matches found)"


def _fmt_stat_line(stat: dict) -> str:
    return (
        f"Matches: {stat['played']}, Wins: {stat['wins']}, Draws: {stat['draws']}, "
        f"Losses: {stat['losses']}, Goals For: {stat['goals_for']}, "
        f"Goals Against: {stat['goals_against']}, Win rate: {stat['win_rate']}%"
    )


def _error(obj: dict) -> str | None:
    if "error" not in obj:
        return None
    lines = [f"Error: {obj['error']}"]
    if obj.get("candidates"):
        lines.append("Did you mean: " + ", ".join(obj["candidates"]) + "?")
    if obj.get("hint"):
        lines.append(obj["hint"])
    if obj.get("known"):
        lines.append("Known competitions: " + ", ".join(obj["known"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@server.tool()
def search_matches(
    team: str = "",
    opponent: str = "",
    competition: str = "",
    season: int | None = None,
    date_from: str = "",
    date_to: str = "",
    stage: str = "",
    round: str = "",
    limit: int = 25,
) -> str:
    """Search match history by team, opponent, competition, season, date range, stage or round.

    Args:
        team: Team name (home or away), e.g. 'Flamengo', 'Palmeiras-SP', 'Sao Paulo'.
        opponent: Restrict to matches against this team (e.g. 'Fluminense').
        competition: 'Brasileirão' / 'Serie A', 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C'.
        season: Calendar year, e.g. 2023.
        date_from: Start of date range, 'YYYY-MM-DD'.
        date_to: End of date range, 'YYYY-MM-DD'.
        stage: Tournament stage, e.g. 'final', 'group stage', 'quarterfinals'.
        round: Round number, e.g. '22'.
        limit: Max matches to return (default 25).
    """
    kb = get_kb()
    result = kb.search_matches(
        team=team or None,
        opponent=opponent or None,
        competition=competition or None,
        season=season,
        date_from=date_from or None,
        date_to=date_to or None,
        stage=stage or None,
        round=round or None,
        limit=limit,
    )
    err = _error(result)
    if err:
        return err
    lines: list[str] = []
    if result.get("team") and result.get("opponent"):
        h2h = result.get("head_to_head") or {}
        lines.append(
            f"Head-to-head in dataset: {h2h.get('team_a')} {h2h.get('team_a_wins')} wins, "
            f"{h2h.get('team_b')} {h2h.get('team_b_wins')} wins, {h2h.get('draws')} draws"
        )
    lines.append(f"Matches found: {result['count']} of {result['total_matches']}")
    lines.append(_fmt_matches(result["matches"], more=max(0, result["total_matches"] - result["count"])))
    return "\n".join(lines)


@server.tool()
def head_to_head(team_a: str, team_b: str, competition: str = "", season: int | None = None, limit: int = 25) -> str:
    """Compare two teams: overall head-to-head record plus the match list.

    Args:
        team_a: First team name, e.g. 'Palmeiras'.
        team_b: Second team name, e.g. 'Santos'.
        competition: Optional competition filter ('Brasileirão', 'Copa do Brasil', 'Libertadores').
        season: Optional season (year) filter.
        limit: Max matches to list (default 25).
    """
    kb = get_kb()
    result = kb.head_to_head(team_a, team_b, competition=competition or None, season=season, limit=limit)
    err = _error(result)
    if err:
        return err
    summary = result["summary"]
    lines = [
        f"{summary['team_a']} vs {summary['team_b']} — head-to-head in dataset:",
        f"- {summary['team_a']} wins: {summary['team_a_wins']}",
        f"- {summary['team_b']} wins: {summary['team_b_wins']}",
        f"- Draws: {summary['draws']}",
        f"- Goals: {summary['team_a']} {summary['goals_team_a']} x {summary['goals_team_b']} {summary['team_b']}",
        "",
        f"Matches found: {result['count']} of {result['total_matches']}",
        _fmt_matches(result["matches"], more=max(0, result["total_matches"] - result["count"])),
    ]
    return "\n".join(lines)


@server.tool()
def team_statistics(team: str, season: int | None = None, competition: str = "") -> str:
    """Win/loss/draw record, goals and home/away splits for one team.

    Args:
        team: Team name, e.g. 'Corinthians', 'Corinthians-SP'.
        season: Optional season (year), e.g. 2022.
        competition: Optional competition filter ('Brasileirão', 'Copa do Brasil', 'Libertadores').
    """
    kb = get_kb()
    result = kb.team_statistics(team, season=season, competition=competition or None)
    err = _error(result)
    if err:
        return err
    label = result["team"]
    filters = result["filters"]
    scope = label
    if filters.get("season"):
        scope += f" ({filters['season']}"
        if filters.get("competition"):
            scope += f", {filters['competition']}"
        scope += ")"
    lines = [f"{scope} record:"]
    overall = result["overall"]
    if overall["played"] == 0:
        lines.append("- No matches found for the given filters.")
        if result.get("seasons_covered"):
            lines.append(f"Seasons with data: {', '.join(map(str, result['seasons_covered'][:20]))}")
        return "\n".join(lines)
    lines.append(f"- {_fmt_stat_line(overall)}")
    lines.append(f"- Home: {_fmt_stat_line(result['home'])}")
    lines.append(f"- Away: {_fmt_stat_line(result['away'])}")
    for comp, stat in result["by_competition"].items():
        lines.append(f"- {comp}: {_fmt_stat_line(stat)}")
    return "\n".join(lines)


@server.tool()
def standings(competition: str, season: int) -> str:
    """League table for a competition and season, calculated from match results.

    Args:
        competition: 'Brasileirão' / 'Serie A', 'Serie B' or 'Serie C'.
        season: Season year, e.g. 2019.
    """
    kb = get_kb()
    result = kb.standings(competition, season)
    err = _error(result)
    if err:
        return err
    lines = [
        f"{result['competition']} {season} standings (calculated from {result['source_file']}):",
    ]
    for row in result["standings"]:
        note = f" — {row['note']}" if row.get("note") else ""
        lines.append(
            f"{row['position']}. {row['team']} — {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L, "
            f"GF {row['goals_for']}, GA {row['goals_against']}){note}"
        )
    lines.append(result["note"])
    return "\n".join(lines)


@server.tool()
def search_players(
    name: str = "",
    nationality: str = "",
    club: str = "",
    position: str = "",
    min_overall: int | None = None,
    max_age: int | None = None,
    sort_by: str = "overall",
    limit: int = 25,
) -> str:
    """Search the FIFA player database by name, nationality, club, position or rating.

    Args:
        name: Full or partial player name, e.g. 'Neymar'.
        nationality: Country, e.g. 'Brazil'.
        club: Club name, e.g. 'Flamengo', 'Santos', 'Grêmio'.
        position: Position code, e.g. 'GK', 'ST', 'LW', 'CDM'.
        min_overall: Minimum FIFA overall rating.
        max_age: Maximum player age.
        sort_by: 'overall', 'potential', 'age' or 'name'.
        limit: Max players to return (default 25).
    """
    kb = get_kb()
    result = kb.search_players(
        name=name or None,
        nationality=nationality or None,
        club=club or None,
        position=position or None,
        min_overall=min_overall,
        max_age=max_age,
        sort_by=sort_by,
        limit=limit,
    )
    if result["count"] == 0:
        return ("No players found for the given filters. "
                "Note: the player dataset is FIFA 19 (2018 season), so only clubs licensed in that game are present.")
    lines = [f"Players found: {result['count']} (showing {result['returned']})"]
    for p in result["players"]:
        lines.append(
            f"- {p['name']} — Overall: {p['overall']}, Position: {p['position']}, "
            f"Club: {p['club'] or 'free agent'}, Age: {p['age']}, Nationality: {p['nationality']}"
        )
    if result.get("club_summary"):
        cs = result["club_summary"]
        lines.append("")
        lines.append(
            f"Club summary for {cs['club']}: {cs['player_count']} players "
            f"(avg rating: {cs['average_overall']})"
        )
    return "\n".join(lines)


@server.tool()
def player_profile(name: str) -> str:
    """Full profile (attributes and skill ratings) for one player by name.

    Args:
        name: Player name, e.g. 'Gabriel Barbosa' or 'Alisson'.
    """
    kb = get_kb()
    result = kb.player_profile(name)
    err = _error(result)
    if err:
        return err
    p = result["player"]
    lines = [
        f"{p['name']} — FIFA overall {p['overall']} (potential {p['potential']})",
        f"- Club: {p['club'] or 'free agent'} | Position: {p['position']} | Jersey: {p['jersey_number']}",
        f"- Nationality: {p['nationality']} | Age: {p['age']} | Preferred foot: {p['preferred_foot']}",
        f"- Height: {p['height']} | Weight: {p['weight']} | Value: {p['value']} | Wage: {p['wage']}",
        f"- Work rate: {p['work_rate']}",
    ]
    top_skills = sorted(p["skills"].items(), key=lambda kv: -(kv[1] or 0))[:8]
    lines.append("- Top skills: " + ", ".join(f"{k} {v}" for k, v in top_skills))
    if result.get("other_matches"):
        lines.append("- Similar names: " + ", ".join(x["name"] for x in result["other_matches"]))
    return "\n".join(lines)


@server.tool()
def team_overview(team: str) -> str:
    """Cross-dataset overview of one team: match history, main rivals and FIFA roster.

    Args:
        team: Team name, e.g. 'Flamengo', 'Palmeiras-SP'.
    """
    kb = get_kb()
    result = kb.team_overview(team)
    err = _error(result)
    if err:
        return err
    lines = [f"{result['team']} — overview across all datasets:"]
    lines.append(f"- Total matches: {result['total_matches']}")
    for comp, n in result["matches_by_competition"].items():
        lines.append(f"  - {comp}: {n} matches")
    if result["seasons"]:
        seasons = result["seasons"]
        lines.append(f"- Seasons covered: {seasons[0]}–{seasons[-1]} ({len(seasons)} seasons)")
    if result["most_common_opponents"]:
        rivals = ", ".join(f"{r['team']} ({r['matches']})" for r in result["most_common_opponents"])
        lines.append(f"- Most common opponents: {rivals}")
    players = result.get("fifa_players")
    if players:
        lines.append(
            f"- FIFA 19 squad: {players['player_count']} players, avg overall {players['average_overall']}"
        )
        for p in players["top_players"][:5]:
            lines.append(f"  - {p['name']} — {p['overall']} ({p['position']})")
    elif result.get("fifa_note"):
        lines.append(f"- {result['fifa_note']}")
    return "\n".join(lines)


@server.tool()
def competition_statistics(competition: str = "", season: int | None = None) -> str:
    """Aggregate statistics for a competition (optionally one season).

    Args:
        competition: 'Brasileirão' / 'Serie A', 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C'.
        season: Optional season (year) filter, e.g. 2023.
    """
    kb = get_kb()
    result = kb.competition_statistics(competition or None, season)
    err = _error(result)
    if err:
        return err
    biggest = result["biggest_win"]
    return "\n".join([
        f"{result['competition']} statistics:"
        + (f" season {season}" if season else f" ({result['seasons'][0]}–{result['seasons'][-1]})" if result.get("seasons") else ""),
        f"- Matches: {result['match_count']} between {result['teams']} teams",
        f"- Date range: {result['date_range'][0]} to {result['date_range'][1]}" if result.get("date_range") else "",
        f"- Average goals per match: {result['average_goals_per_match']} (total {result['total_goals']})",
        f"- Home wins: {result['home_win_rate']}% | Draws: {result['draw_rate']}% | Away wins: {result['away_win_rate']}%",
        f"- Biggest win: {biggest['date']}: {biggest['home_team']} {biggest['home_goal']}-{biggest['away_goal']} {biggest['away_team']} ({biggest['competition']})",
    ])


@server.tool()
def biggest_wins(competition: str = "", season: int | None = None, limit: int = 10) -> str:
    """Largest-margin victories, optionally filtered by competition and season.

    Args:
        competition: Optional competition filter ('Brasileirão', 'Copa do Brasil', 'Libertadores').
        season: Optional season (year) filter.
        limit: Max results (default 10).
    """
    kb = get_kb()
    result = kb.biggest_wins(competition or None, season, limit)
    if not result["wins"]:
        return "No victories found for the given filters."
    lines = [f"Biggest victories (margin) in dataset:"]
    for m in result["wins"]:
        lines.append(_fmt_match(m))
    return "\n".join(lines)


@server.tool()
def compare_seasons(competition: str, season_a: int, season_b: int) -> str:
    """Compare aggregate statistics between two seasons of a competition.

    Args:
        competition: 'Brasileirão' / 'Serie A', 'Copa do Brasil', 'Libertadores'.
        season_a: First season year, e.g. 2018.
        season_b: Second season year, e.g. 2019.
    """
    kb = get_kb()
    result = kb.compare_seasons(competition, season_a, season_b)
    err = _error(result)
    if err:
        return err
    lines = [f"{result['competition']}: {season_a} vs {season_b}"]
    for field, values in result["comparison"].items():
        label = field.replace("_", " ")
        lines.append(f"- {label}: {values['season_a']} ({season_a}) vs {values['season_b']} ({season_b})")
    return "\n".join(lines)


@server.tool()
def list_teams(competition: str = "") -> str:
    """List teams known in the datasets, optionally filtered by competition.

    Args:
        competition: Optional filter ('Brasileirão', 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C').
    """
    kb = get_kb()
    result = kb.list_teams(competition or None)
    err = _error(result)
    if err:
        return err
    lines = [f"Teams ({result['count']}):"]
    lines.append(", ".join(t["team"] for t in result["teams"][:150]))
    if result["count"] > 150:
        lines.append(f"... and {result['count'] - 150} more (use team_statistics or search_matches for details)")
    return "\n".join(lines)


@server.tool()
def dataset_summary() -> str:
    """Describe the loaded datasets: files, coverage, team and player counts."""
    kb = get_kb()
    s = kb.summary()
    lines = ["Brazilian Soccer MCP — loaded datasets:"]
    for file, desc in s["datasets"].items():
        lines.append(f"- {file}: {desc}")
    lines.append(f"- Matches loaded: {s['matches_loaded']}")
    lines.append(f"- Matches by competition: " + ", ".join(f"{k}: {v}" for k, v in s["matches_by_competition"].items()))
    lines.append(f"- Seasons covered: {s['seasons_covered'][0]}–{s['seasons_covered'][1]}")
    lines.append(f"- Unique teams: {s['unique_teams']}")
    lines.append(f"- Players loaded: {s['players_loaded']} ({s['player_nationalities']} nationalities)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http", "sse"], default="stdio")
    parser.add_argument("--data-dir", default=None, help="Override the data/kaggle directory")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.data_dir:
        global _knowledge_base
        _knowledge_base = KnowledgeBase(args.data_dir)
    else:
        get_kb()  # warm the cache so first tool call is fast

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport=args.transport, port=args.port)


if __name__ == "__main__":
    main()
