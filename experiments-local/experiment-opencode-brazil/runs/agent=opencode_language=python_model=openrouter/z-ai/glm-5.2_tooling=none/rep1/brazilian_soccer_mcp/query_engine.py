from datetime import date
from typing import Optional

import pandas as pd

from .normalizers import canonical_team_id, team_display_name, parse_date, DERBIES
from .models import Match, TeamStats, StandingRow, HeadToHead, Player, CompetitionStat
from .data_loader import DataBundle


class QueryEngine:
    def __init__(self, bundle: DataBundle):
        self.bundle = bundle
        self.matches = bundle.matches_unique

    def _team_id(self, name: str) -> str:
        return canonical_team_id(name)

    def _df_for_aggregation(self, competition: Optional[str], season: Optional[int]) -> pd.DataFrame:
        df = self.matches
        if competition:
            df = df[df["competition"] == competition]
        if season is not None:
            df = df[df["season"] == int(season)]
        return df

    def _team_mask(self, df: pd.DataFrame, team_id: str, side: str = "either") -> pd.Series:
        if side == "home":
            return df["home_id"] == team_id
        if side == "away":
            return df["away_id"] == team_id
        return (df["home_id"] == team_id) | (df["away_id"] == team_id)

    def _row_to_match(self, row: pd.Series) -> Match:
        return Match(
            date=row.get("date"),
            home_id=row["home_id"],
            home_name=row["home_name"],
            away_id=row["away_id"],
            away_name=row["away_name"],
            home_goal=int(row["home_goal"]),
            away_goal=int(row["away_goal"]),
            season=row.get("season"),
            competition=row["competition"],
            round=row.get("round"),
            stage=row.get("stage"),
            stadium=row.get("stadium"),
            home_state=row.get("home_state"),
            away_state=row.get("away_state"),
            sources=list(row.get("sources", [])),
        )

    def search_matches(
        self,
        team: Optional[str] = None,
        vs_team: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        side: str = "either",
        limit: Optional[int] = None,
    ) -> list[Match]:
        df = self._df_for_aggregation(competition, season)
        if team:
            tid = self._team_id(team)
            df = df[self._team_mask(df, tid, side)]
        if vs_team:
            vid = self._team_id(vs_team)
            df = df[
                (df["home_id"] == vid) | (df["away_id"] == vid)
            ]
            if team:
                tid = self._team_id(team)
                df = df[self._team_mask(df, tid, side)]
        if date_from:
            d0 = parse_date(date_from)
            if d0:
                df = df[df["date"].apply(lambda d: d is not None and d >= d0)]
        if date_to:
            d1 = parse_date(date_to)
            if d1:
                df = df[df["date"].apply(lambda d: d is not None and d <= d1)]
        df = df.sort_values(["date"], na_position="last")
        if limit:
            df = df.head(int(limit))
        return [self._row_to_match(r) for _, r in df.iterrows()]

    def head_to_head(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> HeadToHead:
        a_id = self._team_id(team_a)
        b_id = self._team_id(team_b)
        df = self.matches
        if competition:
            df = df[df["competition"] == competition]
        mask = (
            ((df["home_id"] == a_id) & (df["away_id"] == b_id))
            | ((df["home_id"] == b_id) & (df["away_id"] == a_id))
        )
        df = df[mask].sort_values("date", na_position="last")
        a_wins = b_wins = draws = a_goals = b_goals = 0
        matches = []
        for _, r in df.iterrows():
            hg, ag = int(r["home_goal"]), int(r["away_goal"])
            if r["home_id"] == a_id:
                a_g, b_g = hg, ag
            else:
                a_g, b_g = ag, hg
            a_goals += a_g
            b_goals += b_g
            if a_g > b_g:
                a_wins += 1
            elif b_g > a_g:
                b_wins += 1
            else:
                draws += 1
            matches.append(self._row_to_match(r))
        return HeadToHead(
            team_a_id=a_id,
            team_a_name=team_display_name(a_id),
            team_b_id=b_id,
            team_b_name=team_display_name(b_id),
            team_a_wins=a_wins,
            team_b_wins=b_wins,
            draws=draws,
            team_a_goals=a_goals,
            team_b_goals=b_goals,
            matches=matches,
        )

    def team_statistics(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        home_away: str = "overall",
    ) -> TeamStats:
        tid = self._team_id(team)
        df = self._df_for_aggregation(competition, season)
        if home_away == "home":
            df = df[df["home_id"] == tid]
        elif home_away == "away":
            df = df[df["away_id"] == tid]
        else:
            df = df[(df["home_id"] == tid) | (df["away_id"] == tid)]
        wins = draws = losses = gf = ga = 0
        for _, r in df.iterrows():
            hg, ag = int(r["home_goal"]), int(r["away_goal"])
            if r["home_id"] == tid:
                tfg, tag = hg, ag
            else:
                tfg, tag = ag, hg
            gf += tfg
            ga += tag
            if tfg > tag:
                wins += 1
            elif tag > tfg:
                losses += 1
            else:
                draws += 1
        matches = len(df)
        win_rate = round(wins / matches, 4) if matches else 0.0
        return TeamStats(
            team_id=tid,
            team_name=team_display_name(tid),
            season=season,
            competition=competition,
            home_away=home_away,
            matches=matches,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=gf,
            goals_against=ga,
            win_rate=win_rate,
        )

    def top_teams_by_record(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        home_away: str = "overall",
        metric: str = "win_rate",
        limit: int = 10,
    ) -> list[TeamStats]:
        df = self._df_for_aggregation(competition, season)
        if home_away == "home":
            teams = set(df["home_id"].unique())
        elif home_away == "away":
            teams = set(df["away_id"].unique())
        else:
            teams = set(df["home_id"].unique()) | set(df["away_id"].unique())
        stats = []
        for tid in teams:
            stats.append(
                self.team_statistics(tid, season, competition, home_away)
            )
        reverse = metric in ("win_rate", "wins", "goals_for")
        stats.sort(
            key=lambda s: (
                getattr(s, metric),
                s.wins,
                s.goals_for - s.goals_against,
            ),
            reverse=reverse,
        )
        return stats[: int(limit)]

    def most_goals_scored(
        self, competition: Optional[str] = None, season: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict]:
        df = self._df_for_aggregation(competition, season)
        home_gf = df.groupby("home_id")["home_goal"].sum()
        away_gf = df.groupby("away_id")["away_goal"].sum()
        totals = home_gf.add(away_gf, fill_value=0).astype(int)
        rows = []
        for tid, goals in totals.sort_values(ascending=False).head(int(limit)).items():
            rows.append({
                "team_id": tid,
                "team_name": team_display_name(tid),
                "goals": int(goals),
            })
        return rows

    def _player_row(self, r: pd.Series) -> Player:
        skills = {}
        for c in r.index:
            if c in (
                "Crossing", "Finishing", "Dribbling", "ShortPassing",
                "LongPassing", "BallControl", "ShotPower", "Vision",
                "Penalties", "StandingTackle",
            ):
                v = r[c]
                if pd.notna(v):
                    skills[c] = int(v)
        return Player(
            id=int(r["ID"]) if pd.notna(r["ID"]) else 0,
            name=r["Name"],
            age=int(r["Age"]) if pd.notna(r["Age"]) else None,
            nationality=r["Nationality"],
            overall=int(r["Overall"]) if pd.notna(r["Overall"]) else 0,
            potential=int(r["Potential"]) if pd.notna(r["Potential"]) else 0,
            club_id=r["club_id"],
            club=r["Club"] if pd.notna(r["Club"]) else "",
            position=r["Position"] if pd.notna(r["Position"]) else None,
            jersey_number=int(r["Jersey Number"]) if pd.notna(r["Jersey Number"]) else None,
            height=r["Height"] if pd.notna(r["Height"]) else None,
            weight=r["Weight"] if pd.notna(r["Weight"]) else None,
            preferred_foot=r["Preferred Foot"] if pd.notna(r["Preferred Foot"]) else None,
            skills=skills,
        )

    def search_player(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = None,
        sort_by: str = "Overall",
    ) -> list[Player]:
        df = self.bundle.players
        if name:
            from .normalizers import _clean
            target = _clean(name)
            df = df[df["Name"].apply(lambda n: target in _clean(n) if isinstance(n, str) else False)]
        if nationality:
            from .normalizers import _clean
            nat = _clean(nationality)
            df = df[df["Nationality"].apply(lambda n: nat == _clean(n) if isinstance(n, str) else False)]
        if club:
            cid = canonical_team_id(club)
            df = df[df["club_id"] == cid]
        if position:
            df = df[df["Position"] == position]
        if min_overall is not None:
            df = df[df["Overall"] >= int(min_overall)]
        if sort_by and sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=False)
        if limit:
            df = df.head(int(limit))
        return [self._player_row(r) for _, r in df.iterrows()]

    def top_players(
        self,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> list[Player]:
        return self.search_player(
            nationality=nationality, club=club, position=position,
            limit=limit, sort_by="Overall",
        )

    def players_at_club(self, club: str) -> dict:
        cid = canonical_team_id(club)
        df = self.bundle.players
        sub = df[df["club_id"] == cid]
        players = [self._player_row(r) for _, r in sub.iterrows()]
        avg = round(sub["Overall"].mean(), 2) if len(sub) else 0.0
        return {
            "club_id": cid,
            "club_name": team_display_name(cid),
            "count": len(players),
            "avg_overall": avg,
            "players": players,
        }

    def competition_standings(
        self, competition: str, season: int, limit: Optional[int] = None,
    ) -> list[StandingRow]:
        df = self._df_for_aggregation(competition, season)
        teams = set(df["home_id"].unique()) | set(df["away_id"].unique())
        table = {}
        for tid in teams:
            table[tid] = {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
                          "gf": 0, "ga": 0}
        for _, r in df.iterrows():
            h, a = r["home_id"], r["away_id"]
            hg, ag = int(r["home_goal"]), int(r["away_goal"])
            table[h]["matches"] += 1
            table[a]["matches"] += 1
            table[h]["gf"] += hg
            table[h]["ga"] += ag
            table[a]["gf"] += ag
            table[a]["ga"] += hg
            if hg > ag:
                table[h]["wins"] += 1
                table[a]["losses"] += 1
            elif ag > hg:
                table[a]["wins"] += 1
                table[h]["losses"] += 1
            else:
                table[h]["draws"] += 1
                table[a]["draws"] += 1
        rows = []
        for tid, s in table.items():
            pts = 3 * s["wins"] + s["draws"]
            rows.append({
                "team_id": tid,
                "team_name": team_display_name(tid),
                "matches": s["matches"],
                "wins": s["wins"],
                "draws": s["draws"],
                "losses": s["losses"],
                "goals_for": s["gf"],
                "goals_against": s["ga"],
                "goal_difference": s["gf"] - s["ga"],
                "points": pts,
            })
        rows.sort(
            key=lambda r: (r["points"], r["wins"], r["goal_difference"], r["goals_for"]),
            reverse=True,
        )
        result = []
        for i, r in enumerate(rows, start=1):
            result.append(StandingRow(
                position=i,
                team_id=r["team_id"],
                team_name=r["team_name"],
                matches=r["matches"],
                wins=r["wins"],
                draws=r["draws"],
                losses=r["losses"],
                goals_for=r["goals_for"],
                goals_against=r["goals_against"],
                goal_difference=r["goal_difference"],
                points=r["points"],
            ))
        if limit:
            result = result[: int(limit)]
        return result

    def competition_champion(self, competition: str, season: int) -> Optional[StandingRow]:
        table = self.competition_standings(competition, season, limit=1)
        return table[0] if table else None

    def relegated_teams(self, competition: str, season: int, n: int = 4) -> list[StandingRow]:
        table = self.competition_standings(competition, season)
        return table[-int(n):] if table else []

    def average_goals_per_match(
        self, competition: Optional[str] = None, season: Optional[int] = None,
    ) -> float:
        df = self._df_for_aggregation(competition, season)
        if df.empty:
            return 0.0
        total = int(df["home_goal"].sum() + df["away_goal"].sum())
        return round(total / len(df), 4)

    def home_vs_away_performance(
        self, competition: Optional[str] = None, season: Optional[int] = None,
    ) -> dict:
        df = self._df_for_aggregation(competition, season)
        if df.empty:
            return {"home_wins": 0, "away_wins": 0, "draws": 0,
                    "home_win_rate": 0.0, "away_win_rate": 0.0, "draw_rate": 0.0,
                    "matches": 0}
        home_wins = int((df["home_goal"] > df["away_goal"]).sum())
        away_wins = int((df["away_goal"] > df["home_goal"]).sum())
        draws = int((df["home_goal"] == df["away_goal"]).sum())
        n = len(df)
        return {
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(home_wins / n, 4),
            "away_win_rate": round(away_wins / n, 4),
            "draw_rate": round(draws / n, 4),
            "matches": n,
        }

    def biggest_wins(
        self, competition: Optional[str] = None, season: Optional[int] = None,
        limit: int = 10,
    ) -> list[Match]:
        df = self._df_for_aggregation(competition, season).copy()
        if df.empty:
            return []
        df = df.assign(
            _diff=(df["home_goal"] - df["away_goal"]).abs()
        ).sort_values(["_diff", "home_goal"], ascending=False).head(int(limit))
        return [self._row_to_match(r) for _, r in df.iterrows()]

    def derbies(
        self, season: Optional[int] = None, competition: Optional[str] = None,
    ) -> list[dict]:
        df = self._df_for_aggregation(competition, season)
        results = []
        for a, b, name in DERBIES:
            mask = (
                ((df["home_id"] == a) & (df["away_id"] == b))
                | ((df["home_id"] == b) & (df["away_id"] == a))
            )
            sub = df[mask].sort_values("date", na_position="last")
            matches = [self._row_to_match(r) for _, r in sub.iterrows()]
            results.append({
                "derby_name": name,
                "team_a": team_display_name(a),
                "team_b": team_display_name(b),
                "count": len(matches),
                "matches": matches,
            })
        return results

    def match_stats(
        self, team: Optional[str] = None, vs_team: Optional[str] = None,
        season: Optional[int] = None, limit: Optional[int] = None,
    ) -> list[dict]:
        df = self.bundle.stats
        if season is not None:
            df = df[df["season"] == int(season)]
        if team:
            tid = self._team_id(team)
            df = df[(df["home_id"] == tid) | (df["away_id"] == tid)]
        if vs_team:
            vid = self._team_id(vs_team)
            df = df[(df["home_id"] == vid) | (df["away_id"] == vid)]
        df = df.sort_values("date", na_position="last")
        if limit:
            df = df.head(int(limit))
        return df.to_dict(orient="records")

    def available_competitions(self) -> list:
        return list(self.bundle.competitions)

    def available_seasons(self, competition: Optional[str] = None) -> list:
        if competition:
            return list(self.bundle.seasons.get(competition, []))
        return self.bundle.seasons

    def data_coverage(self) -> dict:
        mu = self.matches
        return {
            "matches_unique": int(len(mu)),
            "matches_raw": int(len(self.bundle.matches)),
            "players": int(len(self.bundle.players)),
            "matches_with_stats": int(len(self.bundle.stats)),
            "competitions": self.available_competitions(),
            "seasons": {k: [int(s) for s in v] for k, v in self.bundle.seasons.items()},
        }
