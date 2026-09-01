Feature: Statistical Analysis
  As an LLM using the Brazilian Soccer MCP server
  I want aggregated statistics and knowledge-graph lookups
  So that I can answer analytical questions about Brazilian soccer

  Background:
    Given the Brazilian soccer data is loaded

  Scenario: Head-to-head record between classic rivals
    When I request the head-to-head record of "Flamengo" and "Vasco da Gama"
    Then the record should have at least one match
    And wins and draws should add up to the matches played

  Scenario: Biggest victories are ordered by margin
    When I request the biggest victories in "Brasileirão Série A"
    Then I should receive a list of matches
    And each match margin should be greater than or equal to the next one

  Scenario: Average goals per match are reported
    When I request statistics for competition "Brasileirão Série A"
    Then the average goals per match should be between 1 and 5

  Scenario: Search the knowledge graph
    When I search the knowledge graph for "Palmeiras"
    Then I should receive graph nodes
    And every node name should contain "Palmeiras"

  Scenario: Explore knowledge graph relationships
    When I request the graph neighbors of "Flamengo"
    Then I should receive relationships such as played or participates_in

  Scenario: Performance budget
    When I run the search for team "Flamengo" in season 2019
    Then the query should complete within 2 seconds
