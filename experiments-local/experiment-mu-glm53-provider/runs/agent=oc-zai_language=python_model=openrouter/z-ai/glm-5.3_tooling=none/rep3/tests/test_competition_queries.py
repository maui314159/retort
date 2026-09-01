"""
BDD scenarios: competition queries (TASK.md "Required Capabilities" #4) --
standings, champions, finals and knockout brackets.
"""

from __future__ import annotations

from soccer_mcp.bdd import Scenario, expect, expect_equal, expect_gt
from soccer_mcp.queries import (
    QueryError,
    champion,
    finals,
    knockout,
    list_teams,
    standings,
)

FEATURE = "Competition Queries"


def test_2019_brasileirao_standings(dataset):
    (
        Scenario(FEATURE, "Who won the 2019 Brasileirão?")
        .given("the match data is loaded", dataset=dataset)
        .when("I compute the 2019 Série A table",
              table=lambda ctx: standings(ctx["dataset"], "Brasileirão", "2019"))
        .then("Flamengo top the table with the known 90 points",
              assertion=lambda ctx: (
                  expect_equal(ctx["table"].champion.team_id, "flamengo rj"),
                  expect_equal(ctx["table"].champion.points, 90),
                  expect_equal(ctx["table"].champion.wins, 28),
                  expect_equal(len(ctx["table"].rows), 20),
              ))
        .and_("the top three match the historical record",
              assertion=lambda ctx: expect_equal(
                  [r.team_id for r in ctx["table"].rows[:3]],
                  ["flamengo rj", "santos sp", "palmeiras sp"]))
        .run()
    )


def test_standings_math_is_consistent(dataset):
    (
        Scenario(FEATURE, "Every standings row is internally consistent")
        .given("the match data is loaded", dataset=dataset)
        .when("I compute the 2015 Série A table",
              table=lambda ctx: standings(ctx["dataset"], "Série A", "2015"))
        .then("matches, points and goal totals balance",
              assertion=lambda ctx: [
                  (
                      expect_equal(r.wins + r.draws + r.losses, r.matches),
                      expect_equal(r.points, 3 * r.wins + r.draws),
                      expect_gt(r.goals_for, 20),
                  )
                  for r in ctx["table"].rows
              ])
        .run()
    )


def test_relegated_teams_2020(dataset):
    (
        Scenario(FEATURE, "Which teams were relegated in 2020?")
        .given("the match data is loaded", dataset=dataset)
        .when("I compute the 2020 Série A table",
              table=lambda ctx: standings(ctx["dataset"], "Brasileirão", "2020"))
        .then("the bottom four are Vasco, Goiás, Coritiba and Botafogo",
              assertion=lambda ctx: expect_equal(
                  {r.team_id for r in ctx["table"].relegated},
                  {"vasco da gama rj", "goias go", "coritiba pr", "botafogo rj"}))
        .run()
    )


def test_historical_season_standings(dataset):
    (
        Scenario(FEATURE, "Historical seasons (2003-2011) are covered")
        .given("the match data is loaded", dataset=dataset)
        .when("I compute the 2005 Série A table",
              table=lambda ctx: standings(ctx["dataset"], "Brasileirão", "2005"))
        .then("the 22-team 2005 season is computed with Corinthians on top",
              assertion=lambda ctx: (
                  expect_equal(ctx["table"].champion.team_id, "corinthians sp"),
                  expect_equal(len(ctx["table"].rows), 22),
              ))
        .run()
    )


def test_champion_libertadores_2019(dataset):
    (
        Scenario(FEATURE, "Who won the 2019 Copa Libertadores?")
        .given("the match data is loaded", dataset=dataset)
        .when("I ask for the 2019 Libertadores champion",
              result=lambda ctx: champion(ctx["dataset"], "Libertadores", "2019"))
        .then("Flamengo won the single-match final",
              assertion=lambda ctx: (
                  expect_equal(ctx["result"].winner.team_id, "flamengo rj"),
                  expect_equal(ctx["result"].final.ties[0].legs[0].home_goals, 2),
                  expect_equal(ctx["result"].decided_on_penalties, False),
              ))
        .run()
    )


def test_champion_libertadores_2018_two_legged(dataset):
    (
        Scenario(FEATURE, "Two-legged Libertadores final 2018")
        .given("the match data is loaded", dataset=dataset)
        .when("I ask for the 2018 Libertadores champion",
              result=lambda ctx: champion(ctx["dataset"], "Libertadores", "2018"))
        .then("River Plate won on aggregate over two legs",
              assertion=lambda ctx: (
                  expect_equal(ctx["result"].winner.team_id, "river plate"),
                  expect_equal(len(ctx["result"].final.ties[0].legs), 2),
              ))
        .run()
    )


def test_champion_copa_do_brasil_2019(dataset):
    (
        Scenario(FEATURE, "Who won the 2019 Copa do Brasil?")
        .given("the match data is loaded", dataset=dataset)
        .when("I ask for the 2019 Copa do Brasil champion",
              result=lambda ctx: champion(ctx["dataset"], "Copa do Brasil", "2019"))
        .then("Athletico-PR beat Internacional over two legs",
              assertion=lambda ctx: (
                  expect_equal(ctx["result"].winner.team_id, "atletico pr"),
                  expect_equal(len(ctx["result"].final.ties[0].legs), 2),
              ))
        .run()
    )


def test_champion_copa_do_brasil_2021_uses_complete_source(dataset):
    (
        Scenario(FEATURE, "Copa do Brasil 2021 falls back to the complete file")
        .given("the match data is loaded", dataset=dataset)
        .when("I ask for the 2021 Copa do Brasil champion",
              result=lambda ctx: champion(ctx["dataset"], "Copa do Brasil", "2021"))
        .then("Atlético-MG beat Athletico-PR in the December final",
              assertion=lambda ctx: (
                  expect_equal(ctx["result"].winner.team_id, "atletico mg"),
                  expect_equal(len(ctx["result"].final.ties[0].legs), 2),
              ))
        .run()
    )


def test_level_final_reports_penalties(dataset):
    (
        Scenario(FEATURE, "A final level on aggregate is flagged as penalties")
        .given("the match data is loaded", dataset=dataset)
        .when("I ask for the 2022 Copa do Brasil champion",
              result=lambda ctx: champion(ctx["dataset"], "Copa do Brasil", "2022"))
        .then("the final (Corinthians x Flamengo, 1-1 agg) is level and no winner is claimed",
              assertion=lambda ctx: (
                  expect_equal(ctx["result"].winner, None),
                  expect_equal(ctx["result"].decided_on_penalties, True),
                  expect_equal(ctx["result"].final.ties[0].team_a, "corinthians sp"),
              ))
        .run()
    )


def test_list_all_copa_do_brasil_finals(dataset):
    (
        Scenario(FEATURE, "Find all Copa do Brasil finals")
        .given("the match data is loaded", dataset=dataset)
        .when("I list finals across all Copa do Brasil seasons",
              results=lambda ctx: finals(ctx["dataset"], "Copa do Brasil"))
        .then("every season from 2012 to 2023 is covered",
              assertion=lambda ctx: (
                  expect_equal(len(ctx["results"]), 12),
                  expect(all(r.ties or r.note for r in ctx["results"])),
              ))
        .run()
    )


def test_libertadores_knockout_bracket_2018(dataset):
    (
        Scenario(FEATURE, "Show the 2018 Copa Libertadores bracket")
        .given("the match data is loaded", dataset=dataset)
        .when("I request the 2018 Libertadores knockout bracket",
              bracket=lambda ctx: knockout(ctx["dataset"], "Libertadores", "2018"))
        .then("all knockout stages are present with aggregated ties",
              assertion=lambda ctx: (
                  expect_equal(
                      list(ctx["bracket"]),
                      ["Round Of 16", "Quarterfinals", "Semifinals", "Final"]),
                  expect_equal(len(ctx["bracket"]["Round Of 16"]), 8),
                  expect_equal(len(ctx["bracket"]["Quarterfinals"]), 4),
                  expect_equal(len(ctx["bracket"]["Semifinals"]), 2),
                  expect_equal(len(ctx["bracket"]["Final"]), 1),
              ))
        .run()
    )


def test_standings_rejected_for_knockout_competition(dataset):
    (
        Scenario(FEATURE, "Standings are not computed for cups")
        .given("the match data is loaded", dataset=dataset)
        .when("I request Libertadores standings",
              table=lambda ctx: standings(ctx["dataset"], "Libertadores", "2019"))
        .then("a QueryError points to the finals/knockout tools",
              assertion=lambda ctx: (
                  expect(isinstance(ctx.get("error"), QueryError)),
                  expect("knockout" in str(ctx["error"])),
              ))
        .run()
    )


def test_teams_in_a_competition_season(dataset):
    (
        Scenario(FEATURE, "Teams in a competition/season")
        .given("the match data is loaded", dataset=dataset)
        .when("I list the 2022 Série A teams",
              teams=lambda ctx: list_teams(ctx["dataset"], "Brasileirão", "2022"))
        .then("exactly 20 clubs are returned",
              assertion=lambda ctx: expect_equal(len(ctx["teams"]), 20))
        .run()
    )
