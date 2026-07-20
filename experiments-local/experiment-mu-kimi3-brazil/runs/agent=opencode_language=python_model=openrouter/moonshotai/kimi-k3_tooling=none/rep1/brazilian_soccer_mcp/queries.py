"""Query engine over the loaded datasets.

All functions are pure: they take a :class:`~brazilian_soccer_mcp.data.KnowledgeBase`
plus filter arguments and return plain JSON-serializable dictionaries.  The
MCP server layer wraps these and renders human-readable text.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from .data import BRASILEIRAO_A, KnowledgeBase, get_kb
from .normalization import parse_date, team_key, text_key

__all__ = [
    "TeamNotFoundError",
    "find_matches",
    "head_to_head",
    "team_stats",
    "standings",
    "search_players",
    "club_summary",
    "biggest_wins",
    "competition_stats",
    "list_competitions",
    "list_teams",
    "dataset_summary",
    "resolve_team",
]

POSITION_GROUPS: dict[str, set[str]] = {
    "forward": {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
    "midfielder": {
        "CAM", "CDM", "CM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM",
    },
    "defender": {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
    "goalkeeper": {"GK"},
}


class TeamNotFoundError(ValueError):
    """Raised when a team name cannot be resolved against the datasets."""

    def __init__(self, query: str, suggestions: list[str]):
        self.query = query
        self.suggestions = suggestions
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"Unknown team: {query!r}.{hint}")


def _kb(kb: KnowledgeBase | None) -> KnowledgeBase:
    return kb if kb is not None else get_kb()


def _season_int(season: int | str | None) -> int | None:
    if season is None or season == "":
        return None
    return int(season)


def _as_date(value: str | date | datetime | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError(f"Unparseable date: {value!r}")
    return parsed


def _match_to_dict(row: pd.Series) -> dict[str, Any]:
    return {
        "date": row["date"].strftime("%Y-%m-%d"),
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "home_goals": int(row["home_goals"]),
        "away_goals": int(row["away_goals"]),
        "competition": row["competition"],
        "season": int(row["season"]) if pd.notna(row["season"]) else None,
        "stage": row["stage"] or None,
    }


def _competition_mask(df: pd.DataFrame, competition: str | None) -> pd.Series:
    """Accent-insensitive substring match on the canonical competition label."""
    if not competition:
        return pd.Series(True, index=df.index)
    needle = text_key(competition)
    return df["competition"].map(lambda c: needle in text_key(c))


def resolve_team(kb: KnowledgeBase | None, name: str) -> tuple[str, str]:
    """Resolve a user-supplied team name to ``(key, display_name)``.

    Raises :class:`TeamNotFoundError` with close-match suggestions when the
    team does not appear in any match record.
    """
    base = _kb(kb)
    key = team_key(name)
    matches = base.matches
    known = matches[matches["home_key"].eq(key) | matches["away_key"].eq(key)]
    if not known.empty:
        displays = pd.concat([known["home_team"], known["away_team"]])
        displays = displays[displays.map(team_key) == key]
        display = displays.mode().iat[0] if not displays.empty else name
        return key, display
    needle = text_key(name)
    all_names = sorted(set(matches["home_team"]) | set(matches["away_team"]))
    suggestions = [n for n in all_names if needle and needle in text_key(n)][:5]
    if not suggestions:
        suggestions = [n for n in all_names if team_key(n).startswith(key[:4])][:5]
    raise TeamNotFoundError(name, suggestions)


def _filter_matches(
    base: KnowledgeBase,
    *,
    competition: str | None = None,
    season: int | str | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
) -> pd.DataFrame:
    df = base.matches
    mask = _competition_mask(df, competition)
    year = _season_int(season)
    if year is not None:
        mask &= df["season"].eq(year)
    start = _as_date(date_from)
    if start is not None:
        mask &= df["date"].dt.date >= start
    end = _as_date(date_to)
    if end is not None:
        mask &= df["date"].dt.date <= end
    return df[mask]


def find_matches(
    kb: KnowledgeBase | None = None,
    *,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | str | None = None,
    stage: str | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Find matches by team(s), competition, season, stage and/or date range."""
    base = _kb(kb)
    df = _filter_matches(
        base, competition=competition, season=season, date_from=date_from, date_to=date_to
    )
    if stage:
        # Exact match (case/accent-insensitive): "Final" must not also
        # return "Semifinals"/"Quarterfinals".
        needle = text_key(stage)
        df = df[df["stage"].map(lambda s: needle == text_key(s))]
    team_display = None
    if team:
        key, team_display = resolve_team(base, team)
        df = df[df["home_key"].eq(key) | df["away_key"].eq(key)]
    if opponent:
        okey, _ = resolve_team(base, opponent)
        df = df[df["home_key"].eq(okey) | df["away_key"].eq(okey)]
    df = df.sort_values("date", ascending=False, kind="stable")
    return {
        "team": team_display,
        "total": int(len(df)),
        "matches": [_match_to_dict(row) for _, row in df.head(limit).iterrows()],
    }


def head_to_head(
    team_a: str,
    team_b: str,
    kb: KnowledgeBase | None = None,
    *,
    competition: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Full head-to-head history between two teams (either venue)."""
    base = _kb(kb)
    key_a, display_a = resolve_team(base, team_a)
    key_b, display_b = resolve_team(base, team_b)
    df = base.matches
    df = df[
        ((df["home_key"].eq(key_a)) & (df["away_key"].eq(key_b)))
        | ((df["home_key"].eq(key_b)) & (df["away_key"].eq(key_a)))
    ]
    df = df[_competition_mask(df, competition)].sort_values(
        "date", ascending=False, kind="stable"
    )
    wins_a = int(
        (
            ((df["home_key"] == key_a) & (df["home_goals"] > df["away_goals"]))
            | ((df["away_key"] == key_a) & (df["away_goals"] > df["home_goals"]))
        ).sum()
    )
    wins_b = int(
        (
            ((df["home_key"] == key_b) & (df["home_goals"] > df["away_goals"]))
            | ((df["away_key"] == key_b) & (df["away_goals"] > df["home_goals"]))
        ).sum()
    )
    goals_a = int(
        df.loc[df["home_key"] == key_a, "home_goals"].sum()
        + df.loc[df["away_key"] == key_a, "away_goals"].sum()
    )
    goals_b = int(
        df.loc[df["home_key"] == key_b, "home_goals"].sum()
        + df.loc[df["away_key"] == key_b, "away_goals"].sum()
    )
    return {
        "team_a": display_a,
        "team_b": display_b,
        "total": int(len(df)),
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": int(len(df)) - wins_a - wins_b,
        "goals_a": goals_a,
        "goals_b": goals_b,
        "matches": [_match_to_dict(row) for _, row in df.head(limit).iterrows()],
    }


def team_stats(
    team: str,
    kb: KnowledgeBase | None = None,
    *,
    season: int | str | None = None,
    competition: str | None = None,
    venue: str = "all",
) -> dict[str, Any]:
    """Win/draw/loss record and goals for a team.

    ``venue`` is one of ``"all"``, ``"home"`` or ``"away"``.
    """
    base = _kb(kb)
    key, display = resolve_team(base, team)
    df = _filter_matches(base, competition=competition, season=season)
    venue = (venue or "all").lower()
    if venue == "home":
        df = df[df["home_key"].eq(key)]
    elif venue == "away":
        df = df[df["away_key"].eq(key)]
    else:
        venue = "all"
        df = df[df["home_key"].eq(key) | df["away_key"].eq(key)]

    home_rows = df[df["home_key"] == key]
    away_rows = df[df["away_key"] == key]
    wins = int(
        (home_rows["home_goals"] > home_rows["away_goals"]).sum()
        + (away_rows["away_goals"] > away_rows["home_goals"]).sum()
    )
    losses = int(
        (home_rows["home_goals"] < home_rows["away_goals"]).sum()
        + (away_rows["away_goals"] < away_rows["home_goals"]).sum()
    )
    played = int(len(df))
    goals_for = int(home_rows["home_goals"].sum() + away_rows["away_goals"].sum())
    goals_against = int(home_rows["away_goals"].sum() + away_rows["home_goals"].sum())
    by_competition = {
        comp: int(count) for comp, count in df.groupby("competition").size().items()
    }
    return {
        "team": display,
        "season": _season_int(season),
        "competition": competition,
        "venue": venue,
        "matches": played,
        "wins": wins,
        "draws": played - wins - losses,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "win_rate": round(100.0 * wins / played, 1) if played else 0.0,
        "by_competition": by_competition,
    }


def standings(
    season: int | str,
    kb: KnowledgeBase | None = None,
    *,
    competition: str = BRASILEIRAO_A,
) -> dict[str, Any]:
    """League table calculated from match results (3/1/0 points)."""
    base = _kb(kb)
    df = _filter_matches(base, competition=competition, season=season)
    if df.empty:
        return {"competition": competition, "season": _season_int(season), "table": []}

    table: dict[str, dict[str, Any]] = {}

    def slot(key: str, name: str) -> dict[str, Any]:
        return table.setdefault(
            key,
            {"team": name, "played": 0, "wins": 0, "draws": 0, "losses": 0,
             "goals_for": 0, "goals_against": 0, "points": 0},
        )

    for row in df.itertuples():
        home = slot(row.home_key, row.home_team)
        away = slot(row.away_key, row.away_team)
        hg, ag = int(row.home_goals), int(row.away_goals)
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += hg
        home["goals_against"] += ag
        away["goals_for"] += ag
        away["goals_against"] += hg
        if hg > ag:
            home["wins"] += 1
            away["losses"] += 1
            home["points"] += 3
        elif hg < ag:
            away["wins"] += 1
            home["losses"] += 1
            away["points"] += 3
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1

    rows = list(table.values())
    # Brazilian tie-break order: points, wins, goal difference, goals for.
    rows.sort(
        key=lambda r: (
            r["points"],
            r["wins"],
            r["goals_for"] - r["goals_against"],
            r["goals_for"],
        ),
        reverse=True,
    )
    size = len(rows)
    for pos, row in enumerate(rows, start=1):
        row["position"] = pos
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
        row["champion"] = pos == 1
        row["relegated"] = size >= 8 and pos > size - 4
    return {
        "competition": competition,
        "season": _season_int(season),
        "table": rows,
    }


def _player_to_dict(row: pd.Series) -> dict[str, Any]:
    return {
        "id": int(row["ID"]) if pd.notna(row["ID"]) else None,
        "name": row["Name"],
        "age": int(row["Age"]) if pd.notna(row["Age"]) else None,
        "nationality": row["Nationality"],
        "overall": int(row["Overall"]) if pd.notna(row["Overall"]) else None,
        "potential": int(row["Potential"]) if pd.notna(row["Potential"]) else None,
        "club": row["Club"] if pd.notna(row["Club"]) else None,
        "position": row["Position"] if pd.notna(row["Position"]) else None,
    }


def search_players(
    kb: KnowledgeBase | None = None,
    *,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    position_group: str | None = None,
    min_overall: int | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search FIFA players by name/nationality/club/position/rating."""
    base = _kb(kb)
    df = base.players
    mask = pd.Series(True, index=df.index)
    if name:
        needle = text_key(name)
        mask &= df["Name"].map(lambda v: needle in text_key(v))
    if nationality:
        needle = text_key(nationality)
        mask &= df["Nationality"].map(lambda v: needle in text_key(v))
    if club:
        needle = text_key(club)
        mask &= df["Club"].map(lambda v: pd.notna(v) and needle in text_key(v))
    if position:
        mask &= df["Position"].map(
            lambda v: pd.notna(v) and str(v).upper() == position.upper()
        )
    if position_group:
        group = POSITION_GROUPS.get(position_group.lower())
        if group is None:
            raise ValueError(
                f"Unknown position group {position_group!r}; "
                f"choose from {sorted(POSITION_GROUPS)}"
            )
        mask &= df["Position"].isin(group)
    if min_overall is not None:
        mask &= df["Overall"].fillna(0) >= int(min_overall)
    result = df[mask].sort_values(["Overall", "Name"], ascending=[False, True])
    return {
        "total": int(len(result)),
        "players": [_player_to_dict(row) for _, row in result.head(limit).iterrows()],
    }


def club_summary(
    club: str,
    kb: KnowledgeBase | None = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Player roster overview for a club (FIFA dataset)."""
    base = _kb(kb)
    needle = text_key(club)
    df = base.players
    roster = df[df["Club"].map(lambda v: pd.notna(v) and needle in text_key(v))]
    if roster.empty:
        return {"club": club, "matched_clubs": [], "player_count": 0,
                "avg_overall": None, "players": []}
    matched = sorted(roster["Club"].dropna().unique().tolist())
    top = roster.sort_values("Overall", ascending=False)
    return {
        "club": club,
        "matched_clubs": matched,
        "player_count": int(len(roster)),
        "avg_overall": round(float(roster["Overall"].mean()), 1),
        "avg_age": round(float(roster["Age"].mean()), 1),
        "brazilian_count": int((roster["Nationality"] == "Brazil").sum()),
        "players": [_player_to_dict(row) for _, row in top.head(limit).iterrows()],
    }


def biggest_wins(
    kb: KnowledgeBase | None = None,
    *,
    competition: str | None = None,
    season: int | str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Largest victory margins in the (optionally filtered) dataset."""
    base = _kb(kb)
    df = _filter_matches(base, competition=competition, season=season).copy()
    df["margin"] = (df["home_goals"] - df["away_goals"]).abs()
    df["total_goals"] = df["home_goals"] + df["away_goals"]
    df = df[df["margin"] > 0].sort_values(
        ["margin", "total_goals", "date"], ascending=[False, False, False], kind="stable"
    )
    wins = []
    for row in df.head(limit).itertuples():
        home_won = row.home_goals > row.away_goals
        wins.append(
            {
                "date": row.date.strftime("%Y-%m-%d"),
                "winner": row.home_team if home_won else row.away_team,
                "loser": row.away_team if home_won else row.home_team,
                "score": f"{int(row.home_goals)}-{int(row.away_goals)}",
                "margin": int(row.margin),
                "competition": row.competition,
                "season": int(row.season) if pd.notna(row.season) else None,
            }
        )
    return {"total": int(len(df)), "biggest_wins": wins}


def competition_stats(
    kb: KnowledgeBase | None = None,
    *,
    competition: str | None = None,
    season: int | str | None = None,
) -> dict[str, Any]:
    """Aggregated scoring / home-advantage statistics."""
    base = _kb(kb)
    df = _filter_matches(base, competition=competition, season=season)
    played = int(len(df))
    if played == 0:
        return {"competition": competition, "season": _season_int(season),
                "matches": 0}
    total_goals = int(df["home_goals"].sum() + df["away_goals"].sum())
    home_wins = int((df["home_goals"] > df["away_goals"]).sum())
    away_wins = int((df["home_goals"] < df["away_goals"]).sum())
    draws = played - home_wins - away_wins
    per_season = [
        {
            "season": int(year),
            "matches": int(len(group)),
            "avg_goals": round(
                float(group["home_goals"].sum() + group["away_goals"].sum())
                / len(group),
                2,
            ),
        }
        for year, group in df.groupby("season")
    ]
    return {
        "competition": competition,
        "season": _season_int(season),
        "matches": played,
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / played, 2),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_rate": round(100.0 * home_wins / played, 1),
        "draw_rate": round(100.0 * draws / played, 1),
        "away_win_rate": round(100.0 * away_wins / played, 1),
        "per_season": sorted(per_season, key=lambda r: r["season"]),
    }


def list_competitions(kb: KnowledgeBase | None = None) -> dict[str, Any]:
    """Competitions present in the data with coverage info."""
    base = _kb(kb)
    out = []
    for comp, group in base.matches.groupby("competition"):
        seasons = group["season"].dropna()
        out.append(
            {
                "competition": comp,
                "matches": int(len(group)),
                "seasons": [int(seasons.min()), int(seasons.max())] if not seasons.empty else None,
                "teams": int(
                    pd.concat([group["home_key"], group["away_key"]]).nunique()
                ),
            }
        )
    return {"competitions": sorted(out, key=lambda r: r["competition"])}


def list_teams(kb: KnowledgeBase | None = None, *, filter: str | None = None) -> dict[str, Any]:
    """All known team display names, optionally substring-filtered."""
    base = _kb(kb)
    names = sorted(set(base.matches["home_team"]) | set(base.matches["away_team"]))
    if filter:
        needle = text_key(filter)
        names = [n for n in names if needle in text_key(n)]
    return {"total": len(names), "teams": names}


def dataset_summary(kb: KnowledgeBase | None = None) -> dict[str, Any]:
    """Row counts per source file plus deduplication totals."""
    base = _kb(kb)
    dates = base.matches["date"]
    return {
        "files": base.load_report,
        "total_matches": int(len(base.matches)),
        "total_players": int(len(base.players)),
        "competitions": sorted(base.matches["competition"].unique().tolist()),
        "date_range": [
            dates.min().strftime("%Y-%m-%d"),
            dates.max().strftime("%Y-%m-%d"),
        ],
    }
