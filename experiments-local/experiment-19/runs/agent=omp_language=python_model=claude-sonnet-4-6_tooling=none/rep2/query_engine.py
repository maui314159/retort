"""
Query engine for Brazilian Soccer MCP Server.

All query logic lives here, independent of the MCP transport layer,
making it straightforwardly testable.
"""

from typing import Any, Optional

import pandas as pd

from data_loader import SoccerDataLoader, normalize_team, strip_accents

COMPETITION_ALIASES: dict[str, list[str]] = {
    "brasileirao": ["brasileirão", "brasileirao", "serie a", "campeonato brasileiro"],
    "copa do brasil": ["copa do brasil", "copa brasil", "brazilian cup"],
    "copa libertadores": ["libertadores", "copa libertadores"],
}


def _resolve_competition(query: str) -> str:
    """Return accent-stripped canonical competition search term."""
    q = strip_accents(query.lower())
    for canon, aliases in COMPETITION_ALIASES.items():
        for alias in aliases:
            if strip_accents(alias) in q:
                return strip_accents(canon)
    return q


def _comp_mask(series: pd.Series, comp: str) -> pd.Series:
    """Accent-insensitive competition contains check."""
    comp_norm = strip_accents(comp)
    return series.apply(lambda x: strip_accents(str(x).lower())).str.contains(
        comp_norm, na=False
    )


class QueryEngine:
    """
    Executes queries against the loaded soccer data.

    All methods return plain Python dicts/lists that the MCP server
    formats into human-readable strings before returning to callers.
    """

    def __init__(self, loader: Optional[SoccerDataLoader] = None):
        self.loader = loader or SoccerDataLoader()

    # ------------------------------------------------------------------ #
    # Match queries                                                        #
    # ------------------------------------------------------------------ #

    def search_matches(
        self,
        team: str,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Return matches involving *team*, optionally filtered by opponent,
        competition, season, or date range.  Results are sorted newest-first.
        """
        df = self.loader.matches
        norm = normalize_team(team)

        mask = df["home_team"].str.contains(norm, na=False) | df["away_team"].str.contains(
            norm, na=False
        )

        if opponent:
            norm_opp = normalize_team(opponent)
            mask &= df["home_team"].str.contains(norm_opp, na=False) | df[
                "away_team"
            ].str.contains(norm_opp, na=False)

        if competition:
            comp = _resolve_competition(competition)
            mask &= _comp_mask(df["competition"], comp)

        if season is not None:
            mask &= df["season"] == int(season)

        if date_from:
            mask &= df["date"] >= date_from

        if date_to:
            mask &= df["date"] <= date_to

        result = df[mask].sort_values("date", ascending=False).head(limit)
        return result.to_dict("records")

    def head_to_head(
        self,
        team1: str,
        team2: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """
        Return head-to-head record between two teams plus match list.
        """
        matches = self.search_matches(
            team=team1,
            opponent=team2,
            competition=competition,
            season=season,
            limit=500,
        )

        norm1 = normalize_team(team1)
        norm2 = normalize_team(team2)

        t1_wins = t2_wins = draws = 0
        for m in matches:
            ht, at = m["home_team"], m["away_team"]
            hg, ag = m["home_goal"], m["away_goal"]
            if norm1 in ht and norm2 in at:
                if hg > ag:
                    t1_wins += 1
                elif ag > hg:
                    t2_wins += 1
                else:
                    draws += 1
            elif norm2 in ht and norm1 in at:
                if ag > hg:
                    t1_wins += 1
                elif hg > ag:
                    t2_wins += 1
                else:
                    draws += 1
            else:
                # Fallback: team1 substring match
                if hg > ag:
                    t1_wins += 1
                elif ag > hg:
                    t2_wins += 1
                else:
                    draws += 1

        return {
            "team1": team1,
            "team2": team2,
            "team1_wins": t1_wins,
            "team2_wins": t2_wins,
            "draws": draws,
            "total_matches": len(matches),
            "matches": matches,
        }

    # ------------------------------------------------------------------ #
    # Team statistics                                                      #
    # ------------------------------------------------------------------ #

    def get_team_stats(
        self,
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "both",  # "home" | "away" | "both"
    ) -> dict:
        """Return wins/losses/draws/goals for a team."""
        df = self.loader.matches
        norm = normalize_team(team)

        home_mask = df["home_team"].str.contains(norm, na=False)
        away_mask = df["away_team"].str.contains(norm, na=False)

        if competition:
            comp = _resolve_competition(competition)
            comp_mask = _comp_mask(df["competition"], comp)
            home_mask &= comp_mask
            away_mask &= comp_mask

        if season is not None:
            season_mask = df["season"] == int(season)
            home_mask &= season_mask
            away_mask &= season_mask

        if venue == "home":
            away_mask = pd.Series([False] * len(df), index=df.index)
        elif venue == "away":
            home_mask = pd.Series([False] * len(df), index=df.index)

        home_games = df[home_mask]
        away_games = df[away_mask]

        # Vectorised result calculation
        hw = int((home_games["home_goal"] > home_games["away_goal"]).sum())
        hd = int((home_games["home_goal"] == home_games["away_goal"]).sum())
        hl = int((home_games["home_goal"] < home_games["away_goal"]).sum())

        aw = int((away_games["away_goal"] > away_games["home_goal"]).sum())
        ad = int((away_games["away_goal"] == away_games["home_goal"]).sum())
        al = int((away_games["away_goal"] < away_games["home_goal"]).sum())

        wins = hw + aw
        draws = hd + ad
        losses = hl + al
        goals_for = int(home_games["home_goal"].sum() + away_games["away_goal"].sum())
        goals_against = int(
            home_games["away_goal"].sum() + away_games["home_goal"].sum()
        )
        total = wins + draws + losses

        return {
            "team": team,
            "matches": total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_diff": goals_for - goals_against,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
            "competition": competition or "all",
            "season": season or "all",
            "venue": venue,
        }

    # ------------------------------------------------------------------ #
    # Player queries                                                       #
    # ------------------------------------------------------------------ #

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search FIFA player data with any combination of filters."""
        df = self.loader.players
        mask = pd.Series([True] * len(df), index=df.index)

        if name:
            mask &= df["Name"].str.contains(name, case=False, na=False)
        if nationality:
            mask &= df["Nationality"].str.contains(nationality, case=False, na=False)
        if club:
            mask &= df["Club"].str.contains(club, case=False, na=False)
        if position:
            mask &= df["Position"].str.contains(position, case=False, na=False)
        if min_overall is not None:
            overall_num = pd.to_numeric(df["Overall"], errors="coerce")
            mask &= overall_num >= int(min_overall)

        result = df[mask].copy()
        result["_overall_num"] = pd.to_numeric(result["Overall"], errors="coerce")
        result = result.sort_values("_overall_num", ascending=False).head(limit)

        cols = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position"]
        available = [c for c in cols if c in result.columns]
        return result[available].to_dict("records")

    def players_by_club_summary(self, nationality: str = "Brazil") -> list[dict]:
        """
        Return clubs with a count and average rating for players of the given nationality,
        sorted by player count descending.
        """
        df = self.loader.players
        mask = df["Nationality"].str.contains(nationality, case=False, na=False)
        filtered = df[mask].copy()
        filtered["_overall_num"] = pd.to_numeric(filtered["Overall"], errors="coerce")

        summary = (
            filtered.groupby("Club")
            .agg(count=("Name", "count"), avg_rating=("_overall_num", "mean"))
            .reset_index()
            .sort_values("count", ascending=False)
        )
        return [
            {
                "club": row["Club"],
                "player_count": int(row["count"]),
                "avg_rating": round(float(row["avg_rating"]), 1),
            }
            for _, row in summary.iterrows()
        ]

    # ------------------------------------------------------------------ #
    # Competition standings                                                #
    # ------------------------------------------------------------------ #

    def get_standings(
        self,
        competition: str,
        season: int,
        source_filter: Optional[str] = None,
    ) -> list[dict]:
        """
        Calculate and return standings for a competition/season pair.

        Points: Win = 3, Draw = 1, Loss = 0.
        Tiebreaker: goal difference, then goals scored.
        """
        df = self.loader.matches
        comp = _resolve_competition(competition)
        mask = _comp_mask(df["competition"], comp)
        mask &= df["season"] == int(season)

        if source_filter:
            mask &= df["source"] == source_filter

        season_df = df[mask]
        if season_df.empty:
            return []

        # Collect all unique teams (normalized)
        teams = sorted(
            set(season_df["home_team"].unique()) | set(season_df["away_team"].unique())
        )

        standings: list[dict] = []
        for team in teams:
            hg = season_df[season_df["home_team"] == team]
            ag = season_df[season_df["away_team"] == team]

            hw = int((hg["home_goal"] > hg["away_goal"]).sum())
            hd = int((hg["home_goal"] == hg["away_goal"]).sum())
            hl = int((hg["home_goal"] < hg["away_goal"]).sum())
            hgf = int(hg["home_goal"].sum())
            hga = int(hg["away_goal"].sum())

            aw = int((ag["away_goal"] > ag["home_goal"]).sum())
            ad = int((ag["away_goal"] == ag["home_goal"]).sum())
            al = int((ag["away_goal"] < ag["home_goal"]).sum())
            agf = int(ag["away_goal"].sum())
            aga = int(ag["home_goal"].sum())

            w, d, l = hw + aw, hd + ad, hl + al
            gf, ga = hgf + agf, hga + aga
            pts = w * 3 + d

            # Get a human-readable name: prefer the raw name most commonly used
            raw_home = hg["home_team_raw"].mode()
            raw_away = ag["away_team_raw"].mode()
            if not raw_home.empty:
                display = raw_home.iloc[0]
            elif not raw_away.empty:
                display = raw_away.iloc[0]
            else:
                display = team

            standings.append(
                {
                    "team": display,
                    "played": w + d + l,
                    "wins": w,
                    "draws": d,
                    "losses": l,
                    "goals_for": gf,
                    "goals_against": ga,
                    "goal_diff": gf - ga,
                    "points": pts,
                }
            )

        return sorted(
            standings,
            key=lambda x: (-x["points"], -x["goal_diff"], -x["goals_for"]),
        )

    # ------------------------------------------------------------------ #
    # Statistical analysis                                                 #
    # ------------------------------------------------------------------ #

    def get_global_stats(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict:
        """Return aggregated statistics: goals per match, home win rate, etc."""
        df = self.loader.matches
        mask = pd.Series([True] * len(df), index=df.index)

        if competition:
            comp = _resolve_competition(competition)
            mask &= _comp_mask(df["competition"], comp)
        if season is not None:
            mask &= df["season"] == int(season)

        subset = df[mask]
        total = len(subset)
        if total == 0:
            return {"error": "No matches found for given filters."}

        total_goals = int((subset["home_goal"] + subset["away_goal"]).sum())
        home_wins = int((subset["home_goal"] > subset["away_goal"]).sum())
        away_wins = int((subset["away_goal"] > subset["home_goal"]).sum())
        draws = int((subset["home_goal"] == subset["away_goal"]).sum())

        return {
            "total_matches": total,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / total, 2),
            "home_wins": home_wins,
            "home_win_rate": round(home_wins / total * 100, 1),
            "away_wins": away_wins,
            "away_win_rate": round(away_wins / total * 100, 1),
            "draws": draws,
            "draw_rate": round(draws / total * 100, 1),
            "competition": competition or "all",
            "season": season or "all",
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return matches with the largest goal-difference margin."""
        df = self.loader.matches
        mask = pd.Series([True] * len(df), index=df.index)

        if competition:
            comp = _resolve_competition(competition)
            mask &= _comp_mask(df["competition"], comp)
        if season is not None:
            mask &= df["season"] == int(season)

        subset = df[mask].copy()
        subset["margin"] = (subset["home_goal"] - subset["away_goal"]).abs()
        result = subset.nlargest(limit, "margin")
        return result.to_dict("records")

    def top_scoring_teams(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return teams ranked by total goals scored."""
        df = self.loader.matches
        mask = pd.Series([True] * len(df), index=df.index)

        if competition:
            comp = _resolve_competition(competition)
            mask &= _comp_mask(df["competition"], comp)
        if season is not None:
            mask &= df["season"] == int(season)

        subset = df[mask]

        # Sum goals as home team + goals as away team
        home_goals = subset.groupby("home_team")["home_goal"].sum()
        away_goals = subset.groupby("away_team")["away_goal"].sum()
        total = home_goals.add(away_goals, fill_value=0).sort_values(ascending=False)

        results = []
        for team_norm, goals in total.head(limit).items():
            # Pick a display name
            raw = subset[subset["home_team"] == team_norm]["home_team_raw"]
            if raw.empty:
                raw = subset[subset["away_team"] == team_norm]["away_team_raw"]
            display = raw.mode().iloc[0] if not raw.empty else team_norm
            results.append({"team": display, "goals_scored": int(goals)})

        return results
