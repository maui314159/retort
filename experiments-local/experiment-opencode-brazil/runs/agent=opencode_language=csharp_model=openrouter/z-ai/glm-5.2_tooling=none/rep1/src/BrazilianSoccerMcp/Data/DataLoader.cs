// Context block
// File: Data/DataLoader.cs
// Purpose: Load all six Kaggle CSV files into typed models for the Brazilian Soccer MCP
// server. The five match files have heterogeneous schemas, so each is parsed with a
// dedicated private method that maps its columns into the unified MatchRecord. The FIFA
// player file is parsed into PlayerRecord using only the columns the query services
// need. The loader accepts a TeamNameNormalizer and a DateParser so name and date
// normalization is testable in isolation. All file access goes through DataPaths so the
// loader works from build output and the repository root.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Data;

/// <summary>Loads the bundled Kaggle CSV datasets into typed models.</summary>
public sealed class DataLoader
{
    private readonly TeamNameNormalizer _normalizer;
    private readonly DateParser _dates;

    public DataLoader(TeamNameNormalizer normalizer, DateParser dates)
    {
        _normalizer = normalizer;
        _dates = dates;
    }

    /// <summary>Loads every match file and returns the unified list.</summary>
    public List<MatchRecord> LoadAllMatches()
    {
        var matches = new List<MatchRecord>(30_000);
        matches.AddRange(LoadBrasileirao());
        matches.AddRange(LoadCopaDoBrasil());
        matches.AddRange(LoadLibertadores());
        matches.AddRange(LoadBrFootball());
        matches.AddRange(LoadHistoricBrasileirao());
        return matches;
    }

    /// <summary>Loads the FIFA player subset.</summary>
    public List<PlayerRecord> LoadPlayers()
    {
        var path = DataPaths.ResolveCsvFile(DataPaths.Files.FifaPlayers);
        var (header, rows) = CsvReader.ReadFile(path, hasHeader: true);
        var name = CsvReader.IndexOf(header, "Name");
        var id = CsvReader.IndexOf(header, "ID");
        var age = CsvReader.IndexOf(header, "Age");
        var nat = CsvReader.IndexOf(header, "Nationality");
        var overall = CsvReader.IndexOf(header, "Overall");
        var potential = CsvReader.IndexOf(header, "Potential");
        var club = CsvReader.IndexOf(header, "Club");
        var pos = CsvReader.IndexOf(header, "Position");
        var jersey = CsvReader.IndexOf(header, "Jersey Number");
        var foot = CsvReader.IndexOf(header, "Preferred Foot");

        var players = new List<PlayerRecord>(rows.Count);
        foreach (var row in rows)
        {
            if (name < 0 || CsvReader.At(row, name) is not string nm || string.IsNullOrWhiteSpace(nm))
            {
                continue;
            }
            var p = new PlayerRecord
            {
                Id = ParseInt(CsvReader.At(row, id)) ?? 0,
                Name = nm!.Trim(),
                Age = ParseInt(CsvReader.At(row, age)) ?? 0,
                Nationality = (CsvReader.At(row, nat) ?? string.Empty).Trim(),
                Overall = ParseInt(CsvReader.At(row, overall)) ?? 0,
                Potential = ParseInt(CsvReader.At(row, potential)) ?? 0,
                Club = (CsvReader.At(row, club) ?? string.Empty).Trim(),
                Position = (CsvReader.At(row, pos) ?? string.Empty).Trim(),
                JerseyNumber = ParseInt(CsvReader.At(row, jersey)),
                PreferredFoot = (CsvReader.At(row, foot) ?? string.Empty).Trim(),
            };
            players.Add(p);
        }
        return players;
    }

    // ---- Match file loaders ----

    public List<MatchRecord> LoadBrasileirao()
    {
        var path = DataPaths.ResolveCsvFile(DataPaths.Files.BrasileiraoMatches);
        var (header, rows) = CsvReader.ReadFile(path, hasHeader: true);
        var iDate = CsvReader.IndexOf(header, "datetime");
        var iHome = CsvReader.IndexOf(header, "home_team");
        var iHomeState = CsvReader.IndexOf(header, "home_team_state");
        var iAway = CsvReader.IndexOf(header, "away_team");
        var iAwayState = CsvReader.IndexOf(header, "away_team_state");
        var iHg = CsvReader.IndexOf(header, "home_goal");
        var iAg = CsvReader.IndexOf(header, "away_goal");
        var iSeason = CsvReader.IndexOf(header, "season");
        var iRound = CsvReader.IndexOf(header, "round");

        return Map(rows, r => new MatchRecord
        {
            CompetitionType = Competition.Brasileirao,
            Date = _dates.Parse(CsvReader.At(r, iDate) ?? string.Empty),
            HomeRaw = CsvReader.At(r, iHome) ?? string.Empty,
            AwayRaw = CsvReader.At(r, iAway) ?? string.Empty,
            Home = _normalizer.Normalize(CsvReader.At(r, iHome)),
            Away = _normalizer.Normalize(CsvReader.At(r, iAway)),
            HomeGoal = ParseInt(CsvReader.At(r, iHg)) ?? 0,
            AwayGoal = ParseInt(CsvReader.At(r, iAg)) ?? 0,
            Season = ParseInt(CsvReader.At(r, iSeason)),
            Round = CsvReader.At(r, iRound)?.Trim(),
            HomeState = CsvReader.At(r, iHomeState)?.Trim(),
            AwayState = CsvReader.At(r, iAwayState)?.Trim(),
        });
    }

    public List<MatchRecord> LoadCopaDoBrasil()
    {
        var path = DataPaths.ResolveCsvFile(DataPaths.Files.BrazilianCupMatches);
        var (header, rows) = CsvReader.ReadFile(path, hasHeader: true);
        var iDate = CsvReader.IndexOf(header, "datetime");
        var iHome = CsvReader.IndexOf(header, "home_team");
        var iAway = CsvReader.IndexOf(header, "away_team");
        var iHg = CsvReader.IndexOf(header, "home_goal");
        var iAg = CsvReader.IndexOf(header, "away_goal");
        var iSeason = CsvReader.IndexOf(header, "season");
        var iRound = CsvReader.IndexOf(header, "round");

        return Map(rows, r => new MatchRecord
        {
            CompetitionType = Competition.CopaDoBrasil,
            Date = _dates.Parse(CsvReader.At(r, iDate) ?? string.Empty),
            HomeRaw = CsvReader.At(r, iHome) ?? string.Empty,
            AwayRaw = CsvReader.At(r, iAway) ?? string.Empty,
            Home = _normalizer.Normalize(CsvReader.At(r, iHome)),
            Away = _normalizer.Normalize(CsvReader.At(r, iAway)),
            HomeGoal = ParseInt(CsvReader.At(r, iHg)) ?? 0,
            AwayGoal = ParseInt(CsvReader.At(r, iAg)) ?? 0,
            Season = ParseInt(CsvReader.At(r, iSeason)),
            Round = CsvReader.At(r, iRound)?.Trim(),
        });
    }

    public List<MatchRecord> LoadLibertadores()
    {
        var path = DataPaths.ResolveCsvFile(DataPaths.Files.LibertadoresMatches);
        var (header, rows) = CsvReader.ReadFile(path, hasHeader: true);
        var iDate = CsvReader.IndexOf(header, "datetime");
        var iHome = CsvReader.IndexOf(header, "home_team");
        var iAway = CsvReader.IndexOf(header, "away_team");
        var iHg = CsvReader.IndexOf(header, "home_goal");
        var iAg = CsvReader.IndexOf(header, "away_goal");
        var iSeason = CsvReader.IndexOf(header, "season");
        var iStage = CsvReader.IndexOf(header, "stage");

        return Map(rows, r => new MatchRecord
        {
            CompetitionType = Competition.Libertadores,
            Date = _dates.Parse(CsvReader.At(r, iDate) ?? string.Empty),
            HomeRaw = CsvReader.At(r, iHome) ?? string.Empty,
            AwayRaw = CsvReader.At(r, iAway) ?? string.Empty,
            Home = _normalizer.Normalize(CsvReader.At(r, iHome)),
            Away = _normalizer.Normalize(CsvReader.At(r, iAway)),
            HomeGoal = ParseInt(CsvReader.At(r, iHg)) ?? 0,
            AwayGoal = ParseInt(CsvReader.At(r, iAg)) ?? 0,
            Season = ParseInt(CsvReader.At(r, iSeason)),
            Stage = CsvReader.At(r, iStage)?.Trim(),
        });
    }

    public List<MatchRecord> LoadBrFootball()
    {
        var path = DataPaths.ResolveCsvFile(DataPaths.Files.BrFootballDataset);
        var (header, rows) = CsvReader.ReadFile(path, hasHeader: true);
        var iTour = CsvReader.IndexOf(header, "tournament");
        var iHome = CsvReader.IndexOf(header, "home");
        var iAway = CsvReader.IndexOf(header, "away");
        var iHg = CsvReader.IndexOf(header, "home_goal");
        var iAg = CsvReader.IndexOf(header, "away_goal");
        var iTime = CsvReader.IndexOf(header, "time");
        var iDate = CsvReader.IndexOf(header, "date");

        return Map(rows, r =>
        {
            var dateStr = CsvReader.At(r, iDate) ?? string.Empty;
            var timeStr = CsvReader.At(r, iTime);
            var combined = string.IsNullOrWhiteSpace(timeStr) ? dateStr : $"{dateStr} {timeStr}";
            return new MatchRecord
            {
                CompetitionType = Competition.BrFootballDataset,
                Date = _dates.Parse(combined),
                HomeRaw = CsvReader.At(r, iHome) ?? string.Empty,
                AwayRaw = CsvReader.At(r, iAway) ?? string.Empty,
                Home = _normalizer.Normalize(CsvReader.At(r, iHome)),
                Away = _normalizer.Normalize(CsvReader.At(r, iAway)),
                HomeGoal = ParseDecimalInt(CsvReader.At(r, iHg)) ?? 0,
                AwayGoal = ParseDecimalInt(CsvReader.At(r, iAg)) ?? 0,
                Tournament = CsvReader.At(r, iTour)?.Trim(),
            };
        });
    }

    public List<MatchRecord> LoadHistoricBrasileirao()
    {
        var path = DataPaths.ResolveCsvFile(DataPaths.Files.HistoricBrasileirao);
        var (header, rows) = CsvReader.ReadFile(path, hasHeader: true);
        var iData = CsvReader.IndexOf(header, "Data");
        var iAno = CsvReader.IndexOf(header, "Ano");
        var iRound = CsvReader.IndexOf(header, "Rodada");
        var iHome = CsvReader.IndexOf(header, "Equipe_mandante");
        var iAway = CsvReader.IndexOf(header, "Equipe_visitante");
        var iHg = CsvReader.IndexOf(header, "Gols_mandante");
        var iAg = CsvReader.IndexOf(header, "Gols_visitante");
        var iHomeUf = CsvReader.IndexOf(header, "Mandante_UF");
        var iAwayUf = CsvReader.IndexOf(header, "Visitante_UF");
        var iArena = CsvReader.IndexOf(header, "Arena");

        return Map(rows, r => new MatchRecord
        {
            CompetitionType = Competition.HistoricBrasileirao,
            Date = _dates.Parse(CsvReader.At(r, iData) ?? string.Empty),
            HomeRaw = CsvReader.At(r, iHome) ?? string.Empty,
            AwayRaw = CsvReader.At(r, iAway) ?? string.Empty,
            Home = _normalizer.Normalize(CsvReader.At(r, iHome)),
            Away = _normalizer.Normalize(CsvReader.At(r, iAway)),
            HomeGoal = ParseInt(CsvReader.At(r, iHg)) ?? 0,
            AwayGoal = ParseInt(CsvReader.At(r, iAg)) ?? 0,
            Season = ParseInt(CsvReader.At(r, iAno)),
            Round = CsvReader.At(r, iRound)?.Trim(),
            HomeState = CsvReader.At(r, iHomeUf)?.Trim(),
            AwayState = CsvReader.At(r, iAwayUf)?.Trim(),
            Arena = CsvReader.At(r, iArena)?.Trim(),
        });
    }

    // ---- Helpers ----

    private static List<MatchRecord> Map(List<string[]> rows, Func<string[], MatchRecord> selector)
    {
        var list = new List<MatchRecord>(rows.Count);
        foreach (var r in rows)
        {
            try
            {
                list.Add(selector(r));
            }
            catch
            {
                // Skip malformed rows so a single bad line never aborts loading.
            }
        }
        return list;
    }

    private static int? ParseInt(string? v)
    {
        if (string.IsNullOrWhiteSpace(v))
        {
            return null;
        }
        var t = v!.Trim().Trim('"');
        if (int.TryParse(t, out var i))
        {
            return i;
        }
        if (double.TryParse(t, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var d))
        {
            return (int)Math.Round(d);
        }
        return null;
    }

    private static int? ParseDecimalInt(string? v)
    {
        if (string.IsNullOrWhiteSpace(v))
        {
            return null;
        }

        var t = v!.Trim().Trim('"');
        if (double.TryParse(t, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var d))
        {
            return (int)Math.Round(d);
        }
        if (int.TryParse(t, out var i))
        {
            return i;
        }
        return null;
    }
}
