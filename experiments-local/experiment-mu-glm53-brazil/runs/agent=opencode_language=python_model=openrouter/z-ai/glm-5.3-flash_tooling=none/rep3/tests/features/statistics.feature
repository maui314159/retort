# language: en
Feature: Statistical Analysis
  As an MCP client I want aggregated statistics over the match datasets

  Scenario: Average goals per match in the Brasileirão
    Given the match data is loaded
    When I request statistics for "Brasileirão Serie A"
    Then the average goals per match should be plausible
    And the home win rate should be plausible

  Scenario: Biggest victories
    Given the match data is loaded
    When I request the biggest wins for "Brasileirão Serie A"
    Then I should receive a descending list of victories
    And the top victory should have a margin of at least 5 goals

  Scenario: Derbies in a season
    Given the match data is loaded
    When I request derbies for season 2023
    Then I should receive traditional rivalries with records
    And the list should include "Fla-Flu" and "Grenal"

  Scenario: Best away record
    Given the match data is loaded
    When I request statistics for "Brasileirão Serie A"
    Then the best away record should not exceed the best home record
