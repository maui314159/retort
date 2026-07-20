Feature: Statistical Analysis
  As a user of the Brazilian Soccer MCP server
  I want aggregated statistics over the datasets
  So that I can answer analytical questions

  Scenario: Biggest victories are ordered by margin
    Given the match data is loaded
    When I ask for the 10 biggest wins
    Then the margins should be in non-increasing order

  Scenario: Average goals per match
    Given the match data is loaded
    When I ask for the overview of "Brasileirão Série A" season 2019
    Then the average goals per match should be between 1.5 and 4.0
    And home wins should be more frequent than away wins

  Scenario: Cross-file query with player and match data
    Given the match data is loaded
    When I count Brazilian players per club
    Then at least one Brazilian club should appear
