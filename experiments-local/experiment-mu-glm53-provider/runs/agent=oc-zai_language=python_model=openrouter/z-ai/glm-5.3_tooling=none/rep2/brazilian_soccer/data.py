"""Dataset loading and indexing for the Brazilian Soccer MCP server.

Loads all six CSV files from ``data/kaggle`` into a single :class:`Dataset`
with normalized team keys, deduplicated matches, per-competition source
selection, and player indexes.

Source selection matters because three files cover Brasileirão Série A with
overlapping seasons (``Brasileirao_Matches.csv`` 2012-2022,
``novo_campeonato_brasileiro.csv`` 2003-2019 and
``BR-Football-Dataset.csv`` 2014-2023).  Statistics such as league tables are
always computed from a single canonical source per (competition, season) —
the source with the most scored matches that does not look polluted by
matches borrowed from an adjacent season (a real effect for COVID-delayed
2020 seasons recorded under 2021 dates).
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from brazilian_soccer.models import Match, Player, TeamRecord
from brazilian_soccer.normalize import display_name, parse_date, slug, team_key

SERIE_A = "Serie A"
SERIE_B = "Serie B"
SERIE_C = "Serie C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Libertadores"

COMPETITION_DISPLAY = {
    SERIE_A: "Brasileirão Série A",
    SERIE_B: "Brasileirão Série B",
    SERIE_C: "Brasileirão Série C",
    COPA_DO_BRASIL: "Copa do Brasil",
    LIBERTADORES: "Copa Libertadores",
}

COMPETITION_KIND = {
    SERIE_A: "league",
    SERIE_B: "league",
    SERIE_C: "league",
    COPA_DO_BRASIL: "cup",
    LIBERTADORES: "cup",
}

SOURCE_BRASILEIRAO = "Brasileirao_Matches.csv"
SOURCE_CUP = "Brazilian_Cup_Matches.csv"
SOURCE_LIBERTADORES = "Libertadores_Matches.csv"
SOURCE_BRFB = "BR-Football-Dataset.csv"
SOURCE_NOVO = "novo_campeonato_brasileiro.csv"
SOURCE_FIFA = "fifa_data.csv"

SOURCE_PRIORITY = {
    SOURCE_BRASILEIRAO: 0,
    SOURCE_CUP: 0,
    SOURCE_LIBERTADORES: 0,
    SOURCE_NOVO: 1,
    SOURCE_BRFB: 2,
}

KNOCKOUT_STAGES = ("round of 16", "quarterfinal", "semifinal", "final")
STAGE_DISPLAY = {
    "group stage": "Group stage",
    "round of 16": "Round of 16",
    "quarterfinal": "Quarterfinals",
    "semifinal": "Semifinals",
    "final": "Final",
}

STAGE_ALIASES = {
    "group stage": "group stage",
    "groups": "group stage",
    "round of 16": "round of 16",
    "last 16": "round of 16",
    "quarterfinal": "quarterfinal",
    "quarterfinals": "quarterfinal",
    "semifinal": "semifinal",
    "semifinals": "semifinal",
    "final": "final",
    "finals": "final",
}

SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


def _to_int(value) -> int | None:
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def _csv_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


class Dataset:
    """In-memory index over the Brazilian soccer CSV datasets."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.display_names: dict[str, str] = {}
        self.brazilian_clubs: set[str] = set()
        self._by_team: dict[str, list[Match]] = defaultdict(list)
        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        self._deduped: list[Match] | None = None
        self._canonical_cache: dict[tuple, list[Match]] = {}
        self._source_cache: dict[tuple, str | None] = {}
        self._table_cache: dict[tuple, tuple[list[TeamRecord], dict]] = {}
        self._load_all()

    @property
    def directory(self) -> Path:
        return self.data_dir

    def _add_match(self, match: Match) -> None:
        self.matches.append(match)
        self._by_team[match.home].append(match)
        self._by_team[match.away].append(match)

    def _load_all(self) -> None:
        raw_name_counts: Counter = Counter()
        self._load_brasileirao(raw_name_counts)
        self._load_copa_do_brasil(raw_name_counts)
        self._load_libertadores(raw_name_counts)
        self._load_br_football(raw_name_counts)
        self._load_novo(raw_name_counts)
        self._build_display_names(raw_name_counts)
        self._load_fifa()
        self._brazilian_clubs()

    def _load_brasileirao(self, raw_name_counts: Counter) -> None:
        path = self.data_dir / SOURCE_BRASILEIRAO
        for row in _csv_rows(path):
            home_raw = row["home_team"]
            away_raw = row["away_team"]
            raw_name_counts[home_raw] += 1
            raw_name_counts[away_raw] += 1
            season = _to_int(row.get("season"))
            match_date = parse_date(row.get("datetime"))
            self._add_match(Match(
                date=match_date,
                home=team_key(home_raw),
                away=team_key(away_raw),
                home_goals=_to_int(row.get("home_goal")),
                away_goals=_to_int(row.get("away_goal")),
                season=season,
                competition=SERIE_A,
                source=SOURCE_BRASILEIRAO,
                round=row.get("round") or None,
                extras={
                    "home_state": row.get("home_team_state") or None,
                    "away_state": row.get("away_team_state") or None,
                },
            ))

    def _load_copa_do_brasil(self, raw_name_counts: Counter) -> None:
        path = self.data_dir / SOURCE_CUP
        rounds_by_season: dict[int, Counter] = defaultdict(Counter)
        staged_rows = []
        for row in _csv_rows(path):
            staged_rows.append(row)
            season = _to_int(row.get("season"))
            if season is not None:
                rounds_by_season[season][row["round"]] += 1
        stage_by_round = self._copa_stages(rounds_by_season)
        for row in staged_rows:
            home_raw = row["home_team"]
            away_raw = row["away_team"]
            raw_name_counts[home_raw] += 1
            raw_name_counts[away_raw] += 1
            season = _to_int(row.get("season"))
            round_label = row.get("round") or None
            self._add_match(Match(
                date=parse_date(row.get("datetime")),
                home=team_key(home_raw),
                away=team_key(away_raw),
                home_goals=_to_int(row.get("home_goal")),
                away_goals=_to_int(row.get("away_goal")),
                season=season,
                competition=COPA_DO_BRASIL,
                source=SOURCE_CUP,
                round=round_label,
                stage=stage_by_round.get((season, round_label)),
            ))

    @staticmethod
    def _copa_stages(rounds_by_season: dict[int, Counter]) -> dict[tuple, str]:
        """Label the decisive rounds of each Copa do Brasil season.

        The number of rounds in the cup changed over the years (6 to 8), so
        the final is detected structurally: the last round of a season is the
        final when it has at most two matches, the one before it the
        semifinal when it has at most four, and so on.  Seasons whose data
        stops early (2021) simply get no late-round labels.
        """
        labels: dict[tuple, str] = {}
        limits = {0: ("final", 2), 1: ("semifinal", 4), 2: ("quarterfinal", 8), 3: ("round of 16", 16)}
        for season, rounds in rounds_by_season.items():
            ordered = sorted(rounds, key=lambda r: _to_int(r) or 0)
            for offset, (label, cap) in limits.items():
                if offset >= len(ordered):
                    break
                round_label = ordered[-1 - offset]
                if rounds[round_label] <= cap:
                    labels[(season, round_label)] = label
        return labels

    def _load_libertadores(self, raw_name_counts: Counter) -> None:
        path = self.data_dir / SOURCE_LIBERTADORES
        for row in _csv_rows(path):
            season = _to_int(row.get("season"))
            if season is None:
                continue
            home_raw = row["home_team"]
            away_raw = row["away_team"]
            raw_name_counts[home_raw] += 1
            raw_name_counts[away_raw] += 1
            self._add_match(Match(
                date=parse_date(row.get("datetime")),
                home=team_key(home_raw),
                away=team_key(away_raw),
                home_goals=_to_int(row.get("home_goal")),
                away_goals=_to_int(row.get("away_goal")),
                season=season,
                competition=LIBERTADORES,
                source=SOURCE_LIBERTADORES,
                stage=STAGE_ALIASES.get(
                    (row.get("stage") or "").strip().lower(),
                    (row.get("stage") or "").strip().lower() or None,
                ),
            ))

    def _load_br_football(self, raw_name_counts: Counter) -> None:
        path = self.data_dir / SOURCE_BRFB
        for row in _csv_rows(path):
            home_raw = row["home"]
            away_raw = row["away"]
            raw_name_counts[home_raw] += 1
            raw_name_counts[away_raw] += 1
            match_date = parse_date(row.get("date"))
            tournament = (row.get("tournament") or "").strip()
            if tournament not in COMPETITION_KIND:
                continue
            self._add_match(Match(
                date=match_date,
                home=team_key(home_raw),
                away=team_key(away_raw),
                home_goals=_to_int(row.get("home_goal")),
                away_goals=_to_int(row.get("away_goal")),
                season=match_date.year if match_date else None,
                competition=tournament,
                source=SOURCE_BRFB,
                extras={
                    "home_corners": _to_int(row.get("home_corner")),
                    "away_corners": _to_int(row.get("away_corner")),
                    "home_shots": _to_int(row.get("home_shots")),
                    "away_shots": _to_int(row.get("away_shots")),
                    "home_attacks": _to_int(row.get("home_attack")),
                    "away_attacks": _to_int(row.get("away_attack")),
                    "total_corners": _to_int(row.get("total_corners")),
                    "ht_result": (row.get("ht_result") or "").strip() or None,
                    "at_result": (row.get("at_result") or "").strip() or None,
                    "kickoff": (row.get("time") or "").strip() or None,
                },
            ))

    def _load_novo(self, raw_name_counts: Counter) -> None:
        path = self.data_dir / SOURCE_NOVO
        for row in _csv_rows(path):
            home_raw = row["Equipe_mandante"]
            away_raw = row["Equipe_visitante"]
            raw_name_counts[home_raw] += 1
            raw_name_counts[away_raw] += 1
            self._add_match(Match(
                date=parse_date(row.get("Data")),
                home=team_key(home_raw),
                away=team_key(away_raw),
                home_goals=_to_int(row.get("Gols_mandante")),
                away_goals=_to_int(row.get("Gols_visitante")),
                season=_to_int(row.get("Ano")),
                competition=SERIE_A,
                source=SOURCE_NOVO,
                round=row.get("Rodada") or None,
                extras={
                    "arena": (row.get("Arena") or "").strip() or None,
                    "home_state": (row.get("Mandante_UF") or "").strip() or None,
                    "away_state": (row.get("Visitante_UF") or "").strip() or None,
                },
            ))

    def _load_fifa(self) -> None:
        path = self.data_dir / SOURCE_FIFA
        for row in _csv_rows(path):
            club = (row.get("Club") or "").strip() or None
            skills = {}
            for column in SKILL_COLUMNS:
                value = _to_int(row.get(column))
                if value is not None:
                    skills[column] = value
            self.players.append(Player(
                id=_to_int(row.get("ID")),
                name=(row.get("Name") or "").strip(),
                age=_to_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=_to_int(row.get("Overall")),
                potential=_to_int(row.get("Potential")),
                club=club,
                club_key=team_key(club) if club else None,
                position=(row.get("Position") or "").strip(),
                jersey=_to_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip(),
                weight=(row.get("Weight") or "").strip(),
                foot=(row.get("Preferred Foot") or "").strip(),
                skills=skills,
            ))
        for player in self.players:
            if player.club_key:
                self._players_by_club[player.club_key].append(player)

    def _build_display_names(self, raw_name_counts: Counter) -> None:
        grouped: dict[str, Counter] = defaultdict(Counter)
        for raw, count in raw_name_counts.items():
            grouped[team_key(raw)][raw] += count
        for key, counter in grouped.items():
            ranked = sorted(
                counter.items(),
                key=lambda item: (-item[1], "á" not in item[0].lower(), len(item[0])),
            )
            fallback = ranked[0][0]
            self.display_names[key] = display_name(key, fallback)

    def _brazilian_clubs(self) -> None:
        for match in self.matches:
            if match.competition != LIBERTADORES:
                self.brazilian_clubs.add(match.home)
                self.brazilian_clubs.add(match.away)

    @property
    def known_teams(self) -> set[str]:
        return set(self._by_team)

    @property
    def known_clubs(self) -> set[str]:
        return set(self._players_by_club) | self.known_teams

    def team_display(self, key: str) -> str:
        return self.display_names.get(key, display_name(key))

    def matches_for_team(self, team: str) -> list[Match]:
        return self._by_team.get(team, [])

    def players_for_club(self, club_key: str) -> list[Player]:
        return self._players_by_club.get(club_key, [])

    def competition_seasons(self) -> dict[str, dict[int | None, int]]:
        seasons: dict[str, Counter] = defaultdict(Counter)
        for match in self.deduped_matches:
            seasons[match.competition][match.season] += 1
        return {comp: dict(counter) for comp, counter in seasons.items()}

    def deduped(self, competition: str | None = None) -> list[Match]:
        """Return matches with cross-source duplicates collapsed.

        League fixtures are unique per (season, home, away); cup ties are
        deduplicated additionally on the scoreline because the same pairing
        can legitimately meet twice in one season.  Scored records from
        higher-priority sources win over unscored or lower-priority ones.
        """
        kind = COMPETITION_KIND.get(competition)
        keys: dict[tuple, Match] = {}
        candidates = sorted(
            self.matches,
            key=lambda m: (not m.is_scored, SOURCE_PRIORITY.get(m.source, 99)),
        )
        for match in candidates:
            if competition and match.competition != competition:
                continue
            if kind == "league":
                key = (match.competition, match.season, match.home, match.away)
            else:
                key = (match.competition, match.season, match.home, match.away,
                       match.home_goals, match.away_goals)
            if key not in keys:
                keys[key] = match
        return list(keys.values())

    @property
    def deduped_matches(self) -> list[Match]:
        if self._deduped is None:
            self._deduped = self.deduped()
        return self._deduped

    def source_stats(self, competition: str, season: int) -> dict[str, dict]:
        per_source: dict[str, dict] = defaultdict(
            lambda: {"matches": 0, "scored": 0, "team_counts": Counter()}
        )
        for match in self.matches:
            if match.competition != competition or match.season != season:
                continue
            stats = per_source[match.source]
            stats["matches"] += 1
            if match.is_scored:
                stats["scored"] += 1
            stats["team_counts"][match.home] += 1
            stats["team_counts"][match.away] += 1
        return dict(per_source)

    def canonical_source(self, competition: str, season: int) -> tuple[str | None, bool]:
        """Pick the best single source for (competition, season).

        Returns ``(source, polluted)`` where ``polluted`` indicates the
        chosen source appears to contain matches borrowed from an adjacent
        season (COVID-era scheduling).  League sources are skipped when a
        team played more games than a double round-robin allows.
        """
        cache_key = (competition, season)
        if cache_key in self._source_cache:
            return self._source_cache[cache_key], self._source_cache.get(cache_key + ("polluted",), False)
        per_source = self.source_stats(competition, season)
        if not per_source:
            self._source_cache[cache_key] = None
            return None, False

        def overflow_ratio(source: str) -> float:
            teams = len(per_source[source]["team_counts"])
            if teams == 0:
                return 0.0
            cap = 2 * (teams - 1)
            worst = max(per_source[source]["team_counts"].values())
            return max(0.0, (worst - cap) / cap)

        eligible = dict(per_source)
        polluted = False
        if COMPETITION_KIND.get(competition) == "league" and competition in (SERIE_A, SERIE_B):
            clean = {s: st for s, st in per_source.items() if overflow_ratio(s) <= 0.001}
            if clean:
                eligible = clean
            else:
                polluted = True
                eligible = dict(sorted(per_source.items(), key=lambda kv: overflow_ratio(kv[0])))
        best = min(
            eligible.items(),
            key=lambda kv: (-kv[1]["scored"], SOURCE_PRIORITY.get(kv[0], 99)),
        )
        self._source_cache[cache_key] = best[0]
        self._source_cache[cache_key + ("polluted",)] = polluted
        return best[0], polluted

    def canonical_matches(
        self,
        competition: str | None = None,
        season: int | None = None,
    ) -> list[Match]:
        """Matches from one canonical source per (competition, season)."""
        cache_key = (competition, season)
        if cache_key in self._canonical_cache:
            return self._canonical_cache[cache_key]
        competitions: Counter = Counter()
        seasons: Counter = Counter()
        for match in self.matches:
            if competition and match.competition != competition:
                continue
            if season is not None and match.season != season:
                continue
            competitions[match.competition] += 1
            seasons[match.season] += 1
        selected: list[Match] = []
        for comp in competitions:
            for sea in seasons:
                source, _ = self.canonical_source(comp, sea)
                if source is None:
                    continue
                selected.extend(
                    m for m in self.matches
                    if m.competition == comp and m.season == sea and m.source == source
                )
        self._canonical_cache[cache_key] = selected
        return selected

    def league_table(self, competition: str, season: int) -> tuple[list[TeamRecord], dict]:
        """Compute the points table for a league competition and season."""
        cache_key = (competition, season)
        if cache_key in self._table_cache:
            return self._table_cache[cache_key]
        records: dict[str, TeamRecord] = {}
        scored = 0
        total = 0
        for match in self.canonical_matches(competition, season):
            total += 1
            if not match.is_scored:
                continue
            scored += 1
            for team in (match.home, match.away):
                records.setdefault(team, TeamRecord(team=team))
            records[match.home].add_match(match)
            records[match.away].add_match(match)
        table = sorted(
            records.values(),
            key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.team),
        )
        meta = {"scored_matches": scored, "total_matches": total}
        result = (table, meta)
        self._table_cache[cache_key] = result
        return result


@lru_cache(maxsize=4)
def load_dataset(data_dir: str | Path | None = None) -> Dataset:
    """Load and cache the dataset (cached per data directory)."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent.parent / "data" / "kaggle"
    return Dataset(data_dir)
