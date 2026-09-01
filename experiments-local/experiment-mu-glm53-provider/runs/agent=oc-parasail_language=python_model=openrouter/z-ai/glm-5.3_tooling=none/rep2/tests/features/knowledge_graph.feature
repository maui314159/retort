Feature: Knowledge Graph
  As an LLM exploring the soccer knowledge graph
  I want graph overview, team neighbourhoods and entity connections
  So that I can answer structural questions spanning players, teams and matches

  Scenario: Graph overview
    Given the knowledge graph is built
    When I request the graph overview
    Then the graph should contain match, club, player and competition nodes
    And the edge counts should include played_home and plays_for relations

  Scenario: Team graph neighbourhood
    Given the knowledge graph is built
    When I request the team graph for "Palmeiras"
    Then the result should include competitions Palmeiras played in
    And the result should include the most frequent opponents
    And Flamengo should be among the opponents

  Scenario: Connections between two players
    Given the knowledge graph is built
    When I request paths between "Neymar" and "Alisson"
    Then a connection through the Brazil country node should be found

  Scenario: Connections between two teams that played each other
    Given the knowledge graph is built
    When I request paths between "Flamengo" and "Fluminense"
    Then a two-hop connection through a match node should be found
