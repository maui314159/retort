Feature: Player Queries
  As a user of the Brazilian Soccer MCP server
  I want to search the FIFA player database
  So that I can find players by name, nationality and club

  Scenario: Search a player by name
    Given the player data is loaded
    When I search for a player named "Neymar"
    Then the top result should be "Neymar Jr" with overall 92

  Scenario: Find all Brazilian players
    Given the player data is loaded
    When I filter players by nationality "Brazil"
    Then every returned player should have nationality "Brazil"

  Scenario: Find players of a Brazilian club
    Given the player data is loaded
    When I filter players by club "Grêmio"
    Then every returned player should play for "Grêmio"

  Scenario: Find forwards of a club
    Given the player data is loaded
    When I filter players by club "Santos" and position "forward"
    Then every returned player should be a forward

  Scenario: Top rated Brazilian players
    Given the player data is loaded
    When I ask for the top 5 Brazilian players
    Then the first player should be "Neymar Jr"

  Scenario: Unknown player search
    Given the player data is loaded
    When I search for a player named "Zzz No Such Player"
    Then I should receive zero players
