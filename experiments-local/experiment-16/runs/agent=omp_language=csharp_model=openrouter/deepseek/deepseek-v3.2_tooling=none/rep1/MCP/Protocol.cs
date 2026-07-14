using System.Text.Json;
using System.Text.Json.Serialization;

namespace BrazilianSoccerMCP.MCP
{
    /// <summary>
    /// MCP (Model Context Protocol) message base
    /// </summary>
    public class MCPMessage
    {
        [JsonPropertyName("jsonrpc")]
        public string JsonRpc { get; set; } = "2.0";
        
        [JsonPropertyName("id")]
        public object? Id { get; set; }
        
        [JsonPropertyName("method")]
        public string? Method { get; set; }
        
        [JsonPropertyName("params")]
        public object? Params { get; set; }
        
        [JsonPropertyName("result")]
        public object? Result { get; set; }
        
        [JsonPropertyName("error")]
        public MCPError? Error { get; set; }
    }
    
    /// <summary>
    /// MCP error object
    /// </summary>
    public class MCPError
    {
        [JsonPropertyName("code")]
        public int Code { get; set; }
        
        [JsonPropertyName("message")]
        public string Message { get; set; } = "";
        
        [JsonPropertyName("data")]
        public object? Data { get; set; }
    }
    
    /// <summary>
    /// MCP tool definition
    /// </summary>
    public class MCPTool
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = "";
        
        [JsonPropertyName("description")]
        public string Description { get; set; } = "";
        
        [JsonPropertyName("inputSchema")]
        public MCPSchema InputSchema { get; set; } = new MCPSchema();
    }
    
    /// <summary>
    /// MCP JSON schema
    /// </summary>
    public class MCPSchema
    {
        [JsonPropertyName("type")]
        public string Type { get; set; } = "object";
        
        [JsonPropertyName("properties")]
        public Dictionary<string, MCPSchemaProperty> Properties { get; set; } = new Dictionary<string, MCPSchemaProperty>();
        
        [JsonPropertyName("required")]
        public List<string> Required { get; set; } = new List<string>();
    }
    
    /// <summary>
    /// MCP schema property
    /// </summary>
    public class MCPSchemaProperty
    {
        [JsonPropertyName("type")]
        public string Type { get; set; } = "string";
        
        [JsonPropertyName("description")]
        public string Description { get; set; } = "";
        
        [JsonPropertyName("enum")]
        public List<string>? Enum { get; set; }
    }
    
    /// <summary>
    /// MCP list tools result
    /// </summary>
    public class MCPListToolsResult
    {
        [JsonPropertyName("tools")]
        public List<MCPTool> Tools { get; set; } = new List<MCPTool>();
    }
    
    /// <summary>
    /// MCP call tool parameters
    /// </summary>
    public class MCPCallToolParams
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = "";
        
        [JsonPropertyName("arguments")]
        public Dictionary<string, object> Arguments { get; set; } = new Dictionary<string, object>();
    }
    
    /// <summary>
    /// MCP call tool result
    /// </summary>
    public class MCPCallToolResult
    {
        [JsonPropertyName("content")]
        public List<MCPContent> Content { get; set; } = new List<MCPContent>();
    }
    
    /// <summary>
    /// MCP content
    /// </summary>
    public class MCPContent
    {
        [JsonPropertyName("type")]
        public string Type { get; set; } = "text";
        
        [JsonPropertyName("text")]
        public string Text { get; set; } = "";
    }
    
    /// <summary>
    /// MCP server capabilities
    /// </summary>
    public class MCPServerCapabilities
    {
        [JsonPropertyName("tools")]
        public MCPServerToolCapabilities Tools { get; set; } = new MCPServerToolCapabilities();
    }
    
    /// <summary>
    /// MCP server tool capabilities
    /// </summary>
    public class MCPServerToolCapabilities
    {
        [JsonPropertyName("listChanged")]
        public bool ListChanged { get; set; }
    }
    
    /// <summary>
    /// MCP initialization parameters
    /// </summary>
    public class MCPInitializeParams
    {
        [JsonPropertyName("protocolVersion")]
        public string ProtocolVersion { get; set; } = "";
        
        [JsonPropertyName("capabilities")]
        public object? Capabilities { get; set; }
        
        [JsonPropertyName("clientInfo")]
        public MCPClientInfo? ClientInfo { get; set; }
    }
    
    /// <summary>
    /// MCP client info
    /// </summary>
    public class MCPClientInfo
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = "";
        
        [JsonPropertyName("version")]
        public string Version { get; set; } = "";
    }
    
    /// <summary>
    /// MCP initialization result
    /// </summary>
    public class MCPInitializeResult
    {
        [JsonPropertyName("protocolVersion")]
        public string ProtocolVersion { get; set; } = "2024-11-05";
        
        [JsonPropertyName("capabilities")]
        public MCPServerCapabilities Capabilities { get; set; } = new MCPServerCapabilities();
        
        [JsonPropertyName("serverInfo")]
        public MCPServerInfo ServerInfo { get; set; } = new MCPServerInfo();
    }
    
    /// <summary>
    /// MCP server info
    /// </summary>
    public class MCPServerInfo
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = "brazilian-soccer-mcp";
        
        [JsonPropertyName("version")]
        public string Version { get; set; } = "1.0.0";
    }
}