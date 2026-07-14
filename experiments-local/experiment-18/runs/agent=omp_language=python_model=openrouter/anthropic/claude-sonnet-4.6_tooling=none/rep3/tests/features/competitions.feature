Feature: Competition and Statistics Queries
  As an analyst
  I want standings, champions and aggregate statistics
  So that I can summarize competitions and seasons

  Scenario: Compute final standings for a season
    Given the match data is loaded
    When I compute the 2019 "Brasileirao" standings
    Then the champion should be "Flamengo"
    And the champion should have 90 points
    And the top team should have played 38 matches

  Scenario: Identify the champion of a season
    Given the match data is loaded
    When I ask who won the 2019 "Brasileirao"
    Then the answer should name "Flamengo"

  Scenario: Average goals per match is plausible
    Given the match data is loaded
    When I compute aggregate statistics for "Brasileirao"
    Then the average goals per match should be between 2 and 3
    And the home win rate should be greater than the away win rate

  Scenario: Biggest wins are ordered by margin
    Given the match data is loaded
    When I list the biggest wins in "Brasileirao"
    Then each win should have a margin not greater than the previous one
