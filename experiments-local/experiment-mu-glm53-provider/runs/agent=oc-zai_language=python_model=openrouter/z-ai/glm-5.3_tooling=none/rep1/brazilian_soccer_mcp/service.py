"""
Query/analytics engine over the loaded soccer data.

Context (Why): TASK.md "Required Capabilities" enumerates five query families
the MCP server must support - match queries, team queries, player queries,
competition queries and statistical analysis - plus the "Sample Questions"
table (simple lookups, relationship queries, analytical queries). The MCP
tool layer (server.py) must stay thin, so all domain logic lives here.

What:
    * Match queries: ``search_matches`` (by team, opponent, competition,
      season, date range, stage), ``head_to_head``, ``derby_matches``,
      ``finals``.
    * Team queries: ``team_record`` (W/D/L, goals, win rate, home/away
      split), ``team_overview`` (cross-file: aliases, competitions, seasons,
      FIFA squad bridge).
    * Competition queries: ``standings`` (calculated from match results with
      Brazilian tie-breaks: points, wins, goal difference, goals for),
      ``champion`` (league standings top / cup finals aggregate),
      ``relegated`` (bottom N), ``seasons``.
    * Player queries: ``search_players`` (name, nationality, club, position
      or position group, ratings), ``player_profile``, ``club_squad``,
      ``top_brazilian_players``, ``brazilians_at_brazilian_clubs``.
    * Statistics: ``competition_stats`` (average goals, home/draw/away win
      rates), ``biggest_wins``, ``best_records`` (best home/away teams),
      ``compare_seasons``.

    Aggregation rules: queries that pin BOTH competition and season use the
    single most authoritative source for that season (``primary_matches``)
    so overlapping datasets never double-count a fixture; everything else
    uses the deduplicated full match set.

    Every ``*_formatted`` method renders results in the human-readable style
    of the "Example answer format" blocks in TASK.md, which is what the MCP
    tools return to the LLM.

Test: tests/test_*_queries.py and tests/test_statistics.py drive these
methods against the real datasets (BDD given/when/then).
Spec reference: TASK.md "Required Capabilities" sections 1-5, "Sample
Questions and Expected Behaviors", "Success Criteria".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls
from typing import Optional

from .loaders import MATCH_FILES, SoccerData
from .models import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COMPETITION_ALIASES,
    COPA_DO_BRASIL,
    LIBERTADORES,
    Match,
    Player,
    TeamRecord,
)
from .normalizer import DERBIES, TeamRef

# ---------------------------------------------------------------------------
# Position groups (for "show me all forwards" style queries)
# ---------------------------------------------------------------------------

POSITION_GROUPS: dict[str, set[str]] = {
    "goalkeeper": {"GK"},
    "gk": {"GK"},
    "defender": {"CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"},
    "def": {"CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"},
    "midfielder": {"CDM", "CM", "CAM", "LM", "RM", "LDM", "RDM", "LCM", "RCM",
                    "LAM", "RAM"},
    "mid": {"CDM", "CM", "CAM", "LM", "RM", "LDM", "RDM", "LCM", "RCM",
             "LAM", "RAM"},
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
    "fwd": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
    "attacker": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
    "striker": {"ST", "CF", "LS", "RS"},
    "winger": {"LW", "RW", "LF", "RF"},
}

LEAGUE_COMPETITIONS = {BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C}
CUP_COMPETITIONS = {COPA_DO_BRASIL, LIBERTADORES}


@dataclass
class MatchSearchResult:
    matches: list[Match]
    total: int
    team: Optional[TeamRef] = None
    opponent: Optional[TeamRef] = None
    truncated: bool = False


@dataclass
class HeadToHead:
    team_a: TeamRef
    team_b: TeamRef
    matches: list[Match]
    a_wins: int = 0
    b_wins: int = 0
    draws: int = 0
    a_goals: int = 0
    b_goals: int = 0
    competition: Optional[str] = None
    season: Optional[int] = None


@dataclass
class TeamStats:
    team: TeamRef
    record: TeamRecord
    season: Optional[int] = None
    competition: Optional[str] = None
    venue: str = "all"
    home_record: Optional[TeamRecord] = None
    away_record: Optional[TeamRecord] = None


@dataclass
class Standings:
    competition: str
    season: Optional[int]
    table: list[TeamRecord]
    source: str = ""

    @property
    def champion(self) -> Optional[TeamRecord]:
        return self.table[0] if self.table else None


@dataclass
class CompetitionStats:
    competition: Optional[str]
    season: Optional[int]
    matches: int = 0
    goals: int = 0
    home_wins: int = 0
    draws: int = 0
    away_wins: int = 0

    @property
    def avg_goals(self) -> Optional[float]:
        return round(self.goals / self.matches, 2) if self.matches else None

    @property
    def home_win_rate(self) -> Optional[float]:
        return round(100 * self.home_wins / self.matches, 1) if self.matches else None

    @property
    def draw_rate(self) -> Optional[float]:
        return round(100 * self.draws / self.matches, 1) if self.matches else None

    @property
    def away_win_rate(self) -> Optional[float]:
        return round(100 * self.away_wins / self.matches, 1) if self.matches else None


@dataclass
class SquadResult:
    team: TeamRef
    players: list[Player]
    fifa_clubs: list[str] = field(default_factory=list)
    in_fifa: bool = True


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SoccerService:
    """All query capabilities required by TASK.md, in one place."""

    def __init__(self, data: SoccerData) -> None:
        self.data = data
        self.registry = data.registry

    # -- helpers -------------------------------------------------------------

    def resolve_competition(self, name: Optional[str]) -> Optional[str]:
        """Map user input ("brasileirao", "Serie A", ...) to canonical name.

        Idempotent: a canonical name round-trips to itself (a naive
        substring match would turn "Brasileirão Série B" into Série A via
        the "brasileirão" alias).
        """
        if not name:
            return None
        from .normalizer import strip_accents

        raw = name.strip()
        key = raw.lower()
        canonicals = set(COMPETITION_ALIASES.values())

        # 1. exact canonical / alias match
        if raw in canonicals:
            return raw
        if key in COMPETITION_ALIASES:
            return COMPETITION_ALIASES[key]

        # 2. exact match modulo accents/case ("BRASILEIRAO SERIE B")
        flat = strip_accents(key)
        for canonical in canonicals:
            if strip_accents(canonical.lower()) == flat:
                return canonical

        # 3. fuzzy containment, longest alias wins ("campeonato" -> A)
        best: Optional[tuple[str, str]] = None
        for alias, canonical in COMPETITION_ALIASES.items():
            if alias in key or key in alias:
                if best is None or len(alias) > len(best[0]):
                    best = (alias, canonical)
        if best:
            return best[1]

        # 4. canonical containment ("libertadores da america")
        for canonical in sorted(canonicals, key=len, reverse=True):
            flat_canonical = strip_accents(canonical.lower())
            if flat in flat_canonical or flat_canonical in flat:
                return canonical

        raise ValueError(
            f"Unknown competition '{name}'. Known: Brasileirão Série A/B/C, "
            "Copa do Brasil, Copa Libertadores."
        )

    def resolve_team(self, query: str) -> TeamRef:
        return self.registry.resolve(query)

    def _team_matches(self, team_id: str) -> list[Match]:
        return self.data.matches_by_team.get(team_id, [])

    def primary_source(self, competition: str, season: Optional[int]) -> Optional[str]:
        """The single most authoritative source for (competition, season).

        Priority-first: the first source (in MATCH_FILES authority order)
        that recorded this competition+season wins. A pure max-match-count
        rule would misfire where a lower-authority file over-reports (e.g.
        BR-Football files 491 rows under "2021 Série A" because it labels
        season-2020 tail matches played in Jan/Feb 2021 by calendar year).
        """
        counts = self.data.source_counts_by_season.get((competition, season))
        if not counts:
            return None
        for source in MATCH_FILES:
            if source in counts:
                return source
        return next(iter(counts))

    def primary_matches(self, competition: str, season: Optional[int]) -> list[Match]:
        """Matches for one competition+season from one authoritative source."""
        source = self.primary_source(competition, season)
        if source is None:
            return []
        return [
            m
            for m in self.data.matches
            if m.competition == competition and m.season == season and m.source == source
        ]

    def _aggregation_matches(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> list[Match]:
        """Match set for aggregate queries: single-source when fully pinned."""
        if competition and season is not None:
            return self.primary_matches(competition, season)
        result = self.data.matches
        if competition:
            result = [m for m in result if m.competition == competition]
        if season is not None:
            result = [m for m in result if m.season == season]
        return result

    @staticmethod
    def _parse_bound(value: Optional[str]) -> Optional[date_cls]:
        if value is None or not str(value).strip():
            return None
        from .loaders import parse_date

        parsed = parse_date(str(value))
        if parsed is None:
            raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD.")
        return parsed

    # ------------------------------------------------------------------
    # Competition meta
    # ------------------------------------------------------------------

    def competitions(self) -> list[str]:
        seen: set[str] = set()
        for match in self.data.matches:
            seen.add(match.competition)
        return sorted(seen)

    def seasons(self, competition: Optional[str] = None) -> list[int]:
        comp = self.resolve_competition(competition) if competition else None
        seasons: set[int] = set()
        for match in self.data.matches:
            if comp is None or match.competition == comp:
                if match.season is not None:
                    seasons.add(match.season)
        return sorted(seasons)

    # ------------------------------------------------------------------
    # Match queries (TASK.md section 1)
    # ------------------------------------------------------------------

    def search_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        stage: Optional[str] = None,
        limit: int = 30,
    ) -> MatchSearchResult:
        """Find matches by team, opponent, competition, season, date range, stage."""
        team_ref = self.resolve_team(team) if team else None
        opp_ref = self.resolve_team(opponent) if opponent else None
        comp = self.resolve_competition(competition) if competition else None
        lo = self._parse_bound(date_from)
        hi = self._parse_bound(date_to)

        pool = self._aggregation_matches(comp, season) if comp else self.data.matches
        if not comp and season is not None:
            pool = [m for m in pool if m.season == season]
        if stage:
            stage_l = stage.strip().lower()
            pool = [m for m in pool if m.stage and m.stage.lower() == stage_l]

        selected: list[Match] = []
        for m in pool:
            if team_ref and opp_ref:
                if not (
                    {m.home_id, m.away_id} == {team_ref.team_id, opp_ref.team_id}
                ):
                    continue
            elif team_ref:
                if team_ref.team_id not in (m.home_id, m.away_id):
                    continue
            elif opp_ref:
                if opp_ref.team_id not in (m.home_id, m.away_id):
                    continue
            if lo and (m.date is None or m.date < lo):
                continue
            if hi and (m.date is None or m.date > hi):
                continue
            selected.append(m)

        selected.sort(key=lambda m: (m.date is None, m.date or date_cls.min))
        total = len(selected)
        shown = selected[-limit:] if limit and limit > 0 else selected
        return MatchSearchResult(
            matches=shown,
            total=total,
            team=team_ref,
            opponent=opp_ref,
            truncated=total > len(shown),
        )

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> HeadToHead:
        """Head-to-head record between two teams (TASK.md sections 1-2)."""
        a = self.resolve_team(team_a)
        b = self.resolve_team(team_b)
        comp = self.resolve_competition(competition) if competition else None

        pool = self._aggregation_matches(comp, season) if comp else self.data.matches
        if not comp and season is not None:
            pool = [m for m in pool if m.season == season]

        result = HeadToHead(team_a=a, team_b=b, matches=[], competition=comp, season=season)
        for m in pool:
            if {m.home_id, m.away_id} != {a.team_id, b.team_id}:
                continue
            result.matches.append(m)
            if not m.played():
                continue
            a_home = m.home_id == a.team_id
            a_goals, b_goals = (
                (m.home_goals, m.away_goals) if a_home else (m.away_goals, m.home_goals)
            )
            result.a_goals += a_goals
            result.b_goals += b_goals
            if a_goals > b_goals:
                result.a_wins += 1
            elif b_goals > a_goals:
                result.b_wins += 1
            else:
                result.draws += 1
        result.matches.sort(key=lambda m: (m.date is None, m.date or date_cls.min))
        return result

    def derby_matches(
        self,
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> list[tuple[str, Match]]:
        """Matches between famous rival pairs (see normalizer.DERBIES)."""
        comp = self.resolve_competition(competition) if competition else None
        derby_map: dict[frozenset[str], str] = {
            frozenset((a, b)): name for a, b, name in DERBIES
        }
        out: list[tuple[str, Match]] = []
        for m in self.data.matches:
            if season is not None and m.season != season:
                continue
            if comp and m.competition != comp:
                continue
            name = derby_map.get(frozenset((m.home_id, m.away_id)))
            if name:
                out.append((name, m))
        out.sort(key=lambda item: (item[1].date is None, item[1].date or date_cls.min))
        return out

    def finals(self, competition: str, season: Optional[int] = None) -> list[Match]:
        """Final-stage matches of a cup competition for the given season(s).

        * Copa Libertadores: matches whose recorded stage is "final".
        * Copa do Brasil: when round numbers exist, the highest round of a
          season is the final (verified: 2 matches in 2012-2020). When the
          round data is missing or clearly truncated (2021 stops at round 4
          with 16 matches), fall back to the LAST played matches by date -
          the final legs are always a season's latest games (works for the
          BR-Football-only seasons 2022/2023 and for 2021).
        * League competitions have no finals - returns [].
        """
        comp = self.resolve_competition(competition)

        if comp == LIBERTADORES:
            pool = [m for m in self.data.matches if m.competition == comp]
            if season is not None:
                pool = [m for m in pool if m.season == season]
            finals = [m for m in pool if (m.stage or "").lower() == "final"]
            finals.sort(key=lambda m: (m.date is None, m.date or date_cls.min))
            return finals

        if comp == COPA_DO_BRASIL:
            pool = [m for m in self.data.matches if m.competition == comp]
            if season is not None:
                pool = [m for m in pool if m.season == season]

            def round_key(m: Match) -> int:
                try:
                    return int(str(m.round_no).strip())
                except (TypeError, ValueError):
                    return -1

            by_season: dict[int, list[Match]] = {}
            for m in pool:
                if m.season is not None:
                    by_season.setdefault(m.season, []).append(m)

            out: list[Match] = []
            for season_key in sorted(by_season):
                season_pool = by_season[season_key]
                with_rounds = [m for m in season_pool if round_key(m) > 0]
                found: list[Match] = []
                if with_rounds:
                    top_round = max(round_key(m) for m in with_rounds)
                    top_matches = [m for m in with_rounds if round_key(m) == top_round]
                    # a genuine final round stages at most a two-legged final
                    if len(top_matches) <= 4:
                        found = top_matches

                if not found:
                    # Fallback: latest played matches of the season (the
                    # final legs are always a season's last games).
                    played = sorted(
                        (m for m in season_pool if m.played()),
                        key=lambda m: (m.date is None, m.date or date_cls.min),
                    )
                    if not played:
                        continue
                    last_two = played[-2:]
                    if (
                        len(last_two) == 2
                        and {last_two[0].home_id, last_two[0].away_id}
                        == {last_two[1].home_id, last_two[1].away_id}
                    ):
                        found = last_two
                    else:
                        found = [played[-1]]
                out.extend(found)

            out.sort(key=lambda m: (m.date is None, m.date or date_cls.min))
            return out

        # leagues: no finals
        return []

    # ------------------------------------------------------------------
    # Team queries (TASK.md section 2)
    # ------------------------------------------------------------------

    def team_record(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",
    ) -> TeamStats:
        """Win/draw/loss + goals for one team, optionally season/competition/venue."""
        if venue not in ("all", "home", "away"):
            raise ValueError("venue must be 'all', 'home' or 'away'")
        ref = self.resolve_team(team)
        comp = self.resolve_competition(competition) if competition else None
        pool = self._aggregation_matches(comp, season)
        if not comp and season is not None:
            pool = [m for m in pool if m.season == season]

        overall = TeamRecord(team_id=ref.team_id, display=ref.display)
        home_rec = TeamRecord(team_id=ref.team_id, display=ref.display)
        away_rec = TeamRecord(team_id=ref.team_id, display=ref.display)
        for m in pool:
            if ref.team_id not in (m.home_id, m.away_id) or not m.played():
                continue
            is_home = m.home_id == ref.team_id
            gf, ga = (m.home_goals, m.away_goals) if is_home else (m.away_goals, m.home_goals)
            overall.add_match(is_home, gf, ga)
            (home_rec if is_home else away_rec).add_match(is_home, gf, ga)

        if venue == "home":
            record = home_rec
        elif venue == "away":
            record = away_rec
        else:
            record = overall
        return TeamStats(
            team=ref,
            record=record,
            season=season,
            competition=comp,
            venue=venue,
            home_record=home_rec,
            away_record=away_rec,
        )

    def team_overview(self, team: str) -> dict:
        """Everything we know about one team across ALL datasets (cross-file)."""
        ref = self.resolve_team(team)
        competitions: dict[str, list[int]] = {}
        overall = TeamRecord(team_id=ref.team_id, display=ref.display)
        for m in self._team_matches(ref.team_id):
            if m.season is not None:
                competitions.setdefault(m.competition, [])
                if m.season not in competitions[m.competition]:
                    competitions[m.competition].append(m.season)
            if m.played() and ref.team_id in (m.home_id, m.away_id):
                is_home = m.home_id == ref.team_id
                gf, ga = (
                    (m.home_goals, m.away_goals) if is_home else (m.away_goals, m.home_goals)
                )
                overall.add_match(is_home, gf, ga)

        squad = self.club_squad(ref.team_id, ref=ref)
        return {
            "team": ref,
            "variants": self.registry.variants(ref.team_id),
            "competitions": {
                comp: sorted(seasons) for comp, seasons in sorted(competitions.items())
            },
            "record": overall,
            "squad_size": len(squad.players),
            "squad_in_fifa": squad.in_fifa,
        }

    # ------------------------------------------------------------------
    # Competition queries (TASK.md section 4)
    # ------------------------------------------------------------------

    def standings(self, competition: str, season: Optional[int] = None) -> Standings:
        """League table calculated from match results.

        Tie-breaks follow the Brazilian rule: points, wins, goal difference,
        goals for.
        """
        comp = self.resolve_competition(competition)
        pool = self._aggregation_matches(comp, season)
        if not comp and season is not None:
            pool = [m for m in pool if m.season == season]

        records: dict[str, TeamRecord] = {}
        for m in pool:
            if not m.played():
                continue
            home = records.setdefault(
                m.home_id, TeamRecord(team_id=m.home_id, display=m.home_display)
            )
            away = records.setdefault(
                m.away_id, TeamRecord(team_id=m.away_id, display=m.away_display)
            )
            home.add_match(True, m.home_goals, m.away_goals)
            away.add_match(False, m.away_goals, m.home_goals)

        table = sorted(
            records.values(),
            key=lambda r: (
                -r.points, -r.wins, -(r.goals_for - r.goals_against), -r.goals_for, r.display
            ),
        )
        source = self.primary_source(comp, season) or ""
        return Standings(competition=comp, season=season, table=table, source=source)

    def champion(self, competition: str, season: Optional[int] = None) -> str:
        """Who won the competition+season; formatted answer (cup finals aware)."""
        comp = self.resolve_competition(competition)
        if comp in LEAGUE_COMPETITIONS:
            table = self.standings(comp, season).table
            if not table:
                return f"No matches found for {comp} {season or ''}".strip()
            top = table[0]
            lines = [
                f"{season or ''} {comp} champion (calculated from matches): "
                f"{top.display} - {top.points} pts "
                f"({top.wins}W, {top.draws}D, {top.losses}L)".replace("  ", " ")
            ]
            runner = table[1] if len(table) > 1 else None
            if runner:
                lines.append(
                    f"Runner-up: {runner.display} - {runner.points} pts "
                    f"({runner.wins}W, {runner.draws}D, {runner.losses}L)"
                )
            return "\n".join(lines)

        # Cup competitions: decide from the final(s)
        final_matches = self.finals(comp, season)
        played = [m for m in final_matches if m.played()]
        if not played:
            return (
                f"No final matches found for {comp} "
                f"{season or ''} in the dataset.".strip().replace("  ", " ")
            )

        teams: dict[str, dict] = {}
        for m in played:
            teams.setdefault(m.home_id, {"display": m.home_display, "gf": 0, "ga": 0})
            teams.setdefault(m.away_id, {"display": m.away_display, "gf": 0, "ga": 0})
            teams[m.home_id]["gf"] += m.home_goals
            teams[m.home_id]["ga"] += m.away_goals
            teams[m.away_id]["gf"] += m.away_goals
            teams[m.away_id]["ga"] += m.home_goals

        lines = [f"{str(season or '').strip()} {comp} final(s):".strip()]
        for m in played:
            lines.append(
                f"- {m.date_str()}: {m.home_display} {m.score_str()} {m.away_display}"
            )

        ranked = sorted(
            teams.items(), key=lambda kv: (-kv[1]["gf"], kv[1]["display"])
        )
        a, b = ranked[0][1], ranked[1][1]
        if a["gf"] > b["gf"]:
            verdict = (
                f"Aggregate: {a['display']} {a['gf']}-{b['gf']} {b['display']} -> "
                f"Champion: {a['display']}"
            )
        else:
            verdict = (
                f"Aggregate tied {a['gf']}-{b['gf']} between {a['display']} and "
                f"{b['display']}; the tie was decided on penalties/away goals, "
                "which the dataset does not record."
            )
        return "\n".join(lines + [verdict])

    def relegated(
        self, competition: str, season: Optional[int] = None, n: int = 4
    ) -> list[TeamRecord]:
        """Bottom-N of the league table."""
        table = self.standings(competition, season).table
        return list(reversed(table[-n:])) if table else []

    # ------------------------------------------------------------------
    # Player queries (TASK.md section 3)
    # ------------------------------------------------------------------

    @staticmethod
    def _positions_for(position: Optional[str]) -> Optional[set[str]]:
        if not position:
            return None
        key = position.strip().lower()
        if key in POSITION_GROUPS:
            return POSITION_GROUPS[key]
        upper = position.strip().upper()
        known = set().union(*POSITION_GROUPS.values())
        if upper in known:
            return {upper}
        raise ValueError(
            f"Unknown position '{position}'. Use a FIFA position code "
            "(e.g. ST, CAM, CB, GK) or a group (forward, midfielder, defender, goalkeeper)."
        )

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        max_age: Optional[int] = None,
        order: str = "overall",
        limit: int = 20,
    ) -> list[Player]:
        """Search FIFA players by name, nationality, club, position, ratings."""
        positions = self._positions_for(position)
        name_l = name.strip().lower() if name else None
        nat_l = nationality.strip().lower() if nationality else None
        club_l = club.strip().lower() if club else None
        if order not in ("overall", "potential", "age", "name"):
            raise ValueError("order must be one of: overall, potential, age, name")

        found: list[Player] = []
        for p in self.data.players:
            if name_l and name_l not in p.name.lower():
                continue
            if nat_l and nat_l not in p.nationality.lower():
                continue
            if club_l and club_l not in p.club.lower():
                continue
            if positions and p.position not in positions:
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            if max_overall is not None and (p.overall is None or p.overall > max_overall):
                continue
            if max_age is not None and (p.age is None or p.age > max_age):
                continue
            found.append(p)

        def sort_key(p: Player):
            if order == "overall":
                return (-(p.overall or 0), p.name)
            if order == "potential":
                return (-(p.potential or 0), p.name)
            if order == "age":
                return (p.age if p.age is not None else 999, p.name)
            return (p.name,)

        found.sort(key=sort_key)
        return found[:limit] if limit and limit > 0 else found

    def player_profile(self, name: str) -> Player:
        """Full profile for the best name match (exact, then substring)."""
        needle = name.strip().lower()
        for p in self.data.players:
            if p.name.lower() == needle:
                return p
        substring = [p for p in self.data.players if needle in p.name.lower()]
        if not substring:
            raise LookupError(
                f"No player found matching '{name}'. Try another spelling."
            )
        substring.sort(key=lambda p: (-(p.overall or 0), p.name))
        return substring[0]

    def club_squad(self, club: str, ref: Optional[TeamRef] = None) -> SquadResult:
        """FIFA squad for a club; bridges match-data teams to FIFA clubs."""
        team_ref = ref or self.resolve_team(club)
        fifa_clubs = self.data.fifa_clubs_by_team.get(team_ref.team_id, [])
        players: list[Player] = []
        for raw_club in fifa_clubs:
            players.extend(self.data.players_by_club.get(raw_club, []))
        players.sort(key=lambda p: (-(p.overall or 0), p.name))
        return SquadResult(
            team=team_ref, players=players, fifa_clubs=fifa_clubs, in_fifa=bool(players)
        )

    def top_brazilian_players(self, limit: int = 10) -> list[Player]:
        return self.search_players(nationality="Brazil", order="overall", limit=limit)

    def brazilians_at_brazilian_clubs(self, limit: int = 15) -> list[tuple[str, int, float]]:
        """(club display, count, avg overall) for Brazilians at Brazilian clubs."""
        rows: list[tuple[str, int, float]] = []
        for team_id, clubs in self.data.fifa_clubs_by_team.items():
            # a "Brazilian club" here = a club that also appears in the match data
            if team_id not in self.data.matches_by_team:
                continue
            display = self.registry.display(team_id)
            players = [
                p
                for raw in clubs
                for p in self.data.players_by_club.get(raw, [])
                if p.is_brazilian
            ]
            if not players:
                continue
            avg = round(sum(p.overall or 0 for p in players) / len(players), 1)
            rows.append((display, len(players), avg))
        rows.sort(key=lambda row: (-row[1], -row[2]))
        return rows[:limit] if limit else rows

    # ------------------------------------------------------------------
    # Statistical analysis (TASK.md section 5)
    # ------------------------------------------------------------------

    def competition_stats(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> CompetitionStats:
        comp = self.resolve_competition(competition) if competition else None
        pool = self._aggregation_matches(comp, season)
        if not comp and season is not None:
            pool = [m for m in pool if m.season == season]

        stats = CompetitionStats(competition=comp, season=season)
        for m in pool:
            if not m.played():
                continue
            stats.matches += 1
            stats.goals += m.total_goals() or 0
            winner = m.winner()
            if winner == "home":
                stats.home_wins += 1
            elif winner == "away":
                stats.away_wins += 1
            else:
                stats.draws += 1
        return stats

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> list[Match]:
        comp = self.resolve_competition(competition) if competition else None
        pool = self._aggregation_matches(comp, season)
        if not comp and season is not None:
            pool = [m for m in pool if m.season == season]
        played = [m for m in pool if m.played()]
        played.sort(
            key=lambda m: (-(m.margin() or 0), -(m.total_goals() or 0), m.date or date_cls.min)
        )
        return played[:limit] if limit and limit > 0 else played

    def best_records(
        self,
        venue: str = "home",
        competition: Optional[str] = None,
        season: Optional[int] = None,
        min_matches: int = 10,
        limit: int = 10,
    ) -> list[TeamRecord]:
        """Teams with the best win rate at a venue (home or away)."""
        if venue not in ("home", "away"):
            raise ValueError("venue must be 'home' or 'away'")
        comp = self.resolve_competition(competition) if competition else None
        pool = self._aggregation_matches(comp, season)
        if not comp and season is not None:
            pool = [m for m in pool if m.season == season]

        records: dict[str, TeamRecord] = {}
        for m in pool:
            if not m.played():
                continue
            if venue == "home":
                team_id, display, gf, ga = m.home_id, m.home_display, m.home_goals, m.away_goals
            else:
                team_id, display, gf, ga = m.away_id, m.away_display, m.away_goals, m.home_goals
            rec = records.setdefault(team_id, TeamRecord(team_id=team_id, display=display))
            rec.add_match(venue == "home", gf, ga)
        eligible = [r for r in records.values() if r.matches >= min_matches]
        eligible.sort(key=lambda r: (-r.win_rate, -r.matches))
        return eligible[:limit] if limit and limit > 0 else eligible

    def compare_seasons(self, competition: str, season_a: int, season_b: int) -> str:
        """Side-by-side aggregate comparison of two seasons of a competition."""
        comp = self.resolve_competition(competition)
        stats_a = self.competition_stats(comp, season_a)
        stats_b = self.competition_stats(comp, season_b)

        def champ_line(season: int) -> str:
            if comp in LEAGUE_COMPETITIONS:
                table = self.standings(comp, season).table
                if table:
                    return f"{table[0].display} ({table[0].points} pts)"
            return "n/a"

        lines = [
            f"Comparison: {comp} {season_a} vs {season_b}",
            f"Matches: {stats_a.matches} vs {stats_b.matches}",
            f"Average goals/match: {stats_a.avg_goals} vs {stats_b.avg_goals}",
            f"Home win rate: {stats_a.home_win_rate}% vs {stats_b.home_win_rate}%",
            f"Draw rate: {stats_a.draw_rate}% vs {stats_b.draw_rate}%",
            f"Away win rate: {stats_a.away_win_rate}% vs {stats_b.away_win_rate}%",
            f"Champion: {champ_line(season_a)} vs {champ_line(season_b)}",
        ]
        big_a = self.biggest_wins(comp, season_a, 1)
        big_b = self.biggest_wins(comp, season_b, 1)
        if big_a:
            m = big_a[0]
            lines.append(
                f"Biggest win {season_a}: {m.home_display} {m.score_str()} {m.away_display}"
            )
        if big_b:
            m = big_b[0]
            lines.append(
                f"Biggest win {season_b}: {m.home_display} {m.score_str()} {m.away_display}"
            )
        return "\n".join(lines)
