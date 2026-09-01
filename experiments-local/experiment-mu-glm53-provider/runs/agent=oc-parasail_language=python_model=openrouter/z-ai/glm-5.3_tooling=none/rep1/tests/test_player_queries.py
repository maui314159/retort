"""Feature: Player Queries
  Search the FIFA player database by name, nationality, club, position
  and ratings; join players to match data through normalised club keys.
"""

import pytest

from brazilian_soccer import queries
from brazilian_soccer.queries import QueryError


class TestPlayerSearch:
    def test_all_brazilian_players(self, repo):
        # Given the FIFA player database
        result = queries.search_players(repo, nationality="Brazil", limit=10)
        # When filtered to Brazilian players
        # Then all 827 are counted and every one is Brazilian
        assert result["total_players"] == 827
        for player in result["players"]:
            assert player["nationality"] == "Brazil"

    def test_top_rated_brazilian_players(self, repo):
        # Given Brazilian players sorted by rating
        result = queries.search_players(repo, nationality="Brazil", limit=5)
        # When listed
        # Then Neymar Jr leads with his 92 rating
        top = result["players"][0]
        assert top["name"] == "Neymar Jr"
        assert top["overall"] == 92
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_highest_rated_players_at_a_brazilian_club(self, repo):
        # Given Grêmio's squad in the FIFA database
        result = queries.search_players(repo, club="Grêmio", limit=30)
        # When sorted by overall rating
        # Then all 20 licensed players are returned in descending order
        assert result["total_players"] == 20
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)
        for player in result["players"]:
            assert player["club"] == "Grêmio"

    def test_club_absent_from_fifa_dataset_returns_empty(self, repo):
        # Given Flamengo, which is not licensed in this FIFA edition
        result = queries.search_players(repo, club="Flamengo")
        # When searched
        # Then no players are returned rather than an error
        assert result["total_players"] == 0
        assert result["players"] == []

    def test_search_player_by_name(self, repo):
        # Given the question "Who is Gabriel Jesus?"
        result = queries.player_detail(repo, name="Gabriel Jesus")
        # When the name is looked up
        # Then his profile comes back with club and position
        player = result["player"]
        assert player["name"] == "Gabriel Jesus"
        assert player["club"] == "Manchester City"
        assert player["position"] == "ST"
        assert player["overall"] == 83
        assert player["attributes"]["Finishing"] is not None

    def test_player_detail_by_fifa_id(self, repo):
        # Given Messi's FIFA id
        result = queries.player_detail(repo, player_id=158023)
        # When looked up by id
        # Then the full profile with attributes is returned
        assert result["player"]["name"] == "L. Messi"
        assert "Crossing" in result["player"]["attributes"]

    def test_player_not_in_dataset_raises(self, repo):
        # Given a player absent from the FIFA database
        # When looked up
        # Then a helpful error is raised
        with pytest.raises(QueryError, match="No player matches"):
            queries.player_detail(repo, name="Gabriel Barbosa")

    def test_forwards_from_a_club(self, repo):
        # Given forwards at Santos
        result = queries.search_players(repo, club="Santos", position="forward", limit=30)
        # When filtered
        # Then every player is a forward at that club
        assert result["total_players"] >= 3
        for player in result["players"]:
            assert player["position_group"] == "forward"
            assert player["club"] == "Santos"

    def test_position_group_synonyms(self, repo):
        # Given position filters using different synonyms
        for query, expected in [("GK", "goalkeeper"), ("goalkeeper", "goalkeeper")]:
            result = queries.search_players(repo, position=query, limit=5)
            assert result["total_players"] > 0
            assert all(p["position_group"] == expected for p in result["players"])

    def test_minimum_overall_filter(self, repo):
        # Given a minimum rating of 85
        result = queries.search_players(repo, min_overall=85, limit=50)
        # When filtered
        # Then every player meets the threshold
        assert result["total_players"] > 10
        assert all(p["overall"] >= 85 for p in result["players"])

    def test_max_age_filter(self, repo):
        result = queries.search_players(repo, max_age=20, sort="age", limit=20)
        assert result["players"]
        assert all(p["age"] <= 20 for p in result["players"])


class TestCrossFileQueries:
    def test_match_and_player_data_join_on_club(self, repo):
        # Given a Brazilian club licensed in the FIFA database
        # When the same club is queried in match data and player data
        match_stats = queries.team_stats(repo, "Atlético Mineiro")
        players = queries.search_players(repo, club="Atlético Paranaense")
        # Then both sides answer and agree on club identity
        assert match_stats["overall"]["matches"] > 800
        assert players["total_players"] == 20
        assert match_stats["team"] == "Atlético-MG"

    def test_atletico_mineiro_fifa_spelling_matches_match_entity(self, repo):
        # Given the FIFA spelling of the club
        entities = repo.resolve_team("Atlético Mineiro")
        # When resolved
        # Then it denotes the same entity as the match-file spelling
        assert [entity.key for entity in entities] == ["atletico mg"]
        assert repo.matches_for_entity("atletico mg")
