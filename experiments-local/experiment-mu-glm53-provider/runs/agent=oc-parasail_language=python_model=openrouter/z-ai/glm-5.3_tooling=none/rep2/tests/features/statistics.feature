Feature: Statistical Analysis
  As a soccer fan asking natural-language questions
  I want aggregated statistics across the datasets
  So that I can answer analytical questions about Brazilian soccer

  Scenario: Average goals in the Brasileirão
    Given the match data is loaded
    When I request goal averages for "Série A"
    Then the average goals per match should be between 2.0 and 3.0
    And the home win rate should exceed the away win rate

  Scenario: Biggest wins in the dataset
    Given the match data is loaded
    When I request the 5 biggest wins
    Then the largest victory margin should be at least 8 goals
    And the matches should be sorted by margin descending

  Scenario: Derbies in a season
    Given the match data is loaded
    When I request the derbies of season 2023
    Then every match should be between traditional rivals
    And the Fla-Flu derby should appear
    And the Choque-Rei derby should appear

  Scenario: Top scoring teams in a season
    Given the match data is loaded
    When I request the top scoring teams for "Série A" in 2019
    Then Flamengo should be among the top scoring teams

  Scenario: Home advantage across the dataset
    Given the match data is loaded
    When I request goal averages for all competitions
    Then more than 40 percent of matches should be home wins
    And fewer than 35 percent of matches should be away wins
