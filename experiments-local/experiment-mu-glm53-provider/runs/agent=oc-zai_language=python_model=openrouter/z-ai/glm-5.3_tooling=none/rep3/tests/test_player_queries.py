"""
BDD scenarios: player queries over the FIFA database
(TASK.md "Required Capabilities" #3) and cross-file club matching.
"""

from __future__ import annotations

from soccer_mcp.bdd import Scenario, expect, expect_equal, expect_gt
from soccer_mcp.queries import QueryError, search_players, top_players

FEATURE = "Player Queries"


def test_find_player_by_name(dataset):
    (
        Scenario(FEATURE, "Who is Gabriel Jesus?")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I search players named 'Gabriel Jesus'",
              players=lambda ctx: search_players(ctx["dataset"], name="Gabriel Jesus")[0])
        .then("the Manchester City forward is returned",
              assertion=lambda ctx: (
                  expect_gt(len(ctx["players"]), 0),
                  expect(any("Gabriel Jesus" in p.name for p in ctx["players"])),
              ))
        .run()
    )


def test_player_not_in_database_is_reported(dataset):
    (
        Scenario(FEATURE, "Players outside the FIFA dataset are reported honestly")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I search players named 'Gabriel Barbosa'",
              players=lambda ctx: search_players(ctx["dataset"], name="Gabriel Barbosa")[0])
        .then("no players are returned (he is not in this FIFA-era dataset)",
              assertion=lambda ctx: expect_equal(len(ctx["players"]), 0))
        .run()
    )


def test_top_brazilian_players(dataset):
    (
        Scenario(FEATURE, "Who are the top Brazilian players?")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I list the top Brazilians by overall rating",
              players=lambda ctx: top_players(
                  ctx["dataset"], nationality="Brazil", limit=10)[0])
        .then("only Brazilians are returned, sorted by rating",
              assertion=lambda ctx: (
                  expect_equal(len(ctx["players"]), 10),
                  expect(all(p.nationality == "Brazil" for p in ctx["players"])),
                  expect(ctx["players"][0].overall >= ctx["players"][-1].overall),
                  expect_gt(ctx["players"][0].overall, 85,
                            "a 88+ rated Brazilian should top the list"),
              ))
        .run()
    )


def test_players_at_a_brazilian_club(dataset):
    (
        Scenario(FEATURE, "Which players play for Santos?")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I search players at club 'Santos'",
              players=lambda ctx: search_players(ctx["dataset"], club="Santos")[0])
        .then("players from Santos (SP) are returned",
              assertion=lambda ctx: (
                  expect_gt(len(ctx["players"]), 0),
                  expect(all(p.club == "Santos" for p in ctx["players"])),
              ))
        .run()
    )


def test_players_at_club_not_in_fifa_data(dataset):
    (
        Scenario(FEATURE, "Club absent from the FIFA database is reported honestly")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I search players at club 'Flamengo'",
              result=lambda ctx: search_players(ctx["dataset"], club="Flamengo"))
        .then("no players are returned and the club entity has no FIFA names",
              assertion=lambda ctx: (
                  expect_equal(len(ctx["result"][0]), 0),
                  expect_equal(ctx["result"][1].team_id, "flamengo rj"),
                  expect_equal(len(ctx["result"][1].fifa_club_names), 0),
              ))
        .run()
    )


def test_forwards_from_santos(dataset):
    (
        Scenario(FEATURE, "All forwards from a Brazilian club in the FIFA data")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I search forwards at club 'Santos'",
              players=lambda ctx: search_players(
                  ctx["dataset"], club="Santos", position="FWD")[0])
        .then("only forwards from Santos are returned",
              assertion=lambda ctx: (
                  expect_gt(len(ctx["players"]), 0),
                  expect(all(
                      (p.position in {"ST", "LS", "RS", "CF", "LW", "RW", "LF", "RF"})
                      and p.club == "Santos"
                      for p in ctx["players"]
                  )),
              ))
        .run()
    )


def test_forwards_from_club_absent_in_fifa_data(dataset):
    (
        Scenario(FEATURE, "São Paulo FC squads are not in the FIFA-era dataset")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I search forwards at club 'São Paulo'",
              result=lambda ctx: search_players(
                  ctx["dataset"], club="São Paulo", position="FWD"))
        .then("the club resolves but no players are returned",
              assertion=lambda ctx: (
                  expect_equal(ctx["result"][1].team_id, "sao paulo sp"),
                  expect_equal(len(ctx["result"][0]), 0),
              ))
        .run()
    )


def test_filter_by_minimum_rating_and_age(dataset):
    (
        Scenario(FEATURE, "Filters: min rating and max age")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I search Brazilians with overall >= 85 and age <= 25",
              players=lambda ctx: search_players(
                  ctx["dataset"], nationality="Brazil",
                  min_overall=85, max_age=25)[0])
        .then("every result satisfies both filters",
              assertion=lambda ctx: (
                  expect_gt(len(ctx["players"]), 0),
                  expect(all(
                      p.nationality == "Brazil" and p.overall >= 85
                      and p.age is not None and p.age <= 25
                      for p in ctx["players"]
                  )),
              ))
        .run()
    )


def test_top_players_by_skill_attribute(dataset):
    (
        Scenario(FEATURE, "Top players by a specific skill")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I rank Brazilians by 'Finishing'",
              players=lambda ctx: top_players(
                  ctx["dataset"], nationality="Brazil",
                  attribute="Finishing", limit=5)[0])
        .then("results are ordered by the finishing attribute",
              assertion=lambda ctx: (
                  expect_equal(len(ctx["players"]), 5),
                  expect(all(p.skills.get("Finishing", 0) > 80 for p in ctx["players"])),
                  expect(ctx["players"][0].skills["Finishing"]
                         >= ctx["players"][-1].skills["Finishing"]),
              ))
        .run()
    )


def test_player_search_requires_a_filter(dataset):
    (
        Scenario(FEATURE, "Unfiltered player search is rejected")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I search players with no filters at all",
              players=lambda ctx: search_players(ctx["dataset"]))
        .then("a QueryError asks for at least one filter",
              assertion=lambda ctx: (
                  expect(isinstance(ctx.get("error"), QueryError)),
                  expect("at least one filter" in str(ctx["error"]).lower()),
              ))
        .run()
    )


def test_cross_file_club_matching(dataset):
    (
        Scenario(FEATURE, "Club names match across FIFA and match data")
        .given("the FIFA player database is loaded", dataset=dataset)
        .when("I resolve several Brazilian clubs in the registry",
              gremio=lambda ctx: ctx["dataset"].registry.resolve("Grêmio"),
              inter=lambda ctx: ctx["dataset"].registry.resolve("Internacional"),
              sport=lambda ctx: ctx["dataset"].registry.resolve("Sport Club do Recife"))
        .then("each resolves to the match-data team and carries its FIFA club name",
              assertion=lambda ctx: (
                  expect_equal(ctx["gremio"].team.team_id, "gremio rs"),
                  expect("Grêmio" in ctx["gremio"].team.fifa_club_names),
                  expect_equal(ctx["inter"].team.team_id, "internacional rs"),
                  expect_equal(ctx["sport"].team.team_id, "sport pe"),
                  expect("Sport Club do Recife" in ctx["sport"].team.fifa_club_names),
              ))
        .run()
    )
