Feature: Team Queries
  As a user of the Brazilian Soccer MCP server
  I want team records and head-to-head statistics
  So that I can compare clubs

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals

  Scenario: Home record for a team
    Given the match data is loaded
    When I request the home record of "Corinthians" in season "2019"
    Then the record should show 19 matches

  Scenario: Compare two teams head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then the wins, draws and losses should add up to the matches played

  Scenario: List the competitions a team played in
    Given the match data is loaded
    When I ask which competitions "Flamengo" played in
    Then the answer should include "Brasileirão Série A", "Copa do Brasil" and "Copa Libertadores"
