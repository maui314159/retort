"""Query layer implementing the five capability categories from the spec.

Every public function returns plain JSON-serialisable data structures (``dict``
/ ``list`` / ``str`` / ``int`` / ``float`` / ``None``) so they can be served
verbatim by the MCP tools in :mod:`brazilian_soccer_mcp.server`.

Categories:
  1. Match queries        - ``find_matches``, ``head_to_head``
  2. Team queries          - ``team_stats``, ``compare_teams``, ``competitions_for_team``
  3. Player queries        - ``search_players``, ``top_brazilian_players``, ``players_for_club``
  4. Competition queries    - ``standings``, ``champions``, ``relegated_teams``
  5. Statistical analysis   - ``average_goals``, ``biggest_wins``, ``home_away_balance``, ``derbies``
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from .data_loader import SoccerData, load_all
from .normalize import (
    competition_matches,
    normalize_team_name,
    parse_date,
)

DERBY_PAIRS: tuple[tuple[str, str], ...] = (
    ("flamengo", "fluminense"),
    ("corinthians", "palmeiras"),
    ("corinthians", "sao paulo"),
    ("sao paulo", "santos"),
    ("gremio", "internacional"),
    ("atletico", "cruzeiro"),
    ("cruzeiro", "atletico"),
    ("santos", "sao paulo"),
    ("bahia", "vitoria"),
    ("vitoria", "bahia"),
    ("sport", "nautico"),
    ("ceara", "fortaleza"),
    ("avai", "figueirense"),
)


def _resolve_team(data: SoccerData, name: str | None) -> str | None:
    """Resolve a free-form team name to its canonical key.

    Tries exact normalised match first, then falls back to a prefix / substring
    match against the registered display names so that ``"Flamengo"``,
    ``"Flamengo-RJ"`` and ``"flamengo"`` all resolve to ``"flamengo"``.
    """
    if not name:
        return None
    key = normalize_team_name(name)
    if key in data.team_display:
        return key
    for cand in data.team_display:
        if key == cand or key in cand or cand in key:
            return cand
    return None


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return parse_date(str(value))


def _match_dict(data: SoccerData, m) -> dict[str, Any]:
    return {
        "date": m.date.isoformat() if m.date else None,
        "home_team": data.display_name(m.home),
        "away_team": data.display_name(m.away),
        "home_goal": m.home_goal,
        "away_goal": m.away_goal,
        "competition": m.competition,
        "season": m.season,
        "round": m.round,
        "stage": m.stage,
        "venue": m.venue,
        "source": m.source,
    }


def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: Any = None,
    end_date: Any = None,
    limit: int | None = 50,
    data: SoccerData | None = None,
) -> list[dict[str, Any]]:
    """Find matches by team, opponent, competition, season and/or date range.

    When only *team* is given, all matches involving that team (home or away)
    are returned.  When *opponent* is also given, the result is restricted to
    matches between *team* and *opponent*.
    """
    data = data or load_all()
    team_key = _resolve_team(data, team)
    opp_key = _resolve_team(data, opponent)
    start = _to_date(start_date)
    end = _to_date(end_date)
    season_i = int(season) if season is not None else None

    if team is not None and not team_key:
        return []
    if opponent is not None and not opp_key:
        return []

    out: list[dict[str, Any]] = []
    for m in data.matches:
        if team_key is not None and not m.involves(team_key):
            continue
        if opp_key is not None and not m.involves(opp_key):
            continue
        if team_key is not None and opp_key is not None and opp_key == team_key:
            continue
        if competition is not None and not competition_matches(competition, m.competition):
            continue
        if season_i is not None and m.season != season_i:
            continue
        if m.date is not None:
            if start is not None and m.date < start:
                continue
            if end is not None and m.date > end:
                continue
        elif start is not None or end is not None:
            continue
        out.append(_match_dict(data, m))
    out.sort(key=lambda r: (r["date"] or "", r["competition"]))
    if limit is not None:
        return out[:limit]
    return out


def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
    data: SoccerData | None = None,
) -> dict[str, Any]:
    """Return head-to-head record and match list between two teams."""
    data = data or load_all()
    a_key = _resolve_team(data, team_a)
    b_key = _resolve_team(data, team_b)
    if not a_key or not b_key:
        return {"error": "Could not resolve one or both teams", "team_a": team_a, "team_b": team_b}
    season_i = int(season) if season is not None else None
    matches: list = []
    for m in data.matches:
        if m.involves(a_key) and m.involves(b_key):
            if competition is not None and not competition_matches(competition, m.competition):
                continue
            if season_i is not None and m.season != season_i:
                continue
            matches.append(m)
    matches.sort(key=lambda m: (m.date or date.min, m.competition))

    a_wins = b_wins = draws = 0
    a_goals = b_goals = 0
    rows: list[dict[str, Any]] = []
    for m in matches:
        if m.home == a_key:
            hg, ag = m.home_goal, m.away_goal
        else:
            hg, ag = m.away_goal, m.home_goal
        a_goals += hg
        b_goals += ag
        if hg > ag:
            a_wins += 1
        elif ag > hg:
            b_wins += 1
        else:
            draws += 1
        rows.append(_match_dict(data, m))
    return {
        "team_a": data.display_name(a_key),
        "team_b": data.display_name(b_key),
        "matches_played": len(matches),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "matches": rows,
    }


def _record(matches: list, team_key: str, venue: str | None) -> dict[str, int]:
    wins = losses = draws = gf = ga = 0
    home_games = away_games = 0
    for m in matches:
        if venue == "home" and m.home != team_key:
            continue
        if venue == "away" and m.away != team_key:
            continue
        if m.home == team_key:
            gf += m.home_goal
            ga += m.away_goal
            home_games += 1
            if m.home_goal > m.away_goal:
                wins += 1
            elif m.home_goal < m.away_goal:
                losses += 1
            else:
                draws += 1
        elif m.away == team_key:
            gf += m.away_goal
            ga += m.home_goal
            away_games += 1
            if m.away_goal > m.home_goal:
                wins += 1
            elif m.away_goal < m.home_goal:
                losses += 1
            else:
                draws += 1
    played = wins + losses + draws
    return {
        "matches": played,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "goals_for": gf,
        "goals_against": ga,
        "home_games": home_games,
        "away_games": away_games,
        "win_rate": round(wins / played * 100, 1) if played else 0.0,
    }


def team_stats(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
    data: SoccerData | None = None,
) -> dict[str, Any]:
    """Return win/loss/draw record and goals for *team*, optionally filtered."""
    data = data or load_all()
    key = _resolve_team(data, team)
    if not key:
        return {"error": f"Team not found: {team}"}
    season_i = int(season) if season is not None else None
    ms = [m for m in data.matches_for_team(key)
          if (season_i is None or m.season == season_i)
          and (competition is None or competition_matches(competition, m.competition))]
    rec = _record(ms, key, venue)
    by_comp: dict[str, dict[str, int]] = {}
    for m in ms:
        comp = m.competition
        if comp not in by_comp:
            by_comp[comp] = {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
                             "goals_for": 0, "goals_against": 0}
        c = by_comp[comp]
        c["matches"] += 1
        if m.home == key:
            c["goals_for"] += m.home_goal
            c["goals_against"] += m.away_goal
            if m.home_goal > m.away_goal:
                c["wins"] += 1
            elif m.home_goal < m.away_goal:
                c["losses"] += 1
            else:
                c["draws"] += 1
        else:
            c["goals_for"] += m.away_goal
            c["goals_against"] += m.home_goal
            if m.away_goal > m.home_goal:
                c["wins"] += 1
            elif m.away_goal < m.home_goal:
                c["losses"] += 1
            else:
                c["draws"] += 1
    return {
        "team": data.display_name(key),
        "venue": venue,
        "season": season_i,
        "competition": competition,
        **rec,
        "by_competition": by_comp,
    }


def compare_teams(
    team_a: str,
    team_b: str,
    season: int | None = None,
    data: SoccerData | None = None,
) -> dict[str, Any]:
    """Compare two teams' overall records (and head-to-head)."""
    data = data or load_all()
    return {
        "team_a": team_stats(team_a, season=season, data=data),
        "team_b": team_stats(team_b, season=season, data=data),
        "head_to_head": head_to_head(team_a, team_b, season=season, data=data),
    }


def competitions_for_team(team: str, data: SoccerData | None = None) -> dict[str, Any]:
    """List the competitions a team has appeared in along with match counts."""
    data = data or load_all()
    key = _resolve_team(data, team)
    if not key:
        return {"error": f"Team not found: {team}"}
    counts: dict[str, int] = defaultdict(int)
    for m in data.matches_for_team(key):
        counts[m.competition] += 1
    return {
        "team": data.display_name(key),
        "competitions": [{"competition": c, "matches": n} for c, n in
                         sorted(counts.items(), key=lambda x: -x[1])],
    }


def _player_dict(p) -> dict[str, Any]:
    return {
        "id": p.id,
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "position": p.position,
        "jersey": p.jersey,
        "height": p.height,
        "weight": p.weight,
        "preferred_foot": p.preferred_foot,
        "value": p.value,
        "wage": p.wage,
        "top_attributes": dict(sorted(
            ((k, v) for k, v in p.attributes.items() if v is not None),
            key=lambda kv: -(kv[1] or 0))[:5]) if p.attributes else {},
    }


def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int | None = 50,
    sort_by: str = "Overall",
    data: SoccerData | None = None,
) -> list[dict[str, Any]]:
    """Search the FIFA player database by any combination of filters."""
    data = data or load_all()
    name_l = (name or "").strip().lower()
    nat_l = (nationality or "").strip().lower()
    club_key = normalize_team_name(club) if club else None
    pos_l = (position or "").strip().lower()
    min_o = int(min_overall) if min_overall is not None else None
    max_o = int(max_overall) if max_overall is not None else None

    rows: list = []
    for p in data.players:
        if name_l and name_l not in (p.name or "").lower():
            continue
        if nat_l and nat_l not in (p.nationality or "").lower():
            continue
        if club_key and normalize_team_name(p.club) != club_key and club_key not in normalize_team_name(p.club):
            continue
        if pos_l and pos_l not in (p.position or "").lower():
            continue
        if min_o is not None and (p.overall is None or p.overall < min_o):
            continue
        if max_o is not None and (p.overall is None or p.overall > max_o):
            continue
        rows.append(p)
    sort_field = sort_by
    rows.sort(key=lambda p: (getattr(p, sort_field, None) is None,
                            -(getattr(p, sort_field, None) or 0),
                            p.name.lower()))
    if limit is not None:
        rows = rows[:limit]
    return [_player_dict(p) for p in rows]


def top_brazilian_players(limit: int = 20, data: SoccerData | None = None) -> list[dict[str, Any]]:
    """Return the highest-rated Brazilian players in the FIFA dataset."""
    data = data or load_all()
    rows = [p for p in data.players if (p.nationality or "").lower() in ("brazil", "brasil")]
    rows.sort(key=lambda p: (-(p.overall or 0), p.name.lower()))
    return [_player_dict(p) for p in rows[:limit]]


def players_for_club(club: str, data: SoccerData | None = None) -> dict[str, Any]:
    """Return the players attached to *club* plus aggregate rating stats."""
    data = data or load_all()
    club_key = normalize_team_name(club)
    members = data.players_for_club(club_key)
    ratings = [p.overall for p in members if p.overall is not None]
    return {
        "club": club,
        "player_count": len(members),
        "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "players": [_player_dict(p) for p in
                    sorted(members, key=lambda p: -(p.overall or 0))],
    }


def top_clubs_by_nationality(nationality: str = "Brazil",
                             limit: int = 20,
                             data: SoccerData | None = None) -> list[dict[str, Any]]:
    """Rank clubs by number of players of *nationality* (avg rating included)."""
    data = data or load_all()
    nat_l = nationality.lower()
    groups: dict[str, list] = defaultdict(list)
    for p in data.players:
        if nat_l in (p.nationality or "").lower() and p.club:
            groups[p.club].append(p)
    rows = []
    for club, members in groups.items():
        ratings = [m.overall for m in members if m.overall is not None]
        rows.append({
            "club": club,
            "player_count": len(members),
            "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        })
    rows.sort(key=lambda r: (-r["player_count"], -(r["average_rating"] or 0)))
    return rows[:limit]


def standings(
    competition: str = "Brasileirão Serie A",
    season: int | None = None,
    data: SoccerData | None = None,
) -> dict[str, Any]:
    """Compute a league-style standings table from match results."""
    data = data or load_all()
    season_i = int(season) if season is not None else None
    table: dict[str, dict[str, int]] = defaultdict(
        lambda: {"played": 0, "wins": 0, "draws": 0, "losses": 0,
                 "goals_for": 0, "goals_against": 0, "points": 0})
    counted = 0
    for m in data.matches:
        if not competition_matches(competition, m.competition):
            continue
        if season_i is not None and m.season != season_i:
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        h, a = m.home, m.away
        hg, ag = m.home_goal, m.away_goal
        table[h]["played"] += 1
        table[a]["played"] += 1
        table[h]["goals_for"] += hg
        table[h]["goals_against"] += ag
        table[a]["goals_for"] += ag
        table[a]["goals_against"] += hg
        if hg > ag:
            table[h]["wins"] += 1
            table[a]["losses"] += 1
            table[h]["points"] += 3
        elif ag > hg:
            table[a]["wins"] += 1
            table[h]["losses"] += 1
            table[a]["points"] += 3
        else:
            table[h]["draws"] += 1
            table[a]["draws"] += 1
            table[h]["points"] += 1
            table[a]["points"] += 1
        counted += 1

    rows = []
    for key, st in table.items():
        gd = st["goals_for"] - st["goals_against"]
        rows.append({
            "team": data.display_name(key),
            "played": st["played"],
            "wins": st["wins"],
            "draws": st["draws"],
            "losses": st["losses"],
            "goals_for": st["goals_for"],
            "goals_against": st["goals_against"],
            "goal_difference": gd,
            "points": st["points"],
        })
    rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))
    for i, r in enumerate(rows, 1):
        r["position"] = i
    if rows:
        rows[0]["champion"] = True
    return {
        "competition": competition,
        "season": season_i,
        "matches_counted": counted,
        "standings": rows,
    }


def champions(
    competition: str = "Brasileirão Serie A",
    data: SoccerData | None = None,
) -> list[dict[str, Any]]:
    """Return the champion of every season present in *competition*."""
    data = data or load_all()
    by_season: dict[int, dict] = {}
    for s in sorted({m.season for m in data.matches if m.season and competition_matches(competition, m.competition)}):
        table = standings(competition, s, data=data)
        if table["standings"]:
            top = table["standings"][0]
            by_season[s] = top
    return [{"season": s, "champion": r["team"], "points": r["points"],
             "record": f"{r['wins']}W {r['draws']}D {r['losses']}L"}
            for s, r in sorted(by_season.items())]


def relegated_teams(
    competition: str = "Brasileirão Serie A",
    season: int | None = None,
    n: int = 4,
    data: SoccerData | None = None,
) -> list[dict[str, Any]]:
    """Return the bottom *n* teams in the standings (relegation zone)."""
    table = standings(competition, season, data=data)
    rows = table["standings"]
    return rows[-n:][::-1] if n and len(rows) >= n else rows[::-1]


def average_goals(
    competition: str | None = None,
    season: int | None = None,
    data: SoccerData | None = None,
) -> dict[str, Any]:
    """Return average goals-per-match plus home/away win rates."""
    data = data or load_all()
    season_i = int(season) if season is not None else None
    total_goals = 0
    matches_n = 0
    home_wins = away_wins = draws = 0
    for m in data.matches:
        if competition is not None and not competition_matches(competition, m.competition):
            continue
        if season_i is not None and m.season != season_i:
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        matches_n += 1
        total_goals += m.home_goal + m.away_goal
        if m.home_goal > m.away_goal:
            home_wins += 1
        elif m.away_goal > m.home_goal:
            away_wins += 1
        else:
            draws += 1
    return {
        "competition": competition,
        "season": season_i,
        "matches": matches_n,
        "total_goals": total_goals,
        "average_goals_per_match": round(total_goals / matches_n, 2) if matches_n else 0.0,
        "home_win_rate": round(home_wins / matches_n * 100, 1) if matches_n else 0.0,
        "away_win_rate": round(away_wins / matches_n * 100, 1) if matches_n else 0.0,
        "draw_rate": round(draws / matches_n * 100, 1) if matches_n else 0.0,
    }


def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
    data: SoccerData | None = None,
) -> list[dict[str, Any]]:
    """Return the highest-margin victories (optionally filtered)."""
    data = data or load_all()
    season_i = int(season) if season is not None else None
    rows = []
    for m in data.matches:
        if competition is not None and not competition_matches(competition, m.competition):
            continue
        if season_i is not None and m.season != season_i:
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        diff = abs(m.home_goal - m.away_goal)
        if diff == 0:
            continue
        rows.append((diff, m))
    rows.sort(key=lambda t: (-t[0], t[1].date or date.min))
    out = []
    for diff, m in rows[:limit]:
        d = _match_dict(data, m)
        d["goal_difference"] = diff
        out.append(d)
    return out


def home_away_balance(
    competition: str | None = None,
    season: int | None = None,
    data: SoccerData | None = None,
) -> dict[str, Any]:
    """Return per-team home vs away performance breakdown."""
    data = data or load_all()
    season_i = int(season) if season is not None else None
    home_stats: dict[str, dict] = defaultdict(
        lambda: {"played": 0, "wins": 0, "draws": 0, "losses": 0})
    away_stats: dict[str, dict] = defaultdict(
        lambda: {"played": 0, "wins": 0, "draws": 0, "losses": 0})
    for m in data.matches:
        if competition is not None and not competition_matches(competition, m.competition):
            continue
        if season_i is not None and m.season != season_i:
            continue
        if m.home_goal is None or m.away_goal is None:
            continue
        h = home_stats[m.home]
        a = away_stats[m.away]
        h["played"] += 1
        a["played"] += 1
        if m.home_goal > m.away_goal:
            h["wins"] += 1
            a["losses"] += 1
        elif m.away_goal > m.home_goal:
            a["wins"] += 1
            h["losses"] += 1
        else:
            h["draws"] += 1
            a["draws"] += 1

    def rate(st):
        return round(st["wins"] / st["played"] * 100, 1) if st["played"] else 0.0

    teams = set(home_stats) | set(away_stats)
    rows = []
    for t in teams:
        h = home_stats[t]
        a = away_stats[t]
        rows.append({
            "team": data.display_name(t),
            "home_played": h["played"], "home_wins": h["wins"],
            "home_draws": h["draws"], "home_losses": h["losses"],
            "home_win_rate": rate(h),
            "away_played": a["played"], "away_wins": a["wins"],
            "away_draws": a["draws"], "away_losses": a["losses"],
            "away_win_rate": rate(a),
        })
    rows.sort(key=lambda r: -r["home_win_rate"])
    return {"competition": competition, "season": season_i, "teams": rows}


def derbies(
    season: int | None = None,
    competition: str | None = None,
    data: SoccerData | None = None,
) -> list[dict[str, Any]]:
    """Return matches between traditional rival teams (derbies)."""
    data = data or load_all()
    season_i = int(season) if season is not None else None
    pairs = {(min(a, b), max(a, b)) for a, b in DERBY_PAIRS}
    out = []
    for m in data.matches:
        pair = (m.home, m.away) if m.home < m.away else (m.away, m.home)
        if pair not in pairs:
            continue
        if season_i is not None and m.season != season_i:
            continue
        if competition is not None and not competition_matches(competition, m.competition):
            continue
        out.append(_match_dict(data, m))
    out.sort(key=lambda r: (r["date"] or "", r["competition"]))
    return out
