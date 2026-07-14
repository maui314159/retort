Feature: Match Queries
  As an analyst
  I want to find and summarize matches
  So that I can answer questions about fixtures and results

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have a date, scores, and competition
    And the head-to-head summary should account for all decided meetings

  Scenario: Find matches a team played in a season
    Given the match data is loaded
    When I search for "Palmeiras" matches in season 2019
    Then every returned match should involve "Palmeiras"
    And every returned match should be in season 2019

  Scenario: Restrict matches to a competition
    Given the match data is loaded
    When I search for "Flamengo" matches in competition "Copa Libertadores"
    Then every returned match should be in competition "Copa Libertadores"

  Scenario: Most recent meeting between two teams
    Given the match data is loaded
    When I ask for the last meeting between "Flamengo" and "Corinthians"
    Then I should get a single most recent match with a date
