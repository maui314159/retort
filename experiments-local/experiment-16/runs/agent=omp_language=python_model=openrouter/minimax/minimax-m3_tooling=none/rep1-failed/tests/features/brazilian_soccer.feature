Feature: Brazilian Soccer MCP Server

  Background:
    Given the match and player data is loaded

  Scenario: Find matches between two teams
    When I search for matches between "Flamengo" and "Fluminense" in season 2023
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get team statistics
    When I request statistics for "Palmeiras" in season 2022
    Then I should receive wins, losses, draws, and goals

  Scenario: Get head-to-head record
    When I compare "Flamengo" and "Fluminense" head-to-head in season 2023
    Then I should receive a summary with wins and draws

  Scenario: Search players by nationality
    When I search for Brazilian players
    Then I should receive players with Brazilian nationality

  Scenario: Search players by club
    When I search for players at "Real Madrid"
    Then I should receive players whose club contains "Real Madrid"

  Scenario: Compute league standings
    When I request the 2019 Brasileirão standings
    Then I should receive a ranked list of teams with points
    And every team should have played 38 matches

  Scenario: Identify biggest wins
    When I request the biggest wins in the Brasileirão 2022
    Then I should receive matches ordered by goal difference

  Scenario: Calculate goals per match
    When I request the average goals per match for Brasileirão 2023
    Then I should receive a positive average
    And total goals should equal the sum of home and away goals

  Scenario: Find last match between teams
    When I search for the last match between "Flamengo" and "Corinthians"
    Then I should receive the most recent match

  Scenario: Filter matches by competition
    When I search for matches in the "Copa do Brasil" in season 2023
    Then I should receive only Copa do Brasil matches

  Scenario: Identify relegated teams
    When I request the relegated teams for the 2019 Brasileirão
    Then I should receive four relegated teams
    And the champion of the season should be Flamengo

  Scenario: Team name normalization
    When I search for "São Paulo" and "Sao Paulo"
    Then both queries should resolve to the same team key
