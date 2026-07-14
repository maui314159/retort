Feature: Competition Queries
  Query competition standings and metadata.

  Scenario: Competition standings
    Given the match data is loaded
    When I request standings for "Brasileirão" season 2019
    Then I should receive a ranked table with points wins draws and losses

  Scenario: List competitions
    Given the match data is loaded
    When I list all competitions
    Then I should see at least 3 different competitions

  Scenario: List seasons
    Given the match data is loaded
    When I list seasons for "Brasileirão"
    Then I should see multiple seasons
