Feature: Competition Queries
  Standings, champions, finals and relegation computed from match
  results.

  Scenario: Who won the 2019 Brasileirão
    Given the match data is loaded
    When I ask for the champion of "Brasileirão" in season "2019"
    Then the champion should be "Flamengo"
    And the champion should have 90 points

  Scenario: Standings by season are calculated from matches
    Given the match data is loaded
    When I request the standings of "Brasileirão" for season "2019"
    Then the table should have 20 teams
    And every team should play 38 matches
    And the leader should be "Flamengo"

  Scenario: Which teams were relegated in 2020
    Given the match data is loaded
    When I request the standings of "Brasileirão" for season "2020"
    Then the relegated teams should include "Botafogo" and "Vasco da Gama"

  Scenario: Copa do Brasil champion from the final
    Given the match data is loaded
    When I ask for the champion of "Copa do Brasil" in season "2019"
    Then the champion should be "Athletico Paranaense"

  Scenario: Libertadores finals with winners
    Given the match data is loaded
    When I list the finals of the "Libertadores"
    Then at least 6 finals should be listed
    And the 2019 Libertadores champion should be "Flamengo"

  Scenario: Two-legged final decided on penalties is flagged
    Given the match data is loaded
    When I ask for the champion of "Libertadores" in season "2013"
    Then the answer should note that the final was level on aggregate

  Scenario: Standings are rejected for cup competitions
    Given the match data is loaded
    When I request the standings of "Libertadores" for season "2019"
    Then the request should explain that cups have no standings

  Scenario: What competitions has Palmeiras played in
    Given the match data is loaded
    When I request the competitions of team "Palmeiras"
    Then the answer should include "Brasileirão", "Copa do Brasil" and "Libertadores"

  Scenario: Listing all competitions shows coverage
    Given the match data is loaded
    When I list all competitions
    Then all five competitions should be listed
    And each competition should list its season coverage
