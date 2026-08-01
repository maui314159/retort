Feature: Competition Queries
  As a user of the Brazilian Soccer MCP server
  I want standings calculated from match results
  So that I can answer questions like "Who won the 2019 Brasileirão?"

  Scenario: Who won the 2019 Brasileirão
    Given the match data is loaded
    When I request the "Brasileirão" standings for season 2019
    Then the leader should be "Flamengo" with 90 points
    And the leader should be marked as champion

  Scenario: Standings are calculated from all 380 matches
    Given the match data is loaded
    When I request the "Serie A" standings for season 2019
    Then the table should cover 20 teams and 380 matches

  Scenario: Which teams were relegated in 2019
    Given the match data is loaded
    When I request the "Brasileirão" standings for season 2019
    Then exactly 4 teams should be marked as relegated
    And "Cruzeiro" should be relegated

  Scenario: Points follow the 3-1-0 rule
    Given the match data is loaded
    When I request the "Serie A" standings for season 2021
    Then every team's points should equal 3 x wins + draws

  Scenario: List competitions in the dataset
    Given the match data is loaded
    When I list the competitions
    Then the list should include "Brasileirão Série A"
    And the list should include "Copa do Brasil"
    And the list should include "Copa Libertadores"

  Scenario: Cross-file dataset summary
    Given the soccer data store is loaded
    When I request the dataset summary
    Then all 6 CSV files should be reported
    And the unified match count should exceed 16000
    And the player count should be 18207
