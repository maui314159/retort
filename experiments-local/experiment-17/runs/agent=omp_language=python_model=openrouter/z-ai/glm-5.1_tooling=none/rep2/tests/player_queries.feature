Feature: Player Queries
  Verify that player data from the FIFA dataset is queryable.

  Scenario: Search players by nationality
    Given the player data is loaded
    When I search for players with nationality "Brazil"
    Then I should receive a list of players
    And each player nationality should contain "Brazil"

  Scenario: Search players by club
    Given the player data is loaded
    When I search for players at club "Santos"
    Then I should receive a list of players
    And each player club should contain "Santos"
