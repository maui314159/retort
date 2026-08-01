Feature: Team Queries
  As an LLM user I want team records and head-to-head comparisons.

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2022"
    Then I should receive wins, losses, draws, and goals

  Scenario: Get home record of a team
    Given the match data is loaded
    When I request the home record of "Corinthians" in season "2022" in "Brasileirão Série A"
    Then the record should show 19 matches
    And the record should include a win rate

  Scenario: Compare two teams head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then I should see wins for both sides and draws
    And the most recent match should be included

  Scenario: List competitions of a team
    Given the match data is loaded
    When I ask which competitions "Flamengo" played
    Then the answer should include "Brasileirão Série A"
    And the answer should include "Copa do Brasil"
    And the answer should include "Copa Libertadores"
