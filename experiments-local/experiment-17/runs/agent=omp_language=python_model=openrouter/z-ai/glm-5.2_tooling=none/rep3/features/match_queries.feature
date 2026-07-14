Feature: Match Queries
  As a soccer fan I want to search matches by team, opponent, competition,
  season and date range so I can answer questions about fixtures.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Filter matches by competition and season
    Given the match data is loaded
    When I search for matches with competition "Libertadores" and season 2019
    Then every returned match should be from competition "Copa Libertadores"
    And every returned match should be from season 2019

  Scenario: Filter matches by date range
    Given the match data is loaded
    When I search for matches from "2019-06-01" to "2019-06-30"
    Then every returned match should be dated between "2019-06-01" and "2019-06-30"

  Scenario: Filter matches by venue
    Given the match data is loaded
    When I search for "Flamengo" home matches in season 2019
    Then every returned match should have "Flamengo" as the home side

  Scenario: Limit the number of returned matches
    Given the match data is loaded
    When I search for matches with limit 5
    Then I should receive at most 5 matches
