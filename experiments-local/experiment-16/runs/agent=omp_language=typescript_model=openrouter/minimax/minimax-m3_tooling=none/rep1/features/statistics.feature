Feature: Statistical Analysis
  The MCP server must compute aggregate statistics over the dataset.

  Background:
    Given the dataset is loaded

  Scenario: Average goals per match in the Brasileirao
    When I ask for the average goals in "brasileirao"
    Then the response should include a numeric average between 1 and 6
    And it should include a home win rate between 0 and 100 percent

  Scenario: Biggest wins in the supplied dataset
    When I ask for the top 5 biggest wins across all competitions
    Then I should receive exactly 5 results
    And the results should be ordered by margin descending

  Scenario: Best home records
    When I ask for the top 5 best home records
    Then every team should have a positive home win rate
    And the response should be ordered by home win rate descending
