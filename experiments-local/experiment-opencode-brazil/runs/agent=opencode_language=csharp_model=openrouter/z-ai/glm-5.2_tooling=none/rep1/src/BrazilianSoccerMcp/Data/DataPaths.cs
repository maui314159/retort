// Context block
// File: Data/DataPaths.cs
// Purpose: Locate the Kaggle CSV dataset directory for the Brazilian Soccer MCP server.
// The MCP server loads six CSV files from data/kaggle/. This helper walks upward from
// the application base directory until it finds a folder named "data" containing a
// "kaggle" subfolder, which lets the same code run from the repo root, build output,
// or test bin directories. A fallback path can also be supplied via the
// BRAZILIAN_SOCCER_DATA environment variable.
// Language: C# (.NET 10). Tested with xUnit BDD/GWT scenarios.
// Owner: Brazilian Soccer MCP benchmark implementation.

namespace BrazilianSoccerMcp.Data;

/// <summary>Resolves the path to the bundled Kaggle CSV datasets.</summary>
public static class DataPaths
{
    /// <summary>Environment variable used to override the data directory.</summary>
    public const string DataEnvVar = "BRAZILIAN_SOCCER_DATA";

    /// <summary>Subfolder that contains the CSV files.</summary>
    public const string KaggleSubfolder = "kaggle";

    /// <summary>File names of the six datasets described in TASK.md.</summary>
    public static class Files
    {
        public const string BrasileiraoMatches = "Brasileirao_Matches.csv";
        public const string BrazilianCupMatches = "Brazilian_Cup_Matches.csv";
        public const string LibertadoresMatches = "Libertadores_Matches.csv";
        public const string BrFootballDataset = "BR-Football-Dataset.csv";
        public const string HistoricBrasileirao = "novo_campeonato_brasileiro.csv";
        public const string FifaPlayers = "fifa_data.csv";
    }

    /// <summary>Locates the <c>data/kaggle</c> directory.</summary>
    /// <returns>Absolute path to the kaggle directory.</returns>
    /// <exception cref="DirectoryNotFoundException">Thrown when the data folder cannot be located.</exception>
    public static string ResolveKaggleDirectory()
    {
        var env = Environment.GetEnvironmentVariable(DataEnvVar);
        if (!string.IsNullOrWhiteSpace(env) && Directory.Exists(env))
        {
            return Path.Combine(env, KaggleSubfolder);
        }

        var current = AppContext.BaseDirectory;
        for (var depth = 0; depth < 10; depth++)
        {
            var candidate = Path.Combine(current, "data", KaggleSubfolder);
            if (Directory.Exists(candidate))
            {
                return Path.GetFullPath(candidate);
            }
            var parent = Directory.GetParent(current);
            if (parent is null)
            {
                break;
            }
            current = parent.FullName;
        }

        throw new DirectoryNotFoundException(
            "Could not locate the data/kaggle directory. Set the " + DataEnvVar +
            " environment variable to the absolute path of the 'data' folder.");
    }

    /// <summary>Returns the absolute path for a single CSV file.</summary>
    public static string ResolveCsvFile(string fileName)
    {
        return Path.Combine(ResolveKaggleDirectory(), fileName);
    }
}
