// BrazilianSoccerMcp.Server / Mcp / McpProtocol.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. This file implements the Model Context
// Protocol (https://modelcontextprotocol.io) JSON-RPC 2.0 message shapes this
// server cares about: initialize handshake, tools/list, and tools/call.
// Why hand-rolled instead of the official C# SDK? The official
// ModelContextProtocol NuGet package is still in 0.x preview as of this build;
// pinning to a preview API risks the build breaking on a future restore. The MCP
// JSON-RPC-over-stdio surface is small and stable (spec version 2024-11-05), so a
// self-contained implementation keeps the build hermetic (only CsvHelper + xUnit
// deps) while still speaking the protocol an LLM host can drive.
// Message framing: stdio transport uses newline-delimited JSON (each JSON-RPC
// message on its own line; no Content-Length framing — that's LSP, not MCP).
// -----------------------------------------------------------------------------

using System.Text.Json;
using System.Text.Json.Serialization;

namespace BrazilianSoccerMcp.Server.Mcp;

/// <summary>Top-level JSON-RPC 2.0 envelope (request or notification).</summary>
internal sealed class JsonRpcRequest
{
    [JsonPropertyName("jsonrpc")] public string Jsonrpc { get; set; } = "2.0";
    [JsonPropertyName("id")] public JsonElement? Id { get; set; }
    [JsonPropertyName("method")] public string? Method { get; set; }
    [JsonPropertyName("params")] public JsonElement? Params { get; set; }
}

internal sealed class JsonRpcResponse
{
    [JsonPropertyName("jsonrpc")] public string Jsonrpc { get; set; } = "2.0";
    [JsonPropertyName("id")] public JsonElement? Id { get; set; }
    [JsonPropertyName("result")] public object? Result { get; set; }
    [JsonPropertyName("error")] public JsonRpcError? Error { get; set; }
}

internal sealed class JsonRpcError
{
    [JsonPropertyName("code")] public int Code { get; set; }
    [JsonPropertyName("message")] public string Message { get; set; } = string.Empty;
    [JsonPropertyName("data")] public object? Data { get; set; }
}

/// <summary>Initialize result advertised to the host during the handshake.</summary>
internal sealed class InitializeResult
{
    [JsonPropertyName("protocolVersion")] public string ProtocolVersion { get; set; } = "2024-11-05";
    [JsonPropertyName("capabilities")] public ServerCapabilities Capabilities { get; set; } = new();
    [JsonPropertyName("serverInfo")] public ServerInfo ServerInfo { get; set; } = new();
}

internal sealed class ServerCapabilities
{
    [JsonPropertyName("tools")] public object? Tools { get; set; } = new { };
}

internal sealed class ServerInfo
{
    [JsonPropertyName("name")] public string Name { get; set; } = "brazilian-soccer-mcp";
    [JsonPropertyName("version")] public string Version { get; set; } = "1.0.0";
}

/// <summary>MCP tool descriptor returned by tools/list.</summary>
internal sealed class McpToolDescriptor
{
    [JsonPropertyName("name")] public string Name { get; set; } = string.Empty;
    [JsonPropertyName("description")] public string Description { get; set; } = string.Empty;
    [JsonPropertyName("inputSchema")] public JsonElement InputSchema { get; set; }
}

/// <summary>tools/call argument map: tool name + JSON object of named args.</summary>
internal sealed class ToolCallParams
{
    [JsonPropertyName("name")] public string Name { get; set; } = string.Empty;
    [JsonPropertyName("arguments")] public JsonElement? Arguments { get; set; }
}

/// <summary>The result of a tools/call: a list of content parts.</summary>
internal sealed class ToolCallResult
{
    [JsonPropertyName("content")] public List<ToolContent> Content { get; set; } = new();
    [JsonPropertyName("isError")] public bool IsError { get; set; }
}

internal sealed class ToolContent
{
    [JsonPropertyName("type")] public string Type { get; set; } = "text";
    [JsonPropertyName("text")] public string Text { get; set; } = string.Empty;
}
