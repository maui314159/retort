# language: en
Feature: Player Queries
  As an MCP client I want to search the FIFA player database

  Scenario: Find all Brazilian players
    Given the player data is loaded
    When I search for players with nationality "brazil"
    Then I should receive a list of players
    And every player should be Brazilian
    And players should be sorted by overall rating descending

  Scenario: Who is Neymar?
    Given the player data is loaded
    When I look up the player "Neymar Jr"
    Then I should receive the player profile
    And the player should play for "Paris Saint-Germain"

  Scenario: Highest-rated players at a Brazilian club
    Given the player data is loaded
    When I search for players at club "Cruzeiro"
    Then I should receive a list of players
    And the players should have an average rating

  Scenario: Filter players by position and rating
    Given the player data is loaded
    When I search for Brazilian "ST" players rated at least 80
    Then I should receive a list of players
    And every player should be a striker rated at least 80

  Scenario: Unknown player is reported gracefully
    Given the player data is loaded
    When I look up the player "Zé Ninguém"
    Then a not-found error should be raised
