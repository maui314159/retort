"""Query engine implementing all required capability categories.

The engine is pure logic with no MCP dependency: match queries, team
queries, player queries, competition queries (including calculated
standings) and statistical analysis over the loaded datasets.
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from brazilian_soccer_mcp.derbies import DERBIES, Derby, find_derby
from brazilian_soccer_mcp.loader import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    LIBERTADORES,
    LoadedData,
    SOURCE_BR_FOOTBALL,
    SOURCE_BRASILEIRAO,
    SOURCE_CUP,
    SOURCE_FIFA,
    SOURCE_LIBERTADORES,
    SOURCE_NOVO,
    load_data,
    parse_date,
)
from brazilian_soccer_mcp.models import (
    CompetitionStats,
    HeadToHead,
    Match,
    Player,
    StandingRow,
    TeamStats,
)
from brazilian_soccer_mcp.normalize import (
    TeamNotFoundError,
    clean_name,
    strip_accents,
)

ALL_COMPETITIONS = [BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C, COPA_DO_BRASIL, LIBERTADORES]

COMPETITION_ALIASES = {
    "brasileirao": [BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C],
    "campeonato brasileiro": [BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C],
    "brasileirao serie a": [BRASILEIRAO_A],
    "serie a": [BRASILEIRAO_A],
    "a serie": [BRASILEIRAO_A],
    "brasileirao serie b": [BRASILEIRAO_B],
    "serie b": [BRASILEIRAO_B],
    "b serie": [BRASILEIRAO_B],
    "brasileirao serie c": [BRASILEIRAO_C],
    "serie c": [BRASILEIRAO_C],
    "c serie": [BRASILEIRAO_C],
    "copa do brasil": [COPA_DO_BRASIL],
    "brazilian cup": [COPA_DO_BRASIL],
    "copa": [COPA_DO_BRASIL],
    "cup": [COPA_DO_BRASIL],
    "cdb": [COPA_DO_BRASIL],
    "libertadores": [LIBERTADORES],
    "copa libertadores": [LIBERTADORES],
    "libertadores cup": [LIBERTADORES],
    "conmebol libertadores": [LIBERTADORES],
}

POSITION_GROUPS = {
    "GK": {"GK"},
    "DEF": {"LB", "LWB", "RB", "RWB", "CB", "LCB", "RCB"},
    "MID": {"CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"},
    "FWD": {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"},
}

POSITION_WORDS = {
    "gk": "GK", "goalkeeper": "GK", "keeper": "GK", "goleiro": "GK",
    "def": "DEF", "defender": "DEF", "defense": "DEF",
    "zagueiro": "DEF", "back": "DEF", "fullback": "DEF",
    "mid": "MID", "midfielder": "MID", "midfield": "MID", "meia": "MID",
    "fw": "FWD", "fwd": "FWD", "forward": "FWD", "forwards": "FWD",
    "striker": "FWD", "attacker": "FWD", "winger": "FWD", "atacante": "FWD",
    "center forward": "FWD",
}

NATIONALITY_WORD_MAP = {
    "brazilian": "brazil",
    "argentinian": "argentina",
    "argentine": "argentina",
    "english": "england",
    "spanish": "spain",
    "french": "france",
    "german": "germany",
    "italian": "italy",
    "portuguese": "portugal",
    "dutch": "netherlands",
    "colombian": "colombia",
    "uruguayan": "uruguay",
    "chilean": "chile",
    "mexican": "mexico",
    "american": "united states",
}

_STAGE_ALIASES = {
    "final": "final",
    "finals": "final",
    "finals (both legs)": "final",
    "semi": "semifinals",
    "semifinal": "semifinals",
    "semifinals": "semifinals",
    "semi final": "semifinals",
    "quarter": "quarterfinals",
    "quarterfinal": "quarterfinals",
    "quarterfinals": "quarterfinals",
    "quarter final": "quarterfinals",
    "round of 16": "round of 16",
    "r16": "round of 16",
    "octavos": "round of 16",
    "group": "group stage",
    "groups": "group stage",
    "group stage": "group stage",
    "phase de groupe": "group stage",
}

_CUP_STAGE_OFFSETS = {
    "final": 0,
    "semifinals": 1,
    "quarterfinals": 2,
    "round of 16": 3,
}


class QueryError(ValueError):
    """Raised for invalid or unanswerable queries."""


@dataclass(slots=True)
class MatchSearchResult:
    matches: list[Match]
    total: int
    team_key: Optional[str] = None
    team_display: Optional[str] = None
    opponent_key: Optional[str] = None
    opponent_display: Optional[str] = None
    competition_note: Optional[str] = None
    stage_note: Optional[str] = None


@dataclass(slots=True)
class StandingsResult:
    competition: str
    season: Optional[int]
    rows: list[StandingRow]
    played: int
    expected: int
    complete: bool
    champion: Optional[str] = None
    relegated: list[str] = field(default_factory=list)
    note: Optional[str] = None


@dataclass(slots=True)
class TeamInfo:
    key: str
    display: str
    variants: list[str]
    siblings: list[str]
    match_count: int
    first_match: Optional[date]
    last_match: Optional[date]
    competitions: dict
    player_count: int
    avg_player_rating: Optional[float]


@dataclass(slots=True)
class DerbyResult:
    derby: Derby
    matches: list[Match]
    total: int
    team_a_wins: int
    team_b_wins: int
    draws: int
    team_a_display: str = ""
    team_b_display: str = ""
    note: Optional[str] = None


class QueryEngine:
    """All supported queries over the loaded Brazilian soccer data."""

    def __init__(self, data: LoadedData):
        self._data = data
        self._matches: list[Match] = data.matches
        self._players: list[Player] = data.players
        self._registry = data.registry
        self._primary = data.primary_sources
        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        for player in self._players:
            if player.club_key:
                self._players_by_club[player.club_key].append(player)
        self._club_displays: set[str] = {
            player.club_display for player in self._players if player.club_display
        }
        self._cup_final_rounds: dict[int, Optional[int]] = {}
        self._league_trim_drops: dict[tuple[str, Optional[int]], frozenset] = {}
        self._source_labels = {
            SOURCE_BRASILEIRAO: "Brasileirao_Matches.csv",
            SOURCE_CUP: "Brazilian_Cup_Matches.csv",
            SOURCE_LIBERTADORES: "Libertadores_Matches.csv",
            SOURCE_BR_FOOTBALL: "BR-Football-Dataset.csv",
            SOURCE_NOVO: "novo_campeonato_brasileiro.csv",
            SOURCE_FIFA: "fifa_data.csv",
        }

    @property
    def registry(self):
        return self._registry

    @property
    def matches(self) -> list[Match]:
        return self._matches

    @property
    def players(self) -> list[Player]:
        return self._players

    def resolve_team(self, name: str) -> tuple[str, str]:
        return self._registry.resolve(name)

    def _resolve_competition(self, competition: Optional[str]) -> tuple[list[str], Optional[str]]:
        if competition is None or not str(competition).strip():
            return list(ALL_COMPETITIONS), None
        cleaned = clean_name(competition)
        if cleaned in COMPETITION_ALIASES:
            return COMPETITION_ALIASES[cleaned], None
        for alias, comps in COMPETITION_ALIASES.items():
            if cleaned and (alias in cleaned or cleaned in alias) and len(cleaned) >= 4:
                return comps, None
        raise QueryError(
            f"Unknown competition: {competition!r}. Known competitions: "
            + ", ".join(ALL_COMPETITIONS)
        )

    def competition_label(self, competition: Optional[str]) -> Optional[str]:
        """Display label for a competition filter, noting division expansion."""
        if competition is None or not str(competition).strip():
            return None
        comps, _ = self._resolve_competition(competition)
        if len(comps) > 1:
            return f"{comps[0].rsplit(' ', 1)[0]} (all divisions: {', '.join(comps)})"
        return comps[0]

    def _is_primary(self, match: Match) -> bool:
        source = self._primary.get((match.competition, match.season))
        return source is None or match.source == source

    def _league_trimmed_drop_set(self, competition: str, season: Optional[int]) -> frozenset:
        """Indices of primary matches to drop from league seasons with excess
        pair meetings.

        Série A and Série B are strict double round-robin competitions.  Some
        source files mislabel Copa do Brasil fixtures as league matches, which
        makes a pair of teams meet three or more times.  For affected seasons
        at most two matches per pair are kept, preferring venue balance and
        the earliest legs.  `all_sources=True` bypasses this view.
        """
        from brazilian_soccer_mcp.loader import BRASILEIRAO_A, BRASILEIRAO_B

        key = (competition, season)
        if key in self._league_trim_drops:
            return self._league_trim_drops[key]
        drops: set = set()
        if competition in (BRASILEIRAO_A, BRASILEIRAO_B):
            pairs: dict[frozenset, list[tuple[int, Match]]] = defaultdict(list)
            for index, match in enumerate(self._matches):
                if (
                    match.competition == competition
                    and match.season == season
                    and self._is_primary(match)
                ):
                    pairs[frozenset((match.home_key, match.away_key))].append((index, match))
            for items in pairs.values():
                if len(items) <= 2:
                    continue
                items.sort(key=lambda im: (im[1].date or date.min,))
                keep: list[int] = []
                seen_home: set = set()
                for index, match in items:
                    if match.home_key not in seen_home:
                        keep.append(index)
                        seen_home.add(match.home_key)
                    if len(keep) == 2:
                        break
                drops.update(index for index, _ in items)
                drops.difference_update(keep)
        self._league_trim_drops[key] = frozenset(drops)
        return self._league_trim_drops[key]

    def _seasons_of(self, competition: str) -> set:
        seasons = set()
        for match in self._matches:
            if match.competition == competition and match.season is not None:
                seasons.add(match.season)
        return seasons

    def _league_trims(
        self, competitions: Optional[list[str]], season: Optional[int], all_sources: bool
    ) -> dict:
        from brazilian_soccer_mcp.loader import BRASILEIRAO_A, BRASILEIRAO_B

        if all_sources:
            return {}
        trims: dict[tuple[str, Optional[int]], frozenset] = {}
        targets = competitions if competitions is not None else ALL_COMPETITIONS
        for competition in targets:
            if competition not in (BRASILEIRAO_A, BRASILEIRAO_B):
                continue
            seasons = {season} if season is not None else self._seasons_of(competition)
            for candidate in seasons:
                drops = self._league_trimmed_drop_set(competition, candidate)
                if drops:
                    trims[(competition, candidate)] = drops
        return trims

    def _iter_matches(
        self,
        competitions: Optional[list[str]] = None,
        season: Optional[int] = None,
        all_sources: bool = False,
        played_only: bool = False,
    ):
        league_trims = self._league_trims(competitions, season, all_sources)
        for index, match in enumerate(self._matches):
            if competitions is not None and match.competition not in competitions:
                continue
            if season is not None and match.season != season:
                continue
            if not all_sources and not self._is_primary(match):
                continue
            if index in league_trims.get((match.competition, match.season), ()):
                continue
            if played_only and not match.played:
                continue
            yield match

    def _cup_final_round(self, season: Optional[int]) -> Optional[int]:
        if season in self._cup_final_rounds:
            return self._cup_final_rounds[season]
        rounds: Counter = Counter()
        for match in self._matches:
            if (
                match.competition == COPA_DO_BRASIL
                and match.season == season
                and match.source == SOURCE_CUP
                and match.round
            ):
                try:
                    rounds[int(match.round)] += 1
                except ValueError:
                    continue
        final_round = None
        if rounds:
            max_round = max(rounds)
            if rounds[max_round] <= 2:
                final_round = max_round
        self._cup_final_rounds[season] = final_round
        return final_round

    def _stage_rounds_for_cup(self, season: Optional[int]) -> dict[str, str]:
        final_round = self._cup_final_round(season)
        if final_round is None:
            return {}
        return {
            stage: str(final_round - offset)
            for stage, offset in _CUP_STAGE_OFFSETS.items()
        }

    def _match_stage(self, match: Match) -> Optional[str]:
        if match.competition == LIBERTADORES:
            return match.stage
        if match.competition == COPA_DO_BRASIL and match.round:
            rounds = self._stage_rounds_for_cup(match.season)
            for stage, round_label in rounds.items():
                if match.round == round_label:
                    return stage
        return None

    def _apply_stage_filter(self, matches: list[Match], stage: Optional[str]):
        if stage is None:
            return matches, None
        normalized = _STAGE_ALIASES.get(clean_name(stage), clean_name(stage))
        filtered = []
        supports_stage = {LIBERTADORES, COPA_DO_BRASIL}
        for match in matches:
            if match.competition == LIBERTADORES:
                if clean_name(match.stage or "") == normalized:
                    filtered.append(match)
            elif match.competition == COPA_DO_BRASIL:
                rounds = self._stage_rounds_for_cup(match.season)
                target = rounds.get(normalized)
                if target is not None and match.round == target:
                    filtered.append(match)
        stage_note = None
        if not filtered:
            stage_capable = [m for m in matches if m.competition in supports_stage]
            if stage_capable:
                stage_note = f"No '{stage}' stage matches found within these filters."
            else:
                stage_note = (
                    f"No '{stage}' stage matches: stage filters apply to "
                    f"{LIBERTADORES} and {COPA_DO_BRASIL}."
                )
        return filtered, stage_note

    def search_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        stage: Optional[str] = None,
        venue: Optional[str] = None,
        limit: int = 20,
        all_sources: bool = False,
    ) -> MatchSearchResult:
        """Search matches by team, opponent, competition, season, date and stage."""
        if team is None and opponent is not None:
            team, opponent = opponent, None
        team_key = team_display = opponent_key = opponent_display = None
        if team is not None:
            team_key, team_display = self._registry.resolve(team)
        if opponent is not None:
            opponent_key, opponent_display = self._registry.resolve(opponent)
        competitions, comp_note = self._resolve_competition(competition)
        date_start = parse_date(date_from) if date_from else None
        date_end = parse_date(date_to) if date_to else None
        if date_from and date_start is None:
            raise QueryError(f"Invalid date_from: {date_from!r} (expected YYYY-MM-DD)")
        if date_to and date_end is None:
            raise QueryError(f"Invalid date_to: {date_to!r} (expected YYYY-MM-DD)")
        venue_norm = (venue or "").strip().lower() or None
        if venue_norm not in (None, "home", "away", "either", "any"):
            raise QueryError(f"Invalid venue: {venue!r} (use 'home' or 'away')")

        matches = []
        for match in self._iter_matches(competitions, season, all_sources):
            if team_key is not None:
                if team_key not in (match.home_key, match.away_key):
                    continue
                if venue_norm == "home" and match.home_key != team_key:
                    continue
                if venue_norm == "away" and match.away_key != team_key:
                    continue
            if opponent_key is not None:
                if opponent_key not in (match.home_key, match.away_key):
                    continue
                if {match.home_key, match.away_key} != {team_key, opponent_key}:
                    continue
            if date_start and (match.date is None or match.date < date_start):
                continue
            if date_end and (match.date is None or match.date > date_end):
                continue
            matches.append(match)

        matches, stage_note = self._apply_stage_filter(matches, stage)
        matches.sort(key=self._match_sort_key, reverse=True)
        total = len(matches)
        return MatchSearchResult(
            matches=matches[: max(0, limit)],
            total=total,
            team_key=team_key,
            team_display=team_display,
            opponent_key=opponent_key,
            opponent_display=opponent_display,
            competition_note=comp_note,
            stage_note=stage_note,
        )

    @staticmethod
    def _match_sort_key(match: Match):
        round_value = 0
        if match.round:
            try:
                round_value = int(match.round)
            except ValueError:
                round_value = 0
        return (
            match.date or date.min,
            round_value,
            match.competition,
        )

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> HeadToHead:
        """Head-to-head record between two teams."""
        key_a, display_a = self._registry.resolve(team_a)
        key_b, display_b = self._registry.resolve(team_b)
        if key_a == key_b:
            raise QueryError("Please provide two different teams.")
        competitions, _ = self._resolve_competition(competition)
        result = HeadToHead(
            team_a_key=key_a,
            team_a_display=display_a,
            team_b_key=key_b,
            team_b_display=display_b,
        )
        for match in self._iter_matches(competitions, season):
            if {match.home_key, match.away_key} != {key_a, key_b}:
                continue
            result.matches.append(match)
            if not match.played:
                continue
            if match.home_key == key_a:
                goals_a, goals_b = match.home_goals, match.away_goals
            else:
                goals_a, goals_b = match.away_goals, match.home_goals
            result.goals_a += goals_a
            result.goals_b += goals_b
            if goals_a > goals_b:
                result.team_a_wins += 1
            elif goals_b > goals_a:
                result.team_b_wins += 1
            else:
                result.draws += 1
        result.matches.sort(key=self._match_sort_key, reverse=True)
        if limit and len(result.matches) > limit:
            result.matches = result.matches[:limit]
        return result

    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: str = "all",
        all_sources: bool = False,
    ) -> TeamStats:
        """Win/draw/loss and goal statistics for one team."""
        key, display = self._registry.resolve(team)
        venue_norm = (venue or "all").strip().lower()
        if venue_norm not in ("all", "home", "away"):
            raise QueryError(f"Invalid venue: {venue!r} (use 'all', 'home' or 'away')")
        competitions, _ = self._resolve_competition(competition)
        stats = TeamStats(team_key=key, team_display=display)
        for match in self._iter_matches(competitions, season, all_sources, played_only=True):
            if key not in (match.home_key, match.away_key):
                continue
            is_home = match.home_key == key
            if venue_norm == "home" and not is_home:
                continue
            if venue_norm == "away" and is_home:
                continue
            stats.matches += 1
            goals_for = match.home_goals if is_home else match.away_goals
            goals_against = match.away_goals if is_home else match.home_goals
            stats.goals_for += goals_for
            stats.goals_against += goals_against
            if goals_for > goals_against:
                stats.wins += 1
            elif goals_for == goals_against:
                stats.draws += 1
            else:
                stats.losses += 1
        return stats

    def standings(
        self, season: Optional[int], competition: str = BRASILEIRAO_A
    ) -> StandingsResult:
        """League table calculated from match results for one season."""
        if season is None:
            raise QueryError("A season (year) is required for standings.")
        competitions, _ = self._resolve_competition(competition)
        note = None
        if len(competitions) > 1:
            competitions = [BRASILEIRAO_A]
            note = "Competition defaulted to Brasileirão Série A; pass e.g. 'Série B' for other divisions."
        target = competitions[0]
        if target == LIBERTADORES:
            raise QueryError(
                "Standings are only available for league competitions "
                "(Série A/B/C); the Libertadores is a knockout cup."
            )
        table: dict[str, dict] = {}
        played = 0
        for match in self._iter_matches([target], season, played_only=True):
            for key in (match.home_key, match.away_key):
                table.setdefault(
                    key,
                    {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0},
                )
            played += 1
            home = table[match.home_key]
            away = table[match.away_key]
            home["gf"] += match.home_goals
            home["ga"] += match.away_goals
            away["gf"] += match.away_goals
            away["ga"] += match.home_goals
            if match.home_goals > match.away_goals:
                home["w"] += 1
                away["l"] += 1
            elif match.home_goals < match.away_goals:
                away["w"] += 1
                home["l"] += 1
            else:
                home["d"] += 1
                away["d"] += 1
        if not table:
            raise QueryError(
                f"No played matches found for {target} in season {season}."
            )
        rows = []
        for key, entry in table.items():
            points = entry["w"] * 3 + entry["d"]
            rows.append(
                StandingRow(
                    position=0,
                    team_key=key,
                    team_display=self._registry.display_name(key),
                    matches=entry["w"] + entry["d"] + entry["l"],
                    wins=entry["w"],
                    draws=entry["d"],
                    losses=entry["l"],
                    goals_for=entry["gf"],
                    goals_against=entry["ga"],
                    points=points,
                )
            )
        rows.sort(
            key=lambda r: (r.points, r.wins, r.goal_difference, r.goals_for, r.team_display),
            reverse=True,
        )
        for index, row in enumerate(rows, start=1):
            row.position = index
        teams = len(rows)
        expected = teams * (teams - 1)
        complete = played >= expected
        champion = rows[0].team_display if complete else None
        relegated = [r.team_display for r in rows[-4:]] if teams == 20 else []
        if not complete:
            note = (
                f"Season incomplete in the data: {played} of ~{expected} matches played; "
                "the leader is shown, not a confirmed champion."
            )
        return StandingsResult(
            competition=target,
            season=season,
            rows=rows,
            played=played,
            expected=expected,
            complete=complete,
            champion=champion,
            relegated=relegated,
            note=note,
        )

    def competition_overview(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> list[dict]:
        """Overview of competitions: seasons, sources and match counts."""
        competitions, _ = self._resolve_competition(competition)
        overviews = []
        for target in ALL_COMPETITIONS:
            if target not in competitions:
                continue
            seasons: dict[int, Counter] = defaultdict(Counter)
            for match in self._iter_matches([target], season=None, all_sources=True):
                if match.season is not None:
                    seasons[match.season][match.source] += 1
            if not seasons:
                continue
            if season is not None and season not in seasons:
                continue
            sources = sorted(
                {s for counts in seasons.values() for s in counts}
            )
            season_list = sorted(seasons)
            match_count = 0
            primary_count = 0
            for match in self._iter_matches([target], season=season, all_sources=True):
                match_count += 1
                if self._is_primary(match):
                    primary_count += 1
            overviews.append(
                {
                    "competition": target,
                    "seasons": season_list,
                    "selected_season": season,
                    "matches": primary_count,
                    "total_rows": match_count,
                    "sources": [self._source_labels.get(s, s) for s in sources],
                }
            )
        return overviews

    def list_teams(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> list[tuple[str, int]]:
        """Teams present in a competition/season with match counts."""
        competitions, _ = self._resolve_competition(competition)
        counts: Counter = Counter()
        for match in self._iter_matches(competitions, season):
            counts[match.home_key] += 1
            counts[match.away_key] += 1
        return sorted(
            ((self._registry.display_name(key), count) for key, count in counts.items()),
            key=lambda item: (-item[1], item[0]),
        )

    def find_team(self, name: str) -> TeamInfo:
        """Resolve a team name and report its known variants and activity."""
        key, display = self._registry.resolve(name)
        team_matches = [
            m for m in self._matches if key in (m.home_key, m.away_key)
        ]
        dates = [m.date for m in team_matches if m.date]
        competitions = Counter(m.competition for m in team_matches)
        roster = self._players_by_club.get(key, [])
        avg_rating = None
        if roster:
            avg_rating = round(
                sum(p.overall for p in roster) / len(roster), 1
            )
        return TeamInfo(
            key=key,
            display=display,
            variants=self._registry.variants(key),
            siblings=[self._registry.display_name(k) for k in self._registry.sibling_keys(key)],
            match_count=len(team_matches),
            first_match=min(dates) if dates else None,
            last_match=max(dates) if dates else None,
            competitions=dict(competitions),
            player_count=len(roster),
            avg_player_rating=avg_rating,
        )

    def _resolve_club(self, club: str) -> Optional[str]:
        try:
            key, _ = self._registry.resolve(club)
            return key
        except TeamNotFoundError:
            pass
        cleaned = clean_name(club)
        if not cleaned:
            return None
        matches = [c for c in self._club_displays if cleaned in clean_name(c)]
        if len(matches) == 1:
            player = next(
                p for p in self._players if p.club_display == matches[0]
            )
            return player.club_key
        if len(matches) > 1:
            exact = [c for c in matches if clean_name(c) == cleaned]
            if len(exact) == 1:
                player = next(
                    p for p in self._players if p.club_display == exact[0]
                )
                return player.club_key
        raise TeamNotFoundError(club, sorted(matches)[:5])

    def _resolve_position(self, position: Optional[str]) -> Optional[set[str]]:
        if position is None or not str(position).strip():
            return None
        cleaned = clean_name(position)
        upper = cleaned.upper()
        all_positions = {p for group in POSITION_GROUPS.values() for p in group}
        if upper in all_positions:
            return {upper}
        group = POSITION_WORDS.get(cleaned)
        if group:
            return POSITION_GROUPS[group]
        raise QueryError(
            f"Unknown position: {position!r}. Use FIFA codes (ST, LW, CDM, GK, ...) "
            "or groups (goalkeeper, defender, midfielder, forward)."
        )

    @staticmethod
    def _nationality_keys(value: str) -> set[str]:
        cleaned = clean_name(value)
        keys = {cleaned}
        if cleaned in NATIONALITY_WORD_MAP:
            keys.add(NATIONALITY_WORD_MAP[cleaned])
        for suffix in ("ian", "ese", "ine"):
            if cleaned.endswith(suffix) and len(cleaned) > len(suffix) + 2:
                stem = cleaned[: -len(suffix)]
                keys.add(stem)
                keys.add(stem + "a")
        return keys

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        order_by: str = "overall",
        limit: int = 20,
    ) -> list[Player]:
        """Search the FIFA player database by name, nationality, club and position."""
        name_norm = None
        if name is not None and str(name).strip():
            name_norm = strip_accents(str(name)).lower().strip()
        nationality_keys = None
        if nationality is not None and str(nationality).strip():
            nationality_keys = self._nationality_keys(nationality)
        club_key = None
        if club is not None and str(club).strip():
            club_key = self._resolve_club(club)
        positions = self._resolve_position(position)
        order_field = (order_by or "overall").strip().lower()
        allowed_orders = {"overall", "potential", "age", "name"}
        if order_field not in allowed_orders:
            raise QueryError(
                f"Invalid order_by: {order_by!r}. Use one of {sorted(allowed_orders)}."
            )
        results = []
        for player in self._players:
            if name_norm is not None and name_norm not in player.name_norm:
                continue
            if nationality_keys is not None:
                player_keys = self._nationality_keys(player.nationality)
                if not nationality_keys & player_keys:
                    continue
            if club_key is not None and player.club_key != club_key:
                continue
            if positions is not None and player.position not in positions:
                continue
            if min_overall is not None and player.overall < min_overall:
                continue
            if max_overall is not None and player.overall > max_overall:
                continue
            results.append(player)
        if order_field == "name":
            results.sort(key=lambda p: p.name_norm)
        elif order_field == "age":
            results.sort(key=lambda p: (-(p.age or 0), -p.overall))
        else:
            results.sort(key=lambda p: (-getattr(p, order_field), p.name_norm))
        if name_norm is not None and not results:
            import difflib

            close = difflib.get_close_matches(
                name_norm, [p.name_norm for p in self._players], n=5, cutoff=0.5
            )
            raise TeamNotFoundError(
                name,
                [
                    next(p.name for p in self._players if p.name_norm == c)
                    for c in close
                ],
            )
        if limit is not None:
            results = results[: max(0, limit)]
        return results

    def club_players(self, club: str) -> list[Player]:
        """Full roster of a club from the FIFA database, by rating."""
        return self.search_players(club=club, order_by="overall", limit=None)

    def statistics(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        all_sources: bool = False,
    ) -> CompetitionStats:
        """Aggregate statistics: goals per match, home/away win rates."""
        competitions, _ = self._resolve_competition(competition)
        matches = [
            m for m in self._iter_matches(competitions, season, all_sources, played_only=True)
        ]
        if not matches:
            raise QueryError(
                "No played matches found for the given competition/season filters."
            )
        total_matches = len(matches)
        goals = sum(m.total_goals for m in matches)
        home_wins = sum(1 for m in matches if m.home_goals > m.away_goals)
        away_wins = sum(1 for m in matches if m.away_goals > m.home_goals)
        draws = total_matches - home_wins - away_wins
        home_goals = sum(m.home_goals for m in matches)
        away_goals = sum(m.away_goals for m in matches)
        biggest_home = max(matches, key=lambda m: (m.home_goals - m.away_goals, m.total_goals))
        biggest_away = max(matches, key=lambda m: (m.away_goals - m.home_goals, m.total_goals))
        if biggest_away.away_goals <= biggest_away.home_goals:
            biggest_away = None
        return CompetitionStats(
            matches=total_matches,
            goals=goals,
            avg_goals=goals / total_matches,
            home_wins=home_wins,
            draws=draws,
            away_wins=away_wins,
            home_win_rate=home_wins / total_matches,
            draw_rate=draws / total_matches,
            away_win_rate=away_wins / total_matches,
            avg_home_goals=home_goals / total_matches,
            avg_away_goals=away_goals / total_matches,
            biggest_home_win=biggest_home,
            biggest_away_win=biggest_away,
        )

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> list[Match]:
        """Biggest winning margins in the dataset."""
        competitions, _ = self._resolve_competition(competition)
        matches = [
            m for m in self._iter_matches(competitions, season, played_only=True)
        ]
        if not matches:
            raise QueryError(
                "No played matches found for the given competition/season filters."
            )
        matches.sort(key=lambda m: (m.margin, m.total_goals), reverse=True)
        return matches[: max(0, limit)]

    def derbies(
        self,
        derby: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 5,
    ) -> list[DerbyResult]:
        """Matches between traditional rivals (Fla-Flu, Gre-Nal, ...)."""
        selected = DERBIES
        note = None
        if derby is not None and str(derby).strip():
            found = find_derby(derby)
            if found is None:
                names = ", ".join(d.name for d in DERBIES)
                raise QueryError(f"Unknown derby: {derby!r}. Known derbies: {names}.")
            selected = [found]
        competitions, _ = self._resolve_competition(competition)
        results = []
        for entry in selected:
            matches = []
            wins_a = wins_b = draws = 0
            for match in self._iter_matches(competitions, season):
                if {match.home_key, match.away_key} != {entry.team_a, entry.team_b}:
                    continue
                matches.append(match)
                if not match.played:
                    continue
                if match.home_key == entry.team_a:
                    goals_a, goals_b = match.home_goals, match.away_goals
                else:
                    goals_a, goals_b = match.away_goals, match.home_goals
                if goals_a > goals_b:
                    wins_a += 1
                elif goals_b > goals_a:
                    wins_b += 1
                else:
                    draws += 1
            matches.sort(key=self._match_sort_key, reverse=True)
            shown = matches[: max(0, limit)]
            results.append(
                DerbyResult(
                    derby=entry,
                    matches=shown,
                    total=len(matches),
                    team_a_wins=wins_a,
                    team_b_wins=wins_b,
                    draws=draws,
                    team_a_display=self._registry.display_name(entry.team_a),
                    team_b_display=self._registry.display_name(entry.team_b),
                )
            )
        return results


_ENGINE_SINGLETON: Optional[QueryEngine] = None


def find_data_dir(explicit: Optional[str] = None) -> Path:
    """Locate the data/kaggle directory."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    env_dir = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    current = Path(__file__).resolve().parent
    candidates.append(current.parent / "data" / "kaggle")
    cursor = Path.cwd()
    for _ in range(5):
        candidates.append(cursor / "data" / "kaggle")
        cursor = cursor.parent
    for candidate in candidates:
        if (candidate / "fifa_data.csv").exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate the datasets (expected data/kaggle/fifa_data.csv). "
        "Set BRAZILIAN_SOCCER_DATA_DIR or pass an explicit data directory."
    )


def get_engine(data_dir: Optional[str] = None) -> QueryEngine:
    """Return a cached engine, loading the datasets on first use."""
    global _ENGINE_SINGLETON
    if _ENGINE_SINGLETON is None:
        root = find_data_dir(data_dir)
        _ENGINE_SINGLETON = QueryEngine(load_data(root))
    return _ENGINE_SINGLETON
