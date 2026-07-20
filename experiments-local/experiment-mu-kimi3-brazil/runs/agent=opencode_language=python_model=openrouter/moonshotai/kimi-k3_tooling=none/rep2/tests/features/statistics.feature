Feature: Statistical Analysis
  The MCP server aggregates statistics across the datasets.

  Scenario: Biggest wins are sorted by margin
    Given the match data is loaded
    When I request the 5 biggest wins
    Then I should receive exactly 5 matches
    And the victory margins should be sorted descending

  Scenario: Average goals and win rates
    Given the match data is loaded
    When I request aggregate stats for competition "Brasileirão"
    Then the average goals per match should be greater than 2.0
    And home, draw and away rates should sum to 100 percent

  Scenario: Aggregate stats for a single season
    Given the match data is loaded
    When I request aggregate stats for competition "Brasileirão" season 2019
    Then the match count should be 380

  Scenario: Cross-file query combining player and match data
    Given the match data is loaded
    And the player data is loaded
    When I search players at club "Santos" and matches for team "Santos"
    Then both queries should return results

  Scenario: Query performance
    Given the match data is loaded
    Then a simple lookup should respond in under 2 seconds
    And an aggregate query should respond in under 5 seconds
