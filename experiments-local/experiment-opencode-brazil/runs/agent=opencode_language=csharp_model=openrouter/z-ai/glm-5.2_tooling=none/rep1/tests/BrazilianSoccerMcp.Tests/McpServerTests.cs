// Context block
// File: McpServerTests.cs
// Purpose: BDD/GWT tests for the stdio McpServer of the Brazilian Soccer MCP server,
// covering the MCP protocol behaviors required by TASK.md: initialize handshake, tools/list
// exposes the soccer tools, and tools/call returns text content for a known tool. The
// tests feed newline-delimited JSON-RPC lines through a StringWriter/StringReader pair so
// the server can be exercised end-to-end without spawning a process.
// Language: C# (.NET 10) + xUnit. Owner: Brazilian Soccer MCP benchmark implementation.

using System.Text.Json;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

[Collection("SoccerData")]
public class McpServerTests
{
    private readonly SoccerDataFixture _f;
    public McpServerTests(SoccerDataFixture fixture) => _f = fixture;

    // Feature: MCP Protocol

    // Scenario: initialize handshake
    //   Given the MCP server is running
    //   When I send an initialize request
    //   Then I should receive a response with protocolVersion and serverInfo
    [Fact]
    public void Initialize_returns_protocol_version_and_server_info()
    {
        var (output, _) = Run(
            """{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}""");

        var resp = Parse(output);
        Assert.Equal("2.0", resp.root.GetProperty("jsonrpc").GetString());
        Assert.Equal(1, resp.root.GetProperty("id").GetInt32());
        Assert.NotNull(resp.root.GetProperty("result").GetProperty("protocolVersion").GetString());
        Assert.Equal(McpServer.ServerName, resp.root.GetProperty("result").GetProperty("serverInfo").GetProperty("name").GetString());
    }

    // Scenario: tools/list exposes soccer tools
    //   Given the MCP server is running
    //   When I request tools/list
    //   Then the response should include the search_matches tool
    [Fact]
    public void Tools_list_includes_search_matches()
    {
        var (output, _) = Run(
            """{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}""");

        var resp = Parse(output);
        var tools = resp.root.GetProperty("result").GetProperty("tools");
        var names = tools.EnumerateArray().Select(t => t.GetProperty("name").GetString()).ToList();
        Assert.Contains("search_matches", names);
        Assert.Contains("head_to_head", names);
        Assert.Contains("search_players", names);
        Assert.Contains("get_standings", names);
    }

    // Scenario: tools/call returns text content for head_to_head
    //   Given the MCP server is running and data is loaded
    //   When I call head_to_head with Flamengo and Fluminense
    //   Then the response should contain a text block mentioning both teams
    [Fact]
    public void Tools_call_head_to_head_returns_text()
    {
        var (output, _) = Run(
            """{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}}""");

        var resp = Parse(output);
        var content = resp.root.GetProperty("result").GetProperty("content");
        var text = content[0].GetProperty("text").GetString()!;
        Assert.Contains("Flamengo", text);
        Assert.Contains("Fluminense", text);
        Assert.Contains("wins", text);
    }

    // Scenario: tools/call for unknown tool returns an error result
    //   Given the MCP server is running
    //   When I call a non-existent tool
    //   Then the response should have isError true
    [Fact]
    public void Tools_call_unknown_tool_returns_error()
    {
        var (output, _) = Run(
            """{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"does_not_exist","arguments":{}}}""");

        var resp = Parse(output);
        Assert.True(resp.root.GetProperty("result").GetProperty("isError").GetBoolean());
    }

    // Scenario: notifications/initialized produces no response
    //   Given the MCP server is running
    //   When I send a notifications/initialized notification
    //   Then no response should be written
    [Fact]
    public void Initialized_notification_produces_no_response()
    {
        var (output, _) = Run(
            """{"jsonrpc":"2.0","method":"notifications/initialized"}""");

        Assert.Equal(string.Empty, output.Trim());
    }

    private (string output, string log) Run(params string[] lines)
    {
        var input = new StringReader(string.Join('\n', lines));
        var output = new StringWriter();
        var log = new StringWriter();
        var tools = new ToolRegistry(_f.Store);
        var server = new McpServer(tools, input, output, log);
        server.Run();
        return (output.ToString(), log.ToString());
    }

    private static (JsonDocument doc, JsonElement root) Parse(string json)
    {
        var trimmed = json.Trim();
        Assert.False(string.IsNullOrEmpty(trimmed), "expected a JSON-RPC response");
        var doc = JsonDocument.Parse(trimmed.Split('\n', StringSplitOptions.RemoveEmptyEntries).Last());
        return (doc, doc.RootElement);
    }
}
