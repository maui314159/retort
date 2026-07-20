Feature: Match Queries
  As a user of the Brazilian Soccer MCP server
  I want to find matches by team, date and competition
  So that I can answer questions about specific games

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Find matches a team played in a season
    Given the match data is loaded
    When I search for matches of "Palmeiras" in season 2023
    Then every match should involve "Palmeiras"
    And every match should be from season 2023

  Scenario: Find Copa do Brasil finals
    Given the match data is loaded
    When I search for "Copa do Brasil" finals
    Then I should receive a list of matches
    And each match should be from "Copa do Brasil"

  Scenario: Find Copa Libertadores finals
    Given the match data is loaded
    When I search for "Copa Libertadores" finals
    Then every match should have stage "final"

  Scenario: Find matches in a date range
    Given the match data is loaded
    When I search for "Flamengo" matches between "2023-01-01" and "2023-12-31"
    Then every match date should start with "2023"

  Scenario: Team name variations match consistently
    Given the match data is loaded
    When I search for matches of "São Paulo" and of "Sao Paulo-SP" in season 2019
    Then both searches should return the same number of matches
