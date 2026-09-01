"""
Query engine for the Brazilian Soccer MCP server.

Context block
=============
Purpose: Provide a pure-Python query API over the normalized data loaded by
``DataLoader``. Every function returns plain dicts/lists (JSON-serializable)
so they can be served directly by the MCP tool layer without further
adaptation.

Capability areas (mirroring TASK.md)
------------------------------------
1. Match queries     - ``find_matches``, ``head_to_head``
2. Team queries      - ``team_stats``, ``compare_teams``
3. Player queries    - ``find_players``, ``top_players_for_club``
4. Competition       - ``standings``, ``competition_info``
5. Statistical       - ``average_goals``, ``biggest_wins``, ``best_away_record``

All public methods accept human-friendly team names and normalize them
internally via ``normalize_team_name`` so that "Palmeiras-SP", "Palmeiras"
and "palmeiras" resolve to the same entity.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from .data_loader import DataLoader, Match, Player, normalize_team_name, display_team_name, _bare_key


def _team_keys(loader: DataLoader, name: str) -> list[str]:
    """Resolve a user-supplied team name to canonical keys via the loader's resolver."""
    if not name:
        return []
    return loader.resolver.resolve_query_keys(name)


def _match_in_competitions(m: Match, competitions: list[str] | None) -> bool:
    if not competitions:
        return True
    comps = [c.lower() for c in competitions]
    return m.competition.lower() in comps


def _season_match(m: Match, season: str | None) -> bool:
    if not season:
        return True
    return str(m.season) == str(season)


def _date_in_range(m: Match, date_from: str | None, date_to: str | None) -> bool:
    if not m.date:
        # If we have no date and a range was requested, exclude the match.
        return not (date_from or date_to)
    if date_from and m.date < date_from:
        return False
    if date_to and m.date > date_to:
        return False
    return True


class SoccerQueryEngine:
    """High-level query API over loaded data."""

    def __init__(self, loader: DataLoader | None = None):
        self.loader = loader or DataLoader()
        if not self.loader._loaded:
            self.loader.load()

    # ------------------------------------------------------------------ #
    # 1. MATCH QUERIES
    # ------------------------------------------------------------------ #

    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | list[str] | None = None,
        season: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Find matches by team, opponent, competition, season and/or date range.

        ``team`` may be a single team name; when ``opponent`` is also given
        only matches between the two teams are returned (in either venue).
        ``competition`` may be a single name or a list of names.
        """
        competitions = [competition] if isinstance(competition, str) else competition
        team_keys = _team_keys(self.loader, team) if team else []
        opp_keys = _team_keys(self.loader, opponent) if opponent else []

        candidate: Iterable[Match]
        if team_keys:
            candidate = (m for k in team_keys for m in self.loader.matches_for_team(k))
        elif opp_keys:
            candidate = (m for k in opp_keys for m in self.loader.matches_for_team(k))
        else:
            candidate = self.loader.matches

        seen_ids: set[int] = set()
        out: list[dict] = []
        for m in candidate:
            if id(m) in seen_ids:
                continue
            seen_ids.add(id(m))
            if not _match_in_competitions(m, competitions):
                continue
            if not _season_match(m, season):
                continue
            if not _date_in_range(m, date_from, date_to):
                continue
            if team_keys and m.home_team_key not in team_keys and m.away_team_key not in team_keys:
                continue
            if opp_keys and m.home_team_key not in opp_keys and m.away_team_key not in opp_keys:
                continue
            # If both team & opponent given, ensure they are the two participants.
            if team_keys and opp_keys:
                participants = {m.home_team_key, m.away_team_key}
                if not (participants & set(team_keys)) or not (participants & set(opp_keys)):
                    continue
                if len(participants & set(team_keys)) == 0 or len(participants & set(opp_keys)) == 0:
                    continue
            out.append(m.to_dict())
        out.sort(key=lambda x: (x.get("date") or "", x.get("competition")))
        if limit is not None:
            out = out[:limit]
        return out

    def head_to_head(self, team_a: str, team_b: str, competition: str | list[str] | None = None) -> dict:
        """Return head-to-head record between two teams."""
        matches = self.find_matches(team=team_a, opponent=team_b, competition=competition)
        a_keys = set(_team_keys(self.loader, team_a))
        b_keys = set(_team_keys(self.loader, team_b))
        a_wins = b_wins = draws = 0
        a_goals = b_goals = 0
        for m in matches:
            hg, ag = m["home_goal"], m["away_goal"]
            home_key = _bare_key(m["home_team"]) if m["home_team"] else ""
            # Resolve stored display name back to a key set for comparison.
            home_keys = set(_team_keys(self.loader, m["home_team"]))
            away_keys = set(_team_keys(self.loader, m["away_team"]))
            home_is_a = bool(home_keys & a_keys)
            away_is_a = bool(away_keys & a_keys)
            # Determine which side is team A (prefer home, else away).
            if home_is_a:
                a_side, b_side = hg, ag
            elif away_is_a:
                a_side, b_side = ag, hg
            else:
                continue
            if a_side > b_side:
                a_wins += 1
            elif a_side < b_side:
                b_wins += 1
            else:
                draws += 1
            a_goals += a_side
            b_goals += b_side
        return {
            "team_a": display_team_name(team_a),
            "team_b": display_team_name(team_b),
            "matches": len(matches),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
            "match_list": matches,
        }

    # ------------------------------------------------------------------ #
    # 2. TEAM QUERIES
    # ------------------------------------------------------------------ #

    def team_stats(
        self,
        team: str,
        season: str | None = None,
        competition: str | list[str] | None = None,
        venue: str | None = None,  # "home" | "away" | None (both)
    ) -> dict:
        """Return win/draw/loss and goal statistics for a team."""
        competitions = [competition] if isinstance(competition, str) else competition
        team_keys = set(_team_keys(self.loader, team))
        matches = [
            m for k in team_keys for m in self.loader.matches_for_team(k)
            if _season_match(m, season)
            and _match_in_competitions(m, competitions)
        ]
        # De-duplicate matches that may appear under multiple keys.
        seen: set[int] = set()
        dedup: list[Match] = []
        for m in matches:
            if id(m) not in seen:
                seen.add(id(m))
                dedup.append(m)
        matches = dedup
        wins = draws = losses = 0
        goals_for = goals_against = 0
        home_w = home_d = home_l = 0
        away_w = away_d = away_l = 0
        for m in matches:
            is_home = m.home_team_key in team_keys
            if venue and venue == "home" and not is_home:
                continue
            if venue and venue == "away" and is_home:
                continue
            hg, ag = m.home_goal, m.away_goal
            gf = hg if is_home else ag
            ga = ag if is_home else hg
            goals_for += gf
            goals_against += ga
            if gf > ga:
                wins += 1
                if is_home:
                    home_w += 1
                else:
                    away_w += 1
            elif gf < ga:
                losses += 1
                if is_home:
                    home_l += 1
                else:
                    away_l += 1
            else:
                draws += 1
                if is_home:
                    home_d += 1
                else:
                    away_d += 1
        total = wins + draws + losses
        return {
            "team": display_team_name(team),
            "season": season or "all",
            "competition": competition or "all",
            "venue": venue or "all",
            "matches": total,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "win_rate": round(wins / total, 4) if total else 0.0,
            "home": {"wins": home_w, "draws": home_d, "losses": home_l},
            "away": {"wins": away_w, "draws": away_d, "losses": away_l},
        }

    def compare_teams(self, team_a: str, team_b: str, season: str | None = None) -> dict:
        """Compare two teams' stats and their head-to-head record."""
        return {
            "team_a_stats": self.team_stats(team_a, season=season),
            "team_b_stats": self.team_stats(team_b, season=season),
            "head_to_head": self.head_to_head(team_a, team_b),
        }

    # ------------------------------------------------------------------ #
    # 3. PLAYER QUERIES
    # ------------------------------------------------------------------ #

    def find_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int | None = 50,
    ) -> list[dict]:
        """Search the FIFA player database by name / nationality / club / position."""
        name_k = name.lower() if name else None
        nat_k = self._norm_nationality(nationality) if nationality else None
        club_k = _bare_key(club) if club else None
        pos_k = position.upper() if position else None
        out: list[dict] = []
        for p in self.loader.players:
            if name_k and name_k not in p.name.lower():
                continue
            if nat_k and self._norm_nationality(p.nationality) != nat_k:
                continue
            if club_k and club_k not in p.club_key:
                continue
            if pos_k and p.position.upper() != pos_k:
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            out.append(p.to_dict())
        out.sort(key=lambda x: x.get("overall") or 0, reverse=True)
        if limit is not None:
            out = out[:limit]
        return out

    def top_players_for_club(self, club: str, limit: int = 10) -> list[dict]:
        """Return the highest-rated players at a given club."""
        club_k = _bare_key(club)
        players = list(self.loader.players_for_club(club_k))
        players.sort(key=lambda p: p.overall or 0, reverse=True)
        return [p.to_dict() for p in players[:limit]]

    def brazilian_players(self, limit: int | None = 50, min_overall: int | None = None) -> list[dict]:
        """Convenience wrapper: Brazilian players sorted by overall rating."""
        return self.find_players(nationality="Brazil", limit=limit, min_overall=min_overall)

    # ------------------------------------------------------------------ #
    # 4. COMPETITION QUERIES
    # ------------------------------------------------------------------ #

    def standings(self, competition: str, season: str) -> list[dict]:
        """Calculate standings for a competition/season from match results.

        Uses 3 points for a win, 1 for a draw. Teams are sorted by points,
        then goal difference, then goals for.
        """
        comp_lower = competition.lower()
        rows = defaultdict(lambda: {
            "team": "", "team_key": "", "played": 0, "wins": 0, "draws": 0,
            "losses": 0, "goals_for": 0, "goals_against": 0, "points": 0,
        })
        for m in self.loader.matches:
            if m.competition.lower() != comp_lower:
                continue
            if str(m.season) != str(season):
                continue
            for key, disp, gf, ga in (
                (m.home_team_key, m.home_team, m.home_goal, m.away_goal),
                (m.away_team_key, m.away_team, m.away_goal, m.home_goal),
            ):
                if not key:
                    continue
                r = rows[key]
                r["team"] = disp
                r["team_key"] = key
                r["played"] += 1
                r["goals_for"] += gf
                r["goals_against"] += ga
                if gf > ga:
                    r["wins"] += 1
                    r["points"] += 3
                elif gf < ga:
                    r["losses"] += 1
                else:
                    r["draws"] += 1
                    r["points"] += 1
        table = list(rows.values())
        for r in table:
            r["goal_difference"] = r["goals_for"] - r["goals_against"]
        table.sort(
            key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]),
            reverse=True,
        )
        for i, r in enumerate(table, 1):
            r["position"] = i
        return table

    def competition_info(self, competition: str | None = None) -> dict:
        """Return metadata (seasons, match count, teams) for competitions."""
        if competition:
            comp_lower = competition.lower()
            matches = [m for m in self.loader.matches if m.competition.lower() == comp_lower]
            seasons = sorted({m.season for m in matches if m.season})
            teams = sorted({m.home_team for m in matches if m.home_team} |
                           {m.away_team for m in matches if m.away_team})
            return {
                "competition": competition,
                "seasons": seasons,
                "match_count": len(matches),
                "teams": teams,
            }
        # summary of all competitions
        info: dict[str, dict] = {}
        for m in self.loader.matches:
            c = m.competition
            d = info.setdefault(c, {"matches": 0, "seasons": set(), "teams": set()})
            d["matches"] += 1
            if m.season:
                d["seasons"].add(m.season)
            if m.home_team:
                d["teams"].add(m.home_team)
            if m.away_team:
                d["teams"].add(m.away_team)
        return {
            k: {
                "matches": v["matches"],
                "seasons": sorted(v["seasons"]),
                "team_count": len(v["teams"]),
            }
            for k, v in sorted(info.items())
        }

    def champion(self, competition: str, season: str) -> dict | None:
        """Return the champion (top of standings) for a competition/season."""
        table = self.standings(competition, season)
        if not table:
            return None
        top = table[0]
        return {
            "competition": competition,
            "season": season,
            "champion": top["team"],
            "points": top["points"],
            "record": f"{top['wins']}W, {top['draws']}D, {top['losses']}L",
        }

    def relegated_teams(self, competition: str, season: str, n: int = 4) -> list[dict]:
        """Return the bottom *n* teams in the standings (relegation zone)."""
        table = self.standings(competition, season)
        return table[-n:] if table else []

    # ------------------------------------------------------------------ #
    # 5. STATISTICAL ANALYSIS
    # ------------------------------------------------------------------ #

    def average_goals(self, competition: str | list[str] | None = None, season: str | None = None) -> dict:
        """Average goals per match plus home-win/draw/away-win rates."""
        competitions = [competition] if isinstance(competition, str) else competition
        matches = [
            m for m in self.loader.matches
            if _match_in_competitions(m, competitions) and _season_match(m, season)
        ]
        if not matches:
            return {"matches": 0, "avg_goals": 0.0, "home_win_rate": 0.0,
                    "draw_rate": 0.0, "away_win_rate": 0.0}
        total_goals = sum(m.home_goal + m.away_goal for m in matches)
        home_wins = sum(1 for m in matches if m.home_goal > m.away_goal)
        draws = sum(1 for m in matches if m.home_goal == m.away_goal)
        away_wins = sum(1 for m in matches if m.away_goal > m.home_goal)
        n = len(matches)
        return {
            "matches": n,
            "total_goals": total_goals,
            "avg_goals": round(total_goals / n, 3),
            "home_win_rate": round(home_wins / n, 4),
            "draw_rate": round(draws / n, 4),
            "away_win_rate": round(away_wins / n, 4),
        }

    def biggest_wins(self, competition: str | list[str] | None = None, season: str | None = None, limit: int = 10) -> list[dict]:
        """Return the largest goal-difference victories."""
        competitions = [competition] if isinstance(competition, str) else competition
        matches = [
            m for m in self.loader.matches
            if _match_in_competitions(m, competitions) and _season_match(m, season)
        ]
        decorated = []
        for m in matches:
            diff = abs(m.home_goal - m.away_goal)
            decorated.append((diff, m))
        decorated.sort(key=lambda x: x[0], reverse=True)
        out = []
        for diff, m in decorated[:limit]:
            d = m.to_dict()
            d["goal_difference"] = diff
            out.append(d)
        return out

    def best_away_record(self, competition: str | list[str] | None = None, season: str | None = None, limit: int = 10) -> list[dict]:
        """Rank teams by away win rate (minimum 5 away games)."""
        competitions = [competition] if isinstance(competition, str) else competition
        stats: dict[str, dict] = defaultdict(lambda: {
            "team": "", "team_key": "", "played": 0, "wins": 0, "draws": 0,
            "losses": 0, "goals_for": 0, "goals_against": 0,
        })
        for m in self.loader.matches:
            if not _match_in_competitions(m, competitions) or not _season_match(m, season):
                continue
            key = m.away_team_key
            if not key:
                continue
            r = stats[key]
            r["team"] = m.away_team
            r["team_key"] = key
            r["played"] += 1
            r["goals_for"] += m.away_goal
            r["goals_against"] += m.home_goal
            if m.away_goal > m.home_goal:
                r["wins"] += 1
            elif m.away_goal < m.home_goal:
                r["losses"] += 1
            else:
                r["draws"] += 1
        rows = []
        for r in stats.values():
            if r["played"] < 5:
                continue
            r["win_rate"] = round(r["wins"] / r["played"], 4)
            r["points"] = r["wins"] * 3 + r["draws"]
            rows.append(r)
        rows.sort(key=lambda x: (x["win_rate"], x["points"]), reverse=True)
        for i, r in enumerate(rows[:limit], 1):
            r["position"] = i
        return rows[:limit]

    def top_scoring_teams(self, competition: str | list[str] | None = None, season: str | None = None, limit: int = 10) -> list[dict]:
        """Rank teams by total goals scored in the filtered match set."""
        competitions = [competition] if isinstance(competition, str) else competition
        stats: dict[str, dict] = defaultdict(lambda: {"team": "", "goals": 0, "played": 0})
        for m in self.loader.matches:
            if not _match_in_competitions(m, competitions) or not _season_match(m, season):
                continue
            for key, disp, gf in (
                (m.home_team_key, m.home_team, m.home_goal),
                (m.away_team_key, m.away_team, m.away_goal),
            ):
                if not key:
                    continue
                stats[key]["team"] = disp
                stats[key]["goals"] += gf
                stats[key]["played"] += 1
        rows = list(stats.values())
        rows.sort(key=lambda x: x["goals"], reverse=True)
        return rows[:limit]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _norm_nationality(value: str) -> str:
        from .data_loader import _strip_accents
        return _strip_accents(value).lower().strip()
