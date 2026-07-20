Feature: Player Queries
  As a user I want to search the FIFA player database
  so that I can answer "Who is Neymar Jr?", "Find all Brazilian players"
  and "Who are the highest-rated players at Grêmio?".

  Scenario: Search player by name
    Given the player data is loaded
    When I search for players named "Neymar"
    Then I should receive a list of players
    And the top player should be "Neymar Jr"
    And each player should have name, rating, position, and club

  Scenario: Filter Brazilian players
    Given the player data is loaded
    When I search for Brazilian players
    Then I should receive a list of players
    And all returned players should be Brazilian

  Scenario: Filter players by club
    Given the player data is loaded
    When I search for players of club "Grêmio"
    Then I should receive a list of players
    And every player should belong to club "Grêmio"

  Scenario: Highest-rated Brazilian players
    Given the player data is loaded
    When I search for the top 3 Brazilian players
    Then I should receive a list of players
    And the top player should be "Neymar Jr"
    And players should be ordered by overall rating
