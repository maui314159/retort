using System.Text.Json;
using System.Text.Json.Nodes;

namespace BrazilianSoccerMcp.Mcp;

/// <summary>
/// Minimal Model Context Protocol (MCP) server that speaks JSON-RPC 2.0
/// over stdio. Implements the standard lifecycle methods
/// (<c>initialize</c>, <c>initialized</c>, <c>tools/list</c>,
/// <c>tools/call</c>) and exposes the Brazilian soccer query services as
/// MCP tools so an LLM host can invoke them.
///
/// The protocol is intentionally hand-rolled (no external SDK dependency)
/// to keep the project self-contained and to demonstrate the wire format.
/// See https://modelcontextprotocol.io for the full specification.
/// </summary>
public sealed class McpServer
{
    private readonly ToolRegistry _registry;
    private readonly TextReader _input;
    private readonly TextWriter _output;

    private const string ProtocolVersion = "2024-11-05";
    private const string ServerName = "brazilian-soccer-mcp";
    private const string ServerVersion = "1.0.0";

    public McpServer(ToolRegistry registry, TextReader input, TextWriter output)
    {
        _registry = registry;
        _input = input;
        _output = output;
    }

    public void Run(CancellationToken cancellationToken = default)
    {
        string? line;
        while ((line = _input.ReadLine()) != null)
        {
            if (cancellationToken.IsCancellationRequested) break;
            if (string.IsNullOrWhiteSpace(line)) continue;

            var response = HandleLine(line);
            if (response == null) continue;

            var json = response.ToJsonString();
            lock (_output)
            {
                _output.WriteLine(json);
                _output.Flush();
            }
        }
    }

    /// <summary>Processes a single JSON-RPC request line. Returns the response
    /// object, or null if the line is a notification that needs no reply.</summary>
    public JsonObject? HandleLine(string line)
    {
        JsonNode? request;
        try { request = JsonNode.Parse(line); }
        catch { return null; }
        if (request == null) return null;

        // Notifications have no "id" - we just acknowledge by ignoring.
        if (request["method"]?.GetValue<string>() == "notifications/initialized")
            return null;

        var id = request["id"];
        var method = request["method"]?.GetValue<string>();
        var response = Handle(method, request["params"]);
        response["id"] = id?.DeepClone() ?? JsonValue.Create((string?)null);
        response["jsonrpc"] = "2.0";
        return response;
    }

    private JsonObject Handle(string? method, JsonNode? parameters)
    {
        try
        {
            return method switch
            {
                "initialize" => HandleInitialize(),
                "tools/list" => HandleToolsList(),
                "tools/call" => HandleToolsCall(parameters),
                "ping" => Result(new JsonObject()),
                _ => Error(-32601, $"Method not found: {method}"),
            };
        }
        catch (ArgumentException ex)
        {
            return Error(-32602, ex.Message);
        }
        catch (Exception ex)
        {
            return Error(-32603, ex.Message);
        }
    }

    private JsonObject HandleInitialize()
    {
        var result = new JsonObject
        {
            ["protocolVersion"] = ProtocolVersion,
            ["capabilities"] = new JsonObject
            {
                ["tools"] = new JsonObject { },
            },
            ["serverInfo"] = new JsonObject
            {
                ["name"] = ServerName,
                ["version"] = ServerVersion,
            },
        };
        return Result(result);
    }

    private JsonObject HandleToolsList()
    {
        var tools = new JsonArray();
        foreach (var tool in _registry.Tools)
        {
            var obj = new JsonObject
            {
                ["name"] = tool.Name,
                ["description"] = tool.Description,
                ["inputSchema"] = tool.InputSchema,
            };
            tools.Add(obj);
        }
        return Result(new JsonObject { ["tools"] = tools });
    }

    private JsonObject HandleToolsCall(JsonNode? parameters)
    {
        var name = parameters?["name"]?.GetValue<string>()
            ?? throw new ArgumentException("Missing 'name' in tools/call params");
        var args = parameters?["arguments"] as JsonObject ?? new JsonObject();

        var tool = _registry.Get(name);
        var text = tool.Invoke(args);

        var content = new JsonArray
        {
            new JsonObject
            {
                ["type"] = "text",
                ["text"] = text,
            },
        };
        return Result(new JsonObject { ["content"] = content, ["isError"] = false });
    }

    private static JsonObject Result(JsonNode result)
        => new() { ["result"] = result };

    private static JsonObject Error(int code, string message)
        => new()
        {
            ["error"] = new JsonObject
            {
                ["code"] = code,
                ["message"] = message,
            },
        };
}
