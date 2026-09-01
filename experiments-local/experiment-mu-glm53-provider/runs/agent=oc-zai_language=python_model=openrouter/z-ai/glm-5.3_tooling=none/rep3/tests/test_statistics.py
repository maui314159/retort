"""
BDD scenarios: statistical analysis (TASK.md "Required Capabilities" #5) --
averages, home/away splits, biggest wins, derbies.
"""

from __future__ import annotations

from soccer_mcp.bdd import (
    Scenario,
    expect,
    expect_contains,
    expect_equal,
    expect_gt,
    expect_in_range,
)
from soccer_mcp.queries import (
    biggest_wins,
    competition_stats,
    derbies,
    last_match,
    list_teams,
)

FEATURE = "Statistical Analysis"


def test_average_goals_per_match(dataset):
    (
        Scenario(FEATURE, "What's the average goals per match in the Brasileirão?")
        .given("the match data is loaded", dataset=dataset)
        .when("I aggregate all deduplicated Série A matches",
              agg=lambda ctx: competition_stats(ctx["dataset"], competition="Brasileirão")[0])
        .then("the average sits in a realistic 2-3 goal band over thousands of matches",
              assertion=lambda ctx: (
                  expect_gt(ctx["agg"].matches, 7000,
                            "2003-2023 Serie A spans ~8000 matches"),
                  expect_in_range(ctx["agg"].avg_goals, 2.0, 3.0),
              ))
        .run()
    )


def test_outcome_rates_are_coherent(dataset):
    (
        Scenario(FEATURE, "Home/draw/away rates sum to 100%")
        .given("the match data is loaded", dataset=dataset)
        .when("I aggregate the whole dataset",
              agg=lambda ctx: competition_stats(ctx["dataset"])[0])
        .then("the three outcome rates add up to one",
              assertion=lambda ctx: expect_equal(
                  round(ctx["agg"].home_win_rate + ctx["agg"].draw_rate
                        + ctx["agg"].away_win_rate, 6), 1.0))
        .and_("home teams win more often than away teams",
              assertion=lambda ctx: expect(
                  ctx["agg"].home_win_rate > ctx["agg"].away_win_rate,
                  "home advantage should hold across this much data"))
        .run()
    )


def test_average_goals_for_one_season(dataset):
    (
        Scenario(FEATURE, "Average goals for a single season")
        .given("the match data is loaded", dataset=dataset)
        .when("I aggregate the 2019 Série A",
              agg=lambda ctx: competition_stats(
                  ctx["dataset"], competition="Brasileirão", season="2019")[0])
        .then("exactly 380 matches are aggregated",
              assertion=lambda ctx: expect_equal(ctx["agg"].matches, 380))
        .run()
    )


def test_biggest_wins_are_sorted_by_margin(dataset):
    (
        Scenario(FEATURE, "Show me the biggest wins in the dataset")
        .given("the match data is loaded", dataset=dataset)
        .when("I list the biggest wins overall",
              wins=lambda ctx: biggest_wins(ctx["dataset"], limit=10))
        .then("margins are non-increasing and the top margin is huge",
              assertion=lambda ctx: (
                  expect_gt(ctx["wins"][0].goal_margin, 6,
                            "an 8-0+ scoreline exists in the data"),
                  expect(all(
                      ctx["wins"][i].goal_margin >= ctx["wins"][i + 1].goal_margin
                      for i in range(len(ctx["wins"]) - 1)
                  )),
              ))
        .run()
    )


def test_biggest_libertadores_wins(dataset):
    (
        Scenario(FEATURE, "Biggest wins filtered to a competition")
        .given("the match data is loaded", dataset=dataset)
        .when("I list the biggest Libertadores wins",
              wins=lambda ctx: biggest_wins(
                  ctx["dataset"], competition="Libertadores", limit=5))
        .then("all are Libertadores matches with a large margin",
              assertion=lambda ctx: (
                  expect(all(m.competition == "libertadores" for m in ctx["wins"])),
                  expect_gt(ctx["wins"][0].goal_margin, 4),
              ))
        .run()
    )


def test_biggest_wins_for_one_team(dataset):
    (
        Scenario(FEATURE, "Biggest wins for one team")
        .given("the match data is loaded", dataset=dataset)
        .when("I list Palmeiras' biggest wins",
              wins=lambda ctx: biggest_wins(ctx["dataset"], team="Palmeiras", limit=5))
        .then("Palmeiras played in every result",
              assertion=lambda ctx: (
                  expect_gt(len(ctx["wins"]), 0),
                  expect(all(
                      "palmeiras sp" in (m.home_team, m.away_team)
                      for m in ctx["wins"])),
              ))
        .run()
    )


def test_derbies_in_2023(dataset):
    (
        Scenario(FEATURE, "Show me all derbies in 2023")
        .given("the match data is loaded", dataset=dataset)
        .when("I list 2023 derby matches",
              items=lambda ctx: derbies(ctx["dataset"], season="2023"))
        .then("classic derbies from 2023 are present",
              assertion=lambda ctx: (
                  expect_gt(len(ctx["items"]), 20,
                            "2023 had 30+ derbies across competitions"),
                  expect_contains({label for label, _ in ctx["items"]}, "Fla-Flu"),
                  expect_contains({label for label, _ in ctx["items"]}, "Grenal"),
                  expect_contains({label for label, _ in ctx["items"]}, "Derby Paulista"),
              ))
        .and_("every match is from the 2023 season",
              assertion=lambda ctx: expect(all(
                  m.season == "2023" for _, m in ctx["items"])))
        .run()
    )


def test_grenal_derby_history(dataset):
    (
        Scenario(FEATURE, "Grenal head-to-head exists in the dataset")
        .given("the match data is loaded", dataset=dataset)
        .when("I list Grenal matches across all seasons",
              items=lambda ctx: derbies(ctx["dataset"]))
        .then("dozens of Grenal fixtures are found",
              assertion=lambda ctx: expect_gt(
                  sum(1 for label, _ in ctx["items"] if label == "Grenal"), 20))
        .run()
    )


def test_last_match_of_a_team(dataset):
    (
        Scenario(FEATURE, "When did Flamengo last play Corinthians?")
        .given("the match data is loaded", dataset=dataset)
        .when("I ask for Flamengo's last match against Corinthians",
              match=lambda ctx: last_match(ctx["dataset"], "Flamengo", "Corinthians"))
        .then("the latest fixture between them is returned",
              assertion=lambda ctx: (
                  expect(ctx["match"] is not None),
                  expect_equal(
                      {ctx["match"].home_team, ctx["match"].away_team},
                      {"flamengo rj", "corinthians sp"}),
              ))
        .and_("no later meeting exists in the data",
              assertion=lambda ctx: expect(all(
                  m.match_date <= ctx["match"].match_date
                  for m in ctx["dataset"].iter_matches(
                      team="flamengo rj", opponent="corinthians sp"))))
        .run()
    )


def test_all_brazilian_teams_are_listable(dataset):
    (
        Scenario(FEATURE, "Cross-file team listing")
        .given("the match data is loaded", dataset=dataset)
        .when("I list every Brazilian team in the match data",
              teams=lambda ctx: list_teams(ctx["dataset"]))
        .then("hundreds of clubs from all files are present",
              assertion=lambda ctx: (
                  expect_gt(len(ctx["teams"]), 300),
                  expect_contains({t.team_id for t in ctx["teams"]}, "flamengo rj"),
                  expect_contains({t.team_id for t in ctx["teams"]}, "abc rn"),
                  expect_contains({t.team_id for t in ctx["teams"]}, "remo pa"),
              ))
        .run()
    )
