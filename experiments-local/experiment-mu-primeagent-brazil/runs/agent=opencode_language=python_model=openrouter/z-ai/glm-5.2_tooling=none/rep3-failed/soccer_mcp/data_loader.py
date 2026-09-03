"""
Context
=======
Brazilian Soccer MCP Server - data loader.

Part of the ``soccer_mcp`` package.  Loads the six Kaggle CSV datasets from
``data/kaggle/`` into an in-memory :class:`SoccerData` object that the query
layer (:mod:`soccer_mcp.queries`) and the MCP server (:mod:`soccer_mcp.server`)
operate on.

Datasets loaded
---------------
1. ``Brasileirao_Matches.csv``      - Brasileirao Serie A (2012-2022)
2. ``novo_campeonato_brasileiro.csv`` - Brasileirao Serie A historical (2003-2019)
3. ``BR-Football-Dataset.csv``      - Serie A/B/C + Copa do Brasil (2014-2023, rich stats)
4. ``Brazilian_Cup_Matches.csv``    - Copa do Brasil (2012-2021)
5. ``Libertadores_Matches.csv``     - Copa Libertadores (2013-2022)
6. ``fifa_data.csv``                - FIFA player database (~18k players)

Source-priority merge
---------------------
The two Brasileirao files and the BR-Football-Dataset overlap for many seasons.
To avoid double counting in standings / head-to-head / team statistics the
loader tags every match with a per-competition *source rank* and, for each
(competition, season), keeps only the rows from the single best (lowest-rank)
source.  Lower rank == higher priority:

    Brasileirao Serie A : Brasileirao_Matches (0) > BR-Football-Dataset (1) > historical (2)
    Brasileirao Serie B : BR-Football-Dataset (0)
    Brasileirao Serie C : BR-Football-Dataset (0)
    Copa do Brasil       : Brazilian_Cup_Matches (0) > BR-Football-Dataset (1)
    Copa Libertadores    : Libertadores_Matches (0)

This yields one clean record per real-world match for league-style
calculations while still letting the BR-Football-Dataset supply the only data
for Serie B/C, the 2023 Serie A season and the 2022-2023 Copa do Brasil, plus
detailed corner/shot/attack statistics via the separate ``stats_matches``
collection (queried by ``match_stats``).

Team names are canonicalised with :class:`soccer_mcp.normalize.TeamNormalizer`
so that "Sao Paulo-SP", "Sao Paulo" and "Sao Paulo" all resolve to one entity.
Dates are normalised to ISO.  Goals are normalised to int.

The loader is lazy and cached: the first call to :func:`get_data` parses the
CSVs once and returns a process-wide singleton.
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from .normalize import TeamNormalizer, parse_date, to_int_goal

# ---------------------------------------------------------------------------
# Canonical competition names and the user-facing aliases that map to them.
# ---------------------------------------------------------------------------
COMP_BRASILEIRAO_A = "Brasileirao Serie A"
COMP_BRASILEIRAO_B = "Brasileirao Serie B"
COMP_BRASILEIRAO_C = "Brasileirao Serie C"
COMP_COPA_BRASIL = "Copa do Brasil"
COMP_LIBERTADORES = "Copa Libertadores"

ALL_COMPETITIONS = (
    COMP_BRASILEIRAO_A,
    COMP_BRASILEIRAO_B,
    COMP_BRASILEIRAO_C,
    COMP_COPA_BRASIL,
    COMP_LIBERTADORES,
)

# Aliases (lowercased, alphanumeric) accepted in query parameters.
COMPETITION_ALIASES: dict[str, str] = {
    "brasileiraoa": COMP_BRASILEIRAO_A,
    "brasileirao": COMP_BRASILEIRAO_A,
    "seriea": COMP_BRASILEIRAO_A,
    "seriesa": COMP_BRASILEIRAO_A,
    "serieb": COMP_BRASILEIRAO_B,
    "seriesb": COMP_BRASILEIRAO_B,
    "seriec": COMP_BRASILEIRAO_C,
    "seriesc": COMP_BRASILEIRAO_C,
    "copadobrasil": COMP_COPA_BRASIL,
    "copa": COMP_COPA_BRASIL,
    "copabrasil": COMP_COPA_BRASIL,
    "braziliancup": COMP_COPA_BRASIL,
    "libertadores": COMP_LIBERTADORES,
    "copalibertadores": COMP_LIBERTADORES,
    "liberta": COMP_LIBERTADORES,
}

# Tournament name as written in BR-Football-Dataset.csv -> canonical competition.
BR_FD_TOURNAMENT_MAP = {
    "Serie A": COMP_BRASILEIRAO_A,
    "Serie B": COMP_BRASILEIRAO_B,
    "Serie C": COMP_BRASILEIRAO_C,
    "Copa do Brasil": COMP_COPA_BRASIL,
}

# Per-competition source priority (lower == higher priority).
SOURCE_RANK = {
    COMP_BRASILEIRAO_A: {"brasileirao_matches": 0, "br_football": 1, "historical": 2},
    COMP_BRASILEIRAO_B: {"br_football": 0},
    COMP_BRASILEIRAO_C: {"br_football": 0},
    COMP_COPA_BRASIL: {"brazilian_cup": 0, "br_football": 1},
    COMP_LIBERTADORES: {"libertadores": 0},
}

DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kaggle"
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Match:
    """A single football match, source-normalised."""

    date: Optional[str]  # ISO YYYY-MM-DD
    season: Optional[str]  # "YYYY" string
    competition: str
    round_or_stage: Optional[str]
    home_team: str  # canonical key
    away_team: str  # canonical key
    home_goals: Optional[int]
    away_goals: Optional[int]
    source: str

    # Fields populated only from BR-Football-Dataset (None otherwise).
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_attacks: Optional[int] = None
    away_attacks: Optional[int] = None
    ht_result: Optional[str] = None  # home half-time outcome label (WON/LOST/DRAW)
    at_result: Optional[str] = None  # away half-time outcome label
    arena: Optional[str] = None  # from historical file

    source_rank: int = 0
    home_display: str = ""
    away_display: str = ""


@dataclass
class Player:
    """A FIFA player record (subset of relevant columns)."""

    id: Optional[str]
    name: Optional[str]
    age: Optional[int]
    nationality: Optional[str]
    overall: Optional[int]
    potential: Optional[int]
    club: Optional[str]
    club_canonical: Optional[str]
    position: Optional[str]
    jersey_number: Optional[str]
    height: Optional[str]
    weight: Optional[str]
    preferred_foot: Optional[str]
    value: Optional[str]
    wage: Optional[str]
    # Selected skill attributes used for "attributes" responses.
    crossing: Optional[int] = None
    finishing: Optional[int] = None
    dribbling: Optional[int] = None
    shortpassing: Optional[int] = None
    longshots: Optional[int] = None
    defending: Optional[int] = None
    gkdiving: Optional[int] = None
    pace: Optional[int] = None
    shooting: Optional[int] = None
    passing: Optional[int] = None
    dribbling2: Optional[int] = None  # "Dribbling.1"
    defending2: Optional[int] = None  # "Defending.1"
    physical: Optional[int] = None


@dataclass
class SoccerData:
    """In-memory representation of the whole dataset."""

    normalizer: TeamNormalizer
    matches: list[Match] = field(default_factory=list)
    raw_matches: list[Match] = field(default_factory=list)
    stats_matches: list[Match] = field(default_factory=list)
    players: list[Player] = field(default_factory=list)
    # canonical_key -> display name
    team_display: dict[str, str] = field(default_factory=dict)
    # (competition, season) -> set(source ranks present) for diagnostics
    season_sources: dict[tuple[str, str], set] = field(default_factory=dict)

    # ---- lookup helpers -------------------------------------------------
    def seasons_for(self, competition: str) -> list[str]:
        out = set()
        for m in self.matches:
            if m.competition == competition and m.season:
                out.add(m.season)
        return sorted(out)

    def competitions(self) -> list[str]:
        seen = set()
        ordered = []
        for c in ALL_COMPETITIONS:
            for m in self.matches:
                if m.competition == c and c not in seen:
                    seen.add(c)
                    ordered.append(c)
                    break
        return ordered


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_season(value) -> Optional[str]:
    """Normalise a season value to a 4-digit year string, or None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"na", "nan", "none"}:
        return None
    if text.isdigit() and 1900 <= int(text) <= 2100:
        return text
    # Fallback: try to extract a 4-digit year.
    import re

    m = re.search(r"\d{4}", text)
    return m.group(0) if m else None


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def resolve_competition(name: Optional[str]) -> Optional[str]:
    """Resolve a user-supplied competition name to a canonical one."""
    if not name:
        return None
    if name in ALL_COMPETITIONS:
        return name
    import re

    from .normalize import strip_accents

    key = re.sub(r"[^a-z0-9]", "", strip_accents(name.lower()))
    return COMPETITION_ALIASES.get(key)


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------
def _read_rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _observe_teams(normalizer: TeamNormalizer, rows: list[dict], cols: list[str]) -> None:
    for row in rows:
        for col in cols:
            if col in row:
                normalizer.observe(row[col] or "")


def _load_player_rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            return []
        header = [h.strip().lstrip("\ufeff") for h in header]
        # De-duplicate headers like "Dribbling", "Dribbling.1"
        seen: dict[str, int] = {}
        clean_header: list[str] = []
        for h in header:
            if h in seen:
                seen[h] += 1
                clean_header.append(f"{h}.{seen[h]}")
            else:
                seen[h] = 0
                clean_header.append(h)
        out: list[dict] = []
        for raw in reader:
            if not raw:
                continue
            row = dict(zip(clean_header, raw))
            out.append(row)
        return out


def load_data(data_dir: str = DEFAULT_DATA_DIR) -> SoccerData:
    """Load every dataset from ``data_dir`` into a :class:`SoccerData` object."""
    p = lambda *parts: os.path.join(data_dir, *parts)

    bras_path = p("Brasileirao_Matches.csv")
    hist_path = p("novo_campeonato_brasileiro.csv")
    brfd_path = p("BR-Football-Dataset.csv")
    cup_path = p("Brazilian_Cup_Matches.csv")
    lib_path = p("Libertadores_Matches.csv")
    fifa_path = p("fifa_data.csv")

    bras_rows = _read_rows(bras_path)
    hist_rows = _read_rows(hist_path)
    brfd_rows = _read_rows(brfd_path)
    cup_rows = _read_rows(cup_path)
    lib_rows = _read_rows(lib_path)
    fifa_rows = _load_player_rows(fifa_path)

    # ---- Phase 1: observe every team/club name so prominence can resolve.
    normalizer = TeamNormalizer()
    for rows, cols in (
        (bras_rows, ["home_team", "away_team"]),
        (cup_rows, ["home_team", "away_team"]),
        (lib_rows, ["home_team", "away_team"]),
        (brfd_rows, ["home", "away"]),
        (hist_rows, ["Equipe_mandante", "Equipe_visitante"]),
    ):
        _observe_teams(normalizer, rows, cols)
    for row in fifa_rows:
        club = (row.get("Club") or "").strip()
        if club:
            normalizer.observe(club)
    normalizer.finalize()

    data = SoccerData(normalizer=normalizer)

    def mk_match(
        *,
        date,
        season,
        competition,
        round_or_stage,
        home_team,
        away_team,
        home_goals,
        away_goals,
        source,
        source_rank,
        arena=None,
        home_corners=None,
        away_corners=None,
        home_shots=None,
        away_shots=None,
        home_attacks=None,
        away_attacks=None,
        ht_result=None,
        at_result=None,
    ) -> Match:
        home_key = normalizer.canonical(home_team)
        away_key = normalizer.canonical(away_team)
        return Match(
            date=parse_date(date),
            season=_safe_season(season),
            competition=competition,
            round_or_stage=(str(round_or_stage).strip() if round_or_stage not in (None, "") else None),
            home_team=home_key,
            away_team=away_key,
            home_goals=to_int_goal(home_goals),
            away_goals=to_int_goal(away_goals),
            source=source,
            source_rank=source_rank,
            home_display=normalizer.display(home_key),
            away_display=normalizer.display(away_key),
            arena=arena,
            home_corners=_to_int(home_corners),
            away_corners=_to_int(away_corners),
            home_shots=_to_int(home_shots),
            away_shots=_to_int(away_shots),
            home_attacks=_to_int(home_attacks),
            away_attacks=_to_int(away_attacks),
            ht_result=ht_result,
            at_result=at_result,
        )

    add = data.raw_matches.append

    # Brasileirao_Matches.csv  (priority 0 for Serie A)
    sr = SOURCE_RANK[COMP_BRASILEIRAO_A]["brasileirao_matches"]
    for r in bras_rows:
        add(mk_match(
            date=r.get("datetime"), season=r.get("season"),
            competition=COMP_BRASILEIRAO_A, round_or_stage=r.get("round"),
            home_team=r.get("home_team"), away_team=r.get("away_team"),
            home_goals=r.get("home_goal"), away_goals=r.get("away_goal"),
            source="Brasileirao_Matches.csv", source_rank=sr,
        ))

    # historical Brasileirao (priority 2 for Serie A)
    sr = SOURCE_RANK[COMP_BRASILEIRAO_A]["historical"]
    for r in hist_rows:
        add(mk_match(
            date=r.get("Data"), season=r.get("Ano"),
            competition=COMP_BRASILEIRAO_A, round_or_stage=r.get("Rodada"),
            home_team=r.get("Equipe_mandante"), away_team=r.get("Equipe_visitante"),
            home_goals=r.get("Gols_mandante"), away_goals=r.get("Gols_visitante"),
            source="novo_campeonato_brasileiro.csv", source_rank=sr,
            arena=r.get("Arena"),
        ))

    # BR-Football-Dataset.csv  (priority 1 for Serie A/Copa, 0 for Serie B/C)
    for r in brfd_rows:
        tournament = r.get("tournament", "").strip()
        competition = BR_FD_TOURNAMENT_MAP.get(tournament)
        if competition is None:
            continue
        date = r.get("date")
        season = (parse_date(date) or "")[:4] or None
        sr = SOURCE_RANK[competition]["br_football"]
        m = mk_match(
            date=date, season=season, competition=competition,
            round_or_stage=None,
            home_team=r.get("home"), away_team=r.get("away"),
            home_goals=r.get("home_goal"), away_goals=r.get("away_goal"),
            source="BR-Football-Dataset.csv", source_rank=sr,
            home_corners=r.get("home_corner"), away_corners=r.get("away_corner"),
            home_shots=r.get("home_shots"), away_shots=r.get("away_shots"),
            home_attacks=r.get("home_attack"), away_attacks=r.get("away_attack"),
            ht_result=r.get("ht_result"), at_result=r.get("at_result"),
        )
        add(m)
        # BR-Football-Dataset carries detailed stats -> also expose directly.
        data.stats_matches.append(m)

    # Brazilian_Cup_Matches.csv  (priority 0 for Copa do Brasil)
    sr = SOURCE_RANK[COMP_COPA_BRASIL]["brazilian_cup"]
    for r in cup_rows:
        add(mk_match(
            date=r.get("datetime"), season=r.get("season"),
            competition=COMP_COPA_BRASIL, round_or_stage=r.get("round"),
            home_team=r.get("home_team"), away_team=r.get("away_team"),
            home_goals=r.get("home_goal"), away_goals=r.get("away_goal"),
            source="Brazilian_Cup_Matches.csv", source_rank=sr,
        ))

    # Libertadores_Matches.csv  (priority 0 for Libertadores)
    sr = SOURCE_RANK[COMP_LIBERTADORES]["libertadores"]
    for r in lib_rows:
        add(mk_match(
            date=r.get("datetime"), season=r.get("season"),
            competition=COMP_LIBERTADORES, round_or_stage=r.get("stage"),
            home_team=r.get("home_team"), away_team=r.get("away_team"),
            home_goals=r.get("home_goal"), away_goals=r.get("away_goal"),
            source="Libertadores_Matches.csv", source_rank=sr,
        ))

    # ---- Source-priority selection: per (competition, season) keep best rank.
    best_rank: dict[tuple[str, str], int] = {}
    for m in data.raw_matches:
        if m.season is None or m.home_goals is None or m.away_goals is None:
            continue
        key = (m.competition, m.season)
        if key not in best_rank or m.source_rank < best_rank[key]:
            best_rank[key] = m.source_rank
            data.season_sources.setdefault(key, set()).add(m.source)
    for m in data.raw_matches:
        if m.season is None or m.home_goals is None or m.away_goals is None:
            continue
        if m.source_rank == best_rank.get((m.competition, m.season)):
            data.matches.append(m)

    # ---- Players
    _load_players(data, fifa_rows)

    # ---- Team display index
    for m in data.raw_matches:
        data.team_display.setdefault(m.home_team, m.home_display)
        data.team_display.setdefault(m.away_team, m.away_display)

    return data


def _load_players(data: SoccerData, rows: list[dict]) -> None:
    for r in rows:
        club = (r.get("Club") or "").strip() or None
        club_canonical = data.normalizer.canonical(club) if club else None
        player = Player(
            id=r.get("ID"),
            name=(r.get("Name") or "").strip() or None,
            age=_to_int(r.get("Age")),
            nationality=(r.get("Nationality") or "").strip() or None,
            overall=_to_int(r.get("Overall")),
            potential=_to_int(r.get("Potential")),
            club=club,
            club_canonical=club_canonical,
            position=(r.get("Position") or "").strip() or None,
            jersey_number=r.get("Jersey Number"),
            height=(r.get("Height") or "").strip() or None,
            weight=(r.get("Weight") or "").strip() or None,
            preferred_foot=(r.get("Preferred Foot") or "").strip() or None,
            value=(r.get("Value") or "").strip() or None,
            wage=(r.get("Wage") or "").strip() or None,
            crossing=_to_int(r.get("Crossing")),
            finishing=_to_int(r.get("Finishing")),
            dribbling=_to_int(r.get("Dribbling")),
            shortpassing=_to_int(r.get("ShortPassing")),
            longshots=_to_int(r.get("LongShots")),
            defending=_to_int(r.get("Defending")),
            gkdiving=_to_int(r.get("GKDiving")),
            pace=_to_int(r.get("Pace", r.get("Acceleration"))),
            shooting=_to_int(r.get("Shooting")),
            passing=_to_int(r.get("Passing")),
            dribbling2=_to_int(r.get("Dribbling.1")),
            defending2=_to_int(r.get("Defending.1")),
            physical=_to_int(r.get("Physical")),
        )
        data.players.append(player)


@lru_cache(maxsize=1)
def get_data(data_dir: str = DEFAULT_DATA_DIR) -> SoccerData:
    """Return the process-wide cached :class:`SoccerData` singleton."""
    return load_data(data_dir)


def reset_cache() -> None:
    """Clear the cached :class:`SoccerData` (used by tests)."""
    get_data.cache_clear()
