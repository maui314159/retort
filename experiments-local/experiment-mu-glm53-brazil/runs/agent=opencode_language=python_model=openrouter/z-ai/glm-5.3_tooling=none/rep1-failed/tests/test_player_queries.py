"""BDD tests for player queries (spec section: "3. Player Queries").

Feature: Player Queries

  Scenario: Find players by criteria
    Given the FIFA dataset is loaded
    When I search for Brazilian players
    Then I should receive players with name, rating, position and club
"""

from __future__ import annotations


class TestSearchPlayers:
    """Scenario: Find all Brazilian players in the dataset"""

    def test_brazilian_players(self, svc):
        result = svc.search_players(nationality="Brazil", limit=5)
        assert "827 players match" in result
        for ln in result.splitlines():
            if ln.startswith("- "):
                assert "Nationality: Brazil" in ln

    def test_nationality_alias_brasil(self, svc):
        assert "827 players match" in svc.search_players(nationality="brasil", limit=1)

    def test_search_by_name_substring(self, svc):
        result = svc.search_players(name="Neymar")
        assert "Neymar Jr" in result

    def test_search_accent_insensitive(self, svc):
        plain = svc.search_players(club="Gremio", limit=3)
        accented = svc.search_players(club="Grêmio", limit=3)
        assert "20 players match" in plain
        assert plain.splitlines()[1] == accented.splitlines()[1]

    def test_position_group_filter(self, svc):
        """Spec: 'Show me all forwards ...' -> position group FWD."""
        result = svc.search_players(nationality="Brazil", position="FWD", limit=5)
        for ln in result.splitlines():
            if ln.startswith("- "):
                assert "Position: S" in ln or "Position: L" in ln or "Position: R" in ln or "Position: C" in ln

    def test_position_code_filter(self, svc):
        result = svc.search_players(position="GK", club="Grêmio", limit=5)
        assert "Position: GK" in result

    def test_rating_filters(self, svc):
        result = svc.search_players(nationality="Brazil", min_overall=85)
        names = {ln.split(" - ")[0][2:] for ln in result.splitlines() if ln.startswith("- ")}
        assert "Neymar Jr" in names
        assert all(int(_overall(ln)) >= 85 for ln in result.splitlines() if ln.startswith("- "))

    def test_no_results(self, svc):
        assert "No players match" in svc.search_players(name="Zzzz Nobody")


class TestTopPlayers:
    """Scenario: Highest-rated players"""

    def test_top_brazilians(self, svc):
        """Spec example: Neymar Jr tops the Brazilian list."""
        result = svc.top_players(nationality="Brazil", limit=5)
        assert "1. Neymar Jr - Overall: 9" in result

    def test_top_at_gremio(self, svc):
        result = svc.top_players(club="Grêmio", limit=5)
        assert "Top-rated players" in result
        overalls = [int(_overall(ln)) for ln in result.splitlines() if ln[0].isdigit()]
        assert overalls == sorted(overalls, reverse=True)

    def test_top_overall_is_messi(self, svc):
        result = svc.top_players(limit=1)
        assert "L. Messi" in result


class TestPlayerProfile:
    """Spec sample: 'Who is Gabriel Barbosa?' / 'Who is Neymar?'"""

    def test_neymar_profile(self, svc):
        result = svc.player_profile("Neymar Jr")
        assert "Neymar Jr — Player Profile" in result
        assert "Overall: 92" in result
        assert "Paris Saint-Germain" in result
        assert "Attributes:" in result

    def test_profile_suggests_close_matches(self, svc):
        result = svc.player_profile("Gabriel Barbosa")
        assert "not found" in result.lower()
        assert "Closest:" in result

    def test_profile_ambiguous_name(self, svc):
        result = svc.player_profile("Marcelo")
        assert "players match" in result

    def test_gk_attributes(self, svc):
        result = svc.player_profile("Alisson")
        assert "Goalkeeping" in result
        assert "Liverpool" in result


def _overall(line: str) -> str:
    import re

    m = re.search(r"Overall: (\d+)", line)
    assert m, line
    return m.group(1)
