using BrazilianSoccerMcp.Services;
using Xunit;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Shared fixture: loads all CSV data once per test collection.
/// </summary>
public sealed class DataFixture : IAsyncLifetime
{
    public DataRepository Repository { get; private set; } = null!;

    public async Task InitializeAsync()
    {
        var path = FindDataPath();
        Repository = new DataRepository(path);
        await Repository.LoadAsync();
    }

    public Task DisposeAsync() => Task.CompletedTask;

    private static string FindDataPath()
    {
        var dir = AppContext.BaseDirectory;
        for (int i = 0; i < 8; i++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate)) return candidate;
            var parent = Directory.GetParent(dir)?.FullName;
            if (parent == null) break;
            dir = parent;
        }
        throw new DirectoryNotFoundException(
            $"Cannot find 'data/kaggle' starting from {AppContext.BaseDirectory}");
    }
}

[CollectionDefinition("Data")]
public sealed class DataCollection : ICollectionFixture<DataFixture> { }
