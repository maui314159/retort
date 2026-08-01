Feature: Statistical Analysis
  As an LLM user I want aggregated statistics over the datasets.

  Scenario: Biggest wins in the dataset
    Given the match data is loaded
    When I request the 5 biggest victories
    Then the margins should be sorted descending
    And the biggest margin should be at least 8 goals

  Scenario: Average goals per match
    Given the match data is loaded
    When I request statistics for "Brasileirão Série A"
    Then the average goals per match should be between 2.0 and 3.5
    And the home win rate should exceed the away win rate

  Scenario: Compare two seasons
    Given the match data is loaded
    When I compare seasons 2018 and 2019 in "Brasileirão Série A"
    Then both seasons should have 380 matches

  Scenario: Top scoring team of a season
    Given the match data is loaded
    When I request the top scoring teams of 2019 in "Serie A"
    Then the first team should be "Flamengo"
