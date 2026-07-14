Feature: Player Queries
  The MCP server must answer questions about players from the FIFA
  player database.

  Background:
    Given the dataset is loaded

  Scenario: Search for a player by name
    When I search for the player "Neymar"
    Then at least one match should be returned
    And the top result should be a forward or winger from Brazil

  Scenario: Find Brazilian players
    When I search for players with nationality "Brazil"
    Then every returned player should be Brazilian
    And the response should be ordered by overall rating descending

  Scenario: Find players at a club
    When I search for players at "Flamengo"
    Then every player should play for a club matching "Flamengo"

  Scenario: Find forwards at São Paulo FC
    When I search for forwards at "Sao Paulo"
    Then every player should be a forward
    And every player should play for a club matching "Sao Paulo"

  Scenario: Get a club roster summary
    When I ask for the roster at "Palmeiras"
    Then I should receive a total player count and an average overall rating
