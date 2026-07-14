"""Query layer for the Brazilian Soccer MCP server.

Context block
-------------
This module implements the business logic that turns the normalized data
structures produced by ``data_loader.py`` into structured, JSON-serializable
answers. Each public function maps to one of the required query categories
described in ``TASK.md``:

  * Match queries        -> :func:`find_matches`, :func:`find_head_to_head`
  * Team queries         -> :func:`team_statistics`, :func:`compare_teams`
  * Player queries       -> :func:`search_players`, :func:`top_players_at_club`
  * Competition queries  -> :func:`competition_standings`, :func:`competition_seasons`
  * Statistical analysis -> :func:`average_goals`, :func:`biggest_wins`,
                            :func:`home_vs_away_record`, :func:`last_match_between`

All return values are plain Python dicts/lists so they can be serialized by
the MCP server without any additional conversion.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import pandas as pd

from .data_loader import DataLoader, normalize_team_name, parse_date


def _match_to_dict(row: pd.Series) -> dict[str, Any]:
    """Convert a single match row into a serializable dict."""
    d = {
        "date": row.get("date").isoformat() if isinstance(row.get("date"), datetime) else None,
        "home_team": row.get("home_team_display") or row.get("home_team"),
        "away_team": row.get("away_team_display") or row.get("away_team"),
        "home_goal": row.get("home_goal"),
        "away_goal": row.get("away_goal"),
        "season": int(row["season"]) if pd.notna(row.get("season")) else None,
        "competition": row.get("competition"),
        "round": row.get("round"),
        "stage": row.get("stage"),
        "source": row.get("source"),
    }
    return d


def _filter_valid_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Return only rows where both scores are present (needed for stats)."""
    return df.dropna(subset=["home_goal", "away_goal"])


def find_matches(
    loader: DataLoader,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Find matches matching the supplied criteria.

    Any ``None`` argument acts as a wildcard. ``team`` matches either the
    home or away side. When ``opponent`` is also given, the result is the
    set of matches between ``team`` and ``opponent`` (in either order).
    """
    df = loader.matches
    if df.empty:
        return []

    mask = pd.Series([True] * len(df), index=df.index)

    if team:
        t = normalize_team_name(team)
        team_mask = (df["home_team_norm"] == t) | (df["away_team_norm"] == t)
        if opponent:
            o = normalize_team_name(opponent)
            opp_mask = (df["home_team_norm"] == o) | (df["away_team_norm"] == o)
            team_mask = team_mask & opp_mask
        mask &= team_mask

    if competition:
        comp_norm = competition.strip().lower()
        mask &= df["competition"].fillna("").str.lower().str.contains(comp_norm, regex=False)

    if season is not None:
        mask &= df["season"] == int(season)

    if start_date:
        sd = parse_date(start_date)
        if sd is not None:
            valid = df["date"].apply(lambda d: isinstance(d, datetime) and d >= sd)
            mask &= valid

    if end_date:
        ed = parse_date(end_date)
        if ed is not None:
            valid = df["date"].apply(lambda d: isinstance(d, datetime) and d <= ed)
            mask &= valid

    sub = df[mask].sort_values("date", na_position="last")
    if limit is not None:
        sub = sub.head(int(limit))
    return [_match_to_dict(r) for _, r in sub.iterrows()]


def find_head_to_head(
    loader: DataLoader, team_a: str, team_b: str, competition: Optional[str] = None
) -> dict[str, Any]:
    """Return head-to-head record between two teams."""
    matches = find_matches(loader, team=team_a, opponent=team_b, competition=competition)
    a_norm = normalize_team_name(team_a)
    a_wins = b_wins = draws = 0
    a_goals = b_goals = 0
    for m in matches:
        hg, ag = m["home_goal"], m["away_goal"]
        if hg is None or ag is None:
            continue
        # Identify which side is team_a.
        home_norm = normalize_team_name(m["home_team"])
        a_is_home = home_norm == a_norm
        a_score, b_score = (hg, ag) if a_is_home else (ag, hg)
        a_goals += a_score
        b_goals += b_score
        if a_score > b_score:
            a_wins += 1
        elif b_score > a_score:
            b_wins += 1
        else:
            draws += 1
    return {
        "team_a": team_a,
        "team_b": team_b,
        "matches_played": len(matches),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "matches": matches,
    }


def team_statistics(
    loader: DataLoader,
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: Optional[str] = None,
) -> dict[str, Any]:
    """Compute win/draw/loss and goal statistics for a team.

    ``venue`` may be ``"home"``, ``"away"`` or ``None`` (both).
    """
    df = loader.matches
    if df.empty:
        return {"team": team, "matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}

    t = normalize_team_name(team)
    mask = (df["home_team_norm"] == t) | (df["away_team_norm"] == t)
    if season is not None:
        mask &= df["season"] == int(season)
    if competition:
        comp_norm = competition.strip().lower()
        mask &= df["competition"].fillna("").str.lower().str.contains(comp_norm, regex=False)
    if venue:
        v = venue.lower()
        if v == "home":
            mask &= df["home_team_norm"] == t
        elif v == "away":
            mask &= df["away_team_norm"] == t

    sub = _filter_valid_scores(df[mask])
    wins = draws = losses = 0
    gf = ga = 0
    for _, r in sub.iterrows():
        home = r["home_team_norm"] == t
        hg, ag = int(r["home_goal"]), int(r["away_goal"])
        if home:
            team_score, opp_score = hg, ag
        else:
            team_score, opp_score = ag, hg
        gf += team_score
        ga += opp_score
        if team_score > opp_score:
            wins += 1
        elif team_score < opp_score:
            losses += 1
        else:
            draws += 1
    matches = len(sub)
    win_rate = round(wins / matches * 100, 1) if matches else 0.0
    return {
        "team": team,
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
        "win_rate": win_rate,
    }


def compare_teams(
    loader: DataLoader, team_a: str, team_b: str, season: Optional[int] = None
) -> dict[str, Any]:
    """Compare two teams side-by-side and head-to-head."""
    h2h = find_head_to_head(loader, team_a, team_b)
    sa = team_statistics(loader, team_a, season=season)
    sb = team_statistics(loader, team_b, season=season)
    return {
        "team_a_stats": sa,
        "team_b_stats": sb,
        "head_to_head": {
            "team_a_wins": h2h["team_a_wins"],
            "team_b_wins": h2h["team_b_wins"],
            "draws": h2h["draws"],
            "matches_played": h2h["matches_played"],
        },
    }


def search_players(
    loader: DataLoader,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: Optional[int] = 50,
) -> list[dict[str, Any]]:
    """Search the FIFA player dataset."""
    df = loader.players
    if df.empty:
        return []

    mask = pd.Series([True] * len(df), index=df.index)
    if name:
        n = normalize_team_name(name)
        mask &= df["name_normalized"].str.contains(n, regex=False, na=False)
    if nationality:
        nat = normalize_team_name(nationality)
        mask &= df["nationality_normalized"] == nat
    if club:
        c = normalize_team_name(club)
        mask &= df["club_normalized"] == c
    if position:
        mask &= df["Position"].fillna("").str.upper() == position.upper()
    if min_overall is not None:
        mask &= df["Overall"].fillna(0).astype(int) >= int(min_overall)

    sub = df[mask]
    if "Overall" in sub.columns:
        sub = sub.sort_values("Overall", ascending=False)
    if limit is not None:
        sub = sub.head(int(limit))
    return [_player_to_dict(r) for _, r in sub.iterrows()]


def top_players_at_club(loader: DataLoader, club: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return the highest-rated players at a given club."""
    return search_players(loader, club=club, limit=limit)


def _player_to_dict(row: pd.Series) -> dict[str, Any]:
    return {
        "id": int(row["ID"]) if pd.notna(row.get("ID")) else None,
        "name": row.get("Name"),
        "age": int(row["Age"]) if pd.notna(row.get("Age")) else None,
        "nationality": row.get("Nationality"),
        "overall": int(row["Overall"]) if pd.notna(row.get("Overall")) else None,
        "potential": int(row["Potential"]) if pd.notna(row.get("Potential")) else None,
        "club": row.get("Club"),
        "position": row.get("Position"),
        "jersey_number": int(row["Jersey Number"]) if pd.notna(row.get("Jersey Number")) else None,
    }


def competition_standings(
    loader: DataLoader, competition: str, season: int
) -> list[dict[str, Any]]:
    """Compute standings for a competition+season from match results.

    Uses 3 points per win, 1 per draw. Teams are ranked by points, then
    goal difference, then goals for.
    """
    df = loader.matches
    if df.empty:
        return []
    comp_norm = competition.strip().lower()
    mask = (
        df["competition"].fillna("").str.lower().str.contains(comp_norm, regex=False)
        & (df["season"] == int(season))
    )
    sub = _filter_valid_scores(df[mask])
    if sub.empty:
        return []

    stats: dict[str, dict[str, Any]] = {}
    for _, r in sub.iterrows():
        home = r["home_team_display"]
        away = r["away_team_display"]
        hg, ag = int(r["home_goal"]), int(r["away_goal"])
        for name in (home, away):
            if name not in stats:
                stats[name] = {
                    "team": name, "played": 0, "wins": 0, "draws": 0,
                    "losses": 0, "goals_for": 0, "goals_against": 0,
                    "points": 0,
                }
        stats[home]["played"] += 1
        stats[away]["played"] += 1
        stats[home]["goals_for"] += hg
        stats[home]["goals_against"] += ag
        stats[away]["goals_for"] += ag
        stats[away]["goals_against"] += hg
        if hg > ag:
            stats[home]["wins"] += 1
            stats[home]["points"] += 3
            stats[away]["losses"] += 1
        elif ag > hg:
            stats[away]["wins"] += 1
            stats[away]["points"] += 3
            stats[home]["losses"] += 1
        else:
            stats[home]["draws"] += 1
            stats[away]["draws"] += 1
            stats[home]["points"] += 1
            stats[away]["points"] += 1

    table = list(stats.values())
    for t in table:
        t["goal_difference"] = t["goals_for"] - t["goals_against"]
    table.sort(key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]), reverse=True)
    for i, t in enumerate(table, 1):
        t["position"] = i
        if i == 1:
            t["label"] = "Champion"
    return table


def competition_seasons(loader: DataLoader, competition: str) -> list[int]:
    """List seasons available for a competition."""
    df = loader.matches
    if df.empty:
        return []
    comp_norm = competition.strip().lower()
    sub = df[df["competition"].fillna("").str.lower().str.contains(comp_norm, regex=False)]
    return sorted([int(s) for s in sub["season"].dropna().unique().tolist()])


def average_goals(
    loader: DataLoader,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict[str, Any]:
    """Compute average goals per match and home win rate."""
    df = loader.matches
    if df.empty:
        return {"average_goals": 0.0, "matches": 0, "home_win_rate": 0.0}
    mask = pd.Series([True] * len(df), index=df.index)
    if competition:
        comp_norm = competition.strip().lower()
        mask &= df["competition"].fillna("").str.lower().str.contains(comp_norm, regex=False)
    if season is not None:
        mask &= df["season"] == int(season)
    sub = _filter_valid_scores(df[mask])
    if sub.empty:
        return {"average_goals": 0.0, "matches": 0, "home_win_rate": 0.0}
    total_goals = (sub["home_goal"] + sub["away_goal"]).sum()
    matches = len(sub)
    home_wins = (sub["home_goal"] > sub["away_goal"]).sum()
    draws = (sub["home_goal"] == sub["away_goal"]).sum()
    away_wins = (sub["home_goal"] < sub["away_goal"]).sum()
    return {
        "competition": competition,
        "season": season,
        "matches": matches,
        "total_goals": int(total_goals),
        "average_goals": round(float(total_goals) / matches, 2),
        "home_wins": int(home_wins),
        "draws": int(draws),
        "away_wins": int(away_wins),
        "home_win_rate": round(float(home_wins) / matches * 100, 1),
        "away_win_rate": round(float(away_wins) / matches * 100, 1),
    }


def biggest_wins(
    loader: DataLoader,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return the largest victory margins in the dataset."""
    df = loader.matches
    if df.empty:
        return []
    mask = pd.Series([True] * len(df), index=df.index)
    if competition:
        comp_norm = competition.strip().lower()
        mask &= df["competition"].fillna("").str.lower().str.contains(comp_norm, regex=False)
    if season is not None:
        mask &= df["season"] == int(season)
    sub = _filter_valid_scores(df[mask]).copy()
    if sub.empty:
        return []
    sub["margin"] = (sub["home_goal"] - sub["away_goal"]).abs()
    sub = sub.sort_values("margin", ascending=False).head(int(limit))
    results = []
    for _, r in sub.iterrows():
        hg, ag = int(r["home_goal"]), int(r["away_goal"])
        if hg > ag:
            winner = r["home_team_display"]
            loser = r["away_team_display"]
        else:
            winner = r["away_team_display"]
            loser = r["home_team_display"]
        results.append({
            "date": r["date"].isoformat() if isinstance(r["date"], datetime) else None,
            "winner": winner,
            "loser": loser,
            "score": f"{hg}-{ag}",
            "margin": abs(hg - ag),
            "competition": r.get("competition"),
            "season": int(r["season"]) if pd.notna(r.get("season")) else None,
        })
    return results


def home_vs_away_record(
    loader: DataLoader, team: str, season: Optional[int] = None
) -> dict[str, Any]:
    """Split a team's record into home and away portions."""
    return {
        "home": team_statistics(loader, team, season=season, venue="home"),
        "away": team_statistics(loader, team, season=season, venue="away"),
    }


def last_match_between(
    loader: DataLoader, team_a: str, team_b: str
) -> Optional[dict[str, Any]]:
    """Return the most recent match between two teams."""
    matches = find_matches(loader, team=team_a, opponent=team_b)
    if not matches:
        return None
    dated = [m for m in matches if m["date"]]
    if dated:
        dated.sort(key=lambda m: m["date"], reverse=True)
        return dated[0]
    return matches[0]


def list_competitions(loader: DataLoader) -> list[str]:
    return loader.competitions()
