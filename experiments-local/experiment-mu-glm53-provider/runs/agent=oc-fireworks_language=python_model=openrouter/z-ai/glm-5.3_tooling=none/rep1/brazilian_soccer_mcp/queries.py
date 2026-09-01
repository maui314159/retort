"""
 brazilian_soccer_mcp / queries.py
 =================================

 Why
 ---
 The MCP tools, the CLI and the tests all need the same answers, computed
 the same way.  This module is the single implementation of every
 capability required by TASK.md: match search, team statistics, head to
 head, player search, standings, analytical aggregates, derby listings
 and dataset directories.  Every function takes the loaded
 :class:`~brazilian_soccer_mcp.loader.Dataset` plus plain parameters and
 returns a JSON-ready dict (``{"ok": True, ...}`` or ``{"ok": False,
 "error": ...}``) so callers never need try/except control flow.

 What
 ---
 Match queries      - :func:`search_matches`, :func:`last_match_between`
 Team queries       - :func:`team_stats`, :func:`team_profile`,
                      :func:`head_to_head`, :func:`best_records`
 Player queries     - :func:`player_search`, :func:`player_club_report`
 Competition query  - :func:`standings`, :func:`list_competitions`,
                      :func:`list_teams`
 Statistical anlysis- :func:`competition_stats`, :func:`biggest_wins`,
                      :func:`derbies`

 Conventions
 -----------
 * Team names go through the club registry (fuzzy fallback + alternative
   spellings surfaced in the answer).
 * "Not played" fixtures (goals == None) are kept in schedule listings
   but excluded from every statistic.
 * Standings are computed from match results, 3 points per win, ordered
   by points, wins, goal difference, goals for (CBF tie-break style).

 Test: the feature modules under ``tests/`` (one per TASK.md capability).
=======================================================================
"""

from __future__ import annotations

import datetime as _dt
import difflib
from collections import defaultdict

from .loader import COMPETITIONS, Dataset
from .models import Club, Match, StandingRow
from .normalizer import squash

_DATE_MIN = _dt.date.min

_LEAGUE_COMPETITIONS = ("serie_a", "serie_b", "serie_c")
_MAX_LIMIT = 200

#: Curated classic derbies (name, key_a, key_b) used by :func:`derbies`.
DERBIES: list[dict[str, str]] = [
    {
        "name": "Fla-Flu",
        "rivalry": "Rio de Janeiro",
        "a": "flamengo|RJ",
        "b": "fluminense|RJ",
    },
    {
        "name": "Clássico dos Milhões",
        "rivalry": "Rio de Janeiro",
        "a": "flamengo|RJ",
        "b": "vasco|RJ",
    },
    {
        "name": "Clássico Vovô",
        "rivalry": "Rio de Janeiro",
        "a": "fluminense|RJ",
        "b": "vasco|RJ",
    },
    {
        "name": "Derby Paulista",
        "rivalry": "São Paulo",
        "a": "palmeiras|SP",
        "b": "corinthians|SP",
    },
    {
        "name": "Majestoso",
        "rivalry": "São Paulo",
        "a": "sao paulo|SP",
        "b": "corinthians|SP",
    },
    {
        "name": "Choque-Rei",
        "rivalry": "São Paulo",
        "a": "palmeiras|SP",
        "b": "sao paulo|SP",
    },
    {
        "name": "Gre-Nal",
        "rivalry": "Rio Grande do Sul",
        "a": "gremio|RS",
        "b": "internacional|RS",
    },
    {
        "name": "Clássico Mineiro",
        "rivalry": "Minas Gerais",
        "a": "atletico|MG",
        "b": "cruzeiro|MG",
    },
    {"name": "Atletiba", "rivalry": "Paraná", "a": "atletico|PR", "b": "coritiba|PR"},
    {"name": "Ba-Vi", "rivalry": "Bahia", "a": "bahia|BA", "b": "vitoria|BA"},
    {
        "name": "Clássico-Rei (Ceará)",
        "rivalry": "Ceará",
        "a": "ceara|CE",
        "b": "fortaleza|CE",
    },
    {"name": "Re-Pa", "rivalry": "Pará", "a": "remo|PA", "b": "paysandu|PA"},
]

#: FIFA position codes grouped for human-friendly filters.
POSITION_GROUPS: dict[str, set[str]] = {
    "GK": {"GK"},
    "DEF": {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
    "MID": {"CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"},
    "FWD": {"ST", "LS", "RS", "CF", "LW", "RW", "LF", "RF"},
}

#: Nationality spellings the FIFA file uses vs. how people ask.
_NATIONALITY_ALIASES = {
    "brazil": "brazil",
    "brasil": "brazil",
    "brazilian": "brazil",
    "brasilian": "brazil",
    "argentina": "argentina",
    "argentinian": "argentina",
    "portugal": "portugal",
}


# --------------------------------------------------------------------------
# Result helpers & team resolution
# --------------------------------------------------------------------------


def _ok(**payload) -> dict:
    return {"ok": True, **payload}


def _error(message: str, **hints) -> dict:
    return {"ok": False, "error": message, **hints}


def _coerce_season(season) -> int | None:
    if season is None or season == "":
        return None
    try:
        return int(str(season).strip())
    except ValueError:
        return None


def resolve_team(ds: Dataset, name: str) -> tuple[Club | None, list[Club]]:
    """
    Resolve any team spelling to a registry club.

    Returns (club, alternatives): alternatives lists the other clubs that
    share the same core name (e.g. the other Botafogos) so answers can
    offer a disambiguation hint.
    """
    if not name or not name.strip():
        return None, []

    key = ds.resolve_club_key(name)
    club = ds.clubs.get(key)
    if club is not None:
        alternatives = [
            other
            for other_key, other in ds.clubs.items()
            if other.core == club.core and other_key != club.key
        ]
        alternatives.sort(key=lambda c: -c.match_count)
        return club, alternatives

    # Fuzzy fallback over display names and raw variants.
    wanted = squash(name)
    pool: dict[str, Club] = {}
    for club_obj in ds.clubs.values():
        pool[squash(club_obj.display)] = club_obj
        for variant in club_obj.variants:
            pool.setdefault(squash(variant), club_obj)
    close = difflib.get_close_matches(wanted, list(pool), n=8, cutoff=0.75)
    seen_keys: dict[str, Club] = {}
    for match in close:
        club_obj = pool[match]
        seen_keys.setdefault(club_obj.key, club_obj)
    if seen_keys:
        return None, sorted(seen_keys.values(), key=lambda c: -c.match_count)[:5]
    starts = {c.key: c for squashed, c in pool.items() if squashed.startswith(wanted)}
    if starts:
        return None, sorted(starts.values(), key=lambda c: -c.match_count)[:5]
    return None, []


def _team_not_found(name: str, alternatives: list[Club]) -> dict:
    hint = ""
    if alternatives:
        hint = (
            " Did you mean: "
            + ", ".join(
                f"{c.display} ({c.match_count} matches)" for c in alternatives[:5]
            )
            + "?"
        )
    return _error(
        f"Team not found in the dataset: '{name}'.{hint}",
        suggestions=[c.display for c in alternatives[:5]],
    )


def _matches_between(ds: Dataset, key_a: str, key_b: str) -> list[Match]:
    """All matches pairing the two clubs (either orientation)."""
    out = []
    for match in ds.club_matches.get(key_a, []):
        if match.home_key == key_b or match.away_key == key_b:
            out.append(match)
    return out


def _competition_scope(ds: Dataset, competition: str | None):
    """Return (list_of_competition_ids, error_dict|None)."""
    if competition is None or str(competition).strip().lower() in ("all", "*", "any"):
        return list(ds.competition_matches.keys()), None
    from .normalizer import normalize_competition

    comp_id = normalize_competition(competition)
    if comp_id is None or comp_id == "all":
        valid = ", ".join(
            f"{cid} ({meta['display']})" for cid, meta in COMPETITIONS.items()
        )
        return None, _error(
            f"Unknown competition: '{competition}'. Valid: {valid}.",
            valid_competitions=list(COMPETITIONS),
        )
    if comp_id not in ds.competition_matches:
        return None, _error(
            f"Competition '{COMPETITIONS[comp_id]['display']}' has no matches loaded.",
            valid_competitions=list(ds.competition_matches),
        )
    return [comp_id], None


def _stage_key(value: str) -> str:
    """Normalise a stage/round query ('semi-finals' -> 'semifinals')."""
    text = squash(value).replace("-", "").replace(" ", "")
    mapping = {
        "group": "group stage",
        "groupstage": "group stage",
        "fasedegrupos": "group stage",
        "grupos": "group stage",
        "roundof16": "round of 16",
        "16": "round of 16",
        "oitavas": "round of 16",
        "oitavasdefinal": "round of 16",
        "quarter": "quarterfinals",
        "quarters": "quarterfinals",
        "quarterfinal": "quarterfinals",
        "quarterfinals": "quarterfinals",
        "quartas": "quarterfinals",
        "quartasdefinal": "quarterfinals",
        "qf": "quarterfinals",
        "semi": "semifinals",
        "semifinal": "semifinals",
        "semifinals": "semifinals",
        "semis": "semifinals",
        "semisdefinal": "semifinals",
        "final": "final",
        "finals": "final",
        "thefinal": "final",
        "afinal": "final",
        "decisao": "final",
        "grandefinal": "final",
    }
    if text.isdigit():
        return f"round:{text}"
    return mapping.get(text, text.replace(" ", ""))


# --------------------------------------------------------------------------
# 1. Match queries
# --------------------------------------------------------------------------


def search_matches(
    ds: Dataset,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season=None,
    stage: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> dict:
    """
    Search fixtures by team, opponent, competition, season, stage/round
    and date range.  Results are newest-first and include date, score,
    competition and phase for every match.
    """
    from .normalizer import parse_date as _pd

    team_club = opp_club = None
    team_alts: list[Club] = []
    if team:
        team_club, team_alts = resolve_team(ds, team)
        if team_club is None:
            return _team_not_found(team, team_alts)
    if opponent:
        opp_club, opp_alts = resolve_team(ds, opponent)
        if opp_club is None:
            return _team_not_found(opponent, opp_alts)

    comp_ids, err = _competition_scope(ds, competition)
    if err:
        return err
    season_int = _coerce_season(season)
    date_lo = _pd(date_from)
    date_hi = _pd(date_to)
    if (date_from and date_lo is None) or (date_to and date_hi is None):
        return _error("Dates must be ISO format (YYYY-MM-DD).")

    stage_key = _stage_key(stage) if stage else None
    if stage_key and stage_key.startswith("round:") and comp_ids == ["libertadores"]:
        return _error(
            "The Libertadores dataset uses stage names "
            "(group stage, round of 16, quarterfinals, semifinals, final), "
            "not numeric rounds."
        )

    def in_stage(match: Match) -> bool:
        if stage_key is None:
            return True
        if match.competition == "libertadores":
            return squash(match.stage or "") == stage_key
        if stage_key == "final":
            if match.competition == "copa_do_brasil":
                return (
                    match.season is not None
                    and ds.cup_final_rounds.get(match.season) is not None
                    and match.round is not None
                    and match.round.isdigit()
                    and int(match.round) == ds.cup_final_rounds[match.season]
                )
            return False
        if stage_key.startswith("round:"):
            wanted = stage_key.split(":", 1)[1]
            return match.round is not None and str(match.round) == wanted
        return squash(match.stage or "") == stage_key

    candidates: list[Match] = []
    for comp_id in comp_ids:
        if season_int is None:
            candidates.extend(ds.competition_matches.get(comp_id, []))
        else:
            candidates.extend(ds.season_matches.get((comp_id, season_int), []))

    results = []
    for match in candidates:
        if team_club is not None and team_club.key not in (
            match.home_key,
            match.away_key,
        ):
            continue
        if opp_club is not None:
            if team_club is not None:
                if {match.home_key, match.away_key} != {team_club.key, opp_club.key}:
                    continue
            elif opp_club.key not in (match.home_key, match.away_key):
                continue
        if date_lo is not None and (match.date is None or match.date < date_lo):
            continue
        if date_hi is not None and (match.date is None or match.date > date_hi):
            continue
        if not in_stage(match):
            continue
        results.append(match)

    results.sort(key=lambda m: (m.date or _DATE_MIN, m.competition), reverse=True)
    limit = max(1, min(int(limit or 20), _MAX_LIMIT))
    return _ok(
        team=team_club.display if team_club else None,
        team_alternatives=[c.display for c in team_alts][:5],
        opponent=opp_club.display if opp_club else None,
        competition=(
            COMPETITIONS[comp_ids[0]]["display"]
            if len(comp_ids) == 1
            else "all competitions"
        ),
        season=season_int,
        stage_or_round=stage,
        date_from=date_from,
        date_to=date_to,
        total=len(results),
        shown=min(len(results), limit),
        truncated=len(results) > limit,
        matches=[m.to_dict() for m in results[:limit]],
    )


def last_match_between(ds: Dataset, team_a: str, team_b: str) -> dict:
    """The most recent played fixture between two clubs (plus any newer
    scheduled-but-unplayed fixture)."""
    club_a, alts_a = resolve_team(ds, team_a)
    if club_a is None:
        return _team_not_found(team_a, alts_a)
    club_b, alts_b = resolve_team(ds, team_b)
    if club_b is None:
        return _team_not_found(team_b, alts_b)

    matches = _matches_between(ds, club_a.key, club_b.key)
    played = [m for m in matches if m.played]
    if not played and not matches:
        return _error(
            f"No matches between {club_a.display} and {club_b.display} in the dataset."
        )
    played.sort(key=lambda m: (m.date is None, m.date))
    latest = played[-1] if played else None
    scheduled = [
        m
        for m in matches
        if not m.played
        and (latest is None or (m.date and latest.date and m.date > latest.date))
    ]
    return _ok(
        team_a=club_a.display,
        team_b=club_b.display,
        last_played=latest.to_dict() if latest else None,
        later_scheduled=[m.to_dict() for m in scheduled[-3:]],
        total_meetings=len(matches),
    )


def head_to_head(
    ds: Dataset,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season=None,
    limit: int = 20,
) -> dict:
    """Head-to-head record between two clubs (optionally scoped)."""
    club_a, alts_a = resolve_team(ds, team_a)
    if club_a is None:
        return _team_not_found(team_a, alts_a)
    club_b, alts_b = resolve_team(ds, team_b)
    if club_b is None:
        return _team_not_found(team_b, alts_b)

    comp_ids, err = _competition_scope(ds, competition)
    if err:
        return err
    season_int = _coerce_season(season)

    matches = _matches_between(ds, club_a.key, club_b.key)
    scoped = [
        m
        for m in matches
        if m.competition in comp_ids and (season_int is None or m.season == season_int)
    ]

    wins_a = wins_b = draws = 0
    goals_a = goals_b = 0
    for match in scoped:
        if not match.played:
            continue
        a_home = match.home_key == club_a.key
        a_goals, b_goals = (
            (match.home_goals, match.away_goals)
            if a_home
            else (match.away_goals, match.home_goals)
        )
        goals_a += a_goals
        goals_b += b_goals
        if a_goals > b_goals:
            wins_a += 1
        elif a_goals < b_goals:
            wins_b += 1
        else:
            draws += 1

    scoped.sort(key=lambda m: (m.date is None, m.date))
    scoped.reverse()
    limit = max(1, min(int(limit or 20), _MAX_LIMIT))
    return _ok(
        team_a=club_a.display,
        team_b=club_b.display,
        competition=(
            COMPETITIONS[comp_ids[0]]["display"]
            if len(comp_ids) == 1
            else "all competitions"
        ),
        season=season_int,
        meetings=len([m for m in scoped if m.played]),
        wins_team_a=wins_a,
        wins_team_b=wins_b,
        draws=draws,
        goals_team_a=goals_a,
        goals_team_b=goals_b,
        matches=[m.to_dict() for m in scoped[:limit]],
        total=len(scoped),
    )


# --------------------------------------------------------------------------
# 2. Team queries
# --------------------------------------------------------------------------


def _record(matches: list[Match], key: str, venue: str = "all") -> dict:
    """W/D/L + goals for one club over a match list."""
    stats = {
        "matches": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
    }
    for match in matches:
        if not match.played:
            continue
        if venue == "home" and match.home_key != key:
            continue
        if venue == "away" and match.away_key != key:
            continue
        if key not in (match.home_key, match.away_key):
            continue
        home = match.home_key == key
        gf, ga = (
            (match.home_goals, match.away_goals)
            if home
            else (match.away_goals, match.home_goals)
        )
        stats["matches"] += 1
        stats["goals_for"] += gf
        stats["goals_against"] += ga
        if gf > ga:
            stats["wins"] += 1
        elif gf < ga:
            stats["losses"] += 1
        else:
            stats["draws"] += 1
    decided = stats["wins"] + stats["draws"] + stats["losses"]
    stats["win_rate"] = round(100 * stats["wins"] / decided, 1) if decided else None
    return stats


def team_stats(
    ds: Dataset,
    team: str,
    season=None,
    competition: str | None = None,
    venue: str = "all",
) -> dict:
    """
    Win/draw/loss record and goals for a club, optionally scoped to a
    season, competition and venue ('home', 'away' or 'all').
    """
    club, alts = resolve_team(ds, team)
    if club is None:
        return _team_not_found(team, alts)
    venue = squash(venue or "all")
    if venue not in {"all", "home", "away"}:
        return _error("venue must be 'home', 'away' or 'all'.")

    comp_ids, err = _competition_scope(ds, competition)
    if err:
        return err
    season_int = _coerce_season(season)

    matches = [
        m
        for m in ds.club_matches.get(club.key, [])
        if m.competition in comp_ids and (season_int is None or m.season == season_int)
    ]

    overall = _record(matches, club.key, venue)
    result = _ok(
        team=club.display,
        team_key=club.key,
        season=season_int,
        competition=(
            COMPETITIONS[comp_ids[0]]["display"]
            if len(comp_ids) == 1
            else "all competitions"
        ),
        venue=venue,
        record=overall,
    )
    if venue == "all":
        result["home_record"] = _record(matches, club.key, "home")
        result["away_record"] = _record(matches, club.key, "away")
    if len(comp_ids) != 1:
        by_comp = []
        for comp_id in sorted({m.competition for m in matches}):
            rec = _record(
                [m for m in matches if m.competition == comp_id], club.key, venue
            )
            rec["competition"] = COMPETITIONS[comp_id]["display"]
            by_comp.append(rec)
        result["by_competition"] = by_comp
    return result


def team_profile(ds: Dataset, team: str) -> dict:
    """
    Everything the graph knows about one club: spellings seen, states,
    competitions and seasons played, all-time record and FIFA player
    presence (cross-file player + match data).
    """
    club, alts = resolve_team(ds, team)
    if club is None:
        return _team_not_found(team, alts)

    matches = ds.club_matches.get(club.key, [])
    record = _record(matches, club.key)
    by_competition = []
    for comp_id in club.competitions:
        comp_matches = [m for m in matches if m.competition == comp_id]
        rec = _record(comp_matches, club.key)
        seasons = sorted({m.season for m in comp_matches if m.season})
        rec["competition"] = COMPETITIONS[comp_id]["display"]
        rec["seasons"] = {
            "first": seasons[0] if seasons else None,
            "last": seasons[-1] if seasons else None,
            "count": len(seasons),
        }
        by_competition.append(rec)

    fifa_count = sum(
        1 for p in ds.players if p.club and ds.fifa_club_key(p.club) == club.key
    )

    return _ok(
        club=club.to_dict(),
        all_time_record=record,
        by_competition=by_competition,
        fifa_players_in_dataset=fifa_count,
        similar_named_clubs=[c.display for c in alts],
    )


def best_records(
    ds: Dataset,
    venue: str = "home",
    competition: str | None = None,
    season=None,
    metric: str = "win_rate",
    min_matches: int = 10,
    limit: int = 10,
) -> dict:
    """
    Rank teams by a performance metric for a venue - answers "which team
    has the best home/away record?".  Metrics: win_rate, points_per_game,
    goals_for, goals_against, avg_goals_for.
    """
    venue = squash(venue or "all")
    if venue not in {"all", "home", "away"}:
        return _error("venue must be 'home', 'away' or 'all'.")
    metric = squash(metric or "win_rate")
    if metric not in {
        "win_rate",
        "points_per_game",
        "goals_for",
        "goals_against",
        "avg_goals_for",
    }:
        return _error(
            "metric must be one of win_rate, points_per_game, "
            "goals_for, goals_against, avg_goals_for."
        )

    comp_ids, err = _competition_scope(ds, competition)
    if err:
        return err
    season_int = _coerce_season(season)

    pool: list[Match] = []
    for comp_id in comp_ids:
        if season_int is None:
            pool.extend(ds.competition_matches.get(comp_id, []))
        else:
            pool.extend(ds.season_matches.get((comp_id, season_int), []))

    stats: dict[str, dict] = defaultdict(
        lambda: {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
    )
    for match in pool:
        if not match.played:
            continue
        for side, key, gf, ga in (
            ("home", match.home_key, match.home_goals, match.away_goals),
            ("away", match.away_key, match.away_goals, match.home_goals),
        ):
            if venue != "all" and venue != side:
                continue
            entry = stats[key]
            entry["matches"] += 1
            entry["wins" if gf > ga else "losses" if gf < ga else "draws"] += 1
            entry["goals_for"] += gf
            entry["goals_against"] += ga

    rows = []
    for key, entry in stats.items():
        if entry["matches"] < min_matches:
            continue
        decided = entry["wins"] + entry["draws"] + entry["losses"]
        points = 3 * entry["wins"] + entry["draws"]
        row = {
            "team": ds.clubs[key].display if key in ds.clubs else key,
            "team_key": key,
            "matches": entry["matches"],
            "wins": entry["wins"],
            "draws": entry["draws"],
            "losses": entry["losses"],
            "goals_for": entry["goals_for"],
            "goals_against": entry["goals_against"],
            "win_rate": round(100 * entry["wins"] / decided, 1) if decided else 0,
            "points_per_game": round(points / entry["matches"], 2),
            "avg_goals_for": round(entry["goals_for"] / entry["matches"], 2),
        }
        rows.append(row)

    descending = metric not in {"goals_against"}
    rows.sort(
        key=lambda r: (
            (-r[metric], -r["matches"], r["team"])
            if descending
            else (r[metric], r["matches"], r["team"])
        )
    )
    limit = max(1, min(int(limit or 10), 100))
    return _ok(
        venue=venue,
        metric=metric,
        min_matches=min_matches,
        competition=(
            COMPETITIONS[comp_ids[0]]["display"]
            if len(comp_ids) == 1
            else "all competitions"
        ),
        season=season_int,
        teams_ranked=len(rows),
        records=rows[:limit],
    )


# --------------------------------------------------------------------------
# 3. Player queries
# --------------------------------------------------------------------------


def _normalize_nationality(value: str) -> str:
    text = squash(value)
    return _NATIONALITY_ALIASES.get(text, text)


def _position_codes(value: str) -> set[str] | None:
    text = squash(value).upper()
    if text in POSITION_GROUPS:
        return POSITION_GROUPS[text]
    if text in {"STRIKER", "FORWARD", "ATTACKER"}:
        return POSITION_GROUPS["FWD"]
    if text in {"DEFENDER", "DEFENSE", "DEFENCE"}:
        return POSITION_GROUPS["DEF"]
    if text in {"MIDFIELDER", "MIDFIELD"}:
        return POSITION_GROUPS["MID"]
    if text in {"GOALKEEPER", "KEEPER", "GOALIE"}:
        return POSITION_GROUPS["GK"]
    codes = {code for group in POSITION_GROUPS.values() for code in group}
    if text in codes:
        return {text}
    return None


def player_search(
    ds: Dataset,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall=None,
    max_age=None,
    order: str = "overall",
    limit: int = 20,
) -> dict:
    """
    Search the FIFA player database by name, nationality, club, position,
    minimum overall rating and maximum age; order by overall/potential/
    age/name/value.
    """
    name_needle = squash(name) if name else None
    nationality_needle = _normalize_nationality(nationality) if nationality else None
    min_overall_int = int(min_overall) if min_overall is not None else None
    max_age_int = int(max_age) if max_age is not None else None
    order_key = squash(order or "overall")
    order_fields = {"overall", "potential", "age", "name", "value"}
    if order_key not in order_fields:
        return _error(f"order must be one of {sorted(order_fields)}.")

    # Club filter: resolve through the registry, but also allow raw string
    # match so foreign clubs absent from the match data still work.
    club_resolved: Club | None = None
    club_raw_needle: str | None = None
    if club:
        club_resolved, _alts = resolve_team(ds, club)
        if club_resolved is None:
            club_raw_needle = squash(club)

    positions = _position_codes(position) if position else None
    if position and positions is None:
        valid = sorted(
            {code for group in POSITION_GROUPS.values() for code in group}
            | set(POSITION_GROUPS)
        )
        return _error(f"Unknown position '{position}'. Valid codes/groups: {valid}.")

    results = []
    for player in ds.players:
        if name_needle and name_needle not in squash(player.name):
            continue
        if nationality_needle and squash(player.nationality) != nationality_needle:
            continue
        if club_resolved is not None or club_raw_needle:
            if player.club is None:
                continue
            if club_resolved is not None:
                if ds.fifa_club_key(player.club) != club_resolved.key and squash(
                    player.club
                ) != squash(club or ""):
                    continue
            elif squash(player.club) != club_raw_needle:
                continue
        if positions is not None and player.position not in positions:
            continue
        if min_overall_int is not None and player.overall < min_overall_int:
            continue
        if max_age_int is not None and (player.age is None or player.age > max_age_int):
            continue
        results.append(player)

    if order_key == "name":
        results.sort(key=lambda p: p.name)
    elif order_key == "value":
        results.sort(key=lambda p: (p.value_eur is None, -(p.value_eur or 0), p.name))
    elif order_key == "age":
        results.sort(key=lambda p: (p.age is None, -(p.age or 0), p.name))
    else:
        results.sort(key=lambda p: (-(getattr(p, order_key) or 0), p.name))

    limit = max(1, min(int(limit or 20), _MAX_LIMIT))
    return _ok(
        criteria={
            "name": name,
            "nationality": nationality,
            "club": club,
            "position": position,
            "min_overall": min_overall_int,
            "max_age": max_age_int,
            "order": order_key,
        },
        total=len(results),
        shown=min(len(results), limit),
        truncated=len(results) > limit,
        players=[p.to_dict() for p in results[:limit]],
    )


def player_club_report(
    ds: Dataset, nationality: str | None = None, min_overall=None
) -> dict:
    """
    Group players by club: count, average and best rating.  Answers the
    "Brazilian players at Brazilian clubs" style of question and flags
    which clubs the match data knows as Brazilian.
    """
    nationality_needle = _normalize_nationality(nationality) if nationality else None
    min_overall_int = int(min_overall) if min_overall is not None else None

    groups: dict[str, list] = defaultdict(list)
    for player in ds.players:
        if nationality_needle and squash(player.nationality) != nationality_needle:
            continue
        if min_overall_int is not None and player.overall < min_overall_int:
            continue
        groups[player.club or "No club"].append(player)

    rows = []
    for club_name, players in groups.items():
        overalls = [p.overall for p in players]
        best = max(players, key=lambda p: (p.overall, p.name))
        club_key = ds.fifa_club_key(club_name) if club_name != "No club" else None
        club_obj = ds.clubs.get(club_key) if club_key else None
        rows.append(
            {
                "club": club_name,
                "players": len(players),
                "avg_overall": round(sum(overalls) / len(overalls), 1),
                "best_player": {
                    "name": best.name,
                    "overall": best.overall,
                    "position": best.position,
                },
                "brazilian_club_in_match_data": bool(club_obj and club_obj.state),
            }
        )
    rows.sort(key=lambda r: (-r["avg_overall"], -r["players"], r["club"]))
    return _ok(
        nationality=nationality or "all",
        min_overall=min_overall_int,
        clubs=len(rows),
        clubs_report=rows,
    )


# --------------------------------------------------------------------------
# 4. Competition queries
# --------------------------------------------------------------------------


def standings(ds: Dataset, competition: str, season) -> dict:
    """
    League table computed from match results (3 points per win; CBF
    tie-break order).  Champion and relegated (bottom four) included.
    """
    from .normalizer import normalize_competition

    comp_id = normalize_competition(competition)
    if comp_id is None:
        return _error(
            f"Unknown competition: '{competition}'.",
            valid_competitions=list(COMPETITIONS),
        )
    if comp_id not in _LEAGUE_COMPETITIONS:
        return _error(
            f"Standings are only computed for league competitions "
            f"(serie_a, serie_b, serie_c). '{COMPETITIONS[comp_id]['display']}' "
            f"is a knockout competition - try search_matches with stage='final'."
        )
    season_int = _coerce_season(season)
    if season_int is None:
        return _error("A season (year) is required, e.g. season=2019.")

    matches = [m for m in ds.season_matches.get((comp_id, season_int), []) if m.played]
    if not matches:
        available = ds.seasons_for(comp_id)
        return _error(
            f"No matches for {COMPETITIONS[comp_id]['display']} {season_int}. "
            f"Available seasons: {available}."
        )

    table: dict[str, dict] = defaultdict(
        lambda: {
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        }
    )
    for match in matches:
        for key, gf, ga in (
            (match.home_key, match.home_goals, match.away_goals),
            (match.away_key, match.away_goals, match.home_goals),
        ):
            entry = table[key]
            entry["played"] += 1
            entry["goals_for"] += gf
            entry["goals_against"] += ga
            if gf > ga:
                entry["wins"] += 1
                entry["points"] += 3
            elif gf < ga:
                entry["losses"] += 1
            else:
                entry["draws"] += 1
                entry["points"] += 1

    ordered = sorted(
        table.items(),
        key=lambda kv: (
            -kv[1]["points"],
            -kv[1]["wins"],
            -(kv[1]["goals_for"] - kv[1]["goals_against"]),
            -kv[1]["goals_for"],
            kv[0],
        ),
    )
    rows = []
    for position, (key, entry) in enumerate(ordered, start=1):
        rows.append(
            StandingRow(
                position=position,
                team=ds.clubs[key].display if key in ds.clubs else key,
                team_key=key,
                played=entry["played"],
                wins=entry["wins"],
                draws=entry["draws"],
                losses=entry["losses"],
                goals_for=entry["goals_for"],
                goals_against=entry["goals_against"],
                goal_diff=entry["goals_for"] - entry["goals_against"],
                points=entry["points"],
            )
        )

    return _ok(
        competition=COMPETITIONS[comp_id]["display"],
        season=season_int,
        matches_counted=len(matches),
        champion=rows[0].to_dict() if rows else None,
        relegated=[r.to_dict() for r in rows[-4:]] if len(rows) >= 4 else [],
        relegation_note="bottom four (modern Série A standard)",
        rows=[r.to_dict() for r in rows],
    )


def list_competitions(ds: Dataset) -> dict:
    """Every competition with seasons covered and match counts."""
    out = []
    for comp_id, meta in COMPETITIONS.items():
        matches = ds.competition_matches.get(comp_id, [])
        if not matches:
            continue
        seasons = ds.seasons_for(comp_id)
        out.append(
            {
                "id": comp_id,
                "display": meta["display"],
                "description": meta["description"],
                "seasons": seasons,
                "first_season": seasons[0] if seasons else None,
                "last_season": seasons[-1] if seasons else None,
                "matches": len(matches),
                "played": sum(1 for m in matches if m.played),
                "sources": sorted({m.source for m in matches}),
            }
        )
    return _ok(competitions=out)


def list_teams(
    ds: Dataset, competition: str | None = None, season=None, limit: int = 100
) -> dict:
    """
    Team directory: all clubs, or the participants of one competition
    (optionally one season), with match counts.
    """
    comp_ids, err = _competition_scope(ds, competition)
    if err:
        return err
    season_int = _coerce_season(season)

    if season_int is not None and len(comp_ids) == 1:
        pool = ds.season_matches.get((comp_ids[0], season_int), [])
    elif len(comp_ids) == 1:
        pool = ds.competition_matches.get(comp_ids[0], [])
    else:
        pool = None

    if pool is None:
        entries = sorted(ds.clubs.values(), key=lambda c: -c.match_count)
    else:
        keys = {m.home_key for m in pool} | {m.away_key for m in pool}
        entries = [ds.clubs[k] for k in keys if k in ds.clubs]
        entries.sort(key=lambda c: -c.match_count)

    limit = max(1, min(int(limit or 100), _MAX_LIMIT * 5))
    return _ok(
        competition=(
            COMPETITIONS[comp_ids[0]]["display"]
            if len(comp_ids) == 1
            else "all competitions"
        ),
        season=season_int,
        total=len(entries),
        shown=min(len(entries), limit),
        teams=[c.to_dict() for c in entries[:limit]],
    )


# --------------------------------------------------------------------------
# 5. Statistical analysis
# --------------------------------------------------------------------------


def _aggregate(matches: list[Match]) -> dict:
    played = [m for m in matches if m.played]
    total = len(played)
    if not total:
        return {"matches": 0, "played": 0}
    home_wins = sum(1 for m in played if m.home_goals > m.away_goals)
    draws = sum(1 for m in played if m.home_goals == m.away_goals)
    away_wins = total - home_wins - draws
    home_goals = sum(m.home_goals for m in played)
    away_goals = sum(m.away_goals for m in played)
    return {
        "matches": len(matches),
        "played": total,
        "not_played": len(matches) - total,
        "total_goals": home_goals + away_goals,
        "avg_goals_per_match": round((home_goals + away_goals) / total, 2),
        "avg_home_goals": round(home_goals / total, 2),
        "avg_away_goals": round(away_goals / total, 2),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_rate": round(100 * home_wins / total, 1),
        "draw_rate": round(100 * draws / total, 1),
        "away_win_rate": round(100 * away_wins / total, 1),
    }


def competition_stats(ds: Dataset, competition: str | None = None, season=None) -> dict:
    """
    Aggregate statistics: average goals per match, home/draw/away win
    rates - for one competition (+season) or across everything.
    """
    comp_ids, err = _competition_scope(ds, competition)
    if err:
        return err
    season_int = _coerce_season(season)

    def pool_for(comp_id: str) -> list[Match]:
        if season_int is None:
            return ds.competition_matches.get(comp_id, [])
        return ds.season_matches.get((comp_id, season_int), [])

    if len(comp_ids) == 1:
        stats = _aggregate(pool_for(comp_ids[0]))
        return _ok(
            competition=COMPETITIONS[comp_ids[0]]["display"],
            season=season_int,
            stats=stats,
        )

    overall = _aggregate([m for cid in comp_ids for m in pool_for(cid)])
    per_competition = []
    for comp_id in sorted(comp_ids):
        entry = _aggregate(pool_for(comp_id))
        entry["competition"] = COMPETITIONS[comp_id]["display"]
        per_competition.append(entry)
    return _ok(
        competition="all competitions",
        season=season_int,
        stats=overall,
        by_competition=per_competition,
    )


def biggest_wins(
    ds: Dataset, competition: str | None = None, season=None, limit: int = 10
) -> dict:
    """Largest victory margins in the dataset (margin, then total goals)."""
    comp_ids, err = _competition_scope(ds, competition)
    if err:
        return err
    season_int = _coerce_season(season)

    pool: list[Match] = []
    for comp_id in comp_ids:
        if season_int is None:
            pool.extend(ds.competition_matches.get(comp_id, []))
        else:
            pool.extend(ds.season_matches.get((comp_id, season_int), []))
    played = [m for m in pool if m.played]

    played.sort(
        key=lambda m: (
            -abs(m.home_goals - m.away_goals),
            -(m.home_goals + m.away_goals),
            m.date or _DATE_MIN,
        )
    )
    limit = max(1, min(int(limit or 10), 100))
    rows = []
    for match in played[:limit]:
        row = match.to_dict()
        row["margin"] = abs(match.home_goals - match.away_goals)
        rows.append(row)
    return _ok(
        competition=(
            COMPETITIONS[comp_ids[0]]["display"]
            if len(comp_ids) == 1
            else "all competitions"
        ),
        season=season_int,
        biggest_wins=rows,
    )


def derbies(ds: Dataset, season=None, limit_per_derby: int = 5) -> dict:
    """
    Classic Brazilian derbies (curated list) with head-to-head records
    and, optionally, the meetings of one season - answers "show me all
    derbies in 2023".
    """
    season_int = _coerce_season(season)
    out = []
    for derby in DERBIES:
        club_a = ds.clubs.get(derby["a"])
        club_b = ds.clubs.get(derby["b"])
        if club_a is None or club_b is None:
            continue
        matches = _matches_between(ds, derby["a"], derby["b"])
        in_scope = (
            [m for m in matches if m.season == season_int]
            if season_int is not None
            else matches
        )
        wins_a = wins_b = draws = 0
        for match in matches:
            if not match.played:
                continue
            a_home = match.home_key == derby["a"]
            a_goals, b_goals = (
                (match.home_goals, match.away_goals)
                if a_home
                else (match.away_goals, match.home_goals)
            )
            if a_goals > b_goals:
                wins_a += 1
            elif a_goals < b_goals:
                wins_b += 1
            else:
                draws += 1
        in_scope.sort(key=lambda m: (m.date is None, m.date))
        in_scope.reverse()
        limit = max(1, min(int(limit_per_derby or 5), 20))
        out.append(
            {
                "derby": derby["name"],
                "rivalry": derby["rivalry"],
                "team_a": club_a.display,
                "team_b": club_b.display,
                "all_time": {
                    "meetings": wins_a + wins_b + draws,
                    "wins_team_a": wins_a,
                    "wins_team_b": wins_b,
                    "draws": draws,
                },
                "matches_in_scope": len(in_scope),
                "matches": [m.to_dict() for m in in_scope[:limit]],
            }
        )
    out.sort(key=lambda d: (-d["matches_in_scope"], d["derby"]))
    return _ok(
        season=season_int,
        derbies=out,
        derbies_with_matches=sum(1 for d in out if d["matches_in_scope"]),
    )
