using System.Text.Json;
using System.Text.Json.Nodes;

namespace BrazilianSoccerMcp;

/// <summary>
/// Minimal MCP server speaking JSON-RPC 2.0 over stdio (newline-delimited messages).
/// Implements the initialize, tools/list, and tools/call methods.
/// </summary>
public sealed class McpServer
{
    private readonly SoccerTools _tools;
    private readonly Dictionary<string, ToolDef> _byName;

    private const string ProtocolVersion = "2024-11-05";

    public McpServer(SoccerTools tools)
    {
        _tools = tools;
        _byName = tools.Tools().ToDictionary(t => t.Name);
    }

    /// <summary>Run the stdio loop until stdin is closed. Returns when input ends.</summary>
    public void Run()
    {
        using var reader = new StreamReader(Console.OpenStandardInput());
        var writer = new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = false };
        string? line;
        while ((line = reader.ReadLine()) is not null)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            var response = HandleMessage(line);
            if (response is null) continue; // notification, no response
            writer.WriteLine(response);
            writer.Flush();
        }
    }

    /// <summary>Handle a single JSON-RPC request. Returns the response JSON, or null for notifications.</summary>
    public string? HandleMessage(string json)
    {
        JsonNode? doc;
        try { doc = JsonNode.Parse(json); }
        catch { return Error(null, -32700, "Parse error"); }

        if (doc is not JsonObject obj)
            return Error(null, -32700, "Parse error");

        var id = obj["id"]?.DeepClone();
        var method = obj["method"]?.GetValue<string>();

        // Notifications (no id) get no response.
        if (id is null)
            return null;

        try
        {
            var result = method switch
            {
                "initialize" => Initialize(obj["params"]),
                "tools/list" => ListTools(),
                "tools/call" => CallTool(obj["params"]),
                "ping" => new JsonObject { ["pong"] = true },
                _ => throw new McpError(-32601, $"Method not found: {method}")
            };
            return Success(id, result).ToJsonString(JsonOpts);
        }
        catch (McpError ex)
        {
            return Error(id, ex.Code, ex.Message);
        }
    }

    private JsonObject Initialize(JsonNode? parameters)
    {
        // Echo the client's protocol version if compatible, else default.
        return new JsonObject
        {
            ["protocolVersion"] = ProtocolVersion,
            ["capabilities"] = new JsonObject
            {
                ["tools"] = new JsonObject()
            },
            ["serverInfo"] = new JsonObject
            {
                ["name"] = "brazilian-soccer-mcp",
                ["version"] = "1.0.0"
            }
        };
    }

    private JsonObject ListTools()
    {
        var arr = new JsonArray();
        foreach (var t in _tools.Tools())
        {
            arr.Add(new JsonObject
            {
                ["name"] = t.Name,
                ["description"] = t.Description,
                ["inputSchema"] = JsonNode.Parse(t.InputSchema.GetRawText())
            });
        }
        return new JsonObject { ["tools"] = arr };
    }

    private JsonObject CallTool(JsonNode? parameters)
    {
        if (parameters is not JsonObject p)
            throw new McpError(-32602, "Invalid parameters");
        var name = p["name"]?.GetValue<string>()
            ?? throw new McpError(-32602, "Missing tool name");

        if (!_byName.TryGetValue(name, out var tool))
            throw new McpError(-32602, $"Unknown tool: {name}");

        var argsNode = p["arguments"];
        JsonElement argsEl;
        if (argsNode is null)
        {
            argsEl = JsonSerializer.Deserialize<JsonElement>("{}");
        }
        else
        {
            argsEl = JsonSerializer.Deserialize<JsonElement>(argsNode.ToJsonString());
        }

        string text;
        try
        {
            text = tool.Handler(argsEl);
        }
        catch (Exception ex)
        {
            return new JsonObject
            {
                ["content"] = new JsonArray(new JsonObject { ["type"] = "text", ["text"] = $"Error: {ex.Message}" }),
                ["isError"] = true
            };
        }

        return new JsonObject
        {
            ["content"] = new JsonArray(new JsonObject { ["type"] = "text", ["text"] = text }),
            ["isError"] = false
        };
    }

    // ---------- JSON-RPC envelope helpers ----------

    private static JsonObject Success(JsonNode id, JsonObject result) => new()
    {
        ["jsonrpc"] = "2.0",
        ["id"] = id,
        ["result"] = result
    };

    private static string Error(JsonNode? id, int code, string message)
    {
        var obj = new JsonObject
        {
            ["jsonrpc"] = "2.0",
            ["id"] = id,
            ["error"] = new JsonObject { ["code"] = code, ["message"] = message }
        };
        return obj.ToJsonString(JsonOpts);
    }

    private static readonly JsonSerializerOptions JsonOpts = new() { WriteIndented = false };

    private sealed class McpError(int code, string message) : Exception(message)
    {
        public int Code { get; } = code;
    }
}