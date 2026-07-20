Feature: Team Queries
  As a soccer fan asking natural-language questions
  I want team statistics, records and head-to-head comparisons
  So that I can understand how a team performed in a season or competition.

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2023
    Then I should receive wins, losses, draws and goals
    And the matches count should equal wins plus draws plus losses

  Scenario: Get a team's home record
    Given the match data is loaded
    When I request home statistics for "Corinthians" in season 2022
    Then I should receive a home wins, draws and losses breakdown
    And every counted match should be a home match

  Scenario: Compare two teams head-to-head
    Given the match data is loaded
    When I request the head-to-head between "Palmeiras" and "Santos"
    Then I should receive totals for both teams
    And both team win counts should be non-negative integers

  Scenario: Team info lists competitions and FIFA players
    Given the match data is loaded
    When I request info for "Flamengo"
    Then I should receive a competitions map and an overall record
    And the team name should be the canonical form
