"""
Data ingestion for the Brazilian Soccer MCP Server.

Loads the six bundled CSV files, normalises team names, dates, goal counts and
competition labels, then deduplicates matches that appear in more than one
source. The result is a single list of matches plus a player roster that the
query engine consumes.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .normalize import (
    canonical_team_name,
    competition_canonical,
    display_team_name,
    parse_date,
    parse_score,
    parse_season,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "kaggle"


def _path(filename: str) -> Path:
    return DATA_DIR / filename


def _read_csv(filename: str) -> list[dict[str, str]]:
    with _path(filename).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _make_match(
    *,
    source: str,
    competition: str,
    season: int | None,
    round_: str | None,
    stage: str | None,
    date: Any,
    datetime_str: str,
    home_original: str,
    away_original: str,
    home_goal: int | None,
    away_goal: int | None,
    extended: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a uniform match record."""
    home_canonical, home_state, home_base = canonical_team_name(home_original)
    away_canonical, away_state, away_base = canonical_team_name(away_original)
    return {
        "source": source,
        "competition": competition,
        "season": season,
        "round": round_,
        "stage": stage,
        "date": parse_date(date),
        "datetime": datetime_str,
        "home_original": home_original.strip(),
        "away_original": away_original.strip(),
        "home_display": display_team_name(home_original),
        "away_display": display_team_name(away_original),
        "home_canonical": home_canonical,
        "away_canonical": away_canonical,
        "home_state": home_state,
        "away_state": away_state,
        "home_goal": home_goal,
        "away_goal": away_goal,
        "extended": extended or {},
    }


def _dedupe_key(match: dict[str, Any]) -> tuple:
    """
    Composite key identifying the same match across multiple sources.

    For league competitions each team meets the same opponent home and away
    only once per season, so the date is ignored to absorb small date
    differences between sources. Knockout competitions keep the round/stage
    and date in the key to avoid merging distinct legs.
    """
    comp = match["competition"]
    is_league = comp.startswith("Brasileirão")
    if is_league:
        return (
            comp,
            match["season"],
            match["home_canonical"],
            match["away_canonical"],
        )
    return (
        comp,
        match["season"],
        match.get("round") or match.get("stage") or "",
        match["home_canonical"],
        match["away_canonical"],
        match["date"],
    )


def load_brasileirao_matches() -> list[dict[str, Any]]:
    """Load ``Brasileirao_Matches.csv``."""
    rows = _read_csv("Brasileirao_Matches.csv")
    records: list[dict[str, Any]] = []
    for row in rows:
        home_goal = parse_score(row.get("home_goal"))
        away_goal = parse_score(row.get("away_goal"))
        records.append(
            _make_match(
                source="Brasileirao_Matches.csv",
                competition="Brasileirão",
                season=parse_season(row.get("season")),
                round_=row.get("round") or None,
                stage=None,
                date=row.get("datetime"),
                datetime_str=row.get("datetime", ""),
                home_original=row.get("home_team", ""),
                away_original=row.get("away_team", ""),
                home_goal=home_goal,
                away_goal=away_goal,
                extended={"home_team_state": row.get("home_team_state"), "away_team_state": row.get("away_team_state")},
            )
        )
    return records


def load_brazilian_cup_matches() -> list[dict[str, Any]]:
    """Load ``Brazilian_Cup_Matches.csv``."""
    rows = _read_csv("Brazilian_Cup_Matches.csv")
    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(
            _make_match(
                source="Brazilian_Cup_Matches.csv",
                competition="Copa do Brasil",
                season=parse_season(row.get("season")),
                round_=row.get("round") or None,
                stage=None,
                date=row.get("datetime"),
                datetime_str=row.get("datetime", ""),
                home_original=row.get("home_team", ""),
                away_original=row.get("away_team", ""),
                home_goal=parse_score(row.get("home_goal")),
                away_goal=parse_score(row.get("away_goal")),
            )
        )
    return records


def load_libertadores_matches() -> list[dict[str, Any]]:
    """Load ``Libertadores_Matches.csv``."""
    rows = _read_csv("Libertadores_Matches.csv")
    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(
            _make_match(
                source="Libertadores_Matches.csv",
                competition="Copa Libertadores",
                season=parse_season(row.get("season")),
                round_=None,
                stage=row.get("stage") or None,
                date=row.get("datetime"),
                datetime_str=row.get("datetime", ""),
                home_original=row.get("home_team", ""),
                away_original=row.get("away_team", ""),
                home_goal=parse_score(row.get("home_goal")),
                away_goal=parse_score(row.get("away_goal")),
            )
        )
    return records


def load_br_football_matches() -> list[dict[str, Any]]:
    """Load ``BR-Football-Dataset.csv``."""
    rows = _read_csv("BR-Football-Dataset.csv")
    records: list[dict[str, Any]] = []
    for row in rows:
        raw_competition = row.get("tournament", "")
        competition = competition_canonical(raw_competition)
        extended = {
            "home_corner": parse_score(row.get("home_corner")),
            "away_corner": parse_score(row.get("away_corner")),
            "home_attack": parse_score(row.get("home_attack")),
            "away_attack": parse_score(row.get("away_attack")),
            "home_shots": parse_score(row.get("home_shots")),
            "away_shots": parse_score(row.get("away_shots")),
            "ht_result": row.get("ht_result"),
            "at_result": row.get("at_result"),
            "total_corners": parse_score(row.get("total_corners")),
            "time": row.get("time"),
        }
        date_value = row.get("date")
        # The date string in this file is already ISO.
        season = parse_season(date_value[:4]) if date_value else None
        records.append(
            _make_match(
                source="BR-Football-Dataset.csv",
                competition=competition,
                season=season,
                round_=None,
                stage=None,
                date=date_value,
                datetime_str=f"{row.get('date', '')} {row.get('time', '')}".strip(),
                home_original=row.get("home", ""),
                away_original=row.get("away", ""),
                home_goal=parse_score(row.get("home_goal")),
                away_goal=parse_score(row.get("away_goal")),
                extended=extended,
            )
        )
    return records


def load_novo_campeonato_brasileiro() -> list[dict[str, Any]]:
    """Load ``novo_campeonato_brasileiro.csv`` (historical 2003-2019)."""
    rows = _read_csv("novo_campeonato_brasileiro.csv")
    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(
            _make_match(
                source="novo_campeonato_brasileiro.csv",
                competition="Brasileirão",
                season=parse_season(row.get("Ano")),
                round_=row.get("Rodada") or None,
                stage=None,
                date=row.get("Data"),
                datetime_str=row.get("Data", ""),
                home_original=row.get("Equipe_mandante", ""),
                away_original=row.get("Equipe_visitante", ""),
                home_goal=parse_score(row.get("Gols_mandante")),
                away_goal=parse_score(row.get("Gols_visitante")),
                extended={
                    "home_state": row.get("Mandante_UF"),
                    "away_state": row.get("Visitante_UF"),
                    "winner": row.get("Vencedor"),
                    "arena": row.get("Arena"),
                },
            )
        )
    return records


def load_players() -> list[dict[str, Any]]:
    """Load ``fifa_data.csv`` and attach normalised search fields."""
    rows = _read_csv("fifa_data.csv")
    players: list[dict[str, Any]] = []
    for row in rows:
        overall = parse_score(row.get("Overall"))
        player = dict(row)
        player["Name"] = player.get("Name", "").strip()
        player["Nationality"] = player.get("Nationality", "").strip()
        player["Club"] = player.get("Club", "").strip()
        player["Position"] = (player.get("Position") or "").strip().upper()
        player["Overall_int"] = overall if overall is not None else 0
        player["Name_norm"] = display_team_name(player["Name"])
        player["Nationality_norm"] = display_team_name(player["Nationality"])
        player["Club_norm"] = display_team_name(player["Club"])
        players.append(player)
    return players


def load_all() -> dict[str, Any]:
    """
    Load and de-duplicate every CSV.

    Returns a dict with ``matches`` and ``players`` plus a ``team_index`` of
    all canonical team keys seen in the match data.
    """
    all_matches: list[dict[str, Any]] = []
    all_matches.extend(load_brasileirao_matches())
    all_matches.extend(load_brazilian_cup_matches())
    all_matches.extend(load_libertadores_matches())
    all_matches.extend(load_br_football_matches())
    all_matches.extend(load_novo_campeonato_brasileiro())

    # Deduplicate on a stable key, keeping richer extended stats when merging.
    seen: dict[tuple, dict[str, Any]] = {}
    for match in all_matches:
        key = _dedupe_key(match)
        existing = seen.get(key)
        if existing is None:
            seen[key] = match
        else:
            existing["source"] = f"{existing['source']};{match['source']}"
            for ext_key, ext_value in match.get("extended", {}).items():
                if ext_value and not existing["extended"].get(ext_key):
                    existing["extended"][ext_key] = ext_value

    matches = list(seen.values())

    team_index: set[str] = set()
    display_names: dict[str, str] = {}
    for match in matches:
        team_index.add(match["home_canonical"])
        team_index.add(match["away_canonical"])
        display_names.setdefault(match["home_canonical"], match["home_display"])
        display_names.setdefault(match["away_canonical"], match["away_display"])

    return {
        "matches": matches,
        "players": load_players(),
        "team_index": team_index,
        "display_names": display_names,
    }
