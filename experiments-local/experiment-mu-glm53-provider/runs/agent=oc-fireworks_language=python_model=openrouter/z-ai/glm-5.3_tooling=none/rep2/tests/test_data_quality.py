"""BDD scenarios for data coverage and cross-file merging quality.

Feature: Data coverage
  Scenario: All six CSV files are loadable and queryable
    Given the server starts
    When the knowledge graph is built
    Then all competitions, teams and players are present
    And overlapping fixtures between files are deduplicated
"""

from __future__ import annotations

from collections import Counter


class TestAllFilesLoaded:
    def test_expected_match_totals(self, dataset):
        # Given all six CSV files are loaded
        # When matches are counted per competition
        counts = Counter(m.competition for m in dataset.matches)
        # Then every competition is present at the expected scale
        assert counts["brasileirao"] >= 8400      # files 1+2+3 merged/deduped
        assert counts["serie_b"] >= 3600          # file 4
        assert counts["serie_c"] >= 1800          # file 4
        assert counts["copa_do_brasil"] >= 1700   # files 4+5 merged/deduped
        assert counts["libertadores"] == 1255     # file 6

    def test_players_database_is_complete(self, dataset):
        # Given the FIFA file has 18,207 players
        # When loaded
        # Then all of them are queryable with 827 Brazilians
        assert len(dataset.players) == 18207
        assert sum(1 for p in dataset.players if p.nationality == "Brazil") == 827

    def test_team_registry_built_from_all_sources(self, dataset):
        # Given team names from all match files
        # When the registry is built
        # Then hundreds of distinct clubs exist, incl. small cup sides
        assert len(dataset.registry.teams) >= 400
        assert dataset.registry.resolve("Boavista").matched  # tiny RJ cup side


class TestDeduplication:
    def test_serie_a_seasons_are_exactly_380_matches(self, dataset):
        # Given the two Brasileirão files overlap in 2012-2019
        # When each season is counted after merging
        per_season = Counter(
            m.season for m in dataset.matches if m.competition == "brasileirao"
        )
        # Then modern seasons have exactly 380 matches (no double counting)
        for season in range(2012, 2023):
            assert per_season[season] == 380, season
        # And the 24/22-team era had its larger calendars
        assert per_season[2003] == 552
        assert per_season[2005] == 462

    def test_no_duplicate_fixtures_within_a_serie_a_season(self, dataset):
        # Given merged Serie A matches
        # When fixture identity is checked per season
        seen = {}
        for m in dataset.matches:
            if m.competition != "brasileirao" or m.season is None:
                continue
            key = (m.season, m.home.key, m.away.key)
            # Then no ordered pair meets twice in one season
            assert key not in seen, f"duplicate fixture {key}"
            seen[key] = m

    def test_unplayed_2022_rounds_were_filled_from_extended_file(self, dataset):
        # Given the primary file records rounds 31-38 of 2022 without scores
        # When the extended file's results are merged in
        played_2022 = sum(
            1 for m in dataset.matches
            if m.competition == "brasileirao" and m.season == 2022 and m.played
        )
        # Then the 2022 season is (nearly) complete
        assert played_2022 >= 375


class TestCrossFileQueries:
    def test_extended_stats_are_attached_to_merged_matches(self, dataset):
        # Given the extended file carries corners/shots/attacks
        # When matches are merged
        # Then thousands of matches expose those stats
        with_stats = sum(1 for m in dataset.matches if m.stats)
        assert with_stats >= 10000
        sample = next(
            m for m in dataset.matches
            if m.stats and m.competition == "brasileirao" and m.round_label
        )
        assert "corners" in sample.describe()

    def test_2023_season_comes_from_the_extended_file(self, dataset):
        # Given the primary files stop at 2022
        # When the 2023 season is queried
        seasons = dataset.seasons_for("brasileirao")
        # Then 2023 is available through the extended file
        assert 2023 in seasons
        matches_2023 = [
            m for m in dataset.matches
            if m.competition == "brasileirao" and m.season == 2023
        ]
        assert len(matches_2023) >= 370

    def test_player_and_match_data_combine_in_one_answer(self, svc):
        # Given a team exists in both match data and the FIFA dataset
        # When its profile is requested
        result = svc.team_profile("Grêmio")
        # Then the answer combines match history and player squad
        assert "All-time record:" in result
        assert "FIFA dataset: 20 players" in result


class TestUtf8Handling:
    def test_accented_names_survive(self, dataset):
        # Given Brazilian Portuguese names with accents and cedillas
        # When displays are picked
        # Then accented spellings are preserved
        displays = {t.display for t in dataset.registry.teams.values()}
        assert "Grêmio" in displays
        assert "São Paulo" in displays
        assert "Atlético-MG" in displays
