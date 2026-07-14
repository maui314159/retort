Feature: Competition Queries
  The MCP server must compute standings and competition-level answers
  directly from match results.

  Background:
    Given the dataset is loaded

  Scenario: Get the 2019 Brasileirao champion
    When I ask for the "brasileirao_historical" 2019 standings
    Then the first row should be "Flamengo"

  Scenario: Get a season's top three
    When I ask for the "brasileirao" 2022 standings
    Then the table should be ordered by points then goal difference
    And the table should contain at least 4 teams
