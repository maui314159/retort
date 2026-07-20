using System.Text.Json;
using BrazilianSoccerMcp.Graph;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Feature: MCP protocol compliance
/// The server speaks JSON-RPC 2.0 over stdio and implements the MCP handshake,
/// tool listing and tool invocation contract.
/// </summary>
public class McpProtocolFeatureTests
{
    private readonly McpServer _server = new(new ToolRegistry(TestData.Graph));

    private static JsonDocument Send(McpServer server, string message)
    {
        var response = server.HandleMessage(message);
        Assert.NotNull(response);
        return JsonDocument.Parse(response!);
    }

    [Fact]
    public void Given_ServerRunning_When_ClientInitializes_Then_ServerInfoAndToolCapabilitiesAreReturned()
    {
        // Given / When
        using var doc = Send(_server,
            """{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}""");

        // Then
        var result = doc.RootElement.GetProperty("result");
        Assert.Equal("2024-11-05", result.GetProperty("protocolVersion").GetString());
        Assert.Equal("brazilian-soccer-mcp", result.GetProperty("serverInfo").GetProperty("name").GetString());
        Assert.True(result.GetProperty("capabilities").TryGetProperty("tools", out _));
    }

    [Fact]
    public void Given_ServerRunning_When_NotificationArrives_Then_NoResponseIsProduced()
    {
        // Given / When / Then (notifications must never be answered)
        Assert.Null(_server.HandleMessage("""{"jsonrpc":"2.0","method":"notifications/initialized"}"""));
        Assert.Null(_server.HandleMessage("""{"jsonrpc":"2.0","method":"notifications/cancelled","params":{}}"""));
    }

    [Fact]
    public void Given_ServerRunning_When_ToolsListed_Then_AllThirteenToolsHaveSchemas()
    {
        // Given / When
        using var doc = Send(_server, """{"jsonrpc":"2.0","id":2,"method":"tools/list"}""");

        // Then
        var tools = doc.RootElement.GetProperty("result").GetProperty("tools");
        Assert.Equal(13, tools.GetArrayLength());
        foreach (var tool in tools.EnumerateArray())
        {
            Assert.False(string.IsNullOrWhiteSpace(tool.GetProperty("name").GetString()));
            Assert.False(string.IsNullOrWhiteSpace(tool.GetProperty("description").GetString()));
            Assert.Equal("object", tool.GetProperty("inputSchema").GetProperty("type").GetString());
        }
        Assert.Contains(tools.EnumerateArray(), t => t.GetProperty("name").GetString() == "find_matches");
        Assert.Contains(tools.EnumerateArray(), t => t.GetProperty("name").GetString() == "head_to_head");
        Assert.Contains(tools.EnumerateArray(), t => t.GetProperty("name").GetString() == "search_players");
    }

    [Fact]
    public void Given_ServerRunning_When_CallingFindMatches_Then_TextContentIsReturned()
    {
        // Given / When
        using var doc = Send(_server,
            """{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Flamengo","opponent":"Fluminense","limit":2}}}""");

        // Then
        var result = doc.RootElement.GetProperty("result");
        Assert.False(result.GetProperty("isError").GetBoolean());
        var text = result.GetProperty("content")[0].GetProperty("text").GetString();
        Assert.Contains("Flamengo", text);
        Assert.Contains("Fluminense", text);
        Assert.Contains("showing 2 of", text);
    }

    [Fact]
    public void Given_ServerRunning_When_CallingUnknownTool_Then_IsErrorResultExplains()
    {
        // Given / When
        using var doc = Send(_server,
            """{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"fly_to_the_moon","arguments":{}}}""");

        // Then: tool errors are reported as isError results, not protocol errors
        var result = doc.RootElement.GetProperty("result");
        Assert.True(result.GetProperty("isError").GetBoolean());
        Assert.Contains("Unknown tool", result.GetProperty("content")[0].GetProperty("text").GetString());
    }

    [Fact]
    public void Given_ServerRunning_When_RequiredArgumentMissing_Then_IsErrorResult()
    {
        // Given / When
        using var doc = Send(_server,
            """{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team1":"Palmeiras"}}}""");

        // Then
        var result = doc.RootElement.GetProperty("result");
        Assert.True(result.GetProperty("isError").GetBoolean());
        Assert.Contains("team2", result.GetProperty("content")[0].GetProperty("text").GetString());
    }

    [Fact]
    public void Given_ServerRunning_When_MethodUnknown_Then_MethodNotFoundError()
    {
        // Given / When
        using var doc = Send(_server, """{"jsonrpc":"2.0","id":6,"method":"quantum/entangle"}""");

        // Then
        Assert.Equal(-32601, doc.RootElement.GetProperty("error").GetProperty("code").GetInt32());
    }

    [Fact]
    public void Given_ServerRunning_When_MessageIsNotJson_Then_ParseError()
    {
        // Given / When
        using var doc = Send(_server, "this is not json");

        // Then
        Assert.Equal(-32700, doc.RootElement.GetProperty("error").GetProperty("code").GetInt32());
    }

    [Fact]
    public void Given_ServerRunning_When_Ping_Then_EmptyResult()
    {
        // Given / When
        using var doc = Send(_server, """{"jsonrpc":"2.0","id":7,"method":"ping"}""");

        // Then
        Assert.True(doc.RootElement.TryGetProperty("result", out _));
    }

    [Fact]
    public async Task Given_ServerRunning_When_DrivingStdioLoop_Then_EachLineGetsOneResponse()
    {
        // Given
        var server = new McpServer(new ToolRegistry(TestData.Graph));
        var input = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(
            "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{}}\n"
            + "{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n"
            + "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}\n"));
        var output = new MemoryStream();

        // When
        await server.RunAsync(input, output);

        // Then: exactly two responses (the notification is skipped), one per line
        output.Position = 0;
        var text = new StreamReader(output).ReadToEnd();
        var lines = text.Split('\n', StringSplitOptions.RemoveEmptyEntries);
        Assert.Equal(2, lines.Length);
        Assert.All(lines, l => Assert.Contains("\"jsonrpc\":\"2.0\"", l));
    }
}
