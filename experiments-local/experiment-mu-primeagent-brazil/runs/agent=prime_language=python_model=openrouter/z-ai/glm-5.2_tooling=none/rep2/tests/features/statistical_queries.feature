Feature: Statistical Analysis
  As a user of the Brazilian Soccer MCP server
  I want aggregated statistics
  So that I can compare leagues, seasons and venues

  Scenario: Biggest wins
    Given the match data is loaded
    When I request the biggest wins in the Brasileirão
    Then I should receive a list sorted by goal margin descending
    And each result should name a winner, a loser and a score

  Scenario: Average goals
    Given the match data is loaded
    When I request average goals for the Brasileirão in 2019
    Then the average goals per match should be a positive number
    And the home win rate, away win rate and draw rate should sum to 100

  Scenario: Derbies
    Given the match data is loaded
    When I request derbies in season 2023
    Then I should receive at least one derby
    And every derby should be between traditional rivals
