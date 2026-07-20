using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>Feature: multi-format date parsing (ISO, ISO+time, Brazilian).</summary>
public class FlexibleDateParserTests
{
    [Theory]
    [InlineData("2012-05-19 18:30:00", 2012, 5, 19)]
    [InlineData("2023-09-24", 2023, 9, 24)]
    [InlineData("29/03/2003", 2003, 3, 29)]
    [InlineData("\"2012-05-19 18:30:00\"", 2012, 5, 19)]
    public void Given_KnownFormat_When_Parsing_Then_DateIsCorrect(string raw, int y, int m, int d)
    {
        // Given / When
        var parsed = FlexibleDateParser.Parse(raw);

        // Then
        Assert.NotNull(parsed);
        Assert.Equal(new DateTime(y, m, d).Date, parsed!.Value.Date);
    }

    [Theory]
    [InlineData("NA")]
    [InlineData("")]
    [InlineData("not a date")]
    [InlineData(null)]
    public void Given_InvalidOrMissing_When_Parsing_Then_ReturnsNull(string? raw)
    {
        // Given / When / Then
        Assert.Null(FlexibleDateParser.Parse(raw));
    }

    [Fact]
    public void Given_BrazilianFormat_When_Parsing_Then_DayAndMonthAreNotSwapped()
    {
        // Given (29/03 can only be dd/MM)
        var parsed = FlexibleDateParser.Parse("29/03/2003");

        // When / Then
        Assert.Equal(29, parsed!.Value.Day);
        Assert.Equal(3, parsed.Value.Month);
    }
}
