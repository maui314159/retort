"""
query_engine.py
===============

High-level query API over the loaded match and player DataFrames.

Every public function in this module returns a plain Python ``dict`` (or
list of dicts) that the MCP server can serialize to JSON or render as
human-readable text.  Functions are intentionally side-effect free so they
are safe to call concurrently and easy to unit-test.

The module exposes query functions for:

* **Matches** — find matches by team, opponent, competition, season, or
  date range.
* **Teams** — per-team statistics and head-to-head comparisons.
* **Players** — search the FIFA dataset by name, club, nationality, etc.
* **Competitions** — calculate league standings, top scorers, and
  identify relegated teams.
* **Statistics** — average goals per match, biggest wins, home/away
  splits.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from data_loader import (
    display_name_for_key,
    load_matches,
    load_players,
    normalize_team_name,
    resolve_competition,
    resolve_team_name,
)

# Columns that ``search_matches`` will return to callers.
MATCH_OUTPUT_COLUMNS: tuple[str, ...] = (
    "match_id",
    "competition",
    "season",
    "round",
    "stage",
    "date",
    "home_team_display",
    "away_team_display",
    "home_team_state",
    "away_team_state",
    "home_goal",
    "away_goal",
)

# ---------------------------------------------------------------------------
# Cached DataFrame accessors
# ---------------------------------------------------------------------------


def _matches_df() -> pd.DataFrame:
    """Return the unified match DataFrame (cached)."""
    return load_matches()


def _players_df() -> pd.DataFrame:
    """Return the FIFA player DataFrame (cached)."""
    return load_players()


# ---------------------------------------------------------------------------
# Match helpers
# ---------------------------------------------------------------------------

def _format_match(row: pd.Series) -> dict[str, Any]:
    """Convert a match row into a stable dictionary for serialization."""
    if pd.notna(row.get("date")):
        date_str = pd.to_datetime(row["date"]).strftime("%Y-%m-%d")
    else:
        date_str = ""

    competition = row.get("competition", "")
    rnd = row.get("round")
    stage = row.get("stage")
    detail_parts: list[str] = []
    if pd.notna(rnd) and str(rnd).strip() and str(rnd).strip().lower() != "nan":
        detail_parts.append(f"Round {rnd}")
    if pd.notna(stage) and str(stage).strip() and str(stage).strip().lower() != "nan":
        detail_parts.append(str(stage))

    home_goal = row.get("home_goal")
    away_goal = row.get("away_goal")
    goal_diff: int | None = None
    if pd.notna(home_goal) and pd.notna(away_goal):
        goal_diff = abs(int(home_goal) - int(away_goal))

    return {
        "match_id": row.get("match_id"),
        "date": date_str,
        "competition": competition,
        "season": int(row["season"]) if pd.notna(row.get("season")) else None,
        "round": int(rnd) if pd.notna(rnd) and str(rnd).strip() else None,
        "stage": str(stage) if pd.notna(stage) and str(stage).strip() else None,
        "home_team": row.get("home_team_display", ""),
        "away_team": row.get("away_team_display", ""),
        "home_team_state": row.get("home_team_state"),
        "away_team_state": row.get("away_team_state"),
        "home_goal": int(home_goal) if pd.notna(home_goal) else None,
        "away_goal": int(away_goal) if pd.notna(away_goal) else None,
        "goal_difference": goal_diff,
        "detail": " ".join(detail_parts),
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
    """Apply the common match filters used across query functions."""
    mask = pd.Series(True, index=df.index)

    if competition:
        mask &= df["competition"] == competition
    if season is not None:
        mask &= df["season"] == season
    if date_from:
        mask &= df["date"] >= pd.to_datetime(date_from, errors="coerce")
    if date_to:
        mask &= df["date"] <= pd.to_datetime(date_to, errors="coerce")

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


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------

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
    """Return matches matching the supplied criteria."""
    df = _matches_df()

    competition_value: str | None = None
    if competition:
        resolved = resolve_competition(competition)
        if resolved:
            competition_value = resolved[0]
        else:
            return {
                "matches": [],
                "count": 0,
                "message": f"Could not resolve competition: {competition}",
            }

    team_key = resolve_team_name(team, df) if team else None
    opponent_key = resolve_team_name(opponent, df) if opponent else None
    if team and team_key is None:
        return {
            "matches": [],
            "count": 0,
            "message": f"Could not resolve team: {team}",
        }
    if opponent and opponent_key is None:
        return {
            "matches": [],
            "count": 0,
            "message": f"Could not resolve team: {opponent}",
        }

    filtered = _filter_matches(
        df,
        team_key=team_key,
        opponent_key=opponent_key,
        competition=competition_value,
        season=season,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
    )

    matches = [_format_match(row) for _, row in filtered.head(limit).iterrows()]
    return {
        "matches": matches,
        "count": int(len(filtered)),
        "returned": len(matches),
        "team_resolved": team_key,
        "opponent_resolved": opponent_key,
        "competition_resolved": competition_value,
    }


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------

def _team_record(
    df: pd.DataFrame, team_key: str, venue: str | None = None
) -> dict[str, Any]:
    """Aggregate wins/draws/losses/goals for one team over ``df``."""
    home = (
        df[df["home_team_key"] == team_key]
        if venue in (None, "home")
        else pd.DataFrame(columns=df.columns)
    )
    away = (
        df[df["away_team_key"] == team_key]
        if venue in (None, "away")
        else pd.DataFrame(columns=df.columns)
    )

    wins = draws = losses = 0
    gf = ga = 0

    for _, row in home.iterrows():
        hg, ag = row["home_goal"], row["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg_i, ag_i = int(hg), int(ag)
        gf += hg_i
        ga += ag_i
        if hg_i > ag_i:
            wins += 1
        elif hg_i == ag_i:
            draws += 1
        else:
            losses += 1

    for _, row in away.iterrows():
        hg, ag = row["home_goal"], row["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        hg_i, ag_i = int(hg), int(ag)
        gf += ag_i
        ga += hg_i
        if ag_i > hg_i:
            wins += 1
        elif ag_i == hg_i:
            draws += 1
        else:
            losses += 1

    played = wins + draws + losses
    return {
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "win_rate": round(wins / played * 100, 1) if played else 0.0,
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

    competition_value: str | None = None
    if competition:
        resolved = resolve_competition(competition)
        if resolved:
            competition_value = resolved[0]

    filtered = _filter_matches(
        df,
        team_key=team_key,
        competition=competition_value,
        season=season,
        venue=venue,
    )
    record = _team_record(filtered, team_key, venue=venue)
    display = display_name_for_key(team_key, df)

    return {
        "team": display,
        "team_key": team_key,
        "competition": competition_value or competition,
        "season": season,
        "venue": venue or "all",
        **record,
    }


def get_head_to_head(
    team1: str,
    team2: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Return every match between two teams plus a summary record."""
    df = _matches_df()
    key1 = resolve_team_name(team1, df)
    key2 = resolve_team_name(team2, df)
    if key1 is None:
        return {"error": f"Could not resolve team: {team1}"}
    if key2 is None:
        return {"error": f"Could not resolve team: {team2}"}

    competition_value: str | None = None
    if competition:
        resolved = resolve_competition(competition)
        if resolved:
            competition_value = resolved[0]

    filtered = _filter_matches(
        df,
        team_key=key1,
        opponent_key=key2,
        competition=competition_value,
        season=season,
    )
    matches = [_format_match(row) for _, row in filtered.iterrows()]

    wins1 = wins2 = draws = 0
    for m in matches:
        if m["home_goal"] is None or m["away_goal"] is None:
            continue
        home_key = normalize_team_name(m["home_team"])
        if m["home_goal"] > m["away_goal"]:
            if home_key == key1:
                wins1 += 1
            else:
                wins2 += 1
        elif m["home_goal"] < m["away_goal"]:
            if home_key == key1:
                wins1 += 1
            else:
                wins2 += 1
        else:
            draws += 1

    display1 = display_name_for_key(key1, df)
    display2 = display_name_for_key(key2, df)

    return {
        "team1": display1,
        "team2": display2,
        "team1_key": key1,
        "team2_key": key2,
        "competition": competition_value or competition,
        "season": season,
        "matches": matches,
        "count": len(matches),
        "summary": {
            f"{display1}_wins": wins1,
            f"{display2}_wins": wins2,
            "draws": draws,
            "total": len(matches),
        },
    }


# ---------------------------------------------------------------------------
# 3. Player queries
# ---------------------------------------------------------------------------

def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_age: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search the FIFA player dataset."""
    df = _players_df()
    if df.empty:
        return {"players": [], "count": 0}

    mask = pd.Series(True, index=df.index)

    if name:
        needle = normalize_team_name(name)
        mask &= df["name_key"].str.contains(needle, na=False)
    if nationality:
        nat = normalize_team_name(nationality)
        mask &= df["nationality_key"].str.contains(nat, na=False)
    if club:
        club_key = normalize_team_name(club)
        mask &= df["club_key"].str.contains(club_key, na=False)
    if position:
        mask &= df["position"].astype(str).str.contains(position, case=False, na=False)
    if min_overall is not None:
        mask &= df["overall"] >= min_overall
    if max_age is not None:
        mask &= df["age"] <= max_age

    filtered = (
        df[mask]
        .sort_values("overall", ascending=False, na_position="last")
        .head(limit)
    )
    players = [
        {
            "id": int(row["player_id"]) if pd.notna(row["player_id"]) else None,
            "name": row.get("name"),
            "age": int(row["age"]) if pd.notna(row["age"]) else None,
            "nationality": row.get("nationality"),
            "overall": int(row["overall"]) if pd.notna(row["overall"]) else None,
            "potential": int(row["potential"]) if pd.notna(row["potential"]) else None,
            "club": row.get("club") if pd.notna(row.get("club")) else None,
            "position": row.get("position"),
            "jersey_number": row.get("jersey_number"),
        }
        for _, row in filtered.iterrows()
    ]
    return {
        "players": players,
        "count": int(mask.sum()),
        "returned": len(players),
    }


def brazilian_club_summary() -> dict[str, Any]:
    """Return counts and average overall rating for Brazilian clubs."""
    df = _players_df()
    if df.empty:
        return {"clubs": [], "count": 0}

    candidates = {
        "Flamengo": ["flamengo"],
        "Palmeiras": ["palmeiras"],
        "Corinthians": ["corinthians"],
        "São Paulo": ["sao paulo"],
        "Santos": ["santos"],
        "Atlético Mineiro": ["atletico mineiro", "atletico-mg"],
        "Grêmio": ["gremio"],
        "Internacional": ["internacional"],
        "Botafogo": ["botafogo"],
        "Fluminense": ["fluminense"],
        "Vasco da Gama": ["vasco da gama", "vasco"],
        "Cruzeiro": ["cruzeiro"],
        "Athletico-PR": ["athletico-pr", "athletico paranaense"],
    }

    summary: list[dict[str, Any]] = []
    for canonical, keys in candidates.items():
        sub = df[
            df["club_key"].apply(
                lambda ck: any(k in ck for k in keys) if isinstance(ck, str) else False
            )
        ]
        if sub.empty:
            continue
        avg = float(sub["overall"].mean())
        summary.append(
            {
                "club": canonical,
                "player_count": int(len(sub)),
                "average_overall": round(avg, 1),
            }
        )
    summary.sort(key=lambda x: x["player_count"], reverse=True)
    return {"clubs": summary, "count": len(summary)}


# ---------------------------------------------------------------------------
# 4. Competition queries
# ---------------------------------------------------------------------------

def get_standings(competition: str, season: int) -> dict[str, Any]:
    """Compute league standings from match results for a competition/season."""
    df = _matches_df()
    resolved = resolve_competition(competition)
    competition_value = resolved[0] if resolved else competition

    filtered = _filter_matches(df, competition=competition_value, season=season)
    filtered = filtered.dropna(subset=["home_goal", "away_goal"])
    if filtered.empty:
        return {
            "competition": competition_value,
            "season": season,
            "standings": [],
            "message": f"No matches found for {competition} {season}",
        }

    records: dict[str, dict[str, Any]] = {}

    def ensure(team_key: str) -> None:
        if team_key and team_key not in records:
            records[team_key] = {
                "team": display_name_for_key(team_key, df),
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
            }

    for _, row in filtered.iterrows():
        hk, ak = row["home_team_key"], row["away_team_key"]
        if not hk or not ak:
            continue
        ensure(hk)
        ensure(ak)
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
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

    for record in records.values():
        record["goal_difference"] = record["goals_for"] - record["goals_against"]

    standings = sorted(
        records.values(),
        key=lambda r: (r["points"], r["goal_difference"], r["goals_for"]),
        reverse=True,
    )
    for idx, record in enumerate(standings, start=1):
        record["position"] = idx
    return {
        "competition": competition_value,
        "season": season,
        "standings": standings,
        "count": len(standings),
    }


def get_relegated_teams(season: int, bottom: int = 4) -> dict[str, Any]:
    """Return the bottom ``bottom`` teams of a Brasileirão season."""
    standings = get_standings("Brasileirão", season)
    if not standings.get("standings"):
        return {
            "season": season,
            "relegated": [],
            "message": f"No Brasileirão data for season {season}",
        }
    bottom_slice = standings["standings"][-bottom:]
    return {
        "season": season,
        "competition": "Brasileirão",
        "relegated": [
            {"team": row["team"], "position": row["position"], "points": row["points"]}
            for row in bottom_slice
        ],
    }


# ---------------------------------------------------------------------------
# 5. Statistical analysis
# ---------------------------------------------------------------------------

def get_biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Return matches ordered by largest goal difference."""
    df = _matches_df()
    competition_value: str | None = None
    if competition:
        resolved = resolve_competition(competition)
        if resolved:
            competition_value = resolved[0]

    filtered = _filter_matches(df, competition=competition_value, season=season)
    filtered = filtered.dropna(subset=["home_goal", "away_goal"])
    if filtered.empty:
        return {"matches": [], "count": 0}

    filtered = filtered.assign(
        goal_difference=(filtered["home_goal"] - filtered["away_goal"]).abs()
    )
    filtered = filtered.sort_values("goal_difference", ascending=False).head(limit)
    matches = [_format_match(row) for _, row in filtered.iterrows()]
    return {"matches": matches, "count": len(matches)}


def get_goals_per_match(
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Return average goals per match and home/away/draw splits."""
    df = _matches_df()
    competition_value: str | None = None
    if competition:
        resolved = resolve_competition(competition)
        if resolved:
            competition_value = resolved[0]

    filtered = _filter_matches(df, competition=competition_value, season=season)
    filtered = filtered.dropna(subset=["home_goal", "away_goal"])
    if filtered.empty:
        return {
            "average_goals_per_match": 0.0,
            "total_matches": 0,
            "total_goals": 0,
            "home_wins": 0,
            "draws": 0,
            "away_wins": 0,
        }

    total_goals = float(filtered["home_goal"].sum() + filtered["away_goal"].sum())
    total_matches = int(len(filtered))
    average = round(total_goals / total_matches, 2) if total_matches else 0.0
    home_wins = int((filtered["home_goal"] > filtered["away_goal"]).sum())
    draws = int((filtered["home_goal"] == filtered["away_goal"]).sum())
    away_wins = int((filtered["home_goal"] < filtered["away_goal"]).sum())

    home_pct = round(home_wins / total_matches * 100, 1) if total_matches else 0.0
    draw_pct = round(draws / total_matches * 100, 1) if total_matches else 0.0
    away_pct = round(away_wins / total_matches * 100, 1) if total_matches else 0.0

    return {
        "average_goals_per_match": average,
        "total_matches": total_matches,
        "total_goals": int(total_goals),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_pct": home_pct,
        "draw_pct": draw_pct,
        "away_win_pct": away_pct,
    }


def get_top_scoring_teams(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Return teams ranked by total goals scored."""
    df = _matches_df()
    competition_value: str | None = None
    if competition:
        resolved = resolve_competition(competition)
        if resolved:
            competition_value = resolved[0]

    filtered = _filter_matches(df, competition=competition_value, season=season)
    filtered = filtered.dropna(subset=["home_goal", "away_goal"])
    if filtered.empty:
        return {"teams": [], "count": 0}

    home = (
        filtered.groupby("home_team_key")
        .agg(team=("home_team_display", "first"), goals=("home_goal", "sum"))
        .reset_index()
    )
    away = (
        filtered.groupby("away_team_key")
        .agg(team=("away_team_display", "first"), goals=("away_goal", "sum"))
        .reset_index()
    )
    combined = pd.concat([home, away], ignore_index=True)
    totals = (
        combined.groupby("team", as_index=False)["goals"]
        .sum()
        .sort_values("goals", ascending=False)
        .head(limit)
    )
    teams = [
        {"team": row["team"], "goals": int(row["goals"])}
        for _, row in totals.iterrows()
    ]
    return {"teams": teams, "count": len(teams)}


def get_team_competition_history(team: str) -> dict[str, Any]:
    """Return the competitions and season counts a team has played in."""
    df = _matches_df()
    team_key = resolve_team_name(team, df)
    if team_key is None:
        return {"error": f"Could not resolve team: {team}"}

    matches = df[
        (df["home_team_key"] == team_key) | (df["away_team_key"] == team_key)
    ]
    if matches.empty:
        return {"team": team, "team_key": team_key, "competitions": []}

    counts = matches.groupby("competition")["season"].nunique().to_dict()
    history = [
        {"competition": comp, "seasons": int(season_count)}
        for comp, season_count in sorted(counts.items(), key=lambda x: -x[1])
    ]
    return {
        "team": display_name_for_key(team_key, df),
        "team_key": team_key,
        "competitions": history,
    }


__all__ = [
    "search_matches",
    "get_team_stats",
    "get_head_to_head",
    "search_players",
    "brazilian_club_summary",
    "get_standings",
    "get_relegated_teams",
    "get_biggest_wins",
    "get_goals_per_match",
    "get_top_scoring_teams",
    "get_team_competition_history",
]
