using BrazilianSoccerMcp.Services;

namespace BrazilianSoccerMcp.Tests;

public class TeamNameNormalizerTests
{
    // Normalize() keeps the state suffix — it's the grouping key
    [Theory]
    [InlineData("Palmeiras-SP",  "palmeiras-sp")]
    [InlineData("Flamengo-RJ",   "flamengo-rj")]
    [InlineData("Atletico-MG",   "atletico-mg")]
    [InlineData("Atletico-PR",   "atletico-pr")]
    public void Normalize_KeepsStateSuffix(string input, string expected)
        => Assert.Equal(expected, TeamNameNormalizer.Normalize(input));

    // NormalizeForSearch() strips the state suffix — used for user queries & dedup
    [Theory]
    [InlineData("Palmeiras-SP",  "palmeiras")]
    [InlineData("Flamengo-RJ",   "flamengo")]
    [InlineData("Atletico-MG",   "atletico")]
    [InlineData("Atletico-PR",   "atletico")]
    public void NormalizeForSearch_StripsStateSuffix(string input, string expected)
        => Assert.Equal(expected, TeamNameNormalizer.NormalizeForSearch(input));

    // Both methods strip accents
    [Theory]
    [InlineData("São Paulo",  "sao paulo")]
    [InlineData("Grêmio",     "gremio")]
    [InlineData("Atlético",   "atletico")]
    [InlineData("Fortaleza",  "fortaleza")]
    public void StripAccents(string input, string expected)
        => Assert.Equal(expected, TeamNameNormalizer.NormalizeForSearch(input));

    // Parenthetical qualifiers are stripped
    [Fact]
    public void StripParenthesisQualifier()
    {
        var result = TeamNameNormalizer.NormalizeForSearch(
            "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ");
        Assert.Equal("boavista sport club", result);
    }

    // Matches(query, groupingKey): query "flamengo" should match groupingKey "flamengo-rj"
    [Theory]
    [InlineData("Flamengo",   "flamengo",    true)]
    [InlineData("Flamengo",   "flamengo-rj", true)]   // state-suffix on key stripped before compare
    [InlineData("Palmeiras",  "palmeiras",   true)]
    [InlineData("Santos",     "flamengo",    false)]
    [InlineData("Atletico",   "atletico-mg", true)]   // user "Atletico" matches any state variant
    [InlineData("Atletico",   "atletico-pr", true)]
    public void MatchesQuery(string query, string groupingKey, bool expected)
        => Assert.Equal(expected, TeamNameNormalizer.Matches(query, groupingKey));

    // Different state teams do NOT produce the same grouping key
    [Fact]
    public void AtleticoMgAndPrHaveDifferentKeys()
    {
        Assert.NotEqual(
            TeamNameNormalizer.Normalize("Atletico-MG"),
            TeamNameNormalizer.Normalize("Atletico-PR"));
    }
}
