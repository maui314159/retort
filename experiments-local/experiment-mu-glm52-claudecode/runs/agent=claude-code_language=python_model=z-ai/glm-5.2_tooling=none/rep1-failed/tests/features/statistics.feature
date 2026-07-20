Feature: Statistical Analysis
  As a soccer fan asking natural-language questions
  I want aggregated statistics across the dataset
  So that I can compare eras, venues and extremes.

  Scenario: Average goals per match in the Brasileirão
    Given the match data is loaded
    When I request average goals for competition "Brasileirão Série A"
    Then the average goals should be between 2 and 3
    And the home win rate should exceed the away win rate

  Scenario: Biggest victories in the dataset
    Given the match data is loaded
    When I request the biggest wins in competition "Brasileirão Série A"
    Then I should receive a list ranked by margin
    And every margin should be positive

  Scenario: Home advantage quantified
    Given the match data is loaded
    When I request home advantage for competition "Brasileirão Série A" in season 2019
    Then I should receive a home advantage index
    And the home win rate should exceed the away win rate

  Scenario: Best home record in a season
    Given the match data is loaded
    When I request the best home record for competition "Brasileirão Série A" in season 2019
    Then I should receive a ranked list of teams by home win rate
    And Flamengo should top the 2019 home record

  Scenario: Most active teams in the knowledge graph
    Given the match data is loaded
    When I request the most active teams
    Then I should receive a list of teams with match counts
    And the list should be sorted by match count descending
