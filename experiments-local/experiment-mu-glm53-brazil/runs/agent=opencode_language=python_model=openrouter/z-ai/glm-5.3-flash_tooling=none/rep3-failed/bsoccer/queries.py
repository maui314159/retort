"""Query engine over the Brazilian soccer knowledge graph.

All public methods return plain dicts / lists (JSON-friendly) so the MCP
server layer can render them directly. Team and competition names given by
the user are resolved with :mod:`bsoccer.normalization`, so queries tolerate
state suffixes, missing accents and alternate spellings.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from .data_loader import Match, Player, load_all
from .normalization import canonical_key, fold, parse_date

# Display order used when de-duplicating matches that appear in several
# datasets: prefer the primary spec datasets over supplementary ones.
_SOURCE_PRIORITY = {
    "Brasileirao_Matches.csv": 0,
    "Brazilian_Cup_Matches.csv": 1,
    "Libertadores_Matches.csv": 2,
    "novo_campeonato_brasileiro.csv": 3,
    "BR-Football-Dataset.csv": 4,
}

# Canonical competition labels, mapped to the dataset-specific labels used in
# the unified Match records.
_COMPETITION_GROUPS: dict[str, set[str]] = {
    "brasileirao": {"Brasileirão Série A"},
    "serie a": {"Brasileirão Série A", "Série A (BR-Football)"},
    "serie b": {"Série B (BR-Football)"},
    "serie c": {"Série C (BR-Football)"},
    "copa do brasil": {"Copa do Brasil", "Copa do Brasil (BR-Football)"},
    "libertadores": {"Copa Libertadores"},
}

# Reverse map: dataset competition label -> group key (first group wins).
_LABEL_TO_GROUP: dict[str, str] = {}
for _group, _labels in _COMPETITION_GROUPS.items():
    for _label in _labels:
        _LABEL_TO_GROUP.setdefault(_label, _group)


class KnowledgeBase:
    """In-memory knowledge graph over the six datasets."""

    def __init__(self, data_dir: str | None = None):
        self.matches: list[Match] = []
        self.players: list[Player] = []
        self._load(data_dir)
        self._build_indexes()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def _load(self, data_dir: str | None) -> None:
        if data_dir is None:
            self.matches, self.players = load_all()
        else:
            self.matches, self.players = load_all(data_dir)

    def _build_indexes(self) -> None:
        # Canonical team -> most frequent original spelling (display name).
        spelling_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._team_matches: dict[str, list[Match]] = defaultdict(list)
        for match in self.matches:
            self._team_matches[match.home].append(match)
            self._team_matches[match.away].append(match)
            spelling_counts[match.home][match.home_raw] += 1
            spelling_counts[match.away][match.away_raw] += 1
        self.team_display: dict[str, str] = {}
        for team_key, counts in spelling_counts.items():
            self.team_display[team_key] = max(counts.items(), key=lambda kv: kv[1])[0]
        self._index_cup_rounds()
        # Cross-dataset duplicate view, with the primary datasets preferred.
        ordered = sorted(self.matches, key=lambda m: _SOURCE_PRIORITY.get(m.source_file, 99))
        self.matches_unique = self._dedupe(ordered)

    # ------------------------------------------------------------------
    # Name resolution
    # ------------------------------------------------------------------

    def find_team(self, name: str) -> str | None:
        """Resolve a user-supplied team name to a canonical team in the data.

        Tries exact canonical match first, then a unique substring match over
        all known team keys. Returns ``None`` when nothing matches.
        """
        raw = (name or "").strip()
        if not raw:
            return None
        resolved = self._resolve(raw)
        if resolved in self.team_display:
            return resolved
        # Fuzzy fallback: unique substring over canonical keys.
        query = fold(raw)
        candidates = [
            team for team in self.team_display
            if query in fold(team) or query.replace(" ", "") in fold(team).replace(" ", "")
        ]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            # Prefer the shortest match (closest to the user's input).
            return min(candidates, key=len)
        return None

    @staticmethod
    def _resolve(raw: str) -> str:
        from .normalization import resolve_team
        return resolve_team(raw) or fold(raw)

    def team_candidates(self, name: str, limit: int = 8) -> list[str]:
        """Teams whose canonical key contains the folded query (for hints)."""
        query = fold((name or "").strip())
        if not query:
            return []
        hits = [team for team in self.team_display if query in team]
        return sorted(hits, key=len)[:limit]

    def resolve_competitions(self, query: str | None) -> set[str] | None:
        """Map a user competition phrase onto dataset competition labels.

        ``None`` means "no filter" (all competitions).
        """
        if not query or not query.strip():
            return None
        q = fold(query)
        q = re.sub(r"serie\s*([abc])\b", r"serie \1", q)
        q = re.sub(r"\bs[eé]rie\b", "serie", q)
        labels: set[str] = set()
        for group_key, group_labels in _COMPETITION_GROUPS.items():
            group_folded = fold(group_key)
            if group_folded in q or q in group_folded:
                labels |= group_labels
        if not labels:
            # Fall back to substring match over known labels.
            for label in set().union(*_COMPETITION_GROUPS.values()):
                if fold(label) in q or q in fold(label):
                    labels.add(label)
        return labels or None

    # ------------------------------------------------------------------
    # Match queries
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
        round: str | int | None = None,
        limit: int = 50,
        dedupe: bool = True,
    ) -> dict:
        from_date, _ = parse_date(date_from or "")
        to_date, _ = parse_date(date_to or "")
        competition_labels = self.resolve_competitions(competition)

        team_canonical = self.find_team(team) if team else None
        opponent_canonical = self.find_team(opponent) if opponent else None

        results: list[Match] = []
        for match in self.matches:
            if team_canonical and team_canonical not in (match.home, match.away):
                continue
            if opponent_canonical and opponent_canonical not in (match.home, match.away):
                continue
            if team_canonical and opponent_canonical and {match.home, match.away} != {team_canonical, opponent_canonical}:
                continue
            if competition_labels and match.competition not in competition_labels:
                continue
            if season is not None and match.season != season:
                continue
            if from_date and (match.date is None or match.date < from_date):
                continue
            if to_date and (match.date is None or match.date > to_date):
                continue
            if stage and not self._stage_matches(match, stage):
                continue
            if round is not None and (match.round or "").strip() != str(round).strip():
                continue
            results.append(match)

        results.sort(key=self._match_sort_key)
        total = len(results)
        deduped = self._dedupe(results) if dedupe else results
        limit = max(1, min(int(limit or 50), 200))
        truncated = len(deduped) > limit
        page = deduped[:limit]

        response: dict = {
            "count": len(page),
            "total_matches": total,
            "deduplicated": dedupe,
            "matches": [m.to_dict() for m in page],
            "truncated": truncated,
        }
        if team_canonical:
            response["team"] = self.team_display.get(team_canonical, team_canonical)
        if opponent_canonical:
            response["opponent"] = self.team_display.get(opponent_canonical, opponent_canonical)
        if team_canonical and opponent_canonical:
            summary = self._head_to_head_summary(team_canonical, opponent_canonical, competition_labels, season)
            response["head_to_head"] = summary
        return response

    @staticmethod
    def _match_sort_key(match: Match):
        return (
            -(match.date.toordinal() if match.date else 0),
            match.competition,
            match.home,
        )

    def _dedupe(self, matches: list[Match]) -> list[Match]:
        """Drop cross-dataset duplicates (same date, teams, score)."""
        seen: dict[tuple, int] = {}
        output: list[Match] = []
        for match in matches:
            key = (
                match.date_key(),
                tuple(sorted((match.home, match.away))),
                match.home_goal,
                match.away_goal,
            )
            existing_idx = seen.get(key)
            if existing_idx is None:
                seen[key] = len(output)
                output.append(match)
            else:
                existing = output[existing_idx]
                if _SOURCE_PRIORITY.get(match.source_file, 99) < _SOURCE_PRIORITY.get(existing.source_file, 99):
                    output[existing_idx] = match
        return output

    def _stage_matches(self, match: Match, stage_query: str) -> bool:
        stage_q = fold(stage_query.strip())
        if not stage_q:
            return False
        match_stage = fold(match.stage or "")
        wants_final_only = "final" in stage_q and "semi" not in stage_q and "16" not in stage_q
        if wants_final_only:
            # The user asked for finals only: 'semifinals' must not match.
            if match.competition == "Copa do Brasil" and not match_stage:
                return match.round == self._max_cup_round.get(match.season)
            return match_stage == "final"
        return bool(match_stage and stage_q in match_stage)

    def search_players(
        self,
        name: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        position: str | None = None,
        min_overall: int | None = None,
        max_age: int | None = None,
        sort_by: str = "overall",
        limit: int = 25,
    ) -> dict:
        name_q = fold(name or "")
        nationality_q = fold(nationality or "")
        club_q = fold(club or "")
        club_canonical = self.find_team(club) if club else None
        position_q = (position or "").strip().upper()
        sort_by = (sort_by or "overall").lower()
        key_map = {"overall": lambda p: (p.overall or 0), "potential": lambda p: (p.potential or 0),
                   "name": lambda p: p.name.lower(), "age": lambda p: p.age or 0}
        sort_key = key_map.get(sort_by, key_map["overall"])
        reverse = sort_by not in ("name", "age")

        hits: list[Player] = []
        for player in self.players:
            if name_q and name_q not in fold(player.name):
                continue
            if nationality_q and nationality_q not in fold(player.nationality):
                continue
            if club_q:
                raw_ok = club_q in fold(player.club)
                key_ok = club_canonical is not None and player.club_key == club_canonical
                if not (raw_ok or key_ok):
                    continue
            if position_q and position_q != (player.position or "").upper():
                continue
            if min_overall is not None and (player.overall or 0) < min_overall:
                continue
            if max_age is not None and (player.age or 99) > max_age:
                continue
            hits.append(player)

        hits.sort(key=sort_key, reverse=reverse)
        limit = max(1, min(int(limit or 25), 100))
        response = {
            "count": len(hits),
            "returned": min(len(hits), limit),
            "truncated": len(hits) > limit,
            "players": [p.to_dict() for p in hits[:limit]],
        }
        if club_canonical and hits:
            response["club_summary"] = self.club_player_summary(club_canonical)
        return response

    def player_profile(self, name: str) -> dict:
        name_q = fold((name or "").strip())
        if not name_q:
            return {"error": "A player name is required."}
        exact = [p for p in self.players if fold(p.name) == name_q]
        if not exact:
            exact = [p for p in self.players if name_q in fold(p.name)]
        if not exact:
            # Token-wise match ('gabriel barbosa' -> names sharing tokens).
            tokens = [t for t in re.split(r"\s+", name_q) if len(t) > 2]
            if tokens:
                ranked = []
                for player in self.players:
                    player_name = fold(player.name)
                    matched = sum(1 for t in tokens if t in player_name)
                    if matched:
                        ranked.append((matched, player.overall or 0, player))
                ranked.sort(key=lambda r: (-r[0], -r[1]))
                if ranked:
                    best = ranked[0][2]
                    return {
                        "matches_found": len(ranked),
                        "match_quality": f"partial (matched {ranked[0][0]} of {len(tokens)} name tokens)",
                        "player": best.to_dict(include_skills=True),
                        "other_matches": [r[2].to_dict() for r in ranked[1:6]],
                    }
        if not exact:
            return {"error": f"No player named '{name}' found in the FIFA dataset.",
                    "hint": "The player dataset is FIFA 19 (2018 season) and uses display names like 'Neymar Jr'."}
        exact.sort(key=lambda p: p.overall or 0, reverse=True)
        best = exact[0]
        return {
            "matches_found": len(exact),
            "player": best.to_dict(include_skills=True),
            "other_matches": [p.to_dict() for p in exact[1:6]],
        }

    def club_player_summary(self, club_canonical: str) -> dict | None:
        roster = [p for p in self.players if p.club_key == club_canonical]
        if not roster:
            return None
        overalls = [p.overall for p in roster if p.overall is not None]
        return {
            "club": club_canonical,
            "raw_club_names": sorted({p.club for p in roster}),
            "player_count": len(roster),
            "average_overall": round(sum(overalls) / len(overalls), 1) if overalls else None,
            "top_players": [p.to_dict() for p in sorted(roster, key=lambda p: p.overall or 0, reverse=True)[:5]],
        }

    # ------------------------------------------------------------------
    # Team statistics
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_stat() -> dict:
        return {"played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}

    @staticmethod
    def _record_stat(stat: dict, goals_for: int, goals_against: int) -> None:
        stat["played"] += 1
        stat["goals_for"] += goals_for
        stat["goals_against"] += goals_against
        if goals_for > goals_against:
            stat["wins"] += 1
        elif goals_for == goals_against:
            stat["draws"] += 1
        else:
            stat["losses"] += 1

    @staticmethod
    def _finalize_stat(stat: dict) -> dict:
        played = stat["played"]
        out = dict(stat)
        out["goal_difference"] = stat["goals_for"] - stat["goals_against"]
        out["win_rate"] = round(100.0 * stat["wins"] / played, 1) if played else 0.0
        return out

    def team_statistics(self, team: str, season: int | None = None,
                        competition: str | None = None) -> dict:
        canonical = self.find_team(team)
        if canonical is None:
            return {"error": f"Team '{team}' not found.",
                    "candidates": self.team_candidates(team)}
        labels = self.resolve_competitions(competition)
        candidates: list[Match] = []
        for match in self._team_matches.get(canonical, []):
            if season is not None and match.season != season:
                continue
            if labels and match.competition not in labels:
                continue
            if match.home_goal is None or match.away_goal is None:
                continue  # e.g. 'NA' result rows; skip for statistics
            candidates.append(match)
        # The same fixture can appear in several datasets; keep one copy per
        # (date, teams, score) so statistics are not double counted.
        matches_considered = self._dedupe(candidates)
        overall = self._empty_stat()
        home = self._empty_stat()
        away = self._empty_stat()
        by_competition: dict[str, dict] = defaultdict(self._empty_stat)
        for match in matches_considered:
            is_home = match.home == canonical
            gf, ga = (match.home_goal, match.away_goal) if is_home else (match.away_goal, match.home_goal)
            self._record_stat(overall, gf, ga)
            self._record_stat(home if is_home else away, gf, ga)
            self._record_stat(by_competition[match.competition], gf, ga)
        seasons = sorted({m.season for m in matches_considered if m.season is not None})
        response = {
            "team": self.team_display.get(canonical, canonical),
            "filters": {"season": season, "competition": competition},
            "seasons_covered": seasons,
            "overall": self._finalize_stat(overall),
            "home": self._finalize_stat(home),
            "away": self._finalize_stat(away),
            "by_competition": {k: self._finalize_stat(v) for k, v in sorted(by_competition.items())},
        }
        return response

    def head_to_head(self, team_a: str, team_b: str, competition: str | None = None,
                     season: int | None = None, limit: int = 50) -> dict:
        canonical_a = self.find_team(team_a)
        canonical_b = self.find_team(team_b)
        if canonical_a is None or canonical_b is None:
            missing = team_a if canonical_a is None else team_b
            return {"error": f"Team '{missing}' not found.",
                    "candidates": self.team_candidates(missing)}
        if canonical_a == canonical_b:
            return {"error": "Please provide two different teams."}
        labels = self.resolve_competitions(competition)
        matches = [
            m for m in self.matches_unique
            if {m.home, m.away} == {canonical_a, canonical_b}
            and (labels is None or m.competition in labels)
            and (season is None or m.season == season)
        ]
        matches.sort(key=self._match_sort_key)
        total = len(matches)
        limit = max(1, min(int(limit or 50), 200))
        response = {
            "team_a": self.team_display.get(canonical_a, canonical_a),
            "team_b": self.team_display.get(canonical_b, canonical_b),
            "summary": self._head_to_head_summary(canonical_a, canonical_b, labels, season, matches=matches),
            "count": len(matches[:limit]),
            "total_matches": total,
            "truncated": len(matches) > limit,
            "matches": [m.to_dict() for m in matches[:limit]],
        }
        return response

    def _head_to_head_summary(self, canonical_a: str, canonical_b: str,
                              labels: set[str] | None, season: int | None,
                              matches: list[Match] | None = None) -> dict:
        if matches is None:
            matches = [
                m for m in self.matches_unique
                if {m.home, m.away} == {canonical_a, canonical_b}
                and (labels is None or m.competition in labels)
                and (season is None or m.season == season)
            ]
        wins_a = wins_b = draws = 0
        goals_a = goals_b = 0
        for match in matches:
            if match.home_goal is None or match.away_goal is None:
                continue
            a_home = match.home == canonical_a
            gf_a, gf_b = (match.home_goal, match.away_goal) if a_home else (match.away_goal, match.home_goal)
            goals_a += gf_a
            goals_b += gf_b
            if gf_a > gf_b:
                wins_a += 1
            elif gf_a < gf_b:
                wins_b += 1
            else:
                draws += 1
        return {
            "team_a": self.team_display.get(canonical_a, canonical_a),
            "team_b": self.team_display.get(canonical_b, canonical_b),
            "team_a_wins": wins_a,
            "team_b_wins": wins_b,
            "draws": draws,
            "goals_team_a": goals_a,
            "goals_team_b": goals_b,
        }

    # ------------------------------------------------------------------
    # Competition statistics & standings
    # ------------------------------------------------------------------

    def standings(self, competition: str, season: int) -> dict:
        labels = self.resolve_competitions(competition)
        if not labels:
            return {"error": f"Competition '{competition}' not recognized.",
                    "known": sorted(_COMPETITION_GROUPS)}
        if season is None:
            return {"error": "A season (year) is required to compute standings."}
        # Choose the dataset that best covers the requested season: the one
        # with the most matches for that season wins; primary datasets win
        # ties. This avoids double counting when several files overlap.
        coverage: dict[tuple[str, str], int] = defaultdict(int)
        for match in self.matches:
            if match.season == season and match.competition in labels:
                coverage[(match.competition, match.source_file)] += 1
        if not coverage:
            return {"error": f"No matches found for {competition} in season {season}."}
        chosen_key, _count = max(
            coverage.items(),
            key=lambda kv: (kv[1], -_SOURCE_PRIORITY.get(kv[0][1], 99)),
        )
        chosen_label, chosen_source = chosen_key
        rows = [m for m in self.matches
                if m.competition == chosen_label and m.source_file == chosen_source and m.season == season]

        table: dict[str, dict] = defaultdict(lambda: self._empty_stat())
        for match in rows:
            if match.home_goal is None or match.away_goal is None:
                continue
            self._record_stat(table[match.home], match.home_goal, match.away_goal)
            self._record_stat(table[match.away], match.away_goal, match.home_goal)

        entries = []
        for team_key, stat in table.items():
            entries.append({
                "team": self.team_display.get(team_key, team_key),
                "points": stat["wins"] * 3 + stat["draws"],
                **self._finalize_stat(stat),
            })
        # Official Brasileirão tie-break order: points, wins, goal difference, goals for.
        entries.sort(key=lambda e: (-e["points"], -e["wins"], -e["goal_difference"], -e["goals_for"]))
        for idx, entry in enumerate(entries, start=1):
            entry["position"] = idx
        is_brasileirao = chosen_label == "Brasileirão Série A"
        relegation_positions = []
        if is_brasileirao and len(entries) >= 16:
            relegation_positions = list(range(len(entries) - 3, len(entries) + 1))
        if entries:
            entries[0]["note"] = "Champion"
            for entry in entries:
                if relegation_positions and entry["position"] in relegation_positions:
                    entry["note"] = "Relegation zone (bottom 4)"
        return {
            "competition": chosen_label,
            "season": season,
            "source_file": chosen_source,
            "matches_used": len(rows),
            "standings": entries,
            "note": ("Standings calculated from match results. Bottom 4 are relegated in the Brasileirão."
                     if is_brasileirao else "Standings calculated from match results."),
        }

    def competition_statistics(self, competition: str | None = None,
                               season: int | None = None) -> dict:
        labels = self.resolve_competitions(competition)
        matches = [m for m in self.matches_unique
                   if (labels is None or m.competition in labels)
                   and (season is None or m.season == season)
                   and m.home_goal is not None and m.away_goal is not None]
        if not matches:
            return {"error": "No matches found for the given competition/season."}
        total = len(matches)
        total_goals = sum(m.total_goals for m in matches)
        home_wins = sum(1 for m in matches if m.home_goal > m.away_goal)
        draws = sum(1 for m in matches if m.home_goal == m.away_goal)
        away_wins = total - home_wins - draws
        dates = [m.date for m in matches if m.date]
        biggest = max(matches, key=lambda m: m.margin)
        seasons = sorted({m.season for m in matches if m.season is not None})
        return {
            "competition": ", ".join(sorted({m.competition for m in matches})),
            "seasons": seasons,
            "match_count": total,
            "date_range": [min(dates).isoformat(), max(dates).isoformat()] if dates else None,
            "average_goals_per_match": round(total_goals / total, 2),
            "total_goals": total_goals,
            "home_win_rate": round(100.0 * home_wins / total, 1),
            "draw_rate": round(100.0 * draws / total, 1),
            "away_win_rate": round(100.0 * away_wins / total, 1),
            "biggest_win": biggest.to_dict(),
            "teams": len({m.home for m in matches} | {m.away for m in matches}),
        }

    def biggest_wins(self, competition: str | None = None, season: int | None = None,
                     limit: int = 10) -> dict:
        labels = self.resolve_competitions(competition)
        matches = [m for m in self.matches_unique
                   if (labels is None or m.competition in labels)
                   and (season is None or m.season == season)
                   and m.margin is not None and m.margin > 0]
        matches.sort(key=lambda m: (-m.margin, -(m.total_goals or 0), self._match_sort_key(m)))
        limit = max(1, min(int(limit or 10), 50))
        return {
            "count": len(matches[:limit]),
            "wins": [m.to_dict() for m in matches[:limit]],
        }

    def compare_seasons(self, competition: str, season_a: int, season_b: int) -> dict:
        stats_a = self.competition_statistics(competition, season_a)
        stats_b = self.competition_statistics(competition, season_b)
        if "error" in stats_a or "error" in stats_b:
            return {"error": "One or both seasons have no data for this competition.",
                    "season_a": stats_a, "season_b": stats_b}
        fields = ("match_count", "average_goals_per_match", "home_win_rate", "draw_rate", "away_win_rate", "teams")
        diff = {f: {"season_a": stats_a[f], "season_b": stats_b[f]} for f in fields}
        return {
            "competition": competition,
            "season_a": season_a,
            "season_b": season_b,
            "comparison": diff,
        }

    # ------------------------------------------------------------------
    # Cross-file and lookup helpers
    # ------------------------------------------------------------------

    def team_overview(self, team: str) -> dict:
        canonical = self.find_team(team)
        if canonical is None:
            return {"error": f"Team '{team}' not found.",
                    "candidates": self.team_candidates(team)}
        team_matches = self._dedupe(self._team_matches.get(canonical, []))
        by_competition: dict[str, int] = defaultdict(int)
        seasons: set[int] = set()
        for match in team_matches:
            by_competition[match.competition] += 1
            if match.season:
                seasons.add(match.season)
        rivals = defaultdict(int)
        for match in team_matches:
            rivals[match.away if match.home == canonical else match.home] += 1
        top_rivals = sorted(rivals.items(), key=lambda kv: -kv[1])[:5]
        players = self.club_player_summary(canonical)
        return {
            "team": self.team_display.get(canonical, canonical),
            "total_matches": len(team_matches),
            "matches_by_competition": dict(sorted(by_competition.items(), key=lambda kv: -kv[1])),
            "seasons": sorted(seasons),
            "most_common_opponents": [
                {"team": self.team_display.get(t, t), "matches": n} for t, n in top_rivals
            ],
            "fifa_players": players,
            "fifa_note": "Player data comes from the FIFA 19 (2018 season) dataset; many Brazilian clubs may not be licensed there." if players is None else None,
        }

    def list_teams(self, competition: str | None = None) -> dict:
        labels = self.resolve_competitions(competition)
        if competition and not labels:
            return {"error": f"Competition '{competition}' not recognized.",
                    "known": sorted(_COMPETITION_GROUPS)}
        teams = defaultdict(lambda: {"matches": 0, "competitions": set()})
        for match in self.matches_unique:
            if labels and match.competition not in labels:
                continue
            for side in (match.home, match.away):
                teams[side]["matches"] += 1
                teams[side]["competitions"].add(match.competition)
        entries = [
            {
                "team": self.team_display.get(team, team),
                "matches": info["matches"],
                "competitions": sorted(info["competitions"]),
            }
            for team, info in teams.items()
        ]
        entries.sort(key=lambda e: -e["matches"])
        return {"count": len(entries), "teams": entries}

    def summary(self) -> dict:
        by_competition: dict[str, int] = defaultdict(int)
        seasons: set[int] = set()
        teams: set[str] = set()
        for match in self.matches_unique:
            by_competition[match.competition] += 1
            if match.season:
                seasons.add(match.season)
            teams.add(match.home)
            teams.add(match.away)
        nationalities = len({p.nationality for p in self.players})
        clubs = sorted({p.club_key for p in self.players})
        return {
            "datasets": {
                "Brasileirao_Matches.csv": "Brasileirão Série A matches (2012-2022)",
                "Brazilian_Cup_Matches.csv": "Copa do Brasil matches (2012-2021)",
                "Libertadores_Matches.csv": "Copa Libertadores matches with Brazilian clubs (2013-2022)",
                "BR-Football-Dataset.csv": "Série A/B/C + Copa do Brasil extended stats (2014-2023)",
                "novo_campeonato_brasileiro.csv": "Brasileirão Série A 2003-2019",
                "fifa_data.csv": "FIFA 19 player database (2018 season)",
            },
            "matches_loaded": len(self.matches),
            "matches_deduplicated": len(self.matches_unique),
            "matches_by_competition": dict(sorted(by_competition.items(), key=lambda kv: -kv[1])),
            "seasons_covered": [min(seasons), max(seasons)] if seasons else [],
            "unique_teams": len(teams),
            "players_loaded": len(self.players),
            "player_nationalities": nationalities,
            "player_clubs": len(clubs),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _index_cup_rounds(self) -> None:
        """Detect, per season, which Copa do Brasil round number is the final.

        The dataset uses numeric round indices whose total count varies by
        season, and some seasons are missing the final rounds entirely. The
        final is the highest round with at most two matches (one two-legged
        tie); higher-volume last rounds mean the dataset simply ends earlier
        and no final can be identified.
        """
        rounds: dict[int, int] = defaultdict(int)
        counts: dict[tuple[int, str], int] = defaultdict(int)
        for match in self.matches:
            if match.competition == "Copa do Brasil" and match.round:
                try:
                    round_num = int(match.round)
                except ValueError:
                    continue
                season = match.season
                if season is None:
                    continue
                rounds[season] = max(rounds.get(season, 0), round_num)
                counts[(season, match.round.strip())] += 1
        self._max_cup_round = {}
        for season, top in rounds.items():
            if counts.get((season, str(top)), 0) <= 2:
                self._max_cup_round[season] = str(top)
