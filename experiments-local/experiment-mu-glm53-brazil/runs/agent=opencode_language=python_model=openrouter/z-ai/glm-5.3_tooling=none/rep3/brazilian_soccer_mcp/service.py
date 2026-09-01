"""
Query service for the Brazilian Soccer MCP server.

Context block
-------------
Why:
    MCP tools must be thin, typed and documented; all domain logic lives
    here as plain functions over the assembled ``Dataset`` so it can be
    unit-tested (BDD GWT) without spinning up the MCP transport.

What:
    Every capability demanded by TASK.md maps to one function:
      * Match queries    - ``search_matches``, ``head_to_head``, ``last_match``
      * Team queries     - ``team_record``, ``team_profile``, ``list_teams``
      * Player queries   - ``find_players``, ``top_players``, ``players_at_club``
      * Competitions     - ``standings``, ``champion``, ``bracket``,
                           ``competition_info``
      * Statistical      - ``season_averages``, ``biggest_wins``,
                           ``match_statistics``, ``derby_matches``
    Helpers resolve free-text teams (via ``ClubRegistry.resolve``) and
    competitions (via ``normalize.resolve_competition``); ambiguity is
    surfaced, never guessed silently.  League tables use the CBF/Serie A
    ordering: points, wins, goal difference, goals for.

Test:
    BDD GWT scenario suites in ``tests/test_match_queries.py``,
    ``tests/test_team_queries.py``, ``tests/test_player_queries.py``,
    ``tests/test_competition_queries.py`` and ``tests/test_statistics.py``.

Spec references:
    TASK.md "Required Capabilities" 1-5, "Sample Questions and Expected
    Behaviors", "Example answer format" blocks, and the Gherkin sketch in
    "Testing Approach".
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date as Date
from typing import Any

from .dataset import Dataset
from .models import Club, Match, StandingRow
from .normalize import fold_accents, parse_date, resolve_competition

LEAGUE_COMPETITIONS = {"Brasileirão Serie A", "Brasileirão Serie B", "Brasileirão Serie C"}
CUP_COMPETITIONS = {"Copa do Brasil", "Copa Libertadores"}

#: Famous derby pairs keyed by their popular names (club keys post-merge).
DERBIES: list[tuple[str, str, str]] = [
    ("Fla-Flu", "flamengo|RJ", "fluminense|RJ"),
    ("Clássico dos Milhões (Flamengo x Vasco)", "flamengo|RJ", "vasco|RJ"),
    ("Gre-Nal (Grêmio x Internacional)", "gremio|RS", "internacional|RS"),
    ("Choque-Rei (Palmeiras x São Paulo)", "palmeiras|SP", "saopaulo|SP"),
    ("Derby Paulista (Palmeiras x Corinthians)", "palmeiras|SP", "corinthians|SP"),
    ("Majestoso (Corinthians x São Paulo)", "corinthians|SP", "saopaulo|SP"),
    ("Clássico Mineiro (Atlético x Cruzeiro)", "atletico|MG", "cruzeiro|MG"),
    ("Ba-Vi (Bahia x Vitória)", "bahia|BA", "vitoria|BA"),
    ("Atletiba (Athletico x Coritiba)", "atletico|PR", "coritiba|PR"),
]

_POSITION_GROUPS: dict[str, frozenset[str]] = {
    "goalkeeper": frozenset({"GK"}),
    "defender": frozenset({"LB", "LCB", "CB", "RCB", "RB", "LWB", "RWB"}),
    "midfielder": frozenset({"LDM", "CDM", "RDM", "LM", "LCM", "CM", "RCM", "RM", "LAM", "CAM", "RAM"}),
    "forward": frozenset({"LW", "LF", "CF", "RF", "RW", "ST"}),
}


# --------------------------------------------------------------------------
# Resolution helpers
# --------------------------------------------------------------------------


def resolve_competition_or_raise(competition: str) -> str:
    canonical = resolve_competition(competition)
    if canonical is None:
        raise ValueError(
            f"Unknown competition {competition!r}. "
            "Valid: Brasileirão Serie A/B/C, Copa do Brasil, Copa Libertadores."
        )
    return canonical


def resolve_club_or_raise(ds: Dataset, name: str) -> Club:
    ranked = ds.registry.resolve(name)
    if not ranked:
        raise ValueError(f"No team matching {name!r} was found in the dataset.")
    return ranked[0]


def _alternates_for(ds: Dataset, name: str, primary: Club) -> list[str]:
    return [c.display for c in ds.registry.resolve(name) if c.id != primary.id][:5]


def _coerce_season(season: Any) -> int | None:
    if season is None or season == "":
        return None
    try:
        return int(str(season))
    except (TypeError, ValueError):
        raise ValueError(f"Invalid season {season!r}: expected a year like 2019.")


def _coerce_date(value: Any, label: str) -> Date | None:
    if value is None or value == "":
        return None
    if isinstance(value, Date):
        return value
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError(f"Invalid {label} {value!r}: expected YYYY-MM-DD.")
    return parsed


# --------------------------------------------------------------------------
# Match queries
# --------------------------------------------------------------------------


def search_matches(
    ds: Dataset,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: Any = None,
    date_from: Any = None,
    date_to: Any = None,
    stage: str | None = None,
    limit: int = 50,
) -> dict:
    """Search the canonical match index by any combination of criteria."""
    comp = resolve_competition_or_raise(competition) if competition else None
    season_n = _coerce_season(season)
    date_lo = _coerce_date(date_from, "date_from")
    date_hi = _coerce_date(date_to, "date_to")

    team_club = opponent_club = None
    ambiguous: list[str] = []
    if team:
        team_club = resolve_club_or_raise(ds, team)
        ambiguous += [f"{team!r} also matches {a}" for a in _alternates_for(ds, team, team_club)]
    if opponent:
        opponent_club = resolve_club_or_raise(ds, opponent)
        ambiguous += [f"{opponent!r} also matches {a}" for a in _alternates_for(ds, opponent, opponent_club)]
    if team_club and opponent_club and team_club.id == opponent_club.id:
        raise ValueError("team and opponent resolve to the same club.")

    result: list[Match] = []
    for m in ds.matches:
        if comp and m.competition != comp:
            continue
        if season_n is not None and m.season != season_n:
            continue
        if date_lo and (m.date is None or m.date < date_lo):
            continue
        if date_hi and (m.date is None or m.date > date_hi):
            continue
        if stage and (m.stage or "").lower() != stage.lower():
            continue
        if team_club is not None:
            involved = m._home_club == team_club.id or m._away_club == team_club.id
            if not involved:
                continue
            if opponent_club is not None:
                other = m._away_club if m._home_club == team_club.id else m._home_club
                if other != opponent_club.id:
                    continue
        result.append(m)

    result.sort(key=lambda m: (m.date is None, m.date or Date.min, m.competition))
    total = len(result)
    limit = max(0, min(int(limit), 500))
    page = result[:limit]
    return {
        "total_matches": total,
        "returned": len(page),
        "truncated": total > len(page),
        "matches": [m.to_dict() for m in page],
        "notes": ambiguous or None,
    }


def head_to_head(
    ds: Dataset,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: Any = None,
    limit: int = 100,
) -> dict:
    """Head-to-head record between two teams (matches plus W/D/L summary)."""
    comp = resolve_competition_or_raise(competition) if competition else None
    season_n = _coerce_season(season)
    club_a = resolve_club_or_raise(ds, team_a)
    club_b = resolve_club_or_raise(ds, team_b)
    if club_a.id == club_b.id:
        raise ValueError("team_a and team_b resolve to the same club.")

    fixtures = [
        m
        for m in ds.matches
        if (comp is None or m.competition == comp)
        and (season_n is None or m.season == season_n)
        and {m._home_club, m._away_club} == {club_a.id, club_b.id}
    ]
    fixtures.sort(key=lambda m: (m.date is None, m.date or Date.min))

    a_wins = b_wins = draws = goals_a = goals_b = 0
    scored = 0
    for m in fixtures:
        if not m.has_score:
            continue
        scored += 1
        a_home = m._home_club == club_a.id
        ga, gb = (m.home_goals, m.away_goals) if a_home else (m.away_goals, m.home_goals)
        goals_a += ga
        goals_b += gb
        if ga > gb:
            a_wins += 1
        elif gb > ga:
            b_wins += 1
        else:
            draws += 1

    by_comp: dict[str, dict] = {}
    for m in fixtures:
        slot = by_comp.setdefault(m.competition, {"matches": 0, "a_wins": 0, "b_wins": 0, "draws": 0})
        slot["matches"] += 1
        if not m.has_score:
            continue
        a_home = m._home_club == club_a.id
        ga, gb = (m.home_goals, m.away_goals) if a_home else (m.away_goals, m.home_goals)
        if ga > gb:
            slot["a_wins"] += 1
        elif gb > ga:
            slot["b_wins"] += 1
        else:
            slot["draws"] += 1

    limit = max(0, min(int(limit), 500))
    page = fixtures[-limit:] if limit else []
    return {
        "team_a": club_a.display,
        "team_b": club_b.display,
        "filters": {"competition": comp, "season": season_n},
        "summary": {
            "matches": len(fixtures),
            "scored_matches": scored,
            f"{club_a.display} wins": a_wins,
            f"{club_b.display} wins": b_wins,
            "draws": draws,
            f"{club_a.display} goals": goals_a,
            f"{club_b.display} goals": goals_b,
        },
        "by_competition": by_comp or None,
        "matches": [m.to_dict() for m in page],
        "notes": (
            [f"{s} also matches {a}" for s, a in ((team_a, club_a.display),)]
            if _alternates_for(ds, team_a, club_a)
            else None
        ),
    }


def last_match(ds: Dataset, team: str, opponent: str | None = None) -> dict:
    """Most recent match of a team (optionally against a specific opponent)."""
    club = resolve_club_or_raise(ds, team)
    opp = resolve_club_or_raise(ds, opponent) if opponent else None
    candidates = [
        m
        for m in ds.matches
        if (m._home_club == club.id or m._away_club == club.id)
        and (opp is None or m._home_club == opp.id or m._away_club == opp.id)
    ]
    if not candidates:
        return {"team": club.display, "last_match": None}
    latest = max(candidates, key=lambda m: (m.date is not None, m.date or Date.min))
    return {"team": club.display, "last_match": latest.to_dict()}


# --------------------------------------------------------------------------
# Team queries
# --------------------------------------------------------------------------


def _record_for(matches: list[Match], club_id: str, venue: str | None = None) -> dict:
    """Aggregate W/D/L/GF/GA for one club over a match list."""
    played = wins = draws = losses = gf = ga = 0
    for m in matches:
        if not m.has_score:
            continue
        is_home = m._home_club == club_id
        if venue == "home" and not is_home:
            continue
        if venue == "away" and is_home:
            continue
        played += 1
        f, a = (m.home_goals, m.away_goals) if is_home else (m.away_goals, m.home_goals)
        gf += f
        ga += a
        if f > a:
            wins += 1
        elif a > f:
            losses += 1
        else:
            draws += 1
    win_rate = round(wins / played * 100, 1) if played else 0.0
    return {
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "win_rate": win_rate,
    }


def team_record(
    ds: Dataset,
    team: str,
    competition: str | None = None,
    season: Any = None,
    venue: str | None = None,
) -> dict:
    """Win/draw/loss record for a team, optionally per competition/season/venue."""
    if venue not in (None, "home", "away"):
        raise ValueError("venue must be 'home', 'away' or omitted.")
    comp = resolve_competition_or_raise(competition) if competition else None
    season_n = _coerce_season(season)
    club = resolve_club_or_raise(ds, team)

    pool = [
        m
        for m in ds.matches
        if (m._home_club == club.id or m._away_club == club.id)
        and (comp is None or m.competition == comp)
        and (season_n is None or m.season == season_n)
    ]

    by_comp: dict[str, dict] = {}
    by_season: dict[int, dict] = {}
    for m in pool:
        by_comp.setdefault(m.competition, []).append(m)
        if m.season is not None:
            by_season.setdefault(m.season, []).append(m)

    notes = _alternates_for(ds, team, club) or None

    # Completeness note for league seasons with missing scores.
    if comp in LEAGUE_COMPETITIONS and season_n is not None:
        season_pool = [m for m in ds.matches if m.competition == comp and m.season == season_n]
        teams_in_season = {cid for m in season_pool for cid in (m._home_club, m._away_club)}
        if len(teams_in_season) > 1:
            expected = len(teams_in_season) - 1
            if venue is None:
                expected *= 2
            played = _record_for(pool, club.id, venue)["matches"]
            if played < expected:
                note = (
                    f"Data incomplete: only {played} of ~{expected} expected "
                    f"{(venue or '') + ' ' if venue else ''}matches have scores in the source data."
                )
                notes = [note] + (notes or [])

    return {
        "team": club.display,
        "filters": {"competition": comp, "season": season_n, "venue": venue},
        "overall": _record_for(pool, club.id, venue),
        "by_competition": {c: _record_for(ms, club.id, venue) for c, ms in sorted(by_comp.items())},
        "by_season": (
            {s: _record_for(ms, club.id, venue) for s, ms in sorted(by_season.items())}
            if season_n is None
            else None
        ),
        "notes": notes,
    }


def team_profile(ds: Dataset, team: str) -> dict:
    """Cross-file profile of a club: matches, competitions, players."""
    club = resolve_club_or_raise(ds, team)
    matches = ds.matches_for_club(club.id)
    by_comp: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        by_comp[m.competition].append(m)

    competitions = {}
    for comp, ms in sorted(by_comp.items()):
        seasons = sorted({m.season for m in ms if m.season is not None})
        competitions[comp] = {
            "matches": len(ms),
            "seasons": seasons,
            "record": _record_for(ms, club.id),
        }

    players = [p for p in ds.players if p._club_id == club.id]
    players.sort(key=lambda p: -p.overall)

    biggest = [
        m
        for m in matches
        if m.has_score
        and (
            (m._home_club == club.id and m.home_goals - m.away_goals >= 4)
            or (m._away_club == club.id and m.away_goals - m.home_goals >= 4)
        )
    ]
    biggest.sort(key=lambda m: -(m.margin or 0))

    return {
        "club": club.display,
        "club_id": club.id,
        "state": club.state,
        "aliases": club.variants[:8],
        "matches_in_dataset": len(matches),
        "overall_record": _record_for(matches, club.id),
        "competitions": competitions,
        "fifa_players": {
            "count": len(players),
            "average_overall": round(sum(p.overall for p in players) / len(players), 1) if players else None,
            "top": [p.to_dict() for p in players[:5]],
        },
        "biggest_wins": [m.to_dict() for m in biggest[:5]],
        "note": (
            "No players from the FIFA dataset are linked to this club "
            "(the FIFA source omits several Brazilian club rosters)."
            if not players
            else None
        ),
    }


def list_teams(ds: Dataset, competition: str | None = None, season: Any = None) -> dict:
    """Teams present in a competition (and optionally a season)."""
    comp = resolve_competition_or_raise(competition) if competition else None
    season_n = _coerce_season(season)
    pool = [
        m
        for m in ds.matches
        if (comp is None or m.competition == comp) and (season_n is None or m.season == season_n)
    ]
    counts: dict[str, int] = defaultdict(int)
    displays: dict[str, str] = {}
    for m in pool:
        counts[m._home_club] += 1
        counts[m._away_club] += 1
        displays[m._home_club] = m.home_name
        displays[m._away_club] = m.away_name
    teams = [
        {"team": displays[cid], "matches": n}
        for cid, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return {
        "competition": comp,
        "season": season_n,
        "team_count": len(teams),
        "teams": teams,
    }


# --------------------------------------------------------------------------
# Competition queries
# --------------------------------------------------------------------------


def _season_matches(ds: Dataset, competition: str, season: int) -> list[Match]:
    return [m for m in ds.matches if m.competition == competition and m.season == season]


def _compute_table(matches: list[Match], venue: str | None = None) -> tuple[list[StandingRow], int, int]:
    """Build a league table; returns (rows, matches_count, scored_count)."""
    stats: dict[str, dict] = {}
    displays: dict[str, str] = {}
    scored = 0
    for m in matches:
        if m.home_name:
            displays[m._home_club] = m.home_name
        if m.away_name:
            displays[m._away_club] = m.away_name
        for cid in (m._home_club, m._away_club):
            stats.setdefault(cid, {"m": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0})
        if not m.has_score:
            continue
        scored += 1
        # Per-club aggregation with optional venue filter.
        for cid, is_home in ((m._home_club, True), (m._away_club, False)):
            if venue == "home" and not is_home:
                continue
            if venue == "away" and is_home:
                continue
            s = stats[cid]
            gf, ga = (m.home_goals, m.away_goals) if is_home else (m.away_goals, m.home_goals)
            s["m"] += 1
            s["gf"] += gf
            s["ga"] += ga
            if gf > ga:
                s["w"] += 1
                s["pts"] += 3
            elif gf < ga:
                s["l"] += 1
            else:
                s["d"] += 1
                s["pts"] += 1

    ordered = sorted(
        stats.items(),
        key=lambda kv: (-kv[1]["pts"], -kv[1]["w"], -(kv[1]["gf"] - kv[1]["ga"]), -kv[1]["gf"]),
    )
    rows = []
    for rank, (cid, s) in enumerate(ordered, start=1):
        rows.append(
            StandingRow(
                rank=rank,
                team=displays.get(cid, cid),
                matches=s["m"],
                wins=s["w"],
                draws=s["d"],
                losses=s["l"],
                goals_for=s["gf"],
                goals_against=s["ga"],
                goal_diff=s["gf"] - s["ga"],
                points=s["pts"],
            )
        )
    return rows, len(matches), scored


def standings(
    ds: Dataset,
    competition: str,
    season: Any,
    venue: str | None = None,
) -> dict:
    """League table computed from match results (leagues only)."""
    comp = resolve_competition_or_raise(competition)
    season_n = _coerce_season(season)
    if season_n is None:
        raise ValueError("A season (year) is required, e.g. season=2019.")
    if venue not in (None, "home", "away"):
        raise ValueError("venue must be 'home', 'away' or omitted.")
    if comp in CUP_COMPETITIONS:
        raise ValueError(
            f"{comp} is a knockout competition - standings are not defined. "
            f"Use champion() or bracket() instead."
        )

    matches = _season_matches(ds, comp, season_n)
    if not matches:
        raise ValueError(f"No matches found for {comp} {season_n} in the dataset.")

    rows, total, scored = _compute_table(matches, venue)

    # Completeness: double round-robin expectation for Serie A/B-style leagues.
    notes = []
    team_count = len(rows)
    expected = team_count * (team_count - 1) if team_count > 1 else None
    if expected and scored < expected and comp in {"Brasileirão Serie A", "Brasileirão Serie B"}:
        notes.append(
            f"Data incomplete: {scored} of {expected} expected matches have scores "
            f"in the source data; the table may shift."
        )
    if rows and venue is None:
        rows[0].notes.append("Champion (leader in available data)")
        if comp in {"Brasileirão Serie A", "Brasileirão Serie B"} and len(rows) >= 4:
            for row in rows[-4:]:
                row.notes.append("Relegation zone (bottom 4)")

    source = ds.season_sources.get((comp, season_n), {}).get("source")
    return {
        "competition": comp,
        "season": season_n,
        "source": source,
        "venue": venue,
        "matches": total,
        "scored_matches": scored,
        "team_count": team_count,
        "table": [r.to_dict() for r in rows],
        "champion": rows[0].team if rows else None,
        "relegated": [r.team for r in rows[-4:]] if len(rows) >= 4 else [],
        "notes": notes or None,
    }


def _cup_finals(ds: Dataset, competition: str, season: int) -> list[Match] | None:
    """Final-round matches of a cup season, or None if not determinable.

    Copa do Brasil: the highest-numbered round is the final when it has at
    most 2 matches (the two-legged final); more matches mean the data cut
    off mid-tournament.  Copa Libertadores: matches with stage 'final'.
    """
    matches = _season_matches(ds, competition, season)
    if not matches:
        return None
    if competition == "Copa Libertadores":
        finals = [m for m in matches if (m.stage or "").lower() == "final"]
        return finals or None
    rounds: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        if m.round:
            rounds[m.round].append(m)
    if not rounds:
        return None
    try:
        max_round = max(rounds, key=lambda r: int(r))
    except ValueError:
        return None
    final_matches = rounds[max_round]
    return final_matches if len(final_matches) <= 2 else None


def champion(ds: Dataset, competition: str, season: Any) -> dict:
    """Winner of a competition-season (league table or cup final aggregate)."""
    comp = resolve_competition_or_raise(competition)
    season_n = _coerce_season(season)
    if season_n is None:
        raise ValueError("A season (year) is required, e.g. season=2019.")

    if comp in LEAGUE_COMPETITIONS:
        table = standings(ds, comp, season_n)
        top = table["table"][0]
        return {
            "competition": comp,
            "season": season_n,
            "format": "league",
            "champion": top["team"],
            "record": {
                k: top[k]
                for k in ("matches", "wins", "draws", "losses", "goals_for", "goals_against", "points")
            },
            "notes": table["notes"],
        }

    finals = _cup_finals(ds, comp, season_n)
    if finals is None:
        return {
            "competition": comp,
            "season": season_n,
            "format": "cup",
            "champion": None,
            "note": "Final for this season is not present (or not identifiable) in the dataset.",
        }

    scored = [m for m in finals if m.has_score]
    if not scored:
        return {
            "competition": comp,
            "season": season_n,
            "format": "cup",
            "champion": None,
            "final_matches": [m.to_dict() for m in finals],
            "note": "Final found but scores are not recorded in the dataset.",
        }

    totals: dict[str, int] = defaultdict(int)
    displays: dict[str, str] = {}
    for m in scored:
        totals[m._home_club] += m.home_goals or 0
        totals[m._away_club] += m.away_goals or 0
        displays[m._home_club] = m.home_name
        displays[m._away_club] = m.away_name
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    winner, note = None, None
    if len(ranked) == 2 and ranked[0][1] > ranked[1][1]:
        winner = displays[ranked[0][0]]
    elif len(ranked) == 2:
        note = (
            f"Aggregate tied {ranked[0][1]}-{ranked[1][1]} over the final; "
            "the winner was decided on penalties, which the dataset does not record."
        )
    return {
        "competition": comp,
        "season": season_n,
        "format": "cup",
        "champion": winner,
        "final_matches": [m.to_dict() for m in finals],
        "aggregate": {displays[c]: g for c, g in ranked},
        "note": note,
    }


def bracket(ds: Dataset, competition: str, season: Any) -> dict:
    """Knockout rounds of a cup season, final first."""
    comp = resolve_competition_or_raise(competition)
    season_n = _coerce_season(season)
    if season_n is None:
        raise ValueError("A season (year) is required, e.g. season=2018.")
    if comp not in CUP_COMPETITIONS:
        raise ValueError(f"{comp} is a league - use standings() instead.")
    matches = _season_matches(ds, comp, season_n)
    if not matches:
        raise ValueError(f"No matches found for {comp} {season_n} in the dataset.")

    rounds: dict[str, list[Match]] = defaultdict(list)
    group_stage_count = 0
    for m in matches:
        if m.stage:
            key = m.stage
        elif m.round:
            key = f"round:{m.round}"
        else:
            key = "other"
        if key == "group stage":
            group_stage_count += 1
            continue
        rounds[key].append(m)

    stage_order = {
        "round of 16": 4,
        "quarterfinals": 3,
        "semifinals": 2,
        "final": 1,
    }
    round_keys = [k for k in rounds if k.startswith("round:")]
    try:
        max_round_no = max(int(k.split(":", 1)[1]) for k in round_keys)
    except ValueError:
        max_round_no = None

    def label(key: str, ms: list[Match]) -> tuple[int, str]:
        if key.startswith("round:"):
            n = key.split(":", 1)[1]
            # A cup "final" round is the highest-numbered round with <=2 matches.
            if max_round_no is not None:
                try:
                    is_final = int(n) == max_round_no and len(ms) <= 2
                except ValueError:
                    is_final = False
                if is_final:
                    return (0, "Final")
                # Later rounds first (final-ward ordering after the Final).
                return (100 + (max_round_no - int(n)), f"Round {n}")
            return (100, f"Round {n}")
        return (stage_order.get(key, 50), key.replace("_", " ").title())

    labeled = sorted(
        ((label(k, ms), ms) for k, ms in rounds.items()),
        key=lambda kv: kv[0][0],
    )
    structure = [
        {"round": name, "matches": [m.to_dict() for m in sorted(ms, key=lambda x: x.date or Date.min)]}
        for (_, name), ms in labeled
    ]
    return {
        "competition": comp,
        "season": season_n,
        "group_stage_matches": group_stage_count or None,
        "rounds": structure,
    }


def competition_info(ds: Dataset, competition: str | None = None) -> dict:
    """Seasons, sources and champions for one or all competitions."""
    wanted = resolve_competition_or_raise(competition) if competition else None
    per: dict[str, dict[int, dict]] = defaultdict(dict)
    for (comp, season), info in ds.season_sources.items():
        if season is None:
            continue
        if wanted and comp != wanted:
            continue
        per[comp][season] = info

    competitions = {}
    for comp in sorted(per):
        seasons = []
        for season in sorted(per[comp]):
            info = per[comp][season]
            entry: dict[str, Any] = {
                "season": season,
                "matches": info["matches"],
                "source": info["source"],
            }
            try:
                champ = champion(ds, comp, season)
                entry["champion"] = champ.get("champion")
                if champ.get("note"):
                    entry["note"] = champ["note"]
            except ValueError:
                pass
            seasons.append(entry)
        competitions[comp] = {
            "format": "league" if comp in LEAGUE_COMPETITIONS else "cup",
            "seasons": seasons,
        }
    if not competitions:
        raise ValueError(f"No data found for competition {competition!r}.")
    return {"competitions": competitions}


# --------------------------------------------------------------------------
# Player queries
# --------------------------------------------------------------------------


def _position_filter(position: str | None) -> frozenset[str] | None:
    if not position:
        return None
    key = position.strip().lower()
    if key in _POSITION_GROUPS:
        return _POSITION_GROUPS[key]
    if key in ("gk", "gol", "goalkeeper"):
        return _POSITION_GROUPS["goalkeeper"]
    if key in ("fwd", "striker", "atacante"):
        return _POSITION_GROUPS["forward"]
    if key in ("mid", "meia"):
        return _POSITION_GROUPS["midfielder"]
    if key in ("def", "zagueiro", "defender"):
        return _POSITION_GROUPS["defender"]
    return frozenset({position.strip().upper()})


def _player_matches(
    p,
    *,
    name: str | None,
    club_id: str | None,
    nationality: str | None,
    positions: frozenset[str] | None,
    min_overall: int | None,
    max_overall: int | None,
    raw_club_substr: str | None,
) -> bool:
    if name and fold_accents(name).lower() not in fold_accents(p.name).lower():
        return False
    if club_id is not None and p._club_id != club_id:
        # Fall back to raw club-string containment only when the registry
        # could not resolve the club query at all.
        if raw_club_substr is None:
            return False
        if fold_accents(raw_club_substr).lower() not in fold_accents(p.club).lower():
            return False
    if nationality and fold_accents(nationality).lower() != fold_accents(p.nationality).lower():
        return False
    if positions and (p.position is None or p.position.upper() not in positions):
        return False
    if min_overall is not None and p.overall < min_overall:
        return False
    return not (max_overall is not None and p.overall > max_overall)


def find_players(
    ds: Dataset,
    name: str | None = None,
    club: str | None = None,
    nationality: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    limit: int = 50,
) -> dict:
    """Search the FIFA player database by name/club/nationality/position/rating."""
    if not any([name, club, nationality, position, min_overall is not None, max_overall is not None]):
        raise ValueError("Provide at least one filter (name, club, nationality, position, min_overall...).")
    positions = _position_filter(position)
    club_id = None
    raw_club_substr = None
    if club:
        ranked = ds.registry.resolve(club)
        if ranked:
            club_id = ranked[0].id
        else:
            raw_club_substr = club

    found = [
        p
        for p in ds.players
        if _player_matches(
            p,
            name=name,
            club_id=club_id,
            nationality=nationality,
            positions=positions,
            min_overall=min_overall,
            max_overall=max_overall,
            raw_club_substr=raw_club_substr,
        )
    ]
    found.sort(key=lambda p: (-p.overall, p.name))
    total = len(found)
    limit = max(0, min(int(limit), 500))
    page = found[:limit]
    result = {
        "total": total,
        "returned": len(page),
        "truncated": total > len(page),
        "players": [p.to_dict() for p in page],
    }
    if club and total == 0:
        result["note"] = (
            f"No players found for club {club!r}. Note: the FIFA source omits "
            "several Brazilian club rosters (e.g. Flamengo, Palmeiras, "
            "Corinthians, São Paulo)."
        )
    return result


def top_players(
    ds: Dataset,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    limit: int = 10,
) -> dict:
    """Highest-rated players, filterable by nationality/club/position."""
    return find_players(
        ds,
        club=club,
        nationality=nationality,
        position=position,
        limit=max(1, min(int(limit), 100)),
    )


def players_at_club(ds: Dataset, club: str, limit: int = 100) -> dict:
    """Roster summary for a club in the FIFA dataset."""
    ranked = ds.registry.resolve(club)
    if not ranked:
        raise ValueError(f"No club matching {club!r} was found.")
    target = ranked[0]
    players = [p for p in ds.players if p._club_id == target.id]
    players.sort(key=lambda p: (-p.overall, p.name))
    by_pos: dict[str, int] = defaultdict(int)
    for p in players:
        by_pos[p.position or "?"] += 1
    limit = max(0, min(int(limit), 500))
    source_names = sorted({p.club for p in players if p.club})
    return {
        "club": target.display,
        "fifa_source_club_name": source_names[0] if source_names else None,
        "count": len(players),
        "average_overall": round(sum(p.overall for p in players) / len(players), 1) if players else None,
        "by_position": dict(sorted(by_pos.items())) or None,
        "players": [p.to_dict() for p in players[:limit]],
        "note": (
            "The FIFA source omits several Brazilian club rosters "
            "(e.g. Flamengo, Palmeiras, Corinthians, São Paulo)."
            if not players
            else None
        ),
    }


# --------------------------------------------------------------------------
# Statistical analysis
# --------------------------------------------------------------------------


def season_averages(ds: Dataset, competition: str, season: Any = None) -> dict:
    """Goals per match and home/draw/away win rates for a competition(-season)."""
    comp = resolve_competition_or_raise(competition)
    season_n = _coerce_season(season)
    pool = [
        m
        for m in ds.matches
        if m.competition == comp and m.has_score and (season_n is None or m.season == season_n)
    ]
    if not pool:
        raise ValueError(f"No scored matches for {comp}" + (f" {season_n}" if season_n else "") + ".")
    n = len(pool)
    home_wins = sum(1 for m in pool if m.winner == "home")
    away_wins = sum(1 for m in pool if m.winner == "away")
    draws = n - home_wins - away_wins
    total_goals = sum(m.home_goals + m.away_goals for m in pool)
    return {
        "competition": comp,
        "season": season_n,
        "matches": n,
        "total_goals": total_goals,
        "average_goals_per_match": round(total_goals / n, 2),
        "average_home_goals": round(sum(m.home_goals for m in pool) / n, 2),
        "average_away_goals": round(sum(m.away_goals for m in pool) / n, 2),
        "home_win_rate": round(home_wins / n * 100, 1),
        "draw_rate": round(draws / n * 100, 1),
        "away_win_rate": round(away_wins / n * 100, 1),
    }


def biggest_wins(
    ds: Dataset,
    competition: str | None = None,
    season: Any = None,
    limit: int = 10,
) -> dict:
    """Largest victory margins in the dataset."""
    comp = resolve_competition_or_raise(competition) if competition else None
    season_n = _coerce_season(season)
    pool = [
        m
        for m in ds.matches
        if m.has_score
        and (comp is None or m.competition == comp)
        and (season_n is None or m.season == season_n)
    ]
    pool.sort(key=lambda m: (-(m.margin or 0), -(m.home_goals + m.away_goals)))
    limit = max(1, min(int(limit), 100))
    top = pool[:limit]
    return {
        "competition": comp,
        "season": season_n,
        "matches": [{**m.to_dict(), "margin": m.margin} for m in top],
    }


def derby_matches(
    ds: Dataset,
    season: Any = None,
    competition: str | None = None,
    limit: int = 100,
) -> dict:
    """Matches between famous rival pairs (Fla-Flu, Gre-Nal, ...)."""
    comp = resolve_competition_or_raise(competition) if competition else None
    season_n = _coerce_season(season)
    result = []
    for name, a, b in DERBIES:
        club_a = ds.registry.get(_club_team_from_key(a))
        club_b = ds.registry.get(_club_team_from_key(b))
        if club_a is None or club_b is None:
            continue
        fixtures = [
            m
            for m in ds.matches
            if {m._home_club, m._away_club} == {club_a.id, club_b.id}
            and (comp is None or m.competition == comp)
            and (season_n is None or m.season == season_n)
        ]
        if not fixtures:
            continue
        fixtures.sort(key=lambda m: (m.date is None, m.date or Date.min))
        limit_n = max(1, min(int(limit), 500))
        result.append(
            {
                "derby": name,
                "teams": f"{club_a.display} x {club_b.display}",
                "total_matches": len(fixtures),
                "matches": [m.to_dict() for m in fixtures[-limit_n:]],
            }
        )
    return {"season": season_n, "competition": comp, "derbies": result}


def _club_team_from_key(key: str):
    from .normalize import TeamName

    base, _, state = key.rpartition("|")
    return TeamName(base, state or None)


def match_statistics(
    ds: Dataset,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: Any = None,
    limit: int = 50,
) -> dict:
    """Extended per-match statistics (corners, shots, attacks) from BR-Football."""
    comp = resolve_competition_or_raise(competition) if competition else None
    season_n = _coerce_season(season)
    team_club = resolve_club_or_raise(ds, team) if team else None
    opponent_club = resolve_club_or_raise(ds, opponent) if opponent else None

    pool = [
        m
        for m in ds.raw_matches
        if m.source == "BR-Football-Dataset"
        and (comp is None or m.competition == comp)
        and (season_n is None or m.season == season_n)
        and (team_club is None or m._home_club == team_club.id or m._away_club == team_club.id)
        and (opponent_club is None or m._home_club == opponent_club.id or m._away_club == opponent_club.id)
    ]
    pool.sort(key=lambda m: (m.date is None, m.date or Date.min))
    limit = max(0, min(int(limit), 500))
    return {
        "total_matches": len(pool),
        "returned": min(len(pool), limit),
        "matches": [m.to_dict() for m in pool[:limit]],
        "note": "Extended statistics are only available for BR-Football-Dataset rows (2014-2023)."
        if pool
        else "No matching matches with statistics found.",
    }


# --------------------------------------------------------------------------
# Team-name resolution helper (exposed as its own tool)
# --------------------------------------------------------------------------


def resolve_team_info(ds: Dataset, name: str) -> dict:
    """Show how a team name resolves in the knowledge graph."""
    ranked = ds.registry.resolve(name)
    if not ranked:
        raise ValueError(f"No team matching {name!r} was found in the dataset.")
    return {
        "query": name,
        "matches": [
            {
                "club": c.display,
                "club_id": c.id,
                "state": c.state,
                "match_appearances": c.match_count,
                "fifa_players": c.player_count,
                "spelling_variants": c.variants[:8],
            }
            for c in ranked
        ],
    }
