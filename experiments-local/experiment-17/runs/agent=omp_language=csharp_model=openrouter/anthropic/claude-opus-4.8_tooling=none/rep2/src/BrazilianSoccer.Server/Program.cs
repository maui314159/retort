// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    Program.cs
// Project: BrazilianSoccer.Server
// Purpose: Entry point for the Brazilian Soccer MCP server. Boots a Generic
//          Host, loads the Kaggle datasets once into a singleton QueryService,
//          and exposes the SoccerTools over the MCP stdio transport so an LLM
//          client can call them.
// Notes:   - All diagnostic logging goes to stderr; stdout is reserved for the
//            MCP JSON-RPC protocol stream.
//          - The data directory is located by walking up from the working
//            directory (see DataLoader.LocateDataDirectory); override via the
//            SOCCER_DATA_DIR environment variable.
// =============================================================================

using BrazilianSoccer.Core.Data;
using BrazilianSoccer.Core.Queries;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

// MCP stdio uses stdout for protocol traffic; route all logs to stderr.
builder.Logging.AddConsole(options =>
{
    options.LogToStandardErrorThreshold = LogLevel.Trace;
});

builder.Services.AddSingleton(_ =>
{
    var dir = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR");
    if (string.IsNullOrWhiteSpace(dir))
        dir = DataLoader.LocateDataDirectory();
    return new DataLoader(dir).Load();
});
builder.Services.AddSingleton(sp => new QueryService(sp.GetRequiredService<SoccerDataset>()));

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly(typeof(BrazilianSoccer.Server.SoccerTools).Assembly);

await builder.Build().RunAsync();
