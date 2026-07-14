namespace BrazilianSoccerMcp.Models;

/// <summary>
/// Player record from fifa_data.csv (18 207 rows).
/// Only the columns needed for queries are loaded.
/// </summary>
public sealed record FifaPlayer
{
    public int    SofifaId    { get; init; }
    public string Name        { get; init; } = "";
    public int    Age         { get; init; }
    public string Nationality { get; init; } = "";
    public int    Overall     { get; init; }
    public int    Potential   { get; init; }
    public string Club        { get; init; } = "";
    public string Position    { get; init; } = "";
    public int?   JerseyNumber { get; init; }
    public string Height      { get; init; } = "";
    public string Weight      { get; init; } = "";

    // Pre-normalised keys for matching
    public string NameKey        { get; init; } = "";
    public string NationalityKey { get; init; } = "";
    public string ClubKey        { get; init; } = "";
}
