"""Loads and unifies the six Kaggle datasets into queryable in-memory indexes.

The loader reads every CSV in ``data/kaggle/``, converts each row into a
:class:`models.Match` or :class:`models.Player`, and merges duplicate
matches that appear in more than one file (Brasileirão Série A matches,
for example, exist in *three* of the sources). Dedup keeps the row from
the highest-priority source and merges in any extra detail (stadium,
corners/shots statistics) contributed by lower-priority sources.

Source priority for matches:

1. ``Brasileirao_Matches.csv`` — round numbers, 2012-2021 Série A
2. ``novo_campeonato_brasileiro.csv`` — 2003-2019 Série A with stadiums
3. ``Brazilian_Cup_Matches.csv`` — Copa do Brasil with round numbers
4. ``Libertadores_Matches.csv`` — Libertadores with stage names
5. ``BR-Football-Dataset.csv`` — extended stats (corners, shots, attacks)

The :class:`SoccerData` container is instantiated once (module-level
singleton via :func:`get_data`) and exposes prebuilt indexes so that
every MCP tool responds well inside the 2-second budget: lookups are
dict hits, never full scans.
"""

from __future__ import annotations

import csv
import threading
from collections import defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path

from models import Match, Player
from normalize import (
    canonical_team_key,
    normalize_round,
    parse_date,
    parse_int,
    strip_accents,
    team_display_name,
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "kaggle"

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

_BR_TOURNAMENT_MAP = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}

_SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
]


def _read_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _parse_skill(value: str) -> int | None:
    if not value:
        return None
    head = value.split("+")[0].strip()
    return parse_int(head)


class TeamEntry:
    """A team known to the dataset: canonical key plus raw variants."""

    def __init__(self, key: str) -> None:
        self.key = key
        self.raw_variants: set[str] = set()
        self.match_count = 0
        self.player_count = 0

    @property
    def display(self) -> str:
        return team_display_name(self.key)

    def register(self, raw_name: str) -> None:
        self.raw_variants.add(raw_name.strip())

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "display_name": self.display,
            "variants": sorted(self.raw_variants)[:12],
            "matches": self.match_count,
            "players": self.player_count,
        }


class SoccerData:
    """Container for all loaded matches, players and derived indexes."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.stats_matches: list[Match] = []
        self.teams: dict[str, TeamEntry] = {}

        self._by_team: dict[str, list[Match]] = defaultdict(list)
        self._by_comp_season: dict[tuple[str, int | None], list[Match]] = defaultdict(list)
        self._players_by_name: dict[str, list[Player]] = defaultdict(list)
        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        self._dedup: dict[tuple, int] = {}
        self._unscored: dict[tuple, int] = {}

        self._load_matches()
        self._drop_misfiled_league_matches()
        self._load_players()
        self._build_indexes()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _register_team(self, key: str, raw_name: str) -> None:
        entry = self.teams.get(key)
        if entry is None:
            entry = TeamEntry(key)
            self.teams[key] = entry
        entry.register(raw_name)

    def _add_match(self, match: Match) -> None:
        if match.home_key:
            self._register_team(match.home_key, match.home_team)
        if match.away_key:
            self._register_team(match.away_key, match.away_team)
        scored = match.home_goals is not None and match.away_goals is not None
        if scored:
            for key in self._probe_keys(match):
                existing = self._dedup.get(key)
                if existing is not None:
                    self._merge_into(existing, match)
                    return
            fixture = (match.competition, match.season, match.home_key, match.away_key)
            unscored_idx = self._unscored.get(fixture)
            if unscored_idx is not None:
                self._replace_unscored(unscored_idx, match)
                return
        else:
            for key in self._probe_keys(match):
                existing = self._dedup.get(key)
                if existing is not None:
                    return
        index = len(self.matches)
        self.matches.append(match)
        if match.stats:
            self.stats_matches.append(match)
        for key in self._dedup_keys(match):
            self._dedup[key] = index
        if not scored and match.season is not None:
            fixture = (match.competition, match.season, match.home_key, match.away_key)
            self._unscored.setdefault(fixture, index)

    def _merge_into(self, index: int, match: Match) -> None:
        """Merge a duplicate row into the kept match, filling any gaps."""
        kept = self.matches[index]
        updates: dict = {}
        if kept.home_goals is None and match.home_goals is not None:
            updates["home_goals"] = match.home_goals
            updates["away_goals"] = match.away_goals
        if not kept.stats and match.stats:
            updates["stats"] = match.stats
        if not updates:
            return
        merged = replace(kept, **updates)
        self.matches[index] = merged
        if updates.get("stats"):
            self.stats_matches.append(merged)
        fixture = (merged.competition, merged.season, merged.home_key, merged.away_key)
        self._unscored.pop(fixture, None)

    def _replace_unscored(self, index: int, match: Match) -> None:
        """Fill in the result of a fixture previously stored without one.

        The Brasileirão source lists scheduled-but-unplayed fixtures (e.g.
        rescheduled 2022 rounds) with empty goals; when a lower-priority
        source later provides the played result, the placeholder row is
        replaced while keeping any richer detail (round, stadium).
        """
        kept = self.matches[index]
        merged = replace(
            kept,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            stats=kept.stats or match.stats,
        )
        self.matches[index] = merged
        if merged.stats:
            self.stats_matches.append(merged)
        fixture = (merged.competition, merged.season, merged.home_key, merged.away_key)
        self._unscored.pop(fixture, None)

    @staticmethod
    def _probe_keys(match: Match) -> list[tuple]:
        """Dedup lookup keys, tolerating one-day date discrepancies.

        Kaggle sources disagree by a single day on some fixture dates
        (timezone differences at data creation), so date-based identity is
        probed across the date ± 1 day.
        """
        keys = SoccerData._dedup_keys(match)
        if match.date is not None:
            for delta in (-1, 1):
                shifted = date.fromordinal(match.date.toordinal() + delta)
                keys.append(
                    ("date", match.competition, shifted, match.home_key, match.away_key)
                )
        return keys

    @staticmethod
    def _dedup_keys(match: Match) -> list[tuple]:
        """Two dedup identities: exact date, or same season+round pairing.

        Kaggle sources occasionally disagree by one day on a fixture date,
        so (competition, season, home, away, round/stage) is also used to
        catch the same fixture recorded with slightly different dates.
        """
        keys = []
        if match.date is not None:
            keys.append(
                ("date", match.competition, match.date, match.home_key, match.away_key)
            )
        label = match.round or match.stage
        if match.season is not None and label:
            keys.append(
                ("round", match.competition, match.season, match.home_key,
                 match.away_key, label)
            )
        return keys

    def _load_matches(self) -> None:
        self._load_brasileirao()
        self._load_historico()
        self._load_copa_do_brasil()
        self._load_libertadores()
        self._load_br_football()

    def _load_brasileirao(self) -> None:
        path = self.data_dir / "Brasileirao_Matches.csv"
        if not path.exists():
            return
        for row in _read_rows(path):
            self._add_match(Match(
                date=parse_date(row["datetime"]),
                home_team=row["home_team"].strip(),
                away_team=row["away_team"].strip(),
                home_goals=parse_int(row["home_goal"]),
                away_goals=parse_int(row["away_goal"]),
                competition=SERIE_A,
                season=parse_int(row["season"]),
                home_key=canonical_team_key(row["home_team"]),
                away_key=canonical_team_key(row["away_team"]),
                round=normalize_round(SERIE_A, row["round"]),
                kickoff=row["datetime"].split(" ", 1)[1]
                if " " in row["datetime"] else None,
                home_state=row.get("home_team_state"),
                away_state=row.get("away_team_state"),
                source="Brasileirao_Matches.csv",
            ))

    def _load_historico(self) -> None:
        path = self.data_dir / "novo_campeonato_brasileiro.csv"
        if not path.exists():
            return
        for row in _read_rows(path):
            self._add_match(Match(
                date=parse_date(row["Data"]),
                home_team=row["Equipe_mandante"].strip(),
                away_team=row["Equipe_visitante"].strip(),
                home_goals=parse_int(row["Gols_mandante"]),
                away_goals=parse_int(row["Gols_visitante"]),
                competition=SERIE_A,
                season=parse_int(row["Ano"]),
                home_key=canonical_team_key(row["Equipe_mandante"]),
                away_key=canonical_team_key(row["Equipe_visitante"]),
                round=f"Round {row['Rodada'].strip()}",
                stadium=(row.get("Arena") or "").strip() or None,
                home_state=(row.get("Mandante_UF") or "").strip() or None,
                away_state=(row.get("Visitante_UF") or "").strip() or None,
                source="novo_campeonato_brasileiro.csv",
            ))

    def _load_copa_do_brasil(self) -> None:
        path = self.data_dir / "Brazilian_Cup_Matches.csv"
        if not path.exists():
            return
        for row in _read_rows(path):
            self._add_match(Match(
                date=parse_date(row["datetime"]),
                home_team=row["home_team"].strip(),
                away_team=row["away_team"].strip(),
                home_goals=parse_int(row["home_goal"]),
                away_goals=parse_int(row["away_goal"]),
                competition=COPA_DO_BRASIL,
                season=parse_int(row["season"]),
                home_key=canonical_team_key(row["home_team"]),
                away_key=canonical_team_key(row["away_team"]),
                round=normalize_round(COPA_DO_BRASIL, row["round"]),
                kickoff=row["datetime"].split(" ", 1)[1]
                if " " in row["datetime"] else None,
                source="Brazilian_Cup_Matches.csv",
            ))

    def _load_libertadores(self) -> None:
        path = self.data_dir / "Libertadores_Matches.csv"
        if not path.exists():
            return
        for row in _read_rows(path):
            season = parse_int(row["season"])
            self._add_match(Match(
                date=parse_date(row["datetime"]),
                home_team=row["home_team"].strip(),
                away_team=row["away_team"].strip(),
                home_goals=parse_int(row["home_goal"]),
                away_goals=parse_int(row["away_goal"]),
                competition=LIBERTADORES,
                season=season,
                home_key=canonical_team_key(row["home_team"]),
                away_key=canonical_team_key(row["away_team"]),
                stage=(row.get("stage") or "").strip() or None,
                kickoff=row["datetime"].split(" ", 1)[1]
                if " " in row["datetime"] else None,
                source="Libertadores_Matches.csv",
            ))

    def _load_br_football(self) -> None:
        path = self.data_dir / "BR-Football-Dataset.csv"
        if not path.exists():
            return
        for row in _read_rows(path):
            competition = _BR_TOURNAMENT_MAP.get(row["tournament"].strip())
            if competition is None:
                continue
            match_date = parse_date(row["date"])
            season = match_date.year if match_date else None
            stats = {
                "home_corners": parse_int(row.get("home_corner")),
                "away_corners": parse_int(row.get("away_corner")),
                "total_corners": parse_int(row.get("total_corners")),
                "home_shots": parse_int(row.get("home_shots")),
                "away_shots": parse_int(row.get("away_shots")),
                "home_attacks": parse_int(row.get("home_attack")),
                "away_attacks": parse_int(row.get("away_attack")),
                "home_ht_result": (row.get("ht_result") or "").strip() or None,
                "away_ht_result": (row.get("at_result") or "").strip() or None,
            }
            self._add_match(Match(
                date=match_date,
                home_team=row["home"].strip(),
                away_team=row["away"].strip(),
                home_goals=parse_int(row["home_goal"]),
                away_goals=parse_int(row["away_goal"]),
                competition=competition,
                season=season,
                home_key=canonical_team_key(row["home"]),
                away_key=canonical_team_key(row["away"]),
                kickoff=(row.get("time") or "").strip() or None,
                source="BR-Football-Dataset.csv",
                stats=stats,
            ))

    def _load_players(self) -> None:
        path = self.data_dir / "fifa_data.csv"
        if not path.exists():
            return
        for row in _read_rows(path):
            skills = {
                col: _parse_skill(row.get(col, ""))
                for col in _SKILL_COLUMNS
                if _parse_skill(row.get(col, "")) is not None
            }
            player = Player(
                id=(row.get("ID") or "").strip(),
                name=row["Name"].strip(),
                age=parse_int(row.get("Age")),
                nationality=row.get("Nationality", "").strip(),
                overall=parse_int(row.get("Overall")),
                potential=parse_int(row.get("Potential")),
                club=row.get("Club", "").strip(),
                position=(row.get("Position") or "").strip() or None,
                jersey_number=parse_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip() or None,
                weight=(row.get("Weight") or "").strip() or None,
                preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                value=(row.get("Value") or "").strip() or None,
                wage=(row.get("Wage") or "").strip() or None,
                club_key=canonical_team_key(row.get("Club", "")),
                skills=skills,
            )
            self.players.append(player)

    def _learn_aliases(self) -> dict[str, tuple[str, str | None]]:
        """Detect team-key splits across sources and derive new aliases.

        Two rows describing the same fixture (same competition, season,
        score and date within one day) where one team key matches exactly
        and the other differs prove that the two spellings are the same
        club. The differing key of the later-loaded row is mapped onto the
        key of the first-loaded row as a new BASE_ALIASES entry, provided
        the names are compatible (same state suffix, or the suffixless
        side reduces to the other's tokens after dropping legal-form
        words like 'EC', 'FC', 'Clube'). Strict compatibility guards
        against merging genuinely different clubs (e.g. Atletico Nacional
        vs Atletico-MG).
        """
        legal_tokens = {
            "fc", "ec", "sc", "ac", "aa", "ca", "ce", "ge", "se", "ae",
            "ad", "de", "clube", "club", "esporte", "futebol", "cr", "cs",
            "sp", "pa", "urt", "gremio", "club atletico", "fr", "ltda",
            "sa", "sd", "fbc", "ecb", "sl",
        }

        def parts(key: str) -> tuple[str, str | None]:
            if "-" in key:
                base, suffix = key.rsplit("-", 1)
                return base, suffix
            return key, None

        def compatible(k1: str, k2: str) -> bool:
            b1, s1 = parts(k1)
            b2, s2 = parts(k2)
            if b1 == b2:
                return k1 == k2 or s1 is None or s2 is None
            if s1 and s2:
                if s1 != s2:
                    return False
                return set(b1.split()) <= set(b2.split()) or set(b2.split()) <= set(b1.split())
            if s2 is None and s1:
                core = [t for t in b2.split() if t not in legal_tokens]
                return set(core) <= set(b1.split())
            if s1 is None and s2:
                core = [t for t in b1.split() if t not in legal_tokens]
                return set(core) <= set(b2.split())
            return False

        from normalize import BASE_ALIASES

        by_fixture: dict[tuple, list[Match]] = defaultdict(list)
        for match in self.matches:
            if match.score and match.date is not None and match.season is not None:
                for delta in (-1, 0, 1):
                    ordinal = match.date.toordinal() + delta
                    by_fixture[
                        (
                            match.competition,
                            match.season,
                            ordinal,
                            match.score,
                            match.away_key,
                        )
                    ].append(match)
                    by_fixture[
                        (
                            match.competition,
                            match.season,
                            ordinal,
                            match.score,
                            ("h", match.home_key),
                        )
                    ].append(match)
                    by_fixture[
                        ("any", match.competition, match.season, ordinal, match.score)
                    ].append(match)

        learned: dict[str, tuple[str, str | None]] = {}
        seen_pairs: set[tuple] = set()
        position = {id(m): i for i, m in enumerate(self.matches)}
        for bucket in by_fixture.values():
            if len(bucket) < 2:
                continue
            for i, m1 in enumerate(bucket):
                for m2 in bucket[i + 1:]:
                    if m1 is m2:
                        continue
                    if position[id(m1)] > position[id(m2)]:
                        m1, m2 = m2, m1
                    pairs = []
                    if m1.home_key == m2.home_key and m1.away_key != m2.away_key:
                        pairs = [(m2.away_key, m1.away_key)]
                    elif m1.away_key == m2.away_key and m1.home_key != m2.home_key:
                        pairs = [(m2.home_key, m1.home_key)]
                    elif (
                        m1.home_key != m2.home_key
                        and m1.away_key != m2.away_key
                        and compatible(m1.home_key, m2.home_key)
                        and compatible(m1.away_key, m2.away_key)
                    ):
                        pairs = [
                            (m2.home_key, m1.home_key),
                            (m2.away_key, m1.away_key),
                        ]
                    for bad_key, good_key in pairs:
                        if not bad_key or not good_key or not compatible(good_key, bad_key):
                            continue
                        sig = (bad_key, good_key)
                        if sig in seen_pairs:
                            continue
                        seen_pairs.add(sig)
                        bad_base = bad_key.rsplit("-", 1)[0]
                        good_base, good_suffix = parts(good_key)
                        if bad_base in BASE_ALIASES or bad_base in learned:
                            continue
                        learned[bad_base] = (good_base, good_suffix)
        return learned

    def _drop_misfiled_league_matches(self) -> None:
        """Remove stray non-league rows mislabeled as league matches.

        The extended-stats source occasionally tags state-league or cup
        fixtures as Serie A/B (e.g. 'Brasilia FC vs CA Taguatinga' in the
        2016 Serie A). A team appearing in exactly one match of a league
        season is a misfiling: real league participants always play
        several matches, even in partial data.
        """
        league_comps = {SERIE_A, SERIE_B, SERIE_C}
        per_season: dict[tuple[str, int | None], dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for match in self.matches:
            if match.competition in league_comps and match.season is not None:
                per_season[(match.competition, match.season)][match.home_key] += 1
                per_season[(match.competition, match.season)][match.away_key] += 1
        keep: list[Match] = []
        for match in self.matches:
            if match.competition in league_comps and match.season is not None:
                counts = per_season[(match.competition, match.season)]
                if counts[match.home_key] < 2 or counts[match.away_key] < 2:
                    continue
            keep.append(match)
        self.matches = keep

    # ------------------------------------------------------------------
    # Indexes and lookups
    # ------------------------------------------------------------------

    def _build_indexes(self) -> None:
        for match in self.matches:
            self._by_comp_season[(match.competition, match.season)].append(match)
            if match.home_key:
                self._by_team[match.home_key].append(match)
                self.teams[match.home_key].match_count += 1
            if match.away_key:
                self._by_team[match.away_key].append(match)
                self.teams[match.away_key].match_count += 1
        for player in self.players:
            self._players_by_name[_norm_text(player.name)].append(player)
            if player.club_key:
                self._players_by_club[player.club_key].append(player)
                self._register_team(player.club_key, player.club)
                self.teams[player.club_key].player_count += 1
        self.matches.sort(key=lambda m: (m.date or date.min, m.competition))

    def matches_for_team(self, team_key: str) -> list[Match]:
        return self._by_team.get(team_key, [])

    def matches_by_competition(
        self, competition: str | None = None, season: int | None = None
    ) -> list[Match]:
        if competition is None and season is None:
            return list(self.matches)
        result: list[Match] = []
        if competition and season:
            result = self._by_comp_season.get((competition, season), [])
        elif competition:
            for (comp, _), matches in self._by_comp_season.items():
                if comp == competition:
                    result.extend(matches)
        else:
            for (_, sea), matches in self._by_comp_season.items():
                if sea == season:
                    result.extend(matches)
        return sorted(result, key=lambda m: (m.date or date.min, m.competition))

    def seasons_for_competition(self, competition: str) -> list[int]:
        seasons = {
            season
            for (comp, season) in self._by_comp_season
            if comp == competition and season is not None
        }
        return sorted(seasons)

    def competitions(self) -> list[str]:
        return sorted({comp for comp, _ in self._by_comp_season})

    def find_team(self, query: str) -> list[TeamEntry]:
        """Resolve a free-text team name to ranked candidate teams."""
        query = (query or "").strip()
        if not query:
            return []
        key = canonical_team_key(query)
        exact = self.teams.get(key)
        results: list[TeamEntry] = []
        if exact:
            results.append(exact)
        needle = _norm_text(query)
        for team_key, entry in self.teams.items():
            if entry is exact:
                continue
            base = team_key.rsplit("-", 1)[0] if "-" in team_key else team_key
            if (
                needle in base
                or base in needle
                or needle in _norm_text(entry.display)
                or any(
                    needle in _norm_text(v) or _norm_text(v) in needle
                    for v in entry.raw_variants
                )
            ):
                results.append(entry)
        results.sort(key=lambda e: -e.match_count)
        return results

    def search_players_by_name(self, name: str) -> list[Player]:
        needle = _norm_text(name)
        if not needle:
            return []
        exact = self._players_by_name.get(needle, [])
        if exact:
            return list(exact)
        return [
            p for p in self.players if needle in _norm_text(p.name)
        ]

    def players_at_club(self, club_key: str) -> list[Player]:
        return self._players_by_club.get(club_key, [])

    def dataset_overview(self) -> dict:
        per_competition = {}
        for competition in self.competitions():
            seasons = self.seasons_for_competition(competition)
            per_competition[competition] = {
                "matches": len(self.matches_by_competition(competition)),
                "seasons": [f"{s}" for s in seasons],
            }
        nationalities = defaultdict(int)
        for player in self.players:
            nationalities[player.nationality] += 1
        return {
            "total_matches": len(self.matches),
            "total_players": len(self.players),
            "total_teams": len(self.teams),
            "competitions": per_competition,
            "player_nationalities": dict(
                sorted(nationalities.items(), key=lambda kv: -kv[1])[:10]
            ),
        }


def _norm_text(text: str) -> str:
    return " ".join(strip_accents(text).lower().split())


_LOCK = threading.Lock()
_INSTANCE: SoccerData | None = None


def get_data(data_dir: Path = DATA_DIR) -> SoccerData:
    """Return the shared :class:`SoccerData` singleton (lazily loaded).

    Loads the datasets once to learn cross-source team-name aliases from
    duplicate fixtures, then reloads with the expanded alias table so that
    split club identities merge into a single canonical key.
    """
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                first = SoccerData(data_dir)
                aliases = first._learn_aliases()
                if aliases:
                    from normalize import BASE_ALIASES

                    BASE_ALIASES.update(aliases)
                    _INSTANCE = SoccerData(data_dir)
                else:
                    _INSTANCE = first
    return _INSTANCE
