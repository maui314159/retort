Feature: Team Queries
  The MCP server must answer questions about team performance and
  head-to-head comparisons.

  Background:
    Given the dataset is loaded

  Scenario: Get a team's home record in a given season
    When I request "Corinthians" home record in 2022
    Then I should receive wins, draws, losses, and goals

  Scenario: Compare two teams head to head
    When I compare "Palmeiras" and "Santos" head-to-head
    Then I should receive totals for each side and a draw count

  Scenario: Top scorers inferred from per-competition aggregates
    When I ask which team scored the most goals in "brasileirao" 2023
    Then I should receive a single team with the highest total
