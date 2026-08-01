Feature: Player Queries
  As an LLM user I want to search the FIFA player database by name,
  nationality, club and position.

  Scenario: Find all Brazilian players
    Given the player data is loaded
    When I search for players with nationality "Brazil"
    Then I should receive more than 800 players
    And the top player should be "Neymar Jr"

  Scenario: Find players at a Brazilian club
    Given the player data is loaded
    When I search for players at club "Grêmio"
    Then every player should have club "Grêmio"

  Scenario: Find forwards at a club
    Given the player data is loaded
    When I search for forwards at club "Santos"
    Then every player should be a forward

  Scenario: Look up a player profile
    Given the player data is loaded
    When I ask who "Neymar" is
    Then the profile should show overall rating 92
    And the profile should show club "Paris Saint-Germain"

  Scenario: Unknown player gives a helpful message
    Given the player data is loaded
    When I ask who "Zzyzzy Unknown" is
    Then I should receive a not found message
