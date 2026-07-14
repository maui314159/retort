Feature: Player Queries
  As a soccer analyst
  I want to search the FIFA player database
  So that I can find players by name, nationality, club and position.

  Scenario: Search a player by name
    Given the match data is loaded
    When I search for a player named "Neymar"
    Then I should receive a non-empty player list
    And each player should have name, overall, position and club

  Scenario: Top Brazilian players
    Given the match data is loaded
    When I request the top 5 players from "Brazil"
    Then I should receive 5 players
    And every player should be Brazilian
    And the list should be sorted by overall descending

  Scenario: Filter by position group
    Given the match data is loaded
    When I search for "FWD" players limited to 10
    Then I should receive at most 10 players
    And every player should be a forward

  Scenario: Players at a club
    Given the match data is loaded
    When I request players at club "Santos"
    Then each player should have a club containing "Santos"
