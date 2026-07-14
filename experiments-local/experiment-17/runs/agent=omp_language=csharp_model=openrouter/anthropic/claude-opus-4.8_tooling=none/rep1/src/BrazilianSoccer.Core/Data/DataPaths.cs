// -----------------------------------------------------------------------------
// File: Data/DataPaths.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Locates the data/kaggle directory at runtime. The CSVs live alongside the
//   repository root (data/kaggle/*.csv), but the server binary runs from
//   src/BrazilianSoccer.Server/bin/<cfg>/net10.0 and the test host from its own
//   bin directory, so a hard-coded relative path is fragile.
//
//   Resolution order:
//     1. BRAZILIAN_SOCCER_DATA env var, if set (explicit override for deployment).
//     2. Walk upward from the current directory and from the executing assembly's
//        directory looking for a folder that contains data/kaggle with the
//        expected CSV files.
//   Throwing early with a clear message beats silently loading zero rows.
// -----------------------------------------------------------------------------

using System.Reflection;

namespace BrazilianSoccer.Core.Data;

/// <summary>Resolves the on-disk location of the bundled Kaggle datasets.</summary>
public static class DataPaths
{
    /// <summary>Environment variable that, when set, points directly at the kaggle data dir.</summary>
    public const string OverrideEnvVar = "BRAZILIAN_SOCCER_DATA";

    private const string MarkerFile = "Brasileirao_Matches.csv";

    /// <summary>
    /// Returns the absolute path to the directory holding the kaggle CSV files.
    /// </summary>
    /// <exception cref="DirectoryNotFoundException">
    /// Thrown when the data directory cannot be located.
    /// </exception>
    public static string Resolve()
    {
        var overridePath = Environment.GetEnvironmentVariable(OverrideEnvVar);
        if (!string.IsNullOrWhiteSpace(overridePath))
        {
            if (File.Exists(Path.Combine(overridePath, MarkerFile)))
                return Path.GetFullPath(overridePath);
            throw new DirectoryNotFoundException(
                $"{OverrideEnvVar}='{overridePath}' does not contain {MarkerFile}.");
        }

        foreach (var start in EnumerateStartDirectories())
        {
            var found = SearchUpward(start);
            if (found is not null)
                return found;
        }

        throw new DirectoryNotFoundException(
            $"Could not locate data/kaggle/{MarkerFile}. Set the {OverrideEnvVar} " +
            "environment variable to the directory containing the Kaggle CSV files.");
    }

    private static IEnumerable<string> EnumerateStartDirectories()
    {
        yield return Directory.GetCurrentDirectory();

        var asmDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        if (!string.IsNullOrEmpty(asmDir))
            yield return asmDir;

        var baseDir = AppContext.BaseDirectory;
        if (!string.IsNullOrEmpty(baseDir))
            yield return baseDir;
    }

    private static string? SearchUpward(string start)
    {
        var dir = new DirectoryInfo(start);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "data", "kaggle");
            if (File.Exists(Path.Combine(candidate, MarkerFile)))
                return candidate;
            dir = dir.Parent;
        }
        return null;
    }
}
