"""Query engine answering match, team, player, competition, and stats questions."""

from __future__ import annotations

from collections import defaultdict

from .data_loader import COMPETITION_ALIASES, Dataset, Match, Player
from .normalize import (
    DERBIES,
    club_alias,
    derby_name,
    identity_key,
    parse_date,
    text_key,
)

POSITION_CATEGORIES = {
    "goalkeeper": {"GK"},
    "defender": {"LB", "LWB", "CB", "LCB", "RCB", "RB", "RWB"},
    "midfielder": {"CDM", "LDM", "RDM", "CM", "LCM", "RCM", "LM", "RM",
                   "CAM", "LAM", "RAM"},
    "forward": {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"},
}

DEFAULT_MATCH_LIMIT = 20
DEFAULT_PLAYER_LIMIT = 25


class QueryEngine:
    """Answer structured queries over the loaded dataset."""

    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_competition(self, competition: str | None) -> str | None:
        """Map a user competition label onto the canonical one (or None)."""
        if not competition:
            return None
        return COMPETITION_ALIASES.get(text_key(competition), competition.strip())

    def _date_range(
        self, date_from: str | None, date_to: str | None
    ) -> tuple[str | None, str | None]:
        lo = parse_date(date_from)
        hi = parse_date(date_to)
        return (lo.isoformat() if lo else None, hi.isoformat() if hi else None)

    @staticmethod
    def _match_team(match: Match, team: str) -> str | None:
        if match.home_team == team:
            return "home"
        if match.away_team == team:
            return "away"
        return None

    @staticmethod
    def _match_line(match: Match) -> str:
        """Human-readable one-line summary of a match."""
        home = str(match.home_goals) if match.home_goals is not None else "?"
        away = str(match.away_goals) if match.away_goals is not None else "?"
        label = match.competition
        if match.stage:
            label += f" {match.stage.title()}"
        elif match.round:
            label += f" Round {match.round}"
        return (
            f"{match.date or 'unknown date'}: "
            f"{match.home_team} {home}-{away} {match.away_team} ({label})"
        )

    @staticmethod
    def _record(matches: list[Match], team: str) -> dict:
        """W/D/L, GF/GA record for one team across matches."""
        wins = draws = losses = goals_for = goals_against = 0
        played = 0
        for match in matches:
            if match.home_goals is None or match.away_goals is None:
                continue
            played += 1
            if match.home_team == team:
                gf, ga = match.home_goals, match.away_goals
            elif match.away_team == team:
                gf, ga = match.away_goals, match.home_goals
            else:
                continue
            goals_for += gf
            goals_against += ga
            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                draws += 1
        return {
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "win_rate": round(wins / played * 100, 1) if played else 0.0,
        }

    @staticmethod
    def _pair_record(matches: list[Match], team_a: str, team_b: str) -> dict:
        """Head-to-head W/D/L for team_a vs team_b from matches."""
        record = {"team_a": team_a, "team_b": team_b, "team_a_wins": 0,
                  "team_b_wins": 0, "draws": 0}
        for match in matches:
            if match.home_goals is None or match.away_goals is None:
                continue
            pair = {match.home_team, match.away_team}
            if pair != {team_a, team_b}:
                continue
            home_goals, away_goals = match.home_goals, match.away_goals
            if home_goals == away_goals:
                record["draws"] += 1
            else:
                winner = match.home_team if home_goals > away_goals else match.away_team
                if winner == team_a:
                    record["team_a_wins"] += 1
                else:
                    record["team_b_wins"] += 1
        return record

    def _h2h_matches(self, team_a: str, team_b: str) -> list[Match]:
        a = self.dataset.resolve_team(team_a)
        b = self.dataset.resolve_team(team_b)
        return [
            m for m in self.dataset.matches_for_team(a)
            if b in (m.home_team, m.away_team)
        ]

    @staticmethod
    def _filtered_record_summary(matches: list[Match], team: str) -> dict | None:
        """Record of `team` inside an arbitrary filtered match list."""
        if not team:
            return None
        record = QueryEngine._record(
            [m for m in matches if team in (m.home_team, m.away_team)], team
        )
        return record if record["played"] else None

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        round_or_stage: str | None = None,
        limit: int = DEFAULT_MATCH_LIMIT,
    ) -> dict:
        """Find matches by team/opponent/competition/season/date range."""
        canonical_team = self.dataset.resolve_team(team) if team else None
        canonical_opponent = self.dataset.resolve_team(opponent) if opponent else None
        if canonical_opponent and not canonical_team:
            canonical_team, canonical_opponent = canonical_opponent, None

        if canonical_team and canonical_opponent:
            pool = self._h2h_matches(canonical_team, canonical_opponent)
        elif canonical_team:
            pool = self.dataset.matches_for_team(canonical_team)
        else:
            pool = self.dataset.matches

        comp = self._resolve_competition(competition)
        lo, hi = self._date_range(date_from, date_to)
        stage_key = text_key(round_or_stage) if round_or_stage else None

        def stage_label(match: Match) -> str:
            if match.stage:
                return text_key(match.stage)
            if match.round:
                return text_key(f"round {match.round}")
            return ""

        def stage_ok(match: Match) -> bool:
            label = stage_label(match)
            return bool(label) and (
                label == stage_key or stage_key in label
            )

        results: list[Match] = []
        for match in pool:
            if comp and match.competition != comp:
                continue
            if season is not None and match.season != season:
                continue
            if lo and (not match.date or match.date < lo):
                continue
            if hi and (not match.date or match.date > hi):
                continue
            if stage_key and not stage_ok(match):
                continue
            results.append(match)

        if stage_key:
            # "final" should mean finals, not semifinals: keep exact matches
            # when any exist, otherwise fall back to substring matches.
            exact = [m for m in results if stage_label(m) == stage_key]
            if exact:
                results = exact

        results.sort(key=lambda m: (m.date or ""), reverse=True)
        total = len(results)
        shown = results[: max(1, limit)]

        summary: dict = {}
        if canonical_team and canonical_opponent:
            summary = self._pair_record(results, canonical_team, canonical_opponent)
        elif canonical_team:
            record = self._filtered_record_summary(results, canonical_team)
            if record:
                summary = {"team": canonical_team, **record}

        return {
            "query": {
                "team": canonical_team,
                "opponent": canonical_opponent,
                "competition": comp,
                "season": season,
                "date_from": lo,
                "date_to": hi,
                "round_or_stage": round_or_stage,
            },
            "total_matches": total,
            "returned": len(shown),
            "note": (
                f"Showing {len(shown)} of {total} matches. Increase limit to see more."
                if total > len(shown)
                else None
            ),
            "matches": [
                {**m.to_dict(), "line": self._match_line(m)} for m in shown
            ],
            "summary": summary or None,
        }

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------

    def get_team_stats(
        self,
        team: str,
        competition: str | None = None,
        season: int | None = None,
        venue: str | None = None,
    ) -> dict:
        """W/D/L record, goals, and win rate for one team."""
        canonical = self.dataset.resolve_team(team)
        comp = self._resolve_competition(competition)
        matches = self.dataset.matches_for_team(canonical)
        if comp:
            matches = [m for m in matches if m.competition == comp]
        if season is not None:
            matches = [m for m in matches if m.season == season]

        venue_norm = (venue or "all").lower()
        if venue_norm not in {"all", "home", "away"}:
            venue_norm = "all"
        selected = [
            m for m in matches
            if venue_norm == "all"
            or (venue_norm == "home" and m.home_team == canonical)
            or (venue_norm == "away" and m.away_team == canonical)
        ]

        competitions_played = sorted({m.competition for m in matches})
        seasons_played = sorted({m.season for m in matches if m.season})

        return {
            "team": canonical,
            "competition": comp or "all",
            "season": season,
            "venue": venue_norm,
            "record": self._record(selected, canonical),
            "competitions_played": competitions_played,
            "seasons_played": seasons_played,
        }

    def head_to_head(self, team_a: str, team_b: str) -> dict:
        """Head-to-head record plus the most recent meetings."""
        a = self.dataset.resolve_team(team_a)
        b = self.dataset.resolve_team(team_b)
        matches = self._h2h_matches(a, b)
        matches.sort(key=lambda m: (m.date or ""), reverse=True)
        return {
            "team_a": a,
            "team_b": b,
            "derby": derby_name(a, b),
            "record": self._pair_record(matches, a, b),
            "last_meeting": self._match_line(matches[0]) if matches else None,
            "recent_matches": [
                {**m.to_dict(), "line": self._match_line(m)} for m in matches[:5]
            ],
        }

    def get_team_competitions(self, team: str) -> dict:
        """Which competitions (and seasons) a team appears in across all files."""
        canonical = self.dataset.resolve_team(team)
        matches = self.dataset.matches_for_team(canonical)
        counts: dict[str, int] = defaultdict(int)
        seasons_by_comp: dict[str, set[int]] = defaultdict(set)
        for match in matches:
            counts[match.competition] += 1
            if match.season:
                seasons_by_comp[match.competition].add(match.season)
        return {
            "team": canonical,
            "total_matches": len(matches),
            "competitions": {
                comp: {
                    "matches": counts[comp],
                    "seasons": sorted(seasons_by_comp[comp]),
                }
                for comp in sorted(counts)
            },
        }

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        position_category: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = DEFAULT_PLAYER_LIMIT,
    ) -> dict:
        """Search FIFA player data by name/nationality/club/position/rating."""
        name_key = text_key(name) if name else None
        name_tokens = set(name_key.split()) if name_key else None
        nat_key = text_key(nationality) if nationality else None
        positions: set[str] | None = None
        if position:
            positions = {position.strip().upper()}
        elif position_category:
            category = position_category.strip().lower()
            positions = POSITION_CATEGORIES.get(category)
            if positions is None:
                return {
                    "error": (
                        f"Unknown position category '{position_category}'. "
                        f"Options: {sorted(POSITION_CATEGORIES)}"
                    )
                }

        candidates = self.dataset.players
        if club:
            candidates = self._match_club(candidates, club)

        results: list[Player] = []
        for player in candidates:
            if name_key:
                player_key = text_key(player.name)
                player_tokens = set(player_key.split())
                if not (name_tokens <= player_tokens or name_key in player_key):
                    continue
            if nat_key:
                player_nat = text_key(player.nationality)
                if nat_key not in player_nat and player_nat not in nat_key:
                    continue
            if positions and player.position not in positions:
                continue
            if min_overall is not None and player.overall < min_overall:
                continue
            if max_overall is not None and player.overall > max_overall:
                continue
            results.append(player)

        results.sort(key=lambda p: (-p.overall, p.name))
        total = len(results)
        shown = results[: max(1, limit)]

        by_club: dict[str, list[int]] = defaultdict(list)
        if nat_key and not club:
            for player in results:
                if player.club:
                    by_club[player.club].append(player.overall)
            club_summary = [
                {
                    "club": club_name,
                    "players": len(ratings),
                    "avg_overall": round(sum(ratings) / len(ratings), 1),
                }
                for club_name, ratings in sorted(
                    by_club.items(), key=lambda kv: -len(kv[1])
                )[:10]
            ]
        else:
            club_summary = None

        return {
            "query": {
                "name": name,
                "nationality": nationality,
                "club": club,
                "position": position,
                "position_category": position_category,
                "min_overall": min_overall,
                "max_overall": max_overall,
            },
            "matched_clubs": sorted({p.club for p in candidates})[:10] if club else None,
            "total_players": total,
            "returned": len(shown),
            "players": [self._player_dict(p) for p in shown],
            "clubs_with_brazilian_players": club_summary,
        }

    @staticmethod
    def _match_club(players: list[Player], club: str) -> list[Player]:
        """Filter players by club with exact > prefix > contains ranking.

        FIFA spellings ("Sport Club do Recife") are aliased onto the
        canonical match-data names ("Sport Recife") and count as exact.
        """
        wanted = text_key(club)
        alias = club_alias(club)
        alias_key = text_key(alias) if alias else None
        exact: list[Player] = []
        prefix: list[Player] = []
        contains: list[Player] = []
        for player in players:
            player_club = text_key(player.club)
            if not player_club:
                continue
            player_alias = club_alias(player.club)
            aliased = bool(alias) and (
                player_alias == alias
                or (alias_key and player_club == alias_key)
            )
            if player_club == wanted or aliased:
                exact.append(player)
            elif player_club.startswith(wanted):
                prefix.append(player)
            elif wanted in player_club:
                contains.append(player)
        return exact + prefix + contains

    @staticmethod
    def _player_dict(player: Player) -> dict:
        data = player.to_dict()
        data.pop("skills")
        return data

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------

    def get_standings(self, competition: str, season: int) -> dict:
        """League table calculated from match results for one season."""
        comp = self._resolve_competition(competition)
        if not comp:
            return {"error": "competition is required"}
        matches = [
            m for m in self.dataset.matches
            if m.competition == comp
            and m.season == season
            and m.home_goals is not None
            and m.away_goals is not None
        ]
        if not matches:
            return {
                "error": (
                    f"No completed {comp} matches found for season {season}."
                )
            }

        table: dict[str, dict] = {}
        for match in matches:
            for team, gf, ga in (
                (match.home_team, match.home_goals, match.away_goals),
                (match.away_team, match.away_goals, match.home_goals),
            ):
                row = table.setdefault(
                    team,
                    {
                        "team": team, "played": 0, "wins": 0, "draws": 0,
                        "losses": 0, "goals_for": 0, "goals_against": 0,
                    },
                )
                row["played"] += 1
                row["goals_for"] += gf
                row["goals_against"] += ga
                if gf > ga:
                    row["wins"] += 1
                elif gf < ga:
                    row["losses"] += 1
                else:
                    row["draws"] += 1

        rows = sorted(
            table.values(),
            key=lambda r: (
                3 * r["wins"] + r["draws"],
                r["wins"],
                r["goals_for"] - r["goals_against"],
                r["goals_for"],
                r["team"],
            ),
            reverse=True,
        )
        standings = []
        for position, row in enumerate(rows, start=1):
            points = 3 * row["wins"] + row["draws"]
            note = "Champion" if position == 1 else None
            standings.append(
                {
                    "position": position,
                    **row,
                    "goal_difference": row["goals_for"] - row["goals_against"],
                    "points": points,
                    "note": note,
                }
            )
        if len(rows) == 20:
            for row in standings[-4:]:
                row["note"] = "Relegation zone"

        matches_per_team = {row["played"] for row in rows}
        complete = len(matches_per_team) == 1
        return {
            "competition": comp,
            "season": season,
            "matches_used": len(matches),
            "teams": len(rows),
            "table_complete": complete,
            "note": None if complete else (
                "Season appears incomplete in the dataset (teams played a "
                "varying number of matches); positions are indicative only."
            ),
            "standings": standings,
        }

    def get_season_summary(self, season: int) -> dict:
        """Aggregate statistics for one season across competitions."""
        return self._season_summary(season)

    def compare_seasons(self, season_a: int, season_b: int) -> dict:
        """Side-by-side aggregate statistics for two seasons."""
        return {
            "season_a": self._season_summary(season_a),
            "season_b": self._season_summary(season_b),
        }

    def _season_summary(self, season: int) -> dict:
        by_comp: dict[str, list[Match]] = defaultdict(list)
        for match in self.dataset.matches:
            if match.season == season:
                by_comp[match.competition].append(match)

        champions = {}
        for comp in ("Brasileirão", "Serie B", "Serie C"):
            standings = self.get_standings(comp, season)
            if "error" not in standings and standings["standings"]:
                top = standings["standings"][0]
                champions[comp] = {
                    "team": top["team"],
                    "points": top["points"],
                    "record": (
                        f"{top['wins']}W {top['draws']}D {top['losses']}L"
                    ),
                }

        competitions = {}
        for comp, comp_matches in sorted(by_comp.items()):
            with_goals = [
                m for m in comp_matches
                if m.home_goals is not None and m.away_goals is not None
            ]
            total_goals = sum(m.home_goals + m.away_goals for m in with_goals)
            home_wins = sum(
                1 for m in with_goals if m.home_goals > m.away_goals
            )
            draws = sum(1 for m in with_goals if m.home_goals == m.away_goals)
            competitions[comp] = {
                "matches": len(with_goals),
                "total_goals": total_goals,
                "avg_goals_per_match": (
                    round(total_goals / len(with_goals), 2) if with_goals else None
                ),
                "home_win_rate": (
                    round(home_wins / len(with_goals) * 100, 1)
                    if with_goals else None
                ),
                "draw_rate": (
                    round(draws / len(with_goals) * 100, 1) if with_goals else None
                ),
            }
        return {"season": season, "competitions": competitions,
                "champions": champions or None}

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------

    def get_competition_stats(
        self,
        competition: str | None = None,
        season: int | None = None,
        top: int = 5,
    ) -> dict:
        """Aggregate statistics: goals, home advantage, biggest wins."""
        comp = self._resolve_competition(competition)
        matches = self.dataset.matches
        if comp:
            matches = [m for m in matches if m.competition == comp]
        if season is not None:
            matches = [m for m in matches if m.season == season]
        with_goals = [
            m for m in matches
            if m.home_goals is not None and m.away_goals is not None
        ]

        total_goals = sum(m.home_goals + m.away_goals for m in with_goals)
        home_wins = sum(1 for m in with_goals if m.home_goals > m.away_goals)
        away_wins = sum(1 for m in with_goals if m.home_goals < m.away_goals)
        draws = sum(1 for m in with_goals if m.home_goals == m.away_goals)

        biggest = sorted(
            with_goals,
            key=lambda m: abs(m.home_goals - m.away_goals),
            reverse=True,
        )[: max(1, top)]

        return {
            "competition": comp or "all",
            "season": season,
            "matches": len(with_goals),
            "avg_goals_per_match": (
                round(total_goals / len(with_goals), 2) if with_goals else None
            ),
            "home_win_rate": (
                round(home_wins / len(with_goals) * 100, 1) if with_goals else None
            ),
            "away_win_rate": (
                round(away_wins / len(with_goals) * 100, 1) if with_goals else None
            ),
            "draw_rate": (
                round(draws / len(with_goals) * 100, 1) if with_goals else None
            ),
            "top_scoring_teams": self._top_scoring_teams(with_goals, top),
            "biggest_wins": [self._match_line(m) for m in biggest],
        }

    @staticmethod
    def _top_scoring_teams(matches: list[Match], top: int) -> list[dict]:
        goals: dict[str, int] = defaultdict(int)
        for match in matches:
            goals[match.home_team] += match.home_goals
            goals[match.away_team] += match.away_goals
        ranked = sorted(goals.items(), key=lambda kv: -kv[1])[: max(1, top)]
        return [{"team": team, "goals": count} for team, count in ranked]

    def get_best_records(
        self,
        venue: str = "home",
        competition: str | None = None,
        season: int | None = None,
        min_matches: int = 5,
        limit: int = 5,
    ) -> dict:
        """Rank teams by win rate at a venue for the given filters."""
        venue_norm = venue.lower()
        if venue_norm not in {"home", "away"}:
            return {"error": "venue must be 'home' or 'away'"}
        comp = self._resolve_competition(competition)
        matches = self.dataset.matches
        if comp:
            matches = [m for m in matches if m.competition == comp]
        if season is not None:
            matches = [m for m in matches if m.season == season]

        per_team: dict[str, list[Match]] = defaultdict(list)
        for match in matches:
            if venue_norm == "home":
                per_team[match.home_team].append(match)
            else:
                per_team[match.away_team].append(match)

        rankings = []
        for team, team_matches in per_team.items():
            record = self._record(team_matches, team)
            if record["played"] < max(1, min_matches):
                continue
            rankings.append({"team": team, **record})
        rankings.sort(
            key=lambda r: (
                -r["win_rate"],
                -(r["wins"] - r["losses"]),
                r["team"],
            )
        )
        return {
            "venue": venue_norm,
            "competition": comp or "all",
            "season": season,
            "min_matches": min_matches,
            "rankings": rankings[: max(1, limit)],
        }

    def search_derbies(
        self,
        season: int | None = None,
        competition: str | None = None,
        limit: int = DEFAULT_MATCH_LIMIT,
    ) -> dict:
        """Find traditional rivalry matches (Fla-Flu, Gre-Nal, ...)."""
        comp = self._resolve_competition(competition)
        derby_keys = {
            frozenset((identity_key(a), identity_key(b))) for (a, b) in DERBIES
        }
        results = []
        for match in self.dataset.matches:
            if comp and match.competition != comp:
                continue
            if season is not None and match.season != season:
                continue
            pair = frozenset(
                (identity_key(match.home_team), identity_key(match.away_team))
            )
            if pair not in derby_keys:
                continue
            results.append(match)
        results.sort(key=lambda m: (m.date or ""), reverse=True)
        total = len(results)
        shown = results[: max(1, limit)]
        return {
            "query": {"season": season, "competition": comp},
            "total_matches": total,
            "returned": len(shown),
            "matches": [
                {**m.to_dict(), "line": self._match_line(m),
                 "derby": derby_name(m.home_team, m.away_team)}
                for m in shown
            ],
        }

    # ------------------------------------------------------------------
    # Cross-file queries
    # ------------------------------------------------------------------

    def get_club_overview(self, team: str) -> dict:
        """Cross-file view: match record + FIFA squad for one club."""
        canonical = self.dataset.resolve_team(team)
        matches = self.dataset.matches_for_team(canonical)
        stats = self.get_team_stats(canonical)

        players = self._match_club(self.dataset.players, canonical)
        matched_clubs = sorted({p.club for p in players})

        players.sort(key=lambda p: -p.overall)
        recent_seasons = sorted(
            {m.season for m in matches if m.season}, reverse=True
        )
        recent = None
        if recent_seasons:
            season = recent_seasons[0]
            season_matches = [m for m in matches if m.season == season]
            recent = {"season": season, "record": self._record(
                season_matches, canonical
            )}

        return {
            "team": canonical,
            "all_time_record": stats["record"],
            "competitions_played": stats["competitions_played"],
            "most_recent_season": recent,
            "fifa_squad": {
                "matched_clubs": matched_clubs,
                "player_count": len(players),
                "avg_overall": (
                    round(sum(p.overall for p in players) / len(players), 1)
                    if players else None
                ),
                "top_players": [self._player_dict(p) for p in players[:10]],
            },
        }

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def list_teams(self, competition: str | None = None, limit: int | None = None) -> dict:
        """Teams present in the match data, with match counts."""
        comp = self._resolve_competition(competition)
        teams: dict[str, int] = {}
        for match in self.dataset.matches:
            if comp and match.competition != comp:
                continue
            teams[match.home_team] = teams.get(match.home_team, 0) + 1
            teams[match.away_team] = teams.get(match.away_team, 0) + 1
        ranked = sorted(teams.items(), key=lambda kv: (-kv[1], kv[0]))
        if limit:
            ranked = ranked[: max(1, limit)]
        return {
            "competition": comp or "all",
            "team_count": len(teams),
            "teams": [{"team": name, "matches": count} for name, count in ranked],
        }

    def list_competitions(self) -> dict:
        """Competitions, match counts, and season coverage."""
        comps = self.dataset.competitions()
        return {
            "competitions": [
                {
                    "competition": name,
                    "matches": info["matches"],
                    "seasons": info["seasons"],
                    "season_range": (
                        f"{info['seasons'][0]}-{info['seasons'][-1]}"
                        if info["seasons"] else None
                    ),
                }
                for name, info in sorted(comps.items())
            ]
        }
