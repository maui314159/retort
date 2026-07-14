"""Pure query functions over the unified datasets.

CONTEXT
-------
Every function here takes the loaded :class:`~brazilian_soccer.data_loader.Data`
object plus user-supplied filters and returns plain Python data structures
(dicts / lists) -- never pandas frames.  This keeps the layer trivially
testable and lets :mod:`brazilian_soccer.server` focus on formatting.

Team arguments are *raw names* (``"Flamengo"``, ``"Atlético-MG"``) and are
resolved to canonical ids via ``data.resolve_team`` so that naming variants
match correctly (see :mod:`brazilian_soccer.normalize`).

Match dicts have the shape::

    {"date": "YYYY-MM-DD"|None, "competition": str, "home": str,
     "away": str, "home_goals": int|None, "away_goals": int|None,
     "season": int|None, "round": ..., "stage": ..., "arena": ...,
     "source": str}
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import pandas as pd

from .normalize import (
    POSITION_GROUPS,
    canonical_competition,
    position_group,
)

from .data_loader import (
    BRASILEIRAO_A,
    COPA_DO_BRASIL,
    LIBERTADORES,
)

# Traditional Brazilian derbies (canonical team ids) -- used by
# :func:`derby_matches`.  Pairs are unordered.
DERBIES = [
    ("flamengo rj", "fluminense rj", "Fla-Flu"),
    ("corinthians sp", "sao paulo sp", "Majestoso"),
    ("palmeiras sp", "corinthians sp", "Clássico Rei"),
    ("palmeiras sp", "sao paulo sp", "Choque Rei"),
    ("gremio rs", "internacional rs", "Grenal"),
    ("santos sp", "sao paulo sp", "San-São"),
    ("bahia ba", "vitoria ba", "Ba-Vi"),
    ("atletico mg", "cruzeiro mg", "Clássico Mineiro"),
    ("atletico pr", "coritiba pr", "Atle-Tiba"),
    ("sport pe", "nautico pe", "Clássico dos Clássicos"),
    ("cruzeiro mg", "atletico mg", "Clássico Mineiro"),
    ("vasco da gama rj", "flamengo rj", "Clássico dos Gigantes"),
    ("botafogo rj", "flamengo rj", "Clássico da Rivalidade"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finished(df: pd.DataFrame) -> pd.DataFrame:
    """Return only rows with both scores recorded."""
    mask = df["home_goals"].notna() & df["away_goals"].notna()
    return df[mask].copy()


def _date_str(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    try:
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _row_to_match(data, row) -> dict[str, Any]:
    return {
        "date": _date_str(row["date"]),
        "competition": row["competition"],
        "home": data.team_name(row["home_key"]) if row["home_key"] else row["home"],
        "away": data.team_name(row["away_key"]) if row["away_key"] else row["away"],
        "home_goals": (int(row["home_goals"])
                       if pd.notna(row["home_goals"]) else None),
        "away_goals": (int(row["away_goals"])
                       if pd.notna(row["away_goals"]) else None),
        "season": (int(row["season"]) if pd.notna(row["season"]) else None),
        "round": row["round"],
        "stage": row["stage"],
        "arena": row["arena"],
        "source": row["source"],
    }


def _matches_to_list(data, df: pd.DataFrame) -> list[dict[str, Any]]:
    return [_row_to_match(data, row) for _, row in df.iterrows()]


def _competition_filter(df: pd.DataFrame, competition) -> pd.DataFrame:
    if competition is None:
        return df
    canon = canonical_competition(competition)
    if canon is None:
        return df
    # Match canonical label, or a tournament substring (e.g. "Serie A").
    mask = df["competition"].eq(canon)
    if not mask.any():
        mask = df["competition"].str.contains(canon, case=False, na=False)
    return df[mask]


def _team_mask(df: pd.DataFrame, team_key: str, venue: str) -> pd.Series:
    if venue == "home":
        return df["home_key"].eq(team_key)
    if venue == "away":
        return df["away_key"].eq(team_key)
    return df["home_key"].eq(team_key) | df["away_key"].eq(team_key)


def _parse_date_bound(value):
    if value is None:
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(value)
    return pd.to_datetime(value, errors="coerce")


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------

def search_matches(data, team=None, opponent=None, competition=None,
                   season=None, start_date=None, end_date=None,
                   venue: str = "either", limit: int = 50,
                   include_unplayed: bool = False) -> list[dict[str, Any]]:
    """Search matches by team, opponent, competition, season and/or date range.

    *team* and *opponent* are raw names.  *venue* controls whether *team*
    must be home, away or either.  Results are newest-first, capped at
    *limit* (0 = no cap).
    """
    df = data.matches
    if not include_unplayed:
        df = _finished(df)
    if competition is not None:
        df = _competition_filter(df, competition)
    if season is not None:
        df = df[df["season"].eq(int(season))]
    if team is not None:
        tk = data.resolve_team(team)
        df = df[_team_mask(df, tk, venue)]
        if opponent is not None:
            ok = data.resolve_team(opponent)
            df = df[(df["home_key"].eq(ok)) | (df["away_key"].eq(ok))]
    start = _parse_date_bound(start_date)
    end = _parse_date_bound(end_date)
    if start is not None:
        df = df[df["date"].isna() | (df["date"] >= start)]
    if end is not None:
        df = df[df["date"].isna() | (df["date"] <= end)]
    df = df.sort_values("date", ascending=False, kind="mergesort",
                        na_position="last")
    if limit and limit > 0:
        df = df.head(limit)
    return _matches_to_list(data, df)


def last_match(data, team_a, team_b) -> Optional[dict[str, Any]]:
    """Return the most recent finished match between two teams, or None."""
    a = data.resolve_team(team_a)
    b = data.resolve_team(team_b)
    df = _finished(data.matches)
    mask = (((df["home_key"].eq(a)) & (df["away_key"].eq(b)))
            | ((df["home_key"].eq(b)) & (df["away_key"].eq(a))))
    df = df[mask].sort_values("date", ascending=False, kind="mergesort",
                              na_position="last")
    if df.empty:
        return None
    return _row_to_match(data, df.iloc[0])


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------

def _team_result(row, team_key: str) -> str:
    """Return 'W'/'D'/'L' from *team_key*'s perspective."""
    hg, ag = row["home_goals"], row["away_goals"]
    if pd.isna(hg) or pd.isna(ag):
        return "?"
    if row["home_key"] == team_key:
        home, away = hg, ag
    else:
        home, away = ag, hg
    if home > away:
        return "W"
    if home < away:
        return "L"
    return "D"


def team_stats(data, team, season=None, competition=None,
               venue: Optional[str] = None) -> dict[str, Any]:
    """Aggregate record for *team* with optional filters.

    *venue*: None (all), 'home', or 'away'.  Returns wins/draws/losses,
    goals for/against, points (3 per win) and win rate, plus a per-venue
    breakdown when *venue* is None.
    """
    tk = data.resolve_team(team)
    df = _finished(data.matches)
    df = df[_team_mask(df, tk, "either")]
    if season is not None:
        df = df[df["season"].eq(int(season))]
    if competition is not None:
        df = _competition_filter(df, competition)
    if venue in ("home", "away"):
        df = df[_team_mask(df, tk, venue)]

    def _agg(frame: pd.DataFrame) -> dict[str, Any]:
        if frame.empty:
            return {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0, "points": 0,
                    "win_rate": 0.0}
        wins = draws = losses = 0
        gf = ga = 0
        for _, r in frame.iterrows():
            res = _team_result(r, tk)
            if r["home_key"] == tk:
                gf += int(r["home_goals"])
                ga += int(r["away_goals"])
            else:
                gf += int(r["away_goals"])
                ga += int(r["home_goals"])
            if res == "W":
                wins += 1
            elif res == "D":
                draws += 1
            elif res == "L":
                losses += 1
        matches = len(frame)
        points = 3 * wins + draws
        rate = wins / matches if matches else 0.0
        return {"matches": matches, "wins": wins, "draws": draws,
                "losses": losses, "goals_for": gf, "goals_against": ga,
                "points": points, "win_rate": rate}

    overall = _agg(df)
    result = {
        "team": data.team_name(tk),
        "team_key": tk,
        **overall,
    }
    if venue is None:
        home_df = df[_team_mask(df, tk, "home")]
        away_df = df[_team_mask(df, tk, "away")]
        result["home"] = _agg(home_df)
        result["away"] = _agg(away_df)
    return result


def head_to_head(data, team_a, team_b, competition=None,
                 season=None) -> dict[str, Any]:
    """Head-to-head record between two teams."""
    a = data.resolve_team(team_a)
    b = data.resolve_team(team_b)
    df = _finished(data.matches)
    mask = (((df["home_key"].eq(a)) & (df["away_key"].eq(b)))
            | ((df["home_key"].eq(b)) & (df["away_key"].eq(a))))
    df = df[mask]
    if competition is not None:
        df = _competition_filter(df, competition)
    if season is not None:
        df = df[df["season"].eq(int(season))]

    a_wins = b_wins = draws = 0
    a_gf = b_gf = 0
    for _, r in df.iterrows():
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        # Determine goals from each team's perspective.
        if r["home_key"] == a:
            agf, bgf = hg, ag
        else:
            agf, bgf = ag, hg
        a_gf += agf
        b_gf += bgf
        if hg == ag:
            draws += 1
        elif (r["home_key"] == a) == (hg > ag):
            a_wins += 1
        else:
            b_wins += 1

    df = df.sort_values("date", ascending=False, kind="mergesort",
                        na_position="last")
    return {
        "team_a": data.team_name(a),
        "team_b": data.team_name(b),
        "matches": len(df),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_gf,
        "team_b_goals": b_gf,
        "matches_list": _matches_to_list(data, df),
    }


def team_competitions(data, team) -> dict[str, int]:
    """Map competition -> match count for *team* (finished matches)."""
    tk = data.resolve_team(team)
    df = _finished(data.matches)
    df = df[_team_mask(df, tk, "either")]
    if df.empty:
        return {}
    return df["competition"].value_counts().to_dict()


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------

def competition_standings(data, competition, season,
                          top: Optional[int] = None) -> list[dict[str, Any]]:
    """Compute league-style standings for one competition+season.

    Uses 3 points per win, 1 per draw.  Sorted by points, then goal
    difference, then goals for.  Only competitions played as a league
    (Brasileirão Serie A/B/C) produce meaningful tables; cup/knockout
    competitions still return a points-ranked list.
    """
    canon = canonical_competition(competition) or competition
    df = _finished(data.matches)
    df = df[df["competition"].eq(canon) & df["season"].eq(int(season))]
    if df.empty:
        return []

    stats: dict[str, dict[str, int]] = {}
    for _, r in df.iterrows():
        for key in (r["home_key"], r["away_key"]):
            stats.setdefault(key, {"played": 0, "wins": 0, "draws": 0,
                                   "losses": 0, "goals_for": 0,
                                   "goals_against": 0, "points": 0})
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        h, a = r["home_key"], r["away_key"]
        stats[h]["played"] += 1
        stats[a]["played"] += 1
        stats[h]["goals_for"] += hg
        stats[h]["goals_against"] += ag
        stats[a]["goals_for"] += ag
        stats[a]["goals_against"] += hg
        if hg > ag:
            stats[h]["wins"] += 1
            stats[h]["points"] += 3
            stats[a]["losses"] += 1
        elif hg < ag:
            stats[a]["wins"] += 1
            stats[a]["points"] += 3
            stats[h]["losses"] += 1
        else:
            stats[h]["draws"] += 1
            stats[a]["draws"] += 1
            stats[h]["points"] += 1
            stats[a]["points"] += 1

    rows = []
    for key, s in stats.items():
        gd = s["goals_for"] - s["goals_against"]
        rows.append({
            "team": data.team_name(key),
            "team_key": key,
            "played": s["played"],
            "wins": s["wins"],
            "draws": s["draws"],
            "losses": s["losses"],
            "goals_for": s["goals_for"],
            "goals_against": s["goals_against"],
            "goal_diff": gd,
            "points": s["points"],
        })
    rows.sort(key=lambda r: (-r["points"], -r["goal_diff"], -r["goals_for"],
                             r["team"]))
    if top:
        rows = rows[:top]
    return rows


def competition_champion(data, competition, season) -> Optional[str]:
    """Return the display name of the standings leader (champion)."""
    table = competition_standings(data, competition, season, top=1)
    if not table:
        return None
    champ = table[0]
    return f"{champ['team']} - {champ['points']} pts ({champ['wins']}W, {champ['draws']}D, {champ['losses']}L)"


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def biggest_wins(data, competition=None, season=None,
                 limit: int = 10) -> list[dict[str, Any]]:
    """Largest goal-margin victories, biggest first."""
    df = _finished(data.matches)
    if competition is not None:
        df = _competition_filter(df, competition)
    if season is not None:
        df = df[df["season"].eq(int(season))]
    if df.empty:
        return []
    df = df.copy()
    df["margin"] = (df["home_goals"] - df["away_goals"]).abs()
    df = df.sort_values(["margin", "date"], ascending=[False, False],
                        kind="mergesort")
    df = df.head(limit)
    out = []
    for _, r in df.iterrows():
        hg, ag = int(r["home_goals"]), int(r["away_goals"])
        out.append({
            "date": _date_str(r["date"]),
            "competition": r["competition"],
            "home": data.team_name(r["home_key"]),
            "away": data.team_name(r["away_key"]),
            "home_goals": hg,
            "away_goals": ag,
            "margin": int(r["margin"]),
        })
    return out


def average_goals(data, competition=None, season=None) -> dict[str, Any]:
    """Average goals per match plus home/away/draw win rates."""
    df = _finished(data.matches)
    if competition is not None:
        df = _competition_filter(df, competition)
    if season is not None:
        df = df[df["season"].eq(int(season))]
    if df.empty:
        return {"matches": 0, "avg_goals": 0.0, "home_win_rate": 0.0,
                "away_win_rate": 0.0, "draw_rate": 0.0}
    n = len(df)
    total = int(df["home_goals"].sum() + df["away_goals"].sum())
    home_wins = int((df["home_goals"] > df["away_goals"]).sum())
    away_wins = int((df["home_goals"] < df["away_goals"]).sum())
    draws = int((df["home_goals"] == df["away_goals"]).sum())
    return {
        "matches": n,
        "avg_goals": round(total / n, 3),
        "total_goals": total,
        "home_win_rate": round(home_wins / n, 4),
        "away_win_rate": round(away_wins / n, 4),
        "draw_rate": round(draws / n, 4),
    }


def best_record(data, venue: str = "home", competition=None, season=None,
                limit: int = 5, min_matches: int = 10) -> list[dict[str, Any]]:
    """Rank teams by win rate in a given *venue* ('home' or 'away').

    Only teams with at least *min_matches* qualifying matches are ranked.
    """
    df = _finished(data.matches)
    if competition is not None:
        df = _competition_filter(df, competition)
    if season is not None:
        df = df[df["season"].eq(int(season))]
    if df.empty:
        return []
    side_col = "home_key" if venue == "home" else "away_key"
    gf = "home_goals" if venue == "home" else "away_goals"
    ga = "away_goals" if venue == "home" else "home_goals"

    teams = df[side_col].unique()
    rows = []
    for tk in teams:
        sub = df[df[side_col].eq(tk)]
        if len(sub) < min_matches:
            continue
        wins = int((sub[gf] > sub[ga]).sum())
        draws = int((sub[gf] == sub[ga]).sum())
        losses = int((sub[gf] < sub[ga]).sum())
        rows.append({
            "team": data.team_name(tk),
            "team_key": tk,
            "matches": len(sub),
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "win_rate": round(wins / len(sub), 4),
        })
    rows.sort(key=lambda r: (-r["win_rate"], -r["wins"], r["team"]))
    return rows[:limit]


def derby_matches(data, season=None, competition=None) -> list[dict[str, Any]]:
    """Return matches between traditional rival pairs (see :data:`DERBIES`)."""
    df = _finished(data.matches)
    if season is not None:
        df = df[df["season"].eq(int(season))]
    if competition is not None:
        df = _competition_filter(df, competition)
    pair_set = {(a, b) for a, b, _ in DERBIES}
    out = []
    for _, r in df.iterrows():
        key = (r["home_key"], r["away_key"])
        if key in pair_set or (key[1], key[0]) in pair_set:
            m = _row_to_match(data, r)
            for a, b, name in DERBIES:
                if {a, b} == {r["home_key"], r["away_key"]}:
                    m["derby"] = name
                    break
            out.append(m)
    out.sort(key=lambda m: (m["date"] or "", ), reverse=True)
    return out


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

_PLAYER_FIELDS = ["ID", "Name", "Age", "Nationality", "Overall", "Potential",
                  "Club", "Position", "Jersey Number"]


def _player_dict(row) -> dict[str, Any]:
    out = {}
    for f in _PLAYER_FIELDS:
        if f in row.index:
            v = row[f]
            if pd.isna(v):
                out[f] = None
            elif f in ("Overall", "Potential", "Age", "Jersey Number", "ID"):
                out[f] = int(v)
            else:
                out[f] = str(v)
        else:
            out[f] = None
    out["position_group"] = position_group(row.get("Position"))
    return out


def search_players(data, name=None, nationality=None, club=None,
                   position=None, position_group_name=None,
                   min_overall=None, limit: int = 50) -> list[dict[str, Any]]:
    """Search FIFA players by name/nationality/club/position/rating."""
    df = data.players
    if name is not None:
        df = df[df["Name"].str.contains(name, case=False, na=False)]
    if nationality is not None:
        df = df[df["Nationality"].str.contains(nationality, case=False,
                                               na=False)]
    if club is not None:
        ck = data.resolve_team(club)
        # Match either the resolved canonical id or the raw club substring.
        ck_mask = df["club_key"].eq(ck)
        sub_mask = df["Club"].str.contains(club, case=False, na=False)
        df = df[ck_mask | sub_mask]
    if position is not None:
        df = df[df["Position"].str.upper().eq(str(position).upper())]
    if position_group_name is not None:
        pg = position_group_name.upper()
        if pg not in POSITION_GROUPS:
            return []
        df = df[df["Position"].isin(POSITION_GROUPS[pg])]
    if min_overall is not None:
        df = df[df["Overall"].ge(int(min_overall))]
    df = df.sort_values("Overall", ascending=False, kind="mergesort")
    if limit and limit > 0:
        df = df.head(limit)
    return [_player_dict(row) for _, row in df.iterrows()]


def top_players(data, nationality=None, club=None, position_group_name=None,
                limit: int = 10) -> list[dict[str, Any]]:
    """Top-rated players (by FIFA Overall) with optional filters."""
    return search_players(data, nationality=nationality, club=club,
                          position_group_name=position_group_name,
                          limit=limit)


def players_at_club(data, club, position_group_name=None,
                    limit: int = 50) -> list[dict[str, Any]]:
    """All players at *club*, highest-rated first."""
    return search_players(data, club=club,
                          position_group_name=position_group_name,
                          limit=limit)


# ---------------------------------------------------------------------------
# Extended match statistics (BR-Football only)
# ---------------------------------------------------------------------------

def match_statistics(data, team=None, opponent=None, season=None,
                     limit: int = 20) -> list[dict[str, Any]]:
    """Return matches with extended stats (corners, shots, attacks).

    Only the BR-Football dataset carries these columns, so results are
    limited to the 2023 season coverage of that file.
    """
    df = data.matches[data.matches["source"].eq("BR-Football-Dataset")]
    df = _finished(df)
    if team is not None:
        tk = data.resolve_team(team)
        df = df[_team_mask(df, tk, "either")]
        if opponent is not None:
            ok = data.resolve_team(opponent)
            df = df[(df["home_key"].eq(ok)) | (df["away_key"].eq(ok))]
    if season is not None:
        df = df[df["season"].eq(int(season))]
    df = df.sort_values("date", ascending=False, kind="mergesort")
    if limit and limit > 0:
        df = df.head(limit)
    out = []
    for _, r in df.iterrows():
        out.append({
            "date": _date_str(r["date"]),
            "competition": r["competition"],
            "home": data.team_name(r["home_key"]),
            "away": data.team_name(r["away_key"]),
            "home_goals": int(r["home_goals"]),
            "away_goals": int(r["away_goals"]),
            "home_corners": r["home_corners"],
            "away_corners": r["away_corners"],
            "home_shots": r["home_shots"],
            "away_shots": r["away_shots"],
        })
    return out


# ---------------------------------------------------------------------------
# Catalogue helpers
# ---------------------------------------------------------------------------

def list_teams(data, competition=None, season=None,
               limit: int = 0) -> list[dict[str, Any]]:
    """List teams (with match counts), most active first."""
    df = data.matches
    if competition is not None:
        df = _competition_filter(df, competition)
    if season is not None:
        df = df[df["season"].eq(int(season))]
    keys = pd.concat([df["home_key"], df["away_key"]], ignore_index=True)
    counts = keys.value_counts()
    if limit and limit > 0:
        counts = counts.head(limit)
    return [{"team": data.team_name(k), "team_key": k, "matches": int(v)}
            for k, v in counts.items() if k]


def list_competitions(data) -> list[str]:
    """Distinct competition labels present in the data."""
    return sorted(data.matches["competition"].dropna().unique().tolist())
