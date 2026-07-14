Feature: Competition Queries
  As a soccer analyst
  I want to calculate standings from match results
  So that I can determine champions and relegation

  Scenario: Calculate standings for a season
    Given the match data is loaded
    When I request standings for "Brasileirao" season "2019"
    Then I should receive a full league table
    And the table should be sorted by points descending
    And the top team should be Flamengo

  Scenario: Identify the champion
    Given the match data is loaded
    When I request the champion for "Brasileirao" season "2019"
    Then the champion should be Flamengo

  Scenario: Relegated teams
    Given the match data is loaded
    When I request 4 relegated teams for "Brasileirao" season "2019"
    Then I should receive exactly 4 teams
    And they should be the bottom 4 of the standings

  Scenario: Average goals per match
    Given the match data is loaded
    When I request average goals for competition "Brasileirao"
    Then I should receive a positive average goals per match
    And the home win rate should be higher than the away win rate
