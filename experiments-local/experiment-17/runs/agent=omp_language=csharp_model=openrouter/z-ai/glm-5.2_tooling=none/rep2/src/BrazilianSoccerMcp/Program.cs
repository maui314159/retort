using BrazilianSoccerMcp;

// Resolve the data directory: default to ./data/kaggle relative to the working
// directory, overridable via the SOCCER_DATA_DIR environment variable.
var dataDir = Environment.GetEnvironmentVariable("SOCCER_DATA_DIR")
    ?? Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");

if (!Directory.Exists(dataDir))
{
    Console.Error.WriteLine($"Data directory not found: {dataDir}");
    Console.Error.WriteLine("Set SOCCER_DATA_DIR to the path containing the CSV files.");
    Environment.Exit(1);
}

var tools = new SoccerTools(dataDir);
var server = new McpServer(tools);
server.Run();
