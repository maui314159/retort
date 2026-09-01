# language: en
Feature: Team Queries
  As an MCP client I want team records, histories and head-to-head comparisons

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
    And the win rate should be consistent with the record

  Scenario: Get a team's home record
    Given the match data is loaded
    When I request the home record of "Corinthians" in the "Brasileirão Serie A" in season "2022"
    Then I should receive wins, losses, draws, and goals
    And all matches should be home matches

  Scenario: Compare Palmeiras and Santos head-to-head
    Given the match data is loaded
    When I request the head-to-head record of "Palmeiras" and "Santos"
    Then the head-to-head should include wins, draws and goals for both teams

  Scenario: Team history across competitions
    Given the match data is loaded
    When I request the history of "Palmeiras"
    Then the competitions should include "Brasileirão Serie A", "Copa do Brasil" and "Copa Libertadores"

  Scenario: Unknown team is reported, not crashed on
    Given the match data is loaded
    When I request statistics for "Narnia United"
    Then a not-found error should be raised
