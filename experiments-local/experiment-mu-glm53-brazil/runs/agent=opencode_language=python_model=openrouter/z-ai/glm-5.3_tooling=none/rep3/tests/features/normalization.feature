Feature: Data Quality and Normalization
  Handling the messy conventions of the six source CSVs.

  Scenario: Team name variations
    Given names like "Palmeiras-SP", "Palmeiras" and "América - MG"
    When they are normalized
    Then state suffixes are lifted and accents folded
    And official long names map onto canonical club identities

  Scenario: Same club, different spellings
    Given "Vasco" and "Vasco da Gama-RJ" from different files
    When the club registry is finalized
    Then both map to a single club entity

  Scenario: Different clubs, same short name
    Given Botafogo-RJ and Botafogo-PB, América-MG and América-RN
    When they are resolved
    Then the clubs remain distinct

  Scenario: Date formats
    Given "2023-09-24", "2012-05-19 18:30:00" and "29/03/2003"
    When dates are parsed
    Then all three yield the correct calendar date

  Scenario: Missing values
    Given "NA" goals and dates in the raw data
    When rows are parsed
    Then they are kept as unscored fixtures, never counted in statistics

  Scenario: Character encoding
    Given UTF-8 names like São Paulo, Grêmio and Avaí
    When normalized
    Then accents fold to ASCII for matching while display keeps them

  Scenario: Competition aliases
    Given free text like "serie a", "CdB" and "libertadores"
    When resolved
    Then the canonical competition names are returned
