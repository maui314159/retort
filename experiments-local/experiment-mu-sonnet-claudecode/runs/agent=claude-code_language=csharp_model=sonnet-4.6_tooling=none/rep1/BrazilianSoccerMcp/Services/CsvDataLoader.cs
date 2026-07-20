using System.Globalization;
using CsvHelper;
using CsvHelper.Configuration;
using CsvHelper.Configuration.Attributes;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

public class CsvDataLoader(string kaggleDataPath)
{
    public List<UnifiedMatch> LoadAllMatches()
    {
        var matches = new List<UnifiedMatch>();
        matches.AddRange(LoadBrasileirao());
        matches.AddRange(LoadCupMatches());
        matches.AddRange(LoadLibertadores());
        matches.AddRange(LoadBrFootballDataset());
        matches.AddRange(LoadHistoricalBrasileirao());
        return matches;
    }

    public List<FifaPlayer> LoadPlayers()
    {
        var path = Path.Combine(kaggleDataPath, "fifa_data.csv");
        if (!File.Exists(path)) return [];

        var players = new List<FifaPlayer>();
        // Use detectEncodingFromByteOrderMarks to strip UTF-8 BOM
        using var reader = new StreamReader(path, System.Text.Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            BadDataFound = null,
            MissingFieldFound = null,
            HeaderValidated = null,
        });

        try
        {
            csv.Read();
            csv.ReadHeader();
        }
        catch { return players; }

        // Use manual Read() so we can catch per-row exceptions
        while (true)
        {
            bool hasNext;
            try { hasNext = csv.Read(); }
            catch { break; }
            if (!hasNext) break;

            try
            {
                var idStr = csv.GetField("ID") ?? "";
                if (!int.TryParse(idStr, out var id)) continue;

                var name = csv.GetField("Name") ?? "";
                if (string.IsNullOrWhiteSpace(name)) continue;

                var nationality = csv.GetField("Nationality") ?? "";
                var club = csv.GetField("Club") ?? "";
                var position = csv.GetField("Position") ?? "";

                int.TryParse(csv.GetField("Age"), out var age);
                int.TryParse(csv.GetField("Overall"), out var overall);
                int.TryParse(csv.GetField("Potential"), out var potential);
                int? jersey = int.TryParse(csv.GetField("Jersey Number"), out var j) ? j : null;

                players.Add(new FifaPlayer(id, name, age, nationality, overall, potential, club, position, jersey));
            }
            catch { /* skip bad rows */ }
        }
        return players;
    }

    private IEnumerable<UnifiedMatch> LoadBrasileirao()
    {
        var path = Path.Combine(kaggleDataPath, "Brasileirao_Matches.csv");
        if (!File.Exists(path)) yield break;

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            BadDataFound = null,
            MissingFieldFound = null,
        });

        csv.Context.RegisterClassMap<BrasileiraMatchMap>();
        var records = csv.GetRecords<BrasileiraRecord>();

        foreach (var r in records)
        {
            if (string.IsNullOrEmpty(r.HomeTeam)) continue;
            // Skip rows with NA goals (e.g., abandoned matches)
            if (!int.TryParse(r.HomeGoal, out var hg)) continue;
            if (!int.TryParse(r.AwayGoal, out var ag)) continue;
            if (!int.TryParse(r.Season, out var season)) continue;
            yield return new UnifiedMatch(
                ParseDateTime(r.Datetime),
                r.HomeTeam,
                r.AwayTeam,
                hg,
                ag,
                season,
                "Brasileirao Serie A",
                r.Round
            );
        }
    }

    private IEnumerable<UnifiedMatch> LoadCupMatches()
    {
        var path = Path.Combine(kaggleDataPath, "Brazilian_Cup_Matches.csv");
        if (!File.Exists(path)) yield break;

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            BadDataFound = null,
            MissingFieldFound = null,
        });

        csv.Context.RegisterClassMap<CupMatchMap>();
        var records = csv.GetRecords<CupRecord>();

        foreach (var r in records)
        {
            if (string.IsNullOrEmpty(r.HomeTeam)) continue;
            if (!int.TryParse(r.HomeGoal, out var hg)) continue;
            if (!int.TryParse(r.AwayGoal, out var ag)) continue;
            if (!int.TryParse(r.Season, out var season)) continue;
            yield return new UnifiedMatch(
                ParseDateTime(r.Datetime),
                r.HomeTeam,
                r.AwayTeam,
                hg,
                ag,
                season,
                "Copa do Brasil",
                r.Round
            );
        }
    }

    private IEnumerable<UnifiedMatch> LoadLibertadores()
    {
        var path = Path.Combine(kaggleDataPath, "Libertadores_Matches.csv");
        if (!File.Exists(path)) yield break;

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            BadDataFound = null,
            MissingFieldFound = null,
        });

        csv.Context.RegisterClassMap<LibertadoresMatchMap>();
        var records = csv.GetRecords<LibertadoresRecord>();

        foreach (var r in records)
        {
            if (string.IsNullOrEmpty(r.HomeTeam)) continue;
            if (!int.TryParse(r.HomeGoal, out var hg)) continue;
            if (!int.TryParse(r.AwayGoal, out var ag)) continue;
            if (!int.TryParse(r.Season, out var season)) continue;
            yield return new UnifiedMatch(
                ParseDateTime(r.Datetime),
                r.HomeTeam,
                r.AwayTeam,
                hg,
                ag,
                season,
                "Copa Libertadores",
                Stage: r.Stage
            );
        }
    }

    private IEnumerable<UnifiedMatch> LoadBrFootballDataset()
    {
        var path = Path.Combine(kaggleDataPath, "BR-Football-Dataset.csv");
        if (!File.Exists(path)) yield break;

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            BadDataFound = null,
            MissingFieldFound = null,
        });

        csv.Context.RegisterClassMap<BrFootballMap>();
        var records = csv.GetRecords<BrFootballRecord>();

        foreach (var r in records)
        {
            if (string.IsNullOrEmpty(r.Home)) continue;
            var homeGoal = (int)Math.Round(r.HomeGoal);
            var awayGoal = (int)Math.Round(r.AwayGoal);
            if (!DateTime.TryParse(r.Date, out var dt)) continue;

            // Extract year from date for season
            var season = dt.Year;
            yield return new UnifiedMatch(
                dt,
                r.Home,
                r.Away,
                homeGoal,
                awayGoal,
                season,
                r.Tournament ?? "Brazilian Football"
            );
        }
    }

    private IEnumerable<UnifiedMatch> LoadHistoricalBrasileirao()
    {
        var path = Path.Combine(kaggleDataPath, "novo_campeonato_brasileiro.csv");
        if (!File.Exists(path)) yield break;

        using var reader = new StreamReader(path, System.Text.Encoding.UTF8);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            BadDataFound = null,
            MissingFieldFound = null,
        });

        csv.Context.RegisterClassMap<HistoricalMatchMap>();
        var records = csv.GetRecords<HistoricalRecord>();

        foreach (var r in records)
        {
            if (string.IsNullOrEmpty(r.HomeTeam)) continue;
            if (!int.TryParse(r.HomeGoals, out var hg)) continue;
            if (!int.TryParse(r.AwayGoals, out var ag)) continue;
            if (!int.TryParse(r.Year, out var year)) continue;

            // Date format: DD/MM/YYYY
            DateTime? dt = null;
            if (DateTime.TryParseExact(r.Data, "dd/MM/yyyy", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var parsedDate))
                dt = parsedDate;

            yield return new UnifiedMatch(
                dt,
                r.HomeTeam,
                r.AwayTeam,
                hg,
                ag,
                year,
                "Brasileirao Historico",
                r.Round,
                Arena: r.Arena
            );
        }
    }

    private static DateTime? ParseDateTime(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        if (DateTime.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
            return dt;
        return null;
    }

    // CSV record classes and maps
    private class BrasileiraRecord
    {
        public string? Datetime { get; set; }
        public string HomeTeam { get; set; } = "";
        public string AwayTeam { get; set; } = "";
        public string? HomeGoal { get; set; }
        public string? AwayGoal { get; set; }
        public string? Season { get; set; }
        public string? Round { get; set; }
    }

    private sealed class BrasileiraMatchMap : ClassMap<BrasileiraRecord>
    {
        public BrasileiraMatchMap()
        {
            Map(m => m.Datetime).Name("datetime");
            Map(m => m.HomeTeam).Name("home_team");
            Map(m => m.AwayTeam).Name("away_team");
            Map(m => m.HomeGoal).Name("home_goal");
            Map(m => m.AwayGoal).Name("away_goal");
            Map(m => m.Season).Name("season");
            Map(m => m.Round).Name("round");
        }
    }

    private class CupRecord
    {
        public string? Round { get; set; }
        public string? Datetime { get; set; }
        public string HomeTeam { get; set; } = "";
        public string AwayTeam { get; set; } = "";
        public string? HomeGoal { get; set; }
        public string? AwayGoal { get; set; }
        public string? Season { get; set; }
    }

    private sealed class CupMatchMap : ClassMap<CupRecord>
    {
        public CupMatchMap()
        {
            Map(m => m.Round).Name("round");
            Map(m => m.Datetime).Name("datetime");
            Map(m => m.HomeTeam).Name("home_team");
            Map(m => m.AwayTeam).Name("away_team");
            Map(m => m.HomeGoal).Name("home_goal");
            Map(m => m.AwayGoal).Name("away_goal");
            Map(m => m.Season).Name("season");
        }
    }

    private class LibertadoresRecord
    {
        public string? Datetime { get; set; }
        public string HomeTeam { get; set; } = "";
        public string AwayTeam { get; set; } = "";
        public string? HomeGoal { get; set; }
        public string? AwayGoal { get; set; }
        public string? Season { get; set; }
        public string? Stage { get; set; }
    }

    private sealed class LibertadoresMatchMap : ClassMap<LibertadoresRecord>
    {
        public LibertadoresMatchMap()
        {
            Map(m => m.Datetime).Name("datetime");
            Map(m => m.HomeTeam).Name("home_team");
            Map(m => m.AwayTeam).Name("away_team");
            Map(m => m.HomeGoal).Name("home_goal");
            Map(m => m.AwayGoal).Name("away_goal");
            Map(m => m.Season).Name("season");
            Map(m => m.Stage).Name("stage");
        }
    }

    private class BrFootballRecord
    {
        public string? Tournament { get; set; }
        public string Home { get; set; } = "";
        public string Away { get; set; } = "";
        public double HomeGoal { get; set; }
        public double AwayGoal { get; set; }
        public string? Date { get; set; }
    }

    private sealed class BrFootballMap : ClassMap<BrFootballRecord>
    {
        public BrFootballMap()
        {
            Map(m => m.Tournament).Name("tournament");
            Map(m => m.Home).Name("home");
            Map(m => m.Away).Name("away");
            Map(m => m.HomeGoal).Name("home_goal");
            Map(m => m.AwayGoal).Name("away_goal");
            Map(m => m.Date).Name("date");
        }
    }

    private class HistoricalRecord
    {
        public string? Data { get; set; }
        public string? Year { get; set; }
        public string? Round { get; set; }
        public string HomeTeam { get; set; } = "";
        public string AwayTeam { get; set; } = "";
        public string? HomeGoals { get; set; }
        public string? AwayGoals { get; set; }
        public string? Arena { get; set; }
    }

    private sealed class HistoricalMatchMap : ClassMap<HistoricalRecord>
    {
        public HistoricalMatchMap()
        {
            Map(m => m.Data).Name("Data");
            Map(m => m.Year).Name("Ano");
            Map(m => m.Round).Name("Rodada");
            Map(m => m.HomeTeam).Name("Equipe_mandante");
            Map(m => m.AwayTeam).Name("Equipe_visitante");
            Map(m => m.HomeGoals).Name("Gols_mandante");
            Map(m => m.AwayGoals).Name("Gols_visitante");
            Map(m => m.Arena).Name("Arena");
        }
    }

    private class FifaRecord
    {
        public string? FifaId { get; set; }
        public string? Name { get; set; }
        public string? Age { get; set; }
        public string? Nationality { get; set; }
        public string? Overall { get; set; }
        public string? Potential { get; set; }
        public string? Club { get; set; }
        public string? Position { get; set; }
        public string? JerseyNumber { get; set; }
    }

    private sealed class FifaPlayerMap : ClassMap<FifaRecord>
    {
        public FifaPlayerMap()
        {
            Map(m => m.FifaId).Name("ID");
            Map(m => m.Name).Name("Name");
            Map(m => m.Age).Name("Age");
            Map(m => m.Nationality).Name("Nationality");
            Map(m => m.Overall).Name("Overall");
            Map(m => m.Potential).Name("Potential");
            Map(m => m.Club).Name("Club");
            Map(m => m.Position).Name("Position");
            Map(m => m.JerseyNumber).Name("Jersey Number");
        }
    }
}
