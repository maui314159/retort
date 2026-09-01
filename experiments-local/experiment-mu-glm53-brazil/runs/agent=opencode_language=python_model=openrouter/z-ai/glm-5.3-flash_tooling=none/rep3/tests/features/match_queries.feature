# language: en
Feature: Match Queries
  As an MCP client I want to find matches by team, date, competition and stage

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    And the response should include a head-to-head summary

  Scenario: Head-to-head record between two teams
    Given the match data is loaded
    When I request the head-to-head record of "Flamengo" and "Fluminense"
    Then the head-to-head should include wins, draws and goals for both teams
    And the rivalry should be recognized as "Fla-Flu"

  Scenario: Find matches by team and season
    Given the match data is loaded
    When I search for matches of "Palmeiras" in season 2023
    Then I should receive a list of matches
    And every match should be in season 2023

  Scenario: Find matches by date range
    Given the match data is loaded
    When I search for matches between dates "2019-05-01" and "2019-05-31"
    Then I should receive a list of matches
    And every match date should fall within the range

  Scenario: Find all Copa do Brasil finals
    Given the match data is loaded
    When I search for stage "final" in "Copa do Brasil"
    Then I should receive a list of matches
    And every match should be a cup final

  Scenario: Find the Copa Libertadores final of 2018
    Given the match data is loaded
    When I search for stage "final" in "Copa Libertadores" for season 2018
    Then I should receive a list of matches
    And the finalists should include "Boca Juniors" and "River Plate"
