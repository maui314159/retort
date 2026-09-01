Feature: Dataset Loading and Canonical Index
  All six CSVs load; overlapping sources are deduplicated.

  Scenario: All six files are loadable
    Given the bundled Kaggle datasets
    When the dataset is assembled
    Then row counts match the sources:
      | file | rows |
      | Brasileirao_Matches.csv | 4180 |
      | Brazilian_Cup_Matches.csv | 1337 |
      | Libertadores_Matches.csv | 1255 |
      | novo_campeonato_brasileiro.csv | 6886 |
      | BR-Football-Dataset.csv | 10296 |
      | fifa_data.csv | 18207 |

  Scenario: One authoritative source per season
    Given three files covering overlapping Brasileirão seasons
    When the canonical index is built
    Then 2003-2011 comes from the historical file,
      2012-2022 from the dedicated Brasileirão file,
      2023 from BR-Football

  Scenario: No double counting
    Given overlapping sources
    When the canonical index is built
    Then no fixture appears twice in a competition-season

  Scenario: Complete season coverage
    Given the 2019 Brasileirão
    When counted
    Then all 380 fixtures are present with scores

  Scenario: FIFA club join
    Given the FIFA club strings
    When joined through the club registry
    Then Grêmio's 20 players attach to the Grêmio club entity
