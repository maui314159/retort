Feature: Competition Queries
  As a user of the Brazilian Soccer MCP server
  I want standings and competition level information
  So that I can answer questions like "who won the Brasileirão?"

  Scenario: Standings for a season
    Given the match data is loaded
    When I request the 2019 Brasileirão standings
    Then the champion should be Flamengo
    And the champion should have 90 points

  Scenario: Standings completeness
    Given the match data is loaded
    When I request the 2019 Brasileirão standings
    Then there should be 20 teams
    And each team should have wins, draws, losses and points
    And the standings should be sorted by points descending
