"""Query layer for the Brazilian soccer knowledge graph.

All functions accept a `DataStore` instance and return plain Python data
structures so the answers are easy to turn into MCP tool responses.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from data_loader import DataStore
from normalization import normalize_team_name, normalize_text, resolve_team_query


def _to_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce", dayfirst="/" in str(value))
    return parsed.date() if pd.notna(parsed) else None


def _matching_canonicals(df: pd.DataFrame, query: str | None) -> set[str]:
    """Resolve a free-text team query to canonical team names in the data."""
    if not query:
        return set()
    q = str(query).strip()
    # Prefer the curated alias list first.
    matches = set(resolve_team_query(q))
    if len(matches) >= 1:
        return matches

    # Fallback: search all canonical names currently in the dataset.
    names = set(df["home_team"].unique()) | set(df["away_team"].unique())
    key = normalize_text(q)
    for name in names:
        nkey = normalize_text(name)
        if key == nkey or key in nkey:
            matches.add(name)
    return matches


def find_matches(
    ds: DataStore,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return matches matching the supplied filters."""
    df = ds.matches.copy()

    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]

    if season:
        df = df[df["season"] == int(season)]

    d0 = _to_date(date_from)
    d1 = _to_date(date_to)
    if d0:
        df = df[df["date"] >= pd.Timestamp(d0)]
    if d1:
        df = df[df["date"] <= pd.Timestamp(d1)]

    team_names = _matching_canonicals(df, team) if team else set()
    opp_names = _matching_canonicals(df, opponent) if opponent else set()

    if team and not team_names:
        return []
    if opponent and not opp_names:
        return []

    if team_names:
        df = df[df["home_team"].isin(team_names) | df["away_team"].isin(team_names)]
    if opp_names:
        df = df[df["home_team"].isin(opp_names) | df["away_team"].isin(opp_names)]

    if team_names and opp_names:
        df = df[
            (df["home_team"].isin(team_names) | df["away_team"].isin(team_names))
            & (df["home_team"].isin(opp_names) | df["away_team"].isin(opp_names))
        ]

    df = df.sort_values("date", ascending=False).head(limit)
    return [_match_record(r) for _, r in df.iterrows()]


def _match_record(r: pd.Series) -> dict[str, Any]:
    return {
        "date": r["date"].strftime("%Y-%m-%d") if pd.notna(r["date"]) else None,
        "competition": r["competition"],
        "season": int(r["season"]) if pd.notna(r["season"]) else None,
        "home_team": r["home_team"],
        "away_team": r["away_team"],
        "home_goal": int(r["home_goal"]),
        "away_goal": int(r["away_goal"]),
        "round": r["round"] if pd.notna(r["round"]) else None,
        "stage": r["stage"] if pd.notna(r["stage"]) else None,
    }


def team_stats(
    ds: DataStore,
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> dict[str, Any]:
    """Return win/loss/draw and goal statistics for a team."""
    df = ds.matches.copy()
    teams = _matching_canonicals(df, team)
    if not teams:
        return {"team": team, "matches": 0, "error": "Team not found"}

    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    if season:
        df = df[df["season"] == int(season)]

    if venue and venue.lower() == "home":
        df = df[df["home_team"].isin(teams)]
    elif venue and venue.lower() == "away":
        df = df[df["away_team"].isin(teams)]
    else:
        df = df[df["home_team"].isin(teams) | df["away_team"].isin(teams)]

    wins = draws = losses = gf = ga = 0
    for _, r in df.iterrows():
        is_home = r["home_team"] in teams
        team_goals = r["home_goal"] if is_home else r["away_goal"]
        opp_goals = r["away_goal"] if is_home else r["home_goal"]
        gf += int(team_goals)
        ga += int(opp_goals)
        if team_goals > opp_goals:
            wins += 1
        elif team_goals < opp_goals:
            losses += 1
        else:
            draws += 1

    matches = wins + draws + losses
    return {
        "team": team,
        "canonical_teams": sorted(teams),
        "season": season,
        "competition": competition,
        "venue": venue,
        "matches": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "win_rate": round(wins / matches * 100, 1) if matches else 0.0,
    }


def head_to_head(
    ds: DataStore,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Return all matches between two teams plus a summary."""
    df = ds.matches.copy()
    a_teams = _matching_canonicals(df, team_a)
    b_teams = _matching_canonicals(df, team_b)

    df = df[
        (df["home_team"].isin(a_teams) | df["away_team"].isin(a_teams))
        & (df["home_team"].isin(b_teams) | df["away_team"].isin(b_teams))
    ]

    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    if season:
        df = df[df["season"] == int(season)]

    a_wins = b_wins = draws = a_gf = b_gf = 0
    matches_all = []
    for _, r in df.sort_values("date", ascending=False).iterrows():
        rec = _match_record(r)
        matches_all.append(rec)
        h_in_a = r["home_team"] in a_teams
        a_in_a = r["away_team"] in a_teams
        hg = int(r["home_goal"])
        ag = int(r["away_goal"])
        if h_in_a:
            a_gf += hg
            b_gf += ag
        else:
            a_gf += ag
            b_gf += hg

        if hg == ag:
            draws += 1
        elif h_in_a and hg > ag:
            a_wins += 1
        elif a_in_a and ag > hg:
            a_wins += 1
        else:
            b_wins += 1

    return {
        "team_a": team_a,
        "team_b": team_b,
        "matches": len(matches_all),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_gf,
        "team_b_goals": b_gf,
        "match_list": matches_all[:limit],
    }


def biggest_wins(
    ds: DataStore,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return the biggest wins (largest goal difference) in the dataset."""
    df = ds.matches.copy()
    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    if season:
        df = df[df["season"] == int(season)]
    df = df.dropna(subset=["home_goal", "away_goal"])
    df["margin"] = (df["home_goal"] - df["away_goal"]).abs()
    df = df.sort_values(["margin", "date"], ascending=[False, False]).head(limit)
    return [_match_record(r) for _, r in df.iterrows()]


def average_goals_per_match(
    ds: DataStore, competition: str | None = None, season: int | None = None
) -> dict[str, float]:
    """Average total goals per match and home win rate."""
    df = ds.matches.copy()
    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    if season:
        df = df[df["season"] == int(season)]
    df = df.dropna(subset=["home_goal", "away_goal"])
    total = len(df)
    if total == 0:
        return {"matches": 0, "average_goals": 0.0, "home_win_rate": 0.0}
    avg = (df["home_goal"] + df["away_goal"]).mean()
    home_wins = (df["home_goal"] > df["away_goal"]).sum()
    return {
        "matches": int(total),
        "average_goals": round(float(avg), 2),
        "home_win_rate": round(float(home_wins / total * 100), 1),
    }


def best_home_record(ds: DataStore, competition: str | None = None) -> dict[str, Any]:
    """Return the team with the best home record (by win rate, min 5 home games)."""
    df = ds.matches.copy()
    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    df = df.dropna(subset=["home_goal", "away_goal"])
    home = df.groupby("home_team").apply(
        lambda g: pd.Series(
            {
                "matches": len(g),
                "wins": int((g["home_goal"] > g["away_goal"]).sum()),
                "draws": int((g["home_goal"] == g["away_goal"]).sum()),
                "losses": int((g["home_goal"] < g["away_goal"]).sum()),
                "goals_for": int(g["home_goal"].sum()),
                "goals_against": int(g["away_goal"].sum()),
            }
        )
    )
    home = home[home["matches"] >= 5].copy()
    home["win_rate"] = home["wins"] / home["matches"]
    home = home.sort_values(["win_rate", "goals_for"], ascending=[False, False])
    if home.empty:
        return {"team": None, "matches": 0, "win_rate": 0.0}
    top = home.iloc[0]
    return {
        "team": top.name,
        "matches": int(top["matches"]),
        "wins": int(top["wins"]),
        "draws": int(top["draws"]),
        "losses": int(top["losses"]),
        "goals_for": int(top["goals_for"]),
        "goals_against": int(top["goals_against"]),
        "win_rate": round(float(top["win_rate"]) * 100, 1),
    }


def search_players(
    ds: DataStore,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search the FIFA player dataset."""
    df = ds.players.copy()
    if name:
        df = df[df["name"].str.contains(name, case=False, na=False)]
    if nationality:
        df = df[df["nationality"].str.contains(nationality, case=False, na=False)]
    if club:
        df = df[df["club"].str.contains(club, case=False, na=False)]
    if position:
        df = df[df["position"].str.contains(position, case=False, na=False)]
    if min_overall is not None:
        df = df[df["overall"] >= int(min_overall)]
    if max_overall is not None:
        df = df[df["overall"] <= int(max_overall)]
    df = df.sort_values("overall", ascending=False).head(limit)
    return [_player_record(r) for _, r in df.iterrows()]


def top_players(
    ds: DataStore,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Convenience wrapper for the highest-rated players by criteria."""
    return search_players(
        ds,
        nationality=nationality,
        club=club,
        position=position,
        limit=limit,
    )


def _player_record(r: pd.Series) -> dict[str, Any]:
    return {
        "id": int(r["id"]) if pd.notna(r["id"]) else None,
        "name": r["name"],
        "age": int(r["age"]) if pd.notna(r["age"]) else None,
        "nationality": r["nationality"],
        "overall": int(r["overall"]) if pd.notna(r["overall"]) else None,
        "potential": int(r["potential"]) if pd.notna(r["potential"]) else None,
        "club": r["club"],
        "position": r["position"],
        "jersey_number": int(r["jersey_number"]) if pd.notna(r["jersey_number"]) else None,
        "height": r["height"],
        "weight": r["weight"],
    }


def team_competitions(ds: DataStore, team: str) -> list[dict[str, Any]]:
    """List competitions and seasons a team has played in."""
    df = ds.matches.copy()
    teams = _matching_canonicals(df, team)
    if not teams:
        return []
    df = df[df["home_team"].isin(teams) | df["away_team"].isin(teams)]
    grouped = (
        df.groupby(["competition", "season"], dropna=False)
        .size()
        .reset_index(name="matches")
    )
    return [
        {"competition": r["competition"], "season": int(r["season"]), "matches": int(r["matches"])}
        for _, r in grouped.iterrows()
    ]


def list_competitions(ds: DataStore) -> list[str]:
    """Return all competition names in the match data."""
    return sorted(ds.matches["competition"].dropna().unique().tolist())


def list_seasons(ds: DataStore, competition: str | None = None) -> list[int]:
    """Return all seasons, optionally filtered to a competition."""
    df = ds.matches
    if competition:
        df = df[df["competition"].str.contains(competition, case=False, na=False)]
    return sorted([int(s) for s in df["season"].dropna().unique()])
