// Context block
// File: Program.cs
// Purpose: Entry point for the Brazilian Soccer MCP server executable. Wires a
// SoccerDataStore into the ToolRegistry and starts the stdio McpServer. Logging goes to
// stderr so the stdout JSON-RPC channel stays clean for MCP hosts. The data store loads
// datasets lazily so startup is fast; first tool call triggers the CSV load. No CLI
// arguments are required, but the program exits cleanly on EOF from the host.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Services;

// Ensure UTF-8 is used for stdio so Brazilian Portuguese characters survive intact.
Console.InputEncoding = System.Text.Encoding.UTF8;
Console.OutputEncoding = System.Text.Encoding.UTF8;

var store = new SoccerDataStore();
var tools = new ToolRegistry(store);
var server = new McpServer(tools, Console.In, Console.Out, Console.Error);
server.Run();
