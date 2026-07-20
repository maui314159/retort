Feature: Competition Queries
  As a soccer fan asking natural-language questions
  I want standings and competition summaries computed from match results
  So that I can answer who won a season or what a competition contains.

  Scenario: Standings for the 2019 Brasileirão
    Given the match data is loaded
    When I request standings for competition "Brasileirão Série A" in season 2019
    Then I should receive a sorted standings table
    And Flamengo should be the champion of the 2019 Brasileirão
    And each team should have played a positive number of matches

  Scenario: Standings for the 2018 Brasileirão
    Given the match data is loaded
    When I request standings for competition "Brasileirão Série A" in season 2018
    Then I should receive a sorted standings table
    And Palmeiras should be the champion of the 2018 Brasileirão

  Scenario: Competition info lists seasons and teams
    Given the match data is loaded
    When I request info for competition "Copa Libertadores"
    Then I should receive a seasons list and a teams list
    And the total matches should be positive
