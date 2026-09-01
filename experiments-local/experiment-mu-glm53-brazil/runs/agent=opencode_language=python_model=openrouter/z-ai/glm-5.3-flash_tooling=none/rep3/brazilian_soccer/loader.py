"""CSV loading and normalization into Match/Player objects.

Loads the six Kaggle datasets from ``data/kaggle/`` (path overridable with
the ``SOCCER_DATA_DIR`` environment variable):

==============================  =========================================
File                            Competition
==============================  =========================================
Brasileirao_Matches.csv         Brasileirão Serie A (2012-2022)
Brazilian_Cup_Matches.csv       Copa do Brasil (2012-2021)
Libertadores_Matches.csv        Copa Libertadores
BR-Football-Dataset.csv         Serie A/B/C + Copa do Brasil (2014-2023,
                                with corners/attacks/shots statistics)
novo_campeonato_brasileiro.csv  Brasileirão Serie A (2003-2019, PT-BR cols)
fifa_data.csv                   FIFA player database (18k players)
==============================  =========================================

Overlapping datasets describe the same real matches (e.g. Série A
2014-2019 appears in three files).  ``dedupe_matches`` keeps one row per
real match using a source priority so aggregate statistics never
double-count:

- Série A/B/C: key = (competition, season, home, away) — a double
  round-robin league meets every ordered pair once per season.
- Copa do Brasil: key = (competition, date, home, away).
- Libertadores: single source, no dedupe.

Copa do Brasil ``stage`` ("final" etc.) is derived from the round column;
Libertadores stages come straight from the data.  Dates accept ISO,
ISO+time and Brazilian DD/MM/YYYY formats (see ``normalize.parse_date``).
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from .models import (
    BR_FOOTBALL_TOURNAMENTS,
    COPA_DO_BRASIL,
    Player,
    Match,
)
from .normalize import TeamRegistry, parse_date, parse_float, parse_int, parse_time

DATA_DIR = Path(os.environ.get("SOCCER_DATA_DIR", "data/kaggle"))

# Lower number wins when two sources describe the same match.
SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 1,
    "novo_campeonato_brasileiro.csv": 2,
    "BR-Football-Dataset.csv": 3,
    "Brazilian_Cup_Matches.csv": 1,
    "Libertadores_Matches.csv": 1,
}

SKILL_COLUMNS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
    "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle",
]


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _team(registry: TeamRegistry, raw: str) -> str:
    """Register a raw team name for identity resolution; keep the raw form."""
    registry.register(raw)
    return raw


def load_match_rows(registry: TeamRegistry) -> list[Match]:
    """Load all match datasets into normalized Match objects.

    Team identity: ``home_raw``/``away_raw`` store the raw names; canonical
    keys are assigned in ``load_all`` after the registry is finalized.
    """
    rows: list[Match] = []

    # 1. Brasileirão Serie A (2012-2022) - team names carry state suffixes.
    for r in read_csv(DATA_DIR / "Brasileirao_Matches.csv"):
        rows.append(Match(
            competition="Brasileirão Serie A",
            season=parse_int(r["season"]) or 0,
            date=parse_date(r["datetime"]),
            time=parse_time(r["datetime"]),
            round=parse_int(r["round"]),
            home_raw=_team(registry, r["home_team"]),
            away_raw=_team(registry, r["away_team"]),
            home_state=r.get("home_team_state") or None,
            away_state=r.get("away_team_state") or None,
            home_goal=parse_int(r["home_goal"]),
            away_goal=parse_int(r["away_goal"]),
            source="Brasileirao_Matches.csv",
        ))

    # 2. Copa do Brasil (2012-2021).
    for r in read_csv(DATA_DIR / "Brazilian_Cup_Matches.csv"):
        rows.append(Match(
            competition="Copa do Brasil",
            season=parse_int(r["season"]) or 0,
            date=parse_date(r["datetime"]),
            time=parse_time(r["datetime"]),
            round=parse_int(r["round"]),
            home_raw=_team(registry, r["home_team"]),
            away_raw=_team(registry, r["away_team"]),
            home_goal=parse_int(r["home_goal"]),
            away_goal=parse_int(r["away_goal"]),
            source="Brazilian_Cup_Matches.csv",
        ))

    # 3. Copa Libertadores (goals stored as strings; stages provided).
    for r in read_csv(DATA_DIR / "Libertadores_Matches.csv"):
        d = parse_date(r["datetime"])
        rows.append(Match(
            competition="Copa Libertadores",
            season=parse_int(r["season"]) or (d.year if d else 0),
            date=d,
            time=parse_time(r["datetime"]),
            stage=(r.get("stage") or "").strip() or None,
            home_raw=_team(registry, r["home_team"]),
            away_raw=_team(registry, r["away_team"]),
            home_goal=parse_int(r["home_goal"]),
            away_goal=parse_int(r["away_goal"]),
            source="Libertadores_Matches.csv",
        ))

    # 4. Extended statistics dataset (Serie A/B/C + Copa do Brasil,
    #    2014-2023).  Tournament values map to canonical competitions.
    #    Season: league matches in Jan/Feb belong to the previous season's
    #    edition (the COVID 2020 season ended in Feb 2021); cup matches
    #    inherit their season from the explicit-season cup dataset later
    #    (see load_all).
    for r in read_csv(DATA_DIR / "BR-Football-Dataset.csv"):
        comp = BR_FOOTBALL_TOURNAMENTS.get(
            (r.get("tournament") or "").strip().lower())
        if comp is None:
            continue
        d = parse_date(r.get("date"))
        season = d.year if d is None or d.month >= 3 else d.year - 1
        rows.append(Match(
            competition=comp,
            season=season,
            date=d,
            time=parse_time(r.get("time")),
            home_raw=_team(registry, r["home"]),
            away_raw=_team(registry, r["away"]),
            home_goal=parse_int(r["home_goal"]),
            away_goal=parse_int(r["away_goal"]),
            source="BR-Football-Dataset.csv",
            home_corner=parse_int(r.get("home_corner")),
            away_corner=parse_int(r.get("away_corner")),
            home_attack=parse_int(r.get("home_attack")),
            away_attack=parse_int(r.get("away_attack")),
            home_shots=parse_int(r.get("home_shots")),
            away_shots=parse_int(r.get("away_shots")),
            total_corners=parse_int(r.get("total_corners")),
        ))

    # 5. Historical Brasileirão 2003-2019 (Portuguese column names).
    for r in read_csv(DATA_DIR / "novo_campeonato_brasileiro.csv"):
        rows.append(Match(
            competition="Brasileirão Serie A",
            season=parse_int(r["Ano"]) or 0,
            date=parse_date(r["Data"]),
            round=parse_int(r["Rodada"]),
            arena=(r.get("Arena") or "").strip() or None,
            home_raw=_team(registry, r["Equipe_mandante"]),
            away_raw=_team(registry, r["Equipe_visitante"]),
            home_goal=parse_int(r["Gols_mandante"]),
            away_goal=parse_int(r["Gols_visitante"]),
            source="novo_campeonato_brasileiro.csv",
        ))

    return rows


def fix_cup_seasons(registry: TeamRegistry, matches: list[Match]) -> None:
    """Give BR-Football cup rows the season of their Brazilian_Cup_Matches
    twin, matched by (date, home, away).  The extended-stats file has no
    season column, and cup editions can spill into the next calendar year
    (e.g. the 2020 final played in March 2021)."""
    explicit = {}
    for m in matches:
        if m.source == "Brazilian_Cup_Matches.csv" and m.date is not None:
            explicit[(m.date, m.home_key, m.away_key)] = m.season
    for m in matches:
        if m.source == "BR-Football-Dataset.csv" and \
                m.competition == COPA_DO_BRASIL and m.date is not None:
            season = explicit.get((m.date, m.home_key, m.away_key))
            if season:
                m.season = season


def derive_cup_stages(matches: list[Match]) -> None:
    """Derive cup stages ("final", "semifinals", ...) from the per-season
    maximum round of the explicit cup dataset.

    The heuristic is guarded: a round only counts as the final when it has
    exactly two legs.  Some seasons are truncated in the source (2021 ends
    at round 4); there the final is detected instead as the two latest
    fixtures of the season that share the same pair of teams (a two-legged
    tie) - typically coming from the extended-stats file.
    """
    by_season: dict[int, list[Match]] = {}
    for m in matches:
        if m.competition == COPA_DO_BRASIL:
            by_season.setdefault(m.season, []).append(m)

    for season, ms in by_season.items():
        rounds = [m.round for m in ms if m.round is not None]
        if not rounds:
            continue
        top = max(rounds)
        top_legs = [m for m in ms if m.round == top]
        for m in ms:
            if m.round is None:
                continue
            if m.round == top and len(top_legs) == 2:
                m.stage = "final"
            elif m.round == top - 1 and \
                    len([x for x in ms if x.round == top - 1]) == 4:
                m.stage = "semifinals"
            elif m.round == top - 2 and \
                    len([x for x in ms if x.round == top - 2]) == 8:
                m.stage = "quarterfinals"
            else:
                m.stage = f"round {m.round}"
        if len(top_legs) != 2:
            _label_final_from_tail(ms)


def _label_final_from_tail(season_matches: list[Match]) -> None:
    """Label the two-legged final of a truncated season.

    Looks for the latest fixtures that repeat the same team pairing with
    swapped home/away - the classic two-legged cup final.
    """
    dated = sorted((m for m in season_matches if m.date is not None and
                    m.home_goal is not None),
                   key=lambda m: m.date)
    for m in dated:
        m.stage = f"round {m.round}" if m.round is not None else None
    for i in range(len(dated) - 1, 0, -1):
        later, earlier = dated[i], dated[i - 1]
        if {later.home_key, later.away_key} == {earlier.home_key, earlier.away_key}:
            later.stage = "final"
            earlier.stage = "final"
            break


def dedupe_matches(matches: list[Match]) -> list[Match]:
    """Keep one row per real match, preferring richer sources.

    A row with an actual score always wins over a resultless row of a
    higher-priority source (the Brasileirão CSV contains postponed games
    with empty scores that other datasets resolve).
    """
    def rank(m: Match) -> tuple[int, int]:
        return (0 if m.has_result() else 1, SOURCE_PRIORITY.get(m.source, 9))

    best: dict[tuple, Match] = {}
    for m in matches:
        if m.competition.startswith("Brasileirão Serie"):
            key = ("league", m.competition, m.season, m.home_key, m.away_key)
        elif m.competition == COPA_DO_BRASIL:
            key = ("cup", m.season, m.date, m.home_key, m.away_key)
        else:
            key = ("libertadores", id(m))      # single source: no dedupe
        cur = best.get(key)
        if cur is None or rank(m) < rank(cur):
            best[key] = m
    return list(best.values())


def _parse_height(raw: str) -> int | None:
    """FIFA height "5'7" -> centimeters."""
    m = str(raw or "").strip().replace('"', "")
    parts = m.split("'")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return round(int(parts[0]) * 30.48 + int(parts[1]) * 2.54)
    return parse_int(raw)


def _parse_weight(raw: str) -> int | None:
    """FIFA weight "159lbs" -> kilograms."""
    s = str(raw or "").strip().lower().replace("lbs", "")
    kg = parse_float(s)
    return round(kg * 0.45359237) if kg else None


def load_players(registry: TeamRegistry) -> list[Player]:
    """Load the FIFA player database and register club names."""
    players: list[Player] = []
    for r in read_csv(DATA_DIR / "fifa_data.csv"):
        club = (r.get("Club") or "").strip()
        if club:
            registry.register(club)
        players.append(Player(
            id=parse_int(r.get("ID")) or 0,
            name=(r.get("Name") or "").strip(),
            nationality=(r.get("Nationality") or "").strip(),
            overall=parse_int(r.get("Overall")) or 0,
            potential=parse_int(r.get("Potential")) or 0,
            club_key="",
            club_raw=club,
            club_display=club,
            position=(r.get("Position") or "").strip() or None,
            age=parse_int(r.get("Age")),
            jersey=parse_int(r.get("Jersey Number")),
            height_cm=_parse_height(r.get("Height")),
            weight_kg=_parse_weight(r.get("Weight")),
            value=(r.get("Value") or "").strip() or None,
            wage=(r.get("Wage") or "").strip() or None,
            preferred_foot=(r.get("Preferred Foot") or "").strip() or None,
            skills={c: v for c in SKILL_COLUMNS
                    if (v := parse_int(r.get(c))) is not None},
        ))
    return players


def load_all() -> tuple[TeamRegistry, list[Match], list[Player]]:
    """Full pipeline: register team names, resolve identity, build objects."""
    registry = TeamRegistry()
    # Pass 1: load match rows and register all team names so base-name
    # ambiguity is judged on real match data only.
    match_rows = load_match_rows(registry)
    # Pass 2: register FIFA club names (mostly full club names).
    players = load_players(registry)
    # Resolve canonical identity and display names.
    registry.finalize()
    # Then assign final canonical keys everywhere...
    for m in match_rows:
        m.home_key = registry.key_for(m.home_raw)
        m.away_key = registry.key_for(m.away_raw)
    # ...fix cup seasons against the explicit-season dataset...
    fix_cup_seasons(registry, match_rows)
    # ...so cross-source duplicates can be recognized and dropped.
    matches = dedupe_matches(match_rows)
    derive_cup_stages(matches)
    for p in players:
        if p.club_raw:
            p.club_key = registry.key_for(p.club_raw)
            p.club_display = registry.display(p.club_key)
    return registry, matches, players
