"""
BDD GWT scenarios: team queries.

Gherkin counterpart: ``tests/features/team_queries.feature``.

Covers TASK.md "Required Capabilities" -> "2. Team Queries" and the
"Get team statistics" Gherkin sketch in "Testing Approach".
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import service as svc


class TestGetTeamStatistics:
    """Scenario: Get team statistics (TASK.md Testing Approach)."""

    def test_given_match_data_when_requesting_palmeiras_2023_then_record_returned(self, dataset):
        # Given the match data is loaded
        # When I request statistics for "Palmeiras" in season "2023"
        record = svc.team_record(dataset, "Palmeiras", season=2023)
        # Then I should receive wins, losses, draws, and goals
        overall = record["overall"]
        for key in ("matches", "wins", "draws", "losses", "goals_for", "goals_against"):
            assert key in overall
        assert overall["wins"] + overall["draws"] + overall["losses"] == overall["matches"]

    def test_given_palmeiras_2023_when_computed_then_values_match_source(self, dataset):
        # Given the 2023 season data (37 scored matches for Palmeiras)
        record = svc.team_record(dataset, "Palmeiras", competition="Brasileirão Serie A", season=2023)
        # Then the record matches the computed table
        assert record["overall"]["matches"] == 37
        assert record["overall"]["wins"] == 19
        assert record["overall"]["draws"] == 10
        assert record["overall"]["losses"] == 8
        assert record["overall"]["goals_for"] == 61
        assert record["overall"]["goals_against"] == 32
        # And the incomplete-source caveat is surfaced
        assert record["notes"] and "Data incomplete" in record["notes"][0]


class TestVenueRecords:
    def test_given_corinthians_2022_when_home_record_requested_then_home_only(self, dataset):
        # Given "What is Corinthians' home record in 2022?"
        # When requesting the home venue record
        record = svc.team_record(
            dataset, "Corinthians", competition="Brasileirão Serie A", season=2022, venue="home"
        )
        # Then only home matches are counted (15 scored in the partial source)
        overall = record["overall"]
        assert overall["matches"] == 15
        assert overall["wins"] == 10
        assert overall["draws"] == 4
        assert overall["losses"] == 1
        assert overall["goals_for"] == 21
        assert overall["goals_against"] == 7
        assert overall["win_rate"] == 66.7

    def test_given_a_team_when_home_plus_away_then_equals_overall(self, dataset):
        # Given any team season
        # When computing home, away and overall records
        # Then home + away matches equal the overall total
        overall = svc.team_record(dataset, "Grêmio", competition="Brasileirão Serie A", season=2019)[
            "overall"
        ]
        home = svc.team_record(
            dataset, "Grêmio", competition="Brasileirão Serie A", season=2019, venue="home"
        )["overall"]
        away = svc.team_record(
            dataset, "Grêmio", competition="Brasileirão Serie A", season=2019, venue="away"
        )["overall"]
        assert home["matches"] + away["matches"] == overall["matches"] == 38

    def test_given_invalid_venue_when_requested_then_error(self, dataset):
        with pytest.raises(ValueError, match="venue"):
            svc.team_record(dataset, "Grêmio", venue="neutral")


class TestTeamProfile:
    def test_given_palmeiras_when_profile_requested_then_cross_file_view(self, dataset):
        # Given "What competitions has Palmeiras played in?"
        # When requesting the team profile
        profile = svc.team_profile(dataset, "Palmeiras")
        # Then every competition featuring Palmeiras is listed with seasons
        comps = set(profile["competitions"])
        assert "Brasileirão Serie A" in comps
        assert "Copa Libertadores" in comps
        assert "Copa do Brasil" in comps
        serie_a = profile["competitions"]["Brasileirão Serie A"]
        assert serie_a["seasons"][0] == 2004  # Palmeiras were in Serie B in 2003
        assert 2023 in serie_a["seasons"]

    def test_given_a_club_with_fifa_players_when_profiled_then_roster_summary(self, dataset):
        # Given Grêmio's generic FIFA-19 roster (Brazilian clubs ship with
        # fictitious players in that source)
        profile = svc.team_profile(dataset, "Grêmio")
        # Then the profile summarizes the roster
        assert profile["fifa_players"]["count"] == 20
        assert profile["fifa_players"]["average_overall"] == 73.3
        top = profile["fifa_players"]["top"]
        assert top[0]["overall"] == 83
        assert [p["overall"] for p in top] == sorted((p["overall"] for p in top), reverse=True)

    def test_given_a_club_without_fifa_players_when_profiled_then_note(self, dataset):
        # Given Flamengo's roster is absent from the FIFA source
        profile = svc.team_profile(dataset, "Flamengo")
        # Then the profile says so instead of pretending
        assert profile["fifa_players"]["count"] == 0
        assert profile["note"] is not None
        assert "FIFA" in profile["note"]


class TestListTeams:
    def test_given_2019_serie_a_when_teams_listed_then_twenty_clubs(self, dataset):
        # Given the 2019 Brasileirão
        # When listing teams
        result = svc.list_teams(dataset, "Brasileirão Serie A", 2019)
        # Then all 20 clubs appear with match counts
        assert result["team_count"] == 20
        names = [t["team"] for t in result["teams"]]
        assert "Flamengo" in names and "Avaí" in names

    def test_given_copa_libertadores_when_teams_listed_then_foreign_clubs_included(self, dataset):
        # Given Libertadores includes South American clubs
        result = svc.list_teams(dataset, "Copa Libertadores")
        # Then foreign clubs are listed alongside Brazilian ones
        names = " ".join(t["team"] for t in result["teams"])
        assert "Boca Juniors" in names or "River Plate" in names


class TestTeamResolution:
    def test_given_variant_spellings_when_resolved_then_single_club(self, dataset):
        # Given the many spellings of Athletico Paranaense
        # When resolving each
        # Then all map to the same club
        ids = {
            svc.resolve_team_info(dataset, name)["matches"][0]["club_id"]
            for name in ("Athletico", "Athletico-PR", "Atletico Paranaense", "Athletico Paranaense - PR")
        }
        assert ids == {"atletico|PR"}

    def test_given_ambiguous_name_when_resolved_then_alternates_listed(self, dataset):
        # Given "América" matches clubs in Minas Gerais and Rio Grande do Norte
        info = svc.resolve_team_info(dataset, "América")
        # Then both are surfaced, most prominent first
        assert info["matches"][0]["club_id"] == "america|MG"
        assert info["matches"][1]["club_id"] == "america|RN"

    def test_given_a_profile_when_requested_then_alias_spellings_shown(self, dataset):
        profile = svc.team_profile(dataset, "Vasco da Gama")
        assert profile["club_id"] == "vasco|RJ"
        assert any("Vasco" in a for a in profile["aliases"])
