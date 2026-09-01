"""
BDD scenarios: team queries (TASK.md "Required Capabilities" #2).

Feature: Team Queries
  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
"""

from __future__ import annotations

from soccer_mcp.bdd import Scenario, expect, expect_equal, expect_gt, expect_in_range
from soccer_mcp.queries import (
    QueryError,
    best_records,
    compare_teams,
    head_to_head,
    team_stats,
)

FEATURE = "Team Queries"


def test_get_team_statistics(dataset):
    """The spec's second example scenario, verbatim in intent."""
    (
        Scenario(FEATURE, "Get team statistics")
        .given("the match data is loaded", dataset=dataset)
        .when("I request statistics for 'Palmeiras' in season '2023'",
              result=lambda ctx: team_stats(ctx["dataset"], "Palmeiras", season="2023"))
        .then("I should receive wins, losses, draws, and goals",
              assertion=lambda ctx: (
                  expect_gt(ctx["result"].overall.matches, 40,
                            "Palmeiras played 50+ matches in 2023"),
                  expect_in_range(ctx["result"].overall.wins, 15, 35),
                  expect_in_range(ctx["result"].overall.draws, 3, 20),
                  expect_in_range(ctx["result"].overall.losses, 3, 20),
                  expect_gt(ctx["result"].overall.goals_for, 50),
                  expect_gt(ctx["result"].overall.goals_against, 20),
              ))
        .run()
    )


def test_home_record_for_a_season(dataset):
    (
        Scenario(FEATURE, "Home record in a specific season")
        .given("the match data is loaded", dataset=dataset)
        .when("I request Corinthians' home record for the 2022 Brasileirão",
              result=lambda ctx: team_stats(
                  ctx["dataset"], "Corinthians",
                  competition="Brasileirão", season="2022"))
        .then("the home split covers ~19 home matches with consistent totals",
              assertion=lambda ctx: (
                  expect_equal(ctx["result"].home.matches, 19),
                  expect_equal(
                      ctx["result"].home.wins + ctx["result"].home.draws
                      + ctx["result"].home.losses, 19),
                  expect_equal(
                      ctx["result"].home.matches + ctx["result"].away.matches,
                      ctx["result"].overall.matches),
              ))
        .run()
    )


def test_head_to_head_record(dataset):
    (
        Scenario(FEATURE, "Head-to-head between two teams")
        .given("the match data is loaded", dataset=dataset)
        .when("I compare Palmeiras and Santos head-to-head",
              result=lambda ctx: head_to_head(ctx["dataset"], "Palmeiras", "Santos"))
        .then("wins, draws and goals add up to the match count",
              assertion=lambda ctx: (
                  expect_gt(ctx["result"].wins_a, 10),
                  expect_equal(
                      ctx["result"].wins_a + ctx["result"].wins_b + ctx["result"].draws,
                      len(ctx["result"].matches)),
              ))
        .run()
    )


def test_compare_teams_side_by_side(dataset):
    (
        Scenario(FEATURE, "Compare two teams")
        .given("the match data is loaded", dataset=dataset)
        .when("I compare Flamengo and Palmeiras",
              a=lambda ctx: compare_teams(ctx["dataset"], "Flamengo", "Palmeiras")[0],
              b=lambda ctx: compare_teams(ctx["dataset"], "Flamengo", "Palmeiras")[1],
              h2h=lambda ctx: compare_teams(ctx["dataset"], "Flamengo", "Palmeiras")[2])
        .then("both records and the head-to-head are returned",
              assertion=lambda ctx: (
                  expect_gt(ctx["a"].overall.matches, 200),
                  expect_gt(ctx["b"].overall.matches, 200),
                  expect_gt(ctx["h2h"].wins_a + ctx["h2h"].wins_b + ctx["h2h"].draws, 30),
              ))
        .run()
    )


def test_team_record_consistency(dataset):
    (
        Scenario(FEATURE, "Record arithmetic is internally consistent")
        .given("the match data is loaded", dataset=dataset)
        .when("I request Cruzeiro's overall record",
              result=lambda ctx: team_stats(ctx["dataset"], "Cruzeiro"))
        .then("points equal 3*wins + draws and goal difference matches",
              assertion=lambda ctx: (
                  expect_equal(
                      ctx["result"].overall.points,
                      3 * ctx["result"].overall.wins + ctx["result"].overall.draws),
                  expect_equal(
                      ctx["result"].overall.goal_diff,
                      ctx["result"].overall.goals_for - ctx["result"].overall.goals_against),
              ))
        .run()
    )


def test_best_away_record(dataset):
    (
        Scenario(FEATURE, "Which team has the best away record?")
        .given("the match data is loaded", dataset=dataset)
        .when("I rank teams by away win rate",
              ranking=lambda ctx: best_records(ctx["dataset"], venue="away"))
        .then("a non-empty ranking of well-known clubs is returned",
              assertion=lambda ctx: (
                  expect_gt(len(ctx["ranking"]), 5),
                  expect(ctx["ranking"][0][0].win_rate > 0.35,
                         "top away win rate should exceed 35%"),
              ))
        .run()
    )


def test_team_stats_for_a_specific_competition(dataset):
    (
        Scenario(FEATURE, "Team record within one competition")
        .given("the match data is loaded", dataset=dataset)
        .when("I ask for Flamengo's Libertadores record",
              result=lambda ctx: team_stats(
                  ctx["dataset"], "Flamengo", competition="Libertadores"))
        .then("only Libertadores matches are counted",
              assertion=lambda ctx: (
                  expect_gt(ctx["result"].overall.matches, 30),
                  expect(all(comp == "libertadores"
                             for comp, _ in ctx["result"].per_competition)),
              ))
        .run()
    )


def test_ambiguous_team_returns_candidates(dataset):
    (
        Scenario(FEATURE, "Ambiguous team names surface candidates")
        .given("the match data is loaded", dataset=dataset)
        .when("I request statistics for 'America'",
              result=lambda ctx: team_stats(ctx["dataset"], "America"))
        .then("a QueryError lists América-MG and América-RN",
              assertion=lambda ctx: (
                  expect(isinstance(ctx.get("error"), QueryError)),
                  expect(len(ctx["error"].alternatives) >= 2),
              ))
        .run()
    )
