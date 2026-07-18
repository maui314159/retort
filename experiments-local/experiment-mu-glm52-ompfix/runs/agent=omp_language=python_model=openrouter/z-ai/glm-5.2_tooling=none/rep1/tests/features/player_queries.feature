Feature: Player Queries
  As a soccer scout
  I want to search the FIFA player database
  So that I can find players by name, nationality, club, and position

  Scenario: Search player by name
    Given the player data is loaded
    When I search for players named "Neymar"
    Then I should find at least 1 player
    And the player should have a name, overall rating, and club

  Scenario: Find top Brazilian players
    Given the player data is loaded
    When I request the top Brazilian players
    Then I should receive a ranked list
    And the first player should have an overall rating of at least 85

  Scenario: Find players by club
    Given the player data is loaded
    When I search for players at club "Fluminense"
    Then I should find at least 5 players

  Scenario: Find forwards
    Given the player data is loaded
    When I search for forwards
    Then I should find at least 100 players
    And each player should have a forward position
