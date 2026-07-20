"""Query API over the loaded soccer data.

Context
-------
This module wraps a ``DataLoader`` (records + ``KnowledgeGraph``) and exposes
the five capability categories required by TASK.md:

1. Match queries      - search by team, date range, competition, season, H2H.
2. Team queries       - statistics, records, goals, performance by competition.
3. Player queries     - search by name, nationality, club, position, rating.
4. Competition queries- standings (calculated from match results), schedules.
5. Statistical analysis - average goals, home/away performance, biggest wins.

Every method returns plain Python dicts/lists so the MCP server can JSON-encode
them and the ``formatters`` module can render the human-readable text the spec
shows as "example answer format".
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from .data_loader import (
    COMP_BRASILEIRAO,
    COMP_CUP,
    COMP_LIBERTADORES,
    DataLoader,
    Match,
)
from .normalize import team_key

# Traditional Brazilian derbies (accent/case-insensitive team keys).
DERBIES = [
    ("Flamengo", "Fluminense", "Fla-Flu"),
    ("Flamengo", "Vasco", "Clássico da Rivalidade"),
    ("Palmeiras", "Corinthians", "Maior de São Paulo"),
    ("São Paulo", "Corinthians", "Clássico Majestoso"),
    ("São Paulo", "Palmeiras", "Choque-Rei"),
    ("Santos", "São Paulo", "San-São"),
    ("Grêmio", "Internacional", "Grenal"),
    ("Atlético Mineiro", "Cruzeiro", "Clássico Mineiro"),
    ("Bahia", "Vitória", "Ba-Vi"),
    ("Sport", "Náutico", "Clássico dos Clássicos"),
    ("Ceará", "Fortaleza", "Clássico-Rei"),
]


def _goals_or_none(m: Match, side: str) -> Optional[int]:
    return m.home_goal if side == "home" else m.away_goal


class SoccerQueries:
    """High-level query API over loaded data and the knowledge graph."""

    def __init__(self, loader: DataLoader) -> None:
        self.loader = loader
        self.graph = loader.graph
        # Index matches by team key for fast team lookups.
        self._by_team: Dict[str, List[Match]] = defaultdict(list)
        for m in loader.matches:
            self._by_team[m.home_team_key].append(m)
            self._by_team[m.away_team_key].append(m)

    # ------------------------------------------------------------------ teams

    def find_team(self, query: str) -> Optional[Dict[str, Any]]:
        """Resolve *query* to a team node (accent/case-insensitive)."""
        node = self.graph.find_team(query)
        if node is None:
            return None
        return {"id": node.id, "label": node.label}

    def list_teams(self, competition: Optional[str] = None) -> List[str]:
        """List canonical team labels, optionally filtered by competition."""
        labels = set()
        for m in self.loader.matches:
            if competition and m.competition != competition:
                continue
            labels.add(m.home_team)
            labels.add(m.away_team)
        return sorted(labels)

    # ---------------------------------------------------------------- matches

    def search_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search matches by team, opponent, competition, season, and/or date range."""
        team_k = team_key(team) if team else None
        opp_k = team_key(opponent) if opponent else None
        comp = self._resolve_competition(competition) if competition else None
        from_date = _parse_iso(date_from)
        to_date = _parse_iso(date_to)
        candidates: List[Match]
        if team_k:
            candidates = self._by_team.get(team_k, [])
        else:
            candidates = self.loader.matches
        out: List[Dict[str, Any]] = []
        for m in candidates:
            if team_k and m.home_team_key != team_k and m.away_team_key != team_k:
                continue
            if opp_k and m.home_team_key != opp_k and m.away_team_key != opp_k:
                continue
            if opp_k and team_k:
                # Must involve both teams.
                if {m.home_team_key, m.away_team_key} != {team_k, opp_k}:
                    continue
            if comp and m.competition != comp:
                continue
            if season and m.season != season:
                continue
            if from_date and (m.date is None or m.date < from_date):
                continue
            if to_date and (m.date is None or m.date > to_date):
                continue
            out.append(self._match_to_dict(m))
            if limit and len(out) >= limit:
                break
        out.sort(key=lambda d: (d.get("date") or "0000-00-00"), reverse=True)
        return out

    def head_to_head(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> Dict[str, Any]:
        """Head-to-head record between *team_a* and *team_b*."""
        a_k = team_key(team_a)
        b_k = team_key(team_b)
        matches = [
            m for m in self.loader.matches
            if {m.home_team_key, m.away_team_key} == {a_k, b_k}
            and (competition is None or m.competition == self._resolve_competition(competition))
            and m.result_sign() != "unknown"
        ]
        a_wins = b_wins = draws = 0
        a_goals = b_goals = 0
        for m in matches:
            if m.home_team_key == a_k:
                a_g, b_g = m.home_goal, m.away_goal
            else:
                a_g, b_g = m.away_goal, m.home_goal
            a_goals += a_g or 0
            b_goals += b_g or 0
            if a_g > b_g:
                a_wins += 1
            elif a_g < b_g:
                b_wins += 1
            else:
                draws += 1
        a_label = self.graph.team_label(team_a)
        b_label = self.graph.team_label(team_b)
        return {
            "team_a": a_label,
            "team_b": b_label,
            "matches": len(matches),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "team_a_goals": a_goals,
            "team_b_goals": b_goals,
        }

    def last_match_between(self, team_a: str, team_b: str) -> Optional[Dict[str, Any]]:
        """Most recent match between *team_a* and *team_b*."""
        matches = self.search_matches(team=team_a, opponent=team_b)
        return matches[0] if matches else None

    # --------------------------------------------------------------- team stats

    def team_statistics(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,  # "home" | "away" | None (either)
    ) -> Dict[str, Any]:
        """Aggregate win/draw/loss/goals for *team* filtered by season/competition/venue."""
        tk = team_key(team)
        wins = draws = losses = 0
        goals_for = goals_against = 0
        matches_played = 0
        for m in self.loader.matches:
            if m.home_team_key != tk and m.away_team_key != tk:
                continue
            if season and m.season != season:
                continue
            if competition and m.competition != self._resolve_competition(competition):
                continue
            if venue == "home" and m.home_team_key != tk:
                continue
            if venue == "away" and m.away_team_key != tk:
                continue
            if m.result_sign() == "unknown":
                continue
            matches_played += 1
            if m.home_team_key == tk:
                gf, ga = m.home_goal or 0, m.away_goal or 0
            else:
                gf, ga = m.away_goal or 0, m.home_goal or 0
            goals_for += gf
            goals_against += ga
            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                draws += 1
        win_rate = wins / matches_played if matches_played else 0.0
        return {
            "team": self.graph.team_label(team),
            "season": season,
            "competition": self._resolve_competition(competition) if competition else None,
            "venue": venue,
            "matches": matches_played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "win_rate": round(win_rate, 4),
        }

    def team_competitions(self, team: str) -> List[Dict[str, Any]]:
        """Competitions *team* has played in, with match counts."""
        tk = team_key(team)
        counts: Dict[str, int] = defaultdict(int)
        for m in self.loader.matches:
            if m.home_team_key == tk or m.away_team_key == tk:
                counts[m.competition] += 1
        return [
            {"competition": c, "matches": n}
            for c, n in sorted(counts.items(), key=lambda kv: -kv[1])
        ]

    def derbies(self, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """Find traditional derby matches, optionally filtered by season."""
        out: List[Dict[str, Any]] = []
        seen_pairs: set = set()
        for a, b, name in DERBIES:
            a_k, b_k = team_key(a), team_key(b)
            key = frozenset((a_k, b_k))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            h2h = self.head_to_head(a, b)
            if h2h["matches"] == 0:
                continue
            matches = self.search_matches(team=a, opponent=b, season=season)
            if not matches:
                continue
            out.append({
                "derby_name": name,
                "team_a": h2h["team_a"],
                "team_b": h2h["team_b"],
                "matches_in_filter": len(matches),
                "head_to_head": h2h,
            })
        return out

    # ---------------------------------------------------------------- players

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = None,
        sort_by: str = "overall",
    ) -> List[Dict[str, Any]]:
        """Search FIFA player records by name, nationality, club, position, rating."""
        # Forward position groupings (so "forward" matches ST, LW, RW, CF, ...).
        pos_groups = {
            "forward": {"ST", "ST", "LS", "RS", "LW", "RW", "LF", "RF", "CF"},
            "midfielder": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
            "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB", "SW"},
            "goalkeeper": {"GK"},
        }
        target_positions = None
        if position:
            p = position.strip().lower()
            target_positions = pos_groups.get(p, {position.upper()})
        name_q = name.lower() if name else None
        club_q = club.lower() if club else None
        nat_q = nationality.lower() if nationality else None
        out: List[Dict[str, Any]] = []
        for p in self.loader.players:
            if name_q and name_q not in p.name.lower():
                continue
            if nat_q and nat_q not in p.nationality.lower():
                continue
            if club_q and club_q not in p.club.lower():
                continue
            if target_positions and p.position not in target_positions:
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            out.append(self._player_to_dict(p))
        out.sort(key=lambda d: d.get(sort_by) or 0, reverse=True)
        if limit:
            out = out[:limit]
        return out

    def top_brazilian_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Highest-rated Brazilian players in the FIFA dataset."""
        return self.search_players(nationality="Brazil", limit=limit, sort_by="overall")

    def club_roster(self, club: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Players whose club matches *club* (substring, sorted by rating)."""
        return self.search_players(club=club, limit=limit, sort_by="overall")

    # --------------------------------------------------------- competitions

    def list_competitions(self) -> List[str]:
        """Distinct competition names across all match files."""
        return sorted({m.competition for m in self.loader.matches})

    def competition_seasons(self, competition: str) -> List[int]:
        """Seasons available for *competition*."""
        comp = self._resolve_competition(competition)
        seasons = {m.season for m in self.loader.matches if m.competition == comp and m.season is not None}
        return sorted(s for s in seasons if s is not None)

    def standings(self, competition: str, season: int) -> List[Dict[str, Any]]:
        """Calculate standings (points, W/D/L, goals) for *competition* / *season*.

        Uses 3 points per win, 1 per draw, 0 per loss; works for any
        competition whose match file has full home/away scores
        (Brasileirão, Serie B, Serie C, Copa do Brasil, Libertadores).
        """
        comp = self._resolve_competition(competition)
        rows: Dict[str, Dict[str, Any]] = {}
        for m in self.loader.matches:
            if m.competition != comp or m.season != season:
                continue
            if m.result_sign() == "unknown":
                continue
            for side, team_key_val, gf, ga in (
                ("home", m.home_team_key, m.home_goal, m.away_goal),
                ("away", m.away_team_key, m.away_goal, m.home_goal),
            ):
                row = rows.setdefault(
                    team_key_val,
                    {
                        "team": m.home_team if side == "home" else m.away_team,
                        "team_key": team_key_val,
                        "played": 0, "wins": 0, "draws": 0, "losses": 0,
                        "goals_for": 0, "goals_against": 0, "points": 0,
                    },
                )
                # Fix display label to a more canonical one if available.
                row["team"] = self.graph.team_label(team_key_val) or row["team"]
                row["played"] += 1
                row["goals_for"] += gf or 0
                row["goals_against"] += ga or 0
                if gf > ga:
                    row["wins"] += 1
                    row["points"] += 3
                elif gf < ga:
                    row["losses"] += 1
                else:
                    row["draws"] += 1
                    row["points"] += 1
        ordered = sorted(
            rows.values(),
            key=lambda r: (
                -r["points"],
                -(r["goals_for"] - r["goals_against"]),
                -r["goals_for"],
                r["team"],
            ),
        )
        for i, r in enumerate(ordered, start=1):
            r["position"] = i
        return ordered

    def champion(self, competition: str, season: int) -> Optional[Dict[str, Any]]:
        """Return the champion (top of standings) for *competition* / *season*."""
        rows = self.standings(competition, season)
        if not rows:
            return None
        champ = rows[0]
        champ["champion"] = True
        return champ

    # ------------------------------------------------------------- statistics

    def average_goals(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> Dict[str, Any]:
        """Average goals per match and home/away win rates."""
        comp = self._resolve_competition(competition) if competition else None
        total_goals = 0
        matches = 0
        home_wins = away_wins = draws = 0
        for m in self.loader.matches:
            if comp and m.competition != comp:
                continue
            if season and m.season != season:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            matches += 1
            total_goals += m.home_goal + m.away_goal
            sign = m.result_sign()
            if sign == "home":
                home_wins += 1
            elif sign == "away":
                away_wins += 1
            elif sign == "draw":
                draws += 1
        decided = home_wins + away_wins + draws
        return {
            "competition": comp,
            "season": season,
            "matches": matches,
            "total_goals": total_goals,
            "average_goals_per_match": round(total_goals / matches, 3) if matches else 0.0,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(home_wins / decided, 3) if decided else 0.0,
            "away_win_rate": round(away_wins / decided, 3) if decided else 0.0,
            "draw_rate": round(draws / decided, 3) if decided else 0.0,
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Largest goal-margin victories, sorted by margin then by goals."""
        comp = self._resolve_competition(competition) if competition else None
        out: List[Dict[str, Any]] = []
        for m in self.loader.matches:
            if comp and m.competition != comp:
                continue
            if season and m.season != season:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            margin = abs(m.home_goal - m.away_goal)
            if margin == 0:
                continue
            winner = m.home_team if m.home_goal > m.away_goal else m.away_team
            loser = m.away_team if m.home_goal > m.away_goal else m.home_team
            out.append({
                "date": m.date.isoformat() if m.date else None,
                "season": m.season,
                "competition": m.competition,
                "winner": winner,
                "loser": loser,
                "score": f"{m.home_goal}-{m.away_goal}",
                "margin": margin,
                "goals": m.home_goal + m.away_goal,
            })
        out.sort(key=lambda d: (-d["margin"], -d["goals"]))
        return out[:limit]

    def best_home_record(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Team with the best home win rate (min 5 matches)."""
        comp = self._resolve_competition(competition) if competition else None
        agg: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "matches": 0})
        for m in self.loader.matches:
            if comp and m.competition != comp:
                continue
            if season and m.season != season:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            agg[m.home_team_key]["matches"] += 1
            if m.home_goal > m.away_goal:
                agg[m.home_team_key]["wins"] += 1
        best = None
        for tk, v in agg.items():
            if v["matches"] < 5:
                continue
            rate = v["wins"] / v["matches"]
            if best is None or rate > best["win_rate"]:
                best = {
                    "team": self.graph.team_label(tk),
                    "matches": v["matches"],
                    "wins": v["wins"],
                    "win_rate": round(rate, 4),
                }
        return best

    def best_away_record(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Team with the best away win rate (min 5 matches)."""
        comp = self._resolve_competition(competition) if competition else None
        agg: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "matches": 0})
        for m in self.loader.matches:
            if comp and m.competition != comp:
                continue
            if season and m.season != season:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            agg[m.away_team_key]["matches"] += 1
            if m.away_goal > m.home_goal:
                agg[m.away_team_key]["wins"] += 1
        best = None
        for tk, v in agg.items():
            if v["matches"] < 5:
                continue
            rate = v["wins"] / v["matches"]
            if best is None or rate > best["win_rate"]:
                best = {
                    "team": self.graph.team_label(tk),
                    "matches": v["matches"],
                    "wins": v["wins"],
                    "win_rate": round(rate, 4),
                }
        return best

    def top_scorers_by_team(self, competition: str, season: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Teams ranked by goals scored in *competition* / *season*."""
        comp = self._resolve_competition(competition)
        goals: Dict[str, int] = defaultdict(int)
        for m in self.loader.matches:
            if m.competition != comp or m.season != season:
                continue
            if m.home_goal is not None:
                goals[m.home_team_key] += m.home_goal
            if m.away_goal is not None:
                goals[m.away_team_key] += m.away_goal
        rows = [
            {"team": self.graph.team_label(tk), "goals": g}
            for tk, g in goals.items()
        ]
        rows.sort(key=lambda r: -r["goals"])
        return rows[:limit]

    # -------------------------------------------------------------- internals

    def _match_to_dict(self, m: Match) -> Dict[str, Any]:
        return {
            "match_id": m.match_id,
            "competition": m.competition,
            "season": m.season,
            "date": m.date.isoformat() if m.date else None,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "home_goal": m.home_goal,
            "away_goal": m.away_goal,
            "score": f"{m.home_goal}-{m.away_goal}" if m.home_goal is not None else None,
            "round": m.round_,
            "stage": m.stage,
            "arena": m.arena,
            "result": m.result_sign(),
        }

    def _player_to_dict(self, p) -> Dict[str, Any]:
        return {
            "id": p.id,
            "name": p.name,
            "age": p.age,
            "nationality": p.nationality,
            "overall": p.overall,
            "potential": p.potential,
            "club": p.club,
            "position": p.position,
            "jersey_number": p.jersey_number,
            "height": p.height,
            "weight": p.weight,
        }

    @staticmethod
    def _resolve_competition(name: Optional[str]) -> Optional[str]:
        """Map a user-supplied competition name to the canonical form."""
        if name is None:
            return None
        n = name.strip().lower()
        aliases = {
            "brasileirão": COMP_BRASILEIRAO,
            "brasileirao": COMP_BRASILEIRAO,
            "serie a": COMP_BRASILEIRAO,
            "série a": COMP_BRASILEIRAO,
            "copa do brasil": COMP_CUP,
            "brazilian cup": COMP_CUP,
            "libertadores": COMP_LIBERTADORES,
            "copa libertadores": COMP_LIBERTADORES,
            "serie b": "Serie B",
            "serie c": "Serie C",
        }
        return aliases.get(n, name)


def _parse_iso(value: Optional[str]):
    if not value:
        return None
    from .normalize import parse_date

    return parse_date(value)
