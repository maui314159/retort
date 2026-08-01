"""Query engine over the unified Brazilian soccer datasets.

Why: the MCP tools need small, composable query functions for the five
capability categories in the spec: matches, teams, players,
competitions and statistical analysis.

What: ``QueryEngine`` wraps a ``SoccerDataset`` and returns plain
dicts/lists (JSON-friendly) that the MCP layer formats as text.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .data_loader import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    LIBERTADORES,
    POSITION_GROUPS,
    SoccerDataset,
)
from .normalization import normalize_text, parse_date

_COMPETITION_ALIASES = {
    "brasileirao": BRASILEIRAO_A,
    "brasileirao serie a": BRASILEIRAO_A,
    "campeonato brasileiro": BRASILEIRAO_A,
    "campeonato brasileiro serie a": BRASILEIRAO_A,
    "serie a": BRASILEIRAO_A,
    "brasileirao serie b": BRASILEIRAO_B,
    "serie b": BRASILEIRAO_B,
    "brasileirao serie c": BRASILEIRAO_C,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "copa libertadores": LIBERTADORES,
    "libertadores": LIBERTADORES,
    "copa libertadores da america": LIBERTADORES,
}


def resolve_competition(name: str | None, known: list[str] | None = None) -> str | None:
    """Map free-text competition input ("Serie A", "libertadores") to the
    canonical competition name.  ``None`` input passes through."""
    if name is None or not str(name).strip():
        return None
    key = normalize_text(name)
    if key in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[key]
    if known:
        for comp in known:
            if key in normalize_text(comp) or normalize_text(comp) in key:
                return comp
    # Substring fallback against the alias table.
    for alias, comp in _COMPETITION_ALIASES.items():
        if key in alias or alias in key:
            return comp
    return str(name).strip()


class QueryEngine:
    """Structured queries over matches and players."""

    def __init__(self, dataset: SoccerDataset):
        self.dataset = dataset
        self.matches = dataset.matches
        self.players = dataset.players
        self.registry = dataset.registry

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _team_keys(self, name: str) -> list[str]:
        return self.registry.resolve(name)

    def _display(self, key: str) -> str:
        return self.registry.display_name(key)

    def _filter_matches(
        self,
        df: pd.DataFrame | None = None,
        *,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> pd.DataFrame:
        df = self.matches if df is None else df
        mask = pd.Series(True, index=df.index)
        comp = resolve_competition(competition, self.competitions())
        if comp:
            mask &= df["competition"] == comp
        if season is not None:
            mask &= df["season"] == int(season)
        start = parse_date(date_from)
        if start:
            mask &= df["date"] >= pd.Timestamp(start)
        end = parse_date(date_to)
        if end:
            # Inclusive of the whole end day (but not midnight of the next).
            mask &= df["date"] < pd.Timestamp(end) + pd.Timedelta(days=1)
        return df[mask]

    def _match_dict(self, row: pd.Series) -> dict[str, Any]:
        return {
            "date": row["date"].date().isoformat(),
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_goals": int(row["home_goals"]),
            "away_goals": int(row["away_goals"]),
            "competition": row["competition"],
            "season": int(row["season"]) if pd.notna(row["season"]) else None,
            "round": None if pd.isna(row["round"]) else str(row["round"]),
            "arena": None if pd.isna(row.get("arena")) else str(row["arena"]),
            "source": row["source"],
        }

    def competitions(self) -> list[str]:
        return sorted(self.matches["competition"].unique().tolist())

    def seasons(self) -> list[int]:
        return [int(s) for s in sorted(self.matches["season"].dropna().unique())]

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------

    def find_matches(
        self,
        team: str | None = None,
        versus: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        ascending: bool = False,
    ) -> dict[str, Any]:
        """Find matches by team(s), competition, season and/or date range."""
        df = self._filter_matches(
            competition=competition, season=season, date_from=date_from, date_to=date_to
        )
        resolved: dict[str, list[str]] = {}
        if team:
            keys = self._team_keys(team)
            if not keys:
                return {"matches": [], "total": 0, "error": f"Unknown team: {team!r}"}
            resolved[team] = keys
            df = df[df["home_key"].isin(keys) | df["away_key"].isin(keys)]
        if versus:
            keys = self._team_keys(versus)
            if not keys:
                return {"matches": [], "total": 0, "error": f"Unknown team: {versus!r}"}
            resolved[versus] = keys
            df = df[df["home_key"].isin(keys) | df["away_key"].isin(keys)]
        df = df.sort_values("date", ascending=ascending, kind="stable")
        total = len(df)
        rows = [self._match_dict(r) for _, r in df.head(limit).iterrows()]
        return {
            "matches": rows,
            "total": int(total),
            "returned": len(rows),
            "resolved_teams": {k: [self._display(x) for x in v] for k, v in resolved.items()},
        }

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------

    def head_to_head(self, team1: str, team2: str) -> dict[str, Any]:
        """Full head-to-head record between two teams (all competitions)."""
        keys1, keys2 = self._team_keys(team1), self._team_keys(team2)
        if not keys1:
            return {"error": f"Unknown team: {team1!r}"}
        if not keys2:
            return {"error": f"Unknown team: {team2!r}"}
        m = self.matches
        both = m[
            (m["home_key"].isin(keys1) & m["away_key"].isin(keys2))
            | (m["home_key"].isin(keys2) & m["away_key"].isin(keys1))
        ].sort_values("date", ascending=False, kind="stable")
        wins1 = draws = wins2 = 0
        for _, r in both.iterrows():
            home_is_1 = r["home_key"] in keys1
            hg, ag = int(r["home_goals"]), int(r["away_goals"])
            if hg == ag:
                draws += 1
            elif (hg > ag) == home_is_1:
                wins1 += 1
            else:
                wins2 += 1
        return {
            "team1": [self._display(k) for k in keys1],
            "team2": [self._display(k) for k in keys2],
            "total_matches": int(len(both)),
            "team1_wins": wins1,
            "draws": draws,
            "team2_wins": wins2,
            "matches": [self._match_dict(r) for _, r in both.head(20).iterrows()],
            "last_match": self._match_dict(both.iloc[0]) if len(both) else None,
        }

    def team_record(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str = "all",
    ) -> dict[str, Any]:
        """Wins/draws/losses and goals for a team, optionally filtered.

        ``venue`` is one of "all", "home" or "away".
        """
        keys = self._team_keys(team)
        if not keys:
            return {"error": f"Unknown team: {team!r}"}
        df = self._filter_matches(competition=competition, season=season)
        home = df[df["home_key"].isin(keys)]
        away = df[df["away_key"].isin(keys)]

        def tally(frame: pd.DataFrame, gf_col: str, ga_col: str) -> dict[str, int]:
            wins = int((frame[gf_col] > frame[ga_col]).sum())
            draws = int((frame[gf_col] == frame[ga_col]).sum())
            losses = int((frame[gf_col] < frame[ga_col]).sum())
            return {
                "matches": len(frame),
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goals_for": int(frame[gf_col].sum()),
                "goals_against": int(frame[ga_col].sum()),
            }

        home_t = tally(home, "home_goals", "away_goals")
        away_t = tally(away, "away_goals", "home_goals")
        venue = (venue or "all").lower()
        if venue == "home":
            selected = home_t
        elif venue == "away":
            selected = away_t
        else:
            selected = {k: home_t[k] + away_t[k] for k in home_t}
        played = selected["matches"]
        win_rate = round(100.0 * selected["wins"] / played, 1) if played else 0.0
        return {
            "team": [self._display(k) for k in keys],
            "season": season,
            "competition": resolve_competition(competition, self.competitions()),
            "venue": venue,
            **selected,
            "win_rate_pct": win_rate,
            "home": home_t,
            "away": away_t,
        }

    def team_competitions(self, team: str) -> dict[str, Any]:
        """Which competitions/seasons a team appears in (cross-file query)."""
        keys = self._team_keys(team)
        if not keys:
            return {"error": f"Unknown team: {team!r}"}
        df = self.matches[
            self.matches["home_key"].isin(keys) | self.matches["away_key"].isin(keys)
        ]
        per_comp = []
        for comp, grp in df.groupby("competition"):
            per_comp.append(
                {
                    "competition": comp,
                    "matches": int(len(grp)),
                    "seasons": [int(s) for s in sorted(grp["season"].dropna().unique())],
                }
            )
        per_comp.sort(key=lambda c: c["competition"])
        return {
            "team": [self._display(k) for k in keys],
            "competitions": per_comp,
            "total_matches": int(len(df)),
        }

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------

    def _filter_players(
        self,
        *,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        position_group: str | None = None,
        min_overall: int | None = None,
    ) -> pd.DataFrame:
        df = self.players
        mask = pd.Series(True, index=df.index)
        if name:
            needle = normalize_text(name)
            mask &= df["Name"].map(lambda n: needle in normalize_text(n))
        if nationality:
            needle = normalize_text(nationality)
            mask &= df["Nationality"].map(
                lambda n: normalize_text(n) == needle or needle in normalize_text(n)
            )
        if club:
            club_keys = self._team_keys(club)
            if club_keys:
                mask &= df["club_key"].isin(club_keys)
            else:
                needle = normalize_text(club)
                mask &= df["Club"].map(
                    lambda c: pd.notna(c) and needle in normalize_text(c)
                )
        if position:
            mask &= df["Position"].map(
                lambda p: pd.notna(p) and str(p).strip().upper() == position.strip().upper()
            )
        if position_group:
            group = position_group.strip().lower().rstrip("s")
            if group in POSITION_GROUPS:
                mask &= df["position_group"] == group
        if min_overall is not None:
            mask &= df["Overall"] >= int(min_overall)
        return df[mask]

    @staticmethod
    def _player_dict(row: pd.Series) -> dict[str, Any]:
        def num(col: str) -> Any:
            v = row.get(col)
            return None if pd.isna(v) else (int(v) if float(v).is_integer() else float(v))

        return {
            "id": num("ID"),
            "name": row["Name"],
            "age": num("Age"),
            "nationality": row["Nationality"],
            "overall": num("Overall"),
            "potential": num("Potential"),
            "club": None if pd.isna(row.get("Club")) else row["Club"],
            "position": None if pd.isna(row.get("Position")) else row["Position"],
            "position_group": row.get("position_group"),
            "jersey_number": num("Jersey Number"),
            "height": None if pd.isna(row.get("Height")) else row["Height"],
            "weight": None if pd.isna(row.get("Weight")) else row["Weight"],
        }

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        position_group: str | None = None,
        min_overall: int | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search FIFA players by name / nationality / club / position."""
        df = self._filter_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            position_group=position_group,
            min_overall=min_overall,
        ).sort_values("Overall", ascending=False, kind="stable")
        total = len(df)
        return {
            "players": [self._player_dict(r) for _, r in df.head(limit).iterrows()],
            "total": int(total),
            "returned": min(int(total), int(limit)),
        }

    def player_profile(self, name: str) -> dict[str, Any]:
        """Best-match profile for a player name, with skill attributes."""
        df = self._filter_players(name=name).sort_values(
            "Overall", ascending=False, kind="stable"
        )
        if df.empty:
            return {"error": f"No player found matching {name!r}"}
        row = df.iloc[0]
        profile = self._player_dict(row)
        skills = {}
        for col in ("Finishing", "Dribbling", "ShortPassing", "BallControl", "SprintSpeed", "Strength"):
            if col in row and pd.notna(row[col]):
                skills[col] = int(row[col])
        profile["skills"] = skills
        profile["preferred_foot"] = (
            None if pd.isna(row.get("Preferred Foot")) else row["Preferred Foot"]
        )
        exact = df[df["name_key"] == str(name).strip().lower()]
        profile["exact_match"] = bool(len(exact))
        if len(df) > 1:
            profile["other_matches"] = [p["name"] for p in (self._player_dict(r) for _, r in df.iloc[1:6].iterrows())]
        return profile

    def club_roster(self, club: str, nationality: str | None = None) -> dict[str, Any]:
        """Players at a club plus average rating summary."""
        df = self._filter_players(club=club, nationality=nationality).sort_values(
            "Overall", ascending=False, kind="stable"
        )
        if df.empty:
            return {"error": f"No players found for club {club!r}", "players": [], "total": 0}
        return {
            "club": club,
            "nationality": nationality,
            "total": int(len(df)),
            "average_overall": round(float(df["Overall"].mean()), 1),
            "players": [self._player_dict(r) for _, r in df.iterrows()],
        }

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------

    def standings(
        self, season: int, competition: str = BRASILEIRAO_A
    ) -> dict[str, Any]:
        """League table calculated from match results (3/1/0 points)."""
        comp = resolve_competition(competition, self.competitions())
        df = self._filter_matches(competition=comp, season=int(season))
        if df.empty:
            return {"error": f"No matches found for {comp} {season}", "standings": []}
        table: dict[str, dict[str, Any]] = {}

        def slot(key: str) -> dict[str, Any]:
            return table.setdefault(
                key,
                {"team": self._display(key), "played": 0, "wins": 0, "draws": 0,
                 "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0},
            )

        for _, r in df.iterrows():
            h, a = slot(r["home_key"]), slot(r["away_key"])
            hg, ag = int(r["home_goals"]), int(r["away_goals"])
            h["played"] += 1
            a["played"] += 1
            h["goals_for"] += hg
            h["goals_against"] += ag
            a["goals_for"] += ag
            a["goals_against"] += hg
            if hg > ag:
                h["wins"] += 1; h["points"] += 3; a["losses"] += 1
            elif hg < ag:
                a["wins"] += 1; a["points"] += 3; h["losses"] += 1
            else:
                h["draws"] += 1; a["draws"] += 1
                h["points"] += 1; a["points"] += 1
        rows = list(table.values())
        for r in rows:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        rows.sort(
            key=lambda r: (r["points"], r["wins"], r["goal_difference"], r["goals_for"]),
            reverse=True,
        )
        for i, r in enumerate(rows, 1):
            r["position"] = i
        relegated = (
            [r["team"] for r in rows[-4:]] if comp in (BRASILEIRAO_A, BRASILEIRAO_B) and len(rows) >= 20 else []
        )
        return {
            "competition": comp,
            "season": int(season),
            "matches": int(len(df)),
            "champion": rows[0]["team"] if rows else None,
            "relegated": relegated,
            "standings": rows,
        }

    def competition_schedule(
        self, competition: str, season: int | None = None, stage: str | None = None, limit: int = 100
    ) -> dict[str, Any]:
        """Matches of a competition, optionally one season / stage (bracket)."""
        comp = resolve_competition(competition, self.competitions())
        df = self._filter_matches(competition=comp, season=season)
        if stage:
            needle = normalize_text(stage)
            df = df[df["round"].map(lambda r: pd.notna(r) and normalize_text(r) == needle)]
        df = df.sort_values(["date"], kind="stable")
        stages = sorted({str(r) for r in df["round"].dropna().unique()})
        return {
            "competition": comp,
            "season": season,
            "stages": stages,
            "total": int(len(df)),
            "matches": [self._match_dict(r) for _, r in df.head(limit).iterrows()],
        }

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------

    def biggest_wins(
        self,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Largest victory margins in the (filtered) dataset."""
        df = self._filter_matches(competition=competition, season=season).copy()
        df["margin"] = (df["home_goals"] - df["away_goals"]).abs()
        df["total_goals"] = df["home_goals"] + df["away_goals"]
        df = df.sort_values(
            ["margin", "total_goals", "date"], ascending=[False, False, False], kind="stable"
        )
        return {
            "biggest_wins": [self._match_dict(r) for _, r in df.head(limit).iterrows()],
            "matches_considered": int(len(df)),
        }

    def competition_stats(
        self, competition: str | None = None, season: int | None = None
    ) -> dict[str, Any]:
        """Aggregate stats: averages, home/away/draw rates."""
        df = self._filter_matches(competition=competition, season=season)
        if df.empty:
            return {"error": "No matches found for the given filters"}
        total = len(df)
        goals = int((df["home_goals"] + df["away_goals"]).sum())
        home_wins = int((df["home_goals"] > df["away_goals"]).sum())
        draws = int((df["home_goals"] == df["away_goals"]).sum())
        away_wins = total - home_wins - draws
        return {
            "competition": resolve_competition(competition, self.competitions()),
            "season": season,
            "matches": int(total),
            "total_goals": goals,
            "avg_goals_per_match": round(goals / total, 2),
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "home_win_rate_pct": round(100.0 * home_wins / total, 1),
            "draw_rate_pct": round(100.0 * draws / total, 1),
            "away_win_rate_pct": round(100.0 * away_wins / total, 1),
        }

    def compare_seasons(
        self, season_a: int, season_b: int, competition: str | None = None
    ) -> dict[str, Any]:
        """Side-by-side aggregate comparison of two seasons."""
        return {
            "competition": resolve_competition(competition, self.competitions()),
            "season_a": self.competition_stats(competition=competition, season=int(season_a)),
            "season_b": self.competition_stats(competition=competition, season=int(season_b)),
        }

    def top_scoring_teams(
        self, season: int | None = None, competition: str | None = None, limit: int = 10
    ) -> dict[str, Any]:
        """Teams ranked by goals scored in the filtered dataset."""
        df = self._filter_matches(competition=competition, season=season)
        goals: dict[str, int] = {}
        for _, r in df.iterrows():
            goals[r["home_key"]] = goals.get(r["home_key"], 0) + int(r["home_goals"])
            goals[r["away_key"]] = goals.get(r["away_key"], 0) + int(r["away_goals"])
        ranked = sorted(goals.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return {
            "competition": resolve_competition(competition, self.competitions()),
            "season": season,
            "top_scoring_teams": [
                {"team": self._display(k), "goals": v} for k, v in ranked
            ],
        }
