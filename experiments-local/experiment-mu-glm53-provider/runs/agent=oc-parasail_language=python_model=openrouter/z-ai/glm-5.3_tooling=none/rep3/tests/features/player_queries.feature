Feature: Player Queries
  Searching the FIFA player database by name, nationality, club and
  position.

  Scenario: Find all Brazilian players in the dataset
    Given the player data is loaded
    When I search for players of nationality "Brazil"
    Then more than 800 players should be found
    And every player should be Brazilian

  Scenario: Top-rated Brazilian players
    Given the player data is loaded
    When I search for players of nationality "Brazil" sorted by rating
    Then the first player should be "Neymar Jr"
    And his overall rating should be 92

  Scenario: Players at a Brazilian club
    Given the player data is loaded
    When I search for players at club "Fluminense"
    Then at least 15 players should be found
    And every player should play for Fluminense

  Scenario: Forwards from a club
    Given the player data is loaded
    When I search for forwards at club "Santos"
    Then at least 3 players should be found
    And every returned player should be a forward

  Scenario: Look up a player by name
    Given the player data is loaded
    When I look up the player "Neymar"
    Then the player should be found
    And his position should be "LW"
    And his club should be "Paris Saint-Germain"

  Scenario: Player search with no match returns a clear error
    Given the player data is loaded
    When I look up the player "Gabriel Barbosa"
    Then the lookup should report that no player was found

  Scenario: Cross-file query links FIFA clubs to match teams
    Given the match data is loaded
    When I search for players at club "Grêmio"
    Then at least 15 players should be found
    And the club should also have matches in the match data
