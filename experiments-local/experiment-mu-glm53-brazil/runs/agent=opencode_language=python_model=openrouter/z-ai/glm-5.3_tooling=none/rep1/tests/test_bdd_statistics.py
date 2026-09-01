"""BDD scenarios: statistical analysis (spec section 5 - Statistical Analysis).

Gherkin:

Feature: Statistical Analysis
  Scenario: Average goals per match
    Given the match data is loaded
    When I request goals analysis for the Brasileirão
    Then I should receive average goals and home/away win rates
"""



class TestGoalsPerMatch:
    """Scenario: What's the average goals per match in the Brasileirão?"""

    def test_serie_a_goals_analysis(self, ask):
        result = ask("goals_analysis", competition="Série A")
        assert result["matches"] > 8000
        assert 2.2 <= result["avg_goals_per_match"] <= 2.8
        assert result["total_goals"] > 20000

    def test_home_advantage_is_real(self, ask):
        result = ask("goals_analysis", competition="Série A")
        assert result["home_win_rate"] > result["away_win_rate"]
        assert result["home_win_rate"] > 40
        assert result["avg_home_goals"] > result["avg_away_goals"]
        rates = result["home_win_rate"] + result["away_win_rate"] + result["draw_rate"]
        assert abs(rates - 100.0) < 0.5

    def test_season_scoped_analysis(self, ask):
        result = ask("goals_analysis", competition="Série A", season=2019)
        assert result["matches"] == 380
        assert 2.0 <= result["avg_goals_per_match"] <= 3.0

    def test_libertadores_analysis(self, ask):
        result = ask("goals_analysis", competition="Libertadores")
        assert result["matches"] > 1000
        assert result["avg_goals_per_match"] > 2.0


class TestBiggestWins:
    """Scenario: Show me the biggest wins in the dataset."""

    def test_biggest_wins_ranked_by_margin(self, ask):
        result = ask("biggest_wins", limit=10)
        matches = result["matches"]
        assert len(matches) == 10
        margins = [
            abs(m["home_goals"] - m["away_goals"]) for m in matches
        ]
        assert margins == sorted(margins, reverse=True)
        assert margins[0] >= 8

    def test_biggest_win_details(self, ask):
        result = ask("biggest_wins", limit=1)
        top = result["matches"][0]
        assert top["date"]
        assert top["home_team"] and top["away_team"]
        assert top["home_goals"] is not None and top["away_goals"] is not None
        assert "Biggest victories" in result["summary"]

    def test_biggest_serie_a_wins(self, ask):
        result = ask("biggest_wins", competition="Série A", limit=5)
        assert result["matches"]
        assert all(abs(m["home_goals"] - m["away_goals"]) >= 5 for m in result["matches"])


class TestBestRecords:
    """Scenario: Which team has the best away record?"""

    def test_best_away_records(self, ask):
        result = ask("best_records", venue="away", min_matches=100, limit=5)
        assert result["teams"][0]["team"] == "Palmeiras"
        ppgs = [row["ppg"] for row in result["teams"]]
        assert ppgs == sorted(ppgs, reverse=True)

    def test_best_home_records(self, ask):
        result = ask("best_records", venue="home", min_matches=100, limit=5)
        assert result["teams"]
        assert all(row["win_rate"] > 50 for row in result["teams"])

    def test_min_matches_respected(self, ask):
        result = ask("best_records", venue="away", min_matches=100, limit=50)
        assert all(row["matches"] >= 100 for row in result["teams"])

    def test_season_scoped_best_record(self, ask):
        result = ask("best_records", competition="Série A", season=2019, min_matches=30, limit=3)
        assert result["teams"][0]["team"] == "Flamengo"
        assert result["teams"][0]["points"] == 90


class TestHeadToHeadAggregates:
    """Scenario: head-to-head records across the full dataset."""

    def test_fla_flu_all_time(self, ask):
        result = ask("head_to_head", team_a="Flamengo", team_b="Fluminense")
        assert result["total"] >= 40
        a = result["team_a"]
        assert a["wins"] == 18
        assert a["draws"] == 12
        assert a["goals_for"] > a["goals_against"]

    def test_grenal_all_time(self, ask):
        result = ask("head_to_head", team_a="Grêmio", team_b="Internacional", competition="Série A")
        assert result["total"] >= 30


class TestDerbies:
    """Scenario: Show me all derbies in 2023."""

    def test_derbies_2023(self, ask):
        result = ask("derbies", season=2023)
        assert "Fla-Flu" in result["derbies"]
        assert len(result["derbies"]["Fla-Flu"]) == 4
        assert "Grenal" in result["derbies"]
        assert "Majestoso" in result["derbies"]

    def test_all_derby_matches_are_well_formed(self, ask):
        result = ask("derbies", season=2019)
        assert result["total"] > 0
        for matches in result["derbies"].values():
            for match in matches:
                assert match["date"]
                assert match["home_team"] and match["away_team"]

    def test_derbies_any_season(self, ask):
        result = ask("derbies")
        assert result["total"] > 50
