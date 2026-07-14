Feature: Data Quality

  Scenario: Team name normalization
    Given the match data is loaded
    When I search for matches with team "Palmeiras-SP"
    Then results should match normalized team name "Palmeiras"

  Scenario: All CSV files are loadable
    Given the data directory
    Then all six CSV files should be loadable and queryable
