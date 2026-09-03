"""
Context block
=============
Brazilian Soccer MCP Server - Query Engine
-------------------------------------------
Purpose: Implement the high-level query API that backs the MCP tools. Each
method returns plain Python data structures (dicts/lists) so it can be exposed
verbatim through the MCP server and easily asserted by BDD tests.

Capabilities (mapped to the spec's required categories):
  * Match Queries        : find_matches, last_match_between, head_to_head
  * Team Queries         : team_statistics, team_competitions
  * Player Queries       : search_players, top_brazilian_players,
                          players_at_club, brazilian_players_by_club
  * Competition Queries  : standings
  * Statistical Analysis : biggest_wins, average_goals, home_away_performance,
                          derbies, seasons_summary

All team-name matching goes through the normalizer (canonical_key) so the
various spelling conventions across the six CSV files collapse to the same
identity. Dates are pandas Timestamps; missing/NaN goals mean "not played".
"""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from . import normalizer as nz
from .data import (
    COMP_BRASILEIRAO, COMP_CUP, COMP_LIBERTADORES, COMP_HIST,
    get_data, SoccerData,
)

COMP_ALIASES = {
    "brasileirao": [COMP_BRASILEIRAO],
    "brasileirão": [COMP_BRASILEIRAO],
    "serie a": [COMP_BRASILEIRAO],
    "série a": [COMP_BRASILEIRAO],
    "campeonato brasileiro": [COMP_BRASILEIRAO],
    "brasileirao serie a": [COMP_BRASILEIRAO],
    "brf serie a": ["Serie A"],
    "serie b": ["Serie B"],
    "serie c": ["Serie C"],
    "copa do brasil": [COMP_CUP],
    "copa do brazil": [COMP_CUP],
    "brazilian cup": [COMP_CUP],
    "cup": [COMP_CUP],
    "copa libertadores": [COMP_LIBERTADORES],
    "libertadores": [COMP_LIBERTADORES],
    "historical": [COMP_HIST],
    "2003-2019": [COMP_HIST],
    "brasileirão (2003-2019)": [COMP_HIST],
    COMP_HIST: [COMP_HIST],
}


def resolve_competition(name):
    """Resolve a user-facing competition name to internal competition values.

    Returns None when name is empty (meaning "all competitions").
    """
    if name is None:
        return None
    key = str(name).strip().lower()
    if key == "":
        return None
    for alias, comps in COMP_ALIASES.items():
        if key == alias.lower():
            return list(comps)
    return [str(name)]


def _team_key(team):
    return nz.canonical_key(team)


def _to_py(value):
    """Convert numpy scalars/pandas objects to native Python for JSON output."""
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


class QueryEngine:
    """High level query API over the loaded SoccerData."""

    def __init__(self, data=None):
        self.data = data or get_data()
        self._m = self.data.matches
        self._p = self.data.players

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _filter_competition(df, competition):
        comps = resolve_competition(competition)
        if comps is None:
            return df
        return df[df["competition"].isin(comps)]

    @staticmethod
    def _match_row_to_dict(row):
        return {
            "date": _to_py(row.get("date")),
            "season": _to_py(row.get("season")),
            "competition": _to_py(row.get("competition")),
            "home_team": _to_py(row.get("home_display")),
            "away_team": _to_py(row.get("away_display")),
            "home_team_raw": _to_py(row.get("home_team")),
            "away_team_raw": _to_py(row.get("away_team")),
            "home_goal": _to_py(row.get("home_goal")),
            "away_goal": _to_py(row.get("away_goal")),
            "round": _to_py(row.get("round")),
            "stage": _to_py(row.get("stage")),
            "stadium": _to_py(row.get("stadium")),
        }

    def _player_row_to_dict(self, row):
        return {
            "name": _to_py(row.get("Name")),
            "age": _to_py(row.get("Age")),
            "nationality": _to_py(row.get("Nationality")),
            "overall": _to_py(row.get("Overall")),
            "potential": _to_py(row.get("Potential")),
            "club": _to_py(row.get("club_display")),
            "club_raw": _to_py(row.get("Club")),
            "position": _to_py(row.get("Position")),
            "jersey": _to_py(row.get("Jersey Number")),
        }

    # --------------------------------------------------------- match queries
    def find_matches(self, team=None, opponent=None, competition=None,
                     season=None, start_date=None, end_date=None,
                     limit=100, played_only=True):
        """Return matches matching all the supplied criteria.

        team    : matches where the given team is home or away.
        opponent: when team is given, restrict to matches against this opponent.
        competition: competition alias or internal name (None = all).
        season  : integer year.
        start_date / end_date: ISO date strings (inclusive).
        limit   : cap on number of returned matches (None = unlimited).
        played_only: drop rows without final scores.
        """
        df = self._m
        if played_only:
            df = df.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        if season is not None:
            df = df[df["season"] == int(season)]
        if start_date is not None:
            df = df[df["date"] >= pd.to_datetime(start_date)]
        if end_date is not None:
            df = df[df["date"] <= pd.to_datetime(end_date)]
        if team is not None:
            k = _team_key(team)
            df = df[(df.home_key == k) | (df.away_key == k)]
        if opponent is not None:
            ok = _team_key(opponent)
            if team is None:
                df = df[(df.home_key == ok) | (df.away_key == ok)]
            else:
                k = _team_key(team)
                df = df[((df.home_key == k) & (df.away_key == ok)) |
                        ((df.home_key == ok) & (df.away_key == k))]
        df = df.sort_values("date", na_position="last")
        if limit is not None:
            df = df.head(int(limit))
        return [self._match_row_to_dict(r) for _, r in df.iterrows()]

    def head_to_head(self, team_a, team_b, competition=None):
        """Compute head-to-head record between two teams."""
        ka, kb = _team_key(team_a), _team_key(team_b)
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        df = df[((df.home_key == ka) & (df.away_key == kb)) |
                ((df.home_key == kb) & (df.away_key == ka))]
        a_wins = b_wins = draws = 0
        a_gf = a_ga = 0
        matches = []
        for _, r in df.iterrows():
            hg, ag = r["home_goal"], r["away_goal"]
            home_is_a = (r["home_key"] == ka)
            a_goals = hg if home_is_a else ag
            b_goals = ag if home_is_a else hg
            a_gf += a_goals
            a_ga += b_goals
            if a_goals > b_goals:
                a_wins += 1
            elif a_goals < b_goals:
                b_wins += 1
            else:
                draws += 1
            matches.append(self._match_row_to_dict(r))
        matches.sort(key=lambda m: (m["date"] is None, m["date"]))
        return {
            "team_a": nz.display_name(team_a),
            "team_b": nz.display_name(team_b),
            "matches": len(matches),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": int(a_gf),
            "team_b_goals": int(a_ga),
            "match_list": matches,
        }

    def last_match_between(self, team_a, team_b):
        ka, kb = _team_key(team_a), _team_key(team_b)
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = df[((df.home_key == ka) & (df.away_key == kb)) |
                ((df.home_key == kb) & (df.away_key == ka))]
        df = df.dropna(subset=["date"]).sort_values("date")
        if df.empty:
            return None
        return self._match_row_to_dict(df.iloc[-1])

    # ---------------------------------------------------------- team queries
    def team_statistics(self, team, season=None, competition=None, venue=None):
        """Aggregate win/draw/loss and goal stats for a team.

        venue: 'home', 'away' or None (both).
        """
        k = _team_key(team)
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        if season is not None:
            df = df[df["season"] == int(season)]
        if venue == "home":
            df = df[df.home_key == k]
        elif venue == "away":
            df = df[df.away_key == k]
        else:
            df = df[(df.home_key == k) | (df.away_key == k)]
        wins = draws = losses = 0
        gf = ga = 0
        for _, r in df.iterrows():
            home = (r["home_key"] == k)
            team_g = r["home_goal"] if home else r["away_goal"]
            opp_g = r["away_goal"] if home else r["home_goal"]
            gf += team_g
            ga += opp_g
            if team_g > opp_g:
                wins += 1
            elif team_g < opp_g:
                losses += 1
            else:
                draws += 1
        played = len(df)
        win_rate = (wins / played * 100) if played else 0.0
        return {
            "team": nz.display_name(team),
            "venue": venue or "both",
            "season": _to_py(season) if season is not None else "all",
            "competition": competition or "all",
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": int(gf),
            "goals_against": int(ga),
            "goal_difference": int(gf - ga),
            "win_rate": round(win_rate, 2),
        }

    def team_competitions(self, team):
        """List the competitions a team has appeared in, with match counts."""
        k = _team_key(team)
        df = self._m[(self._m.home_key == k) | (self._m.away_key == k)]
        grp = df.groupby("competition").size().sort_values(ascending=False)
        return [{"competition": comp, "matches": int(cnt)}
                for comp, cnt in grp.items()]

    # -------------------------------------------------------- player queries
    def search_players(self, name=None, nationality=None, club=None,
                       position=None, min_rating=None, limit=50,
                       sort_by="Overall", descending=True):
        """Search FIFA players by name/nationality/club/position/rating."""
        df = self._p
        if name:
            df = df[df["Name"].str.contains(name, case=False, na=False)]
        if nationality:
            df = df[df["Nationality"].str.contains(nationality, case=False,
                                                    na=False)]
        if club:
            ck = _team_key(club)
            if ck:
                df = df[df["club_key"] == ck]
            else:
                df = df[df["Club"].str.contains(club, case=False, na=False)]
        if position:
            df = df[df["Position"].astype(str).str.contains(
                position, case=False, na=False)]
        if min_rating is not None:
            df = df[df["Overall"] >= float(min_rating)]
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=not descending)
        if limit is not None:
            df = df.head(int(limit))
        return [self._player_row_to_dict(r) for _, r in df.iterrows()]

    def top_brazilian_players(self, limit=20):
        df = (self._p[self._p["Nationality"] == "Brazil"]
              .sort_values("Overall", ascending=False))
        return [self._player_row_to_dict(r) for _, r in df.head(limit).iterrows()]

    def players_at_club(self, club, sort_by="Overall", descending=True):
        ck = _team_key(club)
        df = self._p[self._p["club_key"] == ck]
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=not descending)
        return [self._player_row_to_dict(r) for _, r in df.iterrows()]

    def brazilian_players_by_club(self):
        """Count of Brazilian players per Brazilian club with avg rating."""
        df = self._p[self._p["Nationality"] == "Brazil"]
        club_keys = (set(self._m["home_key"].dropna().unique()) |
                     set(self._m["away_key"].dropna().unique()))
        df = df[df["club_key"].isin(club_keys)]
        grp = df.groupby(["club_key", "club_display"])
        rows = []
        for (ck, cd), g in grp:
            rows.append({
                "club": cd,
                "players": int(len(g)),
                "avg_rating": round(float(g["Overall"].mean()), 1) if len(g) else 0.0,
                "top_rating": int(g["Overall"].max()) if len(g) else 0,
            })
        rows.sort(key=lambda r: r["players"], reverse=True)
        return rows

    # ----------------------------------------------------- competition queries
    def standings(self, competition="brasileirao", season=None, top=None):
        """Compute league standings from match results.

        For the Brasileirao the modern file (2012+) is preferred; seasons
        2003-2011 fall back to the historical file. 3 pts/win, 1 pt/draw.
        Sorted by points, then goal difference, then goals for.
        """
        comps = resolve_competition(competition) or [COMP_BRASILEIRAO]
        if season is not None:
            if COMP_BRASILEIRAO in comps and int(season) >= 2012:
                comp_val = COMP_BRASILEIRAO
            elif 2003 <= int(season) <= 2011:
                comp_val = COMP_HIST
            else:
                comp_val = comps[0]
        else:
            comp_val = comps[0]
        df = self._m[self._m["competition"] == comp_val]
        if season is not None:
            df = df[df["season"] == int(season)]
        df = df.dropna(subset=["home_goal", "away_goal"])
        teams = {}
        for k in list(df.home_key.unique()) + list(df.away_key.unique()):
            if k and k not in teams:
                teams[k] = {"team": nz.display_name(k), "played": 0, "wins": 0,
                            "draws": 0, "losses": 0, "goals_for": 0,
                            "goals_against": 0}
        for _, r in df.iterrows():
            hk, ak = r["home_key"], r["away_key"]
            hg, ag = r["home_goal"], r["away_goal"]
            ht, at = teams.get(hk), teams.get(ak)
            if not ht or not at:
                continue
            ht["played"] += 1
            at["played"] += 1
            ht["goals_for"] += hg
            ht["goals_against"] += ag
            at["goals_for"] += ag
            at["goals_against"] += hg
            if hg > ag:
                ht["wins"] += 1
                at["losses"] += 1
            elif hg < ag:
                at["wins"] += 1
                ht["losses"] += 1
            else:
                ht["draws"] += 1
                at["draws"] += 1
        rows = []
        for k, t in teams.items():
            pts = 3 * t["wins"] + t["draws"]
            gd = t["goals_for"] - t["goals_against"]
            rows.append({
                "team": t["team"],
                "played": t["played"],
                "wins": t["wins"],
                "draws": t["draws"],
                "losses": t["losses"],
                "goals_for": int(t["goals_for"]),
                "goals_against": int(t["goals_against"]),
                "goal_difference": int(gd),
                "points": int(pts),
            })
        rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"],
                                 -r["goals_for"], r["team"]))
        if top is not None:
            rows = rows[:int(top)]
        return rows

    # --------------------------------------------------- statistical queries
    def biggest_wins(self, competition=None, limit=10):
        """Return the biggest victories (by goal margin) in the dataset."""
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        df = df.assign(margin=(df.home_goal - df.away_goal).abs())
        df = df.sort_values(["margin", "date"], ascending=[False, True])
        rows = []
        for _, r in df.head(int(limit)).iterrows():
            if r["home_goal"] > r["away_goal"]:
                winner, loser = r["home_display"], r["away_display"]
                ws, ls = r["home_goal"], r["away_goal"]
            else:
                winner, loser = r["away_display"], r["home_display"]
                ws, ls = r["away_goal"], r["home_goal"]
            rows.append({
                "date": _to_py(r.get("date")),
                "season": _to_py(r.get("season")),
                "competition": _to_py(r.get("competition")),
                "winner": _to_py(winner),
                "loser": _to_py(loser),
                "score": f"{int(ws)}-{int(ls)}",
                "margin": int(abs(r["home_goal"] - r["away_goal"])),
            })
        return rows

    def average_goals(self, competition=None, season=None):
        """Average goals per match (and home/away split)."""
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        if season is not None:
            df = df[df["season"] == int(season)]
        total = df["home_goal"].sum() + df["away_goal"].sum()
        n = len(df)
        home_wins = (df["home_goal"] > df["away_goal"]).sum()
        away_wins = (df["away_goal"] > df["home_goal"]).sum()
        draws = (df["home_goal"] == df["away_goal"]).sum()
        return {
            "competition": competition or "all",
            "season": _to_py(season) if season is not None else "all",
            "matches": int(n),
            "total_goals": int(total),
            "average_goals_per_match": round(float(total) / n, 3) if n else 0.0,
            "average_home_goals": round(float(df["home_goal"].sum()) / n, 3) if n else 0.0,
            "average_away_goals": round(float(df["away_goal"].sum()) / n, 3) if n else 0.0,
            "home_win_rate": round(float(home_wins) / n * 100, 2) if n else 0.0,
            "away_win_rate": round(float(away_wins) / n * 100, 2) if n else 0.0,
            "draw_rate": round(float(draws) / n * 100, 2) if n else 0.0,
        }

    def home_away_performance(self, competition=None):
        """Overall home vs away performance split for a competition."""
        return self.average_goals(competition=competition)

    def best_home_record(self, competition="brasileirao", season=None, top=10):
        """Teams with the best home win rate."""
        comps = resolve_competition(competition)
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        if season is not None:
            df = df[df["season"] == int(season)]
        rows = []
        for k, g in df.groupby("home_key"):
            if not k:
                continue
            wins = (g["home_goal"] > g["away_goal"]).sum()
            n = len(g)
            rows.append({
                "team": nz.display_name(k),
                "home_matches": int(n),
                "wins": int(wins),
                "win_rate": round(float(wins) / n * 100, 2) if n else 0.0,
            })
        rows.sort(key=lambda r: (-r["win_rate"], -r["wins"], r["team"]))
        return rows[:int(top)]

    def best_away_record(self, competition="brasileirao", season=None, top=10):
        """Teams with the best away win rate (min 10 matches)."""
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        if season is not None:
            df = df[df["season"] == int(season)]
        rows = []
        for k, g in df.groupby("away_key"):
            if not k:
                continue
            wins = (g["away_goal"] > g["home_goal"]).sum()
            n = len(g)
            if n < 10:
                continue
            rows.append({
                "team": nz.display_name(k),
                "away_matches": int(n),
                "wins": int(wins),
                "win_rate": round(float(wins) / n * 100, 2) if n else 0.0,
            })
        rows.sort(key=lambda r: (-r["win_rate"], -r["wins"], r["team"]))
        return rows[:int(top)]

    def derbies(self, competition=None, season=None, limit=100):
        """Return traditional derby matches (see normalizer.DERBY_PAIRS)."""
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        if season is not None:
            df = df[df["season"] == int(season)]
        mask = df.apply(lambda r: nz.is_derby(r["home_display"], r["away_display"]),
                        axis=1)
        df = df[mask].sort_values("date", na_position="last")
        if limit is not None:
            df = df.head(int(limit))
        return [self._match_row_to_dict(r) for _, r in df.iterrows()]

    def seasons_summary(self, competition="brasileirao"):
        """Per-season aggregate summary for a competition."""
        comps = resolve_competition(competition)
        df = self._m.dropna(subset=["home_goal", "away_goal"])
        df = self._filter_competition(df, competition)
        rows = []
        for season, g in df.groupby("season"):
            total = g["home_goal"].sum() + g["away_goal"].sum()
            n = len(g)
            rows.append({
                "season": int(season),
                "matches": int(n),
                "average_goals_per_match": round(float(total) / n, 3) if n else 0.0,
                "home_win_rate": round(float((g["home_goal"] > g["away_goal"]).sum()) / n * 100, 2) if n else 0.0,
                "away_win_rate": round(float((g["away_goal"] > g["home_goal"]).sum()) / n * 100, 2) if n else 0.0,
                "draw_rate": round(float((g["home_goal"] == g["away_goal"]).sum()) / n * 100, 2) if n else 0.0,
            })
        rows.sort(key=lambda r: r["season"])
        return rows


# Convenience singleton accessor.
_engine: Optional[QueryEngine] = None


def get_engine(data: Optional[SoccerData] = None) -> QueryEngine:
    """Return a cached QueryEngine (creates one on first call)."""
    global _engine
    if _engine is None or data is not None:
        _engine = QueryEngine(data)
    return _engine


def reset_engine() -> None:
    """Clear the cached QueryEngine (used by tests)."""
    global _engine
    _engine = None
