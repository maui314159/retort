Feature: Statistical Analysis
  As a soccer fan asking questions in natural language
  I want aggregated statistics across the datasets
  So that I can compare eras, venues and rivalries

  Scenario: Average goals per match in the Brasileirão
    Given the match data is loaded
    When I request league statistics for "Brasileirão Série A"
    Then the average goals per match should be between 2 and 3
    And the home win rate should be higher than the away win rate

  Scenario: Biggest wins in the dataset
    Given the match data is loaded
    When I request the 5 biggest wins
    Then the largest margin should be at least 8 goals
    And wins should be ordered by decreasing margin

  Scenario: Best home record
    Given the match data is loaded
    When I request the best home records in "Brasileirão Série A"
    Then the records should be ranked by win rate
    And the records should not be empty

  Scenario: Best away record
    Given the match data is loaded
    When I request the best away records
    Then the records should not be empty
    And the records should be ranked by win rate

  Scenario: Compare the 2018 and 2019 seasons
    Given the match data is loaded
    When I request league statistics for "Brasileirão Série A" season 2019
    Then the seasons should be comparable
    And the average goals per match should be between 2 and 3

  Scenario: List classic derbies
    Given the match data is loaded
    When I request derby matches
    Then the Fla-Flu derby should be listed
    And the Gre-Nal derby should be listed
    And every derby should have a positive match count

  Scenario: Derbies in a specific season
    Given the match data is loaded
    When I request derby matches for season 2023
    Then the Fla-Flu derby should be listed
    And the Majestoso derby should be listed
