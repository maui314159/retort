"""Tests for player queries (R7, R8)."""


from brazilian_soccer_mcp.normalize import text_key


class TestPlayerNameSearch:
    def test_exact_star_found(self, engine):
        result = engine.search_players(name="Neymar")
        assert result["total_players"] >= 1
        top = result["players"][0]
        assert top["name"] == "Neymar Jr"
        assert top["overall"] == 92

    def test_partial_name(self, engine):
        result = engine.search_players(name="Alisson", limit=10)
        names = [p["name"] for p in result["players"]]
        assert any("Alisson" in n for n in names)

    def test_case_and_accent_insensitive(self, engine):
        result = engine.search_players(name="neymar", limit=5)
        assert result["total_players"] >= 1

    def test_unknown_name(self, engine):
        result = engine.search_players(name="Zezinho Sem Cadastro XYZ")
        assert result["total_players"] == 0


class TestPlayerFilters:
    def test_nationality_filter(self, engine):
        result = engine.search_players(nationality="Brazil", limit=50)
        assert result["total_players"] > 100
        assert all("brazil" in text_key(p["nationality"]) for p in result["players"])

    def test_nationality_ranked_by_overall(self, engine):
        result = engine.search_players(nationality="Brazil", limit=10)
        overalls = [p["overall"] for p in result["players"]]
        assert overalls == sorted(overalls, reverse=True)
        assert overalls[0] >= 88

    def test_club_filter_with_ratings(self, engine):
        result = engine.search_players(club="Santos", limit=50)
        assert result["total_players"] > 0
        for player in result["players"]:
            assert "santos" in text_key(player["club"])
            assert isinstance(player["overall"], int)
        assert any(p["club"] == "Santos" for p in result["players"])

    def test_club_filter_fifa_spelling(self, engine):
        result = engine.search_players(club="Sport Club do Recife", limit=50)
        assert result["total_players"] == 20
        assert all(p["club"] == "Sport Club do Recife" for p in result["players"])

    def test_nationality_and_club_combined(self, engine):
        result = engine.search_players(nationality="Brazil", club="Ceará", limit=50)
        assert result["total_players"] == 20
        assert all(p["club"] == "Ceará Sporting Club" for p in result["players"])

    def test_position_filter(self, engine):
        result = engine.search_players(club="Santos", position="GK", limit=30)
        assert result["total_players"] > 0
        assert all(p["position"] == "GK" for p in result["players"])

    def test_position_category_forward(self, engine):
        result = engine.search_players(club="Santos", position_category="forward", limit=50)
        assert result["total_players"] > 0
        forwards = {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"}
        assert all(p["position"] in forwards for p in result["players"])

    def test_unknown_position_category_errors(self, engine):
        result = engine.search_players(position_category="sweeper")
        assert "error" in result

    def test_overall_range(self, engine):
        result = engine.search_players(min_overall=90, max_overall=99, limit=50)
        assert result["total_players"] > 0
        assert all(90 <= p["overall"] <= 99 for p in result["players"])

    def test_player_attributes_returned(self, engine):
        player = engine.search_players(name="Neymar")["players"][0]
        assert player["age"] is not None
        assert player["nationality"] == "Brazil"
        assert player["club"]
        assert player["position"]
        assert player["value"] or player["value_eur"]

    def test_limit(self, engine):
        result = engine.search_players(nationality="Brazil", limit=7)
        assert result["returned"] == 7
        assert result["total_players"] > 7
