"""Data loading and normalization for the Brazilian soccer datasets.

Handles all 6 CSV files from data/kaggle/, normalizing team names,
dates, and scores into a common Match record so queries can be run
uniformly across competitions and files.

Team-name matching is two-tier:
- normalize_name() strips accents/parentheses and lowercases, but keeps
  state suffixes so 'Atletico-MG' and 'Atletico-PR' stay distinct.
- name_matches() lets a suffix-less query ('palmeiras') match any
  suffixed variant ('palmeiras-sp'), while a suffixed query
  ('atletico-mg') matches only that exact team.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

BRASILEIRAO = "Brasileirão"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"
BR_DATASET = "BR Football Dataset"
HISTORICO = "Brasileirão (2003-2019)"

# Normalized competition names that refer to the same real-world competition.
COMPETITION_ALIASES: dict[str, set[str]] = {
    "brasileirao": {
        "brasileirao",
        "serie a",
        "brasileirao (2003-2019)",
        "campeonato brasileiro serie a",
    },
    "copa do brasil": {"copa do brasil"},
    "libertadores": {"copa libertadores", "libertadores"},
    "serie b": {"serie b"},
}

# When several files cover the same competition+season, prefer the most
# authoritative/dedicated source.
_SOURCE_PRIORITY = [
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "novo_campeonato_brasileiro.csv",
    "BR-Football-Dataset.csv",
]

_SUFFIX_RE = re.compile(r"\s*-\s*[a-z]{2,3}\s*$")


def normalize_name(name: str) -> str:
    """Normalize a team/player/competition name for comparisons.

    Strips accents, removes parenthetical annotations, lowercases, and
    collapses whitespace. State suffixes like '-SP' are kept so that
    distinct teams (Atletico-MG vs Atletico-PR) remain distinct; use
    base_name()/name_matches() for suffix-insensitive matching.
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def base_name(normalized: str) -> str:
    """Strip a trailing state suffix from an already-normalized name."""
    return _SUFFIX_RE.sub("", normalized).strip()


def name_matches(query: str, target: str) -> bool:
    """True if a user-supplied query name matches a dataset team name.

    - A query with a suffix ('Atletico-MG') matches only that team.
    - A query without a suffix ('Palmeiras') matches any state variant
      ('Palmeiras-SP', 'Palmeiras').
    """
    qn = normalize_name(query)
    tn = normalize_name(target)
    if not qn or not tn:
        return False
    if qn == tn:
        return True
    # suffix-less query matches suffixed target
    if _SUFFIX_RE.sub("", qn) == qn and base_name(tn) == qn:
        return True
    return False


def display_name(name: str) -> str:
    """Return a clean display name (no state suffix, no parentheses)."""
    s = name.strip()
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\s*-\s*[A-Z]{2,3}\s*$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def competition_group(name: str) -> set[str]:
    """Resolve a competition name to its set of normalized aliases.

    Falls back to a literal normalized name if no alias group matches.
    """
    n = normalize_name(name)
    for aliases in COMPETITION_ALIASES.values():
        if n in aliases or base_name(n) in aliases:
            return set(aliases)
    return {n}


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
)


def parse_date(value: str) -> Optional[datetime]:
    """Parse dates in ISO or Brazilian (DD/MM/YYYY) formats."""
    if not value:
        return None
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


@dataclass
class Match:
    """A single match, normalized across all source files."""

    competition: str
    season: Optional[int]
    date: Optional[datetime]
    home: str
    away: str
    home_goal: Optional[int]
    away_goal: Optional[int]
    round: Optional[str] = None
    stage: Optional[str] = None
    stadium: Optional[str] = None
    home_state: Optional[str] = None
    away_state: Optional[str] = None
    source_file: str = ""
    # extras from BR-Football-Dataset
    corners: Optional[dict] = field(default=None, repr=False)
    shots: Optional[dict] = field(default=None, repr=False)
    attacks: Optional[dict] = field(default=None, repr=False)

    def winner(self) -> Optional[str]:
        """Return 'home', 'away', 'draw' or None if score missing."""
        if self.home_goal is None or self.away_goal is None:
            return None
        if self.home_goal > self.away_goal:
            return "home"
        if self.away_goal > self.home_goal:
            return "away"
        return "draw"

    def to_dict(self) -> dict:
        return {
            "competition": self.competition,
            "season": self.season,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "home_team": display_name(self.home),
            "away_team": display_name(self.away),
            "home_goal": self.home_goal,
            "away_goal": self.away_goal,
            "round": self.round,
            "stage": self.stage,
            "stadium": self.stadium,
            "source_file": self.source_file,
        }


def _read_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    return rows


def _load_brasileirao(path: Path) -> list[Match]:
    matches = []
    for row in _read_csv(path):
        matches.append(
            Match(
                competition=BRASILEIRAO,
                season=_to_int(row.get("season")),
                date=parse_date(row.get("datetime", "")),
                home=row.get("home_team", "").strip(),
                away=row.get("away_team", "").strip(),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                round=str(row.get("round", "") or "") or None,
                home_state=row.get("home_team_state", "").strip() or None,
                away_state=row.get("away_team_state", "").strip() or None,
                source_file=path.name,
            )
        )
    return matches


def _load_copa_do_brasil(path: Path) -> list[Match]:
    matches = []
    for row in _read_csv(path):
        matches.append(
            Match(
                competition=COPA_DO_BRASIL,
                season=_to_int(row.get("season")),
                date=parse_date(row.get("datetime", "")),
                home=row.get("home_team", "").strip(),
                away=row.get("away_team", "").strip(),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                round=row.get("round", "").strip() or None,
                source_file=path.name,
            )
        )
    return matches


def _load_libertadores(path: Path) -> list[Match]:
    matches = []
    for row in _read_csv(path):
        matches.append(
            Match(
                competition=LIBERTADORES,
                season=_to_int(row.get("season")),
                date=parse_date(row.get("datetime", "")),
                home=row.get("home_team", "").strip(),
                away=row.get("away_team", "").strip(),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                stage=row.get("stage", "").strip() or None,
                source_file=path.name,
            )
        )
    return matches


def _load_br_dataset(path: Path) -> list[Match]:
    matches = []
    for row in _read_csv(path):
        d = parse_date(row.get("date", ""))
        corners = shots = attacks = None
        hc, ac = _to_int(row.get("home_corner")), _to_int(row.get("away_corner"))
        hs, as_ = _to_int(row.get("home_shots")), _to_int(row.get("away_shots"))
        ha, aa = _to_int(row.get("home_attack")), _to_int(row.get("away_attack"))
        if hc is not None or ac is not None:
            corners = {"home": hc, "away": ac}
        if hs is not None or as_ is not None:
            shots = {"home": hs, "away": as_}
        if ha is not None or aa is not None:
            attacks = {"home": ha, "away": aa}
        matches.append(
            Match(
                competition=(row.get("tournament") or "").strip() or "Unknown",
                season=d.year if d else None,
                date=d,
                home=row.get("home", "").strip(),
                away=row.get("away", "").strip(),
                home_goal=_to_int(row.get("home_goal")),
                away_goal=_to_int(row.get("away_goal")),
                source_file=path.name,
                corners=corners,
                shots=shots,
                attacks=attacks,
            )
        )
    return matches


def _load_historico(path: Path) -> list[Match]:
    matches = []
    for row in _read_csv(path):
        matches.append(
            Match(
                competition=HISTORICO,
                season=_to_int(row.get("Ano")),
                date=parse_date(row.get("Data", "")),
                home=row.get("Equipe_mandante", "").strip(),
                away=row.get("Equipe_visitante", "").strip(),
                home_goal=_to_int(row.get("Gols_mandante")),
                away_goal=_to_int(row.get("Gols_visitante")),
                round=str(row.get("Rodada", "") or "") or None,
                home_state=row.get("Mandante_UF", "").strip() or None,
                away_state=row.get("Visitante_UF", "").strip() or None,
                stadium=row.get("Arena", "").strip() or None,
                source_file=path.name,
            )
        )
    return matches


_PLAYER_INT_COLS = {
    "ID", "Age", "Overall", "Potential", "Jersey Number",
    "International Reputation", "Weak Foot", "Skill Moves",
}
_PLAYER_FLOAT_COLS = {
    "Value", "Wage", "Height", "Weight", "Crossing", "Finishing",
    "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve",
    "FKAccuracy", "LongPassing", "BallControl", "Acceleration",
    "SprintSpeed", "Agility", "Reactions", "Balance", "ShotPower",
    "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
    "GKKicking", "GKPositioning", "GKReflexes",
}


def _load_players(path: Path) -> list[dict]:
    players = []
    for row in _read_csv(path):
        rec: dict = {}
        for key, raw in row.items():
            if key is None:
                continue
            key = key.strip()
            if key in _PLAYER_INT_COLS:
                v = _to_int(raw)
            elif key in _PLAYER_FLOAT_COLS:
                try:
                    v = float(str(raw).strip()) if str(raw).strip() else None
                except ValueError:
                    v = None
            else:
                v = (raw or "").strip() or None
            rec[key] = v
        rec["_norm_name"] = normalize_name(rec.get("Name") or "")
        rec["_norm_club"] = normalize_name(rec.get("Club") or "")
        players.append(rec)
    return players


class SoccerData:
    """Container that loads and indexes all datasets."""

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)

        self.matches: list[Match] = []
        self.players: list[dict] = []

        self.matches.extend(self._safe("Brasileirao_Matches.csv", _load_brasileirao))
        self.matches.extend(self._safe("Brazilian_Cup_Matches.csv", _load_copa_do_brasil))
        self.matches.extend(self._safe("Libertadores_Matches.csv", _load_libertadores))
        self.matches.extend(self._safe("BR-Football-Dataset.csv", _load_br_dataset))
        self.matches.extend(self._safe("novo_campeonato_brasileiro.csv", _load_historico))
        self.players.extend(self._safe("fifa_data.csv", _load_players))

    def _safe(self, filename: str, loader) -> list:
        path = self.data_dir / filename
        if not path.exists():
            return []
        return loader(path)

    # ------------------------------------------------------------------
    # lookup helpers
    # ------------------------------------------------------------------
    def competition_matches(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> list[Match]:
        """Matches for a competition and season, deduplicated by source.

        Several CSV files cover the same real competition+season (e.g.
        three files contain the 2019 Brasileirão). To avoid double
        counting, only matches from the single best source file per
        season are returned. When no competition is given, all matches
        are returned as-is.
        """
        if competition is None:
            out = list(self.matches)
        else:
            group = competition_group(competition)
            out = [m for m in self.matches if normalize_name(m.competition) in group]
        if season is not None:
            out = [m for m in out if m.season == season]
            if competition is not None:
                return self._best_source_for(out, season)
            return out
        if competition is None:
            return out
        seasons = sorted({m.season for m in out if m.season is not None})
        result: list[Match] = []
        for s in seasons:
            result.extend(self._best_source_for(out, s))
        result.extend(m for m in out if m.season is None)
        return result

    def _best_source_for(self, matches: list[Match], season: int) -> list[Match]:
        by_file: dict[str, list[Match]] = defaultdict(list)
        for m in matches:
            if m.season == season:
                by_file[m.source_file or ""].append(m)
        if not by_file:
            return []
        best = min(
            by_file.items(),
            key=lambda kv: (-len(kv[1]), self._source_rank(kv[0])),
        )
        return best[1]

    @staticmethod
    def _source_rank(source_file: str) -> int:
        try:
            return _SOURCE_PRIORITY.index(source_file)
        except ValueError:
            return len(_SOURCE_PRIORITY)

    def team_matches(self, team: str) -> list[Match]:
        """All matches involving a team (home or away), any competition."""
        return [
            m
            for m in self.matches
            if name_matches(team, m.home) or name_matches(team, m.away)
        ]

    def head_to_head(self, team_a: str, team_b: str) -> list[Match]:
        """All matches where the two teams faced each other."""
        out = []
        for m in self.matches:
            a_home = name_matches(team_a, m.home)
            a_away = name_matches(team_a, m.away)
            b_home = name_matches(team_b, m.home)
            b_away = name_matches(team_b, m.away)
            if (a_home or b_home) and (a_away or b_away):
                # both teams present, on opposite sides
                if (a_home or a_away) and (b_home or b_away):
                    out.append(m)
        out.sort(key=lambda m: (m.date or datetime.min))
        return out

    def find_player(self, name: str) -> list[dict]:
        n = normalize_name(name)
        return [p for p in self.players if n in (p.get("_norm_name") or "")]

    def club_players(self, club: str) -> list[dict]:
        c = normalize_name(club)
        return [p for p in self.players if p.get("_norm_club") == c]

    def competitions(self) -> list[str]:
        seen = []
        for m in self.matches:
            if m.competition not in seen:
                seen.append(m.competition)
        return seen
