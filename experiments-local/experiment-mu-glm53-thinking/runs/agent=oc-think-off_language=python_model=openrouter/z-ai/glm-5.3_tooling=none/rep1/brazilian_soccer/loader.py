"""Load and normalize the Brazilian soccer CSV datasets.

Handles the data-quality issues called out in the spec:
- team name variations ("Palmeiras-SP", "Palmeiras", "SE Palmeiras",
  "Sport Club Corinthians Paulista", "Atlético Mineiro" vs "Atletico-MG")
- multiple date formats (ISO, DD/MM/YYYY, datetime strings)
- UTF-8 encoded Portuguese names (São Paulo, Grêmio, Avaí, Fortaleza)
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# Words dropped when normalizing verbose club names.
_NOISE_WORDS = {
    "sport", "club", "clube", "sc", "ec", "fc", "ac", "aa", "sec", "se",
    "sociedade", "esportiva", "esporte", "esportes", "de", "do", "da",
    "dos", "das", "antigo", "the", "team", "football", "futebol",
}

# Noise words that must never be the *entire* normalized name (e.g. "Sport").
_KEEP_IF_ALONE = {"sport"}

# Valid Brazilian state abbreviations used as team-name suffixes ("Palmeiras-SP").
_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Distinct clubs that share a bare base name across the datasets. Every
# spelling below maps to the same group, so "Atletico-MG" (state-suffixed
# file), "Atlético Mineiro" (prose) and "Atletico MG" all refer to one team.
_ALIAS_GROUPS: list[list[str]] = [
    ["atletico mg", "atletico mineiro"],
    ["atletico pr", "atletico paranaense", "athletico paranaense"],
    ["atletico go", "atletico goianiense"],
    ["america mg", "america mineiro"],
    ["vasco", "vasco gama"],
    ["sport", "sport recife"],
    ["corinthians", "corinthians paulista", "sport corinthians paulista"],
    ["gremio", "gremio fbpa"],
    ["sao paulo", "sao paulo fc"],
]

_ALIAS_LOOKUP: dict[str, frozenset[str]] = {}
for _group in _ALIAS_GROUPS:
    _fs = frozenset(_group)
    for _k in _group:
        _ALIAS_LOOKUP[_k] = _fs

_SUFFIX_RE = re.compile(r"[-–]\s*([A-Za-z]{2})$")


def strip_accents(text: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )


def _base_and_state(name: str) -> tuple[list[str], str]:
    """Return (base tokens, state suffix) for a raw team name."""
    name = (name or "").strip()
    name = re.sub(r"\(.*?\)", " ", name)  # e.g. "(antigo Esporte Clube Barreira)"
    name = strip_accents(name).lower()
    tokens = [t for t in re.split(r"[^a-z0-9]+", name) if t]
    state = ""
    if len(tokens) >= 2 and tokens[-1].upper() in _UFS:
        # Only treat the trailing token as a state when the name looks
        # suffixed, e.g. "Palmeiras-SP" (hyphen present in the raw name).
        if _SUFFIX_RE.search(name):
            state = tokens[-1]
            tokens = tokens[:-1]
    meaningful = [
        t for t in tokens if t not in _NOISE_WORDS or t in _KEEP_IF_ALONE
    ]
    if not meaningful:
        meaningful = tokens
    return meaningful, state


def group_key(name: str) -> str:
    """Unambiguous identity key: keeps the state suffix when present
    ("Atletico-MG" -> "atletico mg") so distinct clubs that share a bare
    base name are never merged."""
    tokens, state = _base_and_state(name)
    base = " ".join(tokens)
    key = f"{base} {state}".strip() if state else base
    return min(_ALIAS_LOOKUP.get(key, {key}))


def _bare_keys(name: str) -> set[str]:
    tokens, state = _base_and_state(name)
    base = " ".join(tokens)
    keys = {base} if base else set()
    if state:
        keys.add(f"{base} {state}")
    out: set[str] = set()
    for k in keys:
        out.add(k)
        out |= _ALIAS_LOOKUP.get(k, frozenset())
        if " " in k:
            first = k.rsplit(" ", 1)[0]
            out |= _ALIAS_LOOKUP.get(first, frozenset())
    return {k for k in out if k}


def normalize_team(name: str) -> str:
    """Canonical matching key for a team name.

    >>> normalize_team("Palmeiras-SP") == normalize_team("SE Palmeiras")
    True
    """
    return min(_bare_keys(name))


def same_team(a: str, b: str) -> bool:
    """True when two raw team names refer to the same club."""
    return bool(_bare_keys(a) & _bare_keys(b))


def parse_date(value: str) -> date | None:
    """Parse the date formats used across the datasets."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class Match:
    date: date | None
    home: str
    away: str
    home_goal: int
    away_goal: int
    competition: str
    season: int | None
    round: str = ""
    stage: str = ""
    home_state: str = ""
    away_state: str = ""

    @property
    def winner(self) -> str | None:
        if self.home_goal > self.away_goal:
            return "home"
        if self.away_goal > self.home_goal:
            return "away"
        return "draw"


@dataclass
class Player:
    id: str
    name: str
    age: int | None
    nationality: str
    overall: int
    potential: int
    club: str
    position: str
    jersey: int | None


def _int(value: str | None) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _iter_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            yield {k: v for k, v in row.items() if k is not None}


def _load_matches(path: Path, competition: str) -> list[Match]:
    matches = []
    for row in _iter_csv(path):
        dt = parse_date(row.get("datetime") or row.get("date") or row.get("Data") or "")
        season = _int(row.get("season") or row.get("Ano"))
        matches.append(
            Match(
                date=dt,
                home=row.get("home_team") or row.get("home") or row.get("Equipe_mandante") or "",
                away=row.get("away_team") or row.get("away") or row.get("Equipe_visitante") or "",
                home_goal=_int(row.get("home_goal") or row.get("Gols_mandante")) or 0,
                away_goal=_int(row.get("away_goal") or row.get("Gols_visitante")) or 0,
                competition=competition,
                season=season,
                round=str(row.get("round") or row.get("Rodada") or ""),
                stage=row.get("stage") or "",
                home_state=row.get("home_team_state") or row.get("Mandante_UF") or "",
                away_state=row.get("away_team_state") or row.get("Visitante_UF") or "",
            )
        )
    return matches


def _load_stats_dataset(path: Path) -> list[Match]:
    """BR-Football-Dataset.csv — competition name comes from the tournament column."""
    matches = []
    for row in _iter_csv(path):
        dt = parse_date(row.get("date") or "")
        matches.append(
            Match(
                date=dt,
                home=row.get("home") or "",
                away=row.get("away") or "",
                home_goal=_int(row.get("home_goal")) or 0,
                away_goal=_int(row.get("away_goal")) or 0,
                competition=(row.get("tournament") or "").strip(),
                season=dt.year if dt else None,
                round="",
                stage="",
            )
        )
    return matches


def _load_players(path: Path) -> list[Player]:
    players = []
    for row in _iter_csv(path):
        overall = _int(row.get("Overall"))
        if overall is None:
            continue
        players.append(
            Player(
                id=row.get("ID") or "",
                name=row.get("Name") or "",
                age=_int(row.get("Age")),
                nationality=row.get("Nationality") or "",
                overall=overall,
                potential=_int(row.get("Potential")) or overall,
                club=row.get("Club") or "",
                position=row.get("Position") or "",
                jersey=_int(row.get("Jersey Number")),
            )
        )
    return players


class SoccerData:
    """In-memory repository over the six CSV datasets."""

    def __init__(self, matches: list[Match], players: list[Player]):
        self.matches = matches
        self.players = players
        # A bare base name (state suffix stripped) is ambiguous when it is
        # shared by clubs from more than one distinct state (e.g.
        # "atletico": MG/PR/GO, "botafogo": RJ/PB). A base seen both with
        # and without a suffix ("Palmeiras", "Palmeiras-SP") is NOT
        # ambiguous — that is the same club spelled two ways.
        base_states: dict[str, set[str]] = {}
        for m in matches:
            for name in (m.home, m.away):
                tokens, state = _base_and_state(name)
                base = " ".join(tokens)
                if base:
                    base_states.setdefault(base, set()).add(state)
        self.ambiguous_bases = {
            base
            for base, states in base_states.items()
            if len(states - {""}) > 1
        }
        self._base_groups: dict[str, set[str]] = {}
        for m in matches:
            for name in (m.home, m.away):
                tokens, _ = _base_and_state(name)
                base = " ".join(tokens)
                if base:
                    self._base_groups.setdefault(base, set()).add(group_key(name))
        self._match_index: dict[str, list[Match]] = {}
        self._player_club_index: dict[str, list[Player]] = {}
        for m in matches:
            for key in self.keys_for(m.home):
                self._match_index.setdefault(key, []).append(m)
            for key in self.keys_for(m.away):
                self._match_index.setdefault(key, []).append(m)
        for p in players:
            if p.club:
                for key in self.keys_for(p.club):
                    self._player_club_index.setdefault(key, []).append(p)

    def keys_for(self, name: str) -> frozenset[str]:
        """Lookup keys for a name.

        Bare ambiguous bases are excluded; a stateless query for an
        ambiguous base (e.g. "Atletico") expands to every club sharing it.
        """
        tokens, state = _base_and_state(name)
        base = " ".join(tokens)
        keys = set(_bare_keys(name))
        if base and base in self.ambiguous_bases:
            keys.discard(base)
            if not state:
                keys |= set(self._base_groups.get(base, ()))
                extra: set[str] = set()
                for k in keys:
                    extra |= _ALIAS_LOOKUP.get(k, frozenset())
                keys |= extra
        if not keys:
            keys = {group_key(name)}
        return frozenset(keys)

    def matches_for_team(self, team: str) -> list[Match]:
        seen: set[int] = set()
        out: list[Match] = []
        for key in self.keys_for(team):
            for m in self._match_index.get(key, ()):
                if id(m) not in seen:
                    seen.add(id(m))
                    out.append(m)
        return out

    def team_names(self) -> list[str]:
        seen, names = set(), []
        for m in self.matches:
            for name in (m.home, m.away):
                key = group_key(name)
                if key not in seen:
                    seen.add(key)
                    names.append(name)
        return names

    def resolve_team(self, query: str) -> str | None:
        """Return a display name for a (possibly fuzzy) query."""
        keys = self.keys_for(query)
        best_name, best_count = None, -1
        seen: set[str] = set()
        for key in keys:
            for m in self._match_index.get(key, ()):
                for name in (m.home, m.away):
                    if self.keys_for(name) & keys and name not in seen:
                        seen.add(name)
                        count = len(self.matches_for_team(name))
                        if count > best_count:
                            best_name, best_count = name, count
        if best_name:
            return best_name
        q = " ".join(sorted(keys))
        for name in self.team_names():
            if q and (q in name or name.lower() in q):
                return name
        return None

    def players_at_club(self, club: str) -> list[Player]:
        seen: set[str] = set()
        out: list[Player] = []
        for key in self.keys_for(club):
            for p in self._player_club_index.get(key, ()):
                if p.id not in seen:
                    seen.add(p.id)
                    out.append(p)
        return out


def load_data(data_dir: Path | str = DATA_DIR) -> SoccerData:
    data_dir = Path(data_dir)
    matches: list[Match] = []
    matches += _load_matches(data_dir / "Brasileirao_Matches.csv", "Brasileirão")
    matches += _load_matches(data_dir / "Brazilian_Cup_Matches.csv", "Copa do Brasil")
    matches += _load_matches(data_dir / "Libertadores_Matches.csv", "Copa Libertadores")
    matches += _load_matches(
        data_dir / "novo_campeonato_brasileiro.csv", "Brasileirão (2003-2019)"
    )
    matches += _load_stats_dataset(data_dir / "BR-Football-Dataset.csv")
    players = _load_players(data_dir / "fifa_data.csv")
    return SoccerData(matches, players)
