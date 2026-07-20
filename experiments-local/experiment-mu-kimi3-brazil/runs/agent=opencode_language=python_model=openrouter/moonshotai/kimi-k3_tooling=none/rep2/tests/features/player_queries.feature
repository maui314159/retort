Feature: Player Queries
  The MCP server searches the FIFA player database by name,
  nationality, club and position.

  Scenario: Search a player by name
    Given the player data is loaded
    When I search players named "Neymar"
    Then I should find at least one player
    And each player should have name, club, position and rating

  Scenario: Filter players by nationality
    Given the player data is loaded
    When I search players with nationality "Brazil"
    Then I should find at least one player
    And all returned players should have nationality "Brazil"

  Scenario: Filter players by club
    Given the player data is loaded
    When I search players at club "Santos"
    Then I should find at least one player
    And all returned players should play for a club containing "Santos"

  Scenario: Club search is accent-insensitive
    Given the player data is loaded
    When I search players at club "Gremio"
    Then I should find at least one player
    And all returned players should play for a club containing "Grêmio"

  Scenario: Top-rated players are sorted by rating
    Given the player data is loaded
    When I request the top 5 players with nationality "Brazil"
    Then I should receive exactly 5 players
    And the players should be sorted by overall rating descending
    And the best player should have an overall rating of at least 88
