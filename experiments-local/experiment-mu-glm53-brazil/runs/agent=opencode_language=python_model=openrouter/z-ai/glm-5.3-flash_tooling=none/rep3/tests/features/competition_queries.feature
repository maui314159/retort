# language: en
Feature: Competition Queries
  As an MCP client I want standings and season information computed from results

  Scenario: Who won the 2019 Brasileirão?
    Given the match data is loaded
    When I request the standings of "Brasileirão Serie A" for season 2019
    Then the champion should be "Flamengo-RJ"
    And the table should cover 20 teams and 380 matches

  Scenario: Relegation zone in 2020
    Given the match data is loaded
    When I request the standings of "Brasileirão Serie A" for season 2020
    Then a relegation zone with 4 teams should be reported

  Scenario: Standings are not computed for cup competitions
    Given the match data is loaded
    When I request the standings of "Copa Libertadores" for season 2019
    Then a not-found error should be raised

  Scenario: Competition catalog
    Given the match data is loaded
    When I request the list of competitions
    Then the catalog should include "Brasileirão Serie A", "Copa do Brasil" and "Copa Libertadores"

  Scenario: Compare the 2018 and 2019 seasons
    Given the match data is loaded
    When I compare seasons 2018 and 2019 of "Brasileirão Serie A"
    Then both seasons should report a champion and aggregates
