// ============================================================================
// File: Tests/TestFixture.cs
// ----------------------------------------------------------------------------
// Context: Shared xUnit collection fixture that loads the SoccerDataStore once
// for the whole test run (loading 30MB of CSVs per test would be far too slow).
// All test classes take this fixture via [Collection("Store")].
// ============================================================================

using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

public sealed class StoreFixture
{
    public SoccerDataStore Store { get; }

    public StoreFixture()
    {
        // SoccerDataStore resolves data/kaggle via DataPaths.FindDataDir(),
        // walking up from the test bin directory to the repo root.
        Store = new SoccerDataStore();
    }
}

[CollectionDefinition("Store")]
public sealed class StoreCollection : ICollectionFixture<StoreFixture> { }
