Feature: Brazilian Soccer MCP Server

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense" in season 2023
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2022
    Then I should receive wins, losses, draws, and goals

  Scenario: Get head-to-head record
    Given the match data is loaded
    When I compare "Flamengo" and "Fluminense" head-to-head in season 2023
    Then I should receive a summary with wins and draws

  Scenario: Search players by nationality
    Given the player data is loaded
    When I search for Brazilian players
    Then I should receive players with Brazilian nationality

  Scenario: Search players by club
    Given the player data is loaded
    When I search for players at "Real Madrid"
    Then I should receive players whose club contains "Real Madrid"

  Scenario: Compute league standings
    Given the match data is loaded
    When I request the 2023 Brasileirão standings
    Then I should receive a ranked list of teams with points

  Scenario: Identify biggest wins
    Given the match data is loaded
    When I request the biggest wins in the Brasileirão 2023
    Then I should receive matches ordered by goal difference

  Scenario: Calculate goals per match
    Given the match data is loaded
    When I request the average goals per match for Brasileirão 2023
    Then I should receive a positive average

  Scenario: Find last match between teams
    Given the match data is loaded
    When I search for the last match between "Flamengo" and "Corinthians"
    Then I should receive the most recent match

  Scenario: Filter matches by competition
    Given the match data is loaded
    When I search for matches in the "Copa do Brasil" in season 2023
    Then I should receive only Copa do Brasil matches
