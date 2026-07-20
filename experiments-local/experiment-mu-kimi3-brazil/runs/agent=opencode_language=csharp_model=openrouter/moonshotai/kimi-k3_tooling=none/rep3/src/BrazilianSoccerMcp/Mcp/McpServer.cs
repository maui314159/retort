using System.Text;
using System.Text.Json;
using BrazilianSoccerMcp.Tools;

namespace BrazilianSoccerMcp.Mcp;

/// <summary>
/// Minimal, dependency-free Model Context Protocol server over stdio:
/// newline-delimited JSON-RPC 2.0. Implements initialize, ping, tools/list,
/// tools/call, plus empty resources/prompts listings. Nothing but protocol
/// messages is ever written to the output stream.
/// </summary>
public sealed class McpServer
{
    public const string ServerName = "brazilian-soccer-mcp";
    public const string ServerVersion = "1.0.0";
    public const string DefaultProtocolVersion = "2024-11-05";

    private static readonly JsonSerializerOptions SerializerOptions = new()
    {
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
    };

    private readonly ToolRegistry _tools;

    public McpServer(ToolRegistry tools) => _tools = tools;

    /// <summary>
    /// Handles one JSON-RPC message and returns the response line, or null for
    /// notifications (which must not be answered). Separated from I/O for testability.
    /// </summary>
    public string? HandleMessage(string jsonLine)
    {
        JsonDocument doc;
        try
        {
            doc = JsonDocument.Parse(jsonLine);
        }
        catch (JsonException ex)
        {
            return Serialize(new { jsonrpc = "2.0", id = (JsonElement?)null, error = new { code = -32700, message = $"Parse error: {ex.Message}" } });
        }

        using (doc)
        {
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("method", out var methodEl))
                return Serialize(new { jsonrpc = "2.0", id = (JsonElement?)null, error = new { code = -32600, message = "Invalid Request: missing method" } });

            var method = methodEl.GetString() ?? string.Empty;
            var id = root.TryGetProperty("id", out var idEl) ? idEl.Clone() : (JsonElement?)null;

            // Notifications never get a response.
            if (method.StartsWith("notifications/", StringComparison.Ordinal))
                return null;

            try
            {
                return method switch
                {
                    "initialize" => Serialize(new { jsonrpc = "2.0", id, result = InitializeResult(root) }),
                    "ping" => Serialize(new { jsonrpc = "2.0", id, result = new { } }),
                    "tools/list" => Serialize(new { jsonrpc = "2.0", id, result = _tools.ListToolsResult() }),
                    "tools/call" => Serialize(ToolsCallResult(root, id)),
                    "resources/list" => Serialize(new { jsonrpc = "2.0", id, result = new { resources = Array.Empty<object>() } }),
                    "prompts/list" => Serialize(new { jsonrpc = "2.0", id, result = new { prompts = Array.Empty<object>() } }),
                    _ => Serialize(new { jsonrpc = "2.0", id, error = new { code = -32601, message = $"Method not found: '{method}'" } }),
                };
            }
            catch (Exception ex)
            {
                return Serialize(new { jsonrpc = "2.0", id, error = new { code = -32603, message = $"Internal error: {ex.Message}" } });
            }
        }
    }

    private static object InitializeResult(JsonElement root)
    {
        // Echo the client's protocol version when provided, else use our default.
        var version = DefaultProtocolVersion;
        if (root.TryGetProperty("params", out var p)
            && p.ValueKind == JsonValueKind.Object
            && p.TryGetProperty("protocolVersion", out var v)
            && v.ValueKind == JsonValueKind.String)
            version = v.GetString() ?? DefaultProtocolVersion;

        return new
        {
            protocolVersion = version,
            capabilities = new { tools = new { listChanged = false } },
            serverInfo = new { name = ServerName, version = ServerVersion },
        };
    }

    private object ToolsCallResult(JsonElement root, JsonElement? id)
    {
        if (!root.TryGetProperty("params", out var p) || p.ValueKind != JsonValueKind.Object)
            return new { jsonrpc = "2.0", id, error = new { code = -32602, message = "Invalid params: expected object" } };

        var name = p.TryGetProperty("name", out var n) && n.ValueKind == JsonValueKind.String
            ? n.GetString() ?? string.Empty
            : string.Empty;

        Dictionary<string, JsonElement>? args = null;
        if (p.TryGetProperty("arguments", out var a) && a.ValueKind == JsonValueKind.Object)
        {
            args = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
            foreach (var prop in a.EnumerateObject())
                args[prop.Name] = prop.Value.Clone();
        }

        var (text, isError) = _tools.Call(name, args);
        return new
        {
            jsonrpc = "2.0",
            id,
            result = new
            {
                content = new[] { new { type = "text", text } },
                isError,
            },
        };
    }

    private static string Serialize(object value) => JsonSerializer.Serialize(value, SerializerOptions);

    /// <summary>Runs the stdio loop until the input stream closes.</summary>
    public async Task RunAsync(Stream input, Stream output, CancellationToken cancellationToken = default)
    {
        using var reader = new StreamReader(input, Encoding.UTF8);
        var writer = new StreamWriter(output, new UTF8Encoding(false)) { AutoFlush = true };

        while (!cancellationToken.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(cancellationToken).ConfigureAwait(false);
            if (line is null)
                break; // client closed the pipe
            if (string.IsNullOrWhiteSpace(line))
                continue;

            string? response;
            try
            {
                response = HandleMessage(line);
            }
            catch (Exception ex)
            {
                response = Serialize(new { jsonrpc = "2.0", id = (JsonElement?)null, error = new { code = -32603, message = $"Internal error: {ex.Message}" } });
            }

            if (response is not null)
                await writer.WriteLineAsync(response).ConfigureAwait(false);
        }
    }
}
