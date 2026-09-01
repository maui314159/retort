"""Brazilian Soccer MCP Server - query/analysis engine.

Context block
-------------
Purpose: Pure-Python query layer over `SoccerData` that backs every MCP
tool. Keeping the logic out of the server module makes it trivially
unit-testable (the BDD tests exercise these functions directly).

What:
  - search_matches(...)        : filter matches by team(s), competition,
                                 season, date range.
  - head_to_head(a, b)         : win/draw/loss summary + match list.
  - team_stats(team, season?)  : W/D/L, goals, home/away split.
  - standings(competition, season) : computed league table.
  - biggest_wins(competition?, n)  : sorted by goal margin.
  - avg_goals(competition?)    : per-match goal averages.
  - search_players(...)        : name/nationality/club/position filters.
  - top_brazilian_players(n)   : convenience for the spec's example.
  - derbies(season?)           : traditional-rivalry matches.

Why: Each function returns plain dicts/lists (JSON-serializable) so the
MCP tool layer can pass them straight to the LLM without transformation.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from data_loader import Match, SoccerData, get_data
from normalizer import canonical_name, name_key, teams_match

# Traditional Brazilian derbies (by name_key of canonical names).
_DERBY_PAIRS = {
    ("flamengo", "fluminense"),    # Fla-Flu
    ("corinthians", "sao paulo"),  # Majestoso
    ("corinthians", "palmeiras"),  # Paulista derby
    ("santos", "sao paulo"),       # San-São
    ("santos", "corinthians"),     # Clássico da Saudade
    ("gremio", "internacional"),   # Grenal
    ("atletico-mg", "cruzeiro"),   # Clássico Mineiro
    ("flamengo", "vasco"),         # Clássico dos Milhões
    ("bahia", "vitoria"),          # Ba-Vi
    ("fortaleza", "ceara"),        # Clássico-Rei
    ("sport", "nautico"),          # Clássico dos Clássicos
    ("atletico-pr", "coritiba"),   # Atle-Tiba
}


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------

def search_matches(
    sd: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Return matches matching all supplied criteria (AND semantics)."""
    comp_filter = _competition_filter(competition)
    tk = name_key(team) if team else None
    ok = name_key(opponent) if opponent else None

    results: list[dict] = []
    pool: Iterable[Match]
    if tk:
        pool = sd.by_team.get(tk, [])
    else:
        pool = sd.matches

    seen_ids: set[int] = set()
    for m in pool:
        mid = id(m)
        if mid in seen_ids:
            continue
        seen_ids.add(mid)

        if tk and m.home_key != tk and m.away_key != tk:
            continue
        if ok and m.home_key != ok and m.away_key != ok:
            continue
        if comp_filter and not comp_filter(m.competition):
            continue
        if season is not None and m.season != season:
            continue
        if start_date and (m.date is None or m.date < start_date):
            continue
        if end_date and (m.date is None or m.date > end_date):
            continue

        results.append(_match_dict(m))
        if limit and len(results) >= limit:
            break
    # Sort newest-first when dates exist
    results.sort(key=lambda r: r["date"] or "", reverse=True)
    return results


def _match_dict(m: Match) -> dict:
    return {
        "competition": m.competition,
        "date": m.date,
        "season": m.season,
        "round": m.round_label,
        "home_team": m.home_canonical or m.home_raw,
        "away_team": m.away_canonical or m.away_raw,
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "score": m.score_str,
        "stadium": m.stadium,
    }


def _competition_filter(comp: str | None):
    if not comp:
        return None
    c = comp.strip().lower()
    aliases = {
        "brasileirao": ["brasileirão", "brasileirao (histórico)", "serie a"],
        "serie a": ["serie a", "brasileirão"],
        "copa do brasil": ["copa do brasil"],
        "libertadores": ["libertadores"],
    }
    targets = aliases.get(c, [c])
    def _f(comp_name: str) -> bool:
        cn = comp_name.lower()
        return any(t in cn for t in targets)
    return _f


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------

def team_stats(sd: SoccerData, team: str, season: int | None = None) -> dict:
    """Aggregate W/D/L and goals for a team, optionally in one season."""
    matches = sd.matches_for_team_season(team, season) if season else sd.matches_for_team(team)
    tk = name_key(team)
    w = d = l = gf = ga = 0
    home_w = home_d = home_l = away_w = away_d = away_l = 0
    for m in matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        is_home = m.home_key == tk
        my = m.home_goals if is_home else m.away_goals
        opp = m.away_goals if is_home else m.home_goals
        gf += my
        ga += opp
        res = m.result()
        if res == "draw":
            d += 1
            if is_home: home_d += 1
            else: away_d += 1
        elif (res == "home") == is_home:
            w += 1
            if is_home: home_w += 1
            else: away_w += 1
        else:
            l += 1
            if is_home: home_l += 1
            else: away_l += 1
    played = w + d + l
    return {
        "team": canonical_name(team),
        "season": season,
        "played": played,
        "wins": w, "draws": d, "losses": l,
        "goals_for": gf, "goals_against": ga,
        "win_rate": round(w / played, 4) if played else 0.0,
        "home": {"wins": home_w, "draws": home_d, "losses": home_l},
        "away": {"wins": away_w, "draws": away_d, "losses": away_l},
    }


def head_to_head(sd: SoccerData, team_a: str, team_b: str) -> dict:
    ka = name_key(team_a)
    kb = name_key(team_b)
    matches = [
        m for m in sd.matches
        if {m.home_key, m.away_key} == {ka, kb}
    ]
    matches.sort(key=lambda m: m.date or "", reverse=True)
    a_wins = b_wins = draws = 0
    for m in matches:
        res = m.result()
        if res is None:
            continue
        if res == "draw":
            draws += 1
        elif (res == "home" and m.home_key == ka) or (res == "away" and m.away_key == ka):
            a_wins += 1
        else:
            b_wins += 1
    return {
        "team_a": canonical_name(team_a),
        "team_b": canonical_name(team_b),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "matches": [_match_dict(m) for m in matches],
    }


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------

def standings(sd: SoccerData, competition: str, season: int) -> list[dict]:
    """Compute a league table for a competition+season from match results.

    Uses 3 points for a win, 1 for a draw. Only meaningful for round-robin
    competitions (Brasileirão). Knockout cups will produce partial tables.
    """
    comp_filter = _competition_filter(competition)
    table: dict[str, dict] = {}
    for m in sd.matches:
        if m.season != season:
            continue
        if comp_filter and not comp_filter(m.competition):
            continue
        if m.home_goals is None or m.away_goals is None:
            continue
        for key, canon, gf, ga, is_home in (
            (m.home_key, m.home_canonical, m.home_goals, m.away_goals, True),
            (m.away_key, m.away_canonical, m.away_goals, m.home_goals, False),
        ):
            if not key:
                continue
            row = table.setdefault(key, {
                "team": canon, "played": 0, "wins": 0, "draws": 0, "losses": 0,
                "goals_for": 0, "goals_against": 0, "points": 0,
            })
            row["played"] += 1
            row["goals_for"] += gf
            row["goals_against"] += ga
            res = m.result()
            if res == "draw":
                row["draws"] += 1
                row["points"] += 1
            elif (res == "home") == is_home:
                row["wins"] += 1
                row["points"] += 3
            else:
                row["losses"] += 1
    rows = list(table.values())
    for r in rows:
        r["goal_diff"] = r["goals_for"] - r["goals_against"]
    rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["goal_diff"], -r["goals_for"], r["team"]))
    for i, r in enumerate(rows, 1):
        r["position"] = i
    return rows


def champion(sd: SoccerData, competition: str, season: int) -> dict | None:
    table = standings(sd, competition, season)
    if not table:
        return None
    top = table[0]
    return {"season": season, "competition": competition, "champion": top["team"], "points": top["points"]}


def relegated(sd: SoccerData, competition: str, season: int, n: int = 4) -> list[str]:
    table = standings(sd, competition, season)
    if not table:
        return []
    return [r["team"] for r in table[-n:]]


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def biggest_wins(sd: SoccerData, competition: str | None = None, n: int = 10) -> list[dict]:
    comp_filter = _competition_filter(competition)
    rows = []
    for m in sd.matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        if comp_filter and not comp_filter(m.competition):
            continue
        margin = abs(m.home_goals - m.away_goals)
        if margin == 0:
            continue
        rows.append({
            "date": m.date, "competition": m.competition, "season": m.season,
            "home_team": m.home_canonical, "away_team": m.away_canonical,
            "home_goals": m.home_goals, "away_goals": m.away_goals,
            "margin": margin,
        })
    rows.sort(key=lambda r: (-r["margin"], r["date"] or ""))
    return rows[:n]


def avg_goals(sd: SoccerData, competition: str | None = None) -> dict:
    comp_filter = _competition_filter(competition)
    total_goals = 0
    total_matches = 0
    home_wins = draws = away_wins = 0
    for m in sd.matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        if comp_filter and not comp_filter(m.competition):
            continue
        total_matches += 1
        total_goals += m.home_goals + m.away_goals
        res = m.result()
        if res == "home":
            home_wins += 1
        elif res == "away":
            away_wins += 1
        elif res == "draw":
            draws += 1
    decided = home_wins + away_wins + draws
    return {
        "competition": competition or "all",
        "matches": total_matches,
        "avg_goals_per_match": round(total_goals / total_matches, 4) if total_matches else 0.0,
        "home_win_rate": round(home_wins / decided, 4) if decided else 0.0,
        "draw_rate": round(draws / decided, 4) if decided else 0.0,
        "away_win_rate": round(away_wins / decided, 4) if decided else 0.0,
    }


def best_home_record(sd: SoccerData, competition: str | None = None, season: int | None = None,
                     min_matches: int = 5) -> list[dict]:
    comp_filter = _competition_filter(competition)
    stats: dict[str, dict] = {}
    for m in sd.matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        if comp_filter and not comp_filter(m.competition):
            continue
        if season is not None and m.season != season:
            continue
        if not m.home_key:
            continue
        row = stats.setdefault(m.home_key, {"team": m.home_canonical, "played": 0, "wins": 0, "points": 0})
        row["played"] += 1
        res = m.result()
        if res == "home":
            row["wins"] += 1
            row["points"] += 3
        elif res == "draw":
            row["points"] += 1
    out = [r for r in stats.values() if r["played"] >= min_matches]
    for r in out:
        r["win_rate"] = round(r["wins"] / r["played"], 4)
    out.sort(key=lambda r: (-r["win_rate"], -r["points"]))
    return out


def derbies(sd: SoccerData, season: int | None = None) -> list[dict]:
    pairs = {frozenset(p) for p in _DERBY_PAIRS}
    out = []
    for m in sd.matches:
        if season is not None and m.season != season:
            continue
        if frozenset({m.home_key, m.away_key}) in pairs:
            out.append(_match_dict(m))
    out.sort(key=lambda r: r["date"] or "", reverse=True)
    return out


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

def search_players(
    sd: SoccerData,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int | None = None,
    sort_by_overall: bool = True,
) -> list[dict]:
    name_l = name.lower() if name else None
    nat_l = nationality.lower() if nationality else None
    # Club match: allow club name_key match (handle accents)
    club_key = name_key(club) if club else None
    pos_l = position.lower() if position else None

    out: list[dict] = []
    for p in sd.players:
        if name_l and name_l not in p.name.lower():
            continue
        if nat_l and nat_l not in p.nationality.lower():
            continue
        if club_key and name_key(p.club) != club_key and club_key not in name_key(p.club):
            continue
        if pos_l and pos_l not in p.position.lower():
            continue
        if min_overall is not None and (p.overall is None or p.overall < min_overall):
            continue
        out.append({
            "id": p.id, "name": p.name, "age": p.age,
            "nationality": p.nationality, "overall": p.overall,
            "potential": p.potential, "club": p.club, "position": p.position,
            "jersey_number": p.jersey_number,
        })
    if sort_by_overall:
        out.sort(key=lambda x: (-(x["overall"] or 0), x["name"]))
    if limit:
        out = out[:limit]
    return out


def top_brazilian_players(sd: SoccerData, n: int = 10) -> list[dict]:
    return search_players(sd, nationality="Brazil", limit=n)


def players_at_club(sd: SoccerData, club: str, limit: int | None = None) -> list[dict]:
    return search_players(sd, club=club, limit=limit)


# Convenience: use the cached singleton by default
def _data() -> SoccerData:
    return get_data()
