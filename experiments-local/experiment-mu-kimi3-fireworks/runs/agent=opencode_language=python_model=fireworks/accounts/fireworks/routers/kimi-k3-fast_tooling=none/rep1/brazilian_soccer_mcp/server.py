"""MCP server exposing the Brazilian soccer knowledge graph as tools.

Why: the spec requires an MCP server that an LLM client can use to
answer natural-language questions about Brazilian soccer.

What: a FastMCP server whose tools wrap ``QueryEngine`` and return
LLM-friendly, pre-formatted text (matching the spec's answer formats).

Run:
    python -m brazilian_soccer_mcp            # stdio transport (default)
    MCP_TRANSPORT=http python -m brazilian_soccer_mcp   # streamable HTTP
"""

from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP

from .data_loader import get_dataset
from .queries import QueryEngine

mcp = FastMCP(
    "brazilian-soccer",
    instructions=(
        "Knowledge-graph style access to Brazilian soccer data: match results "
        "(Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores), team "
        "records, head-to-head, league standings and the FIFA player database. "
        "Team names are normalized, so 'Palmeiras-SP', 'Palmeiras' and "
        "'palmeiras' all refer to the same team."
    ),
)


def _engine() -> QueryEngine:
    data_dir = os.environ.get("SOCCER_DATA_DIR") or None
    return QueryEngine(get_dataset(data_dir))


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_match(m: dict[str, Any]) -> str:
    label = f"{m['home_team']} {m['home_goals']}-{m['away_goals']} {m['away_team']}"
    suffix = m["competition"]
    if m.get("round"):
        suffix += f" ({'Round' if str(m['round']).isdigit() else 'Stage'} {m['round']})"
    return f"- {m['date']}: {label} [{suffix}]"


def _err(result: dict[str, Any]) -> str | None:
    return result.get("error")


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------


@mcp.tool
def find_matches(
    team: str | None = None,
    versus: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
    ascending: bool = False,
) -> str:
    """Find matches by team, opponent, competition, season or date range.

    Examples: team="Flamengo", versus="Fluminense"; team="Palmeiras",
    season=2023; competition="Copa do Brasil", season=2023.
    Dates accept "YYYY-MM-DD" or "DD/MM/YYYY".
    """
    result = _engine().find_matches(
        team=team,
        versus=versus,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        ascending=ascending,
    )
    if (e := _err(result)) :
        return e
    if not result["matches"]:
        return "No matches found for the given criteria."
    header_bits = []
    for query, names in result["resolved_teams"].items():
        header_bits.append("/".join(names))
    header = " vs ".join(header_bits) if header_bits else (competition or "Matches")
    if season:
        header += f" ({season})"
    lines = [f"{header} — {result['total']} match(es) in dataset:"]
    lines.extend(_fmt_match(m) for m in result["matches"])
    if result["total"] > result["returned"]:
        lines.append(f"... ({result['total'] - result['returned']} more matches in dataset)")
    return "\n".join(lines)


@mcp.tool
def last_match(team1: str, team2: str) -> str:
    """Most recent match between two teams, e.g. "Flamengo" and "Corinthians"."""
    result = _engine().head_to_head(team1, team2)
    if (e := _err(result)):
        return e
    if not result["last_match"]:
        return f"No matches found between {team1} and {team2}."
    m = result["last_match"]
    return (
        f"Most recent {team1} vs {team2}:\n"
        f"{m['date']}: {m['home_team']} {m['home_goals']}-{m['away_goals']} "
        f"{m['away_team']} [{m['competition']}]"
    )


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------


@mcp.tool
def head_to_head(team1: str, team2: str) -> str:
    """Compare two teams head-to-head across all competitions.

    Example: team1="Palmeiras", team2="Santos".
    """
    result = _engine().head_to_head(team1, team2)
    if (e := _err(result)):
        return e
    n1 = result["team1"][0]
    n2 = result["team2"][0]
    lines = [f"{n1} vs {n2} — head-to-head in dataset:"]
    lines.extend(_fmt_match(m) for m in result["matches"][:10])
    if result["total_matches"] > len(result["matches"]):
        lines.append(f"... ({result['total_matches'] - len(result['matches'])} more matches)")
    lines.append("")
    lines.append(
        f"Head-to-head: {n1} {result['team1_wins']} wins, "
        f"{n2} {result['team2_wins']} wins, {result['draws']} draws "
        f"({result['total_matches']} matches)"
    )
    return "\n".join(lines)


@mcp.tool
def team_statistics(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> str:
    """Win/loss/draw record and goals for a team.

    venue: "all" (default), "home" or "away".
    Example: team="Corinthians", season=2022, venue="home".
    """
    result = _engine().team_record(team, season=season, competition=competition, venue=venue)
    if (e := _err(result)):
        return e
    name = result["team"][0]
    scope = competition or "all competitions"
    when = f" ({season} {scope})" if season else f" ({scope})"
    where = "" if result["venue"] == "all" else f" {result['venue']}"
    lines = [f"{name}{where} record{when}:"]
    lines.append(f"- Matches: {result['matches']}")
    lines.append(
        f"- Wins: {result['wins']}, Draws: {result['draws']}, Losses: {result['losses']}"
    )
    lines.append(
        f"- Goals For: {result['goals_for']}, Goals Against: {result['goals_against']}"
    )
    lines.append(f"- Win rate: {result['win_rate_pct']}%")
    if result["venue"] == "all" and result["matches"]:
        h, a = result["home"], result["away"]
        lines.append(
            f"- Home: {h['matches']}P {h['wins']}W {h['draws']}D {h['losses']}L | "
            f"Away: {a['matches']}P {a['wins']}W {a['draws']}D {a['losses']}L"
        )
    return "\n".join(lines)


@mcp.tool
def team_competitions(team: str) -> str:
    """List every competition (and seasons) a team played in the datasets.

    Example: "What competitions has Palmeiras played in?" -> team="Palmeiras".
    """
    result = _engine().team_competitions(team)
    if (e := _err(result)):
        return e
    lines = [f"{result['team'][0]} — competitions in dataset ({result['total_matches']} matches):"]
    for c in result["competitions"]:
        seasons = c["seasons"]
        span = f"{seasons[0]}-{seasons[-1]}" if len(seasons) > 1 else str(seasons[0])
        lines.append(f"- {c['competition']}: {c['matches']} matches ({span})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. Player queries
# ---------------------------------------------------------------------------


def _fmt_player(p: dict[str, Any], rank: int | None = None) -> str:
    club = p["club"] or "No club"
    pos = p["position"] or "?"
    prefix = f"{rank}. " if rank is not None else "- "
    return f"{prefix}{p['name']} - Overall: {p['overall']}, Position: {pos}, Club: {club} ({p['nationality']})"


@mcp.tool
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    limit: int = 15,
) -> str:
    """Search FIFA players by name, nationality, club and/or position.

    Examples: nationality="Brazil" (top Brazilians); club="Grêmio";
    position_group="forward", club="Santos". position_group is one of
    "goalkeeper", "defender", "midfielder", "forward".
    """
    result = _engine().search_players(
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        position_group=position_group,
        min_overall=min_overall,
        limit=limit,
    )
    if (e := _err(result)):
        return e
    if not result["players"]:
        return "No players found for the given criteria."
    criteria = ", ".join(
        f"{k}={v}"
        for k, v in {
            "name": name,
            "nationality": nationality,
            "club": club,
            "position": position or position_group,
            "min_overall": min_overall,
        }.items()
        if v
    ) or "all players"
    lines = [f"Players matching {criteria} — {result['total']} found:"]
    lines.extend(_fmt_player(p, i + 1) for i, p in enumerate(result["players"]))
    if result["total"] > result["returned"]:
        lines.append(f"... ({result['total'] - result['returned']} more players in dataset)")
    return "\n".join(lines)


@mcp.tool
def player_profile(name: str) -> str:
    """Profile of one player (ratings, club, key skills).

    Example: "Who is Gabriel Barbosa?" -> name="Gabriel Barbosa".
    """
    result = _engine().player_profile(name)
    if (e := _err(result)):
        return e
    lines = [
        f"{result['name']} ({result['nationality']})",
        f"- Age: {result['age']} | Club: {result['club'] or 'No club'} | "
        f"Position: {result['position']} (#{result['jersey_number']})",
        f"- Overall: {result['overall']} | Potential: {result['potential']} | "
        f"Foot: {result.get('preferred_foot')}",
        f"- Height: {result['height']} | Weight: {result['weight']}",
    ]
    if result.get("skills"):
        skills = ", ".join(f"{k}: {v}" for k, v in result["skills"].items())
        lines.append(f"- Skills: {skills}")
    if result.get("other_matches"):
        lines.append(f"(Other players matching: {', '.join(result['other_matches'])})")
    return "\n".join(lines)


@mcp.tool
def club_roster(club: str, nationality: str | None = None) -> str:
    """Players at a club with average rating, e.g. club="Flamengo".

    Combine with nationality="Brazil" for Brazilian players at the club.
    """
    result = _engine().club_roster(club, nationality=nationality)
    if (e := _err(result)):
        return e
    nat = f" ({nationality} only)" if nationality else ""
    lines = [
        f"{club} squad{nat}: {result['total']} players (avg rating: {result['average_overall']})"
    ]
    lines.extend(_fmt_player(p, i + 1) for i, p in enumerate(result["players"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Competition queries
# ---------------------------------------------------------------------------


@mcp.tool
def competition_standings(season: int, competition: str = "Brasileirão Série A") -> str:
    """League table for a season, calculated from match results (3/1/0 pts).

    Example: "Who won the 2019 Brasileirão?" -> season=2019.
    """
    result = _engine().standings(season=season, competition=competition)
    if (e := _err(result)):
        return e
    lines = [
        f"{result['season']} {result['competition']} Standings "
        f"(calculated from {result['matches']} matches):"
    ]
    for row in result["standings"][:20]:
        tag = " - Champion" if row["position"] == 1 else ""
        lines.append(
            f"{row['position']:>2}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L) "
            f"GF {row['goals_for']} GA {row['goals_against']}{tag}"
        )
    if result["relegated"]:
        lines.append(f"Relegated: {', '.join(result['relegated'])}")
    return "\n".join(lines)


@mcp.tool
def competition_schedule(
    competition: str,
    season: int | None = None,
    stage: str | None = None,
    limit: int = 50,
) -> str:
    """Matches/bracket of a competition, optionally by season and stage.

    Example: "Show the 2018 Copa Libertadores bracket" ->
    competition="Copa Libertadores", season=2018. Stages include
    "group stage", "round of 16", "quarterfinals", "semifinals", "final".
    """
    result = _engine().competition_schedule(
        competition=competition, season=season, stage=stage, limit=limit
    )
    if not result["matches"]:
        return "No matches found for the given criteria."
    header = f"{result['competition']}"
    if season:
        header += f" {season}"
    if stage:
        header += f" — {stage}"
    lines = [f"{header} ({result['total']} matches):"]
    if result.get("stages"):
        lines.append(f"Stages present: {', '.join(result['stages'])}")
    lines.extend(_fmt_match(m) for m in result["matches"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. Statistical analysis
# ---------------------------------------------------------------------------


@mcp.tool
def biggest_victories(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> str:
    """Biggest wins (goal margin) in the dataset.

    Example: competition="Brasileirão Série A", limit=10.
    """
    result = _engine().biggest_wins(competition=competition, season=season, limit=limit)
    scope = competition or "all competitions"
    if season:
        scope += f" {season}"
    lines = [f"Biggest victories in {scope} (from {result['matches_considered']} matches):"]
    for i, m in enumerate(result["biggest_wins"], 1):
        lines.append(
            f"{i}. {m['date']}: {m['home_team']} {m['home_goals']}-{m['away_goals']} "
            f"{m['away_team']} ({m['competition']})"
        )
    return "\n".join(lines)


@mcp.tool
def competition_overview(competition: str | None = None, season: int | None = None) -> str:
    """Aggregate stats: average goals per match, home/draw/away win rates.

    Example: "What's the average goals per match in the Brasileirão?"
    -> competition="Brasileirão Série A".
    """
    result = _engine().competition_stats(competition=competition, season=season)
    if (e := _err(result)):
        return e
    scope = result["competition"] or "all competitions"
    if season:
        scope += f" {season}"
    lines = [f"Statistics for {scope} ({result['matches']} matches):"]
    lines.append(f"- Total goals: {result['total_goals']}")
    lines.append(f"- Average goals per match: {result['avg_goals_per_match']}")
    lines.append(f"- Home win rate: {result['home_win_rate_pct']}% ({result['home_wins']} matches)")
    lines.append(f"- Draw rate: {result['draw_rate_pct']}% ({result['draws']} matches)")
    lines.append(f"- Away win rate: {result['away_win_rate_pct']}% ({result['away_wins']} matches)")
    return "\n".join(lines)


@mcp.tool
def top_scoring_teams(
    season: int | None = None,
    competition: str | None = None,
    limit: int = 10,
) -> str:
    """Teams with the most goals in a season/competition.

    Example: "Which team scored the most goals in Serie A 2023?"
    -> competition="Serie A" (2022 is the last available season; check dataset_info).
    """
    result = _engine().top_scoring_teams(season=season, competition=competition, limit=limit)
    scope = result["competition"] or "all competitions"
    if season:
        scope += f" {season}"
    lines = [f"Top scoring teams in {scope}:"]
    for i, t in enumerate(result["top_scoring_teams"], 1):
        lines.append(f"{i}. {t['team']} - {t['goals']} goals")
    return "\n".join(lines)


@mcp.tool
def compare_seasons(season_a: int, season_b: int, competition: str | None = None) -> str:
    """Compare aggregate statistics of two seasons side by side.

    Example: "Compare the 2018 and 2019 seasons" -> season_a=2018, season_b=2019.
    """
    result = _engine().compare_seasons(season_a, season_b, competition=competition)
    a, b = result["season_a"], result["season_b"]
    if (e := _err(a)) or (e := _err(b)):
        return e
    scope = result["competition"] or "all competitions"
    lines = [f"Season comparison ({scope}):", f"{'Metric':<28}{season_a:>10}{season_b:>10}"]
    for label, key in (
        ("Matches", "matches"),
        ("Total goals", "total_goals"),
        ("Avg goals per match", "avg_goals_per_match"),
        ("Home win rate %", "home_win_rate_pct"),
        ("Draw rate %", "draw_rate_pct"),
        ("Away win rate %", "away_win_rate_pct"),
    ):
        lines.append(f"{label:<28}{a[key]:>10}{b[key]:>10}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@mcp.tool
def dataset_info() -> str:
    """Overview of the loaded datasets: row counts, competitions, seasons."""
    ds = get_dataset(os.environ.get("SOCCER_DATA_DIR") or None)
    s = ds.summary()
    per_comp = ds.matches.groupby("competition").size().sort_index()
    lines = [
        "Brazilian Soccer datasets loaded:",
        f"- Matches (deduplicated): {s['matches']}",
        f"- FIFA players: {s['players']}",
        f"- Teams: {s['teams']}",
        f"- Seasons: {min(s['seasons'])}-{max(s['seasons'])}",
        "- Matches per competition:",
    ]
    lines.extend(f"  - {comp}: {int(n)}" for comp, n in per_comp.items())
    lines.append("Source files: data/kaggle/*.csv (6 files)")
    return "\n".join(lines)


@mcp.tool
def list_teams(contains: str | None = None, limit: int = 50) -> str:
    """List known teams (canonical display names), optionally filtered.

    Example: contains="Fla" -> Flamengo, Fluminense, ...
    """
    eng = _engine()
    keys = eng.registry.keys()
    if contains:
        from .normalization import normalize_text

        needle = normalize_text(contains)
        keys = [k for k in keys if needle in k]
    names = [eng.registry.display_name(k) for k in keys[:limit]]
    lines = [f"Teams ({len(keys)} matching):"]
    lines.extend(f"- {n}" for n in names)
    if len(keys) > limit:
        lines.append(f"... ({len(keys) - limit} more)")
    return "\n".join(lines)


def main() -> None:
    """Run the MCP server over stdio (default) or HTTP via env vars."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        mcp.run(
            transport="streamable-http",
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8000")),
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
