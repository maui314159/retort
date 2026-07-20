Feature: Competition Queries
  As a user I want standings calculated from match results
  so that I can answer "Who won the 2019 Brasileirão?" and
  "Which teams were relegated in 2020?".

  Scenario: Champion of the 2019 Brasileirão
    Given the match data is loaded
    When I request the "2019" "Brasileirão Série A" standings
    Then the table should contain 20 teams
    And "Flamengo" should be the champion

  Scenario: Relegation in the 2020 Brasileirão
    Given the match data is loaded
    When I request the "2020" "Brasileirão Série A" standings
    Then 4 teams should be marked as relegated
    And "Botafogo" should be relegated

  Scenario: List available competitions
    Given the match data is loaded
    When I list the competitions
    Then the list should include "Brasileirão Série A"
    And the list should include "Copa do Brasil"
    And the list should include "Copa Libertadores"
