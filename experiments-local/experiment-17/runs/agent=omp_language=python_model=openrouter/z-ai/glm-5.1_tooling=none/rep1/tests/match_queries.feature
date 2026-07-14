Feature: Match Queries

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Find matches by competition
    Given the match data is loaded
    When I search for matches in competition "Libertadores"
    Then I should receive matches from that competition only

  Scenario: Find matches by date range
    Given the match data is loaded
    When I search for matches from "2023-01-01" to "2023-12-31"
    Then I should receive matches within that date range
