// BrazilianSoccerMcp.Tests - shared test fixture base.
// All BDD feature classes derive from this to get a single lazily-loaded
// BrazilianSoccerData instance pointing at the repo's data/kaggle directory.
// Loading ~42k CSV rows once keeps the test suite fast.
using BrazilianSoccerMcp.Core;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Services;
using LightBDD.XUnit2;

namespace BrazilianSoccerMcp.Tests;

/// <summary>Base class providing access to the loaded datasets and shared fields.</summary>
public abstract class SoccerFeatureFixture : FeatureFixture
{
    private static readonly Lazy<BrazilianSoccerData> _data = new(LoadData);

    protected SoccerFeatureFixture()
    {
        Data = _data.Value;
        Query = Data.Query;
    }

    protected BrazilianSoccerData Data { get; }
    protected SoccerQueryService Query { get; }

    // Per-scenario scratch state used by the step methods.
    protected IReadOnlyList<Match> ResultMatches = Array.Empty<Match>();
    protected Match? ResultMatch;
    protected TeamStats? ResultStats;
    protected HeadToHead? ResultH2H;
    protected IReadOnlyList<StandingsRow> ResultStandings = Array.Empty<StandingsRow>();
    protected IReadOnlyList<Player> ResultPlayers = Array.Empty<Player>();
    protected double ResultDouble;
    protected (double Home, double Draw, double Away) ResultRates;
    protected string ResultText = "";

    private static BrazilianSoccerData LoadData()
    {
        var dir = ResolveDataDir();
        return new BrazilianSoccerData(dir);
    }

    private static string ResolveDataDir()
    {
        // Walk up from the test bin directory until we find data/kaggle.
        var dir = AppContext.BaseDirectory;
        for (int i = 0; i < 8; i++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate)) return candidate;
            var parent = Directory.GetParent(dir)?.FullName;
            if (parent is null) break;
            dir = parent;
        }
        // Fall back to the environment variable set by the smoke tests.
        return Environment.GetEnvironmentVariable("BSOCCER_DATA")
               ?? Path.Combine(Directory.GetCurrentDirectory(), "data", "kaggle");
    }
}
