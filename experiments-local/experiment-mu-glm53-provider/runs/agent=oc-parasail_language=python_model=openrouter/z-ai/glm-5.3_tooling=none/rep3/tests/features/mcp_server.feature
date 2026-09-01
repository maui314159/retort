Feature: MCP Server
  The server exposes its capabilities over the Model Context Protocol.

  Scenario: The server lists its tools
    Given the MCP server is running
    When I list the available tools
    Then at least 15 tools should be available
    And the tool list should include "search_matches", "search_players", "standings", "head_to_head" and "champion"

  Scenario: Answering a match question through the server
    Given the MCP server is running
    When I call the MCP tool "search_matches" with arguments "team=Flamengo, opponent=Fluminense, limit=5"
    Then the response should contain "Flamengo"
    And the response should contain "Fluminense"
    And the response should contain "matches in dataset"

  Scenario: Answering a player question through the server
    Given the MCP server is running
    When I call the MCP tool "search_players" with arguments "nationality=Brazil, limit=3"
    Then the response should contain "Neymar Jr"
    And the response should contain "Brazil"

  Scenario: Answering a standings question through the server
    Given the MCP server is running
    When I call the MCP tool "standings" with arguments "competition=Brasileirão, season=2019"
    Then the response should contain "Flamengo"
    And the response should contain "Champion"

  Scenario: Unknown teams produce a helpful answer, not a crash
    Given the MCP server is running
    When I call the MCP tool "search_matches" with arguments "team=Not A Real Team"
    Then the response should contain "Could not answer"

  Scenario: The dataset resource is exposed
    Given the MCP server is running
    Then the server should expose the datasets resource
