"""Feature: Sample Question Coverage (spec success criterion)

    Given the MCP server with all tools
    When at least 20 sample questions from the specification are asked
    Then every one receives a meaningful, correctly formatted answer

Each case maps a spec question to one tool call (the way an LLM would
drive it) and asserts the substance of the answer.
"""

from __future__ import annotations

import pytest

from conftest import call_tool

pytestmark = pytest.mark.bdd

# (question, tool, arguments, substrings expected in the answer)
QUESTIONS = [
    # --- Simple lookups -------------------------------------------------
    (
        "When did Flamengo last play Corinthians?",
        "last_match",
        {"team": "Flamengo", "opponent": "Corinthians"},
        ["Corinthians", "2023-10-08", "1-1"],
    ),
    (
        "What was the score of that match?",
        "last_match",
        {"team": "Flamengo", "opponent": "Corinthians"},
        ["1-1"],
    ),
    (
        "Who is Neymar? (player lookup)",
        "search_players",
        {"name": "Neymar"},
        ["Neymar Jr", "Overall: 92", "Paris Saint-Germain"],
    ),
    # --- Match queries ---------------------------------------------------
    (
        "Show me all Flamengo vs Fluminense matches",
        "search_matches",
        {"team": "Flamengo", "opponent": "Fluminense", "limit": 50},
        ["Flamengo", "Fluminense", "Brasileirão"],
    ),
    (
        "What matches did Palmeiras play in 2023?",
        "search_matches",
        {"team": "Palmeiras", "season": 2023, "limit": 40},
        ["Palmeiras", "2023"],
    ),
    (
        "Find all Copa do Brasil finals",
        "search_matches",
        {"competition": "copa_do_brasil", "stage": "final", "limit": 20},
        ["Copa do Brasil Final", "Palmeiras"],
    ),
    # --- Team queries ----------------------------------------------------
    (
        "What is Corinthians' home record in 2022?",
        "team_stats",
        {"team": "Corinthians", "season": 2022, "competition": "serie_a"},
        ["Home:", "Wins: 12", "Matches: 19", "Win rate: 63.2%"],
    ),
    (
        "Compare Palmeiras and Santos head-to-head",
        "head_to_head",
        {"team_a": "Palmeiras", "team_b": "Santos"},
        ["Head-to-head in dataset:", "wins"],
    ),
    (
        "What competitions has Palmeiras played in?",
        "team_competitions",
        {"team": "Palmeiras"},
        ["Brasileirão Série A", "Copa Libertadores", "Copa do Brasil"],
    ),
    # --- Player queries --------------------------------------------------
    (
        "Find all Brazilian players in the dataset",
        "search_players",
        {"nationality": "Brazil", "min_overall": 85},
        ["Neymar Jr", "Casemiro", "Brazil"],
    ),
    (
        "Who are the highest-rated players at Grêmio?",
        "search_players",
        {"club": "Grêmio", "limit": 5},
        ["Grêmio", "Overall: 83"],
    ),
    (
        "Show me all forwards from Santos",
        "search_players",
        {"club": "Santos", "position": "ST"},
        ["Santos", "Position: ST"],
    ),
    (
        "Who is Gabriel Barbosa? (fuzzy name search)",
        "search_players",
        {"name": "Gabriel Barbosa", "limit": 6},
        ["Gabriel Jesus"],
    ),
    (
        "Which players play for Flamengo? (honest gap)",
        "search_players",
        {"club": "Flamengo"},
        ["No players found at Flamengo", "snapshot"],
    ),
    (
        "Brazilian players at Brazilian clubs (overview)",
        "club_overview",
        {},
        ["Atlético-MG", "avg rating"],
    ),
    # --- Competition queries ---------------------------------------------
    (
        "Who won the 2019 Brasileirão?",
        "standings",
        {"competition": "serie_a", "season": 2019},
        ["1. Flamengo - 90 pts (28W, 6D, 4L) - Champion"],
    ),
    (
        "Which teams were relegated in 2020?",
        "relegation",
        {"competition": "serie_a", "season": 2020},
        ["Vasco", "Goiás", "Coritiba", "Botafogo"],
    ),
    (
        "Show the 2019 Copa Libertadores final",
        "search_matches",
        {"competition": "libertadores", "stage": "final", "season": 2019},
        ["2019-11-23", "Flamengo 2-1 River Plate"],
    ),
    # --- Statistical analysis ---------------------------------------------
    (
        "What's the average goals per match in the Brasileirão?",
        "competition_stats",
        {"competition": "serie_a"},
        ["Average goals per match: 2.57", "Home win rate"],
    ),
    (
        "Which team has the best away record?",
        "best_records",
        {"venue": "away", "min_matches": 100},
        ["Palmeiras"],
    ),
    (
        "Show me the biggest wins in the dataset",
        "biggest_wins",
        {"limit": 5},
        ["River Plate 8-0"],
    ),
    (
        "Show me all derbies in 2019",
        "derbies",
        {"season": 2019},
        ["Fla-Flu", "GreNal", "Clássico Majestoso"],
    ),
    (
        "Compare the 2018 and 2019 Brasileirão seasons (2019 side)",
        "competition_stats",
        {"competition": "serie_a", "season": 2019},
        ["Average goals per match: 2.31"],
    ),
    # --- Meta ---------------------------------------------------------------
    (
        "What data do you have? (summary)",
        "data_summary",
        {},
        ["16850", "18207", "Brasileirão Série A"],
    ),
]


@pytest.mark.parametrize(
    ("question", "tool", "args", "expected"),
    QUESTIONS,
    ids=[q.split("(")[0].strip()[:48] for q, *_ in QUESTIONS],
)
def test_sample_question_gets_a_meaningful_answer(server, question, tool, args, expected):
    # Given the MCP server with all tools registered
    # When the question is answered via its tool
    answer = call_tool(server, tool, args)
    # Then the answer is non-empty and contains the expected substance
    assert answer.strip(), f"empty answer for: {question}"
    for fragment in expected:
        assert fragment in answer, f"{question!r}: expected {fragment!r} in:\n{answer}"


def test_at_least_twenty_sample_questions_are_answered():
    # Then the spec's coverage criterion is met: 20+ questions
    assert len(QUESTIONS) >= 20
