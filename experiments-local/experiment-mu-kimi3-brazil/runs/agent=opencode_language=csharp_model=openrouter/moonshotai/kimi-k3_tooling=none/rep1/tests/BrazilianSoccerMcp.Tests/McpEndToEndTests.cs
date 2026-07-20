using System.Diagnostics;
using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// End-to-end test: spawns the real MCP server process and speaks JSON-RPC
/// over its stdin/stdout, exactly like an MCP client would.
/// </summary>
public class McpEndToEndTests : IClassFixture<McpEndToEndTests.ServerProcessFixture>
{
    /// <summary>Builds the server project once and locates the resulting dll.</summary>
    public sealed class ServerProcessFixture : IDisposable
    {
        public string RepoRoot { get; }
        public string ServerDll { get; }

        public ServerProcessFixture()
        {
            // Tests run from tests/BrazilianSoccerMcp.Tests/bin/Debug/net10.0 -> repo root is 5 levels up
            RepoRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
            Assert.True(File.Exists(Path.Combine(RepoRoot, "TASK.md")), $"repo root not found at {RepoRoot}");

            var build = Process.Start(new ProcessStartInfo
            {
                FileName = "dotnet",
                Arguments = "build src/BrazilianSoccerMcp -c Debug -v q --nologo",
                WorkingDirectory = RepoRoot,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            })!;
            build.WaitForExit(TimeSpan.FromMinutes(3));
            Assert.True(build.ExitCode == 0, "server build failed: " + build.StandardError.ReadToEnd());

            ServerDll = Path.Combine(RepoRoot, "src", "BrazilianSoccerMcp", "bin", "Debug", "net10.0", "BrazilianSoccerMcp.dll");
            Assert.True(File.Exists(ServerDll), $"server dll not found at {ServerDll}");
        }

        public void Dispose() { }
    }

    private readonly ServerProcessFixture _fx;

    public McpEndToEndTests(ServerProcessFixture fx) => _fx = fx;

    [Fact]
    public async Task GivenServerProcess_WhenClientSpeaksMcp_ThenToolsAnswerOverStdio()
    {
        // Given the server process running with the repo as working directory
        using var process = new Process();
        process.StartInfo = new ProcessStartInfo
        {
            FileName = "dotnet",
            Arguments = $"\"{_fx.ServerDll}\"",
            WorkingDirectory = _fx.RepoRoot,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        process.Start();

        var responses = new List<string>();
        var readTask = Task.Run(async () =>
        {
            while (await process.StandardOutput.ReadLineAsync() is { } line)
            {
                if (!string.IsNullOrWhiteSpace(line))
                {
                    lock (responses)
                        responses.Add(line);
                }
            }
        });

        async Task<JsonObject> Call(int id, string payload)
        {
            await process.StandardInput.WriteLineAsync(payload);
            await process.StandardInput.FlushAsync();
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(30);
            while (DateTime.UtcNow < deadline)
            {
                lock (responses)
                {
                    var found = responses.FirstOrDefault(r =>
                        JsonNode.Parse(r)?["id"]?.GetValue<int>() == id);
                    if (found is not null)
                        return JsonNode.Parse(found)!.AsObject();
                }
                await Task.Delay(25);
            }
            throw new TimeoutException($"No response for id {id}. stderr: {process.StandardError.ReadToEnd()}");
        }

        // When initializing the MCP handshake
        var init = await Call(1,
            """{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"e2e","version":"1"}}}""");
        Assert.Equal("brazilian-soccer-mcp", init["result"]!["serverInfo"]!["name"]!.GetValue<string>());

        // And listing tools
        var list = await Call(2, """{"jsonrpc":"2.0","id":2,"method":"tools/list"}""");
        Assert.Equal(11, list["result"]!["tools"]!.AsArray().Count);

        // And asking for the 2019 Brasileirão winner via season_standings
        var standings = await Call(3,
            """{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"season_standings","arguments":{"competition":"Brasileirão","season":2019}}}""");
        var text = standings["result"]!["content"]!.AsArray()[0]!["text"]!.GetValue<string>();
        Assert.Contains("1. Flamengo - 90 pts", text);
        Assert.Contains("Champion", text);

        // And asking a player question via top_players
        var players = await Call(4,
            """{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"top_players","arguments":{"nationality":"Brazil","limit":3}}}""");
        var playersText = players["result"]!["content"]!.AsArray()[0]!["text"]!.GetValue<string>();
        Assert.Contains("Neymar Jr", playersText);

        // Then closing stdin (EOF) shuts the server down cleanly
        process.StandardInput.Close();
        Assert.True(process.WaitForExit(TimeSpan.FromSeconds(30)), "server did not exit after stdin EOF");
        Assert.Equal(0, process.ExitCode);
        await readTask;
    }
}
