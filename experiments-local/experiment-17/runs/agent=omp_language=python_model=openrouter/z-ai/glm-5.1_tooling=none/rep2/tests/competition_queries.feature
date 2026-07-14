Feature: Competition Queries
  Verify that competition standings can be calculated from match data.

  Scenario: Get competition standings
    Given the competition data is available
    When I request standings for "Brasileirão" season 2019
    Then I should receive a standings list
    And each entry should have position, points, wins, draws, losses
    And the first-placed team should have the most points
