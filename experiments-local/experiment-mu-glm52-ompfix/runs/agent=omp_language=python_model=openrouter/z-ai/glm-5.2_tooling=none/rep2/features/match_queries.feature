Feature: Match Queries
  As a soccer analyst
  I want to query Brazilian soccer match data
  So that I can answer questions about matches, teams, and competitions

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2023
    Then I should receive wins, losses, draws, and goals

  Scenario: Filter matches by competition
    Given the match data is loaded
    When I search for "Palmeiras" matches in "Copa do Brasil"
    Then all returned matches should be from "Copa do Brasil"

  Scenario: Head-to-head between two teams
    Given the match data is loaded
    When I request head-to-head between "Flamengo" and "Vasco da Gama"
    Then I should receive win counts for both teams and draws

  Scenario: Competition standings calculated from results
    Given the match data is loaded
    When I request standings for "Brasileirão Série A" season 2019
    Then I should receive a sorted table with points
    And the first team should be the champion

  Scenario: Search players by name
    Given the player data is loaded
    When I search for players named "Neymar"
    Then I should receive at least one player
    And the player should have a rating

  Scenario: Filter players by nationality
    Given the player data is loaded
    When I search for players from "Brazil"
    Then all returned players should be Brazilian
    And each player should have an overall rating
