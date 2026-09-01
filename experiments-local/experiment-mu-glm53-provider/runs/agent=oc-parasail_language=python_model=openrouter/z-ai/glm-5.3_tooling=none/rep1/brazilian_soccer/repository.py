"""Data repository: loads, normalises and indexes the six Kaggle datasets.

Context: three of the match files overlap heavily (e.g. the 2012-2019
Brasileirão appears in Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv
and BR-Football-Dataset.csv), teams are spelled differently in every file,
and dates come in ISO and Brazilian formats. This module turns that pile of
CSVs into one curated, de-duplicated in-memory match list plus a player list:

* every raw team/club spelling is resolved to a TeamEntity (two spellings
  denote the same club iff they share the same entity key),
* for every (competition, season) exactly one source file is preferred
  (round-by-round files first, the statistics file last), duplicate rows from
  demoted sources are dropped, and their extended statistics (corners, shots,
  attacks) and stadium names are merged into the kept match,
* the FIFA player table is joined to the same team entities through the
  normalised club key, which is what makes cross-file questions work.

The full raw match list is kept as well so that per-file queries stay
possible (``source=`` filter on match searches).
"""

from __future__ import annotations

import csv
import logging
from collections import Counter, defaultdict
from pathlib import Path

from .models import Match, Player, TeamEntity, position_group
from .normalize import (
    clean_text,
    is_nothing,
    parse_date,
    parse_int,
    split_team,
    strip_accents,
)

logger = logging.getLogger("brazilian_soccer.repository")

SERIE_A = "Brasileirão Serie A"
SERIE_B = "Brasileirão Serie B"
SERIE_C = "Brasileirão Serie C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

COMPETITION_ALIASES = {
    SERIE_A: SERIE_A,
    SERIE_B: SERIE_B,
    SERIE_C: SERIE_C,
    COPA_DO_BRASIL: COPA_DO_BRASIL,
    LIBERTADORES: LIBERTADORES,
    "brasileirao": SERIE_A,
    "brasileirao serie a": SERIE_A,
    "serie a": SERIE_A,
    "campeonato brasileiro": SERIE_A,
    "serie b": SERIE_B,
    "brasileirao serie b": SERIE_B,
    "serie c": SERIE_C,
    "brasileirao serie c": SERIE_C,
    "copa": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "copa do brasil": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "conmebol libertadores": LIBERTADORES,
    "libertadores cup": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
}

BR_FOOTBALL_TOURNAMENTS = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}

SOURCE_PREFERENCE = {
    SERIE_A: (
        "Brasileirao_Matches.csv",
        "novo_campeonato_brasileiro.csv",
        "BR-Football-Dataset.csv",
    ),
    SERIE_B: ("BR-Football-Dataset.csv",),
    SERIE_C: ("BR-Football-Dataset.csv",),
    COPA_DO_BRASIL: (
        "Brazilian_Cup_Matches.csv",
        "BR-Football-Dataset.csv",
    ),
    LIBERTADORES: ("Libertadores_Matches.csv",),
}

DATA_FILES = (
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
    "fifa_data.csv",
)


class TeamRegistry:
    """Resolves every spelling of a club name to a stable team entity."""

    def __init__(self) -> None:
        self._raw_pairs: dict[str, tuple[str, str | None]] = {}
        self._variant_counts: dict[tuple[str, str | None], Counter] = defaultdict(Counter)
        self._base_quals: dict[str, set] = defaultdict(set)
        self._raw_to_key: dict[str, str] = {}
        self.entities: dict[str, TeamEntity] = {}

    def register(self, raw_name: str | None) -> None:
        """Count one occurrence of a raw spelling (call per CSV row)."""
        if not raw_name or is_nothing(raw_name):
            return
        raw_name = raw_name.strip()
        pair = split_team(raw_name)
        if not pair[0]:
            return
        if raw_name not in self._raw_pairs:
            self._raw_pairs[raw_name] = pair
        self._variant_counts[pair][raw_name] += 1

    def finalize(self) -> None:
        for (base, qual) in self._variant_counts:
            self._base_quals[base].add(qual)
        for raw_name, (base, qual) in self._raw_pairs.items():
            self._raw_to_key[raw_name] = self._entity_key(base, qual)
        for (base, qual), counter in self._variant_counts.items():
            key = self._entity_key(base, qual)
            entity = self.entities.get(key)
            if entity is None:
                entity = TeamEntity(
                    key=key,
                    display=self._pick_display(key, base, counter),
                    variants=[],
                )
                self.entities[key] = entity
            if qual:
                entity.qualifiers.add(qual)
            else:
                entity.qualifiers.add(None)
            for variant, _count in counter.most_common():
                if variant not in entity.variants:
                    entity.variants.append(variant)

    def _entity_key(self, base: str, qual: str | None) -> str:
        quals = {q for q in self._base_quals.get(base, set()) if q}
        if len(quals) <= 1:
            return base
        return f"{base} {qual}" if qual else base

    def _pick_display(self, key: str, base: str, counter: Counter) -> str:
        display = counter.most_common(1)[0][0]
        if key == base:
            quals = (self._base_quals.get(base) or {None}) - {None}
            if quals:
                suffix = next(iter(quals))
                lowered = strip_accents(display).lower()
                for token in (f"-{suffix}", f"- {suffix}", f" {suffix}"):
                    if lowered.endswith(token):
                        cut = len(display) - len(token)
                        display = display[:cut]
                        break
        return display.strip() or base

    def key_for(self, raw_name: str | None) -> str:
        if not raw_name or is_nothing(raw_name):
            return ""
        key = self._raw_to_key.get(raw_name.strip())
        if key is not None:
            return key
        return split_team(raw_name)[0]

    def display_for(self, raw_name: str | None) -> str:
        if not raw_name or is_nothing(raw_name):
            return (raw_name or "").strip()
        key = self.key_for(raw_name)
        entity = self.entities.get(key)
        return entity.display if entity else raw_name.strip()

    def resolve(self, query: str | None) -> list[TeamEntity]:
        """Resolve a user-supplied team name to matching entities.

        Exact matches win; otherwise all entities sharing the base name are
        returned (e.g. "atletico" -> Atlético-MG, -GO and -PR); finally a
        substring fallback catches partial spellings.
        """
        if not query or is_nothing(query):
            return []
        base, qual = split_team(query)
        if not base:
            return []
        if qual and f"{base} {qual}" in self.entities:
            return [self.entities[f"{base} {qual}"]]
        if base in self.entities:
            return [self.entities[base]]
        same_base = [
            entity
            for key, entity in self.entities.items()
            if key == base
            or (
                key.startswith(base + " ")
                and key.rsplit(" ", 1)[-1] in (entity.qualifiers - {None})
            )
        ]
        if same_base:
            return sorted(same_base, key=lambda entity: entity.key)
        substring = [
            entity for key, entity in self.entities.items() if base in key
        ]
        return sorted(substring, key=lambda entity: entity.key)

    def all_entities(self) -> list[TeamEntity]:
        return sorted(self.entities.values(), key=lambda entity: entity.key)


class DataRepository:
    """Loads all datasets once and answers queries from memory."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data" / "kaggle"
        self.data_dir = Path(data_dir)
        self.registry = TeamRegistry()
        self.matches: list[Match] = []
        self.raw_matches: list[Match] = []
        self.players: list[Player] = []
        self.load_report: dict = {}
        self.competition_info: dict = {}
        self.final_rounds: dict[int, int] = {}
        self._by_entity: dict[str, list[Match]] = defaultdict(list)
        self._merge_stats_count = 0
        self._shadowed_count = 0
        self._load()

    # ------------------------------------------------------------------ load

    def _read_csv(self, filename: str) -> list[dict]:
        path = self.data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Required dataset file not found: {path}")
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _load(self) -> None:
        parsed = {name: self._read_csv(name) for name in DATA_FILES}
        self._register_teams(parsed)
        self.registry.finalize()

        builders = [
            self._build_brasileirao,
            self._build_cup,
            self._build_libertadores,
            self._build_br_football,
            self._build_novo,
        ]
        raw_matches: list[Match] = []
        reports: dict[str, dict] = {}
        for builder in builders:
            matches, report = builder(parsed)
            raw_matches.extend(matches)
            reports[report.pop("file")] = report
        self.raw_matches = raw_matches

        self.matches = self._curate(raw_matches)
        self._build_indexes()
        self.players, player_report = self._build_players(parsed["fifa_data.csv"])
        reports["fifa_data.csv"] = player_report
        self._build_competition_info()
        self._build_load_report(reports)

    def _register_teams(self, parsed: dict) -> None:
        for row in parsed["Brasileirao_Matches.csv"]:
            self.registry.register(row.get("home_team"))
            self.registry.register(row.get("away_team"))
        for row in parsed["Brazilian_Cup_Matches.csv"]:
            self.registry.register(row.get("home_team"))
            self.registry.register(row.get("away_team"))
        for row in parsed["Libertadores_Matches.csv"]:
            self.registry.register(row.get("home_team"))
            self.registry.register(row.get("away_team"))
        for row in parsed["BR-Football-Dataset.csv"]:
            self.registry.register(row.get("home"))
            self.registry.register(row.get("away"))
        for row in parsed["novo_campeonato_brasileiro.csv"]:
            self.registry.register(row.get("Equipe_mandante"))
            self.registry.register(row.get("Equipe_visitante"))
        for row in parsed["fifa_data.csv"]:
            self.registry.register(row.get("Club"))

    # ----------------------------------------------------------- match files

    def _skip_reason(
        self,
        row: dict,
        *,
        goals: tuple,
        teams: tuple,
        season,
    ) -> str | None:
        for field in teams:
            if is_nothing(row.get(field)):
                return f"missing team ({field})"
        if parse_int(season) is None:
            return "missing season"
        if parse_date(row.get(goals[0]))[0] is None:
            return "missing date"
        if parse_int(row.get(goals[1])) is None or parse_int(row.get(goals[2])) is None:
            return "missing goals"
        return None

    def _make_match(
        self,
        *,
        competition: str,
        season,
        match_date,
        match_time,
        home_raw,
        away_raw,
        home_goals,
        away_goals,
        round_no=None,
        stage=None,
        stadium=None,
        source="",
        stats=None,
    ) -> Match:
        return Match(
            date=match_date,
            time=match_time,
            competition=competition,
            season=int(season),
            home_team=self.registry.key_for(home_raw),
            away_team=self.registry.key_for(away_raw),
            home_display=self.registry.display_for(home_raw),
            away_display=self.registry.display_for(away_raw),
            home_goals=parse_int(home_goals),
            away_goals=parse_int(away_goals),
            round=parse_int(round_no),
            stage=stage,
            stadium=stadium,
            source=source,
            **(stats or {}),
        )

    def _build_brasileirao(self, parsed: dict) -> tuple[list[Match], dict]:
        report = {
            "file": "Brasileirao_Matches.csv",
            "rows": len(parsed["Brasileirao_Matches.csv"]),
            "loaded": 0,
            "skipped": 0,
        }
        matches: list[Match] = []
        for row in parsed["Brasileirao_Matches.csv"]:
            reason = self._skip_reason(
                row,
                goals=("datetime", "home_goal", "away_goal"),
                teams=("home_team", "away_team"),
                season=row.get("season"),
            )
            if reason:
                report["skipped"] += 1
                continue
            match_date, match_time = parse_date(row["datetime"])
            matches.append(
                self._make_match(
                    competition=SERIE_A,
                    season=row["season"],
                    match_date=match_date,
                    match_time=match_time,
                    home_raw=row["home_team"],
                    away_raw=row["away_team"],
                    home_goals=row["home_goal"],
                    away_goals=row["away_goal"],
                    round_no=row.get("round"),
                    source="Brasileirao_Matches.csv",
                )
            )
        report["loaded"] = len(matches)
        return matches, report

    def _build_cup(self, parsed: dict) -> tuple[list[Match], dict]:
        report = {
            "file": "Brazilian_Cup_Matches.csv",
            "rows": len(parsed["Brazilian_Cup_Matches.csv"]),
            "loaded": 0,
            "skipped": 0,
        }
        matches: list[Match] = []
        for row in parsed["Brazilian_Cup_Matches.csv"]:
            reason = self._skip_reason(
                row,
                goals=("datetime", "home_goal", "away_goal"),
                teams=("home_team", "away_team"),
                season=row.get("season"),
            )
            if reason:
                report["skipped"] += 1
                continue
            match_date, match_time = parse_date(row["datetime"])
            matches.append(
                self._make_match(
                    competition=COPA_DO_BRASIL,
                    season=row["season"],
                    match_date=match_date,
                    match_time=match_time,
                    home_raw=row["home_team"],
                    away_raw=row["away_team"],
                    home_goals=row["home_goal"],
                    away_goals=row["away_goal"],
                    round_no=row.get("round"),
                    source="Brazilian_Cup_Matches.csv",
                )
            )
        report["loaded"] = len(matches)
        return matches, report

    def _build_libertadores(self, parsed: dict) -> tuple[list[Match], dict]:
        report = {
            "file": "Libertadores_Matches.csv",
            "rows": len(parsed["Libertadores_Matches.csv"]),
            "loaded": 0,
            "skipped": 0,
        }
        matches: list[Match] = []
        for row in parsed["Libertadores_Matches.csv"]:
            reason = self._skip_reason(
                row,
                goals=("datetime", "home_goal", "away_goal"),
                teams=("home_team", "away_team"),
                season=row.get("season"),
            )
            if reason:
                report["skipped"] += 1
                continue
            match_date, match_time = parse_date(row["datetime"])
            stage = clean_text(row.get("stage")) or None
            matches.append(
                self._make_match(
                    competition=LIBERTADORES,
                    season=row["season"],
                    match_date=match_date,
                    match_time=match_time,
                    home_raw=row["home_team"],
                    away_raw=row["away_team"],
                    home_goals=row["home_goal"],
                    away_goals=row["away_goal"],
                    stage=stage,
                    source="Libertadores_Matches.csv",
                )
            )
        report["loaded"] = len(matches)
        return matches, report

    def _build_br_football(self, parsed: dict) -> tuple[list[Match], dict]:
        rows = parsed["BR-Football-Dataset.csv"]
        report = {
            "file": "BR-Football-Dataset.csv",
            "rows": len(rows),
            "loaded": 0,
            "skipped": 0,
        }
        matches: list[Match] = []
        for row in rows:
            tournament = row.get("tournament")
            competition = BR_FOOTBALL_TOURNAMENTS.get(tournament or "")
            if competition is None:
                report["skipped"] += 1
                continue
            date_text = row.get("date") or ""
            reason = self._skip_reason(
                row,
                goals=("date", "home_goal", "away_goal"),
                teams=("home", "away"),
                season=date_text[:4],
            )
            if reason:
                report["skipped"] += 1
                continue
            match_date, _ = parse_date(row["date"])
            match_time = (row.get("time") or "")[:5] or None
            stats = {
                "home_corners": parse_int(row.get("home_corner")),
                "away_corners": parse_int(row.get("away_corner")),
                "home_shots": parse_int(row.get("home_shots")),
                "away_shots": parse_int(row.get("away_shots")),
                "home_attacks": parse_int(row.get("home_attack")),
                "away_attacks": parse_int(row.get("away_attack")),
            }
            matches.append(
                self._make_match(
                    competition=competition,
                    season=date_text[:4],
                    match_date=match_date,
                    match_time=match_time,
                    home_raw=row["home"],
                    away_raw=row["away"],
                    home_goals=row["home_goal"],
                    away_goals=row["away_goal"],
                    source="BR-Football-Dataset.csv",
                    stats=stats,
                )
            )
        report["loaded"] = len(matches)
        return matches, report

    def _build_novo(self, parsed: dict) -> tuple[list[Match], dict]:
        rows = parsed["novo_campeonato_brasileiro.csv"]
        report = {
            "file": "novo_campeonato_brasileiro.csv",
            "rows": len(rows),
            "loaded": 0,
            "skipped": 0,
        }
        matches: list[Match] = []
        for row in rows:
            reason = self._skip_reason(
                row,
                goals=("Data", "Gols_mandante", "Gols_visitante"),
                teams=("Equipe_mandante", "Equipe_visitante"),
                season=row.get("Ano"),
            )
            if reason:
                report["skipped"] += 1
                continue
            match_date, _ = parse_date(row["Data"])
            stadium = (row.get("Arena") or "").strip() or None
            matches.append(
                self._make_match(
                    competition=SERIE_A,
                    season=row["Ano"],
                    match_date=match_date,
                    match_time=None,
                    home_raw=row["Equipe_mandante"],
                    away_raw=row["Equipe_visitante"],
                    home_goals=row["Gols_mandante"],
                    away_goals=row["Gols_visitante"],
                    round_no=row.get("Rodada"),
                    stadium=stadium,
                    source="novo_campeonato_brasileiro.csv",
                )
            )
        report["loaded"] = len(matches)
        return matches, report

    # ---------------------------------------------------------------- players

    _PLAYER_CORE = frozenset(
        {
            "", "ID", "Name", "Age", "Nationality", "Overall", "Potential",
            "Club", "Position", "Jersey Number", "Height", "Weight",
            "Preferred Foot", "Value", "Wage",
        }
    )
    _PLAYER_MEDIA = frozenset({"Photo", "Flag", "Club Logo", "Real Face"})

    def _build_players(self, rows: list[dict]) -> tuple[list[Player], dict]:
        report = {"rows": len(rows), "loaded": 0, "skipped": 0}
        players: list[Player] = []
        for row in rows:
            fifa_id = parse_int(row.get("ID"))
            name = (row.get("Name") or "").strip()
            if fifa_id is None or not name:
                report["skipped"] += 1
                continue
            club = (row.get("Club") or "").strip() or None
            position = (row.get("Position") or "").strip().upper() or None
            attributes = {
                key: value
                for key, value in row.items()
                if key not in self._PLAYER_CORE
                and key not in self._PLAYER_MEDIA
                and value not in (None, "")
            }
            players.append(
                Player(
                    fifa_id=fifa_id,
                    name=name,
                    age=parse_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=parse_int(row.get("Overall")),
                    potential=parse_int(row.get("Potential")),
                    club=club,
                    club_key=self.registry.key_for(club) if club else "",
                    position=position,
                    position_group=position_group(position),
                    jersey=parse_int(row.get("Jersey Number")),
                    height=(row.get("Height") or "").strip() or None,
                    weight=(row.get("Weight") or "").strip() or None,
                    preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                    value=(row.get("Value") or "").strip() or None,
                    wage=(row.get("Wage") or "").strip() or None,
                    attributes=attributes,
                )
            )
        report["loaded"] = len(players)
        return players, report

    # --------------------------------------------------------------- curation

    @staticmethod
    def _dedup_key(match: Match) -> tuple:
        return (match.date, match.home_team, match.away_team, match.home_goals, match.away_goals)

    def _curate(self, raw_matches: list[Match]) -> list[Match]:
        groups: dict[tuple, list[Match]] = defaultdict(list)
        for match in raw_matches:
            groups[(match.competition, match.season)].append(match)
        curated: list[Match] = []
        merged_stats = 0
        shadowed = 0
        for (_competition, _season), group in groups.items():
            competition = _competition
            preference = SOURCE_PREFERENCE[competition]
            present = {match.source for match in group}
            chosen = next((src for src in preference if src in present), None)
            if chosen is None:
                curated.extend(group)
                continue
            kept: dict[tuple, Match] = {}
            for match in group:
                if match.source == chosen:
                    kept.setdefault(self._dedup_key(match), match)
            for match in group:
                if match.source == chosen:
                    continue
                target = kept.get(self._dedup_key(match))
                if target is None:
                    shadowed += 1
                    continue
                merged_stats += self._merge(target, match)
            curated.extend(kept.values())
        curated.sort(key=lambda match: match.sort_key)
        self._merge_stats_count = merged_stats
        self._shadowed_count = shadowed
        return curated

    @staticmethod
    def _merge(target: Match, donor: Match) -> int:
        merged = 0
        for field in (
            "stadium",
            "home_corners", "away_corners",
            "home_shots", "away_shots",
            "home_attacks", "away_attacks",
        ):
            if getattr(target, field) is None and getattr(donor, field) is not None:
                setattr(target, field, getattr(donor, field))
                merged += 1
        return merged

    # ---------------------------------------------------------------- indexes

    def _build_indexes(self) -> None:
        self._by_entity = defaultdict(list)
        for match in self.matches:
            self._by_entity[match.home_team].append(match)
            self._by_entity[match.away_team].append(match)
        cup_rounds: dict[int, set] = defaultdict(set)
        for match in self.matches:
            if match.competition == COPA_DO_BRASIL and match.round is not None:
                cup_rounds[match.season].add(match.round)
        self.final_rounds = {season: max(rounds) for season, rounds in cup_rounds.items()}

    def matches_for_entity(self, key: str) -> list[Match]:
        return self._by_entity.get(key, [])

    # ------------------------------------------------------------ competition

    @staticmethod
    def canonical_competition(name: str | None) -> str | None:
        if not name or is_nothing(name):
            return None
        return COMPETITION_ALIASES.get(clean_text(name))

    def list_competitions(self) -> list[str]:
        return sorted({match.competition for match in self.matches})

    def _build_competition_info(self) -> None:
        info: dict[str, dict] = {}
        for match in self.matches:
            entry = info.setdefault(
                match.competition,
                {"seasons": {}, "aliases": [], "total_matches": 0},
            )
            entry["total_matches"] += 1
            season = entry["seasons"].setdefault(
                match.season,
                {"matches": 0, "source": match.source, "teams": set()},
            )
            season["matches"] += 1
            season["teams"].add(match.home_team)
            season["teams"].add(match.away_team)
        for competition, entry in info.items():
            entry["aliases"] = sorted(
                alias
                for alias, canon in COMPETITION_ALIASES.items()
                if canon == competition and alias != competition
            )
            for season in entry["seasons"].values():
                season["teams"] = len(season["teams"])
        self.competition_info = info

    def _build_load_report(self, reports: dict) -> None:
        self.load_report = {
            "data_dir": str(self.data_dir),
            "files": reports,
            "matches_loaded_raw": len(self.raw_matches),
            "matches_curated": len(self.matches),
            "duplicates_shadowed": self._shadowed_count,
            "stats_fields_merged": self._merge_stats_count,
            "players_loaded": len(self.players),
            "team_entities": len(self.registry.entities),
        }

    # --------------------------------------------------------------- lookups

    def resolve_team(self, query: str | None) -> list[TeamEntity]:
        return self.registry.resolve(query)

    def entity(self, key: str) -> TeamEntity | None:
        return self.registry.entities.get(key)
