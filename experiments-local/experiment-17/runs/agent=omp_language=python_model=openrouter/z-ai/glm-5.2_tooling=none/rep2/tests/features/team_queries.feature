Feature: Team Queries
  As a soccer analyst
  I want to query team records and head-to-head comparisons
  So that I can compare team performance.

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2023
    Then I should receive wins, losses, draws, and goals
    And the matches count should be positive

  Scenario: Team home record in a season
    Given the match data is loaded
    When I request home statistics for "Corinthians" in season 2022 and competition "Brasileirão"
    Then the home record should be present
    And home matches should be at most 19

  Scenario: Head-to-head comparison
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then I should receive a head-to-head record
    And the wins plus draws plus losses should equal the match count

  Scenario: Team competitions
    Given the match data is loaded
    When I request the competitions of "Palmeiras"
    Then I should receive a non-empty competition map
    And the map should include "Brasileirão Serie A"
