// =============================================================================
// Context
// -----------------------------------------------------------------------------
// File:    CsvReaderTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD unit tests for the RFC 4180 CSV reader covering quoting, escaped
//          quotes, embedded commas, a UTF-8 BOM and accented Portuguese text.
// =============================================================================

using BrazilianSoccer.Core.Csv;
using Xunit;

namespace BrazilianSoccer.Tests;

public sealed class CsvReaderTests
{
    [Fact]
    public void Given_QuotedFieldsWithCommas_When_Read_Then_FieldsAreSplitCorrectly()
    {
        // Given a CSV whose quoted fields contain commas and accents
        const string csv = "a,b,c\n\"Boavista, RJ\",\"São Paulo\",3\n";
        using var reader = new StringReader(csv);
        // When
        var rows = CsvReader.Read(reader).ToList();
        // Then
        Assert.Single(rows);
        Assert.Equal("Boavista, RJ", rows[0]["a"]);
        Assert.Equal("São Paulo", rows[0]["b"]);
        Assert.Equal("3", rows[0]["c"]);
    }

    [Fact]
    public void Given_EscapedQuotes_When_Read_Then_DoubleQuotesCollapse()
    {
        // Given a field with an escaped quote
        const string csv = "name\n\"He said \"\"hi\"\"\"\n";
        using var reader = new StringReader(csv);
        // When
        var rows = CsvReader.Read(reader).ToList();
        // Then
        Assert.Equal("He said \"hi\"", rows[0]["name"]);
    }

    [Fact]
    public void Given_LeadingBom_When_Read_Then_FirstHeaderIsClean()
    {
        // Given content prefixed with a UTF-8 BOM, as in fifa_data.csv
        const string csv = "\uFEFFID,Name\n1,Messi\n";
        using var reader = new StringReader(csv);
        // When
        var rows = CsvReader.Read(reader).ToList();
        // Then
        Assert.Equal("1", rows[0]["ID"]);
        Assert.Equal("Messi", rows[0]["Name"]);
    }

    [Fact]
    public void Given_TrailingRowWithoutNewline_When_Read_Then_LastRowIsIncluded()
    {
        const string csv = "a,b\n1,2";
        using var reader = new StringReader(csv);
        var rows = CsvReader.Read(reader).ToList();
        Assert.Single(rows);
        Assert.Equal("2", rows[0]["b"]);
    }
}
