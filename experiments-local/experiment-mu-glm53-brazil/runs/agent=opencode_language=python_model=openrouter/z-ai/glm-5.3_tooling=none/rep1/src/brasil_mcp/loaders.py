"""Loaders turning the six Kaggle CSV files into Match/Player models.

Every loader is tolerant of the data-quality quirks documented in the spec:
multiple date formats, '-' placeholders for unplayed matches, 'NA' values and
UTF-8 accented team names.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from .dates import parse_date, parse_time, to_year
from .models import Match, Player
from .normalize import TeamRegistry, parse_team_name

SERIE_A = "Brasileirão Série A"
SERIE_B = "Brasileirão Série B"
SERIE_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

BR_FOOTBALL_TOURNAMENTS = {
    "Serie A": SERIE_A,
    "Serie B": SERIE_B,
    "Serie C": SERIE_C,
    "Copa do Brasil": COPA_DO_BRASIL,
}

SKILL_COLUMNS = (
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
    "Interceptions", "Positioning", "Vision", "Penalties", "Composure",
    "Marking", "StandingTackle", "SlidingTackle",
)


def _rows(path: Path) -> Iterable[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"na", "n/a", "-", "none"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _team(registry: TeamRegistry, raw: str) -> tuple[str, str]:
    """Resolve a raw team name to (canonical id, display name).

    Unknown names are observed into the registry on first sight so that
    loaders can also be used standalone (without load_all's pre-pass).
    """
    cid = registry.resolve(raw)
    if cid is None:
        registry.observe(raw)
        cid = registry.resolve(raw)
    if cid is None:
        base, uf, country = parse_team_name(raw)
        cid = f"{base}-{(uf or country).lower()}" if (uf or country) else base
    return cid, registry.display(cid)


def load_brasileirao(path: Path, registry: TeamRegistry) -> list[Match]:
    """Load Brasileirao_Matches.csv (Série A, 2012-2022, state-suffixed names)."""
    matches: list[Match] = []
    for row in _rows(path):
        home, home_display = _team(registry, row["home_team"])
        away, away_display = _team(registry, row["away_team"])
        matches.append(
            Match(
                source="brasileirao",
                competition=SERIE_A,
                home=home,
                away=away,
                home_display=home_display,
                away_display=away_display,
                date=parse_date(row["datetime"]),
                time=parse_date(row["datetime"]).strftime("%H:%M") if parse_date(row["datetime"]) else None,
                season=to_year(row["season"]),
                round=str(row["round"]).strip() or None,
                home_goals=_to_int(row["home_goal"]),
                away_goals=_to_int(row["away_goal"]),
                home_state=(row.get("home_team_state") or "").strip() or None,
                away_state=(row.get("away_team_state") or "").strip() or None,
            )
        )
    return matches


def load_copa_do_brasil(path: Path, registry: TeamRegistry) -> list[Match]:
    """Load Brazilian_Cup_Matches.csv (Copa do Brasil, 2012-2021)."""
    matches: list[Match] = []
    for row in _rows(path):
        home, home_display = _team(registry, row["home_team"])
        away, away_display = _team(registry, row["away_team"])
        matches.append(
            Match(
                source="copa_do_brasil",
                competition=COPA_DO_BRASIL,
                home=home,
                away=away,
                home_display=home_display,
                away_display=away_display,
                date=parse_date(row["datetime"]),
                time=parse_date(row["datetime"]).strftime("%H:%M") if parse_date(row["datetime"]) else None,
                season=to_year(row["season"]),
                round=str(row["round"]).strip() or None,
                home_goals=_to_int(row["home_goal"]),
                away_goals=_to_int(row["away_goal"]),
            )
        )
    return matches


def load_libertadores(path: Path, registry: TeamRegistry) -> list[Match]:
    """Load Libertadores_Matches.csv (Copa Libertadores, 2013-2022)."""
    matches: list[Match] = []
    for row in _rows(path):
        home, home_display = _team(registry, row["home_team"])
        away, away_display = _team(registry, row["away_team"])
        matches.append(
            Match(
                source="libertadores",
                competition=LIBERTADORES,
                home=home,
                away=away,
                home_display=home_display,
                away_display=away_display,
                date=parse_date(row["datetime"]),
                time=parse_date(row["datetime"]).strftime("%H:%M") if parse_date(row["datetime"]) else None,
                season=to_year(row["season"]),
                stage=(row.get("stage") or "").strip() or None,
                home_goals=_to_int(row["home_goal"]),
                away_goals=_to_int(row["away_goal"]),
            )
        )
    return matches


def load_br_football(path: Path, registry: TeamRegistry) -> list[Match]:
    """Load BR-Football-Dataset.csv (Séries A/B/C + Copa do Brasil, 2014-2023,
    with corners/shots/attacks and half-time results)."""
    matches: list[Match] = []
    for row in _rows(path):
        competition = BR_FOOTBALL_TOURNAMENTS.get(row["tournament"].strip())
        if competition is None:
            continue
        home, home_display = _team(registry, row["home"])
        away, away_display = _team(registry, row["away"])
        matches.append(
            Match(
                source="br_football",
                competition=competition,
                home=home,
                away=away,
                home_display=home_display,
                away_display=away_display,
                date=parse_date(row["date"]),
                time=parse_time(row.get("time")),
                season=parse_date(row["date"]).year if parse_date(row["date"]) else None,
                home_goals=_to_int(row["home_goal"]),
                away_goals=_to_int(row["away_goal"]),
                home_corners=_to_int(row.get("home_corner")),
                away_corners=_to_int(row.get("away_corner")),
                total_corners=_to_int(row.get("total_corners")),
                home_shots=_to_int(row.get("home_shots")),
                away_shots=_to_int(row.get("away_shots")),
                home_attacks=_to_int(row.get("home_attack")),
                away_attacks=_to_int(row.get("away_attack")),
                ht_result=(row.get("ht_result") or "").strip() or None,
                at_result=(row.get("at_result") or "").strip() or None,
            )
        )
    return matches


def load_historico(path: Path, registry: TeamRegistry) -> list[Match]:
    """Load novo_campeonato_brasileiro.csv (Série A, 2003-2019, PT-BR columns)."""
    matches: list[Match] = []
    for row in _rows(path):
        home, home_display = _team(registry, row["Equipe_mandante"])
        away, away_display = _team(registry, row["Equipe_visitante"])
        matches.append(
            Match(
                source="brasileirao_historico",
                competition=SERIE_A,
                home=home,
                away=away,
                home_display=home_display,
                away_display=away_display,
                date=parse_date(row["Data"]),
                season=to_year(row["Ano"]),
                round=str(row["Rodada"]).strip() or None,
                home_goals=_to_int(row["Gols_mandante"]),
                away_goals=_to_int(row["Gols_visitante"]),
                venue=(row.get("Arena") or "").strip() or None,
                home_state=(row.get("Mandante_UF") or "").strip() or None,
                away_state=(row.get("Visitante_UF") or "").strip() or None,
            )
        )
    return matches


def load_fifa(path: Path, registry: TeamRegistry) -> list[Player]:
    """Load fifa_data.csv (18,207 players with attributes)."""
    players: list[Player] = []
    for row in _rows(path):
        skills: dict[str, int | None] = {}
        for column in SKILL_COLUMNS:
            skills[column] = _to_int(row.get(column))
        players.append(
            Player(
                id=_to_int(row.get("ID")) or 0,
                name=(row.get("Name") or "").strip(),
                age=_to_int(row.get("Age")),
                nationality=(row.get("Nationality") or "").strip(),
                overall=_to_int(row.get("Overall")),
                potential=_to_int(row.get("Potential")),
                club=(row.get("Club") or "").strip(),
                position=(row.get("Position") or "").strip(),
                jersey=_to_int(row.get("Jersey Number")),
                height=(row.get("Height") or "").strip() or None,
                weight=(row.get("Weight") or "").strip() or None,
                preferred_foot=(row.get("Preferred Foot") or "").strip() or None,
                value=(row.get("Value") or "").strip() or None,
                wage=(row.get("Wage") or "").strip() or None,
                skills=skills,
            )
        )
    return players


def load_all(data_dir: Path | str) -> tuple[list[Match], list[Player], TeamRegistry]:
    """Load every dataset, building a shared team registry as we go.

    The registry is fed twice: once with match team names, then finalized so
    bare-name resolution (e.g. "Grêmio" -> gremio-rs) is available.
    """
    data_dir = Path(data_dir)
    registry = TeamRegistry()
    raw_names: list[str] = []
    for filename, columns in (
        ("Brasileirao_Matches.csv", ("home_team", "away_team")),
        ("Brazilian_Cup_Matches.csv", ("home_team", "away_team")),
        ("Libertadores_Matches.csv", ("home_team", "away_team")),
        ("BR-Football-Dataset.csv", ("home", "away")),
        ("novo_campeonato_brasileiro.csv", ("Equipe_mandante", "Equipe_visitante")),
    ):
        for row in _rows(data_dir / filename):
            for column in columns:
                raw_names.append(row[column].strip())
    for name in raw_names:
        registry.observe(name)
    registry.finalize()

    matches: list[Match] = []
    matches.extend(load_brasileirao(data_dir / "Brasileirao_Matches.csv", registry))
    matches.extend(load_copa_do_brasil(data_dir / "Brazilian_Cup_Matches.csv", registry))
    matches.extend(load_libertadores(data_dir / "Libertadores_Matches.csv", registry))
    matches.extend(load_br_football(data_dir / "BR-Football-Dataset.csv", registry))
    matches.extend(load_historico(data_dir / "novo_campeonato_brasileiro.csv", registry))

    players = load_fifa(data_dir / "fifa_data.csv", registry)
    for player in players:
        if player.club:
            registry.observe(player.club)
    registry.finalize()

    return matches, players, registry
