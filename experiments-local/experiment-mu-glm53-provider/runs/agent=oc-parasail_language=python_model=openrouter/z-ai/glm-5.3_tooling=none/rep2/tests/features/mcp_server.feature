Feature: MCP Server
  As an MCP client
  I want to list the server tools and call them over the protocol
  So that an LLM can answer natural-language soccer questions through the tools

  Scenario: List available tools
    Given the MCP server is running
    When I list the available tools
    Then at least 19 tools should be available
    And tools for matches, players, standings, statistics and the graph should be present

  Scenario: Call the standings tool over MCP
    Given the MCP server is running
    When I call the "standings" tool with competition "Série A" and season 2019
    Then the tool should return a JSON document with a summary
    And the summary should name Flamengo as champion

  Scenario: Call the player search tool over MCP
    Given the MCP server is running
    When I call the "search_players" tool with name "Neymar"
    Then the tool should return Neymar Jr with overall rating 92

  Scenario: Tool errors are reported gracefully
    Given the MCP server is running
    When I call the "standings" tool with competition "Libertadores" and season 2019
    Then the tool should return an error message rather than crashing

  Scenario: Unknown team names suggest alternatives
    Given the MCP server is running
    When I call the "team_stats" tool with team "Flamengu"
    Then the response should suggest Flamengo as a candidate
