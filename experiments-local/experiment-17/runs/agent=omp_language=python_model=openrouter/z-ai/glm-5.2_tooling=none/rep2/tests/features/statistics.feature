Feature: Statistical Analysis
  As a soccer analyst
  I want to compute aggregated statistics across matches
  So that I can identify trends, records and extremes.

  Scenario: Average goals per match
    Given the match data is loaded
    When I request average goals for "Brasileirão" in season 2019
    Then the average goals should be between 2 and 3
    And the win rates should sum to 1

  Scenario: Biggest wins
    Given the match data is loaded
    When I request the 5 biggest wins
    Then I should receive at most 5 results
    And the results should be sorted by margin descending
    And every margin should be at least 5

  Scenario: Best home record
    Given the match data is loaded
    When I request the best home record in "Brasileirão Serie A" for season 2023
    Then I should receive a ranked list
    And the win rates should be descending

  Scenario: Derbies in a season
    Given the match data is loaded
    When I request derbies for season 2023
    Then every derby match should have a derby label
    And each derby should be between a known rival pair
