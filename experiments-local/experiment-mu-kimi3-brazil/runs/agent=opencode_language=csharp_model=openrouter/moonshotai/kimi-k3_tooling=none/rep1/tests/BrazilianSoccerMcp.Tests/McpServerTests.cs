using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Models;
using BrazilianSoccerMcp.Services;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Protocol-level tests for the MCP JSON-RPC server (handled in-process).
/// </summary>
public class McpServerTests
{
    private static McpServer BuildServer()
    {
        var matches = new List<MatchRecord>
        {
            new()
            {
                Date = new DateOnly(2021, 5, 30),
                Season = 2021,
                Competition = DataLoader.BrasileiraoSerieA,
                Source = "synthetic",
                Round = "Round 1",
                HomeTeam = "Palmeiras-SP",
                AwayTeam = "Flamengo-RJ",
                HomeTeamCanonical = "Palmeiras",
                AwayTeamCanonical = "Flamengo",
                HomeGoals = 2,
                AwayGoals = 1,
            },
        };
        var players = new List<PlayerRecord>
        {
            new() { Id = 1, Name = "Neymar Jr", Nationality = "Brazil", Club = "Paris Saint-Germain", Overall = 92, Position = "LW" },
        };
        var service = new SoccerDataService(matches, players);
        return new McpServer(new ToolRegistry(service), TextReader.Null, TextWriter.Null);
    }

    private static JsonObject Send(McpServer server, string json)
    {
        var response = server.HandleMessage(json);
        Assert.NotNull(response);
        return JsonNode.Parse(response)!.AsObject();
    }

    [Fact]
    public void Initialize_ReturnsProtocolVersionCapabilitiesAndServerInfo()
    {
        // Given a running server, when a client initializes
        var response = Send(BuildServer(),
            """{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}""");

        // Then the handshake advertises tools capability
        Assert.Equal(1, response["id"]!.GetValue<int>());
        var result = response["result"]!.AsObject();
        Assert.Equal(McpServer.ProtocolVersion, result["protocolVersion"]!.GetValue<string>());
        Assert.NotNull(result["capabilities"]!["tools"]);
        Assert.Equal("brazilian-soccer-mcp", result["serverInfo"]!["name"]!.GetValue<string>());
    }

    [Fact]
    public void ToolsList_ReturnsAllRegisteredToolsWithSchemas()
    {
        // Given a running server, when listing tools
        var response = Send(BuildServer(), """{"jsonrpc":"2.0","id":2,"method":"tools/list"}""");

        // Then every tool has name, description and input schema
        var tools = response["result"]!["tools"]!.AsArray();
        Assert.Equal(11, tools.Count);
        foreach (var tool in tools)
        {
            Assert.NotNull(tool!["name"]);
            Assert.NotNull(tool["description"]);
            Assert.Equal("object", tool["inputSchema"]!["type"]!.GetValue<string>());
        }
        Assert.Contains(tools, t => t!["name"]!.GetValue<string>() == "find_matches");
        Assert.Contains(tools, t => t!["name"]!.GetValue<string>() == "season_standings");
    }

    [Fact]
    public void ToolsCall_FindMatches_ReturnsTextContent()
    {
        // Given a running server, when calling find_matches
        var response = Send(BuildServer(),
            """{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Palmeiras"}}}""");

        // Then the result is MCP text content
        var result = response["result"]!.AsObject();
        Assert.False(result["isError"]!.GetValue<bool>());
        var text = result["content"]!.AsArray()[0]!["text"]!.GetValue<string>();
        Assert.Contains("Palmeiras 2-1 Flamengo", text);
        Assert.Contains("Brasileirão Série A", text);
    }

    [Fact]
    public void ToolsCall_UnknownTeam_ReturnsIsErrorContent()
    {
        // Given a running server, when the tool cannot resolve a team
        var response = Send(BuildServer(),
            """{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"find_matches","arguments":{"team":"Borussia Dortmund"}}}""");

        // Then the tool reports a domain error inside the result (not a protocol error)
        var result = response["result"]!.AsObject();
        Assert.True(result["isError"]!.GetValue<bool>());
        Assert.Contains("not found", result["content"]!.AsArray()[0]!["text"]!.GetValue<string>());
    }

    [Fact]
    public void ToolsCall_UnknownTool_ReturnsProtocolError()
    {
        // Given a running server, when calling a non-existent tool
        var response = Send(BuildServer(),
            """{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"nope","arguments":{}}}""");

        // Then a JSON-RPC invalid-params error is returned
        Assert.Equal(JsonRpc.InvalidParams, response["error"]!["code"]!.GetValue<int>());
    }

    [Fact]
    public void UnknownMethod_ReturnsMethodNotFound()
    {
        var response = Send(BuildServer(), """{"jsonrpc":"2.0","id":6,"method":"resources/list"}""");
        Assert.Equal(JsonRpc.MethodNotFound, response["error"]!["code"]!.GetValue<int>());
    }

    [Fact]
    public void InvalidJson_ReturnsParseError()
    {
        var response = Send(BuildServer(), "{not json");
        Assert.Equal(JsonRpc.ParseError, response["error"]!["code"]!.GetValue<int>());
    }

    [Fact]
    public void Notification_ProducesNoResponse()
    {
        // Given an initialized notification (no id), when handled
        var response = BuildServer().HandleMessage("""{"jsonrpc":"2.0","method":"notifications/initialized"}""");

        // Then there is nothing to send back
        Assert.Null(response);
    }

    [Fact]
    public void Ping_ReturnsEmptyResult()
    {
        var response = Send(BuildServer(), """{"jsonrpc":"2.0","id":7,"method":"ping"}""");
        Assert.NotNull(response["result"]);
        Assert.Null(response["error"]);
    }

    [Fact]
    public async Task RunAsync_ReadsNewlineDelimitedMessagesUntilEof()
    {
        // Given a server wired to in-memory streams
        var service = new SoccerDataService([], []);
        var input = new StringReader(
            "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}\n" +
            "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}\n");
        var output = new StringWriter();
        var server = new McpServer(new ToolRegistry(service), input, output);

        // When running the stdio loop
        var exitCode = await server.RunAsync();

        // Then both messages were answered, one JSON object per line, then EOF stopped the loop
        Assert.Equal(0, exitCode);
        var lines = output.ToString().Split('\n', StringSplitOptions.RemoveEmptyEntries);
        Assert.Equal(2, lines.Length);
        Assert.All(lines, l => Assert.StartsWith("{", l));
        Assert.Equal(1, JsonNode.Parse(lines[0])!["id"]!.GetValue<int>());
        Assert.Equal(2, JsonNode.Parse(lines[1])!["id"]!.GetValue<int>());
    }
}
