"""BDD scenarios: the 20+ sample questions from the spec, answered end-to-end.

Spec success criteria: 'At least 20 sample questions can be answered' and
'Cross-file queries work (e.g., player + match data)'.

Each parameterized case is one natural-language question mapped to the tool
call that answers it and an assertion on the result.
"""

import pytest

CASES = [
    pytest.param(
        "When did Flamengo last play Corinthians?",
        "search_matches",
        {"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
        lambda r: r["matches"][0]["date"] == "2023-10-08",
        id="last-fla-corinthians",
    ),
    pytest.param(
        "What was the score of that match?",
        "search_matches",
        {"team": "Flamengo", "opponent": "Corinthians", "limit": 1},
        lambda r: (r["matches"][0]["home_goals"], r["matches"][0]["away_goals"]) == (1, 1),
        id="score-of-match",
    ),
    pytest.param(
        "Show me all Flamengo vs Fluminense matches",
        "search_matches",
        {"team": "Flamengo", "opponent": "Fluminense", "limit": 100},
        lambda r: r["total"] >= 40 and len(r["matches"]) >= 40,
        id="fla-flu-all-matches",
    ),
    pytest.param(
        "What matches did Palmeiras play in 2023?",
        "search_matches",
        {"team": "Palmeiras", "season": 2023, "competition": "Série A"},
        lambda r: r["total"] == 37 and all(m["season"] == 2023 for m in r["matches"]),
        id="palmeiras-2023",
    ),
    pytest.param(
        "Find all Copa do Brasil finals",
        "search_matches",
        {"competition": "Copa do Brasil", "stage": "final", "limit": 50},
        lambda r: r["total"] >= 20,
        id="cdb-finals",
    ),
    pytest.param(
        "Who is Neymar?",
        "search_players",
        {"name": "Neymar"},
        lambda r: r["players"][0]["overall"] == 92,
        id="who-is-neymar",
    ),
    pytest.param(
        "Which players play for Santos?",
        "search_players",
        {"club": "Santos"},
        lambda r: r["total"] == 20,
        id="santos-players",
    ),
    pytest.param(
        "Find all Brazilian players in the dataset",
        "search_players",
        {"nationality": "Brazil", "limit": 5},
        lambda r: r["total"] == 827,
        id="all-brazilians",
    ),
    pytest.param(
        "Who are the highest-rated players at Grêmio?",
        "team_players",
        {"team": "Grêmio", "limit": 3},
        lambda r: r["total"] == 20 and r["players"][0]["overall"] >= 80,
        id="gremio-top-players",
    ),
    pytest.param(
        "Show me all forwards from Santos",
        "search_players",
        {"club": "Santos", "position": "forward"},
        lambda r: r["total"] > 0,
        id="santos-forwards",
    ),
    pytest.param(
        "What is Corinthians' home record in 2022?",
        "team_stats",
        {"team": "Corinthians", "season": 2022, "competition": "Série A"},
        lambda r: r["home"]["matches"] == 19,
        id="corinthians-home-2022",
    ),
    pytest.param(
        "Who won the 2019 Brasileirão?",
        "standings",
        {"season": 2019},
        lambda r: r["champion"]["team"] == "Flamengo" and r["champion"]["points"] == 90,
        id="winner-2019",
    ),
    pytest.param(
        "Which teams were relegated in 2019?",
        "standings",
        {"season": 2019},
        lambda r: {x["team"] for x in r["relegated"]} == {"Cruzeiro", "CSA", "Chapecoense", "Avaí"},
        id="relegated-2019",
    ),
    pytest.param(
        "Show the 2019 Copa Libertadores bracket",
        "standings",
        {"season": 2019, "competition": "Libertadores"},
        lambda r: [s["stage"] for s in r["stages"]][-1] == "final",
        id="libertadores-bracket",
    ),
    pytest.param(
        "What competitions has Palmeiras played in?",
        "find_team",
        {"name": "Palmeiras"},
        lambda r: "Brasileirão Série A" in r["competitions"] and "Copa Libertadores" in r["competitions"],
        id="palmeiras-competitions",
    ),
    pytest.param(
        "Compare Palmeiras and Santos head-to-head",
        "compare_teams",
        {"team_a": "Palmeiras", "team_b": "Santos"},
        lambda r: r["head_to_head"]["total"] > 0 and "Palmeiras" in r["summary"],
        id="palmeiras-x-santos",
    ),
    pytest.param(
        "What's the average goals per match in the Brasileirão?",
        "goals_analysis",
        {"competition": "Série A"},
        lambda r: 2.2 <= r["avg_goals_per_match"] <= 2.8,
        id="avg-goals",
    ),
    pytest.param(
        "Which team has the best away record?",
        "best_records",
        {"venue": "away", "min_matches": 100, "limit": 3},
        lambda r: r["teams"][0]["team"] == "Palmeiras",
        id="best-away",
    ),
    pytest.param(
        "Show me the biggest wins in the dataset",
        "biggest_wins",
        {"limit": 5},
        lambda r: abs(r["matches"][0]["home_goals"] - r["matches"][0]["away_goals"]) >= 8,
        id="biggest-wins",
    ),
    pytest.param(
        "Show me all derbies in 2023",
        "derbies",
        {"season": 2023},
        lambda r: "Fla-Flu" in r["derbies"] and "Grenal" in r["derbies"],
        id="derbies-2023",
    ),
    pytest.param(
        "Compare the 2018 and 2019 seasons",
        "standings",
        {"season": 2018},
        lambda r: r["champion"]["team"] == "Palmeiras" and r["champion"]["points"] == 80,
        id="season-2018",
    ),
    pytest.param(
        "Who are the top Brazilian players?",
        "search_players",
        {"nationality": "Brazil", "limit": 3},
        lambda r: r["players"][0]["name"] == "Neymar Jr",
        id="top-brazilians",
    ),
    pytest.param(
        "What did Flamengo do season by season?",
        "team_season_history",
        {"team": "Flamengo"},
        lambda r: len(r["seasons"]) >= 15,
        id="flamengo-history",
    ),
    pytest.param(
        "What data does the server have on Copa do Brasil?",
        "competition_info",
        {"competition": "Copa do Brasil"},
        lambda r: any(row["competition"] == "Copa do Brasil" for row in r["competitions"]),
        id="cdb-info",
    ),
    pytest.param(
        "How does Athletico-PR spell its name in the data?",
        "find_team",
        {"name": "Athletico-PR"},
        lambda r: r["team"] == "Athletico-PR" and r["total_matches"] > 100,
        id="athletico-resolution",
    ),
    pytest.param(
        "Who is the best-rated goalkeeper from Brazil?",
        "search_players",
        {"nationality": "Brazil", "position": "goalkeeper", "limit": 1},
        lambda r: r["players"][0]["position"] == "GK" and r["players"][0]["overall"] >= 85,
        id="best-br-gk",
    ),
    pytest.param(
        "Find matches between 2023-06-01 and 2023-08-31 for Botafogo",
        "search_matches",
        {"team": "Botafogo", "date_from": "2023-06-01", "date_to": "2023-08-31", "limit": 50},
        lambda r: r["total"] > 0
        and all("2023-06-01" <= m["date"] <= "2023-08-31" for m in r["matches"]),
        id="botafogo-date-range",
    ),
]


@pytest.mark.parametrize(("question,tool,kwargs,check".split(",")), CASES)
def test_sample_question(question, tool, kwargs, check, ask):
    result = ask(tool, **kwargs)
    assert "summary" in result, f"{tool} must return a formatted summary"
    assert check(result), f"unexpected answer for: {question!r}"
