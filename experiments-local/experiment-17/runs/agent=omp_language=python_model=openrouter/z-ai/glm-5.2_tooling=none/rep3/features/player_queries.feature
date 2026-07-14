Feature: Player Queries
  As a soccer fan I want to search FIFA player data.

  Scenario: Search Brazilian players
    Given the player data is loaded
    When I search for players with nationality "Brazil"
    Then every returned player should be Brazilian
    And the results should be sorted by overall rating descending

  Scenario: Top Brazilian players
    Given the player data is loaded
    When I request the top 5 Brazilian players
    Then I should receive at most 5 players
    And the first player should have the highest overall rating

  Scenario: Search by name substring
    Given the player data is loaded
    When I search for players named "Neymar"
    Then every returned player should have "Neymar" in their name

  Scenario: Filter by position
    Given the player data is loaded
    When I search for players with position "GK"
    Then every returned player should have position "GK"

  Scenario: Brazilian players grouped by club
    Given the player data is loaded
    When I request Brazilian players grouped by club
    Then the result should include a list of clubs with player counts
