Feature: Team Queries
  As a soccer analyst
  I want to retrieve team statistics
  So that I can evaluate team performance

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
    And the team name should be normalized to "Palmeiras"

  Scenario: Compare teams head-to-head
    Given the match data is loaded
    When I compare "Corinthians" and "Sao Paulo" head-to-head
    Then I should receive a win count for each team and draws

  Scenario: List all teams
    Given the match data is loaded
    When I list all teams
    Then I should see canonical team names including "Flamengo"
