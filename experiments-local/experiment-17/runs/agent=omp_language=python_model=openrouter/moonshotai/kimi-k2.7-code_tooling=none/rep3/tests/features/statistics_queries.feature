Feature: Statistical Analysis
  As a soccer analyst
  I want aggregate statistics
  So that I can analyze trends in Brazilian football

  Scenario: Average goals per match
    Given the match data is loaded
    When I request average goals for "Brasileirao"
    Then the result should contain a positive average goals value

  Scenario: Biggest wins
    Given the match data is loaded
    When I request the biggest "5" wins
    Then the returned matches should be ordered by goal margin descending

  Scenario: Compare two seasons
    Given the match data is loaded
    When I compare season "2022" and season "2023"
    Then I should receive statistics for both seasons
