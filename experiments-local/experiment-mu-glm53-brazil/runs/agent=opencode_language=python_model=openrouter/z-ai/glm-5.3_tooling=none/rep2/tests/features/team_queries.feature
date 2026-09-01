Feature: Team Queries
  As a soccer fan asking questions in natural language
  I want team records, head-to-head comparisons and name resolution
  So that I can understand how any Brazilian club performed

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2023
    Then I should receive wins, losses, draws, and goals
    And the totals should be consistent

  Scenario: Get a team's home record in a season
    Given the match data is loaded
    When I request home statistics for "Corinthians" in season 2022
    Then I should receive wins, losses, draws, and goals
    And the record should count 15 played matches

  Scenario: Compare two teams head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then I should receive their matches and an all-time record
    And the record should account for every played match

  Scenario: List competitions a team played in
    Given the match data is loaded
    When I list the competitions of "Palmeiras"
    Then the team should appear in 3 competitions
    And one of them should be "Copa Libertadores"

  Scenario: Handle team name variations
    Given the match data is loaded
    When I resolve the team name "Sport Club Corinthians Paulista"
    Then it should resolve to the canonical team "Corinthians"

  Scenario: Handle ambiguous team names
    Given the match data is loaded
    When I resolve the team name "Atletico"
    Then it should resolve to the most frequent "Atletico-MG"
    And the alternatives should mention Atletico-PR

  Scenario: Team statistics across all competitions
    Given the match data is loaded
    When I request statistics for "Santos"
    Then the by-competition breakdown should include Brasileirão Série A
    And the overall record should aggregate home and away matches
