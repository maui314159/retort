// Brazilian Soccer MCP Server - BDD test fixture
// Context: xUnit collection fixture that loads the real bundled Kaggle datasets
// exactly once for the whole test run and shares the SoccerQueryService across
// every test class in the collection. Tests assert behaviour against the actual
// data (e.g. Flamengo's 90-point 2019 Brasileirão title, Neymar Jr's 92 overall)
// rather than mocked inputs, so a green run proves the loader, normaliser and
// query engine all work end-to-end against the real CSVs.

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

/// <summary>Shared fixture holding the lazily-loaded query service.</summary>
public sealed class SoccerDataFixture
{
    public SoccerQueryService Service { get; } = new SoccerQueryService();

    public string DataDirectory => DataLocator.FindDataDirectory();
}

/// <summary>Links test classes to the shared <see cref="SoccerDataFixture"/>.</summary>
[CollectionDefinition("Soccer data")]
public sealed class SoccerDataCollection : ICollectionFixture<SoccerDataFixture> { }
