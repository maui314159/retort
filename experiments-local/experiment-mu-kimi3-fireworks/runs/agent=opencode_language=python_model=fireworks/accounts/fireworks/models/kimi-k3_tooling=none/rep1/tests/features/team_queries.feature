Feature: Team Queries
  As a user of the Brazilian Soccer MCP server
  I want team statistics computed from match data
  So that I can answer questions like "What is Corinthians' home record in 2022?"

  Scenario: Get team statistics
    Given the match data is loaded
    When I request statistics for "Palmeiras" in season "2023"
    Then I should receive wins, losses, draws, and goals

  Scenario: Corinthians home record in 2022
    Given the match data is loaded
    When I request home statistics for "Corinthians" in season 2022 of "Brasileirão"
    Then the record should show 19 matches
    And the wins, draws and losses should add up to 19

  Scenario: Which team scored the most goals in Serie A 2023
    Given the match data is loaded
    When I ask for the top scoring teams of "Serie A" season 2023
    Then the top team should have scored more than 50 goals

  Scenario: What competitions has Palmeiras played in
    Given the match data is loaded
    When I ask which competitions "Palmeiras" has played in
    Then the answer should include "Brasileirão Série A"
    And the answer should include "Copa do Brasil"
    And the answer should include "Copa Libertadores"

  Scenario: Compare Palmeiras and Santos head-to-head
    Given the match data is loaded
    When I compare "Palmeiras" and "Santos" head-to-head
    Then the head-to-head summary should show wins for both teams and draws
    And the wins and draws should equal the total matches
