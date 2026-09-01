"""
Feature: The TASK.md sample questions
  The spec's success criteria require at least 20 sample questions to be
  answerable, including cross-file queries.  Each scenario below is one
  row of the spec's "Sample Questions and Expected Behaviors" tables,
  driven end-to-end through the query layer.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp.queries import (
    best_records,
    biggest_wins,
    competition_stats,
    derbies,
    head_to_head,
    last_match_between,
    player_club_report,
    player_search,
    search_matches,
    standings,
    team_profile,
    team_stats,
)


def test_simple_lookup_when_did_flamengo_last_play_corinthians(ds):
    """
    Scenario: "When did Flamengo last play Corinthians?"
      Given the match data is loaded
      When I ask for their last meeting
      Then the newest fixture is returned (2023-10-08, 1-1)
    """
    result = last_match_between(ds, "Flamengo", "Corinthians")
    assert result["ok"]
    assert result["last_played"]["date"] == "2023-10-08"
    assert result["last_played"]["score"] == "1-1"


def test_simple_lookup_what_was_the_score(ds):
    """
    Scenario: "What was the score?"
      Given Flamengo's last match against Corinthians
      Then home_goal and away_goal are both present as "1-1"
    """
    result = last_match_between(ds, "Flamengo", "Corinthians")
    match = result["last_played"]
    assert match["home_goals"] == 1 and match["away_goals"] == 1


def test_simple_lookup_who_is_gabriel_barbosa(ds):
    """
    Scenario: "Who is Gabriel Barbosa?"
      Given the FIFA player database is loaded
      When I search players named "Gabriel Barbosa"
      Then the honest answer is that this FIFA snapshot does not list him
        (it predates his return to Brazilian club data coverage)
    """
    result = player_search(ds, name="Gabriel Barbosa")
    assert result["ok"]
    assert result["total"] == 0


def test_simple_lookup_who_is_gabriel_jesus(ds):
    """
    Scenario: a positive player lookup
      Given the FIFA player database is loaded
      When I search players named "Gabriel Jesus"
      Then the Manchester City striker is returned
    """
    result = player_search(ds, name="Gabriel Jesus")
    assert result["total"] == 1
    player = result["players"][0]
    assert player["club"] == "Manchester City"
    assert player["position"] == "ST"


def test_relationship_which_players_play_for_gremio(ds):
    """
    Scenario: "Which players play for Grêmio?"
      Given the FIFA player database is loaded
      When I filter by club "Grêmio"
      Then 20 squad players are returned
    """
    result = player_search(ds, club="Grêmio", limit=30)
    assert result["ok"]
    assert result["total"] == 20


def test_relationship_show_me_all_derbies_in_2023(ds):
    """
    Scenario: "Show me all derbies in 2023"
      Given the match data is loaded
      When I request the derby catalogue for 2023
      Then ten derbies have fixtures that season
    """
    result = derbies(ds, season=2023)
    assert result["ok"]
    assert result["derbies_with_matches"] == 10


def test_relationship_what_competitions_has_palmeiras_played_in(ds):
    """
    Scenario: "What competitions has Palmeiras played in?"
      Given the match data is loaded
      When I request Palmeiras' profile
      Then Série A, Copa do Brasil and Libertadores are listed
    """
    result = team_profile(ds, "Palmeiras")
    comps = {entry["competition"] for entry in result["by_competition"]}
    assert comps == {"Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"}


def test_relationship_flamengo_vs_fluminense_matches(ds):
    """
    Scenario: "Show me all Flamengo vs Fluminense matches"
      Given the match data is loaded
      When I search fixtures between the two
      Then 44 meetings are found and listed newest-first
    """
    result = search_matches(ds, team="Flamengo", opponent="Fluminense", limit=200)
    assert result["ok"]
    assert result["total"] == 44
    assert result["shown"] == 44


def test_analytical_which_team_has_the_best_home_record(ds):
    """
    Scenario: "Which team has the best home record?"
      Given the match data is loaded
      When I rank home records across Série A history
      Then Grêmio leads
    """
    result = best_records(
        ds, venue="home", competition="serie_a", min_matches=100, limit=3
    )
    assert result["ok"]
    assert result["records"][0]["team"] == "Grêmio"


def test_analytical_which_team_has_the_best_away_record(ds):
    """
    Scenario: "Which team has the best away record?"
      Given the match data is loaded
      When I rank away records across Série A history
      Then Cruzeiro leads
    """
    result = best_records(
        ds, venue="away", competition="serie_a", min_matches=100, limit=3
    )
    assert result["ok"]
    assert result["records"][0]["team"] == "Cruzeiro"


def test_analytical_who_are_the_top_brazilian_players(ds):
    """
    Scenario: "Who are the top Brazilian players?"
      Given the FIFA player database is loaded
      When I sort Brazilians by overall rating
      Then Neymar Jr (92) tops the list
    """
    result = player_search(ds, nationality="Brazil", limit=5)
    assert result["players"][0]["name"] == "Neymar Jr"
    assert result["players"][0]["overall"] == 92


def test_analytical_average_goals_in_the_brasileirao(ds):
    """
    Scenario: "What's the average goals per match in the Brasileirão?"
      Given the match data is loaded
      When I request Série A aggregate statistics
      Then average goals per match is 2.57 over 8,402 played matches
    """
    result = competition_stats(ds, competition="serie_a")
    assert result["stats"]["avg_goals_per_match"] == 2.57
    assert result["stats"]["played"] == 8402


def test_analytical_who_won_the_2019_brasileirao(ds):
    """
    Scenario: "Who won the 2019 Brasileirão?"
      Given the match data is loaded
      Then the computed champion is Flamengo with 90 points
    """
    result = standings(ds, "serie_a", 2019)
    assert result["champion"]["team"] == "Flamengo"
    assert result["champion"]["points"] == 90


def test_analytical_which_teams_were_relegated_in_2020(ds):
    """
    Scenario: "Which teams were relegated in 2020?"
      Given the match data is loaded
      Then Vasco, Goiás, Coritiba and Botafogo formed the drop zone
    """
    result = standings(ds, "serie_a", 2020)
    assert {r["team"] for r in result["relegated"]} == {
        "Vasco da Gama",
        "Goiás",
        "Coritiba",
        "Botafogo",
    }


def test_analytical_biggest_wins_in_the_dataset(ds):
    """
    Scenario: "Show me the biggest wins in the dataset"
      Given the match data is loaded
      Then São Paulo's 9-1 Copa do Brasil rout tops the list
    """
    result = biggest_wins(ds, limit=5)
    assert result["ok"]
    assert result["biggest_wins"][0]["score"] == "9-1"


def test_analytical_compare_the_2018_and_2019_seasons(ds):
    """
    Scenario: "Compare the 2018 and 2019 seasons"
      Given the match data is loaded
      When I request statistics for both Série A seasons
      Then both answer with complete 380-match samples
    """
    for season in (2018, 2019):
        result = competition_stats(ds, competition="serie_a", season=season)
        assert result["ok"]
        assert result["stats"]["played"] == 380


def test_analytical_corinthians_home_record_2022(ds):
    """
    Scenario: "What is Corinthians' home record in 2022?"
      Given the match data is loaded
      Then 19 home matches, 12 wins, 4 draws, 3 losses
    """
    result = team_stats(
        ds, "Corinthians", season=2022, competition="serie_a", venue="home"
    )
    rec = result["record"]
    assert (rec["matches"], rec["wins"], rec["draws"], rec["losses"]) == (19, 12, 4, 3)


def test_analytical_compare_palmeiras_and_santos(ds):
    """
    Scenario: "Compare Palmeiras and Santos head-to-head"
      Given the match data is loaded
      Then 41 meetings: 17 Palmeiras wins, 8 draws, 16 Santos wins
    """
    result = head_to_head(ds, "Palmeiras", "Santos")
    assert (result["wins_team_a"], result["draws"], result["wins_team_b"]) == (
        17,
        8,
        16,
    )


def test_analytical_find_all_copa_do_brasil_finals(ds):
    """
    Scenario: "Find all Copa do Brasil finals"
      Given the match data is loaded
      When I search cup stage "final"
      Then nine completed seasons (2012-2020) contribute two legs each
    """
    result = search_matches(ds, competition="copa_do_brasil", stage="final", limit=100)
    assert result["ok"]
    assert result["total"] == 18


def test_cross_file_player_plus_match_data(ds):
    """
    Scenario: cross-file queries work (success criterion)
      Given the FIFA player database and the match datasets
      When I request the Grêmio profile
      Then it shows 400+ matches from the fixture files
        and 20 players from the FIFA file
    """
    result = team_profile(ds, "Grêmio")
    assert result["club"]["match_count"] > 400
    assert result["fifa_players_in_dataset"] == 20


def test_cross_file_brazilian_players_at_brazilian_clubs(ds):
    """
    Scenario: "Brazilian players at Brazilian clubs"
      Given both data sources
      When I group Brazilian players by club
      Then the Brazilian clubs from the match data are flagged
    """
    result = player_club_report(ds, nationality="Brazil")
    flagged = [r for r in result["clubs_report"] if r["brazilian_club_in_match_data"]]
    assert len(flagged) >= 10
    assert all(r["players"] >= 1 for r in flagged)


def test_what_matches_did_palmeiras_play_in_2023(ds):
    """
    Scenario: "What matches did Palmeiras play in 2023?"
      Given the match data is loaded
      Then 43 fixtures across two competitions
    """
    result = search_matches(ds, team="Palmeiras", season=2023, limit=100)
    assert result["ok"]
    assert result["total"] == 43


@pytest.mark.parametrize(
    "team,season,competition,expected_matches",
    [
        ("Flamengo", 2019, "serie_a", 38),
        ("Corinthians", 2022, "serie_a", 38),
        ("Palmeiras", 2023, None, 43),
    ],
)
def test_team_season_completeness(ds, team, season, competition, expected_matches):
    """
    Scenario Outline: a team's season covers the right number of fixtures
      Given the match data is loaded
      When I request <team>'s record for <season> in <competition>
      Then <expected_matches> fixtures are counted
    """
    result = team_stats(ds, team, season=season, competition=competition)
    assert result["record"]["matches"] == expected_matches
