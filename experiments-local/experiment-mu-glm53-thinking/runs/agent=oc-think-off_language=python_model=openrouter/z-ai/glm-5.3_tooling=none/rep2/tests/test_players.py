"""BDD scenarios for player queries (FIFA dataset)."""

import soccer.queries as q


class TestSearchPlayers:
    def test_search_by_name(self, data):
        """Scenario: who is Neymar? Search FIFA data by name."""
        r = q.search_players(data, name="Neymar")
        assert r["total"] >= 1
        assert any(p["name"] == "Neymar Jr" for p in r["players"])
        top = r["players"][0]
        assert top["overall"] >= 90

    def test_top_brazilian_players(self, data):
        """Scenario: who are the top Brazilian players?"""
        r = q.search_players(data, nationality="Brazil", limit=10)
        assert r["total"] > 500
        overalls = [p["overall"] for p in r["players"]]
        assert overalls == sorted(overalls, reverse=True)
        assert all(p["nationality"] == "Brazil" for p in r["players"])
        assert overalls[0] >= 88  # Neymar Jr

    def test_players_at_a_club(self, data):
        """Scenario: which players play for a Brazilian club?"""
        r = q.search_players(data, club="Grêmio")
        assert r["total"] >= 15
        for p in r["players"]:
            assert "gremio" in (p["club"] or "").lower() or p["club"] == "Grêmio"

    def test_filter_by_position(self, data):
        forwards = q.search_players(data, nationality="Brazil", position="forward", limit=10)
        assert forwards["total"] > 50
        gks = q.search_players(data, nationality="Brazil", position="goalkeeper", limit=10)
        assert all(p["position"] == "GK" for p in gks["players"])

    def test_filter_by_position_code(self, data):
        st = q.search_players(data, nationality="Brazil", position="ST", limit=5)
        assert all(p["position"] == "ST" for p in st["players"])

    def test_min_overall_filter(self, data):
        r = q.search_players(data, nationality="Brazil", min_overall=85)
        assert r["total"] < 30
        assert all(p["overall"] >= 85 for p in r["players"])


class TestBrazilianPlayersByClub:
    def test_grouping_by_club(self, data):
        """Brazilian players at Brazilian clubs, grouped with counts."""
        r = q.brazilian_players_by_club(data)
        clubs = r["clubs"]
        assert len(clubs) > 5
        for club in clubs:
            assert club["players"] > 0
            assert club["avg_overall"] > 50

    def test_cross_file_query(self, data):
        """Clubs in the summary must be teams that appear in match data."""
        from soccer.loader import normalize_name

        r = q.brazilian_players_by_club(data)
        match_teams = {m.home for m in data.matches} | {m.away for m in data.matches}
        for club in r["clubs"]:
            assert normalize_name(club["club"]) in match_teams
