Feature: Competition Queries
  Standings computed from match results, champions and cup brackets.

  Scenario: League champion
    Given the match data is loaded
    When I ask who won the 2019 Brasileirão
    Then Flamengo is champion with 90 points (28W 6D 4L)

  Scenario: Relegation zone
    Given the match data is loaded
    When I ask which teams were relegated in 2020
    Then Vasco da Gama, Goiás, Coritiba and Botafogo are identified

  Scenario: Tie-breaker ordering
    Given the match data is loaded
    When I compute the 2019 table
    Then Santos (22 wins) ranks above Palmeiras (21 wins) at 74 points

  Scenario: Incomplete season caveat
    Given the match data is loaded
    When I compute the 2023 standings
    Then a note reports that 377 of 380 matches have scores

  Scenario: Home and away tables
    Given the match data is loaded
    When I compute the 2019 away table
    Then each team counts 19 away matches and Flamengo leads

  Scenario: Cup standings are refused
    Given the match data is loaded
    When I request standings for the Copa do Brasil
    Then I am pointed to champion() and bracket() instead

  Scenario: Cup champion by aggregate
    Given the match data is loaded
    When I ask who won the 2019 Copa do Brasil
    Then Athletico Paranaense is champion on a 3-1 aggregate

  Scenario: Penalty-decided final
    Given the match data is loaded
    When I ask who won the 2013 Copa Libertadores
    Then the 2-2 aggregate is reported as penalty-decided (winner unknown)

  Scenario: Cup bracket
    Given the match data is loaded
    When I request the 2018 Copa Libertadores bracket
    Then Final, Semifinals, Quarterfinals and Round of 16 are listed

  Scenario: Competition coverage
    Given the match data is loaded
    When I request competition info
    Then all five competitions with their seasons and champions appear
