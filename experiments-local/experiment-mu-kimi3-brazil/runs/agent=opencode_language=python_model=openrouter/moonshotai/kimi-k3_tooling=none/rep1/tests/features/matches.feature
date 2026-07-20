Feature: Match Queries
  As a user I want to find matches by team, opponent, competition and season
  so that I can answer questions like "Show me all Flamengo vs Fluminense
  matches" or "What matches did Palmeiras play in 2023?".

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition
    And every match should be between "Flamengo" and "Fluminense"

  Scenario: Find matches of a team in a season
    Given the match data is loaded
    When I search for matches of "Palmeiras" in season "2023"
    Then I should receive a list of matches
    And every match should be from season 2023
    And every match should involve "Palmeiras"

  Scenario: Find matches in a competition
    Given the match data is loaded
    When I search for "Copa do Brasil" matches of "São Paulo"
    Then I should receive a list of matches
    And every match should be in competition "Copa do Brasil"

  Scenario: Team name variants resolve to the same matches
    Given the match data is loaded
    When I search for matches of "Palmeiras-SP" in season "2022"
    Then I should receive a list of matches
    And every match should be from season 2022
