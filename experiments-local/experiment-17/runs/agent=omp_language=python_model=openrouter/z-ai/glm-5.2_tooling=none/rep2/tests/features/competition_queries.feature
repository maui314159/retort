Feature: Competition Queries
  As a soccer analyst
  I want to compute standings and champions from match results
  So that I can answer questions about competition outcomes.

  Scenario: Standings for a season
    Given the match data is loaded
    When I request the standings for "Brasileirão" in season 2019
    Then I should receive a sorted standings table
    And the champion should be "Flamengo"

  Scenario: Champion of a season
    Given the match data is loaded
    When I request the champion of "Brasileirão" in season 2018
    Then the champion should be "Palmeiras"

  Scenario: Standings totals are consistent
    Given the match data is loaded
    When I request the standings for "Brasileirão" in season 2019
    Then the total points across teams should be positive
    And each team should have 38 played matches

  Scenario: Standings for Copa do Brasil
    Given the match data is loaded
    When I request the standings for "Copa do Brasil" in season 2017
    Then I should receive a sorted standings table
