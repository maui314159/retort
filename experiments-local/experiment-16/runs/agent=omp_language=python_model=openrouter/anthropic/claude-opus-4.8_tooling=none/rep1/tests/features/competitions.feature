Feature: Competition and Statistical Queries
  As an analyst I want standings and aggregate statistics computed from results
  so that I can answer questions about seasons and trends.

  Background:
    Given the soccer knowledge graph is loaded

  Scenario: Standings are computed from match results
    When I request the "Brasileirão" standings for season 2023
    Then the table should be ordered by points descending
    And points should equal wins times three plus draws

  Scenario: Average goals and home win rate are computed
    When I request the average goals for the "Brasileirão"
    Then the average goals per match should be greater than 0
    And the home win rate should be between 0 and 1

  Scenario: Biggest wins are ranked by goal margin
    When I request the biggest wins overall
    Then the first match should have the largest goal margin

  Scenario: Best home records rank teams by win rate
    When I request the best home records with at least 1 match
    Then the teams should be ordered by win rate descending
