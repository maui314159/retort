"""Unit tests for dataset loading, de-duplication and store correctness."""

from __future__ import annotations

import time
from collections import Counter

import pytest

from brazilian_soccer.loader import SKILL_COLUMNS
from brazilian_soccer.store import NotFound, SoccerStore

EXPECTED_COMPETITIONS = {
    "Brasileirão Serie A", "Brasileirão Serie B", "Brasileirão Serie C",
    "Copa do Brasil", "Copa Libertadores",
}


class TestDataCoverage:
    """All six CSV files are loadable and queryable (spec success criteria)."""

    def test_all_six_datasets_used(self, store: SoccerStore):
        sources = {m.source for m in store.matches}
        assert sources == {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
        }
        assert len(store.players) == 18207      # FIFA database row count

    def test_competitions_covered(self, store: SoccerStore):
        comps = {m.competition for m in store.matches}
        assert EXPECTED_COMPETITIONS <= comps

    def test_almost_all_matches_have_scores_and_dates(self, store: SoccerStore):
        # Postponed/walkover fixtures (e.g. Chapecoense 2016) legitimately
        # have no result in the source data; they must stay excluded from
        # statistics via has_result().
        with_result = sum(1 for m in store.matches if m.has_result())
        assert with_result / len(store.matches) > 0.99
        missing_dates = sum(1 for m in store.matches if m.date is None)
        assert missing_dates <= 1               # one broken Libertadores row

    def test_players_have_skills(self, store: SoccerStore):
        neymar = store.get_player("Neymar Jr")
        assert neymar["overall"] == 92
        assert set(SKILL_COLUMNS[:3]) <= set(neymar["skills"])


class TestDedupe:
    def test_serie_a_2019_is_exactly_380_matches(self, store: SoccerStore):
        season = [m for m in store.matches
                  if m.competition == "Brasileirão Serie A" and m.season == 2019]
        assert len(season) == 380
        per_team = Counter()
        for m in season:
            per_team[m.home_key] += 1
            per_team[m.away_key] += 1
        assert set(per_team.values()) == {38}   # 20 teams, double round-robin

    def test_no_cross_source_duplicates_remain(self, store: SoccerStore):
        keys = Counter(
            (m.competition, m.season, m.date, m.home_key, m.away_key)
            for m in store.matches
        )
        assert max(keys.values()) == 1


class TestCrossFileQueries:
    def test_fifa_club_links_to_match_team(self, store: SoccerStore):
        key = store.resolve_team("Atlético Mineiro")
        assert len(store.matches_by_team[key]) > 500       # match datasets
        assert len(store.players_by_club[key]) > 0         # FIFA dataset

    def test_serie_a_2023_only_in_extended_dataset(self, store: SoccerStore):
        season = [m for m in store.matches
                  if m.competition == "Brasileirão Serie A" and m.season == 2023]
        assert season
        assert {m.source for m in season} == {"BR-Football-Dataset.csv"}


class TestResolution:
    def test_team_variants(self, store: SoccerStore):
        assert store.resolve_team("Flamengo") == store.resolve_team("Flamengo-RJ")
        assert store.resolve_team("Sao Paulo") == store.resolve_team("São Paulo")
        assert store.resolve_team("Athletico Paranaense") == \
            store.resolve_team("Atlético - PR")

    def test_unknown_team_raises(self, store: SoccerStore):
        with pytest.raises(NotFound):
            store.resolve_team("Narnia United")

    def test_competition_aliases(self, store: SoccerStore):
        assert store.resolve_competition("brasileirao") == "Brasileirão Serie A"
        assert store.resolve_competition("Serie A") == "Brasileirão Serie A"
        assert store.resolve_competition("Copa do Brasil") == "Copa do Brasil"
        assert store.resolve_competition("libertadores") == "Copa Libertadores"

    def test_unknown_competition_raises(self, store: SoccerStore):
        with pytest.raises(NotFound):
            store.resolve_competition("Champions League")


class TestPerformance:
    """Spec: simple lookups < 2 s, aggregate queries < 5 s."""

    def test_simple_lookup_speed(self, store: SoccerStore):
        start = time.perf_counter()
        store.head_to_head("Flamengo", "Fluminense")
        store.search_matches(team="Palmeiras", season=2023)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"simple lookups took {elapsed:.2f}s"

    def test_aggregate_speed(self, store: SoccerStore):
        start = time.perf_counter()
        store.statistics()
        store.standings("Brasileirão Serie A", 2019)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"aggregates took {elapsed:.2f}s"
