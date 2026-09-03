"""BDD tests: head-to-head comparisons.

Feature: Head to Head
  Scenario: Compare two teams across all matches
    Given the match data is loaded
    When I compare "Flamengo" and "Fluminense"
    Then I should receive wins, losses, draws and goals for each side
    And the counts must sum to the number of matches
"""
from __future__ import annotations

from brsl.query_engine import QueryEngine


class TestHeadToHead:
    # Scenario: Fla-Flu head-to-head
    def test_fla_flu_head_to_head(self, engine: QueryEngine):
        h2h = engine.head_to_head("Flamengo", "Fluminense")
        assert h2h["matches"] > 0
        # Then wins+draws+losses == matches
        assert (h2h["team_a_wins"] + h2h["team_b_wins"] + h2h["draws"]
                == h2h["matches"])
        # And goals are non-negative
        assert h2h["team_a_goals"] >= 0
        assert h2h["team_b_goals"] >= 0
        # And the matches_list length matches
        assert len(h2h["matches_list"]) == h2h["matches"]

    # Scenario: head-to-head restricted to a competition
    def test_head_to_head_restricted_to_competition(self, engine: QueryEngine):
        all_h2h = engine.head_to_head("Palmeiras", "Santos")
        bras = engine.head_to_head("Palmeiras", "Santos",
                                   competition="brasileirao")
        assert bras["matches"] <= all_h2h["matches"]
        for m in bras["matches_list"]:
            assert m["competition"].startswith("Brasileirao") or \
                m["competition"] == "Serie A"

    # Scenario: symmetric counts
    def test_head_to_head_is_symmetric(self, engine: QueryEngine):
        a = engine.head_to_head("Grêmio", "Internacional")
        b = engine.head_to_head("Internacional", "Grêmio")
        assert a["matches"] == b["matches"]
        assert a["team_a_wins"] == b["team_b_wins"]
        assert a["team_b_wins"] == b["team_a_wins"]
        assert a["draws"] == b["draws"]
