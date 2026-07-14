Feature: Match Queries
  The MCP server must answer natural-language questions about match data
  across the six supplied datasets.

  Background:
    Given the dataset is loaded

  Scenario: Find matches between two rival teams
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have a date, scores, and competition
    And the response should include head-to-head wins, draws and losses

  Scenario: Find matches for a single team in a season
    When I search for matches where "Palmeiras" played in 2023
    Then I should receive a list of matches
    And every match should involve Palmeiras

  Scenario: Find matches in a specific competition
    When I search for matches in the "libertadores" competition
    Then every returned match should be in libertadores
    And the response should be at most 200 matches

  Scenario: Find matches by date range
    When I search for matches in 2019-05
    Then every match should be within May 2019

  Scenario: Return the most recent match between two teams
    When I ask for the most recent match between "Flamengo" and "Corinthians"
    Then I should receive exactly one match
    And it should be the latest in the dataset
