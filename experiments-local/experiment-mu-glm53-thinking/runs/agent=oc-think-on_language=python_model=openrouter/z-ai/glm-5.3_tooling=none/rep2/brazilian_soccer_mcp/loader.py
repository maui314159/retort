"""Dataset loading for the Brazilian Soccer MCP server.

Reads the six CSV datasets from ``data/kaggle`` and produces:

- :attr:`SoccerData.matches` — every match row from the five match files,
  canonicalised and enriched with extended statistics where available;
- :attr:`SoccerData.primary_matches` — a de-duplicated "best view" of every
  (competition, season) that avoids double counting when several datasets
  describe the same fixture (e.g. the 2012-2019 Série A appears in both
  ``Brasileirao_Matches.csv`` and ``novo_campeonato_brasileiro.csv``);
- :attr:`SoccerData.players` — the FIFA player dataset.

Season attribution note: the BR-Football dataset has no season column.  For
league competitions (Série A/B/C) Brazilian seasons run roughly May-December,
so January/February rows belong to the *previous* year's season (this is the
COVID-delayed 2020 season finishing in early 2021).  Cup matches keep the
calendar year.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from .models import Match, Player
from .normalize import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    normalize_team_id,
    parse_date,
    parse_datetime,
    team_display_name,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "kaggle"

#: source dataset ids (kept stable for filtering queries by provenance)
SRC_BRASILEIRAO = "brasileirao_matches"
SRC_NOVO = "novo_campeonato_brasileiro"
SRC_CUP = "brazilian_cup_matches"
SRC_LIBERTADORES = "libertadores_matches"
SRC_BR_FOOTBALL = "br_football_dataset"
SRC_FIFA = "fifa_dataset"

#: Preferred dataset per competition, best first.  For a given
#: (competition, season) the first source that has data wins.
SOURCE_PRIORITY: dict[str, tuple[str, ...]] = {
    SERIE_A: (SRC_BRASILEIRAO, SRC_NOVO, SRC_BR_FOOTBALL),
    SERIE_B: (SRC_BR_FOOTBALL,),
    SERIE_C: (SRC_BR_FOOTBALL,),
    COPA_DO_BRASIL: (SRC_CUP, SRC_BR_FOOTBALL),
    LIBERTADORES: (SRC_LIBERTADORES,),
}

#: Copa do Brasil round codes (1..8) -> display label.
CUP_ROUND_LABELS = {
    "1": "Round 1",
    "2": "Round 2",
    "3": "Round 3",
    "4": "Round 4",
    "5": "Round of 16",
    "6": "Quarterfinals",
    "7": "Semifinals",
    "8": "Final",
}

_SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
    "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle",
    "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
]


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "-"}:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _parse_money(value) -> Optional[int]:
    """Parse FIFA money strings like '€110.5M' / '€565K' into integer euros."""
    if not value:
        return None
    match = re.match(r"€?([\d.]+)\s*([KM]?)", str(value).strip())
    if not match:
        return None
    try:
        amount = float(match.group(1))
    except ValueError:
        return None
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000}[match.group(2)]
    return int(amount * multiplier)


def _kickoff_time(raw: str) -> Optional[str]:
    """Extract HH:MM from a timestamp column, dropping seconds."""
    parsed = parse_datetime(raw)
    return parsed.strftime("%H:%M") if (parsed and (parsed.hour or parsed.minute)) else None


class SoccerData:
    """In-memory repository of matches and players with lookup indexes."""

    def __init__(self, matches: list[Match], players: list[Player]) -> None:
        self.matches = matches
        self.players = players
        self.primary_matches = self._select_primary_matches()
        self._attach_extended_stats()
        self._build_indexes()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, data_dir: str | Path = DEFAULT_DATA_DIR) -> "SoccerData":
        """Load every dataset found in ``data_dir``."""
        directory = Path(data_dir)
        loaders: list[Callable[[Path], list[Match]]] = [
            cls._load_brasileirao,
            cls._load_novo,
            cls._load_cup,
            cls._load_libertadores,
            cls._load_br_football,
        ]
        matches: list[Match] = []
        for loader in loaders:
            matches.extend(loader(directory))
        players = cls._load_fifa(directory)
        return cls(matches, players)

    @staticmethod
    def _read_rows(path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _season_from_int(value) -> Optional[int]:
        return _to_int(value)

    @classmethod
    def _load_brasileirao(cls, directory: Path) -> list[Match]:
        rows = cls._read_rows(directory / "Brasileirao_Matches.csv")
        out = []
        for row in rows:
            out.append(
                Match(
                    competition=SERIE_A,
                    season=cls._season_from_int(row.get("season")),
                    home_team=team_display_name(normalize_team_id(row.get("home_team", ""))),
                    away_team=team_display_name(normalize_team_id(row.get("away_team", ""))),
                    home_goals=_to_int(row.get("home_goal")),
                    away_goals=_to_int(row.get("away_goal")),
                    date=parse_date(row.get("datetime", "")),
                    time=_kickoff_time(row.get("datetime", "")),
                    round=f"Round {_to_int(row.get('round')) or ''}".strip() or None,
                    source=SRC_BRASILEIRAO,
                )
            )
        return out

    @classmethod
    def _load_novo(cls, directory: Path) -> list[Match]:
        rows = cls._read_rows(directory / "novo_campeonato_brasileiro.csv")
        out = []
        for row in rows:
            out.append(
                Match(
                    competition=SERIE_A,
                    season=cls._season_from_int(row.get("Ano")),
                    home_team=team_display_name(normalize_team_id(row.get("Equipe_mandante", ""))),
                    away_team=team_display_name(normalize_team_id(row.get("Equipe_visitante", ""))),
                    home_goals=_to_int(row.get("Gols_mandante")),
                    away_goals=_to_int(row.get("Gols_visitante")),
                    date=parse_date(row.get("Data", "")),
                    round=f"Round {_to_int(row.get('Rodada')) or ''}".strip() or None,
                    venue=(row.get("Arena") or "").strip() or None,
                    source=SRC_NOVO,
                )
            )
        return out

    @classmethod
    def _load_cup(cls, directory: Path) -> list[Match]:
        rows = cls._read_rows(directory / "Brazilian_Cup_Matches.csv")
        out = []
        for row in rows:
            label = CUP_ROUND_LABELS.get(str(row.get("round", "")).strip())
            if label is None:
                label = f"Round {row.get('round', '').strip()}".strip()
            out.append(
                Match(
                    competition=COPA_DO_BRASIL,
                    season=cls._season_from_int(row.get("season")),
                    home_team=team_display_name(normalize_team_id(row.get("home_team", ""))),
                    away_team=team_display_name(normalize_team_id(row.get("away_team", ""))),
                    home_goals=_to_int(row.get("home_goal")),
                    away_goals=_to_int(row.get("away_goal")),
                    date=parse_date(row.get("datetime", "")),
                    time=_kickoff_time(row.get("datetime", "")),
                    round=label,
                    source=SRC_CUP,
                )
            )
        return out

    @classmethod
    def _load_libertadores(cls, directory: Path) -> list[Match]:
        rows = cls._read_rows(directory / "Libertadores_Matches.csv")
        out = []
        for row in rows:
            stage = (row.get("stage") or "").strip() or None
            out.append(
                Match(
                    competition=LIBERTADORES,
                    season=cls._season_from_int(row.get("season")),
                    home_team=team_display_name(normalize_team_id(row.get("home_team", ""))),
                    away_team=team_display_name(normalize_team_id(row.get("away_team", ""))),
                    home_goals=_to_int(row.get("home_goal")),
                    away_goals=_to_int(row.get("away_goal")),
                    date=parse_date(row.get("datetime", "")),
                    time=_kickoff_time(row.get("datetime", "")),
                    stage=stage.title() if stage else None,
                    source=SRC_LIBERTADORES,
                )
            )
        return out

    @staticmethod
    def _br_football_season(row: dict[str, str], competition: str) -> Optional[int]:
        """Derive the season for a BR-Football row from its date.

        League seasons run May-December; January/February fixtures belong to
        the previous year's season (COVID-era calendar).  Cup competitions
        use the calendar year.
        """
        match_date = parse_date(row.get("date", ""))
        if match_date is None:
            return None
        if competition in (SERIE_A, SERIE_B, SERIE_C) and match_date.month in (1, 2):
            return match_date.year - 1
        return match_date.year

    @classmethod
    def _load_br_football(cls, directory: Path) -> list[Match]:
        rows = cls._read_rows(directory / "BR-Football-Dataset.csv")
        tournament_map = {"Serie A": SERIE_A, "Serie B": SERIE_B, "Serie C": SERIE_C}
        out = []
        for row in rows:
            raw_tournament = (row.get("tournament") or "").strip()
            if raw_tournament in tournament_map:
                competition = tournament_map[raw_tournament]
            elif raw_tournament == "Copa do Brasil":
                competition = COPA_DO_BRASIL
            else:
                competition = raw_tournament
            out.append(
                Match(
                    competition=competition,
                    season=cls._br_football_season(row, competition),
                    home_team=team_display_name(normalize_team_id(row.get("home", ""))),
                    away_team=team_display_name(normalize_team_id(row.get("away", ""))),
                    home_goals=_to_int(row.get("home_goal")),
                    away_goals=_to_int(row.get("away_goal")),
                    date=parse_date(row.get("date", "")),
                    time=_kickoff_time(row.get("time", "")),
                    venue=None,
                    home_corners=_to_int(row.get("home_corner")),
                    away_corners=_to_int(row.get("away_corner")),
                    home_shots=_to_int(row.get("home_shots")),
                    away_shots=_to_int(row.get("away_shots")),
                    home_attacks=_to_int(row.get("home_attack")),
                    away_attacks=_to_int(row.get("away_attack")),
                    source=SRC_BR_FOOTBALL,
                )
            )
        return out

    @classmethod
    def _load_fifa(cls, directory: Path) -> list[Player]:
        rows = cls._read_rows(directory / "fifa_data.csv")
        players = []
        for row in rows:
            club = (row.get("Club") or "").strip()
            skills = {}
            for column in _SKILL_COLUMNS:
                raw = row.get(column)
                if raw is None:
                    continue
                text = str(raw).strip()
                if text and text.upper() not in {"NA", "N/A", "-"}:
                    try:
                        skills[column] = int(float(text))
                    except ValueError:
                        continue
            players.append(
                Player(
                    id=_to_int(row.get("ID")) or 0,
                    name=(row.get("Name") or "").strip(),
                    age=_to_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip() or None,
                    overall=_to_int(row.get("Overall")),
                    potential=_to_int(row.get("Potential")),
                    club=club or None,
                    position=(row.get("Position") or "").strip() or None,
                    jersey_number=_to_int(row.get("Jersey Number")),
                    preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                    value_eur=_parse_money(row.get("Value")),
                    wage_eur=_parse_money(row.get("Wage")),
                    skills=skills,
                )
            )
        return players

    # ------------------------------------------------------------------
    # De-duplication and enrichment
    # ------------------------------------------------------------------

    def _select_primary_matches(self) -> list[Match]:
        """Choose one authoritative source per (competition, season).

        Sources are tried in :data:`SOURCE_PRIORITY` order, but a source is
        skipped when more than 5% of its rows lack a score (e.g. the 2022
        Série A is unfinished in ``Brasileirao_Matches.csv`` while the
        BR-Football dataset has complete results for that season).  When no
        source reaches the threshold, the most complete one wins.
        """
        by_source: dict[tuple[str, Optional[int]], dict[str, list[Match]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for match in self.matches:
            by_source[(match.competition, match.season)][match.source].append(match)

        primary: list[Match] = []
        for source_map in by_source.values():
            priority = None  # resolved per competition below
            competition = next(iter(source_map.values()))[0].competition
            priority = SOURCE_PRIORITY.get(competition, ())
            ranked = sorted(
                source_map.items(),
                key=lambda item: (
                    priority.index(item[0]) if item[0] in priority else len(priority),
                    -sum(1 for m in item[1] if m.is_played),
                ),
            )
            chosen = None
            for source_id, matches in ranked:
                played = sum(1 for m in matches if m.is_played)
                if matches and played / len(matches) >= 0.95:
                    chosen = matches
                    break
            if chosen is None:
                chosen = ranked[0][1]
            primary.extend(chosen)
        primary.sort(key=lambda m: (m.competition, m.season or 0, m.date or date.min))
        return primary

    def _attach_extended_stats(self) -> None:
        """Copy BR-Football corner/shot/attack stats onto primary matches.

        BR-Football often duplicates fixtures already covered by the
        dedicated files but is the only source of extended statistics, so
        the numbers are joined onto the primary match objects by
        (competition, season, teams) whenever that fixture is unique.
        """
        primary_by_fixture: dict[tuple, list[int]] = defaultdict(list)
        for index, match in enumerate(self.primary_matches):
            key = (match.competition, match.season, match.home_team, match.away_team)
            primary_by_fixture[key].append(index)

        enriched: dict[int, Match] = {}
        for match in self.matches:
            if match.source != SRC_BR_FOOTBALL or match.home_corners is None:
                continue
            key = (match.competition, match.season, match.home_team, match.away_team)
            indexes = primary_by_fixture.get(key)
            if not indexes or len(indexes) != 1:
                continue
            target = self.primary_matches[indexes[0]]
            if target.source == SRC_BR_FOOTBALL:
                continue
            enriched[indexes[0]] = target.with_stats(
                home_corners=match.home_corners,
                away_corners=match.away_corners,
                home_shots=match.home_shots,
                away_shots=match.away_shots,
                home_attacks=match.home_attacks,
                away_attacks=match.away_attacks,
            )
        if enriched:
            self.primary_matches = [
                enriched.get(index, match) for index, match in enumerate(self.primary_matches)
            ]

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    def _build_indexes(self) -> None:
        self.matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self.primary_by_team: dict[str, list[Match]] = defaultdict(list)
        self.primary_by_competition_season: dict[tuple[str, Optional[int]], list[Match]] = (
            defaultdict(list)
        )
        for match in self.matches:
            self.matches_by_team[match.home_team].append(match)
            self.matches_by_team[match.away_team].append(match)
        for match in self.primary_matches:
            self.primary_by_team[match.home_team].append(match)
            self.primary_by_team[match.away_team].append(match)
            self.primary_by_competition_season[(match.competition, match.season)].append(match)

        self.players_by_name: dict[str, list[Player]] = defaultdict(list)
        self.players_by_club: dict[str, list[Player]] = defaultdict(list)
        self.players_by_nationality: dict[str, list[Player]] = defaultdict(list)
        for player in self.players:
            if player.name:
                self.players_by_name[player.name.casefold()].append(player)
            if player.club:
                self.players_by_club[player.club.casefold()].append(player)
            if player.nationality:
                self.players_by_nationality[player.nationality.casefold()].append(player)

        self.known_teams: dict[str, str] = {}
        for team in set(self.matches_by_team):
            self.known_teams[team.casefold()] = team
        for club in set(self.players_by_club):
            self.known_teams.setdefault(club.casefold(), club.title())

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def resolve_team(self, query: str) -> Optional[str]:
        """Resolve a user-supplied team name to a canonical display name.

        Tries exact match, alias/canonical resolution, then substring and
        token containment against every known team.
        """
        text = query.strip()
        if not text:
            return None
        lowered = text.casefold()
        if lowered in self.known_teams:
            return self.known_teams[lowered]

        canonical = team_display_name(normalize_team_id(text))
        if canonical.casefold() in self.known_teams:
            return self.known_teams[canonical.casefold()]

        for known in sorted(self.known_teams):
            if known.startswith(lowered):
                return self.known_teams[known]

        for known in sorted(self.known_teams):
            if lowered in known:
                return self.known_teams[known]
        return None

    def resolve_club_players(self, query: str) -> list[Player]:
        """FIFA players whose club matches a team name in any spelling."""
        resolved = self.resolve_team(query)
        candidates = {resolved.casefold()} if resolved else set()
        candidates.add(query.strip().casefold())
        canonical_id = normalize_team_id(query)
        candidates.add(canonical_id)
        found: dict[int, Player] = {}
        for club_key, players in self.players_by_club.items():
            if club_key in candidates or normalize_team_id(club_key) == canonical_id:
                for player in players:
                    found[player.id] = player
        if found:
            return sorted(found.values(), key=lambda p: (-(p.overall or 0), p.name))
        return []

    def seasons_for_competition(self, competition: str) -> list[int]:
        seasons = {
            season
            for comp, season in self.primary_by_competition_season
            if comp == competition and season is not None
        }
        return sorted(seasons)

    def dataset_stats(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for match in self.matches:
            counts[match.source] += 1
        counts["players"] = len(self.players)
        return dict(counts)
