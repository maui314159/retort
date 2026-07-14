Feature: Brazilian Soccer MCP Server

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Corinthians"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras"
    Then I should receive wins, losses, draws, and goals

  Scenario: Search for players by nationality
    Given the player data is loaded
    When I search for players with nationality "Brazil"
    Then I should receive a list of Brazilian players
    And each player should have name, club, and overall rating

  Scenario: Handle team name variations
    Given the match data is loaded
    When I search for matches for "Sport Club Corinthians Paulista"
    Then I should receive matches for "Corinthians"

  Scenario: Calculate competition standings
    Given the match data is loaded
    When I request standings for "Brasileirão Serie A" in season "2019"
    Then I should receive a ranked list of teams with points

  Scenario: Get head-to-head record
    Given the match data is loaded
    When I request head-to-head between "Flamengo" and "Fluminense"
    Then I should receive total matches, wins for each team, and draws

  Scenario: Statistical analysis - average goals
    Given the match data is loaded
    When I request statistical analysis for "avg_goals"
    Then I should receive the average goals per match

  Scenario: Handle multiple date formats
    Given the match data is loaded
    When I search for matches in season "2003"
    Then I should receive matches with properly formatted dates
