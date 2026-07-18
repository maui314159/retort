Feature: Competition Queries
  As a soccer fan
  I want to query competition standings and information
  So that I can see who won each season and which teams participated

  Scenario: Get standings for a season
    Given the match data is loaded
    When I request standings for competition "Brasileirão" in season 2019
    Then I should receive a ranked table of teams
    And the first team should be marked as champion
    And the champion should be "Flamengo"

  Scenario: Get competition information
    Given the match data is loaded
    When I request information for competition "Libertadores"
    Then I should receive seasons and match count
    And the match count should be at least 1000

  Scenario: Get standings for a non-existent competition
    Given the match data is loaded
    When I request standings for competition "Champions League" in season 2019
    Then I should receive an error message
