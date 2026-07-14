Feature: Match Queries

Scenario: Find matches between two teams
  Given the match data is loaded
  When I search for matches between "Flamengo" and "Fluminense"
  Then I should receive a list of matches
  And each match should have date, scores, and competition

Scenario: Get team statistics
  Given the match data is loaded
  When I request statistics for "Palmeiras" in season 2023
  Then I should receive wins, losses, draws, and goals