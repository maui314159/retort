"""Feature: Data Loading Integrity
  All six CSV files must be loadable and queryable, the curated match list
  must be de-duplicated across overlapping sources, and merged statistics
  (stadiums, corners) must survive source selection.
"""

import pytest


class TestAllFilesLoad:
    def test_all_six_files_are_loaded_and_queryable(self, repo):
        # Given the six Kaggle datasets
        report = repo.load_report
        # When loaded
        # Then every file contributes rows
        files = report["files"]
        assert set(files) == {
            "Brasileirao_Matches.csv",
            "Brazilian_Cup_Matches.csv",
            "Libertadores_Matches.csv",
            "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro.csv",
            "fifa_data.csv",
        }
        assert files["Brasileirao_Matches.csv"]["rows"] == 4180
        assert files["novo_campeonato_brasileiro.csv"]["rows"] == 6886
        assert files["BR-Football-Dataset.csv"]["rows"] == 10296
        assert files["fifa_data.csv"]["rows"] == 18207
        assert report["players_loaded"] == 18207

    def test_unplayed_fixtures_are_skipped_not_corrupted(self, repo):
        # Given rows without scores (unplayed 2022 fixtures and the
        # Libertadores placeholder final)
        report = repo.load_report["files"]
        # When loaded
        # Then they are skipped and counted
        assert report["Brasileirao_Matches.csv"]["skipped"] == 82
        assert report["Libertadores_Matches.csv"]["skipped"] == 2
        # And no loaded match is missing its core fields
        for match in repo.matches[:500]:
            assert match.date is not None
            assert match.home_goals is not None
            assert match.away_goals is not None


class TestCuration:
    def test_overlapping_sources_are_deduplicated(self, repo):
        # Given three files that all contain the 2012-2019 Brasileirão
        # When curated
        # Then the result is smaller than the raw pile and shadowed rows are counted
        assert repo.load_report["matches_loaded_raw"] == 23854
        assert repo.load_report["matches_curated"] == 16612
        assert repo.load_report["duplicates_shadowed"] > 1000

    def test_curated_matches_have_no_exact_duplicates(self, repo):
        # Given the curated match list
        keys = [
            (
                match.competition,
                match.season,
                match.date,
                match.home_team,
                match.away_team,
                match.home_goals,
                match.away_goals,
            )
            for match in repo.matches
        ]
        # When checked for exact duplicates
        # Then every curated match is unique
        assert len(keys) == len(set(keys))

    def test_one_source_per_competition_season(self, repo):
        # Given the curated 2019 Serie A
        matches_2019 = [
            m for m in repo.matches if m.season == 2019 and m.competition == "Brasileirão Serie A"
        ]
        # When inspected
        # Then exactly the 380 matches of one preferred source are kept
        assert len(matches_2019) == 380
        assert {m.source for m in matches_2019} == {"Brasileirao_Matches.csv"}

    def test_extended_statistics_are_merged_not_lost(self, repo):
        # Given matches whose preferred source has no statistics file data
        season_2018 = [
            m
            for m in repo.matches
            if m.season == 2018 and m.competition == "Brasileirão Serie A"
        ]
        # When the merge ran
        # Then corner statistics from the statistics file were attached
        with_corners = [m for m in season_2018 if m.home_corners is not None]
        assert len(with_corners) > 200

    def test_stadiums_are_merged_from_the_historical_file(self, repo):
        # Given the 2019 season preferred from the round-by-round file
        season_2019 = [
            m
            for m in repo.matches
            if m.season == 2019 and m.competition == "Brasileirão Serie A"
        ]
        # When the merge ran
        # Then stadium names from the historical file were attached
        with_stadium = [m for m in season_2019 if m.stadium]
        assert len(with_stadium) >= 370
        assert any(m.stadium == "Maracanã" for m in with_stadium)


class TestEntityResolution:
    def test_major_clubs_resolve_to_single_entities(self, repo):
        # Given the big Brazilian clubs
        # When resolved
        # Then none of them is split across multiple entities
        for query in [
            "Flamengo",
            "Fluminense",
            "Corinthians",
            "Palmeiras",
            "São Paulo",
            "Santos",
            "Grêmio",
            "Internacional",
            "Cruzeiro",
            "Atlético-MG",
            "Athletico-PR",
            "Botafogo",
            "Vasco",
        ]:
            entities = repo.resolve_team(query)
            assert len(entities) == 1, (query, entities)

    def test_big_club_matches_join_across_files(self, repo):
        # Given Flamengo's match list
        flamengo = repo.matches_for_entity("flamengo rj")
        sources = {match.source for match in flamengo}
        competitions = {match.competition for match in flamengo}
        # When aggregating
        # Then matches from several files and competitions join into one record
        assert len(sources) >= 4
        assert {
            "Brasileirão Serie A",
            "Copa Libertadores",
            "Copa do Brasil",
        } <= competitions
        assert len(flamengo) > 900
