"""Query engine for Brazilian soccer data."""

import re
import unicodedata
from datetime import date, datetime
from typing import List, Optional

import pandas as pd

from data_loader import BrazilianSoccerData, team_matches


def _filter_by_team(df: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return rows where either home or away team matches ``team``."""
    mask = df["home_team_raw"].apply(lambda x: team_matches(str(x), team)) | \
           df["away_team_raw"].apply(lambda x: team_matches(str(x), team))
    return df[mask]


def _filter_by_teams(df: pd.DataFrame, team_a: str, team_b: str) -> pd.DataFrame:
    """Return rows where one side matches ``team_a`` and the other ``team_b``."""
    def row_matches(row) -> bool:
        home, away = str(row.home_team_raw), str(row.away_team_raw)
        a_is_home = team_matches(home, team_a)
        a_is_away = team_matches(away, team_a)
        b_is_home = team_matches(home, team_b)
        b_is_away = team_matches(away, team_b)
        return (a_is_home and b_is_away) or (b_is_home and a_is_away)
    return df[df.apply(row_matches, axis=1)]


def _normalize_competition(value: str) -> str:
    """Return a lowercased, accent-folded competition name for matching."""
    value = str(value or "")
    value = "".join(
        c for c in unicodedata.normalize("NFKD", value)
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _competition_matches(value: str, query: str) -> bool:
    """Compare competition names ignoring case, accents and punctuation."""
    return _normalize_competition(value) == _normalize_competition(query)


def _as_int(value) -> Optional[int]:
    return int(value) if pd.notna(value) else None


def _as_float(value) -> float:
    return float(value)


def _fmt_date(value) -> Optional[str]:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _to_date(value):
    """Convert a value to a pandas Timestamp (UTC-naive date)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date)):
        return pd.Timestamp(value)
    try:
        return pd.to_datetime(value)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------


def find_matches(
    data: BrazilianSoccerData,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """Find matches matching the supplied criteria."""
    df = data.matches.copy()

    if team and opponent:
        df = _filter_by_teams(df, team, opponent)
    elif team:
        df = _filter_by_team(df, team)
    elif opponent:
        df = _filter_by_team(df, opponent)

    if competition:
        df = df[df["competition"].apply(lambda x: _competition_matches(x, competition))]

    if season is not None:
        df = df[df["season"] == season]

    start = _to_date(start_date)
    end = _to_date(end_date)
    if start is not None:
        df = df[df["date"] >= start]
    if end is not None:
        df = df[df["date"] <= end]

    df = df.head(limit)
    return [_match_record(row) for _, row in df.iterrows()]


def _match_record(row) -> dict:
    return {
        "date": _fmt_date(row.date),
        "competition": row.competition,
        "home_team": row.home_team_raw,
        "away_team": row.away_team_raw,
        "home_goals": _as_int(row.home_goals),
        "away_goals": _as_int(row.away_goals),
        "season": _as_int(row.season),
        "round": _as_int(row["round"]),
        "stage": row.stage,
        "stadium": row.stadium,
    }


def head_to_head(data: BrazilianSoccerData, team_a: str, team_b: str, limit: int = 50) -> dict:
    """Return matches and aggregate record between two teams."""
    df = _filter_by_teams(data.matches, team_a, team_b).copy()

    def result(row):
        if pd.isna(row.home_goals) or pd.isna(row.away_goals):
            return "unknown"
        home = team_matches(str(row.home_team_raw), team_a)
        a_goals = row.home_goals if home else row.away_goals
        b_goals = row.away_goals if home else row.home_goals
        if a_goals > b_goals:
            return "a_win"
        if a_goals < b_goals:
            return "b_win"
        return "draw"

    df["result"] = df.apply(result, axis=1)
    return {
        "team_a": team_a,
        "team_b": team_b,
        "matches": [_match_record(row) for _, row in df.head(limit).iterrows()],
        "team_a_wins": int((df["result"] == "a_win").sum()),
        "team_b_wins": int((df["result"] == "b_win").sum()),
        "draws": int((df["result"] == "draw").sum()),
    }


# ---------------------------------------------------------------------------
# Team queries
# ---------------------------------------------------------------------------


def team_stats(
    data: BrazilianSoccerData,
    team: str,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    venue: Optional[str] = None,
) -> dict:
    """Calculate wins/losses/draws and goals for a team under given filters."""
    df = data.matches.copy()

    if venue == "home":
        team_mask = df["home_team_raw"].apply(lambda x: team_matches(str(x), team))
        df = df[team_mask]
    elif venue == "away":
        team_mask = df["away_team_raw"].apply(lambda x: team_matches(str(x), team))
        df = df[team_mask]
    else:
        df = _filter_by_team(df, team)

    if competition:
        df = df[df["competition"].apply(lambda x: _competition_matches(x, competition))]

    if season is not None:
        df = df[df["season"] == season]

    def outcome(row):
        home = team_matches(str(row.home_team_raw), team)
        gf = row.home_goals if home else row.away_goals
        ga = row.away_goals if home else row.home_goals
        if pd.isna(gf) or pd.isna(ga):
            return None
        if gf > ga:
            return "win"
        if gf < ga:
            return "loss"
        return "draw"

    df = df.copy()
    df["outcome"] = df.apply(outcome, axis=1)
    df = df[df["outcome"].notna()]

    wins = int((df["outcome"] == "win").sum())
    draws = int((df["outcome"] == "draw").sum())
    losses = int((df["outcome"] == "loss").sum())
    total = wins + draws + losses

    def goals_for(row):
        home = team_matches(str(row.home_team_raw), team)
        return row.home_goals if home else row.away_goals

    def goals_against(row):
        home = team_matches(str(row.home_team_raw), team)
        return row.away_goals if home else row.home_goals

    gf = int(df.apply(goals_for, axis=1).sum()) if total else 0
    ga = int(df.apply(goals_against, axis=1).sum()) if total else 0

    return {
        "team": team,
        "competition": competition,
        "season": season,
        "venue": venue or "all",
        "matches": total,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "win_rate": _as_float(round(wins / total * 100, 1)) if total else 0.0,
    }


def best_attack(
    data: BrazilianSoccerData,
    competition: Optional[str] = None,
    season: Optional[int] = None,
    top_n: int = 5,
) -> List[dict]:
    """Return teams that scored the most goals."""
    df = data.matches.copy()
    if competition:
        df = df[df["competition"].apply(lambda x: _competition_matches(x, competition))]
    if season is not None:
        df = df[df["season"] == season]

    home = df.groupby("home_team")["home_goals"].sum().reset_index()
    home.columns = ["team", "goals"]
    away = df.groupby("away_team")["away_goals"].sum().reset_index()
    away.columns = ["team", "goals"]
    total = pd.concat([home, away]).groupby("team")["goals"].sum().reset_index()
    total = total.sort_values(by="goals", ascending=False).head(top_n)
    return [{"team": row.team, "goals": int(row.goals)} for _, row in total.iterrows()]


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------


def search_players(
    data: BrazilianSoccerData,
    name: Optional[str] = None,
    nationality: Optional[str] = None,
    club: Optional[str] = None,
    position: Optional[str] = None,
    min_overall: Optional[int] = None,
    limit: int = 20,
) -> dict:
    """Search the FIFA player dataset."""
    df = data.players.copy()

    if name:
        name_lower = name.lower()
        mask = df["name"].fillna("").str.lower().str.contains(name_lower, na=False) | \
               df["name_norm"].str.contains(name_lower, na=False)
        df = df[mask]

    if nationality:
        df = df[df["nationality"].str.lower() == nationality.lower()]

    if club:
        club_lower = club.lower()
        df = df[df["club"].fillna("").str.lower().str.contains(club_lower, na=False)]

    if position:
        df = df[df["position"].fillna("").str.upper().str.contains(position.upper(), na=False)]

    if min_overall is not None:
        df = df[df["overall"] >= min_overall]

    df = df.sort_values(by="overall", ascending=False).head(limit)

    records = []
    for _, row in df.iterrows():
        records.append({
            "id": _as_int(row["ID"]) if "ID" in row else None,
            "name": row["name"],
            "age": _as_int(row["age"]),
            "nationality": row.get("nationality"),
            "overall": _as_int(row["overall"]),
            "potential": _as_int(row["potential"]),
            "club": row.get("club"),
            "position": row.get("position"),
        })

    return {
        "count": int(len(records)),
        "players": records,
    }


def top_players_by_club(data: BrazilianSoccerData, club: Optional[str] = None, top_n: int = 5) -> dict:
    """Return highest-overall players, optionally filtered to a club."""
    return search_players(data, club=club, limit=top_n)


# ---------------------------------------------------------------------------
# Competition queries
# ---------------------------------------------------------------------------


def season_standings(
    data: BrazilianSoccerData,
    competition: str,
    season: int,
    top_n: Optional[int] = None,
) -> List[dict]:
    """Compute league table from match results."""
    df = data.matches.copy()
    df = df[df["competition"].apply(lambda x: _competition_matches(x, competition))]
    df = df[df["season"] == season]
    df = df[df["home_goals"].notna() & df["away_goals"].notna()]

    if df.empty:
        return []

    standings = {}
    for _, row in df.iterrows():
        home = str(row.home_team)
        away = str(row.away_team)
        hg, ag = int(row.home_goals), int(row.away_goals)

        for team in (home, away):
            if team not in standings:
                standings[team] = {
                    "team": team,
                    "points": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "matches": 0,
                }
            standings[team]["matches"] += 1

        standings[home]["goals_for"] += hg
        standings[home]["goals_against"] += ag
        standings[away]["goals_for"] += ag
        standings[away]["goals_against"] += hg

        if hg > ag:
            standings[home]["points"] += 3
            standings[home]["wins"] += 1
            standings[away]["losses"] += 1
        elif hg < ag:
            standings[away]["points"] += 3
            standings[away]["wins"] += 1
            standings[home]["losses"] += 1
        else:
            standings[home]["points"] += 1
            standings[away]["points"] += 1
            standings[home]["draws"] += 1
            standings[away]["draws"] += 1

    rows = sorted(
        standings.values(),
        key=lambda r: (r["points"], r["goals_for"] - r["goals_against"], r["goals_for"]),
        reverse=True,
    )
    if top_n:
        rows = rows[:top_n]

    for i, row in enumerate(rows, start=1):
        row["position"] = i

    return rows


def relegated_teams(data: BrazilianSoccerData, competition: str, season: int, bottom_n: int = 4) -> List[dict]:
    """Return the bottom ``bottom_n`` teams in a season table."""
    table = season_standings(data, competition, season)
    if not table:
        return []
    return table[-bottom_n:]


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------


def competition_stats(data: BrazilianSoccerData, competition: Optional[str] = None) -> dict:
    """Aggregate goal statistics for a competition."""
    df = data.matches.copy()
    if competition:
        df = df[df["competition"].apply(lambda x: _competition_matches(x, competition))]

    df = df[df["home_goals"].notna() & df["away_goals"].notna()]
    total = len(df)
    if total == 0:
        return {
            "competition": competition,
            "matches": 0,
            "avg_goals": 0.0,
            "home_win_rate": 0.0,
            "draw_rate": 0.0,
            "away_win_rate": 0.0,
        }

    total_goals = (df["home_goals"] + df["away_goals"]).sum()
    home_wins = int((df["home_goals"] > df["away_goals"]).sum())
    away_wins = int((df["home_goals"] < df["away_goals"]).sum())
    draws = int((df["home_goals"] == df["away_goals"]).sum())

    return {
        "competition": competition,
        "matches": int(total),
        "avg_goals": _as_float(round(total_goals / total, 2)),
        "home_win_rate": _as_float(round(home_wins / total * 100, 1)),
        "draw_rate": _as_float(round(draws / total * 100, 1)),
        "away_win_rate": _as_float(round(away_wins / total * 100, 1)),
    }


def biggest_wins(data: BrazilianSoccerData, competition: Optional[str] = None, top_n: int = 10) -> List[dict]:
    """Return the largest goal-margin victories."""
    df = data.matches.copy()
    if competition:
        df = df[df["competition"].apply(lambda x: _competition_matches(x, competition))]

    df = df[df["home_goals"].notna() & df["away_goals"].notna()]
    df["margin"] = (df["home_goals"] - df["away_goals"]).abs()
    df = df.sort_values(by="margin", ascending=False).head(top_n)

    records = []
    for _, row in df.iterrows():
        records.append({
            "date": _fmt_date(row.date),
            "competition": row.competition,
            "match": f"{row.home_team_raw} {_as_int(row.home_goals)}-{_as_int(row.away_goals)} {row.away_team_raw}",
            "margin": _as_int(row.margin),
        })
    return records


def best_home_record(data: BrazilianSoccerData, competition: Optional[str] = None, min_matches: int = 5) -> List[dict]:
    """Return teams ranked by home win rate."""
    df = data.matches.copy()
    if competition:
        df = df[df["competition"].apply(lambda x: _competition_matches(x, competition))]

    df = df[df["home_goals"].notna() & df["away_goals"].notna()]
    home = df.groupby("home_team").agg(
        matches=("home_team", "size"),
        wins=("home_goals", lambda s: (s > df.loc[s.index, "away_goals"]).sum()),
    ).reset_index()
    home = home[home["matches"] >= min_matches]
    home["win_rate"] = (home["wins"] / home["matches"] * 100).round(1)
    home = home.sort_values(by=["win_rate", "matches"], ascending=False)
    return [{"team": row.home_team, "matches": int(row.matches), "wins": int(row.wins), "win_rate": _as_float(row.win_rate)}
            for _, row in home.iterrows()]


def best_away_record(data: BrazilianSoccerData, competition: Optional[str] = None, min_matches: int = 5) -> List[dict]:
    """Return teams ranked by away win rate."""
    df = data.matches.copy()
    if competition:
        df = df[df["competition"].apply(lambda x: _competition_matches(x, competition))]

    df = df[df["home_goals"].notna() & df["away_goals"].notna()]
    away = df.groupby("away_team").agg(
        matches=("away_team", "size"),
        wins=("away_goals", lambda s: (s > df.loc[s.index, "home_goals"]).sum()),
    ).reset_index()
    away = away[away["matches"] >= min_matches]
    away["win_rate"] = (away["wins"] / away["matches"] * 100).round(1)
    away = away.sort_values(by=["win_rate", "matches"], ascending=False)
    return [{"team": row.away_team, "matches": int(row.matches), "wins": int(row.wins), "win_rate": _as_float(row.win_rate)}
            for _, row in away.iterrows()]
