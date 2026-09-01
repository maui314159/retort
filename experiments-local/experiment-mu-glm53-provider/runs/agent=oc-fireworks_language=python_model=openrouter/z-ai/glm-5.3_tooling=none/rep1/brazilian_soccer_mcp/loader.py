"""
 brazilian_soccer_mcp / loader.py
 ================================

 Why
 ---
 Five of the six CSV files describe overlapping fixtures (the 2019
 Brasileirão appears in Brasileirao_Matches.csv, novo_campeonato_brasileiro
 .csv and BR-Football-Dataset.csv) and every file spells club names
 differently.  Serving queries straight off the raw rows would double- and
 triple-count matches.  This module loads all six datasets once, builds
 the club registry and merges duplicate fixtures into one canonical match
 list with source attribution.

 What
 ---
 :func:`load_dataset` returns a :class:`Dataset` holding:
   * ``matches``          - deduped, chronologically sorted :class:`Match` list;
   * ``players``          - the FIFA player database;
   * ``clubs``            - canonical club registry (key -> :class:`Club`);
   * ``competition_matches`` / ``season_matches`` - per-competition and
     per-(competition, season) indexes;
   * ``club_matches``     - club key -> matches involving that club;
   * ``cup_final_rounds`` - Copa do Brasil season -> final round number.

 Dedup rules (validated against the data, see TASK.md analysis):
   * League competitions (Série A/B/C) are double round-robins, so a
     (season, home-key, away-key) orientation can occur exactly once.
     The best row per orientation wins - source priority
     Brasileirao > novo > BR-Football, preferring a row that has a final
     score over an 'NA' (unplayed) row; round/venue gaps are back-filled
     from the dropped siblings.
   * Cup competitions (Copa do Brasil, Libertadores) can legitimately pair
     the same teams twice in one season, so rows merge only when the score
     matches (or one side is unplayed) AND the dates are within two days.
   * Source priorities keep the richer, primary files (Brasileirao_Matches,
     Brazilian_Cup_Matches, Libertadores_Matches) ahead of the auxiliary
     BR-Football dump.

 Data repairs applied while reading (documented in normalizer.py):
   * novo UF "BH" -> "BA"; novo ("Vitória", "ES") -> "BA".
   * 'NA'/'-' goal cells become None (scheduled, not played).

 Performance: ~33k CSV rows parse in well under a second; all indexes are
 built once at load time so queries are in-memory scans.

 Test: ``tests/test_loader.py``
==================================
"""

from __future__ import annotations

import csv
import datetime as _dt
import os
from collections import Counter, defaultdict
from pathlib import Path

from .models import (  # noqa: F401 (StandingRow re-export)
    Club,
    Match,
    Player,
    StandingRow,
)
from .normalizer import (
    COMPETITIONS,
    DISPLAY_OVERRIDES,
    NOVO_TEAM_UF_FIX,
    NOVO_UF_FIX,
    ClubNormalizer,
    parse_date,
    parse_goals,
    parse_int,
    parse_money,
    parse_time,
    squash,
)

#: The six source files (TASK.md "Provided Data").
DATA_FILES = {
    "brasileirao": "Brasileirao_Matches.csv",
    "cup": "Brazilian_Cup_Matches.csv",
    "libertadores": "Libertadores_Matches.csv",
    "br_football": "BR-Football-Dataset.csv",
    "historical": "novo_campeonato_brasileiro.csv",
    "fifa": "fifa_data.csv",
}

#: Lower number = preferred when two sources describe the same fixture.
_SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 0,
    "Brazilian_Cup_Matches.csv": 1,
    "Libertadores_Matches.csv": 1,
    "novo_campeonato_brasileiro.csv": 2,
    "BR-Football-Dataset.csv": 3,
}

_LEAGUE_COMPETITIONS = {"serie_a", "serie_b", "serie_c"}

#: A club fielded in a league season plays a full round robin; anyone with
#: fewer appearances than this in a competition-season is a mislabeled
#: state-league/cup row (e.g. Suzano-SP's single "Serie B" 2019 match).
_MIN_LEAGUE_APPEARANCES = 8

#: BR-Football "tournament" values -> canonical ids.
_BRF_TOURNAMENT_MAP = {
    "Serie A": "serie_a",
    "Serie B": "serie_b",
    "Serie C": "serie_c",
    "Copa do Brasil": "copa_do_brasil",
}

#: FIFA columns kept as player skill attributes.
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
    "ShotPower",
    "Stamina",
    "Strength",
    "LongShots",
    "Penalties",
    "Interceptions",
    "StandingTackle",
    "SlidingTackle",
)


def default_data_dir() -> Path:
    """Locate ``data/kaggle``: env override first, then repo layout."""
    env = os.environ.get("BRAZILIAN_SOCCER_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "kaggle"


class Dataset:
    """In-memory knowledge graph: matches, players, clubs and indexes."""

    def __init__(
        self,
        matches: list[Match],
        players: list[Player],
        clubs: dict[str, Club],
        normalizer: ClubNormalizer,
    ) -> None:
        self.matches = matches
        self.players = players
        self.clubs = clubs
        self._normalizer = normalizer
        self.club_core_index: dict[str, list[str]] = defaultdict(list)
        for key, club in clubs.items():
            self.club_core_index[club.core].append(key)

        # -- indexes -------------------------------------------------------
        self.competition_matches: dict[str, list[Match]] = defaultdict(list)
        self.season_matches: dict[tuple[str, int], list[Match]] = defaultdict(list)
        self.club_matches: dict[str, list[Match]] = defaultdict(list)
        self.cup_final_rounds: dict[int, int] = {}

        for match in matches:
            self.competition_matches[match.competition].append(match)
            if match.season is not None:
                self.season_matches[(match.competition, match.season)].append(match)
            self.club_matches[match.home_key].append(match)
            self.club_matches[match.away_key].append(match)

        # Copa do Brasil "final" detection: highest round per season, and
        # only a final when that round holds <= 2 matches (two legs).  An
        # incomplete season (2021 in this data) therefore reports no final.
        by_round: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for match in self.competition_matches.get("copa_do_brasil", []):
            if match.season is not None and match.round and match.round.isdigit():
                by_round[match.season][match.round] += 1
        for season, rounds in by_round.items():
            top_round = max(rounds)
            if rounds[top_round] <= 2:
                self.cup_final_rounds[season] = int(top_round)

        # FIFA club resolution cache: raw club string -> club key | None.
        self._fifa_club_keys: dict[str, str | None] = {}

    # -- helpers ----------------------------------------------------------

    def seasons_for(self, competition: str) -> list[int]:
        """Sorted seasons available for a competition."""
        seasons = {
            m.season
            for m in self.competition_matches.get(competition, [])
            if m.season is not None
        }
        return sorted(seasons)

    def resolve_club_key(self, name: str) -> str | None:
        """Canonical key for any team spelling, or None."""
        return self._normalizer.key(name)

    def fifa_club_key(self, club_name: str | None) -> str | None:
        """Resolve a FIFA 'Club' string to a registry club key."""
        if not club_name:
            return None
        cleaned = squash(club_name)
        if cleaned in self._fifa_club_keys:
            return self._fifa_club_keys[cleaned]
        key = self._normalizer.key(club_name)
        result = key if key in self.clubs else None
        self._fifa_club_keys[cleaned] = result
        return result


# --------------------------------------------------------------------------
# Raw row parsing (one helper per source file)
# --------------------------------------------------------------------------


def _read_csv(path: Path, encoding: str = "utf-8") -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required dataset file is missing: {path} "
            f"(set BRAZILIAN_SOCCER_DATA_DIR if data lives elsewhere)"
        )
    with path.open(encoding=encoding, newline="") as handle:
        return list(csv.DictReader(handle))


def _novo_uf(team: str, uf: str) -> str | None:
    """Apply the novo-file UF repairs documented in normalizer.py."""
    uf = (uf or "").strip().upper()
    uf = NOVO_UF_FIX.get(uf, uf)
    if not uf:
        return None
    return NOVO_TEAM_UF_FIX.get((squash(team), uf), uf)


def _raw_rows(data_dir: Path) -> list[dict]:
    """
    Parse the five match CSVs into intermediate row dicts:
    {source, competition, season, date, time, home_raw, away_raw,
     home_state, away_state, home_goals, away_goals, round, stage, venue, stats}
    """
    rows: list[dict] = []

    # 1. Brasileirão Série A (2012-2022), names like "Palmeiras-SP".
    for r in _read_csv(data_dir / DATA_FILES["brasileirao"]):
        season = parse_int(r.get("season"))
        rows.append(
            {
                "source": "Brasileirao_Matches.csv",
                "competition": "serie_a",
                "season": season,
                "date": parse_date(r.get("datetime")),
                "time": parse_time(
                    (r.get("datetime") or "").split(" ")[1]
                    if " " in (r.get("datetime") or "")
                    else None
                ),
                "home_raw": r.get("home_team") or "",
                "away_raw": r.get("away_team") or "",
                "home_state": r.get("home_team_state"),
                "away_state": r.get("away_team_state"),
                "home_goals": parse_goals(r.get("home_goal")),
                "away_goals": parse_goals(r.get("away_goal")),
                "round": str(r.get("round") or "") or None,
                "stage": None,
                "venue": None,
                "stats": None,
            }
        )

    # 2. Copa do Brasil (2012-2021), numeric rounds 1-8.
    for r in _read_csv(data_dir / DATA_FILES["cup"]):
        rows.append(
            {
                "source": "Brazilian_Cup_Matches.csv",
                "competition": "copa_do_brasil",
                "season": parse_int(r.get("season")),
                "date": parse_date(r.get("datetime")),
                "time": parse_time(
                    (r.get("datetime") or "").split(" ")[1]
                    if " " in (r.get("datetime") or "")
                    else None
                ),
                "home_raw": r.get("home_team") or "",
                "away_raw": r.get("away_team") or "",
                "home_state": None,
                "away_state": None,
                "home_goals": parse_goals(r.get("home_goal")),
                "away_goals": parse_goals(r.get("away_goal")),
                "round": str(r.get("round") or "") or None,
                "stage": None,
                "venue": None,
                "stats": None,
            }
        )

    # 3. Copa Libertadores (2013-2022 + one unfinished final), stage labels.
    for r in _read_csv(data_dir / DATA_FILES["libertadores"]):
        rows.append(
            {
                "source": "Libertadores_Matches.csv",
                "competition": "libertadores",
                "season": parse_int(r.get("season")),
                "date": parse_date(r.get("datetime")),
                "time": parse_time(
                    (r.get("datetime") or "").split(" ")[1]
                    if " " in (r.get("datetime") or "")
                    else None
                ),
                "home_raw": r.get("home_team") or "",
                "away_raw": r.get("away_team") or "",
                "home_state": None,
                "away_state": None,
                "home_goals": parse_goals(r.get("home_goal")),
                "away_goals": parse_goals(r.get("away_goal")),
                "round": None,
                "stage": (r.get("stage") or "").strip() or None,
                "venue": None,
                "stats": None,
            }
        )

    # 4. BR-Football extended stats (Série A/B/C + Copa do Brasil, 2014-2023).
    for r in _read_csv(data_dir / DATA_FILES["br_football"]):
        competition = _BRF_TOURNAMENT_MAP.get((r.get("tournament") or "").strip())
        if competition is None:
            continue
        stats = None
        if any(
            r.get(k) not in (None, "")
            for k in (
                "home_corner",
                "away_corner",
                "home_shots",
                "away_shots",
                "home_attack",
                "away_attack",
            )
        ):
            stats = {
                "corners": {
                    "home": parse_int(r.get("home_corner")),
                    "away": parse_int(r.get("away_corner")),
                },
                "shots": {
                    "home": parse_int(r.get("home_shots")),
                    "away": parse_int(r.get("away_shots")),
                },
                "attacks": {
                    "home": parse_int(r.get("home_attack")),
                    "away": parse_int(r.get("home_attack")),
                },
                "half_time": {
                    "home": (r.get("ht_result") or "").strip() or None,
                    "away": (r.get("at_result") or "").strip() or None,
                },
            }
        rows.append(
            {
                "source": "BR-Football-Dataset.csv",
                "competition": competition,
                "season": parse_int((r.get("date") or "")[:4]),
                "date": parse_date(r.get("date")),
                "time": parse_time(r.get("time")),
                "home_raw": r.get("home") or "",
                "away_raw": r.get("away") or "",
                "home_state": None,
                "away_state": None,
                "home_goals": parse_goals(r.get("home_goal")),
                "away_goals": parse_goals(r.get("away_goal")),
                "round": None,
                "stage": None,
                "venue": None,
                "stats": stats,
            }
        )

    # 5. Historical Brasileirão (2003-2019), DD/MM/YYYY dates, stadium, UF cols.
    for r in _read_csv(data_dir / DATA_FILES["historical"]):
        rows.append(
            {
                "source": "novo_campeonato_brasileiro.csv",
                "competition": "serie_a",
                "season": parse_int(r.get("Ano")),
                "date": parse_date(r.get("Data")),
                "time": None,
                "home_raw": r.get("Equipe_mandante") or "",
                "away_raw": r.get("Equipe_visitante") or "",
                "home_state": _novo_uf(
                    r.get("Equipe_mandante") or "", r.get("Mandante_UF") or ""
                ),
                "away_state": _novo_uf(
                    r.get("Equipe_visitante") or "", r.get("Visitante_UF") or ""
                ),
                "home_goals": parse_goals(r.get("Gols_mandante")),
                "away_goals": parse_goals(r.get("Gols_visitante")),
                "round": str(r.get("Rodada") or "") or None,
                "stage": None,
                "venue": (r.get("Arena") or "").strip() or None,
                "stats": None,
            }
        )

    return rows


# --------------------------------------------------------------------------
# Dedup
# --------------------------------------------------------------------------


def _sort_key(row: dict):
    return (
        _SOURCE_PRIORITY.get(row["source"], 9),
        row["date"] is None,
        row["date"] or _dt.date.min,
    )


def _same_fixture(kept: dict, candidate: dict) -> bool:
    """
    Do these two cup rows describe the same fixture?  (League rows never
    reach here - they are merged by orientation in :func:`_dedup`.)
    """
    kept_score = (kept["home_goals"], kept["away_goals"])
    cand_score = (candidate["home_goals"], candidate["away_goals"])
    score_match = (
        kept_score == cand_score
        or kept_score == (None, None)
        or cand_score == (None, None)
    )
    if not score_match:
        return False
    if kept["date"] is None or candidate["date"] is None:
        return True
    return abs((kept["date"] - candidate["date"]).days) <= 2


def _dedup(rows: list[dict]) -> list[dict]:
    """
    Merge duplicate fixtures.

    Leagues (double round-robin): exactly one row survives per (competition,
    season, home, away) orientation - the highest-priority source that has a
    final score, with round/venue gaps back-filled from dropped siblings.
    Score disagreements between sources (e.g. BR-Football vs Brasileirão)
    are resolved in favour of the primary source.

    Cups: rows merge only on score-match (or one side unplayed) AND dates
    within two days, because the same pairing can legitimately repeat in
    later rounds.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[
            (row["competition"], row["season"], row["home_key"], row["away_key"])
        ].append(row)

    kept_rows: list[dict] = []
    for group in groups.values():
        group.sort(key=_sort_key)
        league = group[0]["competition"] in _LEAGUE_COMPETITIONS
        if league:
            kept_rows.append(_best_league_row(group))
            continue
        kept: list[dict] = []
        for candidate in group:
            duplicate_of = None
            for index, existing in enumerate(kept):
                if _same_fixture(existing, candidate):
                    duplicate_of = index
                    break
            if duplicate_of is None:
                kept.append(candidate)
            else:
                existing = kept[duplicate_of]
                # Prefer a played row over an unplayed one.
                if (existing["home_goals"], existing["away_goals"]) == (
                    None,
                    None,
                ) and (candidate["home_goals"], candidate["away_goals"]) != (
                    None,
                    None,
                ):
                    candidate = dict(candidate)
                    _backfill(candidate, existing)
                    kept[duplicate_of] = candidate
                else:
                    _backfill(existing, candidate)
        kept_rows.extend(kept)
    return kept_rows


def _backfill(target: dict, donor: dict) -> None:
    """Copy round/stage/venue/stats into target where target is missing."""
    for field_name in ("round", "stage", "venue", "stats"):
        if target.get(field_name) is None:
            target[field_name] = donor.get(field_name)


def _best_league_row(group: list[dict]) -> dict:
    """Highest-priority row with a final score; round/venue back-filled."""
    chosen = None
    for candidate in group:  # already sorted by source priority
        if (candidate["home_goals"], candidate["away_goals"]) != (None, None):
            chosen = candidate
            break
    if chosen is None:
        return group[0]
    best = dict(chosen)
    for other in group:
        if other is not chosen:
            _backfill(best, other)
    return best


def _drop_mislabeled_league_rows(rows: list[dict]) -> list[dict]:
    """
    Two guards against mislabeled league fixtures in the auxiliary files:

    1. BR-Football occasionally tags Série B fixtures as "Serie A" (e.g.
       the relegated Botafogo/Coritiba/Goiás/Vasco appear 10-12 times in its
       2021 "Serie A" while also playing full Série B seasons).  When a
       season of a league is covered by a primary source (Brasileirao_
       Matches / novo_campeonato_brasileiro), BR-Football league rows
       featuring clubs the primary source never fields in that season are
       dropped as mislabels.

    2. Some rows are state-league fixtures mislabeled as national league
       games (e.g. Suzano-SP and Guarulhos-SP appear once each in the 2019
       "Serie B").  A club fielded in a league season plays a full round
       robin - never just a match or two - so any league row where either
       club appears fewer than ``_MIN_LEAGUE_APPEARANCES`` times in that
       competition-season is dropped.
    """
    primary_participants: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in rows:
        if row["source"] in (
            "Brasileirao_Matches.csv",
            "novo_campeonato_brasileiro.csv",
        ):
            key = (row["competition"], row["season"])
            primary_participants[key].add(row["home_key"])
            primary_participants[key].add(row["away_key"])

    phase_one: list[dict] = []
    for row in rows:
        if (
            row["source"] == "BR-Football-Dataset.csv"
            and row["competition"] in _LEAGUE_COMPETITIONS
        ):
            key = (row["competition"], row["season"])
            participants = primary_participants.get(key)
            if participants is not None and (
                row["home_key"] not in participants
                or row["away_key"] not in participants
            ):
                continue  # mislabeled fixture: club not in that league season
        phase_one.append(row)

    appearances: dict[tuple[str, int], Counter] = defaultdict(Counter)
    for row in phase_one:
        if row["competition"] in _LEAGUE_COMPETITIONS and row["season"] is not None:
            key = (row["competition"], row["season"])
            appearances[key][row["home_key"]] += 1
            appearances[key][row["away_key"]] += 1

    kept: list[dict] = []
    for row in phase_one:
        if row["competition"] in _LEAGUE_COMPETITIONS and row["season"] is not None:
            counts = appearances[(row["competition"], row["season"])]
            if (
                counts[row["home_key"]] < _MIN_LEAGUE_APPEARANCES
                or counts[row["away_key"]] < _MIN_LEAGUE_APPEARANCES
            ):
                continue  # state-league fixture mislabeled as a league game
        kept.append(row)
    return kept


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------


def _display_name(raw_names: list[str], key: str) -> str:
    """Pick the nicest display: curated override, else the most-accented,
    shortest, most frequent raw spelling."""
    core, _, region = key.partition("|")
    override = DISPLAY_OVERRIDES.get((core, region or None))
    if override:
        return override

    def _accents(name: str) -> int:
        return sum(1 for ch in name if ord(ch) > 127)

    counts: dict[str, int] = {}
    for name in raw_names:
        counts[name] = counts.get(name, 0) + 1

    def _accent_rank(name: str) -> tuple[int, int, int, str]:
        """(accents desc, length asc, frequency desc, name) for min()."""
        return (-_accents(name), len(name), -counts[name], name)

    return min(counts, key=_accent_rank)


def _build_registry(
    rows: list[dict], kept: list[dict], normalizer: ClubNormalizer
) -> dict[str, Club]:
    """Registry of clubs: variants from all rows, counts from deduped rows."""
    variants: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        for side in ("home", "away"):
            variants[row[f"{side}_key"]].add(row[f"{side}_raw"])

    counts: dict[str, int] = defaultdict(int)
    played: dict[str, int] = defaultdict(int)
    competitions: dict[str, set[str]] = defaultdict(set)
    seasons: dict[str, set[int]] = defaultdict(set)
    for row in kept:
        for side in ("home", "away"):
            key = row[f"{side}_key"]
            counts[key] += 1
            if (row["home_goals"], row["away_goals"]) != (None, None):
                played[key] += 1
            competitions[key].add(row["competition"])
            if row["season"] is not None:
                seasons[key].add(row["season"])

    clubs: dict[str, Club] = {}
    for key in sorted(variants):
        first_variant = min(variants[key])
        identity = normalizer.identity(first_variant)
        clubs[key] = Club(
            key=key,
            core=identity.core,
            state=identity.state,
            country=identity.country,
            display=_display_name(sorted(variants[key]), key),
            variants=sorted(variants[key]),
            match_count=counts.get(key, 0),
            played_count=played.get(key, 0),
            competitions=sorted(competitions.get(key, set())),
            seasons=sorted(seasons.get(key, set())),
        )
    return clubs


# --------------------------------------------------------------------------
# Players
# --------------------------------------------------------------------------


def _load_players(data_dir: Path) -> list[Player]:
    """Load the FIFA database (utf-8-sig: the file starts with a BOM)."""
    players: list[Player] = []
    for r in _read_csv(data_dir / DATA_FILES["fifa"], encoding="utf-8-sig"):
        position = (r.get("Position") or "").strip() or None
        skills = {}
        for column in _SKILL_COLUMNS:
            value = parse_int(r.get(column))
            if value is not None:
                skills[column] = value
        players.append(
            Player(
                player_id=parse_int(r.get("ID")),
                name=(r.get("Name") or "").strip(),
                age=parse_int(r.get("Age")),
                nationality=(r.get("Nationality") or "").strip(),
                overall=parse_int(r.get("Overall")) or 0,
                potential=parse_int(r.get("Potential")) or 0,
                club=(r.get("Club") or "").strip() or None,
                position=position,
                jersey=parse_int(r.get("Jersey Number")),
                preferred_foot=(r.get("Preferred Foot") or "").strip() or None,
                value=(r.get("Value") or "").strip() or None,
                wage=(r.get("Wage") or "").strip() or None,
                value_eur=parse_money(r.get("Value")),
                wage_eur=parse_money(r.get("Wage")),
                height=(r.get("Height") or "").strip() or None,
                weight=(r.get("Weight") or "").strip() or None,
                skills=skills,
            )
        )
    return players


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def load_dataset(data_dir: str | Path | None = None) -> Dataset:
    """Load every CSV, normalise, dedup and index.  Call once per process."""
    data_dir = Path(data_dir) if data_dir else default_data_dir()

    rows = _raw_rows(data_dir)

    # Pass 1: parse names, learn dominant regions.
    normalizer = ClubNormalizer()
    for row in rows:
        for side in ("home", "away"):
            row[f"{side}_identity"] = normalizer.register(
                row[f"{side}_raw"], row[f"{side}_state"]
            )
    normalizer.finalize()

    # Pass 2: canonical keys - stateless cores adopt their dominant region,
    # so the BR-Football "Santos" merges with the Brasileirão "Santos-SP".
    for row in rows:
        for side in ("home", "away"):
            identity = normalizer.identity(row[f"{side}_raw"], row[f"{side}_state"])
            row[f"{side}_identity"] = identity
            row[f"{side}_key"] = identity.key()
            if identity.region and not row[f"{side}_state"]:
                row[f"{side}_state"] = identity.region

    rows = _drop_mislabeled_league_rows(rows)
    kept = _dedup(rows)
    clubs = _build_registry(rows, kept, normalizer)

    # Match objects, with registry display names.
    matches: list[Match] = []
    for row in kept:
        competition = row["competition"]
        matches.append(
            Match(
                competition=competition,
                competition_display=COMPETITIONS[competition]["display"],
                season=row["season"],
                date=row["date"],
                time=row["time"],
                home=clubs[row["home_key"]].display,
                away=clubs[row["away_key"]].display,
                home_key=row["home_key"],
                away_key=row["away_key"],
                home_goals=row["home_goals"],
                away_goals=row["away_goals"],
                round=row["round"],
                stage=row["stage"],
                venue=row["venue"],
                source=row["source"],
                stats=row["stats"],
            )
        )

    matches.sort(
        key=lambda m: (
            m.date is None,
            m.date or _dt.date.min,
            m.competition,
            m.season or 0,
        )
    )
    players = _load_players(data_dir)
    return Dataset(matches=matches, players=players, clubs=clubs, normalizer=normalizer)
