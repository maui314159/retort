Feature: Competition Queries
  As a soccer fan asking natural-language questions
  I want standings, champions, relegation and cup finals calculated from match results
  So that I can answer questions about each competition season

  Scenario: Who won the 2019 Brasileirão
    Given the match data is loaded
    When I request the "Série A" standings for 2019
    Then the champion should be Flamengo with 90 points
    And the top three should be Flamengo, Santos and Palmeiras
    And the table should list 20 teams
    And the season should be complete with 380 matches

  Scenario: Which teams were relegated in 2020
    Given the match data is loaded
    When I request the "Série A" standings for 2020
    Then the relegated teams should be Coritiba, Vasco, Goiás and Botafogo

  Scenario: Copa do Brasil finals and winners
    Given the match data is loaded
    When I request the "Copa do Brasil" finals
    Then the 2012 final should be won by Palmeiras against Coritiba
    And the 2015 final should be decided on penalties

  Scenario: Copa Libertadores finals and winners
    Given the match data is loaded
    When I request the "Libertadores" finals
    Then the 2019 final should be won by Flamengo against River Plate

  Scenario: Standings are only for leagues
    Given the match data is loaded
    When I request the "Libertadores" standings for 2019
    Then I should receive an error explaining standings apply to leagues

  Scenario: Competition coverage
    Given the match data is loaded
    When I request the competition information
    Then Série A, Série B, Série C, Copa do Brasil and Libertadores should be listed
    And each competition should cover multiple seasons
