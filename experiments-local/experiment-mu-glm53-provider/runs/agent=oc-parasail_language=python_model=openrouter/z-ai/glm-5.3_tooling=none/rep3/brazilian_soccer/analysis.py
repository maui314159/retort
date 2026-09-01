"""Query and analysis functions over the unified soccer dataset.

Every public function takes a loaded :class:`~brazilian_soccer.loader.SoccerData`
and plain query parameters, and returns plain data structures (dataclasses,
dicts, lists) that the MCP server renders as text.  Unknown teams or
competitions raise :class:`AnalysisError` with a helpful message instead of
failing silently.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from typing import Any, Optional

from .loader import SoccerData
from .models import Match, Player, StandingRow, TeamRecord
from .normalize import TeamInfo
from .normalize import compact, fold

__all__ = [
    "AnalysisError",
    "resolve_team",
    "resolve_competition",
    "search_matches",
    "head_to_head",
    "last_match_between",
    "team_stats",
    "team_profile",
    "team_competitions",
    "search_players",
    "player_details",
    "standings",
    "champion",
    "competition_finals",
    "biggest_wins",
    "competition_stats",
    "best_records",
    "derbies",
    "compare_seasons",
    "search_teams",
    "list_competitions",
]

POINTS_PER_WIN = 3
RELEGATION_SPOTS = 4

# Fuzzy-match threshold for forgiving user input.
_FUZZY_THRESHOLD = 0.75


class AnalysisError(ValueError):
    """Raised when a query cannot be resolved (unknown team, season, ...)."""


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def resolve_team(data: SoccerData, query: str) -> TeamInfo:
    """Resolve a user-supplied team name to a canonical team."""
    if not query or not query.strip():
        raise AnalysisError("No team name provided.")
    candidates = data.registry.find(query)
    if not candidates:
        raise AnalysisError(
            f"No team matching '{query}' was found in the dataset. "
            "Use search_teams to look for similar names."
        )
    # Prefer teams that actually appear in match data.
    with_matches = [c for c in candidates if c.match_count > 0]
    best = (with_matches or candidates)[0]
    return best


def resolve_competition(data: SoccerData, query: Optional[str]) -> Optional[str]:
    """Resolve a competition name to its canonical id (None = all)."""
    if not query:
        return None
    q = fold(query)
    aliases = {
        "brasileirao": "brasileirao",
        "brasileirao serie a": "brasileirao",
        "serie a": "brasileirao",
        "seriea": "brasileirao",
        "serie a do brasileirao": "brasileirao",
        "campeonato brasileiro": "brasileirao",
        "brazilian league": "brasileirao",
        "copa do brasil": "copadobrasil",
        "cup brazil": "copadobrasil",
        "brazilian cup": "copadobrasil",
        "copadobrasil": "copadobrasil",
        "libertadores": "libertadores",
        "copa libertadores": "libertadores",
        "libertadores cup": "libertadores",
        "serie b": "serieb",
        "serieb": "serieb",
        "brasileirao serie b": "serieb",
        "serie c": "seriec",
        "seriec": "seriec",
        "brasileirao serie c": "seriec",
    }
    qc = compact(query)
    for name, comp_id in aliases.items():
        if q == name or qc == compact(name):
            return comp_id
    for comp_id, info in data.competitions.items():
        if q == fold(info.display) or qc == compact(info.display):
            return comp_id
    # Substring fallback.
    for name, comp_id in aliases.items():
        if qc in compact(name) or compact(name) in qc:
            return comp_id
    raise AnalysisError(
        f"Unknown competition '{query}'. Available: "
        + ", ".join(i.display for i in data.competitions.values())
    )


def _parse_date_arg(value: str) -> Optional[date]:
    if value is None:
        return None
    from .loader import parse_date

    return parse_date(str(value))


def _format_date(d: Optional[date]) -> str:
    return d.isoformat() if d else "unknown date"


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------


@dataclass
class MatchSearchResult:
    matches: list[Match]
    total: int
    truncated: bool
    team: Optional[TeamInfo] = None
    opponent: Optional[TeamInfo] = None
    competition_id: Optional[str] = None
    season: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    filters: dict = field(default_factory=dict)


def search_matches(
    data: SoccerData,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 20,
) -> MatchSearchResult:
    """Search matches by team, opponent, competition, season and date range."""
    team_info = resolve_team(data, team) if team else None
    opponent_info = resolve_team(data, opponent) if opponent else None
    competition_id = resolve_competition(data, competition)
    date_from_d = _parse_date_arg(date_from) if date_from else None
    date_to_d = _parse_date_arg(date_to) if date_to else None
    stage_q = fold(stage) if stage else None

    pool: list[Match]
    if competition_id:
        pool = data.matches_for_competition(competition_id)
    elif team_info:
        pool = data.matches_for_team(team_info.key)
    else:
        pool = data.matches

    out: list[Match] = []
    for m in pool:
        if team_info and not m.involves(team_info.key):
            continue
        if opponent_info and not m.involves(opponent_info.key):
            continue
        if team_info and opponent_info and team_info.key == opponent_info.key:
            pass
        if season is not None and m.season != season:
            continue
        if date_from_d and (m.date is None or m.date < date_from_d):
            continue
        if date_to_d and (m.date is None or m.date > date_to_d):
            continue
        if stage_q and stage_q not in fold(m.stage):
            continue
        out.append(m)

    out.sort(key=lambda m: (m.date or date.min, m.competition_id), reverse=True)
    total = len(out)
    limited = out[: max(1, min(limit, 200))]
    return MatchSearchResult(
        matches=limited,
        total=total,
        truncated=total > len(limited),
        team=team_info,
        opponent=opponent_info,
        competition_id=competition_id,
        season=season,
        date_from=date_from_d,
        date_to=date_to_d,
        filters={"stage": stage} if stage else {},
    )


@dataclass
class HeadToHeadResult:
    team_a: TeamInfo
    team_b: TeamInfo
    matches: list[Match]
    total: int
    wins_a: int = 0
    wins_b: int = 0
    draws: int = 0
    goals_a: int = 0
    goals_b: int = 0
    per_competition: dict[str, dict[str, int]] = field(default_factory=dict)


def head_to_head(
    data: SoccerData,
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    limit: int = 20,
) -> HeadToHeadResult:
    """All matches between two teams plus the win/draw/loss record."""
    info_a = resolve_team(data, team_a)
    info_b = resolve_team(data, team_b)
    if info_a.key == info_b.key:
        raise AnalysisError("Please provide two different teams.")
    competition_id = resolve_competition(data, competition)
    pool = (
        data.matches_for_competition(competition_id)
        if competition_id
        else data.matches
    )
    result = HeadToHeadResult(team_a=info_a, team_b=info_b, matches=[], total=0)
    for m in pool:
        if {m.home_key, m.away_key} != {info_a.key, info_b.key}:
            continue
        result.matches.append(m)
        gf_a, ga_a = m.opponent_of(info_a.key)[1], m.opponent_of(info_a.key)[2]
        result.goals_a += gf_a
        result.goals_b += ga_a
        winner = m.winner_key
        if winner is None:
            result.draws += 1
        elif winner == info_a.key:
            result.wins_a += 1
        else:
            result.wins_b += 1
        comp = result.per_competition.setdefault(
            m.competition,
            {"matches": 0, f"wins_{info_a.key}": 0, f"wins_{info_b.key}": 0, "draws": 0},
        )
        comp["matches"] += 1
        if winner is None:
            comp["draws"] += 1
        elif winner == info_a.key:
            comp[f"wins_{info_a.key}"] += 1
        else:
            comp[f"wins_{info_b.key}"] += 1
    result.matches.sort(key=lambda m: (m.date or date.min), reverse=True)
    result.total = len(result.matches)
    result.matches = result.matches[: max(1, min(limit, 200))]
    return result


def last_match_between(data: SoccerData, team_a: str, team_b: str) -> Optional[Match]:
    """The most recent match between two teams."""
    info_a = resolve_team(data, team_a)
    info_b = resolve_team(data, team_b)
    best: Optional[Match] = None
    for m in data.matches_for_team(info_a.key):
        if m.involves(info_b.key):
            if best is None or (m.date or date.min) > (best.date or date.min):
                best = m
    return best


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------


def _filter_matches(
    data: SoccerData,
    team_key: str,
    competition: Optional[str],
    season: Optional[int],
) -> list[Match]:
    competition_id = resolve_competition(data, competition)
    pool = data.matches_for_team(team_key)
    if competition_id:
        pool = [m for m in pool if m.competition_id == competition_id]
    if season is not None:
        pool = [m for m in pool if m.season == season]
    return pool


@dataclass
class TeamStatsResult:
    team: TeamInfo
    competition_id: Optional[str]
    season: Optional[int]
    overall: TeamRecord
    home: TeamRecord
    away: TeamRecord
    match_count: int


def team_stats(
    data: SoccerData,
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
) -> TeamStatsResult:
    """Win/draw/loss record, goals and venue splits for one team."""
    info = resolve_team(data, team)
    matches = _filter_matches(data, info.key, competition, season)
    if not matches:
        raise AnalysisError(
            f"No matches found for {info.display}"
            + (f" in season {season}" if season else "")
            + (" in the given competition" if competition else "")
            + "."
        )
    competition_id = resolve_competition(data, competition)
    overall = TeamRecord(team_key=info.key, team=info.display)
    home_rec = TeamRecord(team_key=info.key, team=info.display)
    away_rec = TeamRecord(team_key=info.key, team=info.display)
    for m in matches:
        overall.add_match(m, info.key)
        if m.home_key == info.key:
            home_rec.add_match(m, info.key)
        else:
            away_rec.add_match(m, info.key)
    return TeamStatsResult(
        team=info,
        competition_id=competition_id,
        season=season,
        overall=overall,
        home=home_rec,
        away=away_rec,
        match_count=len(matches),
    )


@dataclass
class TeamCompetitionEntry:
    competition_id: str
    competition: str
    seasons: list[int]
    record: TeamRecord


@dataclass
class TeamProfileResult:
    team: TeamInfo
    entries: list[TeamCompetitionEntry]
    overall: TeamRecord
    first_season: Optional[int]
    last_season: Optional[int]
    squad: list[Player]
    notes: list[str] = field(default_factory=list)


def team_competitions(data: SoccerData, team: str) -> TeamProfileResult:
    """Which competitions and seasons a team appears in (cross-file)."""
    return team_profile(data, team)


def team_profile(data: SoccerData, team: str) -> TeamProfileResult:
    info = resolve_team(data, team)
    matches = data.matches_for_team(info.key)
    by_comp: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        by_comp[m.competition_id].append(m)
    entries = []
    overall = TeamRecord(team_key=info.key, team=info.display)
    all_seasons: set[int] = set()
    for comp_id in sorted(by_comp, key=lambda c: data.competitions[c].display):
        comp_matches = by_comp[comp_id]
        record = TeamRecord(team_key=info.key, team=info.display)
        for m in comp_matches:
            record.add_match(m, info.key)
            overall.add_match(m, info.key)
        seasons = sorted({m.season for m in comp_matches if m.season})
        all_seasons.update(seasons)
        entries.append(
            TeamCompetitionEntry(
                competition_id=comp_id,
                competition=data.competitions[comp_id].display,
                seasons=seasons,
                record=record,
            )
        )
    squad = data.players_for_club(info.key)
    notes = []
    if not squad:
        notes.append(
            f"No {info.display} players appear in the FIFA player dataset."
        )
    return TeamProfileResult(
        team=info,
        entries=entries,
        overall=overall,
        first_season=min(all_seasons) if all_seasons else None,
        last_season=max(all_seasons) if all_seasons else None,
        squad=squad,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------


@dataclass
class PlayerSearchResult:
    players: list[Player]
    total: int
    truncated: bool
    club: Optional[TeamInfo] = None
    filters: dict = field(default_factory=dict)


POSITION_GROUP_ALIASES = {
    "forward": "Forward",
    "forwards": "Forward",
    "attacker": "Forward",
    "striker": "Forward",
    "midfielder": "Midfielder",
    "midfield": "Midfielder",
    "defender": "Defender",
    "defense": "Defender",
    "goalkeeper": "Goalkeeper",
    "goalie": "Goalkeeper",
    "gk": "Goalkeeper",
    "keeper": "Goalkeeper",
}


def _position_matches(player: Player, position_q: str) -> bool:
    """Exact position code match, or position-group word ('forward')."""
    if player.position.upper() == position_q.upper():
        return True
    group = POSITION_GROUP_ALIASES.get(position_q.strip().lower())
    if group:
        return player.position_group == group
    return False


def search_players(
    data: SoccerData,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    max_overall: Optional[int] = None,
    sort_by: str = "overall",
    limit: int = 20,
) -> PlayerSearchResult:
    """Search the FIFA player database by name, nationality, club, position."""
    club_info = None
    club_keys: set[str] = set()
    if club:
        # Resolve the club through the team registry (covers both Brazilian
        # league clubs and foreign clubs present in the FIFA file).
        club_info = resolve_team(data, club)
        club_keys = {club_info.key}
    nationality_q = fold(nationality) if nationality else None
    position_q = fold(position) if position else None

    out = []
    for player in data.players:
        if name and compact(name) not in compact(player.name):
            continue
        if nationality_q and nationality_q not in fold(player.nationality):
            continue
        if club and player.club_key not in club_keys:
            continue
        if position_q and not _position_matches(player, position_q):
            continue
        if min_overall is not None and (player.overall or 0) < min_overall:
            continue
        if max_overall is not None and (player.overall or 999) > max_overall:
            continue
        out.append(player)

    reverse = sort_by in {"overall", "potential", "age"}
    sort_key = {
        "overall": lambda p: p.overall or 0,
        "potential": lambda p: p.potential or 0,
        "age": lambda p: p.age or 0,
        "name": lambda p: p.name,
    }.get(sort_by, lambda p: p.overall or 0)
    out.sort(key=lambda p: (sort_key(p), p.name), reverse=reverse)
    total = len(out)
    limited = out[: max(1, min(limit, 200))]
    return PlayerSearchResult(
        players=limited,
        total=total,
        truncated=total > len(limited),
        club=club_info,
        filters={
            k: v
            for k, v in {
                "name": name,
                "nationality": nationality,
                "position": position,
                "min_overall": min_overall,
                "max_overall": max_overall,
                "sort_by": sort_by,
            }.items()
            if v is not None
        },
    )


def player_details(data: SoccerData, name: str) -> list[Player]:
    """Full detail lookup for one or more players by name."""
    if not name or not name.strip():
        raise AnalysisError("No player name provided.")
    matches = data.find_players_by_name(name)
    if not matches:
        # Fuzzy fallback.
        needle = fold(name)
        best: list[tuple[float, Player]] = []
        for player in data.players:
            ratio = SequenceMatcher(None, needle, fold(player.name)).ratio()
            if ratio >= 0.8:
                best.append((ratio, player))
        best.sort(key=lambda p: -p[0])
        matches = [p for _r, p in best[:5]]
    if not matches:
        raise AnalysisError(f"No player matching '{name}' found in the FIFA dataset.")
    return matches


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------


def _league_table(matches: list[Match]) -> list[TeamRecord]:
    """Compute a league table from a season's matches.

    If a directed pairing appears twice (data noise or knockout-format
    competitions), only the latest match counts, keeping the table a valid
    double round-robin.
    """
    by_pairing: dict[tuple[str, str], list[Match]] = defaultdict(list)
    for m in matches:
        by_pairing[(m.home_key, m.away_key)].append(m)
    records: dict[str, TeamRecord] = {}
    for (_h, _a), games in by_pairing.items():
        game = max(games, key=lambda m: (m.date or date.min,))
        for key in (game.home_key, game.away_key):
            if key not in records:
                records[key] = TeamRecord(team_key=key)
        records[game.home_key].add_match(game, game.home_key)
        records[game.away_key].add_match(game, game.away_key)
    return list(records.values())


def standings(
    data: SoccerData,
    competition: str,
    season: int,
) -> tuple[Any, list[str]]:
    """League standings computed from match results.

    Returns ``(CompetitionStandings, notes)``.
    """
    competition_id = resolve_competition(data, competition)
    info = data.competitions.get(competition_id)
    if not info:
        raise AnalysisError(f"Unknown competition '{competition}'.")
    if info.kind != "league":
        raise AnalysisError(
            f"{info.display} is a cup competition; standings are not "
            "meaningful. Try competition_finals or champion instead."
        )
    if season not in info.seasons:
        raise AnalysisError(
            f"{info.display} has no season {season} in the dataset "
            f"(available: {info.seasons[0]}-{info.seasons[-1]})."
        )
    matches = [m for m in data.matches_for_competition(competition_id) if m.season == season]
    records = _league_table(matches)
    records.sort(key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.team))
    from .models import CompetitionStandings

    table = CompetitionStandings(
        competition_id=competition_id,
        competition=info.display,
        season=season,
    )
    team_names = {r.team_key: r.team for r in records}
    for r in records:
        r.team = team_names.get(r.team_key) or r.team
    # Display names from the registry.
    for r in records:
        reg = data.registry.get(r.team_key)
        if reg:
            r.team = reg.display
    rows = [
        StandingRow(
            position=i + 1,
            team_key=r.team_key,
            team=r.team,
            played=r.matches,
            wins=r.wins,
            draws=r.draws,
            losses=r.losses,
            goals_for=r.goals_for,
            goals_against=r.goals_against,
            goal_diff=r.goal_diff,
            points=r.points,
        )
        for i, r in enumerate(records)
    ]
    table.rows = rows
    notes = []
    total_played = sum(r.played for r in rows) // 2
    teams_count = len(rows)
    if teams_count and total_played < teams_count * (teams_count - 1):
        notes.append(
            f"The dataset is incomplete for this season "
            f"({total_played} of {teams_count * (teams_count - 1)} matches), "
            "so the table is provisional."
        )
    return table, notes


def _cup_final_matches(data: SoccerData, competition_id: str, season: int) -> list[Match]:
    return [
        m
        for m in data.matches_for_competition(competition_id)
        if m.season == season and m.stage == "Final"
    ]


@dataclass
class CupFinalResult:
    competition: str
    season: int
    matches: list[Match]
    winner: Optional[str]
    winner_display: Optional[str]
    note: Optional[str] = None


def _cup_champion(data: SoccerData, competition_id: str, season: int) -> CupFinalResult:
    info = data.competitions[competition_id]
    finals = _cup_final_matches(data, competition_id, season)
    if not finals:
        raise AnalysisError(
            f"No final found for the {season} {info.display} in the dataset."
        )
    totals: dict[str, int] = defaultdict(int)
    for m in finals:
        totals[m.home_key] += m.home_goals
        totals[m.away_key] += m.away_goals
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    winner, note = None, None
    if len(ranked) == 2 and ranked[0][1] == ranked[1][1]:
        note = (
            "The two-legged final finished level on aggregate; it was decided "
            "on penalties, which are not recorded in the dataset."
        )
    else:
        winner = ranked[0][0]
    winner_display = None
    if winner:
        reg = data.registry.get(winner)
        winner_display = reg.display if reg else winner
    return CupFinalResult(
        competition=info.display,
        season=season,
        matches=sorted(finals, key=lambda m: m.date or date.min),
        winner=winner,
        winner_display=winner_display,
        note=note,
    )


def champion(data: SoccerData, competition: str, season: int) -> dict:
    """Determine the champion of a competition season."""
    competition_id = resolve_competition(data, competition)
    info = data.competitions.get(competition_id)
    if not info:
        raise AnalysisError(f"Unknown competition '{competition}'.")
    if season not in info.seasons:
        raise AnalysisError(
            f"{info.display} has no season {season} in the dataset "
            f"(available: {info.seasons[0]}-{info.seasons[-1]})."
        )
    if info.kind == "league":
        table, notes = standings(data, competition_id, season)
        champ = table.champion
        return {
            "competition": info.display,
            "season": season,
            "champion": champ.team,
            "champion_key": champ.team_key,
            "record": f"{champ.wins}W {champ.draws}D {champ.losses}L, {champ.points} pts",
            "method": "top of the calculated league table",
            "notes": notes,
        }
    final = _cup_champion(data, competition_id, season)
    return {
        "competition": final.competition,
        "season": season,
        "champion": final.winner_display,
        "champion_key": final.winner,
        "method": "winner of the final (aggregate over legs)",
        "notes": [final.note] if final.note else [],
    }


def competition_finals(
    data: SoccerData,
    competition: str,
    season: Optional[int] = None,
) -> list[CupFinalResult]:
    """List final-round matches of a cup competition."""
    competition_id = resolve_competition(data, competition)
    info = data.competitions.get(competition_id)
    if not info:
        raise AnalysisError(f"Unknown competition '{competition}'.")
    if info.kind != "cup":
        raise AnalysisError(
            f"{info.display} is a league; use standings or champion instead."
        )
    seasons = [season] if season else info.seasons
    results = []
    for s in seasons:
        try:
            results.append(_cup_champion(data, competition_id, s))
        except AnalysisError:
            continue  # no final recorded for this season
    if season and not results:
        raise AnalysisError(
            f"No final recorded for the {season} {info.display} in the dataset."
        )
    return results


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------


def biggest_wins(
    data: SoccerData,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
) -> list[Match]:
    """Largest victory margins in the dataset."""
    competition_id = resolve_competition(data, competition)
    pool = data.matches_for_competition(competition_id) if competition_id else data.matches
    if season is not None:
        pool = [m for m in pool if m.season == season]
    return sorted(pool, key=lambda m: (-m.margin, m.date or date.min))[: max(1, min(limit, 50))]


def competition_stats(
    data: SoccerData,
    competition: Optional[str] = None,
    season: Optional[int] = None,
) -> dict[str, Any]:
    """Aggregate scoring statistics: goals per match, home advantage."""
    competition_id = resolve_competition(data, competition)
    pool = data.matches_for_competition(competition_id) if competition_id else data.matches
    if season is not None:
        pool = [m for m in pool if m.season == season]
    if not pool:
        raise AnalysisError("No matches found for the given filters.")
    matches = len(pool)
    goals = sum(m.home_goals + m.away_goals for m in pool)
    home_wins = sum(1 for m in pool if m.winner == "home")
    away_wins = sum(1 for m in pool if m.winner == "away")
    draws = matches - home_wins - away_wins
    home_goals = sum(m.home_goals for m in pool)
    away_goals = sum(m.away_goals for m in pool)
    label = data.competitions[competition_id].display if competition_id else "all competitions"
    return {
        "label": label,
        "season": season,
        "matches": matches,
        "goals": goals,
        "avg_goals": goals / matches,
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_pct": home_wins / matches * 100,
        "away_win_pct": away_wins / matches * 100,
        "draw_pct": draws / matches * 100,
        "avg_home_goals": home_goals / matches,
        "avg_away_goals": away_goals / matches,
    }


def best_records(
    data: SoccerData,
    venue: str = "home",
    competition: Optional[str] = None,
    season: Optional[int] = None,
    min_matches: int = 10,
    limit: int = 10,
) -> list[tuple[TeamInfo, TeamRecord, float]]:
    """Rank teams by win rate at a venue ('home' or 'away')."""
    venue_q = fold(venue or "home")
    if venue_q not in {"home", "away"}:
        raise AnalysisError("venue must be 'home' or 'away'.")
    competition_id = resolve_competition(data, competition)
    pool = data.matches_for_competition(competition_id) if competition_id else data.matches
    if season is not None:
        pool = [m for m in pool if m.season == season]
    records: dict[str, TeamRecord] = {}
    for m in pool:
        side_key = m.home_key if venue_q == "home" else m.away_key
        rec = records.setdefault(side_key, TeamRecord(team_key=side_key))
        rec.add_match(m, side_key)
    ranked = []
    for key, rec in records.items():
        if rec.matches < min_matches:
            continue
        reg = data.registry.get(key)
        if not reg:
            continue
        ranked.append((reg, rec, rec.win_rate))
    ranked.sort(key=lambda t: (-t[2], -t[1].points, t[0].display))
    return ranked[: max(1, min(limit, 50))]


# Named Brazilian derbies (by canonical team keys).
DERBIES: list[tuple[str, str, str]] = [
    ("Fla-Flu", "flamengo", "fluminense"),
    ("Clássico dos Milhões", "flamengo", "vascodagama"),
    ("Clássico Vovô", "botafogo", "fluminense"),
    ("Clássico da Amizade", "botafogo", "vascodagama"),
    ("Majestoso", "corinthians", "saopaulo"),
    ("Choque-Rei", "palmeiras", "saopaulo"),
    ("Derby Paulista", "palmeiras", "corinthians"),
    ("San-São", "santos", "saopaulo"),
    ("Grenal", "gremio", "internacional"),
    ("Clássico Mineiro", "atleticomineiro", "cruzeiro"),
    ("Ba-Vi", "bahia", "vitoria"),
    ("Clássico-Rei (CE)", "ceara", "fortaleza"),
    ("Atletiba", "atleticoparanaense", "coritiba"),
    ("Re-Pa", "remo", "paysandu"),
    ("Clássico dos Clássicos", "sportrecife", "nautico"),
    ("Clássico das Multidões", "sportrecife", "santacruz"),
]


@dataclass
class DerbyResult:
    label: str
    matches: list[Match]


def derbies(
    data: SoccerData,
    season: Optional[int] = None,
    competition: Optional[str] = None,
) -> list[DerbyResult]:
    """Matches between traditional rival pairs (named derbies)."""
    competition_id = resolve_competition(data, competition)
    pool = data.matches_for_competition(competition_id) if competition_id else data.matches
    if season is not None:
        pool = [m for m in pool if m.season == season]
    results = []
    for label, a, b in DERBIES:
        pairs = [m for m in pool if {m.home_key, m.away_key} == {a, b}]
        if pairs:
            pairs.sort(key=lambda m: (m.date or date.min), reverse=True)
            results.append(DerbyResult(label=label, matches=pairs))
    return results


def compare_seasons(
    data: SoccerData,
    season_a: int,
    season_b: int,
    competition: str = "brasileirao",
) -> dict[str, Any]:
    """Side-by-side aggregate comparison of two seasons."""
    competition_id = resolve_competition(data, competition)
    info = data.competitions.get(competition_id)
    if not info:
        raise AnalysisError(f"Unknown competition '{competition}'.")
    for s in (season_a, season_b):
        if s not in info.seasons:
            raise AnalysisError(
                f"{info.display} has no season {s} (available: {info.seasons[0]}-{info.seasons[-1]})."
            )
    stats = {}
    for label, s in (("a", season_a), ("b", season_b)):
        stats[label] = competition_stats(data, competition_id, s)
    champs = {}
    for label, s in (("a", season_a), ("b", season_b)):
        try:
            champs[label] = champion(data, competition_id, s)
        except AnalysisError:
            champs[label] = None
    top_team = {}
    for label, s in (("a", season_a), ("b", season_b)):
        pool = [m for m in data.matches_for_competition(competition_id) if m.season == s]
        records = _league_table(pool)
        records.sort(key=lambda r: -r.goals_for)
        if records:
            reg = data.registry.get(records[0].team_key)
            top_team[label] = {
                "team": reg.display if reg else records[0].team_key,
                "goals_for": records[0].goals_for,
            }
    return {
        "competition": info.display,
        "season_a": season_a,
        "season_b": season_b,
        "stats_a": stats["a"],
        "stats_b": stats["b"],
        "champion_a": champs["a"],
        "champion_b": champs["b"],
        "top_scoring_team_a": top_team.get("a"),
        "top_scoring_team_b": top_team.get("b"),
    }


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def search_teams(data: SoccerData, query: str, limit: int = 10) -> list[TeamInfo]:
    """Fuzzy-search teams by name; returns canonical info + variants."""
    if not query or not query.strip():
        raise AnalysisError("No team query provided.")
    return data.registry.find(query)[: max(1, min(limit, 25))]


def list_competitions(data: SoccerData) -> list[Any]:
    """All competitions with season coverage and team counts."""
    return sorted(data.competitions.values(), key=lambda c: c.display)
