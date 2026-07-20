using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Mcp;

/// <summary>
/// MCP server speaking JSON-RPC 2.0 over stdio (newline-delimited messages).
/// Implements initialize, ping, tools/list and tools/call.
/// </summary>
public sealed class McpServer
{
    public const string ServerName = "brazilian-soccer-mcp";
    public const string ServerVersion = "1.0.0";
    public const string ProtocolVersion = "2024-11-05";

    private readonly ToolRegistry _tools;
    private readonly TextReader _input;
    private readonly TextWriter _output;
    private readonly TextWriter _log;

    public McpServer(ToolRegistry tools, TextReader input, TextWriter output, TextWriter? log = null)
    {
        _tools = tools;
        _input = input;
        _output = output;
        _log = log ?? TextWriter.Null;
    }

    /// <summary>Reads newline-delimited JSON-RPC messages until EOF. Returns process exit code.</summary>
    public async Task<int> RunAsync(CancellationToken cancellationToken = default)
    {
        _log.WriteLine($"[{ServerName}] stdio server started, {_tools.Tools.Count} tools registered");
        while (!cancellationToken.IsCancellationRequested)
        {
            var line = await _input.ReadLineAsync(cancellationToken).ConfigureAwait(false);
            if (line is null) break; // EOF -> shutdown
            if (string.IsNullOrWhiteSpace(line)) continue;

            string? response = null;
            try
            {
                response = HandleMessage(line);
            }
            catch (Exception ex)
            {
                response = JsonRpc.Serialize(JsonRpc.Error(null, JsonRpc.InternalError, ex.Message));
            }

            if (response is not null)
            {
                await _output.WriteLineAsync(response).ConfigureAwait(false);
                await _output.FlushAsync().ConfigureAwait(false);
            }
        }
        _log.WriteLine($"[{ServerName}] stdio server stopped");
        return 0;
    }

    /// <summary>Handles one raw JSON-RPC message; returns the serialized response or null for notifications.</summary>
    public string? HandleMessage(string rawMessage)
    {
        JsonNode? node;
        try
        {
            node = JsonNode.Parse(rawMessage);
        }
        catch (Exception)
        {
            return JsonRpc.Serialize(JsonRpc.Error(null, JsonRpc.ParseError, "Invalid JSON"));
        }

        if (node is not JsonObject request)
            return JsonRpc.Serialize(JsonRpc.Error(null, JsonRpc.InvalidRequest, "Message must be a JSON object"));

        var id = request["id"];
        var method = request["method"]?.GetValue<string>();
        if (string.IsNullOrEmpty(method))
            return JsonRpc.Serialize(JsonRpc.Error(id, JsonRpc.InvalidRequest, "Missing 'method'"));

        // Notifications (no id) never get a response.
        var isNotification = id is null;

        try
        {
            switch (method)
            {
                case "initialize":
                    return Respond(id, HandleInitialize());
                case "ping":
                    return Respond(id, new JsonObject());
                case "tools/list":
                    return Respond(id, _tools.ListTools());
                case "tools/call":
                    return Respond(id, _tools.CallTool(request["params"] as JsonObject));
                case "notifications/initialized":
                case "notifications/cancelled":
                case "notifications/progress":
                    return null;
                default:
                    if (method.StartsWith("notifications/", StringComparison.Ordinal))
                        return null;
                    return isNotification
                        ? null
                        : JsonRpc.Serialize(JsonRpc.Error(id, JsonRpc.MethodNotFound, $"Method not found: {method}"));
            }
        }
        catch (ToolCallException ex)
        {
            return JsonRpc.Serialize(JsonRpc.Error(id, ex.RpcCode, ex.Message));
        }
        catch (Exception ex)
        {
            _log.WriteLine($"[{ServerName}] error handling {method}: {ex}");
            return isNotification
                ? null
                : JsonRpc.Serialize(JsonRpc.Error(id, JsonRpc.InternalError, ex.Message));
        }

        string? Respond(JsonNode? messageId, JsonNode result) =>
            isNotification ? null : JsonRpc.Serialize(JsonRpc.Result(messageId, result));
    }

    private static JsonObject HandleInitialize() =>
        new()
        {
            ["protocolVersion"] = ProtocolVersion,
            ["capabilities"] = new JsonObject
            {
                ["tools"] = new JsonObject { ["listChanged"] = false },
            },
            ["serverInfo"] = new JsonObject
            {
                ["name"] = ServerName,
                ["version"] = ServerVersion,
            },
            ["instructions"] =
                "MCP server for Brazilian soccer data (Brasileirão, Copa do Brasil, Copa Libertadores " +
                "matches plus a FIFA player database). Use the tools to query matches, teams, players, " +
                "competitions and statistics. Team names are normalized, so 'Palmeiras-SP', 'palmeiras' " +
                "and 'SE Palmeiras' all match.",
        };
}

public sealed class ToolCallException : Exception
{
    public int RpcCode { get; }

    public ToolCallException(string message, int rpcCode = JsonRpc.InvalidParams) : base(message) =>
        RpcCode = rpcCode;
}
