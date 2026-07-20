Feature: Team Queries
  The MCP server reports team records: wins, draws, losses and goals.

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2021"
    Then I should receive wins, losses, draws, and goals
    And matches should equal wins plus draws plus losses

  Scenario: Home record for a team
    Given the match data is loaded
    When I request statistics for "Corinthians" in season "2021" at "home"
    Then matches played should be greater than 0
    And the win rate should be between 0 and 100
    And goals for plus goals against should be consistent

  Scenario: Statistics filtered by competition
    Given the match data is loaded
    When I request statistics for "Flamengo" in competition "Copa Libertadores"
    Then matches played should be greater than 0
    And matches should equal wins plus draws plus losses
