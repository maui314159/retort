Feature: Match Queries
  Verify that match queries return correct data across all CSV datasets.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Find matches by team and season
    Given the match data is loaded
    When I search for matches with team "Palmeiras" in season 2023
    Then I should receive at least 1 match
    And each match should involve team containing "Palmeiras"

  Scenario: Find matches by competition
    Given the match data is loaded
    When I search for matches in competition "Libertadores"
    Then I should receive at least 1 match
    And each match competition should contain "Libertadores"
