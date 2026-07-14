using System.Text.Json;

namespace BrazilianSoccerMcp;

/// <summary>JSON Schema definitions for each MCP tool's input.</summary>
internal static class Schema
{
    private static JsonElement J(string json) =>
        JsonSerializer.Deserialize<JsonElement>(json);

    public static JsonElement NoArgs => J("""{"type":"object","properties":{}}""");

    public static JsonElement SearchMatches => J("""
        {"type":"object","properties":{
          "team":{"type":"string","description":"Team name (home, away, or either)"},
          "opponent":{"type":"string","description":"Opposing team to filter head-to-head"},
          "competition":{"type":"string","description":"Competition name (Brasileirão, Copa do Brasil, Libertadores)"},
          "season":{"type":"integer","description":"Season year"},
          "from_date":{"type":"string","description":"Start date (YYYY-MM-DD)"},
          "to_date":{"type":"string","description":"End date (YYYY-MM-DD)"},
          "limit":{"type":"integer","description":"Max results (default 100)"}
        }}
        """);

    public static JsonElement HeadToHead => J("""
        {"type":"object","required":["team_a","team_b"],"properties":{
          "team_a":{"type":"string"},"team_b":{"type":"string"}
        }}
        """);

    public static JsonElement LastMatch => J("""
        {"type":"object","properties":{
          "team":{"type":"string"},"opponent":{"type":"string"}
        }}
        """);

    public static JsonElement TeamStats => J("""
        {"type":"object","required":["team"],"properties":{
          "team":{"type":"string"},
          "venue":{"type":"string","description":"home or away"},
          "competition":{"type":"string"},
          "season":{"type":"integer"}
        }}
        """);

    public static JsonElement BestRecord => J("""
        {"type":"object","properties":{
          "competition":{"type":"string"},"season":{"type":"integer"}
        }}
        """);

    public static JsonElement SingleTeam => J("""
        {"type":"object","required":["team"],"properties":{"team":{"type":"string"}}}
        """);

    public static JsonElement BiggestWins => J("""
        {"type":"object","properties":{
          "competition":{"type":"string"},"season":{"type":"integer"},"limit":{"type":"integer"}
        }}
        """);

    public static JsonElement SearchPlayers => J("""
        {"type":"object","properties":{
          "name":{"type":"string"},"nationality":{"type":"string"},
          "club":{"type":"string"},"position":{"type":"string","description":"forward, midfielder, defender, goalkeeper, or a code like ST"},
          "min_overall":{"type":"integer"},"limit":{"type":"integer"}
        }}
        """);

    public static JsonElement TopPlayers => J("""
        {"type":"object","properties":{
          "limit":{"type":"integer"},"nationality":{"type":"string"},"club":{"type":"string"}
        }}
        """);

    public static JsonElement Standings => J("""
        {"type":"object","required":["competition","season"],"properties":{
          "competition":{"type":"string"},"season":{"type":"integer"}
        }}
        """);

    public static JsonElement Relegated => J("""
        {"type":"object","required":["competition","season"],"properties":{
          "competition":{"type":"string"},"season":{"type":"integer"},"count":{"type":"integer"}
        }}
        """);

    public static JsonElement Aggregate => J("""
        {"type":"object","properties":{
          "competition":{"type":"string"},"season":{"type":"integer"}
        }}
        """);

    public static JsonElement SeasonComparison => J("""
        {"type":"object","required":["competition","from_season","to_season"],"properties":{
          "competition":{"type":"string"},"from_season":{"type":"integer"},"to_season":{"type":"integer"}
        }}
        """);
}

internal static class JsonElementExtensions
{
    public static JsonElement? Get(this JsonElement el, string name) =>
        el.TryGetProperty(name, out var v) ? v : null;

    public static string GetStr(this JsonElement el, string name) =>
        el.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String
            ? v.GetString()!
            : throw new InvalidOperationException($"Missing required string argument '{name}'");

    public static int? GetInt(this JsonElement el, string name) =>
        el.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.Number
            ? v.GetInt32()
            : null;

    public static DateTime? GetDate(this JsonElement el, string name)
    {
        if (!el.TryGetProperty(name, out var v) || v.ValueKind != JsonValueKind.String)
            return null;
        return DateTime.TryParse(v.GetString(), out var d) ? d : null;
    }
}