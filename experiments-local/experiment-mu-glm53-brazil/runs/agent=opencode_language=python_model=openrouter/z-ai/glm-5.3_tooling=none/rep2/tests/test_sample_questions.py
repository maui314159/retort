"""End-to-end answers for the sample questions listed in the specification.

The spec requires that at least 20 sample questions can be answered; each
parametrized case below drives the service exactly the way the MCP server
would when an LLM answers the corresponding natural-language question.
"""

from __future__ import annotations

import pytest


def answer(service, question: str) -> dict:
    handler = QUESTIONS[question]
    return handler(service)


def _last_flamengo_corinthians(service):
    result = service.search_matches(team="Flamengo", opponent="Corinthians",
                                    limit=500)
    return {"result": result, "last": result["matches"][-1]}


def _neymar(service):
    return {"result": service.search_players(name="Neymar", limit=5)}


def _players_at_santos(service):
    return {"result": service.search_players(club="Santos", limit=100)}


def _derbies_2023(service):
    return {"result": service.derbies(season=2023)}


def _palmeiras_competitions(service):
    return {"result": service.team_competitions("Palmeiras")}


def _best_home(service):
    return {"result": service.best_records(venue="home")}


def _top_brazilians(service):
    return {"result": service.top_players(nationality="Brazil", n=5)}


def _season_compare(service):
    return {
        "s2018": service.league_statistics(
            competition="Brasileirão Série A", season=2018),
        "s2019": service.league_statistics(
            competition="Brasileirão Série A", season=2019),
    }


def _fla_flu(service):
    return {"result": service.head_to_head("Flamengo", "Fluminense")}


def _palmeiras_2023(service):
    return {"result": service.search_matches(team="Palmeiras", season=2023,
                                              limit=5)}


def _cup_finals(service):
    return {"result": service.search_matches(competition="Copa do Brasil",
                                              stage="final", limit=50)}


def _corinthians_home_2022(service):
    return {"result": service.team_stats(
        "Corinthians", season=2022, competition="Brasileirão Série A",
        venue="home")}


def _top_scorers_2023(service):
    return {"result": service.standings("Brasileirão Série A", 2023)}


def _palmeiras_santos(service):
    return {"result": service.head_to_head("Palmeiras", "Santos")}


def _champion_2019(service):
    return {"result": service.standings("Brasileirão Série A", 2019)}


def _relegated_2020(service):
    return {"result": service.standings("Brasileirão Série A", 2020)}


def _avg_goals(service):
    return {"result": service.league_statistics(
        competition="Brasileirão Série A")}


def _best_away(service):
    return {"result": service.best_records(venue="away")}


def _biggest_wins(service):
    return {"result": service.biggest_wins(n=5)}


def _libertadores_finals(service):
    return {"result": service.search_matches(
        competition="Copa Libertadores", stage="final", limit=20)}


def _all_brazilians(service):
    return {"result": service.search_players(nationality="Brazil", limit=1)}


def _gremio_top(service):
    return {"result": service.top_players(club="Grêmio", n=3)}


def _spfc_forwards(service):
    return {"result": service.search_players(club="São Paulo",
                                              position="forward", limit=5)}


def _gremio_away_record(service):
    return {"result": service.team_stats("Grêmio", venue="away")}


def _serie_b_info(service):
    return {"result": service.competition_info("Serie B")}


QUESTIONS = {
    "When did Flamengo last play Corinthians?": _last_flamengo_corinthians,
    "What was the score in that match?": _last_flamengo_corinthians,
    "Who is Neymar?": _neymar,
    "Which players play for Santos?": _players_at_santos,
    "Show me all derbies in 2023": _derbies_2023,
    "What competitions has Palmeiras played in?": _palmeiras_competitions,
    "Which team has the best home record?": _best_home,
    "Who are the top Brazilian players?": _top_brazilians,
    "Compare the 2018 and 2019 Brasileirão seasons": _season_compare,
    "Show me all Flamengo vs Fluminense matches": _fla_flu,
    "What matches did Palmeiras play in 2023?": _palmeiras_2023,
    "Find all Copa do Brasil finals": _cup_finals,
    "What is Corinthians' home record in 2022?": _corinthians_home_2022,
    "Which team scored the most goals in Serie A 2023?": _top_scorers_2023,
    "Compare Palmeiras and Santos head-to-head": _palmeiras_santos,
    "Who won the 2019 Brasileirão?": _champion_2019,
    "Which teams were relegated in 2020?": _relegated_2020,
    "What's the average goals per match in the Brasileirão?": _avg_goals,
    "Which team has the best away record?": _best_away,
    "Show me the biggest wins in the dataset": _biggest_wins,
    "Show the Copa Libertadores finals": _libertadores_finals,
    "Find all Brazilian players in the dataset": _all_brazilians,
    "Who are the highest-rated players at Grêmio?": _gremio_top,
    "Show me all forwards from São Paulo FC": _spfc_forwards,
    "What is Grêmio's away record?": _gremio_away_record,
    "What seasons does Serie B cover?": _serie_b_info,
}


def test_at_least_20_sample_questions_available():
    assert len(QUESTIONS) >= 20


@pytest.mark.parametrize("question", sorted(QUESTIONS))
def test_sample_question_answers(service, question):
    payload = answer(service, question)
    CHECKS[question](payload)


def check_last_flamengo_corinthians(payload):
    result = payload["result"]
    assert result["total"] >= 40
    assert payload["last"]["date"] == "2023-10-08"
    assert payload["last"]["home_goals"] == 1
    assert payload["last"]["away_goals"] == 1


def check_neymar(payload):
    players = payload["result"]["players"]
    assert players[0]["name"] == "Neymar Jr"
    assert players[0]["overall"] == 92
    assert players[0]["position"] == "LW"


def check_players_at_santos(payload):
    result = payload["result"]
    assert result["total"] >= 15
    assert all(p["club_key"] == "santos-sp" for p in result["players"])


def check_derbies_2023(payload):
    derbies = payload["result"]["derbies"]
    names = {entry["derby"] for entry in derbies}
    assert {"Fla-Flu", "Majestoso", "Choque-Rei"} <= names
    assert all(entry["total_matches"] > 0 for entry in derbies)


def check_palmeiras_competitions(payload):
    names = {entry["competition"] for entry in payload["result"]["competitions"]}
    assert names == {"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"}


def check_best_home(payload):
    records = payload["result"]["records"]
    assert records[0]["win_rate"] > 0.5
    rates = [record["win_rate"] for record in records]
    assert rates == sorted(rates, reverse=True)


def check_top_brazilians(payload):
    players = payload["result"]["players"]
    assert players[0]["name"] == "Neymar Jr"
    assert all(p["nationality"] == "Brazil" for p in players)


def check_season_compare(payload):
    assert payload["s2018"]["matches"] == 380
    assert payload["s2019"]["matches"] == 380
    for season in ("s2018", "s2019"):
        assert 2.0 <= payload[season]["avg_goals_per_match"] <= 3.0


def check_fla_flu(payload):
    summary = payload["result"]["summary"]
    assert summary["matches"] >= 40
    assert summary["team_wins"] + summary["opponent_wins"] + summary["draws"] \
        == summary["matches"]


def check_palmeiras_2023(payload):
    assert payload["result"]["total"] >= 40


def check_cup_finals(payload):
    assert payload["result"]["total"] == 18
    seasons = [m["season"] for m in payload["result"]["matches"]]
    assert all(seasons.count(season) <= 2 for season in set(seasons))


def check_corinthians_home_2022(payload):
    overall = payload["result"]["overall"]
    assert overall["matches"] == 15
    assert overall["wins"] == 10
    assert overall["draws"] == 4
    assert overall["losses"] == 1


def check_top_scorers_2023(payload):
    table = payload["result"]["table"]
    top = max(table, key=lambda row: row["goals_for"])
    assert top["display"] == "Grêmio"


def check_palmeiras_santos(payload):
    summary = payload["result"]["summary"]
    assert summary["matches"] >= 40


def check_champion_2019(payload):
    assert payload["result"]["champion"] == "Flamengo"
    assert payload["result"]["table"][0]["points"] == 90


def check_relegated_2020(payload):
    assert set(payload["result"]["relegated"]) == {
        "Vasco", "Goiás", "Coritiba", "Botafogo RJ",
    }


def check_avg_goals(payload):
    assert 2.0 <= payload["result"]["avg_goals_per_match"] <= 3.0
    assert payload["result"]["home_win_rate"] > payload["result"]["away_win_rate"]


def check_best_away(payload):
    records = payload["result"]["records"]
    assert records[0]["win_rate"] > 0.25


def check_biggest_wins(payload):
    wins = payload["result"]["wins"]
    assert wins[0]["margin"] >= 8
    margins = [w["margin"] for w in wins]
    assert margins == sorted(margins, reverse=True)


def check_libertadores_finals(payload):
    assert payload["result"]["total"] >= 14
    assert all(m["stage"] == "final" for m in payload["result"]["matches"])


def check_all_brazilians(payload):
    assert payload["result"]["total"] == 827


def check_gremio_top(payload):
    players = payload["result"]["players"]
    assert players
    assert all(p["club_key"] == "gremio" for p in players)
    overalls = [p["overall"] for p in players]
    assert overalls == sorted(overalls, reverse=True)


def check_spfc_forwards(payload):
    assert payload["result"]["total"] == 0
    assert payload["result"]["players"] == []


def check_gremio_away_record(payload):
    away = payload["result"]["away"]
    assert away["matches"] > 100
    assert away["wins"] + away["draws"] + away["losses"] == away["matches"]


def check_serie_b_info(payload):
    result = payload["result"]
    assert result["competition"] == "Brasileirão Série B"
    seasons = [entry["season"] for entry in result["seasons"]]
    assert min(seasons) >= 2014
    assert max(seasons) <= 2023


CHECKS = {
    "When did Flamengo last play Corinthians?": check_last_flamengo_corinthians,
    "What was the score in that match?": check_last_flamengo_corinthians,
    "Who is Neymar?": check_neymar,
    "Which players play for Santos?": check_players_at_santos,
    "Show me all derbies in 2023": check_derbies_2023,
    "What competitions has Palmeiras played in?": check_palmeiras_competitions,
    "Which team has the best home record?": check_best_home,
    "Who are the top Brazilian players?": check_top_brazilians,
    "Compare the 2018 and 2019 Brasileirão seasons": check_season_compare,
    "Show me all Flamengo vs Fluminense matches": check_fla_flu,
    "What matches did Palmeiras play in 2023?": check_palmeiras_2023,
    "Find all Copa do Brasil finals": check_cup_finals,
    "What is Corinthians' home record in 2022?": check_corinthians_home_2022,
    "Which team scored the most goals in Serie A 2023?": check_top_scorers_2023,
    "Compare Palmeiras and Santos head-to-head": check_palmeiras_santos,
    "Who won the 2019 Brasileirão?": check_champion_2019,
    "Which teams were relegated in 2020?": check_relegated_2020,
    "What's the average goals per match in the Brasileirão?": check_avg_goals,
    "Which team has the best away record?": check_best_away,
    "Show me the biggest wins in the dataset": check_biggest_wins,
    "Show the Copa Libertadores finals": check_libertadores_finals,
    "Find all Brazilian players in the dataset": check_all_brazilians,
    "Who are the highest-rated players at Grêmio?": check_gremio_top,
    "Show me all forwards from São Paulo FC": check_spfc_forwards,
    "What is Grêmio's away record?": check_gremio_away_record,
    "What seasons does Serie B cover?": check_serie_b_info,
}
