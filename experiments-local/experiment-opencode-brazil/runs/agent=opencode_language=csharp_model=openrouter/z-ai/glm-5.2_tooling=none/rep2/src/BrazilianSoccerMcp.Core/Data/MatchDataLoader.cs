// BrazilianSoccerMcp.Core - Match data loaders.
// One loader method per CSV file, each returning a normalized
// <see cref="Match"/> list. <see cref="MatchDataLoader.LoadAll"/> loads every
// file from a directory and merges them into a single list, skipping rows
// with unparseable dates or scores rather than aborting the load.
using BrazilianSoccerMcp.Core.Data.Csv;
using BrazilianSoccerMcp.Core.Models;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>Loads the five match CSV files into normalized <see cref="Match"/> lists.</summary>
public sealed class MatchDataLoader
{
    public const string BrasileiraoFile = "Brasileirao_Matches.csv";
    public const string CopaDoBrasilFile = "Brazilian_Cup_Matches.csv";
    public const string LibertadoresFile = "Libertadores_Matches.csv";
    public const string BrFootballFile = "BR-Football-Dataset.csv";
    public const string HistoricalFile = "novo_campeonato_brasileiro.csv";

    public IReadOnlyList<Match> LoadAll(string directory) =>
        LoadBrasileirao(directory)
            .Concat(LoadCopaDoBrasil(directory))
            .Concat(LoadLibertadores(directory))
            .Concat(LoadBrFootball(directory))
            .Concat(LoadHistorical(directory))
            .ToList();

    public IReadOnlyList<Match> LoadBrasileirao(string directory)
    {
        var path = Path.Combine(directory, BrasileiraoFile);
        if (!File.Exists(path)) return Array.Empty<Match>();
        return ReadMatches(path, row => new Match
        {
            Competition = Competition.Brasileirao,
            RawCompetition = "Brasileirao Serie A",
            Date = DateParser.Parse(row.GetOrNull("datetime")) ?? DateTime.MinValue,
            HomeTeam = row.Get("home_team"),
            AwayTeam = row.Get("away_team"),
            HomeGoal = row.GetInt("home_goal"),
            AwayGoal = row.GetInt("away_goal"),
            Season = row.GetInt("season"),
            Round = row.Get("round"),
            HomeState = row.Get("home_team_state"),
            AwayState = row.Get("away_team_state")
        });
    }

    public IReadOnlyList<Match> LoadCopaDoBrasil(string directory)
    {
        var path = Path.Combine(directory, CopaDoBrasilFile);
        if (!File.Exists(path)) return Array.Empty<Match>();
        return ReadMatches(path, row => new Match
        {
            Competition = Competition.CopaDoBrasil,
            RawCompetition = "Copa do Brasil",
            Date = DateParser.Parse(row.GetOrNull("datetime")) ?? DateTime.MinValue,
            HomeTeam = row.Get("home_team"),
            AwayTeam = row.Get("away_team"),
            HomeGoal = row.GetInt("home_goal"),
            AwayGoal = row.GetInt("away_goal"),
            Season = row.GetInt("season"),
            Round = row.Get("round")
        });
    }

    public IReadOnlyList<Match> LoadLibertadores(string directory)
    {
        var path = Path.Combine(directory, LibertadoresFile);
        if (!File.Exists(path)) return Array.Empty<Match>();
        return ReadMatches(path, row => new Match
        {
            Competition = Competition.Libertadores,
            RawCompetition = "Copa Libertadores",
            Date = DateParser.Parse(row.GetOrNull("datetime")) ?? DateTime.MinValue,
            HomeTeam = row.Get("home_team"),
            AwayTeam = row.Get("away_team"),
            HomeGoal = row.GetInt("home_goal"),
            AwayGoal = row.GetInt("away_goal"),
            Season = row.GetInt("season"),
            Stage = row.Get("stage")
        });
    }

    public IReadOnlyList<Match> LoadBrFootball(string directory)
    {
        var path = Path.Combine(directory, BrFootballFile);
        if (!File.Exists(path)) return Array.Empty<Match>();
        return ReadMatches(path, row => new Match
        {
            Competition = Competition.Other,
            RawCompetition = row.Get("tournament"),
            Date = DateParser.Parse(row.GetOrNull("date")) ?? DateTime.MinValue,
            HomeTeam = row.Get("home"),
            AwayTeam = row.Get("away"),
            HomeGoal = (int)Math.Round(row.GetDouble("home_goal") ?? 0),
            AwayGoal = (int)Math.Round(row.GetDouble("away_goal") ?? 0),
            Season = DateParser.Parse(row.GetOrNull("date"))?.Year ?? 0,
            HomeCorner = row.GetDouble("home_corner"),
            AwayCorner = row.GetDouble("away_corner"),
            HomeAttack = row.GetDouble("home_attack"),
            AwayAttack = row.GetDouble("away_attack"),
            HomeShots = row.GetDouble("home_shots"),
            AwayShots = row.GetDouble("away_shots"),
            HalfTimeResult = row.GetOrNull("ht_result"),
            TotalCorners = row.GetDouble("total_corners")
        });
    }

    public IReadOnlyList<Match> LoadHistorical(string directory)
    {
        var path = Path.Combine(directory, HistoricalFile);
        if (!File.Exists(path)) return Array.Empty<Match>();
        return ReadMatches(path, row => new Match
        {
            Competition = Competition.HistoricalBrasileirao,
            RawCompetition = "Campeonato Brasileiro (2003-2019)",
            Date = DateParser.Parse(row.GetOrNull("Data")) ?? DateTime.MinValue,
            HomeTeam = row.Get("Equipe_mandante"),
            AwayTeam = row.Get("Equipe_visitante"),
            HomeGoal = row.GetInt("Gols_mandante"),
            AwayGoal = row.GetInt("Gols_visitante"),
            Season = row.GetInt("Ano"),
            Round = row.Get("Rodada"),
            HomeState = row.Get("Mandante_UF"),
            AwayState = row.Get("Visitante_UF"),
            Arena = row.Get("Arena")
        });
    }

    private static IReadOnlyList<Match> ReadMatches(string path, Func<CsvRow, Match> map)
    {
        var rows = SimpleCsvReader.Read(path);
        var matches = new List<Match>(rows.Count);
        foreach (var row in rows)
        {
            try { matches.Add(map(row)); }
            catch { /* skip malformed row rather than aborting load */ }
        }
        return matches;
    }
}
