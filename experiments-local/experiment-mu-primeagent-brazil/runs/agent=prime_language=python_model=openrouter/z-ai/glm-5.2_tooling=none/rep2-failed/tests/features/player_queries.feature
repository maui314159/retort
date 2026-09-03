Feature: Player Queries
  As a user of the Brazilian Soccer MCP server
  I want to search the FIFA player data
  So that I can answer questions about players and clubs

  Scenario: Search Brazilian players
    Given the player data is loaded
    When I search for players of nationality "Brazil"
    Then I should receive players
    And every returned player should be Brazilian
    And the players should be sorted by overall rating descending

  Scenario: Find a player by name
    Given the player data is loaded
    When I search for players named "Neymar"
    Then I should receive at least one player
    And the first player should be Neymar Jr

  Scenario: Top Brazilian players
    Given the player data is loaded
    When I request the top 5 Brazilian players
    Then the highest rated player should be Neymar Jr
    And the highest overall rating should be 92

  Scenario: Players at a club
    Given the player data is loaded
    When I request players at club "Grêmio"
    Then every returned player should play for Grêmio
    And the players should be sorted by overall rating descending
