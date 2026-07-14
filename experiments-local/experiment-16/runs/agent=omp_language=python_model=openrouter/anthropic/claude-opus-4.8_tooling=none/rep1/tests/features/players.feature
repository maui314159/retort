Feature: Player Queries
  As an analyst I want to search FIFA player data by name, nationality and club
  so that I can find players and compare ratings.

  Background:
    Given the soccer knowledge graph is loaded

  Scenario: Search a player by name
    When I search for the player "Gabriel Barbosa"
    Then I should find a player named "Gabriel Barbosa"
    And the player should have an overall rating

  Scenario: Filter players by nationality
    When I search for players from "Brazil"
    Then every returned player should be Brazilian
    And the players should be sorted by overall rating descending

  Scenario: Filter players by club
    When I search for players at the club "Flamengo"
    Then every returned player should belong to "Flamengo"

  Scenario: Filter players by position
    When I search for "Brazil" players in position "ST"
    Then every returned player should play position "ST"
