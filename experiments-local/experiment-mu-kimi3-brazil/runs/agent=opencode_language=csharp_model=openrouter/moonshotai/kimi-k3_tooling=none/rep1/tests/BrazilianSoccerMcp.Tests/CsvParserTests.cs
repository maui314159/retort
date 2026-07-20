using BrazilianSoccerMcp.Data;

namespace BrazilianSoccerMcp.Tests;

/// <summary>Unit tests for the RFC-4180 CSV parser.</summary>
public class CsvParserTests
{
    [Fact]
    public void Parse_SimpleUnquotedRows_SplitsOnCommas()
    {
        // Given a plain CSV document
        using var reader = new StringReader("a,b,c\n1,2,3\n");

        // When parsing rows
        var rows = CsvParser.ReadRows(reader).ToList();

        // Then every cell is split on commas
        Assert.Equal([["a", "b", "c"], ["1", "2", "3"]], rows);
    }

    [Fact]
    public void Parse_QuotedFieldWithComma_KeepsCommaInsideField()
    {
        // Given a row with a quoted comma
        using var reader = new StringReader("10,\"Jul 1, 2004\",2021\n");

        // When parsing
        var rows = CsvParser.ReadRows(reader).ToList();

        // Then the quoted comma does not split the field
        Assert.Single(rows);
        Assert.Equal(["10", "Jul 1, 2004", "2021"], rows[0]);
    }

    [Fact]
    public void Parse_EscapedQuotesInsideQuotedField_UnescapesThem()
    {
        // Given doubled quotes inside a quoted field
        using var reader = new StringReader("\"He said \"\"gol\"\" loudly\",x\n");

        // When parsing
        var rows = CsvParser.ReadRows(reader).ToList();

        // Then the quotes are unescaped
        Assert.Equal("He said \"gol\" loudly", rows[0][0]);
        Assert.Equal("x", rows[0][1]);
    }

    [Fact]
    public void Parse_CrlfLineEndings_ToleratesCarriageReturn()
    {
        // Given Windows line endings
        using var reader = new StringReader("a,b\r\n1,2\r\n");

        // When parsing
        var rows = CsvParser.ReadRows(reader).ToList();

        // Then no stray \r remains in cells
        Assert.Equal([["a", "b"], ["1", "2"]], rows);
    }

    [Fact]
    public void Parse_QuotedUtf8Accents_PreservesCharacters()
    {
        // Given Brazilian Portuguese special characters
        using var reader = new StringReader("\"Grêmio-RS\",\"São Paulo-SP\",\"Avaí\"\n");

        // When parsing
        var rows = CsvParser.ReadRows(reader).ToList();

        // Then UTF-8 content survives intact
        Assert.Equal(["Grêmio-RS", "São Paulo-SP", "Avaí"], rows[0]);
    }

    [Fact]
    public void Parse_TrailingEmptyField_YieldsEmptyString()
    {
        // Given a row ending with an empty cell
        using var reader = new StringReader("a,b,\n");

        // When parsing
        var rows = CsvParser.ReadRows(reader).ToList();

        // Then the trailing empty cell is preserved
        Assert.Equal(["a", "b", ""], rows[0]);
    }

    [Fact]
    public void Parse_NoTrailingNewline_StillYieldsLastRow()
    {
        // Given a file whose last line has no newline
        using var reader = new StringReader("a,b\n1,2");

        // When parsing
        var rows = CsvParser.ReadRows(reader).ToList();

        // Then the final row is still returned
        Assert.Equal(2, rows.Count);
        Assert.Equal(["1", "2"], rows[1]);
    }
}
