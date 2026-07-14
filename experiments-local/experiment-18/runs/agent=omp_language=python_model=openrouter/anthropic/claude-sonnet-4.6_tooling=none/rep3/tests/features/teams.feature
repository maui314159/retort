Feature: Team Queries
  As an analyst
  I want win/loss records and head-to-head comparisons
  So that I can evaluate team performance

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2019
    Then I should receive wins, losses, draws, and goals
    And the number of matches should equal wins plus draws plus losses

  Scenario: Home record for a team in a season
    Given the match data is loaded
    When I request the home record for "Corinthians" in season 2022
    Then the win rate should be between 0 and 1
    And goals for and goals against should be non-negative

  Scenario: Compare two teams head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then wins, draws and goals should be consistent with the meetings

  Scenario: Distinguish same-named clubs by state
    Given the match data is loaded
    When I resolve the teams "Atletico-MG" and "Atletico-GO"
    Then they should resolve to different teams
