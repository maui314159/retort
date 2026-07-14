// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    DatasetFixture.cs
// Project: BrazilianSoccer.Tests
// Purpose: xUnit collection fixture that loads the real Kaggle CSVs once and
//          shares the resulting QueryService across the integration-style BDD
//          tests, so the (multi-second) load happens a single time per run.
// =============================================================================

using BrazilianSoccer.Core.Data;
using BrazilianSoccer.Core.Queries;
using Xunit;

namespace BrazilianSoccer.Tests;

public sealed class DatasetFixture
{
    public SoccerDataset Data { get; }
    public QueryService Query { get; }

    public DatasetFixture()
    {
        var dir = DataLoader.LocateDataDirectory();
        Data = new DataLoader(dir).Load();
        Query = new QueryService(Data);
    }
}

[CollectionDefinition("dataset")]
public sealed class DatasetCollection : ICollectionFixture<DatasetFixture>;
