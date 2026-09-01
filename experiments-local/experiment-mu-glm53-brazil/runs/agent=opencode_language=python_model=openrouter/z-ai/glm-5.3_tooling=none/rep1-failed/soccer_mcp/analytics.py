"""Statistical computations over the unified match list.

CONTEXT
-------
Pure functions consumed by :mod:`soccer_mcp.service`: team records,
head-to-head summaries, league tables (3 points per win), biggest wins,
competition-wide aggregates and derby detection.  Matches without a
recorded score are kept for listings but excluded from all statistics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import Match
from .normalize import TeamRegistry

# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


@dataclass
class TeamRecord:
    """Win/draw/loss record of one team over a set of matches."""

    team: str  # entity key
    team_display: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def win_rate(self) -> float:
        """Wins / decided-or-played matches (draws count as non-wins)."""
        return (self.wins / self.matches) if self.matches else 0.0

    def line(self) -> str:
        rate = f"{self.win_rate * 100:.1f}%"
        return (
            f"Matches: {self.matches}, Wins: {self.wins}, Draws: {self.draws}, "
            f"Losses: {self.losses}\n"
            f"Goals For: {self.goals_for}, Goals Against: {self.goals_against}, "
            f"Goal Diff: {self.goal_diff:+d}\n"
            f"Win rate: {rate}"
        )


def team_record(matches: list[Match], team_key: str, registry: TeamRegistry, venue: str = "all") -> TeamRecord:
    """Aggregate W/D/L and goals for *team_key*.

    Args:
        venue: ``"all"``, ``"home"`` or ``"away"``.
    """
    display = registry.display_name(*_split_key(team_key))
    record = TeamRecord(team=team_key, team_display=display)
    for m in matches:
        if not m.has_score:
            continue
        if m.home == team_key:
            if venue not in ("all", "home"):
                continue
            gf, ga = m.home_goals, m.away_goals  # type: ignore[assignment]
        elif m.away == team_key:
            if venue not in ("all", "away"):
                continue
            gf, ga = m.away_goals, m.home_goals  # type: ignore[assignment]
        else:
            continue
        record.matches += 1
        record.goals_for += gf  # type: ignore[operator]
        record.goals_against += ga  # type: ignore[operator]
        if gf > ga:  # type: ignore[operator]
            record.wins += 1
        elif gf == ga:  # type: ignore[operator]
            record.draws += 1
        else:
            record.losses += 1
    return record


@dataclass
class HeadToHead:
    """Head-to-head summary between two teams."""

    team_a: str
    team_b: str
    display_a: str
    display_b: str
    matches: list[Match]
    wins_a: int = 0
    wins_b: int = 0
    draws: int = 0
    goals_a: int = 0
    goals_b: int = 0

    @property
    def total(self) -> int:
        return len(self.matches)


def head_to_head(
    matches: list[Match], key_a: str, key_b: str, registry: TeamRegistry
) -> HeadToHead:
    h2h = HeadToHead(
        team_a=key_a,
        team_b=key_b,
        display_a=registry.display_name(*_split_key(key_a)),
        display_b=registry.display_name(*_split_key(key_b)),
        matches=[],
    )
    for m in matches:
        if {m.home, m.away} != {key_a, key_b}:
            continue
        h2h.matches.append(m)
        if not m.has_score:
            continue
        if m.home == key_a:
            gf_a, gf_b = m.home_goals, m.away_goals  # type: ignore[assignment]
        else:
            gf_a, gf_b = m.away_goals, m.home_goals  # type: ignore[assignment]
        h2h.goals_a += gf_a  # type: ignore[operator]
        h2h.goals_b += gf_b  # type: ignore[operator]
        if gf_a > gf_b:  # type: ignore[operator]
            h2h.wins_a += 1
        elif gf_a < gf_b:  # type: ignore[operator]
            h2h.wins_b += 1
        else:
            h2h.draws += 1
    return h2h


# --------------------------------------------------------------------------
# Standings
# --------------------------------------------------------------------------


@dataclass
class StandingsRow:
    position: int = 0
    team: str = ""
    team_display: str = ""
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_diff: int = 0
    points: int = 0

    def line(self) -> str:
        return (
            f"{self.position}. {self.team_display} - {self.points} pts "
            f"({self.wins}W, {self.draws}D, {self.losses}L), "
            f"GF {self.goals_for}, GA {self.goals_against}, GD {self.goal_diff:+d}"
        )


def standings(matches: list[Match], registry: TeamRegistry) -> list[StandingsRow]:
    """Compute a league table (win = 3 pts, draw = 1) from a season's matches.

    Matches without scores are ignored; every participating team gets a
    row so partial data is still visible.
    """
    rows: dict[str, StandingsRow] = {}

    def row_for(key: str) -> StandingsRow:
        if key not in rows:
            rows[key] = StandingsRow(
                team=key, team_display=registry.display_name(*_split_key(key))
            )
        return rows[key]

    for m in matches:
        row_for(m.home)
        row_for(m.away)
        if not m.has_score:
            continue
        home, away = row_for(m.home), row_for(m.away)
        home.played += 1
        away.played += 1
        home.goals_for += m.home_goals  # type: ignore[operator]
        home.goals_against += m.away_goals  # type: ignore[operator]
        away.goals_for += m.away_goals  # type: ignore[operator]
        away.goals_against += m.home_goals  # type: ignore[operator]
        if m.home_goals > m.away_goals:  # type: ignore[operator]
            home.wins += 1
            away.losses += 1
            home.points += 3
        elif m.home_goals < m.away_goals:  # type: ignore[operator]
            away.wins += 1
            home.losses += 1
            away.points += 3
        else:
            home.draws += 1
            away.draws += 1
            home.points += 1
            away.points += 1

    table = sorted(
        rows.values(),
        key=lambda r: (
            -r.points,
            -r.wins,
            -(r.goals_for - r.goals_against),
            -r.goals_for,
            r.team_display,
        ),
    )
    for i, row in enumerate(table, start=1):
        row.position = i
        row.goal_diff = row.goals_for - row.goals_against
    return table


# --------------------------------------------------------------------------
# Competition-wide statistics
# --------------------------------------------------------------------------


@dataclass
class CompetitionStats:
    total: int = 0
    scored: int = 0
    home_wins: int = 0
    away_wins: int = 0
    draws: int = 0
    goals: int = 0
    biggest_margin: int = 0

    @property
    def avg_goals(self) -> float:
        return self.goals / self.scored if self.scored else 0.0

    @property
    def home_win_pct(self) -> float:
        return self.home_wins / self.scored if self.scored else 0.0

    @property
    def away_win_pct(self) -> float:
        return self.away_wins / self.scored if self.scored else 0.0

    @property
    def draw_pct(self) -> float:
        return self.draws / self.scored if self.scored else 0.0


def competition_stats(matches: list[Match]) -> CompetitionStats:
    stats = CompetitionStats()
    for m in matches:
        stats.total += 1
        if not m.has_score:
            continue
        stats.scored += 1
        stats.goals += m.home_goals + m.away_goals  # type: ignore[operator]
        margin = m.margin or 0
        stats.biggest_margin = max(stats.biggest_margin, margin)
        winner = m.winner()
        if winner is None:
            stats.draws += 1
        elif winner == m.home:
            stats.home_wins += 1
        else:
            stats.away_wins += 1
    return stats


def biggest_wins(matches: list[Match], registry: TeamRegistry, limit: int = 10) -> list[tuple[int, Match]]:
    """Largest goal margins, most lopsided first (ties: newest first)."""
    scored = [m for m in matches if m.has_score]
    scored.sort(
        key=lambda m: (
            -(m.margin or 0),
            -(m.date.toordinal() if m.date else 0),
        )
    )
    return [(m.margin or 0, m) for m in scored[:limit]]


def best_records(
    matches: list[Match],
    registry: TeamRegistry,
    venue: str,
    min_matches: int = 10,
    limit: int = 5,
) -> list[TeamRecord]:
    """Top teams by win rate for a venue (``home``/``away``/``all``)."""
    teams = {m.home for m in matches} | {m.away for m in matches}
    records = [
        team_record(matches, key, registry, venue=venue)
        for key in teams
    ]
    records = [r for r in records if r.matches >= min_matches]
    records.sort(key=lambda r: (-r.win_rate, -r.points, r.team_display))
    return records[:limit]


# --------------------------------------------------------------------------
# Derbies
# --------------------------------------------------------------------------

#: Famous derby pairings by entity keys (either venue order).
DERBY_PAIRS: list[tuple[str, str, str]] = [
    ("Fla-Flu", "flamengo|RJ", "fluminense|RJ"),
    ("Clássico dos Milhões", "flamengo|RJ", "vasco|RJ"),
    ("Clássico Vovô", "botafogo|RJ", "fluminense|RJ"),
    ("Clássico da Amizade", "botafogo|RJ", "vasco|RJ"),
    ("Derby Paulista", "corinthians|SP", "palmeiras|SP"),
    ("Majestoso", "corinthians|SP", "sao paulo|SP"),
    ("Choque Rei", "palmeiras|SP", "sao paulo|SP"),
    ("Clássico dos Campeões", "santos|SP", "sao paulo|SP"),
    ("Gre-Nal", "gremio|RS", "internacional|RS"),
    ("Clássico Mineiro", "atletico|MG", "cruzeiro|MG"),
    ("Atletiba", "atletico|PR", "coritiba|PR"),
    ("Ba-Vi", "bahia|BA", "vitoria|BA"),
    ("Clássico-Rei", "ceara|CE", "fortaleza|CE"),
    ("Clássico dos Clássicos", "sport|PE", "nautico|PE"),
    ("Clássico das Multidões", "santa cruz|PE", "sport|PE"),
    ("Clássico de Florianópolis", "avai|SC", "figueirense|SC"),
]


def derby_name(home: str, away: str) -> str | None:
    """Name of the derby between two entity keys, if they are classic rivals."""
    for name, a, b in DERBY_PAIRS:
        if {home, away} == {a, b}:
            return name
    return None


def find_derbies(matches: list[Match]) -> list[tuple[str, Match]]:
    """All matches between classic rival pairs, with the derby name."""
    out: list[tuple[str, Match]] = []
    for m in matches:
        name = derby_name(m.home, m.away)
        if name:
            out.append((name, m))
    return out


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _split_key(key: str) -> tuple[str, str | None]:
    """``"atletico|MG"`` -> ``("atletico", "MG")``; ``"boca juniors|"`` -> ``("boca juniors", None)``."""
    base, _, region = key.rpartition("|")
    return base, (region or None)
