Feature: Competition Queries

  Scenario: Calculate standings
    Given the match data is loaded
    When I request standings for season 2019 competition "Brasileirão"
    Then I should receive a sorted table with points and goal difference

  Scenario: Standings include champion marker
    Given the match data is loaded
    When I request standings for season 2019 competition "Brasileirão"
    Then the first-place team should be marked as champion
