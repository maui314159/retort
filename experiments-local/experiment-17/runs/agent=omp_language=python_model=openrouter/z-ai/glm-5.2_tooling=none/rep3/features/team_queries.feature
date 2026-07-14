Feature: Team Queries
  As a soccer fan I want team statistics and head-to-head comparisons.

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2019
    Then I should receive wins, losses, draws, and goals
    And the wins plus draws plus losses should equal the matches played

  Scenario: Head-to-head between two rivals
    Given the match data is loaded
    When I compare "Flamengo" and "Fluminense" head-to-head
    Then I should receive the matches played count
    And the sum of wins and draws should equal the matches played

  Scenario: Team name variants resolve to the same club
    Given the match data is loaded
    When I request statistics for "Flamengo-RJ" in season 2019
    And I request statistics for "Flamengo" in season 2019
    Then the statistics should be identical

  Scenario: Team competitions listing
    Given the match data is loaded
    When I list competitions for "Palmeiras"
    Then the result should include at least one competition
