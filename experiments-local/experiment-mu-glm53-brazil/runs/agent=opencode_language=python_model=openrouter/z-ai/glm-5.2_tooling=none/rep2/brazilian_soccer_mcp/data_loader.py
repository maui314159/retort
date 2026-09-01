# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# Module: brazilian_soccer_mcp.data_loader
# Purpose: Load and normalize all 6 Kaggle CSV datasets into a unified list
# of Match and Player dataclasses, with canonical team keys and ISO dates.
#
# Files handled (relative to repo root):
#   data/kaggle/Brasileirao_Matches.csv        -> Brasileirão Série A
#   data/kaggle/Brazilian_Cup_Matches.csv       -> Copa do Brasil
#   data/kaggle/Libertadores_Matches.csv        -> Copa Libertadores
#   data/kaggle/BR-Football-Dataset.csv         -> Extended stats (multi-comp)
#   data/kaggle/novo_campeonato_brasileiro.csv  -> Brasileirão 2003-2019
#   data/kaggle/fifa_data.csv                   -> FIFA player database
#
# Date format handling:
#   * ISO with time      "2012-05-19 18:30:00"  -> datetime + date
#   * ISO bare           "2023-09-24"           -> date (datetime=None)
#   * Brazilian DD/MM/YYYY "29/03/2003"          -> date (datetime=None)
# Goals are coerced to int when possible; non-numeric/empty -> None.
# All team names are normalized via team_normalize.normalize_team().
# The FIFA csv starts with a UTF-8 BOM; we open it with 'utf-8-sig'.
# --------------------------------------------------------------------------- #
"""Load and normalize the Kaggle Brazilian soccer CSV datasets."""

from __future__ import annotations

import csv
import os
from collections.abc import Iterable
from datetime import date, datetime

from brazilian_soccer_mcp.models import Match, Player
from brazilian_soccer_mcp.team_normalize import normalize_team

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DEFAULT_DATA_DIR = os.path.join(REPO_ROOT, "data", "kaggle")

_BRASILEIRAO_FILE = "Brasileirao_Matches.csv"
_CUP_FILE = "Brazilian_Cup_Matches.csv"
_LIBERTADORES_FILE = "Libertadores_Matches.csv"
_BR_FOOTBALL_FILE = "BR-Football-Dataset.csv"
_HISTORICAL_FILE = "novo_campeonato_brasileiro.csv"
_FIFA_FILE = "fifa_data.csv"


# FIFA skill attributes we surface through the Player dataclass. Keeping this
# list bounded stops the attributes dict from ballooning for no benefit.
_FIFA_SKILL_COLS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
]

_COMP_NAME_NORMALIZE = {
    "brasileirao": "Brasileirão",
    "serie a": "Brasileirão Série A",
    "serie a (brasileirao)": "Brasileirão Série A",
    "copa do brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
    "cup": "Cup",
}


def _coerce_int(value) -> int | None:
    """Best-effort int coercion; returns None for blanks / non-numeric."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        # Tolerate "1.0" floats coming from the BR-Football-Dataset.
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _coerce_year(value) -> int | None:
    n = _coerce_int(value)
    if n is None:
        return None
    # Some datasets store season as a full date-ish string occasionally;
    # accept anything 4-digit-ish.
    return n if 1900 <= n <= 2100 else None


def _parse_datetime(value: str) -> tuple[datetime | None, date | None]:
    """Parse the heterogeneous date/datetime strings across files.

    Returns (datetime_or_None, date_or_None). Both may be None on failure.
    """
    if value is None:
        return None, None
    s = str(value).strip()
    if not s:
        return None, None
    # ISO datetime: "2012-05-19 18:30:00"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt, dt.date()
        except ValueError:
            pass
    # ISO date: "2023-09-24"
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return None, d
    except ValueError:
        pass
    # Brazilian: "29/03/2003" or "29/03/2003 16:00"
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return (dt if "%H" in fmt else None), dt.date()
        except ValueError:
            pass
    return None, None


def _normalize_tournament(raw: str) -> str:
    s = raw.strip().lower()
    return _COMP_NAME_NORMALIZE.get(s, raw.strip())


class DataLoader:
    """Load all Kaggle datasets into normalized Match / Player lists.

    The loader is cheap to construct; ``load_all()`` performs the CSV reads
    and stores the result in ``self.matches`` and ``self.players``. Repeated
    calls reuse the cached result so an MCP server can call ``load_all()``
    on every tool invocation safely.
    """

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR) -> None:
        self.data_dir = data_dir
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self._loaded = False

    # -- public API -----------------------------------------------------------

    def load_all(self) -> DataLoader:
        if self._loaded:
            return self
        self.matches = self._load_matches()
        self.players = self._load_players()
        self._loaded = True
        return self

    # -- match loaders --------------------------------------------------------

    def _load_matches(self) -> list[Match]:
        matches: list[Match] = []
        matches += self._load_brasileirao()
        matches += self._load_cup()
        matches += self._load_libertadores()
        matches += self._load_br_football()
        matches += self._load_historical_brasileirao()
        return matches

    def _path(self, fname: str) -> str:
        return os.path.join(self.data_dir, fname)

    def _load_brasileirao(self) -> list[Match]:
        path = self._path(_BRASILEIRAO_FILE)
        out: list[Match] = []
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                dt, d = _parse_datetime(row.get("datetime", ""))
                home = (row.get("home_team") or "").strip()
                away = (row.get("away_team") or "").strip()
                out.append(Match(
                    date=d, datetime=dt,
                    home_team=home, away_team=away,
                    home_team_key=normalize_team(home),
                    away_team_key=normalize_team(away),
                    home_goal=_coerce_int(row.get("home_goal")),
                    away_goal=_coerce_int(row.get("away_goal")),
                    competition="Brasileirão Série A",
                    season=_coerce_year(row.get("season")),
                    round_info=(row.get("round") or "").strip(),
                    stage=None, stadium=None,
                    source_file=_BRASILEIRAO_FILE,
                ))
        return out

    def _load_cup(self) -> list[Match]:
        path = self._path(_CUP_FILE)
        out: list[Match] = []
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                dt, d = _parse_datetime(row.get("datetime", ""))
                home = (row.get("home_team") or "").strip()
                away = (row.get("away_team") or "").strip()
                out.append(Match(
                    date=d, datetime=dt,
                    home_team=home, away_team=away,
                    home_team_key=normalize_team(home),
                    away_team_key=normalize_team(away),
                    home_goal=_coerce_int(row.get("home_goal")),
                    away_goal=_coerce_int(row.get("away_goal")),
                    competition="Copa do Brasil",
                    season=_coerce_year(row.get("season")),
                    round_info=(row.get("round") or "").strip(),
                    stage=None, stadium=None,
                    source_file=_CUP_FILE,
                ))
        return out

    def _load_libertadores(self) -> list[Match]:
        path = self._path(_LIBERTADORES_FILE)
        out: list[Match] = []
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                dt, d = _parse_datetime(row.get("datetime", ""))
                home = (row.get("home_team") or "").strip()
                away = (row.get("away_team") or "").strip()
                out.append(Match(
                    date=d, datetime=dt,
                    home_team=home, away_team=away,
                    home_team_key=normalize_team(home),
                    away_team_key=normalize_team(away),
                    home_goal=_coerce_int(row.get("home_goal")),
                    away_goal=_coerce_int(row.get("away_goal")),
                    competition="Copa Libertadores",
                    season=_coerce_year(row.get("season")),
                    round_info=None,
                    stage=(row.get("stage") or "").strip(),
                    stadium=None,
                    source_file=_LIBERTADORES_FILE,
                ))
        return out

    def _load_br_football(self) -> list[Match]:
        path = self._path(_BR_FOOTBALL_FILE)
        out: list[Match] = []
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                d = None
                dval = (row.get("date") or "").strip()
                if dval:
                    _, d = _parse_datetime(dval)
                home = (row.get("home") or "").strip()
                away = (row.get("away") or "").strip()
                comp = _normalize_tournament(row.get("tournament") or "")
                out.append(Match(
                    date=d, datetime=None,
                    home_team=home, away_team=away,
                    home_team_key=normalize_team(home),
                    away_team_key=normalize_team(away),
                    home_goal=_coerce_int(row.get("home_goal")),
                    away_goal=_coerce_int(row.get("away_goal")),
                    competition=comp,
                    season=None,  # not in this file
                    round_info=None, stage=None, stadium=None,
                    source_file=_BR_FOOTBALL_FILE,
                ))
        return out

    def _load_historical_brasileirao(self) -> list[Match]:
        path = self._path(_HISTORICAL_FILE)
        out: list[Match] = []
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                _, d = _parse_datetime(row.get("Data", ""))
                home = (row.get("Equipe_mandante") or "").strip()
                away = (row.get("Equipe_visitante") or "").strip()
                rodada = (row.get("Rodada") or "").strip()
                out.append(Match(
                    date=d, datetime=None,
                    home_team=home, away_team=away,
                    home_team_key=normalize_team(home),
                    away_team_key=normalize_team(away),
                    home_goal=_coerce_int(row.get("Gols_mandante")),
                    away_goal=_coerce_int(row.get("Gols_visitante")),
                    competition="Brasileirão Série A",
                    season=_coerce_year(row.get("Ano")),
                    round_info=rodada,
                    stage=None,
                    stadium=(row.get("Arena") or "").strip() or None,
                    source_file=_HISTORICAL_FILE,
                ))
        return out

    # -- player loader --------------------------------------------------------

    def _load_players(self) -> list[Player]:
        path = self._path(_FIFA_FILE)
        out: list[Player] = []
        # utf-8-sig strips the leading BOM this file ships with.
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                # csv.DictReader assigns the BOM/empty first column a generated
                # key like '' or None; ignore it. Use 'ID' as the canonical key.
                pid_raw = row.get("ID")
                pid = _coerce_int(pid_raw) or 0
                name = (row.get("Name") or "").strip()
                club = (row.get("Club") or "").strip()
                attrs: dict[str, int] = {}
                for col in _FIFA_SKILL_COLS:
                    val = row.get(col)
                    n = _coerce_int(val)
                    if n is not None:
                        attrs[col.lower()] = n
                out.append(Player(
                    player_id=pid,
                    name=name,
                    age=_coerce_int(row.get("Age")),
                    nationality=(row.get("Nationality") or "").strip(),
                    overall=_coerce_int(row.get("Overall")),
                    potential=_coerce_int(row.get("Potential")),
                    club=club,
                    club_key=normalize_team(club),
                    position=(row.get("Position") or "").strip() or None,
                    jersey_number=_coerce_int(row.get("Jersey Number")),
                    height=(row.get("Height") or "").strip() or None,
                    weight=(row.get("Weight") or "").strip() or None,
                    preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                    value=(row.get("Value") or "").strip() or None,
                    wage=(row.get("Wage") or "").strip() or None,
                    attributes=attrs,
                ))
        return out

    # -- convenience ----------------------------------------------------------

    def iter_matches(self) -> Iterable[Match]:
        return iter(self.matches)

    def iter_players(self) -> Iterable[Player]:
        return iter(self.players)

    def stats(self) -> dict:
        """Return a small summary dict useful for the MCP 'list_sources' tool."""
        by_comp: dict[str, int] = {}
        for m in self.matches:
            by_comp[m.competition] = by_comp.get(m.competition, 0) + 1
        return {
            "matches_total": len(self.matches),
            "players_total": len(self.players),
            "matches_by_competition": by_comp,
            "source_files": sorted({
                _BRASILEIRAO_FILE, _CUP_FILE, _LIBERTADORES_FILE,
                _BR_FOOTBALL_FILE, _HISTORICAL_FILE, _FIFA_FILE,
            }),
        }
