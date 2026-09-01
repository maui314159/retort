Feature: MCP Server Surface
  The FastMCP server exposing the knowledge base over stdio JSON-RPC.

  Scenario: Tool registry
    Given the server is built
    When the tool list is read
    Then all 18 documented tools are registered with descriptions

  Scenario: JSON-serializable responses
    Given a representative call for every tool
    When the response is serialized
    Then it round-trips through JSON for the MCP transport

  Scenario: Stdio round trip
    Given the server running as a subprocess
    When the client sends initialize, tools/list and tools/call
    Then valid JSON-RPC responses return, including the 2019 champion
