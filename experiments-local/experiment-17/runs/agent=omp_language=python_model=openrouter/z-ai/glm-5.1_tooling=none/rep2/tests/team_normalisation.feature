Feature: Team Name Normalisation
  Verify that team names are normalised correctly across datasets.

  Scenario Outline: Normalise team names with state suffixes
    Given the team name normaliser is available
    When I normalise the team name "<raw_name>"
    Then the result should be "<expected>"

    Examples:
      | raw_name        | expected    |
      | Palmeiras-SP    | Palmeiras   |
      | Flamengo-RJ     | Flamengo    |
      | Corinthians-SP  | Corinthians |
      | São Paulo-SP    | São Paulo   |
