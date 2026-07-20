Feature: Competition Queries
  The MCP server computes standings from match results and
  traverses the knowledge graph for competition membership.

  Scenario: The 2019 Brasileirão champion
    Given the match data is loaded
    When I request the standings for season 2019
    Then the champion should be "Flamengo"
    And the standings should have 20 teams

  Scenario: Standings are internally consistent
    Given the match data is loaded
    When I request the standings for season 2019
    Then every team should have points equal to 3 per win plus 1 per draw
    And every team should have played 38 matches

  Scenario: Relegation zone is tagged
    Given the match data is loaded
    When I request the standings for season 2019
    Then exactly 4 teams should be tagged as relegated

  Scenario: Historical season standings
    Given the match data is loaded
    When I request the standings for season 2009
    Then the champion should be "Flamengo"
    And the standings should have 20 teams

  Scenario: Competitions a team played in
    Given the match data is loaded
    When I ask which competitions "Palmeiras" has played in
    Then the answer should include "Brasileirão Série A"
    And the answer should include "Copa do Brasil"
    And the answer should include "Copa Libertadores"
