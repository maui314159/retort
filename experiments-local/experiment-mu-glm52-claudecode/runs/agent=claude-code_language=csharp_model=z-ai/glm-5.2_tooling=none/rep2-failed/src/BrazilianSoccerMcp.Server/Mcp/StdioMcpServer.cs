// BrazilianSoccerMcp.Server / Mcp / StdioMcpServer.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Drives the Model Context Protocol over
// the stdio transport: reads newline-delimited JSON-RPC 2.0 messages from stdin,
// dispatches to the McpToolRegistry, and writes responses to stdout (one JSON
// object per line).
// Protocol lifecycle implemented:
//   * initialize        -> handshake; advertises protocolVersion + serverInfo.
//   * notifications/initialized -> ack only (no response; it's a notification).
//   * tools/list        -> the tool catalog from McpToolRegistry.ListTools().
//   * tools/call        -> dispatch by name, wrap result in {content:[{type:text,...}]}.
//   * ping              -> empty result (keepalive).
// All other methods respond with -32601 method-not-found so a host gets a clean
// MCP error instead of an unhandled crash.
// Framing note: MCP stdio is newline-delimited JSON (NOT LSP-style Content-Length).
// We read the whole line, parse, and respond. Responses are written with a single
// terminating newline and Console.Out is flushed per message.
// Logging: every line written to stderr is out-of-band (MCP hosts treat stdout as
// the protocol stream), so diagnostics go to stderr.
// -----------------------------------------------------------------------------

using System.Text.Json;
using System.Text.Json.Serialization;

namespace BrazilianSoccerMcp.Server.Mcp;

internal sealed class StdioMcpServer
{
    private readonly McpToolRegistry _registry;
    private readonly TextReader _in;
    private readonly TextWriter _out;
    private readonly TextWriter _err;

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = false,
    };

    public StdioMcpServer(McpToolRegistry registry, TextReader? input = null, TextWriter? output = null, TextWriter? error = null)
    {
        _registry = registry;
        _in = input ?? Console.In;
        _out = output ?? Console.Out;
        _err = error ?? Console.Error;
    }

    /// <summary>
    /// Runs the read/respond loop until stdin is closed. Returns when EOF is reached.
    /// </summary>
    public void Run()
    {
        string? line;
        while ((line = _in.ReadLine()) is not null)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;

            JsonRpcRequest? req;
            try
            {
                req = JsonSerializer.Deserialize<JsonRpcRequest>(line, JsonOpts);
            }
            catch (JsonException ex)
            {
                RespondError(null, -32700, $"Parse error: {ex.Message}");
                continue;
            }

            if (req is null) continue;

            // Notifications (no id) are acknowledged silently.
            if (req.Id is null || req.Id.Value.ValueKind == JsonValueKind.Undefined)
            {
                // notifications/initialized requires no response per MCP spec.
                continue;
            }

            HandleRequest(req);
        }
    }

    private void HandleRequest(JsonRpcRequest req)
    {
        try
        {
            switch (req.Method)
            {
                case "initialize":
                    Respond(req.Id, new InitializeResult());
                    break;
                case "ping":
                    Respond(req.Id, new { });
                    break;
                case "tools/list":
                    Respond(req.Id, new { tools = _registry.ListTools() });
                    break;
                case "tools/call":
                    Respond(req.Id, HandleToolCall(req.Params));
                    break;
                default:
                    RespondError(req.Id, -32601, $"Method not found: {req.Method}");
                    break;
            }
        }
        catch (Exception ex)
        {
            _err.WriteLine($"[brazilian-soccer-mcp] error handling {req.Method}: {ex}");
            RespondError(req.Id, -32603, $"Internal error: {ex.Message}");
        }
    }

    private ToolCallResult HandleToolCall(JsonElement? @params)
    {
        if (!@params.HasValue)
            return ErrorResult("tools/call requires params.");
        var call = @params.Value.Deserialize<ToolCallParams>(JsonOpts);
        if (call is null || string.IsNullOrEmpty(call.Name))
            return ErrorResult("tools/call requires a tool name.");

        var (text, isError) = _registry.Invoke(call.Name, call.Arguments);
        return new ToolCallResult
        {
            Content = new() { new() { Type = "text", Text = text } },
            IsError = isError,
        };
    }

    private static ToolCallResult ErrorResult(string msg) =>
        new() { Content = new() { new() { Type = "text", Text = msg } }, IsError = true };

    private void Respond(JsonElement? id, object result)
    {
        var resp = new JsonRpcResponse { Id = id, Result = result };
        var json = JsonSerializer.Serialize(resp, JsonOpts);
        _out.WriteLine(json);
        _out.Flush();
    }

    private void RespondError(JsonElement? id, int code, string message)
    {
        var resp = new JsonRpcResponse
        {
            Id = id,
            Error = new JsonRpcError { Code = code, Message = message }
        };
        var json = JsonSerializer.Serialize(resp, JsonOpts);
        _out.WriteLine(json);
        _out.Flush();
    }
}
