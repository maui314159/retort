Feature: Team Queries
  As a user of the Brazilian Soccer MCP server
  I want to inspect team records
  So that I can compare teams and analyse their performance

  Scenario: Team statistics for a season
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season 2019
    Then I should receive wins, draws, losses and goals
    And the win rate should be a percentage between 0 and 100

  Scenario: Team home record
    Given the match data is loaded
    When I request home statistics for "Corinthians" in season 2019
    Then the venue should be home
    And the matches count should equal wins plus draws plus losses

  Scenario: Team competitions
    Given the match data is loaded
    When I ask which competitions "Palmeiras" played in
    Then I should receive a list of competitions with match counts

  Scenario: Head to head comparison
    Given the match data is loaded
    When I compare "Flamengo" and "Fluminense" head to head
    Then I should receive win counts for both teams and a draw count
    And the total matches should equal the sum of wins and draws
