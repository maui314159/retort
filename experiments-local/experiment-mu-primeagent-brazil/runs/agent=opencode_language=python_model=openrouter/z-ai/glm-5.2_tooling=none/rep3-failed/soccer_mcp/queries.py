"""
Context
=======
Brazilian Soccer MCP Server - query layer.

Part of the ``soccer_mcp`` package.  Pure-Python functions that answer the
five required query categories described in TASK.md:

    1. Match queries      - find_matches, head_to_head
    2. Team queries       - team_stats, list_teams
    3. Player queries     - search_players, team_players
    4. Competition queries- standings, champion, relegated, list_competitions
    5. Statistical analysis- statistics, biggest_wins, match_stats

Every public function takes plain Python arguments and returns JSON-serialisable
dicts / lists so they can be exposed directly as MCP tools.  A team name given
by the caller is resolved to a canonical key through the shared
:class:`soccer_mcp.normalize.TeamNormalizer`; team name variations
("Palmeiras-SP", "Palmeiras", "Sao Paulo-SP" vs "Sao Paulo") are therefore
matched consistently across all six datasets (see data_loader.py for the
source-priority merge that prevents double counting).

All match-based aggregates operate on the source-priority-selected ``matches``
collection (one clean record per real-world match) unless noted otherwise.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .data_loader import (
    COMP_BRASILEIRAO_A,
    COMP_BRASILEIRAO_B,
    COMP_COPA_BRASIL,
    COMP_LIBERTADORES,
    SoccerData,
    get_data,
    resolve_competition,
)

__all__ = [
    "find_matches",
    "head_to_head",
    "team_stats",
    "list_teams",
    "search_players",
    "team_players",
    "standings",
    "champion",
    "relegated",
    "list_competitions",
    "statistics",
    "biggest_wins",
    "match_stats",
    "resolve_team",
]

_LEAGUE_COMPETITIONS = {COMP_BRASILEIRAO_A, COMP_BRASILEIRAO_B}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _data() -> SoccerData:
    return get_data()


def resolve_team(name: str) -> Optional[str]:
    """Resolve a user-supplied team/club name to a canonical key."""
    if not name:
        return None
    return _data().normalizer.canonical(name)


def _display(key: str) -> str:
    return _data().team_display.get(key) or _data().normalizer.display(key) or key


def _maybe_date_in_range(date: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> bool:
    if date is None:
        # Unknown dates only pass when no range was specified.
        return date_from is None and date_to is None
    if date_from and date < date_from:
        return False
    if date_to and date > date_to:
        return False
    return True


def _competition_filter(competition: Optional[str]) -> Optional[str]:
    return resolve_competition(competition)


def _match_to_dict(m) -> dict:
    out = {
        "date": m.date,
        "season": m.season,
        "competition": m.competition,
        "round": m.round_or_stage,
        "home_team": m.home_display,
        "away_team": m.away_display,
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "score": (
            f"{m.home_goals}-{m.away_goals}"
            if m.home_goals is not None and m.away_goals is not None
            else None
        ),
        "source": m.source,
    }
    return out


def _sort_matches(matches: list, limit: Optional[int]) -> list:
    ordered = sorted(matches, key=lambda m: (m.date or "", m.competition))
    if limit is not None:
        ordered = ordered[:limit]
    return ordered


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    stage: Optional[str] = None,
    venue: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Find matches matching the given criteria.

    ``venue`` may be "home", "away" or "either" (default) for ``team``.
    Dates are ISO ``YYYY-MM-DD``; ``date_from``/``date_to`` are inclusive.
    """
    data = _data()
    comp = _competition_filter(competition)
    team_key = resolve_team(team) if team else None
    opp_key = resolve_team(opponent) if opponent else None
    if venue:
        venue = venue.lower()
        if venue not in {"home", "away", "either", "any"}:
            venue = "either"
    venue = venue or "either"
    if venue == "any":
        venue = "either"

    results = []
    for m in data.matches:
        if comp and m.competition != comp:
            continue
        if season and m.season != str(season):
            continue
        if not _maybe_date_in_range(m.date, date_from, date_to):
            continue
        if stage:
            rs = (m.round_or_stage or "").lower()
            if stage.lower() not in rs:
                continue
        if team_key:
            if venue == "home":
                if m.home_team != team_key:
                    continue
                if opp_key and m.away_team != opp_key:
                    continue
            elif venue == "away":
                if m.away_team != team_key:
                    continue
                if opp_key and m.home_team != opp_key:
                    continue
            else:  # either
                if m.home_team == team_key:
                    if opp_key and m.away_team != opp_key:
                        continue
                elif m.away_team == team_key:
                    if opp_key and m.home_team != opp_key:
                        continue
                else:
                    continue
        elif opp_key:
            if m.home_team != opp_key and m.away_team != opp_key:
                continue
        results.append(m)

    ordered = _sort_matches(results, limit)
    return [_match_to_dict(m) for m in ordered]


def head_to_head(
    team_a: str,
    team_b: str,
    competition: Optional[str] = None,
    limit: int = 100,
) -> dict:
    """Return the head-to-head record between two teams."""
    data = _data()
    a_key = resolve_team(team_a)
    b_key = resolve_team(team_b)
    comp = _competition_filter(competition)

    matches = []
    a_wins = b_wins = draws = a_goals = b_goals = 0
    for m in data.matches:
        if comp and m.competition != comp:
            continue
        if {m.home_team, m.away_team} != {a_key, b_key}:
            continue
        if m.home_goals is None or m.away_goals is None:
            continue
        matches.append(m)
        # Determine each team's goals.
        if m.home_team == a_key:
            ag, bg = m.home_goals, m.away_goals
        else:
            ag, bg = m.away_goals, m.home_goals
        a_goals += ag
        b_goals += bg
        if ag > bg:
            a_wins += 1
        elif bg > ag:
            b_wins += 1
        else:
            draws += 1

    ordered = _sort_matches(matches, limit)
    return {
        "team_a": _display(a_key),
        "team_b": _display(b_key),
        "matches_played": len(matches),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "matches": [_match_to_dict(m) for m in ordered],
    }


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------
def _empty_record() -> dict:
    return {"played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0}


def team_stats(
    team: str,
    season: Optional[str] = None,
    competition: Optional[str] = None,
    venue: Optional[str] = None,
) -> dict:
    """Return win/draw/loss and goal records for a team, optionally split by venue."""
    data = _data()
    key = resolve_team(team)
    comp = _competition_filter(competition)
    if season:
        season = str(season)
    if venue:
        venue = venue.lower()
        if venue not in {"home", "away", "overall", "either", "any"}:
            venue = None

    overall = _empty_record()
    home = _empty_record()
    away = _empty_record()
    by_competition: dict[str, dict] = defaultdict(_empty_record)
    competitions_played: set = set()

    for m in data.matches:
        if comp and m.competition != comp:
            continue
        if season and m.season != season:
            continue
        if m.home_goals is None or m.away_goals is None:
            continue
        is_home = m.home_team == key
        is_away = m.away_team == key
        if not is_home and not is_away:
            continue
        competitions_played.add(m.competition)
        gf = m.home_goals if is_home else m.away_goals
        ga = m.away_goals if is_home else m.home_goals
        win = gf > ga
        draw = gf == ga
        # venue bucket
        if is_home:
            bucket = home
        else:
            bucket = away
        # venue filter (restrict which venue counts toward `overall`)
        if venue in {"home", "away"} and venue != ("home" if is_home else "away"):
            continue
        for rec in (overall, bucket, by_competition[m.competition]):
            rec["played"] += 1
            rec["goals_for"] += gf
            rec["goals_against"] += ga
            if win:
                rec["wins"] += 1
            elif draw:
                rec["draws"] += 1
            else:
                rec["losses"] += 1

    def _rate(rec):
        return round(rec["wins"] / rec["played"], 4) if rec["played"] else None

    return {
        "team": _display(key),
        "season": season,
        "competition": comp,
        "overall": {**overall, "win_rate": _rate(overall)},
        "home": {**home, "win_rate": _rate(home)},
        "away": {**away, "win_rate": _rate(away)},
        "by_competition": {
            c: {**rec, "win_rate": _rate(rec)} for c, rec in by_competition.items()
        },
        "competitions_played": sorted(competitions_played),
    }


def list_teams(
    competition: Optional[str] = None,
    season: Optional[str] = None,
) -> list[str]:
    """List canonical display names of teams, optionally filtered."""
    data = _data()
    comp = _competition_filter(competition)
    if season:
        season = str(season)
    seen: set[str] = set()
    out: list[str] = []
    for m in data.matches:
        if comp and m.competition != comp:
            continue
        if season and m.season != season:
            continue
        for key in (m.home_team, m.away_team):
            if key and key not in seen:
                seen.add(key)
                out.append(_display(key))
    out.sort(key=lambda s: s.lower())
    return out


# ---------------------------------------------------------------------------
# 3. Player queries
# ---------------------------------------------------------------------------
def _player_to_dict(p, detail: bool = False) -> dict:
    out = {
        "id": p.id,
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "position": p.position,
        "jersey_number": p.jersey_number,
        "height": p.height,
        "weight": p.weight,
    }
    if detail:
        out.update({
            "preferred_foot": p.preferred_foot,
            "value": p.value,
            "wage": p.wage,
            "attributes": {
                "crossing": p.crossing,
                "finishing": p.finishing,
                "dribbling": p.dribbling,
                "shortpassing": p.shortpassing,
                "longshots": p.longshots,
                "defending": p.defending,
                "pace": p.pace,
                "shooting": p.shooting,
                "passing": p.passing,
                "physical": p.physical,
            },
        })
    return out


def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: int = 0,
    max_overall: Optional[int] = None,
    limit: int = 25,
    sort_by_overall: bool = True,
) -> list[dict]:
    """Search FIFA players by name substring / nationality / club / position."""
    data = _data()
    name_q = (name or "").lower()
    nat_q = (nationality or "").lower()
    pos_q = (position or "").lower()
    club_q = (club or "").lower()
    club_key = resolve_team(club) if club else None

    matches = []
    for p in data.players:
        if name_q and (not p.name or name_q not in p.name.lower()):
            continue
        if nat_q and (not p.nationality or nat_q not in p.nationality.lower()):
            continue
        if pos_q and (not p.position or pos_q not in p.position.upper()):
            # position codes like ST, LW, CDM - allow substring on upper
            if pos_q not in (p.position or "").upper():
                continue
        if club_q:
            # Match either FIFA club text OR canonical club key (cross-file).
            if not (
                (p.club and club_q in p.club.lower())
                or (p.club_canonical and club_key and p.club_canonical == club_key)
            ):
                continue
        if p.overall is None:
            continue
        if min_overall and p.overall < min_overall:
            continue
        if max_overall is not None and p.overall > max_overall:
            continue
        matches.append(p)

    if sort_by_overall:
        matches.sort(key=lambda p: (-(p.overall or 0), p.name or ""))
    else:
        matches.sort(key=lambda p: (p.name or ""))
    matches = matches[: max(0, limit)]
    return [_player_to_dict(p, detail=False) for p in matches]


def team_players(team: str, position: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Return FIFA players whose club matches a soccer team (cross-file query)."""
    return search_players(club=team, position=position, limit=limit)


# ---------------------------------------------------------------------------
# 4. Competition queries
# ---------------------------------------------------------------------------
def _compute_standings(data: SoccerData, competition: str, season: str) -> list[dict]:
    """Compute a league table from matches for one (competition, season)."""
    rows: dict[str, dict] = {}
    for m in data.matches:
        if m.competition != competition or m.season != season:
            continue
        if m.home_goals is None or m.away_goals is None:
            continue
        for key in (m.home_team, m.away_team):
            rows.setdefault(key, {
                "team": "", "played": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0,
            })
        h, a = m.home_team, m.away_team
        hg, ag = m.home_goals, m.away_goals
        rows[h]["played"] += 1
        rows[a]["played"] += 1
        rows[h]["goals_for"] += hg
        rows[h]["goals_against"] += ag
        rows[a]["goals_for"] += ag
        rows[a]["goals_against"] += hg
        if hg > ag:
            rows[h]["wins"] += 1
            rows[a]["losses"] += 1
        elif ag > hg:
            rows[a]["wins"] += 1
            rows[h]["losses"] += 1
        else:
            rows[h]["draws"] += 1
            rows[a]["draws"] += 1

    table = []
    for key, r in rows.items():
        pts = 3 * r["wins"] + r["draws"]
        gd = r["goals_for"] - r["goals_against"]
        table.append({
            "team": _display(key),
            "played": r["played"],
            "wins": r["wins"],
            "draws": r["draws"],
            "losses": r["losses"],
            "goals_for": r["goals_for"],
            "goals_against": r["goals_against"],
            "goal_diff": gd,
            "points": pts,
        })
    table.sort(key=lambda t: (-t["points"], -t["wins"], -t["goal_diff"], -t["goals_for"], t["team"]))
    for i, row in enumerate(table, 1):
        row["rank"] = i
    return table


def standings(competition: str, season: str, top: Optional[int] = None) -> list[dict]:
    """Return a calculated league standings table.

    Only supported for league-style competitions (Brasileirao Serie A/B/C);
    cup competitions raise a ``ValueError`` because knockout formats do not
    produce a meaningful league table from these datasets.
    """
    data = _data()
    comp = resolve_competition(competition)
    if comp is None:
        raise ValueError(f"Unknown competition: {competition!r}")
    if comp in {COMP_COPA_BRASIL, COMP_LIBERTADORES}:
        raise ValueError(
            f"Standings are only available for league competitions "
            f"(Brasileirao Serie A/B/C), not for {comp}."
        )
    season = str(season)
    available = data.seasons_for(comp)
    if available and season not in available:
        raise ValueError(
            f"Season {season} not found for {comp}. Available seasons: "
            f"{', '.join(available)}"
        )
    table = _compute_standings(data, comp, season)
    if top is not None:
        table = table[:top]
    return table


def champion(competition: str, season: str) -> dict:
    """Return the champion (table-topper) for a league competition + season."""
    table = standings(competition, season)
    if not table:
        raise ValueError(f"No standings for {competition} {season}")
    top = table[0]
    return {
        "competition": resolve_competition(competition),
        "season": str(season),
        "champion": top["team"],
        "points": top["points"],
        "record": {
            "wins": top["wins"], "draws": top["draws"], "losses": top["losses"],
            "goals_for": top["goals_for"], "goals_against": top["goals_against"],
        },
    }


def relegated(competition: str, season: str, n: int = 4) -> list[dict]:
    """Return the bottom ``n`` teams of a league standings table."""
    table = standings(competition, season)
    if not table:
        return []
    n = max(0, min(n, len(table)))
    return list(reversed(table[-n:]))


def list_competitions() -> list[dict]:
    """Summarise every competition available in the dataset."""
    data = _data()
    out = []
    for comp in data.competitions():
        seasons = data.seasons_for(comp)
        match_count = sum(1 for m in data.matches if m.competition == comp)
        teams: set[str] = set()
        for m in data.matches:
            if m.competition == comp:
                teams.add(m.home_team)
                teams.add(m.away_team)
        out.append({
            "competition": comp,
            "seasons": seasons,
            "match_count": match_count,
            "team_count": len(teams),
        })
    return out


# ---------------------------------------------------------------------------
# 5. Statistical analysis
# ---------------------------------------------------------------------------
def statistics(
    competition: Optional[str] = None,
    season: Optional[str] = None,
) -> dict:
    """Return aggregate goal / result statistics for a (competition, season)."""
    data = _data()
    comp = _competition_filter(competition)
    if season:
        season = str(season)

    matches = []
    for m in data.matches:
        if comp and m.competition != comp:
            continue
        if season and m.season != season:
            continue
        if m.home_goals is None or m.away_goals is None:
            continue
        matches.append(m)

    total = len(matches)
    if total == 0:
        return {
            "competition": comp, "season": season, "matches": 0,
            "total_goals": 0, "avg_goals": None, "home_wins": 0, "away_wins": 0,
            "draws": 0, "home_win_rate": None, "avg_home_goals": None,
            "avg_away_goals": None,
        }
    total_goals = sum(m.home_goals + m.away_goals for m in matches)
    home_wins = sum(1 for m in matches if m.home_goals > m.away_goals)
    away_wins = sum(1 for m in matches if m.away_goals > m.home_goals)
    draws = sum(1 for m in matches if m.home_goals == m.away_goals)
    home_goals = sum(m.home_goals for m in matches)
    away_goals = sum(m.away_goals for m in matches)
    return {
        "competition": comp,
        "season": season,
        "matches": total,
        "total_goals": total_goals,
        "avg_goals": round(total_goals / total, 3),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / total, 4),
        "away_win_rate": round(away_wins / total, 4),
        "draw_rate": round(draws / total, 4),
        "avg_home_goals": round(home_goals / total, 3),
        "avg_away_goals": round(away_goals / total, 3),
    }


def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Return the largest victory margins in the dataset."""
    data = _data()
    comp = _competition_filter(competition)
    if season:
        season = str(season)

    rows = []
    for m in data.matches:
        if comp and m.competition != comp:
            continue
        if season and m.season != season:
            continue
        if m.home_goals is None or m.away_goals is None:
            continue
        margin = m.home_goals - m.away_goals
        rows.append((abs(margin), margin, m))
    rows.sort(key=lambda t: (-t[0], t[2].date or "", t[2].competition))
    rows = rows[: max(0, limit)]
    out = []
    for _abs, signed, m in rows:
        out.append({
            "date": m.date,
            "season": m.season,
            "competition": m.competition,
            "home_team": m.home_display,
            "away_team": m.away_display,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "score": f"{m.home_goals}-{m.away_goals}",
            "margin": abs(signed),
            "winner": m.home_display if signed > 0 else m.away_display,
        })
    return out


def match_stats(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 25,
) -> list[dict]:
    """Return detailed per-match statistics (corners/shots/attacks) from the
    BR-Football-Dataset for matches matching the criteria."""
    data = _data()
    comp = _competition_filter(competition)
    team_key = resolve_team(team) if team else None
    opp_key = resolve_team(opponent) if opponent else None
    if season:
        season = str(season)

    results = []
    for m in data.stats_matches:
        if comp and m.competition != comp:
            continue
        if season and m.season != season:
            continue
        if team_key and m.home_team != team_key and m.away_team != team_key:
            continue
        if opp_key and m.home_team != opp_key and m.away_team != opp_key:
            continue
        results.append(m)
    results = _sort_matches(results, limit)
    out = []
    for m in results:
        out.append({
            "date": m.date,
            "season": m.season,
            "competition": m.competition,
            "home_team": m.home_display,
            "away_team": m.away_display,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "home_corners": m.home_corners,
            "away_corners": m.away_corners,
            "total_corners": (
                (m.home_corners or 0) + (m.away_corners or 0)
                if m.home_corners is not None or m.away_corners is not None
                else None
            ),
            "home_shots": m.home_shots,
            "away_shots": m.away_shots,
            "home_attacks": m.home_attacks,
            "away_attacks": m.away_attacks,
            "ht_result": m.ht_result,
            "at_result": m.at_result,
            "source": m.source,
        })
    return out
