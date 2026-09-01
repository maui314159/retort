"""High-level query service over the knowledge base.

CONTEXT
-------
This is the layer the MCP tools call.  Every public method takes plain
strings/ints (as an LLM would produce), resolves teams/competitions
tolerantly and returns a human-readable, spec-formatted answer::

    Flamengo vs Fluminense (Fla-Flu derby):
    - 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A 2023, Round 22)

    Head-to-head in dataset: Flamengo 12 wins, Fluminense 8 wins, 7 draws

All responses are plain text so they can flow straight through the MCP
tool-result channel.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

from .analytics import (
    CompetitionStats,
    HeadToHead,
    StandingsRow,
    TeamRecord,
    best_records,
    biggest_wins as biggest_wins_impl,
    competition_stats,
    find_derbies,
    head_to_head as h2h_impl,
    standings as standings_impl,
    team_record,
)
from .loaders import COMPETITIONS, LEAGUE_COMPETITIONS, KnowledgeBase
from .models import Match, Player
from .normalize import Team, TeamRegistry, strip_accents

VENUES = ("all", "home", "away")

_POSITION_ALIASES = {
    "gk": "GK", "goalkeeper": "GK", "goleiro": "GK",
    "def": "DEF", "defense": "DEF", "defender": "DEF", "defender ": "DEF",
    "mid": "MID", "midfielder": "MID", "midfield": "MID",
    "fwd": "FWD", "forward": "FWD", "forwards": "FWD", "striker": "FWD",
    "atacante": "FWD",
}

_NATIONALITY_ALIASES = {"brasil": "Brazil", "brazil": "Brazil", "bra": "Brazil"}


class SoccerDataService:
    """Facade answering every supported query category from the spec."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self.registry: TeamRegistry = kb.registry
        self.matches: list[Match] = kb.matches
        self.players: list[Player] = kb.players

        # Precomputed indexes (queries must stay well under the spec's
        # 2s/5s performance budget).
        self._by_comp: dict[str, list[Match]] = {}
        for m in self.matches:
            self._by_comp.setdefault(m.competition, []).append(m)
        self._by_comp_season: dict[tuple[str, int], list[Match]] = {}
        for m in self.matches:
            if m.season is not None:
                self._by_comp_season.setdefault((m.competition, m.season), []).append(m)
        self._seasons: dict[str, list[int]] = {
            comp: sorted({m.season for m in ms if m.season is not None})
            for comp, ms in self._by_comp.items()
        }
        self._players_by_name = {}
        for p in self.players:
            self._players_by_name.setdefault(_fold(p.name), []).append(p)

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def _resolve_competition(self, competition: str | None) -> str | None:
        if not competition:
            return None
        key = _fold(competition)
        if key in COMPETITIONS:
            return COMPETITIONS[key]
        for canon in sorted(self._by_comp):
            if _fold(canon) == key:
                return canon
        # tolerate "brasileirao", "serie a 2023", "campeonato brasileiro"...
        for alias, canon in COMPETITIONS.items():
            if key.startswith(alias) or alias.startswith(key) and len(key) >= 4:
                return canon
        return None

    def _bad_competition(self, competition: str | None) -> str | None:
        """Error message when a competition was given but cannot be resolved."""
        if competition and self._resolve_competition(competition) is None:
            return self._competition_not_found(competition)
        return None

    def _resolve_team(self, query: str) -> tuple[Team | None, str]:
        """Resolve a team name; returns ``(team, note)``.

        ``note`` explains disambiguation (e.g. plain "Botafogo" -> the
        famous RJ club) or lists alternatives when resolution fails.
        """
        candidates = self.registry.resolve(query)
        if not candidates:
            return None, ""
        team = candidates[0]
        note = ""
        if len(candidates) > 1:
            others = ", ".join(t.display for t in candidates[1:4])
            note = f" (interpreted as {team.display}; other candidates: {others})"
        return team, note

    @staticmethod
    def _season_of(value: int | str | None) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(str(value).strip())
        except ValueError:
            return None

    @staticmethod
    def _date_of(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value).strip()[:10])
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Match selection
    # ------------------------------------------------------------------

    def _select(
        self,
        competition: str | None = None,
        season: int | str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        team: str | None = None,  # entity key
        opponent: str | None = None,  # entity key
        venue: str = "all",
    ) -> list[Match]:
        comp = self._resolve_competition(competition)
        year = self._season_of(season)
        if comp is not None and year is not None:
            base = list(self._by_comp_season.get((comp, year), []))
        elif comp is not None:
            base = self._by_comp.get(comp, [])
        elif year is not None:
            base = [m for m in self.matches if m.season == year]
        else:
            base = self.matches

        d_from, d_to = self._date_of(date_from), self._date_of(date_to)
        out: list[Match] = []
        for m in base:
            if team is not None:
                if venue == "home" and m.home != team:
                    continue
                if venue == "away" and m.away != team:
                    continue
                if venue == "all" and team not in (m.home, m.away):
                    continue
                if opponent is not None and opponent not in (m.home, m.away):
                    continue
            elif opponent is not None and opponent not in (m.home, m.away):
                continue
            if d_from is not None and (m.date is None or m.date < d_from):
                continue
            if d_to is not None and (m.date is None or m.date > d_to):
                continue
            out.append(m)
        return out

    def _stage_filter(self, matches: list[Match], stage: str | None) -> list[Match]:
        if not stage:
            return matches
        aliases = {
            "finals": "final",
            "semi final": "semifinal",
            "semi-finals": "semifinal",
            "semifinals": "semifinal",
            "quarter finals": "quarterfinals",
            "quarterfinals": "quarterfinals",
            "group stage": "group stage",
            "groupstage": "group stage",
        }
        wanted = aliases.get(_fold(stage), _fold(stage))
        out = []
        for m in matches:
            labels = {_fold(x) for x in (m.round_label, m.stage) if x}
            if wanted in labels:
                out.append(m)
        return out

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _display(self, key: str) -> str:
        base, _, region = key.rpartition("|")
        return self.registry.display_name(base, region or None)

    def _match_line(self, m: Match) -> str:
        when = m.date.isoformat() if m.date else "date unknown"
        comp = m.competition
        bits = []
        if m.season is not None:
            bits.append(str(m.season))
        if m.round_label:
            bits.append(m.round_label)
        ctx = f" ({comp} {' '.join(bits)})" if bits else f" ({comp})"
        return f"{when}: {self._display(m.home)} {m.score_str()} {self._display(m.away)}{ctx}"

    @staticmethod
    def _showing(total: int, shown: int) -> str:
        return f"\n(showing {shown} of {total} matches)" if total > shown else ""

    # ------------------------------------------------------------------
    # 1. Match queries
    # ------------------------------------------------------------------

    def list_competitions(self) -> str:
        lines = ["Competitions in the dataset:"]
        for comp in sorted(self._by_comp):
            seasons = self._seasons[comp]
            if seasons:
                span = f"{seasons[0]}-{seasons[-1]}" if len(seasons) > 1 else str(seasons[0])
                lines.append(
                    f"- {comp}: {len(self._by_comp[comp]):,} matches, seasons {span}"
                )
        total_players = len(self.players)
        lines.append(
            f"\nPlayer data: FIFA dataset with {total_players:,} players "
            f"({sum(1 for p in self.players if _fold(p.nationality) == 'brazil'):,} Brazilians)."
        )
        lines.append(
            "\nCompetitions can be referenced as: "
            + ", ".join(f'"{c}"' for c in ("Brasileirão Série A", "Série B", "Série C", "Copa do Brasil", "Libertadores"))
        )
        return "\n".join(lines)

    def list_teams(self, competition: str | None = None, season: int | str | None = None, limit: int = 40) -> str:
        if (bad := self._bad_competition(competition)) is not None:
            return bad
        comp = self._resolve_competition(competition)
        year = self._season_of(season)
        matches = self._select(competition=comp, season=year)
        if not matches:
            return self._no_matches(comp, year)
        counts: dict[str, int] = {}
        for m in matches:
            counts[m.home] = counts.get(m.home, 0) + 1
            counts[m.away] = counts.get(m.away, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], self._display(kv[0])))
        label = f"{comp} {year}" if comp and year else (comp or "all competitions")
        lines = [f"Teams in {label} ({len(ranked)} teams):"]
        for key, n in ranked[:limit]:
            team = self.registry.teams_by_key().get(key)
            squad = f", {team.player_count} FIFA players" if team and team.player_count else ""
            lines.append(f"- {self._display(key)}: {n} matches{squad}")
        lines.append(self._showing(len(ranked), min(limit, len(ranked))))
        return "\n".join(lines)

    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        stage: str | None = None,
        limit: int = 20,
    ) -> str:
        team_entity = opponent_entity = None
        header_bits: list[str] = []
        if team:
            team_entity, note = self._resolve_team(team)
            if team_entity is None:
                return self._team_not_found(team)
            header_bits.append(team_entity.display + note)
        if opponent:
            opponent_entity, note = self._resolve_team(opponent)
            if opponent_entity is None:
                return self._team_not_found(opponent)
            header_bits.append(opponent_entity.display + note)

        if (bad := self._bad_competition(competition)) is not None:
            return bad

        matches = self._select(
            competition=competition,
            season=season,
            date_from=date_from,
            date_to=date_to,
            team=team_entity.key if team_entity else None,
            opponent=opponent_entity.key if opponent_entity else None,
        )
        matches = self._stage_filter(matches, stage)

        if not matches:
            comp = self._resolve_competition(competition)
            extra = self._stage_hint(stage, comp)
            return "No matches found for those criteria." + extra

        # Newest first (spec example lists most recent matches first).
        ordered = sorted(matches, key=_recency_key, reverse=True)
        shown = ordered[: max(1, min(limit, 50))]

        title = " vs ".join(header_bits) if header_bits else "Matches"
        comp = self._resolve_competition(competition)
        scope = f" in {comp}" if comp else ""
        if season:
            scope += f" {self._season_of(season)}"
        lines = [f"{title}{scope} — {len(matches)} matches in dataset:"]
        lines.extend(f"- {self._match_line(m)}" for m in shown)
        lines.append(self._showing(len(matches), len(shown)))

        if team_entity and opponent_entity:
            h2h = h2h_impl(matches, team_entity.key, opponent_entity.key, self.registry)
            lines.append(
                f"\nHead-to-head: {h2h.display_a} {h2h.wins_a} wins, "
                f"{h2h.display_b} {h2h.wins_b} wins, {h2h.draws} draws"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 2. Team queries
    # ------------------------------------------------------------------

    def head_to_head(self, team_a: str, team_b: str, competition: str | None = None) -> str:
        if (bad := self._bad_competition(competition)) is not None:
            return bad
        entity_a, note_a = self._resolve_team(team_a)
        entity_b, note_b = self._resolve_team(team_b)
        if entity_a is None:
            return self._team_not_found(team_a)
        if entity_b is None:
            return self._team_not_found(team_b)
        if entity_a.key == entity_b.key:
            return "Please provide two different teams."

        matches = self._select(competition=competition)
        h2h = h2h_impl(matches, entity_a.key, entity_b.key, self.registry)
        derby = find_derbies(h2h.matches)
        derby_name = derby[0][0] if derby else None

        title = f"{h2h.display_a} vs {h2h.display_b}"
        if derby_name:
            title += f" ({derby_name})"
        lines = [f"{title} — {h2h.total} matches in dataset:"]
        ordered = sorted(h2h.matches, key=_recency_key, reverse=True)
        for m in ordered[:15]:
            lines.append(f"- {self._match_line(m)}")
        if h2h.total > 15:
            lines.append(f"... ({h2h.total - 15} more matches in dataset)")
        lines.append(
            f"\nHead-to-head in dataset: {h2h.display_a} {h2h.wins_a} wins, "
            f"{h2h.display_b} {h2h.wins_b} wins, {h2h.draws} draws"
        )
        lines.append(
            f"Goals: {h2h.display_a} {h2h.goals_a}, {h2h.display_b} {h2h.goals_b}"
        )
        return "\n".join(lines)

    def team_stats(
        self,
        team: str,
        competition: str | None = None,
        season: int | str | None = None,
        venue: str = "all",
    ) -> str:
        entity, note = self._resolve_team(team)
        if entity is None:
            return self._team_not_found(team)
        if (bad := self._bad_competition(competition)) is not None:
            return bad
        venue = _fold(venue) if venue else "all"
        if venue not in VENUES:
            venue = "all"

        comp = self._resolve_competition(competition)
        year = self._season_of(season)
        matches = self._select(competition=comp, season=year, team=entity.key, venue=venue)
        record = team_record(matches, entity.key, self.registry, venue=venue)

        label_bits = [entity.display + note]
        label_bits.append(comp or "all competitions")
        if year:
            label_bits.append(str(year))
        venue_word = {"all": "", "home": "home ", "away": "away "}[venue]
        header = f"{' '.join(label_bits)} {venue_word}record".replace("  ", " ")

        if record.matches == 0:
            return f"{header}: no scored matches found in the dataset."
        lines = [f"{header}:"]
        lines.extend(f"- {part}" for part in record.line().split("\n"))
        return "\n".join(lines)

    def team_profile(self, team: str) -> str:
        entity, note = self._resolve_team(team)
        if entity is None:
            return self._team_not_found(team)
        matches = self._select(team=entity.key)
        record = team_record(matches, entity.key, self.registry)

        lines = [f"{entity.display}{note} — Team Profile"]

        comps: dict[str, list[int]] = {}
        for m in matches:
            if m.season is not None:
                comps.setdefault(m.competition, []).append(m.season)
        if comps:
            lines.append("Competitions played (in dataset):")
            for comp in sorted(comps):
                years = sorted(set(comps[comp]))
                span = f"{years[0]}-{years[-1]}" if len(years) > 1 else str(years[0])
                lines.append(f"- {comp}: {len(comps[comp])} matches ({span})")
        else:
            lines.append("No matches recorded in the match datasets.")

        if record.matches:
            lines.append(
                f"All-time record (scored matches): {record.matches} matches — "
                f"{record.wins}W {record.draws}D {record.losses}L, "
                f"goals {record.goals_for}:{record.goals_against} "
                f"(win rate {record.win_rate * 100:.1f}%)"
            )

        titles = self._titles(entity.key)
        if titles:
            lines.append("Titles in dataset: " + ", ".join(titles))

        biggest = biggest_wins_impl(matches, self.registry, limit=1)
        if biggest:
            margin, m = biggest[0]
            lines.append(f"Biggest win in dataset: {self._match_line(m)}")

        squad_lines = self._squad_summary(entity)
        lines.extend(squad_lines)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 3. Player queries
    # ------------------------------------------------------------------

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
        limit: int = 20,
    ) -> str:
        results = self._filter_players(
            name=name,
            nationality=nationality,
            club=club,
            position=position,
            min_overall=min_overall,
            max_overall=max_overall,
        )
        results.sort(key=lambda p: (-(p.overall or 0), p.name))
        if not results:
            return "No players match those criteria in the FIFA dataset."

        lines = [f"{len(results)} players match:"]
        shown = results[: max(1, min(limit, 50))]
        for p in shown:
            lines.append(f"- {self._player_line(p)}")
        if len(results) > len(shown):
            lines.append(f"... ({len(results) - len(shown)} more)")
        return "\n".join(lines)

    def top_players(
        self,
        club: str | None = None,
        nationality: str | None = None,
        position: str | None = None,
        limit: int = 10,
    ) -> str:
        results = self._filter_players(club=club, nationality=nationality, position=position)
        results.sort(key=lambda p: (-(p.overall or 0), p.name))
        if not results:
            return "No players match those criteria in the FIFA dataset."
        shown = results[: max(1, min(limit, 50))]
        scope_bits = [b for b in (club, nationality, position) if b]
        scope = f" ({', '.join(scope_bits)})" if scope_bits else ""
        lines = [f"Top-rated players{scope}:"]
        for i, p in enumerate(shown, start=1):
            lines.append(f"{i}. {self._player_line(p)}")
        return "\n".join(lines)

    def player_profile(self, name: str) -> str:
        matches = self._players_by_name.get(_fold(name), [])
        if not matches:
            # substring fallback
            needle = _fold(name)
            matches = [p for p in self.players if needle in _fold(p.name)]
        if not matches:
            close = [p.name for p in sorted(self.players, key=lambda p: -_token_overlap(needle, _fold(p.name)))[:5]]
            return f"Player {name!r} not found in the FIFA dataset. Closest: {', '.join(close)}"
        if len(matches) > 1:
            return (
                f"{len(matches)} players match {name!r}:\n"
                + "\n".join(f"- {self._player_line(p)}" for p in matches[:10])
                + "\nUse the exact listed name for a full profile."
            )
        p = matches[0]
        lines = [f"{p.name} — Player Profile"]
        basics = [f"Overall: {p.overall}", f"Potential: {p.potential}"]
        if p.age is not None:
            basics.append(f"Age: {p.age}")
        basics.append(f"Nationality: {p.nationality}")
        if p.position:
            basics.append(f"Position: {p.position} ({p.position_group})")
        if p.jersey is not None:
            basics.append(f"Jersey: #{p.jersey}")
        if p.club:
            basics.append(f"Club: {p.club}")
        if p.foot:
            basics.append(f"Preferred foot: {p.foot}")
        if p.height or p.weight:
            basics.append(f"Height/Weight: {p.height or '?'} cm / {p.weight or '?'} kg")
        if p.value:
            basics.append(f"Market value: {p.value}")
        if p.wage:
            basics.append(f"Wage: {p.wage}")
        lines.append(" | ".join(basics))

        key_skills = [
            ("Pace", ("SprintSpeed", "Acceleration")),
            ("Shooting", ("Finishing", "ShotPower", "LongShots")),
            ("Passing", ("ShortPassing", "LongPassing", "Vision")),
            ("Dribbling", ("Dribbling", "BallControl", "Agility")),
            ("Defending", ("Marking", "StandingTackle", "Interceptions")),
            ("Physical", ("Strength", "Stamina", "Jumping")),
            ("Goalkeeping", ("GKDiving", "GKReflexes", "GKHandling")),
        ]
        skill_bits = []
        for label, cols in key_skills:
            vals = [p.skills[c] for c in cols if c in p.skills]
            if vals:
                skill_bits.append(f"{label}: {sum(vals) / len(vals):.0f}")
        if skill_bits:
            lines.append("Attributes: " + " | ".join(skill_bits))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 4. Competition queries
    # ------------------------------------------------------------------

    def standings(self, competition: str = "Brasileirão Série A", season: int | str | None = None) -> str:
        comp = self._resolve_competition(competition)
        if comp is None:
            return self._competition_not_found(competition)
        year = self._season_of(season)
        if year is None:
            seasons = self._seasons.get(comp, [])
            return (
                f"Please specify a season for {comp}. "
                f"Available seasons: {', '.join(map(str, seasons))}"
            )
        matches = self._by_comp_season.get((comp, year), [])
        if not matches:
            return self._no_matches(comp, year)
        if comp not in LEAGUE_COMPETITIONS:
            return (
                f"{comp} is a knockout competition — a league table is not "
                f"meaningful. Use the 'finals' tool for deciding matches or "
                f"'search_matches' with stage filters (e.g. stage='final', "
                f"'semifinal')."
            )

        table = standings_impl(matches, self.registry)
        scored = sum(1 for m in matches if m.has_score)
        lines = [
            f"{year} {comp} — Standings (calculated from {len(matches)} matches, "
            f"{scored} with scores):"
        ]
        for row in table:
            tag = " - Champion" if row.position == 1 else ""
            lines.append(row.line() + tag)
        relegated = [r.team_display for r in table[-4:]]
        lines.append(f"\nRelegated (bottom 4): {', '.join(relegated)}")
        if scored < len(matches):
            lines.append(
                f"Note: {len(matches) - scored} matches have no recorded score; "
                "the table covers scored matches only."
            )
        return "\n".join(lines)

    def finals(self, competition: str | None = None, season: int | str | None = None) -> str:
        if (bad := self._bad_competition(competition)) is not None:
            return bad
        comp = self._resolve_competition(competition)
        year = self._season_of(season)
        matches = self._select(competition=comp, season=year)
        finals = [
            m
            for m in matches
            if _fold(m.round_label) == "final" or m.stage == "final"
        ]
        if not finals:
            return "No finals found for those criteria."

        # Group two-legged finals by season + pairing.
        groups: dict[tuple, list[Match]] = {}
        for m in finals:
            gk = (m.season or 0, tuple(sorted((m.home, m.away))), m.competition)
            groups.setdefault(gk, []).append(m)

        label = comp or "all competitions"
        lines = [f"Finals in {label}" + (f" {year}" if year else "") + ":"]
        for (season_key, pair, comp_name), ms in sorted(
            groups.items(), key=lambda kv: (kv[0][0], kv[0][2])
        ):
            legs = sorted(ms, key=lambda m: m.date or date.min)
            season_txt = str(season_key) if season_key else "unknown season"
            for m in legs:
                lines.append(f"- {season_txt} {comp_name}: {self._match_line(m)}")
            summary = self._aggregate_summary(legs)
            if summary:
                lines.append(f"  {summary}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 5. Statistical analysis
    # ------------------------------------------------------------------

    def biggest_wins(
        self, competition: str | None = None, season: int | str | None = None, limit: int = 10
    ) -> str:
        if (bad := self._bad_competition(competition)) is not None:
            return bad
        comp = self._resolve_competition(competition)
        matches = self._select(competition=comp, season=season)
        wins = biggest_wins_impl(matches, self.registry, limit=max(1, min(limit, 25)))
        if not wins:
            return self._no_matches(comp, self._season_of(season))
        label = f"{comp} " if comp else ""
        if season:
            label += f"{self._season_of(season)} "
        lines = [f"Biggest victories in {label}(provided data):"]
        for i, (margin, m) in enumerate(wins, start=1):
            lines.append(f"{i}. {self._match_line(m)}")
        return "\n".join(lines)

    def stats(self, competition: str | None = None, season: int | str | None = None) -> str:
        if (bad := self._bad_competition(competition)) is not None:
            return bad
        comp = self._resolve_competition(competition)
        matches = self._select(competition=comp, season=season)
        if not matches:
            return self._no_matches(comp, self._season_of(season))
        agg = competition_stats(matches)
        label = f"{comp}" if comp else "All competitions"
        if season:
            label += f" {self._season_of(season)}"
        lines = [f"{label} — statistics (provided data):"]
        lines.append(f"- Matches: {agg.total:,} ({agg.scored:,} with recorded scores)")
        if agg.scored:
            lines.append(f"- Average goals per match: {agg.avg_goals:.2f}")
            lines.append(
                f"- Home wins: {agg.home_win_pct * 100:.1f}%, "
                f"Draws: {agg.draw_pct * 100:.1f}%, "
                f"Away wins: {agg.away_win_pct * 100:.1f}%"
            )
        top_scorers = self._top_scoring_teams(matches, 3)
        if top_scorers:
            lines.append(
                "- Top scoring teams: "
                + ", ".join(f"{d} ({g})" for d, g in top_scorers)
            )
        if comp is None or comp in LEAGUE_COMPETITIONS:
            for venue in ("home", "away"):
                best = best_records(
                    matches, self.registry, venue=venue,
                    min_matches=5 if season else 50, limit=3,
                )
                if best:
                    lines.append(
                        f"- Best {venue} records (win rate, "
                        f"min {5 if season else 50} matches): "
                        + ", ".join(
                            f"{r.team_display} {r.win_rate * 100:.0f}% ({r.matches} matches)"
                            for r in best
                        )
                    )
        return "\n".join(lines)

    def derbies(self, season: int | str | None = None, competition: str | None = None) -> str:
        if (bad := self._bad_competition(competition)) is not None:
            return bad
        matches = self._select(competition=competition, season=season)
        found = find_derbies(matches)
        if not found:
            return "No derby matches found for those criteria."
        by_name: dict[str, list[Match]] = {}
        for name, m in found:
            by_name.setdefault(name, []).append(m)
        year = self._season_of(season)
        scope = f" in {year}" if year else ""
        lines = [f"Derby matches{scope} — {len(found)} matches between classic rivals:"]
        for name in sorted(by_name):
            ms = sorted(by_name[name], key=_recency_key, reverse=True)
            lines.append(f"\n{name} ({len(ms)} matches):")
            for m in ms[:5]:
                lines.append(f"- {self._match_line(m)}")
            if len(ms) > 5:
                lines.append(f"... ({len(ms) - 5} more)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _filter_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_overall: int | None = None,
    ) -> list[Player]:
        nat = _NATIONALITY_ALIASES.get(_fold(nationality or ""), nationality or "")
        nat_fold = _fold(nat)
        club_fold = _fold(club or "")
        pos_group = _POSITION_ALIASES.get(_fold(position or ""), "")
        pos_code = _fold(position or "").upper() if position else ""
        name_fold = _fold(name or "")

        out = []
        for p in self.players:
            if name_fold and name_fold not in _fold(p.name):
                continue
            if nat_fold and _fold(p.nationality) != nat_fold:
                continue
            if club_fold and club_fold not in _fold(p.club):
                continue
            if position:
                if not (
                    (p.position and p.position.upper() == pos_code)
                    or (pos_group and p.position_group == pos_group)
                ):
                    continue
            if min_overall is not None and (p.overall is None or p.overall < min_overall):
                continue
            if max_overall is not None and (p.overall is None or p.overall > max_overall):
                continue
            out.append(p)
        return out

    def _player_line(self, p: Player) -> str:
        bits = [f"{p.name} - Overall: {p.overall}"]
        if p.position:
            bits.append(f"Position: {p.position}")
        if p.club:
            bits.append(f"Club: {p.club}")
        if p.age is not None:
            bits.append(f"Age: {p.age}")
        if p.nationality:
            bits.append(f"Nationality: {p.nationality}")
        return ", ".join(bits)

    def _titles(self, team_key: str) -> list[str]:
        titles = []
        for comp in sorted(c for c in self._by_comp if c in LEAGUE_COMPETITIONS):
            for year in self._seasons[comp]:
                table = standings_impl(self._by_comp_season[(comp, year)], self.registry)
                if table and table[0].team == team_key:
                    titles.append(f"{comp} {year}")
        return titles

    def _top_scoring_teams(self, matches: list[Match], limit: int) -> list[tuple[str, int]]:
        goals: dict[str, int] = {}
        for m in matches:
            if not m.has_score:
                continue
            goals[m.home] = goals.get(m.home, 0) + (m.home_goals or 0)
            goals[m.away] = goals.get(m.away, 0) + (m.away_goals or 0)
        ranked = sorted(goals.items(), key=lambda kv: (-kv[1], self._display(kv[0])))
        return [(self._display(k), v) for k, v in ranked[:limit]]

    def _squad_summary(self, entity: Team) -> list[str]:
        if not entity.player_count:
            return []
        squad = [
            p for p in self.players
            if (t := self.registry.resolve_exact(p.club)) is not None and t.key == entity.key
        ]
        if not squad:
            return []
        squad.sort(key=lambda p: -(p.overall or 0))
        overalls = [p.overall for p in squad if p.overall is not None]
        avg = sum(overalls) / len(overalls) if overalls else 0.0
        lines = [
            f"Squad (FIFA data): {len(squad)} players, average rating {avg:.1f}. "
            "Top players:"
        ]
        for p in squad[:5]:
            lines.append(f"- {self._player_line(p)}")
        return lines

    def _aggregate_summary(self, legs: list[Match]) -> str:
        if not legs or not all(m.has_score for m in legs):
            return "Result: not computable (scores missing from dataset)."
        if len(legs) == 1:
            winner = legs[0].winner()
            if winner is None:
                return "Result: draw (single match)."
            return f"Winner: {self._display(winner)}"
        agg: dict[str, int] = {}
        for m in legs:
            agg[m.home] = agg.get(m.home, 0) + (m.home_goals or 0)
            agg[m.away] = agg.get(m.away, 0) + (m.away_goals or 0)
        total = ", ".join(f"{self._display(k)} {v}" for k, v in sorted(agg.items()))
        ranked = sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))
        if ranked[0][1] > ranked[1][1]:
            return f"Aggregate: {total} — {self._display(ranked[0][0])} wins"
        return f"Aggregate: {total} — level (penalty shootouts not in dataset)"

    def _team_not_found(self, query: str) -> str:
        suggestions = ", ".join(t.display for t in self.registry.teams[:8])
        return (
            f"Team {query!r} not found. Try a name like {suggestions}. "
            "Names are matched accent- and state-insensitively "
            "(e.g. 'palmeiras', 'Palmeiras-SP', 'Atletico Mineiro')."
        )

    def _competition_not_found(self, query: str) -> str:
        return (
            f"Competition {query!r} not found. Available: "
            + ", ".join(sorted(self._by_comp))
        )

    def _no_matches(self, competition: str | None, season: int | None) -> str:
        if competition and season is not None:
            seasons = self._seasons.get(competition, [])
            return (
                f"No matches found for {competition} {season}. "
                f"Available seasons: {', '.join(map(str, seasons))}"
            )
        return "No matches found for those criteria."

    def _stage_hint(self, stage: str | None, competition: str | None) -> str:
        if stage and competition and "libertadores" in _fold(competition):
            return (
                f"\nTip: Libertadores stages are 'group stage', 'round of 16', "
                f"'quarterfinals', 'semifinals', 'final'."
            )
        if stage and competition and "copa do brasil" in _fold(competition):
            return (
                "\nTip: Copa do Brasil final rounds are labeled 'Semifinal' "
                "and 'Final' (earlier rounds are numbered)."
            )
        return ""


# ----------------------------------------------------------------------
# Module helpers
# ----------------------------------------------------------------------


def _fold(text: str | None) -> str:
    return strip_accents(text or "").lower().strip()


def _token_overlap(a: str, b: str) -> int:
    ta, tb = set(a.split()), set(b.split())
    return len(ta & tb)


def _recency_key(m: Match):
    return (
        m.date.toordinal() if m.date else 0,
        m.season or 0,
    )
