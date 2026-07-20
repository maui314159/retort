Feature: Competition Queries
  As an LLM client of the MCP server
  I want standings and competition-level information
  So that I can answer questions like "Who won the 2019 Brasileirão?"

  Background:
    Given the match data is loaded

  Scenario: Calculate the 2019 Brasileirão standings
    When I request the standings of competition "Brasileirão Série A" for season 2019
    Then the standings should contain 20 teams
    And the champion should be "Flamengo" with 90 points
    And every team should have played 38 matches
    And points should equal 3 per win plus 1 per draw for every team

  Scenario: Relegation zone is the bottom four teams
    When I request the standings of competition "Brasileirão Série A" for season 2020
    Then the standings should contain 20 teams
    And the bottom 4 teams should occupy positions 17 to 20

  Scenario: Top scoring teams of a season
    When I request the top scoring teams of competition "Brasileirão Série A" for season 2021
    Then the first team should be "Flamengo" with 69 goals

  Scenario: List available competitions
    When I list the competitions
    Then the list should include "Brasileirão Série A", "Copa do Brasil" and "Copa Libertadores"
    And "Brasileirão Série A" should cover seasons 2003 to 2023
