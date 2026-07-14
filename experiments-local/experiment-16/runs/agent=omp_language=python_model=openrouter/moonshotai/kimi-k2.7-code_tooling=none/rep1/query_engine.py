"""
Query engine for Brazilian Soccer MCP Server.

Provides a high-level API over the loaded match/player DataFrames.  Each function
returns plain Python structures that the MCP server serializes into
human-friendly text.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from data_loader import load_matches, load_players, resolve_competition, resolve_team_name

_COLUMNS_TO_KEEP = [
    "match_id", "competition", "season", "round", "stage",
    "date", "home_team_display", "away_team_display",
    "home_team_state", "away_team_state",
    "home_goal", "away_goal",
]


def _matches_df() -> pd.DataFrame:
    """Lazy singleton for the unified match DataFrame."""
    if not hasattr(_matches_df, "_cache"):
        _matches_df._cache = load_matches()
    return _matches_df._cache


def _players_df() -> pd.DataFrame:
    """Lazy singleton for the player DataFrame."""
    if not hasattr(_players_df, "_cache"):
        _players_df._cache = load_players()
    return _players_df._cache


def _format_match(row: pd.Series) -> dict[str, Any]:
    """Convert a match row into a stable dictionary."""
    date_str = pd.to_datetime(row["date"]).strftime("%Y-%m-%d") if pd.notna(row["date"]) else "unknown"
    competition = row["competition"]
    detail_parts = [competition]
    rnd = row.get("round")
    stage = row.get("stage")
    if pd.notna(rnd) and str(rnd).strip():
        detail_parts.append(f"Round {rnd}")
    elif pd.notna(stage) and str(stage).strip():
        detail_parts.append(str(stage))
    return {
        "date": date_str,
        "home_team": row["home_team_display"],
        "away_team": row["away_team_display"],
        "home_goal": int(row["home_goal"]) if pd.notna(row["home_goal"]) else None,
        "away_goal": int(row["away_goal"]) if pd.notna(row["away_goal"]) else None,
        "competition": competition,
        "detail": " ".join(detail_parts[1:]) if len(detail_parts) > 1 else "",
        "goal_difference": abs(int(row["home_goal"]) - int(row["away_goal"]))
        if pd.notna(row["home_goal"]) and pd.notna(row["away_goal"]) else 0,
    }


def _filter_matches(
    df: pd.DataFrame,
    *,
    team_key: str | None = None,
    opponent_key: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str | None = None,
) -> pd.DataFrame:
    """Apply common match filters."""
    mask = pd.Series(True, index=df.index)

    if competition:
        mask &= df["competition"] == competition

    if season is not None:
        mask &= df["season"] == season

    if date_from:
        mask &= df["date"] >= pd.Timestamp(date_from)
    if date_to:
        mask &= df["date"] <= pd.Timestamp(date_to)

    if team_key and opponent_key:
        pair_mask = (
            ((df["home_team_key"] == team_key) & (df["away_team_key"] == opponent_key))
            | ((df["home_team_key"] == opponent_key) & (df["away_team_key"] == team_key))
        )
        mask &= pair_mask
    elif team_key:
        if venue == "home":
            mask &= df["home_team_key"] == team_key
        elif venue == "away":
            mask &= df["away_team_key"] == team_key
        else:
            mask &= (df["home_team_key"] == team_key) | (df["away_team_key"] == team_key)

    return df[mask].copy()


def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Find matches matching the supplied criteria.

    Args:
        team: Team name (resolved against normalized names).
        opponent: Optional second team for head-to-head filtering.
        competition: Competition name or alias.
        season: Season year.
        date_from/date_to: ISO date bounds.
        venue: "home", "away", or None for both.
        limit: Maximum number of matches to return.
    """
    df = _matches_df()
    comp = resolve_competition(competition)
    if comp and len(comp) == 1:
        comp_value = comp[0]
    elif competition is not None:
        return {
            "matches": [],
            "count": 0,
            "message": f"Could not resolve competition: {competition}",
        }
    else:
        comp_value = None

    team_key = resolve_team_name(team, df) if team else None
    opponent_key = resolve_team_name(opponent, df) if opponent else None

    if team and team_key is None:
        return {"matches": [], "count": 0, "message": f"Could not resolve team: {team}"}
    if opponent and opponent_key is None:
        return {"matches": [], "count": 0, "message": f"Could not resolve team: {opponent}"}

    filtered = _filter_matches(
        df,
        team_key=team_key,
        opponent_key=opponent_key,
        competition=comp_value,
        season=season,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
    )

    matches = [_format_match(row) for _, row in filtered.head(limit).iterrows()]
    return {
        "matches": matches,
        "count": int(len(filtered)),
        "team_resolved": team_key,
        "opponent_resolved": opponent_key,
    }


def _team_record(df: pd.DataFrame, team_key: str, venue: str | None = None) -> dict[str, Any]:
    """Compute win/draw/loss record from a filtered DataFrame."""
    home = df[df["home_team_key"] == team_key].copy() if venue in (None, "home") else pd.DataFrame()
    away = df[df["away_team_key"] == team_key].copy() if venue in (None, "away") else pd.DataFrame()

    wins = 0
    draws = 0
    losses = 0
    gf = 0
    ga = 0

    for _, row in home.iterrows():
        if pd.isna(row["home_goal"]) or pd.isna(row["away_goal"]):
            continue
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        gf += hg
        ga += ag
        if hg > ag:
            wins += 1
        elif hg == ag:
            draws += 1
        else:
            losses += 1

    for _, row in away.iterrows():
        if pd.isna(row["home_goal"]) or pd.isna(row["away_goal"]):
            continue
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        gf += ag
        ga += hg
        if ag > hg:
            wins += 1
        elif ag == hg:
            draws += 1
        else:
            losses += 1

    total = wins + draws + losses
    return {
        "matches": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "win_rate": round(wins / total * 100, 1) if total else 0.0,
    }


def get_team_stats(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> dict[str, Any]:
    """Return aggregate statistics for a single team."""
    df = _matches_df()
    team_key = resolve_team_name(team, df)
    if team_key is None:
        return {"error": f"Could not resolve team: {team}"}

    comp = resolve_competition(competition)
    comp_value = comp[0] if comp and len(comp) == 1 else None

    filtered = _filter_matches(df, team_key=team_key, competition=comp_value, season=season, venue=venue)
    record = _team_record(filtered, team_key, venue=venue)

    display_names = pd.concat([df.loc[df["home_team_key"] == team_key, "home_team_display"],
                               df.loc[df["away_team_key"] == team_key, "away_team_display"]])
    display_name = display_names.value_counts().index[0] if len(display_names) else team

    return {
        "team": display_name,
        "team_key": team_key,
        "competition": competition,
        "season": season,
        "venue": venue or "all",
        **record,
    }


def get_head_to_head(team1: str, team2: str, competition: str | None = None, season: int | None = None) -> dict[str, Any]:
    """Return all matches between two teams plus a summary record."""
    df = _matches_df()
    key1 = resolve_team_name(team1, df)
    key2 = resolve_team_name(team2, df)
    if key1 is None:
        return {"error": f"Could not resolve team: {team1}"}
    if key2 is None:
        return {"error": f"Could not resolve team: {team2}"}

    comp = resolve_competition(competition)
    comp_value = comp[0] if comp and len(comp) == 1 else None

    filtered = _filter_matches(df, team_key=key1, opponent_key=key2, competition=comp_value, season=season)
    matches = [_format_match(row) for _, row in filtered.iterrows()]

    wins1 = draws = wins2 = 0
    for m in matches:
        if m["home_goal"] is None or m["away_goal"] is None:
            continue
        home_won = m["home_goal"] > m["away_goal"]
        away_won = m["away_goal"] > m["home_goal"]
        if home_won:
            if normalize_team_name(m["home_team"]) == key1:
                wins1 += 1
            else:
                wins2 += 1
        elif away_won:
            if normalize_team_name(m["away_team"]) == key1:
                wins1 += 1
            else:
                wins2 += 1
        else:
            draws += 1

    display1 = _display_for_key(df, key1)
    display2 = _display_for_key(df, key2)

    return {
        "team1": display1,
        "team2": display2,
        "matches": matches,
        "summary": {
            f"{display1}_wins": wins1,
            f"{display2}_wins": wins2,
            "draws": draws,
            "total": len(matches),
        },
    }


def _display_for_key(df: pd.DataFrame, team_key: str) -> str:
    """Return the most common display name for a canonical team key."""
    names = pd.concat([
        df.loc[df["home_team_key"] == team_key, "home_team_display"],
        df.loc[df["away_team_key"] == team_key, "away_team_display"],
    ])
    return names.value_counts().index[0] if len(names) else team_key


def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search the FIFA player dataset."""
    df = _players_df()
    mask = pd.Series(True, index=df.index)

    if name:
        name_key = name.lower()
        mask &= df["name_key"].str.contains(name_key, na=False)
    if nationality:
        nat_key = nationality.lower()
        mask &= df["nationality_key"].str.contains(nat_key, na=False)
    if club:
        club_key = club.lower()
        mask &= df["club_key"].str.contains(club_key, na=False)
    if position:
        mask &= df["position"].str.contains(position, na=False, case=False)
    if min_overall is not None:
        mask &= df["overall"] >= min_overall

    filtered = df[mask].sort_values("overall", ascending=False, na_position="last").head(limit)
    players = [
        {
            "id": int(row["player_id"]) if pd.notna(row["player_id"]) else None,
            "name": row["name"],
            "age": int(row["age"]) if pd.notna(row["age"]) else None,
            "nationality": row["nationality"],
            "overall": int(row["overall"]) if pd.notna(row["overall"]) else None,
            "potential": int(row["potential"]) if pd.notna(row["potential"]) else None,
            "club": row["club"] if pd.notna(row["club"]) else None,
            "position": row["position"],
            "jersey_number": row["jersey_number"],
        }
        for _, row in filtered.iterrows()
    ]
    return {"players": players, "count": int(len(filtered))}


def get_standings(competition: str, season: int) -> dict[str, Any]:
    """Compute league standings from match results."""
    df = _matches_df()
    comp = resolve_competition(competition)
    comp_value = comp[0] if comp and len(comp) == 1 else competition

    filtered = _filter_matches(df, competition=comp_value, season=season)
    if filtered.empty:
        return {"standings": [], "message": f"No matches found for {competition} {season}"}

    records: dict[str, dict[str, Any]] = {}

    def ensure(team_key: str):
        if team_key not in records:
            records[team_key] = {
                "team": _display_for_key(df, team_key),
                "played": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "points": 0,
            }

    for _, row in filtered.iterrows():
        if pd.isna(row["home_goal"]) or pd.isna(row["away_goal"]):
            continue
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        hk, ak = row["home_team_key"], row["away_team_key"]
        ensure(hk)
        ensure(ak)
        records[hk]["played"] += 1
        records[ak]["played"] += 1
        records[hk]["goals_for"] += hg
        records[hk]["goals_against"] += ag
        records[ak]["goals_for"] += ag
        records[ak]["goals_against"] += hg
        if hg > ag:
            records[hk]["wins"] += 1
            records[hk]["points"] += 3
            records[ak]["losses"] += 1
        elif ag > hg:
            records[ak]["wins"] += 1
            records[ak]["points"] += 3
            records[hk]["losses"] += 1
        else:
            records[hk]["draws"] += 1
            records[ak]["draws"] += 1
            records[hk]["points"] += 1
            records[ak]["points"] += 1

    for team_key, row in records.items():
        row["goal_difference"] = row["goals_for"] - row["goals_against"]

    standings = sorted(
        records.values(),
        key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]),
        reverse=True,
    )
    for idx, row in enumerate(standings, start=1):
        row["position"] = idx

    return {"competition": comp_value, "season": season, "standings": standings}


def get_biggest_wins(competition: str | None = None, season: int | None = None, limit: int = 10) -> dict[str, Any]:
    """Return the matches with the largest goal difference."""
    df = _matches_df()
    comp = resolve_competition(competition)
    comp_value = comp[0] if comp and len(comp) == 1 else None

    filtered = _filter_matches(df, competition=comp_value, season=season)
    filtered = filtered.dropna(subset=["home_goal", "away_goal"])
    filtered["goal_difference"] = (filtered["home_goal"] - filtered["away_goal"]).abs()
    filtered = filtered.sort_values("goal_difference", ascending=False).head(limit)

    return {
        "matches": [_format_match(row) for _, row in filtered.iterrows()],
        "count": int(len(filtered)),
    }


def get_goals_per_match(competition: str | None = None, season: int | None = None) -> dict[str, Any]:
    """Return average total goals per match."""
    df = _matches_df()
    comp = resolve_competition(competition)
    comp_value = comp[0] if comp and len(comp) == 1 else None

    filtered = _filter_matches(df, competition=comp_value, season=season)
    filtered = filtered.dropna(subset=["home_goal", "away_goal"])
    total_goals = float(filtered["home_goal"].sum() + filtered["away_goal"].sum())
    total_matches = int(len(filtered))
    avg = round(total_goals / total_matches, 2) if total_matches else 0.0

    home_wins = int((filtered["home_goal"] > filtered["away_goal"]).sum())
    draws = int((filtered["home_goal"] == filtered["away_goal"]).sum())
    away_wins = int((filtered["home_goal"] < filtered["away_goal"]).sum())

    return {
        "average_goals_per_match": avg,
        "total_matches": total_matches,
        "total_goals": int(total_goals),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
    }


def get_top_scoring_teams(competition: str | None = None, season: int | None = None, limit: int = 10) -> dict[str, Any]:
    """Return teams ranked by total goals scored across all matches."""
    df = _matches_df()
    comp = resolve_competition(competition)
    comp_value = comp[0] if comp and len(comp) == 1 else None

    filtered = _filter_matches(df, competition=comp_value, season=season)
    filtered = filtered.dropna(subset=["home_goal", "away_goal"])

    home = filtered.groupby("home_team_key")[["home_team_display", "home_goal"]].agg(
        {"home_team_display": "first", "home_goal": "sum"}
    ).rename(columns={"home_team_display": "team", "home_goal": "goals"})

    away = filtered.groupby("away_team_key")[["away_team_display", "away_goal"]].agg(
        {"away_team_display": "first", "away_goal": "sum"}
    ).rename(columns={"away_team_display": "team", "away_goal": "goals"})

    combined = pd.concat([home, away]).reset_index(drop=True)
    totals = combined.groupby("team")["goals"].sum().sort_values(ascending=False).head(limit)

    return {
        "teams": [{"team": team, "goals": int(goals)} for team, goals in totals.items()],
        "count": int(len(totals)),
    }


def get_relegated_teams(season: int) -> dict[str, Any]:
    """Return the bottom four teams of a Brasileirão season."""
    standings = get_standings("Brasileirão", season)
    if not standings["standings"]:
        return {"message": f"No Brasileirão data for season {season}"}
    bottom = standings["standings"][-4:]
    return {
        "season": season,
        "relegated": [team["team"] for team in bottom],
        "positions": [team["position"] for team in bottom],
    }


# Re-import helper used by head-to-head result attribution.
from data_loader import normalize_team_name
