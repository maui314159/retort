"""Query layer: statistics, standings, head-to-head, and formatting.

All high-level question answering used by the MCP tools lives here so it
can be tested independently of the MCP transport.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from .loader import Match, SoccerData, name_matches, normalize_name


def _fmt_score(m: Match) -> str:
    hg = "?" if m.home_goal is None else m.home_goal
    ag = "?" if m.away_goal is None else m.away_goal
    return f"{hg}-{ag}"


def _match_line(m: Match) -> str:
    date = m.date.strftime("%Y-%m-%d") if m.date else "unknown date"
    line = f"- {date}: {m.home} {_fmt_score(m)} {m.away} ({m.competition}"
    if m.season:
        line += f" {m.season}"
    if m.round:
        line += f" Round {m.round}"
    if m.stage:
        line += f", {m.stage}"
    line += ")"
    return line


class SoccerQueries:
    """High-level queries over the loaded datasets."""

    def __init__(self, data: SoccerData):
        self.data = data

    # ------------------------------------------------------------------
    # match queries
    # ------------------------------------------------------------------
    def find_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 25,
    ) -> list[Match]:
        """Find matches by team, opponent, competition, season, date range."""
        d_from = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
        d_to = datetime.strptime(date_to, "%Y-%m-%d") if date_to else None

        out = []
        for m in self.data.competition_matches(competition=competition, season=season):
            if team and not (name_matches(team, m.home) or name_matches(team, m.away)):
                continue
            if opponent and not (
                name_matches(opponent, m.home) or name_matches(opponent, m.away)
            ):
                continue
            if team and opponent:
                # both teams must be playing each other
                t_home = name_matches(team, m.home) or name_matches(opponent, m.home)
                t_away = name_matches(team, m.away) or name_matches(opponent, m.away)
                if not (t_home and t_away):
                    continue
            if d_from and (m.date is None or m.date < d_from):
                continue
            if d_to and (m.date is None or m.date.date() > d_to.date()):
                continue
            out.append(m)
        out.sort(key=lambda m: (m.date or datetime.min))
        return out[:limit]

    def last_match_between(self, team_a: str, team_b: str) -> Optional[Match]:
        h2h = self.data.head_to_head(team_a, team_b)
        return h2h[-1] if h2h else None

    def format_match_list(self, matches: list[Match], total: Optional[int] = None) -> str:
        if not matches:
            return "No matches found."
        lines = [_match_line(m) for m in matches]
        total = total if total is not None else len(matches)
        if total > len(matches):
            lines.append(f"... ({total - len(matches)} more matches in dataset)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # team queries
    # ------------------------------------------------------------------
    def team_stats(
        self,
        team: str,
        season: Optional[int] = None,
        competition: Optional[str] = None,
        venue: Optional[str] = None,  # 'home', 'away', or None (both)
    ) -> dict:
        """Win/loss/draw record and goals for a team, with optional filters."""
        stats = {
            "team": team,
            "season": season,
            "competition": competition,
            "venue": venue,
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        for m in self.data.competition_matches(competition=competition, season=season):
            is_home = name_matches(team, m.home)
            is_away = name_matches(team, m.away)
            if not (is_home or is_away):
                continue
            if venue == "home" and not is_home:
                continue
            if venue == "away" and not is_away:
                continue
            if m.home_goal is None or m.away_goal is None:
                continue
            stats["matches"] += 1
            if is_home:
                gf, ga = m.home_goal, m.away_goal
            else:
                gf, ga = m.away_goal, m.home_goal
            stats["goals_for"] += gf
            stats["goals_against"] += ga
            w = m.winner()
            if w == "draw":
                stats["draws"] += 1
            elif (w == "home") == is_home:
                stats["wins"] += 1
            else:
                stats["losses"] += 1
        if stats["matches"]:
            stats["win_rate"] = round(stats["wins"] / stats["matches"] * 100, 1)
        else:
            stats["win_rate"] = 0.0
        return stats

    def format_team_stats(self, stats: dict) -> str:
        bits = [stats["team"], "record"]
        if stats.get("season"):
            bits.append(f"({stats['season']}")
            if stats.get("competition"):
                bits.append(f"{stats['competition']}")
            bits.append(")")
        elif stats.get("competition"):
            bits.append(f"({stats['competition']})")
        if stats.get("venue"):
            bits.append(f"[{stats['venue']} matches]")
        header = " ".join(bits).replace(" )", ")")
        return (
            f"{header}:\n"
            f"- Matches: {stats['matches']}\n"
            f"- Wins: {stats['wins']}, Draws: {stats['draws']}, Losses: {stats['losses']}\n"
            f"- Goals For: {stats['goals_for']}, Goals Against: {stats['goals_against']}\n"
            f"- Win rate: {stats['win_rate']}%"
        )

    def head_to_head_summary(self, team_a: str, team_b: str) -> dict:
        summary = {
            "team_a": team_a,
            "team_b": team_b,
            "matches": 0,
            "team_a_wins": 0,
            "team_b_wins": 0,
            "draws": 0,
        }
        for m in self.data.head_to_head(team_a, team_b):
            if m.home_goal is None or m.away_goal is None:
                continue
            summary["matches"] += 1
            w = m.winner()
            if w == "draw":
                summary["draws"] += 1
            elif w == "home":
                if name_matches(team_a, m.home):
                    summary["team_a_wins"] += 1
                else:
                    summary["team_b_wins"] += 1
            else:
                if name_matches(team_a, m.away):
                    summary["team_a_wins"] += 1
                else:
                    summary["team_b_wins"] += 1
        return summary

    # ------------------------------------------------------------------
    # competition queries
    # ------------------------------------------------------------------
    def standings(self, competition: str, season: int) -> list[dict]:
        """Calculate a league table (3 points per win) from match results.

        Uses a single deduplicated source file per season so overlapping
        datasets (e.g. two files both covering the 2019 Brasileirão) do
        not double-count matches.
        """
        table: dict[str, dict] = {}

        def get(name: str) -> dict:
            key = normalize_name(name)
            if key not in table:
                table[key] = {
                    "team": name,
                    "matches": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0,
                }
            return table[key]

        for m in self.data.competition_matches(competition=competition, season=season):
            if m.home_goal is None or m.away_goal is None:
                continue
            home, away = get(m.home), get(m.away)
            for side, gf, ga in (
                (home, m.home_goal, m.away_goal),
                (away, m.away_goal, m.home_goal),
            ):
                side["matches"] += 1
                side["goals_for"] += gf
                side["goals_against"] += ga
                if gf > ga:
                    side["wins"] += 1
                    side["points"] += 3
                elif gf == ga:
                    side["draws"] += 1
                    side["points"] += 1
                else:
                    side["losses"] += 1

        rows = sorted(
            table.values(),
            key=lambda r: (
                -r["points"],
                -(r["goals_for"] - r["goals_against"]),
                -r["goals_for"],
            ),
        )
        return rows

    def format_standings(self, rows: list[dict], competition: str, season: int) -> str:
        if not rows:
            return f"No standings data for {competition} {season}."
        lines = [f"{competition} {season} Standings (calculated from matches):"]
        for i, r in enumerate(rows, 1):
            gd = r["goals_for"] - r["goals_against"]
            tag = " - Champion" if i == 1 else ""
            lines.append(
                f"{i}. {r['team']} - {r['points']} pts "
                f"({r['wins']}W, {r['draws']}D, {r['losses']}L, GD {gd:+d}){tag}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # player queries
    # ------------------------------------------------------------------
    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        order_by: str = "Overall",
        limit: int = 20,
    ) -> list[dict]:
        n = normalize_name(name) if name else None
        nat = normalize_name(nationality) if nationality else None
        cl = normalize_name(club) if club else None
        pos = position.strip().upper() if position else None
        out = []
        for p in self.data.players:
            if n and n not in (p.get("_norm_name") or ""):
                continue
            if nat and nat != normalize_name(p.get("Nationality") or ""):
                continue
            if cl and cl not in (p.get("_norm_club") or ""):
                continue
            if pos and (p.get("Position") or "").upper() != pos:
                continue
            out.append(p)
        out.sort(
            key=lambda p: p.get(order_by)
            if isinstance(p.get(order_by), (int, float))
            else 0,
            reverse=True,
        )
        return out[:limit]

    def format_players(self, players: list[dict]) -> str:
        if not players:
            return "No players found."
        lines = []
        for i, p in enumerate(players, 1):
            lines.append(
                f"{i}. {p.get('Name')} - Overall: {p.get('Overall')}, "
                f"Position: {p.get('Position')}, Club: {p.get('Club')}, "
                f"Nationality: {p.get('Nationality')}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # statistical analysis
    # ------------------------------------------------------------------
    def competition_stats(
        self, competition: Optional[str] = None, season: Optional[int] = None
    ) -> dict:
        played = home_wins = away_wins = draws = goals = 0
        for m in self.data.competition_matches(competition=competition, season=season):
            if m.home_goal is None or m.away_goal is None:
                continue
            played += 1
            goals += m.home_goal + m.away_goal
            w = m.winner()
            if w == "home":
                home_wins += 1
            elif w == "away":
                away_wins += 1
            else:
                draws += 1
        return {
            "competition": competition or "all competitions",
            "season": season,
            "matches": played,
            "total_goals": goals,
            "avg_goals_per_match": round(goals / played, 2) if played else 0.0,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "draws": draws,
            "home_win_rate": round(home_wins / played * 100, 1) if played else 0.0,
        }

    def biggest_wins(
        self, competition: Optional[str] = None, limit: int = 10
    ) -> list[Match]:
        scored = []
        for m in self.data.competition_matches(competition=competition):
            if m.home_goal is None or m.away_goal is None:
                continue
            scored.append((abs(m.home_goal - m.away_goal), m.home_goal + m.away_goal, m))
        scored.sort(key=lambda t: (-t[0], -t[1]))
        return [m for _, _, m in scored[:limit]]

    def format_biggest_wins(self, matches: list[Match]) -> str:
        if not matches:
            return "No matches found."
        lines = ["Biggest victories in dataset:"]
        for i, m in enumerate(matches, 1):
            date = m.date.strftime("%Y-%m-%d") if m.date else "unknown date"
            lines.append(f"{i}. {date}: {m.home} {_fmt_score(m)} {m.away} ({m.competition})")
        return "\n".join(lines)

    def best_team_record(
        self, venue: str = "home", competition: Optional[str] = None, min_matches: int = 50
    ) -> list[dict]:
        """Rank teams by win rate at a venue ('home' or 'away')."""
        agg: dict[str, dict] = defaultdict(lambda: {"matches": 0, "wins": 0, "team": ""})
        for m in self.data.competition_matches(competition=competition):
            if m.home_goal is None or m.away_goal is None:
                continue
            if venue == "home":
                team, won = m.home, m.winner() == "home"
            else:
                team, won = m.away, m.winner() == "away"
            key = normalize_name(team)
            agg[key]["team"] = team
            agg[key]["matches"] += 1
            if won:
                agg[key]["wins"] += 1
        ranked = [
            {
                "team": v["team"],
                "matches": v["matches"],
                "wins": v["wins"],
                "win_rate": round(v["wins"] / v["matches"] * 100, 1),
            }
            for v in agg.values()
            if v["matches"] >= min_matches
        ]
        ranked.sort(key=lambda r: -r["win_rate"])
        return ranked

    def matches_per_team_summary(self, team: str) -> dict:
        """Per-competition breakdown of a team's matches."""
        per_comp: dict[str, int] = defaultdict(int)
        for m in self.data.team_matches(team):
            per_comp[m.competition] += 1
        return {"team": team, "competitions": dict(per_comp)}
