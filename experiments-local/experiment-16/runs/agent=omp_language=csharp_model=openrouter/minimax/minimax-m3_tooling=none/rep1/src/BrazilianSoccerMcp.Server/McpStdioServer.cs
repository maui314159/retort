// =============================================================================
// Brazilian Soccer MCP Server
// File: McpStdioServer.cs
// Purpose: Minimal MCP server speaking JSON-RPC 2.0 over stdio.
// Context: Implements the subset of MCP that the host needs: initialize,
//          tools/list, tools/call, and the notifications/initialized
//          handshake. The wire format is one JSON object per line on
//          stdin/stdout.
// =============================================================================

using System.Text.Json;
using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Core;

namespace BrazilianSoccerMcp.Server;

/// <summary>
/// Stdio JSON-RPC 2.0 MCP server. Construct with the query engine you want
/// to expose, then call <see cref="RunAsync"/>.
/// </summary>
public sealed class McpStdioServer
{
    private readonly QueryEngine _engine;
    private readonly ToolRegistry _tools;
    private readonly JsonSerializerOptions _json = new()
    {
        WriteIndented = false,
    };

    public McpStdioServer(QueryEngine engine)
    {
        _engine = engine;
        _tools = ToolRegistry.Build(engine);
    }

    public async Task RunAsync(CancellationToken cancellationToken)
    {
        // Use a buffered stdin reader so the loop is async-friendly.
        using var stdin = Console.OpenStandardInput();
        using var stdout = Console.OpenStandardOutput();

        // We do line-by-line reads. StreamReader buffers internally.
        using var reader = new StreamReader(stdin);
        await using var writer = new StreamWriter(stdout) { AutoFlush = true };

        while (!cancellationToken.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(cancellationToken);
            if (line is null) break;                          // EOF: parent died
            if (string.IsNullOrWhiteSpace(line)) continue;    // skip blank lines

            JsonNode? response;
            try
            {
                var request = JsonNode.Parse(line);
                response = HandleRequest(request);
            }
            catch (Exception ex)
            {
                response = JsonSerializer.SerializeToNode(new
                {
                    jsonrpc = "2.0",
                    id = (object?)null,
                    error = new
                    {
                        code = -32700,
                        message = "Parse error",
                        data = ex.Message,
                    },
                }, _json);
            }

            if (response is not null)
            {
                await writer.WriteLineAsync(response.ToJsonString(_json));
            }
        }
    }

    private JsonNode? HandleRequest(JsonNode? request)
    {
        if (request is not JsonObject obj)
            return MakeError(null, -32600, "Invalid Request");

        var id = obj["id"]?.DeepClone();
        var method = obj["method"]?.GetValue<string>();
        var parameters = obj["params"] as JsonObject ?? new JsonObject();

        // Notifications have no id -- we acknowledge by returning null (no
        // response on the wire, per JSON-RPC 2.0).
        if (id is null && method is not null && !IsRequest(obj))
            return null;

        try
        {
            return method switch
            {
                "initialize" => HandleInitialize(id),
                "ping"       => MakeResult(id, new { pong = true }),
                "tools/list" => HandleToolsList(id),
                "tools/call" => HandleToolsCall(id, parameters),
                _            => MakeError(id, -32601, $"Method not found: {method}"),
            };
        }
        catch (Exception ex)
        {
            return MakeError(id, -32603, "Internal error: " + ex.Message);
        }
    }

    private static bool IsRequest(JsonObject obj) => obj["id"] is not null;

    private JsonNode HandleInitialize(JsonNode? id)
    {
        return MakeResult(id, new
        {
            protocolVersion = "2024-11-05",
            serverInfo = new
            {
                name = "brazilian-soccer-mcp",
                version = "1.0.0",
            },
            capabilities = new
            {
                tools = new { },
            },
        });
    }

    private JsonNode HandleToolsList(JsonNode? id)
    {
        var defs = _tools.List().Select(t => new
        {
            name = t.Name,
            description = t.Description,
            inputSchema = t.InputSchema,
        }).ToList();
        return MakeResult(id, new { tools = defs });
    }

    private JsonNode HandleToolsCall(JsonNode? id, JsonObject parameters)
    {
        var name = parameters["name"]?.GetValue<string>()
            ?? throw new InvalidOperationException("Missing 'name' in tools/call params");
        var args = parameters["arguments"] as JsonObject ?? new JsonObject();

        var tool = _tools.Get(name)
            ?? throw new InvalidOperationException($"Unknown tool: {name}");

        var resultText = tool.Invoke(args, _json);
        // MCP tool results are wrapped in a content array of "text" items.
        return MakeResult(id, new
        {
            content = new[]
            {
                new { type = "text", text = resultText },
            },
            isError = false,
        });
    }

    // ---------------------------------------------------------------------
    // JSON-RPC helpers
    // ---------------------------------------------------------------------

    private JsonNode MakeResult(JsonNode? id, object result)
    {
        var node = JsonSerializer.SerializeToNode(result, _json) as JsonObject
            ?? new JsonObject();
        return new JsonObject
        {
            ["jsonrpc"] = "2.0",
            ["id"] = id?.DeepClone(),
            ["result"] = node,
        };
    }

    private JsonNode MakeError(JsonNode? id, int code, string message, object? data = null)
    {
        return new JsonObject
        {
            ["jsonrpc"] = "2.0",
            ["id"] = id?.DeepClone(),
            ["error"] = new JsonObject
            {
                ["code"] = code,
                ["message"] = message,
                ["data"] = data is null ? null : JsonSerializer.SerializeToNode(data, _json),
            },
        };
    }
}
