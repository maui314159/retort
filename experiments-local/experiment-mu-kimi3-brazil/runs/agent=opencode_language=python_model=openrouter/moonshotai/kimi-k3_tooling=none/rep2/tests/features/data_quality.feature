Feature: Data Quality
  Team name normalization, multi-format date parsing and UTF-8 handling.

  Scenario: Team name variations resolve to the same team
    Given the match data is loaded
    Then "Palmeiras-SP" and "Palmeiras" should resolve to the same team
    And "Flamengo-RJ" and "Flamengo" should resolve to the same team
    And "Sport-PE" and "Sport Recife" should resolve to the same team
    And "Athletico-PR" and "Athletico Paranaense" should resolve to the same team

  Scenario: Ambiguous names stay distinct
    Then "Botafogo-SP" and "Botafogo-RJ" should resolve to different teams
    And "Atlético-GO" and "Atlético-MG" should resolve to different teams

  Scenario: Multiple date formats are parsed
    Then "2023-09-24" should parse to the date "2023-09-24"
    And "29/03/2003" should parse to the date "2003-03-29"
    And "2012-05-19 18:30:00" should parse to the date "2012-05-19"

  Scenario: UTF-8 accented names are searchable with and without accents
    Given the match data is loaded
    When I search matches for team "São Paulo" in season 2019
    Then I should receive a list of matches
    When I search matches for team "Gremio" in season 2019
    Then I should receive a list of matches

  Scenario: All six CSV files are loaded and queryable
    Given the match data is loaded
    And the player data is loaded
    Then the dataset overview should list 5 match sources
    And the player table should have more than 18000 rows
