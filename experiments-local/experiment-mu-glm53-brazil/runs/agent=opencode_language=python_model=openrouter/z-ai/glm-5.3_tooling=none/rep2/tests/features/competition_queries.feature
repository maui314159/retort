Feature: Competition Queries
  As a soccer fan asking questions in natural language
  I want standings, champions and competition metadata
  So that I can follow the Brasileirão, Copa do Brasil and Libertadores

  Scenario: Who won the 2019 Brasileirão
    Given the match data is loaded
    When I request the standings of "Brasileirão Série A" season 2019
    Then "Flamengo" should be champion with 90 points
    And the table should have 20 teams
    And the champion row should read 28 wins 6 draws 4 losses

  Scenario: Which teams were relegated in 2019
    Given the match data is loaded
    When I request the standings of "Brasileirão Série A" season 2019
    Then the relegated teams should be Avaí, Chapecoense, CSA and Cruzeiro

  Scenario: Runner-up ordering by wins tiebreak
    Given the match data is loaded
    When I request the standings of "Brasileirão Série A" season 2019
    Then "Santos" should be second with 74 points

  Scenario: Which team scored the most goals in 2023
    Given the match data is loaded
    When I request the standings of "Brasileirão Série A" season 2023
    Then the top scoring team should be Grêmio

  Scenario: Standings for cups are rejected
    Given the match data is loaded
    When I request the standings of "Copa do Brasil" season 2019
    Then the response should explain that cups have no standings

  Scenario: Standings require a season
    Given the match data is loaded
    When I request the standings of "Brasileirão Série A" without a season
    Then the response should list the available seasons

  Scenario: Competition info lists seasons and sources
    Given the match data is loaded
    When I request competition info
    Then 5 competitions should be described
    And the Copa Libertadores should span 2013 to 2022

  Scenario: Historical seasons are covered by the 2003-2019 dataset
    Given the match data is loaded
    When I request the standings of "Brasileirão Série A" season 2005
    Then the champion should be Corinthians
