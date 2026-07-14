"""
Context
=======
Module: brazilian_soccer_mcp.queries

Pure query/aggregation layer over a `KnowledgeBase`. The MCP server (server.py)
is a thin adapter that calls these functions and formats their dict results;
keeping the logic here means it is directly unit-testable without the protocol
in the way (see the BDD tests).

Every public function:
  * accepts a `KnowledgeBase` plus plain query parameters,
  * matches team/player names via the canonical keys precomputed at load time
    (`normalize.names_match` semantics, vectorised here for speed),
  * returns JSON-serialisable Python (dicts/lists/primitives) - never raw
    DataFrames - so the server can hand results straight to an LLM.

Design choices worth knowing:
  * Standings/records exclude matches with missing goals (the 24 NA rows),
    because you cannot award points for a result you don't have.
  * Head-to-head and team records are computed from the home/away perspective
    in one pass over the (already small) filtered frame.
  * "Brasileirão" as a competition filter means Série A specifically - that is
    what users mean by the league title; Série B/C are addressable by their
    full names.
"""

from __future__ import annotations

import pandas as pd

from .data_loader import SERIE_A, KnowledgeBase
from .normalize import canonical

# User-facing competition aliases -> stored competition label.
_COMP_ALIASES = {
    "brasileirao": SERIE_A,
    "brasileirao serie a": SERIE_A,
    "serie a": SERIE_A,
    "serie b": "Brasileirão Série B",
    "serie c": "Brasileirão Série C",
    "copa do brasil": "Copa do Brasil",
    "brazilian cup": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
    "copa libertadores": "Copa Libertadores",
}


def resolve_competition(name: str | None) -> str | None:
    """Map a free-text competition name to a stored label, or None if blank.

    Raises ValueError on an unrecognised non-empty value so callers can report
    the supported set rather than silently returning everything.
    """
    if name is None or str(name).strip() == "":
        return None
    key = canonical(name)
    if key in _COMP_ALIASES:
        return _COMP_ALIASES[key]
    # Allow passing the exact stored label through unchanged.
    raise ValueError(
        f"Unknown competition '{name}'. Known: Brasileirão Série A/B/C, "
        "Copa do Brasil, Copa Libertadores."
    )


def _team_mask(df: pd.DataFrame, column: str, team: str) -> pd.Series:
    """Vectorised canonical substring match against a *_canon column."""
    key = canonical(team)
    col = df[column].fillna("")
    if not key:
        return pd.Series(False, index=df.index)
    # Either side may contain the other (see normalize.names_match): exact
    # match, stored key contains the query, or query contains the stored key.
    contains_key = col.str.contains(key, regex=False)
    key_contains = col.apply(lambda c: bool(c) and c in key)
    return col.eq(key) | contains_key | key_contains


def _apply_filters(
    kb: KnowledgeBase,
    competition: str | None = None,
    season: int | None = None,
) -> pd.DataFrame:
    df = kb.matches
    if competition is not None:
        df = df[df["competition"] == resolve_competition(competition)]
    if season is not None:
        df = df[df["season"] == int(season)]
    return df


def _match_record(row: pd.Series) -> dict:
    """Serialise one match row to a compact, display-ready dict."""
    d = row["match_date"]
    hg = row["home_goal"]
    ag = row["away_goal"]
    return {
        "date": d.isoformat() if d is not None and not pd.isna(d) else None,
        "competition": row["competition"],
        "season": int(row["season"]) if pd.notna(row["season"]) else None,
        "round": None if pd.isna(row["round"]) else str(row["round"]),
        "stage": None if pd.isna(row["stage"]) else str(row["stage"]),
        "home": row["home"],
        "away": row["away"],
        "home_goal": int(hg) if pd.notna(hg) else None,
        "away_goal": int(ag) if pd.notna(ag) else None,
        "score": (
            f"{int(hg)}-{int(ag)}" if pd.notna(hg) and pd.notna(ag) else None
        ),
        "source": row["source"],
    }


def _sort_by_date(df: pd.DataFrame, ascending: bool = True) -> pd.DataFrame:
    # NaT dates sort last regardless of direction so dated rows lead.
    return df.sort_values("match_date", ascending=ascending, na_position="last")


# --------------------------------------------------------------------------- #
# 1. Match queries
# --------------------------------------------------------------------------- #
def find_matches(
    kb: KnowledgeBase,
    team: str | None = None,
    opponent: str | None = None,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "either",
    limit: int = 50,
) -> dict:
    """Find matches by team(s), competition, season, and home/away venue.

    venue: 'home' | 'away' | 'either' (interpreted relative to `team`).
    When `opponent` is given, returns only matches between the two teams
    (in either ground). Results are date-sorted (most recent first).
    """
    df = _apply_filters(kb, competition, season)

    if team:
        home_hit = _team_mask(df, "home_canon", team)
        away_hit = _team_mask(df, "away_canon", team)
        if venue == "home":
            df = df[home_hit]
        elif venue == "away":
            df = df[away_hit]
        else:
            df = df[home_hit | away_hit]

    if opponent:
        opp_home = _team_mask(df, "home_canon", opponent)
        opp_away = _team_mask(df, "away_canon", opponent)
        df = df[opp_home | opp_away]

    total = len(df)
    rows = _sort_by_date(df, ascending=False).head(limit)
    return {
        "count": total,
        "returned": len(rows),
        "matches": [_match_record(r) for _, r in rows.iterrows()],
    }


# --------------------------------------------------------------------------- #
# 2. Team queries
# --------------------------------------------------------------------------- #
def _accumulate_record(df: pd.DataFrame, team: str) -> dict:
    """Compute W/D/L, goals for/against from a team's perspective.

    Matches missing goals are ignored. Operates over `df` already filtered to
    the team's matches.
    """
    home_mask = _team_mask(df, "home_canon", team)
    played = wins = draws = losses = gf = ga = 0
    for _, row in df.iterrows():
        hg, ag = row["home_goal"], row["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        is_home = bool(home_mask.loc[row.name])
        scored, conceded = (int(hg), int(ag)) if is_home else (int(ag), int(hg))
        played += 1
        gf += scored
        ga += conceded
        if scored > conceded:
            wins += 1
        elif scored < conceded:
            losses += 1
        else:
            draws += 1
    win_rate = round(100 * wins / played, 1) if played else 0.0
    return {
        "matches": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": gf,
        "goals_against": ga,
        "goal_difference": gf - ga,
        "points": wins * 3 + draws,
        "win_rate": win_rate,
    }


def team_record(
    kb: KnowledgeBase,
    team: str,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "either",
) -> dict:
    """Aggregate a team's record, optionally scoped by competition/season/venue."""
    df = _apply_filters(kb, competition, season)
    home_hit = _team_mask(df, "home_canon", team)
    away_hit = _team_mask(df, "away_canon", team)
    if venue == "home":
        scoped = df[home_hit]
    elif venue == "away":
        scoped = df[away_hit]
    else:
        scoped = df[home_hit | away_hit]

    if scoped.empty:
        return {
            "team": team,
            "found": False,
            "competition": competition,
            "season": season,
            "venue": venue,
            "record": _accumulate_record(scoped, team),
        }

    # Display name = most common stored spelling among the team's rows. Recompute
    # masks against `scoped` so indices always align with the filtered frame.
    sh = _team_mask(scoped, "home_canon", team)
    sa = _team_mask(scoped, "away_canon", team)
    names = pd.concat([scoped.loc[sh, "home"], scoped.loc[sa, "away"]])
    display = names.mode().iat[0] if not names.empty else team
    return {
        "team": display,
        "found": True,
        "competition": competition,
        "season": season,
        "venue": venue,
        "record": _accumulate_record(scoped, team),
    }


def head_to_head(
    kb: KnowledgeBase,
    team_a: str,
    team_b: str,
    competition: str | None = None,
    season: int | None = None,
) -> dict:
    """Head-to-head summary between two teams across the (filtered) data."""
    df = _apply_filters(kb, competition, season)
    a_home = _team_mask(df, "home_canon", team_a)
    a_away = _team_mask(df, "away_canon", team_a)
    b_home = _team_mask(df, "home_canon", team_b)
    b_away = _team_mask(df, "away_canon", team_b)
    h2h = df[(a_home & b_away) | (a_away & b_home)]

    a_wins = b_wins = draws = a_goals = b_goals = 0
    for _, row in h2h.iterrows():
        hg, ag = row["home_goal"], row["away_goal"]
        if pd.isna(hg) or pd.isna(ag):
            continue
        a_is_home = bool(a_home.loc[row.name])
        a_sc, b_sc = (int(hg), int(ag)) if a_is_home else (int(ag), int(hg))
        a_goals += a_sc
        b_goals += b_sc
        if a_sc > b_sc:
            a_wins += 1
        elif b_sc > a_sc:
            b_wins += 1
        else:
            draws += 1

    rows = _sort_by_date(h2h, ascending=False)
    return {
        "team_a": team_a,
        "team_b": team_b,
        "total_matches": len(h2h),
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "draws": draws,
        "team_a_goals": a_goals,
        "team_b_goals": b_goals,
        "matches": [_match_record(r) for _, r in rows.iterrows()],
    }


# --------------------------------------------------------------------------- #
# 3. Player queries
# --------------------------------------------------------------------------- #
def _player_record(row: pd.Series) -> dict:
    def g(col):
        if col not in row.index:
            return None
        v = row[col]
        return None if pd.isna(v) else v

    overall = g("Overall")
    age = g("Age")
    return {
        "id": int(g("ID")) if g("ID") is not None else None,
        "name": g("Name"),
        "age": int(age) if age is not None else None,
        "nationality": g("Nationality"),
        "overall": int(overall) if overall is not None else None,
        "potential": int(g("Potential")) if g("Potential") is not None else None,
        "club": g("Club"),
        "position": g("Position"),
    }


def find_players(
    kb: KnowledgeBase,
    name: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    position: str | None = None,
    min_overall: int | None = None,
    limit: int = 25,
) -> dict:
    """Search FIFA players by name/nationality/club/position/rating.

    All provided filters are ANDed. Results sort by Overall descending so the
    "top players" intent is the default ordering.
    """
    df = kb.players
    mask = pd.Series(True, index=df.index)
    if name:
        key = canonical(name)
        mask &= df["name_canon"].str.contains(key, regex=False)
    if nationality:
        key = canonical(nationality)
        mask &= df["nationality_canon"].eq(key) | df["nationality_canon"].str.contains(
            key, regex=False
        )
    if club:
        key = canonical(club)
        mask &= df["club_canon"].str.contains(key, regex=False)
    if position:
        pos = str(position).strip().upper()
        mask &= df["Position"].str.upper().eq(pos)
    if min_overall is not None:
        mask &= df["Overall"] >= int(min_overall)

    hits = df[mask].sort_values("Overall", ascending=False, na_position="last")
    total = len(hits)
    rows = hits.head(limit)
    return {
        "count": total,
        "returned": len(rows),
        "players": [_player_record(r) for _, r in rows.iterrows()],
    }


def players_by_club_summary(
    kb: KnowledgeBase, nationality: str | None = "Brazil", top_n: int = 10
) -> dict:
    """Group players (optionally by nationality) by club: count + avg rating.

    Answers "Brazilian players at Brazilian clubs" style asks. Clubs ordered by
    player count descending, then average rating.
    """
    df = kb.players
    if nationality:
        key = canonical(nationality)
        df = df[df["nationality_canon"].eq(key)]
    df = df[df["Club"].astype(str).str.len() > 0]
    grouped = (
        df.groupby("Club")
        .agg(players=("Name", "count"), avg_overall=("Overall", "mean"))
        .sort_values(["players", "avg_overall"], ascending=False)
        .head(top_n)
    )
    return {
        "nationality": nationality,
        "clubs": [
            {
                "club": club,
                "players": int(r["players"]),
                "avg_overall": round(float(r["avg_overall"]), 1),
            }
            for club, r in grouped.iterrows()
        ],
    }


# --------------------------------------------------------------------------- #
# 4. Competition queries
# --------------------------------------------------------------------------- #
def standings(
    kb: KnowledgeBase, competition: str, season: int, top_n: int | None = None
) -> dict:
    """Compute a league table from match results for a competition+season.

    Points = 3*W + D. Tie-break: points, goal difference, goals for. Designed
    for round-robin leagues (Série A/B/C); cup/knockout competitions produce a
    table too but it is less meaningful, so callers should prefer brackets.
    """
    comp = resolve_competition(competition)
    df = kb.matches
    df = df[(df["competition"] == comp) & (df["season"] == int(season))]
    df = df[df["home_goal"].notna() & df["away_goal"].notna()]

    # Group by canonical key (a club has several display spellings across
    # files); pick the modal display name for presentation.
    table: dict[str, dict] = {}
    display_counts: dict[str, dict[str, int]] = {}

    def slot(canon: str, display: str) -> dict:
        names = display_counts.setdefault(canon, {})
        names[display] = names.get(display, 0) + 1
        return table.setdefault(
            canon,
            {
                "matches": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
            },
        )

    for _, row in df.iterrows():
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        h = slot(row["home_canon"], row["home"])
        a = slot(row["away_canon"], row["away"])
        h["matches"] += 1
        a["matches"] += 1
        h["goals_for"] += hg
        h["goals_against"] += ag
        a["goals_for"] += ag
        a["goals_against"] += hg
        if hg > ag:
            h["wins"] += 1
            a["losses"] += 1
        elif ag > hg:
            a["wins"] += 1
            h["losses"] += 1
        else:
            h["draws"] += 1
            a["draws"] += 1

    rows = []
    for canon, entry in table.items():
        entry["team"] = max(display_counts[canon].items(), key=lambda kv: kv[1])[0]
        entry["points"] = entry["wins"] * 3 + entry["draws"]
        entry["goal_difference"] = entry["goals_for"] - entry["goals_against"]
        rows.append(entry)
    rows.sort(
        key=lambda e: (e["points"], e["goal_difference"], e["goals_for"]),
        reverse=True,
    )
    for i, entry in enumerate(rows, start=1):
        entry["position"] = i
    if top_n:
        rows = rows[:top_n]
    return {
        "competition": comp,
        "season": int(season),
        "teams": len(table),
        "standings": rows,
        "champion": rows[0]["team"] if rows else None,
    }


# --------------------------------------------------------------------------- #
# 5. Statistical analysis
# --------------------------------------------------------------------------- #
def competition_stats(
    kb: KnowledgeBase, competition: str | None = None, season: int | None = None
) -> dict:
    """Aggregate goals-per-match, home/away/draw win rates over a filtered set."""
    df = _apply_filters(kb, competition, season)
    df = df[df["home_goal"].notna() & df["away_goal"].notna()]
    n = len(df)
    if n == 0:
        return {
            "competition": competition,
            "season": season,
            "matches": 0,
        }
    hg = df["home_goal"].astype("int64")
    ag = df["away_goal"].astype("int64")
    total_goals = int((hg + ag).sum())
    home_wins = int((hg > ag).sum())
    away_wins = int((ag > hg).sum())
    draws = int((hg == ag).sum())
    return {
        "competition": competition,
        "season": season,
        "matches": n,
        "total_goals": total_goals,
        "avg_goals_per_match": round(total_goals / n, 2),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "home_win_rate": round(100 * home_wins / n, 1),
        "away_win_rate": round(100 * away_wins / n, 1),
        "draw_rate": round(100 * draws / n, 1),
    }


def biggest_wins(
    kb: KnowledgeBase,
    competition: str | None = None,
    season: int | None = None,
    limit: int = 10,
) -> dict:
    """Largest goal-margin victories in the filtered set, margin descending."""
    df = _apply_filters(kb, competition, season)
    df = df[df["home_goal"].notna() & df["away_goal"].notna()].copy()
    df["margin"] = (df["home_goal"].astype("int64") - df["away_goal"].astype("int64")).abs()
    df = df.sort_values(["margin", "match_date"], ascending=[False, False]).head(limit)
    out = []
    for _, row in df.iterrows():
        rec = _match_record(row)
        rec["margin"] = int(row["margin"])
        out.append(rec)
    return {"count": len(out), "matches": out}


def best_record(
    kb: KnowledgeBase,
    competition: str | None = None,
    season: int | None = None,
    venue: str = "either",
    metric: str = "win_rate",
    min_matches: int = 5,
    limit: int = 10,
) -> dict:
    """Rank teams by a record metric (win_rate | points | wins | goal_difference).

    `venue` restricts to home/away matches for "best home/away record" asks.
    Teams with fewer than `min_matches` are excluded to avoid 100%-on-1-game
    noise.
    """
    if metric not in {"win_rate", "points", "wins", "goal_difference"}:
        raise ValueError(f"Unknown metric '{metric}'.")
    df = _apply_filters(kb, competition, season)
    df = df[df["home_goal"].notna() & df["away_goal"].notna()]

    agg: dict[str, dict] = {}
    display_counts: dict[str, dict[str, int]] = {}

    def slot(canon: str, display: str) -> dict:
        names = display_counts.setdefault(canon, {})
        names[display] = names.get(display, 0) + 1
        return agg.setdefault(
            canon,
            {"matches": 0, "wins": 0, "draws": 0, "losses": 0,
             "goals_for": 0, "goals_against": 0},
        )

    for _, row in df.iterrows():
        hg, ag = int(row["home_goal"]), int(row["away_goal"])
        if venue in ("either", "home"):
            e = slot(row["home_canon"], row["home"])
            e["matches"] += 1
            e["goals_for"] += hg
            e["goals_against"] += ag
            if hg > ag:
                e["wins"] += 1
            elif ag > hg:
                e["losses"] += 1
            else:
                e["draws"] += 1
        if venue in ("either", "away"):
            e = slot(row["away_canon"], row["away"])
            e["matches"] += 1
            e["goals_for"] += ag
            e["goals_against"] += hg
            if ag > hg:
                e["wins"] += 1
            elif hg > ag:
                e["losses"] += 1
            else:
                e["draws"] += 1

    rows = []
    for canon, e in agg.items():
        if e["matches"] < min_matches:
            continue
        e["team"] = max(display_counts[canon].items(), key=lambda kv: kv[1])[0]
        e["points"] = e["wins"] * 3 + e["draws"]
        e["goal_difference"] = e["goals_for"] - e["goals_against"]
        e["win_rate"] = round(100 * e["wins"] / e["matches"], 1)
        rows.append(e)
    rows.sort(key=lambda e: (e[metric], e["matches"]), reverse=True)
    return {
        "competition": competition,
        "season": season,
        "venue": venue,
        "metric": metric,
        "teams": rows[:limit],
    }
