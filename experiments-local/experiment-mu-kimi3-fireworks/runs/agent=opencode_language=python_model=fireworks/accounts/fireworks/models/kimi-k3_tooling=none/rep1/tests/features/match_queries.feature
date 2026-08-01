Feature: Match Queries
  As a user of the Brazilian Soccer MCP server
  I want to find matches by team, competition, season and date
  So that I can answer questions like "Show me all Flamengo vs Fluminense matches"

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: The Fla-Flu derby is recognized
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then the result should mention "Fla-Flu"

  Scenario: Find matches a team played in a season
    Given the match data is loaded
    When I search for matches of "Palmeiras" in season 2023
    Then I should receive a list of matches
    And every match should involve "Palmeiras"

  Scenario: Find all Copa do Brasil finals
    Given the match data is loaded
    When I search for "Copa do Brasil" matches at stage "final"
    Then I should receive at least 15 matches
    And every match should be a "final"

  Scenario: Find Libertadores knockout matches
    Given the match data is loaded
    When I search for "Libertadores" matches at stage "semifinals"
    Then I should receive a list of matches
    And every match should be in "Copa Libertadores"

  Scenario: Find matches in a date range
    Given the match data is loaded
    When I search for "Santos" matches between "2019-01-01" and "2019-06-30"
    Then I should receive a list of matches
    And every match date should be within the range

  Scenario: When did Flamengo last play Corinthians
    Given the match data is loaded
    When I ask for the most recent match between "Flamengo" and "Corinthians"
    Then the result should mention "Flamengo"
    And the result should mention "Corinthians"
    And the result should mention a score

  Scenario: Show me all derbies in 2023
    Given the match data is loaded
    When I search for derby matches in season 2023
    Then I should receive at least 10 matches
    And every match should be a named derby

  Scenario: Team name variations resolve consistently
    Given the match data is loaded
    When I search for matches of "Palmeiras-SP" in season 2022
    Then the search should find as many matches as searching for "palmeiras"

  Scenario: Unknown teams produce a helpful error
    Given the match data is loaded
    When I search for matches of "Not A Real Club FC"
    Then the search should report an unknown team
