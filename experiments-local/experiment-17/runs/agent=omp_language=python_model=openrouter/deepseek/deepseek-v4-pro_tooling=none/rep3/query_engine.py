"""
Brazilian Soccer MCP Server - Query Engine
============================================
Provides query functions for match, team, player, competition, and
statistical queries against the loaded datasets.

All functions return formatted text output suitable for MCP tool responses.
"""

from datetime import datetime
from typing import Optional

import pandas as pd

from data_loader import get_matches, get_players, normalize_team


class QueryEngine:
    """Stateless query engine over loaded match and player data."""

    def __init__(self):
        self._matches = get_matches()
        self._players = get_players()

    # ------------------------------------------------------------------
    # 1. Match Queries
    # ------------------------------------------------------------------

    def find_matches(
        self,
        team: Optional[str] = None,
        team2: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """
        Find matches by criteria: team, team2 (head-to-head), competition,
        season, date range.

        Args:
            team: Team name (matches either home or away)
            team2: Second team name for head-to-head queries
            competition: Competition name filter
            season: Season year filter
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            limit: Maximum results (default 50)
        """
        df = self._matches.copy()
        mask = pd.Series(True, index=df.index)

        if team:
            team_norm = normalize_team(team)
            mask &= (df["home_team_norm"] == team_norm) | (df["away_team_norm"] == team_norm)

        if team2:
            team2_norm = normalize_team(team2)
            if team:
                # Head-to-head: both teams involved
                team_norm = normalize_team(team)
                mask &= (
                    ((df["home_team_norm"] == team_norm) & (df["away_team_norm"] == team2_norm))
                    | ((df["home_team_norm"] == team2_norm) & (df["away_team_norm"] == team_norm))
                )

        if competition:
            comp_lower = competition.lower()
            mask &= df["competition"].str.lower().str.contains(comp_lower, na=False)

        if season is not None:
            mask &= df["season"] == season

        if date_from:
            dt_from = pd.Timestamp(date_from)
            mask &= df["date"] >= dt_from

        if date_to:
            dt_to = pd.Timestamp(date_to)
            mask &= df["date"] <= dt_to

        result = df[mask].sort_values("date", ascending=False).head(limit)

        if result.empty:
            return "No matches found matching the criteria."

        lines = [f"Found {len(result)} matches (showing up to {limit}):"]
        for _, row in result.iterrows():
            d = row["date"].strftime("%Y-%m-%d") if row["date"] is not None else "?"
            comp = row["competition"]
            stage = f" ({row['stage']})" if row.get("stage") and str(row["stage"]).strip() else ""
            rd = f" Round {int(row['round'])}" if row.get("round") and int(row["round"]) > 0 else ""
            lines.append(
                f"  {d}: {row['home_team']} {int(row['home_goal'])}-{int(row['away_goal'])} "
                f"{row['away_team']} ({comp}{stage}{rd}, {int(row['season'])})"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 2. Team Queries
    # ------------------------------------------------------------------

    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> str:
        """
        Get team statistics: wins, losses, draws, goals for/against, home/away
        records.

        Args:
            team: Team name
            season: Optional season filter
            competition: Optional competition filter
        """
        df = self._matches.copy()
        team_norm = normalize_team(team)

        # Filter by team involvement
        mask = (df["home_team_norm"] == team_norm) | (df["away_team_norm"] == team_norm)
        if season is not None:
            mask &= df["season"] == season
        if competition:
            mask &= df["competition"].str.lower().str.contains(competition.lower(), na=False)

        result = df[mask]
        if result.empty:
            return f"No matches found for team '{team}'."

        total = len(result)
        home_matches = result[result["home_team_norm"] == team_norm]
        away_matches = result[result["away_team_norm"] == team_norm]

        # Overall record
        wins = losses = draws = 0
        goals_for = goals_against = 0
        home_wins = home_losses = home_draws = 0
        home_gf = home_ga = 0
        away_wins = away_losses = away_draws = 0
        away_gf = away_ga = 0

        for _, row in home_matches.iterrows():
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            goals_for += hg
            goals_against += ag
            home_gf += hg
            home_ga += ag
            if hg > ag:
                wins += 1
                home_wins += 1
            elif hg < ag:
                losses += 1
                home_losses += 1
            else:
                draws += 1
                home_draws += 1

        for _, row in away_matches.iterrows():
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            goals_for += ag
            goals_against += hg
            away_gf += ag
            away_ga += hg
            if ag > hg:
                wins += 1
                away_wins += 1
            elif ag < hg:
                losses += 1
                away_losses += 1
            else:
                draws += 1
                away_draws += 1

        seasons = sorted(result["season"].unique())
        win_pct = (wins / total * 100) if total > 0 else 0

        lines = [
            f"Statistics for {team}:",
            f"  Seasons: {', '.join(str(s) for s in seasons)}",
            f"  Total matches: {total}",
            f"  Wins: {wins}, Draws: {draws}, Losses: {losses}",
            f"  Goals For: {goals_for}, Goals Against: {goals_against}",
            f"  Win rate: {win_pct:.1f}%",
            f"",
            f"  Home record ({len(home_matches)} matches):",
            f"    Wins: {home_wins}, Draws: {home_draws}, Losses: {home_losses}",
            f"    Goals For: {home_gf}, Goals Against: {home_ga}",
            f"",
            f"  Away record ({len(away_matches)} matches):",
            f"    Wins: {away_wins}, Draws: {away_draws}, Losses: {away_losses}",
            f"    Goals For: {away_gf}, Goals Against: {away_ga}",
        ]

        return "\n".join(lines)

    def head_to_head(self, team1: str, team2: str) -> str:
        """
        Compare two teams head-to-head.

        Args:
            team1: First team name
            team2: Second team name
        """
        df = self._matches.copy()
        t1 = normalize_team(team1)
        t2 = normalize_team(team2)

        mask = (
            ((df["home_team_norm"] == t1) & (df["away_team_norm"] == t2))
            | ((df["home_team_norm"] == t2) & (df["away_team_norm"] == t1))
        )
        result = df[mask].sort_values("date", ascending=False)

        if result.empty:
            return f"No head-to-head matches found between '{team1}' and '{team2}'."

        t1_wins = t2_wins = draws = 0
        t1_goals = t2_goals = 0

        for _, row in result.iterrows():
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            if row["home_team_norm"] == t1:
                t1_goals += hg
                t2_goals += ag
                if hg > ag:
                    t1_wins += 1
                elif hg < ag:
                    t2_wins += 1
                else:
                    draws += 1
            else:
                t1_goals += ag
                t2_goals += hg
                if ag > hg:
                    t1_wins += 1
                elif ag < hg:
                    t2_wins += 1
                else:
                    draws += 1

        lines = [
            f"Head-to-head: {team1} vs {team2}",
            f"  Total matches: {len(result)}",
            f"  {team1} wins: {t1_wins}",
            f"  {team2} wins: {t2_wins}",
            f"  Draws: {draws}",
            f"  Goals: {team1} {t1_goals} - {t2_goals} {team2}",
            f"",
            "Recent matches:",
        ]
        for _, row in result.head(10).iterrows():
            d = row["date"].strftime("%Y-%m-%d") if row["date"] is not None else "?"
            lines.append(
                f"  {d}: {row['home_team']} {int(row['home_goal'])}-{int(row['away_goal'])} "
                f"{row['away_team']} ({row['competition']}, {int(row['season'])})"
            )

        return "\n".join(lines)

    def best_home_record(self, season: Optional[int] = None,
                          competition: str = "Brasileirao") -> str:
        """Find the team(s) with the best home record."""
        df = self._matches.copy()
        mask = df["competition"].str.lower().str.contains(competition.lower(), na=False)
        if season is not None:
            mask &= df["season"] == season
        df = df[mask]

        if df.empty:
            return "No data available."

        teams: dict[str, dict] = {}
        for _, row in df.iterrows():
            home = row["home_team_norm"]
            if home not in teams:
                teams[home] = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            teams[home]["matches"] += 1
            teams[home]["gf"] += hg
            teams[home]["ga"] += ag
            if hg > ag:
                teams[home]["wins"] += 1
            elif hg < ag:
                teams[home]["losses"] += 1
            else:
                teams[home]["draws"] += 1

        ranked = sorted(
            teams.items(),
            key=lambda x: (x[1]["wins"] / max(x[1]["matches"], 1), x[1]["gf"]),
            reverse=True,
        )

        lines = ["Best home records (by win rate):"]
        for name, stats in ranked[:10]:
            pct = stats["wins"] / max(stats["matches"], 1) * 100
            lines.append(
                f"  {name}: {stats['wins']}W {stats['draws']}D {stats['losses']}L "
                f"({pct:.1f}%), GF:{stats['gf']} GA:{stats['ga']} "
                f"({stats['matches']} matches)"
            )
        return "\n".join(lines)

    def best_away_record(self, season: Optional[int] = None,
                          competition: str = "Brasileirao") -> str:
        """Find the team(s) with the best away record."""
        df = self._matches.copy()
        mask = df["competition"].str.lower().str.contains(competition.lower(), na=False)
        if season is not None:
            mask &= df["season"] == season
        df = df[mask]

        if df.empty:
            return "No data available."

        teams: dict[str, dict] = {}
        for _, row in df.iterrows():
            away = row["away_team_norm"]
            if away not in teams:
                teams[away] = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            teams[away]["matches"] += 1
            teams[away]["gf"] += ag
            teams[away]["ga"] += hg
            if ag > hg:
                teams[away]["wins"] += 1
            elif ag < hg:
                teams[away]["losses"] += 1
            else:
                teams[away]["draws"] += 1

        ranked = sorted(
            teams.items(),
            key=lambda x: (x[1]["wins"] / max(x[1]["matches"], 1), x[1]["gf"]),
            reverse=True,
        )

        lines = ["Best away records (by win rate):"]
        for name, stats in ranked[:10]:
            pct = stats["wins"] / max(stats["matches"], 1) * 100
            lines.append(
                f"  {name}: {stats['wins']}W {stats['draws']}D {stats['losses']}L "
                f"({pct:.1f}%), GF:{stats['gf']} GA:{stats['ga']} "
                f"({stats['matches']} matches)"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 3. Player Queries
    # ------------------------------------------------------------------

    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """
        Find players by name, nationality, club, position, or minimum rating.

        Args:
            name: Player name substring match
            nationality: Nationality filter (e.g., "Brazil")
            club: Club name filter
            position: Position filter (e.g., "ST", "LW", "GK")
            min_overall: Minimum FIFA overall rating
            limit: Maximum results
        """
        df = self._players.copy()
        mask = pd.Series(True, index=df.index)

        if name:
            mask &= df["Name"].str.lower().str.contains(name.lower(), na=False)
        if nationality:
            mask &= df["Nationality"].str.lower().str.contains(nationality.lower(), na=False)
        if club:
            club_norm = normalize_team(club)
            mask &= (df["club_norm"] == club_norm) | df["Club"].str.lower().str.contains(club.lower(), na=False)
        if position:
            mask &= df["Position"].str.lower().str.contains(position.lower(), na=False)
        if min_overall is not None:
            mask &= df["Overall"] >= min_overall

        result = df[mask].sort_values("Overall", ascending=False).head(limit)

        if result.empty:
            return "No players found matching the criteria."

        lines = [f"Found {len(result)} players:"]
        for _, row in result.iterrows():
            lines.append(
                f"  {row['Name']} | Overall: {int(row['Overall'])} | "
                f"Position: {row['Position']} | Age: {int(row['Age'])} | "
                f"Nationality: {row['Nationality']} | Club: {row['Club']}"
            )

        return "\n".join(lines)

    def top_players_by_club(self, club: str, limit: int = 20) -> str:
        """Get highest-rated players at a specific club."""
        return self.find_players(club=club, limit=limit)

    def brazilian_players_summary(self) -> str:
        """Summary of Brazilian players in the database."""
        df = self._players[self._players["Nationality"].str.lower() == "brazil"]

        if df.empty:
            return "No Brazilian players found."

        total = len(df)
        avg_overall = df["Overall"].mean()

        lines = [
            f"Brazilian players in database: {total}",
            f"Average overall rating: {avg_overall:.1f}",
            f"",
            "Top 10 Brazilian players:",
        ]
        top = df.sort_values("Overall", ascending=False).head(10)
        for i, (_, row) in enumerate(top.iterrows(), 1):
            lines.append(
                f"  {i}. {row['Name']} - Overall: {int(row['Overall'])}, "
                f"Position: {row['Position']}, Club: {row['Club']}"
            )

        lines.append("")
        lines.append("Brazilian players by club (top clubs):")
        club_counts = df.groupby("Club").size().sort_values(ascending=False).head(10)
        avg_by_club = df.groupby("Club")["Overall"].mean()
        for club_name, count in club_counts.items():
            avg = avg_by_club.get(club_name, 0)
            lines.append(f"  {club_name}: {count} players (avg rating: {avg:.0f})")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 4. Competition Queries
    # ------------------------------------------------------------------

    def competition_standings(self, competition: str = "Brasileirao",
                               season: Optional[int] = None) -> str:
        """
        Calculate competition standings from match results.

        Args:
            competition: Competition name
            season: Season year
        """
        df = self._matches.copy()
        mask = df["competition"].str.lower().str.contains(competition.lower(), na=False)
        if season is not None:
            mask &= df["season"] == season
        df = df[mask]

        if df.empty:
            return f"No data found for {competition}" + (f" season {season}" if season else "")

        # Calculate standings
        teams: dict[str, dict] = {}
        for _, row in df.iterrows():
            home = row["home_team_norm"]
            away = row["away_team_norm"]
            hg, ag = int(row["home_goal"]), int(row["away_goal"])

            for team in (home, away):
                if team not in teams:
                    teams[team] = {"pts": 0, "gp": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0}

            # Home team
            teams[home]["gp"] += 1
            teams[home]["gf"] += hg
            teams[home]["ga"] += ag
            if hg > ag:
                teams[home]["w"] += 1
                teams[home]["pts"] += 3
            elif hg < ag:
                teams[home]["l"] += 1
            else:
                teams[home]["d"] += 1
                teams[home]["pts"] += 1

            # Away team
            teams[away]["gp"] += 1
            teams[away]["gf"] += ag
            teams[away]["ga"] += hg
            if ag > hg:
                teams[away]["w"] += 1
                teams[away]["pts"] += 3
            elif ag < hg:
                teams[away]["l"] += 1
            else:
                teams[away]["d"] += 1
                teams[away]["pts"] += 1

        ranked = sorted(
            teams.items(),
            key=lambda x: (x[1]["pts"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
            reverse=True,
        )

        season_str = f" {season}" if season else ""
        lines = [f"{competition}{season_str} Standings:"]
        for i, (name, stats) in enumerate(ranked[:20], 1):
            gd = stats["gf"] - stats["ga"]
            lines.append(
                f"  {i:2d}. {name} - {stats['pts']} pts "
                f"({stats['w']}W, {stats['d']}D, {stats['l']}L) "
                f"GF:{stats['gf']} GA:{stats['ga']} GD:{gd:+d}"
            )

        return "\n".join(lines)

    def competitions_for_team(self, team: str) -> str:
        """List all competitions a team has played in."""
        df = self._matches.copy()
        team_norm = normalize_team(team)
        mask = (df["home_team_norm"] == team_norm) | (df["away_team_norm"] == team_norm)
        result = df[mask]

        if result.empty:
            return f"No competitions found for '{team}'."

        comps = result.groupby("competition").agg(
            matches=("competition", "count"),
            seasons=("season", "nunique"),
        ).sort_values("matches", ascending=False)

        lines = [f"Competitions for {team}:"]
        for comp_name, row in comps.iterrows():
            lines.append(f"  {comp_name}: {int(row['matches'])} matches across {int(row['seasons'])} seasons")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 5. Statistical Analysis
    # ------------------------------------------------------------------

    def average_goals(self, competition: Optional[str] = None,
                       season: Optional[int] = None) -> str:
        """Calculate average goals per match."""
        df = self._matches.copy()
        if competition:
            df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]
        if season is not None:
            df = df[df["season"] == season]

        if df.empty:
            return "No data available."

        total_goals = df["home_goal"].sum() + df["away_goal"].sum()
        total_matches = len(df)
        avg = total_goals / total_matches if total_matches > 0 else 0

        home_wins = (df["home_goal"] > df["away_goal"]).sum()
        away_wins = (df["home_goal"] < df["away_goal"]).sum()
        draws = (df["home_goal"] == df["away_goal"]).sum()

        lines = [
            f"Statistical Summary ({total_matches} matches):",
            f"  Average goals per match: {avg:.2f}",
            f"  Total goals: {int(total_goals)}",
            f"  Home wins: {home_wins} ({home_wins/total_matches*100:.1f}%)",
            f"  Away wins: {away_wins} ({away_wins/total_matches*100:.1f}%)",
            f"  Draws: {draws} ({draws/total_matches*100:.1f}%)",
        ]
        return "\n".join(lines)

    def biggest_wins(self, competition: Optional[str] = None, limit: int = 10) -> str:
        """Find the biggest wins (by goal difference) in the dataset."""
        df = self._matches.copy()
        if competition:
            df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

        df["goal_diff"] = abs(df["home_goal"] - df["away_goal"])
        result = df.sort_values(["goal_diff", "home_goal", "away_goal"], ascending=[False, False, False]).head(limit)

        if result.empty:
            return "No data available."

        lines = ["Biggest victories:"]
        for i, (_, row) in enumerate(result.iterrows(), 1):
            d = row["date"].strftime("%Y-%m-%d") if row["date"] is not None else "?"
            lines.append(
                f"  {i}. {d}: {row['home_team']} {int(row['home_goal'])}-{int(row['away_goal'])} "
                f"{row['away_team']} ({row['competition']}, {int(row['season'])})"
            )

        return "\n".join(lines)

    def season_comparison(self, season1: int, season2: int,
                           competition: str = "Brasileirao") -> str:
        """Compare statistics between two seasons."""
        df = self._matches.copy()
        df = df[df["competition"].str.lower().str.contains(competition.lower(), na=False)]

        s1 = df[df["season"] == season1]
        s2 = df[df["season"] == season2]

        def stats_for(s: pd.DataFrame) -> dict:
            if s.empty:
                return {"matches": 0, "goals": 0, "avg": 0, "home_wins": 0, "draws": 0, "away_wins": 0}
            goals = int(s["home_goal"].sum() + s["away_goal"].sum())
            n = len(s)
            return {
                "matches": n,
                "goals": goals,
                "avg": goals / n,
                "home_wins": int((s["home_goal"] > s["away_goal"]).sum()),
                "draws": int((s["home_goal"] == s["away_goal"]).sum()),
                "away_wins": int((s["home_goal"] < s["away_goal"]).sum()),
            }

        st1 = stats_for(s1)
        st2 = stats_for(s2)

        lines = [
            f"Season Comparison: {season1} vs {season2} ({competition})",
            f"",
            f"  {season1}:",
            f"    Matches: {st1['matches']}",
            f"    Goals: {st1['goals']} (avg {st1['avg']:.2f}/match)",
            f"    Home wins: {st1['home_wins']}, Draws: {st1['draws']}, Away wins: {st1['away_wins']}",
            f"",
            f"  {season2}:",
            f"    Matches: {st2['matches']}",
            f"    Goals: {st2['goals']} (avg {st2['avg']:.2f}/match)",
            f"    Home wins: {st2['home_wins']}, Draws: {st2['draws']}, Away wins: {st2['away_wins']}",
        ]
        return "\n".join(lines)

    def most_goals_team(self, season: Optional[int] = None,
                         competition: str = "Brasileirao") -> str:
        """Find which team scored the most goals."""
        df = self._matches.copy()
        mask = df["competition"].str.lower().str.contains(competition.lower(), na=False)
        if season is not None:
            mask &= df["season"] == season
        df = df[mask]

        if df.empty:
            return "No data available."

        team_goals: dict[str, int] = {}
        for _, row in df.iterrows():
            home = row["home_team_norm"]
            away = row["away_team_norm"]
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            team_goals[home] = team_goals.get(home, 0) + hg
            team_goals[away] = team_goals.get(away, 0) + ag

        ranked = sorted(team_goals.items(), key=lambda x: x[1], reverse=True)

        lines = ["Teams ranked by goals scored:"]
        for name, goals in ranked[:10]:
            lines.append(f"  {name}: {goals} goals")

        return "\n".join(lines)
