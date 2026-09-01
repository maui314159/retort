"""CSV data loading and indexing for the Brazilian Soccer MCP Server.

Loads all six Kaggle datasets into a unified, normalized in-memory model:

===========================  =============================================
File                         Content
===========================  =============================================
Brasileirao_Matches.csv      Brasileirão Série A 2012-2021 (primary)
Brazilian_Cup_Matches.csv    Copa do Brasil 2012-2021
Libertadores_Matches.csv    Copa Libertadores 2013-2021
BR-Football-Dataset.csv      Extended stats (corners/shots/attacks) for
                             Brasileirão Série A/B/C and Copa do Brasil
novo_campeonato_brasileiro   Historical Brasileirão 2003-2019 (+ arena)
fifa_data.csv                FIFA player database (18k players)
===========================  =============================================

Duplicate fixtures across files are de-duplicated on
``(competition, date, home team, away team)`` and enriched in place: the
extended-stats file contributes corners/shots/attacks, and the historical
file contributes arena names.  This keeps statistics (standings, head-to-head,
averages) free of double counting.
"""

from __future__ import annotations

import csv
from datetime import date
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import (
    canonical_competition,
    canonical_team,
    competition_key,
    key_team,
    parse_date,
    parse_int,
)

# Default location of the Kaggle datasets relative to the repository root.
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# Files in load order.  Earlier files win on duplicate fixtures; later files
# only enrich them (extra stats, arena).
_MATCH_FILES = (
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
)
_PLAYER_FILE = "fifa_data.csv"

# Minimum appearances for a team to count as a genuine Série A participant
# (a full season is 38 matches; strays appear once or twice).
_LEAGUE_MIN_APPEARANCES = 10

# Generic club words ignored when resolving loose team-name queries.
_GENERIC_CLUB_WORDS = {
    "fc", "clube", "club", "esporte", "esportes", "ec", "sc", "futebol",
    "regatas", "do", "da", "de", "dos", "das", "the",
}


@dataclass
class Match:
    """A single fixture, normalized across all source files."""

    match_id: str
    competition: str  # canonical competition name
    season: int | None
    date: str | None  # ISO YYYY-MM-DD, when known
    home_team: str  # canonical team name
    away_team: str  # canonical team name
    home_goals: int | None
    away_goals: int | None
    round: str | None = None
    stage: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    arena: str | None = None
    source: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def competition_key(self) -> str:
        return competition_key(self.competition)

    @property
    def winner(self) -> str | None:
        """Canonical name of the winning team, or None for draws/unknown."""
        if self.home_goals is None or self.away_goals is None:
            return None
        if self.home_goals > self.away_goals:
            return self.home_team
        if self.away_goals > self.home_goals:
            return self.away_team
        return None

    @property
    def total_goals(self) -> int | None:
        if self.home_goals is None or self.away_goals is None:
            return None
        return self.home_goals + self.away_goals

    def as_dict(self, include_extra: bool = False) -> dict:
        out = {
            "match_id": self.match_id,
            "competition": self.competition,
            "season": self.season,
            "round": self.round,
            "stage": self.stage,
            "date": self.date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "home_state": self.home_state,
            "away_state": self.away_state,
            "arena": self.arena,
        }
        if include_extra:
            out["extra"] = dict(self.extra)
        return out


@dataclass
class Player:
    """A FIFA-database player entry."""

    player_id: int | None
    name: str
    age: int | None
    nationality: str
    overall: int | None
    potential: int | None
    club: str
    position: str
    jersey_number: int | None
    value: str
    wage: str
    preferred_foot: str
    height_cm: int | None
    weight_kg: int | None
    work_rate: str
    skills: dict = field(default_factory=dict)

    @property
    def club_key(self) -> str:
        return key_team(self.club) if self.club else ""

    def as_dict(self, include_skills: bool = False) -> dict:
        out = {
            "player_id": self.player_id,
            "name": self.name,
            "age": self.age,
            "nationality": self.nationality,
            "overall": self.overall,
            "potential": self.potential,
            "club": self.club,
            "position": self.position,
            "jersey_number": self.jersey_number,
            "value": self.value,
            "wage": self.wage,
            "preferred_foot": self.preferred_foot,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "work_rate": self.work_rate,
        }
        if include_skills:
            out["skills"] = dict(self.skills)
        return out


def _parse_height(value: str) -> int | None:
    """Parse FIFA height strings like ``5'7`` into centimeters."""
    text = (value or "").strip().replace('"', "")
    if not text:
        return None
    try:
        if "'" in text:
            feet, inches = text.split("'", 1)
            inches = inches or "0"
            return round(int(feet) * 30.48 + int(inches) * 2.54)
        if text.endswith("cm"):
            return int(float(text[:-2]))
    except ValueError:
        return None
    return None


def _parse_weight(value: str) -> int | None:
    """Parse FIFA weight strings like ``159lbs`` into kilograms."""
    text = (value or "").strip().lower()
    if not text:
        return None
    try:
        if text.endswith("lbs"):
            return round(int(text[:-3]) * 0.45359237)
        if text.endswith("kg"):
            return int(float(text[:-2]))
    except ValueError:
        return None
    return None


class SoccerData:
    """Unified, indexed view over the six CSV datasets."""

    def __init__(self, data_dir: Path | str | None = None, load: bool = True):
        self.data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self.skipped: dict[str, int] = {}
        self._by_team: dict[str, list[Match]] = {}
        self._by_pair: dict[tuple[str, str], list[Match]] = {}
        self._by_comp_season: dict[tuple[str, int | None], list[Match]] = {}
        self._team_names: dict[str, str] = {}
        self._player_names: dict[str, Player] = {}
        if load:
            self.load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        self.matches = []
        self.players = []
        self.skipped = {}
        seen: dict[tuple, Match] = {}
        near_index: dict[tuple, list[Match]] = {}
        for filename in _MATCH_FILES:
            self._load_match_file(filename, seen, near_index)
        self._drop_league_strays()
        self._load_player_file(_PLAYER_FILE)
        self._build_indexes()

    def _drop_league_strays(self) -> None:
        """Remove junk rows from league data (e.g. state-league matches
        mislabeled "Serie A" in the extended-stats file).

        A real Brasileirão Série A team accumulates dozens of appearances in
        the dataset; stray fixtures involve teams seen only once or twice.
        Only extended-file rows are ever dropped -- the dedicated match files
        are authoritative.
        """
        serie_a = competition_key("Brasileirão Série A")
        in_serie_a = [m for m in self.matches if m.competition_key == serie_a]
        counts: dict[str, int] = {}
        for m in in_serie_a:
            for team in (m.home_team, m.away_team):
                counts[key_team(team)] = counts.get(key_team(team), 0) + 1
        strays = {
            m.match_id
            for m in in_serie_a
            if m.source == "BR-Football-Dataset.csv" and min(
                counts.get(key_team(m.home_team), 0),
                counts.get(key_team(m.away_team), 0),
            ) < _LEAGUE_MIN_APPEARANCES
        }
        if strays:
            self.matches = [m for m in self.matches if m.match_id not in strays]

    def _load_match_file(self, filename: str, seen: dict[tuple, Match],
                         near_index: dict | None = None) -> None:
        path = self.data_dir / filename
        if not path.exists():
            self.skipped[filename] = -1
            return
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            count = 0
            for row_number, row in enumerate(reader):
                match = self._row_to_match(filename, row, row_number)
                if match is None:
                    continue
                key = self._dedupe_key(match)
                existing = seen.get(key)
                if existing is None and near_index is not None:
                    # Second chance: some files record shifted match dates
                    # (postponements/timezones).  Merge when the same
                    # competition/season/fixture appears within +-3 days.
                    existing = self._find_near_match(match, near_index)
                if existing is None:
                    seen[key] = match
                    self.matches.append(match)
                    if near_index is not None:
                        self._index_near(match, near_index)
                else:
                    self._enrich(existing, match)
                count += 1
            self.skipped[filename] = count

    @staticmethod
    def _near_key(match: Match) -> tuple:
        # Note: deliberately excludes season -- files that derive season from
        # the match date mislabel end-of-season fixtures (e.g. the 2020
        # Brasileirão finished in Feb 2021).  The +-3 day window keeps this
        # safe from cross-leg merges (cup ties are a week apart).
        comp = match.competition_key
        home, away = sorted((key_team(match.home_team), key_team(match.away_team)))
        return (comp, home, away)

    @staticmethod
    def _find_near_match(match: Match, near_index: dict) -> Match | None:
        if not match.date:
            return None
        target = date.fromisoformat(match.date)
        best: Match | None = None
        best_delta = 10**6
        for candidate in near_index.get(SoccerData._near_key(match), []):
            if not candidate.date:
                continue
            delta = abs((date.fromisoformat(candidate.date) - target).days)
            if delta == 0 or delta > 30:
                continue
            # Tight window: any shifted-date duplicate.  Wide window: only
            # merge scoreless placeholders (postponed fixtures recorded with
            # NA scores) whose real result was filed under a later date.
            if delta <= 3 or (candidate.home_goals is None and delta <= 30):
                if delta < best_delta:
                    best, best_delta = candidate, delta
        return best

    @staticmethod
    def _index_near(match: Match, near_index: dict) -> None:
        if match.date:
            near_index.setdefault(SoccerData._near_key(match), []).append(match)

    def _row_to_match(self, filename: str, row: dict, row_number: int = 0) -> Match | None:
        """Convert a CSV row into a normalized Match (or None if unusable)."""
        if filename == "Brasileirao_Matches.csv":
            return self._make_match(
                source=filename,
                competition="Brasileirão Série A",
                date=parse_date(row.get("datetime", "")),
                season=parse_int(row.get("season")),
                home=canonical_team(row.get("home_team", "")),
                away=canonical_team(row.get("away_team", "")),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                round=row.get("round"),
                home_state=row.get("home_team_state") or None,
                away_state=row.get("away_team_state") or None,
                _row=row_number,
            )
        if filename == "Brazilian_Cup_Matches.csv":
            return self._make_match(
                source=filename,
                competition="Copa do Brasil",
                date=parse_date(row.get("datetime", "")),
                season=parse_int(row.get("season")),
                home=canonical_team(row.get("home_team", "")),
                away=canonical_team(row.get("away_team", "")),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                round=row.get("round"),
                _row=row_number,
            )
        if filename == "Libertadores_Matches.csv":
            return self._make_match(
                source=filename,
                competition="Copa Libertadores",
                date=parse_date(row.get("datetime", "")),
                season=parse_int(row.get("season")),
                home=canonical_team(row.get("home_team", "")),
                away=canonical_team(row.get("away_team", "")),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                stage=row.get("stage"),
                _row=row_number,
            )
        if filename == "BR-Football-Dataset.csv":
            date = parse_date(row.get("date", ""))
            extra = {
                "home_corners": parse_int(row.get("home_corner")),
                "away_corners": parse_int(row.get("away_corner")),
                "total_corners": parse_int(row.get("total_corners")),
                "home_shots": parse_int(row.get("home_shots")),
                "away_shots": parse_int(row.get("away_shots")),
                "home_attacks": parse_int(row.get("home_attack")),
                "away_attacks": parse_int(row.get("away_attack")),
                "kickoff_time": (row.get("time") or "").strip() or None,
                "ht_result": (row.get("ht_result") or "").strip() or None,
                "at_result": (row.get("at_result") or "").strip() or None,
            }
            return self._make_match(
                source=filename,
                competition=canonical_competition(row.get("tournament", "")),
                date=date,
                season=int(date[:4]) if date else None,
                home=canonical_team(row.get("home", "")),
                away=canonical_team(row.get("away", "")),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                extra=extra,
                _row=row_number,
            )
        if filename == "novo_campeonato_brasileiro.csv":
            return self._make_match(
                source=filename,
                competition="Brasileirão Série A",
                date=parse_date(row.get("Data", "")),
                season=parse_int(row.get("Ano")),
                home=canonical_team(row.get("Equipe_mandante", "")),
                away=canonical_team(row.get("Equipe_visitante", "")),
                home_goals=parse_int(row.get("Gols_mandante")),
                away_goals=parse_int(row.get("Gols_visitante")),
                round=row.get("Rodada"),
                home_state=row.get("Mandante_UF") or None,
                away_state=row.get("Visitante_UF") or None,
                arena=(row.get("Arena") or "").strip() or None,
                _row=row_number,
            )
        return None

    @staticmethod
    def _make_match(**kwargs) -> Match | None:
        """Build a Match, generating its id and rejecting rows without teams."""
        row_number = kwargs.pop("_row", 0)
        kwargs = {
            ("home_team" if k == "home" else "away_team" if k == "away" else k): v
            for k, v in kwargs.items()
            if k in Match.__dataclass_fields__ or k in ("home", "away", "extra")
        }
        home, away = kwargs.get("home_team", ""), kwargs.get("away_team", "")
        if not home or not away:
            return None
        source = kwargs.get("source", "unknown")
        kwargs["match_id"] = f"{source.replace('.csv', '').replace('-', '_')}-{row_number:06d}"
        kwargs.setdefault("extra", {})
        return Match(**kwargs)

    @staticmethod
    def _dedupe_key(match: Match) -> tuple:
        comp = match.competition_key
        home, away = sorted(
            (key_team(match.home_team), key_team(match.away_team))
        )
        if match.date:
            return (comp, match.date, home, away)
        return (comp, match.season, match.round, match.stage, home, away)

    @staticmethod
    def _enrich(keep: Match, duplicate: Match) -> None:
        """Fill gaps in the kept match from a duplicate row of another file."""
        if keep.home_goals is None:
            keep.home_goals = duplicate.home_goals
        if keep.away_goals is None:
            keep.away_goals = duplicate.away_goals
        if keep.arena is None and duplicate.arena:
            keep.arena = duplicate.arena
        if keep.date is None and duplicate.date:
            keep.date = duplicate.date
        if keep.season is None and duplicate.season is not None:
            keep.season = duplicate.season
        if duplicate.source.endswith("BR-Football-Dataset.csv"):
            keep.extra.update(
                {k: v for k, v in duplicate.extra.items() if v is not None}
            )

    def _load_player_file(self, filename: str) -> None:
        path = self.data_dir / filename
        if not path.exists():
            self.skipped[filename] = -1
            return
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            count = 0
            for row in reader:
                player = Player(
                    player_id=parse_int(row.get("ID")),
                    name=(row.get("Name") or "").strip(),
                    age=parse_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=parse_int(row.get("Overall")),
                    potential=parse_int(row.get("Potential")),
                    club=(row.get("Club") or "").strip(),
                    position=(row.get("Position") or "").strip(),
                    jersey_number=parse_int(row.get("Jersey Number")),
                    value=(row.get("Value") or "").strip(),
                    wage=(row.get("Wage") or "").strip(),
                    preferred_foot=(row.get("Preferred Foot") or "").strip(),
                    height_cm=_parse_height(row.get("Height") or ""),
                    weight_kg=_parse_weight(row.get("Weight") or ""),
                    work_rate=(row.get("Work Rate") or "").strip(),
                    skills=self._player_skills(row),
                )
                self.players.append(player)
                count += 1
            self.skipped[filename] = count

    _SKILL_COLUMNS = (
        "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
        "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
        "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
        "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
        "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
        "Composure", "Marking", "StandingTackle", "SlidingTackle",
        "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
    )

    @classmethod
    def _player_skills(cls, row: dict) -> dict:
        return {
            col: val
            for col in cls._SKILL_COLUMNS
            if (val := parse_int(row.get(col))) is not None
        }

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    def _build_indexes(self) -> None:
        self._by_team = {}
        self._by_pair = {}
        self._by_comp_season = {}
        self._team_names = {}
        self._player_names = {}
        for match in self.matches:
            for team in (match.home_team, match.away_team):
                key = key_team(team)
                self._team_names.setdefault(key, team)
                self._by_team.setdefault(key, []).append(match)
            pair = tuple(sorted((key_team(match.home_team), key_team(match.away_team))))
            self._by_pair.setdefault(pair, []).append(match)
            self._by_comp_season.setdefault(
                (match.competition_key, match.season), []
            ).append(match)
        for player in self.players:
            self._player_names.setdefault(player.name.lower(), player)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def matches_for_team(self, team: str) -> list[Match]:
        return self._by_team.get(key_team(team), [])

    def matches_between(self, team_a: str, team_b: str) -> list[Match]:
        return self._by_pair.get(tuple(sorted((key_team(team_a), key_team(team_b)))), [])

    def matches_in_competition(self, competition: str, season: int | None = None) -> list[Match]:
        if season is None:
            key = competition_key(competition)
            return [m for m in self.matches if m.competition_key == key]
        return list(self._by_comp_season.get((competition_key(competition), season), []))

    def resolve_team(self, name: str) -> str | None:
        """Resolve a (possibly partial) team name to a canonical team name."""
        if not name:
            return None
        query = key_team(name)
        if query in self._team_names:
            return self._team_names[query]
        # User typed a partial team name ("palmei" -> "Palmeiras").
        for key, display in self._team_names.items():
            if query and query in key:
                return display
        # User typed a team name with generic club qualifiers
        # ("Flamengo FC" -> "Flamengo") -- but not extra distinct words.
        stripped = " ".join(
            token for token in query.split() if token not in _GENERIC_CLUB_WORDS
        )
        if stripped and stripped != query and stripped in self._team_names:
            return self._team_names[stripped]
        return None

    def team_names(self) -> list[str]:
        """Sorted canonical team names present in the match data."""
        return sorted(self._team_names.values())

    def competition_names(self) -> dict[str, int]:
        """Canonical competition names with match counts."""
        counts: dict[str, int] = {}
        for match in self.matches:
            counts[match.competition] = counts.get(match.competition, 0) + 1
        return dict(sorted(counts.items()))

    def dataset_stats(self) -> dict:
        """Per-file load counts plus unified totals (for diagnostics/tests)."""
        deduped_by_comp: dict[str, int] = {}
        for match in self.matches:
            deduped_by_comp[match.competition] = (
                deduped_by_comp.get(match.competition, 0) + 1
            )
        return {
            "rows_loaded_per_file": dict(sorted(self.skipped.items())),
            "unique_matches": len(self.matches),
            "matches_per_competition": dict(sorted(deduped_by_comp.items())),
            "players": len(self.players),
            "teams": len(self._team_names),
        }
