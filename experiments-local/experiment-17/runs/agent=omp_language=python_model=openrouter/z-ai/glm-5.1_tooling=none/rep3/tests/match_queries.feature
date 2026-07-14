Feature: Match Queries
  Query matches by team, opponent, competition, season, and date range.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Find matches by team and season
    Given the match data is loaded
    When I search for matches with team "Palmeiras" in season 2023
    Then I should receive matches only from season 2023

  Scenario: Find matches by competition
    Given the match data is loaded
    When I search for matches in competition "Copa do Brasil"
    Then all results should be from Copa do Brasil

  Scenario: Search matches with date range
    Given the match data is loaded
    When I search for matches from "2023-01-01" to "2023-12-31"
    Then all results should be within that date range

  Scenario: Head-to-head between two teams
    Given the match data is loaded
    When I request head-to-head between "Flamengo" and "Fluminense"
    Then I should receive wins draws and losses for each team
