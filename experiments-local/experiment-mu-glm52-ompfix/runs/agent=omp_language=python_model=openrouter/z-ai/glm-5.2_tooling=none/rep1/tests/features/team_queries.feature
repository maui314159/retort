Feature: Team Queries
  As a soccer analyst
  I want to query team statistics and compare teams
  So that I can understand team performance across competitions and seasons

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Corinthians" in season 2022
    Then I should receive wins, losses, draws, and goals

  Scenario: Get team home record
    Given the match data is loaded
    When I request home statistics for "Corinthians" in season 2022 in competition "Brasileirão"
    Then I should receive home wins, draws, losses, and goals
    And the win rate should be a percentage

  Scenario: Compare two teams head-to-head
    Given the match data is loaded
    When I compare "Flamengo" and "Fluminense"
    Then I should receive head-to-head wins for both teams

  Scenario: List competitions for a team
    Given the match data is loaded
    When I request competitions for "Palmeiras"
    Then I should see at least 2 competitions
