"""
Sample-question coverage: the TASK.md success criterion

    "At least 20 sample questions can be answered"

Each entry pairs one of the spec's example questions with the MCP tool that
answers it, and the test asserts the tool returns a substantive, non-error
answer.
"""

from __future__ import annotations

import pytest

from soccer_mcp import tools

SAMPLE_QUESTIONS: list[tuple[str, str, dict]] = [
    # -- Match queries ------------------------------------------------------
    ("Show me all Flamengo vs Fluminense matches",
     "search_matches", {"team": "Flamengo", "opponent": "Fluminense", "limit": 5}),
    ("What matches did Palmeiras play in 2023?",
     "search_matches", {"team": "Palmeiras", "season": 2023, "limit": 5}),
    ("Find all Copa do Brasil finals",
     "finals", {"competition": "Copa do Brasil"}),
    ("When did Flamengo last play Corinthians?",
     "last_match", {"team": "Flamengo", "opponent": "Corinthians"}),
    ("What was the score of the last Fla-Flu?",
     "last_match", {"team": "Flamengo", "opponent": "Fluminense"}),
    ("Which Brazilian teams played in the 2022 Libertadores?",
     "search_matches", {"competition": "Libertadores", "season": 2022, "limit": 10}),
    # -- Team queries ---------------------------------------------------------
    ("What is Corinthians' home record in 2022?",
     "team_stats", {"team": "Corinthians", "competition": "Brasileirão", "season": 2022}),
    ("Which team scored the most goals in Serie A 2023?",
     "standings", {"competition": "Série A", "season": 2023}),
    ("Compare Palmeiras and Santos head-to-head",
     "compare_teams", {"team_a": "Palmeiras", "team_b": "Santos"}),
    ("What competitions has Palmeiras played in?",
     "team_competitions", {"team": "Palmeiras"}),
    ("Tell me about the team 'Sport Club Corinthians Paulista'",
     "find_team", {"name": "Sport Club Corinthians Paulista"}),
    ("Which team has the best away record?",
     "best_records", {"venue": "away"}),
    ("Which team has the best home record in the Brasileirão?",
     "best_records", {"venue": "home", "competition": "Brasileirão"}),
    ("List the teams of the 2020 Brasileirão",
     "list_teams", {"competition": "Brasileirão", "season": 2020}),
    # -- Player queries --------------------------------------------------------
    ("Who is Gabriel Barbosa?",
     "find_player", {"name": "Gabriel Barbosa"}),
    ("Who is Gabriel Jesus?",
     "find_player", {"name": "Gabriel Jesus"}),
    ("Find all Brazilian players rated 88 or higher",
     "search_players", {"nationality": "Brazil", "min_overall": 88, "limit": 10}),
    ("Who are the highest-rated players at Santos?",
     "top_players", {"club": "Santos", "limit": 5}),
    ("Show me all forwards from São Paulo FC",
     "search_players", {"club": "São Paulo", "position": "FWD", "limit": 10}),
    ("Show me all forwards from Santos",
     "search_players", {"club": "Santos", "position": "FWD", "limit": 10}),
    ("Who are the top Brazilian players?",
     "top_players", {"nationality": "Brazil", "limit": 10}),
    ("Which players play for Grêmio?",
     "top_players", {"club": "Grêmio", "limit": 10}),
    # -- Competition queries -----------------------------------------------------
    ("Who won the 2019 Brasileirão?",
     "champion", {"competition": "Brasileirão", "season": 2019}),
    ("Who won the 2018 Copa Libertadores?",
     "champion", {"competition": "Libertadores", "season": 2018}),
    ("Which teams were relegated in 2020?",
     "standings", {"competition": "Brasileirão", "season": 2020}),
    ("Show the 2018 Copa Libertadores bracket",
     "knockout", {"competition": "Libertadores", "season": 2018}),
    ("What competitions and seasons are in the dataset?",
     "list_competitions", {}),
    ("Who won the 2023 Copa do Brasil?",
     "champion", {"competition": "Copa do Brasil", "season": 2023}),
    # -- Statistics ---------------------------------------------------------------
    ("What's the average goals per match in the Brasileirão?",
     "competition_stats", {"competition": "Brasileirão"}),
    ("Show me the biggest wins in the dataset",
     "biggest_wins", {"limit": 5}),
    ("Show me all derbies in 2023",
     "derbies", {"season": 2023, "limit": 10}),
    ("What were the goal statistics of the 2023 Brasileirão season?",
     "competition_stats", {"competition": "Brasileirão", "season": 2023}),
    ("Compare the 2018 and 2019 Brasileirão seasons by goals",
     "competition_stats", {"competition": "Brasileirão", "season": 2018}),
]


@pytest.mark.parametrize(
    "question,tool,arguments",
    SAMPLE_QUESTIONS,
    ids=[q[:48] for q, _, _ in SAMPLE_QUESTIONS],
)
def test_sample_question_can_be_answered(question, tool, arguments):
    """Every sample question must produce a substantive answer."""
    assert hasattr(tools, tool), f"tool {tool} missing"
    answer = getattr(tools, tool)(**arguments)
    assert isinstance(answer, str) and len(answer) > 30, (
        f"question '{question}' got a too-short answer:\n{answer}"
    )
    assert "Could not answer" not in answer, (
        f"question '{question}' could not be answered:\n{answer}"
    )


def test_at_least_twenty_sample_questions():
    """The success criterion: >= 20 answerable sample questions."""
    assert len(SAMPLE_QUESTIONS) >= 20
