Feature: Player Queries
  As a soccer analyst
  I want to search player data
  So that I can answer questions about Brazilian players

  Scenario: Search for Brazilian players
    Given the player data is loaded
    When I search for players with nationality "Brazil"
    Then all returned players should be Brazilian

  Scenario: Search for players at a club
    Given the player data is loaded
    When I search for players at club "Santos"
    Then the returned players should include players from Santos

  Scenario: Top Brazilian players
    Given the player data is loaded
    When I request the top "5" Brazilian players
    Then the players should be sorted by overall rating descending
    And all returned players should be Brazilian
