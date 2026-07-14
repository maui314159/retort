Feature: Team Queries
  As a soccer analyst
  I want to compute team statistics
  So that I can compare performance across seasons and venues.

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2023
    Then I should receive wins, losses, draws, and goals
    And the matches count should equal wins plus draws plus losses

  Scenario: Home record for a team
    Given the match data is loaded
    When I request home statistics for "Corinthians" in season 2022
    Then the venue should be home
    And the win rate should be between 0 and 100

  Scenario: Compare two teams head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos"
    Then I should receive statistics for both teams
    And I should receive a head-to-head summary

  Scenario: Home vs away record split
    Given the match data is loaded
    When I request the home vs away record for "Flamengo" in season 2023
    Then I should receive separate home and away statistics
