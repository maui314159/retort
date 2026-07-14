Feature: Team Queries
  Verify that team statistics and head-to-head queries work correctly.

  Scenario: Get team statistics
    Given the team data is available
    When I request statistics for "Palmeiras" in season 2023
    Then I should receive wins, losses, draws, and goals
    And the total matches should equal wins plus draws plus losses

  Scenario: Compare teams head-to-head
    Given the team data is available
    When I compare "Palmeiras" and "Santos" head-to-head
    Then I should receive head-to-head results
