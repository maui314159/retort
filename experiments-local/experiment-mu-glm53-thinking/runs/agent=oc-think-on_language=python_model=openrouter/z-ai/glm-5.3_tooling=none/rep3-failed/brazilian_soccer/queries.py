"""Query and analytics functions powering the MCP tools.

Every function takes the loaded :class:`~brazilian_soccer.loader.SoccerData`
as its first argument and returns plain JSON-serialisable data structures
(dicts / lists / str / int / float / None) so they can be returned directly
from MCP tools.
"""

from __future__ import annotations

from datetime import date

from .loader import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    COMPETITION_ALIASES,
    LIBERTADORES,
    SoccerData,
    parse_date,
)
from .models import Match
from .normalize import ResolveResult, TeamNotFound, strip_accents

LEAGUE_COMPETITIONS = (BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C)
CUP_COMPETITIONS = (COPA_DO_BRASIL, LIBERTADORES)

#: Traditional Brazilian derby pairings (canonical team ids).
DERBIES: list[tuple[str, str, str]] = [
    ("Fla-Flu", "flamengo-rj", "fluminense-rj"),
    ("Clássico dos Milhões", "flamengo-rj", "vasco-da-gama-rj"),
    ("Clássico Vovô", "botafogo-rj", "vasco-da-gama-rj"),
    ("Choque-Rei", "corinthians-sp", "sao-paulo-sp"),
    ("Majestoso", "corinthians-sp", "palmeiras-sp"),
    ("Clássico da Saudade", "palmeiras-sp", "santos-sp"),
    ("Gre-Nal", "gremio-rs", "internacional-rs"),
    ("Atletiba", "athletico-pr", "coritiba-pr"),
    ("Ba-Vi", "bahia-ba", "vitoria-ba"),
    ("Re-Pa", "remo-pa", "paysandu-pa"),
    ("Clássico-Rei", "ceara-ce", "fortaleza-ce"),
    ("Clássico dos Clássicos", "sport-pe", "santa-cruz-pe"),
    ("Clássico das Multidões", "santa-cruz-pe", "nautico-pe"),
]


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #


class QueryError(ValueError):
    """Raised for invalid query parameters (unknown team/competition/...)."""


def resolve_competition(name: str | None) -> str | None:
    """Resolve a user-facing competition name to its canonical form."""
    if name is None or not name.strip():
        return None
    key = strip_accents(name).lower().strip()
    if key in COMPETITION_ALIASES:
        return COMPETITION_ALIASES[key]
    canonical = {strip_accents(c).lower(): c for c in
                 (BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C, COPA_DO_BRASIL, LIBERTADORES)}
    if key in canonical:
        return canonical[key]
    known = ", ".join(sorted({BRASILEIRAO_A, BRASILEIRAO_B, BRASILEIRAO_C, COPA_DO_BRASIL, LIBERTADORES}))
    raise QueryError(f"Unknown competition {name!r}. Known competitions: {known}")


def _resolve_team(data: SoccerData, name: str) -> ResolveResult:
    try:
        return data.teams.resolve(name)
    except TeamNotFound as exc:
        suggestions = data.teams.search(name, limit=5)
        names = ", ".join(s["name"] for s in suggestions) or "none"
        raise QueryError(f"Unknown team {name!r}. Did you mean: {names}?") from exc


def _match_dict(data: SoccerData, match: Match) -> dict:
    out = match.to_dict(data.display_team)
    if match.home_shots is not None:
        out["stats"] = {
            "home_shots": match.home_shots,
            "away_shots": match.away_shots,
            "home_corners": match.home_corners,
            "away_corners": match.away_corners,
            "home_attacks": match.home_attacks,
            "away_attacks": match.away_attacks,
        }
    return out


def _parse_date_param(value: str | None, label: str) -> date | None:
    if value is None or not str(value).strip():
        return None
    parsed = parse_date(str(value))
    if parsed is None:
        raise QueryError(f"Invalid {label} {value!r}; expected ISO format YYYY-MM-DD")
    return parsed


def _sorted_matches(matches: list[Match]) -> list[Match]:
    return sorted(matches, key=lambda m: (m.date is None, m.date or date.min), reverse=False)


def _wins_draws_losses(matches: list[Match], team: str) -> dict:
    wins = draws = losses = 0
    gf = ga = 0
    for m in matches:
        if not m.has_result:
            continue
        home = m.home == team
        own, opp = (m.home_goals, m.away_goals) if home else (m.away_goals, m.home_goals)
        gf += own
        ga += opp
        if own > opp:
            wins += 1
        elif own < opp:
            losses += 1
        else:
            draws += 1
    played = wins + draws + losses
    return {
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": 3 * wins + draws,
        "win_rate": round(wins / played * 100, 1) if played else 0.0,
    }


# --------------------------------------------------------------------------- #
# Match queries
# --------------------------------------------------------------------------- #


def search_matches(
    data: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    limit: int = 20,
) -> dict:
    """Find matches by team, opponent, competition, season, date range or stage."""
    resolved: dict = {}
    team_id = opponent_id = None
    if team:
        res = _resolve_team(data, team)
        team_id = res.canonical
        resolved["team"] = {"id": res.canonical, "name": res.display}
        if res.alternatives:
            resolved["team"]["alternatives_considered"] = res.alternatives
    if opponent:
        res = _resolve_team(data, opponent)
        opponent_id = res.canonical
        resolved["opponent"] = {"id": res.canonical, "name": res.display}
    comp = resolve_competition(competition)
    if competition and comp is None:
        raise QueryError(f"Unknown competition {competition!r}")
    d_from = _parse_date_param(date_from, "date_from")
    d_to = _parse_date_param(date_to, "date_to")

    result = []
    for m in data.matches_for(comp):
        if team_id and team_id not in (m.home, m.away):
            continue
        if opponent_id and opponent_id not in (m.home, m.away):
            continue
        if season is not None and m.season != season:
            continue
        if d_from and (m.date is None or m.date < d_from):
            continue
        if d_to and (m.date is None or m.date > d_to):
            continue
        if stage and m.stage and strip_accents(m.stage).lower() != strip_accents(stage).lower():
            continue
        if stage and not m.stage:
            continue
        result.append(m)

    result = sorted(
        result, key=lambda m: (m.date is None, m.date or date.min), reverse=True
    )
    total = len(result)
    limit = max(0, min(int(limit), 200))
    return {
        "total": total,
        "count": min(total, limit),
        "truncated": total > limit,
        "filters": {
            "competition": comp,
            "season": season,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "stage": stage,
        },
        **resolved,
        "matches": [_match_dict(data, m) for m in result[:limit]],
    }


def head_to_head(
    data: SoccerData,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    limit: int = 20,
) -> dict:
    """All matches between two teams plus the win/draw/loss summary."""
    res_a = _resolve_team(data, team_a)
    res_b = _resolve_team(data, team_b)
    comp = resolve_competition(competition)

    matches = [
        m
        for m in data.matches_for(comp)
        if res_a.canonical in (m.home, m.away) and res_b.canonical in (m.home, m.away)
    ]
    matches = _sorted_matches(matches)

    a_stats = _wins_draws_losses(matches, res_a.canonical)
    return {
        "team_a": {"id": res_a.canonical, "name": res_a.display},
        "team_b": {"id": res_b.canonical, "name": res_b.display},
        "competition": comp,
        "total_matches": a_stats["matches"],
        "team_a_record": {k: a_stats[k] for k in ("wins", "draws", "losses", "goals_for", "goals_against")},
        "team_b_record": {
            "wins": a_stats["losses"],
            "draws": a_stats["draws"],
            "losses": a_stats["wins"],
            "goals_for": a_stats["goals_against"],
            "goals_against": a_stats["goals_for"],
        },
        "matches": [_match_dict(data, m) for m in matches[-limit:]],
    }


def last_meeting(
    data: SoccerData,
    team_a: str,
    team_b: str,
    competition: str | None = None,
) -> dict:
    """The most recent match between two teams."""
    res_a = _resolve_team(data, team_a)
    res_b = _resolve_team(data, team_b)
    comp = resolve_competition(competition)

    matches = [
        m
        for m in data.matches_for(comp)
        if res_a.canonical in (m.home, m.away) and res_b.canonical in (m.home, m.away)
    ]
    if not matches:
        return {
            "team_a": res_a.display,
            "team_b": res_b.display,
            "competition": comp,
            "last_meeting": None,
        }
    latest = max(matches, key=lambda m: (m.date is not None, m.date or date.min))
    return {
        "team_a": res_a.display,
        "team_b": res_b.display,
        "competition": comp,
        "last_meeting": _match_dict(data, latest),
    }


# --------------------------------------------------------------------------- #
# Team queries
# --------------------------------------------------------------------------- #


def team_record(
    data: SoccerData,
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "all",
) -> dict:
    """Win/draw/loss record, goals and streaks for a team."""
    if venue not in ("all", "home", "away"):
        raise QueryError("venue must be 'all', 'home' or 'away'")
    res = _resolve_team(data, team)
    comp = resolve_competition(competition)

    matches = [m for m in data.matches_for(comp) if res.canonical in (m.home, m.away)]
    if season is not None:
        matches = [m for m in matches if m.season == season]
    if venue == "home":
        matches = [m for m in matches if m.home == res.canonical]
    elif venue == "away":
        matches = [m for m in matches if m.away == res.canonical]

    record = _wins_draws_losses(matches, res.canonical)
    biggest_win = None
    for m in matches:
        if not m.has_result or m.home == m.away:
            continue
        if m.home == res.canonical and m.home_goals > m.away_goals:
            margin = m.home_goals - m.away_goals
        elif m.away == res.canonical and m.away_goals > m.home_goals:
            margin = m.away_goals - m.home_goals
        else:
            continue
        if biggest_win is None or margin > biggest_win["margin"]:
            biggest_win = {"margin": margin, "match": _match_dict(data, m)}

    return {
        "team": {"id": res.canonical, "name": res.display},
        "competition": comp,
        "season": season,
        "venue": venue,
        **record,
        "biggest_win": biggest_win,
    }


def team_profile(data: SoccerData, team: str) -> dict:
    """Everything about one team: record, per-competition splits and squad."""
    res = _resolve_team(data, team)
    comp = None
    matches = [m for m in data.matches if res.canonical in (m.home, m.away)]

    overall = _wins_draws_losses(matches, res.canonical)
    by_competition = []
    for competition_name in data.competitions():
        comp_matches = [m for m in data.matches_for(competition_name) if res.canonical in (m.home, m.away)]
        if not comp_matches:
            continue
        stats = _wins_draws_losses(comp_matches, res.canonical)
        seasons = sorted({m.season for m in comp_matches if m.season})
        by_competition.append(
            {
                "competition": competition_name,
                "seasons": [seasons[0], seasons[-1]] if seasons else [],
                **stats,
            }
        )

    squad = [
        p.to_dict()
        for p in data.players
        if data.club_of(p) == res.canonical
    ]
    squad.sort(key=lambda p: -p["overall"])

    return {
        "team": {"id": res.canonical, "name": res.display},
        "total_matches": overall["matches"],
        "overall_record": {k: overall[k] for k in ("wins", "draws", "losses", "goals_for", "goals_against")},
        "by_competition": by_competition,
        "players_in_fifa_dataset": {
            "count": len(squad),
            "top_rated": squad[:10],
        },
    }


def search_teams(data: SoccerData, query: str, limit: int = 10) -> dict:
    """Search canonical team names; helps disambiguate club name spellings."""
    results = data.teams.search(query, limit=limit)
    return {"query": query, "teams": results}


# --------------------------------------------------------------------------- #
# Player queries
# --------------------------------------------------------------------------- #


def _player_matches_name(player, name: str) -> bool:
    needle = strip_accents(name).lower()
    return needle in strip_accents(player.name).lower()


def search_players(
    data: SoccerData,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    order_by: str = "overall",
    limit: int = 20,
) -> dict:
    """Filter FIFA players by name, nationality, club, position and rating."""
    club_id = None
    resolved_club = None
    if club:
        try:
            res = data.teams.resolve(club)
            club_id = res.canonical
            resolved_club = {"id": res.canonical, "name": res.display}
        except TeamNotFound:
            club_id = f"substring:{strip_accents(club).lower()}"
            resolved_club = {"substring_match": club}

    if nationality:
        nat_key = strip_accents(nationality).lower()
    if position:
        pos_key = strip_accents(position).lower()

    result = []
    for p in data.players:
        if name and not _player_matches_name(p, name):
            continue
        if nationality and strip_accents(p.nationality).lower() != nat_key:
            continue
        if position and strip_accents(p.position or "").lower() != pos_key:
            continue
        if min_overall is not None and p.overall < min_overall:
            continue
        if max_overall is not None and p.overall > max_overall:
            continue
        if club:
            if isinstance(club_id, str) and club_id.startswith("substring:"):
                if club_id[len("substring:") :] not in strip_accents(p.club).lower():
                    continue
            elif data.club_of(p) != club_id:
                continue
        result.append(p)

    reverse = order_by in ("overall", "potential", "age")
    if order_by not in ("overall", "potential", "age", "name"):
        raise QueryError("order_by must be one of: overall, potential, age, name")
    if order_by == "name":
        result.sort(key=lambda p: strip_accents(p.name).lower())
    else:
        result.sort(key=lambda p: (-(getattr(p, order_by) or 0), strip_accents(p.name).lower()))

    total = len(result)
    limit = max(0, min(int(limit), 200))
    payload = {
        "total": total,
        "count": min(total, limit),
        "truncated": total > limit,
        **({"club_resolved": resolved_club} if resolved_club else {}),
        "players": [p.to_dict() for p in result[:limit]],
    }
    return payload


def player_profile(data: SoccerData, name: str) -> dict:
    """Full FIFA profile for a player (exact name match preferred)."""
    exact = [p for p in data.players if strip_accents(p.name).lower() == strip_accents(name).lower()]
    if exact:
        players = exact
    else:
        players = [p for p in data.players if _player_matches_name(p, name)]
    if not players:
        raise QueryError(f"No player matching {name!r} in the FIFA dataset")
    if len(players) == 1:
        return players[0].to_dict()
    players.sort(key=lambda p: -p.overall)
    return {
        "multiple_matches": True,
        "total": len(players),
        "players": [p.to_dict() for p in players[:20]],
    }


# --------------------------------------------------------------------------- #
# Competition queries
# --------------------------------------------------------------------------- #


def _standings(data: SoccerData, competition: str, season: int) -> list[dict]:
    table: dict[str, dict] = {}
    for m in data.matches_for(competition):
        if m.season != season or not m.has_result or m.home == m.away:
            continue
        for side, own, opp in ((m.home, m.home_goals, m.away_goals), (m.away, m.away_goals, m.home_goals)):
            row = table.setdefault(
                side,
                {"team": side, "matches": 0, "wins": 0, "draws": 0, "losses": 0,
                 "goals_for": 0, "goals_against": 0},
            )
            row["matches"] += 1
            row["goals_for"] += own
            row["goals_against"] += opp
            if own > opp:
                row["wins"] += 1
            elif own < opp:
                row["losses"] += 1
            else:
                row["draws"] += 1

    rows = []
    for row in table.values():
        gd = row["goals_for"] - row["goals_against"]
        rows.append(
            {
                "team": data.display_team(row["team"]),
                "matches": row["matches"],
                "wins": row["wins"],
                "draws": row["draws"],
                "losses": row["losses"],
                "goals_for": row["goals_for"],
                "goals_against": row["goals_against"],
                "goal_difference": gd,
                "points": 3 * row["wins"] + row["draws"],
            }
        )
    rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_difference"], -r["goals_for"], r["team"]))
    for i, row in enumerate(rows, 1):
        row["position"] = i
    return rows


def standings(data: SoccerData, competition: str, season: int) -> dict:
    """League table computed from match results."""
    comp = resolve_competition(competition)
    if comp is None:
        raise QueryError("competition is required")
    if comp not in LEAGUE_COMPETITIONS:
        raise QueryError(
            f"Standings are only computed for league competitions "
            f"({', '.join(LEAGUE_COMPETITIONS)}); {comp!r} is a cup"
        )
    seasons = data.seasons_for(comp)
    if season not in seasons:
        raise QueryError(
            f"No {comp} data for season {season}. Available seasons: {seasons}"
        )

    rows = _standings(data, comp, season)
    n_teams = len(rows)
    expected_matches = n_teams * (n_teams - 1)
    actual = sum(r["matches"] for r in rows) // 2
    note = None
    if actual < expected_matches:
        note = (
            f"Partial data: {actual} of ~{expected_matches} expected matches; "
            "standings may be incomplete"
        )
    return {
        "competition": comp,
        "season": season,
        "note": note,
        "champion": rows[0]["team"] if rows else None,
        "table": rows,
    }


def _cup_final_matches(data: SoccerData, competition: str, season: int) -> list[Match]:
    matches = data.matches_for(competition)
    if competition == LIBERTADORES:
        return [m for m in matches if m.season == season and (m.stage or "").lower() == "final"]
    # Copa do Brasil: the highest-numbered round of the season is the final.
    season_matches = [m for m in matches if m.season == season]
    if not season_matches:
        return []
    def _round_no(m: Match) -> int:
        try:
            return int((m.stage or "0").split()[-1])
        except ValueError:
            return 0
    max_round = max(_round_no(m) for m in season_matches)
    return [m for m in season_matches if _round_no(m) == max_round]


def _aggregate_finals(data: SoccerData, finals: list[Match]) -> list[dict]:
    """Sum two-legged finals and decide the winner where the data allows."""
    pairs: dict[tuple, list[Match]] = {}
    for m in finals:
        if not m.has_result:
            continue
        key = tuple(sorted((m.home, m.away)))
        pairs.setdefault(key, []).append(m)
    out = []
    for (a, b), legs in pairs.items():
        goals = {a: 0, b: 0}
        for leg in legs:
            goals[leg.home] += leg.home_goals or 0
            goals[leg.away] += leg.away_goals or 0
        if goals[a] > goals[b]:
            winner = data.display_team(a)
        elif goals[b] > goals[a]:
            winner = data.display_team(b)
        else:
            winner = None  # tied on aggregate; penalties not recorded
        out.append(
            {
                "team_a": data.display_team(a),
                "team_b": data.display_team(b),
                "aggregate_score": f"{goals[a]}-{goals[b]}",
                "winner": winner,
                "note": None if winner else "Tied on aggregate; penalty shootout not recorded in dataset",
                "legs": [_match_dict(data, m) for m in _sorted_matches(legs)],
            }
        )
    return out


def finals(data: SoccerData, competition: str, season: int | None = None) -> dict:
    """Final(s) of a cup competition for one or all seasons."""
    comp = resolve_competition(competition)
    if comp is None:
        raise QueryError("competition is required")
    if comp not in CUP_COMPETITIONS:
        raise QueryError(
            f"Finals are tracked for cup competitions ({', '.join(CUP_COMPETITIONS)}); "
            "for league winners use the standings/champion tools"
        )
    seasons = [season] if season else data.seasons_for(comp)
    if season is not None and season not in data.seasons_for(comp):
        raise QueryError(f"No {comp} data for season {season}")
    result = {}
    for s in seasons:
        legs = _cup_final_matches(data, comp, s)
        if legs:
            result[s] = _aggregate_finals(data, legs)
    return {
        "competition": comp,
        "finals_by_season": result,
    }


def champion(data: SoccerData, competition: str, season: int) -> dict:
    """Champion of a league (from standings) or cup (from the final)."""
    comp = resolve_competition(competition)
    if comp is None:
        raise QueryError("competition is required")
    seasons = data.seasons_for(comp)
    if season not in seasons:
        raise QueryError(f"No {comp} data for season {season}. Available seasons: {seasons}")

    if comp in LEAGUE_COMPETITIONS:
        table = _standings(data, comp, season)
        top = table[0] if table else None
        n_teams = len(table)
        expected = n_teams * (n_teams - 1)
        actual = sum(r["matches"] for r in table) // 2
        return {
            "competition": comp,
            "season": season,
            "champion": top["team"] if top else None,
            "record": (
                {k: top[k] for k in ("matches", "wins", "draws", "losses", "goals_for",
                                     "goals_against", "goal_difference", "points")}
                if top else None
            ),
            "note": None if actual >= expected else
            f"Partial data: {actual} of ~{expected} expected matches",
        }
    legs = _cup_final_matches(data, comp, season)
    if not legs:
        return {"competition": comp, "season": season, "champion": None,
                "note": "No final found for this season in the dataset"}
    aggregated = _aggregate_finals(data, legs)
    winners = [f["winner"] for f in aggregated if f["winner"]]
    return {
        "competition": comp,
        "season": season,
        "champion": winners[0] if len(winners) == 1 else (winners or None),
        "final": aggregated[0] if aggregated else None,
    }


def relegated(data: SoccerData, competition: str, season: int, count: int = 4) -> dict:
    """Bottom teams of a league season."""
    comp = resolve_competition(competition)
    if comp is None or comp not in LEAGUE_COMPETITIONS:
        raise QueryError("Relegation applies to league competitions only")
    seasons = data.seasons_for(comp)
    if season not in seasons:
        raise QueryError(f"No {comp} data for season {season}. Available seasons: {seasons}")
    table = _standings(data, comp, season)
    bottom = table[-count:] if count else []
    return {
        "competition": comp,
        "season": season,
        "relegated": [
            {k: row[k] for k in ("position", "team", "points", "wins", "draws", "losses")}
            for row in reversed(bottom)
        ],
    }


def list_competitions(data: SoccerData) -> dict:
    """Competitions available, their seasons and source files."""
    out = []
    for competition in data.competitions():
        matches = data.matches_for(competition)
        seasons = data.seasons_for(competition)
        sources = sorted({m.source for m in matches})
        out.append(
            {
                "competition": competition,
                "seasons": seasons,
                "season_range": [seasons[0], seasons[-1]] if seasons else [],
                "matches": len(matches),
                "sources": sources,
            }
        )
    return {
        "competitions": out,
        "players_dataset": {"name": "FIFA player database", "players": len(data.players)},
    }


# --------------------------------------------------------------------------- #
# Statistical analysis
# --------------------------------------------------------------------------- #


def league_averages(data: SoccerData, competition: str | None = None, season: int | None = None) -> dict:
    """Average goals and home/away/draw rates for a set of matches."""
    comp = resolve_competition(competition)
    matches = [m for m in data.matches_for(comp) if m.has_result and m.home != m.away]
    if season is not None:
        matches = [m for m in matches if m.season == season]
    if not matches:
        return {"competition": comp, "season": season, "matches": 0,
                "note": "No matches found for these filters"}

    total_goals = sum(m.total_goals or 0 for m in matches)
    home_wins = sum(1 for m in matches if m.home_goals > m.away_goals)
    away_wins = sum(1 for m in matches if m.away_goals > m.home_goals)
    draws = len(matches) - home_wins - away_wins
    n = len(matches)
    return {
        "competition": comp,
        "season": season,
        "matches": n,
        "total_goals": total_goals,
        "average_goals_per_match": round(total_goals / n, 2),
        "average_home_goals": round(sum(m.home_goals for m in matches) / n, 2),
        "average_away_goals": round(sum(m.away_goals for m in matches) / n, 2),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / n * 100, 1),
        "away_win_rate": round(away_wins / n * 100, 1),
        "draw_rate": round(draws / n * 100, 1),
    }


def biggest_wins(
    data: SoccerData,
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 10,
) -> dict:
    """Largest winning margins in the dataset."""
    comp = resolve_competition(competition)
    team_id = None
    if team:
        res = _resolve_team(data, team)
        team_id = res.canonical
    candidates = [
        m
        for m in data.matches_for(comp)
        if m.has_result and m.home != m.away and m.goal_margin
    ]
    if season is not None:
        candidates = [m for m in candidates if m.season == season]
    if team_id:
        candidates = [m for m in candidates if team_id in (m.home, m.away)]
    candidates.sort(key=lambda m: (-(m.goal_margin or 0), -(m.total_goals or 0)))
    limit = max(1, min(int(limit), 50))
    return {
        "competition": comp,
        "season": season,
        "count": min(len(candidates), limit),
        "biggest_wins": [
            {**_match_dict(data, m), "margin": m.goal_margin}
            for m in candidates[:limit]
        ],
    }


def best_records(
    data: SoccerData,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "all",
    min_matches: int = 10,
    limit: int = 10,
) -> dict:
    """Rank teams by win rate (overall, home-only or away-only)."""
    if venue not in ("all", "home", "away"):
        raise QueryError("venue must be 'all', 'home' or 'away'")
    comp = resolve_competition(competition)
    matches = [m for m in data.matches_for(comp) if m.has_result and m.home != m.away]
    if season is not None:
        matches = [m for m in matches if m.season == season]

    stats: dict[str, dict] = {}
    for m in matches:
        if venue == "home":
            pairs = [(m.home, m.home_goals, m.away_goals)]
        elif venue == "away":
            pairs = [(m.away, m.away_goals, m.home_goals)]
        else:
            pairs = [
                (m.home, m.home_goals, m.away_goals),
                (m.away, m.away_goals, m.home_goals),
            ]
        for team_id, own, opp in pairs:
            row = stats.setdefault(team_id, {"team": team_id, "matches": 0, "wins": 0, "draws": 0, "losses": 0})
            row["matches"] += 1
            if own > opp:
                row["wins"] += 1
            elif own < opp:
                row["losses"] += 1
            else:
                row["draws"] += 1

    ranked = [row for row in stats.values() if row["matches"] >= min_matches]
    for row in ranked:
        row["win_rate"] = round(row["wins"] / row["matches"] * 100, 1)
    ranked.sort(key=lambda r: (-r["win_rate"], -r["matches"]))
    limit = max(1, min(int(limit), 50))
    for row in ranked:
        row["team"] = data.display_team(row["team"])
    return {
        "competition": comp,
        "season": season,
        "venue": venue,
        "min_matches": min_matches,
        "count": min(len(ranked), limit),
        "best_records": ranked[:limit],
    }


def derbies(data: SoccerData, season: int | None = None, competition: str | None = None) -> dict:
    """Matches between traditional rival clubs."""
    comp = resolve_competition(competition)
    out = []
    for derby_name, team_a, team_b in DERBIES:
        if team_a not in data.teams or team_b not in data.teams:
            continue
        matches = [
            m
            for m in data.matches_for(comp)
            if team_a in (m.home, m.away) and team_b in (m.home, m.away)
        ]
        if season is not None:
            matches = [m for m in matches if m.season == season]
        if not matches:
            continue
        out.append(
            {
                "derby": derby_name,
                "teams": [data.display_team(team_a), data.display_team(team_b)],
                "total_matches": len(matches),
                "matches": [_match_dict(data, m) for m in _sorted_matches(matches)[-10:]],
            }
        )
    return {"season": season, "competition": comp, "derbies": out}
