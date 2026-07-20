using System.Text;
using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>Feature: CSV parsing foundation (quotes, BOMs, encodings).</summary>
public class CsvParserTests
{
    private static CsvParser.CsvTable ParseString(string content)
    {
        using var stream = new MemoryStream(Encoding.UTF8.GetBytes(content));
        return CsvParser.Parse(stream);
    }

    [Fact]
    public void Given_QuotedFieldWithComma_When_Parsing_Then_CommaStaysInsideField()
    {
        // Given
        var csv = "name,joined\nL. Messi,\"Jul 1, 2004\"\n";

        // When
        var table = ParseString(csv);

        // Then
        Assert.Equal(new[] { "name", "joined" }, table.Headers);
        Assert.Single(table.Rows);
        Assert.Equal("L. Messi", table.Rows[0][0]);
        Assert.Equal("Jul 1, 2004", table.Rows[0][1]);
    }

    [Fact]
    public void Given_DoubledQuotes_When_Parsing_Then_TheyBecomeLiteralQuotes()
    {
        // Given
        var csv = "a,b\n\"say \"\"hi \"\"\",\"x\"\n";

        // When
        var table = ParseString(csv);

        // Then
        Assert.Equal("say \"hi \"", table.Rows[0][0]);
        Assert.Equal("x", table.Rows[0][1]);
    }

    [Fact]
    public void Given_Utf8BomAndAccents_When_Parsing_Then_HeaderIsCleanAndAccentsPreserved()
    {
        // Given (BOM + São Paulo/Grêmio accents, as in the real files)
        var bytes = Encoding.UTF8.GetPreamble()
            .Concat(Encoding.UTF8.GetBytes("team,city\nGrêmio,Porto Alegre\nSão Paulo,São Paulo\n"))
            .ToArray();
        using var stream = new MemoryStream(bytes);

        // When
        var table = CsvParser.Parse(stream);

        // Then
        Assert.Equal("team", table.Headers[0]);
        Assert.Equal("Grêmio", table.Rows[0][0]);
        Assert.Equal("São Paulo", table.Rows[1][0]);
    }

    [Fact]
    public void Given_FileWithoutTrailingNewline_When_Parsing_Then_LastRowIsKept()
    {
        // Given
        var csv = "a,b\n1,2\n3,4";

        // When
        var table = ParseString(csv);

        // Then
        Assert.Equal(2, table.Rows.Count);
        Assert.Equal("4", table.Rows[1][1]);
    }

    [Fact]
    public void Given_CrlfLineEndings_When_Parsing_Then_NoCarriageReturnsLeak()
    {
        // Given
        var csv = "a,b\r\n1,2\r\n";

        // When
        var table = ParseString(csv);

        // Then
        Assert.Single(table.Rows);
        Assert.Equal("2", table.Rows[0][1]);
    }
}
