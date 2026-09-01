"""Query layer: every natural-language question category from the spec is
answered by one of these functions, each returning a JSON-serializable dict.

Categories (per TASK.md):
1. Match queries        -> search_matches, head_to_head, find_finals
2. Team queries         -> team_stats, club_overview, resolve_team_info
3. Player queries       -> search_players
4. Competition queries  -> standings, relegated_teams, competitions_overview
5. Statistical analysis -> competition_stats, biggest_wins, derby_matches,
                           search_match_stats
"""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict

from .data import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    POSITION_GROUPS,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    SoccerData,
    TeamInfo,
)
from .dates import parse_date
from .models import Match, Player
from .normalize import (
    COMPETITIONS,
    DERBIES,
    TeamResolutionError,
    competition_label,
    fold_text,
    team_key,
)

DEFAULT_MATCH_LIMIT = 25
DEFAULT_PLAYER_LIMIT = 20

_STAGE_ALIASES: dict[str, str] = {
    "final": "final",
    "finals": "final",
    "the final": "final",
    "semi": "semifinals",
    "semis": "semifinals",
    "semifinal": "semifinals",
    "semifinals": "semifinals",
    "quarter": "quarterfinals",
    "quarters": "quarterfinals",
    "quarterfinal": "quarterfinals",
    "quarterfinals": "quarterfinals",
    "round of 16": "round of 16",
    "last 16": "round of 16",
    "roundof16": "round of 16",
    "group": "group stage",
    "groups": "group stage",
    "group stage": "group stage",
}


def _canonical_stage(query: str) -> str:
    folded = fold_text(query)
    return _STAGE_ALIASES.get(folded, folded)


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _resolve_competition(name: str | None) -> str | None:
    if name is None:
        return None
    label = competition_label(name)
    if label is None:
        known = ", ".join(COMPETITIONS)
        raise TeamResolutionError(
            f"Competition '{name}' not recognized. Known competitions: {known}."
        )
    return label


def _resolve_team(data: SoccerData, name: str) -> str:
    return data.resolve_team(name)


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def _goal_diff(match: Match) -> int:
    """Absolute goal difference; unplayed matches count as 0."""
    pair = match.goal_pair()
    return abs(pair[0] - pair[1]) if pair else 0


def _goal_total(match: Match) -> int:
    pair = match.goal_pair()
    return pair[0] + pair[1] if pair else 0


def _pick(conditions: list, matches: list[Match]) -> list[Match]:
    return [m for m in matches if all(cond(m) for cond in conditions)]


# --------------------------------------------------------------------------
# 1. Match queries
# --------------------------------------------------------------------------


def search_matches(
    data: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    round: int | None = None,
    limit: int = DEFAULT_MATCH_LIMIT,
) -> dict:
    """Find matches by team, opponent, competition, season, date range, stage/round."""
    comp = _resolve_competition(competition)
    team_key_ = _resolve_team(data, team) if team else None
    opp_key = _resolve_team(data, opponent) if opponent else None
    lower = parse_date(date_from)
    upper = parse_date(date_to)

    conditions = []
    if team_key_:
        conditions.append(lambda m: team_key_ in (m.home, m.away))
    if opp_key:
        conditions.append(lambda m: opp_key in (m.home, m.away))
    if team_key_ and opp_key:
        conditions.append(
            lambda m: {m.home, m.away} == {team_key_, opp_key}
        )
    if comp:
        conditions.append(lambda m: m.competition == comp)
    if season is not None:
        conditions.append(lambda m: m.season == int(season))
    if lower:
        conditions.append(lambda m: m.date is not None and m.date >= lower)
    if upper:
        conditions.append(lambda m: m.date is not None and m.date <= upper)
    if stage:
        canonical = _canonical_stage(stage)
        conditions.append(lambda m: m.stage and fold_text(m.stage) == canonical)
    if round is not None:
        conditions.append(lambda m: m.round_number == int(round))

    found = _pick(conditions, data.matches)
    found.sort(key=lambda m: m.date or dt.date.min, reverse=True)
    truncated = len(found) > limit
    return {
        "total_matches": len(found),
        "returned": min(len(found), limit),
        "truncated": truncated,
        "matches": [m.as_dict() for m in found[:limit]],
    }


def head_to_head(
    data: SoccerData,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
    limit: int | None = None,
) -> dict:
    """Full head-to-head record between two teams."""
    key_a = _resolve_team(data, team_a)
    key_b = _resolve_team(data, team_b)
    if key_a == key_b:
        raise TeamResolutionError("Please provide two different teams.")
    comp = _resolve_competition(competition)

    conditions = [lambda m: {m.home, m.away} == {key_a, key_b}]
    if comp:
        conditions.append(lambda m: m.competition == comp)
    if season is not None:
        conditions.append(lambda m: m.season == int(season))

    played = [m for m in _pick(conditions, data.matches) if m.played]
    played.sort(key=lambda m: m.date or dt.date.min)

    wins_a = wins_b = draws = 0
    goals_a = goals_b = 0
    for m in played:
        pair = m.goal_pair()
        assert pair is not None, "played matches always carry goals"
        if m.home == key_a:
            gf, ga = pair
        else:
            gf, ga = pair[1], pair[0]
        goals_a += gf
        goals_b += ga
        if gf > ga:
            wins_a += 1
        elif gf < ga:
            wins_b += 1
        else:
            draws += 1

    shown = played if limit is None else played[-limit:]
    return {
        "team_a": data.teams[key_a].display,
        "team_b": data.teams[key_b].display,
        "competition": comp,
        "season": season,
        "total_matches": len(played),
        "record": {
            f"{data.teams[key_a].display}_wins": wins_a,
            f"{data.teams[key_b].display}_wins": wins_b,
            "draws": draws,
        },
        "goals": {data.teams[key_a].display: goals_a, data.teams[key_b].display: goals_b},
        "latest_match": played[-1].as_dict() if played else None,
        "matches": [m.as_dict() for m in shown],
    }


def find_finals(
    data: SoccerData, competition: str, season: int | None = None
) -> dict:
    """Final (or decisive) matches of cup competitions, by season."""
    comp = _resolve_competition(competition)
    if comp in (SERIE_A, SERIE_B, SERIE_C):
        return {
            "competition": comp,
            "finals": [],
            "note": (
                f"{comp} is a league decided on a standings table, not a final. "
                "Use get_standings to see each season's champion."
            ),
        }

    pool = [m for m in data.matches if m.competition == comp]
    if season is not None:
        pool = [m for m in pool if m.season == int(season)]

    finals: list[dict] = []
    by_season: dict[int | None, list[Match]] = defaultdict(list)
    for m in pool:
        by_season[m.season].append(m)
    for season_key in sorted(by_season, key=lambda s: (s is None, s)):
        matches = by_season[season_key]
        if comp == LIBERTADORES:
            decisive = [m for m in matches if (m.stage or "").lower() == "final"]
        else:
            max_round = max(
                (m.round_number for m in matches if m.round_number), default=None
            )
            decisive = (
                [m for m in matches if m.round_number == max_round] if max_round else []
            )
            if len(decisive) > 2:
                # A real final is at most two legs; a big top round means the
                # dataset ends before the final (e.g. Copa do Brasil 2021).
                finals.append(
                    {
                        "season": season_key,
                        "matches": [],
                        "note": (
                            f"{comp} {season_key} data ends at round {max_round} "
                            f"({len(decisive)} matches); the final itself is not "
                            "in the dataset."
                        ),
                    }
                )
                continue
        if not decisive:
            continue
        entry: dict[str, object] = {
            "season": season_key,
            "matches": [m.as_dict() for m in decisive],
            "winner_on_aggregate": None,
        }
        scored = [m for m in decisive if m.played]
        if scored:
            totals: Counter[str] = Counter()
            for m in scored:
                pair = m.goal_pair()
                assert pair is not None, "played matches always carry goals"
                totals[m.home] += pair[0]
                totals[m.away] += pair[1]
            best = max(totals.values())
            leaders = [k for k, v in totals.items() if v == best]
            entry["winner_on_aggregate"] = (
                data.teams[leaders[0]].display if len(leaders) == 1 else None
            )
            if len(leaders) > 1:
                entry["note"] = "Aggregate tie in recorded goals; tie-breakers are not in the data."
        else:
            entry["note"] = "Final listed in the dataset but score was not recorded."
        finals.append(entry)

    return {"competition": comp, "finals": finals}


# --------------------------------------------------------------------------
# 2. Team queries
# --------------------------------------------------------------------------


def _team_record(matches: list[Match], team: str, venue: str = "all") -> dict:
    """Wins/draws/losses/goals for one team over a list of its matches."""
    wins = draws = losses = 0
    goals_for = goals_against = 0
    considered = 0
    form: list[str] = []
    for m in matches:
        pair = m.goal_pair()
        if pair is None:
            continue
        if venue == "home" and m.home != team:
            continue
        if venue == "away" and m.away != team:
            continue
        considered += 1
        if m.home == team:
            gf, ga = pair
        else:
            gf, ga = pair[1], pair[0]
        goals_for += gf
        goals_against += ga
        if gf > ga:
            wins += 1
            form.append("W")
        elif gf < ga:
            losses += 1
            form.append("L")
        else:
            draws += 1
            form.append("D")
    return {
        "matches": considered,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "win_rate": _round(wins / considered * 100, 1) if considered else 0.0,
        "form_last_10": form[-10:],
    }


def team_stats(
    data: SoccerData,
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> dict:
    """Match record for a team, optionally by season, competition and venue."""
    if venue not in ("all", "home", "away"):
        raise TeamResolutionError("venue must be 'all', 'home' or 'away'.")
    key = _resolve_team(data, team)
    comp = _resolve_competition(competition)

    conditions = []
    if season is not None:
        conditions.append(lambda m: m.season == int(season))
    if comp:
        conditions.append(lambda m: m.competition == comp)
    matches = _pick(conditions, data.matches_for_team(key))

    record = _team_record(matches, key, venue)
    result: dict[str, object] = {
        "team": data.teams[key].display,
        "season": season,
        "competition": comp,
        "venue": venue,
        "record": record,
    }
    unplayed = sum(1 for m in matches if not m.played)
    if unplayed:
        result["data_note"] = (
            f"{unplayed} fixtures for this filter have no recorded score in the "
            "dataset and are excluded from the record."
        )
    if comp is None and record["matches"]:
        by_comp = []
        for competition_name in sorted({m.competition for m in matches}):
            sub = [m for m in matches if m.competition == competition_name]
            by_comp.append(
                {
                    "competition": competition_name,
                    **_team_record(sub, key, venue),
                }
            )
        result["by_competition"] = by_comp
    if season is None and record["matches"]:
        by_season = []
        for season_value in sorted({m.season for m in matches if m.season}):
            sub = [m for m in matches if m.season == season_value]
            by_season.append(
                {
                    "season": season_value,
                    **_team_record(sub, key, venue),
                }
            )
        result["by_season"] = by_season
    return result


def resolve_team_info(data: SoccerData, name: str) -> dict:
    """Show the canonical team and every spelling found across the datasets."""
    key = _resolve_team(data, name)
    info: TeamInfo = data.teams[key]
    played = [m for m in data.matches_for_team(key) if m.played]
    return {
        **info.as_dict(),
        "matches_in_datasets": len(data.matches_for_team(key)),
        "overall_record": _team_record(played, key),
    }


def club_overview(data: SoccerData, club: str) -> dict:
    """Cross-file club profile: match record + FIFA squad (when present)."""
    key = _resolve_team(data, club)
    info = data.teams[key]
    matches = [m for m in data.matches_for_team(key) if m.played]
    competitions_played = sorted({m.competition for m in matches})
    result: dict[str, object] = {
        "club": info.display,
        "competitions_played": competitions_played,
        "overall_record": _team_record(matches, key),
        "by_competition": [
            {"competition": comp, **_team_record([m for m in matches if m.competition == comp], key)}
            for comp in competitions_played
        ],
    }

    squad = [
        p
        for p in data.players
        if p.club and (team_key(p.club) == key or fold_text(p.club) == fold_text(info.display))
    ]
    if squad:
        squad.sort(key=lambda p: (-p.overall, p.name))
        result["fifa_squad"] = {
            "players": len(squad),
            "avg_overall": _round(sum(p.overall for p in squad) / len(squad), 1),
            "top_players": [p.as_dict() for p in squad[:10]],
        }
    else:
        result["fifa_squad"] = None
        result["fifa_squad_note"] = (
            "No FIFA-database players found for this club (the FIFA dataset "
            "covers a subset of Brazilian clubs)."
        )
    return result


# --------------------------------------------------------------------------
# 3. Player queries
# --------------------------------------------------------------------------


def search_players(
    data: SoccerData,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    max_overall: int | None = None,
    min_potential: int | None = None,
    limit: int = DEFAULT_PLAYER_LIMIT,
    sort: str = "overall",
) -> dict:
    """Search the FIFA player database with flexible filters."""
    if position_group and position_group not in POSITION_GROUPS:
        raise TeamResolutionError(
            "position_group must be one of: " + ", ".join(sorted(POSITION_GROUPS))
        )
    group = POSITION_GROUPS.get(position_group or "", set())

    folded_name = fold_text(name) if name else None
    folded_nation = fold_text(nationality) if nationality else None
    folded_club = fold_text(club) if club else None
    folded_position = position.upper() if position else None

    result: list[Player] = []
    for player in data.players:
        if folded_name and folded_name not in fold_text(player.name):
            continue
        if folded_nation and folded_nation not in fold_text(player.nationality):
            continue
        if folded_club and (not player.club or folded_club not in fold_text(player.club)):
            continue
        if folded_position and (player.position or "") != folded_position:
            continue
        if group and (player.position or "") not in group:
            continue
        if min_overall is not None and player.overall < int(min_overall):
            continue
        if max_overall is not None and player.overall > int(max_overall):
            continue
        if min_potential is not None and player.potential < int(min_potential):
            continue
        result.append(player)

    sort_keys = {
        "overall": lambda p: (-p.overall, p.name),
        "potential": lambda p: (-p.potential, p.name),
        "age": lambda p: (p.age if p.age is not None else 999, p.name),
        "value": lambda p: (-(p.value_eur or 0), p.name),
        "name": lambda p: p.name,
    }
    if sort not in sort_keys:
        raise TeamResolutionError(
            "sort must be one of: " + ", ".join(sorted(sort_keys))
        )
    result.sort(key=sort_keys[sort])

    payload = {
        "total_matches": len(result),
        "returned": min(len(result), limit),
        "truncated": len(result) > limit,
        "players": [p.as_dict() for p in result[:limit]],
    }
    if club:
        matched = sorted({p.club for p in result if p.club})
        payload["matched_clubs"] = matched
    if not result and name:
        similar = _players_matching_any_token(data, name)
        payload["note"] = (
            f"No player named '{name}' in the FIFA dataset. "
            f"{len(similar)} players match one of the name's words."
        )
        payload["similar_players"] = [p.as_dict() for p in similar[:10]]
    return payload


def _players_matching_any_token(data: SoccerData, name: str, cap: int = 50) -> list[Player]:
    tokens = {t for t in fold_text(name).split() if len(t) > 2}
    hits: list[Player] = []
    for player in data.players:
        folded = fold_text(player.name)
        if any(t in folded for t in tokens):
            hits.append(player)
    hits.sort(key=lambda p: (-p.overall, p.name))
    return hits[:cap]


def best_players_by_nationality(data: SoccerData, nationality: str, limit: int = 10) -> dict:
    """Convenience view: highest-rated players for a nationality."""
    return search_players(data, nationality=nationality, limit=limit, sort="overall")


# --------------------------------------------------------------------------
# 4. Competition queries
# --------------------------------------------------------------------------


def standings(data: SoccerData, competition: str, season: int) -> dict:
    """League table calculated from match results (3 points per win)."""
    comp = _resolve_competition(competition)
    if comp in (COPA_DO_BRASIL, LIBERTADORES):
        raise TeamResolutionError(
            f"{comp} is a knockout cup; standings tables are not applicable. "
            "Use find_finals for its decisive matches."
        )
    pool = [
        m
        for m in data.matches
        if m.competition == comp and m.season == int(season) and m.played
    ]
    if not pool:
        raise TeamResolutionError(
            f"No {comp} matches found for season {season} in the datasets."
        )
    sources = sorted({m.source for m in pool})
    table: dict[str, dict] = {}
    for m in pool:
        for team in (m.home, m.away):
            table.setdefault(
                team,
                {
                    "team": team,
                    "matches": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0, "points": 0,
                },
            )
        home, away = table[m.home], table[m.away]
        home["matches"] += 1
        away["matches"] += 1
        home["goals_for"] += m.home_goals
        home["goals_against"] += m.away_goals
        away["goals_for"] += m.away_goals
        away["goals_against"] += m.home_goals
        if m.result == "home":
            home["wins"] += 1
            away["losses"] += 1
            home["points"] += 3
        elif m.result == "away":
            away["wins"] += 1
            home["losses"] += 1
            away["points"] += 3
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1

    rows = sorted(
        table.values(),
        key=lambda r: (
            -r["points"],
            -(r["goals_for"] - r["goals_against"]),
            -r["goals_for"],
            data.teams[r["team"]].display,
        ),
    )
    for position, row in enumerate(rows, start=1):
        row["position"] = position
        row["goal_diff"] = row["goals_for"] - row["goals_against"]
        row["team"] = data.teams[row["team"]].display
    champion = rows[0]["team"] if rows else None
    relegated = [r["team"] for r in rows[-4:]] if len(rows) >= 8 else []
    all_fixtures = [
        m
        for m in data.matches
        if m.competition == comp and m.season == int(season)
    ]
    result = {
        "competition": comp,
        "season": int(season),
        "calculated_from": sources,
        "table": rows,
        "champion": champion,
        "relegated_bottom_4": relegated,
    }
    if len(all_fixtures) > len(pool):
        result["data_note"] = (
            f"{len(all_fixtures) - len(pool)} of {len(all_fixtures)} fixtures have no "
            "recorded score in the dataset; the table covers played matches only."
        )
    elif rows and comp in (SERIE_A, SERIE_B):
        n_teams = len(rows)
        expected = 2 * (n_teams - 1)
        short = [r for r in rows if r["matches"] < expected]
        if short:
            missing = sum(expected - r["matches"] for r in short)
            result["data_note"] = (
                f"The dataset is incomplete for this season: {missing} of "
                f"{n_teams * expected} round-robin fixtures are missing, so the "
                "table may differ from the historical record."
            )
    return result


def relegated_teams(data: SoccerData, competition: str, season: int) -> dict:
    """Bottom four of a league season (relegation zone in modern seasons)."""
    table = standings(data, competition, season)
    return {
        "competition": table["competition"],
        "season": table["season"],
        "relegated": table["relegated_bottom_4"],
        "bottom_rows": table["table"][-4:],
    }


def competitions_overview(data: SoccerData) -> dict:
    """Every competition in the datasets with seasons and match counts."""
    per_comp: dict[str, dict[int | None, int]] = defaultdict(lambda: defaultdict(int))
    for m in data.matches:
        per_comp[m.competition][m.season] += 1
    payload: list[tuple[int, dict[str, object]]] = []
    for comp in sorted(per_comp):
        seasons = per_comp[comp]
        total = sum(seasons.values())
        payload.append(
            (
                total,
                {
                    "competition": comp,
                    "seasons": [
                        {"season": season, "matches": count}
                        for season, count in sorted(seasons.items(), key=lambda kv: (kv[0] is None, kv[0]))
                    ],
                    "total_matches": total,
                },
            )
        )
    payload.sort(key=lambda item: -item[0])
    return {
        "competitions": [entry for _total, entry in payload],
        "teams": len(data.teams),
        "players": len(data.players),
        "note": (
            "Seasons are served from the primary source with the richest data "
            "to avoid double counting across overlapping files."
        ),
    }


# --------------------------------------------------------------------------
# 5. Statistical analysis
# --------------------------------------------------------------------------


def competition_stats(
    data: SoccerData, competition: str, season: int | None = None
) -> dict:
    """Aggregate statistics for a competition (and optionally a season)."""
    comp = _resolve_competition(competition)
    conditions = [lambda m: m.competition == comp]
    if season is not None:
        conditions.append(lambda m: m.season == int(season))
    pool = [m for m in _pick(conditions, data.matches) if m.played]
    if not pool:
        raise TeamResolutionError(
            f"No matches found for {comp}" + (f" season {season}" if season else "") + "."
        )
    total_goals = sum(_goal_total(m) for m in pool)
    home_goals_total = 0
    away_goals_total = 0
    for m in pool:
        pair = m.goal_pair()
        assert pair is not None, "pool only contains played matches"
        home_goals_total += pair[0]
        away_goals_total += pair[1]
    home_wins = sum(1 for m in pool if m.result == "home")
    away_wins = sum(1 for m in pool if m.result == "away")
    draws = len(pool) - home_wins - away_wins
    dates = [m.date for m in pool if m.date]
    biggest = max(pool, key=lambda m: _goal_diff(m))
    return {
        "competition": comp,
        "season": season,
        "matches": len(pool),
        "goals_total": total_goals,
        "avg_goals_per_match": _round(total_goals / len(pool)),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_rate": _round(home_wins / len(pool) * 100, 1),
        "draw_rate": _round(draws / len(pool) * 100, 1),
        "away_win_rate": _round(away_wins / len(pool) * 100, 1),
        "avg_home_goals": _round(home_goals_total / len(pool)),
        "avg_away_goals": _round(away_goals_total / len(pool)),
        "date_range": {
            "from": min(dates).isoformat() if dates else None,
            "to": max(dates).isoformat() if dates else None,
        },
        "biggest_win": biggest.as_dict(),
    }


def biggest_wins(
    data: SoccerData,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict:
    """Largest winning margins in the dataset."""
    comp = _resolve_competition(competition)
    conditions = [lambda m: m.played]
    if comp:
        conditions.append(lambda m: m.competition == comp)
    if season is not None:
        conditions.append(lambda m: m.season == int(season))
    pool = _pick(conditions, data.matches)
    pool.sort(
        key=lambda m: (
            -_goal_diff(m),
            -_goal_total(m),
            m.date or dt.date.min,
        )
    )
    winners: list[dict] = []
    for m in pool[:limit]:
        margin = _goal_diff(m)
        winner = (
            data.teams[m.home].display if _goal_diff(m) > 0
            else data.teams[m.away].display
        )
        winners.append({**m.as_dict(), "margin": margin, "winner": winner})
    return {"count": min(len(pool), limit), "matches": winners}


def derby_matches(
    data: SoccerData,
    derby: str | None = None,
    season: int | None = None,
    competition: str | None = None,
    limit: int = 50,
) -> dict:
    """Matches between traditional rivals; omit `derby` to sweep all rivalries."""
    comp = _resolve_competition(competition)
    if derby is None:
        selected = DERBIES
    else:
        folded = fold_text(derby)
        match_found = None
        for name in DERBIES:
            if folded in fold_text(name) or fold_text(name) in folded:
                match_found = name
                break
        if match_found is None:
            raise TeamResolutionError(
                "Unknown derby. Known derbies: " + ", ".join(sorted(DERBIES))
            )
        selected = {match_found: DERBIES[match_found]}

    conditions = []
    if season is not None:
        conditions.append(lambda m: m.season == int(season))
    if comp:
        conditions.append(lambda m: m.competition == comp)

    results = []
    for name, (team_a, team_b) in selected.items():
        pair = {team_a, team_b}
        pool = _pick(
            conditions + [lambda m, pair=pair: {m.home, m.away} == pair],
            data.matches,
        )
        played = [m for m in pool if m.played]
        record = _team_record(played, team_a)
        results.append(
            {
                "derby": name,
                "teams": [data.teams[team_a].display, data.teams[team_b].display],
                "total_matches": len(played),
                "record_for_first_team": record,
                "matches": [m.as_dict() for m in played[-limit:]],
            }
        )
    return {"derbies": results}


def search_match_stats(
    data: SoccerData,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 20,
) -> dict:
    """Extended per-match statistics (corners, shots, attacks) from the
    BR-Football dataset, including seasons it serves as the primary source."""
    comp = _resolve_competition(competition)
    team_key_ = _resolve_team(data, team) if team else None
    opp_key = _resolve_team(data, opponent) if opponent else None

    conditions = [lambda m: m.stats is not None]
    if team_key_:
        conditions.append(lambda m: team_key_ in (m.home, m.away))
    if opp_key:
        conditions.append(lambda m: opp_key in (m.home, m.away))
    if team_key_ and opp_key:
        conditions.append(lambda m: {m.home, m.away} == {team_key_, opp_key})
    if comp:
        conditions.append(lambda m: m.competition == comp)
    if season is not None:
        conditions.append(lambda m: m.season == int(season))

    pool = _pick(conditions, data.matches)
    pool.sort(key=lambda m: m.date or dt.date.min, reverse=True)
    with_stats = [m for m in pool if m.stats is not None]
    return {
        "total_matches": len(with_stats),
        "returned": min(len(with_stats), limit),
        "note": (
            "Extended statistics come from BR-Football-Dataset.csv "
            "(Série A/B/C 2014-2023, Copa do Brasil 2014-2023)."
        ),
        "matches": [m.as_dict() for m in with_stats[:limit]],
    }


def best_home_records(
    data: SoccerData, competition: str, season: int, limit: int = 5
) -> dict:
    """Teams with the best home win rates in a league season."""
    comp = _resolve_competition(competition)
    pool = [
        m
        for m in data.matches
        if m.competition == comp and m.season == int(season) and m.played
    ]
    if not pool:
        raise TeamResolutionError(f"No {comp} matches found for season {season}.")
    records: dict[str, dict] = {}
    for m in pool:
        records.setdefault(m.home, {"matches": 0, "wins": 0, "points": 0})
        records[m.home]["matches"] += 1
        if m.result == "home":
            records[m.home]["wins"] += 1
    ranked = sorted(
        records.items(),
        key=lambda kv: (-(kv[1]["wins"] / kv[1]["matches"]), -kv[1]["matches"]),
    )[:limit]
    return {
        "competition": comp,
        "season": int(season),
        "best_home_records": [
            {
                "team": data.teams[team].display,
                "home_matches": stats["matches"],
                "home_wins": stats["wins"],
                "home_win_rate": _round(stats["wins"] / stats["matches"] * 100, 1),
            }
            for team, stats in ranked
        ],
    }
