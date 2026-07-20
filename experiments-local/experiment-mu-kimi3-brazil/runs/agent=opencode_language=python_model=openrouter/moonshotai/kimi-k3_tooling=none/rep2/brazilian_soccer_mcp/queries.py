"""Query engine implementing the five capability categories from the spec:

1. Match queries        -- :meth:`QueryEngine.search_matches`,
                           :meth:`QueryEngine.head_to_head`
2. Team queries         -- :meth:`QueryEngine.team_statistics`
3. Player queries       -- :meth:`QueryEngine.search_players`,
                           :meth:`QueryEngine.top_players`
4. Competition queries  -- :meth:`QueryEngine.standings`,
                           :meth:`QueryEngine.team_competitions`
5. Statistical analysis -- :meth:`QueryEngine.biggest_wins`,
                           :meth:`QueryEngine.competition_stats`
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .data import DataStore
from .normalization import (
    COMP_BRASILEIRAO_A,
    competition_key,
    norm_text,
    parse_date,
    team_key,
)

_PLAYER_COLS = [
    "ID", "Name", "Age", "Nationality", "Overall", "Potential",
    "Club", "Position", "Jersey Number", "Height", "Weight",
    "Preferred Foot",
]


def _match_to_dict(store: DataStore, row) -> dict[str, Any]:
    return {
        "date": row.date.isoformat() if isinstance(row.date, date) else None,
        "home_team": store.display_name(row.home_key),
        "away_team": store.display_name(row.away_key),
        "home_goals": row.home_goals,
        "away_goals": row.away_goals,
        "score": (
            f"{row.home_goals}-{row.away_goals}"
            if row.home_goals is not None and row.away_goals is not None
            else None
        ),
        "competition": row.competition,
        "season": row.season,
        "round": row.round or None,
    }


class QueryEngine:
    """Runs all queries against a loaded :class:`DataStore`."""

    def __init__(self, store: DataStore | None = None) -> None:
        self.store = store or DataStore()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_team(self, team: str) -> str:
        key = team_key(team)
        if not key:
            raise ValueError(f"Could not understand team name: {team!r}")
        if key not in self.store.team_keys:
            # Substring fallback over known keys (e.g. "corinthians paulista").
            needle = norm_text(team)
            candidates = [k for k in self.store.team_keys if needle in k or k in needle]
            if candidates:
                return sorted(candidates, key=len)[0]
            raise ValueError(f"Team not found in dataset: {team!r}")
        return key

    def _played(self, df: pd.DataFrame) -> pd.DataFrame:
        """Keep only rows with a recorded scoreline."""
        return df[df["home_goals"].notna() & df["away_goals"].notna()]

    def _filter(
        self,
        df: pd.DataFrame | None = None,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> pd.DataFrame:
        out = self.store.canonical if df is None else df
        if team:
            key = self._resolve_team(team)
            out = out[(out["home_key"] == key) | (out["away_key"] == key)]
            if opponent:
                opp = self._resolve_team(opponent)
                out = out[(out["home_key"] == opp) | (out["away_key"] == opp)]
        elif opponent:
            opp = self._resolve_team(opponent)
            out = out[(out["home_key"] == opp) | (out["away_key"] == opp)]
        if competition:
            comp = competition_key(competition)
            if not comp:
                raise ValueError(f"Unknown competition: {competition!r}")
            out = out[out["competition"] == comp]
        if season is not None:
            out = out[out["season"] == int(season)]
        start = parse_date(date_from) if date_from else None
        end = parse_date(date_to) if date_to else None
        if start:
            out = out[out["date"].map(lambda d: d is not None and d >= start)]
        if end:
            out = out[out["date"].map(lambda d: d is not None and d <= end)]
        return out

    @staticmethod
    def _sorted(df: pd.DataFrame, descending: bool = True) -> pd.DataFrame:
        return df.sort_values(
            "date", ascending=not descending,
            key=lambda s: s.map(lambda d: d.toordinal() if d else 0),
        )

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Find matches by team, opponent, competition, season or date range."""
        df = self._filter(
            team=team, opponent=opponent, competition=competition,
            season=season, date_from=date_from, date_to=date_to,
        )
        df = self._sorted(df, descending=True)
        total = len(df)
        rows = [
            _match_to_dict(self.store, row)
            for row in df.head(max(1, int(limit))).itertuples(index=False)
        ]
        return {"total": int(total), "returned": len(rows), "matches": rows}

    def head_to_head(self, team_a: str, team_b: str,
                     limit: int = 10) -> dict[str, Any]:
        """All meetings between two teams plus the win/draw summary."""
        key_a, key_b = self._resolve_team(team_a), self._resolve_team(team_b)
        df = self.store.canonical
        df = df[
            ((df["home_key"] == key_a) & (df["away_key"] == key_b))
            | ((df["home_key"] == key_b) & (df["away_key"] == key_a))
        ]
        played = self._played(df)
        wins_a = int((
            ((played["home_key"] == key_a) & (played["home_goals"] > played["away_goals"]))
            | ((played["away_key"] == key_a) & (played["away_goals"] > played["home_goals"]))
        ).sum())
        wins_b = int((
            ((played["home_key"] == key_b) & (played["home_goals"] > played["away_goals"]))
            | ((played["away_key"] == key_b) & (played["away_goals"] > played["home_goals"]))
        ).sum())
        draws = int(len(played)) - wins_a - wins_b
        recent = self._sorted(df, descending=True).head(max(1, int(limit)))
        name_a, name_b = self.store.display_name(key_a), self.store.display_name(key_b)
        return {
            "team_a": name_a,
            "team_b": name_b,
            "total_matches": int(len(df)),
            "wins_a": wins_a,
            "wins_b": wins_b,
            "draws": draws,
            "matches": [
                _match_to_dict(self.store, row)
                for row in recent.itertuples(index=False)
            ],
            "summary": (
                f"{name_a} vs {name_b}: {len(df)} matches in dataset — "
                f"{name_a} {wins_a} wins, {name_b} {wins_b} wins, {draws} draws"
            ),
        }

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------

    def team_statistics(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str = "all",
    ) -> dict[str, Any]:
        """Win/draw/loss record and goals for a team (optionally filtered)."""
        key = self._resolve_team(team)
        df = self._filter(team=team, competition=competition, season=season)
        venue_norm = norm_text(venue)
        if venue_norm in {"home", "casa"}:
            df = df[df["home_key"] == key]
        elif venue_norm in {"away", "fora"}:
            df = df[df["away_key"] == key]
        elif venue_norm != "all":
            raise ValueError(f"venue must be 'home', 'away' or 'all', got {venue!r}")
        played = self._played(df)

        wins = draws = losses = goals_for = goals_against = 0
        for row in played.itertuples(index=False):
            is_home = row.home_key == key
            gf, ga = (
                (row.home_goals, row.away_goals)
                if is_home else (row.away_goals, row.home_goals)
            )
            goals_for += gf
            goals_against += ga
            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                draws += 1

        n = len(played)
        name = self.store.display_name(key)
        result = {
            "team": name,
            "season": season,
            "competition": competition,
            "venue": venue_norm,
            "matches": int(n),
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": int(goals_for),
            "goals_against": int(goals_against),
            "goal_difference": int(goals_for - goals_against),
            "win_rate": round(100.0 * wins / n, 1) if n else 0.0,
        }
        result["summary"] = (
            f"{name} record"
            + (f" ({season}" if season else " (all seasons")
            + (f", {competition}" if competition else "")
            + (f", {venue_norm} only" if venue_norm != "all" else "")
            + f"): {n} matches — {wins}W {draws}D {losses}L, "
            f"GF {goals_for}, GA {goals_against}, "
            f"win rate {result['win_rate']}%"
        )
        return result

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------

    def _player_rows(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        cols = [c for c in _PLAYER_COLS if c in df.columns]
        out = []
        for row in df[cols].itertuples(index=False):
            record = {
                col: (None if pd.isna(val) else val)
                for col, val in zip(cols, row)
            }
            for num_col in ("ID", "Age", "Overall", "Potential", "Jersey Number"):
                if record.get(num_col) is not None:
                    record[num_col] = int(record[num_col])
            out.append(record)
        return out

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search the FIFA player database by name, nationality, club, ..."""
        df = self.store.players
        if name:
            needle = norm_text(name)
            df = df[df["_name_key"].str.contains(needle, regex=False, na=False)]
        if nationality:
            needle = norm_text(nationality)
            df = df[df["_nat_key"].str.contains(needle, regex=False, na=False)]
        if club:
            needle = norm_text(club)
            df = df[df["_club_key"].str.contains(needle, regex=False, na=False)]
        if position:
            needle = norm_text(position)
            df = df[df["_pos_key"].str.contains(needle, regex=False, na=False)]
        if min_overall is not None:
            df = df[df["Overall"] >= int(min_overall)]
        df = df.sort_values("Overall", ascending=False)
        total = len(df)
        return {
            "total": int(total),
            "returned": min(int(limit), total),
            "players": self._player_rows(df.head(max(1, int(limit)))),
        }

    def top_players(
        self,
        nationality: str | None = None,
        club: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Highest-rated players, optionally filtered by nationality/club."""
        return self.search_players(
            nationality=nationality, club=club, limit=limit
        )

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------

    def _standings_frame(self, season: int, competition: str) -> pd.DataFrame:
        comp = competition_key(competition)
        if not comp:
            raise ValueError(f"Unknown competition: {competition!r}")
        # store.canonical already picks one best source per season.
        df = self.store.canonical
        df = df[(df["competition"] == comp) & (df["season"] == int(season))]
        df = self._played(df)
        if df.empty:
            raise ValueError(
                f"No played matches found for {comp} season {season}"
            )
        return df

    def standings(
        self, season: int, competition: str = COMP_BRASILEIRAO_A
    ) -> dict[str, Any]:
        """League table for *season*, calculated from match results (3/1/0)."""
        df = self._standings_frame(season, competition)
        table: dict[str, dict[str, int]] = {}

        def entry(key: str) -> dict[str, int]:
            return table.setdefault(key, {
                "played": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "points": 0,
            })

        for row in df.itertuples(index=False):
            home, away = entry(row.home_key), entry(row.away_key)
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += row.home_goals
            home["goals_against"] += row.away_goals
            away["goals_for"] += row.away_goals
            away["goals_against"] += row.home_goals
            if row.home_goals > row.away_goals:
                home["wins"] += 1
                home["points"] += 3
                away["losses"] += 1
            elif row.home_goals < row.away_goals:
                away["wins"] += 1
                away["points"] += 3
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        rows = []
        for key, stats in table.items():
            rows.append({
                "team": self.store.display_name(key),
                "team_key": key,
                **stats,
                "goal_difference": stats["goals_for"] - stats["goals_against"],
            })
        rows.sort(
            key=lambda r: (
                -r["points"], -r["wins"], -r["goal_difference"], -r["goals_for"],
                r["team"],
            )
        )
        for i, row in enumerate(rows, start=1):
            row["position"] = i
        n = len(rows)
        for row in rows:
            if row["position"] == 1:
                row["tag"] = "Champion"
            elif n >= 20 and row["position"] > n - 4:
                row["tag"] = "Relegated"
            else:
                row["tag"] = None
        comp = competition_key(competition)
        return {
            "competition": comp,
            "season": int(season),
            "teams": len(rows),
            "standings": rows,
            "champion": rows[0]["team"] if rows else None,
            "relegated": [r["team"] for r in rows if r["tag"] == "Relegated"],
        }

    def team_competitions(self, team: str) -> dict[str, Any]:
        """Competitions a team appears in (knowledge-graph traversal)."""
        key = self._resolve_team(team)
        comps = self.store.graph.team_competitions(team)
        seasons = (
            self.store.canonical[
                (self.store.canonical["home_key"] == key)
                | (self.store.canonical["away_key"] == key)
            ]["season"]
            .dropna()
            .astype(int)
        )
        return {
            "team": self.store.display_name(key),
            "competitions": comps,
            "first_season": int(seasons.min()) if len(seasons) else None,
            "last_season": int(seasons.max()) if len(seasons) else None,
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
        """Largest victory margins in the dataset."""
        df = self._played(self._filter(competition=competition, season=season))
        df = df.assign(
            margin=(df["home_goals"] - df["away_goals"]).abs(),
            total_goals=df["home_goals"] + df["away_goals"],
        )
        df = df.sort_values(["margin", "total_goals"], ascending=False)
        rows = []
        for row in df.head(max(1, int(limit))).itertuples(index=False):
            record = _match_to_dict(self.store, row)
            record["margin"] = int(row.margin)
            rows.append(record)
        return {"returned": len(rows), "biggest_wins": rows}

    def competition_stats(
        self,
        competition: str | None = None,
        season: int | None = None,
    ) -> dict[str, Any]:
        """Aggregate stats: averages, home/draw/away rates, record scoreline."""
        df = self._played(self._filter(competition=competition, season=season))
        n = len(df)
        if n == 0:
            raise ValueError("No played matches match the given filters")
        total_goals = int((df["home_goals"] + df["away_goals"]).sum())
        home_wins = int((df["home_goals"] > df["away_goals"]).sum())
        away_wins = int((df["home_goals"] < df["away_goals"]).sum())
        draws = n - home_wins - away_wins
        biggest = self.biggest_wins(competition=competition, season=season, limit=1)
        return {
            "competition": competition_key(competition) if competition else "all",
            "season": season,
            "matches": n,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / n, 2),
            "home_win_rate": round(100.0 * home_wins / n, 1),
            "draw_rate": round(100.0 * draws / n, 1),
            "away_win_rate": round(100.0 * away_wins / n, 1),
            "biggest_win": biggest["biggest_wins"][0] if biggest["biggest_wins"] else None,
        }

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def overview(self) -> dict[str, Any]:
        """Dataset overview (rows per source, coverage, graph stats)."""
        info = self.store.overview()
        info["graph"] = self.store.graph.stats()
        return info
