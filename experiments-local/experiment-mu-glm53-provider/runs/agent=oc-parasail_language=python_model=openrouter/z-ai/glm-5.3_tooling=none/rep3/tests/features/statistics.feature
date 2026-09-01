Feature: Statistical Analysis
  Aggregated statistics: goals per match, home advantage, biggest wins,
  best venue records, derbies and season comparisons.

  Scenario: Average goals per match in the Brasileirão
    Given the match data is loaded
    When I request competition statistics for "Brasileirão"
    Then the average goals per match should be between 2 and 3
    And the home win rate should be higher than the away win rate

  Scenario: Biggest wins in the dataset
    Given the match data is loaded
    When I request the biggest wins
    Then the biggest margin should be at least 7 goals
    And the results should be sorted by margin descending

  Scenario: Best away record in a season
    Given the match data is loaded
    When I request the best away records for "Brasileirão" season "2023"
    Then the best away team should be "Flamengo"

  Scenario: Home advantage is measurable
    Given the match data is loaded
    When I request competition statistics for all competitions
    Then the home win rate should be above 40 percent
    And the away win rate should be below 30 percent

  Scenario: Compare the 2018 and 2019 seasons
    Given the match data is loaded
    When I compare seasons 2018 and 2019 of the "Brasileirão"
    Then the 2018 champion should be "Palmeiras"
    And the 2019 champion should be "Flamengo"
    And both seasons should average at least 2 goals per match

  Scenario: Derbies in a season
    Given the match data is loaded
    When I request the derbies of season "2023"
    Then at least 10 named derbies should have matches
    And the Fla-Flu derby should appear

  Scenario: Goals-per-match per season stays sane
    Given the match data is loaded
    When I request competition statistics for "Brasileirão" season "2019"
    Then the average goals per match should be between 2 and 3
