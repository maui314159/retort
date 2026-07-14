using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// BDD-style tests for the MCP JSON-RPC protocol layer. We drive the server
/// one request at a time via <see cref="McpServer.HandleLine"/> so we can
/// assert on the exact wire format.
/// </summary>
[Collection("DataCollection")]
public class McpProtocolBddTests
{
    private readonly DataFixture _fixture;

    public McpProtocolBddTests(DataFixture fixture) => _fixture = fixture;

    private static McpServer BuildServer(DataFixture f)
    {
        var repo = f.Repository;
        var registry = new ToolRegistry(
            new MatchService(repo), new TeamService(repo),
            new PlayerService(repo), new CompetitionService(repo));
        return new McpServer(registry, new StringReader(""), new StringWriter());
    }

    private static JsonObject Send(McpServer server, JsonObject request)
        => server.HandleLine(request.ToJsonString())!;

    [Fact]
    public void Initialize_returns_server_info_and_protocol_version()
    {
        // Given an MCP server backed by the loaded data
        var server = BuildServer(_fixture);

        // When the client sends an initialize request
        var resp = Send(server, new JsonObject
        {
            ["jsonrpc"] = "2.0",
            ["id"] = 1,
            ["method"] = "initialize",
            ["params"] = new JsonObject(),
        });

        // Then the response contains protocolVersion and serverInfo
        Assert.Equal("2.0", resp["jsonrpc"]!.ToString());
        Assert.NotNull(resp["result"]!["protocolVersion"]);
        Assert.Equal("brazilian-soccer-mcp", resp["result"]!["serverInfo"]!["name"]!.ToString());
    }

    [Fact]
    public void Tools_list_returns_the_expected_catalogue()
    {
        var server = BuildServer(_fixture);
        var resp = Send(server, new JsonObject
        {
            ["jsonrpc"] = "2.0",
            ["id"] = 2,
            ["method"] = "tools/list",
            ["params"] = new JsonObject(),
        });

        var tools = resp["result"]!["tools"]!.AsArray();
        Assert.True(tools.Count >= 9, "expected at least nine tools");
        var names = tools.Select(t => t!["name"]!.ToString()).ToHashSet();
        Assert.Contains("search_matches", names);
        Assert.Contains("head_to_head", names);
        Assert.Contains("team_stats", names);
        Assert.Contains("search_players", names);
        Assert.Contains("standings", names);
    }

    [Fact]
    public void Tools_call_search_matches_returns_text_content()
    {
        var server = BuildServer(_fixture);
        var resp = Send(server, new JsonObject
        {
            ["jsonrpc"] = "2.0",
            ["id"] = 3,
            ["method"] = "tools/call",
            ["params"] = new JsonObject
            {
                ["name"] = "search_matches",
                ["arguments"] = new JsonObject
                {
                    ["team"] = "Flamengo",
                    ["opponent"] = "Fluminense",
                },
            },
        });

        Assert.Null(resp["error"]);
        var content = resp["result"]!["content"]!.AsArray();
        Assert.Single(content);
        Assert.Equal("text", content[0]!["type"]!.ToString());
        var text = content[0]!["text"]!.ToString();
        Assert.Contains("Flamengo", text);
    }

    [Fact]
    public void Tools_call_unknown_tool_returns_method_error()
    {
        var server = BuildServer(_fixture);
        var resp = Send(server, new JsonObject
        {
            ["jsonrpc"] = "2.0",
            ["id"] = 4,
            ["method"] = "tools/call",
            ["params"] = new JsonObject
            {
                ["name"] = "does_not_exist",
                ["arguments"] = new JsonObject(),
            },
        });

        Assert.NotNull(resp["error"]);
    }

    [Fact]
    public void Notifications_initialized_produces_no_response()
    {
        var server = BuildServer(_fixture);
        var resp = server.HandleLine("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}");
        Assert.Null(resp);
    }
}
