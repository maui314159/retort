Feature: Statistical Analysis
  As a user of the Brazilian Soccer MCP server
  I want aggregated statistics calculated from match data
  So that I can answer analytical questions

  Scenario: Average goals per match in the Brasileirão
    Given the match data is loaded
    When I ask for statistics of the "Brasileirão"
    Then the average goals per match should be between 2.0 and 3.0
    And the home win rate should be between 40 and 60 percent

  Scenario: Win rates split adds up to 100
    Given the match data is loaded
    When I ask for statistics of the "Copa do Brasil"
    Then home, draw and away rates should sum to 100 percent

  Scenario: Show me the biggest wins in the dataset
    Given the match data is loaded
    When I ask for the 5 biggest victories
    Then the margins should be sorted descending
    And the biggest margin should be at least 8 goals

  Scenario: Which team has the best away record
    Given the match data is loaded
    When I ask for the best away records of "Serie A" season 2022
    Then the teams should be ranked by win rate

  Scenario: Compare the 2018 and 2019 seasons
    Given the match data is loaded
    When I compare "Serie A" seasons 2018 and 2019
    Then both seasons should report 380 matches
    And the comparison should include average goals and home win rate
