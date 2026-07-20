Feature: Match Queries
  The MCP server finds matches by team, opponent, competition,
  season and date range, and compares teams head-to-head.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Filter matches by team and season
    Given the match data is loaded
    When I search matches for team "Palmeiras" in season 2021
    Then I should receive a list of matches
    And all returned matches should involve "Palmeiras"
    And all returned matches should be from season 2021

  Scenario: Filter matches by competition
    Given the match data is loaded
    When I search matches in competition "Copa do Brasil"
    Then I should receive a list of matches
    And all returned matches should be from competition "Copa do Brasil"

  Scenario: Filter matches by date range
    Given the match data is loaded
    When I search matches between "2021-01-01" and "2021-12-31"
    Then I should receive a list of matches
    And all returned matches should have dates between "2021-01-01" and "2021-12-31"

  Scenario: Head-to-head comparison
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then the summary should report wins for both teams and draws
    And the wins plus draws should equal the number of played matches
