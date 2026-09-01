"""
BDD scenarios: player queries (TASK.md "Required Capabilities" #3).

Feature: Player Queries
  Scenario: Search players
    Given the FIFA player data is loaded
    When I search for Brazilian players rated 85 or higher
    Then I should receive players with name, rating, position and club
"""

from __future__ import annotations

import pytest


class TestSearchPlayers:
    """Scenario: search the FIFA dataset with filters."""

    def test_all_brazilian_players(self, service):
        # Given the FIFA data is loaded
        # When I search for Brazilian players
        players = service.search_players(nationality="Brazil", limit=2000)
        # Then 827 Brazilians are found (dataset ground truth)
        assert len(players) == 827
        assert all(p.nationality == "Brazil" for p in players)

    def test_sorted_by_overall(self, service):
        players = service.search_players(nationality="Brazil", limit=50)
        ratings = [p.overall for p in players]
        assert ratings == sorted(ratings, reverse=True)

    def test_top_brazilian_is_neymar(self, service):
        # Given TASK.md's example mentions Neymar Jr as the top Brazilian
        players = service.top_brazilian_players(5)
        assert players[0].name == "Neymar Jr"
        assert players[0].overall == 92
        assert players[0].club == "Paris Saint-Germain"
        assert players[0].position == "LW"

    def test_search_by_name(self, service):
        players = service.search_players(name="Gabriel Jesus")
        assert players
        assert any(p.name == "Gabriel Jesus" for p in players)

    def test_filter_by_club_substring(self, service):
        # Given the spec says "Filter FIFA data by Club containing ..."
        # When I search clubs containing "Santos"
        players = service.search_players(club="Santos", limit=100)
        # Then both Santos (20) and Santos Laguna (26) match the substring
        assert len(players) == 46
        assert all("santos" in p.club.lower() for p in players)

    def test_position_group_filter(self, service):
        # Given 'Show me all forwards from Santos'
        # When I filter by the forward position group
        players = service.search_players(club="Santos", position="forward", limit=100)
        assert players
        assert all(p.position in {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"} for p in players)

    def test_exact_position_code_filter(self, service):
        players = service.search_players(club="Santos", position="ST", limit=100)
        assert players
        assert all(p.position == "ST" for p in players)

    def test_min_overall_filter(self, service):
        players = service.search_players(nationality="Brazil", min_overall=90)
        assert [p.name for p in players] == ["Neymar Jr"]

    def test_max_age_filter(self, service):
        players = service.search_players(
            nationality="Brazil", max_age=20, order="overall", limit=100
        )
        assert players
        assert all(p.age <= 20 for p in players)

    def test_invalid_position_rejected(self, service):
        with pytest.raises(ValueError):
            service.search_players(position="quarterback")


class TestPlayerProfile:
    """Scenario: 'Who is Gabriel Barbosa?' / 'How good is Neymar?'."""

    def test_profile_exact_match(self, service):
        profile = service.player_profile("Neymar")
        assert profile.name == "Neymar Jr"
        assert profile.overall == 92
        assert profile.potential == 93
        # And skills were parsed into attributes
        assert profile.attrs["Dribbling"] == 96

    def test_profile_fuzzy_match(self, service):
        # Given a partial name
        profile = service.player_profile("Casemiro")
        assert profile.club == "Real Madrid"
        assert profile.position == "CDM"

    def test_profile_missing_player_is_graceful(self, service):
        # Given 'Gabriel Barbosa' is absent from this FIFA snapshot
        # When I look him up
        # Then a helpful error (not a crash) is raised
        with pytest.raises(LookupError):
            service.player_profile("Gabriel Barbosa")

    def test_metric_conversions(self, service):
        profile = service.player_profile("Neymar")
        # Height 5'9" and weight 150lbs from the raw row
        assert profile.height_cm == 175
        assert profile.weight_kg == 68


class TestClubSquad:
    """Scenario: 'Which players play for Flamengo?' (cross-file bridge)."""

    def test_squad_for_fifa_club(self, service):
        squad = service.club_squad("Santos")
        assert squad.in_fifa
        assert len(squad.players) == 20

    def test_squad_via_match_team_name(self, service):
        # Given the club is usually written 'Grêmio' in match data
        # When I bridge to the FIFA squad
        squad = service.club_squad("Grêmio")
        assert squad.in_fifa
        assert len(squad.players) == 20

    def test_club_not_in_fifa_snapshot(self, service):
        # Given Flamengo is not in the FIFA 19 snapshot (licensing)
        # When I request its squad
        squad = service.club_squad("Flamengo")
        # Then the result says so instead of crashing
        assert squad.in_fifa is False
        assert squad.players == []

    def test_squad_sorted_by_rating(self, service):
        squad = service.club_squad("Atlético Mineiro")
        ratings = [p.overall for p in squad.players]
        assert ratings == sorted(ratings, reverse=True)


class TestBraziliansAtBrazilianClubs:
    """Scenario: TASK.md's 'Brazilian players at Brazilian clubs' example."""

    def test_grouping(self, service):
        rows = service.brazilians_at_brazilian_clubs()
        # Then every FIFA-covered Brazilian club reports 20 players
        assert len(rows) >= 10
        clubs = {club for club, _, _ in rows}
        assert "Atlético Mineiro" in clubs
        assert "Grêmio" in clubs
        for club, count, avg in rows:
            assert count == 20
            assert 60 <= avg <= 85

    def test_formatting(self, service):
        from brazilian_soccer_mcp.formatting import format_brazilians_at_clubs

        text = format_brazilians_at_clubs(service.brazilians_at_brazilian_clubs())
        assert "Atlético Mineiro: 20 players (avg rating: 73.5)" in text


class TestFormatting:
    """Scenario: player lists render like TASK.md's example answers."""

    def test_player_line_format(self, service):
        from brazilian_soccer_mcp.formatting import format_players

        text = format_players(
            service.top_brazilian_players(3), "Top-rated Brazilian players in dataset"
        )
        # Mirrors: '1. Neymar Jr - Overall: 92, Position: LW, Club: ...'
        assert "1. Neymar Jr - Overall: 92, Position: LW" in text
        assert "2. Casemiro - Overall: 88" in text

    def test_squad_format_mentions_coverage_gap(self, service):
        from brazilian_soccer_mcp.formatting import format_squad

        squad = service.club_squad("Flamengo")
        text = format_squad(squad)
        assert "No FIFA squad data for Flamengo" in text
