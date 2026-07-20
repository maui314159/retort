Feature: Player Queries
  As a soccer fan asking natural-language questions
  I want to search the FIFA player database by name, nationality, club and position
  So that I can find players and their ratings.

  Scenario: Find all Brazilian players in the dataset
    Given the match data is loaded
    When I search for players of nationality "Brazil"
    Then I should receive a list of players
    And every player should be Brazilian

  Scenario: Find the highest-rated player at a club
    Given the match data is loaded
    When I search for players at club "Flamengo" sorted by rating
    Then I should receive a list of players
    And the first player should have the highest overall rating

  Scenario: Look up a player by name (Gabriel Barbosa alias "Gabriel")
    Given the match data is loaded
    When I search for players named "Gabriel"
    Then I should receive a list of players
    And every player name should contain "Gabriel"

  Scenario: Filter players by position
    Given the match data is loaded
    When I search for players in position "ST"
    Then I should receive a list of players
    And every player should have position "ST"

  Scenario: Filter Brazilian players above a rating threshold
    Given the match data is loaded
    When I search for Brazilian players with overall at least 85
    Then I should receive a list of players
    And every player should have overall at least 85
    And Neymar Jr should be among the top-rated Brazilians
