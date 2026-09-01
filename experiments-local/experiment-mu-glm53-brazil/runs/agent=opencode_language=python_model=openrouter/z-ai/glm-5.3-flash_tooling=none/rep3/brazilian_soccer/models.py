"""Data model: normalized Match and Player records.

Every row from the five match CSVs becomes one ``Match`` with:
- canonical competition label (``Brasileirão Serie A/B/C``, ``Copa do
  Brasil``, ``Copa Libertadores``),
- a parsed calendar ``date`` (``datetime.date``) plus optional kick-off
  ``time`` string,
- canonical team keys from ``TeamRegistry`` (cross-dataset stable),
- normalized integer goals,
- the originating dataset (``source``) for provenance,
- optional extended statistics (corners/shots/attacks) when present and
  the stadium name (``arena``) when present.

Rows from overlapping datasets describing the *same real match* are
de-duplicated by ``loader`` using a source priority, so statistics never
double-count.  ``Player`` rows come from the FIFA database; ``club_key``
links a player to the same team key space as matches (cross-file queries).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Canonical competition labels.
BRASILEIRAO_A = "Brasileirão Serie A"
BRASILEIRAO_B = "Brasileirão Serie B"
BRASILEIRAO_C = "Brasileirão Serie C"
COPA_DO_BRASIL = "Copa do Brasil"
LIBERTADORES = "Copa Libertadores"

LEAGUE_COMPETITIONS = {BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C}

BR_FOOTBALL_TOURNAMENTS = {
    "serie a": BRASILEIRAO_A,
    "serie b": BRASILEIRAO_B,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
}


@dataclass
class Match:
    competition: str
    season: int
    date: date | None
    home_goal: int | None
    away_goal: int | None
    source: str
    home_key: str = ""
    away_key: str = ""
    home_raw: str = ""
    away_raw: str = ""
    time: str | None = None
    round: int | None = None
    stage: str | None = None
    arena: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    # Extended statistics (BR-Football dataset), all optional.
    home_corner: int | None = None
    away_corner: int | None = None
    home_attack: int | None = None
    away_attack: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    total_corners: int | None = None

    def has_result(self) -> bool:
        return self.home_goal is not None and self.away_goal is not None

    def winner_key(self) -> str | None:
        """Canonical key of the winning team, or None for a draw/unknown."""
        if not self.has_result():
            return None
        if self.home_goal > self.away_goal:
            return self.home_key
        if self.away_goal > self.home_goal:
            return self.away_key
        return None


@dataclass
class Player:
    id: int
    name: str
    nationality: str
    overall: int
    potential: int
    club_key: str
    club_display: str
    club_raw: str
    position: str | None
    age: int | None = None
    jersey: int | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    value: str | None = None
    wage: str | None = None
    preferred_foot: str | None = None
    skills: dict[str, int] = field(default_factory=dict)

    def is_brazilian(self) -> bool:
        return self.nationality.strip().lower() == "brazil"
