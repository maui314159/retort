# SPDX-License-Identifier: Apache-2.0
# Context block ----------------------------------------------------------------
# Module: brazilian_soccer_mcp.queries
# Purpose: High-level query API that the MCP server exposes as tools.
#
# The QueryEngine wraps a DataLoader and exposes pure functions for each of
# the five required capability categories from the spec:
#   1. Match queries     (by team, date range, competition, season)
#   2. Team queries      (statistics, head-to-head, performance)
#   3. Player queries    (search, nationality, club, ratings)
#   4. Competition queries (standings, schedules)
#   5. Statistical analysis (averages, biggest wins, trends)
#
# All query methods return plain dicts/lists so they can be JSON-serialized
# straight onto the MCP tool response wire.
# --------------------------------------------------------------------------- #
"""Query engine for Brazilian soccer data."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from datetime import date, datetime

from brazilian_soccer_mcp.data_loader import DataLoader
from brazilian_soccer_mcp.models import HeadToHead, Match, Player, Standing, TeamStats
from brazilian_soccer_mcp.team_normalize import (
    is_derby,
    normalize_team,
    team_display_name,
)


def _ascii_lower(s: str) -> str:
    """Lowercase + strip accents, for accent-insensitive competition matching."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower().strip()


def _team_display(key: str, fallback: str = "") -> str:
    """Prefer the raw display name when supplied, else canonical display."""
    if fallback:
        return fallback
    return team_display_name(key) or key


def _match_to_dict(m: Match) -> dict:
    return {
        "date": m.date.isoformat() if m.date else None,
        "datetime": m.datetime.isoformat() if m.datetime else None,
        "home_team": m.home_team,
        "away_team": m.away_team,
        "home_team_key": m.home_team_key,
        "away_team_key": m.away_team_key,
        "score": m.score_str,
        "home_goal": m.home_goal,
        "away_goal": m.away_goal,
        "competition": m.competition,
        "season": m.season,
        "round": m.round_info,
        "stage": m.stage,
        "stadium": m.stadium,
        "source_file": m.source_file,
    }


def _player_to_dict(p: Player, include_attributes: bool = False) -> dict:
    out = {
        "id": p.player_id,
        "name": p.name,
        "age": p.age,
        "nationality": p.nationality,
        "overall": p.overall,
        "potential": p.potential,
        "club": p.club,
        "club_key": p.club_key,
        "position": p.position,
        "jersey_number": p.jersey_number,
        "height": p.height,
        "weight": p.weight,
        "preferred_foot": p.preferred_foot,
        "value": p.value,
        "wage": p.wage,
    }
    if include_attributes:
        out["attributes"] = p.attributes
    return out


class QueryEngine:
    """Stateless-ish query layer over a DataLoader.

    Construct once per process; all query methods are read-only and safe to
    call concurrently.
    """

    def __init__(self, loader: DataLoader | None = None) -> None:
        self.loader = loader or DataLoader()
        self.loader.load_all()
        # Pre-index matches by canonical team key for O(1) team lookups.
        self._matches_by_team: dict[str, list[Match]] = defaultdict(list)
        for m in self.loader.matches:
            if m.home_team_key:
                self._matches_by_team[m.home_team_key].append(m)
            if m.away_team_key and m.away_team_key != m.home_team_key:
                self._matches_by_team[m.away_team_key].append(m)
        # Pre-index players by club key.
        self._players_by_club: dict[str, list[Player]] = defaultdict(list)
        for p in self.loader.players:
            if p.club_key:
                self._players_by_club[p.club_key].append(p)

    # ------------------------------------------------------------------ #
    # 1. MATCH QUERIES
    # ------------------------------------------------------------------ #

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Find matches by team / opponent / competition / season / date range.

        Args:
            team: team name (any spelling) -- matches where this team played
                (home OR away).
            opponent: optional opponent team name; ignored if team is None.
            competition: case-insensitive competition name substring
                (e.g. "brasileirao", "libertadores", "copa do brasil").
            season: 4-digit season year.
            start_date / end_date: ISO ``YYYY-MM-DD`` inclusive bounds.
            limit: max matches to return (most recent first).
        """
        team_key = normalize_team(team) if team else None
        opp_key = normalize_team(opponent) if opponent else None
        comp_filter = _ascii_lower(competition) if competition else None
        start = _parse_iso_date(start_date)
        end = _parse_iso_date(end_date)

        if team_key:
            candidates = list(self._matches_by_team.get(team_key, []))
        else:
            candidates = list(self.loader.matches)

        results: list[Match] = []
        for m in candidates:
            if opp_key:
                sides = {m.home_team_key, m.away_team_key}
                if team_key and opp_key not in sides:
                    continue
                if not team_key and opp_key not in sides:
                    continue
            if comp_filter:
                if comp_filter not in _ascii_lower(m.competition):
                    continue
            if season is not None and m.season != season:
                continue
            if start and (m.date is None or m.date < start):
                continue
            if end and (m.date is None or m.date > end):
                continue
            results.append(m)

        # Sort most-recent first when dates exist; stable for equal dates.
        results.sort(key=lambda m: (m.date or date.min, m.datetime or datetime.min),
                     reverse=True)
        if limit and limit > 0:
            results = results[:limit]
        return [_match_to_dict(m) for m in results]

    def head_to_head(
        self, team_a: str, team_b: str, competition: str | None = None
    ) -> dict:
        """Head-to-head record between two teams."""
        ka = normalize_team(team_a)
        kb = normalize_team(team_b)
        if not ka or not kb:
            return {"error": "both team_a and team_b are required"}
        h2h = HeadToHead(team_a_key=ka, team_b_key=kb)
        matches: list[Match] = []
        for m in self._matches_by_team.get(ka, []):
            if {m.home_team_key, m.away_team_key} != {ka, kb}:
                continue
            if competition and competition.lower() not in m.competition.lower():
                continue
            matches.append(m)
            if m.home_goal is None or m.away_goal is None:
                continue
            a_is_home = m.home_team_key == ka
            a_goals = m.home_goal if a_is_home else m.away_goal
            b_goals = m.away_goal if a_is_home else m.home_goal
            h2h.team_a_goals += a_goals
            h2h.team_b_goals += b_goals
            h2h.matches += 1
            if a_goals > b_goals:
                h2h.team_a_wins += 1
            elif b_goals > a_goals:
                h2h.team_b_wins += 1
            else:
                h2h.draws += 1
        matches.sort(key=lambda m: (m.date or date.min, m.datetime or datetime.min),
                     reverse=True)
        return {
            "team_a": _team_display(ka, team_a),
            "team_b": _team_display(kb, team_b),
            "team_a_key": ka,
            "team_b_key": kb,
            "is_derby": is_derby(ka, kb),
            "team_a_wins": h2h.team_a_wins,
            "team_b_wins": h2h.team_b_wins,
            "draws": h2h.draws,
            "team_a_goals": h2h.team_a_goals,
            "team_b_goals": h2h.team_b_goals,
            "matches_total": h2h.matches,
            "matches": [_match_to_dict(m) for m in matches[:50]],
        }

    # ------------------------------------------------------------------ #
    # 2. TEAM QUERIES
    # ------------------------------------------------------------------ #

    def team_statistics(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str | None = None,
    ) -> dict:
        """Aggregate win/draw/loss/goal record for a team.

        Args:
            team: team name (any spelling).
            season: optional season filter.
            competition: optional competition name substring filter.
            venue: "home", "away", or None (both).
        """
        key = normalize_team(team)
        if not key:
            return {"error": "team is required"}
        venue_norm = venue.lower().strip() if venue else None
        comp_filter = _ascii_lower(competition) if competition else None

        stats = TeamStats(team_key=key, display_name=_team_display(key, team))
        for m in self._matches_by_team.get(key, []):
            if season is not None and m.season != season:
                continue
            if comp_filter and comp_filter not in _ascii_lower(m.competition):
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            is_home = m.home_team_key == key
            if venue_norm == "home" and not is_home:
                continue
            if venue_norm == "away" and is_home:
                continue
            gf = m.home_goal if is_home else m.away_goal
            ga = m.away_goal if is_home else m.home_goal
            stats.matches += 1
            stats.goals_for += gf
            stats.goals_against += ga
            if is_home:
                stats.home_matches += 1
                stats.home_goals_for += gf
                stats.home_goals_against += ga
            else:
                stats.away_matches += 1
                stats.away_goals_for += gf
                stats.away_goals_against += ga
            if gf > ga:
                stats.wins += 1
                if is_home: stats.home_wins += 1
                else: stats.away_wins += 1
            elif gf < ga:
                stats.losses += 1
                if is_home: stats.home_losses += 1
                else: stats.away_losses += 1
            else:
                stats.draws += 1
                if is_home: stats.home_draws += 1
                else: stats.away_draws += 1
        return _team_stats_to_dict(stats)

    def competitions_for_team(self, team: str) -> dict:
        """List competitions a team appears in, with match counts."""
        key = normalize_team(team)
        if not key:
            return {"error": "team is required"}
        comps: dict[str, int] = defaultdict(int)
        for m in self._matches_by_team.get(key, []):
            comps[m.competition] += 1
        return {
            "team": _team_display(key, team),
            "team_key": key,
            "competitions": [
                {"competition": c, "matches": n}
                for c, n in sorted(comps.items(), key=lambda kv: -kv[1])
            ],
        }

    # ------------------------------------------------------------------ #
    # 3. PLAYER QUERIES
    # ------------------------------------------------------------------ #

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 50,
        sort_by_overall: bool = True,
    ) -> list[dict]:
        """Search FIFA player data by name/nationality/club/position/rating."""
        name_filter = name.lower().strip() if name else None
        nat_filter = nationality.lower().strip() if nationality else None
        club_key = normalize_team(club) if club else None
        pos_filter = position.upper().strip() if position else None

        out: list[Player] = []
        for p in self.loader.players:
            if name_filter and name_filter not in p.name.lower():
                continue
            if nat_filter and nat_filter not in p.nationality.lower():
                continue
            if club_key and p.club_key != club_key:
                # Loosen: also match if the club string contains the raw query.
                if not (club and club.lower() in p.club.lower()):
                    continue
            if pos_filter and (p.position is None or p.position.upper() != pos_filter):
                continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            out.append(p)
        if sort_by_overall:
            out.sort(key=lambda p: (p.overall or 0, p.name), reverse=True)
        if limit and limit > 0:
            out = out[:limit]
        return [_player_to_dict(p, include_attributes=False) for p in out]

    def top_rated_by_nationality(
        self, nationality: str, limit: int = 10
    ) -> list[dict]:
        """Top-rated players for a given nationality."""
        nat = nationality.lower().strip()
        players = [p for p in self.loader.players
                   if nat in p.nationality.lower()]
        players.sort(key=lambda p: (p.overall or 0, p.name), reverse=True)
        return [_player_to_dict(p) for p in players[:limit]]

    def top_rated_by_club(self, club: str, limit: int = 10) -> list[dict]:
        """Top-rated players at a given club."""
        key = normalize_team(club)
        players: list[Player] = []
        for p in self.loader.players:
            if p.club_key == key or (club and club.lower() in p.club.lower()):
                players.append(p)
        players.sort(key=lambda p: (p.overall or 0, p.name), reverse=True)
        return [_player_to_dict(p) for p in players[:limit]]

    # ------------------------------------------------------------------ #
    # 4. COMPETITION QUERIES
    # ------------------------------------------------------------------ #

    def list_competitions(self) -> list[dict]:
        """List competitions and season counts present in the data."""
        comp_seasons: dict[str, set[int | None]] = defaultdict(set)
        comp_counts: dict[str, int] = defaultdict(int)
        for m in self.loader.matches:
            comp_seasons[m.competition].add(m.season)
            comp_counts[m.competition] += 1
        return [
            {
                "competition": c,
                "matches": comp_counts[c],
                "seasons": sorted(s for s in comp_seasons[c] if s is not None),
            }
            for c in sorted(comp_counts)
        ]

    def standings(
        self,
        season: int,
        competition: str = "Brasileirão Série A",
    ) -> list[dict]:
        """Calculate league standings for a season from match results.

        Standings are computed only over competitions that look like
        league tables (Brasileirão). Cup knockouts are not table-shaped;
        asking for them returns an empty list with an explanatory note.
        """
        comp_norm = competition.lower()
        if "libertadores" in comp_norm or "copa do brasil" in comp_norm:
            return [{"note": f"{competition} is a knockout cup; standings are "
                              "not applicable. Use search_matches instead."}]

        rows: dict[str, TeamStats] = {}
        for m in self.loader.matches:
            if m.season != season:
                continue
            if comp_norm not in m.competition.lower():
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            for key in (m.home_team_key, m.away_team_key):
                if key not in rows:
                    rows[key] = TeamStats(team_key=key,
                                          display_name=team_display_name(key))
            home = rows[m.home_team_key]
            away = rows[m.away_team_key]
            hg, ag = m.home_goal, m.away_goal
            home.matches += 1; away.matches += 1
            home.goals_for += hg; home.goals_against += ag
            away.goals_for += ag; away.goals_against += hg
            home.home_matches += 1; away.away_matches += 1
            if hg > ag:
                home.wins += 1; away.losses += 1
            elif ag > hg:
                away.wins += 1; home.losses += 1
            else:
                home.draws += 1; away.draws += 1
        standings = [
            Standing(
                team_key=s.team_key,
                display_name=s.display_name,
                played=s.matches,
                wins=s.wins, draws=s.draws, losses=s.losses,
                goals_for=s.goals_for, goals_against=s.goals_against,
                goal_diff=s.goals_for - s.goals_against,
                points=s.points,
            )
            for s in rows.values()
        ]
        # Sort by points, then goal diff, then goals for.
        standings.sort(key=lambda s: (s.points, s.goal_diff, s.goals_for),
                       reverse=True)
        out = [s.as_dict() for s in standings]
        if out:
            out[0]["champion"] = True
        return out

    # ------------------------------------------------------------------ #
    # 5. STATISTICAL ANALYSIS
    # ------------------------------------------------------------------ #

    def average_goals(
        self,
        competition: str | None = None,
        season: int | None = None,
    ) -> dict:
        """Average goals per match and home/away win rates."""
        comp_filter = _ascii_lower(competition) if competition else None
        total_goals = 0
        total_matches = 0
        home_wins = 0
        away_wins = 0
        draws = 0
        for m in self.loader.matches:
            if comp_filter and comp_filter not in _ascii_lower(m.competition):
                continue
            if season is not None and m.season != season:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            total_matches += 1
            total_goals += m.home_goal + m.away_goal
            if m.home_goal > m.away_goal:
                home_wins += 1
            elif m.away_goal > m.home_goal:
                away_wins += 1
            else:
                draws += 1
        if total_matches == 0:
            return {"average_goals_per_match": 0.0, "total_matches": 0}
        return {
            "average_goals_per_match": round(total_goals / total_matches, 3),
            "total_matches": total_matches,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(home_wins / total_matches, 4),
            "away_win_rate": round(away_wins / total_matches, 4),
            "draw_rate": round(draws / total_matches, 4),
        }

    def biggest_wins(
        self,
        competition: str | None = None,
        season: int | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Matches sorted by goal margin (largest victory first)."""
        comp_filter = _ascii_lower(competition) if competition else None
        candidates: list[tuple[int, Match]] = []
        for m in self.loader.matches:
            if comp_filter and comp_filter not in _ascii_lower(m.competition):
                continue
            if season is not None and m.season != season:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            margin = abs(m.home_goal - m.away_goal)
            if margin == 0:
                continue
            candidates.append((margin, m))
        # Sort by margin desc, then by total goals desc for tie-break.
        candidates.sort(key=lambda t: (t[0], t[1].home_goal + t[1].away_goal),
                        reverse=True)
        out = []
        for margin, m in candidates[:limit]:
            d = _match_to_dict(m)
            d["margin"] = margin
            winner = m.winner_key()
            d["winner"] = _team_display(winner) if winner else "(draw)"
            out.append(d)
        return out

    def best_record_by_venue(
        self, venue: str, competition: str | None = None,
        min_matches: int = 10,
    ) -> list[dict]:
        """Teams with the best win rate at the given venue ('home' or 'away')."""
        venue_norm = venue.lower().strip()
        if venue_norm not in ("home", "away"):
            return [{"error": "venue must be 'home' or 'away'"}]
        comp_filter = _ascii_lower(competition) if competition else None
        agg: dict[str, TeamStats] = {}
        for m in self.loader.matches:
            if comp_filter and comp_filter not in _ascii_lower(m.competition):
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            if venue_norm == "home":
                key = m.home_team_key
                gf, ga = m.home_goal, m.away_goal
            else:
                key = m.away_team_key
                gf, ga = m.away_goal, m.home_goal
            s = agg.setdefault(key, TeamStats(team_key=key,
                                              display_name=team_display_name(key)))
            s.matches += 1
            s.goals_for += gf; s.goals_against += ga
            if gf > ga: s.wins += 1
            elif gf < ga: s.losses += 1
            else: s.draws += 1
        rows = [s for s in agg.values() if s.matches >= min_matches]
        rows.sort(key=lambda s: s.win_rate, reverse=True)
        return [_team_stats_to_dict(s) for s in rows[:20]]

    def top_scorers_by_team(self, team: str, limit: int = 10) -> list[dict]:
        """List a team's top goal threats (FIFA 'Finishing' attribute proxy).

        The Kaggle match datasets don't name individual scorers, so we use the
        FIFA player database's 'Finishing' attribute as a goal-scoring proxy
        for players at the requested club.
        """
        key = normalize_team(team)
        players = [p for p in self.loader.players
                   if p.club_key == key or (team and team.lower() in p.club.lower())]
        players.sort(key=lambda p: p.attributes.get("finishing", 0), reverse=True)
        out = []
        for p in players[:limit]:
            d = _player_to_dict(p)
            d["finishing"] = p.attributes.get("finishing")
            out.append(d)
        return out

    def derbies_in_season(self, season: int) -> list[dict]:
        """All derby matches (per the curated DERBIES set) in a season."""
        out: list[Match] = []
        for m in self.loader.matches:
            if m.season != season:
                continue
            if is_derby(m.home_team_key, m.away_team_key):
                out.append(m)
        out.sort(key=lambda m: (m.date or date.min), reverse=True)
        return [_match_to_dict(m) for m in out]

    # ------------------------------------------------------------------ #
    # MISC / UTILITY
    # ------------------------------------------------------------------ #

    def list_teams(self, competition: str | None = None) -> list[dict]:
        """List all canonical team keys + display names, optionally per comp."""
        comp_filter = _ascii_lower(competition) if competition else None
        seen: dict[str, int] = defaultdict(int)
        for m in self.loader.matches:
            if comp_filter and comp_filter not in _ascii_lower(m.competition):
                continue
            if m.home_team_key:
                seen[m.home_team_key] += 1
            if m.away_team_key:
                seen[m.away_team_key] += 1
        return [
            {"team_key": k, "display_name": team_display_name(k), "matches": n}
            for k, n in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

    def sources(self) -> dict:
        """Summary of loaded datasets."""
        return self.loader.stats()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _parse_iso_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _team_stats_to_dict(s: TeamStats) -> dict:
    return {
        "team": s.display_name,
        "team_key": s.team_key,
        "matches": s.matches,
        "wins": s.wins, "draws": s.draws, "losses": s.losses,
        "goals_for": s.goals_for, "goals_against": s.goals_against,
        "goal_diff": s.goals_for - s.goals_against,
        "points": s.points,
        "win_rate": round(s.win_rate, 4),
        "home": {
            "matches": s.home_matches, "wins": s.home_wins,
            "draws": s.home_draws, "losses": s.home_losses,
            "goals_for": s.home_goals_for,
            "goals_against": s.home_goals_against,
            "win_rate": round(s.home_win_rate, 4),
        },
        "away": {
            "matches": s.away_matches, "wins": s.away_wins,
            "draws": s.away_draws, "losses": s.away_losses,
            "goals_for": s.away_goals_for,
            "goals_against": s.away_goals_against,
            "win_rate": round(s.away_win_rate, 4),
        },
    }
