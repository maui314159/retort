"""Query engine powering the Brazilian Soccer MCP server.

The engine wraps a :class:`~brsl.knowledge_graph.KnowledgeGraph` and exposes a
small set of high-level, JSON-serialisable query functions grouped into the
five capability areas required by the specification:

* :func:`QueryEngine.search_matches`            - 1. Match queries
* :func:`QueryEngine.head_to_head`               - head-to-head comparison
* :func:`QueryEngine.team_stats`                 - 2. Team queries
* :func:`QueryEngine.players_at_brazilian_clubs` - 3. Player queries
* :func:`QueryEngine.search_players`
* :func:`QueryEngine.standings` / :func:`cup_bracket`
                                                - 4. Competition queries
* :func:`QueryEngine.average_goals` / :func:`home_vs_away`
* :func:`QueryEngine.biggest_victories`          - 5. Statistical analysis

All return values are plain ``dict``/``list``/``int``/``float``/``str`` so they
can be passed straight to ``json.dumps`` and surfaced through the MCP tool
layer in :mod:`brsl.server`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd

from . import data_loader as dl
from .knowledge_graph import KnowledgeGraph
from .normalization import normalize_team, team_matches

# ---------------------------------------------------------------------------
# Competition normalization helpers
# ---------------------------------------------------------------------------

# Map a logical competition bucket to the human-readable labels it covers.
BUCKET_LABELS = {
    "brasileirao": ["Brasileirao Serie A", "Brasileirao Serie A (2003-2019)",
                    "Serie A"],
    "serie_b": ["Serie B"],
    "serie_c": ["Serie C"],
    "copa_do_brasil": ["Copa do Brasil"],
    "libertadores": ["Copa Libertadores"],
}

LEAGUE_BUCKETS = {"brasileirao", "serie_b", "serie_c"}
CUP_BUCKETS = {"copa_do_brasil", "libertadores"}


@lru_cache(maxsize=None)
def normalize_competition_query(query: str | None) -> str | None:
    """Map a free-text competition name to a logical bucket.

    ``"brasileirao"``, ``"Serie A"``, ``"Campeonato Brasileiro"`` and
    ``"Brasileirão"`` all map to the ``"brasileirao"`` bucket.
    """
    if not query:
        return None
    q = str(query).strip().lower()
    if not q:
        return None
    aliases = {
        "brasileirao": ["brasileirao", "brasileirão", "serie a", "série a",
                        "campeonato brasileiro", "brasileirão serie a",
                        "serie a (2003-2019)"],
        "serie_b": ["serie b", "série b", "serie b (brasil)"],
        "serie_c": ["serie c", "série c"],
        "copa_do_brasil": ["copa do brasil", "copa do brazil",
                           "brazilian cup", "copa-do-brasil"],
        "libertadores": ["libertadores", "copa libertadores",
                         "libertadores da america",
                         "copa libertadores da america"],
    }
    for bucket, names in aliases.items():
        for name in names:
            if q == name:
                return bucket
    # Match against the canonical labels found in the data too.
    norm = normalize_team(q).key.replace(" ", "_")
    for bucket in aliases:
        if norm and norm in bucket:
            return bucket
    # Fall back to substring match on the raw query.
    for bucket, names in aliases.items():
        if any(name in q for name in names):
            return bucket
    return None


def preferred_source(bucket: str, season: int | None) -> str:
    """Return the single most authoritative source for a (bucket, season).

    This is used by standings / season-scoped team statistics so the same
    physical match is never double counted and computed point totals match
    real-world tables (e.g. Flamengo 90 pts in the 2019 Brasileirao).
    """
    if bucket in ("serie_b", "serie_c"):
        return "br_football"
    if bucket == "libertadores":
        return "libertadores"
    if bucket == "copa_do_brasil":
        if season is not None and season >= 2022:
            return "br_football"
        return "copa_do_brasil"
    # brasileirao
    if season is not None and season <= 2011:
        return "historico"
    return "brasileirao"


def _team_id(key: str, state: Any) -> str:
    if state is None or pd.isna(state) or state == "":
        return key
    return f"{key}|{state}"


def _team_display(name: str, state: Any) -> str:
    if state is None or pd.isna(state) or state == "":
        return name
    return f"{name}-{state}"


def _parse_team(query: str) -> tuple[str, str | None]:
    """Return (base_key, optional_state) parsed from a team query string."""
    tn = normalize_team(query)
    return tn.key, tn.state


def _frame_for_bucket_season(df: pd.DataFrame, bucket: str,
                             season: int | None) -> pd.DataFrame:
    """Return ``df`` rows for a competition bucket and season.

    When ``season`` is set the result is restricted to the single preferred
    source for that (bucket, season) so standings are never double counted.
    """
    labels = set(BUCKET_LABELS.get(bucket, []))
    sub = df[df["competition"].isin(labels)]
    if season is not None:
        sub = sub[sub["season"] == season]
        src = preferred_source(bucket, season)
        candidate = sub[sub["source"] == src]
        if not candidate.empty:
            sub = candidate
    return sub


def _match_to_dict(m: pd.Series) -> dict[str, Any]:
    return {
        "date": (None if pd.isna(m["date"]) else m["date"].strftime("%Y-%m-%d")),
        "time": (None if pd.isna(m["date"]) else m["date"].strftime("%H:%M")),
        "home_team": m["home_team"],
        "away_team": m["away_team"],
        "home_goal": (None if pd.isna(m["home_goal"]) else int(m["home_goal"])),
        "away_goal": (None if pd.isna(m["away_goal"]) else int(m["away_goal"])),
        "competition": m["competition"],
        "season": (None if pd.isna(m["season"]) else int(m["season"])),
        "round": (None if pd.isna(m.get("round")) else str(m["round"])),
        "stage": (None if pd.isna(m.get("stage")) else str(m["stage"])),
        "stadium": (None if pd.isna(m.get("stadium")) else str(m["stadium"])),
        "source": m["source"],
    }


# ---------------------------------------------------------------------------
# Query engine
# ---------------------------------------------------------------------------


class QueryEngine:
    """High-level query API over the loaded knowledge graph."""

    def __init__(self, graph: KnowledgeGraph | None = None) -> None:
        self.graph = graph or KnowledgeGraph.load()
        self.df = self.graph.matches_df

    # ----- 1. Match queries ------------------------------------------------
    def search_matches(self, team: str | None = None,
                       opponent: str | None = None,
                       competition: str | None = None,
                       season: int | None = None,
                       date_from: str | None = None,
                       date_to: str | None = None,
                       limit: int = 50) -> dict[str, Any]:
        """Search matches by team, opponent, competition, season and date."""
        df = self.df
        bucket = normalize_competition_query(competition)
        if bucket is not None:
            df = _frame_for_bucket_season(df, bucket, season)
        elif season is not None:
            df = df[df["season"] == season]

        if date_from:
            df = df[df["date"] >= pd.to_datetime(date_from)]
        if date_to:
            df = df[df["date"] <= pd.to_datetime(date_to)]

        if team:
            tk, tstate = _parse_team(team)
            df = df[(df["home_team_key"].map(lambda k: team_matches(team, k)))
                    | (df["away_team_key"].map(lambda k: team_matches(team, k)))]
            if tstate:
                df = df[(df["home_state"] == tstate) | (df["away_state"] == tstate)]

        if opponent:
            ok, ostate = _parse_team(opponent)
            opp_mask = ((df["home_team_key"].map(lambda k: team_matches(opponent, k)))
                        | (df["away_team_key"].map(lambda k: team_matches(opponent, k))))
            if ostate:
                opp_mask = opp_mask & ((df["home_state"] == ostate)
                                       | (df["away_state"] == ostate))
            df = df[opp_mask]
            if team:
                tk = _parse_team(team)[0]
                df = df[((df["home_team_key"].map(lambda k: team_matches(team, k)))
                         & (df["away_team_key"].map(lambda k: team_matches(opponent, k))))
                        | ((df["home_team_key"].map(lambda k: team_matches(opponent, k)))
                           & (df["away_team_key"].map(lambda k: team_matches(team, k))))]

        df = df.sort_values("date", kind="stable")
        total = len(df)
        limited = df.head(limit) if limit and limit > 0 else df
        return {
            "count": int(total),
            "showing": int(len(limited)),
            "matches": [_match_to_dict(r) for _, r in limited.iterrows()],
            "competition": competition,
            "season": season,
        }

    # ----- head to head ----------------------------------------------------
    def head_to_head(self, team_a: str, team_b: str,
                     competition: str | None = None) -> dict[str, Any]:
        a_key, a_state = _parse_team(team_a)
        b_key, b_state = _parse_team(team_b)
        df = self.df
        bucket = normalize_competition_query(competition)
        if bucket is not None:
            df = _frame_for_bucket_season(df, bucket, None)

        a_wins = b_wins = draws = 0
        a_goals = b_goals = 0
        matches: list[dict[str, Any]] = []
        for _, r in df.iterrows():
            home = r["home_team_key"]
            away = r["away_team_key"]
            a_home = team_matches(team_a, home) or team_matches(team_a, away)
            if not a_home:
                continue
            a_is_home = team_matches(team_a, home)
            # team b must be the *other* side
            other = away if a_is_home else home
            if not team_matches(team_b, other):
                continue
            if a_state:
                a_state_match = (r["home_state"] if a_is_home else r["away_state"])
                if a_state_match != a_state:
                    continue
            if b_state:
                b_state_match = (r["away_state"] if a_is_home else r["home_state"])
                if b_state_match != b_state:
                    continue
            hg = r["home_goal"]
            ag = r["away_goal"]
            if pd.isna(hg) or pd.isna(ag):
                continue
            hg, ag = int(hg), int(ag)
            a_score = hg if a_is_home else ag
            b_score = ag if a_is_home else hg
            a_goals += a_score
            b_goals += b_score
            if a_score > b_score:
                a_wins += 1
            elif a_score < b_score:
                b_wins += 1
            else:
                draws += 1
            entry = _match_to_dict(r)
            entry["team_a_home"] = bool(a_is_home)
            matches.append(entry)
        matches.sort(key=lambda m: (m["date"] or "", m["season"] or 0))
        return {
            "team_a": team_a, "team_b": team_b,
            "matches": len(matches),
            "team_a_wins": a_wins, "team_b_wins": b_wins, "draws": draws,
            "team_a_goals": a_goals, "team_b_goals": b_goals,
            "matches_list": matches,
        }

    # ----- 2. Team queries -------------------------------------------------
    def _team_frame(self, df: pd.DataFrame, team: str, state: str | None):
        if state:
            return df[((df["home_team_key"].map(lambda k: team_matches(team, k)))
                       & (df["home_state"] == state))
                      | ((df["away_team_key"].map(lambda k: team_matches(team, k)))
                         & (df["away_state"] == state))]
        return df[(df["home_team_key"].map(lambda k: team_matches(team, k)))
                  | (df["away_team_key"].map(lambda k: team_matches(team, k)))]

    def team_stats(self, team: str, season: int | None = None,
                   competition: str | None = None,
                   venue: str | None = None) -> dict[str, Any]:
        """Return win/draw/loss/goals statistics for a team.

        ``venue`` may be ``"home"``, ``"away"`` or ``None`` (both).
        """
        _, state = _parse_team(team)
        df = self.df
        bucket = normalize_competition_query(competition)
        if bucket is not None and season is not None:
            df = _frame_for_bucket_season(df, bucket, season)
        elif bucket is not None:
            df = _frame_for_bucket_season(df, bucket, None)
        elif season is not None:
            df = df[df["season"] == season]

        tk, _ = _parse_team(team)
        team_rows = self._team_frame(df, team, state)

        def stats_for(rows: pd.DataFrame) -> dict[str, Any]:
            w = d = l = gf = ga = 0
            for _, r in rows.iterrows():
                if pd.isna(r["home_goal"]) or pd.isna(r["away_goal"]):
                    continue
                is_home = team_matches(team, r["home_team_key"])
                hg, ag = int(r["home_goal"]), int(r["away_goal"])
                scored = hg if is_home else ag
                conceded = ag if is_home else hg
                gf += scored
                ga += conceded
                if scored > conceded:
                    w += 1
                elif scored < conceded:
                    l += 1
                else:
                    d += 1
            total = w + d + l
            return {
                "matches": total, "wins": w, "draws": d, "losses": l,
                "goals_for": gf, "goals_against": ga,
                "goal_diff": gf - ga,
                "win_rate": round(w / total * 100, 1) if total else 0.0,
            }

        if venue == "home":
            team_rows = team_rows[team_rows["home_team_key"].map(
                lambda k: team_matches(team, k))]
        elif venue == "away":
            team_rows = team_rows[team_rows["away_team_key"].map(
                lambda k: team_matches(team, k))]

        overall = stats_for(team_rows)
        home_rows = team_rows[team_rows["home_team_key"].map(
            lambda k: team_matches(team, k))]
        away_rows = team_rows[team_rows["away_team_key"].map(
            lambda k: team_matches(team, k))]
        overall["home"] = stats_for(home_rows)
        overall["away"] = stats_for(away_rows)
        overall["team"] = team
        overall["season"] = season
        overall["competition"] = competition
        overall["venue"] = venue
        return overall

    def team_competitions(self, team: str) -> dict[str, Any]:
        """Return the competitions a team has participated in across files."""
        tk, state = _parse_team(team)
        rows = self._team_frame(self.df, team, state)
        comps = (rows.groupby("competition")
                 .agg(matches=("competition", "size"),
                      seasons=("season", lambda s: sorted({int(x) for x in s
                                                          if pd.notna(x)})))
                 .reset_index())
        result = []
        for _, r in comps.iterrows():
            result.append({"competition": r["competition"],
                           "matches": int(r["matches"]),
                           "seasons": list(r["seasons"])})
        result.sort(key=lambda c: -c["matches"])
        return {"team": team, "competitions": result}

    def top_scoring_teams(self, season: int | None = None,
                         competition: str | None = None,
                         limit: int = 10) -> dict[str, Any]:
        """Return teams ranked by total goals scored in a competition/season."""
        bucket = normalize_competition_query(competition) or "brasileirao"
        df = _frame_for_bucket_season(self.df, bucket, season)
        gf: dict[str, int] = {}
        display: dict[str, str] = {}
        for _, r in df.iterrows():
            if pd.isna(r["home_goal"]) or pd.isna(r["away_goal"]):
                continue
            for side in ("home", "away"):
                tid = _team_id(r[f"{side}_team_key"], r[f"{side}_state"])
                gf[tid] = gf.get(tid, 0) + int(r[f"{side}_goal"])
                display.setdefault(tid, _team_display(r[f"{side}_team"],
                                                     r[f"{side}_state"]))
        ranked = sorted(gf.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        return {
            "competition": competition, "season": season,
            "teams": [{"team": display[tid], "goals": g} for tid, g in ranked],
        }

    # ----- 3. Player queries ----------------------------------------------
    def search_players(self, name: str | None = None,
                       nationality: str | None = None,
                       club: str | None = None,
                       position: str | None = None,
                       min_overall: int | None = None,
                       order_by: str = "Overall",
                       limit: int = 20) -> dict[str, Any]:
        players = self.graph.players_df
        if "Name" not in players.columns:
            return {"count": 0, "players": []}
        mask = pd.Series(True, index=players.index)
        if name:
            mask &= players["Name"].astype(str).str.contains(
                name, case=False, na=False, regex=False)
        if nationality:
            mask &= players["Nationality"].astype(str).str.contains(
                nationality, case=False, na=False, regex=False)
        if club:
            mask &= players["Club"].astype(str).str.contains(
                club, case=False, na=False, regex=False)
        if position and "Position" in players.columns:
            mask &= players["Position"].astype(str).str.contains(
                position, case=False, na=False, regex=False)
        if min_overall is not None and "Overall" in players.columns:
            mask &= pd.to_numeric(players["Overall"], errors="coerce") >= min_overall

        sub = players[mask]
        if order_by in sub.columns:
            sub = sub.sort_values(order_by, ascending=False)
        sub = sub.head(limit)
        out = []
        for _, r in sub.iterrows():
            out.append({
                "name": r.get("Name"),
                "age": (None if pd.isna(r.get("Age")) else int(r.get("Age"))),
                "nationality": r.get("Nationality"),
                "overall": (None if pd.isna(r.get("Overall"))
                            else int(r.get("Overall"))),
                "potential": (None if pd.isna(r.get("Potential"))
                              else int(r.get("Potential"))),
                "club": r.get("Club"),
                "position": r.get("Position"),
                "jersey": (None if pd.isna(r.get("Jersey Number"))
                           else r.get("Jersey Number")),
                "value": r.get("Value"),
                "wage": r.get("Wage"),
            })
        return {"count": int(players[mask].shape[0]),
                "showing": len(out), "players": out}

    def top_brazilian_players(self, limit: int = 10) -> dict[str, Any]:
        res = self.search_players(nationality="Brazil", order_by="Overall",
                                  limit=limit)
        res["title"] = "Top-rated Brazilian players"
        return res

    def players_at_brazilian_clubs(self, limit: int = 10) -> dict[str, Any]:
        """Summarise Brazilian players grouped by Brazilian club."""
        players = self.graph.players_df
        if "Nationality" not in players.columns or "Club" not in players.columns:
            return {"clubs": []}
        braz = players[players["Nationality"].astype(str).str.contains(
            "Brazil", case=False, na=False)]
        # Only consider clubs that themselves field Brazilian players and look
        # like Brazilian clubs (contain one of the well-known Brazilian names).
        brazilian_club_hints = [
            "flamengo", "fluminense", "vasco", "botafogo", "palmeiras",
            "corinthians", "santos", "sao paulo", "são paulo", "gremio",
            "grêmio", "internacional", "cruzeiro", "atletico mineiro",
            "atlético mineiro", "bahia", "fortaleza", "ceará", "ceara",
            "sport", "chapecoense", "parana", "vitoria", "vitória",
            "america", "américa", "goias", "goiás", "athletico",
        ]

        def is_brazilian_club(name: str) -> bool:
            n = str(name).lower()
            return any(h in n for h in brazilian_club_hints)

        braz = braz.assign(_is_br=braz["Club"].map(is_brazilian_club))
        braz = braz[braz["_is_br"]]
        grouped = (braz.groupby("Club")
                   .agg(players=("ID", "size"),
                        avg_overall=("Overall", "mean"))
                   .reset_index())
        grouped["avg_overall"] = grouped["avg_overall"].round(1)
        grouped = grouped.sort_values("players", ascending=False).head(limit)
        return {
            "clubs": [{"club": r["Club"], "players": int(r["players"]),
                       "avg_overall": (None if pd.isna(r["avg_overall"])
                                       else float(r["avg_overall"]))}
                      for _, r in grouped.iterrows()],
        }

    # ----- 4. Competition queries -----------------------------------------
    def standings(self, competition: str, season: int,
                  limit: int | None = None) -> dict[str, Any]:
        """Compute a league standings table (3 pts win / 1 draw / 0 loss)."""
        bucket = normalize_competition_query(competition) or "brasileirao"
        if bucket not in LEAGUE_BUCKETS:
            return self.cup_bracket(competition, season)
        df = _frame_for_bucket_season(self.df, bucket, season)
        teams: dict[str, dict[str, Any]] = {}
        for _, r in df.iterrows():
            if pd.isna(r["home_goal"]) or pd.isna(r["away_goal"]):
                continue
            hg, ag = int(r["home_goal"]), int(r["away_goal"])
            for side, opp_side in (("home", "away"), ("away", "home")):
                tid = _team_id(r[f"{side}_team_key"], r[f"{side}_state"])
                disp = _team_display(r[f"{side}_team"], r[f"{side}_state"])
                e = teams.setdefault(tid, {"team": disp, "played": 0, "wins": 0,
                                           "draws": 0, "losses": 0,
                                           "goals_for": 0, "goals_against": 0,
                                           "points": 0})
                e["played"] += 1
                scored = hg if side == "home" else ag
                conceded = ag if side == "home" else hg
                e["goals_for"] += scored
                e["goals_against"] += conceded
                if scored > conceded:
                    e["wins"] += 1
                    e["points"] += 3
                elif scored < conceded:
                    e["losses"] += 1
                else:
                    e["draws"] += 1
                    e["points"] += 1
        rows = sorted(teams.values(),
                      key=lambda e: (-e["points"], -e["wins"],
                                     -(e["goals_for"] - e["goals_against"]),
                                     -e["goals_for"], e["team"]))
        if limit:
            rows = rows[:limit]
        if rows:
            rows[0]["champion"] = True
        return {"competition": competition, "season": season,
                "standings": rows, "source": preferred_source(bucket, season)}

    def cup_bracket(self, competition: str, season: int) -> dict[str, Any]:
        """Return cup (Copa do Brasil / Libertadores) matches grouped by round."""
        bucket = normalize_competition_query(competition)
        if bucket not in CUP_BUCKETS:
            bucket = "copa_do_brasil"
        df = _frame_for_bucket_season(self.df, bucket, season)
        group_col = "stage" if bucket == "libertadores" else "round"
        out: dict[str, list[dict[str, Any]]] = {}
        for _, r in df.sort_values("date").iterrows():
            key = (None if pd.isna(r.get(group_col)) or r.get(group_col) is None
                   else str(r.get(group_col)))
            stage = key or "unknown"
            out.setdefault(stage, []).append(_match_to_dict(r))
        return {"competition": competition, "season": season,
                "stages": out, "match_count": int(len(df))}

    def champion(self, competition: str, season: int) -> dict[str, Any]:
        table = self.standings(competition, season)
        if "standings" in table and table["standings"]:
            top = table["standings"][0]
            return {"competition": competition, "season": season,
                    "champion": top["team"], "points": top["points"],
                    "record": [top["wins"], top["draws"], top["losses"]]}
        return {"competition": competition, "season": season,
                "champion": None}

    def relegated(self, competition: str, season: int,
                  n: int = 4) -> dict[str, Any]:
        table = self.standings(competition, season)
        if "standings" not in table:
            return {"competition": competition, "season": season,
                    "relegated": []}
        rows = table["standings"][-n:]
        return {"competition": competition, "season": season,
                "relegated": [r["team"] for r in rows]}

    # ----- 5. Statistical analysis ---------------------------------------
    def average_goals(self, competition: str | None = None,
                      season: int | None = None) -> dict[str, Any]:
        df = self.df
        bucket = normalize_competition_query(competition)
        if bucket is not None:
            df = _frame_for_bucket_season(df, bucket, season)
        elif season is not None:
            df = df[df["season"] == season]
        scored = df[(df["home_goal"].notna()) & (df["away_goal"].notna())]
        if scored.empty:
            return {"competition": competition, "season": season,
                    "matches": 0, "avg_goals": 0.0,
                    "home_win_rate": 0.0, "draw_rate": 0.0,
                    "away_win_rate": 0.0}
        total_goals = scored["home_goal"].sum() + scored["away_goal"].sum()
        n = len(scored)
        home_wins = (scored["winner"] == "home").sum()
        draws = (scored["winner"] == "draw").sum()
        away_wins = (scored["winner"] == "away").sum()
        return {
            "competition": competition, "season": season,
            "matches": int(n),
            "total_goals": int(total_goals),
            "avg_goals": round(float(total_goals) / n, 3),
            "avg_home_goals": round(float(scored["home_goal"].sum()) / n, 3),
            "avg_away_goals": round(float(scored["away_goal"].sum()) / n, 3),
            "home_win_rate": round(float(home_wins) / n * 100, 1),
            "draw_rate": round(float(draws) / n * 100, 1),
            "away_win_rate": round(float(away_wins) / n * 100, 1),
        }

    def home_vs_away(self, competition: str | None = None,
                     season: int | None = None) -> dict[str, Any]:
        return self.average_goals(competition, season)

    def biggest_victories(self, competition: str | None = None,
                          season: int | None = None,
                          limit: int = 10) -> dict[str, Any]:
        df = self.df
        bucket = normalize_competition_query(competition)
        if bucket is not None:
            df = _frame_for_bucket_season(df, bucket, season)
        elif season is not None:
            df = df[df["season"] == season]
        scored = df[(df["home_goal"].notna()) & (df["away_goal"].notna())].copy()
        scored["margin"] = (scored["home_goal"].astype(int)
                            - scored["away_goal"].astype(int)).abs()
        scored = scored.sort_values(["margin", "date"], ascending=[False, True])
        out = []
        for _, r in scored.head(limit).iterrows():
            out.append({
                "date": (None if pd.isna(r["date"]) else
                         r["date"].strftime("%Y-%m-%d")),
                "winner": (r["home_team"] if int(r["home_goal"]) > int(r["away_goal"])
                           else r["away_team"]),
                "loser": (r["away_team"] if int(r["home_goal"]) > int(r["away_goal"])
                          else r["home_team"]),
                "winner_goals": int(max(r["home_goal"], r["away_goal"])),
                "loser_goals": int(min(r["home_goal"], r["away_goal"])),
                "competition": r["competition"],
                "season": (None if pd.isna(r["season"]) else int(r["season"])),
            })
        return {"competition": competition, "season": season,
                "biggest_victories": out}

    def derbies(self, season: int | None = None,
                limit: int = 50) -> dict[str, Any]:
        """Find matches between traditional Brazilian rival pairs."""
        rivals = [
            ("Flamengo", "Fluminense", "Fla-Flu"),
            ("Flamengo", "Vasco", "Clássico dos Milhões"),
            ("Corinthians", "São Paulo", "Clássico Majestoso"),
            ("Corinthians", "Palmeiras", "Derby Paulista"),
            ("Palmeiras", "São Paulo", "Choque-Rei"),
            ("Santos", "São Paulo", "San-São"),
            ("Grêmio", "Internacional", "Grenal"),
            ("Atlético", "Cruzeiro", "Clássico Mineiro"),
            ("Bahia", "Vitória", "Ba-Vi"),
            ("Sport", "Santa Cruz", "Clássico das Multidões"),
            ("Fortaleza", "Ceará", "Clássico-Rei"),
        ]
        df = self.df
        if season is not None:
            df = df[df["season"] == season]
        results = []
        for a, b, name in rivals:
            for _, r in df.iterrows():
                a_home = team_matches(a, r["home_team_key"])
                b_away = team_matches(b, r["away_team_key"])
                b_home = team_matches(b, r["home_team_key"])
                a_away = team_matches(a, r["away_team_key"])
                if (a_home and b_away) or (b_home and a_away):
                    results.append({
                        "derby": name, **_match_to_dict(r),
                    })
        results.sort(key=lambda m: (m["date"] or "", m["derby"]))
        total = len(results)
        results = results[:limit]
        return {"season": season, "count": total, "derbies": results}

    # ----- cross-file (player + match) ------------------------------------
    def team_players(self, team: str, limit: int = 50) -> dict[str, Any]:
        """FIFA players whose club matches ``team`` (cross-file player+match)."""
        return self.search_players(club=team, order_by="Overall", limit=limit)

    def team_summary(self, team: str) -> dict[str, Any]:
        """Combine match stats and player roster for a team (cross-file)."""
        return {
            "team": team,
            "stats": self.team_stats(team),
            "competitions": self.team_competitions(team),
            "players": self.team_players(team, limit=20),
        }


def get_engine() -> QueryEngine:
    """Return a process-wide cached :class:`QueryEngine`."""
    return _ENGINE


@lru_cache(maxsize=1)
def _build_engine() -> QueryEngine:
    return QueryEngine(KnowledgeGraph.load())


_ENGINE: QueryEngine = _build_engine()
