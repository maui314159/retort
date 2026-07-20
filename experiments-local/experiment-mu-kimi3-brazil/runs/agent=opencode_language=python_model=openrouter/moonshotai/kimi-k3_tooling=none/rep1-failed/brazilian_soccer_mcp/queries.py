"""Query layer over the unified Brazilian soccer dataset.

Why: the MCP tools need small, composable, well-tested functions that
answer the five capability categories from the specification: match
queries, team queries, player queries, competition queries and
statistical analysis.

What: every public function takes a `Dataset` (or uses the cached
default) and returns JSON-serializable dicts. Where the specification
shows an example answer format, the result also carries a ``summary``
string in that style.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .data import (
    BRASILEIRAO_A,
    BRASILEIRAO_B,
    BRASILEIRAO_C,
    COPA_DO_BRASIL,
    LIBERTADORES,
    Dataset,
    get_dataset,
)
from .normalization import display_team, normalize_team, strip_accents

# ----------------------------------------------------------------------
# Filter helpers
# ----------------------------------------------------------------------

_COMPETITION_ALIASES = {
    "brasileirao": BRASILEIRAO_A,
    "brasileirao serie a": BRASILEIRAO_A,
    "serie a": BRASILEIRAO_A,
    "campeonato brasileiro": BRASILEIRAO_A,
    "campeonato brasileiro serie a": BRASILEIRAO_A,
    "brasileirao serie b": BRASILEIRAO_B,
    "serie b": BRASILEIRAO_B,
    "brasileirao serie c": BRASILEIRAO_C,
    "serie c": BRASILEIRAO_C,
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
    "copa libertadores da america": LIBERTADORES,
}


def _norm_text(value: str) -> str:
    return strip_accents(str(value)).lower().strip()


def resolve_competition(query: str | None, matches: pd.DataFrame) -> str | None:
    """Resolve a free-text competition name to a canonical one.

    Returns the canonical competition name, or None when *query* is
    None. Raises ValueError when the query matches nothing.
    """
    if query is None:
        return None
    q = _norm_text(query)
    if q in _COMPETITION_ALIASES:
        return _COMPETITION_ALIASES[q]
    known = sorted(matches["competition"].unique())
    for name in known:
        if _norm_text(name) == q:
            return name
    for name in known:  # substring fallback, e.g. "série a"
        if q and q in _norm_text(name):
            return name
    raise ValueError(
        f"unknown competition {query!r}; available: {', '.join(known)}"
    )


def _parse_date(value: str | None, dayfirst: bool = False) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, format="mixed", dayfirst=dayfirst, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"could not parse date: {value!r}")
    return pd.Timestamp(ts)


def _filter_matches(
    matches: pd.DataFrame,
    *,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str | None = None,
    round_: int | None = None,
    stage: str | None = None,
) -> pd.DataFrame:
    """Apply the shared filter set to the unified match table."""
    df = matches
    if competition is not None:
        df = df[df["competition"] == resolve_competition(competition, matches)]
    if season is not None:
        df = df[df["season"] == int(season)]
    start = _parse_date(date_from)
    if start is not None:
        df = df[df["date"] >= start]
    end = _parse_date(date_to)
    if end is not None:
        df = df[df["date"] <= end + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)]
    if round_ is not None:
        df = df[df["round"] == int(round_)]
    if stage is not None:
        df = _filter_stage(df, stage)
    if team is not None:
        canon = normalize_team(team)
        home = df["home_canon"] == canon
        away = df["away_canon"] == canon
        if venue == "home":
            df = df[home]
        elif venue == "away":
            df = df[away]
        else:
            df = df[home | away]
    if opponent is not None:
        canon = normalize_team(opponent)
        df = df[(df["home_canon"] == canon) | (df["away_canon"] == canon)]
    return df


def _filter_stage(df: pd.DataFrame, stage: str) -> pd.DataFrame:
    """Filter by knockout stage; 'final' also maps to the Copa do Brasil's last round."""
    s = _norm_text(stage)
    if s in {"final", "finals"}:
        lib_mask = df["stage"].fillna("").map(_norm_text).isin({"final", "finals"})
        cup = df[df["competition"] == COPA_DO_BRASIL]
        if len(cup):
            max_round = cup.groupby("season")["round"].transform("max")
            cup_final_mask = (cup["round"] == max_round) & cup["round"].notna()
            final_idx = set(df.index[lib_mask]) | set(cup.index[cup_final_mask])
            return df.loc[sorted(final_idx)]
        return df[lib_mask]
    mask = df["stage"].fillna("").map(lambda v: s in _norm_text(v))
    return df[mask]


def _match_record(row: pd.Series) -> dict[str, Any]:
    return {
        "date": row["date"].strftime("%Y-%m-%d"),
        "competition": row["competition"],
        "season": int(row["season"]) if pd.notna(row["season"]) else None,
        "round": int(row["round"]) if pd.notna(row["round"]) else None,
        "stage": row["stage"] if pd.notna(row["stage"]) else None,
        "home_team": display_team(row["home_canon"]),
        "away_team": display_team(row["away_canon"]),
        "home_goals": int(row["home_goals"]),
        "away_goals": int(row["away_goals"]),
    }


def _format_match(rec: dict[str, Any]) -> str:
    label = rec["competition"]
    if rec["round"] is not None:
        label += f" Round {rec['round']}"
    elif rec["stage"]:
        label += f" {rec['stage']}"
    return (
        f"{rec['date']}: {rec['home_team']} {rec['home_goals']}-"
        f"{rec['away_goals']} {rec['away_team']} ({label})"
    )


def _result_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add winner/loser helper columns to a match frame."""
    out = df.copy()
    out["_home_win"] = out["home_goals"] > out["away_goals"]
    out["_draw"] = out["home_goals"] == out["away_goals"]
    out["_away_win"] = out["home_goals"] < out["away_goals"]
    return out


# ----------------------------------------------------------------------
# 1. Match queries
# ----------------------------------------------------------------------


def find_matches(
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    venue: str | None = None,
    round: int | None = None,  # noqa: A002 - public API mirrors the spec
    stage: str | None = None,
    limit: int = 50,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """Find matches by team(s), competition, season, date range or stage.

    ``venue`` may be "home" or "away" (default: either). ``stage``
    accepts values like "final", "semifinals", "group stage".
    """
    ds = dataset or get_dataset()
    if venue not in (None, "home", "away"):
        raise ValueError("venue must be 'home', 'away' or None")
    df = _filter_matches(
        ds.matches,
        team=team,
        opponent=opponent,
        competition=competition,
        season=season,
        date_from=date_from,
        date_to=date_to,
        venue=venue,
        round_=round,
        stage=stage,
    ).sort_values("date", ascending=False)

    total = int(len(df))
    records = [_match_record(r) for _, r in df.head(limit).iterrows()]
    lines = [_format_match(r) for r in records]
    if total > len(records):
        lines.append(f"... ({total - len(records)} more matches in dataset)")
    summary = "\n".join(lines) if lines else "No matches found."
    return {"count": total, "matches": records, "summary": summary}


# ----------------------------------------------------------------------
# 2. Team queries
# ----------------------------------------------------------------------


def head_to_head(
    team_a: str,
    team_b: str,
    competition: str | None = None,
    limit: int = 20,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """All matches between two teams plus the win/draw/loss balance."""
    ds = dataset or get_dataset()
    df = _filter_matches(
        ds.matches, team=team_a, opponent=team_b, competition=competition
    ).sort_values("date", ascending=False)

    canon_a = normalize_team(team_a)
    wins_a = int(
        (
            ((df["home_canon"] == canon_a) & (df["home_goals"] > df["away_goals"]))
            | ((df["away_canon"] == canon_a) & (df["away_goals"] > df["home_goals"]))
        ).sum()
    )
    wins_b = int(
        (
            ((df["home_canon"] != canon_a) & (df["home_goals"] > df["away_goals"]))
            | ((df["away_canon"] != canon_a) & (df["away_goals"] > df["home_goals"]))
        ).sum()
    )
    draws = int((df["home_goals"] == df["away_goals"]).sum())

    records = [_match_record(r) for _, r in df.head(limit).iterrows()]
    name_a, name_b = display_team(canon_a), display_team(normalize_team(team_b))
    lines = [f"{name_a} vs {name_b}:"]
    lines += [_format_match(r) for r in records]
    if len(df) > len(records):
        lines.append(f"... ({len(df) - len(records)} more matches in dataset)")
    lines.append(
        f"\nHead-to-head in dataset: {name_a} {wins_a} wins, "
        f"{name_b} {wins_b} wins, {draws} draws"
    )
    return {
        "team_a": name_a,
        "team_b": name_b,
        "matches_played": int(len(df)),
        "team_a_wins": wins_a,
        "team_b_wins": wins_b,
        "draws": draws,
        "matches": records,
        "summary": "\n".join(lines) if len(df) else f"No matches between {name_a} and {name_b} found.",
    }


def team_statistics(
    team: str,
    season: int | None = None,
    competition: str | None = None,
    venue: str | None = None,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """Win/draw/loss record and goals for a team (optionally filtered)."""
    ds = dataset or get_dataset()
    if venue not in (None, "home", "away"):
        raise ValueError("venue must be 'home', 'away' or None")
    df = _filter_matches(
        ds.matches, team=team, season=season, competition=competition, venue=venue
    )
    canon = normalize_team(team)
    name = display_team(canon)

    at_home = df["home_canon"] == canon
    goals_for = int(
        df.loc[at_home, "home_goals"].sum() + df.loc[~at_home, "away_goals"].sum()
    )
    goals_against = int(
        df.loc[at_home, "away_goals"].sum() + df.loc[~at_home, "home_goals"].sum()
    )
    wins = int(
        (
            (at_home & (df["home_goals"] > df["away_goals"]))
            | (~at_home & (df["away_goals"] > df["home_goals"]))
        ).sum()
    )
    draws = int((df["home_goals"] == df["away_goals"]).sum())
    played = int(len(df))
    losses = played - wins - draws
    win_rate = round(100.0 * wins / played, 1) if played else 0.0

    scope = []
    if venue:
        scope.append(venue)
    if season:
        scope.append(str(season))
    if competition:
        scope.append(resolve_competition(competition, ds.matches))
    label = f" ({' '.join(scope)})" if scope else ""
    summary = (
        f"{name}{label}:\n"
        f"- Matches: {played}\n"
        f"- Wins: {wins}, Draws: {draws}, Losses: {losses}\n"
        f"- Goals For: {goals_for}, Goals Against: {goals_against}\n"
        f"- Win rate: {win_rate}%"
    )
    return {
        "team": name,
        "season": season,
        "competition": resolve_competition(competition, ds.matches) if competition else None,
        "venue": venue,
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "win_rate_pct": win_rate,
        "summary": summary,
    }


# ----------------------------------------------------------------------
# 3. Player queries
# ----------------------------------------------------------------------

_POSITION_GROUPS = {
    "goalkeeper": {"GK"},
    "defender": {"LB", "RB", "CB", "LCB", "RCB", "LWB", "RWB"},
    "midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
}

_PLAYER_COLUMNS = ["Name", "Age", "Nationality", "Overall", "Potential", "Club", "Position"]


def _player_record(row: pd.Series) -> dict[str, Any]:
    return {
        "name": row["Name"],
        "age": int(row["Age"]) if pd.notna(row["Age"]) else None,
        "nationality": row["Nationality"],
        "overall": int(row["Overall"]) if pd.notna(row["Overall"]) else None,
        "potential": int(row["Potential"]) if pd.notna(row["Potential"]) else None,
        "club": row["Club"] if pd.notna(row["Club"]) else None,
        "position": row["Position"] if pd.notna(row["Position"]) else None,
    }


def _filter_players(
    players: pd.DataFrame,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
) -> pd.DataFrame:
    df = players
    if name:
        q = _norm_text(name)
        df = df[df["name_norm"].str.contains(q, na=False, regex=False)]
    if nationality:
        q = _norm_text(nationality)
        df = df[df["Nationality"].fillna("").map(_norm_text) == q]
    if club:
        canon = normalize_team(club)
        df = df[df["club_canon"] == canon]
    if position:
        p = position.strip().upper()
        group = _POSITION_GROUPS.get(_norm_text(position))
        if group:
            df = df[df["Position"].isin(sorted(group))]
        else:
            df = df[df["Position"].fillna("").str.upper() == p]
    if min_overall is not None:
        df = df[df["Overall"] >= int(min_overall)]
    return df


def search_players(
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 20,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """Search FIFA players by name, nationality, club, position or rating.

    ``position`` accepts a specific code ("ST", "CDM") or a group
    ("forward", "midfielder", "defender", "goalkeeper").
    """
    ds = dataset or get_dataset()
    df = _filter_players(
        ds.players,
        name=name,
        nationality=nationality,
        club=club,
        position=position,
        min_overall=min_overall,
    ).sort_values("Overall", ascending=False)
    total = int(len(df))
    records = [_player_record(r) for _, r in df.head(limit).iterrows()]
    lines = [
        f"{p['name']} - Overall: {p['overall']}, Position: {p['position']}, Club: {p['club']}"
        for p in records
    ]
    return {
        "count": total,
        "players": records,
        "summary": "\n".join(lines) if lines else "No players found.",
    }


def top_players(
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    limit: int = 10,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """Highest-rated players, optionally filtered (e.g. Brazilian players)."""
    return search_players(
        nationality=nationality,
        club=club,
        position=position,
        limit=limit,
        dataset=dataset,
    )


def players_by_club(
    nationality: str | None = None,
    limit: int = 20,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """Player count and average rating per club (e.g. Brazilians per club)."""
    ds = dataset or get_dataset()
    df = _filter_players(ds.players, nationality=nationality)
    df = df[df["Club"].notna()]
    grouped = (
        df.groupby("Club")["Overall"]
        .agg(players="size", avg_overall="mean")
        .sort_values(["players", "avg_overall"], ascending=False)
        .head(limit)
    )
    clubs = [
        {"club": club, "players": int(r["players"]), "avg_overall": round(float(r["avg_overall"]), 1)}
        for club, r in grouped.iterrows()
    ]
    scope = f"{nationality} players" if nationality else "Players"
    lines = [f"- {c['club']}: {c['players']} players (avg rating: {c['avg_overall']})" for c in clubs]
    return {
        "nationality": nationality,
        "clubs": clubs,
        "summary": f"{scope} by club:\n" + "\n".join(lines) if lines else "No players found.",
    }


# ----------------------------------------------------------------------
# 4. Competition queries
# ----------------------------------------------------------------------


def standings(
    season: int,
    competition: str = BRASILEIRAO_A,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """League table calculated from match results (3/1/0 points)."""
    ds = dataset or get_dataset()
    comp = resolve_competition(competition, ds.matches)
    df = _filter_matches(ds.matches, competition=comp, season=season)
    if df.empty:
        raise ValueError(f"no matches found for {comp} season {season}")

    stats: dict[str, dict[str, int]] = {}

    def _row(team: str) -> dict[str, int]:
        return stats.setdefault(
            team, {"played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0, "points": 0}
        )

    for r in df.itertuples():
        home, away = _row(r.home_canon), _row(r.away_canon)
        hg, ag = int(r.home_goals), int(r.away_goals)
        home["played"] += 1
        away["played"] += 1
        home["gf"] += hg
        home["ga"] += ag
        away["gf"] += ag
        away["ga"] += hg
        if hg > ag:
            home["wins"] += 1
            home["points"] += 3
            away["losses"] += 1
        elif hg < ag:
            away["wins"] += 1
            away["points"] += 3
            home["losses"] += 1
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1

    order = sorted(
        stats.items(),
        key=lambda kv: (
            -kv[1]["points"],
            -kv[1]["wins"],
            -(kv[1]["gf"] - kv[1]["ga"]),
            -kv[1]["gf"],
            kv[0],
        ),
    )
    table = []
    for pos, (canon, s) in enumerate(order, start=1):
        table.append(
            {
                "position": pos,
                "team": display_team(canon),
                "played": s["played"],
                "wins": s["wins"],
                "draws": s["draws"],
                "losses": s["losses"],
                "goals_for": s["gf"],
                "goals_against": s["ga"],
                "goal_difference": s["gf"] - s["ga"],
                "points": s["points"],
            }
        )

    lines = [f"{season} {comp} standings (calculated from {len(df)} matches):"]
    for i, t in enumerate(table):
        suffix = " - Champion" if i == 0 else ""
        lines.append(
            f"{t['position']}. {t['team']} - {t['points']} pts "
            f"({t['wins']}W, {t['draws']}D, {t['losses']}L){suffix}"
        )
    return {
        "season": int(season),
        "competition": comp,
        "matches_counted": int(len(df)),
        "champion": table[0]["team"],
        "table": table,
        "summary": "\n".join(lines),
    }


def list_competitions(dataset: Dataset | None = None) -> dict[str, Any]:
    """All competitions in the dataset with match counts and season range."""
    ds = dataset or get_dataset()
    comps = []
    for comp, g in ds.matches.groupby("competition"):
        seasons = sorted(int(s) for s in g["season"].dropna().unique())
        comps.append(
            {
                "competition": comp,
                "matches": int(len(g)),
                "seasons": seasons,
                "season_range": [seasons[0], seasons[-1]] if seasons else None,
            }
        )
    comps.sort(key=lambda c: c["competition"])
    return {"competitions": comps, "count": len(comps)}


def list_teams(
    competition: str | None = None,
    season: int | None = None,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """All distinct team names (canonical, display form)."""
    ds = dataset or get_dataset()
    df = _filter_matches(ds.matches, competition=competition, season=season)
    canons = sorted(set(df["home_canon"]) | set(df["away_canon"]))
    teams = [display_team(c) for c in canons]
    return {"count": len(teams), "teams": teams}


# ----------------------------------------------------------------------
# 5. Statistical analysis
# ----------------------------------------------------------------------


def biggest_wins(
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """Largest goal-margin victories in the dataset."""
    ds = dataset or get_dataset()
    df = _filter_matches(ds.matches, competition=competition, season=season).copy()
    df["_margin"] = (df["home_goals"] - df["away_goals"]).abs()
    df["_total"] = df["home_goals"] + df["away_goals"]
    df = df.sort_values(["_margin", "_total", "date"], ascending=[False, False, True])
    top = df.head(limit)
    records = []
    for _, r in top.iterrows():
        rec = _match_record(r)
        rec["margin"] = int(r["_margin"])
        records.append(rec)
    scope = f" ({competition})" if competition else ""
    lines = [f"Biggest victories{scope}:"]
    for i, rec in enumerate(records, start=1):
        lines.append(f"{i}. {_format_match(rec)}")
    return {"count": int(len(df)), "results": records, "summary": "\n".join(lines)}


def competition_overview(
    competition: str | None = None,
    season: int | None = None,
    dataset: Dataset | None = None,
) -> dict[str, Any]:
    """Aggregate stats: averages, home/away win rates, draws."""
    ds = dataset or get_dataset()
    comp = resolve_competition(competition, ds.matches) if competition else None
    df = _result_columns(_filter_matches(ds.matches, competition=comp, season=season))
    played = int(len(df))
    if played == 0:
        raise ValueError("no matches found for the given filters")
    total_goals = int(df["home_goals"].sum() + df["away_goals"].sum())
    home_wins = int(df["_home_win"].sum())
    draws = int(df["_draw"].sum())
    away_wins = int(df["_away_win"].sum())
    result = {
        "competition": comp,
        "season": season,
        "matches": played,
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / played, 2),
        "home_win_pct": round(100.0 * home_wins / played, 1),
        "draw_pct": round(100.0 * draws / played, 1),
        "away_win_pct": round(100.0 * away_wins / played, 1),
    }
    label = comp or "all competitions"
    if season:
        label += f" {season}"
    result["summary"] = (
        f"Overview - {label}:\n"
        f"Matches: {played}\n"
        f"Average goals per match: {result['avg_goals_per_match']}\n"
        f"Home win rate: {result['home_win_pct']}%\n"
        f"Draw rate: {result['draw_pct']}%\n"
        f"Away win rate: {result['away_win_pct']}%"
    )
    return result


def team_competitions(team: str, dataset: Dataset | None = None) -> dict[str, Any]:
    """Which competitions a team appears in, with match counts."""
    ds = dataset or get_dataset()
    df = _filter_matches(ds.matches, team=team)
    name = display_team(normalize_team(team))
    comps = [
        {"competition": comp, "matches": int(len(g))}
        for comp, g in df.groupby("competition")
    ]
    comps.sort(key=lambda c: c["competition"])
    return {"team": name, "competitions": comps, "count": len(comps)}
