"""
BDD scenarios: match queries (TASK.md "Required Capabilities" #1).

Feature: Match Queries
  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
"""

from __future__ import annotations

from soccer_mcp.bdd import Scenario, expect, expect_equal, expect_gt
from soccer_mcp.queries import QueryError, search_matches

FEATURE = "Match Queries"


def test_find_matches_between_two_teams(dataset):
    """The spec's first example scenario, verbatim in intent."""
    (
        Scenario(FEATURE, "Find matches between two teams")
        .given("the match data is loaded", dataset=dataset)
        .when("I search for matches between 'Flamengo' and 'Fluminense'",
              result=lambda ctx: search_matches(
                  ctx["dataset"], team="Flamengo", opponent="Fluminense"))
        .then("I should receive a list of matches",
              assertion=lambda ctx: expect_gt(ctx["result"].total, 20,
                                              "expected many Fla-Flu matches"))
        .and_("each match should have date, scores, and competition",
              assertion=lambda ctx: [
                  (expect(m.match_date is not None, f"missing date: {m}"),
                   expect(isinstance(m.home_goals, int) and isinstance(m.away_goals, int),
                          f"missing scores: {m}"),
                   expect(bool(m.competition), f"missing competition: {m}"))
                  for m in ctx["result"].matches
              ])
        .run()
    )


def test_matches_for_a_team_in_a_season(dataset):
    (
        Scenario(FEATURE, "Matches for one team in a given season")
        .given("the match data is loaded", dataset=dataset)
        .when("I ask what matches Palmeiras played in 2023",
              result=lambda ctx: search_matches(
                  ctx["dataset"], team="Palmeiras", season="2023"))
        .then("only 2023 matches involving Palmeiras are returned",
              assertion=lambda ctx: (
                  expect_gt(ctx["result"].total, 40, "Palmeiras played 50+ games in 2023"),
                  expect(all(
                      m.season == "2023" and "palmeiras sp" in (m.home_team, m.away_team)
                      for m in ctx["result"].matches
                  ), "season/team filter leaked"),
              ))
        .run()
    )


def test_matches_by_competition(dataset):
    (
        Scenario(FEATURE, "Matches by competition")
        .given("the match data is loaded", dataset=dataset)
        .when("I search Libertadores matches for Grêmio",
              result=lambda ctx: search_matches(
                  ctx["dataset"], team="Grêmio", competition="Libertadores"))
        .then("all results are Libertadores matches with Grêmio",
              assertion=lambda ctx: (
                  expect_gt(ctx["result"].total, 10),
                  expect(all(
                      m.competition == "libertadores"
                      and "gremio rs" in (m.home_team, m.away_team)
                      for m in ctx["result"].matches
                  )),
              ))
        .run()
    )


def test_matches_by_date_range(dataset):
    (
        Scenario(FEATURE, "Matches by inclusive date range")
        .given("the match data is loaded", dataset=dataset)
        .when("I search Brasileirão matches in September 2023",
              result=lambda ctx: search_matches(
                  ctx["dataset"],
                  competition="Brasileirão",
                  date_from="2023-09-01",
                  date_to="2023-09-30",
              ))
        .then("every match falls inside the range",
              assertion=lambda ctx: (
                  expect_gt(ctx["result"].total, 20, "a month of Serie A has 30-40 games"),
                  expect(all(
                      "2023-09-01" <= m.match_date.isoformat() <= "2023-09-30"
                      for m in ctx["result"].matches
                  )),
              ))
        .run()
    )


def test_find_cup_finals_by_stage(dataset):
    (
        Scenario(FEATURE, "Find finals via the stage filter")
        .given("the match data is loaded", dataset=dataset)
        .when("I search Libertadores matches with stage 'final'",
              result=lambda ctx: search_matches(
                  ctx["dataset"], competition="Libertadores", stage="final"))
        .then("only finals are returned",
              assertion=lambda ctx: (
                  expect_gt(ctx["result"].total, 10, "2013-2020 finals exist in the data"),
                  expect(all(m.stage == "final" for m in ctx["result"].matches)),
              ))
        .run()
    )


def test_overlapping_sources_are_deduplicated(dataset):
    (
        Scenario(FEATURE, "The same fixture is never counted twice")
        .given("the match data is loaded", dataset=dataset)
        .when("I search all Série A matches for the 2019 season",
              result=lambda ctx: search_matches(
                  ctx["dataset"], competition="Brasileirão", season="2019"))
        .then("exactly one row per fixture is returned (380 for Série A 2019)",
              assertion=lambda ctx: expect_equal(
                  ctx["result"].total, 380,
                  f"got {ctx['result'].total}; sources must be double counting"))
        .run()
    )


def test_name_variants_return_the_same_fixtures(dataset):
    (
        Scenario(FEATURE, "Team name variants resolve to the same team")
        .given("the match data is loaded", dataset=dataset)
        .when("I search 'Palmeiras-SP' 2023 and 'Palmeiras' 2023",
              suffixed=lambda ctx: search_matches(
                  ctx["dataset"], team="Palmeiras-SP", season="2023"),
              plain=lambda ctx: search_matches(
                  ctx["dataset"], team="Palmeiras", season="2023"))
        .then("both queries return the same match set",
              assertion=lambda ctx: expect_equal(
                  ctx["suffixed"].total, ctx["plain"].total))
        .run()
    )


def test_ambiguous_team_name_is_reported(dataset):
    (
        Scenario(FEATURE, "Ambiguous team names surface candidates")
        .given("the match data is loaded", dataset=dataset)
        .when("I search matches for the ambiguous name 'Atletico'",
              result=lambda ctx: search_matches(ctx["dataset"], team="Atletico"))
        .then("a QueryError lists the Atlético clubs",
              assertion=lambda ctx: (
                  expect(isinstance(ctx.get("error"), QueryError),
                         "expected a QueryError for the ambiguous name"),
                  expect("ambiguous" in str(ctx["error"])),
                  expect(len(ctx["error"].alternatives) >= 3,
                         "MG, PR, GO, BA and AC variants should be listed"),
              ))
        .run()
    )


def test_unknown_team_name_is_reported(dataset):
    (
        Scenario(FEATURE, "Unknown team names fail gracefully")
        .given("the match data is loaded", dataset=dataset)
        .when("I search matches for a team that does not exist",
              result=lambda ctx: search_matches(ctx["dataset"], team="Gotham City FC"))
        .then("a QueryError is raised with a helpful message",
              assertion=lambda ctx: (
                  expect(isinstance(ctx.get("error"), QueryError)),
                  expect("No team found" in str(ctx["error"])),
              ))
        .run()
    )


def test_matches_from_a_specific_source_file(dataset):
    (
        Scenario(FEATURE, "Restricting a query to one source file")
        .given("the match data is loaded", dataset=dataset)
        .when("I search Série A 2019 in the historical file only",
              result=lambda ctx: search_matches(
                  ctx["dataset"], competition="Brasileirão", season="2019",
                  source="novo_campeonato_brasileiro"))
        .then("only rows from that file are returned",
              assertion=lambda ctx: (
                  expect_gt(ctx["result"].total, 300),
                  expect(all(
                      m.source == "novo_campeonato_brasileiro"
                      for m in ctx["result"].matches
                  )),
              ))
        .run()
    )
