Feature: Player Queries
  As an analyst
  I want to search and rank players
  So that I can answer questions about the FIFA player database

  Scenario: Search a player by name
    Given the player data is loaded
    When I search for the player "Neymar"
    Then I should find at least one player
    And the top result should be Brazilian

  Scenario: Find Brazilian players
    Given the player data is loaded
    When I list players from "Brazil"
    Then I should receive many players
    And every returned player should have nationality "Brazil"

  Scenario: Top Brazilian players are ranked by overall rating
    Given the player data is loaded
    When I request the top 5 players from "Brazil"
    Then the results should be sorted by overall rating descending

  Scenario: Filter players by position
    Given the player data is loaded
    When I request the top 5 "GK" players from "Brazil"
    Then every returned player should play position "GK"
