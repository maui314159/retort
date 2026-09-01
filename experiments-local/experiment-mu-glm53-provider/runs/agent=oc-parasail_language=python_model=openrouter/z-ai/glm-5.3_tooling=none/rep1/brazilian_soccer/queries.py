"""Query layer: turns repository data into answers for MCP tools.

Context: every capability required by TASK.md is implemented here as a
plain function over the DataRepository, returning JSON-serialisable dicts:
match search (team/date/competition/season criteria), team records,
head-to-head comparisons, standings calculated from match results, player
search/detail, rankings, aggregated statistics, biggest wins and derbies.
The tool layer (tools.py) wraps these functions with JSON schemas; errors
raise QueryError, which becomes a tool-level error response.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .models import LIBERTADORES_STAGE_ORDER, Match, Player
from .normalize import clean_text, is_nothing, parse_date, parse_int
from .repository import COPA_DO_BRASIL, LIBERTADORES, SERIE_A, DataRepository

DEFAULT_MATCH_LIMIT = 25
MAX_MATCH_LIMIT = 200
DEFAULT_PLAYER_LIMIT = 25
MAX_PLAYER_LIMIT = 200

DERBIES = (
    ("Flamengo", "Fluminense", "Fla-Flu"),
    ("Flamengo", "Vasco", "Clássico dos Milhões"),
    ("Corinthians", "São Paulo", "Majestoso"),
    ("Palmeiras", "São Paulo", "Choque-Rei"),
    ("Palmeiras", "Corinthians", "Derby Paulista"),
    ("Santos", "Corinthians", "Clássico Alvinegro"),
    ("Grêmio", "Internacional", "Grenal"),
    ("Atlético-MG", "Cruzeiro", "Clássico Mineiro"),
    ("Botafogo", "Fluminense", "Clássico Vovô"),
    ("Bahia", "Vitória", "Ba-Vi"),
    ("Ceará", "Fortaleza", "Clássico-Rei"),
    ("Athletico-PR", "Coritiba", "Atletiba"),
    ("Sport", "Náutico", "Clássico dos Clássicos"),
    ("Avaí", "Figueirense", "Clássico de Florianópolis"),
    ("Ponte Preta", "Guarani", "Dérbi Campineiro"),
)

POSITION_SYNONYMS = {
    "goalkeeper": "goalkeeper", "gk": "goalkeeper", "keeper": "goalkeeper",
    "defender": "defender", "defense": "defender", "def": "defender",
    "midfielder": "midfielder", "midfield": "midfielder", "mid": "midfielder",
    "forward": "forward", "fwd": "forward", "attacker": "forward",
    "striker": "forward", "att": "forward",
}


class QueryError(ValueError):
    """User-facing query error (bad filters, ambiguous team names...)."""


# ----------------------------------------------------------------- helpers

def _norm_key(value: str | None) -> str:
    """Normalise an enum-style parameter (metric, sort) to snake_case."""
    if not value:
        return ""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _resolve_one(repo: DataRepository, name: str | None, label: str = "team"):
    entities = repo.resolve_team(name)
    if not entities:
        raise QueryError(
            f"No team found for '{name}'. Use the find_team tool to list "
            "matching teams and their spellings."
        )
    if len(entities) > 1:
        options = ", ".join(entity.display for entity in entities)
        raise QueryError(
            f"'{name}' is ambiguous; it can mean {len(entities)} teams: {options}. "
            "Include the state suffix (e.g. 'America-MG') to pick one."
        )
    return entities[0]


def _resolve_multi(repo: DataRepository, name: str | None):
    entities = repo.resolve_team(name)
    if not entities:
        raise QueryError(f"No team found for '{name}'. Try the find_team tool.")
    return entities


def _parse_season(season) -> int:
    value = parse_int(season)
    if value is None:
        raise QueryError(f"Invalid season: {season!r}")
    return value


def _parse_date_bound(value: str, label: str) -> date:
    parsed, _ = parse_date(value)
    if parsed is None:
        raise QueryError(f"Invalid {label} date: {value!r} (use YYYY-MM-DD)")
    return parsed


def _canonical_competition(repo: DataRepository, competition: str | None) -> str | None:
    if competition is None or is_nothing(competition):
        return None
    canonical = repo.canonical_competition(competition)
    if canonical is None:
        valid = ", ".join(repo.list_competitions())
        raise QueryError(f"Unknown competition: {competition!r}. Valid: {valid}")
    return canonical


def _stage_matches(repo: DataRepository, match: Match, stage: str) -> bool:
    wanted = clean_text(stage)
    if wanted == "final":
        if match.competition == LIBERTADORES:
            return match.stage == "final"
        if match.competition == COPA_DO_BRASIL:
            return match.round is not None and match.round == repo.final_rounds.get(match.season)
        return False
    if match.stage is None:
        return False
    return clean_text(match.stage) == wanted


def _source_pool(repo: DataRepository, source: str | None):
    if source is None or is_nothing(source):
        return repo.matches, None
    filename = source.strip()
    if not filename.endswith(".csv"):
        filename += ".csv"
    pool = [match for match in repo.raw_matches if match.source == filename]
    if not pool:
        raise QueryError(
            f"No matches found from source '{filename}'. Available sources: "
            + ", ".join(sorted({match.source for match in repo.raw_matches}))
        )
    return pool, filename


def _apply_filters(
    repo: DataRepository,
    matches: list[Match],
    *,
    competition: str | None = None,
    season=None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    round_no=None,
) -> list[Match]:
    canonical = _canonical_competition(repo, competition)
    season_value = _parse_season(season) if season is not None and not is_nothing(season) else None
    lower = _parse_date_bound(date_from, "from") if date_from else None
    upper = _parse_date_bound(date_to, "to") if date_to else None
    round_value = parse_int(round_no) if round_no is not None and not is_nothing(round_no) else None
    want_stage = clean_text(stage) if stage and not is_nothing(stage) else None
    result = []
    for match in matches:
        if canonical and match.competition != canonical:
            continue
        if season_value and match.season != season_value:
            continue
        if lower and match.date < lower:
            continue
        if upper and match.date > upper:
            continue
        if want_stage and not _stage_matches(repo, match, want_stage):
            continue
        if round_value is not None and match.round != round_value:
            continue
        result.append(match)
    return result


# ------------------------------------------------------------------ matches

def search_matches(
    repo: DataRepository,
    *,
    team: str | None = None,
    opponent: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    competition: str | None = None,
    season=None,
    date_from: str | None = None,
    date_to: str | None = None,
    stage: str | None = None,
    round=None,
    venue: str | None = None,
    source: str | None = None,
    limit: int = DEFAULT_MATCH_LIMIT,
    sort: str = "date_desc",
) -> dict:
    """Search matches by team, date range, competition, season, stage or source."""
    pool, source_name = _source_pool(repo, source)
    notes: list[str] = []

    team_keys: set[str] = set()
    if team and not is_nothing(team):
        entities = _resolve_multi(repo, team)
        team_keys = {entity.key for entity in entities}
        if len(entities) > 1:
            names = ", ".join(entity.display for entity in entities)
            notes.append(f"'{team}' matched multiple teams: {names}")
    opponent_keys: set[str] = set()
    if opponent and not is_nothing(opponent):
        entities = _resolve_multi(repo, opponent)
        opponent_keys = {entity.key for entity in entities}
        if len(entities) > 1:
            names = ", ".join(entity.display for entity in entities)
            notes.append(f"'{opponent}' matched multiple teams: {names}")
    home_keys: set[str] = set()
    if home_team and not is_nothing(home_team):
        home_keys = {entity.key for entity in _resolve_multi(repo, home_team)}
    away_keys: set[str] = set()
    if away_team and not is_nothing(away_team):
        away_keys = {entity.key for entity in _resolve_multi(repo, away_team)}
    if venue and clean_text(venue) not in ("home", "away"):
        raise QueryError("venue must be 'home' or 'away'")

    filtered = _apply_filters(
        repo,
        pool,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        stage=stage,
        round_no=round,
    )

    selected: list[Match] = []
    for match in filtered:
        if team_keys:
            home_side = match.home_team in team_keys
            away_side = match.away_team in team_keys
            if venue == "home":
                if not home_side:
                    continue
            elif venue == "away":
                if not away_side:
                    continue
            elif not (home_side or away_side):
                continue
            if opponent_keys:
                if not (
                    (home_side and match.away_team in opponent_keys)
                    or (away_side and match.home_team in opponent_keys)
                ):
                    continue
        else:
            if opponent_keys:
                if not (
                    match.home_team in opponent_keys or match.away_team in opponent_keys
                ):
                    continue
        if home_keys and match.home_team not in home_keys:
            continue
        if away_keys and match.away_team not in away_keys:
            continue
        selected.append(match)

    reverse = _norm_key(sort) != "date_asc"
    selected.sort(key=lambda match: match.sort_key, reverse=reverse)
    total = len(selected)
    limit_value = max(1, min(parse_int(limit) or DEFAULT_MATCH_LIMIT, MAX_MATCH_LIMIT))
    page = selected[:limit_value]
    payload = {
        "total_matches": total,
        "returned": len(page),
        "matches": [match.to_dict() for match in page],
    }
    if source_name:
        payload["source"] = source_name
        payload["note"] = (
            "Results come from the raw source file and may contain duplicates "
            "shadowed in the curated dataset."
        )
    if notes:
        payload["notes"] = notes
    if total > len(page):
        payload["truncated"] = True
    return payload


def head_to_head(
    repo: DataRepository,
    team_a: str,
    team_b: str,
    *,
    competition: str | None = None,
    season=None,
    limit: int = DEFAULT_MATCH_LIMIT,
) -> dict:
    """Compare two teams head-to-head: results, goals and match list."""
    entity_a = _resolve_one(repo, team_a, "team_a")
    entity_b = _resolve_one(repo, team_b, "team_b")
    if entity_a.key == entity_b.key:
        raise QueryError("Please provide two different teams.")
    pool = _apply_filters(repo, repo.matches, competition=competition, season=season)
    pair = {entity_a.key, entity_b.key}
    meetings = [
        match
        for match in pool
        if match.home_team in pair and match.away_team in pair
    ]
    meetings.sort(key=lambda match: match.sort_key, reverse=True)
    wins_a = wins_b = draws = goals_a = goals_b = 0
    for match in meetings:
        goals_home, goals_away = match.home_goals, match.away_goals
        a_home = match.home_team == entity_a.key
        a_goals, b_goals = (goals_home, goals_away) if a_home else (goals_away, goals_home)
        goals_a += a_goals
        goals_b += b_goals
        if a_goals > b_goals:
            wins_a += 1
        elif b_goals > a_goals:
            wins_b += 1
        else:
            draws += 1
    limit_value = max(1, min(parse_int(limit) or DEFAULT_MATCH_LIMIT, MAX_MATCH_LIMIT))
    payload = {
        "team_a": entity_a.display,
        "team_b": entity_b.display,
        "matches_played": len(meetings),
        "team_a_wins": wins_a,
        "team_b_wins": wins_b,
        "draws": draws,
        "team_a_goals": goals_a,
        "team_b_goals": goals_b,
        "most_recent": meetings[0].to_dict() if meetings else None,
        "first_meeting": meetings[-1].to_dict() if meetings else None,
        "matches": [match.to_dict() for match in meetings[:limit_value]],
    }
    if len(meetings) > limit_value:
        payload["truncated"] = True
    if not meetings:
        payload["note"] = "These teams never met in the curated dataset."
    return payload


# --------------------------------------------------------------------- teams

def _record_matches(matches: list[Match], key: str) -> list[Match]:
    return [match for match in matches if key in (match.home_team, match.away_team)]


def _summarise_record(matches: list[Match], key: str) -> dict:
    wins = draws = losses = goals_for = goals_against = 0
    for match in matches:
        home = match.home_team == key
        scored, conceded = (
            (match.home_goals, match.away_goals) if home else (match.away_goals, match.home_goals)
        )
        goals_for += scored
        goals_against += conceded
        if scored > conceded:
            wins += 1
        elif scored < conceded:
            losses += 1
        else:
            draws += 1
    played = len(matches)
    return {
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "points": 3 * wins + draws,
        "win_rate": round(wins / played, 3) if played else None,
    }


def team_stats(
    repo: DataRepository,
    team: str,
    *,
    season=None,
    competition: str | None = None,
    limit_recent: int = 5,
) -> dict:
    """Win/loss/draw record, goals and per-competition splits for one team."""
    entity = _resolve_one(repo, team)
    pool = _apply_filters(repo, repo.matches, competition=competition, season=season)
    matches = _record_matches(pool, entity.key)
    home_matches = [m for m in matches if m.home_team == entity.key]
    away_matches = [m for m in matches if m.away_team == entity.key]
    by_competition: dict[str, list[Match]] = defaultdict(list)
    for match in matches:
        by_competition[match.competition].append(match)
    recent = sorted(matches, key=lambda m: m.sort_key, reverse=True)
    payload = {
        "team": entity.display,
        "filters": {
            "season": _parse_season(season) if season is not None and not is_nothing(season) else None,
            "competition": _canonical_competition(repo, competition),
        },
        "overall": _summarise_record(matches, entity.key),
        "home": _summarise_record(home_matches, entity.key),
        "away": _summarise_record(away_matches, entity.key),
        "by_competition": [
            {"competition": name, **_summarise_record(rows, entity.key)}
            for name, rows in sorted(by_competition.items())
        ],
        "recent_matches": [match.to_dict() for match in recent[: max(0, parse_int(limit_recent) or 5)]],
    }
    if not matches:
        payload["note"] = "No matches found for this team with the given filters."
    return payload


def _aggregate_table(matches: list[Match]) -> dict[str, dict]:
    table: dict[str, dict] = {}
    for match in matches:
        for key, is_home in ((match.home_team, True), (match.away_team, False)):
            row = table.setdefault(
                key,
                {
                    "team": key,
                    "matches": 0, "wins": 0, "draws": 0, "losses": 0,
                    "goals_for": 0, "goals_against": 0,
                    "home_wins": 0, "home_matches": 0,
                    "away_wins": 0, "away_matches": 0,
                },
            )
            row["matches"] += 1
            scored = match.home_goals if is_home else match.away_goals
            conceded = match.away_goals if is_home else match.home_goals
            row["goals_for"] += scored
            row["goals_against"] += conceded
            if is_home:
                row["home_matches"] += 1
                if scored > conceded:
                    row["wins"] += 1
                    row["home_wins"] += 1
                elif scored < conceded:
                    row["losses"] += 1
                else:
                    row["draws"] += 1
            else:
                row["away_matches"] += 1
                if scored > conceded:
                    row["wins"] += 1
                    row["away_wins"] += 1
                elif scored < conceded:
                    row["losses"] += 1
                else:
                    row["draws"] += 1
    return table


_RANKING_METRICS = {
    "points", "wins", "draws", "losses", "matches",
    "goals_for", "goals_against", "goal_diff", "win_rate",
    "home_wins", "home_points", "home_win_rate",
    "away_wins", "away_points", "away_win_rate",
}


def team_rankings(
    repo: DataRepository,
    *,
    competition: str | None = None,
    season=None,
    metric: str = "points",
    limit: int = 10,
) -> dict:
    """Rank teams by an aggregate metric (best away record, most goals...)."""
    metric = _norm_key(metric)
    if metric not in _RANKING_METRICS:
        raise QueryError(
            f"Unknown metric '{metric}'. Valid metrics: {', '.join(sorted(_RANKING_METRICS))}"
        )
    pool = _apply_filters(repo, repo.matches, competition=competition, season=season)
    if not pool:
        raise QueryError("No matches found for the given filters.")
    table = _aggregate_table(pool)
    rows = []
    for key, row in table.items():
        entity = repo.entity(key)
        row = dict(row)
        row["team"] = entity.display if entity else key
        row["goal_diff"] = row["goals_for"] - row["goals_against"]
        row["points"] = 3 * row["wins"] + row["draws"]
        row["win_rate"] = round(row["wins"] / row["matches"], 3) if row["matches"] else 0.0
        row["home_points"] = 3 * row["home_wins"]
        row["away_points"] = 3 * row["away_wins"]
        row["home_win_rate"] = (
            round(row["home_wins"] / row["home_matches"], 3) if row["home_matches"] else 0.0
        )
        row["away_win_rate"] = (
            round(row["away_wins"] / row["away_matches"], 3) if row["away_matches"] else 0.0
        )
        rows.append(row)
    rows.sort(key=lambda row: (row[metric], row["points"], row["goal_diff"]), reverse=True)
    limit_value = max(1, min(parse_int(limit) or 10, 100))
    return {
        "metric": metric,
        "competition": _canonical_competition(repo, competition),
        "season": _parse_season(season) if season is not None and not is_nothing(season) else None,
        "total_teams": len(rows),
        "rankings": rows[:limit_value],
    }


def find_team(repo: DataRepository, query: str) -> dict:
    """Resolve a team name (any spelling) to the club entity it denotes."""
    entities = repo.resolve_team(query)
    if not entities:
        raise QueryError(
            f"No team matches '{query}'. Note the datasets focus on Brazilian "
            "clubs plus Libertadores opponents."
        )
    results = []
    for entity in entities:
        matches = repo.matches_for_entity(entity.key)
        competitions = defaultdict(int)
        seasons = set()
        for match in matches:
            competitions[match.competition] += 1
            seasons.add(match.season)
        player_count = sum(1 for player in repo.players if player.club_key == entity.key)
        results.append(
            {
                **entity.to_dict(),
                "matches_in_dataset": len(matches),
                "seasons": [str(season) for season in sorted(seasons)],
                "competitions": dict(sorted(competitions.items())),
                "players_in_fifa_dataset": player_count,
            }
        )
    return {"query": query, "results": results}


# ------------------------------------------------------------------- players

def _player_matches_query(player: Player, query: str) -> bool:
    return clean_text(query) in clean_text(player.name)


def search_players(
    repo: DataRepository,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall=None,
    max_age=None,
    sort: str = "overall",
    limit: int = DEFAULT_PLAYER_LIMIT,
) -> dict:
    """Search the FIFA player database by name, nationality, club and position."""
    notes: list[str] = []
    name_key = clean_text(name) if name and not is_nothing(name) else None
    nationality_key = clean_text(nationality) if nationality and not is_nothing(nationality) else None
    position_key = (position or "").strip().upper() if position and not is_nothing(position) else None
    position_group_key = POSITION_SYNONYMS.get(clean_text(position)) if position else None

    club_keys: set[str] = set()
    club_substring = None
    if club and not is_nothing(club):
        entities = repo.resolve_team(club)
        if entities:
            club_keys = {entity.key for entity in entities}
            if len(entities) > 1:
                names = ", ".join(entity.display for entity in entities)
                notes.append(f"Club '{club}' matched multiple teams: {names}")
        else:
            club_substring = clean_text(club)

    min_overall_value = parse_int(min_overall)
    max_age_value = parse_int(max_age)
    if min_overall is not None and not is_nothing(min_overall) and min_overall_value is None:
        raise QueryError(f"Invalid min_overall: {min_overall!r}")
    if max_age is not None and not is_nothing(max_age) and max_age_value is None:
        raise QueryError(f"Invalid max_age: {max_age!r}")

    selected: list[Player] = []
    for player in repo.players:
        if name_key and not _player_matches_query(player, name_key):
            continue
        if nationality_key and nationality_key not in clean_text(player.nationality):
            continue
        if position_key:
            if player.position != position_key and player.position_group != position_group_key:
                continue
        if club_keys and player.club_key not in club_keys:
            continue
        if club_substring and club_substring not in clean_text(player.club):
            continue
        if min_overall_value is not None and (player.overall or 0) < min_overall_value:
            continue
        if max_age_value is not None and (player.age or 999) > max_age_value:
            continue
        selected.append(player)

    sort_key = _norm_key(sort) or "overall"
    if sort_key == "name":
        selected.sort(key=lambda player: player.name)
    elif sort_key == "age":
        selected.sort(key=lambda player: (player.age or 999, -(player.overall or 0)))
    elif sort_key == "potential":
        selected.sort(key=lambda player: (-(player.potential or 0), player.name))
    else:
        selected.sort(key=lambda player: (-(player.overall or 0), player.name))

    total = len(selected)
    limit_value = max(1, min(parse_int(limit) or DEFAULT_PLAYER_LIMIT, MAX_PLAYER_LIMIT))
    payload = {
        "total_players": total,
        "returned": min(total, limit_value),
        "players": [player.to_dict() for player in selected[:limit_value]],
    }
    if notes:
        payload["notes"] = notes
    if total > limit_value:
        payload["truncated"] = True
    return payload


def player_detail(
    repo: DataRepository,
    *,
    name: str | None = None,
    player_id=None,
) -> dict:
    """Full FIFA profile for one player, by name or FIFA id."""
    id_value = parse_int(player_id)
    if id_value is not None:
        for player in repo.players:
            if player.fifa_id == id_value:
                return {"player": player.to_dict(detailed=True)}
        raise QueryError(f"No player with FIFA id {player_id}.")
    if not name or is_nothing(name):
        raise QueryError("Provide a player name or FIFA id.")
    name_key = clean_text(name)
    matches = [player for player in repo.players if _player_matches_query(player, name_key)]
    if not matches:
        raise QueryError(f"No player matches '{name}'.")
    matches.sort(key=lambda player: (-(player.overall or 0), player.name))
    best = matches[0]
    payload = {"player": best.to_dict(detailed=True)}
    if len(matches) > 1:
        payload["other_matching_players"] = [
            player.to_dict() for player in matches[1:6]
        ]
    return payload


# -------------------------------------------------------------- competitions

def standings(repo: DataRepository, competition: str, season) -> dict:
    """League table calculated from match results for one competition season."""
    canonical = _canonical_competition(repo, competition)
    season_value = _parse_season(season)
    info = repo.competition_info.get(canonical or "")
    if info is None or season_value not in info["seasons"]:
        available = {
            name: sorted(entry["seasons"]) for name, entry in repo.competition_info.items()
        }
        raise QueryError(
            f"No data for {canonical} {season_value}. Available: {available}"
        )
    matches = [
        match
        for match in repo.matches
        if match.competition == canonical and match.season == season_value
    ]
    table = _aggregate_table(matches)
    rows = []
    for key, row in table.items():
        entity = repo.entity(key)
        row = dict(row)
        row["team"] = entity.display if entity else key
        row["goal_diff"] = row["goals_for"] - row["goals_against"]
        row["points"] = 3 * row["wins"] + row["draws"]
        rows.append(row)
    rows.sort(
        key=lambda row: (row["points"], row["wins"], row["goal_diff"], row["goals_for"], row["team"]),
        reverse=True,
    )
    teams_count = len(rows)
    relegated: list[str] = []
    for position, row in enumerate(rows, start=1):
        row["position"] = position
        row["status"] = None
        if position == 1:
            row["status"] = "champion"
        if canonical == SERIE_A and teams_count >= 18 and position > teams_count - 4:
            row["status"] = "relegated"
            relegated.append(row["team"])
    expected = teams_count * (teams_count - 1)
    payload = {
        "competition": canonical,
        "season": season_value,
        "source": info["seasons"][season_value]["source"],
        "matches_counted": len(matches),
        "teams": teams_count,
        "table": rows,
        "champion": rows[0]["team"] if rows else None,
    }
    if relegated:
        payload["relegated"] = relegated
    if expected and len(matches) < expected:
        payload["data_complete"] = False
        payload["note"] = (
            f"Partial data: {len(matches)} of {expected} expected matches."
        )
    else:
        payload["data_complete"] = True
    return payload


def competition_info(repo: DataRepository, competition: str | None = None) -> dict:
    """List competitions, their seasons, sources and match counts."""
    if competition is None or is_nothing(competition):
        payload = []
        for name, entry in sorted(repo.competition_info.items()):
            payload.append(
                {
                    "competition": name,
                    "aliases": entry["aliases"],
                    "total_matches": entry["total_matches"],
                    "seasons": {
                        str(season): season_info
                        for season, season_info in sorted(entry["seasons"].items())
                    },
                }
            )
        return {"competitions": payload}
    canonical = _canonical_competition(repo, competition)
    info = repo.competition_info.get(canonical or "")
    if info is None:
        raise QueryError(f"Unknown competition: {competition!r}")
    return {
        "competition": canonical,
        "aliases": info["aliases"],
        "total_matches": info["total_matches"],
        "seasons": {
            str(season): season_info for season, season_info in sorted(info["seasons"].items())
        },
    }


# ---------------------------------------------------------------- statistics

def biggest_wins(
    repo: DataRepository,
    *,
    competition: str | None = None,
    season=None,
    limit: int = 10,
) -> dict:
    """Largest victory margins in the dataset."""
    pool = _apply_filters(repo, repo.matches, competition=competition, season=season)
    if not pool:
        raise QueryError("No matches found for the given filters.")
    ranked = sorted(
        pool,
        key=lambda match: (match.margin, match.home_goals + match.away_goals, match.date),
        reverse=True,
    )
    limit_value = max(1, min(parse_int(limit) or 10, 100))
    page = ranked[:limit_value]
    return {
        "total_matches": len(pool),
        "returned": len(page),
        "biggest_wins": [
            {**match.to_dict(), "margin": match.margin, "winner": _winner_display(match)}
            for match in page
        ],
    }


def _winner_display(match: Match) -> str | None:
    if match.outcome == "home":
        return match.home_display
    if match.outcome == "away":
        return match.away_display
    return None


def stats_summary(
    repo: DataRepository,
    *,
    competition: str | None = None,
    season=None,
) -> dict:
    """Aggregate statistics: goals per match, home/away win rates, extremes."""
    pool = _apply_filters(repo, repo.matches, competition=competition, season=season)
    if not pool:
        raise QueryError("No matches found for the given filters.")
    total_matches = len(pool)
    home_wins = sum(1 for match in pool if match.outcome == "home")
    away_wins = sum(1 for match in pool if match.outcome == "away")
    draws = total_matches - home_wins - away_wins
    goals = sum(match.home_goals + match.away_goals for match in pool)
    home_goals = sum(match.home_goals for match in pool)
    away_goals = sum(match.away_goals for match in pool)
    biggest = max(pool, key=lambda match: (match.margin, match.home_goals + match.away_goals))
    return {
        "competition": _canonical_competition(repo, competition),
        "season": _parse_season(season) if season is not None and not is_nothing(season) else None,
        "matches": total_matches,
        "teams": len({match.home_team for match in pool} | {match.away_team for match in pool}),
        "total_goals": goals,
        "average_goals_per_match": round(goals / total_matches, 2),
        "average_home_goals": round(home_goals / total_matches, 2),
        "average_away_goals": round(away_goals / total_matches, 2),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(home_wins / total_matches, 3),
        "away_win_rate": round(away_wins / total_matches, 3),
        "draw_rate": round(draws / total_matches, 3),
        "biggest_win": {**biggest.to_dict(), "margin": biggest.margin},
        "date_range": [
            min(match.date for match in pool).isoformat(),
            max(match.date for match in pool).isoformat(),
        ],
    }


def derby_matches(
    repo: DataRepository,
    *,
    season=None,
    competition: str | None = None,
    limit: int = 50,
) -> dict:
    """Matches between traditional rival pairs (Fla-Flu, Grenal, ...)."""
    pool = _apply_filters(repo, repo.matches, competition=competition, season=season)
    rival_pairs = [
        (
            {_resolve_one(repo, team_a).key, _resolve_one(repo, team_b).key},
            name,
        )
        for team_a, team_b, name in DERBIES
    ]
    results = []
    for match in pool:
        pair = {match.home_team, match.away_team}
        for keys, name in rival_pairs:
            if pair == keys:
                results.append((match, name))
                break
    results.sort(key=lambda item: item[0].sort_key, reverse=True)
    limit_value = max(1, min(parse_int(limit) or 50, MAX_MATCH_LIMIT))
    page = results[:limit_value]
    return {
        "total_matches": len(results),
        "returned": len(page),
        "derbies": [
            {"derby": name, **match.to_dict()} for match, name in page
        ],
    }
