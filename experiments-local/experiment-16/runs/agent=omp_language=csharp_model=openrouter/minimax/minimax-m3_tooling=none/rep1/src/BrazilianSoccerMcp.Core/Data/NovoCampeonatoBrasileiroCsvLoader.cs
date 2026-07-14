// =============================================================================
// Brazilian Soccer MCP Server
// File: NovoCampeonatoBrasileiroCsvLoader.cs
// Purpose: Stream-reads novo_campeonato_brasileiro.csv (2003-2019) into
//          MatchRecord rows.
// Context: This file is the only one that stores the arena name, has a
//          dedicated 'Vencedor' column (Mandante/Visitante/Empate), and
//          uses DD/MM/YYYY dates -- so we route it through the multi-format
//          DateTimeParser and preserve the 'Arena' field for the rare
//          query that needs it.
// =============================================================================

using System.Globalization;
using BrazilianSoccerMcp.Core.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Core.Data;

public static class NovoCampeonatoBrasileiroCsvLoader
{
    public const string DefaultFileName = "data/kaggle/novo_campeonato_brasileiro.csv";

    public static IReadOnlyList<MatchRecord> Load(string path)
    {
        var cfg = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
            BadDataFound = null,
            TrimOptions = TrimOptions.Trim,
        };

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, cfg);
        csv.Read();
        csv.ReadHeader();

        var results = new List<MatchRecord>();
        while (csv.Read())
        {
            var rawHome = csv.GetField("Equipe_mandante") ?? string.Empty;
            var rawAway = csv.GetField("Equipe_visitante") ?? string.Empty;
            var rawDate = csv.GetField("Data");
            var date = DateTimeParser.TryParse(rawDate, out var d) ? d : default;
            var homeGoals = ParseIntSafe(csv.GetField("Gols_mandante"));
            var awayGoals = ParseIntSafe(csv.GetField("Gols_visitante"));
            var winner = NullIfEmpty(csv.GetField("Vencedor"));

            // Some rows in this file have no recorded goals but do have a
            // 'Vencedor' value; if either side is missing we still keep
            // the row and trust the winner column.
            results.Add(new MatchRecord
            {
                Competition = Competition.Brasileirao,
                HomeTeam = rawHome,
                AwayTeam = rawAway,
                HomeTeamState = NullIfEmpty(csv.GetField("Mandante_UF")),
                AwayTeamState = NullIfEmpty(csv.GetField("Visitante_UF")),
                HomeGoal = homeGoals,
                AwayGoal = awayGoals,
                Season = ParseIntSafe(csv.GetField("Ano")),
                Date = date,
                Round = NullIfEmpty(csv.GetField("Rodada")),
                Arena = NullIfEmpty(csv.GetField("Arena")),
                SourceId = NullIfEmpty(csv.GetField("ID")),
                Stage = winner,
            });
        }
        return results;
    }

    private static int ParseIntSafe(string? s) =>
        int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v) ? v : 0;

    private static string? NullIfEmpty(string? s) =>
        string.IsNullOrWhiteSpace(s) ? null : s.Trim().Trim('"');
}
