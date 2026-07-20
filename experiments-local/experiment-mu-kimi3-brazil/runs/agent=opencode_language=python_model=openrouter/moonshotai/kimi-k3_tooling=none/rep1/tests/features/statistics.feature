Feature: Statistical Analysis
  As a user I want aggregated statistics
  so that I can answer "What's the average goals per match in the
  Brasileirão?" and "Show me the biggest wins in the dataset".

  Scenario: Average goals and home advantage
    Given the match data is loaded
    When I compute statistics for "Brasileirão Série A" in season "2019"
    Then the average goals per match should be reported
    And the home win rate should be reported

  Scenario: Biggest wins in the dataset
    Given the match data is loaded
    When I request the 5 biggest wins
    Then each entry should show winner, loser, score, and competition
    And the winning margins should be in descending order

  Scenario: Compare two seasons
    Given the match data is loaded
    When I compute statistics for "Brasileirão Série A" in seasons "2018" and "2019"
    Then both seasons should report average goals per match
