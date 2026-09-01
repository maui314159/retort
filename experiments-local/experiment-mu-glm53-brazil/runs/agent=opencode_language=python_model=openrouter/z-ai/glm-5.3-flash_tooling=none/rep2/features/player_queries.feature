Feature: Player Queries
  As an LLM using the Brazilian Soccer MCP server
  I want to search the FIFA player database
  So that I can answer questions about players

  Background:
    Given the Brazilian soccer data is loaded

  Scenario: Look up a player by name
    When I search for the player "Neymar"
    Then I should receive matching players
    And the top result should have a name, nationality, club and overall rating

  Scenario: Full player profile with attributes
    When I request the profile of "Neymar"
    Then I should receive the player's attributes
    And the profile should include skill ratings

  Scenario: Find Brazilian players
    When I search for players with nationality "Brazil" and minimum overall 85
    Then I should receive matching players
    And every player should be Brazilian with overall at least 85

  Scenario: Filter players by club
    When I search for players with club "Grêmio"
    Then I should receive matching players
    And every player should belong to "Grêmio"

  Scenario: Unknown player fails gracefully
    When I request the profile of "Zezinho Semclube"
    Then the response should indicate no player was found
