"""Load every provided CSV dataset into a unified, queryable knowledge base."""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from .models import Match, Player, SKILL_COLUMNS
from .normalize import TeamRegistry

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"

# Canonical competition names.
BRASILEIRAO_A = "Brasileirão Série A"
BRASILEIRAO_B = "Brasileirão Série B"
BRASILEIRAO_C = "Brasileirão Série C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

#: User-facing competition aliases -> canonical competition name.
COMPETITION_ALIASES = {
    "brasileirao serie a": BRASILEIRAO_A,
    "brasileirao série a": BRASILEIRAO_A,
    "brasileirao": BRASILEIRAO_A,
    "serie a": BRASILEIRAO_A,
    "série a": BRASILEIRAO_A,
    "serie a (brasil)": BRASILEIRAO_A,
    "brasileirao serie b": BRASILEIRAO_B,
    "brasileirão série b": BRASILEIRAO_B,
    "serie b": BRASILEIRAO_B,
    "série b": BRASILEIRAO_B,
    "serie b (brasil)": BRASILEIRAO_B,
    "brasileirao serie c": BRASILEIRAO_C,
    "brasileirão série c": BRASILEIRAO_C,
    "serie c": BRASILEIRAO_C,
    "série c": BRASILEIRAO_C,
    "serie c (brasil)": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "copa do brasil (brasil)": COPA_DO_BRASIL,
    "copa libertadores": LIBERTADORES,
    "libertadores": LIBERTADORES,
    "copa libertadores da america": LIBERTADORES,
    "conmebol libertadores": LIBERTADORES,
}

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y")


def parse_date(text: str | None) -> date | None:
    """Parse the multiple date formats used across the datasets."""
    if not text or not text.strip():
        return None
    text = text.strip()
    if text.lower() in {"na", "n/a", "none", "null", "-"}:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_int(value) -> int | None:
    """Parse goals/counts that may arrive as int, '2', '2.0' or garbage."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(round(float(value)))
    text = str(value).strip()
    if not text or text.lower() in {"na", "n/a", "none", "null", "-"}:
        return None
    try:
        return int(round(float(text)))
    except ValueError:
        head = text.split("+", 1)[0]
        try:
            return int(round(float(head)))
        except ValueError:
            return None


def parse_year(value) -> int | None:
    n = parse_int(value)
    return n if n and 1900 < n < 2200 else None


#: Lower number wins when several files describe the same
#: (competition, season): the dedicated per-competition files are more
#: authoritative than the aggregate BR-Football dataset.
SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 0,
    "novo_campeonato_brasileiro.csv": 1,
    "Brazilian_Cup_Matches.csv": 0,
    "Libertadores_Matches.csv": 0,
    "BR-Football-Dataset.csv": 2,
}

#: League competitions with a strict home-and-away round robin, where a
#: given (season, home, away) pairing occurs exactly once.  Série C is
#: excluded because its group + playoff formats can legitimately repeat
#: a pairing.
ROUND_ROBIN_COMPETITIONS = frozenset({BRASILEIRAO_A, BRASILEIRAO_B})


class SoccerData:
    """In-memory knowledge base over all six datasets."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.teams = TeamRegistry()
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self._by_competition: dict[str, list[Match]] = {}
        self._seasons: dict[str, set[int]] = defaultdict(set)
        self._club_of_player: dict[int, str] = {}  # player id -> canonical club key

        self._load()

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #

    def _read(self, filename: str) -> list[dict]:
        path = self.data_dir / filename
        with open(path, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))

    def _load(self) -> None:
        match_files = (
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "novo_campeonato_brasileiro.csv",
            "BR-Football-Dataset.csv",
        )

        # Pass 1: register every team name so the registry can merge bare
        # spellings into state-suffixed canonical ids before matches are built.
        for filename in match_files:
            for row in self._read(filename):
                self._note_teams(filename, row)

        self.teams.merge_bare_keys()

        # Pass 2: build every candidate Match once, dropping impossible
        # self-play rows (source-data artefacts like "Bragantino vs Bragantino").
        candidates: list[Match] = [
            m
            for filename in match_files
            for row in self._read(filename)
            for m in self._row_to_matches(filename, row)
            if m.home != m.away
        ]

        # Pass 3: for each (competition, season) keep only rows from the most
        # authoritative source that covers it.  Overlapping files disagree on
        # dates/scores for the same fixture, so mixing them would corrupt
        # standings; the aggregate file still contributes Série B/C, extended
        # match statistics, and seasons the dedicated files do not cover.
        best_source: dict[tuple[str, int | None], str] = {}
        for match in candidates:
            key = (match.competition, match.season)
            current = best_source.get(key)
            if current is None or SOURCE_PRIORITY[match.source] < SOURCE_PRIORITY[current]:
                best_source[key] = match.source
        filtered = [
            m
            for m in candidates
            if m.source == best_source[(m.competition, m.season)]
        ]

        # Pass 4: dedup.  Three levels:
        #   1. exact natural key (date + teams + score + competition);
        #   2. same fixture (season + competition + teams + score) within one
        #      calendar day -- some sources carry a one-day-shifted date for
        #      the very same match (timezone artefacts);
        #   3. for round-robin leagues, one row per (season, home, away)
        #      pairing, which also drops residual within-source duplicates.
        seen: set[tuple] = set()
        fuzzy_index: dict[tuple, list[Match]] = defaultdict(list)
        pairings: set[tuple] = set()
        for match in sorted(filtered, key=lambda m: (m.date is None, m.date or date.min)):
            key = self._dedup_key(match)
            if key in seen:
                continue
            seen.add(key)
            fuzzy_key = (
                match.competition,
                match.season,
                match.home,
                match.away,
                match.home_goals,
                match.away_goals,
            )
            if any(
                match.date is not None
                and other.date is not None
                and abs((match.date - other.date).days) <= 1
                for other in fuzzy_index[fuzzy_key]
            ):
                continue
            fuzzy_index[fuzzy_key].append(match)
            if match.competition in ROUND_ROBIN_COMPETITIONS and match.season:
                pairing = (match.competition, match.season, match.home, match.away)
                if pairing in pairings:
                    continue
                pairings.add(pairing)
            self._add_match(match)

        self._load_players()

    def _note_teams(self, filename: str, row: dict) -> None:
        if filename == "Brasileirao_Matches.csv":
            self.teams.note(row["home_team"], row.get("home_team_state"))
            self.teams.note(row["away_team"], row.get("away_team_state"))
        elif filename == "novo_campeonato_brasileiro.csv":
            # The state columns in this file are unreliable (e.g. "Vitória"
            # tagged ES instead of BA, "BH" instead of "BA"), so the bare
            # club names are registered on their own; the registry's
            # prominence-based folding assigns them to the right club.
            self.teams.note(row["Equipe_mandante"])
            self.teams.note(row["Equipe_visitante"])
        elif filename == "BR-Football-Dataset.csv":
            self.teams.note(row["home"])
            self.teams.note(row["away"])
        else:  # Brazilian_Cup_Matches.csv, Libertadores_Matches.csv
            self.teams.note(row["home_team"])
            self.teams.note(row["away_team"])

    def _row_to_matches(self, filename: str, row: dict) -> list[Match]:
        """Convert one CSV row into a :class:`Match` (or none on garbage rows)."""
        if filename == "Brasileirao_Matches.csv":
            return [
                Match(
                    date=parse_date(row["datetime"]),
                    season=parse_year(row["season"]),
                    competition=BRASILEIRAO_A,
                    stage=f"Round {row['round']}" if row.get("round") else None,
                    home=self.teams.canonical(row["home_team"], row.get("home_team_state")),
                    away=self.teams.canonical(row["away_team"], row.get("away_team_state")),
                    home_goals=parse_int(row["home_goal"]),
                    away_goals=parse_int(row["away_goal"]),
                    venue=None,
                    source=filename,
                )
            ]
        if filename == "Brazilian_Cup_Matches.csv":
            return [
                Match(
                    date=parse_date(row["datetime"]),
                    season=parse_year(row["season"]),
                    competition=COPA_DO_BRASIL,
                    stage=f"Round {row['round']}" if row.get("round") else None,
                    home=self.teams.canonical(row["home_team"]),
                    away=self.teams.canonical(row["away_team"]),
                    home_goals=parse_int(row["home_goal"]),
                    away_goals=parse_int(row["away_goal"]),
                    venue=None,
                    source=filename,
                )
            ]
        if filename == "Libertadores_Matches.csv":
            return [
                Match(
                    date=parse_date(row["datetime"]),
                    season=parse_year(row["season"]),
                    competition=LIBERTADORES,
                    stage=row.get("stage") or None,
                    home=self.teams.canonical(row["home_team"]),
                    away=self.teams.canonical(row["away_team"]),
                    home_goals=parse_int(row["home_goal"]),
                    away_goals=parse_int(row["away_goal"]),
                    venue=None,
                    source=filename,
                )
            ]
        if filename == "novo_campeonato_brasileiro.csv":
            return [
                Match(
                    date=parse_date(row["Data"]),
                    season=parse_year(row["Ano"]),
                    competition=BRASILEIRAO_A,
                    stage=f"Round {row['Rodada']}" if row.get("Rodada") else None,
                    home=self.teams.canonical(row["Equipe_mandante"]),
                    away=self.teams.canonical(row["Equipe_visitante"]),
                    home_goals=parse_int(row["Gols_mandante"]),
                    away_goals=parse_int(row["Gols_visitante"]),
                    venue=row.get("Arena") or None,
                    source=filename,
                )
            ]
        # BR-Football-Dataset.csv: tournament column drives the competition.
        tournament = (row.get("tournament") or "").strip().lower()
        competition = COMPETITION_ALIASES.get(tournament, tournament.title())
        match_date = parse_date(row.get("date"))
        season = parse_year(row.get("date", "")[:4]) if row.get("date") else None
        # Brazilian national leagues never kick off before March; a league
        # fixture dated January or February belongs to the season that
        # started the previous year (e.g. the COVID-extended 2020 Série A
        # finished in February 2021).
        if (
            match_date
            and season
            and match_date.month in (1, 2)
            and competition in ROUND_ROBIN_COMPETITIONS
        ):
            season -= 1
        return [
            Match(
                date=match_date,
                season=season,
                competition=competition,
                stage=None,
                home=self.teams.canonical(row["home"]),
                away=self.teams.canonical(row["away"]),
                home_goals=parse_int(row.get("home_goal")),
                away_goals=parse_int(row.get("away_goal")),
                venue=None,
                source=filename,
                home_corners=parse_int(row.get("home_corner")),
                away_corners=parse_int(row.get("away_corner")),
                home_shots=parse_int(row.get("home_shots")),
                away_shots=parse_int(row.get("away_shots")),
                home_attacks=parse_int(row.get("home_attack")),
                away_attacks=parse_int(row.get("away_attack")),
            )
        ]

    def _dedup_key(self, match: Match) -> tuple:
        """Natural key identifying the same fixture across overlapping files."""
        return (
            match.date,
            match.home,
            match.away,
            match.home_goals,
            match.away_goals,
            match.competition,
        )

    def _add_match(self, match: Match) -> None:
        self.matches.append(match)
        self._by_competition.setdefault(match.competition, []).append(match)
        if match.season:
            self._seasons[match.competition].add(match.season)

    # ------------------------------------------------------------------ #
    # Players
    # ------------------------------------------------------------------ #

    def _load_players(self) -> None:
        for row in self._read("fifa_data.csv"):
            try:
                player = Player(
                    player_id=int(row["ID"]),
                    name=row["Name"],
                    age=parse_int(row.get("Age")),
                    nationality=row.get("Nationality") or "",
                    overall=parse_int(row.get("Overall")) or 0,
                    potential=parse_int(row.get("Potential")),
                    club=(row.get("Club") or "").strip(),
                    position=row.get("Position") or None,
                    jersey_number=parse_int(row.get("Jersey Number")),
                    preferred_foot=row.get("Preferred Foot") or None,
                    value=row.get("Value") or None,
                    wage=row.get("Wage") or None,
                    height=row.get("Height") or None,
                    weight=row.get("Weight") or None,
                    skills={
                        col: v
                        for col in SKILL_COLUMNS
                        if (v := parse_int(row.get(col))) is not None
                    },
                )
            except (KeyError, ValueError, TypeError):
                continue
            self.players.append(player)
            self._club_of_player[player.player_id] = self.teams.canonical(player.club) if player.club else ""

    def club_of(self, player: Player) -> str:
        """Canonical team key for the player's club (empty string if none)."""
        return self._club_of_player.get(player.player_id, "")

    # ------------------------------------------------------------------ #
    # Access helpers
    # ------------------------------------------------------------------ #

    def matches_for(self, competition: str | None = None) -> list[Match]:
        if competition is None:
            return self.matches
        return self._by_competition.get(competition, [])

    def competitions(self) -> list[str]:
        return sorted(self._by_competition)

    def seasons_for(self, competition: str) -> list[int]:
        return sorted(self._seasons.get(competition, set()))

    def display_team(self, canonical: str) -> str:
        return self.teams.display(canonical)


def load_soccer_data(data_dir: Path | None = None) -> SoccerData:
    """Load all datasets (cached after the first call)."""
    global _CACHE
    if _CACHE is None or data_dir is not None:
        _CACHE = SoccerData(data_dir)
    return _CACHE


_CACHE: SoccerData | None = None
