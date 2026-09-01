"""
BDD GWT scenarios: player queries (FIFA database).

Gherkin counterpart: ``tests/features/player_queries.feature``.

Covers TASK.md "Required Capabilities" -> "3. Player Queries":
search by name, filter by nationality/club/position, ratings.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import service as svc


class TestFindPlayers:
    def test_given_fifa_data_when_searching_brazilians_then_827_found(self, dataset):
        # Given "Find all Brazilian players in the dataset"
        # When filtering by nationality
        result = svc.find_players(dataset, nationality="Brazil")
        # Then all 827 Brazilian players are found
        assert result["total"] == 827

    def test_given_a_name_when_searching_then_substring_match(self, dataset):
        # Given "Who is Gabriel Barbosa?" / "Who is Neymar?"
        # When searching by name substring
        result = svc.find_players(dataset, name="Neymar")
        # Then Neymar Jr is found with his rating and club
        assert result["total"] == 1
        neymar = result["players"][0]
        assert neymar["name"] == "Neymar Jr"
        assert neymar["overall"] == 92
        assert neymar["position"] == "LW"
        assert neymar["club"] == "Paris Saint-Germain"

    def test_given_a_partial_name_when_searching_then_accent_insensitive(self, dataset):
        # Given accented player names in the source ("Éder Militão")
        # When searching with plain ASCII "Eder Militao"
        result = svc.find_players(dataset, name="Eder Militao")
        # Then the accented original is found
        assert result["total"] == 1
        assert result["players"][0]["name"] == "Éder Militão"
        assert result["players"][0]["nationality"] == "Brazil"

    def test_given_no_filters_when_searching_then_error(self, dataset):
        # Given a filterless request
        # When searching
        # Then the API refuses rather than dumping 18k rows
        with pytest.raises(ValueError, match="at least one filter"):
            svc.find_players(dataset)

    def test_given_rating_bounds_when_searching_then_range_applied(self, dataset):
        # Given a rating range question
        result = svc.find_players(dataset, nationality="Brazil", min_overall=85)
        # Then every returned player meets the bound
        assert result["total"] >= 3
        assert all(p["overall"] >= 85 for p in result["players"])


class TestTopPlayers:
    def test_given_brazilian_players_when_ranked_then_neymar_leads(self, dataset):
        # Given "Who are the top Brazilian players?"
        # When ranking by overall rating
        result = svc.top_players(dataset, nationality="Brazil", limit=3)
        # Then Neymar Jr tops the list
        assert result["players"][0]["name"] == "Neymar Jr"
        assert result["players"][0]["overall"] == 92
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_given_a_position_group_when_ranked_then_filtered(self, dataset):
        # Given "Show me all forwards" style queries
        # When filtering by the 'forward' group
        result = svc.top_players(dataset, nationality="Brazil", position="forward", limit=10)
        forward_codes = {"LW", "LF", "CF", "RF", "RW", "ST"}
        assert result["total"] > 0
        assert all(p["position"] in forward_codes for p in result["players"])

    def test_given_goalkeepers_when_ranked_then_alisson_found(self, dataset):
        # Given Brazilian goalkeepers
        result = svc.top_players(dataset, nationality="Brazil", position="goalkeeper", limit=5)
        # Then Alisson (Liverpool) appears
        names = [p["name"] for p in result["players"]]
        assert "Alisson" in names
        assert all(p["position"] == "GK" for p in result["players"])


class TestPlayersAtClub:
    def test_given_gremio_when_roster_requested_then_20_players(self, dataset):
        # Given "Which players play for Grêmio?"
        # When requesting the roster
        roster = svc.players_at_club(dataset, "Grêmio")
        # Then the 20 FIFA players are returned with summary stats
        assert roster["count"] == 20
        assert roster["average_overall"] == 73.3
        assert roster["by_position"]["GK"] >= 1

    def test_given_full_official_name_when_roster_requested_then_resolved(self, dataset):
        # Given "Sport Club do Recife" vs the dataset's "Sport - PE"
        roster = svc.players_at_club(dataset, "Sport Recife")
        assert roster["count"] == 20
        assert roster["fifa_source_club_name"] == "Sport Club do Recife"
        assert all(p["club"] == "Sport Club do Recife" for p in roster["players"])

    def test_given_flamengo_when_roster_requested_then_empty_with_note(self, dataset):
        # Given "Who are the highest-rated players at Flamengo?"
        # When requesting the roster
        roster = svc.players_at_club(dataset, "Flamengo")
        # Then the FIFA data gap is reported honestly
        assert roster["count"] == 0
        assert roster["note"] is not None

    def test_given_club_filter_when_searching_players_then_joined_via_registry(self, dataset):
        # Given club search joins through the club registry
        result = svc.find_players(dataset, club="Atlético Mineiro", limit=5)
        assert result["total"] == 20
        assert all(p["club"] == "Atlético Mineiro" for p in result["players"])

    def test_given_a_foreign_club_when_searched_then_found(self, dataset):
        # Given cross-file queries can reach world clubs too
        result = svc.find_players(dataset, club="Liverpool", nationality="Brazil")
        names = [p["name"] for p in result["players"]]
        assert "Alisson" in names
        assert "Fabinho" in names
