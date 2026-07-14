Feature: Match Queries
  As an analyst using the Brazilian Soccer MCP server
  I want to find matches by team, opponent, competition and season
  So that I can answer questions about who played whom and when

  Background:
    Given the knowledge base is loaded

  Scenario: Find matches between two teams
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive at least 20 matches
    And each match should have a date, scores, and competition

  Scenario: Team name variations resolve to the same club
    When I search for matches for "Flamengo-RJ" in the "Brasileirão" season "2019"
    And I search for matches for "Flamengo" in the "Brasileirão" season "2019"
    Then both searches should return the same number of matches

  Scenario: Find matches by competition and season
    When I search for matches in the "Libertadores" season "2019"
    Then every returned match should be in competition "Copa Libertadores"
    And every returned match should be in season "2019"

  Scenario: Restrict matches to a home venue
    When I search for home matches for "Corinthians" in the "Brasileirão" season "2019"
    Then there should be 19 matches
    And "Corinthians" should be the home team in every match

  Scenario: A team plays across multiple competitions
    When I list the competitions "Palmeiras" has played in
    Then the competitions should include "Brasileirão Série A"
    And the competitions should include "Copa Libertadores"
