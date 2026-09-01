Feature: Team Queries
  Team records, home/away splits, head-to-head comparisons and
  cross-file team profiles.

  Scenario: Get team statistics for a season
    Given the match data is loaded
    When I request statistics for "Corinthians" in season "2022" in competition "Brasileirão"
    Then I should receive wins, losses, draws, and goals
    And the home record should cover 19 matches

  Scenario: Team statistics aggregate across all competitions
    Given the match data is loaded
    When I request statistics for "Corinthians" in season "2022"
    Then the overall record should cover more matches than the Brasileirão alone

  Scenario: Compare two teams head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then the wins, draws and losses should add up to the number of matches
    And the head-to-head should include at least 40 matches

  Scenario: Team profile spans competitions and the player file
    Given the match data is loaded
    When I request the profile for "Palmeiras"
    Then the profile should list competitions including "Copa Libertadores"
    And the profile should show matches across more than one competition

  Scenario: Team name variants resolve to one team
    Given the match data is loaded
    When I request statistics for "palmeiras-sp" in season "2023"
    Then the statistics should be for "Palmeiras"

  Scenario: Which team scored the most goals in Serie A 2023
    Given the match data is loaded
    When I compute the 2023 Brasileirão standings
    Then the top-scoring team should have scored at least 60 goals
    And no team should have scored more goals than the top-scoring team

