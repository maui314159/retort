Feature: Statistical Analysis
  Calculate aggregated statistics across matches.

  Scenario: Average goals per match
    Given the match data is loaded
    When I request average goals per match
    Then the result should include total matches and average goals

  Scenario: Biggest wins
    Given the match data is loaded
    When I request the biggest wins
    Then I should receive results sorted by goal difference descending

  Scenario: Home vs away performance
    Given the match data is loaded
    When I request home vs away statistics
    Then I should receive home win rate and away win rate
