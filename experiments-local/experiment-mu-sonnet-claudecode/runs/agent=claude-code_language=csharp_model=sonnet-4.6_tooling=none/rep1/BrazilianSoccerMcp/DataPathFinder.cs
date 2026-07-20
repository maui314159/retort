namespace BrazilianSoccerMcp;

public static class DataPathFinder
{
    public static string FindKaggleDataPath()
    {
        var envPath = Environment.GetEnvironmentVariable("DATA_DIR");
        if (!string.IsNullOrEmpty(envPath) && Directory.Exists(envPath))
            return envPath;

        // Walk up from the current directory to find data/kaggle
        var current = Directory.GetCurrentDirectory();
        for (int i = 0; i < 8; i++)
        {
            var candidate = Path.Combine(current, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;

            var parent = Directory.GetParent(current);
            if (parent == null) break;
            current = parent.FullName;
        }

        // Also try relative to the assembly location
        var assemblyDir = Path.GetDirectoryName(typeof(DataPathFinder).Assembly.Location) ?? "";
        current = assemblyDir;
        for (int i = 0; i < 8; i++)
        {
            var candidate = Path.Combine(current, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;

            var parent = Directory.GetParent(current);
            if (parent == null) break;
            current = parent.FullName;
        }

        throw new DirectoryNotFoundException(
            "Could not find data/kaggle directory. Set DATA_DIR environment variable to the kaggle data path.");
    }
}
