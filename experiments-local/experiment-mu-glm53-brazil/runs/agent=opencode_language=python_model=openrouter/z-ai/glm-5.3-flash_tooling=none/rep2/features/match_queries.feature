Feature: Match Queries
  As an LLM using the Brazilian Soccer MCP server
  I want to find matches by team, competition, season and dates
  So that I can answer questions about fixtures and results

  Background:
    Given the Brazilian soccer data is loaded

  Scenario: Find matches between two teams
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores and competition
    And the result should include a head-to-head record

  Scenario: Team name variants resolve to the same matches
    When I search for matches between "Flamengo-RJ" and "Fluminense-RJ"
    Then the total number of matches should be the same as for "Flamengo" and "Fluminense"

  Scenario: Get matches for a team in a season
    When I search for matches for team "Palmeiras" in season 2022
    Then I should receive a list of matches
    And every match should be from season "2022"

  Scenario: Filter matches by date range
    When I search for matches for team "Corinthians" from "2022-07-01" to "2022-07-31"
    Then I should receive a list of matches
    And every match date should fall between "2022-07-01" and "2022-07-31"

  Scenario: Filter matches by competition
    When I search for matches for team "Palmeiras" in competition "Copa do Brasil"
    Then I should receive a list of matches
    And every match should be from competition "Copa do Brasil"

  Scenario: Find Libertadores finals by stage
    When I search for matches in competition "Copa Libertadores" with stage "final"
    Then I should receive a list of matches
    And every match should have stage "final"

  Scenario: Unknown team returns a graceful response
    When I search for matches for team "Atlético do Maranhão FC"
    Then the response should indicate no team was found
