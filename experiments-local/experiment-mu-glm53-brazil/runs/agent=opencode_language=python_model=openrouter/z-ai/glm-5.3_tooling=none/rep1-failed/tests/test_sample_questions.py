"""End-to-end answers for the spec's sample questions.

Feature: Sample questions
  Scenario Outline: Answering the spec's documented questions
    Given the knowledge base is loaded
    When the corresponding query is issued
    Then a coherent, non-empty answer is produced

Success criterion from TASK.md: "At least 20 sample questions can be
answered" - each test below is one question from the spec's tables and
example sections.
"""

from __future__ import annotations

import pytest


class TestSimpleLookups:
    """Spec table: Simple Lookups"""

    def test_q01_when_did_flamengo_last_play_corinthians(self, svc):
        """When did Flamengo last play Corinthians?"""
        result = svc.search_matches(team="Flamengo", opponent="Corinthians", limit=1)
        lines = [ln for ln in result.splitlines() if ln.startswith("- ")]
        assert lines and lines[0][2:12].count("-") == 2
        assert "Head-to-head" in result

    def test_q02_what_was_the_score(self, svc):
        """What was the score? (follow-up on the match above)"""
        result = svc.search_matches(team="Flamengo", opponent="Corinthians", limit=1)
        line = next(ln for ln in result.splitlines() if ln.startswith("- "))
        score = line.split(": ")[1]
        assert any(ch.isdigit() for ch in score) or "score unknown" in score

    def test_q03_who_is_gabriel_barbosa(self, svc):
        """Who is Gabriel Barbosa? (not in this FIFA dataset - must say so helpfully)"""
        result = svc.player_profile("Gabriel Barbosa")
        assert "not found" in result.lower()
        assert "Closest:" in result  # suggests similar names

    def test_q04_who_is_neymar(self, svc):
        result = svc.player_profile("Neymar Jr")
        assert "Overall: 92" in result
        assert "Paris Saint-Germain" in result


class TestRelationshipQueries:
    """Spec table: Relationship Queries"""

    def test_q05_which_players_play_for_gremio(self, svc):
        """Which players play for Grêmio? (Flamengo has no squad in this
        FIFA dataset; Grêmio is the spec-style equivalent that does.)"""
        result = svc.search_players(club="Grêmio", limit=10)
        assert "20 players match" in result
        assert "Grêmio" in result

    def test_q06_show_me_all_derbies_in_2019(self, svc):
        result = svc.derbies(season=2019)
        for derby in ("Fla-Flu", "Derby Paulista", "Gre-Nal", "Ba-Vi", "Atletiba"):
            assert derby in result

    def test_q07_what_competitions_has_palmeiras_played_in(self, svc):
        result = svc.team_profile("Palmeiras")
        for comp in ("Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"):
            assert comp in result

    def test_q08_flamengo_vs_fluminense_all_matches(self, svc):
        result = svc.search_matches(team="Flamengo", opponent="Fluminense", limit=5)
        assert "matches in dataset" in result
        assert "Head-to-head" in result

    def test_q09_palmeiras_matches_in_2023(self, svc):
        result = svc.search_matches(team="Palmeiras", season=2023, limit=3)
        assert "37 matches" in result


class TestAnalyticalQueries:
    """Spec table: Analytical Queries + example sections"""

    def test_q10_which_team_has_the_best_home_record(self, svc):
        result = svc.stats(competition="Brasileirão Série A")
        assert "Best home records" in result
        assert "%" in result

    def test_q11_who_are_the_top_brazilian_players(self, svc):
        result = svc.top_players(nationality="Brazil", limit=5)
        assert "1. Neymar Jr" in result

    def test_q12_corinthians_home_record_2022(self, svc):
        result = svc.team_stats(
            team="Corinthians", competition="Brasileirão Série A", season=2022, venue="home"
        )
        assert "Matches: 19" in result
        assert "Win rate:" in result

    def test_q13_which_team_scored_most_goals_serie_a_2019(self, svc):
        result = svc.stats(competition="Brasileirão Série A", season=2019)
        assert "Top scoring teams: Flamengo (86)" in result

    def test_q14_compare_palmeiras_and_santos(self, svc):
        result = svc.head_to_head("Palmeiras", "Santos")
        assert "Head-to-head in dataset" in result
        assert "Goals:" in result

    def test_q15_who_won_the_2019_brasileirao(self, svc):
        result = svc.standings("Brasileirão Série A", 2019)
        assert "1. Flamengo - 90 pts (28W, 6D, 4L)" in result
        assert "Champion" in result

    def test_q16_2018_libertadores_final(self, svc):
        """Show the 2018 Copa Libertadores final (bracket climax)."""
        result = svc.finals(competition="Libertadores", season=2018)
        assert "Boca Juniors" in result and "River Plate" in result
        assert "River Plate wins" in result

    def test_q17_which_teams_were_relegated_in_2020(self, svc):
        result = svc.standings("Brasileirão Série A", 2020)
        relegated_line = result.split("Relegated (bottom 4): ")[1].split("\n")[0]
        for club in ("Coritiba", "Vasco da Gama"):
            assert club in relegated_line

    def test_q18_average_goals_per_match_brasileirao(self, svc):
        result = svc.stats(competition="Brasileirão Série A")
        assert "Average goals per match: 2." in result

    def test_q19_which_team_has_the_best_away_record(self, svc):
        result = svc.stats(competition="Brasileirão Série A")
        assert "Best away records" in result

    def test_q20_biggest_wins_in_dataset(self, svc):
        result = svc.biggest_wins(limit=5)
        assert "8-0" in result  # Santos 8-0 Bolívar, 2012 Libertadores

    def test_q21_find_all_copa_do_brasil_finals(self, svc):
        result = svc.finals(competition="Copa do Brasil")
        assert "2013" in result and "2020" in result
        assert "Aggregate" in result

    def test_q22_all_brazilian_forwards(self, svc):
        """Spec: 'Show me all forwards from São Paulo FC' - São Paulo FC
        has no squad in this FIFA snapshot, so query Brazilian forwards."""
        result = svc.search_players(nationality="Brazil", position="FWD", min_overall=80, limit=10)
        assert "players match" in result

    def test_q23_highest_rated_players_at_gremio(self, svc):
        result = svc.top_players(club="Grêmio", limit=3)
        assert "Top-rated players" in result

    def test_q24_what_do_you_know_about_atletico_mg(self, svc):
        result = svc.team_profile("Atlético-MG")
        assert "Atlético-MG — Team Profile" in result
        assert "Brasileirão Série A 2021" in result  # 2021 title

    def test_q25_matches_on_a_specific_date(self, svc):
        """The BR-Football example row: São Paulo 1-1 Flamengo, 2023-09-24."""
        result = svc.search_matches(date_from="2023-09-24", date_to="2023-09-24", limit=10)
        assert "São Paulo 1-1 Flamengo" in result

    def test_q26_away_record_of_flamengo_2019(self, svc):
        result = svc.team_stats(
            team="Flamengo", competition="Brasileirão Série A", season=2019, venue="away"
        )
        assert "Matches: 19" in result
        assert "away record" in result


class TestQuestionCoverage:
    """The spec's success criterion: at least 20 sample questions answerable."""

    def test_at_least_20_questions_answered(self, svc):
        answers = [
            svc.search_matches(team="Flamengo", opponent="Corinthians", limit=1),
            svc.player_profile("Neymar Jr"),
            svc.search_players(club="Grêmio", limit=3),
            svc.derbies(season=2019),
            svc.team_profile("Palmeiras"),
            svc.search_matches(team="Flamengo", opponent="Fluminense", limit=3),
            svc.search_matches(team="Palmeiras", season=2023, limit=3),
            svc.stats(competition="Brasileirão Série A"),
            svc.top_players(nationality="Brazil", limit=3),
            svc.team_stats(team="Corinthians", competition="Brasileirão Série A", season=2022, venue="home"),
            svc.stats(competition="Brasileirão Série A", season=2019),
            svc.head_to_head("Palmeiras", "Santos"),
            svc.standings("Brasileirão Série A", 2019),
            svc.finals(competition="Libertadores", season=2018),
            svc.standings("Brasileirão Série A", 2020),
            svc.stats(competition="Brasileirão Série A"),
            svc.biggest_wins(limit=3),
            svc.finals(competition="Copa do Brasil"),
            svc.search_players(nationality="Brazil", position="FWD", min_overall=80, limit=5),
            svc.top_players(club="Grêmio", limit=3),
            svc.team_profile("Atlético-MG"),
            svc.search_matches(date_from="2023-09-24", date_to="2023-09-24", limit=5),
        ]
        assert len(answers) >= 20
        for answer in answers:
            assert isinstance(answer, str) and len(answer) > 40
