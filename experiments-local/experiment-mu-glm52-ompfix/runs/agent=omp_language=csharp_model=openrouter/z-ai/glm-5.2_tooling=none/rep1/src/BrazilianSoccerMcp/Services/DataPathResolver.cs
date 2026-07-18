// Brazilian Soccer MCP Server - Data directory resolution
//
// Context: The CSV datasets live at <repo-root>/data/kaggle/. When the MCP
// server runs over stdio its working directory is not guaranteed to be the repo
// root, and tests run from their own bin folder. This resolver walks upward
// from the assembly's base directory (the bin/... folder) until it finds a
// "data/kaggle" directory, so the datasets are located regardless of where the
// process was launched from.

namespace BrazilianSoccerMcp.Services;

/// <summary>Locates the bundled Kaggle datasets on disk.</summary>
public static class DataPathResolver
{
    private const string DataFolder = "data";
    private const string KaggleFolder = "kaggle";

    /// <summary>
    /// Finds the data/kaggle directory by searching from the assembly base
    /// directory upward, then falling back to the current working directory.
    /// </summary>
    /// <returns>The absolute path to the kaggle data directory.</returns>
    public static string ResolveDataDirectory()
    {
        var candidates = new List<string>();

        // Walk upward from the bin output folder.
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var d = dir; d is not null; d = d.Parent)
        {
            candidates.Add(Path.Combine(d.FullName, DataFolder, KaggleFolder));
            candidates.Add(Path.Combine(d.FullName, KaggleFolder));
        }

        // Also try the current working directory and a relative path.
        candidates.Add(Path.Combine(Environment.CurrentDirectory, DataFolder, KaggleFolder));
        candidates.Add(Path.Combine(Directory.GetCurrentDirectory(), DataFolder, KaggleFolder));

        foreach (var candidate in candidates.Distinct())
        {
            if (Directory.Exists(candidate))
                return Path.GetFullPath(candidate);
        }

        // As a last resort return the most likely relative path so the caller
        // can produce a clear "file not found" error.
        return Path.GetFullPath(Path.Combine(DataFolder, KaggleFolder));
    }
}
