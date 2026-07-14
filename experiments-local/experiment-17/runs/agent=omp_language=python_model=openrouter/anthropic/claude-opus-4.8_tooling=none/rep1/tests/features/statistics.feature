Feature: Statistical Analysis
  As an analyst
  I want aggregated statistics and rankings
  So that I can answer analytical questions about the data

  Background:
    Given the knowledge base is loaded

  Scenario: Average goals per match in a season
    When I compute statistics for "Brasileirão" season "2019"
    Then the average goals per match should be between 2 and 3
    And the home, away and draw win rates should sum to about 100 percent

  Scenario: Biggest wins are ordered by margin
    When I find the 10 biggest wins overall
    Then the results should be ordered by goal margin descending
    And the largest margin should be at least 5

  Scenario: Best home record in a season
    When I rank teams by "win_rate" for home matches in "Brasileirão" season "2019"
    Then the first ranked team should be "Flamengo"
    And every ranked team should have played at least 5 matches

  Scenario: A simple lookup responds quickly
    When I time a head-to-head lookup for "Flamengo" and "Corinthians"
    Then the lookup should complete in under 2 seconds
