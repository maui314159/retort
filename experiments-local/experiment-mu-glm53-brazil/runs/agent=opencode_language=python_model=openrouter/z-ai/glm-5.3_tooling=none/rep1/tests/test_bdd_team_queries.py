"""BDD scenarios: team queries (spec section 2 - Team Queries).

Gherkin:

Feature: Team Queries
  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
"""



class TestTeamStatistics:
    """Scenario: Get team statistics for one season."""

    def test_palmeiras_2023_statistics(self, ask):
        result = ask("team_stats", team="Palmeiras", season=2023, competition="Série A")
        overall = result["overall"]
        assert overall["matches"] == 37
        assert overall["wins"] == 19
        assert overall["draws"] == 10
        assert overall["losses"] == 8
        assert overall["goals_for"] == 61
        assert overall["goals_against"] == 32

    def test_wins_draws_losses_sum_to_matches(self, ask):
        for team in ("Palmeiras", "Flamengo", "Santos", "Corinthians"):
            result = ask("team_stats", team=team, season=2019, competition="Série A")
            record = result["overall"]
            assert record["wins"] + record["draws"] + record["losses"] == record["matches"]
            assert record["matches"] == 38

    def test_home_plus_away_equals_overall(self, ask):
        result = ask("team_stats", team="Flamengo", season=2019, competition="Série A")
        assert result["home"]["matches"] + result["away"]["matches"] == result["overall"]["matches"]
        assert result["home"]["goals_for"] + result["away"]["goals_for"] == result["overall"]["goals_for"]

    def test_statistics_include_competition_breakdown(self, ask):
        result = ask("team_stats", team="Flamengo", season=2019)
        competitions = {row["competition"] for row in result["by_competition"]}
        assert "Brasileirão Série A" in competitions
        assert "Copa Libertadores" in competitions


class TestHomeRecord:
    """Scenario: What is Corinthians' home record in 2022?"""

    def test_corinthians_home_record_2022(self, ask):
        result = ask("team_stats", team="Corinthians", season=2022, competition="Série A")
        home = result["home"]
        assert home["matches"] == 19
        assert home["wins"] + home["draws"] + home["losses"] == 19
        assert "Corinthians" in result["summary"]
        assert "Home:" in result["summary"]


class TestTopScoringTeams:
    """Scenario: Which team scored the most goals in Serie A 2023?"""

    def test_most_goals_in_serie_a_2023(self, loaded_store):
        records = loaded_store.best_records(competition="Série A", season=2023, min_matches=30)
        by_goals = sorted(records, key=lambda r: -r["goals_for"])
        top = by_goals[0]
        assert top["team"] in ("Palmeiras", "Flamengo", "Botafogo-RJ", "Grêmio", "Atlético-MG")
        assert top["goals_for"] >= 60

    def test_serie_a_2019_top_scorer_is_flamengo(self, loaded_store):
        records = loaded_store.best_records(competition="Série A", season=2019, min_matches=30)
        by_goals = sorted(records, key=lambda r: -r["goals_for"])
        assert by_goals[0]["team"] == "Flamengo"
        assert by_goals[0]["goals_for"] == 86


class TestHeadToHeadComparison:
    """Scenario: Compare Palmeiras and Santos head-to-head."""

    def test_palmeiras_vs_santos(self, ask):
        result = ask("head_to_head", team_a="Palmeiras", team_b="Santos", competition="Série A")
        assert result["total"] >= 30
        a, b = result["team_a"], result["team_b"]
        assert a["wins"] + b["wins"] + a["draws"] == a["matches"]
        assert a["matches"] == b["matches"]
        assert "Head-to-head in dataset" in result["summary"]

    def test_compare_teams_tool(self, ask):
        result = ask("compare_teams", team_a="Palmeiras", team_b="Santos")
        assert result["team_a"]["team"] == "Palmeiras"
        assert result["team_b"]["team"] == "Santos"
        assert result["head_to_head"]["total"] > 0
        assert "Head-to-head" in result["summary"]
        assert "Most recent meeting" in result["summary"]


class TestSeasonHistory:
    """Scenario: team performance trends across seasons."""

    def test_flamengo_season_history(self, ask):
        result = ask("team_season_history", team="Flamengo")
        seasons = [row["season"] for row in result["seasons"]]
        assert 2019 in seasons
        assert 2022 in seasons
        assert seasons == sorted(seasons, reverse=True)

    def test_history_contains_2019_title_season(self, ask):
        result = ask("team_season_history", team="Flamengo")
        row_2019 = next(r for r in result["seasons"] if r["season"] == 2019)
        assert row_2019["points"] >= 90


class TestFindTeam:
    """Scenario: resolve a team and describe what the datasets know."""

    def test_find_team_full_official_name(self, ask):
        result = ask("find_team", name="Sport Club Corinthians Paulista")
        assert result["team"] == "Corinthians"
        assert result["total_matches"] > 500
        assert "Brasileirão Série A" in result["competitions"]

    def test_find_team_reports_championships(self, ask):
        result = ask("find_team", name="Flamengo")
        assert "2019 Brasileirão Série A" in result.get("titles", [])

    def test_find_team_cross_file_squad_info(self, ask):
        result = ask("find_team", name="Grêmio")
        assert result["squad_size"] == 20
        assert "FIFA squad" in result["summary"]
