Feature: Team Queries
  As a user I want team records and head-to-head comparisons
  so that I can answer "What is Corinthians' home record in 2022?" and
  "Compare Palmeiras and Santos head-to-head".

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals
    And the win rate should be reported

  Scenario: Get home record of a team
    Given the match data is loaded
    When I request the home record of "Corinthians" in season "2022"
    Then I should receive wins, losses, draws, and goals
    And the team should have played 19 matches

  Scenario: Head-to-head comparison
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then the summary should include wins for both teams and draws
    And the listed matches should involve "Palmeiras" and "Santos"
