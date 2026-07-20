// =============================================================================
// File: BrazilianSoccerMcp.Tests/DatabaseFixture.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server — test support.
//   xUnit collection fixture that builds the SoccerDatabase once for the whole
//   test assembly. Loading the six Kaggle CSVs (~35k matches + 18k players)
//   is expensive enough that we do not want to repeat it per test.
// =============================================================================
namespace BrazilianSoccerMcp.Tests;

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Query;
using Xunit;

public sealed class DatabaseFixture
{
    public SoccerDatabase Database { get; }
    public MatchQueryService Matches { get; }
    public TeamQueryService Teams { get; }
    public PlayerQueryService Players { get; }
    public CompetitionQueryService Competitions { get; }
    public StatisticsService Stats { get; }

    public DatabaseFixture()
    {
        Database = new SoccerDatabase();
        Matches = new MatchQueryService(Database);
        Teams = new TeamQueryService(Database, Matches);
        Players = new PlayerQueryService(Database);
        Competitions = new CompetitionQueryService(Database);
        Stats = new StatisticsService(Database);
    }
}

[CollectionDefinition("Soccer")]
public sealed class SoccerCollection : ICollectionFixture<DatabaseFixture> { }
