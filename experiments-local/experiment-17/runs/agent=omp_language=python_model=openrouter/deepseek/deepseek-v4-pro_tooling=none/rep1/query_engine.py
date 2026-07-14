"""
Brazilian Soccer MCP Server - Query Engine
==========================================
Core query logic for searching matches, teams, players, competitions,
and calculating statistics. All queries operate on pre-loaded pandas
DataFrames for performance.

Design:
  - All query functions accept pre-loaded data (no I/O inside queries).
  - Team name matching uses fuzzy_match_team from data_loader.
  - Results are returned as formatted strings suitable for MCP tool responses.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from data_loader import (
    fuzzy_match_team,
    get_all_team_names,
    load_all_match_data,
    load_fifa_players,
)


# ── Match Queries ───────────────────────────────────────────────────────────


def search_matches(
    matches_df: pd.DataFrame,
    *,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> str:
    """Search matches by team, opponent, competition, season, and date range."""
    df = matches_df.copy()

    all_teams = get_all_team_names(matches_df)

    if team:
        team_canon = fuzzy_match_team(team, all_teams)
        if team_canon is None:
            return f"Team '{team}' not found in dataset."
        mask = (df["home_team_norm"] == team_canon) | (df["away_team_norm"] == team_canon)
        df = df[mask]
        if opponent is None:
            opponent_filter = None
        else:
            opp_canon = fuzzy_match_team(opponent, all_teams)
            if opp_canon is None:
                return f"Opponent '{opponent}' not found in dataset."
            mask_opp = (df["home_team_norm"] == opp_canon) | (df["away_team_norm"] == opp_canon)
            df = df[mask_opp]

    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    if season is not None:
        df = df[df["season"] == season]

    if start_date:
        start = pd.to_datetime(start_date)
        df = df[df["date"] >= start]
    if end_date:
        end = pd.to_datetime(end_date)
        df = df[df["date"] <= end]

    df = df.sort_values("date", ascending=False, na_position="last")

    if df.empty:
        return "No matches found matching the criteria."

    result_lines = [f"Found {len(df)} match(es):"]
    for _, row in df.head(limit).iterrows():
        date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "unknown date"
        comp = row.get("competition", "unknown")
        home = row.get("home_team_norm", "unknown")
        away = row.get("away_team_norm", "unknown")
        hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else 0
        ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else 0
        extra = ""
        if "round" in row.index and pd.notna(row["round"]):
            extra = f" - Round {int(row['round'])}"
        elif "stage" in row.index and pd.notna(row["stage"]):
            extra = f" - {row['stage']}"
        result_lines.append(f"  {date_str}: {home} {hg}-{ag} {away} ({comp}{extra})")

    if len(df) > limit:
        result_lines.append(f"  ... and {len(df) - limit} more matches.")

    return "\n".join(result_lines)


def get_head_to_head(
    matches_df: pd.DataFrame,
    team1: str,
    team2: str,
) -> str:
    """Compare two teams head-to-head."""
    all_teams = get_all_team_names(matches_df)
    t1 = fuzzy_match_team(team1, all_teams)
    t2 = fuzzy_match_team(team2, all_teams)

    if t1 is None:
        return f"Team '{team1}' not found in dataset."
    if t2 is None:
        return f"Team '{team2}' not found in dataset."

    mask = (
        ((matches_df["home_team_norm"] == t1) & (matches_df["away_team_norm"] == t2))
        | ((matches_df["home_team_norm"] == t2) & (matches_df["away_team_norm"] == t1))
    )
    h2h = matches_df[mask].sort_values("date", ascending=False, na_position="last")

    if h2h.empty:
        return f"No matches found between {t1} and {t2}."

    t1_wins = 0
    t2_wins = 0
    draws = 0
    t1_goals = 0
    t2_goals = 0

    for _, row in h2h.iterrows():
        if row["home_team_norm"] == t1:
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
        else:
            ag, hg = int(row["home_goal"]), int(row["away_goal"])
        t1_goals += hg
        t2_goals += ag
        if hg > ag:
            t1_wins += 1
        elif ag > hg:
            t2_wins += 1
        else:
            draws += 1

    lines = [
        f"Head-to-head: {t1} vs {t2}",
        f"Total matches: {len(h2h)}",
        f"{t1}: {t1_wins} wins, {t2}: {t2_wins} wins, {draws} draws",
        f"Goals: {t1} {t1_goals} - {t2_goals} {t2}",
        "",
        "Recent matches:",
    ]
    for _, row in h2h.head(20).iterrows():
        date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "unknown"
        comp = row.get("competition", "unknown")
        if row["home_team_norm"] == t1:
            lines.append(f"  {date_str}: {t1} {int(row['home_goal'])}-{int(row['away_goal'])} {t2} ({comp})")
        else:
            lines.append(f"  {date_str}: {t2} {int(row['home_goal'])}-{int(row['away_goal'])} {t1} ({comp})")

    return "\n".join(lines)


def get_biggest_wins(
    matches_df: pd.DataFrame,
    competition: str | None = None,
    limit: int = 20,
) -> str:
    """Get the biggest victories in the dataset."""
    df = matches_df.copy()

    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    df["goal_diff"] = (df["home_goal"] - df["away_goal"]).abs()
    biggest = df.nlargest(limit, "goal_diff")

    if biggest.empty:
        return "No matches found."

    lines = ["Biggest victories:"]
    for i, (_, row) in enumerate(biggest.iterrows(), 1):
        date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "unknown"
        comp = row.get("competition", "unknown")
        home = row.get("home_team_norm", "unknown")
        away = row.get("away_team_norm", "unknown")
        hg = int(row["home_goal"])
        ag = int(row["away_goal"])
        winner = home if hg > ag else away
        lines.append(f"  {i}. {date_str}: {home} {hg}-{ag} {away} ({comp}) - {winner} won by {abs(hg - ag)}")

    return "\n".join(lines)


# ── Team Queries ────────────────────────────────────────────────────────────


def get_team_stats(
    matches_df: pd.DataFrame,
    team: str,
    season: int | None = None,
    competition: str | None = None,
) -> str:
    """Get team statistics: wins, losses, draws, goals, home/away records."""
    all_teams = get_all_team_names(matches_df)
    t = fuzzy_match_team(team, all_teams)
    if t is None:
        return f"Team '{team}' not found in dataset."

    mask = (matches_df["home_team_norm"] == t) | (matches_df["away_team_norm"] == t)
    df = matches_df[mask]

    if season is not None:
        df = df[df["season"] == season]
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

    if df.empty:
        return f"No matches found for {t} with the given criteria."

    total = len(df)
    wins = 0
    losses = 0
    draws = 0
    gf = 0
    ga = 0
    home_wins = home_losses = home_draws = home_gf = home_ga = 0
    away_wins = away_losses = away_draws = away_gf = away_ga = 0

    for _, row in df.iterrows():
        is_home = row["home_team_norm"] == t
        hg = int(row["home_goal"])
        ag = int(row["away_goal"])

        if is_home:
            my_goals, opp_goals = hg, ag
            home_gf += hg
            home_ga += ag
        else:
            my_goals, opp_goals = ag, hg
            away_gf += ag
            away_ga += hg

        gf += my_goals
        ga += opp_goals

        if my_goals > opp_goals:
            wins += 1
            if is_home:
                home_wins += 1
            else:
                away_wins += 1
        elif opp_goals > my_goals:
            losses += 1
            if is_home:
                home_losses += 1
            else:
                away_losses += 1
        else:
            draws += 1
            if is_home:
                home_draws += 1
            else:
                away_draws += 1

    home_matches = home_wins + home_losses + home_draws
    away_matches = away_wins + away_losses + away_draws
    win_pct = (wins / total * 100) if total > 0 else 0

    context_parts = []
    if season:
        context_parts.append(str(season))
    if competition:
        context_parts.append(competition)
    context = f" ({' '.join(context_parts)})" if context_parts else ""

    lines = [
        f"{t} Statistics{context}:",
        f"  Matches: {total}",
        f"  Record: {wins}W, {draws}D, {losses}L",
        f"  Win rate: {win_pct:.1f}%",
        f"  Goals For: {gf}, Goals Against: {ga} (GD: {gf - ga:+d})",
        "",
    ]
    if home_matches > 0:
        home_pct = (home_wins / home_matches * 100) if home_matches > 0 else 0
        lines.append(f"  Home record ({home_matches} matches): {home_wins}W, {home_draws}D, {home_losses}L ({home_pct:.1f}%)")
        lines.append(f"    Goals: {home_gf} for, {home_ga} against")
    if away_matches > 0:
        away_pct = (away_wins / away_matches * 100) if away_matches > 0 else 0
        lines.append(f"  Away record ({away_matches} matches): {away_wins}W, {away_draws}D, {away_losses}L ({away_pct:.1f}%)")
        lines.append(f"    Goals: {away_gf} for, {away_ga} against")

    return "\n".join(lines)


def get_highest_scoring_teams(
    matches_df: pd.DataFrame,
    competition: str | None = None,
    season: int | None = None,
    top_n: int = 10,
) -> str:
    """Find teams with the most goals scored."""
    df = matches_df.copy()
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season is not None:
        df = df[df["season"] == season]

    if df.empty:
        return "No data matching the criteria."

    # Aggregate goals by team
    goals: dict[str, int] = {}
    for _, row in df.iterrows():
        home = row.get("home_team_norm", "")
        away = row.get("away_team_norm", "")
        hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else 0
        ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else 0
        if home:
            goals[home] = goals.get(home, 0) + hg
        if away:
            goals[away] = goals.get(away, 0) + ag

    sorted_teams = sorted(goals.items(), key=lambda x: x[1], reverse=True)[:top_n]

    context_parts = []
    if competition:
        context_parts.append(competition)
    if season:
        context_parts.append(str(season))
    context = f" ({' '.join(context_parts)})" if context_parts else ""

    lines = [f"Top scoring teams{context}:"]
    for i, (team, g) in enumerate(sorted_teams, 1):
        lines.append(f"  {i}. {team}: {g} goals")

    return "\n".join(lines)


# ── Player Queries ──────────────────────────────────────────────────────────


def search_players(
    players_df: pd.DataFrame,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 20,
) -> str:
    """Search FIFA player database by name, nationality, club, position, and rating."""
    df = players_df.copy()

    if name:
        df = df[df["Name"].str.contains(name, case=False, na=False)]
    if nationality:
        df = df[df["Nationality"].str.contains(nationality, case=False, na=False)]
    if club:
        df = df[df["Club"].str.contains(club, case=False, na=False)]
    if position:
        # Position field can contain multiple positions like "LW,ST"
        df = df[df["Position"].str.contains(position, case=False, na=False)]
    if min_overall is not None:
        df = df[df["Overall"] >= min_overall]
    if max_overall is not None:
        df = df[df["Overall"] <= max_overall]

    df = df.sort_values("Overall", ascending=False)

    if df.empty:
        return "No players found matching the criteria."

    lines = [f"Found {len(df)} player(s):"]
    for _, row in df.head(limit).iterrows():
        name_val = row["Name"]
        ovr = int(row["Overall"])
        pot = int(row["Potential"]) if pd.notna(row["Potential"]) else 0
        pos = row["Position"]
        club_val = row["Club"]
        nat = row["Nationality"]
        age = int(row["Age"]) if pd.notna(row["Age"]) else 0
        lines.append(f"  {name_val} - Overall: {ovr}, Potential: {pot}, Position: {pos}, Club: {club_val}, Nation: {nat}, Age: {age}")

    if len(df) > limit:
        lines.append(f"  ... and {len(df) - limit} more players.")

    return "\n".join(lines)


def get_top_brazilian_players(
    players_df: pd.DataFrame,
    limit: int = 20,
) -> str:
    """Get the highest-rated Brazilian players."""
    return search_players(players_df, nationality="Brazil", limit=limit)


def get_players_by_club(
    players_df: pd.DataFrame,
    club: str,
    limit: int = 30,
) -> str:
    """Get players for a specific club, sorted by rating."""
    return search_players(players_df, club=club, limit=limit)


# ── Competition Queries ─────────────────────────────────────────────────────


def get_standings(
    matches_df: pd.DataFrame,
    competition: str = "Brasileirão",
    season: int | None = None,
) -> str:
    """Calculate league standings from match results.

    Uses the standard 3-1-0 points system.
    """
    df = matches_df[matches_df["competition"].str.lower().str.contains(competition.lower(), na=False)].copy()
    if season is not None:
        df = df[df["season"] == season]

    if df.empty:
        return "No data found for the given competition/season."

    # Calculate standings
    teams: dict[str, dict[str, int]] = {}
    for _, row in df.iterrows():
        home = row["home_team_norm"]
        away = row["away_team_norm"]
        hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else 0
        ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else 0

        for team in (home, away):
            if team and team not in teams:
                teams[team] = {"pts": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "mp": 0}

        if home in teams:
            teams[home]["mp"] += 1
            teams[home]["gf"] += hg
            teams[home]["ga"] += ag
        if away in teams:
            teams[away]["mp"] += 1
            teams[away]["gf"] += ag
            teams[away]["ga"] += hg

        if hg > ag:
            if home in teams:
                teams[home]["pts"] += 3
                teams[home]["w"] += 1
            if away in teams:
                teams[away]["l"] += 1
        elif ag > hg:
            if away in teams:
                teams[away]["pts"] += 3
                teams[away]["w"] += 1
            if home in teams:
                teams[home]["l"] += 1
        else:
            if home in teams:
                teams[home]["pts"] += 1
                teams[home]["d"] += 1
            if away in teams:
                teams[away]["pts"] += 1
                teams[away]["d"] += 1

    # Sort by points, then goal difference, then goals for
    ranked = sorted(
        teams.items(),
        key=lambda x: (x[1]["pts"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
        reverse=True,
    )

    actual_season = season or "all seasons"
    lines = [f"{competition} Standings ({actual_season}):"]
    for i, (team, stats) in enumerate(ranked[:30], 1):
        gd = stats["gf"] - stats["ga"]
        gd_str = f"+{gd}" if gd > 0 else str(gd)
        lines.append(
            f"  {i:2d}. {team:<25s} {stats['pts']:3d} pts  "
            f"{stats['w']:2d}W {stats['d']:2d}D {stats['l']:2d}L  "
            f"GF:{stats['gf']:3d} GA:{stats['ga']:3d} GD:{gd_str:>4s}"
        )

    return "\n".join(lines)


def get_season_summary(
    matches_df: pd.DataFrame,
    competition: str = "Brasileirão",
    season: int | None = None,
) -> str:
    """Get a summary of a competition season including champion and statistics."""
    df = matches_df[matches_df["competition"].str.lower().str.contains(competition.lower(), na=False)].copy()

    if df.empty:
        return f"No data found for {competition}."

    actual_season = season or "all seasons"
    if season is not None:
        df = df[df["season"] == season]

    if df.empty:
        return f"No data found for {competition} season {season}."

    total_matches = len(df)
    total_goals = int(df["home_goal"].sum()) + int(df["away_goal"].sum())
    avg_goals = total_goals / total_matches if total_matches > 0 else 0
    home_wins = int(((df["home_goal"] > df["away_goal"]).sum()))
    away_wins = int(((df["away_goal"] > df["home_goal"]).sum()))
    draws = int(((df["home_goal"] == df["away_goal"]).sum()))
    home_win_pct = home_wins / total_matches * 100 if total_matches > 0 else 0

    # Calculate champion if league
    standings_text = get_standings(matches_df, competition, season)
    first_line = standings_text.split("\n")[1] if "\n" in standings_text else ""

    lines = [
        f"{competition} Summary ({actual_season}):",
        f"  Total matches: {total_matches}",
        f"  Total goals: {total_goals}",
        f"  Average goals per match: {avg_goals:.2f}",
        f"  Home wins: {home_wins} ({home_win_pct:.1f}%)",
        f"  Away wins: {away_wins} ({(away_wins/total_matches*100):.1f}%)",
        f"  Draws: {draws} ({(draws/total_matches*100):.1f}%)",
        "",
        "Standings (top 5):",
    ]
    for line in standings_text.split("\n")[1:6]:
        lines.append(line)

    return "\n".join(lines)


# ── Statistical Queries ─────────────────────────────────────────────────────


def get_average_goals(
    matches_df: pd.DataFrame,
    competition: str | None = None,
    season: int | None = None,
) -> str:
    """Calculate average goals per match."""
    df = matches_df.copy()
    if competition:
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
    if season is not None:
        df = df[df["season"] == season]

    if df.empty:
        return "No data matching the criteria."

    total = len(df)
    goals = int(df["home_goal"].sum()) + int(df["away_goal"].sum())
    avg = goals / total if total > 0 else 0

    home_wins = int((df["home_goal"] > df["away_goal"]).sum())
    away_wins = int((df["away_goal"] > df["home_goal"]).sum())
    draws = int((df["home_goal"] == df["away_goal"]).sum())

    context = ""
    if competition:
        context += f" {competition}"
    if season:
        context += f" {season}"

    lines = [
        f"Match statistics{context}:",
        f"  Total matches: {total}",
        f"  Total goals: {goals}",
        f"  Average goals per match: {avg:.2f}",
        f"  Home win rate: {home_wins/total*100:.1f}% ({home_wins} matches)",
        f"  Away win rate: {away_wins/total*100:.1f}% ({away_wins} matches)",
        f"  Draw rate: {draws/total*100:.1f}% ({draws} matches)",
    ]
    return "\n".join(lines)


def get_team_performance_trend(
    matches_df: pd.DataFrame,
    team: str,
    competition: str = "Brasileirão",
) -> str:
    """Show a team's performance by season."""
    all_teams = get_all_team_names(matches_df)
    t = fuzzy_match_team(team, all_teams)
    if t is None:
        return f"Team '{team}' not found in dataset."

    df = matches_df[
        matches_df["competition"].str.lower().str.contains(competition.lower(), na=False)
    ].copy()

    mask = (df["home_team_norm"] == t) | (df["away_team_norm"] == t)
    df = df[mask]

    if df.empty:
        return f"No {competition} data found for {t}."

    seasons = sorted(df["season"].dropna().unique())

    lines = [f"{t} performance in {competition}:"]
    for season in seasons:
        s_df = df[df["season"] == season]
        wins = losses = draws = gf = ga = 0
        for _, row in s_df.iterrows():
            is_home = row["home_team_norm"] == t
            hg = int(row["home_goal"])
            ag = int(row["away_goal"])
            my_goals = hg if is_home else ag
            opp_goals = ag if is_home else hg
            gf += my_goals
            ga += opp_goals
            if my_goals > opp_goals:
                wins += 1
            elif opp_goals > my_goals:
                losses += 1
            else:
                draws += 1
        pts = wins * 3 + draws
        lines.append(
            f"  {int(season)}: {wins}W {draws}D {losses}L, {pts} pts, GF:{gf} GA:{ga}"
        )

    return "\n".join(lines)


# ── Data Summary ────────────────────────────────────────────────────────────


def get_data_summary(matches_df: pd.DataFrame, players_df: pd.DataFrame) -> str:
    """Get a summary of the loaded datasets."""
    competitions = matches_df["competition"].dropna().unique()
    seasons = sorted(matches_df["season"].dropna().unique())
    teams = get_all_team_names(matches_df)

    # Count Brazilian players
    brazilian_players = int((players_df["Nationality"].str.lower() == "brazil").sum())
    total_players = len(players_df)

    lines = [
        "Brazilian Soccer Database Summary:",
        "",
        "Match Data:",
        f"  Total matches: {len(matches_df):,}",
        f"  Competitions: {', '.join(sorted(competitions))}",
        f"  Seasons: {int(seasons[0])} to {int(seasons[-1])} ({len(seasons)} seasons)",
        f"  Teams: {len(teams)}",
        "",
        "Player Data:",
        f"  Total players: {total_players:,}",
        f"  Brazilian players: {brazilian_players:,}",
        f"  Clubs represented: {players_df['Club'].nunique():,}",
        f"  Nationalities: {players_df['Nationality'].nunique():,}",
    ]
    return "\n".join(lines)