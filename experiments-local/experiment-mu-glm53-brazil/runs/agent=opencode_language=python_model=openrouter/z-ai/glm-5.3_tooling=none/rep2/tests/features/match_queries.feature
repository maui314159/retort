Feature: Match Queries
  As a soccer fan asking questions in natural language
  I want to search the match datasets by team, date, competition and season
  So that I can find fixtures, scores and competitions

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2023
    Then I should receive wins, losses, draws, and goals

  Scenario: Find matches for a team in a season
    Given the match data is loaded
    When I search for matches of team "Palmeiras" in season 2023
    Then I should receive a list of matches
    And every match should involve the team "Palmeiras"
    And every match should be from season 2023

  Scenario: Find all Copa do Brasil finals
    Given the match data is loaded
    When I search for finals of competition "Copa do Brasil"
    Then every match should be from competition "Copa do Brasil"
    And each season should contribute at most 2 finals
    And the dataset should contain 18 finals

  Scenario: Find matches by date range
    Given the match data is loaded
    When I search for matches from "2019-11-01" to "2019-11-30" in competition "Brasileirão Série A" and season 2019
    Then every match should fall within the date range
    And the result should not be empty

  Scenario: Find the most recent match between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Corinthians"
    Then the last match should be on "2023-10-08"
    And the last match should have a score

  Scenario: Reject unknown teams politely
    Given the match data is loaded
    When I search for matches of team "Manchester United"
    Then the response should explain the team was not found
