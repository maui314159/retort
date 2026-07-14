Feature: Data Coverage
  Verify that all CSV datasets are loaded and queryable.

  Scenario: All datasets load and provide data
    Given all datasets are loaded
    When I query for available teams and competitions
    Then I should find teams from all match datasets
    And I should find multiple competitions
    And I should find multiple seasons
