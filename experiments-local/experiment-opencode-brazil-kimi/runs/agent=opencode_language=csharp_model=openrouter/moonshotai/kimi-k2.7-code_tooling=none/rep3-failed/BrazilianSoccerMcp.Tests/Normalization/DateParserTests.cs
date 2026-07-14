// <copyright file="DateParserTests.cs" company="BrazilianSoccerMcp">
// Brazilian Soccer MCP Server - Tests for date parsing from multiple formats.
// </copyright>
using BrazilianSoccerMcp.Core.Normalization;
using FluentAssertions;

namespace BrazilianSoccerMcp.Tests.Normalization;

public class DateParserTests
{
    [Theory]
    [InlineData("2012-05-19 18:30:00", 2012, 5, 19)]
    [InlineData("2023-09-24", 2023, 9, 24)]
    [InlineData("29/03/2003", 2003, 3, 29)]
    public void Parse_HandlesKnownFormats(string raw, int year, int month, int day)
    {
        var date = DateParser.Parse(raw);

        date.Should().NotBeNull();
        date!.Value.Year.Should().Be(year);
        date.Value.Month.Should().Be(month);
        date.Value.Day.Should().Be(day);
    }

    [Fact]
    public void Parse_ReturnsNullForEmptyString()
    {
        DateParser.Parse(string.Empty).Should().BeNull();
        DateParser.Parse(null).Should().BeNull();
    }
}
