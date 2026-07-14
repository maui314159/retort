"""
================================================================================
Context
--------------------------------------------------------------------------------
Module  : brazilian_soccer.graph
Purpose : SoccerGraph - the in-memory knowledge graph and query engine that
          answers every capability category in the spec:
            1. Match queries      (by team / date range / competition / season)
            2. Team queries       (record, goals, per-competition splits)
            3. Player queries      (name / nationality / club search)
            4. Competition queries (standings computed from results)
            5. Statistical analysis (averages, biggest wins, head-to-head,
                                     home vs away, best records)

Graph model:
  Nodes  - teams (keyed by normalized name), players, matches.
  Edges  - team --PLAYED--> match (home/away), player --PLAYS_FOR--> team.
Indexes built once at construction:
  _by_team[key]        -> list[MatchRecord]   (every match a team appears in)
  _by_competition[c]   -> list[MatchRecord]
  _players_by_club[k]  -> list[PlayerRecord]
  _players_by_nat[n]   -> list[PlayerRecord]
This keeps simple lookups O(matches-for-one-team) and aggregate queries a single
linear pass, comfortably inside the spec's 2s / 5s budgets.

Team-name resolution goes through normalize.normalize_team, so callers may pass
"Flamengo", "Flamengo-RJ" or "Clube de Regatas do Flamengo" interchangeably.
================================================================================
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence

from .loader import MatchRecord, PlayerRecord
from .normalize import base_of, normalize_team, parse_date, split_team, team_key

@dataclass(slots=True)
class TeamRecord:
    """Aggregated win/draw/loss/goal record for a team over a match subset."""

    team: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return self.wins / self.matches if self.matches else 0.0

    def as_dict(self) -> dict:
        return {
            "team": self.team,
            "matches": self.matches,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
            "points": self.points,
            "win_rate": round(self.win_rate, 4),
        }


def _match_dict(m: MatchRecord) -> dict:
    return {
        "competition": m.competition,
        "season": m.season,
        "date": m.match_date.isoformat() if m.match_date else None,
        "home_team": m.home_name,
        "away_team": m.away_name,
        "home_goal": m.home_goal,
        "away_goal": m.away_goal,
        "round": m.round,
        "stage": m.stage,
        "source": m.source,
    }


def _player_dict(p: PlayerRecord) -> dict:
    return {
        "id": p.player_id,
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "position": p.position,
    }


class SoccerGraph:
    """Indexed knowledge graph over match and player records."""

    def __init__(
        self, matches: Sequence[MatchRecord], players: Sequence[PlayerRecord]
    ) -> None:
        self.matches: List[MatchRecord] = self._dedup(matches)
        self.players: List[PlayerRecord] = list(players)

        self._by_team: Dict[str, List[MatchRecord]] = defaultdict(list)
        self._by_competition: Dict[str, List[MatchRecord]] = defaultdict(list)
        self._display: Dict[str, str] = {}
        # base name -> set of full state-aware keys sharing it, so a bare-name
        # query ("Flamengo") fans out to every concrete club key it matches.
        self._by_base: Dict[str, set] = defaultdict(set)
        for m in self.matches:
            self._by_competition[m.competition].append(m)
            for key, name in ((m.home_key, m.home_name), (m.away_key, m.away_name)):
                if not key:
                    continue
                self._by_team[key].append(m)
                self._display.setdefault(key, name)
                self._by_base[base_of(key)].add(key)

        # Disambiguate display names for clubs that share a base name but differ
        # by state (e.g. "Atletico" -> "Atletico-MG" / "Atletico-PR") so callers
        # never see two distinct clubs under one label.
        for base, keys in self._by_base.items():
            if len(keys) > 1:
                for k in keys:
                    sep = k.split("|", 1)
                    if len(sep) == 2 and sep[1]:
                        self._display[k] = f"{self._display[k]}-{sep[1].upper()}"

        # For each base name, the canonical key set a *bare* query resolves to:
        # the unstated base key (rows that carry no state, e.g. Libertadores
        # "Palmeiras") plus the single dominant state variant by match count.
        # This makes "Flamengo" mean Flamengo-RJ rather than a union with the
        # minor Flamengo-PI, while still spanning datasets that omit the state.
        self._canonical: Dict[str, frozenset] = {}
        for base, keys in self._by_base.items():
            chosen = set()
            if base in self._by_team:
                chosen.add(base)
            stated = [k for k in keys if "|" in k]
            if stated:
                stated.sort(key=lambda k: len(self._by_team[k]), reverse=True)
                chosen.add(stated[0])
            self._canonical[base] = frozenset(chosen or keys)

        self._players_by_club: Dict[str, List[PlayerRecord]] = defaultdict(list)
        self._players_by_nat: Dict[str, List[PlayerRecord]] = defaultdict(list)
        for p in self.players:
            if p.club_key:
                self._players_by_club[p.club_key].append(p)
            if p.nationality:
                self._players_by_nat[p.nationality.lower()].append(p)

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _dedup(matches: Sequence[MatchRecord]) -> List[MatchRecord]:
        """Drop duplicate match rows shared across overlapping source files.

        The Brasileirão is present in both Brasileirao_Matches.csv (with state
        suffixes) and the historical novo_campeonato_brasileiro.csv for the
        overlapping 2012-2019 seasons. The two disagree on the exact date (often
        by a day), so date cannot be part of the identity; within a competition
        and season a (home, away) league fixture with a given scoreline is
        unique. First-seen wins, preserving the richer state-suffixed,
        round-bearing Brasileirao_Matches row which is loaded first. Rows
        lacking both team keys or a season are always kept.

        BR-Football-Dataset.csv is kept under its own "Serie A" label rather
        than merged into "Brasileirão": it uses verbose, suffix-free team names
        that do not reliably reduce to the same key, and the spec treats it as a
        separate extended-statistics dataset. League standings and competition-
        filtered records therefore stay clean, while unfiltered team queries
        legitimately span both labels.
        """
        seen: set = set()
        out: List[MatchRecord] = []
        for m in matches:
            if not m.home_key or not m.away_key or m.season is None:
                out.append(m)
                continue
            key = (
                m.competition,
                m.season,
                m.home_key,
                m.away_key,
                m.home_goal,
                m.away_goal,
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(m)
        return out


    def _resolve_keys(self, team: Optional[str]) -> Optional[frozenset]:
        """Map a team query to the set of concrete state-aware keys it matches.

        A state-qualified name ("Atletico-MG") resolves to exactly that key. A
        bare name ("Flamengo") resolves to the canonical set for its base: the
        unstated base key plus the dominant state variant by match count, so it
        means the major club (Flamengo-RJ), not a union with minor namesakes.
        Returns None for empty input, or an empty set when nothing matches.
        """
        if not team:
            return None
        base, state = split_team(team)
        if not base:
            return frozenset()
        if state:
            return frozenset({f"{base}|{state}"})
        canonical = self._canonical.get(base)
        if canonical:
            return canonical
        # Unseen base: fall back to anything sharing it (possibly empty).
        keys = set(self._by_base.get(base, ()))
        if base in self._by_team:
            keys.add(base)
        return frozenset(keys)

    def team_display_name(self, team: str) -> str:
        """Best-known display name for *team* (falls back to the input)."""
        keys = self._resolve_keys(team)
        if keys:
            for k in keys:
                if k in self._display:
                    return self._display[k]
        return team

    def _competition_matches(self, competition: Optional[str]) -> List[MatchRecord]:
        if not competition:
            return self.matches
        target = competition.strip().lower()
        # Allow partial/alias matches like "serie a" -> "Serie A", "libertadores".
        result: List[MatchRecord] = []
        seen_keys = set()
        for key, lst in self._by_competition.items():
            if target in key.lower():
                result.extend(lst)
                seen_keys.add(key)
        return result

    # -- 1. Match queries ----------------------------------------------------

    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        home_only: bool = False,
        away_only: bool = False,
        limit: Optional[int] = None,
    ) -> List[MatchRecord]:
        """Filter matches by any combination of criteria.

        team/opponent are normalized; season is an int year; date bounds are
        inclusive ISO/Brazilian date strings. Results are sorted newest-first.
        """
        team_keys = self._resolve_keys(team)
        opp_keys = self._resolve_keys(opponent)
        start = parse_date(start_date) if start_date else None
        end = parse_date(end_date) if end_date else None

        # Start from the narrowest available index: union the team's match lists.
        if team_keys:
            pool: Sequence[MatchRecord] = []
            for k in team_keys:
                pool.extend(self._by_team.get(k, ()))
        elif competition:
            pool = self._competition_matches(competition)
        else:
            pool = self.matches

        comp_target = competition.strip().lower() if competition else None
        seen_ids: set = set()
        out: List[MatchRecord] = []
        for m in pool:
            if team_keys and len(team_keys) > 1:
                if id(m) in seen_ids:
                    continue
                seen_ids.add(id(m))
            if team_keys:
                home_match = m.home_key in team_keys
                away_match = m.away_key in team_keys
                if home_only and not home_match:
                    continue
                if away_only and not away_match:
                    continue
                if not home_only and not away_only and not (home_match or away_match):
                    continue
            if opp_keys is not None and not (
                m.home_key in opp_keys or m.away_key in opp_keys
            ):
                continue
            if comp_target and comp_target not in m.competition.lower():
                continue
            if season is not None and m.season != season:
                continue
            if start and (m.match_date is None or m.match_date < start):
                continue
            if end and (m.match_date is None or m.match_date > end):
                continue
            out.append(m)

        out.sort(key=lambda r: (r.match_date or date.min), reverse=True)
        return out[:limit] if limit else out

    def head_to_head(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> dict:
        """Head-to-head summary between two teams across (optional) competition."""
        keys_a = self._resolve_keys(team_a) or frozenset()
        keys_b = self._resolve_keys(team_b) or frozenset()
        matches = self.find_matches(team=team_a, opponent=team_b, competition=competition)
        a_wins = b_wins = draws = 0
        for m in matches:
            w = m.winner_key()
            if w is None:
                if m.has_score:
                    draws += 1
            elif w in keys_a:
                a_wins += 1
            elif w in keys_b:
                b_wins += 1
        return {
            "team_a": self.team_display_name(team_a),
            "team_b": self.team_display_name(team_b),
            "total_matches": len(matches),
            "team_a_wins": a_wins,
            "team_b_wins": b_wins,
            "draws": draws,
            "matches": [_match_dict(m) for m in matches],
        }

    # -- 2. Team queries -----------------------------------------------------

    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",  # "all" | "home" | "away"
    ) -> TeamRecord:
        """Compute a team's W/D/L and goal record over the filtered matches."""
        keys = self._resolve_keys(team) or frozenset()
        rec = TeamRecord(team=self.team_display_name(team))
        home_only = venue == "home"
        away_only = venue == "away"
        for m in self.find_matches(
            team=team,
            season=season,
            competition=competition,
            home_only=home_only,
            away_only=away_only,
        ):
            if not m.has_score:
                continue
            is_home = m.home_key in keys
            gf = m.home_goal if is_home else m.away_goal
            ga = m.away_goal if is_home else m.home_goal
            rec.matches += 1
            rec.goals_for += gf
            rec.goals_against += ga
            if gf > ga:
                rec.wins += 1
            elif gf < ga:
                rec.losses += 1
            else:
                rec.draws += 1
        return rec

    # -- 3. Player queries ---------------------------------------------------

    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[PlayerRecord]:
        """Search players by any combination of fields, sorted by rating desc."""
        if club:
            pool: Sequence[PlayerRecord] = self._players_by_club.get(
                normalize_team(club), []
            )
        elif nationality:
            pool = self._players_by_nat.get(nationality.strip().lower(), [])
        else:
            pool = self.players

        name_q = name.strip().lower() if name else None
        pos_q = position.strip().lower() if position else None
        out: List[PlayerRecord] = []
        for p in pool:
            if name_q and name_q not in p.name.lower():
                continue
            if pos_q and pos_q != p.position.lower():
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            out.append(p)
        out.sort(key=lambda p: (p.overall or 0), reverse=True)
        return out[:limit] if limit else out

    # -- 4. Competition queries ----------------------------------------------

    def standings(
        self, competition: str, season: int
    ) -> List[TeamRecord]:
        """League table computed from match results for one season.

        Sorted by points, then goal difference, then goals scored. Each match
        with a recorded score contributes 3/1/0 points. Cup/knockout matches
        produce a table too, but it is most meaningful for league play.
        """
        comp_target = competition.strip().lower()
        table: Dict[str, TeamRecord] = {}

        def slot(key: str, display: str) -> TeamRecord:
            r = table.get(key)
            if r is None:
                r = TeamRecord(team=display)
                table[key] = r
            return r

        for m in self.matches:
            if m.season != season or comp_target not in m.competition.lower():
                continue
            if not m.has_score or not m.home_key or not m.away_key:
                continue
            home = slot(m.home_key, m.home_name)
            away = slot(m.away_key, m.away_name)
            home.matches += 1
            away.matches += 1
            home.goals_for += m.home_goal
            home.goals_against += m.away_goal
            away.goals_for += m.away_goal
            away.goals_against += m.home_goal
            if m.home_goal > m.away_goal:
                home.wins += 1
                away.losses += 1
            elif m.home_goal < m.away_goal:
                away.wins += 1
                home.losses += 1
            else:
                home.draws += 1
                away.draws += 1

        return sorted(
            table.values(),
            key=lambda r: (r.points, r.goal_difference, r.goals_for),
            reverse=True,
        )

    # -- 5. Statistical analysis ---------------------------------------------

    def average_goals(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        """Average goals/match and home/away/draw win rates over a subset."""
        pool = self._competition_matches(competition)
        total_goals = 0
        counted = 0
        home_wins = away_wins = draws = 0
        for m in pool:
            if season is not None and m.season != season:
                continue
            if not m.has_score:
                continue
            counted += 1
            total_goals += m.home_goal + m.away_goal
            if m.home_goal > m.away_goal:
                home_wins += 1
            elif m.away_goal > m.home_goal:
                away_wins += 1
            else:
                draws += 1
        return {
            "competition": competition or "all",
            "season": season,
            "matches": counted,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / counted, 4) if counted else 0.0,
            "home_win_rate": round(home_wins / counted, 4) if counted else 0.0,
            "away_win_rate": round(away_wins / counted, 4) if counted else 0.0,
            "draw_rate": round(draws / counted, 4) if counted else 0.0,
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[MatchRecord]:
        """Matches with the largest goal margin, biggest first."""
        pool = self._competition_matches(competition)
        scored = [
            m
            for m in pool
            if m.has_score and (season is None or m.season == season)
        ]
        scored.sort(
            key=lambda m: (abs(m.home_goal - m.away_goal), m.home_goal + m.away_goal),
            reverse=True,
        )
        return scored[:limit]

    def best_records(
        self,
        venue: str = "all",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 5,
        limit: int = 10,
    ) -> List[TeamRecord]:
        """Teams ranked by win rate (then points) over the filtered subset.

        venue selects home-only, away-only or all matches.
        """
        pool = self._competition_matches(competition)
        home_only = venue == "home"
        away_only = venue == "away"
        table: Dict[str, TeamRecord] = {}

        def slot(key: str, display: str) -> TeamRecord:
            r = table.get(key)
            if r is None:
                r = TeamRecord(team=display)
                table[key] = r
            return r

        for m in pool:
            if season is not None and m.season != season:
                continue
            if not m.has_score:
                continue
            for is_home in (True, False):
                if home_only and not is_home:
                    continue
                if away_only and is_home:
                    continue
                key = m.home_key if is_home else m.away_key
                display = m.home_name if is_home else m.away_name
                if not key:
                    continue
                gf = m.home_goal if is_home else m.away_goal
                ga = m.away_goal if is_home else m.home_goal
                r = slot(key, display)
                r.matches += 1
                r.goals_for += gf
                r.goals_against += ga
                if gf > ga:
                    r.wins += 1
                elif gf < ga:
                    r.losses += 1
                else:
                    r.draws += 1

        ranked = [r for r in table.values() if r.matches >= min_matches]
        ranked.sort(key=lambda r: (r.win_rate, r.points, r.goal_difference), reverse=True)
        return ranked[:limit]

    # -- dict-returning convenience wrappers (used by the MCP server) --------

    @staticmethod
    def match_to_dict(m: MatchRecord) -> dict:
        return _match_dict(m)

    @staticmethod
    def player_to_dict(p: PlayerRecord) -> dict:
        return _player_dict(p)
