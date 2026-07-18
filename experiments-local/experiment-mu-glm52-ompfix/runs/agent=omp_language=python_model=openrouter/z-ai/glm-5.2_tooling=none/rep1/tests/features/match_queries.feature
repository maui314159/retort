Feature: Match Queries
  As a soccer fan
  I want to search for matches by team, opponent, competition, and season
  So that I can find specific games in the Brazilian soccer dataset

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get head-to-head record
    Given the match data is loaded
    When I request the head-to-head record between "Palmeiras" and "Santos"
    Then I should receive wins, losses, and draws for both teams

  Scenario: Find matches by competition and season
    Given the match data is loaded
    When I search for matches in competition "Brasileirão" in season 2019
    Then I should receive matches from that competition and season

  Scenario: Team not found returns error message
    Given the match data is loaded
    When I search for matches for team "Nonexistent FC"
    Then I should receive an error message
