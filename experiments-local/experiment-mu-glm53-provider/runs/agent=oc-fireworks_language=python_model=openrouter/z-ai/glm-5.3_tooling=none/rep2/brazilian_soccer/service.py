"""Query layer: every capability the MCP server exposes, as plain methods.

Each method takes simple arguments (team names, competition names, seasons,
filters), resolves them through the knowledge graph and returns a
human-readable answer formatted like the examples in the specification.
The MCP server in :mod:`server` is a thin wrapper around this class, and
the BDD test suite exercises these methods directly.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from .competitions import COMPETITIONS, is_league, resolve_competition
from .derbies import DERBIES, find_derby
from .loader import FIFA_UNLICENSED_NOTE, SoccerData
from .models import Match, Player, TeamRecord
from .normalize import Team, fold, parse_date

DEFAULT_MATCH_LIMIT = 15
DEFAULT_PLAYER_LIMIT = 15


def _words(text: str) -> set[str]:
    """Split into lowercase alphanumeric words (accents folded)."""
    return {
        fold(token)
        for token in re.split(r"[^0-9A-Za-zÀ-ÿ]+", text.lower())
        if token
    }


def _stage_matches(query: str, *labels: str | None) -> bool:
    """Word-level stage matching so 'final' does not hit 'semifinals'."""
    query_words = _words(query)
    if not query_words:
        return True
    for label in labels:
        if not label:
            continue
        label_words = _words(label)
        if query_words == label_words:
            return True
        for word in query_words:
            if not any(
                word == other or word == other.rstrip("s") or word.rstrip("s") == other
                for other in label_words
            ):
                break
        else:
            if query_words <= label_words or len(query_words) == 1:
                return True
    return False


class SoccerService:
    """All supported queries over the loaded knowledge graph."""

    def __init__(self, data: SoccerData) -> None:
        self.data = data

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def _team(self, query: str) -> Team | str:
        """Resolve a team query or return an error message string."""
        resolution = self.data.registry.resolve(query)
        if resolution.matched and resolution.key:
            return self.data.registry.teams[resolution.key]
        if resolution.ambiguous:
            options = " / ".join(t.display for t in resolution.ambiguous[:8])
            return (
                f"Team name '{query}' is ambiguous. "
                f"Did you mean: {options}?"
            )
        suggestions = " / ".join(resolution.suggestions) or "no close match"
        return f"Team '{query}' not found. Did you mean: {suggestions}?"

    @staticmethod
    def _competition(query: str | None) -> tuple[str | None, str | None]:
        """Resolve a competition name; returns (canonical id, error)."""
        if query is None:
            return None, None
        comp_id = resolve_competition(query)
        if comp_id is None:
            options = ", ".join(COMPETITIONS.values())
            return None, f"Competition '{query}' not found. Available: {options}."
        return comp_id, None

    def _season_int(self, season) -> int | None:
        try:
            return int(str(season).strip())
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------

    def _filter_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season=None,
        stage: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[Match] | str:
        comp_id, comp_error = self._competition(competition)
        if comp_error:
            return comp_error
        season_int = self._season_int(season) if season not in (None, "") else None
        lo = parse_date(date_from) if date_from else None
        hi = parse_date(date_to) if date_to else None
        stage_key = fold(stage) if stage else None

        team_keys: set[str] = set()
        opp_keys: set[str] = set()
        for query, bucket in ((team, "team"), (opponent, "opponent")):
            if not query:
                continue
            resolved = self._team(query)
            if isinstance(resolved, str):
                return resolved
            if bucket == "team":
                team_keys.add(resolved.key)
            else:
                opp_keys.add(resolved.key)

        result = []
        for match in self.data.matches:
            if comp_id and match.competition != comp_id:
                continue
            if season_int is not None and match.season != season_int:
                continue
            if team_keys and not ({match.home.key, match.away.key} & team_keys):
                continue
            if opp_keys and not ({match.home.key, match.away.key} & opp_keys):
                continue
            if lo and (match.date is None or match.date < lo):
                continue
            if hi and (match.date is None or match.date > hi):
                continue
            if stage_key:
                if not _stage_matches(stage, match.stage, match.round_label):
                    continue
            result.append(match)
        result.sort(key=lambda m: (m.date is None, m.date or date.min), reverse=True)
        return result

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season=None,
        stage: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = DEFAULT_MATCH_LIMIT,
    ) -> str:
        """Find matches by team, opponent, competition, season, stage or
        date range (most recent first)."""
        matches = self._filter_matches(
            team, opponent, competition, season, stage, date_from, date_to
        )
        if isinstance(matches, str):
            return matches
        if not matches:
            return "No matches found for the given filters."
        if team or opponent:
            subject = self._match_subject(team, opponent)
        elif competition:
            subject = COMPETITIONS[resolve_competition(competition) or "brasileirao"]
        else:
            subject = "all competitions"

        lines = [f"Matches ({subject}): {len(matches)} found"]
        for match in matches[: max(1, limit)]:
            lines.append(f"- {match.describe()}")
        hidden = len(matches) - min(len(matches), max(1, limit))
        if hidden > 0:
            lines.append(f"  (+{hidden} more matches in dataset)")
        by_comp = defaultdict(int)
        for match in matches:
            by_comp[match.competition_display] += 1
        lines.append(
            "By competition: "
            + ", ".join(f"{name}: {count}" for name, count in sorted(by_comp.items()))
        )
        if team and opponent:
            lines.append(self._h2h_line(matches, team_key=None, team=team))
        return "\n".join(lines)

    def _match_subject(self, team: str | None, opponent: str | None) -> str:
        parts: list[str] = []
        keys: list[str] = []
        for query in (team, opponent):
            if not query:
                continue
            resolved = self._team(query)
            if isinstance(resolved, str):
                parts.append(query)
            else:
                parts.append(resolved.display)
                keys.append(resolved.key)
        subject = " x ".join(parts) if parts else "all teams"
        if len(keys) == 2:
            derby_name = self._derby_name(*keys)
            if derby_name:
                subject += f" ({derby_name})"
        return subject

    # ------------------------------------------------------------------
    # 2. Head-to-head
    # ------------------------------------------------------------------

    def _h2h_line(self, matches: list[Match], team_key: str | None, team: str | None) -> str:
        if team_key is None and team is not None:
            resolved = self._team(team)
            if isinstance(resolved, str):
                return "Head-to-head: unavailable (team resolution failed)"
            team_key = resolved.key
        if team_key is None:
            return "Head-to-head: unavailable"
        wins = draws = losses = 0
        other: str | None = None
        for match in matches:
            result = match.result_for(team_key)
            if result is None:
                continue
            if result == "W":
                wins += 1
            elif result == "D":
                draws += 1
            else:
                losses += 1
            other_key = match.away.key if match.home.key == team_key else match.home.key
            if other is None:
                other = self.data.registry.display(other_key)
        team_display = self.data.registry.display(team_key)
        if other is None:
            return "Head-to-head in dataset: no played matches."
        return (
            f"Head-to-head in dataset: {team_display} {wins} wins, "
            f"{draws} draws, {other} {losses} wins"
        )

    def head_to_head(
        self, team_a: str, team_b: str, competition: str | None = None, limit: int = 10
    ) -> str:
        """Compare two teams head-to-head, optionally within one
        competition."""
        matches = self._filter_matches(
            team=team_a, opponent=team_b, competition=competition
        )
        if isinstance(matches, str):
            return matches
        a = self._team(team_a)
        b = self._team(team_b)
        if isinstance(a, str):
            return a
        if isinstance(b, str):
            return b
        if not matches:
            return f"No matches between {a.display} and {b.display} in the dataset."

        derby_name = self._derby_name(a.key, b.key)
        title = f"{a.display} vs {b.display}"
        if derby_name:
            title += f" ({derby_name})"
        lines = [f"{title} - {len(matches)} matches in dataset:"]
        for match in matches[: max(1, limit)]:
            lines.append(f"- {match.describe()}")
        hidden = len(matches) - min(len(matches), max(1, limit))
        if hidden > 0:
            lines.append(f"  (+{hidden} more matches in dataset)")
        lines.append(self._h2h_line(matches, a.key, None))
        return "\n".join(lines)

    @staticmethod
    def _derby_name(team_a: str, team_b: str) -> str | None:
        for derby in DERBIES:
            if {derby.team_a, derby.team_b} == {team_a, team_b}:
                return derby.name
        return None

    # ------------------------------------------------------------------
    # 3. Team queries
    # ------------------------------------------------------------------

    def team_stats(
        self,
        team: str,
        season=None,
        competition: str | None = None,
        venue: str = "all",
    ) -> str:
        """Win/draw/loss record, goals and win rate; optionally filtered by
        season, competition and venue ('home' / 'away' / 'all')."""
        resolved = self._team(team)
        if isinstance(resolved, str):
            return resolved
        comp_id, comp_error = self._competition(competition)
        if comp_error:
            return comp_error
        season_int = self._season_int(season) if season not in (None, "") else None
        venue_key = (venue or "all").strip().lower()
        if venue_key not in ("all", "home", "away"):
            venue_key = "all"

        record = TeamRecord()
        for match in self.data.matches_for_team(resolved.key):
            if comp_id and match.competition != comp_id:
                continue
            if season_int is not None and match.season != season_int:
                continue
            is_home = match.home.key == resolved.key
            if venue_key == "home" and not is_home:
                continue
            if venue_key == "away" and is_home:
                continue
            result = match.result_for(resolved.key)
            if result is None:
                continue
            gf = match.home_goals if is_home else match.away_goals
            ga = match.away_goals if is_home else match.home_goals
            record.add(result, gf or 0, ga or 0)

        context = resolved.display
        if season_int is not None:
            context += f" ({season_int}"
            if comp_id:
                context += f" {COMPETITIONS[comp_id]}"
            if venue_key != "all":
                context += f", {venue_key} matches"
            context += ")"
        elif comp_id:
            context += f" ({COMPETITIONS[comp_id]}"
            if venue_key != "all":
                context += f", {venue_key} matches"
            context += ")"
        elif venue_key != "all":
            context += f" ({venue_key} matches)"

        if record.matches == 0:
            return f"{context}: no played matches in the dataset for these filters."
        lines = [
            f"{context}:",
            f"- Matches: {record.matches}",
            f"- Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}",
            f"- Goals For: {record.goals_for}, Goals Against: {record.goals_against}",
            f"- Win rate: {record.win_rate:.1%}",
        ]
        return "\n".join(lines)

    def team_profile(self, team: str) -> str:
        """Everything the graph knows about one team: competitions, seasons,
        all-time record, biggest win and FIFA squad."""
        resolved = self._team(team)
        if isinstance(resolved, str):
            return resolved
        key = resolved.key
        matches = self.data.matches_for_team(key)
        lines = [f"{resolved.display}"
                 + (f" ({resolved.state})" if resolved.state else "")]

        by_comp: dict[str, set[int]] = defaultdict(set)
        for match in matches:
            if match.season:
                by_comp[match.competition_display].add(match.season)
        if by_comp:
            lines.append("Competitions in dataset:")
            for name, seasons in sorted(by_comp.items()):
                span = f"{min(seasons)}-{max(seasons)}"
                lines.append(f"- {name}: {span}")
        else:
            lines.append("No matches found for this team in the dataset.")

        record = TeamRecord()
        best: Match | None = None
        for match in matches:
            result = match.result_for(key)
            if result is None:
                continue
            is_home = match.home.key == key
            record.add(
                result,
                match.home_goals if is_home else match.away_goals or 0,
                match.away_goals if is_home else match.home_goals or 0,
            )
            if result == "W":
                margin = match.margin
                if best is None or margin > best.margin:
                    best = match
        if record.matches:
            lines.append(
                f"All-time record: {record.wins}W {record.draws}D {record.losses}L, "
                f"GF {record.goals_for}, GA {record.goals_against} "
                f"({record.matches} played matches)"
            )
        if best is not None:
            lines.append(f"Biggest win in dataset: {best.describe(include_stats=False)}")

        fifa_count, fifa_avg = self._fifa_squad(key)
        if fifa_count:
            lines.append(
                f"FIFA dataset: {fifa_count} players, average rating {fifa_avg:.1f}"
            )
        else:
            # Brazilian clubs absent from the FIFA dataset (licensing).
            unlicensed = {
                "flamengorj", "palmeirassp", "corinthianssp", "saopaulosp", "vascorj",
            }
            lines.append("FIFA dataset: no players recorded for this club.")
            if key in unlicensed:
                lines.append(f"Note: {FIFA_UNLICENSED_NOTE}")
        return "\n".join(lines)

    def _fifa_squad(self, team_key: str) -> tuple[int, float]:
        players = [
            p for p in self.data.players if p.club
            and self.data.club_team_key(p.club) == team_key
        ]
        if not players:
            return 0, 0.0
        return len(players), sum(p.overall for p in players) / len(players)

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------

    def league_standings(
        self,
        competition: str = "brasileirao",
        season=None,
        venue: str = "all",
    ) -> str:
        """League table computed from match results, with champion and
        (for Serie A/B) relegated teams."""
        comp_id, comp_error = self._competition(competition)
        if comp_error:
            return comp_error
        if comp_id is None:
            comp_id = "brasileirao"
        if not is_league(comp_id):
            return (
                f"{COMPETITIONS[comp_id]} is a knockout competition - no league "
                f"table exists. Use the finals tool for deciding matches, or "
                f"search_matches with a stage filter."
            )
        seasons = self.data.seasons_for(comp_id)
        if not seasons:
            return f"No matches loaded for {COMPETITIONS[comp_id]}."
        season_int = (
            self._season_int(season) if season not in (None, "") else seasons[-1]
        )
        if season_int is None:
            return f"Season '{season}' is not a valid year."
        if season_int not in seasons:
            span = f"{seasons[0]}-{seasons[-1]}"
            return (
                f"No {COMPETITIONS[comp_id]} data for {season_int} "
                f"(available seasons: {span})."
            )

        venue_key = (venue or "all").strip().lower()
        if venue_key not in ("all", "home", "away"):
            venue_key = "all"

        table: dict[str, TeamRecord] = defaultdict(TeamRecord)
        played_count = 0
        for match in self.data.matches:
            if match.competition != comp_id or match.season != season_int:
                continue
            if not match.played:
                continue
            played_count += 1
            home_res = (
                "W" if match.home_goals > match.away_goals
                else "D" if match.home_goals == match.away_goals
                else "L"
            )
            away_res = "L" if home_res == "W" else "D" if home_res == "D" else "W"
            if venue_key == "all":
                table[match.home.key].add(home_res, match.home_goals, match.away_goals)
                table[match.away.key].add(away_res, match.away_goals, match.home_goals)
            elif venue_key == "home":
                table[match.home.key].add(home_res, match.home_goals, match.away_goals)
            else:  # away-only table
                table[match.away.key].add(away_res, match.away_goals, match.home_goals)

        ranked = sorted(
            table.items(),
            key=lambda kv: (
                -kv[1].points,
                -kv[1].wins,
                -kv[1].goal_diff,
                -kv[1].goals_for,
                self.data.registry.display(kv[0]),
            ),
        )
        if not ranked:
            return f"No played matches for {COMPETITIONS[comp_id]} {season_int}."

        venue_note = "" if venue_key == "all" else f" ({venue_key} matches only)"
        lines = [f"{COMPETITIONS[comp_id]} {season_int} standings{venue_note} "
                 f"(computed from {played_count} played matches):"]
        relegated_zone = (
            venue_key == "all"
            and comp_id in ("brasileirao", "serie_b")
            and len(ranked) >= 16
        )
        for position, (key, record) in enumerate(ranked, start=1):
            entry = (
                f"{position}. {self.data.registry.display(key)} - {record.points} pts "
                f"({record.wins}W, {record.draws}D, {record.losses}L, "
                f"GF {record.goals_for}, GA {record.goals_against})"
            )
            if position == 1 and venue_key == "all":
                entry += " - Champion"
            if relegated_zone and position > len(ranked) - 4:
                entry += " - Relegated"
            lines.append(entry)
        note = self.data.notes.get((comp_id, season_int))
        if note:
            lines.append(f"Note: {note}")
        return "\n".join(lines)

    def finals(self, competition: str) -> str:
        """Deciding matches per season for cup competitions."""
        comp_id, comp_error = self._competition(competition)
        if comp_error:
            return comp_error
        if comp_id is None:
            return "Please specify a competition (Copa do Brasil or Libertadores)."
        if comp_id == "libertadores":
            return self._libertadores_finals()
        if comp_id == "copa_do_brasil":
            return self._copa_finals()
        return (
            f"{COMPETITIONS[comp_id]} is a league - see league_standings for "
            f"the champion by season."
        )

    def _libertadores_finals(self) -> str:
        lines = ["Copa Libertadores finals in dataset:"]
        seasons = self.data.seasons_for("libertadores")
        for season in seasons:
            matches = [
                m for m in self.data.matches
                if m.competition == "libertadores" and m.season == season
                and (m.stage or "").lower() == "final"
            ]
            if not matches:
                semis = [
                    m for m in self.data.matches
                    if m.competition == "libertadores" and m.season == season
                    and (m.stage or "").lower() == "semifinals"
                ]
                semi_teams = sorted(
                    {m.home.display for m in semis} | {m.away.display for m in semis}
                )
                lines.append(
                    f"{season}: no final recorded (semifinalists: "
                    f"{', '.join(semi_teams)})."
                )
                note = self.data.notes.get(("libertadores", season))
                if note:
                    lines.append(f"  Note: {note}")
                continue
            lines.append(self._two_leg_summary(matches, season, away_goals_before=2021))
        return "\n".join(lines)

    def _two_leg_summary(self, matches: list[Match], season: int,
                         away_goals_before: int | None) -> str:
        played = [m for m in matches if m.played]
        if not played:
            teams = f"{matches[0].home.display} vs {matches[0].away.display}"
            line = f"{season}: Final {teams} - result not recorded in dataset."
            note = self.data.notes.get((matches[0].competition, season))
            if note:
                line += f"\n  Note: {note}"
            return line
        first = played[0]
        a, b = first.home, first.away
        agg_a = agg_b = 0
        leg_lines = []
        away_a = away_b = 0  # away goals for team a / b
        for match in played:
            agg_a += match.home_goals if match.home.key == a.key else match.away_goals
            agg_b += match.away_goals if match.home.key == a.key else match.home_goals
            if match.home.key != a.key:
                away_a += match.away_goals
            else:
                away_b += match.away_goals
            leg_lines.append(match.describe(include_stats=False))
        summary = f"{season}: " + " / ".join(leg_lines)
        summary += f" - aggregate {a.display} {agg_a}-{agg_b} {b.display}"
        if agg_a != agg_b:
            winner = a if agg_a > agg_b else b
            summary += f", Champion: {winner.display}"
        elif away_goals_before is not None and season < away_goals_before:
            if away_a != away_b:
                winner = a if away_a > away_b else b
                summary += (
                    f" - {winner.display} won on away goals"
                    f" ({a.display} {away_a} away vs {b.display} {away_b} away)"
                )
            else:
                summary += " - level aggregate and away goals (penalties; winner not in dataset)"
        else:
            summary += " - level aggregate (decided on penalties; winner not in dataset)"
        return summary

    def _copa_finals(self) -> str:
        lines = ["Copa do Brasil finals in dataset:"]
        comp_matches = [
            m for m in self.data.matches if m.competition == "copa_do_brasil"
        ]
        seasons = sorted({m.season for m in comp_matches if m.season})
        for season in seasons:
            season_matches = [m for m in comp_matches if m.season == season]
            finals = [m for m in season_matches if (m.stage or "") == "Final"]
            if finals:
                note = ""
                if not any(m.round_label for m in finals):
                    note = " (inferred from the latest recorded matches of the season)"
                lines.append(self._two_leg_summary(finals, season, None) + note)
            else:
                lines.append(f"{season}: final not identifiable in dataset.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------

    def biggest_wins(
        self,
        competition: str | None = None,
        season=None,
        limit: int = 10,
    ) -> str:
        """Rank the biggest victory margins in the dataset."""
        matches = self._filter_matches(competition=competition, season=season)
        if isinstance(matches, str):
            return matches
        played = [m for m in matches if m.played]
        played.sort(key=lambda m: (-m.margin, -m.total_goals, m.date or date.min))
        if not played:
            return "No played matches found for the given filters."
        comp_note = (
            COMPETITIONS[resolve_competition(competition) or "brasileirao"]
            if competition else "all competitions"
        )
        season_note = f" {season}" if season not in (None, "") else ""
        lines = [f"Biggest victories ({comp_note}{season_note}):"]
        for position, match in enumerate(played[: max(1, limit)], start=1):
            lines.append(f"{position}. {match.describe(include_stats=False)}")
        return "\n".join(lines)

    def competition_info(self, competition: str | None = None, season=None) -> str:
        """Overview of one competition (or all): match counts, seasons,
        average goals and home/away win rates."""
        if competition is None:
            lines = ["Competitions in dataset:"]
            for comp_id, display in COMPETITIONS.items():
                matches = [m for m in self.data.matches if m.competition == comp_id]
                seasons = self.data.seasons_for(comp_id)
                span = f"{seasons[0]}-{seasons[-1]}" if seasons else "-"
                lines.append(
                    f"- {display}: {len(matches)} matches "
                    f"({sum(1 for m in matches if m.played)} played), "
                    f"seasons {span}"
                )
            lines.append(
                "Ask for a competition by name for detailed statistics."
            )
            return "\n".join(lines)

        comp_id, comp_error = self._competition(competition)
        if comp_error:
            return comp_error
        if comp_id is None:
            return self.competition_info(None)
        season_int = self._season_int(season) if season not in (None, "") else None
        matches = [m for m in self.data.matches if m.competition == comp_id]
        if season_int is not None:
            matches = [m for m in matches if m.season == season_int]
            if not matches:
                seasons = self.data.seasons_for(comp_id)
                return (
                    f"No data for {COMPETITIONS[comp_id]} in {season_int} "
                    f"(available: {seasons[0]}-{seasons[-1]})."
                )
        played = [m for m in matches if m.played]
        if not played:
            return f"No played matches for {COMPETITIONS[comp_id]}."
        total = len(played)
        goals = sum(m.total_goals for m in played)
        home_wins = sum(1 for m in played if m.home_goals > m.away_goals)
        draws = sum(1 for m in played if m.home_goals == m.away_goals)
        away_wins = total - home_wins - draws
        seasons = self.data.seasons_for(comp_id)
        span = f", seasons {seasons[0]}-{seasons[-1]}" if seasons and season_int is None else ""
        lines = [
            f"{COMPETITIONS[comp_id]}{span}:",
            f"- Matches played: {total} of {len(matches)} recorded",
            f"- Average goals per match: {goals / total:.2f}",
            f"- Home wins: {home_wins} ({home_wins / total:.1%})",
            f"- Draws: {draws} ({draws / total:.1%})",
            f"- Away wins: {away_wins} ({away_wins / total:.1%})",
        ]
        note = self.data.notes.get((comp_id, season_int or 0))
        if season_int is not None and note:
            lines.append(f"- Note: {note}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 6. Player queries
    # ------------------------------------------------------------------

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        sort: str = "overall",
        limit: int = DEFAULT_PLAYER_LIMIT,
    ) -> str:
        """Search the FIFA player database by name, nationality, club,
        position (code or role like 'Forward') and rating."""
        from .models import POSITION_GROUPS

        name_key = fold(name) if name else None
        nat_key = fold(nationality) if nationality else None
        club_key = fold(club) if club else None
        pos_key = fold(position) if position else None

        matches: list[Player] = []
        for player in self.data.players:
            if name_key and name_key not in fold(player.name):
                continue
            if nat_key and nat_key not in fold(player.nationality):
                continue
            if club_key:
                if not player.club:
                    continue  # free agents never match a club filter
                club_folded = fold(player.club)
                if not (club_key in club_folded or club_folded in club_key):
                    continue
            if pos_key:
                group = POSITION_GROUPS.get(player.position or "", "")
                if not (
                    pos_key == fold(player.position or "")
                    or pos_key == fold(group)
                ):
                    continue
            if min_overall is not None and player.overall < int(min_overall):
                continue
            if max_overall is not None and player.overall > int(max_overall):
                continue
            matches.append(player)

        sort_key = (sort or "overall").lower()
        if sort_key == "potential":
            matches.sort(key=lambda p: (-p.potential, p.name))
        elif sort_key == "age":
            matches.sort(key=lambda p: (p.age if p.age is not None else 999, p.name))
        elif sort_key == "name":
            matches.sort(key=lambda p: fold(p.name))
        else:
            matches.sort(key=lambda p: (-p.overall, -p.potential, p.name))

        if not matches:
            hint = ""
            if club_key and not any(
                p.club
                and (club_key in fold(p.club) or fold(p.club) in club_key)
                for p in self.data.players
            ):
                hint = " " + FIFA_UNLICENSED_NOTE
            return f"No players found for the given filters.{hint}"

        lines = [
            f"Players matching filters: {len(matches)} found "
            f"(showing up to {max(1, limit)})"
        ]
        for position, player in enumerate(matches[: max(1, limit)], start=1):
            club = player.club or "No club"
            details = [
                f"Overall: {player.overall}",
                f"Potential: {player.potential}",
                f"Position: {player.position or 'N/A'} ({player.position_group()})",
                f"Club: {club}",
            ]
            if player.age is not None:
                details.append(f"Age: {player.age}")
            if player.nationality:
                details.append(f"Nationality: {player.nationality}")
            lines.append(f"{position}. {player.name} - " + ", ".join(details))
        return "\n".join(lines)

    def players_by_club(
        self,
        nationality: str | None = "Brazil",
        brazilian_clubs_only: bool = True,
        limit: int = 20,
    ) -> str:
        """Aggregate players per club (count + average rating), optionally
        restricted to one nationality and to Brazilian league clubs."""
        nat_key = fold(nationality) if nationality else None
        buckets: dict[str, list[Player]] = defaultdict(list)
        for player in self.data.players:
            if nat_key and nat_key not in fold(player.nationality):
                continue
            if not player.club:
                continue
            if brazilian_clubs_only:
                team_key = self.data.club_team_key(player.club)
                if team_key is None:
                    continue
                buckets[self.data.registry.display(team_key)].append(player)
            else:
                buckets[player.club].append(player)
        if not buckets:
            return "No players found for the given filters."
        rows = sorted(
            buckets.items(),
            key=lambda kv: (-len(kv[1]), -sum(p.overall for p in kv[1]) / len(kv[1])),
        )
        nat_note = f" ({nationality})" if nationality else ""
        scope = (
            "Brazilian clubs (that also appear in the match datasets)"
            if brazilian_clubs_only else "all clubs"
        )
        lines = [f"Players by club{nat_note} - {scope}:"]
        for club, players in rows[: max(1, limit)]:
            avg = sum(p.overall for p in players) / len(players)
            lines.append(f"- {club}: {len(players)} players (avg rating: {avg:.0f})")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 7. Derbies
    # ------------------------------------------------------------------

    def derby_matches(
        self,
        derby: str | None = None,
        season=None,
        limit: int = 10,
    ) -> str:
        """List famous derbies, or all matches of one derby (optionally in
        one season)."""
        if derby is None:
            lines = ["Known derbies (clássicos):"]
            for entry in DERBIES:
                a = self.data.registry.teams.get(entry.team_a)
                b = self.data.registry.teams.get(entry.team_b)
                if a is None or b is None:
                    continue
                count = len(
                    self._pair_matches({entry.team_a, entry.team_b}, season=None)
                )
                lines.append(
                    f"- {entry.name} ({entry.region}): {a.display} x {b.display}"
                    f" - {count} matches in dataset"
                )
            return "\n".join(lines)

        found = find_derby(derby)
        if found is None:
            options = ", ".join(d.name for d in DERBIES)
            return f"Derby '{derby}' not found. Known derbies: {options}."
        a = self.data.registry.teams.get(found.team_a)
        b = self.data.registry.teams.get(found.team_b)
        if a is None or b is None:
            return f"Derby {found.name} references teams missing from the dataset."
        season_int = self._season_int(season) if season not in (None, "") else None
        matches = self._pair_matches({found.team_a, found.team_b}, season_int)
        title = f"{found.name} ({a.display} x {b.display})"
        if season_int is not None:
            title += f", {season_int}"
        if not matches:
            return f"{title}: no matches in dataset."
        lines = [f"{title} - {len(matches)} matches in dataset:"]
        for match in matches[: max(1, limit)]:
            lines.append(f"- {match.describe()}")
        hidden = len(matches) - min(len(matches), max(1, limit))
        if hidden > 0:
            lines.append(f"  (+{hidden} more matches in dataset)")
        lines.append(self._h2h_line(matches, found.team_a, None))
        return "\n".join(lines)

    def _pair_matches(self, pair: set[str], season: int | None) -> list[Match]:
        out = []
        for match in self.data.matches:
            if season is not None and match.season != season:
                continue
            if {match.home.key, match.away.key} == pair:
                out.append(match)
        out.sort(key=lambda m: (m.date is None, m.date or date.min), reverse=True)
        return out
