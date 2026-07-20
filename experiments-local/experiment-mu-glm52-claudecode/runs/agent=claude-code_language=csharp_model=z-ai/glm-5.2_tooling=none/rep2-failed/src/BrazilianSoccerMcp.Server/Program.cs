// BrazilianSoccerMcp.Server / Program.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server (TASK.md). Entry point for the stdio MCP
// server host.
// What it does:
//   1. Resolves the data/kaggle CSV directory (looks next to the server binary
//      first because the .csproj copies the CSVs to the output folder, then
//      falls back to the repo-root data/kaggle path via DataLocator).
//   2. Constructs the SoccerDataService (loads all six CSVs once) and the
//      McpToolRegistry that exposes the query surface as MCP tools.
//   3. Runs the StdioMcpServer read/respond loop until stdin closes.
// Diagnostics go to stderr so the stdout JSON-RPC stream stays clean.
// CLI flags:
//   --data-root <path>   override the CSV directory location.
//   --print-tools        print the tool catalog as JSON to stdout and exit (handy
//                       for smoke-testing the tool surface without a host).
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Server.Mcp;

var cliArgs = Environment.GetCommandLineArgs();
string? dataRoot = null;
bool printTools = false;
for (int i = 1; i < cliArgs.Length; i++)
{
    if (cliArgs[i] == "--data-root" && i + 1 < cliArgs.Length) dataRoot = cliArgs[++i];
    else if (cliArgs[i] == "--print-tools") printTools = true;
}

// Resolve the CSV directory. Prefer the explicit override, then the data/kaggle
// folder next to the binary (copied via the .csproj <None CopyToOutputDirectory>),
// then the repo-root walk-up in DataLocator.
string kagglePath;
try
{
    kagglePath = DataLocator.ResolveKagglePath(dataRoot);
}
catch (DirectoryNotFoundException ex)
{
    Console.Error.WriteLine($"[brazilian-soccer-mcp] {ex.Message}");
    return 2;
}

var data = new SoccerDataService(kagglePath);
var registry = new McpToolRegistry(data);

if (printTools)
{
    var tools = registry.ListTools();
    Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(tools,
        new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
    return 0;
}

var server = new StdioMcpServer(registry);
server.Run();
return 0;
