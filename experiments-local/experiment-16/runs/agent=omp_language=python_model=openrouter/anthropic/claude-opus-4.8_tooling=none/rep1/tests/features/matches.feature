Feature: Match Queries
  As an analyst I want to find matches by team, opponent, competition and season
  so that I can review fixtures and results.

  Background:
    Given the soccer knowledge graph is loaded

  Scenario: Find matches between two teams
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive 2 matches
    And each match should have a date, scores and a competition

  Scenario: Head-to-head record between two teams
    When I request the head-to-head between "Flamengo" and "Fluminense"
    Then Flamengo should have 1 win
    And Fluminense should have 1 win
    And there should be 0 draws

  Scenario: Filter matches by season and competition
    When I search Brasileirao matches for "Palmeiras" in season 2023
    Then I should receive 3 matches
    And every match should be in the "Brasileirão" competition

  Scenario: Distinct clubs sharing a base name are not merged
    When I request the team record for "Atletico-MG" in season 2023
    Then the team should have played 1 match
    And the record should not include "Atletico-PR" matches

  Scenario: Matches with missing scores are still listed
    When I search for all matches involving "Santos"
    Then the result should include a match with no recorded score
