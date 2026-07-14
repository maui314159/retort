Feature: Team Queries

Scenario: Get head to head record
  Given the match data is loaded
  When I request head to head between "Corinthians" and "Palmeiras"
  Then I should receive win counts for both teams and draws

Scenario: Search for players by nationality
  Given the player data is loaded
  When I search for players with nationality "Brazil" and min rating 85
  Then I should receive a list of highly rated Brazilian players