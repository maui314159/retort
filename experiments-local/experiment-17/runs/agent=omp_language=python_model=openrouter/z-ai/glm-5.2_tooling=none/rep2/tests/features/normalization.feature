Feature: Team Name Normalisation
  As a soccer analyst
  I want team names from different sources to match consistently
  So that cross-file queries return correct results.

  Scenario Outline: Same club under different spellings resolves to one id
    Given the match data is loaded
    When I resolve the team name "<name>"
    Then the canonical id should be "<id>"

    Examples:
      | name               | id               |
      | Palmeiras-SP       | palmeiras sp     |
      | Palmeiras          | palmeiras sp     |
      | São Paulo          | sao paulo sp     |
      | Sao Paulo          | sao paulo sp     |
      | Atlético-MG        | atletico mg      |
      | Atletico Mineiro   | atletico mg      |
      | Athletico-PR       | atletico pr      |
      | Atletico Paranaense| atletico pr      |
      | Atlético-GO        | atletico go      |
      | Sport-PE           | sport pe         |
      | Sport Recife       | sport pe         |
      | Botafogo-RJ        | botafogo rj      |
      | Botafogo RJ        | botafogo rj      |
      | Botafogo           | botafogo rj      |
      | Bahia-BA           | bahia ba         |
      | EC Bahia           | bahia ba         |
      | Fortaleza-CE       | fortaleza ce     |
      | Fortaleza FC       | fortaleza ce     |
      | Flamengo-RJ        | flamengo rj      |
      | Flamengo           | flamengo rj      |

  Scenario: Different-state clubs with the same short name stay distinct
    Given the match data is loaded
    When I resolve the team names "Atlético-MG" and "Atlético-GO"
    Then their canonical ids should differ
