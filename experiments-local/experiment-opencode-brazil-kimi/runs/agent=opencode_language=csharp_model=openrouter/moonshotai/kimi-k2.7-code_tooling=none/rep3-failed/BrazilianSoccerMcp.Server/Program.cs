// <copyright file="Program.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Bootstrap for the stdio-based MCP server.
// </copyright>
using BrazilianSoccerMcp.Core.Data;
using BrazilianSoccerMcp.Core.Services;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Console;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Server;

class Program
{
    static async Task Main(string[] args)
    {
        var builder = Host.CreateApplicationBuilder(args);

        // Resolve the data directory. If a path is supplied as the first argument use it,
        // otherwise search upward from the application base directory for data/kaggle.
        var dataDirectory = args.Length > 0
            ? args[0]
            : ResolveDataDirectory();

        builder.Services.AddSingleton(new CsvDataLoader(dataDirectory));
        builder.Services.AddSingleton<SoccerDataContext>();
        builder.Services.AddSingleton<SoccerQueryService>();

        // Keep log output on stderr so that stdout remains a clean MCP JSON-RPC stream.
        builder.Logging.ClearProviders();
        builder.Logging.SetMinimumLevel(LogLevel.Warning);
        builder.Logging.AddConsole(options =>
        {
            options.LogToStandardErrorThreshold = LogLevel.Trace;
        });

        builder.Services.AddMcpServer()
            .WithStdioServerTransport()
            .WithToolsFromAssembly();

        await builder.Build().RunAsync();
    }

    private static string ResolveDataDirectory()
    {
        var current = AppContext.BaseDirectory;
        for (var i = 0; i < 8; i++)
        {
            var candidate = Path.Combine(current, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;

            var parent = Directory.GetParent(current);
            if (parent == null)
                break;
            current = parent.FullName;
        }

        return Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
    }
}
