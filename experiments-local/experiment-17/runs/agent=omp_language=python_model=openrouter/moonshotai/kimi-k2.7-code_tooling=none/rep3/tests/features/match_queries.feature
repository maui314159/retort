Feature: Match Queries
  As a soccer analyst
  I want to search match data
  So that I can answer questions about Brazilian football matches

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Find matches for a team in a season
    Given the match data is loaded
    When I search for matches for "Palmeiras" in season "2023"
    Then I should receive matches only from season "2023"

  Scenario: Find matches by competition
    Given the match data is loaded
    When I search for "Copa do Brasil" matches
    Then all returned matches should have competition "Copa do Brasil"
