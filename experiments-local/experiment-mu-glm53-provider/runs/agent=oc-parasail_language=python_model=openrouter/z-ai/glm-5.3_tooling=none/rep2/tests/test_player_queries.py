"""GWT tests for player queries against the FIFA dataset."""

from __future__ import annotations


class TestSearchPlayers:
    def test_given_name_query_when_searched_then_substring_matches(self, engine):
        result = engine.search_players(name="Casemiro")
        assert result["total_players"] == 1
        player = result["players"][0]
        assert player["nationality"] == "Brazil"
        assert player["position"] == "CDM"

    def test_given_nationality_when_searched_then_only_that_nationality(self, engine):
        result = engine.search_players(nationality="Brazil", limit=500)
        assert result["total_players"] > 500
        for player in result["players"]:
            assert player["nationality"] == "Brazil"

    def test_given_brazilian_club_when_searched_then_registry_match(self, engine):
        # FIFA club strings map to the curated registry (e.g. "Atlético Mineiro")
        result = engine.search_players(club="Atlético Mineiro", limit=100)
        assert result["total_players"] > 0
        for player in result["players"]:
            assert player["club"] == "Atlético Mineiro"

    def test_given_foreign_club_when_searched_then_raw_string_match(self, engine):
        result = engine.search_players(club="Liverpool", limit=50)
        assert result["total_players"] > 0
        for player in result["players"]:
            assert player["club"] == "Liverpool"

    def test_given_position_filter_when_searched_then_position_respected(self, engine):
        result = engine.search_players(nationality="Brazil", position="ST", limit=100)
        assert result["total_players"] > 0
        for player in result["players"]:
            assert player["position"] == "ST"

    def test_given_rating_threshold_when_searched_then_minimum_respected(self, engine):
        result = engine.search_players(min_overall=90, limit=100)
        for player in result["players"]:
            assert player["overall"] >= 90

    def test_given_combined_filters_when_searched_then_all_applied(self, engine):
        result = engine.search_players(
            nationality="Brazil", club="Santos", min_overall=70, limit=100
        )
        assert result["total_players"] > 0
        for player in result["players"]:
            assert player["nationality"] == "Brazil"
            assert player["club"] == "Santos"
            assert player["overall"] >= 70


class TestTopPlayers:
    def test_given_brazilian_players_when_ranked_then_neymar_leads(self, engine):
        result = engine.top_players(nationality="Brazil", limit=10)
        assert result["players"][0]["name"] == "Neymar Jr"
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_given_club_scope_when_ranked_then_only_that_club(self, engine):
        result = engine.top_players(club="Cruzeiro", limit=10)
        assert result["players"]
        for player in result["players"]:
            assert player["club"] == "Cruzeiro"


class TestPlayersAtBrazilianClubs:
    def test_given_brazilian_clubs_when_summarized_then_fifa_clubs_listed(self, engine):
        result = engine.players_at_brazilian_clubs()
        club_names = [row["club"] for row in result["clubs"]]
        for expected in ("Grêmio", "Santos", "Cruzeiro", "Bahia"):
            assert expected in " ".join(club_names) or any(expected in n for n in club_names)
        for row in result["clubs"]:
            assert row["players"] > 0
            assert 50 <= row["average_rating"] <= 90

    def test_given_fifa19_licensing_when_summarized_then_limitation_noted(self, engine):
        result = engine.players_at_brazilian_clubs()
        assert "FIFA 19" in result["summary"]


class TestPlayerData:
    def test_given_fifa_file_when_loaded_then_expected_totals(self, engine):
        assert len(engine.players) == 18207
        brazilians = [p for p in engine.players if p.nationality == "Brazil"]
        assert len(brazilians) == 827

    def test_given_free_agents_when_loaded_then_club_is_none(self, engine):
        free_agents = [p for p in engine.players if p.club is None]
        assert len(free_agents) == 241

    def test_given_player_records_when_serialized_then_fields_present(self, engine):
        neymar = next(p for p in engine.players if p.name == "Neymar Jr")
        data = neymar.as_dict()
        assert data["overall"] == 92
        assert data["position"] == "LW"
        assert data["value_eur"] == 118_500_000
