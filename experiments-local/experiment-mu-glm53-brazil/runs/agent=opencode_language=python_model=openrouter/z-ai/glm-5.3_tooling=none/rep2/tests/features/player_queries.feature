Feature: Player Queries
  As a soccer fan asking questions in natural language
  I want to search the FIFA player database
  So that I can find players by name, club, nationality and position

  Scenario: Search a player by name
    Given the player data is loaded
    When I search for players named "Neymar"
    Then "Neymar Jr" should be found with overall rating 92

  Scenario: Find the top Brazilian players
    Given the player data is loaded
    When I request the top 3 Brazilian players
    Then "Neymar Jr" should lead the list
    And every player should be Brazilian

  Scenario: Find players at a Brazilian club
    Given the player data is loaded
    When I search for players at club "Santos"
    Then every result should play for Santos
    And the result should not be empty

  Scenario: Show all forwards from a club
    Given the player data is loaded
    When I search for forwards at club "Grêmio"
    Then every result should be a forward position
    And the result should not be empty

  Scenario: Brazilian players at Brazilian clubs
    Given the player data is loaded
    When I aggregate Brazilian players by club
    Then each listed club should be a Brazilian club
    And Santos should be listed with player counts

  Scenario: Clubs without licensed squads return empty results
    Given the player data is loaded
    When I search for players at club "Flamengo"
    Then the result should be an empty list without errors
