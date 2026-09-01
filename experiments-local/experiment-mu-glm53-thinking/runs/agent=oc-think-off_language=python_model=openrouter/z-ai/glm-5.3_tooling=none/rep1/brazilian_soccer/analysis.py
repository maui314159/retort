"""Query and analysis functions backing the MCP tools."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .loader import Match, Player, SoccerData, group_key

_COMPETITION_ALIASES = {
    "brasileirao": "Brasileirão",
    "brasileirão": "Brasileirão",
    "serie a (2003-2019)": "Brasileirão (2003-2019)",
    "brazilian cup": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
}


def _comp_key(comp: str) -> str:
    comp = (comp or "").strip().lower()
    return _COMPETITION_ALIASES.get(comp, comp)


def _match_dict(m: Match) -> dict[str, Any]:
    d = asdict(m)
    d["date"] = m.date.isoformat() if m.date else None
    d["score"] = f"{m.home_goal}-{m.away_goal}"
    return d


def find_matches(
    data: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str = "any",  # any | home | away
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Find matches by team, opponent, competition, season, or date range."""
    tkeys = data.keys_for(team) if team else None
    okeys = data.keys_for(opponent) if opponent else None
    comp = _comp_key(competition) if competition else None
    results = []
    for m in data.matches:
        if tkeys:
            home_hit = bool(data.keys_for(m.home) & tkeys)
            away_hit = bool(data.keys_for(m.away) & tkeys)
            if venue == "home" and not home_hit:
                continue
            if venue == "away" and not away_hit:
                continue
            if venue not in ("home", "away") and not (home_hit or away_hit):
                continue
        if okeys and not (
            data.keys_for(m.home) & okeys or data.keys_for(m.away) & okeys
        ):
            continue
        if comp and _comp_key(m.competition) != comp:
            continue
        if season is not None and m.season != season:
            continue
        if date_from and (m.date is None or m.date.isoformat() < date_from):
            continue
        if date_to and (m.date is None or m.date.isoformat() > date_to):
            continue
        results.append(m)
    results.sort(key=lambda m: (m.date is None, m.date), reverse=True)
    return [_match_dict(m) for m in results[:limit]]


def _record(data: SoccerData, matches: list[Match], tkeys: frozenset[str]) -> dict[str, Any]:
    wins = draws = losses = gf = ga = 0
    home_matches = away_matches = 0
    for m in matches:
        if data.keys_for(m.home) & tkeys:
            home_matches += 1
            gf += m.home_goal
            ga += m.away_goal
            if m.home_goal > m.away_goal:
                wins += 1
            elif m.home_goal == m.away_goal:
                draws += 1
            else:
                losses += 1
        else:
            away_matches += 1
            gf += m.away_goal
            ga += m.home_goal
            if m.away_goal > m.home_goal:
                wins += 1
            elif m.home_goal == m.away_goal:
                draws += 1
            else:
                losses += 1
    total = wins + draws + losses
    return {
        "matches": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "home_matches": home_matches,
        "away_matches": away_matches,
        "win_rate": round(wins / total * 100, 1) if total else 0.0,
    }


def team_stats(
    data: SoccerData,
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "any",
) -> dict[str, Any]:
    """Win/loss/draw record, goals, and per-venue split for a team."""
    tkeys = data.keys_for(team)
    comp = _comp_key(competition) if competition else None
    matches = []
    for m in data.matches_for_team(team):
        if season is not None and m.season != season:
            continue
        if comp and _comp_key(m.competition) != comp:
            continue
        home_hit = bool(data.keys_for(m.home) & tkeys)
        away_hit = bool(data.keys_for(m.away) & tkeys)
        if venue == "home" and not home_hit:
            continue
        if venue == "away" and not away_hit:
            continue
        matches.append(m)
    display = data.resolve_team(team) or team
    overall = _record(data, matches, tkeys)
    home_only = [m for m in matches if data.keys_for(m.home) & tkeys]
    away_only = [m for m in matches if data.keys_for(m.away) & tkeys]
    return {
        "team": display,
        "season": season,
        "competition": competition,
        "venue": venue,
        "overall": overall,
        "home": _record(data, home_only, tkeys),
        "away": _record(data, away_only, tkeys),
    }


def head_to_head(
    data: SoccerData,
    team: str,
    opponent: str,
    competition: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Head-to-head record between two teams across the dataset."""
    tkeys = data.keys_for(team)
    okeys = data.keys_for(opponent)
    comp = _comp_key(competition) if competition else None
    matches = [
        m
        for m in data.matches
        if (
            bool(data.keys_for(m.home) & tkeys) != bool(data.keys_for(m.home) & okeys)
            or bool(data.keys_for(m.away) & tkeys) != bool(data.keys_for(m.away) & okeys)
        )
        and (
            (bool(data.keys_for(m.home) & tkeys) or bool(data.keys_for(m.away) & tkeys))
            and (bool(data.keys_for(m.home) & okeys) or bool(data.keys_for(m.away) & okeys))
        )
        and (comp is None or _comp_key(m.competition) == comp)
    ]
    matches.sort(key=lambda m: (m.date is None, m.date))
    team_wins = opp_wins = draws = 0
    for m in matches:
        winner = m.winner
        if winner == "draw":
            draws += 1
        else:
            home_is_team = bool(data.keys_for(m.home) & tkeys)
            scorer = "home" if home_is_team else "away"
            loser = "away" if home_is_team else "home"
            if winner == scorer:
                team_wins += 1
            else:
                opp_wins += 1
    return {
        "team": data.resolve_team(team) or team,
        "opponent": data.resolve_team(opponent) or opponent,
        "competition": competition,
        "total_matches": len(matches),
        "team_wins": team_wins,
        "opponent_wins": opp_wins,
        "draws": draws,
        "matches": [_match_dict(m) for m in matches[-limit:]],
    }


def standings(
    data: SoccerData,
    season: int,
    competition: str = "Brasileirão",
) -> list[dict[str, Any]]:
    """League table computed from match results (3 points per win)."""
    comp = _comp_key(competition)
    table: dict[str, dict[str, Any]] = {}
    for m in data.matches:
        if m.season != season or _comp_key(m.competition) != comp:
            continue
        for name in (m.home, m.away):
            key = group_key(name)
            if key not in table:
                table[key] = {
                    "team": name,
                    "points": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                }
        h = table[group_key(m.home)]
        a = table[group_key(m.away)]
        h["goals_for"] += m.home_goal
        h["goals_against"] += m.away_goal
        a["goals_for"] += m.away_goal
        a["goals_against"] += m.home_goal
        if m.home_goal > m.away_goal:
            h["points"] += 3
            h["wins"] += 1
            a["losses"] += 1
        elif m.home_goal < m.away_goal:
            a["points"] += 3
            a["wins"] += 1
            h["losses"] += 1
        else:
            h["points"] += 1
            a["points"] += 1
            h["draws"] += 1
            a["draws"] += 1
    rows = list(table.values())
    for row in rows:
        row["goal_diff"] = row["goals_for"] - row["goals_against"]
        row["matches"] = row["wins"] + row["draws"] + row["losses"]
    rows.sort(key=lambda r: (-r["points"], -r["goal_diff"], -r["goals_for"]))
    return rows


def biggest_wins(
    data: SoccerData,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Largest goal-margin victories in the dataset."""
    comp = _comp_key(competition) if competition else None
    matches = [
        m
        for m in data.matches
        if (comp is None or _comp_key(m.competition) == comp)
        and (season is None or m.season == season)
    ]
    matches.sort(key=lambda m: abs(m.home_goal - m.away_goal), reverse=True)
    out = []
    for m in matches[:limit]:
        out.append({**_match_dict(m), "margin": abs(m.home_goal - m.away_goal)})
    return out


def average_goals(
    data: SoccerData,
    competition: str | None = None,
    season: int | None = None,
) -> dict[str, Any]:
    """Average goals per match and home/away win rates."""
    comp = _comp_key(competition) if competition else None
    matches = [
        m
        for m in data.matches
        if (comp is None or _comp_key(m.competition) == comp)
        and (season is None or m.season == season)
    ]
    if not matches:
        return {"matches": 0}
    goals = sum(m.home_goal + m.away_goal for m in matches)
    home_wins = sum(1 for m in matches if m.winner == "home")
    away_wins = sum(1 for m in matches if m.winner == "away")
    draws = sum(1 for m in matches if m.winner == "draw")
    n = len(matches)
    return {
        "matches": n,
        "total_goals": goals,
        "avg_goals_per_match": round(goals / n, 2),
        "home_win_rate": round(home_wins / n * 100, 1),
        "away_win_rate": round(away_wins / n * 100, 1),
        "draw_rate": round(draws / n * 100, 1),
    }


def search_players(
    data: SoccerData,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    sort_by_rating: bool = True,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Search FIFA player data by name, nationality, club, position, rating."""
    results: list[Player] = []
    name_q = group_key(name or "") if name else None
    nationality_q = (nationality or "").strip().lower()
    club_q = data.keys_for(club) if club else None
    position_q = (position or "").strip().upper()
    for p in data.players:
        if name_q and name_q not in group_key(p.name):
            continue
        if nationality_q and p.nationality.strip().lower() != nationality_q:
            continue
        if club_q and not (data.keys_for(p.club) & club_q):
            continue
        if position_q and p.position.strip().upper() != position_q:
            continue
        if min_overall is not None and p.overall < min_overall:
            continue
        if max_overall is not None and p.overall > max_overall:
            continue
        results.append(p)
    if sort_by_rating:
        results.sort(key=lambda p: (-p.overall, p.name))
    return [asdict(p) for p in results[:limit]]


# Known Brazilian clubs to map FIFA club names against match data.
BRAZILIAN_CLUBS = [
    "Flamengo", "Palmeiras", "Corinthians", "São Paulo", "Santos",
    "Grêmio", "Internacional", "Fluminense", "Atlético Mineiro",
    "Cruzeiro", "Vasco da Gama", "Botafogo", "Bahia", "Sport Recife",
    "Fortaleza", "Athletico Paranaense", "Goiás", "Coritiba", "Ceará",
    "Chapecoense", "Avaí", "Bragantino", "Cuiabá", "Juventude",
    "Atlético Goianiense", "América Mineiro", "Vitória", "Ponte Preta",
]


def brazilian_club_summary(data: SoccerData) -> list[dict[str, Any]]:
    """Count and average rating of players per Brazilian club (cross-file query)."""
    out = []
    for club in BRAZILIAN_CLUBS:
        squad = data.players_at_club(club)
        if squad:
            out.append(
                {
                    "club": club,
                    "players": len(squad),
                    "avg_rating": round(
                        sum(p.overall for p in squad) / len(squad), 1
                    ),
                }
            )
    out.sort(key=lambda r: -r["players"])
    return out
