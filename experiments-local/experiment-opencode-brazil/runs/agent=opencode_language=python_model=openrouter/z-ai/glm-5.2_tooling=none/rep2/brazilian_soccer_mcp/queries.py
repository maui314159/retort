# ============================================================================
# Context: Brazilian Soccer MCP Server benchmark.
# Query engine. Stateless, in-memory analytics over the unified Match records
# and the FIFA player DataFrame. Each public method returns plain Python types
# (dicts/lists) so they can be serialized as MCP tool results. Designed to be
# fully testable without any network or LLM dependency.
# ----------------------------------------------------------------------------
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

from .data_loader import DataLoader, Match
from .normalizers import canonical_team_name, normalize_competition, team_key


class QueryEngine:
    """Provide the analytical queries the MCP server exposes as tools."""

    def __init__(self, loader: Optional[DataLoader] = None):
        self.loader = loader or DataLoader()

    # ------------------------------------------------------------------
    # Match queries
    # ------------------------------------------------------------------
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Find matches matching the given filters. Team/opponent match either side."""
        tk = team_key(team) if team else None
        ok = team_key(opponent) if opponent else None
        comp_filter = normalize_competition(competition) if competition else None
        sd = _parse(start_date)
        ed = _parse(end_date)

        results: list[dict] = []
        for m in self.loader.matches:
            if tk:
                if m.home_team_key != tk and m.away_team_key != tk:
                    continue
            if ok:
                if m.away_team_key != ok and m.home_team_key != ok:
                    continue
                # opponent must be on the opposite side of `team`
                if tk:
                    if tk == m.home_team_key and m.away_team_key != ok:
                        continue
                    if tk == m.away_team_key and m.home_team_key != ok:
                        continue
            if comp_filter and m.competition != comp_filter:
                continue
            if season is not None and m.season != season:
                continue
            if sd and (m.date is None or m.date < sd):
                continue
            if ed and (m.date is None or m.date > ed):
                continue
            results.append(self._match_summary(m))
        results.sort(key=lambda r: (r.get("date") or "", r.get("competition")))
        if limit is not None:
            results = results[:limit]
        return results

    def head_to_head(self, team_a: str, team_b: str) -> dict:
        """Head-to-head comparison between two teams across all datasets."""
        ka = team_key(team_a)
        kb = team_key(team_b)
        if not ka or not kb:
            return {"error": "Invalid team names", "team_a": team_a, "team_b": team_b}

        a_wins = b_wins = draws = 0
        a_goals = b_goals = 0
        matches: list[dict] = []
        for m in self.loader.matches:
            if {m.home_team_key, m.away_team_key} != {ka, kb}:
                continue
            # Identify which side is team_a.
            if m.home_team_key == ka:
                a, b = m.home_goals, m.away_goals
            else:
                a, b = m.away_goals, m.home_goals
            a_goals += a
            b_goals += b
            if a > b:
                a_wins += 1
            elif b > a:
                b_wins += 1
            else:
                draws += 1
            matches.append(self._match_summary(m))
        matches.sort(key=lambda r: r.get("date") or "")
        return {
            "team_a": canonical_team_name(team_a),
            "team_b": canonical_team_name(team_b),
            "matches_played": len(matches),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "matches": matches,
        }

    # ------------------------------------------------------------------
    # Team queries
    # ------------------------------------------------------------------
    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,  # "home", "away", or None for both
    ) -> dict:
        """Aggregate win/loss/draw and goals for a team, optionally filtered."""
        tk = team_key(team)
        if not tk:
            return {"error": "Invalid team name", "team": team}
        comp_filter = normalize_competition(competition) if competition else None

        wins = losses = draws = 0
        gf = ga = 0
        played = 0
        for m in self.loader.matches:
            if tk not in (m.home_team_key, m.away_team_key):
                continue
            if season is not None and m.season != season:
                continue
            if comp_filter and m.competition != comp_filter:
                continue
            if venue == "home" and m.home_team_key != tk:
                continue
            if venue == "away" and m.away_team_key != tk:
                continue
            played += 1
            if m.home_team_key == tk:
                ours, theirs = m.home_goals, m.away_goals
            else:
                ours, theirs = m.away_goals, m.home_goals
            gf += ours
            ga += theirs
            if ours > theirs:
                wins += 1
            elif theirs > ours:
                losses += 1
            else:
                draws += 1
        win_rate = (wins / played * 100) if played else 0.0
        return {
            "team": canonical_team_name(team),
            "season": season,
            "competition": competition,
            "venue": venue,
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "win_rate": round(win_rate, 2),
        }

    # ------------------------------------------------------------------
    # Player queries
    # ------------------------------------------------------------------
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Search FIFA player database with flexible filters."""
        df = self.loader.players_df
        if df.empty:
            return []
        mask = df["Name"].notna()
        if name:
            mask &= df["Name"].str.contains(name, case=False, na=False)
        if nationality:
            mask &= df["Nationality"].str.contains(nationality, case=False, na=False)
        if club:
            club_key_val = team_key(club)
            mask &= df["club_key"] == club_key_val
        if position:
            mask &= df["Position"].astype(str).str.upper() == position.upper()
        if min_overall is not None:
            mask &= df["Overall"].astype(float) >= float(min_overall)
        cols = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position"]
        cols = [c for c in cols if c in df.columns]
        subset = df.loc[mask, cols].sort_values("Overall", ascending=False)
        if limit is not None:
            subset = subset.head(limit)
        return subset.fillna("").to_dict(orient="records")

    def top_brazilian_players(self, limit: int = 20) -> list[dict]:
        """Highest-rated Brazilian players in the FIFA dataset."""
        return self.search_players(nationality="Brazil", limit=limit)

    def players_at_club(self, club: str, limit: Optional[int] = None) -> list[dict]:
        """All players whose FIFA Club matches the given team name."""
        return self.search_players(club=club, limit=limit)

    # ------------------------------------------------------------------
    # Competition queries
    # ------------------------------------------------------------------
    def standings(self, competition: str, season: int) -> list[dict]:
        """Calculate standings (points, W/D/L, GF/GA) from match results.

        Only round-robin competitions (Brasileirao) produce meaningful tables,
        but the calculation works for any competition label.
        """
        comp_filter = normalize_competition(competition)
        table: dict[str, dict] = {}
        for m in self.loader.matches:
            if m.competition != comp_filter:
                continue
            if m.season != season:
                continue
            for side, tk, gf_, ga_ in (
                ("home", m.home_team_key, m.home_goals, m.away_goals),
                ("away", m.away_team_key, m.away_goals, m.home_goals),
            ):
                if not tk:
                    continue
                row = table.setdefault(tk, {
                    "team": m.home_team if side == "home" else m.away_team,
                    "played": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0, "points": 0,
                })
                row["played"] += 1
                row["goals_for"] += gf_
                row["goals_against"] += ga_
                if gf_ > ga_:
                    row["wins"] += 1
                    row["points"] += 3
                elif gf_ < ga_:
                    row["losses"] += 1
                else:
                    row["draws"] += 1
                    row["points"] += 1
        rows = list(table.values())
        rows.sort(key=lambda r: (-r["points"], -r["wins"], -(r["goals_for"] - r["goals_against"]), -r["goals_for"], r["team"]))
        for i, r in enumerate(rows, 1):
            r["position"] = i
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        return rows

    def champion(self, competition: str, season: int) -> Optional[dict]:
        """Return the top team in the calculated standings (champion)."""
        table = self.standings(competition, season)
        return table[0] if table else None

    def relegated_teams(self, competition: str, season: int, n: int = 4) -> list[dict]:
        """Return the bottom n teams in the standings (relegation zone)."""
        table = self.standings(competition, season)
        return table[-n:] if table else []

    # ------------------------------------------------------------------
    # Statistical analysis
    # ------------------------------------------------------------------
    def average_goals(self, competition: Optional[str] = None, season: Optional[int] = None) -> dict:
        """Average goals per match, plus home/away win rates."""
        comp_filter = normalize_competition(competition) if competition else None
        total_goals = 0
        match_count = 0
        home_wins = away_wins = draws = 0
        for m in self.loader.matches:
            if comp_filter and m.competition != comp_filter:
                continue
            if season is not None and m.season != season:
                continue
            match_count += 1
            total_goals += m.home_goals + m.away_goals
            if m.home_goals > m.away_goals:
                home_wins += 1
            elif m.away_goals > m.home_goals:
                away_wins += 1
            else:
                draws += 1
        if match_count == 0:
            return {"competition": competition, "season": season, "matches": 0}
        return {
            "competition": competition,
            "season": season,
            "matches": match_count,
            "average_goals_per_match": round(total_goals / match_count, 3),
            "home_win_rate": round(home_wins / match_count * 100, 2),
            "away_win_rate": round(away_wins / match_count * 100, 2),
            "draw_rate": round(draws / match_count * 100, 2),
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Largest goal-margin victories in the dataset."""
        comp_filter = normalize_competition(competition) if competition else None
        rows: list[tuple[int, dict]] = []
        for m in self.loader.matches:
            if comp_filter and m.competition != comp_filter:
                continue
            if season is not None and m.season != season:
                continue
            margin = abs(m.home_goals - m.away_goals)
            if margin == 0:
                continue
            rows.append((margin, self._match_summary(m)))
        rows.sort(key=lambda t: (-t[0], t[1].get("date") or ""))
        return [r for _, r in rows[:limit]]

    def best_home_record(self, season: Optional[int] = None, competition: Optional[str] = None) -> Optional[dict]:
        """Team with the highest home win rate (min 5 matches)."""
        return self._best_record(venue="home", season=season, competition=competition)

    def best_away_record(self, season: Optional[int] = None, competition: Optional[str] = None) -> Optional[dict]:
        """Team with the highest away win rate (min 5 matches)."""
        return self._best_record(venue="away", season=season, competition=competition)

    def _best_record(self, venue: str, season: Optional[int], competition: Optional[str]) -> Optional[dict]:
        comp_filter = normalize_competition(competition) if competition else None
        stats: dict[str, dict] = {}
        for m in self.loader.matches:
            if comp_filter and m.competition != comp_filter:
                continue
            if season is not None and m.season != season:
                continue
            if venue == "home":
                tk = m.home_team_key
                ours, theirs = m.home_goals, m.away_goals
                name = m.home_team
            else:
                tk = m.away_team_key
                ours, theirs = m.away_goals, m.home_goals
                name = m.away_team
            if not tk:
                continue
            row = stats.setdefault(tk, {"team": name, "played": 0, "wins": 0})
            row["played"] += 1
            if ours > theirs:
                row["wins"] += 1
        best = None
        for row in stats.values():
            if row["played"] < 5:
                continue
            rate = row["wins"] / row["played"]
            if best is None or rate > best["win_rate"]:
                best = {
                    "team": row["team"],
                    "played": row["played"],
                    "wins": row["wins"],
                    "win_rate": round(rate * 100, 2),
                    "venue": venue,
                }
        return best

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def list_teams(self, competition: Optional[str] = None) -> list[str]:
        """Return sorted unique canonical team names, optionally per competition."""
        names: set[str] = set()
        comp_filter = normalize_competition(competition) if competition else None
        for m in self.loader.matches:
            if comp_filter and m.competition != comp_filter:
                continue
            if m.home_team:
                names.add(m.home_team)
            if m.away_team:
                names.add(m.away_team)
        return sorted(names)

    def list_competitions(self) -> list[str]:
        """Return the distinct competition labels present in the dataset."""
        return sorted({m.competition for m in self.loader.matches})

    def list_seasons(self, competition: Optional[str] = None) -> list[int]:
        """Return sorted distinct seasons available, optionally per competition."""
        comp_filter = normalize_competition(competition) if competition else None
        seasons: set[int] = set()
        for m in self.loader.matches:
            if comp_filter and m.competition != comp_filter:
                continue
            if m.season is not None:
                seasons.add(m.season)
        return sorted(seasons)

    @staticmethod
    def _match_summary(m: Match) -> dict:
        return {
            "competition": m.competition,
            "season": m.season,
            "date": m.date.date().isoformat() if m.date else None,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "round": m.round,
            "stage": m.stage,
            "stadium": m.stadium,
            "source_file": m.source_file,
        }


def _parse(value: Optional[str]) -> Optional[datetime]:
    from .normalizers import parse_date
    return parse_date(value)
