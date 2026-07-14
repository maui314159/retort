Feature: Team Queries
  As an analyst
  I want win/loss/draw records and head-to-head comparisons
  So that I can evaluate team performance

  Background:
    Given the knowledge base is loaded

  Scenario: Get a team's home record for a season
    When I request the home record for "Corinthians" in the "Brasileirão" season "2022"
    Then I should receive wins, losses, draws, and goals
    And the wins, draws and losses should sum to the matches played
    And the win rate should be between 0 and 100

  Scenario: Points are computed as three per win plus one per draw
    When I request the record for "Flamengo" in the "Brasileirão" season "2019"
    Then the points should equal three times the wins plus the draws

  Scenario: Compare two teams head-to-head
    When I compare "Palmeiras" and "Santos" head-to-head
    Then the team A wins, team B wins and draws should sum to the total matches
    And the total matches should be greater than 0

  Scenario: Head-to-head is symmetric
    When I compare "Palmeiras" and "Santos" head-to-head
    And I compare "Santos" and "Palmeiras" head-to-head
    Then both comparisons should report the same total matches
