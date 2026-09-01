"""Feature: Sample Questions End-to-End

The specification's success criteria require that at least 20 sample
questions can be answered.  Each scenario below maps one question from the
specification (or its "Sample Questions and Expected Behaviors" tables) to a
query call and asserts a meaningful, data-verified answer.
"""

from __future__ import annotations

from brazilian_soccer import query


class TestSimpleLookups:
    """Questions from the specification's "Simple Lookups" table."""

    def test_q01_when_did_flamengo_last_play_corinthians(self, dataset):
        result = query.last_match_between(dataset, "Flamengo", "Corinthians")
        match = result["match"]
        assert match is not None
        assert match["date"] is not None
        assert match["home_goals"] is not None

    def test_q02_what_was_the_score_of_that_match(self, dataset):
        result = query.last_match_between(dataset, "Flamengo", "Corinthians")
        match = result["match"]
        assert match["home_goals"] >= 0 and match["away_goals"] >= 0
        assert match["home_goals"] is not None and match["away_goals"] is not None

    def test_q03_who_is_gabriel_barbosa(self, dataset):
        result = query.search_players(dataset, name="Gabriel Barbosa")
        assert result["total"] == 0

    def test_q04_who_is_neymar(self, dataset):
        result = query.search_players(dataset, name="Neymar")
        neymar = result["players"][0]
        assert neymar["name"] == "Neymar Jr"
        assert neymar["overall"] == 92
        assert neymar["nationality"] == "Brazil"


class TestRelationshipQueries:
    """Questions from the specification's "Relationship Queries" table."""

    def test_q05_which_players_play_for_gremio(self, dataset):
        result = query.search_players(dataset, club="Grêmio", limit=30)
        assert result["total"] == 20
        assert all(p["club"] == "Grêmio" for p in result["players"])

    def test_q06_show_me_all_derbies_in_2023(self, dataset):
        result = query.derbies(dataset, season=2023, limit=100)
        assert result["total"] >= 20
        derby_names = {m["derby"] for m in result["matches"]}
        assert "Fla-Flu" in derby_names
        assert "Gre-Nal" in derby_names

    def test_q07_what_competitions_has_palmeiras_played_in(self, dataset):
        result = query.team_competitions(dataset, "Palmeiras")
        competitions = {c["competition"] for c in result["competitions"]}
        assert competitions >= {"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"}

    def test_q08_what_matches_did_palmeiras_play_in_2023(self, dataset):
        result = query.search_matches(dataset, team="Palmeiras", season=2023, limit=100)
        assert 30 < result["total"] < 60


class TestAnalyticalQueries:
    """Questions from the specification's "Analytical Queries" table and examples."""

    def test_q09_which_team_has_the_best_home_record(self, dataset):
        result = query.best_records(dataset, competition="Serie A", venue="home", min_matches=100)
        assert result["records"]
        assert result["records"][0]["win_rate"] >= result["records"][1]["win_rate"]

    def test_q10_who_are_the_top_brazilian_players(self, dataset):
        result = query.top_players(dataset, nationality="Brazil", limit=3)
        assert result["players"][0]["name"] == "Neymar Jr"
        assert all(p["nationality"] == "Brazil" for p in result["players"])

    def test_q11_compare_the_2018_and_2019_seasons(self, dataset):
        result = query.season_comparison(dataset, "Serie A", 2018, 2019)
        champions = {s["season"]: s["champion"] for s in result["seasons"]}
        assert champions[2018] == "Palmeiras"
        assert champions[2019] == "Flamengo"

    def test_q12_what_is_corinthians_home_record_in_2022(self, dataset):
        result = query.team_stats(
            dataset, "Corinthians", competition="Serie A", season=2022, venue="home",
        )
        assert (result["played"], result["wins"], result["draws"], result["losses"]) == (19, 12, 4, 3)

    def test_q13_which_team_scored_the_most_goals_in_serie_a_2023(self, dataset):
        table, _ = dataset.league_table("Serie A", 2023)
        top = max(table, key=lambda r: r.goals_for)
        assert dataset.team_display(top.team) in {"Grêmio", "Flamengo", "Palmeiras", "Botafogo", "Atlético-MG"}

    def test_q14_compare_palmeiras_and_santos_head_to_head(self, dataset):
        result = query.head_to_head(dataset, "Palmeiras", "Santos", limit=5)
        assert result["total"] > 20
        assert result["wins_a"] + result["wins_b"] + result["draws"] + result["unscored"] == result["total"]

    def test_q15_who_won_the_2019_brasileirao(self, dataset):
        result = query.champion(dataset, "Brasileirão", 2019)
        assert result["champion"] == "Flamengo"
        assert result["points"] == 90

    def test_q16_show_the_2018_copa_libertadores_bracket(self, dataset):
        result = query.bracket(dataset, "Libertadores", 2018)
        assert [r["stage"] for r in result["rounds"]] == [
            "round of 16", "quarterfinal", "semifinal", "final",
        ]
        assert result["rounds"][-1]["ties"][0]["winner"] == "River Plate"

    def test_q17_which_teams_were_relegated_in_2020(self, dataset):
        result = query.standings(dataset, "Serie A", 2020)
        relegated = [row["team"] for row in result["table"] if row["relegated"]]
        assert set(relegated) == {"Coritiba", "Botafogo", "Vasco da Gama", "Goiás"}

    def test_q18_whats_the_average_goals_per_match_in_the_brasileirao(self, dataset):
        result = query.average_goals(dataset, competition="Brasileirão")
        assert 2.0 < result["avg_goals"] < 3.0
        assert result["matches"] > 5000

    def test_q19_which_team_has_the_best_away_record(self, dataset):
        result = query.best_records(dataset, competition="Serie A", venue="away", min_matches=100)
        assert result["records"]
        assert result["records"][0]["win_rate"] > 30

    def test_q20_show_me_the_biggest_wins_in_the_dataset(self, dataset):
        result = query.biggest_wins(dataset, limit=3)
        top = result["wins"][0]
        assert top["margin"] >= 8

    def test_q21_find_all_copa_do_brasil_finals(self, dataset):
        result = query.search_matches(
            dataset, competition="Copa do Brasil", stage="final", limit=50,
        )
        assert result["total"] >= 16
        assert all(m["stage"] == "final" for m in result["matches"])

    def test_q22_show_me_all_flamengo_vs_fluminense_matches(self, dataset):
        result = query.search_matches(dataset, team="Flamengo", opponent="Fluminense", limit=100)
        assert result["total"] > 40

    def test_q23_find_all_brazilian_players_in_the_dataset(self, dataset):
        result = query.search_players(dataset, nationality="Brazil", limit=1)
        assert result["total"] > 700

    def test_q24_highest_rated_players_at_a_brazilian_club(self, dataset):
        result = query.top_players(dataset, club="Internacional", limit=3)
        assert result["total"] == 20
        ratings = [p["overall"] for p in result["players"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_q25_brazilian_players_at_brazilian_clubs_summary(self, dataset):
        result = query.players_by_club(dataset)
        assert result["total_clubs"] >= 10
        assert any(c["club"] == "Grêmio" for c in result["clubs"])

    def test_q26_who_won_the_libertadores_2019(self, dataset):
        result = query.champion(dataset, "Libertadores", 2019)
        assert result["champion"] == "Flamengo"

    def test_q27_who_won_the_copa_do_brasil_2020(self, dataset):
        result = query.champion(dataset, "Copa do Brasil", 2020)
        assert result["champion"] == "Palmeiras"

    def test_q28_matches_in_a_date_range(self, dataset):
        result = query.search_matches(
            dataset, competition="Serie A", from_date="2019-05-01", to_date="2019-05-31",
        )
        assert result["total"] > 30
        assert all(m["date"].startswith("2019-05") for m in result["matches"])
