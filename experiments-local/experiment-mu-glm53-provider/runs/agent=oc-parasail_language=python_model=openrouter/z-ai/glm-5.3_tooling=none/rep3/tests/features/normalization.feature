Feature: Data Normalization
  Team name variants, date formats and character encoding are
  normalized so cross-file queries work.

  Scenario: State suffixes are stripped consistently
    Given the match data is loaded
    Then the names "Palmeiras-SP", "Palmeiras - SP" and "Palmeiras" should resolve to the same team
    And the names "Flamengo-RJ" and "Flamengo" should resolve to the same team

  Scenario: Full legal names resolve to the canonical club
    Given the match data is loaded
    Then the name "Sport Club Corinthians Paulista" should resolve to "Corinthians"
    And the name "Sport Club do Recife" should resolve to "Sport Recife"
    And the name "América FC (Minas Gerais)" should resolve to "América Mineiro"

  Scenario: Accented and unaccented spellings are the same team
    Given the match data is loaded
    Then the names "São Paulo", "Sao Paulo" and "Sao Paulo-SP" should resolve to the same team
    And the names "Grêmio" and "Gremio-RS" should resolve to the same team

  Scenario: Athletico Paranaense spelling drift
    Given the match data is loaded
    Then the names "Atletico-PR", "Atlético-PR", "Athletico Paranaense" and "Athletico" should resolve to the same team

  Scenario: Namesake clubs stay distinct
    Given the match data is loaded
    Then the name "Flamengo - PI" should not resolve to "Flamengo"
    And the name "Botafogo - PB" should not resolve to "Botafogo"
    And the name "América - RN" should not resolve to "América Mineiro"

  Scenario: Multiple date formats are parsed
    Then the date "2023-09-24" should parse to 2023-09-24
    And the date "29/03/2003" should parse to 2003-03-29
    And the date "2012-05-19 18:30:00" should parse to 2012-05-19
    And the date "NA" should not parse

  Scenario: Unplayable rows are skipped during loading
    Given the match data is loaded
    Then the loaded match count should be lower than the raw CSV row count

  Scenario: The same fixture in two files is only counted once
    Given the match data is loaded
    Then the 2012 Brasileirão season should have 380 matches

  Scenario: UTF-8 names survive round-trips
    Then the folded form of "São Paulo" should be "sao paulo"
    And the folded form of "Fortaleza Esporte Clube" should be "fortaleza esporte clube"
