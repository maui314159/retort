Feature: Competition Queries
  As a soccer analyst
  I want to retrieve competition standings and winners
  So that I can determine season outcomes

  Scenario: Calculate standings for a season
    Given the match data is loaded
    When I request standings for season "2019" competition "Brasileirao"
    Then I should receive a table sorted by points descending
    And the first team should be the champion

  Scenario: Determine competition winner
    Given the match data is loaded
    When I request the winner for season "2019" competition "Brasileirao"
    Then the winner should be "Flamengo"
