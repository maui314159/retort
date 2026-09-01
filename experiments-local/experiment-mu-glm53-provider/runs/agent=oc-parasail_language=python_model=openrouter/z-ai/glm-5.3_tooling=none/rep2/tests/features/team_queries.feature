Feature: Team Queries
  As a soccer fan asking natural-language questions
  I want team records, head-to-head comparisons and profiles
  So that I can understand how any Brazilian team performed

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals

  Scenario: Home record for a season
    Given the match data is loaded
    When I request home statistics for "Corinthians" in season 2022 in competition "Série A"
    Then the record should show 19 home matches
    And the record should show 12 wins, 4 draws and 3 losses
    And the summary should contain the win rate

  Scenario: Compare teams head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then I should receive wins, draws and losses for both teams
    And the match counts of both teams should be equal
    And Palmeiras should have 17 wins and Santos 16 wins with 8 draws

  Scenario: Best away record
    Given the match data is loaded
    When I request the best away records with at least 50 matches
    Then the ranking should be sorted by win rate descending
    And every ranked team should have at least 50 away matches

  Scenario: Team profile across files
    Given the match data is loaded
    When I request the profile of "Palmeiras"
    Then the profile should list multiple competitions
    And the profile should include an overall record
