"""
Query engine for the Brazilian Soccer MCP Server.

This module provides the business logic behind the MCP tools. It is decoupled
from the transport layer so that the same queries can be exercised directly in
the pytest suite.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Optional

from .normalize import (
    canonical_team_name,
    competition_canonical,
    display_team_name,
    parse_date_param,
    parse_score,
    strip_accents,
)


class SoccerEngine:
    """
    Read-only query engine over the normalised match and player datasets.

    Parameters
    ----------
    matches:
        Normalised match records produced by ``data_loader.load_all``.
    players:
        Normalised player records produced by ``data_loader.load_all``.
    """

    def __init__(self, matches: list[dict[str, Any]], players: list[dict[str, Any]]):
        self.matches = matches
        self.players = players
        self._team_index = self._build_team_index()
        self._display_names: dict[str, str] = {}
        for match in matches:
            self._display_names.setdefault(match["home_canonical"], match["home_display"])
            self._display_names.setdefault(match["away_canonical"], match["away_display"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_team_index(self) -> set[str]:
        """Collect every canonical team key appearing in the match data."""
        index: set[str] = set()
        for match in self.matches:
            index.add(match["home_canonical"])
            index.add(match["away_canonical"])
        return index

    def _team_keys(self, name: str) -> set[str]:
        """
        Resolve a user-supplied team name to the set of canonical team keys
        that match it.

        Matching uses exact key equality, substring containment, and a short
        alias dictionary for nicknames (e.g. ``spfc`` -> São Paulo).
        """
        name = name.strip()
        if not name:
            return set()

        alias_name = self._display_alias(name)
        candidates = [name]
        if alias_name:
            candidates.append(alias_name)

        keys: set[str] = set()
        for candidate in candidates:
            canonical, state, base = canonical_team_name(candidate)
            if canonical and canonical in self._team_index:
                keys.add(canonical)
                continue
            for team_key in self._team_index:
                if self._keys_match(canonical, base, team_key):
                    keys.add(team_key)
        return keys

    def _display_alias(self, name: str) -> Optional[str]:
        """Translate nicknames like "spfc" to a standard team name."""
        from .normalize import DISPLAY_ALIASES as aliases
        key = strip_accents(name).lower()
        key = "".join(c for c in key if c.isalnum())
        return aliases.get(key)

    def _keys_match(self, query_key: str, query_base: str, team_key: str) -> bool:
        """Return True when *query_key* matches *team_key*."""
        if not query_key or not team_key:
            return False
        if query_key in team_key or team_key in query_key:
            return True
        if query_base and (query_base in team_key or team_key in query_base):
            return True
        # looser word-boundary style: if any word of the query base appears
        # as a contiguous substring in the team key.
        for word in self._query_words(query_base):
            if len(word) > 2 and word in team_key:
                return True
        return False

    @staticmethod
    def _query_words(base_key: str) -> list[str]:
        """Split a base key into candidate words."""
        words: list[str] = []
        current = ""
        for ch in base_key:
            if ch.isalpha() or ch.isdigit():
                current += ch
            else:
                if current:
                    words.append(current)
                    current = ""
        if current:
            words.append(current)
        return words

    def _display(self, canonical_key: str) -> str:
        """Best-effort display name for a canonical team key."""
        return self._display_names.get(canonical_key, canonical_key.title())

    @staticmethod
    def _match_date_value(match: dict[str, Any]) -> date:
        """Return the match date or a sentinel far in the past when missing."""
        return match.get("date") or date(1900, 1, 1)

    def _format_match(self, match: dict[str, Any]) -> str:
        """Single-line string representation of a match."""
        date_str = match["date"].isoformat() if match.get("date") else "date unknown"
        home = match["home_display"]
        away = match["away_display"]
        hg = match.get("home_goal")
        ag = match.get("away_goal")
        score = "-"
        if hg is not None and ag is not None:
            score = f"{hg}-{ag}"
        context_parts: list[str] = [match["competition"]]
        if match.get("season"):
            context_parts.append(str(match["season"]))
        if match.get("round"):
            context_parts.append(f"Round {match['round']}")
        if match.get("stage"):
            context_parts.append(match["stage"])
        context = ", ".join(context_parts)
        return f"{date_str}: {home} {score} {away} ({context})"

    def _sort_matches(self, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort matches by date descending."""
        return sorted(matches, key=lambda m: (self._match_date_value(m), m.get("round") or ""), reverse=True)

    # ------------------------------------------------------------------
    # Match queries
    # ------------------------------------------------------------------

    def find_matches(
        self,
        team1: Optional[str] = None,
        team2: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str | date] = None,
        date_to: Optional[str | date] = None,
        round_: Optional[str | int] = None,
        stage: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """
        Find matches involving one or two teams.

        ``team1`` and ``team2`` are order-independent when both are supplied.
        """
        keys1 = self._team_keys(team1) if team1 else None
        keys2 = self._team_keys(team2) if team2 else None
        comp = competition_canonical(competition) if competition else None
        d_from = parse_date_param(date_from)
        d_to = parse_date_param(date_to)
        round_str = str(round_).strip() if round_ is not None else None
        stage_norm = strip_accents(stage).lower() if stage else None

        results: list[dict[str, Any]] = []
        for match in self.matches:
            if keys1 is not None and keys2 is not None:
                ordered = (
                    match["home_canonical"] in keys1 and match["away_canonical"] in keys2
                ) or (
                    match["home_canonical"] in keys2 and match["away_canonical"] in keys1
                )
                if not ordered:
                    continue
            elif keys1 is not None:
                if match["home_canonical"] not in keys1 and match["away_canonical"] not in keys1:
                    continue
            elif keys2 is not None:
                if match["home_canonical"] not in keys2 and match["away_canonical"] not in keys2:
                    continue

            if comp and match.get("competition") != comp:
                continue
            if season is not None and match.get("season") != season:
                continue
            if d_from and (not match.get("date") or match["date"] < d_from):
                continue
            if d_to and (not match.get("date") or match["date"] > d_to):
                continue
            if round_str and str(match.get("round") or "").strip() != round_str:
                continue
            if stage_norm and stage_norm not in strip_accents(match.get("stage") or "").lower():
                continue
            results.append(match)

        results = self._sort_matches(results)
        if limit:
            results = results[:limit]

        if not results:
            return "No matches found for the requested criteria."
        header = "Matches found:"
        return header + "\n" + "\n".join("- " + self._format_match(m) for m in results)

    def head_to_head(
        self,
        team1: str,
        team2: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Return fixtures between two teams plus a head-to-head summary."""
        keys1 = self._team_keys(team1)
        keys2 = self._team_keys(team2)
        if not keys1 or not keys2:
            return "Could not resolve one of the team names."

        comp = competition_canonical(competition) if competition else None
        matches: list[dict[str, Any]] = []
        team1_wins = 0
        team2_wins = 0
        draws = 0

        for match in self.matches:
            if match["home_canonical"] in keys1 and match["away_canonical"] in keys2:
                perspective = "home"
            elif match["home_canonical"] in keys2 and match["away_canonical"] in keys1:
                perspective = "away"
            else:
                continue
            if comp and match.get("competition") != comp:
                continue
            if season is not None and match.get("season") != season:
                continue

            hg = match.get("home_goal")
            ag = match.get("away_goal")
            matches.append(match)
            if hg is None or ag is None:
                continue
            t1_goals = hg if perspective == "home" else ag
            t2_goals = ag if perspective == "home" else hg
            if t1_goals > t2_goals:
                team1_wins += 1
            elif t1_goals < t2_goals:
                team2_wins += 1
            else:
                draws += 1

        matches = self._sort_matches(matches)
        if limit:
            matches = matches[:limit]
        if not matches:
            return f"No head-to-head record found between {team1} and {team2}."

        lines = [f"{team1} vs {team2}:", *("- " + self._format_match(m) for m in matches)]
        if team1_wins or team2_wins or draws:
            lines.append(
                f"\nHead-to-head in dataset: {team1} {team1_wins} wins, "
                f"{team2} {team2_wins} wins, {draws} draws"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Team queries
    # ------------------------------------------------------------------

    def _team_stats_subset(self, matches: list[dict[str, Any]], keys: set[str]) -> dict[str, Any]:
        """Compute wins/draws/losses and goals for a team over a match set."""
        stats = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
        for match in matches:
            if match["home_canonical"] in keys:
                team_goals = match.get("home_goal")
                opp_goals = match.get("away_goal")
                stats["matches"] += 1
            elif match["away_canonical"] in keys:
                team_goals = match.get("away_goal")
                opp_goals = match.get("home_goal")
                stats["matches"] += 1
            else:
                continue
            if team_goals is None or opp_goals is None:
                continue
            stats["gf"] += team_goals
            stats["ga"] += opp_goals
            if team_goals > opp_goals:
                stats["wins"] += 1
            elif team_goals < opp_goals:
                stats["losses"] += 1
            else:
                stats["draws"] += 1
        return stats

    def team_statistics(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
    ) -> str:
        """Return overall, home and away statistics for a team."""
        keys = self._team_keys(team)
        if not keys:
            return f"No team matching '{team}' was found."

        comp = competition_canonical(competition) if competition else None
        team_matches: list[dict[str, Any]] = []
        home_matches: list[dict[str, Any]] = []
        away_matches: list[dict[str, Any]] = []

        for match in self.matches:
            if match["home_canonical"] not in keys and match["away_canonical"] not in keys:
                continue
            if comp and match.get("competition") != comp:
                continue
            if season is not None and match.get("season") != season:
                continue
            team_matches.append(match)
            if match["home_canonical"] in keys:
                home_matches.append(match)
            if match["away_canonical"] in keys:
                away_matches.append(match)

        if not team_matches:
            return f"No matches found for {team} with the given filters."

        overall = self._team_stats_subset(team_matches, keys)
        home = self._team_stats_subset(home_matches, keys)
        away = self._team_stats_subset(away_matches, keys)

        def fmt(label: str, s: dict[str, Any]) -> str:
            matches = s["matches"]
            rate = (s["wins"] / matches * 100) if matches else 0.0
            return (
                f"{label} ({matches} matches): "
                f"{s['wins']}W/{s['draws']}D/{s['losses']}L, "
                f"GF {s['gf']}, GA {s['ga']}, win rate {rate:.1f}%"
            )

        title = team
        if season:
            title += f" ({season})"
        if competition:
            title += f" {comp}"

        return (
            f"Team statistics for {title}:\n"
            + f"- Overall: {fmt('Overall', overall)}\n"
            + f"- Home:    {fmt('Home', home)}\n"
            + f"- Away:    {fmt('Away', away)}"
        )

    def team_competitions(self, team: str) -> str:
        """List every competition/season pair a team has played in."""
        keys = self._team_keys(team)
        if not keys:
            return f"No team matching '{team}' was found."
        pairs: set[tuple[str, Optional[int]]] = set()
        for match in self.matches:
            if match["home_canonical"] in keys or match["away_canonical"] in keys:
                pairs.add((match["competition"], match.get("season")))
        if not pairs:
            return f"No competitions found for {team}."
        sorted_pairs = sorted(pairs, key=lambda x: (x[0], x[1] or 0))
        lines = [f"{team} has played in:"]
        for competition, season in sorted_pairs:
            season_str = str(season) if season else "unknown season"
            lines.append(f"- {competition} ({season_str})")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Player queries
    # ------------------------------------------------------------------

    def _matches_name(self, row: dict[str, Any], query: str) -> bool:
        query = strip_accents(query).lower()
        names = [
            row.get("Name", ""),
            row.get("Name_norm", ""),
        ]
        return any(query in strip_accents(name).lower() for name in names)

    @staticmethod
    def _matches_nationality(row: dict[str, Any], query: str) -> bool:
        query_norm = strip_accents(query).lower()
        nat_norm = strip_accents(row.get("Nationality", "")).lower()
        if query_norm in ("brazil", "brasil"):
            return nat_norm in ("brazil", "brasil")
        return query_norm in nat_norm

    def _matches_club(self, row: dict[str, Any], query: str) -> bool:
        query_norm = strip_accents(query).lower()
        query_key, _, query_base = canonical_team_name(query)
        club_norm = strip_accents(row.get("Club", "")).lower()
        if query_norm in club_norm:
            return True
        club_key, _, club_base = canonical_team_name(club_norm)
        if query_key in (club_key, club_base) or club_key in query_key:
            return True
        return query_base in club_base or club_base in query_base

    @staticmethod
    def _matches_position(row: dict[str, Any], query: str) -> bool:
        position = (row.get("Position") or "").upper()
        query_pos = query.upper().strip()
        if not query_pos:
            return True
        return query_pos in position or position in query_pos

    def _filter_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for row in self.players:
            if name and not self._matches_name(row, name):
                continue
            if nationality and not self._matches_nationality(row, nationality):
                continue
            if club and not self._matches_club(row, club):
                continue
            if position and not self._matches_position(row, position):
                continue
            results.append(row)
        return results

    def find_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Search the FIFA player database."""
        results = self._filter_players(name, nationality, club, position)
        results.sort(key=lambda r: (-r["Overall_int"], r["Name"].lower()))
        if limit:
            results = results[:limit]
        if not results:
            return "No players found for the requested criteria."
        lines = ["Players found:"]
        for row in results:
            lines.append(
                f"- {row['Name']} ({row['Nationality']}) - Overall {row.get('Overall', 'N/A')}, "
                f"Position {row.get('Position', 'N/A')}, Club {row.get('Club', 'N/A')}"
            )
        return "\n".join(lines)

    def top_players(
        self,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """Return the highest-rated players matching the optional filters."""
        results = self._filter_players(nationality=nationality, club=club, position=position)
        results.sort(key=lambda r: (-r["Overall_int"], r["Name"].lower()))
        if limit:
            results = results[:limit]
        if not results:
            return "No players found for the requested criteria."
        lines = [f"Top {len(results)} players:"]
        for i, row in enumerate(results, start=1):
            lines.append(
                f"{i}. {row['Name']} - Overall {row.get('Overall', 'N/A')}, "
                f"Position {row.get('Position', 'N/A')}, Club {row.get('Club', 'N/A')}"
            )
        return "\n".join(lines)

    def player_details(self, name: str) -> str:
        """Return a summary for a single player."""
        results = self._filter_players(name=name)
        if not results:
            return f"No player named '{name}' found."
        row = max(results, key=lambda r: r["Overall_int"])
        details = [
            f"Name: {row['Name']}",
            f"Nationality: {row.get('Nationality', 'N/A')}",
            f"Age: {row.get('Age', 'N/A')}",
            f"Club: {row.get('Club', 'N/A')}",
            f"Position: {row.get('Position', 'N/A')}",
            f"Overall: {row.get('Overall', 'N/A')}",
            f"Potential: {row.get('Potential', 'N/A')}",
            f"Jersey Number: {row.get('Jersey Number', 'N/A')}",
        ]
        return "\n".join(details)

    # ------------------------------------------------------------------
    # Competition queries
    # ------------------------------------------------------------------

    def _compute_standings(
        self,
        competition: str,
        season: Optional[int] = None,
    ) -> list[tuple[str, dict[str, int]]]:
        comp = competition_canonical(competition)
        table: dict[str, dict[str, int]] = defaultdict(
            lambda: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
        )
        for match in self.matches:
            if match.get("competition") != comp:
                continue
            if season is not None and match.get("season") != season:
                continue
            hg = match.get("home_goal")
            ag = match.get("away_goal")
            home = match["home_canonical"]
            away = match["away_canonical"]
            if hg is None or ag is None:
                continue

            table[home]["P"] += 1
            table[away]["P"] += 1
            table[home]["GF"] += hg
            table[home]["GA"] += ag
            table[away]["GF"] += ag
            table[away]["GA"] += hg
            if hg > ag:
                table[home]["W"] += 1
                table[home]["Pts"] += 3
                table[away]["L"] += 1
            elif hg < ag:
                table[away]["W"] += 1
                table[away]["Pts"] += 3
                table[home]["L"] += 1
            else:
                table[home]["D"] += 1
                table[away]["D"] += 1
                table[home]["Pts"] += 1
                table[away]["Pts"] += 1

        def sort_key(item: tuple[str, dict[str, int]]) -> tuple:
            _, s = item
            return (s["Pts"], s["GF"] - s["GA"], s["GF"], s["W"])

        return sorted(table.items(), key=sort_key, reverse=True)

    def competition_standings(
        self,
        competition: str,
        season: int,
    ) -> str:
        """Return a league table for a competition and season."""
        standings = self._compute_standings(competition, season)
        if not standings:
            return f"No standings found for {competition} {season}."

        lines = [f"{competition_canonical(competition)} {season} standings:"]
        for i, (team_key, stats) in enumerate(standings, start=1):
            label = "Champion" if i == 1 else f"{i}"
            lines.append(
                f"{label}. {self._display(team_key)} - {stats['Pts']} pts "
                f"({stats['W']}W, {stats['D']}D, {stats['L']}L), "
                f"GF {stats['GF']}, GA {stats['GA']}, GD {stats['GF'] - stats['GA']}"
            )
        return "\n".join(lines)

    def relegated_teams(self, season: int) -> str:
        """Return the bottom four teams of the Brasileirão for a season."""
        standings = self._compute_standings("Brasileirão", season)
        if not standings:
            return f"No Brasileirão data found for {season}."
        bottom = standings[-4:]
        lines = [f"Relegated teams from the {season} Brasileirão:"]
        for rank, (team_key, stats) in enumerate(bottom, start=len(standings) - 3):
            lines.append(
                f"{rank}. {self._display(team_key)} - {stats['Pts']} pts "
                f"({stats['W']}W, {stats['D']}D, {stats['L']}L)"
            )
        return "\n".join(lines)

    def competition_finals(
        self,
        competition: str,
        season: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """
        Return matches that belong to the deepest round/stage available for a
        competition. This maps naturally to "Copa do Brasil finals" or
        "Libertadores final".
        """
        comp = competition_canonical(competition)
        candidates = [m for m in self.matches if m.get("competition") == comp]
        if season is not None:
            candidates = [m for m in candidates if m.get("season") == season]
        if not candidates:
            return f"No matches found for {comp}."

        # Numeric rounds take priority; otherwise use stage.
        numeric_rounds = [m for m in candidates if isinstance(m.get("round"), (int, str)) and str(m["round"]).isdigit()]
        if numeric_rounds:
            deepest = max(int(str(m["round"])) for m in numeric_rounds)
            finals = [m for m in candidates if str(m.get("round")) == str(deepest)]
        else:
            stages = [m for m in candidates if m.get("stage")]
            if not stages:
                return f"No final-stage data available for {comp}."
            # Heuristic: deepest stage is the alphabetically last among known
            # labels such as "final", but precise brackets vary by source.
            order = {"group stage": 0, "round of 16": 1, "quarter": 2, "semi": 3, "final": 4}

            def stage_order(match: dict[str, Any]) -> int:
                stage = strip_accents(match.get("stage", "")).lower()
                for key, value in order.items():
                    if key in stage:
                        return value
                return 0

            deepest_stage_value = max(stage_order(m) for m in stages)
            finals = [m for m in stages if stage_order(m) == deepest_stage_value]

        finals = self._sort_matches(finals)
        if limit:
            finals = finals[:limit]
        if not finals:
            return f"No finals matches found for {comp}."

        lines = [f"Final-stage matches for {comp}" + (f" ({season})" if season else "") + ":"]
        lines.extend("- " + self._format_match(m) for m in finals)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Statistical queries
    # ------------------------------------------------------------------

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Return the matches with the largest goal difference."""
        comp = competition_canonical(competition) if competition else None
        matches: list[tuple[int, dict[str, Any]]] = []
        for match in self.matches:
            if comp and match.get("competition") != comp:
                continue
            if season is not None and match.get("season") != season:
                continue
            hg = match.get("home_goal")
            ag = match.get("away_goal")
            if hg is None or ag is None:
                continue
            diff = abs(hg - ag)
            matches.append((diff, match))
        matches.sort(key=lambda x: (x[0], x[1].get("date") or date.min), reverse=True)
        if limit:
            matches = matches[:limit]
        if not matches:
            return "No decisive matches found for the requested criteria."

        lines = ["Biggest wins by goal difference:"]
        for diff, match in matches:
            lines.append("- " + self._format_match(match) + f" [margin {diff}]")
        return "\n".join(lines)

    def average_goals(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        """Return average total goals per match and home win rate."""
        comp = competition_canonical(competition) if competition else None
        total_goals = 0
        matches_with_score = 0
        home_wins = 0
        home_matches = 0
        for match in self.matches:
            if comp and match.get("competition") != comp:
                continue
            if season is not None and match.get("season") != season:
                continue
            hg = match.get("home_goal")
            ag = match.get("away_goal")
            if hg is None or ag is None:
                continue
            total_goals += hg + ag
            matches_with_score += 1
            home_matches += 1
            if hg > ag:
                home_wins += 1

        if not matches_with_score:
            return "No scored matches available for the requested criteria."

        avg = total_goals / matches_with_score
        home_win_rate = (home_wins / home_matches * 100) if home_matches else 0.0

        scope = "All competitions"
        if comp:
            scope = comp
        if season is not None:
            scope += f" {season}"

        return (
            f"{scope} (from {matches_with_score} scored matches):\n"
            f"- Average goals per match: {avg:.2f}\n"
            f"- Home win rate: {home_win_rate:.1f}%"
        )

    def best_away_record(self, min_matches: int = 10) -> str:
        """Rank teams by away win rate, requiring a minimum number of away games."""
        away_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"matches": 0, "wins": 0, "gf": 0, "ga": 0}
        )
        for match in self.matches:
            ag = match.get("away_goal")
            hg = match.get("home_goal")
            if ag is None or hg is None:
                continue
            team = match["away_canonical"]
            away_stats[team]["matches"] += 1
            away_stats[team]["gf"] += ag
            away_stats[team]["ga"] += hg
            if ag > hg:
                away_stats[team]["wins"] += 1

        qualified = [
            (team, stats)
            for team, stats in away_stats.items()
            if stats["matches"] >= min_matches
        ]
        qualified.sort(key=lambda x: (x[1]["wins"] / x[1]["matches"], x[1]["wins"]), reverse=True)
        lines = ["Best away records (min 10 away matches):"]
        for team, stats in qualified[:10]:
            rate = stats["wins"] / stats["matches"] * 100
            lines.append(
                f"- {self._display(team)}: {stats['wins']} wins from {stats['matches']} away games "
                f"({rate:.1f}%)"
            )
        return "\n".join(lines)
