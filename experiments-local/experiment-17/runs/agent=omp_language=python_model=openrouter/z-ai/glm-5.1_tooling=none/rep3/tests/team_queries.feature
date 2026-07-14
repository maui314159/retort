Feature: Team Queries
  Query team statistics including records, goals, and performance.

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras"
    Then I should receive wins losses draws and goals

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Corinthians" in season 2022
    Then I should receive season-specific statistics

  Scenario: Get team home record
    Given the match data is loaded
    When I request home statistics for "Flamengo"
    Then the statistics should reflect home matches only

  Scenario: Top teams by goals
    Given the match data is loaded
    When I request top teams by goals
    Then I should receive a ranked list of teams by goals scored
