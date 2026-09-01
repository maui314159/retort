"""In-memory knowledge store unifying all match and player datasets.

The store loads the six CSVs once, deduplicates matches that appear in more
than one dataset (the 2012-2019 Série A seasons exist in three files), builds
team/player indexes, and exposes the query surface used by the MCP tools and
the CLI.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from .dates import parse_date
from .loaders import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    load_all,
)
from .models import Match, Player, TeamRecord
from .normalize import BRAZILIAN_UFS, normalize_text

SOURCE_PRIORITY = {
    "brasileirao": 0,
    "copa_do_brasil": 1,
    "libertadores": 2,
    "brasileiro_historico": 3,
    "brasileirao_historico": 3,
    "br_football": 4,
}

COMPETITION_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("libertadores",), LIBERTADORES),
    (("copa do brasil", "copadobrasil", "cdb", "brazilian cup"), COPA_DO_BRASIL),
    (("serie b", "serieb", "b series", "serie b brasileirao"), SERIE_B),
    (("serie c", "seriec", "c series"), SERIE_C),
    (("serie a", "seriea", "brasileirao", "brasileirao serie a"), SERIE_A),
]

DERBIES: list[tuple[str, str, str]] = [
    ("Fla-Flu", "flamengo-rj", "fluminense-rj"),
    ("Clássico dos Milhões", "flamengo-rj", "vasco-rj"),
    ("Clássico Vovô", "botafogo-rj", "fluminense-rj"),
    ("Majestoso", "corinthians-sp", "sao paulo-sp"),
    ("Choque-Rei", "palmeiras-sp", "sao paulo-sp"),
    ("Derby Paulista", "palmeiras-sp", "corinthians-sp"),
    ("Grenal", "gremio-rs", "internacional-rs"),
    ("Atletiba", "atletico-pr", "coritiba-pr"),
    ("Ba-Vi", "bahia-ba", "vitoria-ba"),
    ("Clássico-Rei", "fortaleza-ce", "ceara-ce"),
    ("Clássico dos Clássicos", "sport-pe", "santa cruz-pe"),
    ("Clássico das Multidões", "sport-pe", "nautico-pe"),
]

POSITION_GROUPS: dict[str, set[str]] = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "midfielder": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
    "forward": {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"},
}

FINAL_WORDS = {"final", "finals", "finais", "decisao", "championship match"}

FOREIGN_FIFA_CLUBS = {"Boavista FC"}

ALL_COMPETITIONS = [SERIE_A, SERIE_B, SERIE_C, COPA_DO_BRASIL, LIBERTADORES]


def match_competitions(query: str | None) -> list[str]:
    """Translate a free-text competition name to canonical competition names."""
    if not query:
        return list(ALL_COMPETITIONS)
    needle = normalize_text(query)
    for needles, canonical in COMPETITION_ALIASES:
        if any(n in needle for n in needles):
            return [canonical]
    return []


def _is_brazilian_club(club_id: str) -> bool:
    parts = club_id.rsplit("-", 1)
    return len(parts) == 2 and parts[1].upper() in BRAZILIAN_UFS


class SoccerStore:
    """Repository of matches, players and teams with query helpers."""

    def __init__(self, data_dir: Path | str = "data/kaggle") -> None:
        self.data_dir = Path(data_dir)
        raw_matches, self.players, self.registry = load_all(self.data_dir)
        self._reconcile_brf_seasons(raw_matches)
        self.matches, self.duplicate_count = self._deduplicate(raw_matches)
        self._by_team: dict[str, list[int]] = defaultdict(list)
        self._by_competition: dict[str, list[int]] = defaultdict(list)
        for index, match in enumerate(self.matches):
            self._by_team[match.home].append(index)
            self._by_team[match.away].append(index)
            self._by_competition[match.competition].append(index)
        self._cup_final_rounds: dict[int, str] = {}
        for match in self.matches:
            if match.competition == COPA_DO_BRASIL and match.season is not None and match.round:
                current = self._cup_final_rounds.get(match.season)
                try:
                    round_num = int(match.round)
                except ValueError:
                    continue
                current_num = int(current) if current else -1
                if round_num > current_num:
                    self._cup_final_rounds[match.season] = match.round
        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        for player in self.players:
            if player.club and player.club not in FOREIGN_FIFA_CLUBS:
                club_id = self.registry.resolve(player.club)
                if club_id:
                    self._players_by_club[club_id].append(player)

    @staticmethod
    def _reconcile_brf_seasons(matches: list[Match]) -> None:
        """Fix calendar-year season labels in BR-Football-Dataset records.

        That dataset labels matches by calendar year, but seasons cross the
        year boundary (the COVID-delayed 2020 Série A/B/C and Copa do Brasil
        finals ran into Jan-Mar 2021). Two-step fix:

        1. If a trusted source (Brasileirão/Copa/Libertadores files) has the
           same fixture (competition + pairing) within 4 days, adopt its
           season label.
        2. Otherwise, Jan/Feb league matches belong to the previous year's
           season.
        """
        index: dict[tuple, list[tuple[date, int]]] = defaultdict(list)
        for match in matches:
            if match.source != "br_football" and match.date and match.season:
                index[(match.competition, match.home, match.away)].append(
                    (match.date, match.season)
                )
        for match in matches:
            if match.source != "br_football" or not match.date or not match.season:
                continue
            key = (match.competition, match.home, match.away)
            for ref_date, ref_season in index.get(key, ()):
                if abs((match.date - ref_date).days) <= 4:
                    if ref_season != match.season:
                        match.season = ref_season
                    break
            else:
                if match.date.month <= 2 and match.competition != COPA_DO_BRASIL:
                    match.season = match.date.year - 1

    @staticmethod
    def _deduplicate(matches: list[Match]) -> tuple[list[Match], int]:
        """Merge matches shared across datasets, keeping the richest record.

        The same fixture appears in up to three files with slightly different
        dates (timezone/data-entry drift of a day or two). Matches are grouped
        by (competition, season, home, away) and merged when their dates are
        at most 4 days apart, which the datasets show separates true
        duplicates (gap <= 4 days) from legitimately distinct meetings such
        as Libertadores group-stage vs knockout pairings (gap >= 14 days).
        The record from the highest-priority source is kept and enriched with
        any fields (venue, stats, kick-off time) only present in duplicates.
        """
        groups: dict[tuple, list[Match]] = defaultdict(list)
        order: list[tuple] = []
        dated: list[Match] = []
        for match in matches:
            if match.date is None or match.season is None:
                dated.append(match)
                continue
            key = (match.competition, match.season, match.home, match.away)
            if key not in groups:
                order.append(key)
            groups[key].append(match)

        result: list[Match] = []
        duplicates = 0
        for key in order:
            cluster: list[Match] = []
            last_date: date | None = None
            for match in sorted(groups[key], key=lambda m: (m.date is None, m.date)):
                if last_date is not None and match.date is not None and (match.date - last_date).days > 4:
                    duplicates += _merge_cluster(cluster, result)
                    cluster = []
                cluster.append(match)
                last_date = match.date or last_date
            duplicates += _merge_cluster(cluster, result)
            duplicates += _absorb_postponed(groups[key], result)
        result.extend(dated)
        return result, duplicates

    def resolve_team(self, name: str | None) -> str | None:
        return self.registry.resolve(name) if name else None

    def team_display(self, cid: str) -> str:
        return self.registry.display(cid)

    def suggest_teams(self, query: str, limit: int = 8) -> list[str]:
        return self.registry.suggest(query, limit)

    def competitions_summary(self) -> list[dict]:
        """Per-competition coverage: seasons, match counts and team counts."""
        summary: dict[str, dict] = {}
        for match in self.matches:
            entry = summary.setdefault(
                match.competition,
                {"competition": match.competition, "matches": 0, "seasons": set(), "teams": set()},
            )
            entry["matches"] += 1
            if match.season:
                entry["seasons"].add(match.season)
            entry["teams"].add(match.home)
            entry["teams"].add(match.away)
        rows = []
        for competition in ALL_COMPETITIONS:
            entry = summary.get(competition)
            if not entry:
                continue
            rows.append(
                {
                    "competition": competition,
                    "matches": entry["matches"],
                    "seasons": (
                        f"{min(entry['seasons'])}-{max(entry['seasons'])}"
                        if entry["seasons"] else "n/a"
                    ),
                    "teams": len(entry["teams"]),
                }
            )
        return rows

    def find_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | date | None = None,
        date_to: str | date | None = None,
        stage: str | None = None,
        venue: str = "any",
        only_played: bool = False,
        limit: int | None = 50,
    ) -> tuple[list[Match], int]:
        """Find matches by team, opponent, competition, season, date or stage.

        ``venue`` is 'any', 'home' or 'away' relative to ``team``. Returns the
        (possibly truncated) match list plus the total matching count.
        """
        team_id = self.resolve_team(team) if team else None
        opponent_id = self.resolve_team(opponent) if opponent else None
        if team and not team_id:
            return [], 0
        if opponent and not opponent_id:
            return [], 0
        competitions = match_competitions(competition)
        if competition and not competitions:
            return [], 0
        from_date = _coerce_date(date_from)
        to_date = _coerce_date(date_to)

        if team_id:
            candidates: list[int] = list(self._by_team.get(team_id, []))
        else:
            candidates = list(range(len(self.matches)))

        matched: list[Match] = []
        for index in candidates:
            match = self.matches[index]
            if team_id and not match.involves(team_id):
                continue
            if team_id and venue == "home" and match.home != team_id:
                continue
            if team_id and venue == "away" and match.away != team_id:
                continue
            if opponent_id and not match.involves(opponent_id):
                continue
            if competitions and match.competition not in competitions:
                continue
            if season is not None and match.season != season:
                continue
            if from_date and (match.date is None or match.date < from_date):
                continue
            if to_date and (match.date is None or match.date > to_date):
                continue
            if stage and not self._stage_matches(match, stage):
                continue
            if only_played and not match.played:
                continue
            matched.append(match)
        matched.sort(key=lambda m: (m.date is None, m.date or date.min), reverse=True)
        total = len(matched)
        return (matched[:limit], total) if limit is not None else (matched, total)

    def _stage_matches(self, match: Match, stage: str) -> bool:
        needle = normalize_text(stage)
        if not needle:
            return True
        if needle in FINAL_WORDS:
            if match.competition == COPA_DO_BRASIL:
                return match.round == self._cup_final_rounds.get(match.season)
            if match.competition == LIBERTADORES:
                return (match.stage or "") == "final"
        stage_text = normalize_text(match.stage or "")
        if stage_text and (stage_text == needle or stage_text.startswith(needle)):
            return True
        round_text = normalize_text(match.round or "")
        if round_text:
            if round_text == needle or f"round {round_text}" == needle:
                return True
            if needle.isdigit() and round_text == needle:
                return True
        if needle.isdigit() and (match.round or "") == needle:
            return True
        return False

    def head_to_head(
        self, team_a: str, team_b: str, competition: str | None = None
    ) -> dict | None:
        """Head-to-head record between two teams across the datasets."""
        a_id = self.resolve_team(team_a)
        b_id = self.resolve_team(team_b)
        if not a_id or not b_id:
            return None
        matches, _total = self.find_matches(
            team=a_id, opponent=b_id, competition=competition, limit=None
        )
        a_record = TeamRecord(team=a_id, display=self.team_display(a_id))
        b_record = TeamRecord(team=b_id, display=self.team_display(b_id))
        for match in matches:
            a_record.add(match)
            b_record.add(match)
        return {
            "team_a": a_record.to_dict(),
            "team_b": b_record.to_dict(),
            "matches": matches,
        }

    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
    ) -> dict | None:
        """Overall/home/away records plus per-competition and per-season splits."""
        team_id = self.resolve_team(team)
        if not team_id:
            return None
        matches, _total = self.find_matches(
            team=team_id, season=season, competition=competition, limit=None
        )
        display = self.team_display(team_id)
        overall = TeamRecord(team=team_id, display=display)
        home = TeamRecord(team=team_id, display=display)
        away = TeamRecord(team=team_id, display=display)
        by_competition: dict[str, TeamRecord] = {}
        by_season: dict[int, TeamRecord] = {}
        for match in matches:
            overall.add(match)
            (home if match.home == team_id else away).add(match)
            comp_record = by_competition.setdefault(
                match.competition, TeamRecord(team=team_id, display=display)
            )
            comp_record.add(match)
            if match.season:
                season_record = by_season.setdefault(
                    match.season, TeamRecord(team=team_id, display=display)
                )
                season_record.add(match)
        return {
            "team": display,
            "canonical_id": team_id,
            "overall": overall.to_dict(),
            "home": home.to_dict(),
            "away": away.to_dict(),
            "by_competition": [
                {"competition": name, **by_competition[name].to_dict()}
                for name in ALL_COMPETITIONS
                if name in by_competition
            ],
            "by_season": [
                {"season": year, **by_season[year].to_dict()}
                for year in sorted(by_season, reverse=True)
            ],
        }

    def standings(self, season: int, competition: str = SERIE_A) -> dict | None:
        """League table computed from match results for one season."""
        competitions = match_competitions(competition)
        if not competitions:
            return None
        canonical = competitions[0]
        if canonical == LIBERTADORES:
            return self._libertadores_summary(season)
        matches, _total = self.find_matches(
            competition=canonical, season=season, limit=None, only_played=True
        )
        if not matches:
            return None
        records: dict[str, TeamRecord] = {}
        for match in matches:
            for team, display in (
                (match.home, match.home_display),
                (match.away, match.away_display),
            ):
                if team not in records:
                    records[team] = TeamRecord(team=team, display=display)
            records[match.home].add(match)
            records[match.away].add(match)
        max_matches = max((r.matches for r in records.values()), default=0)
        regulars = [r for r in records.values() if r.matches * 2 >= max_matches]
        table = sorted(
            regulars,
            key=lambda r: (-r.points, -r.wins, -r.goal_diff, -r.goals_for, r.display),
        )
        return {
            "season": season,
            "competition": canonical,
            "table": [record.to_dict() for record in table],
            "champion": table[0].to_dict() if table else None,
            "relegated": [record.to_dict() for record in table[-4:]],
        }

    def _libertadores_summary(self, season: int) -> dict | None:
        """Stage-by-stage summary for a Libertadores season."""
        matches, _total = self.find_matches(
            competition=LIBERTADORES, season=season, limit=None
        )
        if not matches:
            return None
        stages: dict[str, list[Match]] = defaultdict(list)
        for match in matches:
            stages[match.stage or "unknown"].append(match)
        stage_summary = []
        for stage_name in ("group stage", "round of 16", "quarterfinals", "semifinals", "final"):
            if stage_name in stages:
                stage_matches = sorted(
                    stages[stage_name], key=lambda m: (m.date is None, m.date or date.min)
                )
                stage_summary.append({"stage": stage_name, "matches": stage_matches})
        return {"season": season, "competition": LIBERTADORES, "stages": stage_summary}

    def biggest_wins(
        self,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> list[Match]:
        """Largest goal-margin victories, newest first among equal margins."""
        matches, _total = self.find_matches(
            competition=competition, season=season, limit=None, only_played=True
        )
        ranked = sorted(
            matches,
            key=lambda m: (
                -(m.margin or 0),
                -(m.goals or 0),
                m.date is None,
                m.date or date.min,
            ),
        )
        return ranked[:limit]

    def goals_analysis(
        self, competition: str | None = None, season: int | None = None
    ) -> dict | None:
        """Average goals, home/away win rates and draw rate for a filter set."""
        matches, _total = self.find_matches(
            competition=competition, season=season, limit=None, only_played=True
        )
        played = [m for m in matches if m.played]
        if not played:
            return None
        count = len(played)
        total_goals = sum(m.goals or 0 for m in played)
        home_wins = sum(1 for m in played if m.home_goals > m.away_goals)
        away_wins = sum(1 for m in played if m.home_goals < m.away_goals)
        draws = count - home_wins - away_wins
        return {
            "matches": count,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / count, 2),
            "avg_home_goals": round(sum(m.home_goals for m in played) / count, 2),
            "avg_away_goals": round(sum(m.away_goals for m in played) / count, 2),
            "home_win_rate": round(100 * home_wins / count, 1),
            "away_win_rate": round(100 * away_wins / count, 1),
            "draw_rate": round(100 * draws / count, 1),
        }

    def best_records(
        self,
        competition: str | None = None,
        season: int | None = None,
        venue: str = "overall",
        min_matches: int = 10,
        limit: int = 10,
    ) -> list[dict]:
        """Rank teams by points-per-game for a filter set and venue."""
        matches, _total = self.find_matches(
            competition=competition, season=season, limit=None, only_played=True
        )
        records: dict[str, TeamRecord] = {}
        for match in matches:
            if venue == "home":
                teams = (match.home,)
            elif venue == "away":
                teams = (match.away,)
            else:
                teams = (match.home, match.away)
            for team in teams:
                record = records.setdefault(
                    team, TeamRecord(team=team, display=self.team_display(team))
                )
                record.add(match)
        eligible = [r for r in records.values() if r.matches >= min_matches]
        eligible.sort(key=lambda r: (-r.points / r.matches, -r.win_rate, -r.goal_diff, r.display))
        return [
            record.to_dict() | {"ppg": round(record.points / record.matches, 2)}
            for record in eligible[:limit]
        ]

    def derbies(
        self,
        season: int | None = None,
        competition: str | None = None,
        limit: int = 50,
    ) -> dict[str, list[Match]]:
        """Matches between traditional rival pairs (famous Brazilian derbies)."""
        result: dict[str, list[Match]] = {}
        for name, team_a, team_b in DERBIES:
            if not self.registry.is_known(team_a) or not self.registry.is_known(team_b):
                continue
            matches, _total = self.find_matches(
                team=team_a,
                opponent=team_b,
                season=season,
                competition=competition,
                limit=limit,
            )
            if matches:
                result[name] = matches
        return result

    def player_search(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        max_age: int | None = None,
        order_by: str = "overall",
        limit: int = 20,
    ) -> tuple[list[Player], int]:
        """Search FIFA players by name, nationality, club, position or ratings.

        ``club`` accepts Brazilian team names in any spelling (e.g.
        'Athletico-PR', 'Atlético Paranaense') as well as foreign club names.
        """
        name_needle = normalize_text(name) if name else None
        nationality_needle = normalize_text(nationality) if nationality else None
        club_ids = self._resolve_club_filter(club)
        if club and not club_ids:
            return [], 0
        positions = self._expand_positions(position)
        matched: list[Player] = []
        for player in self.players:
            if name_needle and name_needle not in normalize_text(player.name):
                continue
            if nationality_needle and nationality_needle not in normalize_text(player.nationality):
                continue
            if club_ids is not None:
                if player.club in FOREIGN_FIFA_CLUBS:
                    continue
                player_club = self.registry.resolve(player.club) if player.club else None
                if player_club not in club_ids:
                    continue
            if positions is not None and player.position not in positions:
                continue
            if min_overall is not None and (player.overall is None or player.overall < min_overall):
                continue
            if max_overall is not None and (player.overall is None or player.overall > max_overall):
                continue
            if max_age is not None and (player.age is None or player.age > max_age):
                continue
            matched.append(player)
        matched.sort(key=_player_sort_key(order_by), reverse=_sort_descending(order_by))
        total = len(matched)
        return matched[:limit], total

    def _resolve_club_filter(self, club: str | None) -> set[str] | None:
        """Resolve a club query to the set of acceptable canonical club ids."""
        if not club:
            return None
        resolved = self.registry.resolve(club)
        if resolved:
            return {resolved}
        needle = normalize_text(club)
        if not needle:
            return set()
        matches_found = {
            self.registry.resolve(player.club)
            for player in self.players
            if player.club
            and player.club not in FOREIGN_FIFA_CLUBS
            and needle in normalize_text(player.club)
        }
        return {club_id for club_id in matches_found if club_id}

    def _expand_positions(self, position: str | None) -> set[str] | None:
        if not position:
            return None
        needle = normalize_text(position)
        direct = {"gk": "goalkeeper", "gol": "goalkeeper", "goleiro": "goalkeeper"}
        needle = direct.get(needle, needle)
        if needle in POSITION_GROUPS:
            return POSITION_GROUPS[needle]
        if needle in {"atacante", "striker"}:
            return POSITION_GROUPS["forward"]
        if needle in {"meia", "meio campista"}:
            return POSITION_GROUPS["midfielder"]
        if needle in {"zagueiro", "lateral"}:
            return POSITION_GROUPS["defender"]
        return {position.upper()}

    def brazilian_clubs_with_squads(self) -> list[dict]:
        """FIFA clubs that correspond to Brazilian teams in the match data."""
        clubs = []
        for club_id, players in self._players_by_club.items():
            if not _is_brazilian_club(club_id):
                continue
            if not self._by_team.get(club_id):
                continue
            overalls = [p.overall for p in players if p.overall is not None]
            clubs.append(
                {
                    "club": self.team_display(club_id),
                    "canonical_id": club_id,
                    "players": len(players),
                    "avg_overall": round(sum(overalls) / len(overalls), 1) if overalls else None,
                }
            )
        clubs.sort(key=lambda c: (-c["players"], c["club"]))
        return clubs

    def squad_of(self, team: str) -> list[Player]:
        """All FIFA players whose club matches a Brazilian team name."""
        team_id = self.resolve_team(team)
        if not team_id:
            return []
        return self._players_by_club.get(team_id, [])


def _merge_cluster(cluster: list[Match], result: list[Match]) -> int:
    """Fold a cluster of duplicate matches into one record; returns dup count."""
    if not cluster:
        return 0
    keeper = min(
        cluster,
        key=lambda m: (not m.played, SOURCE_PRIORITY.get(m.source, 99)),
    )
    for other in cluster:
        if other is keeper:
            continue
        for field_name in (
            "date", "time", "venue", "home_state", "away_state", "round", "stage",
            "home_goals", "away_goals", "home_corners", "away_corners",
            "total_corners", "home_shots", "away_shots", "home_attacks",
            "away_attacks", "ht_result", "at_result", "season",
        ):
            if getattr(keeper, field_name) is None and getattr(other, field_name) is not None:
                setattr(keeper, field_name, getattr(other, field_name))
    result.append(keeper)
    return len(cluster) - 1


def _absorb_postponed(group: list[Match], result: list[Match]) -> int:
    """Merge unplayed records of a fixture into its played counterpart.

    A postponed match can appear with its originally scheduled date (no
    result) in one file and with the actually played date in another, weeks
    apart. Within one (competition, season, pairing) group such an unplayed
    record is the same fixture, so it is absorbed into the closest played
    record instead of surviving as a phantom match. Returns the number of
    phantom records removed.
    """
    unplayed = [m for m in group if not m.played]
    played = [m for m in group if m.played]
    if not unplayed or not played:
        return 0
    absorbed = 0
    for phantom in unplayed:
        phantom_index = next((i for i, r in enumerate(result) if r is phantom), None)
        if phantom_index is None:
            continue
        target = min(
            played,
            key=lambda m: abs((m.date or date.min) - (phantom.date or date.min)),
        )
        for field_name in ("round", "venue", "home_state", "away_state", "time"):
            if getattr(target, field_name) is None and getattr(phantom, field_name) is not None:
                setattr(target, field_name, getattr(phantom, field_name))
        del result[phantom_index]
        absorbed += 1
    return absorbed


def _coerce_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return parse_date(value)


def _player_sort_key(order_by: str):
    field = normalize_text(order_by).replace(" ", "_")
    field = {"rating": "overall"}.get(field, field)
    if field not in {"overall", "potential", "age", "name", "jersey"}:
        field = "overall"

    def key(player: Player):
        value = getattr(player, field)
        if field == "name":
            return value.lower()
        if value is None:
            return (1, 0, player.name.lower())
        return (0, value, player.name.lower())

    return key


def _sort_descending(order_by: str) -> bool:
    field = normalize_text(order_by).replace(" ", "_")
    return field != "name"


def default_data_dir() -> Path:
    """Locate the bundled data directory from CWD or the package parents."""
    candidates = [
        Path.cwd() / "data" / "kaggle",
        Path(__file__).resolve().parents[2] / "data" / "kaggle",
        Path(__file__).resolve().parents[3] / "data" / "kaggle",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return Path.cwd() / "data" / "kaggle"
