"""
Brazilian Soccer MCP - Query Engine.

This module implements the high-level query operations exposed by the MCP
server.  It is intentionally decoupled from ``server.py`` so that the same
logic can be unit-tested without spinning up an MCP transport.

All public functions accept raw user-facing strings and return either a
formatted markdown string or a serializable Python structure.  Team-name
normalization is performed internally.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pandas as pd

from brazilian_soccer_mcp.data_store import DataStore, get_data_store
from brazilian_soccer_mcp.team_normalizer import normalize_team_name


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _format_date(value: pd.Timestamp | Any) -> str:
    """Return a human-readable date string."""
    if pd.isna(value):
        return "Unknown"
    return pd.to_datetime(value).strftime("%Y-%m-%d")

def _match_line(row: pd.Series) -> str:
    """Format a single match as a markdown bullet."""
    competition = row.get("competition", "")
    round_label = row.get("round", "")
    stage = row.get("stage", "")
    extra = ""
    if competition:
        extra += f" ({competition}"
        if stage and str(stage).lower() not in ("nan", "none", ""):
            extra += f" {stage}"
        elif round_label and str(round_label).lower() not in ("nan", "none", ""):
            extra += f" Round {round_label}"
        extra += ")"
    hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else 0
    ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else 0
    return (
        f"- {_format_date(row['date'])}: "
        f"{row['home_team']} {hg}-{ag} "
        f"{row['away_team']}{extra}"
    )


def _filter_matches(
    store: DataStore,
    team: str | None = None,
    opponent: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    competition: str | None = None,
    season: int | None = None,
) -> pd.DataFrame:
    """Return a filtered copy of the matches DataFrame."""
    df = store.matches.copy()

    if team:
        canonical = normalize_team_name(team)
        df = df[(df["home_team"] == canonical) | (df["away_team"] == canonical)]

    if opponent:
        canonical_opp = normalize_team_name(opponent)
        df = df[
            (df["home_team"] == canonical_opp) | (df["away_team"] == canonical_opp)
        ]

    if competition:
        df = df[df["competition"].str.lower() == competition.lower()]

    if season is not None:
        df = df[df["season"] == season]

    if date_from:
        df = df[df["date"] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df["date"] <= pd.to_datetime(date_to)]

    return df


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------
def find_matches(
    store: DataStore | None = None,
    team: str | None = None,
    opponent: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 20,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Search matches by team, opponent, date range, competition and season."""
    store = store or get_data_store()
    df = _filter_matches(
        store,
        team=team,
        opponent=opponent,
        date_from=date_from,
        date_to=date_to,
        competition=competition,
        season=season,
    )

    total = len(df)
    df = df.head(limit)

    if response_format.lower() == "json":
        return {
            "total": total,
            "returned": len(df),
            "matches": df.replace({pd.NaT: None}).to_dict(orient="records"),
        }

    header = []
    if team and opponent:
        header.append(f"Matches between {normalize_team_name(team)} and {normalize_team_name(opponent)}")
    elif team:
        header.append(f"Matches for {normalize_team_name(team)}")
    elif opponent:
        header.append(f"Matches involving {normalize_team_name(opponent)}")
    else:
        header.append("Matches")

    if competition:
        header[-1] += f" ({competition})"
    if season:
        header[-1] += f" {season}"

    lines = [f"# {header[0]}", f"Showing {len(df)} of {total} matches", ""]
    for _, row in df.iterrows():
        lines.append(_match_line(row))
    return "\n".join(lines)


def get_head_to_head(
    store: DataStore | None = None,
    team_a: str = "",
    team_b: str = "",
    limit: int = 20,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return the head-to-head history between two teams."""
    store = store or get_data_store()
    canonical_a = normalize_team_name(team_a)
    canonical_b = normalize_team_name(team_b)

    df = store.matches.copy()
    df = df[
        (
            (df["home_team"] == canonical_a) & (df["away_team"] == canonical_b)
        )
        | (
            (df["home_team"] == canonical_b) & (df["away_team"] == canonical_a)
        )
    ].sort_values("date", ascending=False)

    wins_a = draws = wins_b = 0
    for _, row in df.iterrows():
        if row["home_team"] == canonical_a:
            if row["home_goal"] > row["away_goal"]:
                wins_a += 1
            elif row["home_goal"] < row["away_goal"]:
                wins_b += 1
            else:
                draws += 1
        else:
            if row["home_goal"] > row["away_goal"]:
                wins_b += 1
            elif row["home_goal"] < row["away_goal"]:
                wins_a += 1
            else:
                draws += 1

    total = len(df)
    df = df.head(limit)

    if response_format.lower() == "json":
        return {
            "team_a": canonical_a,
            "team_b": canonical_b,
            "total_matches": total,
            f"{canonical_a}_wins": wins_a,
            "draws": draws,
            f"{canonical_b}_wins": wins_b,
            "matches": df.replace({pd.NaT: None}).to_dict(orient="records"),
        }

    lines = [
        f"# {canonical_a} vs {canonical_b}",
        f"Head-to-head in dataset: {canonical_a} {wins_a} wins, {canonical_b} {wins_b} wins, {draws} draws",
        f"Showing {len(df)} of {total} matches:",
        "",
    ]
    for _, row in df.iterrows():
        lines.append(_match_line(row))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------
def get_team_stats(
    store: DataStore | None = None,
    team: str = "",
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return wins, draws, losses and goals for a team."""
    store = store or get_data_store()
    canonical = normalize_team_name(team)
    stats = store.team_stats(canonical, season=season, competition=competition, venue=venue)

    if response_format.lower() == "json":
        return stats

    venue_label = venue.title() if venue else "Overall"
    season_label = str(season) if season else "all seasons"
    comp_label = competition if competition else "all competitions"
    return (
        f"# {canonical} {venue_label} Record ({comp_label}, {season_label})\n"
        f"- Matches: {stats['matches']}\n"
        f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
        f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}\n"
        f"- Goal Difference: {stats.get('goal_difference', 0)}\n"
        f"- Win rate: {stats['win_rate']}%"
    )


def list_teams(
    store: DataStore | None = None,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return the list of teams present in the match data."""
    store = store or get_data_store()
    teams = sorted(
        set(store.matches["home_team"].dropna())
        | set(store.matches["away_team"].dropna())
    )
    teams = [t for t in teams if t]

    if response_format.lower() == "json":
        return {"teams": teams, "count": len(teams)}

    lines = [f"# Teams in dataset ({len(teams)})", ""]
    lines.extend(f"- {t}" for t in teams)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------
def search_players(
    store: DataStore | None = None,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Search the FIFA player database."""
    store = store or get_data_store()
    df = store.players.copy()

    if name:
        df = df[df["name"].str.contains(name, case=False, na=False)]
    if nationality:
        df = df[
            df["nationality"]
            .str.strip()
            .str.lower()
            .eq(nationality.strip().lower())
        ]
    if club:
        canonical = normalize_team_name(club)
        df = df[
            (df["club"].str.lower() == canonical.lower())
            | df["club_raw"].str.contains(club, case=False, na=False)
        ]
    if position:
        df = df[df["position"].str.contains(position, case=False, na=False)]
    if min_overall is not None:
        df = df[df["overall"] >= min_overall]

    df = df.sort_values("overall", ascending=False).head(limit)

    if response_format.lower() == "json":
        return {
            "total_matching": len(df),
            "players": df.fillna("").to_dict(orient="records"),
        }

    lines = [f"# Player Search Results ({len(df)} found)", ""]
    for _, row in df.iterrows():
        club_display = row["club"] or row["club_raw"] or "Unknown"
        lines.append(
            f"- {row['name']} - Overall: {row['overall']}, "
            f"Position: {row['position']}, Club: {club_display}, "
            f"Nationality: {row['nationality']}"
        )
    return "\n".join(lines)


def top_brazilian_players(
    store: DataStore | None = None,
    limit: int = 10,
    at_brazilian_club: bool = False,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return the highest-rated Brazilian players."""
    store = store or get_data_store()
    df = store.players[store.players["is_brazilian"]].copy()

    if at_brazilian_club:
        brazilian_clubs = set(store.matches["home_team"]) | set(store.matches["away_team"])
        df = df[df["club"].isin(brazilian_clubs)]

    df = df.sort_values("overall", ascending=False).head(limit)

    if response_format.lower() == "json":
        return {
            "count": len(df),
            "players": df.fillna("").to_dict(orient="records"),
        }

    lines = [f"# Top Brazilian Players{' at Brazilian Clubs' if at_brazilian_club else ''}", ""]
    for _, row in df.iterrows():
        club_display = row["club"] or row["club_raw"] or "Unknown"
        lines.append(
            f"- {row['name']} - Overall: {row['overall']}, "
            f"Position: {row['position']}, Club: {club_display}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------
def get_standings(
    store: DataStore | None = None,
    season: int = 0,
    competition: str | None = None,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return calculated league standings for a season."""
    store = store or get_data_store()
    df = store.standings(season, competition=competition)

    if response_format.lower() == "json":
        return {
            "season": season,
            "competition": competition,
            "standings": df.to_dict(orient="records"),
        }

    lines = [
        f"# {season} {competition or 'All Competitions'} Standings (calculated from matches)",
        "",
    ]
    for idx, row in df.iterrows():
        rank = int(idx) + 1
        marker = " - Champion" if rank == 1 else ""
        lines.append(
            f"{rank}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L){marker}"
        )
    return "\n".join(lines)


def get_competition_winners(
    store: DataStore | None = None,
    season: int = 0,
    competition: str | None = None,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return the team with the most points in a season/competition."""
    store = store or get_data_store()
    df = store.standings(season, competition=competition)

    if df.empty:
        result: dict[str, Any] = {
            "season": season,
            "competition": competition,
            "winner": None,
            "message": "No standings could be calculated for the requested season/competition.",
        }
        return result if response_format.lower() == "json" else result["message"]

    winner = df.iloc[0]
    result = {
        "season": season,
        "competition": competition,
        "winner": winner["team"],
        "points": int(winner["points"]),
        "record": f"{winner['wins']}W, {winner['draws']}D, {winner['losses']}L",
    }

    if response_format.lower() == "json":
        return result

    return (
        f"# {season} {competition or 'All Competitions'} Winner\n"
        f"{result['winner']} - {result['points']} pts ({result['record']})"
    )


# ---------------------------------------------------------------------------
# Statistical analysis queries
# ---------------------------------------------------------------------------
def get_biggest_wins(
    store: DataStore | None = None,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return the biggest victories in the dataset."""
    store = store or get_data_store()
    df = store.matches.copy()
    if competition:
        df = df[df["competition"].str.lower() == competition.lower()]
    if season is not None:
        df = df[df["season"] == season]

    df = df.dropna(subset=["home_goal", "away_goal"]).copy()
    df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
    df = df.sort_values("margin", ascending=False).head(limit)

    if response_format.lower() == "json":
        return {
            "count": len(df),
            "matches": df.replace({pd.NaT: None}).to_dict(orient="records"),
        }

    lines = [f"# Biggest Victories{' (' + competition + ')' if competition else ''}", ""]
    for _, row in df.iterrows():
        lines.append(_match_line(row))
    return "\n".join(lines)


def get_average_goals(
    store: DataStore | None = None,
    competition: str | None = None,
    season: int | None = None,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return average goals per match and home win rate."""
    store = store or get_data_store()
    df = store.matches.copy()
    if competition:
        df = df[df["competition"].str.lower() == competition.lower()]
    if season is not None:
        df = df[df["season"] == season]

    df = df.dropna(subset=["home_goal", "away_goal"])
    total_goals = df["home_goal"].sum() + df["away_goal"].sum()
    matches = len(df)
    avg = round(total_goals / matches, 2) if matches else 0.0

    home_wins = int((df["home_goal"] > df["away_goal"]).sum())
    home_win_rate = round(home_wins / matches * 100, 1) if matches else 0.0

    result = {
        "matches": matches,
        "average_goals_per_match": avg,
        "home_win_rate": home_win_rate,
    }
    if response_format.lower() == "json":
        return result

    return (
        f"# Goal Averages{' (' + competition + ')' if competition else ''}\n"
        f"- Matches analyzed: {matches}\n"
        f"- Average goals per match: {avg}\n"
        f"- Home win rate: {home_win_rate}%"
    )


def get_top_scorers(
    store: DataStore | None = None,
    season: int | None = None,
    limit: int = 10,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Return the teams with the most goals scored."""
    store = store or get_data_store()
    df = store.top_scorers(season=season, limit=limit)

    if response_format.lower() == "json":
        return {"count": len(df), "top_scorers": df.to_dict(orient="records")}

    season_label = str(season) if season else "all seasons"
    lines = [f"# Top Scoring Teams ({season_label})", ""]
    for idx, row in df.iterrows():
        lines.append(f"{int(idx) + 1}. {row['team']} - {int(row['goals'])} goals")
    return "\n".join(lines)


def compare_seasons(
    store: DataStore | None = None,
    season_a: int = 0,
    season_b: int = 0,
    competition: str | None = None,
    response_format: str = "markdown",
) -> str | dict[str, Any]:
    """Compare aggregate match statistics across two seasons."""
    store = store or get_data_store()

    def _season_stats(season: int) -> dict[str, Any]:
        df = store.matches[store.matches["season"] == season].copy()
        if competition:
            df = df[df["competition"].str.lower() == competition.lower()]
        df = df.dropna(subset=["home_goal", "away_goal"])
        matches = len(df)
        if matches == 0:
            return {"season": season, "matches": 0}
        home_wins = int((df["home_goal"] > df["away_goal"]).sum())
        draws = int((df["home_goal"] == df["away_goal"]).sum())
        away_wins = int((df["away_goal"] > df["home_goal"]).sum())
        return {
            "season": season,
            "matches": matches,
            "goals": int(df["home_goal"].sum() + df["away_goal"].sum()),
            "avg_goals": round(
                (df["home_goal"].sum() + df["away_goal"].sum()) / matches, 2
            ),
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "home_win_rate": round(home_wins / matches * 100, 1),
        }

    stats_a = _season_stats(season_a)
    stats_b = _season_stats(season_b)
    result = {"season_a": stats_a, "season_b": stats_b}

    if response_format.lower() == "json":
        return result

    lines = [
        f"# Season Comparison: {season_a} vs {season_b}",
        "",
        f"| Metric | {season_a} | {season_b} |",
        "|---|---|---|",
    ]
    for key in ["matches", "goals", "avg_goals", "home_wins", "draws", "away_wins", "home_win_rate"]:
        label = key.replace("_", " ").title()
        lines.append(f"| {label} | {stats_a.get(key, 0)} | {stats_b.get(key, 0)} |")
    return "\n".join(lines)
