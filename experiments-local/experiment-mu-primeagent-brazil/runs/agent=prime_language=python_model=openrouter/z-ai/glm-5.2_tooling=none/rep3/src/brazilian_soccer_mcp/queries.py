"""
Context Block
=============

Module: brazilian_soccer_mcp.queries
Purpose: High-level query engine over the ``KnowledgeGraph``
         implementing all spec-required capabilities:

  1. Match queries    - find_matches, head_to_head
  2. Team queries     - team_statistics, team_info, compare_teams,
                        best_home_record, best_away_record
  3. Player queries   - find_players, top_players,
                        players_at_brazilian_clubs
  4. Competition      - competition_standings, competition_seasons,
                        competition_info
  5. Statistical      - biggest_wins, average_goals, home_vs_away

Every public method returns a plain dict / list-of-dicts that is
JSON-serialisable for the MCP transport.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .data_loader import MatchRecord
from .knowledge_graph import KnowledgeGraph
from datetime import datetime
from .normalizer import team_match_key, format_date, parse_date


class SoccerQueries:
    """Query engine over the Brazilian soccer knowledge graph."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    # -- helpers -----------------------------------------------------------
    def _display_name_for_key(self, key: str) -> str:
        node = self.graph.teams.get(key)
        return node.display_name if node else key

    @staticmethod
    def _match_dict(m: MatchRecord) -> dict:
        return {
            "match_id": m.match_id,
            "date": format_date(m.date),
            "home_team": m.home_team,
            "away_team": m.away_team,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "score": f"{m.home_goals}-{m.away_goals}" if m.home_goals is not None else None,
            "competition": m.competition,
            "season": m.season,
            "round": m.round_info,
            "stage": m.stage,
            "source": m.source_file,
        }

    @staticmethod
    def _player_dict(p) -> dict:
        r = p.record
        return {
            "name": r.name, "age": r.age, "nationality": r.nationality,
            "overall": r.overall, "potential": r.potential, "club": r.club,
            "position": r.position, "jersey_number": r.jersey_number,
            "value": r.value, "wage": r.wage,
        }

    # ==================================================================
    # 1. MATCH QUERIES
    # ==================================================================
    def find_matches(
        self, team: Optional[str] = None, opponent: Optional[str] = None,
        competition: Optional[str] = None, season: Optional[int] = None,
        date_from: Optional[str] = None, date_to: Optional[str] = None,
        limit: Optional[int] = 50,
    ) -> dict:
        """Find matches matching the given criteria."""
        team_key = team_match_key(team) if team else None
        opp_key = team_match_key(opponent) if opponent else None
        comp_node = self.graph.get_competition(competition) if competition else None
        comp_name = comp_node.name if comp_node else None
        dt_from = parse_date(date_from) if date_from else None
        dt_to = parse_date(date_to) if date_to else None
        results = []
        for m in self.graph.loader.matches:
            if team_key and m.home_team_key != team_key and m.away_team_key != team_key:
                continue
            if opp_key:
                if m.home_team_key != opp_key and m.away_team_key != opp_key:
                    continue
                if team_key and opp_key == team_key:
                    continue
            if comp_name and m.competition != comp_name:
                continue
            if season is not None and m.season != season:
                continue
            if dt_from and m.date and m.date < dt_from:
                continue
            if dt_to and m.date and m.date > dt_to:
                continue
            results.append(m)
        results.sort(key=lambda m: m.date or datetime.min, reverse=True)
        total = len(results)
        limited = results[:limit] if limit is not None else results
        return {
            "matches": [self._match_dict(m) for m in limited],
            "count": len(limited), "total_found": total,
            "filters": {"team": team, "opponent": opponent,
                        "competition": comp_name, "season": season,
                        "date_from": date_from, "date_to": date_to},
        }

    def head_to_head(self, team1: str, team2: str, competition: Optional[str] = None) -> dict:
        """Compute head-to-head record between two teams."""
        key1, key2 = team_match_key(team1), team_match_key(team2)
        comp_node = self.graph.get_competition(competition) if competition else None
        comp_name = comp_node.name if comp_node else None
        matches, t1w, t2w, dr = [], 0, 0, 0
        t1g, t2g = 0, 0
        for m in self.graph.loader.matches:
            if m.home_team_key not in (key1, key2):
                continue
            if m.away_team_key not in (key1, key2):
                continue
            if m.home_team_key == m.away_team_key:
                continue
            if comp_name and m.competition != comp_name:
                continue
            matches.append(m)
            hg, ag = m.home_goals or 0, m.away_goals or 0
            t1g += hg if m.home_team_key == key1 else ag
            t2g += hg if m.home_team_key == key2 else ag
            if hg > ag:
                t1w += 1 if m.home_team_key == key1 else 0
                t2w += 1 if m.home_team_key == key2 else 0
            elif hg < ag:
                t1w += 1 if m.away_team_key == key1 else 0
                t2w += 1 if m.away_team_key == key2 else 0
            else:
                dr += 1
        matches.sort(key=lambda m: m.date or datetime.min, reverse=True)
        return {
            "team1": self._display_name_for_key(key1),
            "team2": self._display_name_for_key(key2),
            "team1_wins": t1w, "team2_wins": t2w, "draws": dr,
            "total_matches": len(matches),
            "team1_goals": t1g, "team2_goals": t2g,
            "matches": [self._match_dict(m) for m in matches],
        }

    # ==================================================================
    # 2. TEAM QUERIES
    # ==================================================================
    def team_statistics(self, team: str, season: Optional[int] = None,
                        competition: Optional[str] = None, venue: Optional[str] = None) -> dict:
        """Compute W/D/L and goal statistics for a team."""
        key = team_match_key(team)
        comp_node = self.graph.get_competition(competition) if competition else None
        comp_name = comp_node.name if comp_node else None
        w = d = l = gf = ga = n = 0
        for m in self.graph.loader.matches:
            is_home = m.home_team_key == key
            is_away = m.away_team_key == key
            if not (is_home or is_away):
                continue
            if venue == "home" and not is_home:
                continue
            if venue == "away" and not is_away:
                continue
            if season is not None and m.season != season:
                continue
            if comp_name and m.competition != comp_name:
                continue
            hg, ag = m.home_goals or 0, m.away_goals or 0
            _gf, _ga = (hg, ag) if is_home else (ag, hg)
            gf += _gf; ga += _ga; n += 1
            if _gf > _ga: w += 1
            elif _gf < _ga: l += 1
            else: d += 1
        wr = (w / n * 100) if n else 0
        comps = sorted(set(m.competition for m in self.graph.loader.matches
                           if m.home_team_key == key or m.away_team_key == key))
        seasons = sorted(set(m.season for m in self.graph.loader.matches
                              if (m.home_team_key == key or m.away_team_key == key) and m.season))
        return {
            "team": self._display_name_for_key(key), "team_key": key,
            "venue": venue, "season": season, "competition": comp_name,
            "matches": n, "wins": w, "draws": d, "losses": l,
            "goals_for": gf, "goals_against": ga,
            "goal_difference": gf - ga, "win_rate": round(wr, 1),
            "competitions_played": comps, "seasons_played": seasons,
        }

    def team_info(self, team: str) -> dict:
        """Return basic information about a team."""
        key = team_match_key(team)
        node = self.graph.teams.get(key)
        if not node:
            return {"error": f"Team not found: {team}", "team": team}
        cs = defaultdict(lambda: {"matches": 0, "wins": 0, "draws": 0, "losses": 0})
        for m in node.all_matches:
            rec = cs[m.competition]; rec["matches"] += 1
            is_home = m.home_team_key == key
            hg, ag = m.home_goals or 0, m.away_goals or 0
            gf, ga = (hg, ag) if is_home else (ag, hg)
            if gf > ga: rec["wins"] += 1
            elif gf < ga: rec["losses"] += 1
            else: rec["draws"] += 1
        players = self.graph.find_players_by_club(team)
        rated = [p.record.overall for p in players if p.record.overall]
        avg = round(sum(rated) / len(rated), 1) if rated else None
        return {
            "team": node.display_name, "team_key": key,
            "states": sorted(node.states),
            "total_matches": node.match_count,
            "home_matches": len(node.home_matches),
            "away_matches": len(node.away_matches),
            "competitions": dict(sorted(cs.items())),
            "player_count": len(players), "avg_player_rating": avg,
            "top_players": [
                {"name": p.record.name, "overall": p.record.overall, "position": p.record.position}
                for p in sorted(players, key=lambda p: p.record.overall or 0, reverse=True)[:5]
            ] if players else [],
        }

    def compare_teams(self, team1: str, team2: str) -> dict:
        """Compare two teams side by side."""
        return {"team1": self.team_info(team1), "team2": self.team_info(team2),
                "head_to_head": self.head_to_head(team1, team2)}

    def _venue_ranking(self, venue: str, competition: Optional[str], season: Optional[int]) -> dict:
        comp_node = self.graph.get_competition(competition) if competition else None
        comp_name = comp_node.name if comp_node else None
        recs = defaultdict(lambda: {"wins": 0, "draws": 0, "losses": 0, "matches": 0})
        for m in self.graph.loader.matches:
            if comp_name and m.competition != comp_name:
                continue
            if season is not None and m.season != season:
                continue
            hg, ag = m.home_goals or 0, m.away_goals or 0
            if venue == "home":
                tk, won = m.home_team_key, hg > ag
            else:
                tk, won = m.away_team_key, ag > hg
            if not tk:
                continue
            r = recs[tk]; r["matches"] += 1
            if won: r["wins"] += 1
            elif hg == ag: r["draws"] += 1
            else: r["losses"] += 1
        rankings = []
        for k, r in recs.items():
            if r["matches"] == 0:
                continue
            wr = r["wins"] / r["matches"] * 100
            rankings.append({"team": self._display_name_for_key(k), "matches": r["matches"],
                              "wins": r["wins"], "draws": r["draws"], "losses": r["losses"],
                              "win_rate": round(wr, 1)})
        rankings.sort(key=lambda x: (x["win_rate"], x["wins"]), reverse=True)
        return {"venue": venue, "competition": comp_name, "season": season,
                "rankings": rankings[:20]}

    def best_home_record(self, competition: Optional[str] = None, season: Optional[int] = None) -> dict:
        """Rank teams by home win rate."""
        return self._venue_ranking("home", competition, season)

    def best_away_record(self, competition: Optional[str] = None, season: Optional[int] = None) -> dict:
        """Rank teams by away win rate."""
        return self._venue_ranking("away", competition, season)

    # ==================================================================
    # 3. PLAYER QUERIES
    # ==================================================================
    def find_players(self, name: Optional[str] = None, nationality: Optional[str] = None,
                     club: Optional[str] = None, position: Optional[str] = None,
                     min_rating: Optional[int] = None, max_rating: Optional[int] = None,
                     limit: Optional[int] = 50, sort_by: str = "overall") -> dict:
        """Find players matching the given criteria."""
        players = list(self.graph.players.values())
        if name:
            nl = name.lower()
            players = [p for p in players if nl in p.record.name.lower()]
        if nationality:
            nl = nationality.lower()
            players = [p for p in players if p.record.nationality.lower() == nl]
        if club:
            ck = team_match_key(club)
            players = [p for p in players if p.record.club_key == ck]
        if position:
            pu = position.upper()
            players = [p for p in players if p.record.position and p.record.position.upper() == pu]
        if min_rating is not None:
            players = [p for p in players if (p.record.overall or 0) >= min_rating]
        if max_rating is not None:
            players = [p for p in players if (p.record.overall or 0) <= max_rating]
        players.sort(key=lambda p: getattr(p.record, sort_by, None) or 0, reverse=True)
        total = len(players)
        limited = players[:limit] if limit is not None else players
        return {"players": [self._player_dict(p) for p in limited],
                "count": len(limited), "total_found": total}

    def top_players(self, nationality: Optional[str] = None, club: Optional[str] = None,
                    position: Optional[str] = None, limit: int = 10) -> dict:
        """Return the top-rated players (optionally filtered)."""
        return self.find_players(nationality=nationality, club=club,
                                 position=position, limit=limit, sort_by="overall")

    def players_at_brazilian_clubs(self, min_rating: int = 70, limit: int = 50) -> dict:
        """Find players at Brazilian clubs (cross-references match data)."""
        br_keys = set(self.graph.teams.keys())
        results = [p for p in self.graph.players.values()
                   if p.record.club_key in br_keys and (p.record.overall or 0) >= min_rating]
        results.sort(key=lambda p: p.record.overall or 0, reverse=True)
        total = len(results)
        limited = results[:limit]
        by_club = defaultdict(list)
        for p in limited:
            by_club[p.record.club].append(self._player_dict(p))
        return {
            "players": [self._player_dict(p) for p in limited],
            "count": len(limited), "total_found": total,
            "by_club": {c: pl for c, pl in sorted(by_club.items())}
        }

    # ==================================================================
    # 4. COMPETITION QUERIES
    # ==================================================================
    def competition_standings(self, competition: str, season: Optional[int] = None) -> dict:
        """Calculate standings for a competition season from match results.

        Uses 3 points per win, 1 per draw.  Teams are identified by
        ``(team_key, state)`` so that clubs sharing a base name
        (e.g. Atletico-MG vs Atletico-PR) are kept separate.
        """
        comp_node = self.graph.get_competition(competition)
        if not comp_node:
            return {"error": f"Competition not found: {competition}", "competition": competition}
        if season is not None and season not in comp_node.seasons:
            return {"error": f"Season {season} not found in {comp_node.name}",
                    "competition": comp_node.name, "season": season,
                    "available_seasons": sorted(comp_node.seasons)}
        table = defaultdict(lambda: {
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "points": 0,
            "display": "", "state": None,
        })
        for m in comp_node.matches:
            if season is not None and m.season != season:
                continue
            hg, ag = m.home_goals or 0, m.away_goals or 0
            if not m.home_team_key or not m.away_team_key:
                continue
            hid = (m.home_team_key, m.home_state)
            aid = (m.away_team_key, m.away_state)
            hr = table[hid]; ar = table[aid]
            hr["display"] = m.home_team; hr["state"] = m.home_state
            ar["display"] = m.away_team; ar["state"] = m.away_state
            hr["played"] += 1; ar["played"] += 1
            hr["goals_for"] += hg; hr["goals_against"] += ag
            ar["goals_for"] += ag; ar["goals_against"] += hg
            if hg > ag:
                hr["wins"] += 1; hr["points"] += 3
                ar["losses"] += 1
            elif hg < ag:
                ar["wins"] += 1; ar["points"] += 3
                hr["losses"] += 1
            else:
                hr["draws"] += 1; ar["draws"] += 1
                hr["points"] += 1; ar["points"] += 1
        standings = []
        for (key, state), rec in table.items():
            if rec["played"] == 0:
                continue
            gd = rec["goals_for"] - rec["goals_against"]
            name = rec["display"] or self._display_name_for_key(key)
            if state and " " not in name and name.lower() == key:
                name = f"{name} ({state})"
            elif state and state not in name:
                # Show state for disambiguation when key is ambiguous
                pass
            standings.append({
                "team": name, "team_key": key, "state": state,
                "played": rec["played"], "wins": rec["wins"],
                "draws": rec["draws"], "losses": rec["losses"],
                "goals_for": rec["goals_for"], "goals_against": rec["goals_against"],
                "goal_difference": gd, "points": rec["points"],
            })
        standings.sort(key=lambda x: (x["points"], x["wins"], x["goal_difference"],
                                      x["goals_for"]), reverse=True)
        for i, s in enumerate(standings, 1):
            s["position"] = i
        champion = standings[0]["team"] if standings else None
        return {
            "competition": comp_node.name, "season": season,
            "champion": champion,
            "standings": standings,
        }

    def competition_seasons(self, competition: str) -> dict:
        """List all seasons available for a competition."""
        comp_node = self.graph.get_competition(competition)
        if not comp_node:
            return {"error": f"Competition not found: {competition}"}
        return {
            "competition": comp_node.name,
            "seasons": sorted(comp_node.seasons),
            "total_matches": comp_node.match_count,
        }

    def competition_info(self, competition: str) -> dict:
        """Return summary information about a competition."""
        comp_node = self.graph.get_competition(competition)
        if not comp_node:
            return {"error": f"Competition not found: {competition}"}
        seasons = sorted(comp_node.seasons)
        season_counts = {}
        for s in seasons:
            sm = [m for m in comp_node.matches if m.season == s]
            total_goals = sum((m.home_goals or 0) + (m.away_goals or 0) for m in sm)
            season_counts[s] = {"matches": len(sm), "total_goals": total_goals}
        return {
            "competition": comp_node.name,
            "total_matches": comp_node.match_count,
            "seasons": seasons,
            "season_breakdown": season_counts,
        }

    def all_competitions(self) -> dict:
        """List all competitions with summary info."""
        comps = []
        for name in sorted(self.graph.competitions.keys()):
            c = self.graph.competitions[name]
            comps.append({
                "name": c.name, "total_matches": c.match_count,
                "seasons": sorted(c.seasons),
            })
        return {"competitions": comps}

    # ==================================================================
    # 5. STATISTICAL ANALYSIS
    # ==================================================================
    def biggest_wins(self, competition: Optional[str] = None,
                     season: Optional[int] = None, limit: int = 10) -> dict:
        """Find the biggest victory margins in the dataset."""
        comp_node = self.graph.get_competition(competition) if competition else None
        comp_name = comp_node.name if comp_node else None
        wins = []
        for m in self.graph.loader.matches:
            if comp_name and m.competition != comp_name:
                continue
            if season is not None and m.season != season:
                continue
            hg, ag = m.home_goals, m.away_goals
            if hg is None or ag is None:
                continue
            margin = abs(hg - ag)
            if margin == 0:
                continue
            if hg > ag:
                winner = m.home_team
                loser = m.away_team
                score = f"{hg}-{ag}"
            else:
                winner = m.away_team
                loser = m.home_team
                score = f"{ag}-{hg}"
            wins.append({
                "date": format_date(m.date), "winner": winner, "loser": loser,
                "score": score, "margin": margin, "competition": m.competition,
                "season": m.season,
            })
        wins.sort(key=lambda x: x["margin"], reverse=True)
        return {
            "competition": comp_name, "season": season,
            "biggest_wins": wins[:limit], "count": min(limit, len(wins)),
        }

    def average_goals(self, competition: Optional[str] = None,
                      season: Optional[int] = None) -> dict:
        """Calculate average goals per match and other scoring stats."""
        comp_node = self.graph.get_competition(competition) if competition else None
        comp_name = comp_node.name if comp_node else None
        total_goals = 0
        total_matches = 0
        home_goals = away_goals = 0
        for m in self.graph.loader.matches:
            if comp_name and m.competition != comp_name:
                continue
            if season is not None and m.season != season:
                continue
            hg, ag = m.home_goals or 0, m.away_goals or 0
            total_goals += hg + ag
            home_goals += hg
            away_goals += ag
            total_matches += 1
        if total_matches == 0:
            return {"error": "No matches found", "competition": comp_name, "season": season}
        home_win_rate = 0
        away_win_rate = 0
        draw_rate = 0
        hw = aw = dr = 0
        for m in self.graph.loader.matches:
            if comp_name and m.competition != comp_name:
                continue
            if season is not None and m.season != season:
                continue
            hg, ag = m.home_goals or 0, m.away_goals or 0
            if hg > ag: hw += 1
            elif hg < ag: aw += 1
            else: dr += 1
        home_win_rate = hw / total_matches * 100
        away_win_rate = aw / total_matches * 100
        draw_rate = dr / total_matches * 100
        return {
            "competition": comp_name, "season": season,
            "total_matches": total_matches, "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / total_matches, 2),
            "avg_home_goals": round(home_goals / total_matches, 2),
            "avg_away_goals": round(away_goals / total_matches, 2),
            "home_win_rate": round(home_win_rate, 1),
            "away_win_rate": round(away_win_rate, 1),
            "draw_rate": round(draw_rate, 1),
        }

    def home_vs_away(self, competition: Optional[str] = None,
                     season: Optional[int] = None) -> dict:
        """Compare home vs away performance across all matches."""
        return self.average_goals(competition=competition, season=season)

    def team_list(self, search: Optional[str] = None, limit: int = 50) -> dict:
        """List all teams (optionally filtered by search string)."""
        if search:
            teams = self.graph.find_teams(search)
        else:
            teams = list(self.graph.teams.values())
        teams.sort(key=lambda t: t.match_count, reverse=True)
        limited = teams[:limit]
        return {
            "teams": [
                {"team": t.display_name, "team_key": t.key,
                 "states": sorted(t.states), "total_matches": t.match_count}
                for t in limited
            ],
            "count": len(limited), "total_found": len(teams),
        }

    def search_all(self, query: str) -> dict:
        """Search across teams, players, and competitions by name."""
        teams = self.graph.find_teams(query)
        players = self.graph.find_players_by_name(query)
        comp = self.graph.get_competition(query)
        return {
            "query": query,
            "teams": [{"name": t.display_name, "key": t.key,
                       "total_matches": t.match_count} for t in teams[:10]],
            "players": [self._player_dict(p) for p in players[:10]],
            "competition": comp.name if comp else None,
        }
