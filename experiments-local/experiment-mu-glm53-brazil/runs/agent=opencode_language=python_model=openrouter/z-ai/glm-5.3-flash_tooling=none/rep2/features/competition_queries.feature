Feature: Competition Queries
  As an LLM using the Brazilian Soccer MCP server
  I want standings and competition statistics computed from match results
  So that I can answer questions about competitions and seasons

  Background:
    Given the Brazilian soccer data is loaded

  Scenario: Determine the 2019 Brasileirão champion
    When I request the standings for "Brasileirão Série A" season "2019"
    Then the champion should be "Flamengo"
    And the champion should have 90 points

  Scenario: Standings cover a complete season
    When I request the standings for "Brasileirão Série A" season "2019"
    Then the standings should contain 20 teams
    And every team should have played 38 matches

  Scenario: Relegation is annotated
    When I request the standings for "Brasileirão Série A" season "2020"
    Then the standings should mark 4 relegated teams

  Scenario: Competition statistics aggregate
    When I request statistics for competition "Copa Libertadores"
    Then I should receive average goals per match and home win rate
    And the number of matches should be greater than 1000

  Scenario: Unknown season fails gracefully
    When I request the standings for "Brasileirão Série A" season "1999"
    Then the response should indicate no matches were found
