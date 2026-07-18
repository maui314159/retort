"""
brazilian_soccer_mcp.query_engine
=================================

Query engine that turns structured parameters into formatted answer strings.

Context
-------
This is the brain of the MCP server. Each method corresponds to one of the five
query categories in the spec:

  1. Match Queries     — search_matches, head_to_head
  2. Team Queries      — team_statistics, compare_teams
  3. Player Queries    — search_players, top_players_at_club
  4. Competition Queries — standings, competition_info
  5. Statistical Analysis — average_goals, biggest_wins, home_vs_away

Every method returns a human-readable string (the ``answer format`` examples in
the spec) so the MCP tools can return them directly to the LLM.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Optional

from .knowledge_graph import KnowledgeGraph
from .models import Match, Player

# Forward positions for the "forwards" filter
FORWARD_POSITIONS = {"ST", "LW", "RW", "CF", "LF", "RF", "RS", "LS"}


class QueryEngine:
    """Answer natural-language-shaped queries against the knowledge graph."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    # ==================================================================
    # 1. Match Queries
    # ==================================================================

    def search_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """Search matches by team, opponent, competition, season, or date range."""
        matches = self.graph.data.matches

        # filter by team
        if team:
            canonical = self.graph.resolve_team(team)
            if not canonical:
                return f"Team '{team}' not found in the dataset."
            matches = [m for m in matches if canonical in (m.home_team, m.away_team)]

        # filter by opponent
        if opponent:
            opp = self.graph.resolve_team(opponent)
            if not opp:
                return f"Opponent '{opponent}' not found in the dataset."
            matches = [m for m in matches if opp in (m.home_team, m.away_team)]

        # filter by competition
        if competition:
            comp = self._resolve_competition(competition)
            if comp:
                matches = [m for m in matches if m.competition == comp]
            else:
                matches = [m for m in matches if competition.lower() in m.competition.lower()]

        # filter by season
        if season is not None:
            matches = [m for m in matches if m.season == season]

        # filter by date range
        sd = self._parse_date(start_date)
        ed = self._parse_date(end_date)
        if sd:
            matches = [m for m in matches if m.date and m.date >= sd]
        if ed:
            matches = [m for m in matches if m.date and m.date <= ed]

        if not matches:
            return "No matches found matching the criteria."

        # sort by date descending
        matches.sort(key=lambda m: m.date or date.min, reverse=True)

        total = len(matches)
        shown = matches[:limit]
        lines = [f"Found {total} match(es) matching criteria:"]
        for m in shown:
            lines.append(self._format_match_line(m))
        if total > limit:
            lines.append(f"... ({total - limit} more matches)")
        return "\n".join(lines)

    def head_to_head(self, team_a: str, team_b: str) -> str:
        """Head-to-head record between two teams."""
        a = self.graph.resolve_team(team_a)
        b = self.graph.resolve_team(team_b)
        if not a:
            return f"Team '{team_a}' not found in the dataset."
        if not b:
            return f"Team '{team_b}' not found in the dataset."

        matches = self.graph.head_to_head(a, b)
        if not matches:
            return f"No head-to-head matches found between {a} and {b}."

        matches.sort(key=lambda m: m.date or date.min, reverse=True)

        wins_a = wins_b = draws = 0
        gf_a = gf_b = 0
        for m in matches:
            if m.home_goals is None or m.away_goals is None:
                continue
            if m.home_team == a:
                hg, ag = m.home_goals, m.away_goals
            else:
                hg, ag = m.away_goals, m.home_goals
            gf_a += hg
            gf_b += ag
            if hg > ag:
                wins_a += 1
            elif hg < ag:
                wins_b += 1
            else:
                draws += 1

        lines = [f"{a} vs {b} (head-to-head):"]
        shown = matches[:20]
        for m in shown:
            lines.append(f"  {self._format_match_line(m)}")
        if len(matches) > 20:
            lines.append(f"  ... ({len(matches) - 20} more matches in dataset)")
        lines.append("")
        lines.append(
            f"Head-to-head in dataset: {a} {wins_a} wins, {b} {wins_b} wins, {draws} draws"
        )
        lines.append(f"Goals: {a} {gf_a}, {b} {gf_b}")
        return "\n".join(lines)

    # ==================================================================
    # 2. Team Queries
    # ==================================================================

    def team_statistics(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,  # "home", "away", or None (all)
    ) -> str:
        """Calculate win/loss/draw record and goals for a team."""
        canonical = self.graph.resolve_team(team)
        if not canonical:
            return f"Team '{team}' not found in the dataset."

        resolved_comp = self._resolve_competition(competition) if competition else None
        matches = self.graph.matches_for_team(canonical, resolved_comp, season)
        if venue == "home":
            matches = [m for m in matches if m.home_team == canonical]
        elif venue == "away":
            matches = [m for m in matches if m.away_team == canonical]

        if not matches:
            ctx = self._filter_context(season, competition, venue)
            return f"No matches found for {canonical}{ctx}."

        wins = draws = losses = 0
        gf = ga = 0
        for m in matches:
            if m.home_goals is None or m.away_goals is None:
                continue
            if m.home_team == canonical:
                tg, og = m.home_goals, m.away_goals
            else:
                tg, og = m.away_goals, m.home_goals
            gf += tg
            ga += og
            if tg > og:
                wins += 1
            elif tg < og:
                losses += 1
            else:
                draws += 1

        played = wins + draws + losses
        win_rate = (wins / played * 100) if played else 0

        ctx = self._filter_context(season, competition, venue)
        lines = [f"{canonical} record{ctx}:"]
        lines.append(f"  Matches: {played}")
        lines.append(f"  Wins: {wins}, Draws: {draws}, Losses: {losses}")
        lines.append(f"  Goals For: {gf}, Goals Against: {ga}")
        lines.append(f"  Win rate: {win_rate:.1f}%")
        return "\n".join(lines)

    def compare_teams(self, team_a: str, team_b: str) -> str:
        """Compare two teams head-to-head with full statistics."""
        return self.head_to_head(team_a, team_b)

    # ==================================================================
    # 3. Player Queries
    # ==================================================================

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        is_forward: bool = False,
        limit: int = 20,
    ) -> str:
        """Search FIFA player database by name, nationality, club, position."""
        players = self.graph.data.players

        if name:
            nl = name.lower()
            players = [p for p in players if nl in p.name.lower()]
        if nationality:
            players = [p for p in players if p.nationality.lower() == nationality.lower()]
        if club:
            found = self.graph.players_for_club(club)
            player_ids = {p.id for p in found}
            players = [p for p in players if p.id in player_ids] if players else found
        if position:
            players = [p for p in players if p.position.upper() == position.upper()]
        if is_forward:
            players = [p for p in players if p.position in FORWARD_POSITIONS]
        if min_overall is not None:
            players = [p for p in players if p.overall is not None and p.overall >= min_overall]

        if not players:
            return "No players found matching the criteria."

        players.sort(key=lambda p: p.overall or 0, reverse=True)
        total = len(players)
        shown = players[:limit]

        lines = [f"Found {total} player(s) matching criteria:"]
        for i, p in enumerate(shown, 1):
            lines.append(self._format_player_line(i, p))
        if total > limit:
            lines.append(f"... ({total - limit} more players)")
        return "\n".join(lines)

    def top_players_at_club(self, club: str, limit: int = 10) -> str:
        """Highest-rated players at a given club."""
        players = self.graph.players_for_club(club)
        if not players:
            return f"No players found for club '{club}'."
        players.sort(key=lambda p: p.overall or 0, reverse=True)
        shown = players[:limit]
        lines = [f"Top-rated players at {club}:"]
        for i, p in enumerate(shown, 1):
            lines.append(self._format_player_line(i, p))
        return "\n".join(lines)

    def top_brazilian_players(self, limit: int = 20) -> str:
        """Top-rated Brazilian players in the dataset."""
        brazilians = [p for p in self.graph.data.players if p.nationality == "Brazil"]
        brazilians.sort(key=lambda p: p.overall or 0, reverse=True)
        shown = brazilians[:limit]
        lines = ["Top-rated Brazilian players in dataset:"]
        for i, p in enumerate(shown, 1):
            lines.append(self._format_player_line(i, p))
        return "\n".join(lines)

    # ==================================================================
    # 4. Competition Queries
    # ==================================================================

    def standings(self, competition: str, season: int, top_n: int = 20) -> str:
        """Calculate standings from match results for a competition/season."""
        comp = self._resolve_competition(competition)
        if not comp:
            return f"Competition '{competition}' not found."

        matches = self.graph.matches_for_competition(comp, season)
        scored = [m for m in matches if m.home_goals is not None and m.away_goals is not None]
        if not scored:
            return f"No scored matches found for {comp} {season}."

        table: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
        # [wins, draws, losses, goals_for, goals_against, points]
        for m in scored:
            h, a = m.home_team, m.away_team
            table[h][3] += m.home_goals
            table[h][4] += m.away_goals
            table[a][3] += m.away_goals
            table[a][4] += m.home_goals
            if m.home_goals > m.away_goals:
                table[h][0] += 1; table[h][5] += 3; table[a][2] += 1
            elif m.home_goals < m.away_goals:
                table[a][0] += 1; table[a][5] += 3; table[h][2] += 1
            else:
                table[h][1] += 1; table[a][1] += 1
                table[h][5] += 1; table[a][5] += 1

        ranked = sorted(
            table.items(),
            key=lambda x: (-x[1][5], -x[1][0], -(x[1][3] - x[1][4]), -x[1][3], x[0]),
        )
        shown = ranked[:top_n]

        lines = [f"{season} {comp} Standings (calculated from matches):"]
        for i, (team, rec) in enumerate(shown, 1):
            w, d, l, gf, ga, pts = rec
            marker = " - Champion" if i == 1 else ""
            lines.append(f"  {i}. {team} - {pts} pts ({w}W, {d}D, {l}L){marker}")
        if len(ranked) > top_n:
            lines.append(f"  ... ({len(ranked) - top_n} more teams)")
        return "\n".join(lines)

    def competition_info(self, competition: str) -> str:
        """Overview of a competition: seasons, match count, teams."""
        comp = self._resolve_competition(competition)
        if not comp:
            return f"Competition '{competition}' not found."

        c = self.graph.competitions.get(comp)
        if not c:
            return f"Competition '{comp}' not found."

        seasons = sorted(c.seasons)
        teams = set()
        for m in self.graph.matches_for_competition(comp):
            teams.add(m.home_team)
            teams.add(m.away_team)

        lines = [f"{comp}:"]
        lines.append(f"  Seasons: {', '.join(str(s) for s in seasons)}")
        lines.append(f"  Total matches: {c.match_count}")
        lines.append(f"  Teams: {len(teams)}")
        return "\n".join(lines)

    def competitions_for_team(self, team: str) -> str:
        """Which competitions has a team played in?"""
        canonical = self.graph.resolve_team(team)
        if not canonical:
            return f"Team '{team}' not found in the dataset."
        comps = set()
        match_counts: dict[str, int] = defaultdict(int)
        for m in self.graph.matches_for_team(canonical):
            comps.add(m.competition)
            match_counts[m.competition] += 1
        if not comps:
            return f"No matches found for {canonical}."
        lines = [f"Competitions {canonical} has played in:"]
        for c in sorted(comps):
            lines.append(f"  {c}: {match_counts[c]} matches")
        return "\n".join(lines)

    # ==================================================================
    # 5. Statistical Analysis
    # ==================================================================

    def average_goals(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
    ) -> str:
        """Average goals per match and home/away win rates."""
        matches = self.graph.data.matches
        if competition:
            comp = self._resolve_competition(competition)
            if comp:
                matches = [m for m in matches if m.competition == comp]
        if season is not None:
            matches = [m for m in matches if m.season == season]

        scored = [m for m in matches if m.home_goals is not None and m.away_goals is not None]
        if not scored:
            ctx = self._filter_context(season, competition)
            return f"No scored matches found{ctx}."

        total_goals = sum(m.home_goals + m.away_goals for m in scored)
        avg = total_goals / len(scored)
        home_wins = sum(1 for m in scored if m.home_goals > m.away_goals)
        away_wins = sum(1 for m in scored if m.away_goals > m.home_goals)
        draws = len(scored) - home_wins - away_wins
        hw_rate = home_wins / len(scored) * 100
        aw_rate = away_wins / len(scored) * 100
        d_rate = draws / len(scored) * 100

        ctx = self._filter_context(season, competition)
        lines = [f"Goal statistics{ctx}:"]
        lines.append(f"  Matches: {len(scored)}")
        lines.append(f"  Average goals per match: {avg:.2f}")
        lines.append(f"  Total goals: {total_goals}")
        lines.append(f"  Home win rate: {hw_rate:.1f}%")
        lines.append(f"  Away win rate: {aw_rate:.1f}%")
        lines.append(f"  Draw rate: {d_rate:.1f}%")
        return "\n".join(lines)

    def biggest_wins(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """Biggest victories (by goal difference) in the dataset."""
        matches = self.graph.data.matches
        if competition:
            comp = self._resolve_competition(competition)
            if comp:
                matches = [m for m in matches if m.competition == comp]
        if season is not None:
            matches = [m for m in matches if m.season == season]

        scored = [m for m in matches if m.home_goals is not None and m.away_goals is not None]
        if not scored:
            return "No scored matches found."

        scored.sort(key=lambda m: abs(m.goal_difference or 0), reverse=True)
        shown = scored[:limit]
        lines = ["Biggest victories in dataset:"]
        for m in shown:
            lines.append(f"  {self._format_match_line(m)}")
        return "\n".join(lines)

    def best_records(
        self,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        venue: Optional[str] = None,
        metric: str = "win_rate",
        limit: int = 10,
    ) -> str:
        """Rank teams by win rate (or goals scored) for a given context."""
        matches = self.graph.data.matches
        if competition:
            comp = self._resolve_competition(competition)
            if comp:
                matches = [m for m in matches if m.competition == comp]
        if season is not None:
            matches = [m for m in matches if m.season == season]

        stats: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
        # [wins, draws, losses, goals_for]
        for m in matches:
            if m.home_goals is None or m.away_goals is None:
                continue
            for team, is_home in [(m.home_team, True), (m.away_team, False)]:
                if venue == "home" and not is_home:
                    continue
                if venue == "away" and is_home:
                    continue
                tg = m.home_goals if is_home else m.away_goals
                og = m.away_goals if is_home else m.home_goals
                stats[team][3] += tg
                if tg > og:
                    stats[team][0] += 1
                elif tg < og:
                    stats[team][2] += 1
                else:
                    stats[team][1] += 1

        ranked = []
        for team, (w, d, l, gf) in stats.items():
            played = w + d + l
            if played == 0:
                continue
            if metric == "goals":
                rank_val = gf
            else:
                rank_val = w / played
            ranked.append((team, w, d, l, gf, played, rank_val))

        ranked.sort(key=lambda x: -x[6])
        shown = ranked[:limit]

        ctx = self._filter_context(season, competition, venue)
        metric_label = "goals scored" if metric == "goals" else "win rate"
        lines = [f"Teams ranked by {metric_label}{ctx}:"]
        for i, (team, w, d, l, gf, played, rv) in enumerate(shown, 1):
            if metric == "goals":
                lines.append(f"  {i}. {team} - {gf} goals ({w}W-{d}D-{l}L)")
            else:
                lines.append(f"  {i}. {team} - {rv*100:.1f}% ({w}W-{d}D-{l}L, {gf} GF)")
        return "\n".join(lines)

    # ==================================================================
    # Formatting helpers
    # ==================================================================

    def _format_match_line(self, m: Match) -> str:
        d = m.date.isoformat() if m.date else "Unknown date"
        hg = m.home_goals if m.home_goals is not None else "?"
        ag = m.away_goals if m.away_goals is not None else "?"
        comp_short = m.competition
        extra = ""
        if m.round:
            extra = f" Round {m.round}"
        elif m.stage:
            extra = f" ({m.stage})"
        return f"- {d}: {m.home_team} {hg}-{ag} {m.away_team} ({comp_short}{extra})"

    def _format_player_line(self, index: int, p: Player) -> str:
        overall = p.overall if p.overall is not None else "?"
        return (
            f"{index}. {p.name} - Overall: {overall}, "
            f"Position: {p.position}, Club: {p.club}"
        )

    def _filter_context(
        self,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> str:
        parts = []
        if venue:
            parts.append(venue)
        if season:
            parts.append(str(season))
        if competition:
            comp = self._resolve_competition(competition) or competition
            parts.append(comp)
        if not parts:
            return ""
        return f" ({' '.join(parts)})"

    def _resolve_competition(self, query: str) -> Optional[str]:
        """Resolve a user-provided competition name to a canonical one."""
        competitions = self.graph.competitions_list()
        # exact
        if query in competitions:
            return query
        # case-insensitive
        ql = query.lower()
        for c in competitions:
            if c.lower() == ql:
                return c
        # substring / alias
        aliases = {
            "brasileirao": "Brasileirão Serie A",
            "brasileirão": "Brasileirão Serie A",
            "serie a": "Brasileirão Serie A",
            "serie b": "Brasileirão Serie B",
            "serie c": "Brasileirão Serie C",
            "copa do brasil": "Copa do Brasil",
            "brazilian cup": "Copa do Brasil",
            "libertadores": "Copa Libertadores",
            "copa libertadores": "Copa Libertadores",
        }
        if ql in aliases and aliases[ql] in competitions:
            return aliases[ql]
        for c in competitions:
            if ql in c.lower():
                return c
        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        from datetime import datetime
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
