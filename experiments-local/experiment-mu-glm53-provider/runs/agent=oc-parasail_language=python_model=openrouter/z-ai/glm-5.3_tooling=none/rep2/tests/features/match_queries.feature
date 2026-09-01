Feature: Match Queries
  As a soccer fan asking natural-language questions
  I want to search matches by team, opponent, competition, season, date and stage
  So that I can find any fixture in the Brazilian soccer datasets

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    And only Flamengo and Fluminense should be involved

  Scenario: Matches for a team in a season and competition
    Given the match data is loaded
    When I search for matches of "Palmeiras" in competition "Série A" in season 2023
    Then every match should involve Palmeiras
    And every match should be from the 2023 Brasileirão Série A

  Scenario: Find Copa Libertadores finals
    Given the match data is loaded
    When I search for Libertadores matches in stage "final" in season 2019
    Then every match should be a final
    And the 2019 final should be Flamengo 2-1 River Plate

  Scenario: Filter matches by date range
    Given the match data is loaded
    When I search for matches from "2019-06-01" to "2019-06-30" in competition "Copa do Brasil"
    Then every match should be dated within June 2019
    And every match should be a Copa do Brasil match

  Scenario: Team name variants resolve to the same team
    Given the match data is loaded
    When I search for matches of "Flamengo-RJ" in season 2012
    And I search for matches of "CR Flamengo" in season 2012
    Then both searches should return the same number of matches
