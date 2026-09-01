"""Query engine for the Brazilian Soccer MCP Server.

Implements the five required capability categories from the specification:

1. Match queries        -- ``search_matches`` (by team, date range, competition, season)
2. Team queries         -- ``team_statistics``, ``team_comparison``, ``team_overview``
3. Player queries       -- ``search_players``, ``player_profile``
4. Competition queries  -- ``league_standings``, ``competition_statistics``, ``biggest_wins``
5. Statistical analysis -- averages, win rates, margins, head-to-head
   (``head_to_head`` plus the aggregates above)

Every method returns a JSON-serializable ``dict`` with:
* ``query``  -- the normalized parameters used
* ``summary``-- a human-readable answer paragraph (in the style of the
  specification's example answer formats)
* structured payloads (``matches``, ``standings``, ``statistics``, ...)
* ``count``  -- number of rows in the primary payload, where applicable

All string matching is accent- and case-insensitive and goes through the
team-name canonicalization layer, so "Palmeiras-SP", "Palmeiras - SP" and
"Sao Paulo"/"São Paulo" style variants all resolve to the same team.
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict

from .data_loader import Match, Player, SoccerData
from .knowledge_graph import KnowledgeGraph
from .normalize import competition_key, key_team


def _fold(text: str) -> str:
    """Accent/case-insensitive comparison key for free-text queries."""
    decomposed = unicodedata.normalize("NFD", text or "")
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(stripped.lower().split())


def _fmt_score(m: Match) -> str:
    if m.home_goals is None or m.away_goals is None:
        return "vs"
    return f"{m.home_goals}-{m.away_goals}"


def _match_view(m: Match) -> dict:
    view = {
        "match_id": m.match_id,
        "date": m.date,
        "competition": m.competition,
        "season": m.season,
        "fixture": f"{m.home_team} {_fmt_score(m)} {m.away_team}",
        "home_team": m.home_team,
        "away_team": m.away_team,
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
    }
    if m.round:
        view["round"] = m.round
    if m.stage:
        view["stage"] = m.stage
    return view


def _resolve(data: SoccerData, name: str | None) -> str | None:
    return data.resolve_team(name) if name else None


class QueryEngine:
    """High-level query layer over the loaded datasets and knowledge graph."""

    def __init__(self, data: SoccerData | None = None, data_dir=None):
        self.data = data if data is not None else SoccerData(data_dir)
        self.graph = KnowledgeGraph(self.data)

    # ==================================================================
    # Shared record computation
    # ==================================================================

    @staticmethod
    def _record(matches: list[Match], team: str) -> dict:
        """Win/draw/loss + goals aggregates for ``team`` over ``matches``."""
        rec = {
            "team": team,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        for m in matches:
            if m.home_goals is None or m.away_goals is None:
                continue
            if team == m.home_team:
                gf, ga = m.home_goals, m.away_goals
            elif team == m.away_team:
                gf, ga = m.away_goals, m.home_goals
            else:
                continue
            rec["played"] += 1
            rec["goals_for"] += gf
            rec["goals_against"] += ga
            if gf > ga:
                rec["wins"] += 1
            elif gf == ga:
                rec["draws"] += 1
            else:
                rec["losses"] += 1
        rec["goal_difference"] = rec["goals_for"] - rec["goals_against"]
        if rec["played"]:
            rec["win_rate"] = round(100 * rec["wins"] / rec["played"], 1)
        else:
            rec["win_rate"] = None
        return rec

    @staticmethod
    def _venue_split(matches: list[Match], team: str) -> tuple[dict, dict]:
        home = QueryEngine._record([m for m in matches if m.home_team == team], team)
        away = QueryEngine._record([m for m in matches if m.away_team == team], team)
        return home, away

    # ==================================================================
    # 1. Match queries
    # ==================================================================

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        stage: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Find matches by team, opponent, competition, season, stage or dates."""
        params = {
            "team": team, "opponent": opponent, "competition": competition,
            "season": season, "date_from": date_from, "date_to": date_to,
            "stage": stage, "limit": limit,
        }
        team_r, opponent_r = _resolve(self.data, team), _resolve(self.data, opponent)
        if team and team_r is None:
            return self._no_team(team)
        if opponent and opponent_r is None:
            return self._no_team(opponent)

        if team_r and opponent_r:
            pool = self.data.matches_between(team_r, opponent_r)
        elif team_r:
            pool = self.data.matches_for_team(team_r)
        elif opponent_r:
            pool = self.data.matches_for_team(opponent_r)
        else:
            pool = list(self.data.matches)

        if competition:
            pool = [m for m in pool if m.competition_key == competition_key(competition)]
        if season is not None:
            pool = [m for m in pool if m.season == season]
        if stage:
            stage_fold = _fold(stage)
            exact = [m for m in pool if m.stage and _fold(m.stage) == stage_fold]
            if not exact:
                exact = [m for m in pool if m.stage and stage_fold in _fold(m.stage)]
            pool = exact
        if date_from:
            pool = [m for m in pool if m.date and m.date >= date_from]
        if date_to:
            pool = [m for m in pool if m.date and m.date <= date_to]

        pool.sort(key=lambda m: (m.date or "", m.match_id), reverse=True)
        total = len(pool)
        shown = [_match_view(m) for m in pool[:limit]]

        summary = self._match_summary(pool, total, team_r, opponent_r, competition, season, limit)
        result = {"query": params, "summary": summary, "matches": shown, "total_matches": total, "count": len(shown)}
        if team_r and opponent_r:
            result["head_to_head"] = self.head_to_head(team_r, opponent_r, competition, season)["record"]
        return result

    def _match_summary(self, pool, total, team_r, opponent_r, competition, season, limit) -> str:
        parts = []
        if team_r and opponent_r:
            record = self._h2h_record(pool, team_r, opponent_r)
            parts.append(
                f"{team_r} vs {opponent_r}: {total} matches in dataset. "
                f"Head-to-head: {team_r} {record['team_a_wins']} wins, "
                f"{opponent_r} {record['team_b_wins']} wins, {record['draws']} draws."
            )
        elif team_r:
            parts.append(f"{team_r}: {total} matches found.")
        else:
            parts.append(f"{total} matches found.")
        scope = " / ".join(
            filter(None, [competition, f"season {season}" if season else None])
        )
        if scope:
            parts.append(f"Scope: {scope}.")
        if total > limit:
            parts.append(f"Showing the {limit} most recent.")
        return " ".join(parts)

    @staticmethod
    def _no_team(name: str) -> dict:
        return {
            "query": {"team": name},
            "summary": f"No team matching '{name}' was found in the dataset.",
            "matches": [],
            "count": 0,
        }

    # ==================================================================
    # Head-to-head (statistical analysis)
    # ==================================================================

    def head_to_head(
        self, team_a: str, team_b: str, competition: str | None = None, season: int | None = None
    ) -> dict:
        """Compare two teams' record against each other."""
        a, b = _resolve(self.data, team_a), _resolve(self.data, team_b)
        if a is None or b is None:
            missing = team_a if a is None else team_b
            return {"query": {"team_a": team_a, "team_b": team_b}, "summary": f"No team matching '{missing}' found.", "count": 0}
        pool = self.data.matches_between(a, b)
        if competition:
            pool = [m for m in pool if m.competition_key == competition_key(competition)]
        if season is not None:
            pool = [m for m in pool if m.season == season]
        pool.sort(key=lambda m: (m.date or "", m.match_id))
        record = self._h2h_record(pool, a, b)
        recent = [_match_view(m) for m in pool[-10:]][::-1]
        summary = (
            f"Head-to-head {a} vs {b}: {a} {record['team_a_wins']} wins, "
            f"{b} {record['team_b_wins']} wins, {record['draws']} draws "
            f"({record['played']} matches in dataset). "
            f"Goals: {a} {record['team_a_goals']} - {record['team_b_goals']} {b}."
        )
        return {
            "query": {"team_a": a, "team_b": b, "competition": competition, "season": season},
            "summary": summary,
            "record": record,
            "recent_matches": recent,
            "count": record["played"],
        }

    def _h2h_record(self, pool: list[Match], a: str, b: str) -> dict:
        record = {
            "team_a": a,
            "team_b": b,
            "played": 0,
            "team_a_wins": 0,
            "team_b_wins": 0,
            "draws": 0,
            "team_a_goals": 0,
            "team_b_goals": 0,
        }
        for m in pool:
            if m.home_goals is None or m.away_goals is None:
                continue
            record["played"] += 1
            if m.home_team == a:
                ga, gb = m.home_goals, m.away_goals
            else:
                ga, gb = m.away_goals, m.home_goals
            record["team_a_goals"] += ga
            record["team_b_goals"] += gb
            if ga > gb:
                record["team_a_wins"] += 1
            elif ga < gb:
                record["team_b_wins"] += 1
            else:
                record["draws"] += 1
        return record

    # ==================================================================
    # 2. Team queries
    # ==================================================================

    def team_statistics(
        self, team: str, competition: str | None = None, season: int | None = None, venue: str | None = None
    ) -> dict:
        """Overall / home / away record for a team, optionally scoped."""
        resolved = _resolve(self.data, team)
        if resolved is None:
            return {"query": {"team": team}, "summary": f"No team matching '{team}' found in the dataset.", "count": 0}
        pool = self.data.matches_for_team(resolved)
        if competition:
            pool = [m for m in pool if m.competition_key == competition_key(competition)]
        if season is not None:
            pool = [m for m in pool if m.season == season]

        if venue and venue.lower() in {"home", "away"}:
            venue = venue.lower()
            scoped = [m for m in pool if (m.home_team == resolved) == (venue == "home")]
        else:
            venue = None
            scoped = pool

        record = self._record(scoped, resolved)
        home_record, away_record = self._venue_split(scoped, resolved)
        competitions = sorted({m.competition for m in scoped})
        scope_desc = " / ".join(filter(None, [competition, f"season {season}" if season else None, venue])) or "all matches in dataset"
        if record["played"]:
            summary = (
                f"{resolved} record ({scope_desc}): "
                f"Played {record['played']}, Wins {record['wins']}, Draws {record['draws']}, "
                f"Losses {record['losses']}. Goals For {record['goals_for']}, "
                f"Goals Against {record['goals_against']}. Win rate {record['win_rate']}%."
            )
        else:
            summary = f"{resolved} has no scored matches for scope ({scope_desc})."
        return {
            "query": {"team": resolved, "competition": competition, "season": season, "venue": venue},
            "summary": summary,
            "statistics": record,
            "home_record": home_record,
            "away_record": away_record,
            "competitions": competitions,
            "count": record["played"],
        }

    def team_comparison(
        self, team_a: str, team_b: str, competition: str | None = None, season: int | None = None
    ) -> dict:
        """Side-by-side statistics for two teams plus their head-to-head."""
        a, b = _resolve(self.data, team_a), _resolve(self.data, team_b)
        if a is None or b is None:
            missing = team_a if a is None else team_b
            return {"query": {"team_a": team_a, "team_b": team_b}, "summary": f"No team matching '{missing}' found.", "count": 0}
        stats_a = self.team_statistics(a, competition, season)["statistics"]
        stats_b = self.team_statistics(b, competition, season)["statistics"]
        h2h = self.head_to_head(a, b, competition, season)["record"]
        summary = (
            f"{a}: {stats_a['wins']}W {stats_a['draws']}D {stats_a['losses']}L, "
            f"GF {stats_a['goals_for']}, GA {stats_a['goals_against']}. "
            f"{b}: {stats_b['wins']}W {stats_b['draws']}D {stats_b['losses']}L, "
            f"GF {stats_b['goals_for']}, GA {stats_b['goals_against']}. "
            f"Head-to-head: {a} {h2h['team_a_wins']} wins, {b} {h2h['team_b_wins']} wins, "
            f"{h2h['draws']} draws."
        )
        return {
            "query": {"team_a": a, "team_b": b, "competition": competition, "season": season},
            "summary": summary,
            "team_a": stats_a,
            "team_b": stats_b,
            "head_to_head": h2h,
            "count": 2,
        }

    def team_overview(self, team: str) -> dict:
        """Cross-file overview: matches, competitions and FIFA-squad players."""
        resolved = _resolve(self.data, team)
        if resolved is None:
            return {"query": {"team": team}, "summary": f"No team matching '{team}' found.", "count": 0}
        matches = self.data.matches_for_team(resolved)
        competitions = sorted({m.competition for m in matches})
        seasons = sorted({m.season for m in matches if m.season is not None})
        record = self._record(matches, resolved)

        club_key = key_team(resolved)
        players = [
            p for p in self.data.players
            if p.club and p.club_key and (
                p.club_key == club_key or club_key in p.club_key or p.club_key in club_key
            )
        ]
        players.sort(key=lambda p: (-(p.overall or 0), p.name))
        players_view = [p.as_dict() for p in players[:15]]

        summary = (
            f"{resolved} overview: {record['played']} matches in dataset across "
            f"{len(competitions)} competitions ({', '.join(competitions) or 'none'}). "
            f"Record: {record['wins']}W {record['draws']}D {record['losses']}L. "
            f"Seasons covered: {seasons[0]}-{seasons[-1]}." if seasons else
            f"{resolved} overview: {record['played']} matches in dataset."
        )
        if players:
            summary += f" FIFA database lists {len(players)} players for this club."
        else:
            summary += " No players for this club in the FIFA database."
        return {
            "query": {"team": resolved},
            "summary": summary,
            "statistics": record,
            "competitions": competitions,
            "seasons": seasons,
            "players": players_view,
            "player_count": len(players),
            "count": record["played"],
        }

    # ==================================================================
    # 3. Player queries
    # ==================================================================

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_age: int | None = None,
        limit: int = 20,
    ) -> dict:
        """Search the FIFA player database by name/nationality/club/position."""
        pool = self.data.players
        if name:
            needle = _fold(name)
            pool = [p for p in pool if needle in _fold(p.name)]
        if nationality:
            nat = _fold(nationality)
            pool = [p for p in pool if nat in _fold(p.nationality)]
        if club:
            club_fold = _fold(club)
            pool = [p for p in pool if club_fold in _fold(p.club)]
        if position:
            pos = position.strip().upper()
            pool = [p for p in pool if p.position.upper() == pos]
        if min_overall is not None:
            pool = [p for p in pool if (p.overall or 0) >= min_overall]
        if max_age is not None:
            pool = [p for p in pool if p.age is not None and p.age <= max_age]

        pool = sorted(pool, key=lambda p: (-(p.overall or 0), -(p.potential or 0), p.name))
        total = len(pool)
        shown = [p.as_dict() for p in pool[:limit]]
        filters = {
            k: v
            for k, v in {
                "name": name, "nationality": nationality, "club": club,
                "position": position, "min_overall": min_overall, "max_age": max_age,
            }.items()
            if v is not None
        }
        summary = f"{total} players matched ({', '.join(f'{k}={v}' for k, v in filters.items()) or 'no filters'})."
        if total:
            top = pool[0]
            summary += f" Top rated: {top.name} ({top.club or 'no club'}) overall {top.overall}."
        if total > limit:
            summary += f" Showing top {limit} by overall rating."
        return {"query": filters, "summary": summary, "players": shown, "total_players": total, "count": len(shown)}

    def player_profile(self, player_name: str) -> dict:
        """Full profile (attributes + skills) for a player by name."""
        needle = _fold(player_name)
        exact = [p for p in self.data.players if _fold(p.name) == needle]
        candidates = exact or [p for p in self.data.players if needle in _fold(p.name)]
        if not candidates:
            return {"query": {"player": player_name}, "summary": f"No player named '{player_name}' found in the FIFA database.", "count": 0}
        candidates.sort(key=lambda p: -(p.overall or 0))
        best = candidates[0]
        profile = best.as_dict(include_skills=True)
        summary = (
            f"{best.name}: {best.nationality}, age {best.age}, position {best.position}, "
            f"club {best.club or 'none'}. Overall {best.overall}, potential {best.potential}. "
            f"{best.preferred_foot} foot, value {best.value or 'n/a'}."
        )
        if len(candidates) > 1:
            summary += f" ({len(candidates)} players matched this name; showing the highest rated.)"
        return {
            "query": {"player": player_name},
            "summary": summary,
            "player": profile,
            "other_matches": [p.as_dict() for p in candidates[1:5]],
            "count": 1,
        }

    # ==================================================================
    # 4. Competition queries
    # ==================================================================

    def league_standings(self, competition: str, season: int) -> dict:
        """League table computed from match results for a season."""
        matches = self.data.matches_in_competition(competition, season)
        if not matches:
            return {
                "query": {"competition": competition, "season": season},
                "summary": f"No matches found for {competition} season {season}.",
                "count": 0,
            }
        table: dict[str, dict] = {}
        for m in matches:
            if m.home_goals is None or m.away_goals is None:
                continue
            for team, gf, ga in ((m.home_team, m.home_goals, m.away_goals), (m.away_team, m.away_goals, m.home_goals)):
                row = table.setdefault(team, {"team": team, "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0})
                row["played"] += 1
                row["goals_for"] += gf
                row["goals_against"] += ga
                if gf > ga:
                    row["wins"] += 1
                elif gf == ga:
                    row["draws"] += 1
                else:
                    row["losses"] += 1
        rows = []
        for row in table.values():
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
            row["points"] = 3 * row["wins"] + row["draws"]
            rows.append(row)
        rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["team"]))

        comp_key = competition_key(competition)
        for position, row in enumerate(rows, start=1):
            row["position"] = position
            if comp_key == competition_key("Brasileirão Série A") and len(rows) >= 16:
                if position == 1:
                    row["zone"] = "Champion"
                elif position > len(rows) - 4:
                    row["zone"] = "Relegation"
        champion = rows[0] if rows else None
        summary = (
            f"{competition} {season} standings (computed from {len(matches)} matches): "
            f"1. {champion['team']} - {champion['points']} pts "
            f"({champion['wins']}W {champion['draws']}D {champion['losses']}L) - Champion."
            if champion else
            f"No scored matches found for {competition} {season}."
        )
        if champion and comp_key == competition_key("Brasileirão Série A"):
            relegated = [r["team"] for r in rows[-4:]]
            summary += f" Relegated: {', '.join(relegated)}."
        return {
            "query": {"competition": competition, "season": season},
            "summary": summary,
            "standings": rows,
            "count": len(rows),
        }

    def competition_statistics(self, competition: str, season: int | None = None) -> dict:
        """Aggregate stats for a competition (and optional season)."""
        matches = self.data.matches_in_competition(competition, season)
        scored = [m for m in matches if m.home_goals is not None and m.away_goals is not None]
        total_goals = sum(m.total_goals for m in scored)
        home_wins = sum(1 for m in scored if m.home_goals > m.away_goals)
        away_wins = sum(1 for m in scored if m.away_goals > m.home_goals)
        draws = len(scored) - home_wins - away_wins
        stats = {
            "competition": competition,
            "season": season,
            "matches": len(scored),
            "total_goals": total_goals,
            "average_goals_per_match": round(total_goals / len(scored), 2) if scored else None,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(100 * home_wins / len(scored), 1) if scored else None,
            "draw_rate": round(100 * draws / len(scored), 1) if scored else None,
            "away_win_rate": round(100 * away_wins / len(scored), 1) if scored else None,
        }
        seasons = sorted({m.season for m in self.data.matches_in_competition(competition) if m.season is not None})
        scope = f"{competition}" + (f" season {season}" if season is not None else "")
        summary = (
            f"{scope}: {stats['matches']} matches with scores, "
            f"average {stats['average_goals_per_match']} goals per match. "
            f"Home wins {stats['home_win_rate']}%, draws {stats['draw_rate']}%, "
            f"away wins {stats['away_win_rate']}%."
            if scored else
            f"No scored matches found for {scope}."
        )
        return {
            "query": {"competition": competition, "season": season},
            "summary": summary,
            "statistics": stats,
            "seasons_available": seasons,
            "count": stats["matches"],
        }

    def biggest_wins(
        self, competition: str | None = None, season: int | None = None, limit: int = 10
    ) -> dict:
        """Largest winning margins, optionally scoped to a competition/season."""
        pool = list(self.data.matches)
        if competition:
            pool = [m for m in pool if m.competition_key == competition_key(competition)]
        if season is not None:
            pool = [m for m in pool if m.season == season]
        pool = [m for m in pool if m.home_goals is not None and m.away_goals is not None]
        pool.sort(key=lambda m: (abs(m.home_goals - m.away_goals), m.total_goals), reverse=True)
        shown = [_match_view(m) for m in pool[:limit]]
        scope = competition + (f" season {season}" if season is not None else "") if competition else "all competitions in dataset"
        summary = f"Biggest victories in {scope}:" if shown else f"No scored matches found for {scope}."
        for index, view in enumerate(shown, start=1):
            summary += f" {index}. {view['fixture']} ({view['date']}, {view['competition']})."
        return {"query": {"competition": competition, "season": season, "limit": limit}, "summary": summary, "matches": shown, "count": len(shown)}

    # ==================================================================
    # Knowledge-graph queries
    # ==================================================================

    def graph_search(self, query: str, node_types: list[str] | None = None, limit: int = 20) -> dict:
        """Search knowledge-graph nodes (teams, players, clubs, competitions, matches)."""
        nodes = self.graph.search_nodes(query, node_types, limit)
        view = [{"id": n.node_id, "type": n.type, "name": n.name, "props": n.props} for n in nodes]
        summary = f"{len(view)} graph nodes matched '{query}'." if view else f"No graph nodes matched '{query}'."
        return {"query": {"text": query, "node_types": node_types}, "summary": summary, "nodes": view, "count": len(view)}

    def graph_neighbors(self, node_name: str, edge_types: list[str] | None = None, limit: int = 50) -> dict:
        """Explore relationships around a knowledge-graph node."""
        result = self.graph.neighbors(node_name, edge_types, limit)
        if not result:
            return {"query": {"node": node_name}, "summary": f"Node '{node_name}' not found in the knowledge graph.", "count": 0}
        node = result["node"]
        rel_total = sum(len(v) for v in result["relationships"].values())
        rel_types = ", ".join(sorted(result["relationships"]))
        summary = (
            f"{node['name']} ({node['type']}): {rel_total} relationships "
            f"({rel_types or 'none'})." if rel_total else f"{node['name']} ({node['type']}): no relationships."
        )
        return {
            "query": {"node": node_name, "edge_types": edge_types},
            "summary": summary,
            "node": node,
            "relationships": result["relationships"],
            "count": rel_total,
        }
