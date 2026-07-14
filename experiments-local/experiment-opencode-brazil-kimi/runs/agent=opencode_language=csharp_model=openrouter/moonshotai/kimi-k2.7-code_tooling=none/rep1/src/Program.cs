/*
 * Brazilian Soccer MCP Server - Entry Point
 *
 * Loads the Brazilian soccer datasets and starts an MCP server over stdio
 * exposing tools for match, team, player, competition and statistical queries.
 */
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Mcp;
using BrazilianSoccerMcp.Queries;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace BrazilianSoccerMcp;

public static class Program
{
    public static async Task Main(string[] args)
    {
        var dataDirectory = ResolveDataDirectory();

        var builder = Host.CreateApplicationBuilder(args);
        builder.Logging.SetMinimumLevel(LogLevel.Warning);

        builder.Services.AddSingleton(new DataRepository(dataDirectory));
        builder.Services.AddSingleton<QueryEngine>();
        builder.Services.AddMcpServer(_ => { })
            .WithStdioServerTransport()
            .WithTools<SoccerTools>();

        await builder.Build().RunAsync();
    }

    private static string ResolveDataDirectory()
    {
        // Running from project output: data is copied to the output directory.
        var outputData = Path.Combine(AppContext.BaseDirectory, "data", "kaggle");
        if (Directory.Exists(outputData)) return outputData;

        // Running from repository root.
        var repoData = Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
        if (Directory.Exists(repoData)) return repoData;

        var parentRepoData = Path.Combine(Directory.GetCurrentDirectory(), "..", "data", "kaggle");
        if (Directory.Exists(parentRepoData)) return Path.GetFullPath(parentRepoData);

        throw new DirectoryNotFoundException("Could not locate data/kaggle directory.");
    }
}
