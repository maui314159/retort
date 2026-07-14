// Context block
// File: Mcp/McpServer.cs
// Purpose: Stdio JSON-RPC implementation of the Model Context Protocol for the Brazilian
// Soccer MCP server. The server reads newline-delimited JSON-RPC messages from stdin,
// dispatches requests to the ToolRegistry, and writes responses to stdout. All logging
// goes to stderr so the stdout channel stays clean. Supported methods: initialize,
// notifications/initialized (notification, no reply), ping, tools/list, and tools/call.
// The server is designed to be driven by an LLM host that connects stdio to the process.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Mcp;

/// <summary>Stdio MCP server.</summary>
public sealed class McpServer
{
    public const string ProtocolVersion = "2024-11-05";
    public const string ServerName = "brazilian-soccer-mcp";
    public const string ServerVersion = "1.0.0";

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

    /// <summary>Runs the read/dispatch loop until the input stream closes.</summary>
    public void Run()
    {
        string? line;
        while ((line = _input.ReadLine()) is not null)
        {
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }
            try
            {
                HandleLine(line);
            }
            catch (Exception ex)
            {
                Log("error: " + ex.Message);
            }
        }
    }

    private void HandleLine(string line)
    {
        using var doc = JsonDocument.Parse(line);
        var root = doc.RootElement;
        if (!root.TryGetProperty("jsonrpc", out _) && !root.TryGetProperty("method", out _))
        {
            return;
        }
        root.TryGetProperty("id", out var idEl);
        string? id = idEl.ValueKind == JsonValueKind.Undefined ? null : idEl.GetRawText();
        if (!root.TryGetProperty("method", out var methodEl))
        {
            return;
        }
        var method = methodEl.GetString() ?? string.Empty;
        var hasParams = root.TryGetProperty("params", out var paramsEl);
        var isNotification = id is null;

        // Dispatch.
        switch (method)
        {
            case "initialize":
                Respond(id, new JsonObject
                {
                    ["protocolVersion"] = ProtocolVersion,
                    ["capabilities"] = new JsonObject
                    {
                        ["tools"] = new JsonObject { ["listChanged"] = false }
                    },
                    ["serverInfo"] = new JsonObject
                    {
                        ["name"] = ServerName,
                        ["version"] = ServerVersion,
                    },
                });
                return;
            case "notifications/initialized":
                // Notification: no response.
                return;
            case "ping":
                Respond(id, new JsonObject());
                return;
            case "tools/list":
                Respond(id, new JsonObject
                {
                    ["tools"] = _tools.ListJson(),
                });
                return;
            case "tools/call":
                HandleToolsCall(id, hasParams ? paramsEl : default);
                return;
            default:
                if (isNotification) return;
                RespondError(id, -32601, "Method not found: " + method);
                return;
        }
    }

    private void HandleToolsCall(string? id, JsonElement paramsEl)
    {
        string? name = null;
        JsonElement args = default;
        if (paramsEl.ValueKind == JsonValueKind.Object)
        {
            if (paramsEl.TryGetProperty("name", out var n))
            {
                name = n.GetString();
            }
            if (paramsEl.TryGetProperty("arguments", out var a))
            {
                args = a;
            }
        }
        if (string.IsNullOrEmpty(name))
        {
            RespondError(id, -32602, "Missing tool name");
            return;
        }
        try
        {
            var result = _tools.Invoke(name!, args.ValueKind == JsonValueKind.Undefined ? new JsonObject() : JsonNode.Parse(args.GetRawText())!);
            Respond(id, new JsonObject
            {
                ["content"] = new JsonArray
                {
                    new JsonObject
                    {
                        ["type"] = "text",
                        ["text"] = result,
                    }
                },
                ["isError"] = false,
            });
        }
        catch (Exception ex)
        {
            Respond(id, new JsonObject
            {
                ["content"] = new JsonArray
                {
                    new JsonObject
                    {
                        ["type"] = "text",
                        ["text"] = "Error: " + ex.Message,
                    }
                },
                ["isError"] = true,
            });
        }
    }

    private void Respond(string? id, JsonObject result)
    {
        var obj = new JsonObject
        {
            ["jsonrpc"] = "2.0",
        };
        if (id is not null)
        {
            obj["id"] = JsonNode.Parse(id);
        }
        obj["result"] = result;
        Write(obj);
    }

    private void RespondError(string? id, int code, string message)
    {
        var obj = new JsonObject
        {
            ["jsonrpc"] = "2.0",
        };
        if (id is not null)
        {
            obj["id"] = JsonNode.Parse(id);
        }
        obj["error"] = new JsonObject
        {
            ["code"] = code,
            ["message"] = message,
        };
        Write(obj);
    }

    private void Write(JsonNode node)
    {
        var json = node.ToJsonString();
        _output.WriteLine(json);
        _output.Flush();
    }

    private void Log(string message) => _log.WriteLine($"[{ServerName}] {message}");
}
