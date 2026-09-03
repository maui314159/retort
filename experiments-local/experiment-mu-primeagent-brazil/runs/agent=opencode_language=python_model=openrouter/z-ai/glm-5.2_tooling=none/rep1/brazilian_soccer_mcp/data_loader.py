"""Loaders for the six bundled Kaggle CSV datasets.

All six files are loaded eagerly into memory on first use (lazy, cached via
:func:`load_all`).  Team names are normalised through
:func:`brazilian_soccer_mcp.normalize.normalize_team_name` so that the same
team in different files (``"Palmeiras-SP"`` vs ``"Palmeiras"``) collapses onto
one canonical key, while a display registry keeps a pretty, accented name for
responses.
"""

from __future__ import annotations

import csv
import functools
import os
import threading
from collections import defaultdict

from .models import Match, Player
from .normalize import (
    display_team_name,
    normalize_team_name,
    parse_date,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle")

COMPETITION_BRASILEIRAO_A = "Brasileirão Serie A"
COMPETITION_BRASILEIRAO_B = "Brasileirão Serie B"
COMPETITION_BRASILEIRAO_C = "Brasileirão Serie C"
COMPETITION_COPA_DO_BRASIL = "Copa do Brasil"
COMPETITION_LIBERTADORES = "Copa Libertadores"

_BR_FOOTBALL_TOURNAMENT_MAP = {
    "Serie A": COMPETITION_BRASILEIRAO_A,
    "Serie B": COMPETITION_BRASILEIRAO_B,
    "Serie C": COMPETITION_BRASILEIRAO_C,
    "Copa do Brasil": COMPETITION_COPA_DO_BRASIL,
}

FIFA_SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
)


def _safe_int(value, default=None):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return default
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return default


def _read_csv(path: str, encoding: str = "utf-8-sig"):
    with open(path, encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        yield from reader


class SoccerData:
    """In-memory knowledge graph: matches, players and helper indexes."""

    def __init__(self, matches: list[Match], players: list[Player],
                 team_display: dict[str, str], data_dir: str = DATA_DIR):
        self.matches = matches
        self.players = players
        self.team_display = team_display
        self.data_dir = data_dir
        self._index_by_team: dict[str, list[Match]] | None = None
        self._index_by_competition: dict[str, list[Match]] | None = None
        self._player_index_by_club: dict[str, list[Player]] | None = None
        self._player_index_by_name: dict[str, list[Player]] | None = None
        self._lock = threading.Lock()

    def _ensure_team_index(self):
        if self._index_by_team is None:
            with self._lock:
                if self._index_by_team is None:
                    idx: dict[str, list[Match]] = defaultdict(list)
                    for m in self.matches:
                        idx[m.home].append(m)
                        idx[m.away].append(m)
                    self._index_by_team = dict(idx)
        return self._index_by_team

    def _ensure_competition_index(self):
        if self._index_by_competition is None:
            with self._lock:
                if self._index_by_competition is None:
                    idx: dict[str, list[Match]] = defaultdict(list)
                    for m in self.matches:
                        idx[m.competition].append(m)
                    self._index_by_competition = dict(idx)
        return self._index_by_competition

    def _ensure_player_indexes(self):
        if self._player_index_by_club is None:
            with self._lock:
                if self._player_index_by_club is None:
                    by_club: dict[str, list[Player]] = defaultdict(list)
                    by_name: dict[str, list[Player]] = defaultdict(list)
                    for p in self.players:
                        if p.club:
                            by_club[normalize_team_name(p.club)].append(p)
                        if p.name:
                            by_name[p.name.lower()].append(p)
                    self._player_index_by_club = dict(by_club)
                    self._player_index_by_name = dict(by_name)
        return self._player_index_by_club, self._player_index_by_name

    def display_name(self, key: str) -> str:
        return self.team_display.get(key, key)

    def matches_for_team(self, team_key: str) -> list[Match]:
        return list(self._ensure_team_index().get(team_key, ()))

    def matches_for_competition(self, competition_key: str) -> list[Match]:
        from .normalize import competition_matches
        out: list[Match] = []
        for comp, ms in self._ensure_competition_index().items():
            if competition_matches(competition_key, comp):
                out.extend(ms)
        return out

    def players_for_club(self, club_key: str) -> list[Player]:
        by_club, _ = self._ensure_player_indexes()
        return list(by_club.get(club_key, ()))

    def players_named(self, name: str) -> list[Player]:
        _, by_name = self._ensure_player_indexes()
        key = name.strip().lower()
        out: list[Player] = []
        for full, players in by_name.items():
            if key in full:
                out.extend(players)
        return out


def _register_team(display_map: dict[str, str], raw: str) -> str:
    """Normalise *raw* to a canonical key, registering a pretty display name."""
    key = normalize_team_name(raw)
    if not key:
        return key
    pretty = display_team_name(raw)
    existing = display_map.get(key)
    if (existing is None
            or (any(ord(ch) > 127 for ch in pretty)
                and not any(ord(ch) > 127 for ch in existing))
            or (len(pretty) < len(existing) and " " in existing)):
        display_map[key] = pretty
    return key


def _load_brasileirao(path: str, display_map: dict[str, str]) -> list[Match]:
    matches: list[Match] = []
    for row in _read_csv(path):
        home = _register_team(display_map, row.get("home_team", ""))
        away = _register_team(display_map, row.get("away_team", ""))
        matches.append(Match(
            date=parse_date(row.get("datetime")),
            home=home,
            away=away,
            home_display=display_map.get(home, display_team_name(row.get("home_team", ""))),
            away_display=display_map.get(away, display_team_name(row.get("away_team", ""))),
            home_goal=_safe_int(row.get("home_goal"), 0) or 0,
            away_goal=_safe_int(row.get("away_goal"), 0) or 0,
            competition=COMPETITION_BRASILEIRAO_A,
            season=_safe_int(row.get("season")),
            round=str(row.get("round")) if row.get("round") else None,
            source=os.path.basename(path),
        ))
    return matches


def _load_copa_do_brasil(path: str, display_map: dict[str, str]) -> list[Match]:
    matches: list[Match] = []
    for row in _read_csv(path):
        home = _register_team(display_map, row.get("home_team", ""))
        away = _register_team(display_map, row.get("away_team", ""))
        matches.append(Match(
            date=parse_date(row.get("datetime")),
            home=home,
            away=away,
            home_display=display_map.get(home, display_team_name(row.get("home_team", ""))),
            away_display=display_map.get(away, display_team_name(row.get("away_team", ""))),
            home_goal=_safe_int(row.get("home_goal"), 0) or 0,
            away_goal=_safe_int(row.get("away_goal"), 0) or 0,
            competition=COMPETITION_COPA_DO_BRASIL,
            season=_safe_int(row.get("season")),
            round=str(row.get("round")) if row.get("round") else None,
            source=os.path.basename(path),
        ))
    return matches


def _load_libertadores(path: str, display_map: dict[str, str]) -> list[Match]:
    matches: list[Match] = []
    for row in _read_csv(path):
        home = _register_team(display_map, row.get("home_team", ""))
        away = _register_team(display_map, row.get("away_team", ""))
        matches.append(Match(
            date=parse_date(row.get("datetime")),
            home=home,
            away=away,
            home_display=display_map.get(home, display_team_name(row.get("home_team", ""))),
            away_display=display_map.get(away, display_team_name(row.get("away_team", ""))),
            home_goal=_safe_int(row.get("home_goal"), 0) or 0,
            away_goal=_safe_int(row.get("away_goal"), 0) or 0,
            competition=COMPETITION_LIBERTADORES,
            season=_safe_int(row.get("season")),
            stage=row.get("stage") or None,
            source=os.path.basename(path),
        ))
    return matches


def _load_br_football(path: str, display_map: dict[str, str]) -> list[Match]:
    matches: list[Match] = []
    for row in _read_csv(path):
        tournament = row.get("tournament", "")
        competition = _BR_FOOTBALL_TOURNAMENT_MAP.get(tournament, tournament or "Unknown")
        home = _register_team(display_map, row.get("home", ""))
        away = _register_team(display_map, row.get("away", ""))
        extras = {}
        for key in ("home_corner", "away_corner", "home_attack", "away_attack",
                    "home_shots", "away_shots", "total_corners", "ht_result", "at_result"):
            if row.get(key) not in (None, ""):
                extras[key] = row[key]
        matches.append(Match(
            date=parse_date(row.get("date")),
            home=home,
            away=away,
            home_display=display_map.get(home, display_team_name(row.get("home", ""))),
            away_display=display_map.get(away, display_team_name(row.get("away", ""))),
            home_goal=_safe_int(row.get("home_goal"), 0) or 0,
            away_goal=_safe_int(row.get("away_goal"), 0) or 0,
            competition=competition,
            season=parse_date(row.get("date")).year if row.get("date") else None,
            venue=None,
            source=os.path.basename(path),
            extras=extras,
        ))
    return matches


def _load_novo(path: str, display_map: dict[str, str]) -> list[Match]:
    matches: list[Match] = []
    for row in _read_csv(path):
        home = _register_team(display_map, row.get("Equipe_mandante", ""))
        away = _register_team(display_map, row.get("Equipe_visitante", ""))
        hg = _safe_int(row.get("Gols_mandante"), 0) or 0
        ag = _safe_int(row.get("Gols_visitante"), 0) or 0
        matches.append(Match(
            date=parse_date(row.get("Data")),
            home=home,
            away=away,
            home_display=display_map.get(home, display_team_name(row.get("Equipe_mandante", ""))),
            away_display=display_map.get(away, display_team_name(row.get("Equipe_visitante", ""))),
            home_goal=hg,
            away_goal=ag,
            competition=COMPETITION_BRASILEIRAO_A,
            season=_safe_int(row.get("Ano")),
            round=str(row.get("Rodada")) if row.get("Rodada") else None,
            venue=row.get("Arena") or None,
            source=os.path.basename(path),
        ))
    return matches


def _load_fifa(path: str) -> list[Player]:
    players: list[Player] = []
    for row in _read_csv(path):
        attributes = {}
        for col in FIFA_SKILL_COLUMNS:
            val = row.get(col)
            if val not in (None, ""):
                attributes[col] = _safe_int(val)
        players.append(Player(
            id=_safe_int(row.get("ID")),
            name=(row.get("Name") or "").strip(),
            age=_safe_int(row.get("Age")),
            nationality=(row.get("Nationality") or "").strip(),
            overall=_safe_int(row.get("Overall")),
            potential=_safe_int(row.get("Potential")),
            club=(row.get("Club") or "").strip(),
            position=(row.get("Position") or "").strip() or None,
            jersey=_safe_int(row.get("Jersey Number")),
            height=(row.get("Height") or "").strip() or None,
            weight=(row.get("Weight") or "").strip() or None,
            preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
            value=(row.get("Value") or "").strip() or None,
            wage=(row.get("Wage") or "").strip() or None,
            attributes=attributes,
        ))
    return players


def _dedupe(matches: list[Match]) -> list[Match]:
    """Drop duplicate matches that come from overlapping source files.

    The same fixture appears in several source CSVs (e.g. a 2019 Brasileirão
    match is present in ``Brasileirao_Matches.csv``, ``novo_campeonato`` and
    ``BR-Football-Dataset.csv``), often with slightly shifted dates.  We
    therefore dedupe on ``(season, home, away, home_goal, away_goal)`` which is
    robust to the one-day date drift while keeping distinct home/away legs.
    """
    seen: set = set()
    out: list[Match] = []
    for m in matches:
        key = (m.season, m.home, m.away, m.home_goal, m.away_goal)
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def load_all(data_dir: str = DATA_DIR) -> SoccerData:
    """Load every dataset and return a populated :class:`SoccerData`.

    The result is cached for the lifetime of the process so repeated calls are
    essentially free, which keeps simple lookups well under the 2s budget.
    """
    return _load_all_impl(data_dir)


@functools.lru_cache(maxsize=4)
def _load_all_impl(data_dir: str) -> SoccerData:
    display_map: dict[str, str] = {}
    matches: list[Match] = []
    matches += _load_brasileirao(os.path.join(data_dir, "Brasileirao_Matches.csv"), display_map)
    matches += _load_copa_do_brasil(os.path.join(data_dir, "Brazilian_Cup_Matches.csv"), display_map)
    matches += _load_libertadores(os.path.join(data_dir, "Libertadores_Matches.csv"), display_map)
    matches += _load_br_football(os.path.join(data_dir, "BR-Football-Dataset.csv"), display_map)
    matches += _load_novo(os.path.join(data_dir, "novo_campeonato_brasileiro.csv"), display_map)
    matches = _dedupe(matches)
    players = _load_fifa(os.path.join(data_dir, "fifa_data.csv"))
    return SoccerData(matches=matches, players=players, team_display=display_map, data_dir=data_dir)
