"""BDD scenarios: player queries (spec section 3 - Player Queries).

Gherkin:

Feature: Player Queries
  Scenario: Search players by name
    Given the FIFA player data is loaded
    When I search for a player named "Alisson"
    Then I should receive his club, position and rating
"""



class TestSearchByName:
    """Scenario: Who is Gabriel Barbosa? / simple name lookups."""

    def test_who_is_alisson(self, ask):
        result = ask("search_players", name="Alisson")
        alisson = result["players"][0]
        assert alisson["name"] == "Alisson"
        assert alisson["club"] == "Liverpool"
        assert alisson["position"] == "GK"
        assert alisson["nationality"] == "Brazil"
        assert alisson["overall"] == 85

    def test_neymar_is_highest_rated_brazilian(self, ask):
        result = ask("search_players", nationality="Brazil", limit=1)
        top = result["players"][0]
        assert top["name"] == "Neymar Jr"
        assert top["overall"] == 92
        assert top["position"] == "LW"
        assert top["club"] == "Paris Saint-Germain"

    def test_missing_player_handled_gracefully(self, ask):
        result = ask("search_players", name="Gabriel Barbosa")
        assert result["total"] == 0
        assert "No players found" in result["summary"]


class TestBrazilianPlayers:
    """Scenario: Find all Brazilian players in the dataset."""

    def test_brazilian_player_count(self, ask):
        result = ask("search_players", nationality="Brazil", limit=1)
        assert result["total"] == 827

    def test_top_brazilian_players_format(self, ask):
        result = ask("search_players", nationality="Brazil", min_overall=86)
        assert "Neymar Jr - Overall: 92" in result["summary"]
        overalls = [p["overall"] for p in result["players"]]
        assert overalls == sorted(overalls, reverse=True)

    def test_nationality_filter_is_exact(self, ask):
        result = ask("search_players", nationality="Brazil", limit=200)
        assert all(p["nationality"] == "Brazil" for p in result["players"])


class TestClubQueries:
    """Scenario: Which players play for Flamengo? (cross-file query)."""

    def test_santos_squad_has_20_players(self, ask):
        result = ask("search_players", club="Santos")
        assert result["total"] == 20
        assert all(p["club"] == "Santos" for p in result["players"])

    def test_santos_does_not_match_santos_laguna(self, ask):
        """'Santos' must not drag in the Mexican club Santos Laguna."""
        result = ask("search_players", club="Santos")
        assert all(p["club"] != "Santos Laguna" for p in result["players"])
        laguna = ask("search_players", club="Santos Laguna")
        assert laguna["total"] > 0
        assert all(p["club"] == "Santos Laguna" for p in laguna["players"])

    def test_club_accepts_team_name_variants(self, ask):
        for variant in ("Athletico-PR", "Atlético Paranaense", "Athletico Paranaense", "atletico-pr"):
            result = ask("search_players", club=variant)
            assert result["total"] == 20, f"variant {variant!r} should find the squad"

    def test_flamengo_missing_from_fifa_gets_helpful_note(self, ask):
        result = ask("team_players", team="Flamengo")
        assert result["total"] == 0
        assert "No FIFA squad found" in result["summary"]
        assert "Grêmio" in result["summary"], "should list available Brazilian clubs"

    def test_brazilian_clubs_with_squads(self, loaded_store):
        clubs = loaded_store.brazilian_clubs_with_squads()
        names = {c["club"] for c in clubs}
        assert "Grêmio" in names
        assert "Santos" in names
        assert "Fluminense" in names
        assert "Boavista" not in names, "Portuguese Boavista must not appear as Brazilian"
        assert "Club América" not in names, "Mexican Club América must not appear as Brazilian"
        assert all(c["players"] > 0 for c in clubs)


class TestPositionQueries:
    """Scenario: Show me all forwards from a club."""

    def test_forwards_from_gremio(self, ask):
        result = ask("search_players", club="Grêmio", position="forward")
        assert result["total"] > 0
        forward_codes = {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"}
        assert all(p["position"] in forward_codes for p in result["players"])

    def test_position_group_names(self, ask):
        result = ask("search_players", nationality="Brazil", position="goalkeeper", limit=5)
        assert all(p["position"] == "GK" for p in result["players"])
        result = ask("search_players", nationality="Brazil", position="GK", limit=5)
        assert all(p["position"] == "GK" for p in result["players"])

    def test_position_code_filter(self, ask):
        result = ask("search_players", nationality="Brazil", position="ST", limit=10)
        assert all(p["position"] == "ST" for p in result["players"])


class TestRatingFilters:
    """Scenario: highest-rated players and rating filters."""

    def test_min_overall_filter(self, ask):
        result = ask("search_players", min_overall=90)
        assert result["total"] >= 5
        assert all(p["overall"] >= 90 for p in result["players"])

    def test_max_age_filter(self, ask):
        result = ask("search_players", nationality="Brazil", max_age=21, limit=30)
        assert all(p["age"] <= 21 for p in result["players"])

    def test_ordering_by_overall_descending(self, ask):
        result = ask("search_players", nationality="Brazil", limit=50)
        overalls = [p["overall"] for p in result["players"]]
        assert overalls == sorted(overalls, reverse=True)
