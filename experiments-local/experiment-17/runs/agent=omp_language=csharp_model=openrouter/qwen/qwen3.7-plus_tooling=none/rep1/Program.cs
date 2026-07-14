using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Services;
using ModelContextProtocol.Server;

var builder = WebApplication.CreateBuilder(args);

// Add MCP server
builder.Services.AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

// Register data loader and services
var dataDir = Path.Combine(Directory.GetCurrentDirectory(), "..", "data", "kaggle");
if (!Directory.Exists(dataDir))
{
    // Fallback for different execution contexts
    dataDir = Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
}

builder.Services.AddSingleton(new DataLoader(dataDir));
builder.Services.AddSingleton<SoccerService>();

var app = builder.Build();

// MCP endpoints
app.MapMcp();

app.Run();
