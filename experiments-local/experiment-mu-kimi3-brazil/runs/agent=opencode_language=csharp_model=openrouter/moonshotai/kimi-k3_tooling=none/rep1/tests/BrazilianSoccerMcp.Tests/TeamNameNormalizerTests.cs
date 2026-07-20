using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>
/// Unit tests for team-name normalization: state suffixes, accents, club prefixes
/// and full official names must all resolve to one canonical name.
/// </summary>
public class TeamNameNormalizerTests
{
    [Theory]
    [InlineData("Palmeiras-SP", "Palmeiras")]
    [InlineData("SE Palmeiras", "Palmeiras")]
    [InlineData("palmeiras", "Palmeiras")]
    [InlineData("Flamengo-RJ", "Flamengo")]
    [InlineData("CR Flamengo", "Flamengo")]
    [InlineData("Sao Paulo-SP", "São Paulo")]
    [InlineData("São Paulo FC", "São Paulo")]
    [InlineData("Gremio-RS", "Grêmio")]
    [InlineData("Grêmio FBPA", "Grêmio")]
    [InlineData("Sport Club Corinthians Paulista", "Corinthians")]
    [InlineData("Corinthians-SP", "Corinthians")]
    [InlineData("Vasco da Gama-RJ", "Vasco da Gama")]
    [InlineData("Vasco", "Vasco da Gama")]
    [InlineData("Sport-PE", "Sport Recife")]
    [InlineData("Sport Club do Recife", "Sport Recife")]
    [InlineData("America-MG", "América Mineiro")]
    [InlineData("América - MG", "América Mineiro")]
    [InlineData("EC Juventude", "Juventude")]
    [InlineData("Juventude-RS", "Juventude")]
    [InlineData("Red Bull Bragantino-SP", "Red Bull Bragantino")]
    [InlineData("Avai-SC", "Avaí")]
    public void CanonicalName_NameVariations_ResolveToCanonical(string raw, string expected) =>
        Assert.Equal(expected, TeamNameNormalizer.CanonicalName(raw));

    [Theory]
    // The "Atletico" stem is ambiguous; the state suffix must disambiguate.
    [InlineData("Atletico-MG", "Atlético Mineiro")]
    [InlineData("Atlético - MG", "Atlético Mineiro")]
    [InlineData("Clube Atlético Mineiro", "Atlético Mineiro")]
    [InlineData("Atletico-PR", "Athletico Paranaense")]
    [InlineData("Athletico-PR", "Athletico Paranaense")]
    [InlineData("Atlético Paranaense - PR", "Athletico Paranaense")]
    [InlineData("Atletico-GO", "Atlético Goianiense")]
    public void CanonicalName_AmbiguousAtleticoStem_StateSuffixDisambiguates(string raw, string expected) =>
        Assert.Equal(expected, TeamNameNormalizer.CanonicalName(raw));

    [Fact]
    public void CanonicalName_LongOfficialNameWithParenthetical_Resolves()
    {
        // Given the most decorated name variant in the Copa do Brasil file
        var raw = "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ";

        // When canonicalizing
        var canonical = TeamNameNormalizer.CanonicalName(raw);

        // Then it resolves to Boavista
        Assert.Equal("Boavista", canonical);
    }

    [Fact]
    public void CanonicalName_ForeignClubWithCountrySuffix_StripsSuffix()
    {
        // Given a Libertadores foreign club with a country tag
        Assert.Equal("Nacional", TeamNameNormalizer.CanonicalName("Nacional (URU)"));
        Assert.Equal("Barcelona", TeamNameNormalizer.CanonicalName("Barcelona-EQU"));
    }

    [Fact]
    public void CanonicalName_UnknownTeam_FallsBackToCleanedName()
    {
        // Given a team missing from the alias table
        var canonical = TeamNameNormalizer.CanonicalName("Tupi");

        // Then the cleaned raw name is returned unchanged
        Assert.Equal("Tupi", canonical);
    }

    [Theory]
    [InlineData("Flamengo-RJ", "flamengo", true)]
    [InlineData("Flamengo-RJ", "Fluminense-RJ", false)]
    [InlineData("São Paulo", "Sao Paulo-SP", true)]
    [InlineData("Atletico-MG", "Atletico-PR", false)]
    [InlineData("", "Flamengo", false)]
    public void SameTeam_ComparesCanonicalForms(string a, string b, bool expected) =>
        Assert.Equal(expected, TeamNameNormalizer.SameTeam(a, b));

    [Fact]
    public void NormalizeKey_HandlesAccentsAndCase() =>
        Assert.Equal(TeamNameNormalizer.NormalizeKey("Grêmio"),
                     TeamNameNormalizer.NormalizeKey("GREMIO"));
}
