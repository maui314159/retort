Feature: Player Queries
  Search FIFA player data by name, nationality, club, and position.

  Scenario: Search players by name
    Given the player data is loaded
    When I search for players named "Neymar"
    Then I should find at least one player

  Scenario: Search Brazilian players
    Given the player data is loaded
    When I search for players from "Brazil"
    Then I should receive players with Brazilian nationality

  Scenario: Search players by club
    Given the player data is loaded
  When I search for players at club "Santos"
  Then all results should play for a club containing Santos

  Scenario: Top-rated Brazilian players
    Given the player data is loaded
    When I search for Brazilian players with min overall 85
    Then all results should have overall rating at least 85
