"""MCP server exposing Brazilian soccer knowledge over the Kaggle datasets.

Run with::

    python server.py                  # stdio transport (default)
    python server.py --transport streamable-http --port 8321

The server registers 16 tools covering the five capability groups from the
specification: match queries, team queries, player queries, competition
queries and statistical analysis. Every tool returns a JSON object that
pairs a human-readable ``summary`` (formatted like the examples in the
spec) with structured ``data`` so an attached LLM can either relay the
summary verbatim or reason over the raw fields.

Team names in tool arguments are free text: they pass through the
canonical-key normalizer, so "Palmeiras", "palmeiras-sp", "Palmeiras - SP"
and "SE Palmeiras" all resolve to the same club. Genuinely ambiguous
names (e.g. "Atletico", which matches Atlético-MG, Athletico-PR and
Atlético-GO) return a disambiguation payload listing the candidates with
their canonical keys and match counts.
"""

from __future__ import annotations

import argparse
from datetime import date

from mcp.server.mcpserver import MCPServer

from data_loader import (
    COPA_DO_BRASIL,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    SoccerData,
    get_data,
)
from normalize import (
    DERBY_PAIRS,
    canonical_team_key,
    parse_date,
    resolve_competition,
    team_display_name,
)
from stats import (
    best_records,
    biggest_wins,
    champion_and_relegated,
    competition_aggregates,
    derby_matches,
    finals,
    head_to_head,
    standings,
    team_record,
)

POSITION_GROUPS = {
    "goalkeeper": ["GK"],
    "gk": ["GK"],
    "defender": ["CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"],
    "df": ["CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"],
    "midfielder": ["CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"],
    "mf": ["CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM", "LAM", "RAM", "LM", "RM"],
    "forward": ["ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"],
    "fw": ["ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"],
}

LEAGUE_FULL_SEASON = {
    SERIE_A: 380,
    SERIE_B: 380,
    SERIE_C: 190,
}


def _resolve_competition_arg(raw: str | None) -> tuple[str | None, dict | None]:
    if not raw:
        return None, None
    resolved = resolve_competition(raw)
    if resolved is None:
        from data_loader import get_data as _gd

        known = _gd().competitions()
        return None, {
            "error": f"Unknown competition '{raw}'.",
            "known_competitions": known,
        }
    return resolved, None


def _resolve_team_arg(
    query: str | None, data: SoccerData
) -> tuple[str | None, dict | None]:
    if not query:
        return None, None
    exact_key = canonical_team_key(query)
    if exact_key and exact_key in data.teams:
        return exact_key, None
    candidates = data.find_team(query)
    if not candidates:
        return None, {
            "error": f"No team matching '{query}' was found in the dataset.",
        }
    if len(candidates) == 1:
        return candidates[0].key, None
    top, second = candidates[0], candidates[1]
    if top.match_count >= 5 * max(second.match_count, 1):
        return top.key, None
    return None, {
        "error": (
            f"Team name '{query}' is ambiguous. Re-run with a more specific "
            "name or one of the team_key values below."
        ),
        "candidates": [
            {
                "team_key": c.key,
                "display_name": c.display,
                "matches": c.match_count,
                "known_variants": sorted(c.raw_variants)[:6],
            }
            for c in candidates[:8]
        ],
    }


def _season_arg(raw) -> int | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    if text[-1] in "sS" and text[:-1].isdigit():
        return int(text[:-1])
    return int(text) if text.isdigit() else None


def _stage_matches(match, stage: str) -> bool:
    label = (match.stage or match.round or "").strip().lower()
    if not label:
        return False
    target = stage.strip().lower()
    target_singular = target.rstrip("s")
    label_singular = label.rstrip("s")
    return target in (label, label_singular) or target_singular in (label, label_singular)


def _match_line(match) -> str:
    when = match.date.isoformat() if match.date else "date unknown"
    label = match.round or match.stage or ""
    suffix = f" ({label})" if label else ""
    home = team_display_name(match.home_key)
    away = team_display_name(match.away_key)
    return f"{when}: {home} {match.score} {away} - {match.competition}{suffix}"


def _finals_payload(matches: list) -> dict:
    by_season: dict[int, list] = {}
    for match in matches:
        by_season.setdefault(match.season or 0, []).append(match)
    editions = []
    for season in sorted(by_season, reverse=True):
        legs = sorted(by_season[season], key=lambda m: m.date or date.min)
        if not any(leg.score for leg in legs):
            continue
        legs = [leg for leg in legs if leg.score] or legs
        if len(legs) == 1:
            leg = legs[0]
            winner_key = leg.winner_key()
            detail = (
                f"{team_display_name(leg.home_key)} {leg.score} {team_display_name(leg.away_key)}"
            )
        else:
            first, second = legs[0], legs[-1]
            a, b = first.home_key, first.away_key
            goals_a = (first.home_goals or 0) + (second.away_goals or 0)
            goals_b = (first.away_goals or 0) + (second.home_goals or 0)
            winner_key = a if goals_a > goals_b else (b if goals_b > goals_a else None)
            detail = (
                f"2 legs, aggregate {team_display_name(a)} {goals_a}-{goals_b} "
                f"{team_display_name(b)}"
                + ("" if winner_key else " (level on aggregate; decided on penalties, not in data)")
            )
        editions.append(
            {
                "season": season or None,
                "winner": (
                    team_display_name(winner_key)
                    if winner_key
                    else "unknown / drawn on aggregate"
                ),
                "detail": detail,
                "legs": [m.to_dict() for m in legs],
            }
        )
    return {"editions": editions}


app = MCPServer(
    name="brazilian-soccer",
    title="Brazilian Soccer Knowledge Server",
    instructions=(
        "Answers natural-language questions about Brazilian soccer using "
        "bundled Kaggle datasets: Brasileirao Serie A (2003-2023), Serie B/C "
        "(2014-2023), Copa do Brasil (2012-2023), Copa Libertadores "
        "(2013-2022) and a FIFA player database. Team names are matched "
        "leniently across naming conventions ('Palmeiras-SP', 'Palmeiras', "
        "'SE Palmeiras' are the same club). Player data is FIFA-based and "
        "does NOT include every Brazilian club (Flamengo, Palmeiras, "
        "Corinthians, Sao Paulo and Vasco are absent from the FIFA dataset "
        "for licensing reasons)."
    ),
)


@app.tool()
def get_dataset_overview() -> dict:
    """Summarize what data is available: competitions, seasons, matches, players."""
    data = get_data()
    overview = data.dataset_overview()
    summary_lines = ["Brazilian soccer dataset overview:"]
    for competition, info in overview["competitions"].items():
        seasons = info["seasons"]
        season_span = f"{seasons[0]}-{seasons[-1]}" if seasons else "n/a"
        summary_lines.append(
            f"- {competition}: {info['matches']} matches, seasons {season_span}"
        )
    summary_lines.append(
        f"- FIFA player database: {overview['total_players']} players, "
        f"{overview['total_teams']} teams known overall"
    )
    return {"summary": "\n".join(summary_lines), "data": overview}


@app.tool()
def resolve_team(query: str) -> dict:
    """Resolve a free-text team name to its canonical key, variants and stats.

    Use this when a team name might be ambiguous (e.g. 'Atletico', 'America')
    before calling match/team tools, or to discover how a club is spelled
    across the source files.
    """
    data = get_data()
    key, error = _resolve_team_arg(query, data)
    if error:
        return error
    entry = data.teams[key]
    return {
        "summary": (
            f"'{query}' resolves to {entry.display} (team_key: {key}); "
            f"{entry.match_count} matches and {entry.player_count} players "
            "in dataset."
        ),
        "data": entry.to_dict(),
    }


@app.tool()
def list_teams(
    competition: str | None = None,
    season: int | None = None,
    search: str | None = None,
) -> dict:
    """List teams in the dataset, optionally filtered by competition, season
    or a name substring."""
    data = get_data()
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    season_val = _season_arg(season)
    entries = list(data.teams.values())
    if comp or season_val is not None:
        matches = data.matches_by_competition(comp, season_val)
        keys = {m.home_key for m in matches} | {m.away_key for m in matches}
        entries = [e for e in entries if e.key in keys]
    if search:
        needle = search.lower()
        entries = [
            e
            for e in entries
            if needle in e.key
            or needle in e.display.lower()
            or any(needle in v.lower() for v in e.raw_variants)
        ]
    entries.sort(key=lambda e: (-e.match_count, e.key))
    return {
        "summary": f"{len(entries)} teams match the filters.",
        "data": {
            "count": len(entries),
            "teams": [e.to_dict() for e in entries[:60]],
        },
    }


@app.tool()
def search_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    limit: int = 25,
) -> dict:
    """Search matches by team, opponent, competition, season, date range
    (YYYY-MM-DD or DD/MM/YYYY) and stage (e.g. 'final', 'semifinal',
    'group stage'). Returns most recent matches first."""
    data = get_data()
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    season_val = _season_arg(season)
    team_key = None
    if team:
        team_key, error = _resolve_team_arg(team, data)
        if error:
            return error
    opponent_key = None
    if opponent:
        opponent_key, error = _resolve_team_arg(opponent, data)
        if error:
            return error
    limit = max(1, min(int(limit), 100))

    pool = data.matches_for_team(team_key) if team_key else list(data.matches)
    date_min = parse_date(date_from)
    date_max = parse_date(date_to)
    results = []
    for match in pool:
        if comp and match.competition != comp:
            continue
        if season_val is not None and match.season != season_val:
            continue
        if opponent_key and not match.involves(opponent_key):
            continue
        if date_min and (match.date is None or match.date < date_min):
            continue
        if date_max and (match.date is None or match.date > date_max):
            continue
        if stage and not _stage_matches(match, stage):
            continue
        results.append(match)
    results.sort(key=lambda m: (m.date or date.min), reverse=True)

    lines = []
    if team_key and opponent_key:
        name_a = team_display_name(team_key)
        name_b = team_display_name(opponent_key)
        h2h = head_to_head(results, team_key, opponent_key)
        lines.append(f"{name_a} vs {name_b}:")
        for match in results[:limit]:
            lines.append(f"- {_match_line(match)}")
        if len(results) > limit:
            lines.append(f"... ({len(results) - limit} more matches in dataset)")
        lines.append(
            f"Head-to-head in selection: {name_a} {h2h['team_a_wins']} wins, "
            f"{name_b} {h2h['team_b_wins']} wins, {h2h['draws']} draws"
        )
    elif results:
        lines.append(f"{len(results)} matches found (showing up to {limit}):")
        for match in results[:limit]:
            lines.append(f"- {_match_line(match)}")
    else:
        lines.append("No matches found for the given filters.")

    return {
        "summary": "\n".join(lines),
        "data": {
            "total_matches": len(results),
            "matches": [m.to_dict() for m in results[:limit]],
        },
    }


@app.tool()
def get_head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Compare two teams head-to-head: wins/draws/losses, goals and all
    meetings (most recent first)."""
    data = get_data()
    key_a, error = _resolve_team_arg(team_a, data)
    if error:
        return error
    key_b, error = _resolve_team_arg(team_b, data)
    if error:
        return error
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    season_val = _season_arg(season)
    pool = data.matches_by_competition(comp, season_val)
    record = head_to_head(pool, key_a, key_b)
    if record["total_meetings"] == 0:
        return {
            "summary": (
                f"No matches between {team_display_name(key_a)} and "
                f"{team_display_name(key_b)} were found in the dataset"
                + (f" for the requested filters ({comp or 'all competitions'})."
                   if comp or season_val else ".")
            ),
            "data": {"total_meetings": 0, "matches": []},
        }
    name_a = team_display_name(key_a)
    name_b = team_display_name(key_b)
    lines = [
        f"{name_a} vs {name_b} (head-to-head in dataset):",
        f"- Meetings: {record['total_meetings']}",
        f"- {name_a} wins: {record['team_a_wins']}",
        f"- {name_b} wins: {record['team_b_wins']}",
        f"- Draws: {record['draws']}",
        f"- Goals: {name_a} {record['team_a_goals']} - {record['team_b_goals']} {name_b}",
    ]
    recent = sorted(record["matches"], key=lambda m: m.date or date.min, reverse=True)
    lines.append("Most recent meetings:")
    for match in recent[:10]:
        lines.append(f"- {_match_line(match)}")
    return {
        "summary": "\n".join(lines),
        "data": {
            "team_a": name_a,
            "team_b": name_b,
            "team_a_wins": record["team_a_wins"],
            "team_b_wins": record["team_b_wins"],
            "draws": record["draws"],
            "team_a_goals": record["team_a_goals"],
            "team_b_goals": record["team_b_goals"],
            "total_meetings": record["total_meetings"],
            "matches": [m.to_dict() for m in recent],
        },
    }


@app.tool()
def get_team_stats(
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str | None = None,
) -> dict:
    """Win/draw/loss record, goals and points for one team, optionally
    filtered by competition, season and venue ('home' or 'away')."""
    data = get_data()
    key, error = _resolve_team_arg(team, data)
    if error:
        return error
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    season_val = _season_arg(season)
    matches = data.matches_by_competition(comp, season_val)
    if venue and venue.strip().lower() in {"home", "away"}:
        wanted = venue.strip().lower()
        matches = [
            m
            for m in matches
            if (wanted == "home" and m.home_key == key)
            or (wanted == "away" and m.away_key == key)
        ]
    record = team_record(matches, key)
    display = team_display_name(key)
    if record.matches == 0:
        return {
            "summary": f"No matches found for {display} with the given filters.",
            "data": {"team": display, "matches": 0},
        }
    scope = " / ".join(
        str(part)
        for part in [comp, season_val, (venue or "").strip().lower() or None]
        if part
    ) or "all competitions"
    home = record.merge_line("home")
    away = record.merge_line("away")
    lines = [
        f"{display} record ({scope}):",
        f"- Matches: {record.matches}",
        f"- Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}",
        f"- Goals For: {record.goals_for}, Goals Against: {record.goals_against}",
        f"- Win rate: {record.win_rate}%",
        f"- Home: {home['matches']} matches ({home['wins']}W {home['draws']}D {home['losses']}L)",
        f"- Away: {away['matches']} matches ({away['wins']}W {away['draws']}D {away['losses']}L)",
    ]
    return {"summary": "\n".join(lines), "data": {"team": display, **record.to_dict()}}


@app.tool()
def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    max_age: int | None = None,
    limit: int = 25,
    sort: str = "overall",
) -> dict:
    """Search the FIFA player database by name, nationality, club, position
    (FIFA code like 'ST'/'LW'/'GK' or group: forward/midfielder/defender/
    goalkeeper), minimum overall rating and maximum age. Sorted by overall
    by default; also 'potential' or 'age'."""
    data = get_data()
    limit = max(1, min(int(limit), 100))
    players = list(data.players)
    if name:
        players = data.search_players_by_name(name)
    if nationality:
        needle = nationality.strip().lower()
        players = [p for p in players if needle in p.nationality.lower()]
    if club:
        key, error = _resolve_team_arg(club, data)
        if error:
            needle = club.strip().lower()
            players = [p for p in players if needle in p.club.lower()]
        else:
            players = [p for p in players if p.club_key == key]
    if position:
        raw = position.strip()
        if raw.upper() in POSITION_GROUPS:
            allowed = set(POSITION_GROUPS[raw.upper()])
        elif raw.upper() in {"GK", "CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB",
                             "CDM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM",
                             "LAM", "RAM", "LM", "RM", "ST", "LS", "RS", "CF",
                             "LF", "RF", "LW", "RW"}:
            allowed = {raw.upper()}
        else:
            allowed = set(POSITION_GROUPS.get(raw.lower().rstrip("s"), []))
        players = [p for p in players if p.position in allowed]
    if min_overall is not None:
        players = [p for p in players if (p.overall or 0) >= int(min_overall)]
    if max_age is not None:
        players = [p for p in players if p.age is not None and p.age <= int(max_age)]

    sort_key = (sort or "overall").strip().lower()
    if sort_key == "potential":
        players.sort(key=lambda p: (-(p.potential or 0), p.name))
    elif sort_key == "age":
        players.sort(key=lambda p: (p.age or 999, p.name))
    elif sort_key == "name":
        players.sort(key=lambda p: p.name)
    else:
        players.sort(key=lambda p: (-(p.overall or 0), p.name))

    if not players:
        return {
            "summary": "No players found for the given filters. Note the FIFA "
            "dataset does not include Flamengo, Palmeiras, Corinthians, "
            "Sao Paulo or Vasco players (licensing).",
            "data": {"count": 0, "players": []},
        }
    lines = [f"{len(players)} players match (showing up to {limit}):"]
    for player in players[:limit]:
        lines.append(
            f"- {player.name} - Overall: {player.overall}, "
            f"Position: {player.position}, Club: {player.club}, "
            f"Age: {player.age}, Nationality: {player.nationality}"
        )
    return {
        "summary": "\n".join(lines),
        "data": {
            "count": len(players),
            "players": [p.to_dict() for p in players[:limit]],
        },
    }


@app.tool()
def get_player_details(name: str) -> dict:
    """Full profile for a player (FIFA ratings, attributes, contract info)."""
    data = get_data()
    matches = data.search_players_by_name(name)
    if not matches:
        return {"error": f"No player matching '{name}' found in the FIFA dataset."}
    best = sorted(matches, key=lambda p: -(p.overall or 0))[:3]
    lines = []
    for player in best:
        lines.append(
            f"{player.name} ({player.nationality}, {player.position}) - "
            f"Overall {player.overall}, Potential {player.potential}, "
            f"Age {player.age}, Club {player.club}, "
            f"Jersey #{player.jersey_number}"
        )
    return {
        "summary": "\n".join(lines),
        "data": {
            "matches_found": len(matches),
            "players": [p.to_dict(include_skills=True) for p in best],
        },
    }


@app.tool()
def get_club_players(
    club: str,
    nationality: str | None = None,
    position: str | None = None,
) -> dict:
    """List the squad of a club from the FIFA database, with average rating,
    plus the club's recent match results (cross-file player + match data)."""
    data = get_data()
    key, error = _resolve_team_arg(club, data)
    if error:
        return error
    players = data.players_at_club(key)
    if nationality:
        needle = nationality.strip().lower()
        players = [p for p in players if needle in p.nationality.lower()]
    if position:
        raw = position.strip()
        allowed = set(
            POSITION_GROUPS.get(raw.upper(), POSITION_GROUPS.get(raw.lower().rstrip("s"), []))
        )
        if not allowed and raw.upper():
            allowed = {raw.upper()}
        players = [p for p in players if p.position in allowed]
    players.sort(key=lambda p: (-(p.overall or 0), p.name))
    display = team_display_name(key)
    lines = []
    if players:
        ratings = [p.overall for p in players if p.overall is not None]
        avg = round(sum(ratings) / len(ratings), 1) if ratings else None
        lines.append(
            f"{display} squad in FIFA dataset: {len(players)} players "
            f"(average rating: {avg})"
        )
        for player in players[:15]:
            lines.append(
                f"- {player.name} - Overall: {player.overall}, "
                f"Position: {player.position}, Nationality: {player.nationality}"
            )
        brazilians = [p for p in players if p.nationality.lower() == "brazil"]
        if brazilians:
            brz_avg = round(
                sum(p.overall for p in brazilians if p.overall) / len(brazilians), 1
            )
            lines.append(
                f"Brazilian players at club: {len(brazilians)} (avg rating: {brz_avg})"
            )
    else:
        lines.append(
            f"No {display} players in the FIFA dataset. Note it excludes "
            "Flamengo, Palmeiras, Corinthians, Sao Paulo and Vasco."
        )
    team_matches = sorted(
        data.matches_for_team(key), key=lambda m: m.date or date.min, reverse=True
    )
    record = team_record(data.matches_for_team(key), key)
    lines.append(
        f"Match data: {record.matches} matches in dataset "
        f"({record.wins}W {record.draws}D {record.losses}L)."
    )
    if team_matches:
        lines.append("Most recent matches:")
        for match in team_matches[:5]:
            lines.append(f"- {_match_line(match)}")
    return {
        "summary": "\n".join(lines),
        "data": {
            "club": display,
            "team_key": key,
            "squad": [p.to_dict() for p in players[:30]],
            "squad_size": len(players),
            "match_record": record.to_dict(),
            "recent_matches": [m.to_dict() for m in team_matches[:5]],
        },
    }


@app.tool()
def get_standings(competition: str = "Brasileirão Série A", season: int = 2023) -> dict:
    """League table computed from match results, with champion, runner-up
    and relegated teams."""
    data = get_data()
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    season_val = _season_arg(season)
    if season_val is None:
        return {"error": "A valid season year is required, e.g. 2019."}
    matches = data.matches_by_competition(comp, season_val)
    if not matches:
        return {
            "error": f"No matches found for {comp} {season_val}.",
            "available_seasons": data.seasons_for_competition(comp),
        }
    table = standings(matches)
    highlights = champion_and_relegated(table)
    scored = [m for m in matches if m.score is not None]
    expected = LEAGUE_FULL_SEASON.get(comp)
    partial = expected is not None and len(scored) < expected
    lines = [f"{comp} {season_val} standings (calculated from {len(scored)} matches):"]
    for row in table:
        marker = ""
        if row["position"] == 1:
            marker = " - Champion"
        elif row["team"] in highlights["relegated"]:
            marker = " - Relegated"
        lines.append(
            f"{row['position']}. {row['team']} - {row['points']} pts "
            f"({row['wins']}W, {row['draws']}D, {row['losses']}L){marker}"
        )
    if partial:
        lines.append(
            f"Note: data for this season is partial "
            f"({len(scored)} of {expected} matches)."
        )
    return {
        "summary": "\n".join(lines),
        "data": {
            "competition": comp,
            "season": season_val,
            "matches_played": len(scored),
            "partial_data": partial,
            "champion": highlights["champion"],
            "runner_up": highlights["runner_up"],
            "relegated": highlights["relegated"],
            "table": table,
        },
    }


@app.tool()
def get_competition_info(competition: str) -> dict:
    """Seasons, match counts and final results for a competition."""
    data = get_data()
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    matches = data.matches_by_competition(comp)
    seasons = data.seasons_for_competition(comp)
    per_season = []
    for season in seasons:
        season_matches = data.matches_by_competition(comp, season)
        per_season.append(
            {
                "season": season,
                "matches": len(season_matches),
                "scored": sum(1 for m in season_matches if m.score is not None),
            }
        )
    finals_payload = _finals_payload(finals(matches))
    lines = [
        f"{comp}: {len(matches)} matches across {len(seasons)} seasons "
        f"({seasons[0]}-{seasons[-1] if seasons else ''})."
    ]
    if comp == LIBERTADORES or comp == COPA_DO_BRASIL:
        lines.append("Finals in dataset:")
        for edition in finals_payload["editions"][:12]:
            lines.append(f"- {edition['season']}: won by {edition['winner']} ({edition['detail']})")
    else:
        lines.append(
            "League format: standings are computed from match results; "
            "use get_standings for a specific season."
        )
    lines.append(
        "Top scorers are not derivable: the datasets have no goal-scorer events."
    )
    return {
        "summary": "\n".join(lines),
        "data": {
            "competition": comp,
            "total_matches": len(matches),
            "seasons": seasons,
            "per_season": per_season,
            "finals": finals_payload["editions"],
        },
    }


@app.tool()
def get_competition_finals(competition: str = "Copa do Brasil") -> dict:
    """All final-round matches for a cup competition, with two-leg
    aggregates and winners per edition."""
    data = get_data()
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    payload = _finals_payload(finals(data.matches_by_competition(comp)))
    lines = [f"{comp} finals in dataset:"]
    for edition in payload["editions"]:
        lines.append(f"- {edition['season']}: won by {edition['winner']} ({edition['detail']})")
    return {"summary": "\n".join(lines), "data": payload}


@app.tool()
def get_aggregate_statistics(
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Average goals per match plus home/draw/away win rates, optionally
    for one competition and season."""
    data = get_data()
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    season_val = _season_arg(season)
    matches = data.matches_by_competition(comp, season_val)
    agg = competition_aggregates(matches)
    scope = " / ".join(str(p) for p in [comp, season_val] if p) or "the whole dataset"
    lines = [f"Aggregate statistics for {scope}:"]
    if agg["matches"]:
        lines.append(f"- Matches: {agg['matches']}")
        lines.append(f"- Average goals per match: {agg['avg_goals_per_match']}")
        lines.append(f"- Home win rate: {agg['home_win_rate_pct']}%")
        lines.append(f"- Draw rate: {agg['draw_rate_pct']}%")
        lines.append(f"- Away win rate: {agg['away_win_rate_pct']}%")
    else:
        lines.append("No matches found for the given filters.")
    per_season = []
    if comp and season_val is None:
        for season in data.seasons_for_competition(comp):
            per_season.append(
                {
                    "season": season,
                    **competition_aggregates(data.matches_by_competition(comp, season)),
                }
            )
        if per_season:
            lines.append("Per season (avg goals): " + ", ".join(
                f"{row['season']}: {row['avg_goals_per_match']}" for row in per_season
            ))
    return {"summary": "\n".join(lines), "data": {"scope": scope, **agg, "per_season": per_season}}


@app.tool()
def get_biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    team: str | None = None,
    limit: int = 10,
) -> dict:
    """Matches with the largest goal margins, optionally filtered."""
    data = get_data()
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    season_val = _season_arg(season)
    team_key = None
    if team:
        team_key, error = _resolve_team_arg(team, data)
        if error:
            return error
    limit = max(1, min(int(limit), 50))
    matches = data.matches_by_competition(comp, season_val)
    if team_key:
        matches = [m for m in matches if m.involves(team_key)]
    wins = biggest_wins(matches, limit)
    lines = ["Biggest victories (by goal margin):"]
    for i, win in enumerate(wins, 1):
        lines.append(
            f"{i}. {win['date']}: {win['home_team']} {win['score']} "
            f"{win['away_team']} ({win['competition']}, margin {win['margin']})"
        )
    return {"summary": "\n".join(lines), "data": {"wins": wins}}


@app.tool()
def get_best_records(
    competition: str | None = None,
    season: int | None = None,
    metric: str = "points",
    venue: str = "all",
    limit: int = 10,
) -> dict:
    """Rank teams by 'points', 'win_rate' or 'goals' over a set of matches,
    with venue filter ('home', 'away' or 'all')."""
    data = get_data()
    comp, error = _resolve_competition_arg(competition)
    if error:
        return error
    season_val = _season_arg(season)
    matches = data.matches_by_competition(comp, season_val)
    venue_norm = (venue or "all").strip().lower()
    records = best_records(matches, metric=metric, limit=limit, venue=venue_norm)
    metric_norm = (metric or "points").strip().lower()
    label = {
        "points": "points",
        "win_rate": "win rate",
        "win rate": "win rate",
        "goals": "goals scored",
    }.get(metric_norm, metric_norm)
    scope_parts = [comp, season_val, venue_norm if venue_norm != "all" else None]
    scope = " / ".join(str(p) for p in scope_parts if p) or "all competitions"
    lines = [f"Teams ranked by {label} ({scope}):"]
    record_line = {
        "goals": lambda r: f"{r['goals_for']} goals in {r['matches']} matches",
        "win_rate": lambda r: (
            f"{r['win_rate_pct']}% ({r['wins']}W {r['draws']}D "
            f"{r['losses']}L in {r['matches']})"
        ),
    }
    for i, row in enumerate(records, 1):
        if metric_norm in {"goals", "goals scored"}:
            detail = record_line["goals"](row)
        elif metric_norm in {"win_rate", "win rate"}:
            detail = record_line["win_rate"](row)
        else:
            detail = (
                f"{row['points']} pts ({row['wins']}W {row['draws']}D "
                f"{row['losses']}L in {row['matches']})"
            )
        lines.append(f"{i}. {row['team']} - {detail}")
    return {"summary": "\n".join(lines), "data": {"ranking": records}}


@app.tool()
def get_derby_matches(
    derby: str | None = None,
    team: str | None = None,
    season: int | None = None,
) -> dict:
    """Matches between classic Brazilian rivals (Fla-Flu, Gre-Nal, Derby
    Paulista, Ba-Vi, Clássico Mineiro, ...). Filter by derby name, team or
    season."""
    data = get_data()
    season_val = _season_arg(season)
    matches = data.matches_by_competition(None, season_val)
    all_derbies = derby_matches(matches, season=season_val)
    if derby:
        needle = derby.strip().lower()
        all_derbies = [d for d in all_derbies if needle in d["derby"].lower()]
    team_key = None
    if team:
        team_key, error = _resolve_team_arg(team, data)
        if error:
            return error
    if team_key:
        pairings = {
            name: frozenset((a, b)) for a, b, name in DERBY_PAIRS
        }
        all_derbies = [
            d for d in all_derbies if team_key in pairings[d["derby"]]
        ]
    lines = [f"{len(all_derbies)} derby matches found (showing up to 20):"]
    for d in all_derbies[-20:]:
        lines.append(
            f"- {d['date']}: {d['derby']} - {d['home_team']} {d['score']} "
            f"{d['away_team']} ({d['competition']} {d['season']})"
        )
    return {
        "summary": "\n".join(lines),
        "data": {
            "derbies_known": [name for _, _, name in DERBY_PAIRS],
            "count": len(all_derbies),
            "matches": all_derbies[-50:],
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Brazilian Soccer MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
    )
    parser.add_argument("--port", type=int, default=8321)
    args = parser.parse_args(argv)
    if args.transport == "stdio":
        app.run()
    else:
        app.run(transport="streamable-http", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
