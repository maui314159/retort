Feature: Data Coverage
  As a verifier of the Brazilian Soccer MCP server
  I want to confirm all provided datasets are loadable and queryable
  So that the success criteria of the specification are met

  Scenario: All six CSV files are loadable
    Given the data is loaded
    Then the matches dataframe should contain rows from every match dataset
    And the players dataframe should contain FIFA players

  Scenario: Team name normalization across files
    Given the data is loaded
    Then "Flamengo-RJ" and "Flamengo" should map to the same team
    And "Atlético-MG" and "Atletico Mineiro" should map to the same team
    And "São Paulo" and "Sao Paulo" should map to the same team

  Scenario: Cross-file query
    Given the data is loaded
    When I request players at "Grêmio" and the head to head of "Grêmio" against "Internacional"
    Then both queries should return results
