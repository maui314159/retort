Feature: Match Queries
  As a soccer analyst
  I want to query Brazilian soccer match data
  So that I can answer natural-language questions about matches

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2022"
    Then I should receive wins, losses, draws, and goals
    And the played count should be greater than zero

  Scenario: Head-to-head comparison
    Given the match data is loaded
    When I compare "Flamengo" and "Fluminense" head-to-head
    Then I should receive wins, draws, and goals for both teams
    And the matches played should be greater than zero

  Scenario: Filter matches by competition
    Given the match data is loaded
    When I search for matches in competition "Copa do Brasil"
    Then every returned match should belong to "Copa do Brasil"
