"""Query engine for the Brazilian Soccer MCP server.

Every function takes the loaded :class:`~brazilian_soccer.data.Dataset` plus
plain filters, and returns dictionaries of plain Python values so the MCP
tool layer can format them and tests can assert on them directly.  Team and
competition names are resolved leniently: common aliases ("brasileirao",
"serie a") and club name variants ("Palmeiras-SP" vs "Palmeiras") are
accepted, and ambiguous inputs raise :class:`AmbiguousTeamError` listing the
candidates.
"""

from __future__ import annotations

from datetime import date

from brazilian_soccer.data import (
    COPA_DO_BRASIL,
    COMPETITION_DISPLAY,
    COMPETITION_KIND,
    KNOCKOUT_STAGES,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    STAGE_ALIASES,
    STAGE_DISPLAY,
    Dataset,
)
from brazilian_soccer.models import Match, TeamRecord
from brazilian_soccer.normalize import (
    DERBIES,
    DERBY_PAIRS,
    parse_date,
    slug,
    team_key,
)

POSITION_GROUPS = {
    "goalkeeper": ("GK",),
    "defender": ("CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"),
    "midfielder": (
        "CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM",
    ),
    "forward": ("ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"),
}

RELEGATION_SLOTS = 4


class QueryError(Exception):
    """Base class for user-facing query errors."""


class TeamNotFoundError(QueryError):
    def __init__(self, name: str, suggestion: str = ""):
        self.name = name
        self.suggestion = suggestion
        super().__init__(f"Team not found: {name!r}")


class AmbiguousTeamError(QueryError):
    def __init__(self, name: str, candidates: list[str]):
        self.name = name
        self.candidates = candidates
        super().__init__(f"Ambiguous team name: {name!r}")


class CompetitionNotFoundError(QueryError):
    def __init__(self, name: str, available: list[str]):
        super().__init__(f"Competition not found: {name!r}")
        self.available = available


def resolve_team(dataset: Dataset, name: str) -> str:
    """Resolve a raw team name to a canonical team key."""
    key = team_key(name or "")
    if key in dataset.known_teams or key in dataset.known_clubs:
        return key
    needle = slug(name or "")
    exact = {t for t in dataset.known_teams | dataset.known_clubs if t == needle}
    if exact:
        return next(iter(exact))
    partial = {
        t for t in dataset.known_teams | dataset.known_clubs
        if needle and (needle in t or t in needle)
    }
    display_partial = {
        t for t in dataset.known_teams | dataset.known_clubs
        if needle and needle in slug(dataset.team_display(t) if t in dataset.known_teams else t)
    }
    candidates = partial | display_partial
    if len(candidates) == 1:
        return next(iter(candidates))
    if len(candidates) > 1:
        raise AmbiguousTeamError(name, sorted(dataset.team_display(c) for c in candidates)[:12])
    raise TeamNotFoundError(name)


def resolve_competition(dataset: Dataset, name: str | None) -> str | None:
    """Resolve a user-provided competition name to a canonical one."""
    if not name:
        return None
    key = slug(name)
    canonical = {slug(c): c for c in COMPETITION_DISPLAY}
    canonical.update({
        "brasileirao": SERIE_A,
        "brasileirao serie a": SERIE_A,
        "serie a": SERIE_A,
        "seriea": SERIE_A,
        "serie a do brasileirao": SERIE_A,
        "brazilian serie a": SERIE_A,
        "brasileirao serie b": SERIE_B,
        "serie b": SERIE_B,
        "serieb": SERIE_B,
        "brazilian serie b": SERIE_B,
        "serie c": SERIE_C,
        "seriec": SERIE_C,
        "brazilian serie c": SERIE_C,
        "copa do brasil": COPA_DO_BRASIL,
        "copa brasil": COPA_DO_BRASIL,
        "brazilian cup": COPA_DO_BRASIL,
        "cup of brazil": COPA_DO_BRASIL,
        "libertadores": LIBERTADORES,
        "copa libertadores": LIBERTADORES,
        "libertadores cup": LIBERTADORES,
        "conmebol libertadores": LIBERTADORES,
    })
    if key in canonical:
        return canonical[key]
    for alias, comp in canonical.items():
        if alias in key or key in alias:
            return comp
    available = [COMPETITION_DISPLAY[c] for c in COMPETITION_DISPLAY]
    raise CompetitionNotFoundError(name, available)


def resolve_position(name: str) -> tuple[str, ...]:
    """Resolve a position filter to FIFA position codes."""
    if not name:
        return ()
    key = slug(name)
    if key in POSITION_GROUPS:
        return POSITION_GROUPS[key]
    codes = {code.lower(): code for group in POSITION_GROUPS.values() for code in group}
    if key in codes:
        return (codes[key],)
    raise QueryError(
        f"Unknown position {name!r}. Use a FIFA code (ST, LW, GK, ...) or a group "
        f"(forward, midfielder, defender, goalkeeper)."
    )


def _match_dict(dataset: Dataset, match: Match) -> dict:
    return {
        "date": match.date.isoformat() if match.date else None,
        "home": dataset.team_display(match.home),
        "away": dataset.team_display(match.away),
        "home_goals": match.home_goals,
        "away_goals": match.away_goals,
        "season": match.season,
        "competition": COMPETITION_DISPLAY.get(match.competition, match.competition),
        "stage": match.stage,
        "round": match.round,
        "source": match.source,
        "margin": match.margin,
    }


def _apply_date_bounds(
    matches: list[Match],
    from_date: str | None,
    to_date: str | None,
) -> list[Match]:
    lower = _date_bound(from_date, "from")
    upper = _date_bound(to_date, "to")
    result = matches
    if lower:
        result = [m for m in result if m.date and m.date >= lower]
    if upper:
        result = [m for m in result if m.date and m.date <= upper]
    return result


def _date_bound(value: str | None, kind: str) -> date | None:
    if not value:
        return None
    text = value.strip()
    if len(text) == 4 and text.isdigit():
        year = int(text)
        return date(year, 1, 1) if kind == "from" else date(year, 12, 31)
    parsed = parse_date(text)
    if parsed is None:
        raise QueryError(f"Invalid date {value!r}; use YYYY-MM-DD or DD/MM/YYYY.")
    return parsed


def _match_stage_label(match: Match) -> str | None:
    if match.stage:
        return match.stage
    if match.round:
        return f"round {match.round}"
    return None


def search_matches(
    dataset: Dataset,
    *,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    stage: str | None = None,
    team_side: str = "any",
    limit: int = 20,
) -> dict:
    """Search matches by team, opponent, competition, season, date or stage."""
    team_key_ = resolve_team(dataset, team) if team else None
    opponent_key = resolve_team(dataset, opponent) if opponent else None
    competition_key = resolve_competition(dataset, competition)
    stage_key = slug(stage) if stage else None
    if team_side not in ("any", "home", "away"):
        raise QueryError("team_side must be 'any', 'home' or 'away'.")

    pool = dataset.deduped_matches
    if competition_key:
        pool = [m for m in pool if m.competition == competition_key]
    if season is not None:
        pool = [m for m in pool if m.season == season]
    pool = _apply_date_bounds(pool, from_date, to_date)
    if team_key_:
        if team_side == "home":
            pool = [m for m in pool if m.home == team_key_]
        elif team_side == "away":
            pool = [m for m in pool if m.away == team_key_]
        else:
            pool = [m for m in pool if m.involves(team_key_)]
    if opponent_key:
        pool = [m for m in pool if m.involves(opponent_key)]
        if team_key_:
            pool = [m for m in pool if m.involves(team_key_)]
    if stage_key:
        wanted = STAGE_ALIASES.get(stage_key, stage_key)
        pool = [m for m in pool if (_match_stage_label(m) or "") == wanted]

    pool = sorted(pool, key=lambda m: m.sort_key(), reverse=True)
    total = len(pool)
    shown = pool[: max(1, limit)]
    return {
        "matches": [_match_dict(dataset, m) for m in shown],
        "total": total,
        "shown": len(shown),
        "filters": {
            "team": dataset.team_display(team_key_) if team_key_ else None,
            "opponent": dataset.team_display(opponent_key) if opponent_key else None,
            "competition": COMPETITION_DISPLAY.get(competition_key) if competition_key else None,
            "season": season,
            "from_date": from_date,
            "to_date": to_date,
            "stage": stage,
        },
    }


def last_match_between(dataset: Dataset, team_a: str, team_b: str) -> dict:
    """Return the most recent match between two teams."""
    key_a = resolve_team(dataset, team_a)
    key_b = resolve_team(dataset, team_b)
    candidates = [
        m for m in dataset.deduped_matches
        if {m.home, m.away} == {key_a, key_b} and m.date is not None
    ]
    if not candidates:
        return {
            "team_a": dataset.team_display(key_a),
            "team_b": dataset.team_display(key_b),
            "match": None,
            "all_matches_between": 0,
        }
    latest = max(candidates, key=lambda m: (m.date, m.sort_key()))
    return {
        "team_a": dataset.team_display(key_a),
        "team_b": dataset.team_display(key_b),
        "match": _match_dict(dataset, latest),
        "all_matches_between": len(candidates),
    }


def head_to_head(
    dataset: Dataset,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict:
    """Head-to-head record between two teams."""
    key_a = resolve_team(dataset, team_a)
    key_b = resolve_team(dataset, team_b)
    competition_key = resolve_competition(dataset, competition)
    pool = [
        m for m in dataset.deduped_matches
        if {m.home, m.away} == {key_a, key_b}
    ]
    if competition_key:
        pool = [m for m in pool if m.competition == competition_key]
    if season is not None:
        pool = [m for m in pool if m.season == season]
    pool = sorted(pool, key=lambda m: m.sort_key(), reverse=True)
    wins_a = sum(1 for m in pool if m.winner == key_a)
    wins_b = sum(1 for m in pool if m.winner == key_b)
    draws = sum(1 for m in pool if m.is_scored and m.winner is None)
    unscored = sum(1 for m in pool if not m.is_scored)
    return {
        "team_a": dataset.team_display(key_a),
        "team_b": dataset.team_display(key_b),
        "total": len(pool),
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": draws,
        "unscored": unscored,
        "goals_a": sum(m.goals_for(key_a) or 0 for m in pool),
        "goals_b": sum(m.goals_for(key_b) or 0 for m in pool),
        "matches": [_match_dict(dataset, m) for m in pool[: max(1, limit)]],
        "competition": COMPETITION_DISPLAY.get(competition_key) if competition_key else None,
        "season": season,
    }


def team_stats(
    dataset: Dataset,
    team: str,
    *,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss record for a team, optionally filtered."""
    key = resolve_team(dataset, team)
    competition_key = resolve_competition(dataset, competition)
    if venue not in ("all", "home", "away"):
        raise QueryError("venue must be 'all', 'home' or 'away'.")
    pool = dataset.canonical_matches(competition_key, season)
    pool = [m for m in pool if m.involves(key)]
    if venue == "home":
        pool = [m for m in pool if m.home == key]
    elif venue == "away":
        pool = [m for m in pool if m.away == key]
    record = TeamRecord(team=key)
    for match in pool:
        record.add_match(match)
    unscored = sum(1 for m in pool if not m.is_scored)
    seasons = sorted({m.season for m in pool if m.season})
    return {
        "team": dataset.team_display(key),
        "venue": venue,
        "competition": COMPETITION_DISPLAY.get(competition_key) if competition_key else "all competitions",
        "season": season,
        "seasons_covered": seasons,
        "played": record.played,
        "wins": record.wins,
        "draws": record.draws,
        "losses": record.losses,
        "goals_for": record.goals_for,
        "goals_against": record.goals_against,
        "points": record.points,
        "win_rate": round(record.win_rate * 100, 1) if record.win_rate is not None else None,
        "unscored_matches": unscored,
        "matches_in_pool": len(pool),
    }


def best_records(
    dataset: Dataset,
    *,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "all",
    min_matches: int = 10,
    limit: int = 5,
) -> dict:
    """Rank teams by win rate over a filtered match pool."""
    competition_key = resolve_competition(dataset, competition)
    if venue not in ("all", "home", "away"):
        raise QueryError("venue must be 'all', 'home' or 'away'.")
    pool = dataset.canonical_matches(competition_key, season)
    if venue == "home":
        pool = [(m, m.home) for m in pool if m.is_scored]
    elif venue == "away":
        pool = [(m, m.away) for m in pool if m.is_scored]
    else:
        pool = [(m, m.home) for m in pool if m.is_scored] + [(m, m.away) for m in pool if m.is_scored]
    records: dict[str, TeamRecord] = {}
    for match, team in pool:
        records.setdefault(team, TeamRecord(team=team))
        records[team].add_match(match)
    qualified = [
        r for r in records.values()
        if r.played >= min_matches and r.win_rate is not None
    ]
    ranked = sorted(qualified, key=lambda r: (-r.win_rate, -(r.points / r.played), r.team))
    return {
        "venue": venue,
        "competition": COMPETITION_DISPLAY.get(competition_key) if competition_key else "all competitions",
        "season": season,
        "min_matches": min_matches,
        "records": [
            {
                "team": dataset.team_display(r.team),
                "played": r.played,
                "wins": r.wins,
                "draws": r.draws,
                "losses": r.losses,
                "goals_for": r.goals_for,
                "goals_against": r.goals_against,
                "win_rate": round(r.win_rate * 100, 1),
            }
            for r in ranked[: max(1, limit)]
        ],
    }


def team_competitions(dataset: Dataset, team: str) -> dict:
    """Competitions and seasons a team appears in across all files."""
    key = resolve_team(dataset, team)
    stats: dict[str, dict] = {}
    for match in dataset.deduped_matches:
        if not match.involves(key):
            continue
        comp = COMPETITION_DISPLAY.get(match.competition, match.competition)
        entry = stats.setdefault(comp, {"competition": comp, "matches": 0, "seasons": set()})
        entry["matches"] += 1
        if match.season:
            entry["seasons"].add(match.season)
    competitions = []
    for comp in sorted(stats):
        entry = stats[comp]
        seasons = sorted(entry["seasons"])
        competitions.append({
            "competition": comp,
            "matches": entry["matches"],
            "seasons": seasons,
            "first_season": seasons[0] if seasons else None,
            "last_season": seasons[-1] if seasons else None,
        })
    return {
        "team": dataset.team_display(key),
        "competitions": competitions,
        "total_matches": sum(c["matches"] for c in competitions),
    }


def search_players(
    dataset: Dataset,
    *,
    name: str | None = None,
    club: str | None = None,
    nationality: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 20,
) -> dict:
    """Search the FIFA player database by name, club, nationality, position."""
    club_key = resolve_team(dataset, club) if club else None
    positions = resolve_position(position) if position else ()
    needle = slug(name) if name else None
    result = []
    for player in dataset.players:
        if needle and needle not in slug(player.name):
            continue
        if club_key and player.club_key != club_key:
            continue
        if nationality and slug(nationality) not in slug(player.nationality):
            continue
        if positions and player.position not in positions:
            continue
        if min_overall is not None and (player.overall is None or player.overall < min_overall):
            continue
        if max_overall is not None and (player.overall is None or player.overall > max_overall):
            continue
        result.append(player)
    result.sort(key=lambda p: (-(p.overall or 0), p.name))
    total = len(result)
    return {
        "players": [_player_dict(dataset, p) for p in result[: max(1, limit)]],
        "total": total,
        "shown": min(len(result), max(1, limit)),
        "filters": {
            "name": name,
            "club": dataset.team_display(club_key) if club_key else None,
            "nationality": nationality,
            "position": position,
            "min_overall": min_overall,
            "max_overall": max_overall,
        },
    }


def _player_dict(dataset: Dataset, player) -> dict:
    return {
        "id": player.id,
        "name": player.name,
        "age": player.age,
        "nationality": player.nationality,
        "overall": player.overall,
        "potential": player.potential,
        "club": player.club,
        "position": player.position or None,
        "jersey": player.jersey,
        "height": player.height or None,
        "weight": player.weight or None,
    }


def top_players(
    dataset: Dataset,
    *,
    club: str | None = None,
    nationality: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> dict:
    """Highest-rated players matching the given filters."""
    result = search_players(
        dataset,
        club=club,
        nationality=nationality,
        position=position,
        limit=limit,
    )
    result["players"] = result["players"][: max(1, limit)]
    return result


def players_by_club(
    dataset: Dataset,
    *,
    nationality: str | None = "Brazil",
    only_brazilian_clubs: bool = True,
    limit: int = 15,
) -> dict:
    """Aggregate players per club (default: Brazilians at Brazilian clubs)."""
    nationality_key = slug(nationality) if nationality else None
    clubs: dict[str, list] = {}
    for player in dataset.players:
        if not player.club_key:
            continue
        if nationality_key and slug(player.nationality) != nationality_key:
            continue
        if only_brazilian_clubs and player.club_key not in dataset.brazilian_clubs:
            continue
        clubs.setdefault(player.club_key, []).append(player)
    entries = []
    for club_key, players in clubs.items():
        ratings = [p.overall for p in players if p.overall is not None]
        entries.append({
            "club": dataset.team_display(club_key),
            "players": len(players),
            "avg_overall": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "best_player": max(players, key=lambda p: p.overall or 0).name if players else None,
        })
    entries.sort(key=lambda e: (-e["players"], -e["avg_overall"] or 0, e["club"]))
    return {"nationality": nationality, "clubs": entries[: max(1, limit)], "total_clubs": len(entries)}


def standings(dataset: Dataset, competition: str = SERIE_A, season: int | None = None) -> dict:
    """Points table for a league competition, computed from match results."""
    competition_key = resolve_competition(dataset, competition)
    if COMPETITION_KIND.get(competition_key) != "league":
        raise QueryError(
            f"{COMPETITION_DISPLAY.get(competition_key)} is a knockout competition "
            f"and has no league table. Use the champion or bracket tools instead."
        )
    seasons = sorted({
        m.season for m in dataset.matches
        if m.competition == competition_key and m.season
    })
    if season is None:
        if not seasons:
            raise QueryError(f"No seasons found for {COMPETITION_DISPLAY[competition_key]}.")
        season = seasons[-1]
    if season not in seasons:
        raise QueryError(
            f"No data for {COMPETITION_DISPLAY[competition_key]} {season}. "
            f"Available seasons: {seasons[0]}-{seasons[-1]}."
        )
    table, meta = dataset.league_table(competition_key, season)
    rows = []
    relegated_zone = COMPETITION_KIND[competition_key] == "league" and competition_key in (SERIE_A, SERIE_B)
    for index, record in enumerate(table):
        rows.append({
            "rank": index + 1,
            "team": dataset.team_display(record.team),
            "played": record.played,
            "wins": record.wins,
            "draws": record.draws,
            "losses": record.losses,
            "goals_for": record.goals_for,
            "goals_against": record.goals_against,
            "goal_diff": record.goal_diff,
            "points": record.points,
            "champion": index == 0,
            "relegated": relegated_zone and index >= len(table) - RELEGATION_SLOTS,
        })
    return {
        "competition": COMPETITION_DISPLAY[competition_key],
        "season": season,
        "table": rows,
        "scored_matches": meta["scored_matches"],
        "total_matches": meta["total_matches"],
        "relegation_slots": RELEGATION_SLOTS if relegated_zone else 0,
        "available_seasons": seasons,
    }


def _aggregate_final(dataset: Dataset, finals: list[Match]) -> dict | None:
    if not finals:
        return None
    teams = {f.home for f in finals} | {f.away for f in finals}
    if len(teams) != 2:
        return None
    team_a, team_b = sorted(teams)
    goals_a = sum(m.goals_for(team_a) or 0 for m in finals if m.is_scored)
    goals_b = sum(m.goals_for(team_b) or 0 for m in finals if m.is_scored)
    if goals_a > goals_b:
        winner, method = team_a, "aggregate score"
    elif goals_b > goals_a:
        winner, method = team_b, "aggregate score"
    else:
        winner, method = None, "aggregate tied (decided on penalties, not in dataset)"
    return {
        "team_a": dataset.team_display(team_a),
        "team_b": dataset.team_display(team_b),
        "goals_a": goals_a,
        "goals_b": goals_b,
        "winner": dataset.team_display(winner) if winner else None,
        "method": method,
        "legs": [
            {
                "date": m.date.isoformat() if m.date else None,
                "home": dataset.team_display(m.home),
                "away": dataset.team_display(m.away),
                "score": f"{m.home_goals}-{m.away_goals}" if m.is_scored else "N/A",
            }
            for m in sorted(finals, key=lambda m: m.sort_key())
        ],
    }


def champion(dataset: Dataset, competition: str, season: int | None = None) -> dict:
    """Determine the champion of a competition and season from the data."""
    competition_key = resolve_competition(dataset, competition)
    seasons = sorted({
        m.season for m in dataset.matches
        if m.competition == competition_key and m.season
    })
    if season is None:
        if not seasons:
            raise QueryError(f"No seasons found for {COMPETITION_DISPLAY[competition_key]}.")
        season = seasons[-1]
    if season not in seasons:
        raise QueryError(
            f"No data for {COMPETITION_DISPLAY[competition_key]} {season}. "
            f"Available seasons: {seasons[0]}-{seasons[-1]}."
        )
    if COMPETITION_KIND.get(competition_key) == "league":
        table, meta = dataset.league_table(competition_key, season)
        if not table:
            return {"competition": COMPETITION_DISPLAY[competition_key], "season": season, "champion": None}
        winner = table[0]
        return {
            "competition": COMPETITION_DISPLAY[competition_key],
            "season": season,
            "champion": dataset.team_display(winner.team),
            "method": "top of the points table",
            "points": winner.points,
            "record": f"{winner.wins}W {winner.draws}D {winner.losses}L",
            "runner_up": dataset.team_display(table[1].team) if len(table) > 1 else None,
            "relegated": [dataset.team_display(r.team) for r in table[-RELEGATION_SLOTS:]]
            if competition_key in (SERIE_A, SERIE_B) else [],
            "scored_matches": meta["scored_matches"],
        }
    source, _ = dataset.canonical_source(competition_key, season)
    finals = [
        m for m in dataset.canonical_matches(competition_key, season)
        if m.stage == "final"
    ]
    final = _aggregate_final(dataset, finals)
    if final is None:
        late_rounds = [
            m for m in dataset.canonical_matches(competition_key, season)
            if m.stage in KNOCKOUT_STAGES
        ]
        return {
            "competition": COMPETITION_DISPLAY[competition_key],
            "season": season,
            "champion": None,
            "note": "Final not present in the dataset for this season.",
            "knockout_matches_available": len(late_rounds),
        }
    final.update({
        "competition": COMPETITION_DISPLAY[competition_key],
        "season": season,
        "champion": final["winner"],
    })
    return final


def bracket(dataset: Dataset, competition: str, season: int) -> dict:
    """Knockout bracket (round of 16 to final) for a cup competition."""
    competition_key = resolve_competition(dataset, competition)
    if COMPETITION_KIND.get(competition_key) != "cup":
        raise QueryError(
            f"{COMPETITION_DISPLAY.get(competition_key)} is a league competition; "
            f"use the standings tool instead."
        )
    pool = [
        m for m in dataset.canonical_matches(competition_key, season)
        if m.stage in KNOCKOUT_STAGES
    ]
    if not pool:
        return {
            "competition": COMPETITION_DISPLAY[competition_key],
            "season": season,
            "rounds": [],
            "note": "No knockout-stage matches in the dataset for this season.",
        }
    rounds = []
    for stage in KNOCKOUT_STAGES:
        stage_matches = [m for m in pool if m.stage == stage]
        if not stage_matches:
            continue
        ties: dict[frozenset, list[Match]] = {}
        for match in stage_matches:
            ties.setdefault(frozenset((match.home, match.away)), []).append(match)
        tie_list = []
        for pair, legs in ties.items():
            legs = sorted(legs, key=lambda m: m.sort_key())
            team_a, team_b = sorted(pair)
            goals_a = sum(m.goals_for(team_a) or 0 for m in legs if m.is_scored)
            goals_b = sum(m.goals_for(team_b) or 0 for m in legs if m.is_scored)
            if goals_a > goals_b:
                winner = team_a
            elif goals_b > goals_a:
                winner = team_b
            else:
                winner = None
            tie_list.append({
                "team_a": dataset.team_display(team_a),
                "team_b": dataset.team_display(team_b),
                "aggregate": f"{goals_a}-{goals_b}",
                "winner": dataset.team_display(winner) if winner else None,
                "legs": [
                    {
                        "date": m.date.isoformat() if m.date else None,
                        "home": dataset.team_display(m.home),
                        "away": dataset.team_display(m.away),
                        "score": f"{m.home_goals}-{m.away_goals}" if m.is_scored else "N/A",
                    }
                    for m in legs
                ],
            })
        tie_list.sort(key=lambda t: (t["team_a"], t["team_b"]))
        rounds.append({"stage": stage, "stage_display": STAGE_DISPLAY.get(stage, stage), "ties": tie_list})
    return {
        "competition": COMPETITION_DISPLAY[competition_key],
        "season": season,
        "rounds": rounds,
    }


def competition_overview(dataset: Dataset) -> dict:
    """List every competition with its seasons and match counts."""
    seasons = dataset.competition_seasons()
    competitions = []
    for comp in sorted(COMPETITION_DISPLAY, key=lambda c: COMPETITION_DISPLAY[c]):
        if comp not in seasons:
            continue
        season_counts = seasons[comp]
        ordered = sorted(s for s in season_counts if s is not None)
        competitions.append({
            "competition": COMPETITION_DISPLAY[comp],
            "kind": COMPETITION_KIND[comp],
            "matches": sum(season_counts.values()),
            "seasons": ordered,
            "first_season": ordered[0] if ordered else None,
            "last_season": ordered[-1] if ordered else None,
        })
    return {
        "competitions": competitions,
        "total_matches": sum(c["matches"] for c in competitions),
        "players": len(dataset.players),
        "teams": len(dataset.known_teams),
    }


def average_goals(
    dataset: Dataset,
    *,
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
) -> dict:
    """Average goals per match plus home/draw/away outcome rates."""
    competition_key = resolve_competition(dataset, competition)
    team_key_ = resolve_team(dataset, team) if team else None
    pool = dataset.canonical_matches(competition_key, season)
    if team_key_:
        pool = [m for m in pool if m.involves(team_key_)]
    scored = [m for m in pool if m.is_scored]
    total_goals = sum(m.home_goals + m.away_goals for m in scored)
    home_wins = sum(1 for m in scored if m.home_goals > m.away_goals)
    away_wins = sum(1 for m in scored if m.away_goals > m.home_goals)
    draws = len(scored) - home_wins - away_wins
    count = len(scored)
    return {
        "competition": COMPETITION_DISPLAY.get(competition_key) if competition_key else "all competitions",
        "season": season,
        "team": dataset.team_display(team_key_) if team_key_ else None,
        "matches": count,
        "avg_goals": round(total_goals / count, 2) if count else None,
        "avg_home_goals": round(sum(m.home_goals for m in scored) / count, 2) if count else None,
        "avg_away_goals": round(sum(m.away_goals for m in scored) / count, 2) if count else None,
        "home_win_rate": round(home_wins / count * 100, 1) if count else None,
        "draw_rate": round(draws / count * 100, 1) if count else None,
        "away_win_rate": round(away_wins / count * 100, 1) if count else None,
    }


def biggest_wins(
    dataset: Dataset,
    *,
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 5,
) -> dict:
    """Largest victory margins in the dataset."""
    competition_key = resolve_competition(dataset, competition)
    team_key_ = resolve_team(dataset, team) if team else None
    pool = dataset.canonical_matches(competition_key, season)
    if team_key_:
        pool = [m for m in pool if m.involves(team_key_)]
    scored = [m for m in pool if m.is_scored and m.date is not None]
    ranked = sorted(scored, key=lambda m: (-m.margin, -(m.home_goals + m.away_goals)))
    return {
        "competition": COMPETITION_DISPLAY.get(competition_key) if competition_key else "all competitions",
        "season": season,
        "team": dataset.team_display(team_key_) if team_key_ else None,
        "wins": [_match_dict(dataset, m) for m in ranked[: max(1, limit)]],
    }


def derbies(
    dataset: Dataset,
    *,
    season: int | None = None,
    team: str | None = None,
    limit: int = 30,
) -> dict:
    """Matches between traditional rivals (Fla-Flu, Gre-Nal, Majestoso...)."""
    team_key_ = resolve_team(dataset, team) if team else None
    pool = []
    for match in dataset.deduped_matches:
        pair = frozenset((match.home, match.away))
        name = DERBY_PAIRS.get(pair)
        if not name:
            continue
        if season is not None and match.season != season:
            continue
        if team_key_ and not match.involves(team_key_):
            continue
        pool.append((name, match))
    pool.sort(key=lambda item: item[1].sort_key(), reverse=True)
    total = len(pool)
    known = [
        {
            "derby": name,
            "teams": [dataset.team_display(a), dataset.team_display(b)],
        }
        for a, b, name in sorted(DERBIES, key=lambda d: d[2])
    ]
    return {
        "matches": [
            {**_match_dict(dataset, m), "derby": name} for name, m in pool[: max(1, limit)]
        ],
        "total": total,
        "season": season,
        "team": dataset.team_display(team_key_) if team_key_ else None,
        "known_derbies": known,
    }


def season_comparison(
    dataset: Dataset,
    competition: str,
    season_a: int,
    season_b: int,
) -> dict:
    """Compare two seasons of a competition (goals, home advantage, champion)."""
    competition_key = resolve_competition(dataset, competition)
    summaries = []
    for season in (season_a, season_b):
        goals = average_goals(dataset, competition=competition_key, season=season)
        summary = {
            "season": season,
            "matches": goals["matches"],
            "avg_goals": goals["avg_goals"],
            "home_win_rate": goals["home_win_rate"],
            "away_win_rate": goals["away_win_rate"],
            "draw_rate": goals["draw_rate"],
        }
        if COMPETITION_KIND.get(competition_key) == "league":
            table, meta = dataset.league_table(competition_key, season)
            if table:
                summary["champion"] = dataset.team_display(table[0].team)
                summary["champion_points"] = table[0].points
                summary["top_scorer_team"] = dataset.team_display(
                    max(table, key=lambda r: r.goals_for).team
                )
                summary["top_scorer_team_goals"] = max(r.goals_for for r in table)
        else:
            finals = [
                m for m in dataset.canonical_matches(competition_key, season)
                if m.stage == "final"
            ]
            final = _aggregate_final(dataset, finals)
            summary["champion"] = final["winner"] if final else None
        biggest = biggest_wins(dataset, competition=competition_key, season=season, limit=1)
        summary["biggest_win"] = biggest["wins"][0] if biggest["wins"] else None
        summaries.append(summary)
    return {
        "competition": COMPETITION_DISPLAY.get(competition_key) if competition_key else "all competitions",
        "seasons": summaries,
    }


def team_profile(dataset: Dataset, team: str, players_limit: int = 5) -> dict:
    """Combined match-history and player view of one team (cross-file)."""
    key = resolve_team(dataset, team)
    comps = team_competitions(dataset, key)
    players = top_players(dataset, club=key, limit=players_limit)
    overall = team_stats(dataset, key)
    return {
        "team": dataset.team_display(key),
        "record": {
            "played": overall["played"],
            "wins": overall["wins"],
            "draws": overall["draws"],
            "losses": overall["losses"],
            "goals_for": overall["goals_for"],
            "goals_against": overall["goals_against"],
            "win_rate": overall["win_rate"],
        },
        "competitions": comps["competitions"],
        "top_players": players["players"],
        "players_at_club": players["total"],
    }
