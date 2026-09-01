Feature: Team Queries
  As an LLM using the Brazilian Soccer MCP server
  I want team records, comparisons and overviews
  So that I can answer questions about how teams performed

  Background:
    Given the Brazilian soccer data is loaded

  Scenario: Get team statistics for a season
    When I request statistics for "Palmeiras" in season "2022" in competition "Brasileirão Série A"
    Then I should receive wins, losses, draws and goals
    And the team should have played 38 matches

  Scenario: Team statistics with home venue split
    When I request statistics for "Corinthians" in season "2022" in competition "Brasileirão Série A" at venue "home"
    Then I should receive wins, losses, draws and goals
    And the team should have played 19 matches

  Scenario: Team name variations are normalized
    When I request statistics for "Palmeiras-SP" in season "2022" in competition "Brasileirão Série A"
    Then the resolved team should be "Palmeiras"

  Scenario: Compare two teams head-to-head
    When I compare "Palmeiras" and "Santos"
    Then I should receive statistics for both teams
    And I should receive a head-to-head record

  Scenario: Team overview includes cross-file player data
    When I request an overview for "Grêmio"
    Then the overview should include competitions and seasons
    And the overview should include FIFA players for the club

  Scenario: Unknown team statistics fail gracefully
    When I request statistics for "Nonexistent FC" in season "2022"
    Then the response should indicate no team was found
