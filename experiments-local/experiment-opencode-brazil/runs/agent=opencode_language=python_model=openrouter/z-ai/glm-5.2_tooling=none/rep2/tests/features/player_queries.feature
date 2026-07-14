Feature: Player Queries
  As a soccer analyst
  I want to search the FIFA player database
  So that I can find Brazilian players and club rosters

  Scenario: Find top Brazilian players
    Given the FIFA player data is loaded
    When I request the top 10 Brazilian players
    Then I should receive up to 10 players
    And each player should have nationality Brazil
    And the players should be sorted by overall rating descending

  Scenario: Search players by name
    Given the FIFA player data is loaded
    When I search for players named "Neymar"
    Then I should receive at least one player
    And the first player should be named "Neymar Jr"

  Scenario: Filter players by minimum rating
    Given the FIFA player data is loaded
    When I search for players with minimum overall rating 90
    Then every returned player should have an overall rating of at least 90
