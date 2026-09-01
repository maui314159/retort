Feature: Statistical Analysis
  Aggregates: goals per match, home advantage, biggest wins, extended stats.

  Scenario: Average goals per match
    Given the match data is loaded
    When I average the 2019 Brasileirão
    Then 380 matches produced 876 goals at 2.31 per match

  Scenario: Home advantage
    Given the match data is loaded
    When I compute 2019 win rates
    Then home wins exceed away wins and rates sum to 100%

  Scenario: Biggest wins
    Given the match data is loaded
    When I rank the biggest wins
    Then margins are sorted descending and each entry has full context

  Scenario: Extended match statistics
    Given the match data is loaded
    When I request Flamengo's 2023 match statistics
    Then corners, shots, attacks and half-time results are returned

  Scenario: Query performance
    Given the warm in-memory dataset
    When I run a simple lookup
    Then it responds in under 2 seconds
    When I run aggregate queries
    Then they respond in under 5 seconds
