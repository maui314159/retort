Feature: Player Queries
  As a user of the Brazilian Soccer MCP server
  I want to search the FIFA player database
  So that I can answer questions like "Who are the highest-rated Brazilian players?"

  Scenario: Search players by name
    Given the player data is loaded
    When I search for a player named "Neymar"
    Then the top result should be "Neymar Jr"

  Scenario: Find all Brazilian players in the dataset
    Given the player data is loaded
    When I filter players by nationality "Brazil"
    Then I should find more than 800 players
    And every player should be Brazilian

  Scenario: Top-rated Brazilian players
    Given the player data is loaded
    When I ask for the top 3 Brazilian players by rating
    Then the first player should be "Neymar Jr" with rating 92
    And the players should be sorted by overall rating

  Scenario: Which players play for a club
    Given the player data is loaded
    When I filter players by club "Santos"
    Then every player should play for "Santos"

  Scenario: Show me forwards from a club
    Given the player data is loaded
    When I filter "Santos" players by position group "forward"
    Then I should receive at least 2 players
    And every player should be a forward

  Scenario: Who is Gabriel Jesus
    Given the player data is loaded
    When I ask for the profile of "Gabriel Jesus"
    Then the profile should show club "Manchester City"
    And the profile should include skill ratings
