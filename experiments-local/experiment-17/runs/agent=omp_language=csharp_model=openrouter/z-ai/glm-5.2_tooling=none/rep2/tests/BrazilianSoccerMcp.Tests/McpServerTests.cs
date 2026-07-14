using BrazilianSoccerMcp.Tests.Infrastructure;
using System.Text.Json;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: MCP Protocol
/// BDD scenarios verifying the JSON-RPC server responds correctly to
/// initialize, tools/list, and tools/call.
/// </summary>
[Collection("SoccerData")]
public class McpServerTests
{
    private readonly DataFixture _f;
    public McpServerTests(DataFixture f) => _f = f;

    private McpServer NewServer() => new(new SoccerTools(_f.Loader));

    // Scenario: initialize returns server info and tools capability
    [Fact]
    public void Initialize_returns_protocol_version_and_capabilities()
    {
        var server = NewServer();
        var req = """{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}""";
        var resp = server.HandleMessage(req);
        Assert.NotNull(resp);

        using var doc = JsonDocument.Parse(resp!);
        var root = doc.RootElement;
        Assert.Equal("2.0", root.GetProperty("jsonrpc").GetString());
        Assert.Equal(1, root.GetProperty("id").GetInt32());
        var result = root.GetProperty("result");
        Assert.False(string.IsNullOrEmpty(result.GetProperty("protocolVersion").GetString()));
        Assert.True(result.GetProperty("capabilities").TryGetProperty("tools", out _));
        Assert.Equal("brazilian-soccer-mcp", result.GetProperty("serverInfo").GetProperty("name").GetString());
    }

    // Scenario: tools/list returns all tools with schemas
    [Fact]
    public void ToolsList_returns_tools_with_input_schemas()
    {
        var server = NewServer();
        var req = """{"jsonrpc":"2.0","id":2,"method":"tools/list"}""";
        var resp = server.HandleMessage(req);

        using var doc = JsonDocument.Parse(resp!);
        var tools = doc.RootElement.GetProperty("result").GetProperty("tools");
        Assert.True(tools.GetArrayLength() >= 10);
        foreach (var t in tools.EnumerateArray())
        {
            Assert.False(string.IsNullOrEmpty(t.GetProperty("name").GetString()));
            Assert.False(string.IsNullOrEmpty(t.GetProperty("description").GetString()));
            Assert.True(t.TryGetProperty("inputSchema", out _));
        }
    }

    // Scenario: tools/call search_matches returns text content
    [Fact]
    public void CallTool_search_matches_returns_text_content()
    {
        var server = NewServer();
        var req = """
            {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","limit":3}}}
            """;
        var resp = server.HandleMessage(req);

        using var doc = JsonDocument.Parse(resp!);
        var result = doc.RootElement.GetProperty("result");
        Assert.False(result.GetProperty("isError").GetBoolean());
        var content = result.GetProperty("content");
        Assert.Equal(1, content.GetArrayLength());
        Assert.Equal("text", content[0].GetProperty("type").GetString());
        var text = content[0].GetProperty("text").GetString();
        Assert.False(string.IsNullOrEmpty(text));
    }

    // Scenario: tools/call head_to_head returns both teams
    [Fact]
    public void CallTool_head_to_head_returns_comparison()
    {
        var server = NewServer();
        var req = """
            {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}}
            """;
        var resp = server.HandleMessage(req);

        using var doc = JsonDocument.Parse(resp!);
        var text = doc.RootElement.GetProperty("result").GetProperty("content")[0].GetProperty("text").GetString();
        Assert.Contains("Flamengo", text);
        Assert.Contains("Fluminense", text);
        Assert.Contains("head-to-head", text);
    }

    // Scenario: tools/call standings returns champion
    [Fact]
    public void CallTool_standings_returns_table()
    {
        var server = NewServer();
        var req = """
            {"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão","season":2019}}}
            """;
        var resp = server.HandleMessage(req);

        using var doc = JsonDocument.Parse(resp!);
        var text = doc.RootElement.GetProperty("result").GetProperty("content")[0].GetProperty("text").GetString();
        Assert.Contains("Standings", text);
        Assert.Contains("Champion", text);
    }

    // Scenario: unknown tool returns an error
    [Fact]
    public void CallTool_unknown_returns_error()
    {
        var server = NewServer();
        var req = """{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"nonexistent","arguments":{}}}""";
        var resp = server.HandleMessage(req);

        using var doc = JsonDocument.Parse(resp!);
        Assert.True(doc.RootElement.TryGetProperty("error", out var err));
        Assert.Equal(-32602, err.GetProperty("code").GetInt32());
    }

    // Scenario: notifications (no id) get no response
    [Fact]
    public void Notification_returns_null()
    {
        var server = NewServer();
        var req = """{"jsonrpc":"2.0","method":"initialized"}""";
        Assert.Null(server.HandleMessage(req));
    }

    // Scenario: at least 20 sample questions can be answered (tool coverage)
    [Fact]
    public void Tool_set_covers_required_query_categories()
    {
        var server = NewServer();
        var req = """{"jsonrpc":"2.0","id":7,"method":"tools/list"}""";
        var resp = server.HandleMessage(req);
        using var doc = JsonDocument.Parse(resp!);
        var names = doc.RootElement.GetProperty("result").GetProperty("tools")
            .EnumerateArray().Select(t => t.GetProperty("name").GetString()!).ToHashSet();

        // Match, team, player, competition, and statistics tools must all be present.
        Assert.Contains("search_matches", names);
        Assert.Contains("head_to_head", names);
        Assert.Contains("team_stats", names);
        Assert.Contains("search_players", names);
        Assert.Contains("top_players", names);
        Assert.Contains("standings", names);
        Assert.Contains("champion", names);
        Assert.Contains("average_goals", names);
        Assert.Contains("biggest_wins", names);
        Assert.True(names.Count >= 17, $"expected >=17 tools, got {names.Count}");
    }
}