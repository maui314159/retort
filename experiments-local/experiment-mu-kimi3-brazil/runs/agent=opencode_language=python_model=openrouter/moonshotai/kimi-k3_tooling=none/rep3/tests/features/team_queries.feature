Feature: Team Queries
  As an LLM client of the MCP server
  I want team records and statistics
  So that I can answer questions like "What is Corinthians' home record in 2022?"

  Background:
    Given the match data is loaded

  Scenario: Get team home record for a season
    When I request home statistics for "Corinthians" in season 2022
    Then I should receive wins, losses, draws, and goals
    And the record should contain more than 0 matches
    And wins plus draws plus losses should equal matches played

  Scenario: Get team statistics for a whole season
    When I request statistics for "Palmeiras" in season 2021
    Then I should receive wins, losses, draws, and goals
    And the win rate should be between 0 and 100

  Scenario: Team statistics include a per-competition breakdown
    When I request statistics for "Flamengo" in season 2019
    Then the result should include statistics per competition
    And the breakdown should include "Brasileirão Série A"

  Scenario: List teams of a league season
    When I list the teams of competition "Brasileirão Série A" in season 2019
    Then I should receive exactly 20 teams
    And the list should include "Flamengo" and "Palmeiras"
