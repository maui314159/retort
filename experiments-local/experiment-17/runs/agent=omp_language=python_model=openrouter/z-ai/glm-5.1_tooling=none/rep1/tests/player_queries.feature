Feature: Player Queries

  Scenario: Search player by name
    Given the player data is loaded
    When I search for players named "Neymar"
    Then I should receive player records matching that name

  Scenario: Filter players by nationality
    Given the player data is loaded
    When I search for players of nationality "Brazil"
    Then I should receive only Brazilian players

  Scenario: Filter players by club
    Given the player data is loaded
    When I search for players at club "Santos"
    Then I should receive players from that club
