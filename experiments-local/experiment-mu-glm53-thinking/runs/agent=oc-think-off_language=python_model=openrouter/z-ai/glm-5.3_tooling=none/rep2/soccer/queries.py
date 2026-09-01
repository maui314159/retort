"""Query layer: matches, teams, players, competitions and statistics.

Every function takes the loaded :class:`~soccer.loader.SoccerData` plus
plain-python filter arguments, and returns JSON-serializable dicts.
Team and competition names are matched loosely (accents, case and
state suffixes ignored) so that "palmeiras", "Palmeiras-SP" and
"SPORT Club Corinthians Paulista" all resolve correctly.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from soccer.loader import SoccerData, competition_matches
from soccer.normalize import normalize_name

# Well-known derby pairings (normalized keys are computed at runtime).
_DERBY_NAMES = [
    ("Flamengo", "Fluminense"),  # Fla-Flu
    ("Flamengo", "Vasco"),  # Clássico dos Milhões
    ("Flamengo", "Botafogo"),
    ("Corinthians", "Palmeiras"),  # Choque-Rei
    ("Corinthians", "São Paulo"),  # Majestoso
    ("Palmeiras", "São Paulo"),  # Choque-Rei
    ("Santos", "Corinthians"),  # Clássico Alvinegro
    ("Grêmio", "Internacional"),  # Grenal
    ("Cruzeiro", "Atlético Mineiro"),  # Clássico Mineiro
    ("Bahia", "Vitória"),  # Ba-Vi
    ("Fortaleza", "Ceará"),  # Clássico-Rei
    ("Sport", "Náutico"),  # Clássico dos Clássicos
    ("Athletico-PR", "Coritiba"),  # Atletiba
]

_POSITION_GROUPS = {
    "forward": {"ST", "LS", "RS", "LW", "RW", "LF", "RF", "CF"},
    "midfielder": {"CAM", "LAM", "RAM", "LM", "RM", "CM", "LCM", "RCM", "LDM", "CDM", "RDM"},
    "defender": {"LB", "RB", "LWB", "RWB", "CB", "LCB", "RCB"},
    "goalkeeper": {"GK"},
}


# ---------------------------------------------------------------------------
# Filtering helpers


def _filter_matches(
    data: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
) -> list:
    team_key = data.resolve_team(team) if team else None
    opp_key = data.resolve_team(opponent) if opponent else None
    if team and team_key is None:
        return []
    if opponent and opp_key is None:
        return []

    def _d(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    lo, hi = _d(date_from), _d(date_to)
    stage_re = None
    if stage:
        stage_key = normalize_name(stage)
        if stage_key:
            stage_re = re.compile(rf"\b{re.escape(stage_key)}")

    out = []
    for m in data.matches:
        if team_key is not None and not m.involves(team_key):
            continue
        if opp_key is not None and not m.involves(opp_key):
            continue
        if team_key is not None and opp_key is not None and m.home not in (
            team_key,
            opp_key,
        ):
            continue
        if competition is not None and not competition_matches(competition, m.competition):
            continue
        if season is not None and m.season != season:
            continue
        if lo is not None and m.date < lo:
            continue
        if hi is not None and m.date > hi:
            continue
        if stage_re is not None and not stage_re.search(normalize_name(m.round or "")):
            continue
        out.append(m)
    return out


def _record_for(data: SoccerData, m, team_key: str) -> str:
    if m.home_goals == m.away_goals:
        return "draw"
    winner_home = m.home_goals > m.away_goals
    if m.home == team_key:
        return "win" if winner_home else "loss"
    return "win" if not winner_home else "loss"


def _check_team(data: SoccerData, name: str) -> str | None:
    key = data.resolve_team(name)
    return key


# ---------------------------------------------------------------------------
# 1. Match queries


def find_matches(
    data: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    limit: int = 50,
) -> dict:
    """Find matches by team, opponent, competition, season or date range."""
    matches = _filter_matches(
        data, team, opponent, competition, season, date_from, date_to, stage
    )
    matches = sorted(matches, key=lambda m: m.date, reverse=True)
    shown = matches[: limit]
    return {
        "total": len(matches),
        "returned": len(shown),
        "matches": [_match_dict(data, m) for m in shown],
    }


def _match_dict(data: SoccerData, m) -> dict:
    d = m.to_dict()
    d["home_display"] = data.display(m.home)
    d["away_display"] = data.display(m.away)
    d["score"] = f"{m.home_goals}-{m.away_goals}"
    if m.stats:
        d["stats"] = m.stats
    return d


def last_match(data: SoccerData, team: str, opponent: str | None = None) -> dict:
    """Most recent match for a team (optionally vs a specific opponent)."""
    key = _check_team(data, team)
    if key is None:
        return {"error": f"Unknown team: {team}"}
    matches = _filter_matches(data, team=key, opponent=opponent)
    if not matches:
        return {"error": "No matches found"}
    m = max(matches, key=lambda m: m.date)
    return _match_dict(data, m)


def head_to_head(
    data: SoccerData, team_a: str, team_b: str, competition: str | None = None
) -> dict:
    """Head-to-head record between two teams."""
    a = _check_team(data, team_a)
    b = _check_team(data, team_b)
    if a is None or b is None:
        return {"error": f"Unknown team: {team_a if a is None else team_b}"}
    if a == b:
        return {"error": "Teams must differ"}
    matches = _filter_matches(data, team=a, opponent=b, competition=competition)
    wins = {a: 0, b: 0}
    draws = 0
    for m in matches:
        result = _record_for(data, m, a)
        if result == "win":
            wins[a] += 1
        elif result == "loss":
            wins[b] += 1
        else:
            draws += 1
    return {
        "team_a": data.display(a),
        "team_b": data.display(b),
        "total_matches": len(matches),
        f"{data.display(a)} wins": wins[a],
        f"{data.display(b)} wins": wins[b],
        "draws": draws,
        "matches": [_match_dict(data, m) for m in sorted(matches, key=lambda m: m.date)[-20:]],
    }


# ---------------------------------------------------------------------------
# 2. Team queries


def team_stats(
    data: SoccerData,
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
) -> dict:
    """Win/draw/loss record and goals for a team, optionally by season,
    competition and venue ("home", "away" or both)."""
    key = _check_team(data, team)
    if key is None:
        return {"error": f"Unknown team: {team}"}
    matches = _filter_matches(data, team=key, season=season, competition=competition)
    if venue and venue.lower() in ("home", "away"):
        v = venue.lower()
        matches = [m for m in matches if getattr(m, v) == key]
    wins = draws = losses = gf = ga = 0
    home_w = home_d = home_l = 0
    away_w = away_d = away_l = 0
    for m in matches:
        r = _record_for(data, m, key)
        if r == "win":
            wins += 1
        elif r == "draw":
            draws += 1
        else:
            losses += 1
        bucket = [home_w, home_d, home_l] if m.home == key else [away_w, away_d, away_l]
        bucket[{"win": 0, "draw": 1, "loss": 2}[r]] += 1
        if m.home == key:
            gf += m.home_goals
            ga += m.away_goals
            home_w, home_d, home_l = bucket
        else:
            gf += m.away_goals
            ga += m.home_goals
            away_w, away_d, away_l = bucket
    out = {
        "team": data.display(key),
        "season": season,
        "competition": competition,
        "venue": venue or "all",
        "matches": len(matches),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "win_rate": round(wins / len(matches) * 100, 1) if matches else 0,
        "home_record": {"w": home_w, "d": home_d, "l": home_l},
        "away_record": {"w": away_w, "d": away_d, "l": away_l},
    }
    return out


def team_competitions(data: SoccerData, team: str) -> dict:
    """Competitions a team appears in, with match counts."""
    key = _check_team(data, team)
    if key is None:
        return {"error": f"Unknown team: {team}"}
    counts: dict[str, int] = defaultdict(int)
    for m in data.matches:
        if m.involves(key):
            counts[m.competition] += 1
    return {"team": data.display(key), "competitions": dict(counts)}


def best_record(
    data: SoccerData,
    venue: str = "home",
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 10,
    limit: int = 10,
) -> dict:
    """Teams with the best home (or away) records by win rate."""
    tally: dict[str, dict] = defaultdict(lambda: {"m": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0})
    for m in data.matches:
        if competition is not None and not competition_matches(competition, m.competition):
            continue
        if season is not None and m.season != season:
            continue
        if venue == "home":
            team, gf, ga = m.home, m.home_goals, m.away_goals
        else:
            team, gf, ga = m.away, m.away_goals, m.home_goals
        t = tally[team]
        t["m"] += 1
        t["gf"] += gf
        t["ga"] += ga
        if gf > ga:
            t["w"] += 1
        elif gf == ga:
            t["d"] += 1
        else:
            t["l"] += 1
    ranked = []
    for team, t in tally.items():
        if t["m"] < min_matches:
            continue
        ranked.append(
            {
                "team": data.display(team),
                "matches": t["m"],
                "wins": t["w"],
                "draws": t["d"],
                "losses": t["l"],
                "goals_for": t["gf"],
                "goals_against": t["ga"],
                "win_rate": round(t["w"] / t["m"] * 100, 1),
            }
        )
    ranked.sort(key=lambda r: (-r["win_rate"], -r["matches"]))
    return {"venue": venue, "teams": ranked[:limit]}


# ---------------------------------------------------------------------------
# 3. Player queries


def search_players(
    data: SoccerData,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int = 0,
    limit: int = 20,
) -> dict:
    """Search FIFA player data by name/nationality/club/position/rating."""
    from soccer.normalize import normalize_player_name

    name_key = normalize_player_name(name) if name else None
    nat_key = normalize_name(nationality) if nationality else None
    club_key = normalize_name(club) if club else None
    pos = (position or "").strip().upper()

    out = []
    for p in data.players:
        if name_key and name_key not in p.name_key:
            continue
        if nat_key and nat_key not in p.nationality_key:
            continue
        if club_key and (p.club_key is None or club_key not in p.club_key):
            continue
        if pos:
            wanted = _POSITION_GROUPS.get(pos.lower(), {pos})
            if p.position not in wanted:
                continue
        if p.overall < min_overall:
            continue
        out.append(p)
    out.sort(key=lambda p: (-p.overall, p.name))
    return {
        "total": len(out),
        "returned": min(len(out), limit),
        "players": [p.to_dict() for p in out[:limit]],
    }


def brazilian_players_by_club(data: SoccerData, limit: int = 15) -> dict:
    """Brazilian nationality players grouped by club (Brazilian clubs only)."""
    brazilian_teams = set()
    for m in data.matches:
        if "Brasileir" in m.competition or "Série" in m.competition or m.competition == "Copa do Brasil":
            brazilian_teams.update((m.home, m.away))
    clubs: dict[str, list] = defaultdict(list)
    for p in data.players:
        if p.nationality_key != "brazil":
            continue
        if not p.club_key or p.club_key not in brazilian_teams:
            continue
        clubs[p.club_key].append(p)
    summary = []
    for club_key, group in clubs.items():
        summary.append(
            {
                "club": group[0].club,
                "players": len(group),
                "avg_overall": round(sum(x.overall for x in group) / len(group), 1),
                "top_player": max(group, key=lambda x: x.overall).name,
            }
        )
    summary.sort(key=lambda c: (-c["players"], -c["avg_overall"]))
    return {"clubs": summary[:limit]}


# ---------------------------------------------------------------------------
# 4. Competition queries


def standings(
    data: SoccerData,
    season: int,
    competition: str = "Brasileirão",
    limit: int | None = None,
) -> dict:
    """League table calculated from match results (3 points per win)."""
    table: dict[str, dict] = defaultdict(
        lambda: {"pts": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "mp": 0}
    )
    for m in data.matches:
        if m.season != season or not competition_matches(competition, m.competition):
            continue
        for team, gf, ga in ((m.home, m.home_goals, m.away_goals), (m.away, m.away_goals, m.home_goals)):
            row = table[team]
            row["mp"] += 1
            row["gf"] += gf
            row["ga"] += ga
            if gf > ga:
                row["w"] += 1
                row["pts"] += 3
            elif gf == ga:
                row["d"] += 1
                row["pts"] += 1
            else:
                row["l"] += 1
    rows = [
        {
            "position": i,
            "team": data.display(team),
            "points": row["pts"],
            "matches": row["mp"],
            "wins": row["w"],
            "draws": row["d"],
            "losses": row["l"],
            "goals_for": row["gf"],
            "goals_against": row["ga"],
            "goal_diff": row["gf"] - row["ga"],
        }
        for i, (team, row) in enumerate(
            sorted(table.items(), key=lambda kv: (-kv[1]["pts"], kv[1]["gf"] - kv[1]["ga"])), 1
        )
    ]
    if rows:
        rows[0]["champion"] = True
    if limit:
        rows = rows[:limit]
    return {"season": season, "competition": competition, "standings": rows}


def relegated(data: SoccerData, season: int, competition: str = "Brasileirão", n: int = 4) -> dict:
    """Bottom n teams of a season (relegation zone)."""
    table = standings(data, season, competition, limit=None)
    rows = table["standings"][-n:]
    for row in rows:
        row["relegated"] = True
    return {"season": season, "relegated": rows}


def competition_seasons(data: SoccerData, competition: str) -> dict:
    """Seasons covered by a competition."""
    seasons = sorted(
        {m.season for m in data.matches if competition_matches(competition, m.competition) and m.season}
    )
    return {"competition": competition, "seasons": seasons}


# ---------------------------------------------------------------------------
# 5. Statistical analysis


def biggest_wins(data: SoccerData, competition: str | None = None, limit: int = 10) -> dict:
    """Largest goal-margin victories."""
    candidates = [
        m
        for m in data.matches
        if competition is None or competition_matches(competition, m.competition)
    ]
    candidates.sort(key=lambda m: (abs(m.home_goals - m.away_goals), m.total_goals()), reverse=True)
    out = []
    for m in candidates[:limit]:
        d = _match_dict(data, m)
        d["margin"] = abs(m.home_goals - m.away_goals)
        out.append(d)
    return {"biggest_wins": out}


def goals_statistics(data: SoccerData, competition: str | None = None) -> dict:
    """Average goals per match plus home/away win rates."""
    matches = [
        m
        for m in data.matches
        if competition is None or competition_matches(competition, m.competition)
    ]
    if not matches:
        return {"error": "No matches found"}
    total = sum(m.total_goals() for m in matches)
    home_wins = sum(1 for m in matches if m.home_goals > m.away_goals)
    away_wins = sum(1 for m in matches if m.away_goals > m.home_goals)
    draws = len(matches) - home_wins - away_wins
    n = len(matches)
    return {
        "competition": competition or "all",
        "matches": n,
        "total_goals": total,
        "avg_goals_per_match": round(total / n, 2),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / n * 100, 1),
        "away_win_rate": round(away_wins / n * 100, 1),
        "draw_rate": round(draws / n * 100, 1),
    }


def season_comparison(data: SoccerData, season_a: int, season_b: int, competition: str | None = None) -> dict:
    """Compare aggregate statistics between two seasons."""
    def agg(season: int) -> dict:
        ms = [
            m
            for m in data.matches
            if m.season == season
            and (competition is None or competition_matches(competition, m.competition))
        ]
        if not ms:
            return {"matches": 0}
        return {
            "matches": len(ms),
            "avg_goals_per_match": round(sum(m.total_goals() for m in ms) / len(ms), 2),
            "home_win_rate": round(
                sum(1 for m in ms if m.home_goals > m.away_goals) / len(ms) * 100, 1
            ),
        }

    return {"season_a": season_a, "stats_a": agg(season_a), "season_b": season_b, "stats_b": agg(season_b)}


def find_derbies(data: SoccerData, season: int | None = None, limit: int = 50) -> dict:
    """Find derby matches between traditional rivals."""
    pairs = set()
    for a, b in _DERBY_NAMES:
        ka, kb = data.resolve_team(a), data.resolve_team(b)
        if ka and kb:
            pairs.add(frozenset((ka, kb)))
    out = []
    for m in data.matches:
        if season is not None and m.season != season:
            continue
        if frozenset((m.home, m.away)) in pairs:
            out.append(m)
    out.sort(key=lambda m: m.date, reverse=True)
    return {"total": len(out), "matches": [_match_dict(data, m) for m in out[:limit]]}
