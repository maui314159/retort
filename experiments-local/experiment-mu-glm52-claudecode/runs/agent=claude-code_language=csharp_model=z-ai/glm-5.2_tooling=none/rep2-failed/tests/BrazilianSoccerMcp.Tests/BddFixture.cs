// BrazilianSoccerMcp.Tests / BddFixture.cs
// -----------------------------------------------------------------------------
// Context: BDD test scaffolding for the Brazilian Soccer MCP server. The data load
// (six CSVs, ~24k matches + 18k players) is expensive, so all tests share one
// SoccerDataService via an xUnit collection fixture. The Gherkin scenarios in
// TASK.md ("Testing Approach") translate into Given/When/Then-structured [Fact]
// methods, one per scenario.
// The Gwt helper is intentionally lightweight — it records the human-readable step
// so a failing assertion reports the scenario outline, while keeping assertions as
// plain xUnit calls for debugger-friendliness.
// -----------------------------------------------------------------------------

using BrazilianSoccerMcp.Core.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Loads the SoccerDataService once and shares it across every BDD scenario in
/// the collection. The data path is resolved the same way the server resolves it
/// (walk-up to data/kaggle), so tests run from the test bin directory.
/// </summary>
public sealed class SoccerDataFixture : IDisposable
{
    public SoccerDataService Data { get; }

    public SoccerDataFixture()
    {
        Data = new SoccerDataService();
        // Touch Matches to force the lazy load here so a load failure fails the
        // fixture construction (and surfaces clearly) rather than every test.
        _ = Data.Matches.Count;
    }

    public void Dispose() { }
}

[CollectionDefinition("SoccerData")]
public sealed class SoccerDataCollection : ICollectionFixture<SoccerDataFixture> { }

/// <summary>
/// Records Given/When/Then step text for scenario readability. Purely cosmetic —
/// assertions remain plain xUnit so they're debuggable.
/// </summary>
internal static class Gwt
{
    public static string Given(string step) => $"GIVEN {step}";
    public static string When(string step) => $"WHEN  {step}";
    public static string Then(string step) => $"THEN  {step}";
    public static string And(string step) => $"AND   {step}";
}
