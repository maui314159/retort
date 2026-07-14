using System.Text.Json;
using System.Text.Json.Serialization;

namespace BrazilianSoccerMCP.Models;

/// <summary>
/// JSON-RPC 2.0 message types for MCP protocol.
/// </summary>

public class JsonRpcRequest
{
    [JsonPropertyName("jsonrpc")]
    public string JsonRpc { get; set; } = "2.0";

    [JsonPropertyName("id")]
    public JsonElement? Id { get; set; }

    [JsonPropertyName("method")]
    public string Method { get; set; } = "";

    [JsonPropertyName("params")]
    public JsonElement? Params { get; set; }
}

public class JsonRpcResponse
{
    [JsonPropertyName("jsonrpc")]
    public string JsonRpc { get; set; } = "2.0";

    [JsonPropertyName("id")]
    public JsonElement? Id { get; set; }

    [JsonPropertyName("result")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public JsonElement? Result { get; set; }

    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public JsonRpcError? Error { get; set; }

    public static JsonRpcResponse Success(JsonElement? id, object result)
    {
        return new JsonRpcResponse
        {
            Id = id,
            Result = JsonSerializer.SerializeToElement(result)
        };
    }

    public static JsonRpcResponse Failure(JsonElement? id, int code, string message)
    {
        return new JsonRpcResponse
        {
            Id = id,
            Error = new JsonRpcError { Code = code, Message = message }
        };
    }

    public static JsonRpcResponse MethodNotFound(JsonElement? id, string method)
    {
        return Failure(id, -32601, $"Method not found: {method}");
    }
}

public class JsonRpcError
{
    [JsonPropertyName("code")]
    public int Code { get; set; }

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}

// MCP Protocol messages

public class InitializeResult
{
    [JsonPropertyName("protocolVersion")]
    public string ProtocolVersion { get; set; } = "2024-11-05";

    [JsonPropertyName("capabilities")]
    public ServerCapabilities Capabilities { get; set; } = new();

    [JsonPropertyName("serverInfo")]
    public ServerInfo ServerInfo { get; set; } = new();
}

public class ServerCapabilities
{
    [JsonPropertyName("tools")]
    public CapabilityEntry? Tools { get; set; } = new();

    [JsonPropertyName("resources")]
    public CapabilityEntry? Resources { get; set; } = new();
}

public class CapabilityEntry
{
    // Can be extended with listChanged, subscribe, etc.
}

public class ServerInfo
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "brazilian-soccer-mcp";

    [JsonPropertyName("version")]
    public string Version { get; set; } = "1.0.0";
}

public class ListToolsResult
{
    [JsonPropertyName("tools")]
    public List<ToolDefinition> Tools { get; set; } = new();
}

public class ToolDefinition
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("description")]
    public string Description { get; set; } = "";

    [JsonPropertyName("inputSchema")]
    public JsonElement InputSchema { get; set; }
}

public class CallToolParams
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("arguments")]
    public JsonElement? Arguments { get; set; }
}

public class CallToolResult
{
    [JsonPropertyName("content")]
    public List<ContentItem> Content { get; set; } = new();
}

public class ContentItem
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "text";

    [JsonPropertyName("text")]
    public string Text { get; set; } = "";
}

public class ListResourcesResult
{
    [JsonPropertyName("resources")]
    public List<ResourceDefinition> Resources { get; set; } = new();
}

public class ResourceDefinition
{
    [JsonPropertyName("uri")]
    public string Uri { get; set; } = "";

    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("description")]
    public string Description { get; set; } = "";

    [JsonPropertyName("mimeType")]
    public string MimeType { get; set; } = "text/csv";
}

public class ReadResourceParams
{
    [JsonPropertyName("uri")]
    public string Uri { get; set; } = "";
}

public class ReadResourceResult
{
    [JsonPropertyName("contents")]
    public List<ResourceContent> Contents { get; set; } = new();
}

public class ResourceContent
{
    [JsonPropertyName("uri")]
    public string Uri { get; set; } = "";

    [JsonPropertyName("mimeType")]
    public string MimeType { get; set; } = "text/csv";

    [JsonPropertyName("text")]
    public string Text { get; set; } = "";
}

/// <summary>
/// Notification message (no id).
/// </summary>
public class JsonRpcNotification
{
    [JsonPropertyName("jsonrpc")]
    public string JsonRpc { get; set; } = "2.0";

    [JsonPropertyName("method")]
    public string Method { get; set; } = "";

    [JsonPropertyName("params")]
    public JsonElement? Params { get; set; }
}
