"""
Club registry - the team-name knowledge graph.

Context block
-------------
Why:
    The five match datasets and the FIFA dataset spell the same club in
    dozens of ways ("Palmeiras-SP", "Palmeiras", "Athletico Paranaense - PR",
    "Sport Club do Recife", ...).  Queries like "What is Corinthians' home
    record?" must find every one of those spellings while keeping genuinely
    distinct clubs (Botafogo-RJ vs Botafogo-PB, América-MG vs América-RN)
    apart.

What:
    ``ClubRegistry`` maps every ``TeamName`` variant onto a ``Club`` entity.
    * ``register``   - record a raw spelling (increments a counter).
    * ``finalize``   - merge state-less clubs (base ``|`` only) into the
      same-base state-qualified club with the most match records, so
      "Vasco" (novo) folds into Vasco da Gama-RJ and a bare Libertadores
      "Flamengo" folds into Flamengo-RJ.  State-qualified clubs never merge.
    * ``resolve``    - rank clubs for a free-text query: exact key, then
      exact base (by record count), then substring containment (min length
      4).  Used by every team-facing tool for fuzzy disambiguation.
    * ``get``        - variant key -> Club after merges are applied.

Test:
    BDD GWT scenarios in ``tests/test_dataset.py`` (registry merging) and
    ``tests/test_team_queries.py`` (resolution ordering).

Spec references:
    TASK.md "Data Quality Notes" - "Implementation should normalize team
    names for consistent matching"; "Handles team name variations
    correctly" (Success Criteria).
"""

from __future__ import annotations

from .models import Club
from .normalize import NO_MERGE_BASES, TeamName, normalize_team

_MIN_CONTAINMENT_LEN = 4


class ClubRegistry:
    """Registry of club entities keyed by normalized ``TeamName`` keys."""

    def __init__(self) -> None:
        self._clubs: dict[str, Club] = {}
        self._by_id: dict[str, Club] = {}

    # -- construction ----------------------------------------------------

    def register(self, raw_name: str) -> TeamName:
        """Record a raw team spelling and return its normalized identity."""
        team = normalize_team(raw_name)
        if not team.base:
            return team
        club = self._clubs.get(team.key)
        if club is None:
            club = Club(id=team.key, base=team.base, state=team.state)
            self._clubs[team.key] = club
        club.variant_counts[raw_name.strip()] = club.variant_counts.get(raw_name.strip(), 0) + 1
        return team

    def add_match_count(self, team: TeamName, amount: int = 1) -> None:
        club = self._clubs.get(team.key)
        if club is not None:
            club.match_count += amount

    def finalize(self) -> None:
        """Merge state-less clubs into dominant same-base state-qualified clubs."""
        # Group clubs by base.
        by_base: dict[str, list[Club]] = {}
        for club in self._clubs.values():
            by_base.setdefault(club.base, []).append(club)

        merges: dict[str, Club] = {}
        for base, clubs in by_base.items():
            if base in NO_MERGE_BASES:
                continue
            stateful = [c for c in clubs if c.state]
            stateless = [c for c in clubs if not c.state]
            if not stateful or not stateless:
                continue
            dominant = max(stateful, key=lambda c: (c.match_count, len(c.variant_counts)))
            for club in stateless:
                merges[club.id] = dominant

        # Apply merges: fold counters into the dominant club and mark the
        # source club as merged so lookups redirect.
        for source_id, dominant in merges.items():
            source = self._clubs[source_id]
            dominant.match_count += source.match_count
            for variant, count in source.variant_counts.items():
                dominant.variant_counts[variant] = dominant.variant_counts.get(variant, 0) + count
            source.merged_into = dominant.id

        # Rebuild the id lookup: every key (including merged sources)
        # resolves to its surviving club.
        self._by_id = {}
        for club in self._clubs.values():
            target = club
            seen = set()
            while target.merged_into and target.merged_into not in seen:
                seen.add(target.id)
                target = self._clubs[target.merged_into]
            self._by_id[club.id] = target

    # -- lookup ----------------------------------------------------------

    def get(self, team: TeamName) -> Club | None:
        return self._by_id.get(team.key)

    def all_clubs(self) -> list[Club]:
        """All surviving (non-merged) clubs."""
        return [c for c in self._by_id.values() if not c.merged_into]

    def resolve(self, query: str) -> list[Club]:
        """Rank clubs matching a free-text team name.

        Tier 1: exact (base, state) key.  Tier 2: exact base, any state,
        ordered by record count.  Tier 3: substring containment either way
        (only for bases >= 4 chars), ordered by record count.  Returns an
        empty list when nothing matches.
        """
        team = normalize_team(query)
        if not team.base:
            return []

        def rank_key(club: Club) -> tuple[int, int]:
            return (club.match_count + club.player_count, len(club.variant_counts))

        # Tier 1: exact identity.
        exact = self.get(team)
        if exact is not None:
            return [exact]

        results: dict[str, Club] = {}

        # Tier 2: same base, any state.
        for club in self.all_clubs():
            if club.base == team.base:
                results[club.id] = club
        if results:
            return sorted(results.values(), key=rank_key, reverse=True)

        # Tier 3: containment either way.
        if len(team.base) >= _MIN_CONTAINMENT_LEN:
            for club in self.all_clubs():
                if len(club.base) >= _MIN_CONTAINMENT_LEN and (
                    team.base in club.base or club.base in team.base
                ):
                    results[club.id] = club
        return sorted(results.values(), key=rank_key, reverse=True)

    def resolve_one(self, query: str) -> Club | None:
        ranked = self.resolve(query)
        return ranked[0] if ranked else None

    def __len__(self) -> int:
        return len(self.all_clubs())
