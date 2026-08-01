Feature: Data Quality Handling
  As a user of the Brazilian Soccer MCP server
  I want messy real-world inputs normalized
  So that team name variations, date formats and UTF-8 text all work

  Scenario Outline: Team name variations map to the same team
    Given the match data is loaded
    When I normalize the team name <raw>
    Then the canonical team should be <canonical>

    Examples:
      | raw                              | canonical            |
      | Palmeiras-SP                     | palmeiras            |
      | América - MG                     | america mineiro      |
      | Athletico-PR                     | athletico paranaense |
      | Vasco Da Gama RJ                 | vasco                |
      | São Paulo                        | sao paulo            |
      | Grêmio                           | gremio               |
      | Sport Club Corinthians Paulista  | corinthians          |
      | EC Bahia                         | bahia                |
      | Fortaleza FC                     | fortaleza            |

  Scenario Outline: Multiple date formats are parsed
    Given the match data is loaded
    When I parse the date <raw>
    Then the parsed date should be <expected>

    Examples:
      | raw                   | expected    |
      | 2023-09-24            | 2023-09-24  |
      | 29/03/2003            | 2003-03-29  |
      | 2012-05-19 18:30:00   | 2012-05-19  |

  Scenario: UTF-8 team names with accents are handled
    Given the match data is loaded
    Then the store should contain teams "sao paulo", "gremio" and "avai"

  Scenario: Competition names accept synonyms
    Given the match data is loaded
    Then "brasileirao" should resolve to the "serie a" competition
    And "Libertadores" should resolve to the "copa libertadores" competition
