Feature: Match Queries
  As an LLM user I want to find matches by team, competition,
  season and date so I can answer questions about results.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Find matches of a team in one season
    Given the match data is loaded
    When I search for matches of "Palmeiras" in season "2022"
    Then I should receive a list of matches
    And every match should be from season 2022
    And every match should involve "Palmeiras"

  Scenario: Find matches by competition
    Given the match data is loaded
    When I search for "Copa do Brasil" matches in season "2023"
    Then I should receive a list of matches
    And every match should be from competition "Copa do Brasil"

  Scenario: Find matches by date range
    Given the match data is loaded
    When I search for matches from "01/09/2023" to "30/09/2023"
    Then I should receive a list of matches
    And every match date should be in "2023-09"

  Scenario: Team name variations resolve to the same team
    Given the match data is loaded
    When I compare match counts for "Palmeiras-SP" and "Palmeiras"
    Then both counts should be equal and positive

  Scenario: Unknown team returns a helpful error
    Given the match data is loaded
    When I search for matches of "Wakanda United"
    Then I should receive an unknown team error
