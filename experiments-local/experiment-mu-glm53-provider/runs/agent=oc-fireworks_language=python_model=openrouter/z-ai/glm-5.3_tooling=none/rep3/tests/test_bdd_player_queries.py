"""Feature: Player Queries (BDD)

Spec scenarios:

    Scenario: Search players by name
      Given the FIFA player database is loaded
      When I search for "Gabriel Barbosa"
      Then I should receive the closest matching players

    Scenario: Filter Brazilian players by rating
      When I search for Brazilian players
      Then the highest-rated players come first (Neymar Jr, 92)

    Scenario: Find players at a Brazilian club
      When I search for players at "Atlético Mineiro" (any spelling)
      Then the FIFA club spelling is joined to the match-data team
"""

from __future__ import annotations

import pytest

from brsoccer import queries as q

pytestmark = pytest.mark.bdd


class TestSearchPlayersByName:
    """Scenario: Who is Gabriel Barbosa? / Who is Neymar?"""

    def test_gabriel_barbosa_finds_gabriel_candidates(self, sd):
        # Given the FIFA player database is loaded
        # When I search for "Gabriel Barbosa" (not in this snapshot)
        players = q.search_players(sd, name="Gabriel Barbosa", limit=10)
        # Then the closest matching players are returned
        names = [p.name for p in players]
        assert "Gabriel Jesus" in names
        assert any("Barbosa" in n for n in names)  # e.g. "M. Barbosa" (GK, Villarreal)
        # And every hit matches on Gabriel or Barbosa (accent-insensitive:
        # "Gabrìel" is a distinct accented player name)
        from brsoccer.normalize import strip_accents

        assert all("Gabriel" in strip_accents(n) or "Barbosa" in n for n in names)

    def test_neymar_exact(self, sd):
        # When I search for "Neymar"
        players = q.search_players(sd, name="Neymar")
        # Then exactly one player matches: Neymar Jr, 92, LW, PSG
        assert len(players) == 1
        neymar = players[0]
        assert neymar.overall == 92
        assert neymar.position == "LW"
        assert neymar.club == "Paris Saint-Germain"
        assert neymar.nationality == "Brazil"

    def test_at_least_one_filter_required(self, sd):
        # When I search with no filters at all
        # Then a friendly error asks for at least one filter
        with pytest.raises(q.QueryError, match="at least one filter"):
            q.search_players(sd)


class TestSearchPlayersByNationality:
    """Scenario: Find all Brazilian players in the dataset."""

    def test_brazilian_players_count(self, sd):
        # When I search for all Brazilian players
        players = q.search_players(sd, nationality="Brazil", limit=None)
        # Then the dataset holds 827 of them, sorted by rating
        assert len(players) == 827
        ratings = [p.overall for p in players]
        assert ratings == sorted(ratings, reverse=True)

    def test_top_brazilian_players(self, sd):
        # When I ask for the top Brazilians
        players = q.search_players(sd, nationality="Brazil", min_overall=88)
        # Then Neymar Jr (92) leads the list
        assert players[0].name == "Neymar Jr"
        assert players[0].overall == 92
        names = {p.name for p in players}
        assert {"Casemiro", "Coutinho", "Marcelo", "Thiago Silva"} <= names

    def test_nationality_is_accent_insensitive(self, sd):
        # When I search for players from "Brasil" or "Brazil"
        a = q.search_players(sd, nationality="Brazil", limit=None)
        b = q.search_players(sd, nationality="Brasil", limit=None)
        # Then both resolve to the same set
        assert len(a) == len(b) == 827


class TestSearchPlayersByClub:
    """Scenario: Which players play for <club>? (cross-file join)."""

    def test_atletico_mineiro_join(self, sd):
        # When I search for players at "Atlético Mineiro"
        players = q.search_players(sd, club="Atlético Mineiro")
        # Then the FIFA spelling joins to the match-data team (20 players)
        assert len(players) == 20
        assert all(p.club == "Atlético Mineiro" for p in players)
        # And the best player is rated 83
        assert players[0].overall == 83

    def test_atletico_mg_variant_is_the_same_club(self, sd):
        # When I search with the Brasileirão spelling "Atletico-MG"
        by_variant = q.search_players(sd, club="Atletico-MG")
        by_full_name = q.search_players(sd, club="Atlético Mineiro")
        # Then both spellings find the same squad
        assert {p.fifa_id for p in by_variant} == {p.fifa_id for p in by_full_name}

    def test_gremio_top_players(self, sd):
        # When I ask for the highest-rated players at Grêmio
        players = q.search_players(sd, club="Grêmio")
        # Then 20 players are found, best rated 83
        assert len(players) == 20
        assert players[0].overall == 83

    def test_santos_does_not_match_santos_laguna(self, sd):
        # When I search for players at "Santos" (the Brazilian club)
        players = q.search_players(sd, club="Santos")
        # Then every hit is the Brazilian Santos, not Santos Laguna
        assert players
        assert all(p.club == "Santos" for p in players)

    def test_flamengo_honestly_absent_from_fifa_snapshot(self, sd):
        # Given the FIFA snapshot omits Flamengo's squad
        # When I search for players at Flamengo
        players = q.search_players(sd, club="Flamengo")
        # Then no players are found (an honest empty answer)
        assert players == []


class TestSearchPlayersByPosition:
    """Scenario: Show me all forwards from <club>."""

    def test_forwards_at_santos(self, sd):
        # When I search for strikers (ST) at Santos
        players = q.search_players(sd, club="Santos", position="ST")
        # Then only Santos strikers are returned
        assert players
        assert all(p.position == "ST" and p.club == "Santos" for p in players)

    def test_position_filter_narrows_results(self, sd):
        # When I compare all Brazilian goalkeepers with all Brazilians
        gks = q.search_players(sd, nationality="Brazil", position="GK", limit=None)
        all_br = q.search_players(sd, nationality="Brazil", limit=None)
        # Then the position filter returns a strict subset
        assert 0 < len(gks) < len(all_br)
        assert all(p.position == "GK" for p in gks)


class TestClubOverview:
    """Scenario: Brazilian players at Brazilian clubs (per-club breakdown)."""

    def test_club_overview_groups(self, sd):
        # When I request the Brazilian-players-per-club overview
        groups = q.club_overview(sd, nationality="Brazil")
        # Then 16 Brazilian clubs have squads in the snapshot
        assert len(groups) == 16
        # And the main clubs each list 20 players in this snapshot
        main_clubs = [g for g in groups if g["count"] == 20]
        assert len(main_clubs) >= 15
        # And Atlético-MG tops the list on average rating
        assert groups[0]["display"] == "Atlético-MG"
        assert groups[0]["count"] == 20
        assert groups[0]["avg_overall"] == pytest.approx(73, abs=1.0)

    def test_club_overview_skips_foreign_clubs(self, sd):
        # When I request the overview
        groups = q.club_overview(sd)
        # Then no foreign club appears (only teams from the match data)
        for group in groups:
            assert sd.is_brazilian_team(group["key"])
