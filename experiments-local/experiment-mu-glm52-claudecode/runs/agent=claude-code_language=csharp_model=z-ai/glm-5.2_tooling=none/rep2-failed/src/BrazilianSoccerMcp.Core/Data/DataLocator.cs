// BrazilianSoccerMcp.Core / Data / DataLocator.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. The CSVs live under data/kaggle/ at the
// repository root, but assemblies execute from bin/Debug/net10.0 (tests) or next
// to the server binary (server). A path-resolution helper keeps both consumers
// pointing at the same on-disk data without copying 11 MB of CSVs into every
// test output directory.
// Strategy:
//   1. If <paramref name="explicitRoot"/> is given, use it (server passes its own
//      output/data/kaggle path).
//   2. Otherwise walk upward from AppContext.BaseDirectory until we find a
//      directory containing "data/kaggle".
//   3. Fall back to the current working directory, then to a repo-root-relative
//      guess ("../../../../data/kaggle"). Throws if nothing resolves — failing
//      loud is better than silently returning zero rows.
// -----------------------------------------------------------------------------

using System.Runtime.CompilerServices;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>Resolves the path to the data/kaggle CSV directory.</summary>
public static class DataLocator
{
    public const string KaggleFolder = "data/kaggle";

    /// <summary>
    /// Returns the absolute path to the kaggle data folder, or throws if it cannot
    /// be located.
    /// </summary>
    public static string ResolveKagglePath(string? explicitRoot = null,
        [CallerFilePath] string sourceFile = "")
    {
        // 1. Explicit root wins.
        if (!string.IsNullOrWhiteSpace(explicitRoot) && Directory.Exists(explicitRoot))
            return Path.GetFullPath(explicitRoot);

        // 2. Walk upward from the assembly base directory.
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, KaggleFolder);
            if (Directory.Exists(candidate))
                return Path.GetFullPath(candidate);
            dir = dir.Parent;
        }

        // 3. Walk upward from the current working directory.
        dir = new DirectoryInfo(Environment.CurrentDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, KaggleFolder);
            if (Directory.Exists(candidate))
                return Path.GetFullPath(candidate);
            dir = dir.Parent;
        }

        // 4. Last-ditch: source-file-relative (used only when built from source).
        if (!string.IsNullOrEmpty(sourceFile))
        {
            var srcDir = Path.GetDirectoryName(sourceFile);
            for (int i = 0; i < 8 && srcDir is not null; i++)
            {
                var candidate = Path.Combine(srcDir, KaggleFolder);
                if (Directory.Exists(candidate))
                    return Path.GetFullPath(candidate);
                srcDir = Path.GetDirectoryName(srcDir);
            }
        }

        throw new DirectoryNotFoundException(
            $"Could not locate the '{KaggleFolder}' data directory. " +
            $"Searched from AppContext.BaseDirectory='{AppContext.BaseDirectory}', " +
            $"CWD='{Environment.CurrentDirectory}', and source file '{sourceFile}'. " +
            "Pass an explicit root via SoccerDataService(dataRoot) or place the data " +
            "folder at the repository root.");
    }

    /// <summary>Returns the absolute path to a named CSV inside the kaggle folder.</summary>
    public static string ResolveCsv(string fileName, string? explicitRoot = null)
        => Path.Combine(ResolveKagglePath(explicitRoot), fileName);

    /// <summary>Canonical file names used across the solution.</summary>
    public static class Files
    {
        public const string Brasileirao = "Brasileirao_Matches.csv";
        public const string CopaDoBrasil = "Brazilian_Cup_Matches.csv";
        public const string Libertadores = "Libertadores_Matches.csv";
        public const string Extended = "BR-Football-Dataset.csv";
        public const string HistoricalBrasileirao = "novo_campeonato_brasileiro.csv";
        public const string FifaPlayers = "fifa_data.csv";
    }
}
