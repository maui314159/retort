"""The spec's success criterion: at least 20 sample questions answerable.

Each case maps a natural-language question (from TASK.md) to the tool call
that answers it and asserts the answer mentions the expected content.
"""

from __future__ import annotations

import pytest

from soccer_mcp import tools_api as t

SAMPLE_QUESTIONS = [
    # Simple lookups
    ("When did Flamengo last play Corinthians?",
     lambda: t.last_match("Flamengo", "Corinthians"), ["Flamengo", "Corinthians"]),
    ("What was the score? (last Flamengo vs Corinthians)",
     lambda: t.last_match("Flamengo", "Corinthians"), ["-"]),
    ("Who is Gabriel Jesus?",
     lambda: t.player_profile("Gabriel Jesus"), ["Gabriel Jesus", "Overall"]),
    # Match queries
    ("Show me all Flamengo vs Fluminense matches",
     lambda: t.head_to_head("Flamengo", "Fluminense"), ["Fla-Flu", "Head-to-head"]),
    ("What matches did Palmeiras play in 2023?",
     lambda: t.search_matches(team="Palmeiras", season=2023), ["Palmeiras"]),
    ("Find all Copa do Brasil finals",
     lambda: t.search_matches(competition="Copa do Brasil", stage="final"),
     ["Copa do Brasil"]),
    ("Show me all derbies in 2023",
     lambda: t.find_derbies(season=2023), ["Fla-Flu"]),
    # Team queries
    ("What is Corinthians' home record in 2022?",
     lambda: t.team_stats("Corinthians", competition="Brasileirão", season=2022,
                          venue="home"),
     ["Corinthians home record", "Win rate"]),
    ("Which team scored the most goals in Serie A 2023?",
     lambda: t.top_scoring_teams("Serie A", 2023, limit=3), ["goals"]),
    ("Compare Palmeiras and Santos head-to-head",
     lambda: t.head_to_head("Palmeiras", "Santos"), ["Head-to-head"]),
    ("What competitions has Palmeiras played in?",
     lambda: t.team_competitions("Palmeiras"),
     ["Copa do Brasil", "Copa Libertadores"]),
    # Player queries
    ("Find all Brazilian players in the dataset",
     lambda: t.search_players(nationality="Brazil", limit=10), ["Brazil"]),
    ("Who are the highest-rated players at Santos?",
     lambda: t.top_players(club="Santos", limit=5), ["Santos"]),
    ("Show me all forwards from Santos",
     lambda: t.search_players(club="Santos", position_group="forward"),
     ["Santos"]),
    ("Who are the top Brazilian players?",
     lambda: t.top_players(nationality="Brazil", limit=5), ["Neymar Jr"]),
    # Competition queries
    ("Who won the 2019 Brasileirão?",
     lambda: t.standings(2019, "brasileirao"), ["Flamengo - 90 pts", "Champion"]),
    ("Show the 2018 Copa Libertadores knockout stage",
     lambda: t.search_matches(competition="Libertadores", season=2018,
                              stage="semifinals"),
     ["Copa Libertadores"]),
    ("Which teams were relegated in 2019?",
     lambda: t.standings(2019), ["Relegated"]),
    # Statistical analysis
    ("What's the average goals per match in the Brasileirão?",
     lambda: t.competition_stats("brasileirao"), ["Average goals per match"]),
    ("Which team has the best away record in 2022 Serie A?",
     lambda: t.best_away_records("Serie A", 2022), ["win rate"]),
    ("Which team has the best home record in 2022 Serie A?",
     lambda: t.best_home_records("Serie A", 2022), ["win rate"]),
    ("Show me the biggest wins in the dataset",
     lambda: t.biggest_wins(limit=5), ["Biggest victories"]),
    ("Compare the 2018 and 2019 seasons",
     lambda: t.compare_seasons("Serie A", 2018, 2019), ["2018 vs 2019"]),
]


@pytest.mark.parametrize("question,call,expected", SAMPLE_QUESTIONS,
                         ids=[q for q, _, _ in SAMPLE_QUESTIONS])
def test_sample_question(question, call, expected):
    answer = call()
    assert answer.strip(), f"empty answer for {question!r}"
    for needle in expected:
        assert needle in answer, f"{needle!r} missing from answer to {question!r}:\n{answer}"


def test_at_least_twenty_questions():
    assert len(SAMPLE_QUESTIONS) >= 20
