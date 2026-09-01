"""CSV loaders for the six Kaggle datasets.

Loads and normalizes every match from the five match files and all players
from the FIFA file. Team names are canonicalized through the club registry
(``clubs.resolve_club`` with a ``clubs.fallback_club`` for names outside
the registry). Dates are parsed through ``normalize.parse_datetime`` which
handles both ISO ("2012-05-19 18:30:00") and Brazilian ("29/03/2003")
formats. All files are read as UTF-8 (the FIFA file carries a BOM).
"""

from __future__ import annotations

import csv
from pathlib import Path

from .clubs import Club, FIFA_CLUB_INDEX, fallback_club, resolve_club
from .models import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    Match,
    MatchStats,
    Player,
)
from .normalize import parse_datetime, parse_int, parse_money_eur

DATA_SUBDIR = "data/kaggle"

MATCH_FILES = (
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
)

PLAYER_FILE = "fifa_data.csv"

_BRF_TOURNAMENT_FAMILIES = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}


class ClubResolver:
    """Caches club identities so repeated raw names resolve once."""

    def __init__(self) -> None:
        self._cache: dict[str, Club] = {}

    def resolve(self, raw_name: str) -> Club:
        raw_name = (raw_name or "").strip()
        cached = self._cache.get(raw_name)
        if cached is not None:
            return cached
        club = resolve_club(raw_name) or fallback_club(raw_name)
        self._cache[raw_name] = club
        return club


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_brasileirao(path: Path, resolver: ClubResolver) -> list[Match]:
    matches = []
    for i, row in enumerate(_read_csv(path)):
        d, t = parse_datetime(row.get("datetime", ""))
        home = resolver.resolve(row.get("home_team", ""))
        away = resolver.resolve(row.get("away_team", ""))
        matches.append(
            Match(
                match_id=f"bra-{i}",
                date=d,
                time=t,
                family=SERIE_A,
                season=parse_int(row.get("season")),
                stage=f"Round {row.get('round', '').strip()}" if row.get("round") else None,
                round=parse_int(row.get("round")),
                home_team=home.club_id,
                away_team=away.club_id,
                home_display=home.display,
                away_display=away.display,
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                source=path.name,
            )
        )
    return matches


def _load_copa_do_brasil(path: Path, resolver: ClubResolver) -> list[Match]:
    matches = []
    for i, row in enumerate(_read_csv(path)):
        d, t = parse_datetime(row.get("datetime", ""))
        home = resolver.resolve(row.get("home_team", ""))
        away = resolver.resolve(row.get("away_team", ""))
        rnd = parse_int(row.get("round"))
        matches.append(
            Match(
                match_id=f"cup-{i}",
                date=d,
                time=t,
                family=COPA_DO_BRASIL,
                season=parse_int(row.get("season")),
                stage=f"Round {rnd}" if rnd else None,
                round=rnd,
                home_team=home.club_id,
                away_team=away.club_id,
                home_display=home.display,
                away_display=away.display,
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                source=path.name,
            )
        )
    return matches


def _load_libertadores(path: Path, resolver: ClubResolver) -> list[Match]:
    matches = []
    for i, row in enumerate(_read_csv(path)):
        d, t = parse_datetime(row.get("datetime", ""))
        home = resolver.resolve(row.get("home_team", ""))
        away = resolver.resolve(row.get("away_team", ""))
        stage = (row.get("stage") or "").strip() or None
        matches.append(
            Match(
                match_id=f"lib-{i}",
                date=d,
                time=t,
                family=LIBERTADORES,
                season=parse_int(row.get("season")),
                stage=stage,
                round=None,
                home_team=home.club_id,
                away_team=away.club_id,
                home_display=home.display,
                away_display=away.display,
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                source=path.name,
            )
        )
    return matches


def _load_br_football(path: Path, resolver: ClubResolver) -> list[Match]:
    matches = []
    for i, row in enumerate(_read_csv(path)):
        tournament = (row.get("tournament") or "").strip()
        family = _BRF_TOURNAMENT_FAMILIES.get(tournament)
        if family is None:
            continue
        d, t = parse_datetime(row.get("date", ""))
        home = resolver.resolve(row.get("home", ""))
        away = resolver.resolve(row.get("away", ""))
        stats = MatchStats(
            home_corners=parse_int(row.get("home_corner")),
            away_corners=parse_int(row.get("away_corner")),
            total_corners=parse_int(row.get("total_corners")),
            home_shots=parse_int(row.get("home_shots")),
            away_shots=parse_int(row.get("away_shots")),
            home_attacks=parse_int(row.get("home_attack")),
            away_attacks=parse_int(row.get("away_attack")),
            halftime_diff=parse_int(row.get("ht_diff")),
        )
        matches.append(
            Match(
                match_id=f"brf-{i}",
                date=d,
                time=(row.get("time") or "").strip() or None,
                family=family,
                season=d.year if d else None,
                stage=None,
                round=None,
                home_team=home.club_id,
                away_team=away.club_id,
                home_display=home.display,
                away_display=away.display,
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                source=path.name,
                stats=stats,
            )
        )
    return matches


def _load_novo(path: Path, resolver: ClubResolver) -> list[Match]:
    matches = []
    for i, row in enumerate(_read_csv(path)):
        d, _t = parse_datetime(row.get("Data", ""))
        home = resolver.resolve(row.get("Equipe_mandante", ""))
        away = resolver.resolve(row.get("Equipe_visitante", ""))
        rnd = parse_int(row.get("Rodada"))
        matches.append(
            Match(
                match_id=f"novo-{i}",
                date=d,
                time=None,
                family=SERIE_A,
                season=parse_int(row.get("Ano")),
                stage=f"Round {rnd}" if rnd else None,
                round=rnd,
                home_team=home.club_id,
                away_team=away.club_id,
                home_display=home.display,
                away_display=away.display,
                home_goals=parse_int(row.get("Gols_mandante")),
                away_goals=parse_int(row.get("Gols_visitante")),
                source=path.name,
                stadium=(row.get("Arena") or "").strip() or None,
            )
        )
    return matches


def load_matches(data_dir: str | Path) -> tuple[list[Match], dict[str, Club]]:
    """Load every match file. Returns (matches, club_id -> Club registry)."""
    data_dir = Path(data_dir)
    resolver = ClubResolver()
    loaders = {
        "Brasileirao_Matches.csv": _load_brasileirao,
        "Brazilian_Cup_Matches.csv": _load_copa_do_brasil,
        "Libertadores_Matches.csv": _load_libertadores,
        "BR-Football-Dataset.csv": _load_br_football,
        "novo_campeonato_brasileiro.csv": _load_novo,
    }
    matches: list[Match] = []
    for filename, loader in loaders.items():
        path = data_dir / filename
        if path.exists():
            matches.extend(loader(path, resolver))
    return matches, resolver._cache


def load_players(data_dir: str | Path) -> list[Player]:
    """Load the FIFA player dataset (FIFA 19 snapshot, 18,207 players)."""
    path = Path(data_dir) / PLAYER_FILE
    players: list[Player] = []
    for row in _read_csv(path):
        club = (row.get("Club") or "").strip() or None
        club_id = FIFA_CLUB_INDEX.get(club) if club else None
        players.append(
            Player(
                fifa_id=parse_int(row.get("ID")) or 0,
                name=(row.get("Name") or "").strip(),
                age=parse_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=parse_int(row.get("Overall")) or 0,
                potential=parse_int(row.get("Potential")) or 0,
                club=club,
                club_id=club_id,
                position=(row.get("Position") or "").strip() or None,
                jersey=parse_int(row.get("Jersey Number")),
                value_eur=parse_money_eur(row.get("Value") or ""),
                wage_eur=parse_money_eur(row.get("Wage") or ""),
                preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
            )
        )
    return players


def find_data_dir(start: str | Path | None = None) -> Path:
    """Locate the ``data/kaggle`` directory from a start path or cwd."""
    if start:
        candidate = Path(start)
        if candidate.is_dir():
            return candidate
    cwd = Path.cwd()
    for base in (cwd, *cwd.parents):
        candidate = base / DATA_SUBDIR
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        f"Could not locate '{DATA_SUBDIR}' from {cwd}. Run from the project root."
    )
