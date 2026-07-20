Feature: MCP Server Tools
  As an MCP client (LLM agent)
  I want to call the FastMCP tools and get JSON answers
  So that the server can be integrated into a larger agent workflow.

  Scenario: The server exposes the expected toolset
    Given the FastMCP server is built
    Then the server should advertise tools for matches, teams, players and competitions

  Scenario: Cross-file query combining team and player data
    Given the FastMCP server is built
    When the client calls team_info for "Flamengo"
    Then the response should include competitions the team played in
    And the response should include the count of FIFA players linked to the club

  Scenario: Normalizing through a tool call
    Given the FastMCP server is built
    When the client calls normalize_team_name with "Atletico-MG"
    Then the canonical name in the response should be "Atlético Mineiro"
