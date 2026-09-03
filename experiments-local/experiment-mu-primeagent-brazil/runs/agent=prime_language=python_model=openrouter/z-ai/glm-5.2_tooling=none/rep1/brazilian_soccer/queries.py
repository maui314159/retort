"""
Context block
=============
Module: brazilian_soccer.queries
Purpose: Pure-Python query layer over the normalized ``DataStore`` produced by
         ``brazilian_soccer.data_loader``. Every public function returns plain
         JSON-serializable Python objects (dicts/lists/scalars) so they can be
         served directly by the MCP tools in ``server.py`` and asserted against
         in the pytest BDD/GWT suite.

Capabilities implemented (mapped to REQUIREMENTS.json):
  R3  find_matches ........ filter by team (home / away / either)
  R4  find_matches ........ filter by date range and/or season
  R5  find_matches ........ filter by competition (spans all match files)
  R6  team_statistics ..... win/loss/draw record + goals for/against
  R7  search_players ...... search FIFA players by name
  R8  search_players ...... filter players by nationality and/or club w/ ratings
  R9  standings ........... season standings computed from match results
  R10 statistics .......... aggregate stats (avg goals, home/away, biggest wins)
  R11 head_to_head ........ head-to-head W/L/D between two teams

This module has no MCP dependency; it is imported by ``server.py`` and the
test suite.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import numpy as np

from .data_loader import (
    DataStore,
    get_store,
    canonical_competition,
    normalize_team,
)


# ---------------------------------------------------------------------------
# Output sanitization
# ---------------------------------------------------------------------------

def _clean(value: Any) -> Any:
    """Convert pandas/numpy scalars and Timestamps to JSON-safe Python values."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.date().isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if np.isnan(v) else v
    if isinstance(value, float):
        return None if np.isnan(value) else value
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if value is pd.NA:
        return None
    return value


def _row_to_dict(row: pd.Series, columns: list) -> dict:
    out: dict = {}
    for c in columns:
        out[c] = _clean(row[c]) if c in row.index else None
    return out


# ---------------------------------------------------------------------------
# Match filtering
# ---------------------------------------------------------------------------

def _filter_matches(
    store: DataStore,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[Any] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: str = "either",
) -> pd.DataFrame:
    """Apply every supported filter and return the matching match rows."""
    m = store.matches

    # Competition filter (R5) spans all match files via the canonical column.
    if competition:
        comp = canonical_competition(competition)
        m = m[m["competition"] == comp]

    # Season filter (R4).
    if season is not None:
        season_int = pd.to_numeric(season, errors="coerce")
        if pd.isna(season_int):
            return m.iloc[0:0]
        m = m[m["season"] == int(season_int)]

    # Date range filter (R4).
    if date_from is not None:
        lo = pd.to_datetime(date_from, errors="coerce")
        if lo is not pd.NaT:
            m = m[m["date"] >= lo]
    if date_to is not None:
        hi = pd.to_datetime(date_to, errors="coerce")
        if hi is not pd.NaT:
            m = m[m["date"] <= hi]

    # Team filter (R3): home / away / either, using normalized keys.
    if team:
        tkey = normalize_team(team)
        if not tkey:
            return m.iloc[0:0]
        if venue == "home":
            m = m[m["home_team_norm"] == tkey]
        elif venue == "away":
            m = m[m["away_team_norm"] == tkey]
        else:  # either
            m = m[(m["home_team_norm"] == tkey) | (m["away_team_norm"] == tkey)]

    # Opponent filter (used by head-to-head / vs queries).
    if opponent:
        okey = normalize_team(opponent)
        if not okey:
            return m.iloc[0:0]
        m = m[
            ((m["home_team_norm"] == okey) | (m["away_team_norm"] == okey))
            & (m["home_team_norm"] != m["away_team_norm"])
        ]

    return m


_MATCH_COLS = [
    "date", "season", "competition", "home_team", "away_team",
    "home_goal", "away_goal", "round", "stage", "source",
]


def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[Any] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: str = "either",
    limit: Optional[int] = 50,
    store: Optional[DataStore] = None,
) -> list:
    """Return match records matching the given criteria (R3, R4, R5).

    ``team`` is matched on the normalized key so spelling variants
    (``Palmeiras-SP`` vs ``Palmeiras``) and accents (``São Paulo`` vs
    ``Sao Paulo``) are handled. ``venue`` selects home/away/either.
    ``competition`` accepts aliases (``Serie A`` -> Brasileirao).
    """
    store = store or get_store()
    sub = _filter_matches(
        store, team=team, opponent=opponent, competition=competition,
        season=season, date_from=date_from, date_to=date_to, venue=venue,
    )
    sub = sub.sort_values("date", na_position="last")
    if limit is not None:
        sub = sub.head(int(limit))
    return [_row_to_dict(r, _MATCH_COLS) for _, r in sub.iterrows()]


# ---------------------------------------------------------------------------
# Team statistics (R6)
# ---------------------------------------------------------------------------

def team_statistics(
    team: str,
    season: Optional[Any] = None,
    competition: Optional[str] = None,
    venue: str = "either",
    store: Optional[DataStore] = None,
) -> dict:
    """Return aggregated W/L/D and goals for/against for a team (R6)."""
    store = store or get_store()
    tkey = normalize_team(team)
    sub = _filter_matches(
        store, team=team, competition=competition, season=season, venue=venue,
    )

    wins = draws = losses = 0
    gf = ga = 0
    played = 0
    by_competition: dict = {}

    for _, r in sub.iterrows():
        hg, ag = r["home_goal"], r["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue  # unplayed match - listed but not counted in aggregates
        is_home = r["home_team_norm"] == tkey
        team_gf = int(hg) if is_home else int(ag)
        team_ga = int(ag) if is_home else int(hg)
        played += 1
        gf += team_gf
        ga += team_ga
        if team_gf > team_ga:
            wins += 1
            res = "wins"
        elif team_gf < team_ga:
            losses += 1
            res = "losses"
        else:
            draws += 1
            res = "draws"
        comp = str(r["competition"])
        bc = by_competition.setdefault(
            comp, {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
                   "goals_for": 0, "goals_against": 0},
        )
        bc["matches"] += 1
        bc[res] += 1
        bc["goals_for"] += team_gf
        bc["goals_against"] += team_ga

    win_rate = round(wins / played, 4) if played else 0.0
    season_val = None
    if season is not None:
        s = pd.to_numeric(season, errors="coerce")
        season_val = None if pd.isna(s) else int(s)
    return {
        "team": team,
        "season": season_val,
        "competition": competition,
        "venue": venue,
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "win_rate": win_rate,
        "by_competition": by_competition,
    }


# ---------------------------------------------------------------------------
# Head-to-head (R11)
# ---------------------------------------------------------------------------

def head_to_head(
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    season: Optional[Any] = None,
    limit: Optional[int] = None,
    store: Optional[DataStore] = None,
) -> dict:
    """Return head-to-head W/L/D between two named teams (R11)."""
    store = store or get_store()
    a_key, b_key = normalize_team(team_a), normalize_team(team_b)
    sub = _filter_matches(store, competition=competition, season=season)
    # Both teams must be present, one as home and one as away.
    sub = sub[
        ((sub["home_team_norm"] == a_key) & (sub["away_team_norm"] == b_key))
        | ((sub["home_team_norm"] == b_key) & (sub["away_team_norm"] == a_key))
    ]
    sub = sub.sort_values("date", na_position="last")

    a_wins = b_wins = draws = 0
    a_gf = b_gf = 0
    played = 0
    matches: list = []
    for _, r in sub.iterrows():
        hg, ag = r["home_goal"], r["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        if r["home_team_norm"] == a_key:
            a_g, b_g = int(hg), int(ag)
        else:
            a_g, b_g = int(ag), int(hg)
        a_gf += a_g
        b_gf += b_g
        played += 1
        if a_g > b_g:
            a_wins += 1
        elif a_g < b_g:
            b_wins += 1
        else:
            draws += 1
        matches.append({
            "date": _clean(r["date"]),
            "season": _clean(r["season"]),
            "competition": _clean(r["competition"]),
            "home_team": _clean(r["home_team"]),
            "away_team": _clean(r["away_team"]),
            "home_goal": int(hg),
            "away_goal": int(ag),
        })
    if limit is not None:
        matches = matches[: int(limit)]
    return {
        "team_a": team_a,
        "team_b": team_b,
        "matches_played": played,
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_gf,
        "team_b_goals": b_gf,
        "matches": matches,
    }


# ---------------------------------------------------------------------------
# Players (R7, R8)
# ---------------------------------------------------------------------------

# FIFA position codes grouped into outfield roles for the position filter.
_POSITION_GROUPS = {
    "GK": {"GK"},
    "GOALKEEPER": {"GK"},
    "DEF": {"CB", "RB", "LB", "RWB", "LWB", "RCB", "LCB"},
    "DEFENDER": {"CB", "RB", "LB", "RWB", "LWB", "RCB", "LCB"},
    "MF": {"CM", "CDM", "CAM", "RM", "LM", "RCM", "LCM", "RDM", "LDM",
           "RAM", "LAM"},
    "MIDFIELDER": {"CM", "CDM", "CAM", "RM", "LM", "RCM", "LCM", "RDM", "LDM",
                   "RAM", "LAM"},
    "MID": {"CM", "CDM", "CAM", "RM", "LM", "RCM", "LCM", "RDM", "LDM",
            "RAM", "LAM"},
    "FW": {"ST", "CF", "RF", "LF", "RS", "LS", "RW", "LW"},
    "FORWARD": {"ST", "CF", "RF", "LF", "RS", "LS", "RW", "LW"},
    "STRIKER": {"ST", "CF", "RF", "LF", "RS", "LS"},
}


def _player_row(r: pd.Series) -> dict:
    return {
        "id": _clean(r["ID"]),
        "name": _clean(r["Name"]),
        "age": _clean(r["Age"]),
        "nationality": _clean(r["Nationality"]),
        "overall": _clean(r["Overall"]),
        "potential": _clean(r["Potential"]),
        "club": _clean(r["Club"]),
        "position": _clean(r["Position"]),
        "jersey_number": _clean(r["Jersey Number"]),
        "height": _clean(r["Height"]),
        "weight": _clean(r["Weight"]),
    }


def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    max_overall: Optional[int] = None,
    limit: Optional[int] = 50,
    sort_by: str = "overall",
    desc: bool = True,
    store: Optional[DataStore] = None,
) -> list:
    """Search the FIFA player database (R7, R8).

    ``name`` is a case-insensitive substring match. ``nationality`` and
    ``club`` are matched on the normalized key (accent/case-insensitive).
    ``position`` may be a FIFA code (e.g. ``"ST"``) or a role group
    (``"GK"``, ``"DEF"``, ``"MF"``, ``"FW"`` / ``"forward"``).
    Results are sorted by ``sort_by`` (default ``overall`` rating).
    """
    store = store or get_store()
    p = store.players

    if name:
        p = p[p["Name"].astype(str).str.lower()
              .str.contains(str(name).lower(), na=False)]
    if nationality:
        nkey = normalize_team(nationality)
        p = p[p["Nationality_norm"] == nkey]
    if club:
        ckey = normalize_team(club)
        p = p[p["Club_norm"] == ckey]
    if position:
        grp = _POSITION_GROUPS.get(position.upper())
        if grp is not None:
            p = p[p["Position"].astype(str).isin(grp)]
        else:
            p = p[p["Position"].astype(str).str.upper() == position.upper()]
    if min_overall is not None:
        p = p[p["Overall"] >= float(min_overall)]
    if max_overall is not None:
        p = p[p["Overall"] <= float(max_overall)]

    sort_col = sort_by if sort_by in p.columns else "Overall"
    p = p.sort_values(by=sort_col, ascending=not desc)
    if limit is not None:
        p = p.head(int(limit))
    return [_player_row(r) for _, r in p.iterrows()]


def players_by_club(
    nationality: Optional[str] = None,
    store: Optional[DataStore] = None,
) -> list:
    """Aggregate players per club with average/max rating.

    Optionally restricted to a nationality - useful for "Brazilian players at
    Brazilian clubs" style questions (R8).
    """
    store = store or get_store()
    p = store.players
    if nationality:
        p = p[p["Nationality_norm"] == normalize_team(nationality)]
    p = p.dropna(subset=["Club"])
    agg = (
        p.groupby("Club")
        .agg(players=("ID", "size"), avg_overall=("Overall", "mean"),
             max_overall=("Overall", "max"))
        .reset_index()
        .sort_values("players", ascending=False)
    )
    out = []
    for _, r in agg.iterrows():
        out.append({
            "club": _clean(r["Club"]),
            "players": int(r["players"]),
            "avg_overall": round(float(r["avg_overall"]), 2)
            if not pd.isna(r["avg_overall"]) else None,
            "max_overall": _clean(r["max_overall"]),
        })
    return out


# ---------------------------------------------------------------------------
# Competition standings (R9)
# ---------------------------------------------------------------------------

# Priority order for choosing a single source per (season, competition) so the
# standings are never double-counted across overlapping datasets.
_SOURCE_PRIORITY = [
    "Brasileirao_Matches.csv",
    "novo_campeonato_brasileiro.csv",
    "BR-Football-Dataset.csv",
]


def _standings_source(store: DataStore, competition: str, season: int):
    sub = store.matches[(store.matches["competition"] == competition)
                        & (store.matches["season"] == season)]
    if sub.empty:
        return None
    for src in _SOURCE_PRIORITY:
        if (sub["source"] == src).any():
            return src
    return sub["source"].mode().iloc[0]


def standings(
    season: Any,
    competition: str = "Brasileirao",
    store: Optional[DataStore] = None,
) -> list:
    """Compute season standings from match results (R9).

    Points: 3 for a win, 1 for a draw. Teams are ranked by points, then goal
    difference, then goals for. The standings are *computed* from the matches
    in a single (non-overlapping) source per season, never hardcoded.
    """
    store = store or get_store()
    comp = canonical_competition(competition)
    season_int = int(pd.to_numeric(season, errors="coerce"))

    src = _standings_source(store, comp, season_int)
    if src is None:
        return []

    sub = store.matches[
        (store.matches["competition"] == comp)
        & (store.matches["season"] == season_int)
        & (store.matches["source"] == src)
    ]

    table: dict = {}
    for _, r in sub.iterrows():
        hg, ag = r["home_goal"], r["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        home = r["home_team_norm"]
        away = r["away_team_norm"]
        if not home or not away:
            continue
        h_entry = table.setdefault(home, {"team": r["home_team"],
                                          "played": 0, "wins": 0, "draws": 0,
                                          "losses": 0, "goals_for": 0,
                                          "goals_against": 0})
        a_entry = table.setdefault(away, {"team": r["away_team"],
                                          "played": 0, "wins": 0, "draws": 0,
                                          "losses": 0, "goals_for": 0,
                                          "goals_against": 0})
        h_entry["played"] += 1
        a_entry["played"] += 1
        h_entry["goals_for"] += int(hg)
        h_entry["goals_against"] += int(ag)
        a_entry["goals_for"] += int(ag)
        a_entry["goals_against"] += int(hg)
        if int(hg) > int(ag):
            h_entry["wins"] += 1
            a_entry["losses"] += 1
        elif int(hg) < int(ag):
            h_entry["losses"] += 1
            a_entry["wins"] += 1
        else:
            h_entry["draws"] += 1
            a_entry["draws"] += 1

    rows = []
    for entry in table.values():
        pts = entry["wins"] * 3 + entry["draws"]
        gd = entry["goals_for"] - entry["goals_against"]
        rows.append({
            "team": entry["team"],
            "played": entry["played"],
            "wins": entry["wins"],
            "draws": entry["draws"],
            "losses": entry["losses"],
            "goals_for": entry["goals_for"],
            "goals_against": entry["goals_against"],
            "goal_difference": gd,
            "points": pts,
        })
    rows.sort(key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]),
              reverse=True)
    for i, row in enumerate(rows, 1):
        row["position"] = i
        row["champion"] = (i == 1)
    return rows


# ---------------------------------------------------------------------------
# Statistical analysis (R10)
# ---------------------------------------------------------------------------

def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[Any] = None,
    limit: int = 10,
    store: Optional[DataStore] = None,
) -> list:
    """Return the largest victory margins in the dataset (R10)."""
    store = store or get_store()
    sub = _filter_matches(store, competition=competition, season=season)
    sub = sub.dropna(subset=["home_goal", "away_goal"])
    if sub.empty:
        return []
    sub = sub.copy()
    sub["margin"] = (sub["home_goal"].astype(int) - sub["away_goal"].astype(int)).abs()
    sub = sub.sort_values(["margin", "date"], ascending=[False, True])
    out = []
    for _, r in sub.head(int(limit)).iterrows():
        hg, ag = int(r["home_goal"]), int(r["away_goal"])
        out.append({
            "date": _clean(r["date"]),
            "season": _clean(r["season"]),
            "competition": _clean(r["competition"]),
            "home_team": _clean(r["home_team"]),
            "away_team": _clean(r["away_team"]),
            "score": f"{hg}-{ag}",
            "margin": abs(hg - ag),
            "winner": _clean(r["home_team"]) if hg > ag else _clean(r["away_team"]),
        })
    return out


def statistics(
    competition: Optional[str] = None,
    season: Optional[Any] = None,
    store: Optional[DataStore] = None,
) -> dict:
    """Aggregate statistics over the dataset (R10).

    Includes total matches, average goals per match, home/draw/away win
    rates and the biggest victories.
    """
    store = store or get_store()
    sub = _filter_matches(store, competition=competition, season=season)
    scored = sub.dropna(subset=["home_goal", "away_goal"])
    total = len(scored)
    home_wins = int(((scored["home_goal"] > scored["away_goal"])).sum())
    draws = int(((scored["home_goal"] == scored["away_goal"])).sum())
    away_wins = int(((scored["home_goal"] < scored["away_goal"])).sum())
    total_goals = int(scored["home_goal"].sum() + scored["away_goal"].sum())

    def _rate(x):
        return round(x / total, 4) if total else 0.0

    return {
        "competition": competition,
        "season": None if season is None else int(pd.to_numeric(season, errors="coerce"))
            if not pd.isna(pd.to_numeric(season, errors="coerce")) else None,
        "matches": total,
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / total, 3) if total else 0.0,
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_rate": _rate(home_wins),
        "draw_rate": _rate(draws),
        "away_win_rate": _rate(away_wins),
        "biggest_wins": biggest_wins(competition=competition, season=season,
                                      limit=5, store=store),
    }


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def list_competitions(store: Optional[DataStore] = None) -> list:
    """Return the canonical competitions present in the data."""
    store = store or get_store()
    return store.competitions()


def list_seasons(competition: Optional[str] = None,
                 store: Optional[DataStore] = None) -> list:
    """Return the seasons available, optionally for one competition."""
    store = store or get_store()
    return store.seasons(competition)


def list_teams(competition: Optional[str] = None,
               season: Optional[Any] = None,
               store: Optional[DataStore] = None) -> list:
    """Return team display names, optionally filtered by competition/season."""
    store = store or get_store()
    sub = _filter_matches(store, competition=competition, season=season)
    names = pd.concat([sub["home_team"], sub["away_team"]], ignore_index=True)
    return sorted(n for n in names.dropna().unique().tolist() if n)


def team_competitions(team: str,
                       store: Optional[DataStore] = None) -> list:
    """Return the competitions a team has appeared in (R5 cross-file)."""
    store = store or get_store()
    tkey = normalize_team(team)
    sub = store.matches[
        (store.matches["home_team_norm"] == tkey)
        | (store.matches["away_team_norm"] == tkey)
    ]
    comps = sorted(sub["competition"].dropna().unique().tolist())
    return [{"competition": c,
             "matches": int((sub["competition"] == c).sum())} for c in comps]
