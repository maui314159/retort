Feature: Match Queries
  As a soccer analyst
  I want to search match data by team, opponent, competition and season
  So that I can answer questions about fixtures and results.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    And every match should involve either "Flamengo" or "Fluminense"

  Scenario: Filter matches by team and season
    Given the match data is loaded
    When I search for matches of team "Palmeiras" in season 2023
    Then I should receive a list of matches
    And every match should be in season 2023
    And every match should involve "Palmeiras"

  Scenario: Filter matches by competition
    Given the match data is loaded
    When I search for matches in competition "Copa do Brasil" in season 2021
    Then every match should have competition "Copa do Brasil"

  Scenario: Last match between two teams
    Given the match data is loaded
    When I request the last match between "Flamengo" and "Corinthians"
    Then I should receive a single match
    And the match should have a date and scores

  Scenario: Matches are deduplicated across overlapping sources
    Given the match data is loaded
    When I request statistics for "Flamengo" in season 2019 and competition "Brasileirão"
    Then the matches played should be at most 38
