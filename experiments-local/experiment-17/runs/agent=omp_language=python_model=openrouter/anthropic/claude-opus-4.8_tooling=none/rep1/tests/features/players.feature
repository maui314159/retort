Feature: Player Queries
  As an analyst
  I want to search the FIFA player database
  So that I can find players by name, nationality, club and rating

  Background:
    Given the knowledge base is loaded

  Scenario: Find a player by name
    When I search for players named "Neymar"
    Then I should receive at least one player
    And the top player's nationality should be "Brazil"

  Scenario: Find Brazilian players
    When I search for players from "Brazil"
    Then I should receive at least 100 players
    And every returned player should have nationality "Brazil"

  Scenario: Players are ranked by overall rating
    When I search for players from "Brazil"
    Then the players should be ordered by overall rating descending

  Scenario: Filter players by minimum rating
    When I search for players from "Brazil" with overall at least 85
    Then every returned player should have an overall of at least 85

  Scenario: Summarise Brazilian players by club
    When I summarise "Brazil" players grouped by club
    Then each club entry should report a player count and an average rating
