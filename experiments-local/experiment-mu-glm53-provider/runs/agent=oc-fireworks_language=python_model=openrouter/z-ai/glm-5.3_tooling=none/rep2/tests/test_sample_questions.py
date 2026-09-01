"""BDD scenarios answering the specification's sample questions.

Feature: Sample questions
  Given the knowledge graph is loaded
  When each sample question from the specification is asked
  Then a useful, correctly-formatted answer comes back

This suite covers more than 20 natural-language questions from the
"Sample Questions and Expected Behaviors" and "Required Capabilities"
tables of the specification, exercised through the same service layer
the MCP tools expose.
"""

from __future__ import annotations

import re


def _first_match_line(result: str) -> str:
    for line in result.splitlines():
        if line.startswith("- "):
            return line
    raise AssertionError(f"no match lines in:\n{result}")


class TestSimpleLookups:
    def test_when_did_flamengo_last_play_corinthians(self, svc):
        # "When did Flamengo last play Corinthians?"
        result = svc.search_matches(team="Flamengo", opponent="Corinthians", limit=1)
        line = _first_match_line(result)
        assert re.match(r"- \d{4}-\d{2}-\d{2}: ", line)
        assert "Flamengo" in result and "Corinthians" in result

    def test_what_was_the_score(self, svc):
        # "What was the score?" (of the most recent Fla x Corinthians match)
        result = svc.search_matches(team="Flamengo", opponent="Corinthians", limit=1)
        line = _first_match_line(result)
        assert re.search(r"\d+-\d+", line), line

    def test_who_is_neymar(self, svc):
        # "Who is Neymar?"
        result = svc.search_players(name="Neymar")
        assert "Neymar Jr" in result
        assert "Overall: 92" in result
        assert "Position: LW" in result

    def test_who_is_messi(self, svc):
        # "Who is L. Messi?" (non-Brazilian lookup works too)
        result = svc.search_players(name="Messi")
        assert "L. Messi" in result
        assert "Overall: 94" in result


class TestRelationshipQueries:
    def test_which_players_play_for_flamengo(self, svc):
        # "Which players play for Flamengo?"
        result = svc.search_players(club="Flamengo")
        assert "No players found" in result
        assert "licensing" in result  # explains the FIFA gap honestly

    def test_show_me_all_derbies_in_2023(self, svc):
        # "Show me all derbies in 2023"
        result = svc.derby_matches(season=2023)
        assert "matches in dataset" in result
        # At least one classic happened in 2023
        assert re.search(r"\d+ matches in dataset", result)

    def test_what_competitions_has_palmeiras_played_in(self, svc):
        # "What competitions has Palmeiras played in?"
        result = svc.team_profile("Palmeiras")
        assert "Copa do Brasil: 2012-2023" in result
        assert "Copa Libertadores: 2013-2022" in result
        assert "Brasileirão Serie A: 2004-2023" in result

    def test_which_players_play_for_gremio(self, svc):
        # "Which players play for Grêmio?"
        result = svc.search_players(club="Grêmio", nationality="Brazil", limit=25)
        found = int(re.search(r"(\d+) found", result).group(1))
        assert found >= 20
        assert "Club: Grêmio" in result


class TestAnalyticalQueries:
    def test_which_team_has_the_best_home_record(self, svc):
        # "Which team has the best home record?" (latest full Serie A season)
        result = svc.league_standings("Brasileirão", season=2019, venue="home")
        first = [ln for ln in result.splitlines() if ln.startswith("1. ")][0]
        assert "pts" in first

    def test_who_are_the_top_brazilian_players(self, svc):
        # "Who are the top Brazilian players?"
        result = svc.search_players(nationality="Brazil", limit=10)
        assert "1. Neymar Jr - Overall: 92" in result
        assert "2. Casemiro" in result

    def test_compare_the_2018_and_2019_seasons(self, svc):
        # "Compare the 2018 and 2019 seasons"
        info_2018 = svc.competition_info("Brasileirão", season=2018)
        info_2019 = svc.competition_info("Brasileirão", season=2019)
        assert "Matches played: 380 of 380" in info_2018
        assert "Matches played: 380 of 380" in info_2019
        avg_18 = float(re.search(r"Average goals per match: ([\d.]+)", info_2018).group(1))
        avg_19 = float(re.search(r"Average goals per match: ([\d.]+)", info_2019).group(1))
        assert avg_18 != avg_19 or (2.0 < avg_18 < 3.0)

    def test_which_team_scored_the_most_goals_in_serie_a_2023(self, svc, dataset):
        # "Which team scored the most goals in Serie A 2023?"
        result = svc.league_standings("Brasileirão", season=2023)
        # Recompute the expected top scorer directly from the graph
        goals: dict[str, int] = {}
        for m in dataset.matches:
            if m.competition == "brasileirao" and m.season == 2023 and m.played:
                goals[m.home.key] = goals.get(m.home.key, 0) + m.home_goals
                goals[m.away.key] = goals.get(m.away.key, 0) + m.away_goals
        expected_key = max(goals, key=goals.get)
        expected_display = dataset.registry.display(expected_key)
        expected_gf = goals[expected_key]
        # Then the standings list that team with exactly that GF total
        line = [ln for ln in result.splitlines() if ln.startswith("1. ")][0]
        assert expected_display in line
        assert f"GF {expected_gf}," in line

    def test_who_won_the_2019_brasileirao(self, svc):
        # "Who won the 2019 Brasileirão?"
        result = svc.league_standings("Brasileirão", season=2019)
        assert "1. Flamengo - 90 pts" in result
        assert "Champion" in result

    def test_who_won_the_2020_libertadores(self, svc):
        # "Who won the 2020 Copa Libertadores?"
        result = svc.finals("Libertadores")
        assert "2020:" in result
        assert "Palmeiras 1-0 Santos" in result
        assert "Champion: Palmeiras" in result

    def test_which_teams_were_relegated_in_2020(self, svc):
        # "Which teams were relegated in 2020?"
        result = svc.league_standings("Brasileirão", season=2020)
        relegated = " ".join(ln for ln in result.splitlines() if "Relegated" in ln)
        for team in ("Vasco", "Goiás", "Coritiba", "Botafogo"):
            assert team in relegated

    def test_whats_the_average_goals_per_match_in_the_brasileirao(self, svc):
        # "What's the average goals per match in the Brasileirão?"
        result = svc.competition_info("Brasileirão")
        assert re.search(r"Average goals per match: 2\.\d+", result)

    def test_which_team_has_the_best_away_record(self, svc):
        # "Which team has the best away record?" (2019 Serie A)
        result = svc.league_standings("Brasileirão", season=2019, venue="away")
        assert "away matches only" in result
        first = [ln for ln in result.splitlines() if ln.startswith("1. ")][0]
        assert "pts" in first

    def test_show_me_the_biggest_wins_in_the_dataset(self, svc):
        # "Show me the biggest wins in the dataset"
        result = svc.biggest_wins(limit=5)
        margins = [
            abs(int(a) - int(b))
            for a, b in re.findall(r"\d{4}-\d{2}-\d{2}: .+? (\d+)-(\d+) ", result)
        ]
        assert margins[0] >= 8
        assert margins == sorted(margins, reverse=True)

    def test_compare_palmeiras_and_santos_head_to_head(self, svc):
        # "Compare Palmeiras and Santos head-to-head"
        result = svc.head_to_head("Palmeiras", "Santos")
        assert "Head-to-head in dataset: Palmeiras" in result
        numbers = [
            int(n)
            for n in re.findall(r"(\d+) wins|(\d+) draws", result.splitlines()[-1])
            for n in n if n
        ]
        assert sum(numbers) >= 30

    def test_what_is_corinthians_home_record_in_2022(self, svc):
        # "What is Corinthians' home record in 2022?"
        result = svc.team_stats("Corinthians", season=2022, venue="home")
        assert "Matches: 29" in result  # league + cups at home in 2022
        league_only = svc.team_stats(
            "Corinthians", season=2022, competition="Brasileirão", venue="home"
        )
        assert "Matches: 19" in league_only

    def test_find_all_copa_do_brasil_finals(self, svc):
        # "Find all Copa do Brasil finals"
        result = svc.finals("Copa do Brasil")
        for season in range(2012, 2024):
            assert f"{season}:" in result, season
        assert "Champion: Palmeiras" in result  # 2012

    def test_show_the_2018_libertadores_bracket_stages(self, svc):
        # "Show the 2018 Copa Libertadores bracket"
        result = svc.search_matches(
            competition="Libertadores", season=2018, stage="final", limit=5
        )
        assert "Boca Juniors" in result and "River Plate" in result
        semis = svc.search_matches(
            competition="Libertadores", season=2018, stage="semifinals", limit=5
        )
        assert "Semifinals" in semis

    def test_flamengo_vs_fluminense_all_matches(self, svc):
        # "Show me all Flamengo vs Fluminense matches"
        result = svc.search_matches(team="Flamengo", opponent="Fluminense", limit=5)
        count = int(re.search(r"(\d+) found", result).group(1))
        assert count >= 30
        assert "Fla-Flu" in result

    def test_what_matches_did_palmeiras_play_in_2023(self, svc):
        # "What matches did Palmeiras play in 2023?"
        result = svc.search_matches(team="Palmeiras", season=2023)
        count = int(re.search(r"(\d+) found", result).group(1))
        assert count >= 30
        by_comp = [ln for ln in result.splitlines() if ln.startswith("By competition")][0]
        assert "Copa do Brasil" in by_comp  # cross-competition coverage

    def test_brazilian_players_at_brazilian_clubs(self, svc):
        # "Find all Brazilian players in the dataset" (grouped by club)
        result = svc.players_by_club(nationality="Brazil", limit=10)
        assert "avg rating" in result
        assert "Grêmio" in result

    def test_gre_nal_last_matches(self, svc):
        # "When was the last Gre-Nal?"
        result = svc.derby_matches("Gre-Nal", limit=2)
        line = _first_match_line(result)
        assert re.match(r"- \d{4}-\d{2}-\d{2}: ", line)
        assert "Grêmio" in line and "Internacional" in line

    def test_who_are_the_highest_rated_players_at_santos(self, svc):
        # "Who are the highest-rated players at Santos?"
        result = svc.search_players(club="Santos", limit=5, sort="overall")
        overalls = [int(o) for o in re.findall(r"Overall: (\d+)", result)]
        assert overalls == sorted(overalls, reverse=True)
        assert overalls[0] >= 75

    def test_all_matches_between_atletico_mg_and_cruzeiro(self, svc):
        # "Show all matches between Atlético-MG and Cruzeiro" (state suffix query)
        result = svc.head_to_head("Atlético-MG", "Cruzeiro")
        assert "matches in dataset" in result
        assert "Atlético-MG" in result
