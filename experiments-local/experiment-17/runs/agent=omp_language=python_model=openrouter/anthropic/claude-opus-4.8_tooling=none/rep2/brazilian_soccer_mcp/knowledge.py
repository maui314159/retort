"""
Context
=======
Module: brazilian_soccer_mcp.knowledge
Purpose: The query engine. Wraps the normalized match/player tables produced by
         :mod:`.loader` and answers the capability categories required by the
         spec: match search, team stats, player search, competition standings,
         and aggregate statistics.

Return contract
---------------
Every public method returns a plain dict/list of primitives (JSON-serializable),
never a DataFrame. Formatting into prose lives in :mod:`.formatting`; MCP tools
return the formatted text. This separation keeps the engine unit-testable
against structured values rather than rendered strings.

Performance
-----------
Tables are held in memory. Team lookups build a boolean mask over the relevant
key columns (vectorized, O(n) over ~24k unified match rows) — comfortably inside
the 2s simple-lookup / 5s aggregate budget.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from . import loader
from .normalize import query_key

# Default location of the bundled datasets, relative to repo root.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


class KnowledgeBase:
    """In-memory knowledge base over the Brazilian-soccer datasets."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self.matches: pd.DataFrame = loader.load_matches(self.data_dir)
        self.players: pd.DataFrame = loader.load_players(self.data_dir)

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #
    def _team_mask(self, team: str, side: str = "either") -> pd.Series:
        """Boolean mask of matches involving *team* on the requested side.

        ``side`` in {"home", "away", "either"}. Matching uses normalized-key
        substring so partial names ("Atletico") resolve, but a bare token also
        matches longer keys ("atletico mineiro").
        """
        q = query_key(team)
        if not q:
            return pd.Series(False, index=self.matches.index)
        home_hit = self.matches["home_key"].str.contains(q, regex=False, na=False) | \
            self.matches["home_key"].eq(q)
        away_hit = self.matches["away_key"].str.contains(q, regex=False, na=False) | \
            self.matches["away_key"].eq(q)
        if side == "home":
            return home_hit
        if side == "away":
            return away_hit
        return home_hit | away_hit

    @staticmethod
    def _match_record(row: pd.Series) -> dict[str, Any]:
        date = row["date"]
        return {
            "date": date.strftime("%Y-%m-%d") if pd.notna(date) else None,
            "season": int(row["season"]),
            "competition": row["competition"],
            "home_team": row["home_raw"],
            "away_team": row["away_raw"],
            "home_goal": int(row["home_goal"]),
            "away_goal": int(row["away_goal"]),
            "stage": None if pd.isna(row["stage"]) else str(row["stage"]),
        }

    # ------------------------------------------------------------------ #
    # 1. Match queries
    # ------------------------------------------------------------------ #
    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return matches filtered by any combination of criteria, newest first.

        When both *team* and *opponent* are given, only matches between the two
        (either home/away orientation) are returned.
        """
        df = self.matches
        mask = pd.Series(True, index=df.index)
        if team:
            mask &= self._team_mask(team)
        if opponent:
            mask &= self._team_mask(opponent)
        if competition:
            cq = query_key(competition)
            comp_keys = df["competition"].str.lower().map(query_key)
            mask &= comp_keys.str.contains(cq, regex=False, na=False)
        if season is not None:
            mask &= df["season"].eq(int(season))
        if date_from:
            mask &= df["date"] >= pd.to_datetime(date_from)
        if date_to:
            mask &= df["date"] <= pd.to_datetime(date_to)

        sel = df[mask].sort_values("date", ascending=False, na_position="last")
        return [self._match_record(r) for _, r in sel.head(limit).iterrows()]

    def head_to_head(self, team_a: str, team_b: str) -> dict[str, Any]:
        """Aggregate head-to-head record between two teams across all data.

        Wins are attributed by normalized key, so orientation (home/away) is
        handled correctly.
        """
        mask = self._team_mask(team_a) & self._team_mask(team_b)
        sel = self.matches[mask]
        a_key = query_key(team_a)
        a_wins = b_wins = draws = a_goals = b_goals = 0
        for _, r in sel.iterrows():
            a_is_home = a_key in r["home_key"] or r["home_key"] == a_key
            ag = r["home_goal"] if a_is_home else r["away_goal"]
            bg = r["away_goal"] if a_is_home else r["home_goal"]
            a_goals += ag
            b_goals += bg
            if ag > bg:
                a_wins += 1
            elif bg > ag:
                b_wins += 1
            else:
                draws += 1
        return {
            "team_a": team_a,
            "team_b": team_b,
            "matches": int(len(sel)),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "fixtures": [
                self._match_record(r)
                for _, r in sel.sort_values("date", ascending=False).head(20).iterrows()
            ],
        }

    # ------------------------------------------------------------------ #
    # 2. Team queries
    # ------------------------------------------------------------------ #
    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str = "all",
    ) -> dict[str, Any]:
        """Win/draw/loss record, goals for/against and win-rate for a team.

        ``venue`` in {"all", "home", "away"} restricts to that venue's fixtures.
        """
        df = self.matches
        if venue == "home":
            mask = self._team_mask(team, "home")
        elif venue == "away":
            mask = self._team_mask(team, "away")
        else:
            mask = self._team_mask(team)
        if season is not None:
            mask &= df["season"].eq(int(season))
        if competition:
            cq = query_key(competition)
            mask &= df["competition"].map(query_key).str.contains(cq, regex=False, na=False)

        sel = df[mask]
        key = query_key(team)
        wins = draws = losses = gf = ga = 0
        for _, r in sel.iterrows():
            is_home = key in r["home_key"] or r["home_key"] == key
            tf = r["home_goal"] if is_home else r["away_goal"]
            ta = r["away_goal"] if is_home else r["home_goal"]
            gf += tf
            ta_ = ta
            ga += ta_
            if tf > ta:
                wins += 1
            elif tf < ta:
                losses += 1
            else:
                draws += 1
        played = len(sel)
        return {
            "team": team,
            "season": season,
            "competition": competition,
            "venue": venue,
            "matches": int(played),
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points": wins * 3 + draws,
            "win_rate": round(wins / played * 100, 1) if played else 0.0,
        }

    def competitions_for_team(self, team: str) -> list[dict[str, Any]]:
        """List competitions a team appears in, with match counts and seasons."""
        sel = self.matches[self._team_mask(team)]
        out = []
        for comp, grp in sel.groupby("competition"):
            seasons = sorted(grp["season"].unique().tolist())
            out.append({
                "competition": comp,
                "matches": int(len(grp)),
                "seasons": seasons,
            })
        out.sort(key=lambda d: d["matches"], reverse=True)
        return out

    # ------------------------------------------------------------------ #
    # 3. Player queries
    # ------------------------------------------------------------------ #
    def find_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Search the FIFA player table, sorted by Overall descending."""
        df = self.players
        mask = pd.Series(True, index=df.index)
        if name:
            mask &= df["name_lower"].str.contains(name.lower(), regex=False, na=False)
        if nationality:
            mask &= df["Nationality"].str.lower().eq(nationality.lower())
        if club:
            ck = query_key(club)
            mask &= df["club_key"].str.contains(ck, regex=False, na=False)
        if position:
            mask &= df["Position"].fillna("").str.upper().eq(position.upper())
        if min_overall is not None:
            mask &= df["Overall"] >= int(min_overall)

        sel = df[mask].sort_values("Overall", ascending=False).head(limit)
        return [self._player_record(r) for _, r in sel.iterrows()]

    @staticmethod
    def _player_record(row: pd.Series) -> dict[str, Any]:
        def g(col: str) -> Any:
            v = row.get(col)
            return None if pd.isna(v) else v
        return {
            "name": g("Name"),
            "age": int(row["Age"]) if pd.notna(row.get("Age")) else None,
            "nationality": g("Nationality"),
            "overall": int(row["Overall"]) if pd.notna(row.get("Overall")) else None,
            "potential": int(row["Potential"]) if pd.notna(row.get("Potential")) else None,
            "club": g("Club"),
            "position": g("Position"),
        }

    def players_by_club_summary(self, nationality: str = "Brazil", top: int = 15) -> list[dict[str, Any]]:
        """Per-club count and average rating for players of a given nationality."""
        df = self.players
        sel = df[df["Nationality"].str.lower().eq(nationality.lower())]
        out = []
        for club, grp in sel.groupby("Club"):
            out.append({
                "club": club,
                "players": int(len(grp)),
                "avg_overall": round(float(grp["Overall"].mean()), 1),
            })
        out.sort(key=lambda d: (-d["players"], -d["avg_overall"]))
        return out[:top]

    # ------------------------------------------------------------------ #
    # 4. Competition queries
    # ------------------------------------------------------------------ #
    def standings(self, competition: str, season: int) -> list[dict[str, Any]]:
        """Compute a league table for a (competition, season) from match results.

        Uses 3-1-0 points. Returns rows sorted by points, then goal difference,
        then goals for. Only meaningful for round-robin leagues (Série A/B/C);
        cup/knockout competitions will still aggregate but ranking is informal.
        """
        cq = query_key(competition)
        df = self.matches
        mask = df["competition"].map(query_key).str.contains(cq, regex=False, na=False) & \
            df["season"].eq(int(season))
        sel = df[mask]

        table: dict[str, dict[str, Any]] = {}

        def slot(key: str, name: str) -> dict[str, Any]:
            if key not in table:
                table[key] = {
                    "team": name, "played": 0, "wins": 0, "draws": 0,
                    "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0,
                }
            return table[key]

        for _, r in sel.iterrows():
            h = slot(r["home_id"], r["home_raw"])
            a = slot(r["away_id"], r["away_raw"])
            hg, ag = int(r["home_goal"]), int(r["away_goal"])
            h["played"] += 1
            a["played"] += 1
            h["goals_for"] += hg
            h["goals_against"] += ag
            a["goals_for"] += ag
            a["goals_against"] += hg
            if hg > ag:
                h["wins"] += 1
                h["points"] += 3
                a["losses"] += 1
            elif ag > hg:
                a["wins"] += 1
                a["points"] += 3
                h["losses"] += 1
            else:
                h["draws"] += 1
                a["draws"] += 1
                h["points"] += 1
                a["points"] += 1

        rows = list(table.values())
        for row in rows:
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
        rows.sort(key=lambda d: (-d["points"], -d["goal_difference"], -d["goals_for"]))
        for i, row in enumerate(rows, 1):
            row["position"] = i
        return rows

    # ------------------------------------------------------------------ #
    # 5. Statistical analysis
    # ------------------------------------------------------------------ #
    def competition_stats(
        self, competition: str | None = None, season: int | None = None
    ) -> dict[str, Any]:
        """Aggregate goal/home-win statistics over a filtered slice of matches."""
        df = self.matches
        mask = pd.Series(True, index=df.index)
        if competition:
            cq = query_key(competition)
            mask &= df["competition"].map(query_key).str.contains(cq, regex=False, na=False)
        if season is not None:
            mask &= df["season"].eq(int(season))
        sel = df[mask]
        n = len(sel)
        if n == 0:
            return {"competition": competition, "season": season, "matches": 0}
        total_goals = int((sel["home_goal"] + sel["away_goal"]).sum())
        home_wins = int((sel["home_goal"] > sel["away_goal"]).sum())
        away_wins = int((sel["away_goal"] > sel["home_goal"]).sum())
        draws = n - home_wins - away_wins
        return {
            "competition": competition,
            "season": season,
            "matches": n,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / n, 2),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(home_wins / n * 100, 1),
            "away_win_rate": round(away_wins / n * 100, 1),
            "draw_rate": round(draws / n * 100, 1),
        }

    def biggest_wins(
        self, competition: str | None = None, season: int | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Matches with the largest goal margin, biggest first."""
        df = self.matches
        mask = pd.Series(True, index=df.index)
        if competition:
            cq = query_key(competition)
            mask &= df["competition"].map(query_key).str.contains(cq, regex=False, na=False)
        if season is not None:
            mask &= df["season"].eq(int(season))
        sel = df[mask].copy()
        sel["margin"] = (sel["home_goal"] - sel["away_goal"]).abs()
        sel = sel.sort_values(["margin", "date"], ascending=[False, False]).head(limit)
        out = []
        for _, r in sel.iterrows():
            rec = self._match_record(r)
            rec["margin"] = int(r["margin"])
            out.append(rec)
        return out

    def top_scoring_teams(
        self, competition: str | None = None, season: int | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Teams ranked by total goals scored in the filtered slice."""
        df = self.matches
        mask = pd.Series(True, index=df.index)
        if competition:
            cq = query_key(competition)
            mask &= df["competition"].map(query_key).str.contains(cq, regex=False, na=False)
        if season is not None:
            mask &= df["season"].eq(int(season))
        sel = df[mask]
        goals: dict[str, dict[str, Any]] = {}
        for _, r in sel.iterrows():
            for key, name, gf in (
                (r["home_id"], r["home_raw"], r["home_goal"]),
                (r["away_id"], r["away_raw"], r["away_goal"]),
            ):
                slot = goals.setdefault(key, {"team": name, "goals": 0, "matches": 0})
                slot["goals"] += int(gf)
                slot["matches"] += 1
        rows = sorted(goals.values(), key=lambda d: d["goals"], reverse=True)
        return rows[:limit]

    # ------------------------------------------------------------------ #
    # meta
    # ------------------------------------------------------------------ #
    def summary(self) -> dict[str, Any]:
        """High-level counts useful for sanity checks and an MCP overview tool."""
        return {
            "total_matches": int(len(self.matches)),
            "total_players": int(len(self.players)),
            "competitions": sorted(self.matches["competition"].unique().tolist()),
            "season_range": [
                int(self.matches["season"].min()),
                int(self.matches["season"].max()),
            ],
        }
