// =============================================================================
// File: Data/MatchLoader.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP Server.
//   Loads every match CSV file into a single List<MatchRecord>, assigning:
//     - a canonical Competition bucket
//     - a SourceFile provenance tag
//     - parsed Date / Season
//     - normalized home/away team keys (TeamNameNormalizer)
//
// File → Competition bucket mapping:
//   Brasileirao_Matches.csv        -> "Brasileirão"  (Serie A, 2012-present)
//   novo_campeonato_brasileiro.csv -> "Brasileirão"  (Serie A, 2003-2019)
//   Brazilian_Cup_Matches.csv      -> "Copa do Brasil"
//   Libertadores_Matches.csv       -> "Libertadores"
//   BR-Football-Dataset.csv        -> per-row: tournament column drives bucket:
//         "Serie A"        -> "Brasileirão"
//         "Copa do Brasil" -> "Copa do Brasil"
//         "Serie B"/"Serie C" -> kept verbatim as their own buckets
//
// Goal values are coerced from the raw strings (which can be "2", "2.0", "")
// and are dropped to null when missing/empty so partial/void matches are
// still indexable by team/competition but excluded from result math.
// =============================================================================
namespace BrazilianSoccerMcp.Data;

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using BrazilianSoccerMcp.Csv;
using BrazilianSoccerMcp.Models;

public static class MatchLoader
{
    public const string Brasileirao = "Brasileirão";
    public const string CopaDoBrasil = "Copa do Brasil";
    public const string Libertadores = "Libertadores";

    public static List<MatchRecord> LoadAll(string dataDir)
    {
        var matches = new List<MatchRecord>(24_000);
        LoadBrasileirao(Path.Combine(dataDir, "Brasileirao_Matches.csv"), matches);
        LoadBrazilianCup(Path.Combine(dataDir, "Brazilian_Cup_Matches.csv"), matches);
        LoadLibertadores(Path.Combine(dataDir, "Libertadores_Matches.csv"), matches);
        LoadBrFootball(Path.Combine(dataDir, "BR-Football-Dataset.csv"), matches);
        LoadHistoricalBrasileirao(Path.Combine(dataDir, "novo_campeonato_brasileiro.csv"), matches);
        return matches;
    }

    // ---- per-file loaders -------------------------------------------------

    private static void LoadBrasileirao(string path, List<MatchRecord> sink)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        for (int i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 9) continue;
            var m = new MatchRecord
            {
                SourceFile = "Brasileirao_Matches.csv",
                Competition = Brasileirao,
                Date = MatchDateParser.TryParse(r[0]),
                HomeTeam = r[1].Trim('"').Trim(),
                HomeTeamState = NullIfBlank(r[2]),
                AwayTeam = r[3].Trim('"').Trim(),
                AwayTeamState = NullIfBlank(r[4]),
                HomeGoal = TryParseInt(r[5]),
                AwayGoal = TryParseInt(r[6]),
                Season = MatchDateParser.TryParseSeason(r[7]),
                Round = NullIfBlank(r[8]),
            };
            FinalizeRecord(m);
            sink.Add(m);
        }
    }

    private static void LoadBrazilianCup(string path, List<MatchRecord> sink)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        for (int i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 7) continue;
            var m = new MatchRecord
            {
                SourceFile = "Brazilian_Cup_Matches.csv",
                Competition = CopaDoBrasil,
                Round = NullIfBlank(r[0]),
                Date = MatchDateParser.TryParse(r[1]),
                HomeTeam = r[2].Trim(),
                AwayTeam = r[3].Trim(),
                HomeGoal = TryParseInt(r[4]),
                AwayGoal = TryParseInt(r[5]),
                Season = MatchDateParser.TryParseSeason(r[6]),
            };
            FinalizeRecord(m);
            sink.Add(m);
        }
    }

    private static void LoadLibertadores(string path, List<MatchRecord> sink)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        for (int i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 7) continue;
            var m = new MatchRecord
            {
                SourceFile = "Libertadores_Matches.csv",
                Competition = Libertadores,
                Date = MatchDateParser.TryParse(r[0]),
                HomeTeam = r[1].Trim(),
                AwayTeam = r[2].Trim(),
                HomeGoal = TryParseInt(r[3]),
                AwayGoal = TryParseInt(r[4]),
                Season = MatchDateParser.TryParseSeason(r[5]),
                Stage = NullIfBlank(r[6]),
            };
            FinalizeRecord(m);
            sink.Add(m);
        }
    }

    private static void LoadBrFootball(string path, List<MatchRecord> sink)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        // Header: tournament,home,home_goal,away_goal,away,home_corner,
        //         away_corner,home_attack,away_attack,home_shots,away_shots,
        //         time,date,ht_diff,at_diff,ht_result,at_result,total_corners
        for (int i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 5) continue;
            var tournament = r[0].Trim();
            var competition = MapBrFootballTournament(tournament);
            if (competition == null) continue;
            var m = new MatchRecord
            {
                SourceFile = "BR-Football-Dataset.csv",
                Competition = competition,
                HomeTeam = r[1].Trim(),
                HomeGoal = TryParseInt(r[2]),
                AwayGoal = TryParseInt(r[3]),
                AwayTeam = r[4].Trim(),
                Date = MatchDateParser.TryParse(r.Length > 12 ? r[12] : null),
                Season = MatchDateParser.TryParseSeason(r.Length > 12 ? r[12] : null),
                Stage = null,
            };
            FinalizeRecord(m);
            sink.Add(m);
        }
    }

    private static void LoadHistoricalBrasileirao(string path, List<MatchRecord> sink)
    {
        if (!File.Exists(path)) return;
        var rows = CsvReader.ReadAll(path);
        // Header: ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,
        //         Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,
        //         Vencedor,Arena,OBS
        for (int i = 1; i < rows.Count; i++)
        {
            var r = rows[i];
            if (r.Length < 8) continue;
            var m = new MatchRecord
            {
                SourceFile = "novo_campeonato_brasileiro.csv",
                Competition = Brasileirao,
                Date = MatchDateParser.TryParse(r[1]),
                Season = MatchDateParser.TryParseSeason(r[2]),
                Round = NullIfBlank(r[3]),
                HomeTeam = r[4].Trim(),
                AwayTeam = r[5].Trim(),
                HomeGoal = TryParseInt(r[6]),
                AwayGoal = TryParseInt(r[7]),
                HomeTeamState = NullIfBlank(r.Length > 8 ? r[8] : null),
                AwayTeamState = NullIfBlank(r.Length > 9 ? r[9] : null),
                Arena = NullIfBlank(r.Length > 11 ? r[11] : null),
            };
            FinalizeRecord(m);
            sink.Add(m);
        }
    }

    // ---- helpers ----------------------------------------------------------

    private static string? MapBrFootballTournament(string tournament)
    {
        if (string.IsNullOrWhiteSpace(tournament)) return null;
        var t = tournament.Trim();
        if (string.Equals(t, "Serie A", StringComparison.OrdinalIgnoreCase))
            return Brasileirao;
        if (string.Equals(t, "Copa do Brasil", StringComparison.OrdinalIgnoreCase))
            return CopaDoBrasil;
        if (string.Equals(t, "Serie B", StringComparison.OrdinalIgnoreCase))
            return "Serie B";
        if (string.Equals(t, "Serie C", StringComparison.OrdinalIgnoreCase))
            return "Serie C";
        if (t.Contains("Libertadores", StringComparison.OrdinalIgnoreCase))
            return Libertadores;
        return null; // unknown tournament not surfaced by the spec
    }

    private static void FinalizeRecord(MatchRecord m)
    {
        m.HomeTeamNormalized = TeamNameNormalizer.Normalize(m.HomeTeam);
        m.AwayTeamNormalized = TeamNameNormalizer.Normalize(m.AwayTeam);
        if (string.IsNullOrEmpty(m.HomeTeamState))
            m.HomeTeamState = ExtractStateSuffix(m.HomeTeam);
        if (string.IsNullOrEmpty(m.AwayTeamState))
            m.AwayTeamState = ExtractStateSuffix(m.AwayTeam);
    }

    private static string? ExtractStateSuffix(string raw)
    {
        // e.g. "Palmeiras-SP" -> "SP"
        var idx = raw.LastIndexOf('-');
        if (idx <= 0 || idx >= raw.Length - 1) return null;
        var tail = raw.Substring(idx + 1).Trim();
        if (tail.Length >= 2 && tail.Length <= 3 && IsAsciiLetters(tail))
            return tail.ToUpperInvariant();
        return null;
    }

    private static bool IsAsciiLetters(string s)
    {
        foreach (var c in s)
            if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z'))) return false;
        return true;
    }

    private static int? TryParseInt(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var s = raw.Trim();
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v))
            return v;
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)d;
        return null;
    }

    private static string? NullIfBlank(string? s)
        => string.IsNullOrWhiteSpace(s) ? null : s.Trim();
}
