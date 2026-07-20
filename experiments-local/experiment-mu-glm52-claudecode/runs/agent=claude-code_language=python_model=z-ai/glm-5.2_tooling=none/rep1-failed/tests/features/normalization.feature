Feature: Team Name Normalization
  As a soccer fan asking natural-language questions
  I want team name variations to resolve to one canonical club
  So that "Palmeiras-SP", "Palmeiras" and the long form all match.

  Scenario Outline: Common spellings resolve to one canonical name
    Given the match data is loaded
    When I normalize the team name "<spelling>"
    Then the canonical name should be "<canonical>"

    Examples:
      | spelling        | canonical            |
      | Palmeiras-SP    | Palmeiras            |
      | Palmeiras       | Palmeiras            |
      | Flamengo-RJ     | Flamengo             |
      | Flamengo        | Flamengo             |
      | Sao Paulo       | São Paulo            |
      | São Paulo-SP    | São Paulo            |
      | Gremio          | Grêmio               |
      | Grêmio-RS       | Grêmio               |
      | Atletico-MG     | Atlético Mineiro     |
      | Atletico Mineiro| Atlético Mineiro     |
      | Athletico-PR    | Athletico Paranaense |
      | Atletico-PR     | Athletico Paranaense |
      | America-MG      | América Mineiro      |
      | America MG      | América Mineiro      |
      | Ceara           | Ceará                |
      | Ceará-CE        | Ceará                |

  Scenario: Disambiguation by state suffix for ambiguous bases
    Given the match data is loaded
    When I normalize the team names "Atletico-MG" and "Atletico-PR"
    Then they should resolve to different canonical clubs
