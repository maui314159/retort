"""CSV loaders and the in-memory :class:`SoccerData` container.

Loading is a two-pass job:

Pass 1 feeds every raw team spelling from the five match files into the
:class:`~brsoccer.normalize.TeamRegistry` so ambiguous name bases can be
detected (see :mod:`brsoccer.normalize`).

Pass 2 builds :class:`~brsoccer.models.Match` rows using canonical team
keys.  Because the files overlap -- both Brasileirão files cover
2012-2019 and the BR-Football file covers 2014-2023 -- rows are deduped
per competition on ``(date, home, away)``, keeping the first row in
source-priority order and merging in anything richer (stadium, kickoff
time, corner/shot/attack stats) from the dropped duplicates.

The FIFA player table is loaded with ``utf-8-sig`` (it carries a BOM)
and each player's club is joined to the team registry through the same
canonicaliser, enabling cross-file queries (players <-> matches).
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path

from .dates import parse_date, parse_int, parse_season
from .models import Match, Player
from .normalize import TeamRegistry, _preprocess

# ------------------------------------------------------------------ constants

COMPETITIONS: dict[str, str] = {
    "serie_a": "Brasileirão Série A",
    "serie_b": "Brasileirão Série B",
    "serie_c": "Brasileirão Série C",
    "copa_do_brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
}

#: League competitions (round-robin) for which standings make sense.
LEAGUES = {"serie_a", "serie_b", "serie_c"}

#: Friendly spellings a caller may use for competition arguments.
_COMP_ALIASES = {
    "brasileirao": "serie_a",
    "brasileirao serie a": "serie_a",
    "serie a": "serie_a",
    "a": "serie_a",
    "serie b": "serie_b",
    "b": "serie_b",
    "serie c": "serie_c",
    "c": "serie_c",
    "copa": "copa_do_brasil",
    "copa do brasil": "copa_do_brasil",
    "brazilian cup": "copa_do_brasil",
    "libertadores": "libertadores",
    "copa libertadores": "libertadores",
    "conmebol libertadores": "libertadores",
}

#: Source priority per competition: earlier rows win field conflicts on
#: dedupe, later sources may still donate extra fields (stats, venue).
_SOURCE_PRIORITY = {
    "serie_a": ("Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"),
    "copa_do_brasil": ("Brazilian_Cup_Matches.csv", "BR-Football-Dataset.csv"),
    "libertadores": ("Libertadores_Matches.csv",),
    "serie_b": ("BR-Football-Dataset.csv",),
    "serie_c": ("BR-Football-Dataset.csv",),
}

MATCH_FILES = (
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "BR-Football-Dataset.csv",
    "novo_campeonato_brasileiro.csv",
)
PLAYER_FILE = "fifa_data.csv"

_SKILL_COLUMNS = (
    "Crossing",
    "Finishing",
    "HeadingAccuracy",
    "ShortPassing",
    "Volleys",
    "Dribbling",
    "Curve",
    "FKAccuracy",
    "LongPassing",
    "BallControl",
    "Acceleration",
    "SprintSpeed",
    "Agility",
    "Reactions",
    "Balance",
    "ShotPower",
    "Jumping",
    "Stamina",
    "Strength",
    "LongShots",
    "Aggression",
    "Interceptions",
    "Positioning",
    "Vision",
    "Penalties",
    "Composure",
    "Marking",
    "StandingTackle",
    "SlidingTackle",
    "GKDiving",
    "GKHandling",
    "GKKicking",
    "GKPositioning",
    "GKReflexes",
)


def canonical_competition(text: str | None) -> str | None:
    """Map a user-supplied competition name to a registry code."""
    if not text:
        return None
    norm = _preprocess(text)
    if norm in COMPETITIONS:
        return norm
    return _COMP_ALIASES.get(norm)


def find_data_dir(explicit: str | Path | None = None) -> Path:
    """Locate the ``data/kaggle`` directory (env var, cwd, or repo root)."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get("BRSOCCER_DATA_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(Path.cwd() / "data" / "kaggle")
    # Repo root relative to this file (package lives at the repo root).
    candidates.append(Path(__file__).resolve().parent.parent / "data" / "kaggle")
    for candidate in candidates:
        if candidate.is_dir() and (candidate / MATCH_FILES[0]).exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate the Kaggle datasets. Expected a directory containing "
        f"{MATCH_FILES[0]} etc. Set BRSOCCER_DATA_DIR or pass data_dir explicitly. "
        f"Tried: {[str(c) for c in candidates]}"
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV as dicts with UTF-8-sig (BOM-tolerant) encoding."""
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


# ------------------------------------------------------------------ raw rows


def _raw_rows(data_dir: Path) -> list[dict]:
    """Read the five match files into a uniform raw-row shape."""
    raw: list[dict] = []

    # 1. Brasileirão Série A (2012-2022) -- team names like "Palmeiras-SP".
    for row in _read_csv(data_dir / "Brasileirao_Matches.csv"):
        raw.append(
            {
                "source": "Brasileirao_Matches.csv",
                "competition": "serie_a",
                "date_text": (row.get("datetime") or "").strip(),
                "date": parse_date(row.get("datetime")),
                "kickoff": (row.get("datetime") or "").split(" ")[1] if " " in (row.get("datetime") or "") else None,
                "season": parse_season(row.get("season")),
                "stage": (row.get("round") or "").strip(),
                "home_raw": (row.get("home_team") or "").strip(),
                "away_raw": (row.get("away_team") or "").strip(),
                "home_goal": parse_int(row.get("home_goal")),
                "away_goal": parse_int(row.get("away_goal")),
                "venue": None,
                "stats": None,
            }
        )

    # 2. Copa do Brasil (2012-2021) -- round numbers; "final" is round 8.
    for row in _read_csv(data_dir / "Brazilian_Cup_Matches.csv"):
        dt = (row.get("datetime") or "").strip()
        raw.append(
            {
                "source": "Brazilian_Cup_Matches.csv",
                "competition": "copa_do_brasil",
                "date_text": dt,
                "date": parse_date(dt),
                "kickoff": dt.split(" ")[1] if " " in dt else None,
                "season": parse_season(row.get("season")),
                "stage": (row.get("round") or "").strip(),
                "home_raw": (row.get("home_team") or "").strip(),
                "away_raw": (row.get("away_team") or "").strip(),
                "home_goal": parse_int(row.get("home_goal")),
                "away_goal": parse_int(row.get("away_goal")),
                "venue": None,
                "stats": None,
            }
        )

    # 3. Copa Libertadores (2013-2022) -- stages, some missing scores ("-").
    for row in _read_csv(data_dir / "Libertadores_Matches.csv"):
        dt = (row.get("datetime") or "").strip()
        raw.append(
            {
                "source": "Libertadores_Matches.csv",
                "competition": "libertadores",
                "date_text": dt,
                "date": parse_date(dt),
                "kickoff": dt.split(" ")[1] if " " in dt else None,
                "season": parse_season(row.get("season")),
                "stage": (row.get("stage") or "").strip(),
                "home_raw": (row.get("home_team") or "").strip(),
                "away_raw": (row.get("away_team") or "").strip(),
                "home_goal": parse_int(row.get("home_goal")),
                "away_goal": parse_int(row.get("away_goal")),
                "venue": None,
                "stats": None,
            }
        )

    # 4. BR-Football (2014-2023) -- corner/shot/attack stats, no round info.
    for row in _read_csv(data_dir / "BR-Football-Dataset.csv"):
        tournament = (row.get("tournament") or "").strip()
        code = {
            "Serie A": "serie_a",
            "Serie B": "serie_b",
            "Serie C": "serie_c",
            "Copa do Brasil": "copa_do_brasil",
        }.get(tournament)
        if code is None:
            continue
        stats = {
            "home_corners": parse_int(row.get("home_corner")),
            "away_corners": parse_int(row.get("away_corner")),
            "home_shots": parse_int(row.get("home_shots")),
            "away_shots": parse_int(row.get("away_shots")),
            "home_attacks": parse_int(row.get("home_attack")),
            "away_attacks": parse_int(row.get("away_attack")),
        }
        date_text = (row.get("date") or "").strip()
        match_date = parse_date(date_text)
        # Brazilian leagues run May-December, so league rows dated in
        # January/February belong to the previous year's season (only the
        # pandemic-delayed 2020 season ended in Feb 2021 in these files).
        # Cups (Copa do Brasil, Libertadores) do start in February.
        season = parse_season(date_text[:4])
        if code in LEAGUES and match_date is not None and match_date.month <= 2 and season:
            season -= 1
        raw.append(
            {
                "source": "BR-Football-Dataset.csv",
                "competition": code,
                "date_text": date_text,
                "date": match_date,
                "kickoff": (row.get("time") or "").strip() or None,
                "season": season,
                "stage": "",
                "home_raw": (row.get("home") or "").strip(),
                "away_raw": (row.get("away") or "").strip(),
                "home_goal": parse_int(row.get("home_goal")),
                "away_goal": parse_int(row.get("away_goal")),
                "venue": None,
                "stats": stats,
            }
        )

    # 5. Historical Brasileirão (2003-2019) -- DD/MM/YYYY dates, arenas.
    for row in _read_csv(data_dir / "novo_campeonato_brasileiro.csv"):
        raw.append(
            {
                "source": "novo_campeonato_brasileiro.csv",
                "competition": "serie_a",
                "date_text": (row.get("Data") or "").strip(),
                "date": parse_date(row.get("Data")),
                "kickoff": None,
                "season": parse_season(row.get("Ano")),
                "stage": (row.get("Rodada") or "").strip(),
                "home_raw": (row.get("Equipe_mandante") or "").strip(),
                "away_raw": (row.get("Equipe_visitante") or "").strip(),
                "home_goal": parse_int(row.get("Gols_mandante")),
                "away_goal": parse_int(row.get("Gols_visitante")),
                "venue": (row.get("Arena") or "").strip() or None,
                "stats": None,
            }
        )

    return raw


# ------------------------------------------------------------------ players


def _parse_skill(value: str | None) -> int | None:
    """Parse FIFA skill cells like ``88+2`` or ``84``."""
    if not value:
        return None
    head = value.strip().split("+")[0]
    try:
        return int(head)
    except ValueError:
        return None


def _load_players(data_dir: Path, registry: TeamRegistry) -> list[Player]:
    players: list[Player] = []
    for row in _read_csv(data_dir / PLAYER_FILE):
        club_raw = (row.get("Club") or "").strip()
        club_key = registry.key_of(club_raw) if club_raw else None
        if club_key and registry.entry_of(club_key) is None:
            club_key = None  # club not present in the match datasets
        skill = {col: _parse_skill(row.get(col)) for col in _SKILL_COLUMNS}
        skill = {k: v for k, v in skill.items() if v is not None}
        try:
            fifa_id = int(row.get("ID") or 0)
        except ValueError:
            continue
        players.append(
            Player(
                fifa_id=fifa_id,
                name=(row.get("Name") or "").strip(),
                age=parse_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=parse_int(row.get("Overall")) or 0,
                potential=parse_int(row.get("Potential")) or 0,
                club=club_raw,
                club_key=club_key,
                position=(row.get("Position") or "").strip(),
                jersey=parse_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip() or None,
                weight=(row.get("Weight") or "").strip() or None,
                value=(row.get("Value") or "").strip() or None,
                wage=(row.get("Wage") or "").strip() or None,
                skill=skill,
            )
        )
    return players


# ------------------------------------------------------------------ container


class SoccerData:
    """Queryable in-memory store of all six datasets."""

    def __init__(self, matches: list[Match], players: list[Player], registry: TeamRegistry) -> None:
        self.matches = sorted(matches, key=lambda m: m.sort_key())
        self.players = players
        self.registry = registry
        # Indexes (built once; every query is a filtered scan of these).
        self._by_team: dict[str, list[Match]] = defaultdict(list)
        self._by_comp: dict[str, list[Match]] = defaultdict(list)
        for match in self.matches:
            self._by_team[match.home].append(match)
            self._by_team[match.away].append(match)
            self._by_comp[match.competition].append(match)
        # Registry bookkeeping: competitions and seasons per team.
        for match in self.matches:
            for key in (match.home, match.away):
                entry = registry.entry_of(key)
                if entry:
                    entry.competitions.add(match.competition)
                    if match.season:
                        entry.seasons.add(match.season)

    # -- construction ----------------------------------------------------

    @classmethod
    def load(cls, data_dir: str | Path | None = None) -> "SoccerData":
        """Load all six CSV datasets (two registry passes + dedupe)."""
        directory = find_data_dir(data_dir)
        raw_rows = _raw_rows(directory)

        # Pass 1: feed every team spelling to the registry.
        registry = TeamRegistry()
        for row in raw_rows:
            registry.ingest(row["home_raw"])
            registry.ingest(row["away_raw"])
        registry.finalize()

        # Pass 2: build canonical Match rows, deduped per competition.
        matches = _build_matches(raw_rows, registry)
        players = _load_players(directory, registry)
        return cls(matches, players, registry)

    # -- convenience ------------------------------------------------------

    def matches_for_team(self, key: str) -> list[Match]:
        return self._by_team.get(key, [])

    def matches_for_competition(self, code: str) -> list[Match]:
        return self._by_comp.get(code, [])

    def team_display(self, key: str) -> str:
        return self.registry.display_of(key)

    def is_brazilian_team(self, key: str) -> bool:
        """True when a team plays in one of the Brazilian competitions."""
        entry = self.registry.entry_of(key)
        return bool(entry and (entry.competitions & {"serie_a", "serie_b", "serie_c", "copa_do_brasil"}))

    def brazilian_team_keys(self) -> list[str]:
        return [k for k in self.registry.entries if self.is_brazilian_team(k)]

    def seasons_for(self, code: str) -> list[int]:
        seasons = {m.season for m in self.matches_for_competition(code) if m.season}
        return sorted(seasons)


def _build_matches(raw_rows: list[dict], registry: TeamRegistry) -> list[Match]:
    """Turn raw rows into deduped, merged :class:`Match` objects.

    The source files overlap: both Brasileirão files cover 2012-2019 and
    BR-Football covers 2014-2023, with the same fixture sometimes dated a
    day apart (timezone drift between sources).

    * ``serie_a`` / ``serie_b`` are pure double round-robin leagues, so
      each ordered ``(season, home, away)`` pair occurs exactly once per
      season -- buckets collapse on that key regardless of small date
      drift, with source priority (see ``_SOURCE_PRIORITY``) breaking
      score conflicts.
    * ``serie_c`` (final-phase rematches), the cups and Libertadores can
      legitimately meet the same pair repeatedly, so those dedupe on the
      exact ``(date, home, away)`` first and then fuzzy-merge rows of the
      same season/pair dated within one day when the scores agree.
    """
    priority = {
        comp: {name: rank for rank, name in enumerate(names)}
        for comp, names in _SOURCE_PRIORITY.items()
    }
    ordered_rows = sorted(
        raw_rows,
        key=lambda r: priority[r["competition"]].get(r["source"], 99),
    )

    league_buckets: dict[tuple, list[Match]] = defaultdict(list)
    cup_buckets: dict[tuple, list[Match]] = defaultdict(list)

    for row in ordered_rows:
        comp = row["competition"]
        home = registry.key_of(row["home_raw"])
        away = registry.key_of(row["away_raw"])
        if not home or not away:
            continue
        match = Match(
            date=row["date"],
            date_text=row["date_text"],
            competition=comp,
            competition_display=COMPETITIONS[comp],
            season=row["season"],
            stage=row["stage"],
            home=home,
            away=away,
            home_display=registry.display_of(home),
            away_display=registry.display_of(away),
            home_goal=row["home_goal"],
            away_goal=row["away_goal"],
            kickoff=row["kickoff"],
            venue=row["venue"],
            source=row["source"],
        )
        if row["stats"]:
            match = replace(match, **row["stats"])
        if comp in ("serie_a", "serie_b"):
            league_buckets[(row["season"], home, away)].append(match)
        else:
            cup_buckets[(row["date"], home, away)].append(match)

    matches: list[Match] = []
    # Leagues: one row per ordered pair per season.
    for bucket in league_buckets.values():
        primary = bucket[0]
        for duplicate in bucket[1:]:
            primary = _merge(primary, duplicate)
        matches.append(primary)
    # Cups: exact-date key first, then a +/-1 day fuzzy pass per season pair.
    seen: dict[tuple, list[Match]] = defaultdict(list)
    for (match_date, home, away), bucket in cup_buckets.items():
        primary = bucket[0]
        for duplicate in bucket[1:]:
            primary = _merge(primary, duplicate)
        seen[(primary.season, home, away)].append(primary)
    for group in seen.values():
        merged: list[Match] = []
        for match in group:
            duplicate_of = None
            for kept in merged:
                if (
                    kept.date
                    and match.date
                    and abs((kept.date - match.date).days) <= 1
                    and _same_score(kept, match)
                ):
                    duplicate_of = kept
                    break
            if duplicate_of is None:
                merged.append(match)
            else:
                merged[merged.index(duplicate_of)] = _merge(duplicate_of, match)
        matches.extend(merged)
    return matches


def _same_score(a: Match, b: Match) -> bool:
    """True when two rows agree on the score (missing scores tolerated)."""
    if not a.played and not b.played:
        return True
    if a.played and not b.played:
        return True
    if not a.played and b.played:
        return True
    return a.home_goal == b.home_goal and a.away_goal == b.away_goal


def _merge(primary: Match, duplicate: Match) -> Match:
    """Keep ``primary`` but graft any richer fields from ``duplicate``."""
    updates: dict = {}
    for attr in (
        "home_goal",
        "away_goal",
        "kickoff",
        "venue",
        "home_corners",
        "away_corners",
        "home_shots",
        "away_shots",
        "home_attacks",
        "away_attacks",
    ):
        if getattr(primary, attr) is None and getattr(duplicate, attr) is not None:
            updates[attr] = getattr(duplicate, attr)
    if not primary.stage and duplicate.stage:
        updates["stage"] = duplicate.stage
    if updates:
        return replace(primary, **updates)
    return primary


__all__ = [
    "SoccerData",
    "COMPETITIONS",
    "LEAGUES",
    "canonical_competition",
    "find_data_dir",
    "load_default",
]


def load_default(data_dir: str | Path | None = None) -> SoccerData:
    """Convenience wrapper around :meth:`SoccerData.load`."""
    return SoccerData.load(data_dir)
