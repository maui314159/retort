Feature: Statistical Analysis
  Verify that aggregate match statistics are calculated correctly.

  Scenario: Get match statistics for a competition
    Given the statistical data is available
    When I request statistics for competition "Brasileirão"
    Then I should receive aggregate statistics
    And average goals should be a positive number
    And home win rate should be between 0 and 100
