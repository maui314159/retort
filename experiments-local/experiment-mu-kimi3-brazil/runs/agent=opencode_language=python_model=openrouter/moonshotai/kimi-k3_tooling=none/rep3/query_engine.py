"""Query engine for the Brazilian Soccer MCP server.

Implements every query category required by the specification:

1. Match queries        -> :func:`find_matches`, :func:`head_to_head`
2. Team queries         -> :func:`team_statistics`, :func:`list_teams`
3. Player queries       -> :func:`search_players`, :func:`top_players`,
                           :func:`player_profile`
4. Competition queries  -> :func:`competition_standings`,
                           :func:`top_scoring_teams`,
                           :func:`list_competitions`
5. Statistical analysis -> :func:`biggest_wins`,
                           :func:`competition_overview`

All public functions return JSON-serialisable structures (dicts / lists of
dicts / scalars) so they can be surfaced directly as MCP tool responses.
"""

from __future__ import annotations

import re
from typing import Optional

import pandas as pd

from soccer_data import (
    COMP_BRASILEIRAO,
    COMP_COPA_DO_BRASIL,
    COMP_LIBERTADORES,
    COMP_SERIE_B,
    COMP_SERIE_C,
    SoccerStore,
    get_store,
    normalize_team,
    normalize_text,
    parse_date,
)

MAX_LIMIT = 100

# ---------------------------------------------------------------------------
# Competition name resolution
# ---------------------------------------------------------------------------
_COMPETITION_ALIASES = {
    "brasileirao": COMP_BRASILEIRAO,
    "brasileirao serie a": COMP_BRASILEIRAO,
    "serie a": COMP_BRASILEIRAO,
    "campeonato brasileiro": COMP_BRASILEIRAO,
    "campeonato brasileiro serie a": COMP_BRASILEIRAO,
    "brasileirao serie b": COMP_SERIE_B,
    "serie b": COMP_SERIE_B,
    "brasileirao serie c": COMP_SERIE_C,
    "serie c": COMP_SERIE_C,
    "copa do brasil": COMP_COPA_DO_BRASIL,
    "brazilian cup": COMP_COPA_DO_BRASIL,
    "libertadores": COMP_LIBERTADORES,
    "copa libertadores": COMP_LIBERTADORES,
    "copa libertadores da america": COMP_LIBERTADORES,
}

# ---------------------------------------------------------------------------
# FIFA position groups
# ---------------------------------------------------------------------------
_POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "midfielder": {"CDM", "CM", "CAM", "LM", "RM", "LDM", "RDM", "LCM",
                   "RCM", "LAM", "RAM"},
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
}

_SUFFIX_DISPLAY_RE = re.compile(r"\s*[-(]?\s*[A-Z]{2,3}\)?$")


def _resolve_competition(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = normalize_text(value)
    if key in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[key]
    for canonical in (COMP_BRASILEIRAO, COMP_SERIE_B, COMP_SERIE_C,
                      COMP_COPA_DO_BRASIL, COMP_LIBERTADORES):
        if normalize_text(canonical) == key:
            return canonical
    raise ValueError(
        f"Unknown competition {value!r}. Known competitions: "
        "Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores."
    )


def _resolve_team_key(store: SoccerStore, team: str) -> str:
    """Resolve a user-supplied team name to a canonical store key."""
    key = normalize_team(team)
    known = set(store.played_matches.home_key) | set(store.played_matches.away_key)
    known |= set(store.players.club_team_key.dropna())
    if key in known:
        return key
    candidates = sorted(k for k in known if key and key in k)
    if len(candidates) == 1:
        return candidates[0]
    if key:
        return key  # unknown team: let queries return empty results
    raise ValueError("Team name must not be empty")


def _display_names(store: SoccerStore) -> dict:
    """Map each canonical team key to a friendly display name."""
    raw = pd.concat(
        [store.matches[["home_key", "home_team"]].rename(
            columns={"home_key": "key", "home_team": "raw"}),
         store.matches[["away_key", "away_team"]].rename(
            columns={"away_key": "key", "away_team": "raw"})]
    )
    counts = raw.groupby(["key", "raw"]).size().reset_index(name="n")
    counts = counts.sort_values("n", ascending=False)
    best = counts.drop_duplicates("key").set_index("key")["raw"].to_dict()
    names = {}
    for key, name in best.items():
        pretty = _SUFFIX_DISPLAY_RE.sub("", str(name)).strip()
        names[key] = pretty or str(name)
    return names


def _team_name(store: SoccerStore, key: str) -> str:
    return _display_names(store).get(key, key.title())


def _match_to_dict(store: SoccerStore, row: pd.Series) -> dict:
    return {
        "date": row["date"].date().isoformat() if pd.notna(row["date"]) else None,
        "season": int(row["season"]) if pd.notna(row["season"]) else None,
        "competition": row["competition"],
        "home_team": _team_name(store, row["home_key"]),
        "away_team": _team_name(store, row["away_key"]),
        "home_goals": int(row["home_goals"]) if pd.notna(row["home_goals"]) else None,
        "away_goals": int(row["away_goals"]) if pd.notna(row["away_goals"]) else None,
        "round": (int(row["round"]) if pd.notna(row["round"])
                  and str(row["round"]).replace(".", "").isdigit()
                  else (str(row["round"]) if pd.notna(row["round"]) else None)),
        "stage": str(row["stage"]) if pd.notna(row["stage"]) else None,
        "venue": str(row["venue"]) if pd.notna(row["venue"]) else None,
        "source": row["source"],
    }


def _played(store: SoccerStore) -> pd.DataFrame:
    return store.played_matches


def _filter_matches(
    store: SoccerStore,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: Optional[str] = None,
    stage: Optional[str] = None,
) -> pd.DataFrame:
    df = _played(store)
    comp = _resolve_competition(competition)
    if comp is not None:
        df = df[df.competition == comp]
    if season is not None:
        df = df[df.season == int(season)]
    if date_from is not None:
        df = df[df.date >= parse_date(date_from)]
    if date_to is not None:
        df = df[df.date <= parse_date(date_to)]
    if stage is not None:
        skey = normalize_text(stage)
        stage_keys = df.stage.map(normalize_text)
        on_round = df["round"].map(normalize_text) == skey
        exact = df[(stage_keys == skey) | on_round]
        if exact.empty:
            contains = stage_keys.str.contains(skey, na=False, regex=False)
            exact = df[contains | on_round]
        df = exact
    if team is not None:
        key = _resolve_team_key(store, team)
        if venue == "home":
            df = df[df.home_key == key]
        elif venue == "away":
            df = df[df.away_key == key]
        else:
            df = df[(df.home_key == key) | (df.away_key == key)]
    if opponent is not None:
        okey = _resolve_team_key(store, opponent)
        df = df[(df.home_key == okey) | (df.away_key == okey)]
    return df


# ---------------------------------------------------------------------------
# 1. Match queries
# ---------------------------------------------------------------------------
def find_matches(
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    venue: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 20,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Find matches filtered by team, opponent, competition, season, dates."""
    store = store or get_store()
    if venue not in (None, "home", "away"):
        raise ValueError("venue must be 'home' or 'away'")
    df = _filter_matches(store, team, opponent, competition, season,
                         date_from, date_to, venue, stage)
    df = df.sort_values("date", ascending=False, kind="mergesort")
    limit = max(1, min(int(limit), MAX_LIMIT))
    return {
        "total": int(len(df)),
        "returned": int(min(len(df), limit)),
        "matches": [_match_to_dict(store, row)
                    for _, row in df.head(limit).iterrows()],
    }


def head_to_head(
    team1: str,
    team2: str,
    limit: int = 10,
    store: Optional[SoccerStore] = None,
) -> dict:
    """All matches between two teams plus the win/draw/loss balance."""
    store = store or get_store()
    key1 = _resolve_team_key(store, team1)
    key2 = _resolve_team_key(store, team2)
    df = _played(store)
    df = df[((df.home_key == key1) & (df.away_key == key2))
            | ((df.home_key == key2) & (df.away_key == key1))]
    df = df.sort_values("date", ascending=False, kind="mergesort")

    wins1 = int((((df.home_key == key1) & (df.home_goals > df.away_goals))
                 | ((df.away_key == key1) & (df.away_goals > df.home_goals))).sum())
    wins2 = int((((df.home_key == key2) & (df.home_goals > df.away_goals))
                 | ((df.away_key == key2) & (df.away_goals > df.home_goals))).sum())
    draws = int((df.home_goals == df.away_goals).sum())
    limit = max(1, min(int(limit), MAX_LIMIT))
    return {
        "team1": _team_name(store, key1),
        "team2": _team_name(store, key2),
        "total_matches": int(len(df)),
        "summary": {
            f"{_team_name(store, key1)}_wins": wins1,
            f"{_team_name(store, key2)}_wins": wins2,
            "draws": draws,
        },
        "matches": [_match_to_dict(store, row)
                    for _, row in df.head(limit).iterrows()],
    }


# ---------------------------------------------------------------------------
# 2. Team queries
# ---------------------------------------------------------------------------
def _record_for(df: pd.DataFrame, key: str) -> dict:
    home = df[df.home_key == key]
    away = df[df.away_key == key]
    wins = int(((home.home_goals > home.away_goals).sum())
               + ((away.away_goals > away.home_goals).sum()))
    draws = int(((home.home_goals == home.away_goals).sum())
                + ((away.away_goals == away.home_goals).sum()))
    played = int(len(home) + len(away))
    losses = played - wins - draws
    gf = int(home.home_goals.sum() + away.away_goals.sum())
    ga = int(home.away_goals.sum() + away.home_goals.sum())
    return {
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "win_rate_pct": round(100.0 * wins / played, 1) if played else 0.0,
    }


def team_statistics(
    team: str,
    season: Optional[int] = None,
    competition: Optional[str] = None,
    venue: Optional[str] = None,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Win/draw/loss record and goals for a team (optionally filtered)."""
    store = store or get_store()
    key = _resolve_team_key(store, team)
    df = _filter_matches(store, team=team, competition=competition,
                         season=season, venue=venue)
    result = {
        "team": _team_name(store, key),
        "season": int(season) if season is not None else None,
        "competition": _resolve_competition(competition),
        "venue": venue or "all",
        **_record_for(df, key),
    }
    if competition is None:
        breakdown = {}
        for comp, sub in df.groupby("competition"):
            breakdown[comp] = _record_for(sub, key)
        result["by_competition"] = breakdown
    return result


def list_teams(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    store: Optional[SoccerStore] = None,
) -> dict:
    """List the canonical names of teams present in the datasets."""
    store = store or get_store()
    df = _filter_matches(store, competition=competition, season=season)
    keys = sorted(set(df.home_key) | set(df.away_key))
    names = sorted({_team_name(store, k) for k in keys})
    return {"total": len(names), "teams": names}


# ---------------------------------------------------------------------------
# 3. Player queries
# ---------------------------------------------------------------------------
_PLAYER_COLUMNS = ["ID", "Name", "Age", "Nationality", "Overall", "Potential",
                   "Club", "Position", "JerseyNumber", "Height", "Weight"]


def _player_to_dict(row: pd.Series) -> dict:
    out = {}
    for col in _PLAYER_COLUMNS:
        if col not in row.index:
            continue
        val = row[col]
        if pd.isna(val):
            out[col.lower()] = None
        elif col in ("ID", "Age", "Overall", "Potential", "JerseyNumber"):
            out[col.lower()] = int(val)
        else:
            out[col.lower()] = str(val)
    return out


def _filter_players(
    store: SoccerStore,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
) -> pd.DataFrame:
    df = store.players
    if name is not None:
        key = normalize_text(name)
        df = df[df.name_key.str.contains(key, na=False, regex=False)]
    if nationality is not None:
        key = normalize_text(nationality)
        df = df[df.nationality_key == key]
    if club is not None:
        key = normalize_text(club)
        df = df[df.club_key.str.contains(key, na=False, regex=False)]
    if position is not None:
        pkey = normalize_text(position)
        if pkey in _POSITION_GROUPS:
            df = df[df.Position.isin(sorted(_POSITION_GROUPS[pkey]))]
        else:
            df = df[df.Position.fillna("").str.upper() == pkey.upper()]
    if min_overall is not None:
        df = df[df.Overall >= int(min_overall)]
    return df


def search_players(
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Search FIFA players by name, nationality, club, position, rating."""
    store = store or get_store()
    df = _filter_players(store, name, nationality, club, position, min_overall)
    df = df.sort_values("Overall", ascending=False, kind="mergesort")
    limit = max(1, min(int(limit), MAX_LIMIT))
    return {
        "total": int(len(df)),
        "returned": int(min(len(df), limit)),
        "players": [_player_to_dict(row) for _, row in df.head(limit).iterrows()],
    }


def top_players(
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    limit: int = 10,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Highest-rated players, optionally filtered (e.g. Brazilian players)."""
    store = store or get_store()
    return search_players(nationality=nationality, club=club,
                          position=position, limit=limit, store=store)


def player_profile(
    name: str,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Profile of the best-matching player for a name (exact > startswith >
    contains), with key skill ratings."""
    store = store or get_store()
    key = normalize_text(name)
    df = store.players
    exact = df[df.name_key == key]
    if exact.empty:
        exact = df[df.name_key.str.startswith(key, na=False)]
    if exact.empty:
        exact = df[df.name_key.str.contains(key, na=False, regex=False)]
    if exact.empty:
        return {"found": False, "query": name, "player": None}
    row = exact.sort_values("Overall", ascending=False).iloc[0]
    skills = {}
    for col in ("Crossing", "Finishing", "HeadingAccuracy", "ShortPassing",
                "Volleys", "Dribbling", "Curve", "FKAccuracy", "LongPassing",
                "BallControl", "Acceleration", "SprintSpeed", "Agility",
                "Reactions", "Balance", "ShotPower", "Jumping", "Stamina",
                "Strength", "LongShots", "Aggression", "Interceptions",
                "Positioning", "Vision", "Penalties", "Composure", "Marking",
                "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
                "GKKicking", "GKPositioning", "GKReflexes"):
        if col in row.index and pd.notna(row[col]):
            try:
                skills[col.lower()] = int(row[col])
            except (TypeError, ValueError):
                pass
    return {
        "found": True,
        "query": name,
        "player": {**_player_to_dict(row), "skills": skills},
    }


# ---------------------------------------------------------------------------
# 4. Competition queries
# ---------------------------------------------------------------------------
def competition_standings(
    season: int,
    competition: str = COMP_BRASILEIRAO,
    store: Optional[SoccerStore] = None,
) -> dict:
    """League table calculated from match results (3/1/0 points).

    Brazilian tie-break order: points, wins, goal difference, goals for.
    """
    store = store or get_store()
    comp = _resolve_competition(competition)
    df = _filter_matches(store, competition=comp, season=int(season))
    if df.empty:
        return {"competition": comp, "season": int(season),
                "total_teams": 0, "standings": []}
    keys = sorted(set(df.home_key) | set(df.away_key))
    rows = []
    for key in keys:
        rec = _record_for(df, key)
        rows.append({
            "team": _team_name(store, key),
            "played": rec["matches"],
            "wins": rec["wins"],
            "draws": rec["draws"],
            "losses": rec["losses"],
            "goals_for": rec["goals_for"],
            "goals_against": rec["goals_against"],
            "goal_difference": rec["goal_difference"],
            "points": rec["wins"] * 3 + rec["draws"],
        })
    rows.sort(key=lambda r: (-r["points"], -r["wins"],
                             -r["goal_difference"], -r["goals_for"],
                             r["team"]))
    for i, row in enumerate(rows, start=1):
        row["position"] = i
    if rows:
        rows[0]["champion"] = True
    return {
        "competition": comp,
        "season": int(season),
        "total_teams": len(rows),
        "note": "Calculated from match results in the provided datasets",
        "standings": rows,
    }


def top_scoring_teams(
    season: Optional[int] = None,
    competition: Optional[str] = None,
    limit: int = 10,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Teams ranked by goals scored."""
    store = store or get_store()
    df = _filter_matches(store, competition=competition, season=season)
    gf = pd.concat([
        df.groupby("home_key").home_goals.sum(),
        df.groupby("away_key").away_goals.sum(),
    ]).groupby(level=0).sum().sort_values(ascending=False)
    limit = max(1, min(int(limit), MAX_LIMIT))
    return {
        "competition": _resolve_competition(competition),
        "season": int(season) if season is not None else None,
        "teams": [{"team": _team_name(store, k), "goals": int(v)}
                  for k, v in gf.head(limit).items()],
    }


def list_competitions(store: Optional[SoccerStore] = None) -> dict:
    """Competitions in the store with season coverage and match counts."""
    store = store or get_store()
    df = _played(store)
    out = []
    for comp, sub in df.groupby("competition"):
        seasons = sorted(int(s) for s in sub.season.dropna().unique())
        out.append({
            "competition": comp,
            "matches": int(len(sub)),
            "seasons": seasons,
            "season_range": f"{seasons[0]}-{seasons[-1]}" if seasons else None,
        })
    return {"total": len(out), "competitions": out}


# ---------------------------------------------------------------------------
# 5. Statistical analysis
# ---------------------------------------------------------------------------
def biggest_wins(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    limit: int = 10,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Matches with the largest goal margin."""
    store = store or get_store()
    df = _filter_matches(store, competition=competition, season=season).copy()
    df["margin"] = (df.home_goals - df.away_goals).abs()
    df = df.sort_values(["margin", "home_goals", "away_goals"],
                        ascending=False, kind="mergesort")
    limit = max(1, min(int(limit), MAX_LIMIT))
    matches = []
    for _, row in df.head(limit).iterrows():
        entry = _match_to_dict(store, row)
        entry["margin"] = int(row["margin"])
        matches.append(entry)
    return {"matches": matches}


def best_team_records(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
    limit: int = 10,
    min_matches: int = 5,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Teams ranked by points per game, e.g. 'best away record'.

    ``venue`` restricts the record to home or away matches; teams with
    fewer than ``min_matches`` matches are ignored.
    """
    store = store or get_store()
    if venue not in (None, "home", "away"):
        raise ValueError("venue must be 'home' or 'away'")
    df = _filter_matches(store, competition=competition, season=season)
    keys = sorted(set(df.home_key) | set(df.away_key))
    rows = []
    for key in keys:
        if venue == "home":
            sub = df[df.home_key == key]
        elif venue == "away":
            sub = df[df.away_key == key]
        else:
            sub = df[(df.home_key == key) | (df.away_key == key)]
        rec = _record_for(sub, key)
        if rec["matches"] < int(min_matches):
            continue
        ppg = (rec["wins"] * 3 + rec["draws"]) / rec["matches"]
        rows.append({"team": _team_name(store, key),
                     "points_per_game": round(ppg, 2), **rec})
    rows.sort(key=lambda r: (-r["points_per_game"], -r["win_rate_pct"],
                             -r["goal_difference"], r["team"]))
    limit = max(1, min(int(limit), MAX_LIMIT))
    return {
        "competition": _resolve_competition(competition),
        "season": int(season) if season is not None else None,
        "venue": venue or "all",
        "teams": rows[:limit],
    }


def competition_overview(
    competition: Optional[str] = None,
    season: Optional[int] = None,
    store: Optional[SoccerStore] = None,
) -> dict:
    """Aggregate stats: matches, goals per match, home/draw/away rates."""
    store = store or get_store()
    df = _filter_matches(store, competition=competition, season=season)
    played = int(len(df))
    if played == 0:
        return {"matches": 0}
    goals = int(df.home_goals.sum() + df.away_goals.sum())
    home_wins = int((df.home_goals > df.away_goals).sum())
    draws = int((df.home_goals == df.away_goals).sum())
    away_wins = played - home_wins - draws
    return {
        "competition": _resolve_competition(competition),
        "season": int(season) if season is not None else None,
        "matches": played,
        "total_goals": goals,
        "avg_goals_per_match": round(goals / played, 2),
        "home_win_rate_pct": round(100.0 * home_wins / played, 1),
        "draw_rate_pct": round(100.0 * draws / played, 1),
        "away_win_rate_pct": round(100.0 * away_wins / played, 1),
    }
