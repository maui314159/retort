Feature: Competition Queries
  As a soccer analyst
  I want to calculate competition standings
  So that I can answer questions about champions and relegation.

  Scenario: Calculate standings for a season
    Given the match data is loaded
    When I request standings for competition "Brasileirao Serie A" in season 2022
    Then I should receive a ranked list of teams
    And the first team should be labeled Champion
    And each team should have points, wins, draws, and losses

  Scenario: List available competitions
    Given the match data is loaded
    When I list all competitions
    Then the list should include Brasileirao, Copa do Brasil, and Libertadores

  Scenario: List seasons for a competition
    Given the match data is loaded
    When I request seasons for competition "Libertadores"
    Then I should receive a list of integer years
