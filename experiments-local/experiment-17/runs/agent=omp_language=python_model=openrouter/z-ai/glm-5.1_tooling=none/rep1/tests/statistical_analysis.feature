Feature: Statistical Analysis

  Scenario: Average goals calculation
    Given the match data is loaded
    When I request average goals for competition "Brasileirão"
    Then I should receive average goals per match and home win rate

  Scenario: Biggest wins
    Given the match data is loaded
    When I request biggest wins
    Then I should receive matches sorted by goal difference
