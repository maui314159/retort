Feature: Match Queries
  As a soccer analyst
  I want to search match data across competitions
  So that I can answer natural language questions about fixtures.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have a date, scores, and competition

  Scenario: Find matches by team and season
    Given the match data is loaded
    When I search for matches with team "Palmeiras" in season 2023
    Then I should receive a list of matches
    And every match should involve Palmeiras in 2023

  Scenario: Filter matches by competition
    Given the match data is loaded
    When I search for matches in competition "Libertadores"
    Then every match should belong to the Libertadores competition

  Scenario: Last match between two teams
    Given the match data is loaded
    When I request the last match between "Flamengo" and "Corinthians"
    Then I should receive a single match
    And the match should have a valid date

  Scenario: Head-to-head record
    Given the match data is loaded
    When I request the head-to-head record for "Flamengo" vs "Fluminense"
    Then I should receive wins, draws, losses, and goals
    And the total matches played should equal the sum of results
