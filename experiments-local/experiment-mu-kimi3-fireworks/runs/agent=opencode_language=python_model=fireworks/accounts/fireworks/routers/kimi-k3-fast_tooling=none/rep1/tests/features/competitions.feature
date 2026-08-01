Feature: Competition Queries
  As an LLM user I want standings and brackets calculated from
  match results.

  Scenario: Who won the 2019 Brasileirão
    Given the match data is loaded
    When I request the 2019 "Brasileirão Série A" standings
    Then the champion should be "Flamengo" with 90 points
    And the table should have 20 teams

  Scenario: Standings are internally consistent
    Given the match data is loaded
    When I request the 2021 "Brasileirão Série A" standings
    Then every team should have played 38 matches
    And points should equal 3 per win plus 1 per draw

  Scenario: Relegation zone
    Given the match data is loaded
    When I request the 2019 "Brasileirão Série A" standings
    Then 4 teams should be marked as relegated

  Scenario: Copa Libertadores bracket
    Given the match data is loaded
    When I request the 2018 "Copa Libertadores" bracket
    Then the stages should include "group stage"
    And the stages should include "final"
