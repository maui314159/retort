Feature: Match Queries
  Searching match data across all competitions by team, season,
  competition and date range.

  Scenario: Find matches between two teams
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then I should receive a list of matches
    And each match should have date, scores, and competition

  Scenario: Head-to-head matches come from both sides' home grounds
    Given the match data is loaded
    When I search for matches between "Flamengo" and "Fluminense"
    Then some matches should have "Flamengo" at home
    And some matches should have "Fluminense" at home

  Scenario: Matches for one team in a season
    Given the match data is loaded
    When I search for matches of team "Palmeiras" in season "2023"
    Then all returned matches should involve "Palmeiras"
    And all returned matches should be from season 2023
    And more than 30 matches should be found

  Scenario: Filter matches by competition
    Given the match data is loaded
    When I search for matches of team "Corinthians" in competition "Libertadores"
    Then all returned matches should be from the Libertadores

  Scenario: Filter matches by date range
    Given the match data is loaded
    When I search for matches between dates "2023-06-01" and "2023-06-15"
    Then all returned matches should fall within the date range
    And the search should find at least 20 matches

  Scenario: Most recent match between two teams
    Given the match data is loaded
    When I request the last match between "Flamengo" and "Corinthians"
    Then I should receive a single match
    And the match should have a score

  Scenario: Unresolvable team name is reported clearly
    Given the match data is loaded
    When I search for matches of team "ZZZ Unknown Club ZZZ"
    Then the search should fail with a helpful message

  Scenario: Copa do Brasil finals can be found
    Given the match data is loaded
    When I list the finals of the "Copa do Brasil"
    Then finals from several seasons should be returned
    And the 2012 final should be between "Palmeiras" and "Coritiba"
