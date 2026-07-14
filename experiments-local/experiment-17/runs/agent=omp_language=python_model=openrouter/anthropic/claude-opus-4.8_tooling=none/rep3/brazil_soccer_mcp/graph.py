"""
================================================================================
brazil_soccer_mcp.graph
================================================================================
Context:
    The in-memory knowledge graph and query engine. It ingests normalized
    Match / Player records (from loaders.py) and answers the query categories
    required by the spec: match lookups, team stats, player search, competition
    standings, head-to-head and aggregate statistics.

Entities & relationships (conceptual graph):
    Team  --(home_of / away_of)-->  Match  <--(scored_in)--  goals
    Player --(plays_for)--> Club(Team) ; Player --(from)--> Nationality
    Match --(part_of)--> Competition (per season)

Implementation:
    Nodes/edges are realized as Python dicts/lists with precomputed indexes
    (matches-by-team-key, players-by-club/nationality/name token). Everything
    is built once at startup; queries are pure reads, so they are fast and
    side-effect free.

Team resolution:
    User queries are matched to canonical team keys via: exact normalized key,
    then a curated alias map, then substring containment (longest unambiguous
    match wins). This handles "Flamengo" / "Flamengo-RJ" / "São Paulo" /
    "Sao Paulo" without per-team hard-coding.

Deduplication:
    Aggregate computations (standings, averages, biggest wins) deduplicate
    overlapping source rows via Match.dedup_key so a fixture present in several
    CSVs is counted once.
================================================================================
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from .loaders import (
    DATA_DIR,
    Match,
    Player,
    load_all_matches,
    load_all_players,
)
from .normalize import normalize_competition, normalize_team, parse_team

# Curated aliases: colloquial/short form (base key) -> a raw team name whose
# parsed (base, state) resolves to the intended club.
_TEAM_ALIASES = {
    "galo": "Atletico-MG",
    "cam": "Atletico-MG",
    "fla": "Flamengo-RJ",
    "flu": "Fluminense-RJ",
    "timao": "Corinthians",
    "verdao": "Palmeiras",
    "peixe": "Santos-SP",
    "imortal": "Gremio",
    "colorado": "Internacional-RS",
    "inter": "Internacional-RS",
}


@dataclass
class TeamRecord:
    """Aggregated win/draw/loss/goal record for a team."""

    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    def add(self, scored: int, conceded: int) -> None:
        self.matches += 1
        self.goals_for += scored
        self.goals_against += conceded
        if scored > conceded:
            self.wins += 1
            self.points += 3
        elif scored == conceded:
            self.draws += 1
            self.points += 1
        else:
            self.losses += 1

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        return (self.wins / self.matches) if self.matches else 0.0


class KnowledgeGraph:
    """In-memory knowledge graph over matches and players."""

    # Source preference when several files cover the same (competition,
    # season) with equal match counts. Dedicated competition files carry
    # state suffixes + round numbers, so they win ties over the broad
    # stats file.
    _SOURCE_PRIORITY = {
        "Brasileirao_Matches.csv": 0,
        "Brazilian_Cup_Matches.csv": 1,
        "Libertadores_Matches.csv": 2,
        "novo_campeonato_brasileiro.csv": 3,
        "BR-Football-Dataset.csv": 4,
    }

    def __init__(self, matches: List[Match], players: List[Player]):
        self.matches = matches
        self.players = players

        self._assign_canonical_keys(matches)
        self.primary_matches = self._select_primary(matches)

        # Indexes (built over deduplicated primary matches) -------------------
        self._matches_by_team: Dict[str, List[Match]] = defaultdict(list)
        self._team_display: Dict[str, str] = {}
        self._team_key_set: set = set()
        self._team_bases: set = set()
        for m in self.primary_matches:
            for key, base, disp in (
                (m.home_ckey, m.home_key, m.home),
                (m.away_ckey, m.away_key, m.away),
            ):
                if not key:
                    continue
                self._matches_by_team[key].append(m)
                self._team_key_set.add(key)
                self._team_bases.add(base)
                cur = self._team_display.get(key)
                if cur is None or len(disp) < len(cur):
                    self._team_display[key] = disp

        self._players_by_club: Dict[str, List[Player]] = defaultdict(list)
        self._players_by_nat: Dict[str, List[Player]] = defaultdict(list)
        for p in players:
            if p.club_key:
                self._players_by_club[p.club_key].append(p)
            if p.nationality_key:
                self._players_by_nat[p.nationality_key].append(p)

    # ------------------------------------------------------------------ #
    # Canonical key assignment + source dedup
    # ------------------------------------------------------------------ #
    def _assign_canonical_keys(self, matches: List[Match]) -> None:
        """Compute corpus-aware canonical keys.

        A base name is *ambiguous* when it appears with more than one distinct
        state/country code across the whole corpus (e.g. "atletico" -> MG, GO,
        PR). For ambiguous bases the canonical key is "base|STATE" (missing
        states filled from the base's dominant state); unambiguous bases use
        the bare base, so "palmeiras-sp" and "palmeiras" still merge.
        """
        states_by_base: Dict[str, "Counter[str]"] = defaultdict(Counter)
        for m in matches:
            if m.home_state:
                states_by_base[m.home_key][m.home_state] += 1
            if m.away_state:
                states_by_base[m.away_key][m.away_state] += 1

        self._ambiguous_bases = {
            base for base, c in states_by_base.items() if len(c) > 1
        }
        self._dominant_state = {
            base: c.most_common(1)[0][0] for base, c in states_by_base.items()
        }

        for m in matches:
            m.home_ckey = self._canonical(m.home_key, m.home_state)
            m.away_ckey = self._canonical(m.away_key, m.away_state)

    def _canonical(self, base: str, state: Optional[str]) -> str:
        if not base:
            return ""
        if base in self._ambiguous_bases:
            st = state or self._dominant_state.get(base)
            return f"{base}|{st}" if st else base
        return base

    def _select_primary(self, matches: List[Match]) -> List[Match]:
        """Keep one source per (competition, season) to avoid double counting.

        For each (competition, season) choose the source with the most rows;
        ties broken by _SOURCE_PRIORITY. Seasons covered by only one file keep
        that file. The full match list stays available via self.matches.
        """
        by_group: Dict[Tuple[str, Optional[int]], "Counter[str]"] = defaultdict(Counter)
        for m in matches:
            by_group[(m.competition, m.season)][m.source] += 1
        chosen: Dict[Tuple[str, Optional[int]], str] = {}
        for group, counts in by_group.items():
            chosen[group] = min(
                counts,
                key=lambda s: (-counts[s], self._SOURCE_PRIORITY.get(s, 99)),
            )
        return [
            m for m in matches if chosen[(m.competition, m.season)] == m.source
        ]

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def from_data_dir(cls, data_dir: str = DATA_DIR) -> "KnowledgeGraph":
        return cls(load_all_matches(data_dir), load_all_players(data_dir))

    # ------------------------------------------------------------------ #
    # Team resolution
    # ------------------------------------------------------------------ #
    def resolve_team(self, query: str) -> Optional[str]:
        """Resolve a user team string to a canonical team key, or None.

        Honors a state/country suffix in the query: "Atletico-GO" maps to the
        GO club, distinct from "Atletico-MG". Falls back to the base's
        canonical key, then curated aliases, then substring containment.
        """
        if not query:
            return None
        base, state = parse_team(query)
        if not base:
            return None
        # Build the canonical key the same way the corpus did.
        ckey = self._canonical(base, state)
        if ckey in self._team_key_set:
            return ckey
        # Base-only canonical (ignore a possibly-absent state).
        bare = self._canonical(base, None)
        if bare in self._team_key_set:
            return bare
        if base in _TEAM_ALIASES:
            alias = self._canonical(*parse_team(_TEAM_ALIASES[base]))
            if alias in self._team_key_set:
                return alias
        # Substring containment over base names; prefer most-played team.
        candidates = [
            k
            for k in self._team_key_set
            if base in k.split("|")[0] or k.split("|")[0] in base
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda k: len(self._matches_by_team[k]))

    def team_display(self, key: Optional[str]) -> str:
        """Human-readable name for a canonical key (state shown if ambiguous)."""
        if not key:
            return ""
        disp = self._team_display.get(key, key)
        if "|" in key:
            state = key.split("|", 1)[1]
            if state and not disp.upper().endswith(state):
                return f"{disp}-{state}"
        return disp

    # ------------------------------------------------------------------ #
    # Match queries
    # ------------------------------------------------------------------ #
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        home_only: bool = False,
        away_only: bool = False,
        limit: Optional[int] = None,
    ) -> List[Match]:
        team_key = self.resolve_team(team) if team else None
        opp_key = self.resolve_team(opponent) if opponent else None
        comp = normalize_competition(competition) if competition else None
        df = normalize_date(date_from) if date_from else None
        dt = normalize_date(date_to) if date_to else None

        if team_key:
            pool: Iterable[Match] = self._matches_by_team.get(team_key, [])
        else:
            pool = self.primary_matches

        results: List[Match] = []
        for m in pool:
            if team_key:
                if home_only and m.home_ckey != team_key:
                    continue
                if away_only and m.away_ckey != team_key:
                    continue
                if not home_only and not away_only and team_key not in (m.home_ckey, m.away_ckey):
                    continue
            if opp_key and opp_key not in (m.home_ckey, m.away_ckey):
                continue
            if comp and m.competition != comp:
                continue
            if season is not None and m.season != season:
                continue
            if df and (m.date is None or m.date < df):
                continue
            if dt and (m.date is None or m.date > dt):
                continue
            results.append(m)

        results.sort(key=lambda x: (x.date or date.min, x.competition))
        if limit is not None:
            return results[:limit]
        return results

    # ------------------------------------------------------------------ #
    # Team statistics
    # ------------------------------------------------------------------ #
    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        home_only: bool = False,
        away_only: bool = False,
    ) -> Optional[Tuple[str, TeamRecord]]:
        team_key = self.resolve_team(team)
        if not team_key:
            return None
        comp = normalize_competition(competition) if competition else None
        rec = TeamRecord()
        for m in self._matches_by_team.get(team_key, []):
            if season is not None and m.season != season:
                continue
            if comp and m.competition != comp:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            is_home = m.home_ckey == team_key
            if home_only and not is_home:
                continue
            if away_only and is_home:
                continue
            if is_home:
                rec.add(m.home_goal, m.away_goal)
            else:
                rec.add(m.away_goal, m.home_goal)
        return team_key, rec

    def head_to_head(
        self, team_a: str, team_b: str, competition: Optional[str] = None
    ) -> Optional[dict]:
        ka = self.resolve_team(team_a)
        kb = self.resolve_team(team_b)
        if not ka or not kb:
            return None
        comp = normalize_competition(competition) if competition else None
        a_wins = b_wins = draws = a_goals = b_goals = 0
        meetings: List[Match] = []
        for m in self._matches_by_team.get(ka, []):
            if kb not in (m.home_ckey, m.away_ckey):
                continue
            if comp and m.competition != comp:
                continue
            meetings.append(m)
            if m.home_goal is None or m.away_goal is None:
                continue
            a_is_home = m.home_ckey == ka
            a_score = m.home_goal if a_is_home else m.away_goal
            b_score = m.away_goal if a_is_home else m.home_goal
            a_goals += a_score
            b_goals += b_score
            if a_score > b_score:
                a_wins += 1
            elif b_score > a_score:
                b_wins += 1
            else:
                draws += 1
        meetings.sort(key=lambda x: (x.date or date.min))
        return {
            "team_a_key": ka,
            "team_b_key": kb,
            "team_a": self.team_display(ka),
            "team_b": self.team_display(kb),
            "a_wins": a_wins,
            "b_wins": b_wins,
            "draws": draws,
            "a_goals": a_goals,
            "b_goals": b_goals,
            "meetings": meetings,
        }

    # ------------------------------------------------------------------ #
    # Player queries
    # ------------------------------------------------------------------ #
    def search_players(self, name: str, limit: int = 25) -> List[Player]:
        key = normalize_team(name)
        if not key:
            return []
        exact = [p for p in self.players if p.name_key == key]
        if exact:
            return sorted(exact, key=lambda p: -(p.overall or 0))[:limit]
        partial = [p for p in self.players if key in p.name_key]
        return sorted(partial, key=lambda p: -(p.overall or 0))[:limit]

    def players_by_club(self, club: str, limit: Optional[int] = None) -> List[Player]:
        club_key = normalize_team(club)
        result = list(self._players_by_club.get(club_key, []))
        if not result and club_key:
            # Substring fallback over club keys.
            for k, players in self._players_by_club.items():
                if club_key in k or k in club_key:
                    result.extend(players)
        result.sort(key=lambda p: -(p.overall or 0))
        return result[:limit] if limit else result

    def players_by_nationality(
        self, nationality: str, limit: Optional[int] = None
    ) -> List[Player]:
        key = normalize_team(nationality)
        result = list(self._players_by_nat.get(key, []))
        result.sort(key=lambda p: -(p.overall or 0))
        return result[:limit] if limit else result

    def top_players(
        self,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> List[Player]:
        if nationality:
            pool = self.players_by_nationality(nationality)
        elif club:
            pool = self.players_by_club(club)
        else:
            pool = list(self.players)
        if position:
            pos = position.strip().upper()
            pool = [p for p in pool if p.position.upper() == pos]
        pool.sort(key=lambda p: -(p.overall or 0))
        return pool[:limit]

    def brazilian_clubs_summary(self, top: int = 25) -> List[dict]:
        """Brazilian players grouped by club (Brazilian-club heuristic).

        A club is treated as Brazilian if it also appears as a team in the
        match data (i.e. it plays in Brazilian competitions).
        """
        brazilians = self._players_by_nat.get("brazil", [])
        by_club: Dict[str, List[Player]] = defaultdict(list)
        for p in brazilians:
            if p.club_key and p.club_key in self._team_bases:
                by_club[p.club].append(p)
        summary = []
        for club, players in by_club.items():
            ratings = [p.overall for p in players if p.overall is not None]
            summary.append(
                {
                    "club": club,
                    "count": len(players),
                    "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0.0,
                }
            )
        summary.sort(key=lambda d: (-d["count"], -d["avg_rating"]))
        return summary[:top]

    # ------------------------------------------------------------------ #
    # Competition queries
    # ------------------------------------------------------------------ #
    def standings(
        self, competition: str, season: int
    ) -> List[Tuple[str, TeamRecord]]:
        comp = normalize_competition(competition)
        pool = [
            m
            for m in self.primary_matches
            if m.competition == comp
            and m.season == season
            and m.home_goal is not None
            and m.away_goal is not None
        ]
        table: Dict[str, TeamRecord] = defaultdict(TeamRecord)
        for m in pool:
            table[m.home_ckey].add(m.home_goal, m.away_goal)
            table[m.away_ckey].add(m.away_goal, m.home_goal)
        rows = list(table.items())
        rows.sort(
            key=lambda kv: (
                -kv[1].points,
                -kv[1].wins,
                -kv[1].goal_difference,
                -kv[1].goals_for,
            )
        )
        return rows

    def champion(self, competition: str, season: int) -> Optional[Tuple[str, TeamRecord]]:
        table = self.standings(competition, season)
        return table[0] if table else None

    def seasons(self, competition: Optional[str] = None) -> List[int]:
        comp = normalize_competition(competition) if competition else None
        years = {
            m.season
            for m in self.matches
            if m.season is not None and (comp is None or m.competition == comp)
        }
        return sorted(years)

    def competitions(self) -> List[str]:
        return sorted({m.competition for m in self.matches})

    # ------------------------------------------------------------------ #
    # Aggregate statistics
    # ------------------------------------------------------------------ #
    def aggregate_stats(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        comp = normalize_competition(competition) if competition else None
        pool = [
            m
            for m in self.primary_matches
            if m.home_goal is not None
            and m.away_goal is not None
            and (comp is None or m.competition == comp)
            and (season is None or m.season == season)
        ]
        n = len(pool)
        if n == 0:
            return {
                "matches": 0,
                "avg_goals_per_match": 0.0,
                "home_win_rate": 0.0,
                "away_win_rate": 0.0,
                "draw_rate": 0.0,
                "total_goals": 0,
            }
        total_goals = sum(m.home_goal + m.away_goal for m in pool)
        home_wins = sum(1 for m in pool if m.home_goal > m.away_goal)
        away_wins = sum(1 for m in pool if m.away_goal > m.home_goal)
        draws = n - home_wins - away_wins
        return {
            "matches": n,
            "avg_goals_per_match": round(total_goals / n, 2),
            "home_win_rate": round(home_wins / n, 3),
            "away_win_rate": round(away_wins / n, 3),
            "draw_rate": round(draws / n, 3),
            "total_goals": total_goals,
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> List[Match]:
        comp = normalize_competition(competition) if competition else None
        pool = [
            m
            for m in self.primary_matches
            if m.home_goal is not None
            and m.away_goal is not None
            and (comp is None or m.competition == comp)
            and (season is None or m.season == season)
        ]
        pool.sort(
            key=lambda m: (
                -abs(m.home_goal - m.away_goal),
                -(m.home_goal + m.away_goal),
                m.date or date.min,
            )
        )
        return pool[:limit]

    def best_record(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        home_only: bool = False,
        away_only: bool = False,
        min_matches: int = 5,
    ) -> List[Tuple[str, TeamRecord]]:
        comp = normalize_competition(competition) if competition else None
        pool = [
            m
            for m in self.primary_matches
            if m.home_goal is not None
            and m.away_goal is not None
            and (comp is None or m.competition == comp)
            and (season is None or m.season == season)
        ]
        table: Dict[str, TeamRecord] = defaultdict(TeamRecord)
        for m in pool:
            if not away_only:
                table[m.home_ckey].add(m.home_goal, m.away_goal)
            if not home_only:
                table[m.away_ckey].add(m.away_goal, m.home_goal)
        rows = [(k, r) for k, r in table.items() if r.matches >= min_matches]
        rows.sort(key=lambda kv: (-kv[1].win_rate, -kv[1].matches))
        return rows


def build_graph(data_dir: str = DATA_DIR) -> KnowledgeGraph:
    """Convenience constructor used by the server and tests."""
    return KnowledgeGraph.from_data_dir(data_dir)
