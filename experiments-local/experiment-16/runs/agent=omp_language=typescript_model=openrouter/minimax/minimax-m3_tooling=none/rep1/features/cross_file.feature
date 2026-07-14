Feature: Data Quality & Cross-File Coverage
  The MCP server should handle team name variations and UTF-8 strings,
  and answer questions that span match + player data.

  Background:
    Given the dataset is loaded

  Scenario: State-suffixed team names are normalized
    When I search for matches where "Flamengo-RJ" played
    Then every match should involve the canonical "Flamengo"

  Scenario: Diacritics are normalized for matching
    When I search for matches where "São Paulo" played
    Then every match should involve "São Paulo"

  Scenario: The Brasileirao CSV is queryable
    When I search for matches in "brasileirao"
    Then the result count should be at least 4000

  Scenario: The Copa do Brasil CSV is queryable
    When I search for matches in "copa_do_brasil"
    Then the result count should be at least 1000

  Scenario: The Libertadores CSV is queryable
    When I search for matches in "libertadores"
    Then the result count should be at least 1000

  Scenario: The historical Brasileirão CSV is queryable
    When I search for matches in "brasileirao_historical"
    Then the result count should be at least 6000

  Scenario: The extended BR-Football dataset is queryable
    When I search for matches in "br_football"
    Then the result count should be at least 5000
