// -----------------------------------------------------------------------------
// File: Data/MatchLoader.cs
// Project: BrazilianSoccer.Core
//
// Context:
//   Reads the five match CSVs into the unified Match model. Each file has its own
//   column layout, so there is one Load* method per file; all share the tolerant
//   parsers in CsvFields and the name cleaner in TeamName.
//
//   Files and quirks handled here:
//     - Brasileirao_Matches.csv  : Serie A 2012-2022; names carry "-SP" suffix.
//     - Brazilian_Cup_Matches.csv: Copa do Brasil; names use spaced " - MG" form
//                                  and the "round" column doubles as the stage.
//     - Libertadores_Matches.csv : goals are quoted strings; has a "stage" column;
//                                  season may be "NA".
//     - BR-Football-Dataset.csv  : extended stats; no season column (derived from
//                                  the date); tournament string maps to Serie A/B/C
//                                  or Copa do Brasil; goals are floats ("1.0").
//     - novo_campeonato_brasileiro.csv: historical Serie A 2003-2019; Portuguese
//                                  headers (Equipe_mandante, Gols_mandante, ...);
//                                  Brazilian date format; carries the stadium.
//
//   CsvHelper is configured to read by header name, trim whitespace, and ignore
//   missing/extra fields so the loaders are resilient to minor header drift.
// -----------------------------------------------------------------------------

using System.Globalization;
using BrazilianSoccer.Core.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccer.Core.Data;

/// <summary>Loads each match CSV into normalised <see cref="Match"/> records.</summary>
public static class MatchLoader
{
    private static CsvConfiguration Config => new(CultureInfo.InvariantCulture)
    {
        HasHeaderRecord = true,
        TrimOptions = TrimOptions.Trim,
        MissingFieldFound = null,
        BadDataFound = null,
        HeaderValidated = null,
        DetectColumnCountChanges = false,
    };

    /// <summary>Loads every match file found under <paramref name="dataDir"/>.</summary>
    public static List<Match> LoadAll(string dataDir)
    {
        var matches = new List<Match>(capacity: 24_000);
        matches.AddRange(LoadBrasileirao(Path.Combine(dataDir, "Brasileirao_Matches.csv")));
        matches.AddRange(LoadCup(Path.Combine(dataDir, "Brazilian_Cup_Matches.csv")));
        matches.AddRange(LoadLibertadores(Path.Combine(dataDir, "Libertadores_Matches.csv")));
        matches.AddRange(LoadExtended(Path.Combine(dataDir, "BR-Football-Dataset.csv")));
        matches.AddRange(LoadHistorical(Path.Combine(dataDir, "novo_campeonato_brasileiro.csv")));
        return matches;
    }

    public static IEnumerable<Match> LoadBrasileirao(string path)
    {
        foreach (var csv in Rows(path))
        {
            yield return new Match
            {
                Competition = Competition.BrasileiraoSerieA,
                Source = DataSource.BrasileiraoMatches,
                Season = CsvFields.ParseInt(csv.GetField("season")),
                Date = CsvFields.ParseDate(csv.GetField("datetime")),
                Round = CsvFields.Clean(csv.GetField("round")),
                HomeTeam = TeamName.Canonicalize(csv.GetField("home_team")),
                AwayTeam = TeamName.Canonicalize(csv.GetField("away_team")),
                HomeGoals = CsvFields.ParseInt(csv.GetField("home_goal")),
                AwayGoals = CsvFields.ParseInt(csv.GetField("away_goal")),
            };
        }
    }

    public static IEnumerable<Match> LoadCup(string path)
    {
        foreach (var csv in Rows(path))
        {
            yield return new Match
            {
                Competition = Competition.CopaDoBrasil,
                Source = DataSource.BrazilianCupMatches,
                Season = CsvFields.ParseInt(csv.GetField("season")),
                Date = CsvFields.ParseDate(csv.GetField("datetime")),
                Round = CsvFields.Clean(csv.GetField("round")),
                Stage = CsvFields.Clean(csv.GetField("round")),
                HomeTeam = TeamName.Canonicalize(csv.GetField("home_team")),
                AwayTeam = TeamName.Canonicalize(csv.GetField("away_team")),
                HomeGoals = CsvFields.ParseInt(csv.GetField("home_goal")),
                AwayGoals = CsvFields.ParseInt(csv.GetField("away_goal")),
            };
        }
    }

    public static IEnumerable<Match> LoadLibertadores(string path)
    {
        foreach (var csv in Rows(path))
        {
            yield return new Match
            {
                Competition = Competition.Libertadores,
                Source = DataSource.LibertadoresMatches,
                Season = CsvFields.ParseInt(csv.GetField("season")),
                Date = CsvFields.ParseDate(csv.GetField("datetime")),
                Stage = CsvFields.Clean(csv.GetField("stage")),
                HomeTeam = TeamName.Canonicalize(csv.GetField("home_team")),
                AwayTeam = TeamName.Canonicalize(csv.GetField("away_team")),
                HomeGoals = CsvFields.ParseInt(csv.GetField("home_goal")),
                AwayGoals = CsvFields.ParseInt(csv.GetField("away_goal")),
            };
        }
    }

    public static IEnumerable<Match> LoadExtended(string path)
    {
        foreach (var csv in Rows(path))
        {
            var date = CsvFields.ParseDate(csv.GetField("date"));
            yield return new Match
            {
                Competition = MapTournament(csv.GetField("tournament")),
                Source = DataSource.ExtendedStats,
                Season = date?.Year,
                Date = date,
                HomeTeam = TeamName.Canonicalize(csv.GetField("home")),
                AwayTeam = TeamName.Canonicalize(csv.GetField("away")),
                HomeGoals = CsvFields.ParseInt(csv.GetField("home_goal")),
                AwayGoals = CsvFields.ParseInt(csv.GetField("away_goal")),
                Stats = new MatchStats(
                    HomeCorners: CsvFields.ParseInt(csv.GetField("home_corner")),
                    AwayCorners: CsvFields.ParseInt(csv.GetField("away_corner")),
                    HomeAttacks: CsvFields.ParseInt(csv.GetField("home_attack")),
                    AwayAttacks: CsvFields.ParseInt(csv.GetField("away_attack")),
                    HomeShots: CsvFields.ParseInt(csv.GetField("home_shots")),
                    AwayShots: CsvFields.ParseInt(csv.GetField("away_shots")),
                    HalfTimeHomeResult: CsvFields.Clean(csv.GetField("ht_result")),
                    HalfTimeAwayResult: CsvFields.Clean(csv.GetField("at_result")),
                    TotalCorners: CsvFields.ParseInt(csv.GetField("total_corners"))),
            };
        }
    }

    public static IEnumerable<Match> LoadHistorical(string path)
    {
        foreach (var csv in Rows(path))
        {
            yield return new Match
            {
                Competition = Competition.BrasileiraoSerieA,
                Source = DataSource.HistoricalBrasileirao,
                Season = CsvFields.ParseInt(csv.GetField("Ano")),
                Date = CsvFields.ParseDate(csv.GetField("Data")),
                Round = CsvFields.Clean(csv.GetField("Rodada")),
                HomeTeam = TeamName.Canonicalize(csv.GetField("Equipe_mandante")),
                AwayTeam = TeamName.Canonicalize(csv.GetField("Equipe_visitante")),
                HomeGoals = CsvFields.ParseInt(csv.GetField("Gols_mandante")),
                AwayGoals = CsvFields.ParseInt(csv.GetField("Gols_visitante")),
                Venue = CsvFields.Clean(csv.GetField("Arena")),
            };
        }
    }

    /// <summary>Maps the BR-Football "tournament" string to a <see cref="Competition"/>.</summary>
    public static Competition MapTournament(string? tournament)
    {
        var t = tournament?.Trim();
        return t switch
        {
            "Serie A" => Competition.BrasileiraoSerieA,
            "Serie B" => Competition.BrasileiraoSerieB,
            "Serie C" => Competition.BrasileiraoSerieC,
            "Copa do Brasil" => Competition.CopaDoBrasil,
            _ => Competition.Unknown,
        };
    }

    // Streams CsvHelper records; yields the reader positioned on each data row so
    // callers read fields by header name without allocating an intermediate DTO.
    private static IEnumerable<CsvReader> Rows(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException($"Match data file not found: {path}", path);

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, Config);
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
            yield return csv;
    }
}
