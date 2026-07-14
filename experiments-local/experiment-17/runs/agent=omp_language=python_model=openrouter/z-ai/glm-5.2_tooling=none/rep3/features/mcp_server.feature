Feature: MCP Server Tools
  The Brazilian soccer data should be exposed as MCP tools that an LLM
  can call to produce text answers.

  Scenario: All expected tools are registered
    Given the MCP server is loaded
    Then the server should register at least 14 tools
    And the server should register a tool named "search_matches"
    And the server should register a tool named "head_to_head"
    And the server should register a tool named "team_stats"
    And the server should register a tool named "competition_standings"
    And the server should register a tool named "search_players"
    And the server should register a tool named "top_players"
    And the server should register a tool named "biggest_wins"
    And the server should register a tool named "average_goals"
    And the server should register a tool named "best_record"
    And the server should register a tool named "derbies"
    And the server should register a tool named "catalog"

  Scenario: Calling the standings tool returns text mentioning the champion
    Given the MCP server is loaded
    When I call the "competition_standings" tool with competition "Brasileirão" and season 2019
    Then the response text should mention "Flamengo"

  Scenario: Calling the catalog tool returns text
    Given the MCP server is loaded
    When I call the "catalog" tool
    Then the response text should mention "Brasileirão"
