// Brazilian Soccer MCP Server - Data directory locator
// Context: The server can be launched from the repo root (so "data/kaggle" is a
// relative path) or from its published bin directory (so the data lives several
// directories up). This locator walks upward from both the current working
// directory and the assembly base directory looking for a folder containing
// "Brasileirao_Matches.csv", which is the canonical marker that we've found the
// bundled dataset. Falls back to a relative "data/kaggle" if nothing matches.

namespace BrazilianSoccerMcp.Data;

/// <summary>Locates the bundled Kaggle data directory at runtime.</summary>
public static class DataLocator
{
    public static string FindDataDirectory()
    {
        var candidates = new List<string>
        {
            Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle"),
        };

        // Walk upward from the assembly base directory.
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (int i = 0; i < 8 && dir != null; i++)
        {
            candidates.Add(Path.Combine(dir.FullName, "data", "kaggle"));
            dir = dir.Parent;
        }

        // Also walk upward from the current working directory.
        dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        for (int i = 0; i < 6 && dir != null; i++)
        {
            candidates.Add(Path.Combine(dir.FullName, "data", "kaggle"));
            dir = dir.Parent;
        }

        foreach (var c in candidates.Distinct())
        {
            if (File.Exists(Path.Combine(c, "Brasileirao_Matches.csv")))
                return c;
        }

        // Last-resort fallback: assume relative path from cwd.
        return Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
    }
}
