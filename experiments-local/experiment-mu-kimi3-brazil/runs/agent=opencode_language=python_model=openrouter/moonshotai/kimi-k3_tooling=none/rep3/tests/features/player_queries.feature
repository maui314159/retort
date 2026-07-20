Feature: Player Queries
  As an LLM client of the MCP server
  I want to search the FIFA player database
  So that I can answer questions like "Who are the highest-rated players at Grêmio?"

  Background:
    Given the player data is loaded

  Scenario: Search a player by name
    When I search for a player named "Neymar"
    Then I should find exactly 1 player
    And the player should be "Neymar Jr" with overall 92

  Scenario: Filter players by Brazilian nationality
    When I search for players with nationality "Brazil"
    Then I should find more than 800 players
    And every player should have nationality "Brazil"

  Scenario: Filter players by club
    When I search for players at club "Grêmio"
    Then I should find at least 10 players
    And every player club should contain "Grêmio"

  Scenario: Top rated players are sorted by overall rating
    When I request the top 5 players with nationality "Brazil"
    Then I should receive 5 players
    And the players should be sorted by descending overall rating
    And the first player should be "Neymar Jr"

  Scenario: Filter players by position group
    When I search for forwards at club "Santos"
    Then every player position should be a forward position

  Scenario: Player profile includes skill ratings
    When I request the profile of "Casemiro"
    Then the profile should be found
    And the player should play for "Real Madrid"
    And the profile should include skill ratings

  Scenario: Unknown player is reported as not found
    When I request the profile of "Zzz Unknown Player"
    Then the profile should not be found
