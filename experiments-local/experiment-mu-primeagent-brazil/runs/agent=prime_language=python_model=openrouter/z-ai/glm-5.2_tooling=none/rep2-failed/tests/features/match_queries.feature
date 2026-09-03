Feature: Match Queries
  As a user of the Brazilian Soccer MCP server
  I want to search the match data
  So that I can answer questions about historical Brazilian soccer matches

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have a date, scores and a competition

  Scenario: Find matches by team in a season
    Given the match data is loaded
    When I search for matches for team "Palmeiras" in season 2019
    Then I should receive at least one match
    And every match should be from season 2019
    And every match should involve Palmeiras

  Scenario: Find Copa do Brasil matches
    Given the match data is loaded
    When I search for matches in competition "Copa do Brasil"
    Then I should receive matches
    And every match should belong to the Copa do Brasil competition

  Scenario: Last match between two teams
    Given the match data is loaded
    When I ask for the last match between "Flamengo" and "Corinthians"
    Then I should receive a single match with a date and a score
