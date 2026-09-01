"""Query and analysis layer for the Brazilian Soccer MCP server.

:class:`SoccerQueryService` wraps a :class:`~brazilian_soccer_mcp.loader.SoccerData`
repository and answers the five query categories required by the
specification:

1. Match queries — find matches by team, opponent, competition, season,
   date range or stage.
2. Team queries — records (W/D/L, goals), home/away splits, profiles.
3. Player queries — FIFA database search by name, nationality, club and
   position.
4. Competition queries — standings computed from match results, seasons,
   champions and relegation.
5. Statistical analysis — head-to-head, averages, biggest wins, home
   advantage, derby fixtures.

All methods return plain JSON-serialisable dicts so the MCP layer can pass
them straight through to the calling LLM.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from typing import Any, Optional

from .loader import SoccerData
from .models import DRAW, LOSS, WIN, Match
from .normalize import DERBIES, KNOWN_COMPETITIONS, normalize_competition

DEFAULT_LIMIT = 25
MAX_LIMIT = 200


def _fmt_pct(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value * 100, 1)


class SoccerQueryService:
    """High-level query API over the loaded soccer datasets."""

    def __init__(self, data: SoccerData) -> None:
        self.data = data

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve(self, team: str) -> str:
        resolved = self.data.resolve_team(team)
        if resolved is None:
            raise ValueError(
                f"Unknown team: {team!r}. Use the 'list_teams' tool to see known names."
            )
        return resolved

    @staticmethod
    def _filter_matches(
        matches: list[Match],
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        stage: Optional[str] = None,
        source: Optional[str] = None,
    ) -> list[Match]:
        from .normalize import parse_date

        start = parse_date(date_from) if date_from else None
        end = parse_date(date_to) if date_to else None
        stage_pattern = None
        if stage:
            stage_pattern = re.compile(r"\b" + re.escape(stage.strip().casefold()) + r"\b")

        def keep(match: Match) -> bool:
            if competition and match.competition != competition:
                return False
            if season is not None and match.season != season:
                return False
            if start and (match.date is None or match.date < start):
                return False
            if end and (match.date is None or match.date > end):
                return False
            if stage_pattern:
                label = (match.stage or match.round or "").casefold()
                if not stage_pattern.search(label):
                    return False
            if source and match.source != source:
                return False
            return True

        return [m for m in matches if keep(m)]

    def _team_matches(
        self,
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "any",
        primary_only: bool = True,
    ) -> list[Match]:
        pool = self.data.primary_by_team.get(team, []) if primary_only else self.data.matches_by_team.get(team, [])
        out = []
        for match in pool:
            if competition and match.competition != competition:
                continue
            if season is not None and match.season != season:
                continue
            if venue == "home" and match.home_team != team:
                continue
            if venue == "away" and match.away_team != team:
                continue
            out.append(match)
        out.sort(key=lambda m: (m.date or date.min, m.competition))
        return out

    @staticmethod
    def _record(matches: list[Match], team: str) -> dict[str, Any]:
        wins = draws = losses = goals_for = goals_against = 0
        for match in matches:
            result = match.result_for(team)
            if result is None:
                continue
            if result == WIN:
                wins += 1
            elif result == DRAW:
                draws += 1
            else:
                losses += 1
            if match.is_played:
                if match.home_team == team:
                    goals_for += match.home_goals or 0
                    goals_against += match.away_goals or 0
                else:
                    goals_for += match.away_goals or 0
                    goals_against += match.home_goals or 0
        played = wins + draws + losses
        return {
            "team": team,
            "matches": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_difference": goals_for - goals_against,
            "win_rate": _fmt_pct(wins / played) if played else None,
        }

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------

    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        stage: Optional[str] = None,
        venue: str = "any",
        source: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Find matches by team, opponent, competition, season and dates."""
        if team and opponent:
            team_name = self._resolve(team)
            opponent_name = self._resolve(opponent)
            pool = [
                m
                for m in self.data.primary_matches
                if {m.home_team, m.away_team} == {team_name, opponent_name}
            ]
            if venue == "home":
                pool = [m for m in pool if m.home_team == team_name]
            elif venue == "away":
                pool = [m for m in pool if m.away_team == team_name]
            if not source:
                # keep the de-duplicated primary view unless a source is asked for
                pass
            matches = self._filter_matches(
                pool, competition, season, date_from, date_to, stage, source
            )
            heading = f"{team_name} vs {opponent_name}"
        elif team:
            team_name = self._resolve(team)
            matches = self._filter_matches(
                self._team_matches(team_name, competition, season, venue),
                date_from=date_from,
                date_to=date_to,
                stage=stage,
                source=source,
            )
            heading = team_name
        else:
            matches = self._filter_matches(
                self.data.matches if source else self.data.primary_matches,
                competition,
                season,
                date_from,
                date_to,
                stage,
                source,
            )
            heading = "All matches"

        matches = sorted(matches, key=lambda m: (m.date or date.min, m.competition), reverse=True)
        total = len(matches)
        limit = max(1, min(limit, MAX_LIMIT))
        page = matches[:limit]
        lines = [m.summary_line() for m in page]
        summary = f"{heading}: {total} match(es) found"
        if total > limit:
            summary += f" (showing {limit})"
        return {
            "summary": summary,
            "total": total,
            "shown": len(page),
            "matches": [m.to_dict() for m in page],
            "match_lines": lines,
        }

    def head_to_head(
        self,
        team_a: str,
        team_b: str,
        competition: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """All meetings between two teams plus the win/draw/loss summary."""
        name_a = self._resolve(team_a)
        name_b = self._resolve(team_b)
        matches = [
            m
            for m in self.data.primary_matches
            if {m.home_team, m.away_team} == {name_a, name_b}
        ]
        matches = self._filter_matches(matches, competition=competition)
        matches.sort(key=lambda m: m.date or date.min, reverse=True)

        wins_a = wins_b = draws = 0
        for match in matches:
            result_a = match.result_for(name_a)
            if result_a == WIN:
                wins_a += 1
            elif result_a == LOSS:
                wins_b += 1
            elif result_a == DRAW:
                draws += 1

        total = len(matches)
        page = matches[: max(1, min(limit, MAX_LIMIT))]
        summary = (
            f"Head-to-head {name_a} vs {name_b} ({total} matches in dataset): "
            f"{name_a} {wins_a} wins, {name_b} {wins_b} wins, {draws} draws"
        )
        return {
            "summary": summary,
            "team_a": name_a,
            "team_b": name_b,
            "total_matches": total,
            "team_a_wins": wins_a,
            "team_b_wins": wins_b,
            "draws": draws,
            "matches": [m.to_dict() for m in page],
            "match_lines": [m.summary_line() for m in page],
        }

    def last_meeting(self, team_a: str, team_b: str) -> dict[str, Any]:
        """Most recent match between two teams (with the score)."""
        name_a = self._resolve(team_a)
        name_b = self._resolve(team_b)
        matches = [
            m
            for m in self.data.primary_matches
            if {m.home_team, m.away_team} == {name_a, name_b} and m.is_played
        ]
        if not matches:
            return {
                "summary": f"No matches found between {name_a} and {name_b} in the dataset.",
                "match": None,
            }
        latest = max(matches, key=lambda m: m.date or date.min)
        summary = (
            f"Last meeting: {latest.summary_line()}"
        )
        return {"summary": summary, "match": latest.to_dict()}

    def derbies(self, competition: Optional[str] = None, season: Optional[int] = None) -> dict[str, Any]:
        """Matches between traditional rival clubs (Fla-Flu, Grenal, ...)."""
        blocks = []
        matches_found = 0
        for derby in DERBIES:
            name_a = self.data.resolve_team(derby["team_a"])
            name_b = self.data.resolve_team(derby["team_b"])
            if not name_a or not name_b:
                continue
            matches = [
                m
                for m in self.data.primary_matches
                if {m.home_team, m.away_team} == {name_a, name_b}
            ]
            matches = self._filter_matches(matches, competition=competition, season=season)
            if not matches:
                continue
            matches.sort(key=lambda m: m.date or date.min, reverse=True)
            matches_found += len(matches)
            blocks.append(
                {
                    "derby": derby["name"],
                    "teams": [name_a, name_b],
                    "total_matches": len(matches),
                    "recent": [m.to_dict() for m in matches[:5]],
                    "recent_lines": [m.summary_line() for m in matches[:5]],
                }
            )
        return {
            "summary": f"Found {matches_found} derby matches across {len(blocks)} rivalries",
            "derby_count": len(blocks),
            "match_count": matches_found,
            "derbies": blocks,
        }

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------

    def team_record(
        self,
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "all",
    ) -> dict[str, Any]:
        """Win/draw/loss record, goals and win rate for a team."""
        if venue not in ("all", "home", "away"):
            raise ValueError("venue must be 'all', 'home' or 'away'")
        name = self._resolve(team)
        matches = self._team_matches(name, competition, season, venue)
        record = self._record(matches, name)

        label = name
        if season:
            label += f" ({season}"
            label += f" {competition})" if competition else ")"
        elif competition:
            label += f" ({competition})"
        if venue in ("home", "away"):
            label += f" {venue} matches"

        breakdown = []
        by_comp: dict[tuple[str, Optional[int]], list[Match]] = defaultdict(list)
        for match in matches:
            by_comp[(match.competition, match.season)].append(match)
        for (comp, season_key), comp_matches in sorted(
            by_comp.items(), key=lambda item: (item[0][0], item[0][1] or 0)
        ):
            comp_record = self._record(comp_matches, name)
            comp_record["competition"] = comp
            comp_record["season"] = season_key
            breakdown.append(comp_record)

        summary = (
            f"{label}: {record['matches']} matches, "
            f"{record['wins']}W {record['draws']}D {record['losses']}L, "
            f"GF {record['goals_for']}, GA {record['goals_against']}, "
            f"win rate {record['win_rate']}%"
        )
        return {
            "summary": summary,
            **record,
            "venue": venue,
            "competition": competition,
            "season": season,
            "breakdown_by_competition": breakdown,
        }

    def team_profile(self, team: str) -> dict[str, Any]:
        """Everything the datasets know about one club."""
        name = self._resolve(team)
        all_matches = self._team_matches(name)
        record = self._record(all_matches, name)
        home_matches = [m for m in all_matches if m.home_team == name]
        away_matches = [m for m in all_matches if m.away_team == name]
        home_record = self._record(home_matches, name)
        away_record = self._record(away_matches, name)

        competitions: dict[str, list[int]] = defaultdict(list)
        for match in all_matches:
            if match.season:
                seasons = competitions[match.competition]
                if match.season not in seasons:
                    seasons.append(match.season)
        competitions = {comp: sorted(seasons) for comp, seasons in competitions.items()}

        first = min((m.date for m in all_matches if m.date), default=None)
        last = max((m.date for m in all_matches if m.date), default=None)
        biggest = max(
            (m for m in all_matches if m.is_played),
            key=lambda m: (m.result_for(name) == WIN, m.goal_margin or 0),
            default=None,
        )

        players = self.data.resolve_club_players(name)
        summary = (
            f"{name}: {record['matches']} matches in dataset "
            f"({record['wins']}W {record['draws']}D {record['losses']}L), "
            f"{len(competitions)} competition(s), {len(players)} FIFA players"
        )
        return {
            "summary": summary,
            "team": name,
            "record": record,
            "home_record": home_record,
            "away_record": away_record,
            "competitions": competitions,
            "first_match": first.isoformat() if first else None,
            "last_match": last.isoformat() if last else None,
            "biggest_win": biggest.summary_line() if biggest else None,
            "squad": [p.to_dict() for p in players],
        }

    def list_teams(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict[str, Any]:
        """Teams known to the system, optionally filtered to a competition."""
        teams: dict[str, dict[str, int]] = defaultdict(lambda: {"matches": 0})
        for match in self.data.primary_matches:
            if competition and match.competition != competition:
                continue
            if season is not None and match.season != season:
                continue
            for team in (match.home_team, match.away_team):
                teams[team]["matches"] += 1
        team_list = sorted(teams)
        return {
            "summary": f"{len(team_list)} teams found",
            "teams": team_list,
        }

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        """Search the FIFA player database by any combination of filters."""
        if not any([name, nationality, club, position, min_overall, max_overall]):
            pool = self.data.players
        elif name:
            token = name.strip().casefold()
            pool = [p for p in self.data.players if token in p.name.casefold()]
            if nationality:
                pool = [p for p in pool if (p.nationality or "").casefold() == nationality.casefold()]
        else:
            pool = list(self.data.players)

        if nationality:
            nat = nationality.strip().casefold()
            if nat in ("brazil", "brazilian", "brasil", "brasileiro"):
                nat = "brazil"
            pool = [p for p in pool if (p.nationality or "").casefold() == nat]
        if club:
            resolved = self.data.resolve_club_players(club)
            allowed_ids = {p.id for p in resolved}
            club_key = club.strip().casefold()
            pool = [
                p
                for p in pool
                if p.id in allowed_ids or (p.club or "").casefold() == club_key
            ]
        if position:
            pos = position.strip().upper()
            pool = [p for p in pool if (p.position or "").upper() == pos]
        if min_overall is not None:
            pool = [p for p in pool if p.overall is not None and p.overall >= min_overall]
        if max_overall is not None:
            pool = [p for p in pool if p.overall is not None and p.overall <= max_overall]

        pool.sort(key=lambda p: (-(p.overall or 0), p.name))
        total = len(pool)
        limit = max(1, min(limit, MAX_LIMIT))
        page = pool[:limit]
        summary = f"{total} player(s) found"
        if total > limit:
            summary += f" (showing top {limit})"
        return {
            "summary": summary,
            "total": total,
            "shown": len(page),
            "players": [p.to_dict() for p in page],
        }

    def top_players(
        self,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Highest-rated players, optionally filtered."""
        return self.search_players(
            nationality=nationality, club=club, position=position, limit=limit
        )

    def club_squad(self, club: str, limit: int = MAX_LIMIT) -> dict[str, Any]:
        """All FIFA players at a club (any spelling of the club name)."""
        players = self.data.resolve_club_players(club)
        if not players:
            return {
                "summary": f"No FIFA players found for club {club!r}",
                "players": [],
            }
        overalls = [p.overall for p in players if p.overall is not None]
        avg = round(sum(overalls) / len(overalls), 1) if overalls else None
        summary = f"{players[0].club}: {len(players)} players, average rating {avg}"
        return {
            "summary": summary,
            "club": players[0].club,
            "player_count": len(players),
            "average_overall": avg,
            "players": [p.to_dict() for p in players[: max(1, min(limit, MAX_LIMIT))]],
        }

    def brazilian_players_by_club(self, limit: int = 20) -> dict[str, Any]:
        """Brazilian players grouped by the club they play for."""
        by_club: dict[str, list[Any]] = defaultdict(list)
        for player in self.data.players:
            if (player.nationality or "").casefold() == "brazil" and player.club:
                by_club[player.club].append(player)
        rows = []
        for club, players in by_club.items():
            overalls = [p.overall for p in players if p.overall is not None]
            rows.append(
                {
                    "club": club,
                    "players": len(players),
                    "average_overall": round(sum(overalls) / len(overalls), 1) if overalls else None,
                    "top_player": max(players, key=lambda p: p.overall or 0).name,
                }
            )
        rows.sort(key=lambda row: (-row["players"], -row["average_overall"] or 0))
        page = rows[: max(1, min(limit, MAX_LIMIT))]
        summary = f"Brazilian players at {len(by_club)} clubs"
        return {"summary": summary, "club_count": len(by_club), "clubs": page}

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------

    def competition_info(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict[str, Any]:
        """Competitions and seasons available in the datasets."""
        match_counts: dict[str, int] = defaultdict(int)
        seasons_by_comp: dict[str, set[int]] = defaultdict(set)
        for match in self.data.primary_matches:
            match_counts[match.competition] += 1
            if match.season:
                seasons_by_comp[match.competition].add(match.season)

        wanted = None
        if competition:
            wanted = normalize_competition(competition)
            if wanted not in KNOWN_COMPETITIONS and wanted not in match_counts:
                raise ValueError(
                    f"Unknown competition: {competition!r}. Known: {KNOWN_COMPETITIONS}"
                )
        comps = set(match_counts)
        if wanted:
            comps = {c for c in comps if c == wanted}
        if season:
            comps = {c for c in comps if season in seasons_by_comp.get(c, set())}

        payload = {
            comp: {
                "seasons": sorted(seasons_by_comp.get(comp, set())),
                "season_count": len(seasons_by_comp.get(comp, set())),
                "matches": match_counts[comp],
            }
            for comp in sorted(comps)
        }
        return {
            "summary": f"{len(payload)} competition(s) available",
            "competitions": payload,
        }

    def standings(
        self,
        competition: str,
        season: int,
        relegated_count: int = 4,
        promoted_count: int = 4,
    ) -> dict[str, Any]:
        """League table computed from match results for one season."""
        wanted = normalize_competition(competition)
        if wanted not in KNOWN_COMPETITIONS:
            raise ValueError(
                f"Unknown competition: {competition!r}. Known: {KNOWN_COMPETITIONS}"
            )
        matches = [
            m
            for m in self.data.primary_matches
            if m.competition == wanted and m.season == season and m.is_played
        ]
        if not matches:
            raise ValueError(f"No data for {wanted} season {season}.")

        table: dict[str, dict[str, Any]] = {}
        for match in matches:
            for team in (match.home_team, match.away_team):
                table.setdefault(
                    team,
                    {
                        "team": team,
                        "points": 0,
                        "wins": 0,
                        "draws": 0,
                        "losses": 0,
                        "goals_for": 0,
                        "goals_against": 0,
                        "played": 0,
                    },
                )
            home = table[match.home_team]
            away = table[match.away_team]
            home["played"] += 1
            away["played"] += 1
            home["goals_for"] += match.home_goals
            home["goals_against"] += match.away_goals
            away["goals_for"] += match.away_goals
            away["goals_against"] += match.home_goals
            if match.home_goals > match.away_goals:
                home["wins"] += 1
                home["points"] += 3
                away["losses"] += 1
            elif match.home_goals < match.away_goals:
                away["wins"] += 1
                away["points"] += 3
                home["losses"] += 1
            else:
                home["draws"] += 1
                away["draws"] += 1
                home["points"] += 1
                away["points"] += 1

        rows = sorted(
            table.values(),
            key=lambda row: (
                -row["points"],
                -(row["goals_for"] - row["goals_against"]),
                -row["goals_for"],
                row["team"],
            ),
        )
        for position, row in enumerate(rows, start=1):
            row["position"] = position
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
            row["note"] = ""
        if rows:
            rows[0]["note"] = "Champion"
        for row in rows[-relegated_count:]:
            if row["position"] != 1:
                row["note"] = (row["note"] + " Relegated").strip()
        for row in rows[:promoted_count]:
            if wanted in ("Brasileirão Série B", "Brasileirão Série C"):
                row["note"] = (row["note"] + " Promotion spot").strip()

        champion = rows[0]["team"] if rows else None
        teams = len(rows)
        expected = teams * (teams - 1) if teams > 1 else None
        caveat = ""
        if expected and len(matches) < expected:
            caveat = (
                f" Note: season data is incomplete ({len(matches)} of ~{expected} matches "
                f"available in the provided datasets)."
            )
        summary = (
            f"{wanted} {season} standings computed from {len(matches)} matches: "
            f"champion {champion} with {rows[0]['points']} pts"
            if rows
            else f"No standings for {wanted} {season}"
        ) + caveat
        return {
            "summary": summary,
            "competition": wanted,
            "season": season,
            "matches_used": len(matches),
            "expected_matches": expected,
            "complete": not (expected and len(matches) < expected),
            "champion": champion,
            "relegated": [row["team"] for row in rows[-relegated_count:]],
            "table": rows,
        }

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------

    def stats_summary(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> dict[str, Any]:
        """Goals-per-match averages and home/away/draw rates."""
        matches = self._filter_matches(self.data.primary_matches, competition, season)
        played = [m for m in matches if m.is_played]
        if not played:
            return {"summary": "No matches found for the given filters."}
        total_goals = sum(m.total_goals for m in played)
        home_wins = sum(1 for m in played if m.home_goals > m.away_goals)
        away_wins = sum(1 for m in played if m.home_goals < m.away_goals)
        draws = len(played) - home_wins - away_wins
        label = competition or "all competitions"
        if season:
            label += f" {season}"
        summary = (
            f"{label}: {len(played)} matches, "
            f"{total_goals / len(played):.2f} goals per match, "
            f"home win rate {_fmt_pct(home_wins / len(played))}%, "
            f"draw rate {_fmt_pct(draws / len(played))}%, "
            f"away win rate {_fmt_pct(away_wins / len(played))}%"
        )
        return {
            "summary": summary,
            "competition": competition,
            "season": season,
            "matches": len(played),
            "total_goals": total_goals,
            "average_goals_per_match": round(total_goals / len(played), 2),
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": _fmt_pct(home_wins / len(played)),
            "away_win_rate": _fmt_pct(away_wins / len(played)),
            "draw_rate": _fmt_pct(draws / len(played)),
        }

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Largest goal-margin victories in the dataset."""
        matches = self._filter_matches(self.data.primary_matches, competition, season)
        played = [m for m in matches if m.is_played]
        played.sort(key=lambda m: (-(m.goal_margin or 0), m.date or date.min))
        limit = max(1, min(limit, MAX_LIMIT))
        page = played[:limit]
        lines = [
            f"{m.date.isoformat() if m.date else 'unknown'}: "
            f"{m.winner()} won {m.home_goals}-{m.away_goals} "
            f"({m.home_team} vs {m.away_team}, {m.competition})"
            for m in page
        ]
        summary = f"Biggest wins ({competition or 'all competitions'})" + (
            f" {season}" if season else ""
        )
        return {
            "summary": summary,
            "matches": [m.to_dict() for m in page],
            "match_lines": lines,
        }

    def best_records(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: str = "home",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Teams with the best win rate, home or away."""
        if venue not in ("home", "away"):
            raise ValueError("venue must be 'home' or 'away'")
        matches = self._filter_matches(self.data.primary_matches, competition, season)
        by_team: dict[str, list[Match]] = defaultdict(list)
        for match in matches:
            if not match.is_played:
                continue
            team = match.home_team if venue == "home" else match.away_team
            by_team[team].append(match)
        records = []
        minimum = 5
        for team, team_matches in by_team.items():
            record = self._record(team_matches, team)
            if record["matches"] >= minimum:
                record["points_per_game"] = (
                    round((record["wins"] * 3 + record["draws"]) / record["matches"], 2)
                    if record["matches"]
                    else None
                )
                records.append(record)
        records.sort(
            key=lambda r: (
                -(r["wins"] / r["matches"] if r["matches"] else 0),
                -r["wins"],
                r["team"],
            )
        )
        limit = max(1, min(limit, MAX_LIMIT))
        page = records[:limit]
        label = f"best {venue} records"
        if competition:
            label += f" in {competition}"
        if season:
            label += f" {season}"
        return {
            "summary": f"Teams with the {label} (min {minimum} matches)",
            "venue": venue,
            "records": page,
        }

    def season_comparison(self, first_season: int, second_season: int, competition: Optional[str] = None) -> dict[str, Any]:
        """Compare aggregate statistics between two seasons."""
        comp = normalize_competition(competition) if competition else None
        stats_a = self.stats_summary(comp, first_season)
        stats_b = self.stats_summary(comp, second_season)

        def safe(value: Any, default: Any = None) -> Any:
            return value if value is not None else default

        delta_goals = None
        if stats_a.get("matches") and stats_b.get("matches"):
            delta_goals = round(
                stats_b["average_goals_per_match"] - stats_a["average_goals_per_match"], 2
            )
        summary = (
            f"Season comparison {first_season} vs {second_season}"
            + (f" ({comp})" if comp else "")
            + f": goals per match {safe(stats_a.get('average_goals_per_match'))} -> "
            f"{safe(stats_b.get('average_goals_per_match'))}"
        )
        return {
            "summary": summary,
            "season_a": { "season": first_season, **{k: v for k, v in stats_a.items() if k != "summary"} },
            "season_b": { "season": second_season, **{k: v for k, v in stats_b.items() if k != "summary"} },
            "average_goals_delta": delta_goals,
        }
