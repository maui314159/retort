"""Query layer: structured answers over the unified match/player tables.

Every function returns plain Python dicts/lists so they can be unit-tested
directly, formatted to text for MCP tools, or serialized as JSON. All team,
competition and date inputs accept the messy real-world variations handled
by :mod:`soccer_mcp.normalize`.
"""

from __future__ import annotations

import difflib
import re
from typing import Any

import pandas as pd

from .data import DataStore
from .normalize import (
    COMPETITIONS,
    canonical_competition,
    canonical_team,
    derby_name,
    normalize_text,
    parse_user_date,
)


class QueryError(ValueError):
    """Raised when a query cannot be resolved (unknown team, etc.)."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_team(store: DataStore, name: str) -> str:
    key = canonical_team(name)
    if not key:
        raise QueryError("Empty team name.")
    known = set(store.teams)
    if key in known:
        return key
    # Fuzzy fallback handles "Corinthians Paulista", "Flamengo RJ" and
    # misspellings, but stays strict enough to reject non-clubs.
    close = difflib.get_close_matches(key, sorted(known), n=1, cutoff=0.6)
    if close:
        return close[0]
    raise QueryError(f"Unknown team: {name!r}. Try list_teams() to browse.")


def _resolve_competition(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    key = canonical_competition(value)
    if key is None:
        raise QueryError(
            f"Unknown competition: {value!r}. Expected one of: "
            + ", ".join(sorted(COMPETITIONS))
        )
    return key


def _filter(
    store: DataStore,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str = "any",
    stage: str | None = None,
    played_only: bool = True,
) -> pd.DataFrame:
    df = store.matches
    mask = pd.Series(True, index=df.index)

    comp_key = _resolve_competition(competition)
    if comp_key is not None:
        mask &= df["competition"] == comp_key

    if season is not None and str(season).strip():
        mask &= df["season"] == int(str(season).strip())

    start = parse_user_date(date_from)
    if start is not None:
        mask &= df["date"] >= start
    end = parse_user_date(date_to)
    if end is not None:
        mask &= df["date"] <= end

    team_key = _resolve_team(store, team) if team else None
    opp_key = _resolve_team(store, opponent) if opponent else None

    venue_norm = normalize_text(venue) or "any"
    if team_key and opp_key:
        if venue_norm == "home":
            mask &= (df["home"] == team_key) & (df["away"] == opp_key)
        elif venue_norm == "away":
            mask &= (df["home"] == opp_key) & (df["away"] == team_key)
        else:
            mask &= (
                ((df["home"] == team_key) & (df["away"] == opp_key))
                | ((df["home"] == opp_key) & (df["away"] == team_key))
            )
    elif team_key:
        if venue_norm == "home":
            mask &= df["home"] == team_key
        elif venue_norm == "away":
            mask &= df["away"] == team_key
        else:
            mask &= (df["home"] == team_key) | (df["away"] == team_key)

    if stage:
        # Word-boundary match so "final" doesn't also match "semifinals".
        stage_norm = re.escape(normalize_text(stage))
        pattern = rf"\b{stage_norm}\b"
        mask &= (
            df["stage"].map(normalize_text).str.contains(pattern, na=False, regex=True)
            | df["round"].astype(str).str.contains(pattern, na=False, regex=True)
        )

    if played_only:
        mask &= df["home_goals"].notna() & df["away_goals"].notna()

    return df[mask]


def _match_row(store: DataStore, row: pd.Series) -> dict[str, Any]:
    return {
        "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else None,
        "competition": COMPETITIONS.get(row["competition"], {}).get(
            "display", row["competition"]
        ),
        "competition_key": row["competition"],
        "season": int(row["season"]) if pd.notna(row["season"]) else None,
        "round": str(row["round"]) if pd.notna(row["round"]) else "",
        "stage": str(row["stage"]) if pd.notna(row["stage"]) else "",
        "home_team": store.display_team(row["home"]),
        "away_team": store.display_team(row["away"]),
        "home_goals": int(row["home_goals"]) if pd.notna(row["home_goals"]) else None,
        "away_goals": int(row["away_goals"]) if pd.notna(row["away_goals"]) else None,
        "source": row["source"],
    }


def _result_counts(df: pd.DataFrame, team_key: str) -> dict[str, Any]:
    """W/D/L and goals for ``team_key`` within a filtered match frame."""
    played = df[df["home_goals"].notna() & df["away_goals"].notna()]
    is_home = played["home"] == team_key
    gf = played["home_goals"].where(is_home, played["away_goals"])
    ga = played["away_goals"].where(is_home, played["home_goals"])
    wins = int((gf > ga).sum())
    draws = int((gf == ga).sum())
    losses = int((gf < ga).sum())
    matches = len(played)
    return {
        "matches": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": int(gf.sum()) if matches else 0,
        "goals_against": int(ga.sum()) if matches else 0,
        "win_rate": round(100.0 * wins / matches, 1) if matches else 0.0,
    }


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------

def search_matches(
    store: DataStore,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str = "any",
    stage: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Find matches by team, competition, season, date range or stage."""
    df = _filter(store, team, opponent, competition, season,
                 date_from, date_to, venue, stage, played_only=False)
    df = df.sort_values("date", ascending=False, na_position="last")
    total = len(df)
    page = df.iloc[offset:offset + limit]
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "matches": [_match_row(store, row) for _, row in page.iterrows()],
    }


def head_to_head(
    store: DataStore,
    team1: str,
    team2: str,
    competition: str | None = None,
    season: int | str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """All matches between two teams plus the aggregate W/D/L record."""
    key1 = _resolve_team(store, team1)
    key2 = _resolve_team(store, team2)
    df = _filter(store, key1, key2, competition, season)
    df = df.sort_values("date", ascending=False, na_position="last")

    wins1 = draws = wins2 = 0
    goals1 = goals2 = 0
    for _, row in df.iterrows():
        hg, ag = int(row["home_goals"]), int(row["away_goals"])
        if row["home"] == key1:
            g1, g2 = hg, ag
        else:
            g1, g2 = ag, hg
        goals1 += g1
        goals2 += g2
        if g1 > g2:
            wins1 += 1
        elif g1 < g2:
            wins2 += 1
        else:
            draws += 1

    return {
        "team1": store.display_team(key1),
        "team2": store.display_team(key2),
        "derby": derby_name(key1, key2),
        "total_matches": len(df),
        "team1_wins": wins1,
        "team2_wins": wins2,
        "draws": draws,
        "team1_goals": goals1,
        "team2_goals": goals2,
        "matches": [_match_row(store, row) for _, row in df.head(limit).iterrows()],
    }


def last_match(store: DataStore, team1: str, team2: str) -> dict[str, Any]:
    """The most recent match between two teams."""
    result = head_to_head(store, team1, team2, limit=1)
    if not result["matches"]:
        raise QueryError(f"No matches found between {team1!r} and {team2!r}.")
    return result["matches"][0]


def find_derbies(
    store: DataStore,
    season: int | str | None = None,
    competition: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Matches between traditional rivals (Fla-Flu, Gre-Nal, ...)."""
    df = _filter(store, competition=competition, season=season)
    derby_col = [derby_name(h, a) for h, a in zip(df["home"], df["away"])]
    df = df[[d is not None for d in derby_col]].copy()
    names = [d for d in derby_col if d is not None]
    df = df.assign(derby=names)
    df = df.sort_values("date", ascending=False, na_position="last")
    page = df.head(limit)
    matches = []
    for (_, row), derby in zip(page.iterrows(), page["derby"]):
        entry = _match_row(store, row)
        entry["derby"] = derby
        matches.append(entry)
    return {"total": len(df), "matches": matches}


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------

def team_stats(
    store: DataStore,
    team: str,
    competition: str | None = None,
    season: int | str | None = None,
    venue: str = "any",
) -> dict[str, Any]:
    """Win/draw/loss record, goals and win rate for one team."""
    key = _resolve_team(store, team)
    df = _filter(store, key, competition=competition, season=season, venue=venue)
    stats = _result_counts(df, key)
    stats.update({
        "team": store.display_team(key),
        "competition": COMPETITIONS.get(_resolve_competition(competition), {}).get(
            "display", "All competitions"
        ) if competition else "All competitions",
        "season": int(str(season).strip()) if season is not None and str(season).strip() else None,
        "venue": venue,
    })
    return stats


def team_competitions(store: DataStore, team: str) -> dict[str, Any]:
    """Which competitions (and seasons) a team appears in."""
    key = _resolve_team(store, team)
    df = _filter(store, key)
    played = df[df["home_goals"].notna()]
    comps = []
    for comp, group in played.groupby("competition"):
        seasons = sorted(int(s) for s in group["season"].dropna().unique())
        comps.append({
            "competition": COMPETITIONS.get(comp, {}).get("display", comp),
            "competition_key": comp,
            "seasons": seasons,
            "matches": len(group),
        })
    comps.sort(key=lambda c: -c["matches"])
    return {
        "team": store.display_team(key),
        "competitions": comps,
        "total_matches": len(played),
    }


# ---------------------------------------------------------------------------
# 3. Player queries
# ---------------------------------------------------------------------------

def _filter_players(
    store: DataStore,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
) -> pd.DataFrame:
    df = store.players
    mask = pd.Series(True, index=df.index)
    if name:
        mask &= df["name_norm"].str.contains(normalize_text(name), na=False)
    if nationality:
        mask &= df["nationality_norm"] == normalize_text(nationality)
    if club:
        # Prefer exact club matches ("Santos") over substring hits
        # ("Santos Laguna"); fall back to substring when no club equals.
        club_norm = normalize_text(club)
        exact = df["club_norm"] == club_norm
        mask &= exact if exact.any() else df["club_norm"].str.contains(club_norm, na=False)
    if position:
        mask &= df["position"].astype(str).str.upper() == str(position).upper()
    if position_group:
        mask &= df["position_group"] == normalize_text(position_group)
    if min_overall is not None:
        mask &= df["overall"] >= int(min_overall)
    return df[mask]


def _player_row(row: pd.Series) -> dict[str, Any]:
    return {
        "id": int(row["id"]) if pd.notna(row["id"]) else None,
        "name": row["name"],
        "age": int(row["age"]) if pd.notna(row["age"]) else None,
        "nationality": row["nationality"],
        "overall": int(row["overall"]) if pd.notna(row["overall"]) else None,
        "potential": int(row["potential"]) if pd.notna(row["potential"]) else None,
        "club": row["club"] if pd.notna(row["club"]) else None,
        "position": row["position"] if pd.notna(row["position"]) else None,
        "position_group": row["position_group"] if pd.notna(row["position_group"]) else None,
    }


def search_players(
    store: DataStore,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search FIFA players by name, nationality, club or position."""
    df = _filter_players(store, name, nationality, club,
                         position, position_group, min_overall)
    df = df.sort_values("overall", ascending=False, na_position="last")
    return {
        "total": len(df),
        "players": [_player_row(row) for _, row in df.head(limit).iterrows()],
    }


def top_players(
    store: DataStore,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Highest-rated players, optionally filtered."""
    return search_players(
        store, nationality=nationality, club=club, position=position,
        position_group=position_group, limit=limit,
    )


def player_profile(store: DataStore, name: str) -> dict[str, Any]:
    """Full attribute profile for the best-matching player name.

    Matching order: exact -> substring -> all-tokens-present -> fuzzy.
    """
    df = store.players
    norm = normalize_text(name)
    exact = df[df["name_norm"] == norm]
    if exact.empty:
        sub = df[df["name_norm"].str.contains(norm, na=False)]
    else:
        sub = exact
    if sub.empty:
        tokens = [t for t in norm.split() if t]
        token_mask = pd.Series(True, index=df.index)
        for token in tokens:
            token_mask &= df["name_norm"].str.contains(token, na=False)
        sub = df[token_mask]
    if sub.empty:
        close = difflib.get_close_matches(
            norm, df["name_norm"].tolist(), n=1, cutoff=0.6
        )
        sub = df[df["name_norm"].isin(close)] if close else df.iloc[0:0]
    if sub.empty:
        raise QueryError(f"No player found for {name!r}.")
    row = sub.sort_values("overall", ascending=False).iloc[0]
    profile = _player_row(row)
    skills = {
        col: int(row[col])
        for col in (
            "crossing", "finishing", "heading_accuracy", "short_passing",
            "volleys", "dribbling", "curve", "fk_accuracy", "long_passing",
            "ball_control", "acceleration", "sprint_speed", "agility",
            "reactions", "balance", "shot_power", "jumping", "stamina",
            "strength", "long_shots", "aggression", "interceptions",
            "positioning", "vision", "penalties", "composure", "marking",
            "standing_tackle", "sliding_tackle",
        )
        if col in row and pd.notna(row[col])
    }
    profile["skills"] = skills
    profile["preferred_foot"] = (
        row["preferred_foot"] if pd.notna(row.get("preferred_foot")) else None
    )
    jersey = pd.to_numeric(pd.Series([row.get("jersey_number")]),
                           errors="coerce").iloc[0]
    profile["jersey_number"] = int(jersey) if pd.notna(jersey) else None
    return profile


# ---------------------------------------------------------------------------
# 4. Competition queries
# ---------------------------------------------------------------------------

def standings(
    store: DataStore,
    season: int | str,
    competition: str = "serie a",
) -> dict[str, Any]:
    """League table calculated from match results (3 pts win, 1 pt draw).

    Tie-breakers follow CBF convention: wins, goal difference, goals for.
    For Série A the leader is flagged champion and the bottom four relegated.
    """
    comp_key = _resolve_competition(competition) or "serie a"
    year = int(str(season).strip())
    df = _filter(store, competition=comp_key, season=year)
    if df.empty:
        raise QueryError(f"No matches for {comp_key} season {year}.")

    table: dict[str, dict[str, int]] = {}
    for _, row in df.iterrows():
        for key in (row["home"], row["away"]):
            table.setdefault(key, {"played": 0, "wins": 0, "draws": 0,
                                   "losses": 0, "gf": 0, "ga": 0})
        h, a = table[row["home"]], table[row["away"]]
        hg, ag = int(row["home_goals"]), int(row["away_goals"])
        h["played"] += 1
        a["played"] += 1
        h["gf"] += hg
        h["ga"] += ag
        a["gf"] += ag
        a["ga"] += hg
        if hg > ag:
            h["wins"] += 1
            a["losses"] += 1
        elif hg < ag:
            a["wins"] += 1
            h["losses"] += 1
        else:
            h["draws"] += 1
            a["draws"] += 1

    rows = []
    for key, t in table.items():
        points = 3 * t["wins"] + t["draws"]
        rows.append({
            "team": store.display_team(key),
            "team_key": key,
            "played": t["played"],
            "wins": t["wins"],
            "draws": t["draws"],
            "losses": t["losses"],
            "goals_for": t["gf"],
            "goals_against": t["ga"],
            "goal_difference": t["gf"] - t["ga"],
            "points": points,
        })
    rows.sort(key=lambda r: (-r["points"], -r["wins"],
                             -r["goal_difference"], -r["goals_for"], r["team"]))
    for i, row in enumerate(rows, start=1):
        row["position"] = i
    if comp_key == "serie a" and rows:
        rows[0]["champion"] = True
        for row in rows[-4:]:
            row["relegated"] = True
    return {
        "competition": COMPETITIONS.get(comp_key, {}).get("display", comp_key),
        "competition_key": comp_key,
        "season": year,
        "teams": len(rows),
        "matches": len(df),
        "standings": rows,
    }


def top_scoring_teams(
    store: DataStore,
    competition: str | None = None,
    season: int | str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Teams ranked by goals scored."""
    df = _filter(store, competition=competition, season=season)
    goals: dict[str, list[int]] = {}
    for _, row in df.iterrows():
        goals.setdefault(row["home"], [0, 0])
        goals.setdefault(row["away"], [0, 0])
        goals[row["home"]][0] += int(row["home_goals"])
        goals[row["away"]][0] += int(row["away_goals"])
        goals[row["home"]][1] += 1
        goals[row["away"]][1] += 1
    ranking = sorted(
        (
            {
                "team": store.display_team(k),
                "team_key": k,
                "goals": v[0],
                "matches": v[1],
                "goals_per_match": round(v[0] / v[1], 2) if v[1] else 0.0,
            }
            for k, v in goals.items()
        ),
        key=lambda r: (-r["goals"], -r["goals_per_match"]),
    )
    return {"total_teams": len(ranking), "teams": ranking[:limit]}


def list_competitions(store: DataStore) -> dict[str, Any]:
    """Every competition in the store with seasons and match counts."""
    comps = []
    for comp in store.competitions:
        df = store.matches[store.matches["competition"] == comp]
        played = df[df["home_goals"].notna()]
        seasons = sorted(int(s) for s in df["season"].dropna().unique())
        comps.append({
            "competition": COMPETITIONS.get(comp, {}).get("display", comp),
            "competition_key": comp,
            "seasons": seasons,
            "matches": len(played),
        })
    return {"competitions": comps}


def list_teams(
    store: DataStore,
    competition: str | None = None,
    season: int | str | None = None,
) -> dict[str, Any]:
    """Canonical team names, optionally scoped to competition/season."""
    if competition or season:
        df = _filter(store, competition=competition, season=season,
                     played_only=False)
        keys = sorted(set(df["home"]) | set(df["away"]))
    else:
        keys = store.teams
    return {"total": len(keys),
            "teams": [store.display_team(k) for k in keys]}


def dataset_summary(store: DataStore) -> dict[str, Any]:
    """Row counts per source file plus unified-store totals."""
    return {
        "sources": dict(store.source_row_counts),
        "unified_matches": len(store.matches),
        "played_matches": int(store.matches["home_goals"].notna().sum()),
        "players": len(store.players),
        "teams": len(store.teams),
        "competitions": store.competitions,
        "seasons_by_competition": {
            comp: store.seasons(comp) for comp in store.competitions
        },
    }


# ---------------------------------------------------------------------------
# 5. Statistical analysis
# ---------------------------------------------------------------------------

def competition_stats(
    store: DataStore,
    competition: str | None = None,
    season: int | str | None = None,
) -> dict[str, Any]:
    """Goals averages and home/draw/away splits (overall or per competition)."""
    df = _filter(store, competition=competition, season=season)
    if df.empty:
        raise QueryError("No matches found for the given filters.")
    total_goals = df["home_goals"].astype(float) + df["away_goals"].astype(float)
    home_wins = int((df["home_goals"] > df["away_goals"]).sum())
    draws = int((df["home_goals"] == df["away_goals"]).sum())
    away_wins = int((df["home_goals"] < df["away_goals"]).sum())
    n = len(df)
    comp_key = _resolve_competition(competition)
    return {
        "competition": COMPETITIONS.get(comp_key, {}).get("display", "All competitions")
        if comp_key else "All competitions",
        "season": int(str(season).strip()) if season is not None and str(season).strip() else None,
        "matches": n,
        "total_goals": int(total_goals.sum()),
        "avg_goals_per_match": round(float(total_goals.mean()), 2),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_rate": round(100.0 * home_wins / n, 1),
        "draw_rate": round(100.0 * draws / n, 1),
        "away_win_rate": round(100.0 * away_wins / n, 1),
    }


def biggest_wins(
    store: DataStore,
    competition: str | None = None,
    season: int | str | None = None,
    team: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Largest victory margins in the (filtered) dataset."""
    df = _filter(store, team=team, competition=competition, season=season).copy()
    df["margin"] = (df["home_goals"].astype(float) - df["away_goals"].astype(float)).abs()
    df["total_goals"] = df["home_goals"].astype(float) + df["away_goals"].astype(float)
    df = df.sort_values(["margin", "total_goals", "date"],
                        ascending=[False, False, False])
    return {
        "matches": [_match_row(store, row) | {"margin": int(row["margin"])}
                    for _, row in df.head(limit).iterrows()]
    }


def best_home_records(
    store: DataStore,
    competition: str | None = None,
    season: int | str | None = None,
    min_matches: int = 5,
    limit: int = 10,
) -> dict[str, Any]:
    """Teams ranked by home win rate (minimum match threshold)."""
    df = _filter(store, competition=competition, season=season)
    records = {}
    for key, group in df.groupby("home"):
        stats = _result_counts(group, key)
        if stats["matches"] >= min_matches:
            records[key] = stats
    ranking = sorted(
        (
            {"team": store.display_team(k), "team_key": k, **v}
            for k, v in records.items()
        ),
        key=lambda r: (-r["win_rate"], -r["wins"]),
    )
    return {"teams": ranking[:limit]}


def best_away_records(
    store: DataStore,
    competition: str | None = None,
    season: int | str | None = None,
    min_matches: int = 5,
    limit: int = 10,
) -> dict[str, Any]:
    """Teams ranked by away win rate (minimum match threshold)."""
    df = _filter(store, competition=competition, season=season)
    records = {}
    for key, group in df.groupby("away"):
        stats = _result_counts(group, key)
        if stats["matches"] >= min_matches:
            records[key] = stats
    ranking = sorted(
        (
            {"team": store.display_team(k), "team_key": k, **v}
            for k, v in records.items()
        ),
        key=lambda r: (-r["win_rate"], -r["wins"]),
    )
    return {"teams": ranking[:limit]}


def season_comparison(
    store: DataStore,
    competition: str,
    season_a: int | str,
    season_b: int | str,
) -> dict[str, Any]:
    """Side-by-side aggregate stats for two seasons of a competition."""
    a = competition_stats(store, competition, season_a)
    b = competition_stats(store, competition, season_b)
    return {
        "competition": a["competition"],
        "season_a": a,
        "season_b": b,
        "avg_goals_delta": round(
            b["avg_goals_per_match"] - a["avg_goals_per_match"], 2
        ),
    }
