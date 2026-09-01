"""
Feature: Player Queries
  As a soccer fan I want to search the FIFA player database by name,
  nationality, club and position, and see which Brazilian clubs the
  snapshot actually contains.
"""

from __future__ import annotations

from brazilian_soccer_mcp.queries import (
    player_club_report,
    player_search,
)


class TestSearchByNationality:
    """TASK.md: "Find all Brazilian players in the dataset"."""

    def test_all_brazilian_players(self, ds):
        """
        Scenario: every Brazilian player
          Given the FIFA player database is loaded
          When I search for nationality "Brazil"
          Then 827 players are found
          And they are ordered by overall rating, descending
        """
        result = player_search(ds, nationality="Brazil", limit=50)
        assert result["ok"], result
        assert result["total"] == 827
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_top_rated_brazilians(self, ds):
        """
        Scenario: the highest-rated Brazilians
          Given the FIFA player database is loaded
          When I search Brazilians with a minimum overall of 88
          Then Neymar Jr (92) is first
        """
        result = player_search(ds, nationality="Brazil", min_overall=88)
        assert result["ok"]
        top = result["players"][0]
        assert top["name"] == "Neymar Jr"
        assert top["overall"] == 92
        assert top["position"] == "LW"
        assert top["club"] == "Paris Saint-Germain"


class TestSearchByNameAndClub:
    """TASK.md: "Who is Gabriel Barbosa?" / "Which players play for X?"."""

    def test_name_lookup_hit(self, ds):
        """
        Scenario: look a player up by name
          Given the FIFA player database is loaded
          When I search for the name "Gabriel Jesus"
          Then the striker is found with his club and ratings
        """
        result = player_search(ds, name="Gabriel Jesus")
        assert result["ok"]
        assert result["total"] >= 1
        player = result["players"][0]
        assert "Gabriel Jesus" in player["name"]
        assert player["position"] in {"ST", "CF", "LW", "RW"}

    def test_name_lookup_miss_is_honest(self, ds):
        """
        Scenario: a name the snapshot does not contain
          Given the FIFA player database is loaded
          When I search for "Gabriel Barbosa"
          Then zero players are returned
          And the answer notes the FIFA snapshot's limited club coverage
        """
        result = player_search(ds, name="Gabriel Barbosa")
        assert result["ok"]
        assert result["total"] == 0
        assert result["players"] == []

    def test_players_at_brazilian_club(self, ds):
        """
        Scenario: a squad list for a club the snapshot covers
          Given the FIFA player database is loaded
          When I search players at club "Grêmio"
          Then 20 players are found, led by a rating above 80
        """
        result = player_search(ds, club="Grêmio", limit=30)
        assert result["ok"], result
        assert result["total"] == 20
        assert result["players"][0]["overall"] > 80

    def test_players_at_club_outside_match_data(self, ds):
        """
        Scenario: a foreign club absent from the match datasets
          Given the FIFA player database is loaded
          When I search players at club "Juventus"
          Then the search still works via the FIFA club string
          And Cristiano Ronaldo (94) is among them
        """
        result = player_search(ds, club="Juventus", limit=10)
        assert result["ok"]
        assert result["total"] == 25
        names = [p["name"] for p in result["players"]]
        assert "Cristiano Ronaldo" in names

    def test_players_at_club_not_in_fifa_snapshot(self, ds):
        """
        Scenario: a Brazilian club the FIFA snapshot does not list
          Given the FIFA player database is loaded
          When I search forwards at club "São Paulo"
          Then zero players are found (the snapshot lists no São Paulo squad)
        """
        result = player_search(ds, club="São Paulo", position="FWD")
        assert result["ok"]
        assert result["total"] == 0


class TestPositionAndAttributeFilters:
    """TASK.md: "Show me all forwards from <club>"."""

    def test_position_group_filter(self, ds):
        """
        Scenario: position groups expand to FIFA codes
          Given the FIFA player database is loaded
          When I search Brazilian forwards with overall >= 85
          Then every result has a forward position code
        """
        result = player_search(
            ds, nationality="Brazil", position="FWD", min_overall=85, limit=50
        )
        assert result["ok"]
        assert result["total"] >= 1
        forward_codes = {"ST", "LS", "RS", "CF", "LW", "RW", "LF", "RF"}
        assert all(p["position"] in forward_codes for p in result["players"])

    def test_position_code_filter(self, ds):
        """
        Scenario: an exact FIFA position code
          Given the FIFA player database is loaded
          When I search Brazilian goalkeepers
          Then every result is a GK
        """
        result = player_search(ds, nationality="Brazil", position="GK")
        assert result["ok"]
        assert result["total"] > 10
        assert all(p["position"] == "GK" for p in result["players"])

    def test_invalid_position(self, ds):
        """
        Scenario: unknown position
          Given the FIFA player database is loaded
          When I search position "winger"
          Then the error lists the valid codes and groups
        """
        result = player_search(ds, position="winger")
        assert not result["ok"]
        assert "ST" in result["error"] and "FWD" in result["error"]

    def test_ordering_options(self, ds):
        """
        Scenario: alternative orderings
          Given the FIFA player database is loaded
          When I order Brazilians by age and by name
          Then the results are sorted accordingly
        """
        by_age = player_search(ds, nationality="Brazil", order="age", limit=30)
        ages = [p["age"] for p in by_age["players"]]
        assert ages == sorted(ages, reverse=True)
        by_name = player_search(ds, nationality="Brazil", order="name", limit=30)
        names = [p["name"] for p in by_name["players"]]
        assert names == sorted(names)


class TestPlayerClubReport:
    """TASK.md: "Brazilian players at Brazilian clubs"."""

    def test_report_groups_brazilian_clubs(self, ds):
        """
        Scenario: a per-club report of Brazilian players
          Given the FIFA player database is loaded
          When I group Brazilian players by club
          Then Brazilian clubs from the match data are flagged
          And each carries a count, average and best rating
        """
        result = player_club_report(ds, nationality="Brazil")
        assert result["ok"], result
        brazilian_rows = [
            r for r in result["clubs_report"] if r["brazilian_club_in_match_data"]
        ]
        assert len(brazilian_rows) >= 10
        for row in brazilian_rows:
            assert row["players"] >= 1
            assert row["avg_overall"] > 60
            assert row["best_player"]["name"]

    def test_report_top_brazilian_club(self, ds):
        """
        Scenario: the strongest Brazilian club group
          Given the FIFA player database is loaded
          When I group Brazilian players by club
          Then Atlético Mineiro's 20 players lead on average rating
        """
        result = player_club_report(ds, nationality="Brazil")
        brazilian_rows = [
            r for r in result["clubs_report"] if r["brazilian_club_in_match_data"]
        ]
        top = brazilian_rows[0]
        assert top["club"] == "Atlético Mineiro"
        assert top["players"] == 20
        assert top["avg_overall"] == 73.5
