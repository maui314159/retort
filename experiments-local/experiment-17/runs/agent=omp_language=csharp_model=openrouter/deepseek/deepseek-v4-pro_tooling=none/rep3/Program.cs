using System.Diagnostics;
using System.Text;
using System.Text.Json;
using BrazilianSoccerMCP.Models;
using BrazilianSoccerMCP.Services;

namespace BrazilianSoccerMCP;

/// <summary>
/// Brazilian Soccer MCP Server - Model Context Protocol server for Brazilian soccer data.
/// Provides tools for querying matches, teams, players, competitions, and statistics
/// from 6 Kaggle datasets covering Brasileirão, Copa do Brasil, Copa Libertadores,
/// and FIFA player data.
/// </summary>
public class Program
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false,
    };

    public static void Main(string[] args)
    {
        // Determine data directory
        var dataDir = args.Length > 0 ? args[0] : Path.Combine(AppContext.BaseDirectory, "data");

        // If running from project directory, try parent paths
        if (!Directory.Exists(dataDir))
        {
            dataDir = Path.Combine(Directory.GetCurrentDirectory(), "data");
        }

        // Log to stderr so it doesn't interfere with stdio protocol
        Console.Error.WriteLine($"[brazilian-soccer-mcp] Loading data from: {dataDir}");
        var sw = Stopwatch.StartNew();

        var loader = new DataLoader(dataDir);
        loader.LoadAll();

        Console.Error.WriteLine($"[brazilian-soccer-mcp] Loaded {loader.AllMatches.Count:N0} matches and {loader.Players.Count:N0} players in {sw.Elapsed.TotalSeconds:F1}s");

        var matchService = new MatchService(loader.AllMatches);
        var playerService = new PlayerService(loader.Players);
        var competitionService = new CompetitionService(loader.AllMatches);
        var toolRegistry = new ToolRegistry(matchService, playerService, competitionService);
        var resourceRegistry = new ResourceRegistry(dataDir);

        // MCP server name
        const string serverName = "brazilian-soccer-mcp";

        // Read JSON-RPC messages from stdin, one per line
        using var stdin = Console.OpenStandardInput();
        using var stdout = Console.OpenStandardOutput();
        using var reader = new StreamReader(stdin, Encoding.UTF8);
        using var writer = new StreamWriter(stdout, Encoding.UTF8) { AutoFlush = true };

        Console.Error.WriteLine($"[{serverName}] MCP server ready, waiting for requests...");

        string? line;
        while ((line = reader.ReadLine()) != null)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;

            JsonRpcRequest? request;
            try
            {
                request = JsonSerializer.Deserialize<JsonRpcRequest>(line, JsonOptions);
            }
            catch (JsonException ex)
            {
                Console.Error.WriteLine($"[{serverName}] JSON parse error: {ex.Message}");
                continue;
            }

            if (request == null) continue;

            try
            {
                ProcessRequest(request, toolRegistry, resourceRegistry, writer);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"[{serverName}] Error processing {request.Method}: {ex.Message}");
                SendResponse(writer, JsonRpcResponse.Failure(request.Id, -32603, $"Internal error: {ex.Message}"));
            }
        }

        Console.Error.WriteLine($"[{serverName}] stdin closed, shutting down.");
    }

    private static void ProcessRequest(JsonRpcRequest request, ToolRegistry toolRegistry,
        ResourceRegistry resourceRegistry, StreamWriter writer)
    {
        switch (request.Method)
        {
            case "initialize":
                HandleInitialize(request, writer);
                break;

            case "notifications/initialized":
                // No response needed for notifications
                break;

            case "tools/list":
                HandleToolsList(request, toolRegistry, writer);
                break;

            case "tools/call":
                HandleToolsCall(request, toolRegistry, writer);
                break;

            case "resources/list":
                HandleResourcesList(request, resourceRegistry, writer);
                break;

            case "resources/read":
                HandleResourcesRead(request, resourceRegistry, writer);
                break;

            case "ping":
                SendResponse(writer, JsonRpcResponse.Success(request.Id, new { }));
                break;

            default:
                SendResponse(writer, JsonRpcResponse.MethodNotFound(request.Id, request.Method));
                break;
        }
    }

    private static void HandleInitialize(JsonRpcRequest request, StreamWriter writer)
    {
        var result = new InitializeResult
        {
            ProtocolVersion = "2024-11-05",
            Capabilities = new ServerCapabilities
            {
                Tools = new CapabilityEntry(),
                Resources = new CapabilityEntry(),
            },
            ServerInfo = new ServerInfo
            {
                Name = "brazilian-soccer-mcp",
                Version = "1.0.0",
            },
        };

        SendResponse(writer, JsonRpcResponse.Success(request.Id, result));
    }

    private static void HandleToolsList(JsonRpcRequest request, ToolRegistry toolRegistry, StreamWriter writer)
    {
        var result = new ListToolsResult
        {
            Tools = toolRegistry.GetToolDefinitions(),
        };
        SendResponse(writer, JsonRpcResponse.Success(request.Id, result));
    }

    private static void HandleToolsCall(JsonRpcRequest request, ToolRegistry toolRegistry, StreamWriter writer)
    {
        var callParams = JsonSerializer.Deserialize<CallToolParams>(
            request.Params?.GetRawText() ?? "{}", JsonOptions);

        if (callParams == null || string.IsNullOrEmpty(callParams.Name))
        {
            SendResponse(writer, JsonRpcResponse.Failure(request.Id, -32602, "Missing tool name"));
            return;
        }

        var result = toolRegistry.ExecuteTool(callParams.Name, callParams.Arguments);
        SendResponse(writer, JsonRpcResponse.Success(request.Id, result));
    }

    private static void HandleResourcesList(JsonRpcRequest request, ResourceRegistry registry, StreamWriter writer)
    {
        var result = new ListResourcesResult
        {
            Resources = registry.GetResources(),
        };
        SendResponse(writer, JsonRpcResponse.Success(request.Id, result));
    }

    private static void HandleResourcesRead(JsonRpcRequest request, ResourceRegistry registry, StreamWriter writer)
    {
        var readParams = JsonSerializer.Deserialize<ReadResourceParams>(
            request.Params?.GetRawText() ?? "{}", JsonOptions);

        if (readParams == null || string.IsNullOrEmpty(readParams.Uri))
        {
            SendResponse(writer, JsonRpcResponse.Failure(request.Id, -32602, "Missing resource URI"));
            return;
        }

        var resourceResult = registry.ReadResource(readParams.Uri);
        if (resourceResult == null)
        {
            SendResponse(writer, JsonRpcResponse.Failure(request.Id, -32602, $"Resource not found: {readParams.Uri}"));
            return;
        }

        SendResponse(writer, JsonRpcResponse.Success(request.Id, resourceResult));
    }

    private static void SendResponse(StreamWriter writer, JsonRpcResponse response)
    {
        var json = JsonSerializer.Serialize(response, JsonOptions);
        writer.WriteLine(json);
    }
}

/// <summary>
/// Registry for MCP resources (expose datasets as resources).
/// </summary>
public class ResourceRegistry
{
    private readonly string _dataDir;

    public ResourceRegistry(string dataDir) => _dataDir = dataDir;

    public List<ResourceDefinition> GetResources()
    {
        var kaggleDir = Path.Combine(_dataDir, "kaggle");
        if (!Directory.Exists(kaggleDir)) return new();

        return new List<ResourceDefinition>
        {
            new() { Uri = "csv://brasileirao_matches", Name = "Brasileirão Matches", Description = "Campeonato Brasileiro Série A matches", MimeType = "text/csv" },
            new() { Uri = "csv://brazilian_cup_matches", Name = "Copa do Brasil Matches", Description = "Copa do Brasil matches", MimeType = "text/csv" },
            new() { Uri = "csv://libertadores_matches", Name = "Copa Libertadores Matches", Description = "Copa Libertadores matches", MimeType = "text/csv" },
            new() { Uri = "csv://br_football_dataset", Name = "Brazilian Football Dataset", Description = "Extended match statistics", MimeType = "text/csv" },
            new() { Uri = "csv://novo_campeonato_brasileiro", Name = "Historical Brasileirão", Description = "Brasileirão matches 2003-2019", MimeType = "text/csv" },
            new() { Uri = "csv://fifa_players", Name = "FIFA Players", Description = "FIFA player database", MimeType = "text/csv" },
        };
    }

    public ReadResourceResult? ReadResource(string uri)
    {
        var fileName = uri.Replace("csv://", "") switch
        {
            "brasileirao_matches" => "Brasileirao_Matches.csv",
            "brazilian_cup_matches" => "Brazilian_Cup_Matches.csv",
            "libertadores_matches" => "Libertadores_Matches.csv",
            "br_football_dataset" => "BR-Football-Dataset.csv",
            "novo_campeonato_brasileiro" => "novo_campeonato_brasileiro.csv",
            "fifa_players" => "fifa_data.csv",
            _ => null,
        };

        if (fileName == null) return null;

        var filePath = Path.Combine(_dataDir, "kaggle", fileName);
        if (!File.Exists(filePath)) return null;

        // Read first 5000 lines of CSV for resource content
        var lines = File.ReadLines(filePath).Take(5000);
        var content = string.Join("\n", lines);

        return new ReadResourceResult
        {
            Contents = new List<ResourceContent>
            {
                new() { Uri = uri, MimeType = "text/csv", Text = content }
            }
        };
    }
}