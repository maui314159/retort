Feature: Statistical Analysis
  As an LLM client of the MCP server
  I want aggregated statistics across matches
  So that I can answer questions like "What's the average goals per match in the Brasileirão?"

  Background:
    Given the match data is loaded

  Scenario: Average goals per match in the Brasileirão
    When I request the overview of competition "Brasileirão Série A"
    Then the average goals per match should be between 2.0 and 3.5
    And the home, draw and away rates should add up to 100 percent

  Scenario: Compare two seasons
    When I request the overview of competition "Brasileirão Série A" for season 2018
    And I request the overview of competition "Brasileirão Série A" for season 2019
    Then both seasons should have 380 matches

  Scenario: Biggest wins in the dataset
    When I request the 5 biggest wins
    Then the biggest win should have a margin of at least 8 goals
    And the margins should be sorted in descending order

  Scenario: Best home record of a season
    When I request the best home records of competition "Brasileirão Série A" for season 2019
    Then every listed team should have at least 5 home matches
    And the teams should be sorted by descending points per game

  Scenario: Simple lookups are fast
    When I time a head-to-head lookup between "Flamengo" and "Corinthians"
    Then the lookup should take less than 2 seconds

  Scenario: Aggregate queries are fast
    When I time a standings request for season 2019
    Then the aggregate query should take less than 5 seconds
