Feature: Player Queries
  FIFA database search: names, nationality, club, position, ratings.

  Scenario: Find all Brazilian players
    Given the FIFA player data is loaded
    When I filter players by nationality "Brazil"
    Then 827 Brazilian players are found

  Scenario: Search by name
    Given the FIFA player data is loaded
    When I search for "Neymar"
    Then Neymar Jr is returned with overall 92 and his club

  Scenario: Top Brazilian players
    Given the FIFA player data is loaded
    When I rank Brazilian players by overall rating
    Then Neymar Jr leads the list

  Scenario: Players at a club
    Given the FIFA player data is loaded
    When I request the roster of "Grêmio"
    Then 20 players are returned with an average overall rating

  Scenario: Club rosters missing from the FIFA source
    Given the FIFA player data is loaded
    When I request the roster of "Flamengo"
    Then the data gap is reported honestly instead of an error

  Scenario: Position groups
    Given the FIFA player data is loaded
    When I filter Brazilian "forward" players
    Then only attacking positions are returned
