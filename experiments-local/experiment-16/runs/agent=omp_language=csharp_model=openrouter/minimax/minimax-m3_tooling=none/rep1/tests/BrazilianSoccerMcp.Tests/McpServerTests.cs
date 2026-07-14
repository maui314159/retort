// =============================================================================
// Brazilian Soccer MCP Server
// File: McpServerTests.cs
// Purpose: End-to-end JSON-RPC tests against the MCP stdio server.
// Context: Each test spawns the server as a child process, feeds it a
//          JSON-RPC request on stdin, and asserts the response shape.
//          This exercises the full transport the LLM host will use.
// =============================================================================

using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests;

public class McpServerTests
{
    // AppContext.BaseDirectory is .../tests/BrazilianSoccerMcp.Tests/bin/Debug/net10.0/
    // 5 levels up lands on the repo root.
    private static string RepoRoot =>
        Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));

    private static string ProjectPath =>
        Path.Combine(RepoRoot, "src", "BrazilianSoccerMcp.Server", "BrazilianSoccerMcp.Server.csproj");

    private static async Task<JsonNode> RoundTripAsync(string request)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "dotnet",
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            WorkingDirectory = RepoRoot,
        };
        psi.ArgumentList.Add("run");
        psi.ArgumentList.Add("--no-build");
        psi.ArgumentList.Add("--project");
        psi.ArgumentList.Add(ProjectPath);
        psi.ArgumentList.Add(RepoRoot);

        using var p = Process.Start(psi)!;
        var stderrTask = Task.Run(async () => await p.StandardError.ReadToEndAsync());
        await p.StandardInput.WriteLineAsync(request);
        p.StandardInput.Close();

        var line = await p.StandardOutput.ReadLineAsync();
        var stderr = await stderrTask;
        await p.WaitForExitAsync();

        if (line is null)
        {
            throw new InvalidOperationException(
                $"No response from server. Stderr:\n{stderr}");
        }
        try
        {
            return JsonNode.Parse(line)!;
        }
        catch (Exception ex)
        {
            throw new InvalidOperationException(
                $"Bad JSON from server: {ex.Message}\nLine: {line}\nStderr:\n{stderr}");
        }
    }

    [Fact]
    public async Task Given_initialize_request_When_sending_Then_server_returns_capabilities()
    {
        var resp = await RoundTripAsync("""{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}""");
        resp["jsonrpc"]!.GetValue<string>().Should().Be("2.0");
        resp["id"]!.GetValue<int>().Should().Be(1);
        resp["result"]!["serverInfo"]!["name"]!.GetValue<string>().Should().Be("brazilian-soccer-mcp");
        resp["result"]!["capabilities"]!["tools"].Should().NotBeNull();
    }

    [Fact]
    public async Task Given_tools_list_request_When_sending_Then_returns_at_least_5_tools()
    {
        var resp = await RoundTripAsync("""{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}""");
        var tools = resp["result"]!["tools"]!.AsArray();
        tools.Count.Should().BeGreaterThanOrEqualTo(5);
    }

    [Fact]
    public async Task Given_find_matches_by_team_When_calling_tool_Then_returns_text_content()
    {
        var req = "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"find_matches_by_team\",\"arguments\":{\"team\":\"Flamengo\",\"limit\":3}}}";
        var resp = await RoundTripAsync(req);
        if (resp["result"] is null)
            throw new InvalidOperationException($"Server returned no result. Response: {resp.ToJsonString()}");
        var content = resp["result"]!["content"]!.AsArray();
        content.Should().HaveCount(1);
        content[0]!["type"]!.GetValue<string>().Should().Be("text");
        var text = content[0]!["text"]!.GetValue<string>();
        text.Should().Contain("Flamengo");
    }

    [Fact]
    public async Task Given_head_to_head_When_calling_tool_Then_returns_counts_and_match_list()
    {
        var req = "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"find_head_to_head\",\"arguments\":{\"team_a\":\"Flamengo\",\"team_b\":\"Fluminense\"}}}";
        var resp = await RoundTripAsync(req);
        if (resp["result"] is null)
            throw new InvalidOperationException($"Server returned no result. Response: {resp.ToJsonString()}");
        var text = resp["result"]!["content"]![0]!["text"]!.GetValue<string>();
        text.Should().Contain("H2H");
        text.Should().Contain("Flamengo");
        text.Should().Contain("Fluminense");
    }

    [Fact]
    public async Task Given_search_players_When_calling_tool_Then_returns_ranked_players()
    {
        var req = "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"search_players\",\"arguments\":{\"name\":\"Neymar\"}}}";
        var resp = await RoundTripAsync(req);
        if (resp["result"] is null)
            throw new InvalidOperationException($"Server returned no result. Response: {resp.ToJsonString()}");
        var text = resp["result"]!["content"]![0]!["text"]!.GetValue<string>();
        text.Should().Contain("Neymar");
        text.Should().Contain("OVR");
    }
    [Fact]
    public async Task Given_get_team_record_When_calling_tool_Then_returns_W_D_L_summary()
    {
        var req = "{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":{\"name\":\"get_team_record\",\"arguments\":{\"team\":\"Corinthians\",\"season\":2022,\"competition\":\"Brasileirao\",\"home_or_away\":\"Home\"}}}";
        var resp = await RoundTripAsync(req);
        if (resp["result"] is null)
            throw new InvalidOperationException($"Server returned no result. Response: {resp.ToJsonString()}");
        var text = resp["result"]!["content"]![0]!["text"]!.GetValue<string>();
        text.Should().Contain("Corinthians");
        text.Should().Contain("played");
        text.Should().Contain("win rate");
    }
    [Fact]
    public async Task Given_get_standings_When_calling_tool_Then_returns_ranked_list()
    {
        var req = "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"get_standings\",\"arguments\":{\"season\":2019,\"competition\":\"Brasileirao\"}}}";
        var resp = await RoundTripAsync(req);
        if (resp["result"] is null)
            throw new InvalidOperationException($"Server returned no result. Response: {resp.ToJsonString()}");
        var text = resp["result"]!["content"]![0]!["text"]!.GetValue<string>();
        text.Should().Contain("standings");
        text.Should().Contain("Flamengo");  // 2019 champion
    }

    [Fact]
    public async Task Given_unknown_method_When_sending_Then_returns_method_not_found_error()
    {
        var req = """{"jsonrpc":"2.0","id":99,"method":"unknown/method","params":{}}""";
        var resp = await RoundTripAsync(req);
        resp["error"]!["code"]!.GetValue<int>().Should().Be(-32601);
    }
}
