Feature: Statistical Analysis
  As a data analyst
  I want to calculate aggregate statistics
  So that I can understand trends in Brazilian soccer

  Scenario: Get average goals for a competition
    Given the match data is loaded
    When I request average goals for competition "Brasileirão"
    Then I should receive the average goals per match
    And the average should be greater than 2.0

  Scenario: Get biggest victories
    Given the match data is loaded
    When I request the biggest victories
    Then I should receive a list of matches
    And each match should have a score

  Scenario: Get best home records
    Given the match data is loaded
    When I request the best home records in competition "Brasileirão" in season 2019
    Then I should receive a ranked list of teams by win rate

  Scenario: Team name normalization works
    Given the match data is loaded
    When I search for matches for team "Flamengo-RJ"
    Then I should receive matches
    And the matches should include team "Flamengo"
