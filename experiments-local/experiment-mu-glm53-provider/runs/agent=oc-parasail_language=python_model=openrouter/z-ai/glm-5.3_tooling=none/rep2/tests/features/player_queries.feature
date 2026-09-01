Feature: Player Queries
  As a soccer fan asking natural-language questions
  I want to search the FIFA player database by name, nationality, club and position
  So that I can find players and their ratings

  Scenario: Search player by name
    Given the FIFA player data is loaded
    When I search for players named "Neymar"
    Then the results should include "Neymar Jr"
    And he should be Brazilian with overall rating 92

  Scenario: Top Brazilian players
    Given the FIFA player data is loaded
    When I request the top 5 players of nationality "Brazil"
    Then the top rated player should be "Neymar Jr"
    And every listed player should be Brazilian
    And the players should be sorted by overall rating descending

  Scenario: Players at a Brazilian club
    Given the FIFA player data is loaded
    When I search for players at club "Grêmio"
    Then at least 20 players should be found
    And every player should play for Grêmio

  Scenario: Players by position and rating
    Given the FIFA player data is loaded
    When I search for Brazilian goalkeepers with overall at least 85
    Then every player should be a Brazilian goalkeeper rated at least 85
    And Alisson should be among the results

  Scenario: Player search with no results
    Given the FIFA player data is loaded
    When I search for players named "Gabriel Barbosa"
    Then zero players should be found and the answer should say so gracefully
