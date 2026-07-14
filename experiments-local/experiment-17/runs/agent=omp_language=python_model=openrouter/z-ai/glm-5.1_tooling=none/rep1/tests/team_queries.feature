Feature: Team Queries

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2023
    Then I should receive wins, losses, draws, and goals

  Scenario: Head-to-head comparison
    Given the match data is loaded
    When I compare "Flamengo" and "Fluminense" head-to-head
    Then I should receive win counts for both teams and draws

  Scenario: Team home record
    Given the match data is loaded
    When I request home-only statistics for "Corinthians"
    Then I should receive statistics for home matches only
