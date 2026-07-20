#!/usr/bin/env python3
"""Brazilian Soccer MCP Server."""

import json
from typing import Any

import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from data_loader import (
    load_brasileirao, load_copa_brasil, load_libertadores,
    load_br_football, load_historico, load_fifa, load_all_matches,
    normalize_team,
)

app = Server("brazilian-soccer")

# --- Data loaded once at import time ---
_DATA: dict[str, Any] = {}


def _get_data() -> dict[str, Any]:
    if not _DATA:
        _DATA["brasileirao"] = load_brasileirao()
        _DATA["copa_brasil"] = load_copa_brasil()
        _DATA["libertadores"] = load_libertadores()
        _DATA["br_football"] = load_br_football()
        _DATA["historico"] = load_historico()
        _DATA["fifa"] = load_fifa()
        _DATA["all_matches"] = load_all_matches()
    return _DATA


def _fmt_match(row: pd.Series) -> str:
    date = row.get("datetime", "")
    if pd.notna(date) and hasattr(date, "strftime"):
        date = date.strftime("%Y-%m-%d")
    home = row.get("home_team", "")
    away = row.get("away_team", "")
    hg = int(row["home_goal"]) if pd.notna(row.get("home_goal")) else "?"
    ag = int(row["away_goal"]) if pd.notna(row.get("away_goal")) else "?"
    comp = row.get("competition", "")
    rnd = f" Round {int(row['round'])}" if "round" in row and pd.notna(row.get("round")) else ""
    stage = f" ({row['stage']})" if "stage" in row and pd.notna(row.get("stage")) else ""
    return f"{date}: {home} {hg}-{ag} {away} [{comp}{rnd}{stage}]"


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_matches",
            description=(
                "Search match data across all competitions (Brasileirão Serie A, "
                "Copa do Brasil, Copa Libertadores). Filter by team name(s), date range, "
                "competition, and/or season. Returns match results with scores."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name to search (matches home or away). Partial match supported.",
                    },
                    "team2": {
                        "type": "string",
                        "description": "Second team name for head-to-head search.",
                    },
                    "competition": {
                        "type": "string",
                        "description": "Competition filter: 'Brasileirao', 'Copa do Brasil', 'Libertadores', or leave empty for all.",
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year (e.g. 2023).",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date filter (YYYY-MM-DD).",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date filter (YYYY-MM-DD).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum matches to return (default 20).",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="get_team_stats",
            description=(
                "Get statistics for a team: wins, losses, draws, goals for/against, "
                "win rate. Optionally filter by competition and/or season."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "team": {
                        "type": "string",
                        "description": "Team name.",
                    },
                    "competition": {
                        "type": "string",
                        "description": "Competition filter (optional).",
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year (optional).",
                    },
                    "home_only": {
                        "type": "boolean",
                        "description": "Only include home matches.",
                        "default": False,
                    },
                    "away_only": {
                        "type": "boolean",
                        "description": "Only include away matches.",
                        "default": False,
                    },
                },
                "required": ["team"],
            },
        ),
        Tool(
            name="search_players",
            description=(
                "Search FIFA player data by name, nationality, club, or position. "
                "Returns player ratings and attributes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Player name (partial match).",
                    },
                    "nationality": {
                        "type": "string",
                        "description": "Player nationality (e.g. 'Brazil').",
                    },
                    "club": {
                        "type": "string",
                        "description": "Club name (partial match).",
                    },
                    "position": {
                        "type": "string",
                        "description": "Playing position (e.g. 'ST', 'GK', 'CB').",
                    },
                    "min_overall": {
                        "type": "integer",
                        "description": "Minimum FIFA overall rating.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default 20).",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="get_head_to_head",
            description=(
                "Get head-to-head record between two teams across all competitions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "team1": {
                        "type": "string",
                        "description": "First team name.",
                    },
                    "team2": {
                        "type": "string",
                        "description": "Second team name.",
                    },
                    "competition": {
                        "type": "string",
                        "description": "Competition filter (optional).",
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year (optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum recent matches to show (default 10).",
                        "default": 10,
                    },
                },
                "required": ["team1", "team2"],
            },
        ),
        Tool(
            name="get_competition_standings",
            description=(
                "Calculate standings (points table) for Brasileirão Serie A in a given season."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "season": {
                        "type": "integer",
                        "description": "Season year (e.g. 2019).",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top teams to show (default 20).",
                        "default": 20,
                    },
                },
                "required": ["season"],
            },
        ),
        Tool(
            name="get_biggest_wins",
            description=(
                "Find the biggest victories (largest goal margins) across all competitions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "description": "Competition filter (optional).",
                    },
                    "team": {
                        "type": "string",
                        "description": "Limit to wins/losses involving this team (optional).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default 10).",
                        "default": 10,
                    },
                },
            },
        ),
        Tool(
            name="get_average_goals",
            description=(
                "Calculate average goals per match statistics for a competition and/or season."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "competition": {
                        "type": "string",
                        "description": "Competition filter (optional).",
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year (optional).",
                    },
                },
            },
        ),
    ]


def _filter_competition(df: pd.DataFrame, competition: str) -> pd.DataFrame:
    if not competition:
        return df
    comp_lower = competition.lower()
    if "brasil" in comp_lower and "cup" not in comp_lower and "copa" not in comp_lower:
        mask = df["competition"].str.lower().str.contains("brasileirao", na=False)
    elif "copa" in comp_lower and "brasil" in comp_lower:
        mask = df["competition"].str.lower().str.contains("copa do brasil", na=False)
    elif "libertadores" in comp_lower:
        mask = df["competition"].str.lower().str.contains("libertadores", na=False)
    else:
        mask = df["competition"].str.lower().str.contains(comp_lower, na=False)
    return df[mask]


def _find_team_matches(df: pd.DataFrame, team: str) -> pd.Series:
    norm = normalize_team(team)
    # Try normalized first, then partial raw match
    mask_norm = (df["home_team_norm"] == norm) | (df["away_team_norm"] == norm)
    if mask_norm.any():
        return mask_norm
    # Fallback: case-insensitive partial match on original names
    tl = team.lower()
    return (
        df["home_team"].str.lower().str.contains(tl, na=False) |
        df["away_team"].str.lower().str.contains(tl, na=False)
    )


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    data = _get_data()

    if name == "search_matches":
        df = data["all_matches"].copy()
        team = arguments.get("team", "")
        team2 = arguments.get("team2", "")
        competition = arguments.get("competition", "")
        season = arguments.get("season")
        date_from = arguments.get("date_from", "")
        date_to = arguments.get("date_to", "")
        limit = int(arguments.get("limit", 20))

        if team:
            mask = _find_team_matches(df, team)
            df = df[mask]
        if team2:
            mask2 = _find_team_matches(df, team2)
            df = df[mask2]
        if competition:
            df = _filter_competition(df, competition)
        if season:
            df = df[df.get("season", pd.Series()) == int(season)] if "season" in df.columns else df
        if date_from:
            df = df[df["datetime"] >= pd.to_datetime(date_from)]
        if date_to:
            df = df[df["datetime"] <= pd.to_datetime(date_to)]

        df = df.dropna(subset=["datetime"]).sort_values("datetime", ascending=False)
        total = len(df)
        rows = df.head(limit)

        if rows.empty:
            return [TextContent(type="text", text="No matches found matching the criteria.")]

        lines = [f"Found {total} matches (showing up to {limit}):"]
        for _, row in rows.iterrows():
            lines.append("  " + _fmt_match(row))
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "get_team_stats":
        df = data["all_matches"].copy()
        team = arguments["team"]
        competition = arguments.get("competition", "")
        season = arguments.get("season")
        home_only = arguments.get("home_only", False)
        away_only = arguments.get("away_only", False)

        if competition:
            df = _filter_competition(df, competition)
        if season and "season" in df.columns:
            df = df[df["season"] == int(season)]

        team_norm = normalize_team(team)
        tl = team.lower()

        home_mask = (df["home_team_norm"] == team_norm) | df["home_team"].str.lower().str.contains(tl, na=False)
        away_mask = (df["away_team_norm"] == team_norm) | df["away_team"].str.lower().str.contains(tl, na=False)

        if home_only:
            home_df = df[home_mask].copy()
            away_df = pd.DataFrame()
        elif away_only:
            home_df = pd.DataFrame()
            away_df = df[away_mask].copy()
        else:
            home_df = df[home_mask].copy()
            away_df = df[away_mask & ~home_mask].copy()

        def _stats(hdf, adf):
            stats = {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
                     "goals_for": 0, "goals_against": 0}
            for _, row in hdf.iterrows():
                hg, ag = row.get("home_goal"), row.get("away_goal")
                if pd.isna(hg) or pd.isna(ag):
                    continue
                hg, ag = int(hg), int(ag)
                stats["matches"] += 1
                stats["goals_for"] += hg
                stats["goals_against"] += ag
                if hg > ag:
                    stats["wins"] += 1
                elif hg == ag:
                    stats["draws"] += 1
                else:
                    stats["losses"] += 1
            for _, row in adf.iterrows():
                hg, ag = row.get("home_goal"), row.get("away_goal")
                if pd.isna(hg) or pd.isna(ag):
                    continue
                hg, ag = int(hg), int(ag)
                stats["matches"] += 1
                stats["goals_for"] += ag
                stats["goals_against"] += hg
                if ag > hg:
                    stats["wins"] += 1
                elif hg == ag:
                    stats["draws"] += 1
                else:
                    stats["losses"] += 1
            return stats

        stats = _stats(home_df, away_df)
        m = stats["matches"]
        if m == 0:
            return [TextContent(type="text", text=f"No matches found for team '{team}'.")]

        wr = stats["wins"] / m * 100
        label = competition or "All competitions"
        s_label = f" ({season})" if season else ""
        lines = [
            f"{team} stats - {label}{s_label}:",
            f"  Matches: {m}",
            f"  Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}",
            f"  Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}",
            f"  Goal Difference: {stats['goals_for'] - stats['goals_against']:+d}",
            f"  Win Rate: {wr:.1f}%",
        ]
        if not home_only and not away_only:
            h_stats = _stats(home_df, pd.DataFrame())
            a_stats = _stats(pd.DataFrame(), away_df)
            if h_stats["matches"]:
                lines.append(f"  Home: {h_stats['wins']}W/{h_stats['draws']}D/{h_stats['losses']}L "
                             f"(GF:{h_stats['goals_for']} GA:{h_stats['goals_against']})")
            if a_stats["matches"]:
                lines.append(f"  Away: {a_stats['wins']}W/{a_stats['draws']}D/{a_stats['losses']}L "
                             f"(GF:{a_stats['goals_for']} GA:{a_stats['goals_against']})")
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "search_players":
        df = data["fifa"].copy()
        name_q = arguments.get("name", "")
        nationality = arguments.get("nationality", "")
        club = arguments.get("club", "")
        position = arguments.get("position", "")
        min_overall = arguments.get("min_overall")
        limit = int(arguments.get("limit", 20))

        if name_q:
            df = df[df["Name"].str.lower().str.contains(name_q.lower(), na=False)]
        if nationality:
            df = df[df["Nationality"].str.lower().str.contains(nationality.lower(), na=False)]
        if club:
            df = df[df["Club"].str.lower().str.contains(club.lower(), na=False)]
        if position:
            df = df[df["Position"].str.lower().str.contains(position.lower(), na=False)]
        if min_overall:
            df = df[df["Overall"] >= int(min_overall)]

        df = df.sort_values("Overall", ascending=False)
        total = len(df)
        rows = df.head(limit)

        if rows.empty:
            return [TextContent(type="text", text="No players found matching the criteria.")]

        lines = [f"Found {total} players (showing top {min(limit, total)} by overall rating):"]
        for _, row in rows.iterrows():
            name_str = row.get("Name", "")
            overall = int(row["Overall"]) if pd.notna(row.get("Overall")) else "?"
            pos = row.get("Position", "")
            club_str = row.get("Club", "")
            nat = row.get("Nationality", "")
            age = int(row["Age"]) if pd.notna(row.get("Age")) else "?"
            lines.append(f"  {name_str} | Overall: {overall} | Pos: {pos} | Club: {club_str} | Nat: {nat} | Age: {age}")
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "get_head_to_head":
        df = data["all_matches"].copy()
        team1 = arguments["team1"]
        team2 = arguments["team2"]
        competition = arguments.get("competition", "")
        season = arguments.get("season")
        limit = int(arguments.get("limit", 10))

        if competition:
            df = _filter_competition(df, competition)
        if season and "season" in df.columns:
            df = df[df["season"] == int(season)]

        t1_norm = normalize_team(team1)
        t2_norm = normalize_team(team2)
        t1l = team1.lower()
        t2l = team2.lower()

        def matches_team(df, norm, raw):
            return (df["home_team_norm"] == norm) | (df["away_team_norm"] == norm) | \
                   df["home_team"].str.lower().str.contains(raw, na=False) | \
                   df["away_team"].str.lower().str.contains(raw, na=False)

        mask1 = matches_team(df, t1_norm, t1l)
        mask2 = matches_team(df, t2_norm, t2l)
        h2h = df[mask1 & mask2].copy()

        total = len(h2h)
        if total == 0:
            return [TextContent(type="text", text=f"No matches found between '{team1}' and '{team2}'.")]

        t1_wins = t2_wins = draws = 0
        for _, row in h2h.iterrows():
            hg, ag = row.get("home_goal"), row.get("away_goal")
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            ht_norm = row.get("home_team_norm", "")
            ht_raw = row.get("home_team", "").lower()
            home_is_t1 = (ht_norm == t1_norm) or (t1l in ht_raw)
            if hg == ag:
                draws += 1
            elif hg > ag:
                if home_is_t1:
                    t1_wins += 1
                else:
                    t2_wins += 1
            else:
                if home_is_t1:
                    t2_wins += 1
                else:
                    t1_wins += 1

        h2h_sorted = h2h.dropna(subset=["datetime"]).sort_values("datetime", ascending=False)
        lines = [
            f"Head-to-Head: {team1} vs {team2} ({total} matches)",
            f"  {team1} wins: {t1_wins} | {team2} wins: {t2_wins} | Draws: {draws}",
            f"",
            f"Recent matches (up to {limit}):",
        ]
        for _, row in h2h_sorted.head(limit).iterrows():
            lines.append("  " + _fmt_match(row))
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "get_competition_standings":
        season = int(arguments["season"])
        top_n = int(arguments.get("top_n", 20))

        # Use Brasileirão datasets
        frames = []
        for src in ["brasileirao", "historico"]:
            df = data[src].copy()
            if "season" in df.columns:
                frames.append(df[df["season"] == season])
        if not frames:
            return [TextContent(type="text", text=f"No data found for season {season}.")]
        df = pd.concat(frames, ignore_index=True).drop_duplicates()

        # Build standings
        teams: dict[str, dict] = {}

        def update(team, gf, ga):
            if team not in teams:
                teams[team] = {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
            t = teams[team]
            t["P"] += 1
            t["GF"] += gf
            t["GA"] += ga
            if gf > ga:
                t["W"] += 1
                t["Pts"] += 3
            elif gf == ga:
                t["D"] += 1
                t["Pts"] += 1
            else:
                t["L"] += 1

        for _, row in df.iterrows():
            hg, ag = row.get("home_goal"), row.get("away_goal")
            if pd.isna(hg) or pd.isna(ag):
                continue
            home = row.get("home_team_norm") or row.get("home_team", "")
            away = row.get("away_team_norm") or row.get("away_team", "")
            update(home, int(hg), int(ag))
            update(away, int(ag), int(hg))

        if not teams:
            return [TextContent(type="text", text=f"No match data found for Brasileirão {season}.")]

        table = sorted(teams.items(), key=lambda x: (-x[1]["Pts"], -(x[1]["GF"] - x[1]["GA"]), -x[1]["GF"]))
        lines = [f"Brasileirão Serie A {season} Standings (calculated):"]
        for i, (team, s) in enumerate(table[:top_n], 1):
            gd = s["GF"] - s["GA"]
            lines.append(f"  {i:2}. {team:<30} Pts:{s['Pts']:3} | {s['W']}W {s['D']}D {s['L']}L | "
                         f"GF:{s['GF']} GA:{s['GA']} GD:{gd:+d}")
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "get_biggest_wins":
        df = data["all_matches"].copy()
        competition = arguments.get("competition", "")
        team = arguments.get("team", "")
        limit = int(arguments.get("limit", 10))

        if competition:
            df = _filter_competition(df, competition)
        if team:
            mask = _find_team_matches(df, team)
            df = df[mask]

        df = df.dropna(subset=["home_goal", "away_goal"])
        df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
        df = df.sort_values("margin", ascending=False)

        rows = df.head(limit)
        if rows.empty:
            return [TextContent(type="text", text="No match data found.")]

        lines = [f"Biggest victories (top {limit}):"]
        for _, row in rows.iterrows():
            margin = int(row["margin"])
            lines.append(f"  Margin {margin}: " + _fmt_match(row))
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "get_average_goals":
        df = data["all_matches"].copy()
        competition = arguments.get("competition", "")
        season = arguments.get("season")

        if competition:
            df = _filter_competition(df, competition)
        if season and "season" in df.columns:
            df = df[df["season"] == int(season)]

        df = df.dropna(subset=["home_goal", "away_goal"])
        if df.empty:
            return [TextContent(type="text", text="No data found.")]

        total_matches = len(df)
        total_goals = (df["home_goal"] + df["away_goal"]).sum()
        avg = total_goals / total_matches if total_matches else 0
        home_wins = (df["home_goal"] > df["away_goal"]).sum()
        draws = (df["home_goal"] == df["away_goal"]).sum()
        away_wins = (df["home_goal"] < df["away_goal"]).sum()

        label = competition or "All competitions"
        s_label = f" ({season})" if season else ""
        lines = [
            f"Goal statistics - {label}{s_label}:",
            f"  Total matches: {total_matches}",
            f"  Total goals: {int(total_goals)}",
            f"  Average goals/match: {avg:.2f}",
            f"  Home wins: {home_wins} ({home_wins/total_matches*100:.1f}%)",
            f"  Draws: {draws} ({draws/total_matches*100:.1f}%)",
            f"  Away wins: {away_wins} ({away_wins/total_matches*100:.1f}%)",
        ]
        return [TextContent(type="text", text="\n".join(lines))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
