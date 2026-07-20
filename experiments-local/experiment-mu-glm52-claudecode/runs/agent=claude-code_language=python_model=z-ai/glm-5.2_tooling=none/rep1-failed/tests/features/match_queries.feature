Feature: Match Queries
  As a soccer fan asking natural-language questions
  I want to search matches by team, opponent, competition and date
  So that I can find fixtures and scores across all provided datasets.

  Scenario: Find matches between two traditional rivals (Fla-Flu)
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have a date, scores and competition
    And Flamengo and Fluminense should both appear in every match

  Scenario: Find all Palmeiras matches in the 2023 season
    Given the match data is loaded
    When I search for matches of team "Palmeiras" in season 2023
    Then I should receive a list of matches
    And every match should have season 2023
    And every match should involve Palmeiras

  Scenario: Find matches in a competition by name
    Given the match data is loaded
    When I search for matches in competition "Copa do Brasil" in season 2019
    Then I should receive a list of matches
    And every match should belong to competition "Copa do Brasil"

  Scenario: Find matches by date range
    Given the match data is loaded
    When I search for matches between "2019-09-01" and "2019-09-30"
    Then I should receive a list of matches
    And every match date should fall within September 2019

  Scenario: Head-to-head record between two teams
    Given the match data is loaded
    When I request the head-to-head record between "Flamengo" and "Fluminense"
    Then I should receive a summary with total matches, wins, draws and goals
    And the wins plus draws plus losses should equal the total matches
