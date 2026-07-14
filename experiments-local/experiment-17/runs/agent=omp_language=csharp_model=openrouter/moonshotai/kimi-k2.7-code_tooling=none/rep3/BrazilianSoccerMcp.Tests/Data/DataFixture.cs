using BrazilianSoccerMcp.Server.Data;

namespace BrazilianSoccerMcp.Tests.Data;

public sealed class DataFixture : IDisposable
{
    public SoccerDataContext Context { get; }

    public DataFixture()
    {
        var dataDirectory = FindDataDirectory();
        Context = new DataLoader(dataDirectory).Load();
    }

    public void Dispose()
    {
    }

    private static string FindDataDirectory()
    {
        var assemblyDirectory = Path.GetDirectoryName(typeof(DataFixture).Assembly.Location)!;

        var publishedData = Path.Combine(assemblyDirectory, "data", "kaggle");
        if (Directory.Exists(publishedData))
        {
            return publishedData;
        }

        var repoData = Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
        if (Directory.Exists(repoData))
        {
            return repoData;
        }

        var parentRepoData = Path.Combine(Directory.GetCurrentDirectory(), "..", "data", "kaggle");
        if (Directory.Exists(parentRepoData))
        {
            return Path.GetFullPath(parentRepoData);
        }

        throw new DirectoryNotFoundException("Could not find data/kaggle directory for tests.");
    }
}

[CollectionDefinition("SoccerData")]
public sealed class SoccerDataCollection : ICollectionFixture<DataFixture>
{
}
