Feature: Statistical Analysis
  As a soccer fan I want aggregate statistics.

  Scenario: Average goals per match
    Given the match data is loaded
    When I request average goals for "Brasileirão" season 2019
    Then the average goals per match should be between 1.5 and 4.0
    And the home win rate plus away win rate plus draw rate should be 100

  Scenario: Biggest wins
    Given the match data is loaded
    When I request the 5 biggest wins in "Brasileirão"
    Then I should receive at most 5 results
    And each win should have a positive margin
    And the margins should be sorted descending

  Scenario: Best home record
    Given the match data is loaded
    When I request the best home record in "Brasileirão" season 2019
    Then every returned team should have played at least one home match
    And the win rates should be sorted descending

  Scenario: Derbies in a season
    Given the match data is loaded
    When I request derbies in season 2023
    Then each derby should involve two different rival teams

  Scenario: Average goals across all competitions
    Given the match data is loaded
    When I request average goals with no filters
    Then the matches count should be positive
