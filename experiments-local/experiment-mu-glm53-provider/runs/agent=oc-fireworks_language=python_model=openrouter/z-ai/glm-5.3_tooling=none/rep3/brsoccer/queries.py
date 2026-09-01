"""Query engine over :class:`~brsoccer.data.SoccerData`.

Every function takes the loaded :class:`SoccerData` container as its
first argument and returns plain data structures (lists of
:class:`~brsoccer.models.Match` / :class:`~brsoccer.models.Player` /
dicts).  Presentation lives in :mod:`brsoccer.formatting`; MCP wiring in
:mod:`brsoccer.mcp_server`.

Team arguments accept any spelling variant ("Palmeiras-SP",
"ATHLETICO PARANAENSE", "Red Bull Bragantino") and are resolved through
the team registry; ambiguous names (e.g. bare "Santos") resolve to the
club with the most recorded matches, and callers can surface the other
candidates via :func:`alternatives_note`.
"""

from __future__ import annotations

import re
from datetime import date

from .data import COMPETITIONS, LEAGUES, SoccerData, canonical_competition
from .dates import parse_date
from .models import Match, Player, TableRow
from .normalize import _preprocess

# Famous derbies (Clássicos) with their canonical display names; team
# spellings are resolved through the registry at query time.
DERBIES: list[tuple[str, str, str]] = [
    ("Fla-Flu", "Flamengo", "Fluminense"),
    ("Clássico dos Milhões", "Flamengo", "Vasco"),
    ("Clássico Majestoso", "Corinthians", "Palmeiras"),
    ("Choque-Rei", "Corinthians", "São Paulo"),
    ("San-São", "Santos", "São Paulo"),
    ("GreNal", "Grêmio", "Internacional"),
    ("Atletiba", "Athletico Paranaense", "Coritiba"),
    ("Ba-Vi", "Bahia", "Vitória"),
]


class QueryError(ValueError):
    """Raised for unresolvable team/competition/season arguments."""

    def __init__(self, message: str, candidates: list[str] | None = None) -> None:
        super().__init__(message)
        self.candidates = candidates or []


#: Endonyms/variants for nationality filters ("Brasil" == "Brazil").
_NATIONALITY_ALIASES = {
    "brasil": "brazil",
    "brasilian": "brazil",
    "brasilianas": "brazil",
    "holland": "netherlands",
    "usa": "united states",
    "argentina republica": "argentina",
}


def _norm_nationality(text: str) -> str:
    norm = _preprocess(text)
    return _NATIONALITY_ALIASES.get(norm, norm)


# ------------------------------------------------------------------ helpers


def resolve_team(sd: SoccerData, name: str) -> str:
    """Resolve a user-supplied team name to a canonical registry key."""
    if not name or not name.strip():
        raise QueryError("A team name is required.")
    resolution = sd.registry.resolve_one(name)
    if resolution is None or sd.registry.entry_of(resolution.key) is None:
        close = sd.registry.resolve(name, limit=5)
        raise QueryError(
            f"No team found for '{name}'. Try one of: "
            + (", ".join(r.display for r in close) if close else "Flamengo, Palmeiras, Corinthians, ...")
        )
    return resolution.key


def alternatives_note(sd: SoccerData, name: str) -> str:
    """Other teams that also matched the name (for disambiguation)."""
    return sd.registry.alternatives_note(name)


def _resolve_competition(competition: str | None, default: str | None = None) -> str | None:
    code = canonical_competition(competition) if competition else default
    if competition and code is None:
        raise QueryError(
            f"Unknown competition '{competition}'. Valid: {', '.join(sorted(COMPETITIONS))} "
            "(aliases like 'brasileirao' or 'copa' also work)."
        )
    return code


def _parse_date_arg(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return parse_date(str(value))


def _norm_stage_token(token: str) -> str:
    """Normalise one stage word: lowercase, de-accent, singularise."""
    token = _preprocess(token)
    if token.endswith("s") and len(token) > 4:
        token = token[:-1]
    return token


def _stage_matches(match_stage: str, wanted: str, competition: str | None) -> bool:
    """Stage filter: word-boundary match on round/stage text.

    'final' must match the final but NOT 'quarterfinals'/'semifinals';
    'group' matches 'group stage'; '16' matches 'round of 16'.  The Copa
    do Brasil dataset numbers its final as round "8", so asking for
    'final' there matches round 8.
    """
    if not wanted:
        return True
    w = _norm_stage_token(wanted)
    stage = _preprocess(match_stage or "")
    if not stage:
        return False
    if stage == w:
        return True
    if w == "final" and competition == "copa_do_brasil" and stage == "8":
        return True
    if re.search(rf"\b{re.escape(w)}\b", stage):
        return True
    return w in [_norm_stage_token(tok) for tok in stage.split()]


# ------------------------------------------------------------------ matches


def find_matches(
    sd: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    stage: str | None = None,
    limit: int | None = None,
) -> list[Match]:
    """Search matches by team, opponent, competition, season, dates, stage."""
    team_key = resolve_team(sd, team) if team else None
    opponent_key = resolve_team(sd, opponent) if opponent else None
    code = _resolve_competition(competition)
    start = _parse_date_arg(date_from)
    end = _parse_date_arg(date_to)

    results: list[Match] = []
    pool = sd.matches_for_competition(code) if code else sd.matches
    for match in pool:
        if team_key and not match.involves(team_key):
            continue
        if opponent_key and not match.involves(opponent_key):
            continue
        if team_key and opponent_key and not match.is_between(team_key, opponent_key):
            continue
        if season is not None and match.season != season:
            continue
        if start and (match.date is None or match.date < start):
            continue
        if end and (match.date is None or match.date > end):
            continue
        if not _stage_matches(match.stage, stage, code):
            continue
        results.append(match)
    results.sort(key=lambda m: m.sort_key(), reverse=True)  # most recent first
    return results[:limit] if limit else results


def last_match(sd: SoccerData, team: str, opponent: str | None = None) -> Match | None:
    """Most recent recorded match of a team (optionally vs an opponent)."""
    matches = find_matches(sd, team=team, opponent=opponent)
    return matches[0] if matches else None


def head_to_head(
    sd: SoccerData,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Head-to-head record between two teams across the dataset."""
    key_a = resolve_team(sd, team_a)
    key_b = resolve_team(sd, team_b)
    code = _resolve_competition(competition)
    matches = [
        m
        for m in sd.matches
        if m.is_between(key_a, key_b)
        and (code is None or m.competition == code)
        and (season is None or m.season == season)
    ]
    matches.sort(key=lambda m: m.sort_key(), reverse=True)
    record = {key_a: 0, key_b: 0, "draws": 0}
    goals = {key_a: 0, key_b: 0}
    for match in matches:
        if not match.played:
            continue
        goals[match.home] += match.home_goal
        goals[match.away] += match.away_goal
        result_a = match.result_for(key_a)
        if result_a == "W":
            record[key_a] += 1
        elif result_a == "L":
            record[key_b] += 1
        else:
            record["draws"] += 1
    return {
        "team_a": key_a,
        "team_a_display": sd.team_display(key_a),
        "team_b": key_b,
        "team_b_display": sd.team_display(key_b),
        "matches": matches,
        "wins_a": record[key_a],
        "wins_b": record[key_b],
        "draws": record["draws"],
        "goals_a": goals[key_a],
        "goals_b": goals[key_b],
    }


# ------------------------------------------------------------------ teams


def _team_record(matches: list[Match], key: str, venue: str = "all") -> dict:
    """Aggregate W/D/L and goals for one team from its matches."""
    stats = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "unplayed": 0}
    for match in matches:
        if venue == "home" and match.home != key:
            continue
        if venue == "away" and match.away != key:
            continue
        stats["matches"] += 1
        if not match.played:
            stats["unplayed"] += 1
            continue
        own, other = (
            (match.home_goal, match.away_goal) if match.home == key else (match.away_goal, match.home_goal)
        )
        stats["goals_for"] += own
        stats["goals_against"] += other
        if own > other:
            stats["wins"] += 1
        elif own < other:
            stats["losses"] += 1
        else:
            stats["draws"] += 1
    played = stats["matches"] - stats["unplayed"]
    stats["win_rate"] = (stats["wins"] / played * 100.0) if played else 0.0
    return stats


def team_stats(
    sd: SoccerData,
    team: str,
    season: int | None = None,
    competition: str | None = None,
) -> dict:
    """Full record for a team: overall plus home/away splits."""
    key = resolve_team(sd, team)
    code = _resolve_competition(competition)
    pool = sd.matches_for_team(key)
    if code:
        pool = [m for m in pool if m.competition == code]
    if season is not None:
        pool = [m for m in pool if m.season == season]
    competitions = sorted({m.competition for m in pool})
    return {
        "key": key,
        "display": sd.team_display(key),
        "season": season,
        "competition": code,
        "competitions_seen": competitions,
        "overall": _team_record(pool, key, "all"),
        "home": _team_record(pool, key, "home"),
        "away": _team_record(pool, key, "away"),
        "matches": pool,
    }


def team_competitions(sd: SoccerData, team: str) -> list[dict]:
    """Competitions a team appears in, with match counts and season spans."""
    key = resolve_team(sd, team)
    out: list[dict] = []
    for code in sorted({m.competition for m in sd.matches_for_team(key)}):
        matches = [m for m in sd.matches_for_team(key) if m.competition == code]
        seasons = sorted({m.season for m in matches if m.season})
        out.append(
            {
                "competition": code,
                "display": COMPETITIONS[code],
                "matches": len(matches),
                "first_season": seasons[0] if seasons else None,
                "last_season": seasons[-1] if seasons else None,
            }
        )
    out.sort(key=lambda c: -c["matches"])
    return out


# ------------------------------------------------------------------ competitions


def _table(sd: SoccerData, code: str, season: int) -> list[TableRow]:
    """Compute a league table (points ranking) for one season."""
    accum: dict[str, dict[str, int]] = {}
    for match in sd.matches_for_competition(code):
        if match.season != season or not match.played:
            continue
        for key, own, other in (
            (match.home, match.home_goal, match.away_goal),
            (match.away, match.away_goal, match.home_goal),
        ):
            row = accum.setdefault(
                key, {"played": 0, "win": 0, "draw": 0, "loss": 0, "gf": 0, "ga": 0, "points": 0}
            )
            row["played"] += 1
            row["gf"] += own
            row["ga"] += other
            if own > other:
                row["win"] += 1
                row["points"] += 3
            elif own == other:
                row["draw"] += 1
                row["points"] += 1
            else:
                row["loss"] += 1
    ordered = sorted(
        accum.items(),
        key=lambda kv: (-kv[1]["points"], -(kv[1]["gf"] - kv[1]["ga"]), -kv[1]["gf"], kv[0]),
    )
    return [
        TableRow(
            position=rank,
            team=key,
            display=sd.team_display(key),
            played=row["played"],
            win=row["win"],
            draw=row["draw"],
            loss=row["loss"],
            goals_for=row["gf"],
            goals_against=row["ga"],
            points=row["points"],
        )
        for rank, (key, row) in enumerate(ordered, start=1)
    ]


def standings(sd: SoccerData, competition: str | None = "serie_a", season: int | None = None) -> list[TableRow]:
    """League standings computed from match results.

    Defaults to the most recent season available for the competition.
    Cups and Libertadores are knockout/group competitions -- standings
    are refused with a helpful error instead.
    """
    code = _resolve_competition(competition, default="serie_a")
    if code not in LEAGUES:
        raise QueryError(
            f"'{COMPETITIONS[code]}' is not a league, so standings do not apply. "
            "Ask for its finals/results instead (e.g. stage='final'), or use "
            "competition='serie_a' / 'serie_b'."
        )
    seasons = sd.seasons_for(code)
    if not seasons:
        raise QueryError(f"No matches loaded for {COMPETITIONS[code]}.")
    chosen = season if season is not None else seasons[-1]
    if chosen not in seasons:
        raise QueryError(
            f"No {COMPETITIONS[code]} data for season {chosen}. "
            f"Available seasons: {seasons[0]}-{seasons[-1]}"
        )
    return _table(sd, code, chosen)


def relegation(
    sd: SoccerData, competition: str | None = "serie_a", season: int | None = None, n: int = 4
) -> list[TableRow]:
    """Bottom ``n`` teams of a league table (default 4 relegated)."""
    table = standings(sd, competition, season)
    return table[-n:]


def competition_info(sd: SoccerData, competition: str | None = None) -> dict:
    """Coverage summary for one competition (or all when omitted)."""
    if competition is None:
        return {
            "competitions": [
                _competition_summary(sd, code) for code in sorted(COMPETITIONS)
            ],
        }
    code = _resolve_competition(competition)
    if code not in sd._by_comp or not sd.matches_for_competition(code):
        raise QueryError(f"No data loaded for '{competition}'.")
    return _competition_summary(sd, code)


def _competition_summary(sd: SoccerData, code: str) -> dict:
    matches = sd.matches_for_competition(code)
    seasons = sd.seasons_for(code)
    teams = {m.home for m in matches} | {m.away for m in matches}
    return {
        "code": code,
        "display": COMPETITIONS[code],
        "matches": len(matches),
        "seasons": seasons,
        "first_season": seasons[0] if seasons else None,
        "last_season": seasons[-1] if seasons else None,
        "teams": len(teams),
        "is_league": code in LEAGUES,
        "note": (
            "Round-robin league; standings available."
            if code in LEAGUES
            else "Knockout/two-leg format; use stage filters (e.g. 'final') instead of standings."
        ),
    }


# ------------------------------------------------------------------ players


def search_players(
    sd: SoccerData,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int | None = 20,
) -> list[Player]:
    """Search the FIFA player database by name/nationality/club/position."""
    if not any((name, nationality, club, position, min_overall, max_overall)):
        raise QueryError(
            "Provide at least one filter (name, nationality, club, position, min_overall)."
        )
    name_norm = _preprocess(name) if name else None
    nat_norm = _norm_nationality(nationality) if nationality else None
    pos_norm = _preprocess(position) if position else None
    club_key = sd.registry.key_of(club) if club else None
    club_entry = sd.registry.entry_of(club_key) if club_key else None
    club_norm = _preprocess(club) if club else None

    def _name_ok(player: Player) -> bool:
        if name_norm in _preprocess(player.name):
            return True
        # Fallback for "full name" queries whose exact form is absent:
        # match on any distinctive query word ("Gabriel Barbosa" -> Gabriel).
        words = [w for w in name_norm.split() if len(w) > 3]
        if not words:
            return False
        player_name = _preprocess(player.name)
        return any(w in player_name for w in words) and len(words) > 1

    results: list[Player] = []
    for player in sd.players:
        if name_norm and not _name_ok(player):
            continue
        if nat_norm and nat_norm != _norm_nationality(player.nationality):
            continue
        if pos_norm and pos_norm not in _preprocess(player.position):
            continue
        if min_overall is not None and player.overall < min_overall:
            continue
        if max_overall is not None and player.overall > max_overall:
            continue
        if club_norm:
            if club_entry is not None:
                # Brazilian club: join through the canonical registry key.
                if player.club_key != club_key:
                    continue
            else:
                # Any other club: match the FIFA spelling (exact, then substring).
                player_club = _preprocess(player.club)
                if player_club != club_norm and club_norm not in player_club:
                    continue
        results.append(player)
    results.sort(key=lambda p: (-p.overall, p.name))
    return results[:limit] if limit else results


def club_overview(sd: SoccerData, nationality: str = "Brazil") -> list[dict]:
    """Players of ``nationality`` grouped by their (Brazilian) clubs."""
    nat_norm = _norm_nationality(nationality)
    groups: dict[str, dict] = {}
    for player in sd.players:
        if _norm_nationality(player.nationality) != nat_norm:
            continue
        key = player.club_key
        if key is None or not sd.is_brazilian_team(key):
            continue
        group = groups.setdefault(
            key, {"key": key, "display": sd.team_display(key), "players": [], "overall": []}
        )
        group["players"].append(player)
        group["overall"].append(player.overall)
    out = []
    for key, group in groups.items():
        out.append(
            {
                "key": key,
                "display": group["display"],
                "count": len(group["players"]),
                "avg_overall": sum(group["overall"]) / len(group["overall"]),
                "best": max(group["players"], key=lambda p: (p.overall, p.name)),
            }
        )
    out.sort(key=lambda g: (-g["count"], -g["avg_overall"]))
    return out


# ------------------------------------------------------------------ statistics


def _played_pool(sd: SoccerData, competition: str | None, season: int | None) -> list[Match]:
    code = _resolve_competition(competition)
    pool = sd.matches_for_competition(code) if code else sd.matches
    if season is not None:
        pool = [m for m in pool if m.season == season]
    return [m for m in pool if m.played]


def competition_stats(
    sd: SoccerData, competition: str | None = None, season: int | None = None
) -> dict:
    """Average goals, home/draw/away win rates for a (competition, season)."""
    pool = _played_pool(sd, competition, season)
    if not pool:
        return {"matches": 0, "avg_goals": 0.0, "home_win_rate": 0.0, "draw_rate": 0.0, "away_win_rate": 0.0}
    goals = sum(m.total_goals or 0 for m in pool)
    home_wins = sum(1 for m in pool if m.home_goal > m.away_goal)
    away_wins = sum(1 for m in pool if m.home_goal < m.away_goal)
    draws = len(pool) - home_wins - away_wins
    n = len(pool)
    return {
        "matches": n,
        "avg_goals": goals / n,
        "total_goals": goals,
        "home_win_rate": home_wins / n * 100.0,
        "draw_rate": draws / n * 100.0,
        "away_win_rate": away_wins / n * 100.0,
    }


def biggest_wins(
    sd: SoccerData,
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 10,
) -> list[Match]:
    """Largest goal-margin victories, newest first among equal margins."""
    key = resolve_team(sd, team) if team else None
    pool = _played_pool(sd, competition, season)
    if key:
        pool = [m for m in pool if m.involves(key)]
    pool.sort(key=lambda m: (-(m.margin or 0), m.sort_key()))
    return pool[:limit]


def best_records(
    sd: SoccerData,
    venue: str = "home",
    competition: str | None = None,
    season: int | None = None,
    min_matches: int = 10,
    limit: int = 10,
) -> list[dict]:
    """Rank teams by win rate at a venue (overall/home/away)."""
    if venue not in ("home", "away", "all"):
        raise QueryError("venue must be 'home', 'away' or 'all'.")
    code = _resolve_competition(competition)
    pool = sd.matches_for_competition(code) if code else sd.matches
    if season is not None:
        pool = [m for m in pool if m.season == season]
    teams = {m.home for m in pool} | {m.away for m in pool}
    ranked = []
    for key in teams:
        stats = _team_record(pool, key, venue)
        if stats["matches"] - stats["unplayed"] < min_matches:
            continue
        ranked.append({"key": key, "display": sd.team_display(key), **stats})
    ranked.sort(key=lambda r: (-r["win_rate"], -r["matches"], r["display"]))
    return ranked[:limit]


def derbies(
    sd: SoccerData, season: int | None = None, competition: str | None = None
) -> list[tuple[str, list[Match]]]:
    """Notable derby matches (Fla-Flu, GreNal, ...) for a season/competition."""
    code = _resolve_competition(competition)
    results: list[tuple[str, list[Match]]] = []
    for derby_name, team_a, team_b in DERBIES:
        try:
            key_a = resolve_team(sd, team_a)
            key_b = resolve_team(sd, team_b)
        except QueryError:  # pragma: no cover - registry always has these
            continue
        matches = [
            m
            for m in sd.matches
            if m.is_between(key_a, key_b)
            and (season is None or m.season == season)
            and (code is None or m.competition == code)
        ]
        if matches:
            matches.sort(key=lambda m: m.sort_key(), reverse=True)
            results.append((derby_name, matches))
    return results


def data_summary(sd: SoccerData) -> dict:
    """Dataset coverage overview (all six CSV files)."""
    per_competition = {code: _competition_summary(sd, code) for code in sorted(COMPETITIONS)}
    return {
        "total_matches": len(sd.matches),
        "total_players": len(sd.players),
        "total_teams": len(sd.registry.entries),
        "match_date_range": [
            str(min((m.date for m in sd.matches if m.date), default=date.min)),
            str(max((m.date for m in sd.matches if m.date), default=date.max)),
        ],
        "player_nationalities": len({p.nationality for p in sd.players}),
        "brazilian_players": sum(1 for p in sd.players if _preprocess(p.nationality) == "brazil"),
        "competitions": per_competition,
    }


__all__ = [
    "QueryError",
    "DERBIES",
    "resolve_team",
    "find_matches",
    "last_match",
    "head_to_head",
    "team_stats",
    "team_competitions",
    "standings",
    "relegation",
    "competition_info",
    "search_players",
    "club_overview",
    "competition_stats",
    "biggest_wins",
    "best_records",
    "derbies",
    "data_summary",
]
