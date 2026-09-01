"""Query engine for the Brazilian soccer datasets.

``SoccerData`` loads every CSV once, normalizes team identities, dedupes
fixtures shared between files, builds indexes and exposes query methods for
the five capability families required by the specification:

1. Match queries ........... ``search_matches``, ``head_to_head``
2. Team queries ............ ``team_stats``, ``team_profile``, ``best_records``
3. Player queries .......... ``search_players``, ``top_players``,
                             ``players_at_brazilian_clubs``
4. Competition queries ...... ``standings``, ``competition_finals``,
                             ``competition_info``, ``top_scoring_teams``
5. Statistical analysis .... ``goal_averages``, ``biggest_wins``, ``derbies``

plus knowledge-graph exploration (``graph_overview``, ``team_graph``,
``graph_paths``) and disambiguation support (``list_clubs``).

Every method returns a plain dict with a human-formatted ``summary``
string (mirroring the answer formats in the spec) plus structured fields.
"""

from __future__ import annotations

import difflib
from dataclasses import replace
from datetime import date
from pathlib import Path

from .clubs import CLUBS, DERBIES, Club, resolve_club
from .knowledge_graph import KnowledgeGraph, build_knowledge_graph
from .loaders import find_data_dir, load_matches, load_players
from .models import (
    COPA_DO_BRASIL,
    FAMILY_DISPLAY,
    LIBERTADORES,
    SERIE_A,
    SERIE_B,
    SERIE_C,
    Match,
    Player,
    TeamRecord,
)
from .normalize import normalize_text, parse_datetime

_FAMILY_MATCHES = {
    "serie a": SERIE_A,
    "serie b": SERIE_B,
    "serie c": SERIE_C,
    "copa do brasil": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "brasileirao": SERIE_A,
    "brasileirao serie a": SERIE_A,
    "brasileirao serie b": SERIE_B,
    "brasileirao serie c": SERIE_C,
    "brazilian cup": COPA_DO_BRASIL,
    "campeonato brasileiro": SERIE_A,
    "serie a brasileirao": SERIE_A,
}
LEAGUE_FAMILIES = frozenset({SERIE_A, SERIE_B, SERIE_C})

# Authoritative file per competition family. For a season covered by one of
# these files, its fixtures define the fixture set; rows from other files
# describing the same pairing (BR-Football dates are often shifted by a day)
# are merged in, and rows describing pairings the authoritative file does not
# have (mislabelled BR-Football rows) are dropped.
PREFERRED_SOURCES = {
    SERIE_A: ("Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv"),
    COPA_DO_BRASIL: ("Brazilian_Cup_Matches.csv",),
    LIBERTADORES: ("Libertadores_Matches.csv",),
}


def _resolve_family(competition: str | None) -> str | None:
    if not competition:
        return None
    return _FAMILY_MATCHES.get(normalize_text(competition))


class SoccerData:
    """In-memory dataset + indexes + query methods."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = find_data_dir(data_dir)
        raw_matches, club_cache = load_matches(self.data_dir)
        self.players: list[Player] = load_players(self.data_dir)
        self.matches, self.dropped_rows = self._dedupe(raw_matches)
        self._build_indexes(club_cache)

    # ------------------------------------------------------------------
    # loading / indexing
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_fixture(primary: Match, other: Match) -> Match:
        """Merge two rows describing the same fixture (same family, season
        and pairing). The primary row keeps its identity; missing fields
        (stats, stadium, stage, date) are filled from the other row."""
        extras = {primary.source, other.source, *primary.also_in_sources, *other.also_in_sources}
        updates = {}
        if primary.stage is None and other.stage is not None:
            updates["stage"] = other.stage
            updates["round"] = other.round
        if primary.date is None and other.date is not None:
            updates["date"] = other.date
        if primary.time is None and other.time is not None:
            updates["time"] = other.time
        if primary.stadium is None and other.stadium is not None:
            updates["stadium"] = other.stadium
        if primary.stats is None and other.stats is not None:
            updates["stats"] = other.stats
        if primary.home_goals is None and other.home_goals is not None:
            updates["home_goals"] = other.home_goals
            updates["away_goals"] = other.away_goals
        if updates:
            primary = replace(primary, **updates)
        if extras != {primary.source, *primary.also_in_sources}:
            primary = replace(primary, also_in_sources=tuple(sorted(extras - {primary.source})))
        return primary

    @staticmethod
    def _exact_date_dedup(rows: list[Match]) -> list[Match]:
        seen: dict = {}
        for row in rows:
            key = (row.date, row.home_team, row.away_team)
            if key in seen:
                seen[key] = SoccerData._merge_fixture(seen[key], row)
            else:
                seen[key] = row
        return list(seen.values())

    @staticmethod
    def _dedupe(raw: list[Match]) -> tuple[list[Match], int]:
        """Cross-file fixture reconciliation.

        For every (competition, season) covered by an authoritative file,
        that file's fixtures define the fixture set: rows from other files
        matching a fixture pairing are merged into it (BR-Football rows
        contribute extended statistics), rows without a matching pairing are
        dropped as mislabelled data. Seasons not covered by an authoritative
        file (e.g. Série A 2023, Copa do Brasil 2022-23) keep every row with
        an exact-date dedup safety net.
        """
        by_family_season: dict[tuple, list[Match]] = {}
        for m in raw:
            by_family_season.setdefault((m.family, m.season), []).append(m)

        out: list[Match] = []
        dropped = 0
        for (family, _season), rows in by_family_season.items():
            preferred = PREFERRED_SOURCES.get(family, ())
            present = [
                src for src in preferred if any(r.source == src for r in rows)
            ]
            if not present:
                out.extend(SoccerData._exact_date_dedup(rows))
                continue
            top = present[0]
            merged: dict[tuple, Match] = {}
            surplus: list[Match] = []
            for row in rows:
                if row.source == top:
                    key = (row.home_team, row.away_team)
                    if key in merged:  # anomalous duplicate within one file
                        surplus.append(row)
                    else:
                        merged[key] = row
            for row in rows:
                if row.source == top:
                    continue
                key = (row.home_team, row.away_team)
                if key in merged:
                    merged[key] = SoccerData._merge_fixture(merged[key], row)
                else:
                    dropped += 1
            out.extend(merged.values())
            out.extend(surplus)
        out.sort(key=lambda m: (m.date is None, m.date or date.min, m.family))
        return out, dropped

    def _build_indexes(self, club_cache: dict) -> None:
        self.clubs: dict[str, Club] = dict(CLUBS)
        for _raw_name, club in club_cache.items():
            self.clubs.setdefault(club.club_id, club)
        self._display: dict[str, str] = {}
        for m in self.matches:
            self._display[m.home_team] = m.home_display
            self._display[m.away_team] = m.away_display

        self._by_team: dict[str, list[Match]] = {}
        self._by_family_season: dict[tuple, list[Match]] = {}
        self._by_family: dict[str, list[Match]] = {}
        for m in self.matches:
            self._by_team.setdefault(m.home_team, []).append(m)
            self._by_team.setdefault(m.away_team, []).append(m)
            self._by_family.setdefault(m.family, []).append(m)
            if m.season is not None:
                self._by_family_season.setdefault((m.family, m.season), []).append(m)

        self._players_by_club: dict[str | None, list[Player]] = {}
        self._players_by_nationality: dict[str, list[Player]] = {}
        for p in self.players:
            self._players_by_club.setdefault(p.club_id, []).append(p)
            self._players_by_nationality.setdefault(p.nationality, []).append(p)

        # Exact-alias index over every club actually present in the data
        # (curated + fallback identities). Curated clubs are registered
        # first so ambiguous base names keep their curated owner.
        self._observed_alias: dict[str, Club] = {}
        for club_id, club in self.clubs.items():
            if club_id not in self._by_team:
                continue
            for alias in club.aliases:
                self._observed_alias.setdefault(alias, club)

        # Map every distinct FIFA club string (including foreign clubs like
        # "Paris Saint-Germain") to a club id so the knowledge graph gets a
        # plays_for edge for every player.
        from .clubs import fallback_club as _fallback_club

        self._fifa_club_map: dict[str, str] = {}
        for p in self.players:
            if not p.club or p.club in self._fifa_club_map:
                continue
            if p.club_id:
                self._fifa_club_map[p.club] = p.club_id
            else:
                foreign = _fallback_club(p.club)
                self.clubs.setdefault(foreign.club_id, foreign)
                self._fifa_club_map[p.club] = foreign.club_id

        self.kg: KnowledgeGraph = build_knowledge_graph(
            self.matches, self.players, self.clubs, self._display, self._fifa_club_map
        )

    # ------------------------------------------------------------------
    # resolution helpers
    # ------------------------------------------------------------------
    def _club_popularity(self, club_id: str) -> int:
        return len(self._by_team.get(club_id, ()))

    def _resolve(self, query: str) -> Club | None:
        """Resolve a team string against curated and observed identities.

        Curated registry first (resolve_club), then the exact-alias index
        of every club present in the data - this also resolves foreign
        Libertadores clubs ("Boca Juniors") and small fallback clubs.
        """
        if not query:
            return None
        club = resolve_club(query)
        if club is not None:
            return club
        return self._observed_alias.get(normalize_text(query))

    def resolve_team(self, query: str) -> tuple[Club | None, list[dict]]:
        """Resolve a user-supplied team name to a club.

        Returns (club, candidate_list). When the name matches exactly only
        the club is returned; otherwise candidates are ranked by how many
        matches the club appears in (so "Flamengo" outranks "Flamengo-PI").
        Near-miss names ("Flamengu") are matched fuzzily via difflib.
        """
        if not query:
            return None, []
        club = self._resolve(query)
        if club is not None:
            return club, []
        key = normalize_text(query)
        candidates = []
        seen_ids = set()
        for alias, club_obj in self._observed_alias.items():
            if not key:
                continue
            if key in alias or alias in key:
                if club_obj.club_id not in seen_ids:
                    candidates.append(club_obj)
                    seen_ids.add(club_obj.club_id)
        if not candidates and len(key) >= 4:
            # fuzzy typo tolerance ("Flamengu" -> Flamengo)
            names = {
                normalize_text(c.name): c
                for c in self._observed_alias.values()
            }
            for close in difflib.get_close_matches(key, list(names), n=6, cutoff=0.75):
                match = names[close]
                if match.club_id not in seen_ids:
                    candidates.append(match)
                    seen_ids.add(match.club_id)
        candidates.sort(key=lambda c: -self._club_popularity(c.club_id))
        return None, [
            {
                "club_id": c.club_id,
                "name": self._display.get(c.club_id, c.display),
                "matches_in_dataset": self._club_popularity(c.club_id),
            }
            for c in candidates[:6]
        ]

    def _require_team(self, query: str, param_name: str = "team") -> dict | None:
        club, candidates = self.resolve_team(query)
        if club is None:
            msg = f"Could not uniquely resolve {param_name} '{query}'."
            if candidates:
                names = ", ".join(c["name"] for c in candidates)
                msg += f" Did you mean: {names}?"
            return {"error": msg, "candidates": candidates}
        return None

    # ------------------------------------------------------------------
    # 1. match queries
    # ------------------------------------------------------------------
    def search_matches(
        self,
        team: str | None = None,
        opponent: str | None = None,
        competition: str | None = None,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        stage: str | None = None,
        limit: int = 50,
    ) -> dict:
        """Find matches by team, opponent, competition, season, date range, stage."""
        if team:
            err = self._require_team(team)
            if err:
                return err
        if opponent:
            err = self._require_team(opponent, "opponent")
            if err:
                return err
        team_id = self._resolve(team).club_id if team else None
        opp_id = self._resolve(opponent).club_id if opponent else None

        family = _resolve_family(competition)
        if competition and family is None:
            return {"error": f"Unknown competition '{competition}'. Valid: Série A, Série B, Série C, Copa do Brasil, Libertadores."}

        d_from = parse_datetime(date_from)[0] if date_from else None
        d_to = parse_datetime(date_to)[0] if date_to else None
        stage_key = normalize_text(stage) if stage else None

        pool = self.matches
        if family:
            pool = self._by_family.get(family, [])
        elif season is not None:
            pool = [m for m in pool if m.season == season]
        if family and season is not None:
            pool = self._by_family_season.get((family, season), [])

        results = []
        for m in pool:
            if team_id and team_id not in (m.home_team, m.away_team):
                continue
            if opp_id and opp_id not in (m.home_team, m.away_team):
                continue
            if team_id and opp_id and {m.home_team, m.away_team} != {team_id, opp_id}:
                continue
            if d_from and (m.date is None or m.date < d_from):
                continue
            if d_to and (m.date is None or m.date > d_to):
                continue
            if stage_key and not self._stage_matches(stage_key, m.stage):
                continue
            results.append(m)
        results.sort(key=lambda m: (m.date is None, m.date or date.min), reverse=True)

        total = len(results)
        limited = results[: max(1, limit)]
        header = self._match_filter_header(team_id, opp_id, family, season, d_from, d_to)
        lines = [f"{header}: {total} match(es) found"]
        for m in limited:
            lines.append(self._format_match_line(m))
        if total > len(limited):
            lines.append(f"... ({total - len(limited)} more matches in dataset)")
        return {
            "summary": "\n".join(lines),
            "total_matches": total,
            "returned": len(limited),
            "matches": [m.as_dict() for m in limited],
        }

    def head_to_head(self, team_a: str, team_b: str) -> dict:
        """Compare two teams head-to-head across every competition in the data."""
        for label, value in (("team_a", team_a), ("team_b", team_b)):
            err = self._require_team(value, label)
            if err:
                return err
        a = self._resolve(team_a)
        b = self._resolve(team_b)
        if a.club_id == b.club_id:
            return {"error": "Please provide two different teams."}

        fixtures = [
            m
            for m in self.matches
            if {m.home_team, m.away_team} == {a.club_id, b.club_id}
        ]
        fixtures.sort(key=lambda m: (m.date is None, m.date or date.min), reverse=True)

        rec_a = TeamRecord(a.club_id, a.display)
        rec_b = TeamRecord(b.club_id, b.display)
        for m in fixtures:
            res_a = m.result_for(a.club_id)
            if res_a is None:
                continue
            if m.home_team == a.club_id:
                rec_a.add(res_a, m.home_goals, m.away_goals)
                rec_b.add("W" if res_a == "L" else "D" if res_a == "D" else "L", m.away_goals, m.home_goals)
            else:
                rec_b.add("W" if res_a == "L" else "D" if res_a == "D" else "L", m.home_goals, m.away_goals)
                rec_a.add(res_a, m.away_goals, m.home_goals)

        lines = [
            f"Head-to-head: {a.display} vs {b.display}",
            f"Matches in dataset: {rec_a.matches}",
            f"{a.name} wins: {rec_a.wins}, {b.name} wins: {rec_b.wins}, draws: {rec_a.draws}",
            f"Goals: {a.name} {rec_a.goals_for}:{rec_a.goals_against} {b.name}",
        ]
        for m in fixtures[:10]:
            lines.append(self._format_match_line(m))
        if rec_a.matches > 10:
            lines.append(f"... ({rec_a.matches - 10} more matches in dataset)")
        return {
            "summary": "\n".join(lines),
            "team_a": rec_a.as_dict(),
            "team_b": rec_b.as_dict(),
            "total_matches": rec_a.matches,
            "matches": [m.as_dict() for m in fixtures[:25]],
        }

    # ------------------------------------------------------------------
    # 2. team queries
    # ------------------------------------------------------------------
    def team_stats(
        self,
        team: str,
        season: int | None = None,
        competition: str | None = None,
        venue: str | None = None,
    ) -> dict:
        """Win/draw/loss record and goals for a team, optionally filtered."""
        err = self._require_team(team)
        if err:
            return err
        club = self._resolve(team)
        family = _resolve_family(competition)
        if competition and family is None:
            return {"error": f"Unknown competition '{competition}'."}
        venue_key = (venue or "").lower()
        if venue_key not in ("", "home", "away", "all"):
            return {"error": "venue must be 'home', 'away' or 'all'."}

        record = TeamRecord(club.club_id, club.display)
        for m in self._by_team.get(club.club_id, ()):
            if season is not None and m.season != season:
                continue
            if family and m.family != family:
                continue
            if not m.played:
                continue
            if m.home_team == club.club_id:
                if venue_key == "away":
                    continue
                record.add(m.result_for(club.club_id), m.home_goals, m.away_goals)
            else:
                if venue_key == "home":
                    continue
                record.add(m.result_for(club.club_id), m.away_goals, m.home_goals)

        if record.matches == 0:
            return {
                "summary": f"No matches found for {club.display} with these filters.",
                "record": None,
            }
        scope = self._scope_label(family, season, venue_key)
        lines = [
            f"{club.display} record ({scope}):",
            f"- Matches: {record.matches}",
            f"- Wins: {record.wins}, Draws: {record.draws}, Losses: {record.losses}",
            f"- Goals For: {record.goals_for}, Goals Against: {record.goals_against}",
            f"- Win rate: {record.win_rate * 100:.1f}%",
        ]
        return {
            "summary": "\n".join(lines),
            "record": record.as_dict(),
        }

    def team_profile(self, team: str) -> dict:
        """Cross-file profile: competitions played, seasons, record, squad."""
        err = self._require_team(team)
        if err:
            return err
        club = self._resolve(team)
        fixtures = self._by_team.get(club.club_id, [])
        by_family: dict[str, dict] = {}
        for m in fixtures:
            entry = by_family.setdefault(
                m.family, {"family": m.family, "seasons": set(), "matches": 0, "wins": 0, "draws": 0, "losses": 0}
            )
            entry["matches"] += 1
            if m.season is not None:
                entry["seasons"].add(m.season)
            res = m.result_for(club.club_id)
            if res == "W":
                entry["wins"] += 1
            elif res == "D":
                entry["draws"] += 1
            elif res == "L":
                entry["losses"] += 1

        total_record = TeamRecord(club.club_id, club.display)
        for m in fixtures:
            if not m.played:
                continue
            if m.home_team == club.club_id:
                total_record.add(m.result_for(club.club_id), m.home_goals, m.away_goals)
            else:
                total_record.add(m.result_for(club.club_id), m.away_goals, m.home_goals)

        squad = sorted(
            self._players_by_club.get(club.club_id, []), key=lambda p: -p.overall
        )
        last_match = max(
            (m for m in fixtures if m.date), key=lambda m: m.date, default=None
        )

        lines = [f"{club.display} — team profile", f"Matches in dataset: {len(fixtures)}"]
        for entry in sorted(by_family.values(), key=lambda e: -e["matches"]):
            seasons = self._season_range(entry["seasons"])
            lines.append(
                f"- {FAMILY_DISPLAY.get(entry['family'], entry['family'])}: "
                f"{entry['matches']} matches ({seasons}), "
                f"{entry['wins']}W {entry['draws']}D {entry['losses']}L"
            )
        lines.append(
            f"Overall: {total_record.wins}W {total_record.draws}D {total_record.losses}L, "
            f"goals {total_record.goals_for}:{total_record.goals_against}"
        )
        if squad:
            lines.append(f"FIFA squad in dataset: {len(squad)} players "
                         f"(avg rating {sum(p.overall for p in squad) / len(squad):.1f})")
        else:
            lines.append("FIFA squad in dataset: none (FIFA 19 snapshot does not cover this club)")
        if last_match is not None:
            lines.append(f"Most recent match: {self._format_match_line(last_match).lstrip('- ').strip()}")
        return {
            "summary": "\n".join(lines),
            "club_id": club.club_id,
            "competitions": [
                {
                    "competition": FAMILY_DISPLAY.get(e["family"], e["family"]),
                    "matches": e["matches"],
                    "seasons": sorted(e["seasons"]),
                    "wins": e["wins"],
                    "draws": e["draws"],
                    "losses": e["losses"],
                }
                for e in sorted(by_family.values(), key=lambda e: -e["matches"])
            ],
            "overall_record": total_record.as_dict(),
            "squad": [p.as_dict() for p in squad[:25]],
            "last_match": last_match.as_dict() if last_match else None,
        }

    def best_records(
        self,
        venue: str = "home",
        competition: str | None = None,
        season: int | None = None,
        minimum_matches: int = 10,
        limit: int = 10,
    ) -> dict:
        """Rank teams by win rate in a venue ('home', 'away' or 'all')."""
        venue_key = (venue or "all").lower()
        if venue_key not in ("home", "away", "all"):
            return {"error": "venue must be 'home', 'away' or 'all'."}
        family = _resolve_family(competition)
        pool = self._filtered_matches(family, season)
        records: dict[str, TeamRecord] = {}
        for m in pool:
            if not m.played:
                continue
            for side, club_id, gf, ga in (
                ("home", m.home_team, m.home_goals, m.away_goals),
                ("away", m.away_team, m.away_goals, m.home_goals),
            ):
                if venue_key != "all" and side != venue_key:
                    continue
                rec = records.setdefault(
                    club_id, TeamRecord(club_id, self._display.get(club_id, club_id))
                )
                result = "W" if gf > ga else ("D" if gf == ga else "L")
                rec.add(result, gf, ga)
        ranked = sorted(
            (r for r in records.values() if r.matches >= minimum_matches),
            key=lambda r: (-r.win_rate, -r.matches, -r.goal_difference),
        )[:limit]
        scope = self._scope_label(family, season, venue_key)
        lines = [f"Best {venue_key} records ({scope}, min {minimum_matches} matches):"]
        for i, r in enumerate(ranked, 1):
            lines.append(
                f"{i}. {r.display} - {r.win_rate * 100:.1f}% "
                f"({r.wins}W {r.draws}D {r.losses}L in {r.matches} matches)"
            )
        return {
            "summary": "\n".join(lines),
            "ranking": [r.as_dict() for r in ranked],
        }

    # ------------------------------------------------------------------
    # 3. player queries
    # ------------------------------------------------------------------
    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        limit: int = 25,
    ) -> dict:
        """Search the FIFA player database by name/nationality/club/position."""
        club_id = None
        raw_club_key = None
        if club:
            resolved = resolve_club(club)
            if resolved is not None:
                club_id = resolved.club_id
            else:
                raw_club_key = normalize_text(club)

        name_key = normalize_text(name) if name else None
        nat_key = nationality.strip().lower() if nationality else None
        pos_key = normalize_text(position) if position else None

        results = []
        for p in self.players:
            if name_key and name_key not in normalize_text(p.name):
                continue
            if nat_key and p.nationality.lower() != nat_key:
                continue
            if club_id and p.club_id != club_id:
                continue
            if raw_club_key and (p.club is None or raw_club_key not in normalize_text(p.club)):
                continue
            if pos_key and (p.position is None or pos_key != normalize_text(p.position)):
                continue
            if min_overall is not None and p.overall < min_overall:
                continue
            results.append(p)
        results.sort(key=lambda p: (-p.overall, p.name))
        total = len(results)
        limited = results[: max(1, limit)]
        lines = [f"Player search: {total} player(s) found"]
        for p in limited:
            lines.append(self._format_player_line(p))
        if total > len(limited):
            lines.append(f"... ({total - len(limited)} more players)")
        return {
            "summary": "\n".join(lines),
            "total_players": total,
            "players": [p.as_dict() for p in limited],
        }

    def top_players(
        self,
        nationality: str | None = None,
        club: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Highest-rated players, optionally filtered by nationality/club."""
        result = self.search_players(
            nationality=nationality, club=club, limit=limit
        )
        if "error" in result:
            return result
        scope_bits = []
        if nationality:
            scope_bits.append(nationality)
        if club:
            scope_bits.append(club)
        scope = " ".join(scope_bits) if scope_bits else "all nationalities"
        lines = [f"Top-rated players ({scope}):"]
        for i, p in enumerate(result["players"], 1):
            lines.append(
                f"{i}. {p['name']} - Overall: {p['overall']}, "
                f"Position: {p['position']}, Club: {p['club']}"
            )
        return {
            "summary": "\n".join(lines),
            "players": result["players"],
        }

    def players_at_brazilian_clubs(self) -> dict:
        """Brazilian players at Brazilian clubs present in the FIFA dataset."""
        rows = []
        for club_id, players in self._players_by_club.items():
            club = self.clubs.get(club_id)
            if club is None or club.country != "BRA":
                continue
            brazilians = [p for p in players if p.nationality == "Brazil"]
            if not brazilians:
                continue
            avg = sum(p.overall for p in brazilians) / len(brazilians)
            best = max(brazilians, key=lambda p: p.overall)
            rows.append(
                {
                    "club": self._display.get(club_id, club.display),
                    "players": len(brazilians),
                    "average_rating": round(avg, 1),
                    "best_player": best.name,
                    "best_rating": best.overall,
                }
            )
        rows.sort(key=lambda r: -r["players"])
        lines = ["Brazilian players at Brazilian clubs (FIFA 19 snapshot):"]
        for r in rows:
            lines.append(
                f"- {r['club']}: {r['players']} players "
                f"(avg rating {r['average_rating']}, top: {r['best_player']} {r['best_rating']})"
            )
        lines.append(
            "Note: FIFA 19 licensing excludes Flamengo, Palmeiras, Corinthians, "
            "São Paulo and Vasco squads from this dataset."
        )
        return {"summary": "\n".join(lines), "clubs": rows}

    # ------------------------------------------------------------------
    # 4. competition queries
    # ------------------------------------------------------------------
    def competition_info(self) -> dict:
        """Coverage of each competition: seasons, matches, sources."""
        info = {}
        for family, fixtures in self._by_family.items():
            seasons = sorted({m.season for m in fixtures if m.season is not None})
            sources = sorted({m.source for m in fixtures})
            info[family] = {
                "competition": FAMILY_DISPLAY.get(family, family),
                "seasons": seasons,
                "matches": len(fixtures),
                "sources": sources,
            }
        lines = ["Competitions in dataset:"]
        for family in sorted(info, key=lambda f: -info[f]["matches"]):
            entry = info[family]
            seasons = self._season_range(entry["seasons"])
            lines.append(
                f"- {entry['competition']}: {entry['matches']} matches ({seasons})"
            )
        return {"summary": "\n".join(lines), "competitions": info}

    def standings(self, competition: str, season: int) -> dict:
        """League table calculated from match results for one season.

        Tie-breakers follow the CBF criteria: points, wins, goal
        difference, goals scored.
        """
        family = _resolve_family(competition)
        if family is None:
            return {"error": f"Unknown competition '{competition}'."}
        if family not in LEAGUE_FAMILIES:
            return {
                "error": "Standings are only available for league competitions "
                "(Série A, Série B, Série C). For cup competitions use competition_finals."
            }
        fixtures = self._by_family_season.get((family, season), [])
        if not fixtures:
            known = sorted(
                s for (f, s) in self._by_family_season if f == family
            )
            return {
                "error": f"No {FAMILY_DISPLAY.get(family)} matches found for {season}.",
                "available_seasons": known,
            }
        records: dict[str, TeamRecord] = {}
        for m in fixtures:
            if not m.played or m.home_team is None:
                continue
            home = records.setdefault(
                m.home_team, TeamRecord(m.home_team, m.home_display)
            )
            away = records.setdefault(
                m.away_team, TeamRecord(m.away_team, m.away_display)
            )
            if m.home_goals > m.away_goals:
                home.add("W", m.home_goals, m.away_goals)
                away.add("L", m.away_goals, m.home_goals)
            elif m.home_goals < m.away_goals:
                home.add("L", m.home_goals, m.away_goals)
                away.add("W", m.away_goals, m.home_goals)
            else:
                home.add("D", m.home_goals, m.away_goals)
                away.add("D", m.away_goals, m.home_goals)
        table = sorted(
            records.values(),
            key=lambda r: (-r.points, -r.wins, -r.goal_difference, -r.goals_for, r.display),
        )
        counted = sum(r.matches for r in table) // 2
        teams = len(table)
        expected = teams * (teams - 1)
        completeness = "complete" if counted >= expected else "partial"
        display = FAMILY_DISPLAY.get(family, family)

        lines = [f"{season} {display} standings (calculated from matches, source: {fixtures[0].source}):"]
        relegated_mark = teams - 4
        for i, r in enumerate(table, 1):
            suffix = ""
            if i == 1:
                suffix = " - Champion"
            elif family == SERIE_A and i > relegated_mark:
                suffix = " - Relegated"
            lines.append(
                f"{i}. {r.display} - {r.points} pts ({r.wins}W, {r.draws}D, {r.losses}L){suffix}"
            )
        if completeness == "partial":
            lines.append(
                f"Note: season data is partial ({counted}/{expected} expected matches in dataset)."
            )
        return {
            "summary": "\n".join(lines),
            "season": season,
            "competition": display,
            "source": fixtures[0].source,
            "matches_counted": counted,
            "completeness": completeness,
            "champion": table[0].as_dict() if table else None,
            "relegated": [r.as_dict() for r in table[-4:]] if family == SERIE_A else [],
            "table": [r.as_dict() for r in table],
        }

    def _standings_note(self) -> dict:
        return {
            "matches_after_reconciliation": len(self.matches),
            "rows_dropped_as_mislabelled": self.dropped_rows,
        }

    def competition_finals(self, competition: str) -> dict:
        """Finals and winners for cup competitions (Copa do Brasil, Libertadores)."""
        family = _resolve_family(competition)
        if family is None:
            return {"error": f"Unknown competition '{competition}'."}
        if family == COPA_DO_BRASIL:
            fixtures = self._by_family.get(family, [])
            finals: dict[int, list[Match]] = {}
            seasons = sorted({m.season for m in fixtures if m.season is not None})
            by_season: dict[int, dict[int, list[Match]]] = {}
            for m in fixtures:
                if m.season is None or m.round is None or not m.played:
                    continue
                by_season.setdefault(m.season, {}).setdefault(m.round, []).append(m)
            for season in seasons:
                rounds = by_season.get(season, {})
                final_round = None
                for rnd in sorted(rounds, reverse=True):
                    games = rounds[rnd]
                    if len(games) == 2 and len({g.home_team for g in games}) == 2 and len(
                        {g.away_team for g in games}
                    ) == 2 and {games[0].home_team, games[0].away_team} == {
                        games[1].home_team,
                        games[1].away_team,
                    }:
                        final_round = rnd
                        break
                if final_round is not None:
                    finals[season] = rounds[final_round]
        elif family == LIBERTADORES:
            fixtures = self._by_family.get(family, [])
            finals: dict[int, list[Match]] = {}
            for m in fixtures:
                if (m.stage or "").lower() == "final" and m.season is not None:
                    finals.setdefault(m.season, []).append(m)
        else:
            return {
                "error": "Finals are only tracked for cup competitions. "
                "For leagues use standings (the top of the table is the champion)."
            }

        display = FAMILY_DISPLAY.get(family, family)
        rows = []
        for season in sorted(finals):
            legs = sorted(finals[season], key=lambda m: (m.date is None, m.date or date.min))
            if not legs:
                continue
            team_ids = {legs[0].home_team, legs[0].away_team}
            agg: dict[str, int] = {t: 0 for t in team_ids}
            for leg in legs:
                if not leg.played:
                    continue
                agg[leg.home_team] = agg.get(leg.home_team, 0) + leg.home_goals
                agg[leg.away_team] = agg.get(leg.away_team, 0) + leg.away_goals
            ranked = sorted(agg.items(), key=lambda kv: -kv[1])
            if len(ranked) == 2 and ranked[0][1] == ranked[1][1]:
                winner_text = "decided on penalties (not recorded in data)"
                winner = None
            else:
                winner = ranked[0][0]
                winner_text = self._display.get(winner, winner)
            leg_texts = " / ".join(
                f"{leg.home_display} {leg.home_goals}-{leg.away_goals} {leg.away_display}"
                if leg.played
                else f"{leg.home_display} vs {leg.away_display} (no score recorded)"
                for leg in legs
            )
            rows.append(
                {
                    "season": season,
                    "final": leg_texts,
                    "aggregate": f"{self._display.get(ranked[0][0], ranked[0][0])} {ranked[0][1]}-{ranked[1][1]} {self._display.get(ranked[1][0], ranked[1][0])}" if len(ranked) == 2 else "",
                    "winner": self._display.get(winner, "") if winner else None,
                    "winner_note": winner_text if winner is None else "",
                }
            )
        lines = [f"{display} finals in dataset:"]
        for r in rows:
            lines.append(f"- {r['season']}: {r['final']} -> winner: {r['winner'] or r['winner_note']}")
        if not rows:
            lines.append("(no finals recorded in the dataset)")
        return {"summary": "\n".join(lines), "finals": rows}

    def top_scoring_teams(self, competition: str | None = None, season: int | None = None, limit: int = 10) -> dict:
        """Teams with the most goals scored (player-level scorers are not in the data)."""
        family = _resolve_family(competition)
        pool = self._filtered_matches(family, season)
        goals: dict[str, int] = {}
        for m in pool:
            if not m.played:
                continue
            goals[m.home_team] = goals.get(m.home_team, 0) + m.home_goals
            goals[m.away_team] = goals.get(m.away_team, 0) + m.away_goals
        ranked = sorted(goals.items(), key=lambda kv: -kv[1])[:limit]
        scope = self._scope_label(family, season, "all")
        lines = [f"Top-scoring teams ({scope}):"]
        for i, (club_id, g) in enumerate(ranked, 1):
            lines.append(f"{i}. {self._display.get(club_id, club_id)} - {g} goals")
        lines.append("Note: individual top scorers cannot be derived - the datasets record team goals only.")
        return {
            "summary": "\n".join(lines),
            "teams": [
                {"team": self._display.get(c, c), "goals": g} for c, g in ranked
            ],
        }

    # ------------------------------------------------------------------
    # 5. statistical analysis
    # ------------------------------------------------------------------
    def goal_averages(self, competition: str | None = None, season: int | None = None) -> dict:
        """Average goals per match plus home/draw/away win rates."""
        family = _resolve_family(competition)
        pool = [m for m in self._filtered_matches(family, season) if m.played]
        if not pool:
            return {"error": "No played matches found for these filters."}
        total_goals = sum(m.total_goals for m in pool)
        home_wins = sum(1 for m in pool if m.winner() == m.home_team)
        away_wins = sum(1 for m in pool if m.winner() == m.away_team)
        draws = len(pool) - home_wins - away_wins
        home_goals = sum(m.home_goals for m in pool)
        away_goals = sum(m.away_goals for m in pool)
        n = len(pool)
        scope = self._scope_label(family, season, "all")
        lines = [
            f"Goal statistics ({scope}):",
            f"- Matches: {n}",
            f"- Average goals per match: {total_goals / n:.2f}",
            f"- Average home goals: {home_goals / n:.2f}, away goals: {away_goals / n:.2f}",
            f"- Home win rate: {home_wins / n * 100:.1f}%",
            f"- Draw rate: {draws / n * 100:.1f}%",
            f"- Away win rate: {away_wins / n * 100:.1f}%",
        ]
        return {
            "summary": "\n".join(lines),
            "matches": n,
            "average_goals_per_match": round(total_goals / n, 2),
            "average_home_goals": round(home_goals / n, 2),
            "average_away_goals": round(away_goals / n, 2),
            "home_win_rate": round(home_wins / n * 100, 1),
            "draw_rate": round(draws / n * 100, 1),
            "away_win_rate": round(away_wins / n * 100, 1),
        }

    def biggest_wins(self, competition: str | None = None, season: int | None = None, limit: int = 10) -> dict:
        """Largest victory margins in the dataset."""
        family = _resolve_family(competition)
        pool = [m for m in self._filtered_matches(family, season) if m.played]
        ranked = sorted(
            pool, key=lambda m: (-(m.goal_margin or 0), -(m.total_goals or 0))
        )[: max(1, limit)]
        scope = self._scope_label(family, season, "all")
        lines = [f"Biggest victories ({scope}):"]
        for i, m in enumerate(ranked, 1):
            lines.append(
                f"{i}. {self._format_match_line(m)}"
            )
        return {
            "summary": "\n".join(lines),
            "matches": [m.as_dict() for m in ranked],
        }

    def derbies(self, season: int | None = None, limit: int = 50) -> dict:
        """Matches between traditional rivals (Fla-Flu, Grenal, ...)."""
        pairs = {frozenset((d.club_a, d.club_b)): d for d in DERBIES}
        fixtures = []
        for m in self.matches:
            key = frozenset((m.home_team, m.away_team))
            derby = pairs.get(key)
            if derby and (season is None or m.season == season):
                fixtures.append((derby, m))
        fixtures.sort(key=lambda dm: (dm[1].date is None, dm[1].date or date.min), reverse=True)
        total = len(fixtures)
        shown = fixtures[: max(1, limit)]
        lines = [f"Derbies{' in ' + str(season) if season else ''}: {total} matches in dataset"]
        for derby, m in shown:
            lines.append(f"[{derby.name}] {self._format_match_line(m)}")
        if total > len(shown):
            lines.append(f"... ({total - len(shown)} more derby matches)")
        derby_names = [d.name for d in DERBIES]
        return {
            "summary": "\n".join(lines),
            "total_matches": total,
            "tracked_derbies": derby_names,
            "matches": [
                {"derby": derby.name, **m.as_dict()} for derby, m in shown
            ],
        }

    # ------------------------------------------------------------------
    # knowledge graph queries
    # ------------------------------------------------------------------
    def graph_overview(self) -> dict:
        stats = self.kg.stats()
        lines = [
            "Knowledge graph overview:",
            f"- Nodes: {stats['nodes']} ({', '.join(f'{k}: {v}' for k, v in sorted(stats['node_types'].items()))})",
            f"- Edges: {stats['edges']} ({', '.join(f'{k}: {v}' for k, v in sorted(stats['edge_types'].items()))})",
        ]
        return {"summary": "\n".join(lines), **stats}

    def team_graph(self, team: str) -> dict:
        """Knowledge-graph neighbourhood of a team: competitions, opponents, squad."""
        err = self._require_team(team)
        if err:
            return err
        club = self._resolve(team)
        node_id = f"club:{club.club_id}"

        opponents: dict[str, int] = {}
        competitions: dict[str, int] = {}
        for m in self._by_team.get(club.club_id, ()):
            opp = m.away_team if m.home_team == club.club_id else m.home_team
            opponents[opp] = opponents.get(opp, 0) + 1
            competitions[m.family] = competitions.get(m.family, 0) + 1
        top_opponents = sorted(opponents.items(), key=lambda kv: -kv[1])[:10]
        squad = sorted(
            self._players_by_club.get(club.club_id, []), key=lambda p: -p.overall
        )[:10]

        lines = [f"Knowledge graph for {club.display} (node degree: {self.kg.degree(node_id)}):"]
        lines.append("Competitions (via match nodes):")
        for family, count in sorted(competitions.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {FAMILY_DISPLAY.get(family, family)}: {count} matches")
        lines.append("Most frequent opponents:")
        for opp_id, count in top_opponents:
            lines.append(f"- {self._display.get(opp_id, opp_id)}: {count} matches")
        if squad:
            lines.append("Squad (FIFA dataset):")
            for p in squad:
                lines.append(f"- {p.name} ({p.position}, {p.overall})")
        else:
            lines.append("Squad: not covered by the FIFA dataset")
        return {
            "summary": "\n".join(lines),
            "club_id": club.club_id,
            "node_id": node_id,
            "competitions": {
                FAMILY_DISPLAY.get(f, f): c for f, c in competitions.items()
            },
            "top_opponents": [
                {"team": self._display.get(o, o), "matches": c} for o, c in top_opponents
            ],
            "squad": [p.as_dict() for p in squad],
        }

    def graph_paths(self, entity_a: str, entity_b: str, max_hops: int = 3) -> dict:
        """Shortest knowledge-graph connections between two entities."""
        nodes_a = self._find_graph_nodes(entity_a)
        nodes_b = self._find_graph_nodes(entity_b)
        if not nodes_a:
            return {"error": f"No graph node found for '{entity_a}'."}
        if not nodes_b:
            return {"error": f"No graph node found for '{entity_b}'."}
        start = nodes_a[0].id
        goal = nodes_b[0].id
        paths = self.kg.find_paths(start, goal, max_hops=max_hops)
        if not paths:
            return {
                "summary": f"No connection found between '{entity_a}' and '{entity_b}' within {max_hops} hops.",
                "paths": [],
            }
        lines = [
            f"Connections between {nodes_a[0].label} and {nodes_b[0].label} (max {max_hops} hops):"
        ]
        rendered = []
        for path in paths:
            steps = [nodes_a[0].label]
            for rel, node_id in path:
                node = self.kg.node(node_id)
                steps.append(f"--[{rel}]--> {node.label if node else node_id}")
            rendered.append(" ".join(steps))
            lines.append(f"- {' '.join(steps)}")
        return {"summary": "\n".join(lines), "paths": rendered}

    def _find_graph_nodes(self, query: str):
        hits = self.kg.find_node(query)
        if hits:
            return hits
        club = self._resolve(query)
        if club:
            return [n for n in (self.kg.node(f"club:{club.club_id}"),) if n]
        return []

    # ------------------------------------------------------------------
    # disambiguation helper
    # ------------------------------------------------------------------
    def list_clubs(self, query: str | None = None, limit: int = 25) -> dict:
        """List known clubs (optionally filtered), with dataset presence."""
        key = normalize_text(query) if query else None
        rows = []
        for club_id, club in self.clubs.items():
            if key and key not in normalize_text(club.name) and key not in normalize_text(club.display):
                continue
            presence = self._club_popularity(club_id)
            if presence == 0 and key is None:
                continue
            rows.append(
                {
                    "club_id": club_id,
                    "name": self._display.get(club_id, club.display),
                    "state": club.state,
                    "matches_in_dataset": presence,
                }
            )
        rows.sort(key=lambda r: -r["matches_in_dataset"])
        limited = rows[: max(1, limit)]
        lines = [f"Clubs{' matching ' + query if query else ''}: {len(rows)} found"]
        for r in limited:
            lines.append(f"- {r['name']} ({r['matches_in_dataset']} matches)")
        return {"summary": "\n".join(lines), "clubs": limited, "total": len(rows)}

    # ------------------------------------------------------------------
    # formatting helpers
    # ------------------------------------------------------------------
    def _filtered_matches(self, family: str | None, season: int | None) -> list[Match]:
        if family and season is not None:
            return self._by_family_season.get((family, season), [])
        if family:
            return self._by_family.get(family, [])
        if season is not None:
            return [m for m in self.matches if m.season == season]
        return self.matches

    @staticmethod
    def _stage_matches(stage_key: str, match_stage: str | None) -> bool:
        """Token-aware stage matching: 'final' must not match 'quarterfinals'."""
        if match_stage is None:
            return False
        tokens = normalize_text(match_stage).split()
        if stage_key in tokens:
            return True
        if len(stage_key) >= 3:
            return any(tok.startswith(stage_key) for tok in tokens)
        return False

    @staticmethod
    def _season_range(seasons) -> str:
        seasons = sorted(seasons)
        if not seasons:
            return "no seasons"
        if len(seasons) == 1:
            return str(seasons[0])
        return f"{seasons[0]}-{seasons[-1]}"

    @staticmethod
    def _scope_label(family: str | None, season: int | None, venue: str) -> str:
        parts = []
        if family:
            parts.append(FAMILY_DISPLAY.get(family, family))
        else:
            parts.append("all competitions")
        if season is not None:
            parts.append(str(season))
        if venue == "home":
            parts.append("home matches")
        elif venue == "away":
            parts.append("away matches")
        return ", ".join(parts)

    def _match_filter_header(self, team_id, opp_id, family, season, d_from, d_to) -> str:
        bits = []
        if team_id:
            bits.append(self._display.get(team_id, team_id))
        if opp_id:
            bits.append(f"vs {self._display.get(opp_id, opp_id)}")
        if family:
            bits.append(FAMILY_DISPLAY.get(family, family))
        if season is not None:
            bits.append(str(season))
        if d_from:
            bits.append(f"from {d_from.isoformat()}")
        if d_to:
            bits.append(f"to {d_to.isoformat()}")
        return f"Matches for {', '.join(bits)}" if bits else "All matches"

    def _format_match_line(self, m: Match) -> str:
        when = m.date.isoformat() if m.date else f"{m.season or '?'}"
        score = f"{m.home_goals}-{m.away_goals}" if m.played else "vs"
        stage = f", {m.stage}" if m.stage else ""
        return (
            f"- {when}: {m.home_display} {score} {m.away_display} "
            f"({m.competition}{stage})"
        )

    @staticmethod
    def _format_player_line(p: Player) -> str:
        return (
            f"- {p.name} - Overall: {p.overall}, Position: {p.position}, "
            f"Club: {p.club or 'Free agent'}, Nationality: {p.nationality}"
        )


_ENGINE: SoccerData | None = None


def get_engine(data_dir: str | Path | None = None) -> SoccerData:
    """Process-wide cached engine (data loads once, queries stay fast)."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = SoccerData(data_dir)
    return _ENGINE
