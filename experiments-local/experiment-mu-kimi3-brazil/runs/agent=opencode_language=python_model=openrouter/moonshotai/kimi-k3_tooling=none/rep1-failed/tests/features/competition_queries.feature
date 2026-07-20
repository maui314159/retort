Feature: Competition Queries
  As a user of the Brazilian Soccer MCP server
  I want standings calculated from match results
  So that I can answer questions about seasons and champions

  Scenario: 2019 Brasileirão champion
    Given the match data is loaded
    When I request the standings for season 2019
    Then the champion should be "Flamengo" with 90 points

  Scenario: Standings are arithmetically consistent
    Given the match data is loaded
    When I request the standings for season 2018
    Then every row should satisfy points equals 3 per win plus 1 per draw

  Scenario: List available competitions
    Given the match data is loaded
    When I list the competitions
    Then the list should include "Brasileirão Série A", "Copa do Brasil" and "Copa Libertadores"

  Scenario: List teams of a season
    Given the match data is loaded
    When I list the teams of "Brasileirão Série A" season 2019
    Then there should be 20 teams
