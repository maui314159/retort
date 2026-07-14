Feature: Player Queries
  As a soccer analyst
  I want to search the FIFA player dataset
  So that I can find players by name, nationality, club, and position.

  Scenario: Search players by nationality
    Given the player data is loaded
    When I search for players of nationality "Brazil"
    Then I should receive a list of players
    And every player should be Brazilian

  Scenario: Top players at a club
    Given the player data is loaded
    When I request the top 5 players at "Flamengo"
    Then I should receive at most 5 players
    And the players should be sorted by overall rating descending

  Scenario: Search by name
    Given the player data is loaded
    When I search for players named "Neymar"
    Then I should receive at least one player
    And the first result should be Neymar Jr

  Scenario: Filter by minimum overall rating
    Given the player data is loaded
    When I search for Brazilian players with minimum overall 85
    Then every player should have an overall rating of at least 85
