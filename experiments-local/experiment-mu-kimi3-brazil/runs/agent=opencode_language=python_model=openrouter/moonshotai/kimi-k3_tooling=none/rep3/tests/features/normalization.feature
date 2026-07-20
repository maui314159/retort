Feature: Data Quality and Cross-file Queries
  As a consumer of the MCP server
  I want team names, dates and encodings handled consistently
  So that queries work across all six provided CSV files

  Scenario: Team name variations normalise to the same key
    Then the team names "Palmeiras-SP", "Palmeiras" and "palmeiras" should all normalise to "palmeiras"
    And the team names "Atletico-PR", "Athletico Paranaense" and "Athletico" should all normalise to "athletico pr"
    And the team names "Atletico-MG" and "Atletico Mineiro" should all normalise to "atletico mg"
    And the team names "América - MG" and "America MG" should both normalise to "america mg"

  Scenario: Accented team names are supported
    Then the team name "Grêmio-RS" should normalise to "gremio"
    And the team name "São Paulo-SP" should normalise to "sao paulo"

  Scenario: Multiple date formats are parsed
    Then the date "2023-09-24" should parse to year 2023 month 9 day 24
    And the date "29/03/2003" should parse to year 2003 month 3 day 29
    And the date "2012-05-19 18:30:00" should parse to year 2012 month 5 day 19

  Scenario: All six CSV files are loaded
    Given the soccer data is loaded
    Then matches from source "Brasileirao_Matches" should be present
    And matches from source "Brazilian_Cup_Matches" should be present
    And matches from source "Libertadores_Matches" should be present
    And matches from source "BR-Football-Dataset" should be present
    And matches from source "novo_campeonato_brasileiro" should be present
    And the player table should contain more than 18000 players

  Scenario: Cross-file query links players and matches
    Given the soccer data is loaded
    When I search for players at club "Grêmio"
    And I search for matches of "Grêmio" in competition "Brasileirão" and season 2019
    Then the club search should return at least 10 players
    And the match search should return 38 matches
