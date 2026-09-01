"""Load all six Kaggle CSV datasets into a unified, queryable model.

Files loaded (from ``data/kaggle``):

============================  =====================================
File                          Competition
============================  =====================================
Brasileirao_Matches.csv       Brasileirão Serie A
Brazilian_Cup_Matches.csv     Copa do Brasil
Libertadores_Matches.csv      Copa Libertadores
BR-Football-Dataset.csv       Serie A/B/C, Copa do Brasil (detailed)
novo_campeonato_brasileiro    Brasileirão Serie A (2003-2019)
fifa_data.csv                 players
============================  =====================================

Overlapping records between the aggregate files and the detailed
BR-Football-Dataset are de-duplicated: the first record for a given
(date, competition, team-pair) wins, and any extra statistics
(corners, shots, ...) from duplicate sources are merged in.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from soccer.models import Match, Player
from soccer.normalize import (
    NameRegistry,
    normalize_name,
    normalize_player_name,
    strip_accents,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# Detailed-dataset tournament names -> canonical competition names.
_DETAILED_COMPETITIONS = {
    "Serie A": "Brasileirão Serie A",
    "Serie B": "Série B",
    "Serie C": "Série C",
    "Copa do Brasil": "Copa do Brasil",
}

# Copa do Brasil numeric rounds -> textual stage names.
_CUP_ROUNDS = {
    "1": "first round",
    "2": "second round",
    "3": "third round",
    "4": "round of 32",
    "5": "round of 16",
    "6": "quarterfinals",
    "7": "semifinals",
    "8": "final",
}


def parse_date(raw: str) -> date | None:
    """Parse the date formats used across the datasets.

    Handles ISO dates with time ("2012-05-19 18:30:00"), plain ISO
    dates ("2023-09-24") and Brazilian DD/MM/YYYY ("29/03/2003").
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _to_int(raw) -> int | None:
    """Parse ints that may arrive as "3" or as float text "3.0"."""
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        try:
            return int(float(str(raw).strip()))
        except (TypeError, ValueError):
            return None


def _to_float(raw) -> float | None:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


@dataclass
class SoccerData:
    """All loaded data plus lookup indexes."""

    matches: list[Match]
    players: list[Player]
    registry: NameRegistry

    # ------------------------------------------------------------------
    # Team name helpers
    def resolve_team(self, query: str) -> str | None:
        """Resolve a user-supplied team name to a canonical key."""
        if not query:
            return None
        key = normalize_name(query)
        known = set(self.registry.keys())
        if key in known:
            return key
        # Substring match (e.g. "corinthians" -> "corinthians paulista").
        candidates = [k for k in known if key in k or k in key]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            # Token-level match for long legal names such as
            # "Sport Club Corinthians Paulista" -> "corinthians":
            # pick known keys fully covered by the query's tokens,
            # breaking ties by the longest shared token.
            qtokens = set(key.split())
            covered = [k for k in known if set(k.split()) <= qtokens]
            if covered:
                candidates = covered
        if candidates:
            # Prefer the candidate sharing the longest token with the query
            # ("corinthians" over the generic "sport" when resolving
            # "Sport Club Corinthians Paulista"); break ties by popularity
            # so "Santos" resolves to the Brazilian club, not Santos Laguna.
            return max(
                candidates,
                key=lambda k: (max(map(len, k.split())), self.registry.count(k)),
            )
        return None

    def display(self, key: str) -> str:
        return self.registry.display(key)

    def all_teams(self) -> list[str]:
        return self.registry.keys()

    # ------------------------------------------------------------------
    def _add_match(self, match: Match) -> None:
        """Add a match, de-duplicating against already-loaded matches.

        The same fixture appears in several files with slightly shifted
        dates (timezone differences between sources), so the dedupe key
        is (season, competition, home, away) rather than the date.
        """
        dedupe = (
            match.season if match.season is not None else match.date.year,
            match.competition,
            match.home,
            match.away,
        )
        existing = self._match_index.get(dedupe)
        if existing is not None:
            if not existing.stats and match.stats:
                existing.stats.update(match.stats)
            if not existing.venue and match.venue:
                existing.venue = match.venue
            return
        self._match_index[dedupe] = match
        self.matches.append(match)

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, data_dir: Path | str = DATA_DIR) -> "SoccerData":
        data_dir = Path(data_dir)
        registry = NameRegistry()
        data = cls(matches=[], players=[], registry=registry)
        data._match_index = {}

        data._load_brasileirao(data_dir / "Brasileirao_Matches.csv", registry)
        data._load_cup(data_dir / "Brazilian_Cup_Matches.csv", registry)
        data._load_libertadores(data_dir / "Libertadores_Matches.csv", registry)
        data._load_detailed(data_dir / "BR-Football-Dataset.csv", registry)
        data._load_historical(data_dir / "novo_campeonato_brasileiro.csv", registry)
        data.matches.sort(key=lambda m: (m.date, m.competition))
        data._match_index = {}
        data.players = data._load_players(data_dir / "fifa_data.csv")
        return data

    # ------------------------------------------------------------------
    def _load_brasileirao(self, path: Path, registry: NameRegistry) -> None:
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                registry.register(row["home_team"])
                registry.register(row["away_team"])
                d = parse_date(row["datetime"])
                if d is None:
                    continue
                self._add_match(
                    Match(
                        date=d,
                        home=normalize_name(row["home_team"]),
                        away=normalize_name(row["away_team"]),
                        home_goals=_to_int(row["home_goal"]) or 0,
                        away_goals=_to_int(row["away_goal"]) or 0,
                        competition="Brasileirão Serie A",
                        season=_to_int(row["season"]),
                        round=str(_to_int(row["round"]) or row["round"]),
                    )
                )

    def _load_cup(self, path: Path, registry: NameRegistry) -> None:
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                registry.register(row["home_team"])
                registry.register(row["away_team"])
                d = parse_date(row["datetime"])
                if d is None:
                    continue
                self._add_match(
                    Match(
                        date=d,
                        home=normalize_name(row["home_team"]),
                        away=normalize_name(row["away_team"]),
                        home_goals=_to_int(row["home_goal"]) or 0,
                        away_goals=_to_int(row["away_goal"]) or 0,
                        competition="Copa do Brasil",
                        season=_to_int(row["season"]),
                        round=_CUP_ROUNDS.get(row["round"].strip(), row["round"]),
                    )
                )

    def _load_libertadores(self, path: Path, registry: NameRegistry) -> None:
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                registry.register(row["home_team"])
                registry.register(row["away_team"])
                d = parse_date(row["datetime"])
                if d is None:
                    continue
                hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
                self._add_match(
                    Match(
                        date=d,
                        home=normalize_name(row["home_team"]),
                        away=normalize_name(row["away_team"]),
                        home_goals=hg if hg is not None else 0,
                        away_goals=ag if ag is not None else 0,
                        competition="Copa Libertadores",
                        season=_to_int(row["season"]),
                        round=row["stage"],
                    )
                )

    def _load_detailed(self, path: Path, registry: NameRegistry) -> None:
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                competition = _DETAILED_COMPETITIONS.get(row["tournament"].strip())
                if competition is None:
                    continue
                registry.register(row["home"])
                registry.register(row["away"])
                d = parse_date(row["date"])
                if d is None:
                    continue
                hg, ag = _to_int(row["home_goal"]), _to_int(row["away_goal"])
                stats = {}
                for key in (
                    "home_corner",
                    "away_corner",
                    "home_attack",
                    "away_attack",
                    "home_shots",
                    "away_shots",
                    "total_corners",
                ):
                    val = _to_float(row.get(key))
                    if val is not None:
                        stats[key] = val
                self._add_match(
                    Match(
                        date=d,
                        home=normalize_name(row["home"]),
                        away=normalize_name(row["away"]),
                        home_goals=int(hg) if hg is not None else 0,
                        away_goals=int(ag) if ag is not None else 0,
                        competition=competition,
                        # Brazilian seasons are calendar-year aligned, so
                        # the kick-off year is a sound season inference.
                        season=d.year,
                        stats=stats,
                    )
                )

    def _load_historical(self, path: Path, registry: NameRegistry) -> None:
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                registry.register(row["Equipe_mandante"])
                registry.register(row["Equipe_visitante"])
                d = parse_date(row["Data"])
                if d is None:
                    continue
                self._add_match(
                    Match(
                        date=d,
                        home=normalize_name(row["Equipe_mandante"]),
                        away=normalize_name(row["Equipe_visitante"]),
                        home_goals=_to_int(row["Gols_mandante"]) or 0,
                        away_goals=_to_int(row["Gols_visitante"]) or 0,
                        competition="Brasileirão Serie A",
                        season=_to_int(row["Ano"]),
                        round=str(_to_int(row["Rodada"]) or row["Rodada"]),
                        venue=row.get("Arena") or None,
                    )
                )

    def _load_players(self, path: Path) -> list[Player]:
        players: list[Player] = []
        with open(path, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                try:
                    player = Player(
                        id=int(row["ID"]),
                        name=row["Name"].strip(),
                        age=_to_int(row.get("Age")),
                        nationality=(row.get("Nationality") or "").strip(),
                        overall=_to_int(row.get("Overall")) or 0,
                        potential=_to_int(row.get("Potential")) or 0,
                        club=(row.get("Club") or "").strip() or None,
                        position=(row.get("Position") or "").strip() or None,
                        jersey_number=_to_int(row.get("Jersey Number")),
                        nationality_key=normalize_name(row.get("Nationality") or ""),
                        club_key=normalize_name(row.get("Club") or ""),
                        name_key=normalize_player_name(row.get("Name") or ""),
                    )
                except (KeyError, ValueError, TypeError):
                    continue
                players.append(player)
        return players


def load_soccer_data(data_dir: Path | str = DATA_DIR) -> SoccerData:
    """Convenience wrapper around :meth:`SoccerData.load`."""
    return SoccerData.load(data_dir)


def competition_matches(pattern: str | None, competition: str) -> bool:
    """Loose competition-name match (case/accent-insensitive substring)."""
    if pattern is None:
        return True
    p = strip_accents(pattern).strip().lower()
    c = strip_accents(competition).strip().lower()
    return p in c or c in p
