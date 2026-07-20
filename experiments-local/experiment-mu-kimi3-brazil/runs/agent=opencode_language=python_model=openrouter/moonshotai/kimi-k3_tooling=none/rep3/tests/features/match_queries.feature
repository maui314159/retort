Feature: Match Queries
  As an LLM client of the MCP server
  I want to find matches by team, opponent, competition, season and date
  So that I can answer questions like "Show me all Flamengo vs Fluminense matches"

  Background:
    Given the match data is loaded

  Scenario: Find matches between two teams
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    And every match should involve both "Flamengo" and "Fluminense"

  Scenario: Find matches a team played in a season
    When I search for matches of "Palmeiras" in season 2021
    Then I should receive at least 38 matches
    And every match should involve "Palmeiras"

  Scenario: Filter matches by competition
    When I search for matches of "Flamengo" in competition "Copa do Brasil"
    Then every returned match should be from competition "Copa do Brasil"
    And every match should involve "Flamengo"

  Scenario: Filter matches by date range
    When I search for matches of "Corinthians" between "2022-01-01" and "2022-12-31"
    Then every returned match date should be within "2022-01-01" and "2022-12-31"

  Scenario: Head-to-head balance between rivals
    When I compare "Palmeiras" and "Santos" head-to-head
    Then the summary should contain wins for both teams and draws
    And the summary counts should add up to the total number of matches

  Scenario: Unknown team returns no matches
    When I search for matches of "Nonexistent FC" in season 2019
    Then I should receive an empty list of matches

  Scenario: Team name variations resolve to the same club
    When I search for matches of "Flamengo-RJ" in competition "Brasileirão" and season 2019
    And I search for matches of "Flamengo" in competition "Brasileirão" and season 2019
    Then both searches should return the same number of matches

  Scenario: Find Copa Libertadores finals
    When I search for matches in competition "Libertadores" at stage "final"
    Then I should receive a list of matches
    And every returned match should be at stage "final"
