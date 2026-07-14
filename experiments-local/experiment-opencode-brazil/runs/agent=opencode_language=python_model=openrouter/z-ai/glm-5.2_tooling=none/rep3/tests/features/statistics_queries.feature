Feature: Statistical Analysis
  As a soccer analyst
  I want to compute aggregate statistics
  So that I can understand trends across the dataset.

  Scenario: Average goals per match
    Given the match data is loaded
    When I request average goals for competition "Brasileirao Serie A"
    Then I should receive an average goals value greater than zero
    And the home win rate should be between 0 and 100

  Scenario: Biggest wins in the dataset
    Given the match data is loaded
    When I request the top 5 biggest wins
    Then I should receive at most 5 results
    And each result should have a winner, loser, score, and margin

  Scenario: Biggest wins are sorted by margin descending
    Given the match data is loaded
    When I request the top 10 biggest wins in "Libertadores"
    Then the margins should be sorted in descending order
