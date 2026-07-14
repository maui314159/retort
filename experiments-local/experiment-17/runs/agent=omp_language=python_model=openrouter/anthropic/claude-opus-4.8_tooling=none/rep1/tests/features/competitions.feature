Feature: Competition Queries
  As an analyst
  I want league standings computed from match results
  So that I can answer who won a season

  Background:
    Given the knowledge base is loaded

  Scenario: Compute the 2019 Brasileirão champion
    When I compute the standings for "Brasileirão" season "2019"
    Then the champion should be "Flamengo"
    And the standings should contain 20 teams
    And the top team should have 90 points

  Scenario: Standings are ordered by points descending
    When I compute the standings for "Brasileirão" season "2019"
    Then each team should have no more points than the team above it

  Scenario: Every team in a round-robin season plays the same number of matches
    When I compute the standings for "Brasileirão" season "2019"
    Then every team should have played 38 matches

  Scenario: Listing available competitions
    When I list the available competitions
    Then the result should include "Brasileirão Série A"
    And the result should include "Copa do Brasil"
    And the result should include "Copa Libertadores"
