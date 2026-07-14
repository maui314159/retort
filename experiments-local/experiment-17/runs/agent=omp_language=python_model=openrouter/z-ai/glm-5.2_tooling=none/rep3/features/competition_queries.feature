Feature: Competition Queries
  As a soccer fan I want standings and season information.

  Scenario: Standings for a season
    Given the match data is loaded
    When I request standings for "Brasileirão" season 2019
    Then the champion should be "Flamengo"
    And the top team should have the most points

  Scenario: Standings positions are 1-indexed and contiguous
    Given the match data is loaded
    When I request standings for "Brasileirão" season 2019
    Then the positions should start at 1 and increment by 1

  Scenario: Standings respect points ordering
    Given the match data is loaded
    When I request standings for "Brasileirão" season 2019
    Then each team should have at least as many points as the team below it

  Scenario: Competition seasons listing
    Given the match data is loaded
    When I request seasons for "Copa do Brasil"
    Then the result should include a non-empty list of seasons

  Scenario: Standings match count is realistic
    Given the match data is loaded
    When I request standings for "Brasileirão" season 2019
    Then every team should have played at most 38 matches
