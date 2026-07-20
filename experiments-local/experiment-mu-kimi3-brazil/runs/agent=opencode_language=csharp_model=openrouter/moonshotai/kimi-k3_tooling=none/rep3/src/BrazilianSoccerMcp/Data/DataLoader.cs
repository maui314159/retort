using System.Globalization;

namespace BrazilianSoccerMcp.Data;

/// <summary>
/// Loads all six Kaggle CSV files into a unified, deduplicated in-memory dataset.
///
/// The five match files overlap (e.g. the 2019 season appears in three of them), so a
/// source-priority rule is applied per (competition, season): the season is taken from
/// exactly one authoritative file. This yields a duplicate-free history covering
/// Brasileirão Série A 2003-2023, Copa do Brasil 2012-2023, Copa Libertadores 2013-2022
/// and Série B/C 2014-2023 — with every one of the six files contributing data.
/// </summary>
public static class DataLoader
{
    public const string SerieA = "Brasileirão Série A";
    public const string SerieB = "Brasileirão Série B";
    public const string SerieC = "Brasileirão Série C";
    public const string CopaDoBrasil = "Copa do Brasil";
    public const string Libertadores = "Copa Libertadores";

    public sealed record LoadResult(
        IReadOnlyList<Match> Matches,
        IReadOnlyList<Player> Players,
        IReadOnlyDictionary<string, int> SourceContributions,
        int TotalMatchRowsRead);

    private sealed record RawMatch(Match Match, int Priority);

    public static LoadResult Load(string dataDir)
    {
        var raw = new List<RawMatch>();
        raw.AddRange(LoadBrasileirao(Path.Combine(dataDir, "Brasileirao_Matches.csv")));
        raw.AddRange(LoadNovoCampeonato(Path.Combine(dataDir, "novo_campeonato_brasileiro.csv")));
        raw.AddRange(LoadBrazilianCup(Path.Combine(dataDir, "Brazilian_Cup_Matches.csv")));
        raw.AddRange(LoadLibertadores(Path.Combine(dataDir, "Libertadores_Matches.csv")));
        raw.AddRange(LoadBrFootball(Path.Combine(dataDir, "BR-Football-Dataset.csv")));

        var totalRows = raw.Count;

        // Per (competition, season) keep only the highest-priority (lowest number) source.
        var matches = raw
            .GroupBy(r => (r.Match.Competition, r.Match.Season))
            .SelectMany(g =>
            {
                var best = g.Min(r => r.Priority);
                return g.Where(r => r.Priority == best).Select(r => r.Match);
            })
            .OrderByDescending(m => m.Date)
            .ToList();

        var contributions = matches
            .GroupBy(m => m.Source)
            .ToDictionary(g => g.Key, g => g.Count());

        var players = LoadPlayers(Path.Combine(dataDir, "fifa_data.csv"));

        return new LoadResult(matches, players, contributions, totalRows);
    }

    // ---- match file loaders -------------------------------------------------

    private static IEnumerable<RawMatch> LoadBrasileirao(string path)
    {
        var table = CsvParser.Load(path);
        const string source = "Brasileirao_Matches.csv";
        var row = 0;
        foreach (var r in table.Rows)
        {
            row++;
            var home = Col(r, table, "home_team");
            var away = Col(r, table, "away_team");
            yield return new RawMatch(new Match
            {
                Id = $"{source}:{row}",
                Date = FlexibleDateParser.Parse(Col(r, table, "datetime")),
                Season = ParseInt(Col(r, table, "season")),
                Competition = SerieA,
                Round = NullIfEmpty(Col(r, table, "round")) is { } rd ? $"Round {rd}" : null,
                HomeTeam = home,
                AwayTeam = away,
                HomeKey = TeamNameNormalizer.CanonKey(home),
                AwayKey = TeamNameNormalizer.CanonKey(away),
                HomeGoals = ParseGoals(Col(r, table, "home_goal")),
                AwayGoals = ParseGoals(Col(r, table, "away_goal")),
                Source = source,
            }, 1);
        }
    }

    private static IEnumerable<RawMatch> LoadNovoCampeonato(string path)
    {
        var table = CsvParser.Load(path);
        const string source = "novo_campeonato_brasileiro.csv";
        var row = 0;
        foreach (var r in table.Rows)
        {
            row++;
            var home = Col(r, table, "Equipe_mandante");
            var away = Col(r, table, "Equipe_visitante");
            yield return new RawMatch(new Match
            {
                Id = $"{source}:{row}",
                Date = FlexibleDateParser.Parse(Col(r, table, "Data")),
                Season = ParseInt(Col(r, table, "Ano")),
                Competition = SerieA,
                Round = NullIfEmpty(Col(r, table, "Rodada")) is { } rd ? $"Round {rd}" : null,
                HomeTeam = home,
                AwayTeam = away,
                HomeKey = TeamNameNormalizer.CanonKey(home),
                AwayKey = TeamNameNormalizer.CanonKey(away),
                HomeGoals = ParseGoals(Col(r, table, "Gols_mandante")),
                AwayGoals = ParseGoals(Col(r, table, "Gols_visitante")),
                Source = source,
                Arena = NullIfEmpty(Col(r, table, "Arena")),
            }, 2);
        }
    }

    private static IEnumerable<RawMatch> LoadBrazilianCup(string path)
    {
        var table = CsvParser.Load(path);
        const string source = "Brazilian_Cup_Matches.csv";
        var row = 0;
        foreach (var r in table.Rows)
        {
            row++;
            var home = Col(r, table, "home_team");
            var away = Col(r, table, "away_team");
            yield return new RawMatch(new Match
            {
                Id = $"{source}:{row}",
                Date = FlexibleDateParser.Parse(Col(r, table, "datetime")),
                Season = ParseInt(Col(r, table, "season")),
                Competition = CopaDoBrasil,
                Round = NullIfEmpty(Col(r, table, "round")) is { } rd ? $"Round {rd}" : null,
                HomeTeam = home,
                AwayTeam = away,
                HomeKey = TeamNameNormalizer.CanonKey(home),
                AwayKey = TeamNameNormalizer.CanonKey(away),
                HomeGoals = ParseGoals(Col(r, table, "home_goal")),
                AwayGoals = ParseGoals(Col(r, table, "away_goal")),
                Source = source,
            }, 1);
        }
    }

    private static IEnumerable<RawMatch> LoadLibertadores(string path)
    {
        var table = CsvParser.Load(path);
        const string source = "Libertadores_Matches.csv";
        var row = 0;
        foreach (var r in table.Rows)
        {
            row++;
            var home = Col(r, table, "home_team");
            var away = Col(r, table, "away_team");
            yield return new RawMatch(new Match
            {
                Id = $"{source}:{row}",
                Date = FlexibleDateParser.Parse(Col(r, table, "datetime")),
                Season = ParseInt(Col(r, table, "season")), // "NA" -> null
                Competition = Libertadores,
                Round = NullIfEmpty(Col(r, table, "stage")),
                HomeTeam = home,
                AwayTeam = away,
                HomeKey = TeamNameNormalizer.CanonKey(home),
                AwayKey = TeamNameNormalizer.CanonKey(away),
                HomeGoals = ParseGoals(Col(r, table, "home_goal")),
                AwayGoals = ParseGoals(Col(r, table, "away_goal")),
                Source = source,
            }, 1);
        }
    }

    private static IEnumerable<RawMatch> LoadBrFootball(string path)
    {
        var table = CsvParser.Load(path);
        const string source = "BR-Football-Dataset.csv";
        var row = 0;
        foreach (var r in table.Rows)
        {
            row++;
            var competition = Col(r, table, "tournament") switch
            {
                "Serie A" => SerieA,
                "Serie B" => SerieB,
                "Serie C" => SerieC,
                "Copa do Brasil" => CopaDoBrasil,
                var other => string.IsNullOrWhiteSpace(other) ? "Unknown" : other,
            };
            var home = Col(r, table, "home");
            var away = Col(r, table, "away");
            var date = FlexibleDateParser.Parse(Col(r, table, "date"));
            yield return new RawMatch(new Match
            {
                Id = $"{source}:{row}",
                Date = date,
                Season = date?.Year,
                Competition = competition,
                Round = null,
                HomeTeam = home,
                AwayTeam = away,
                HomeKey = TeamNameNormalizer.CanonKey(home),
                AwayKey = TeamNameNormalizer.CanonKey(away),
                HomeGoals = ParseGoals(Col(r, table, "home_goal")),
                AwayGoals = ParseGoals(Col(r, table, "away_goal")),
                Source = source,
            }, 9);
        }
    }

    // ---- player loader --------------------------------------------------------

    private static IReadOnlyList<Player> LoadPlayers(string path)
    {
        var table = CsvParser.Load(path);
        var players = new List<Player>(table.Rows.Count);
        foreach (var r in table.Rows)
        {
            var id = ParseInt(Col(r, table, "ID"));
            var name = Col(r, table, "Name");
            if (id is null || string.IsNullOrWhiteSpace(name))
                continue;
            var club = NullIfEmpty(Col(r, table, "Club"));
            players.Add(new Player
            {
                Id = id.Value,
                Name = name,
                Age = ParseInt(Col(r, table, "Age")),
                Nationality = NullIfEmpty(Col(r, table, "Nationality")),
                Overall = ParseInt(Col(r, table, "Overall")),
                Potential = ParseInt(Col(r, table, "Potential")),
                Club = club,
                ClubKey = club is null ? null : TeamNameNormalizer.CanonKey(club),
                Position = NullIfEmpty(Col(r, table, "Position")),
                JerseyNumber = ParseInt(Col(r, table, "Jersey Number")),
            });
        }
        return players;
    }

    // ---- helpers --------------------------------------------------------------

    private static string Col(string[] row, CsvParser.CsvTable table, string name) =>
        CsvParser.Get(row, table.ColumnIndex(name));

    internal static int? ParseGoals(string raw)
    {
        var s = raw.Trim().Trim('"');
        if (s.Length == 0 || s is "NA" or "NaN")
            return null;
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i))
            return i;
        if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var d))
            return (int)Math.Round(d);
        return null;
    }

    internal static int? ParseInt(string raw)
    {
        var s = raw.Trim().Trim('"');
        return int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i) ? i : null;
    }

    private static string? NullIfEmpty(string s) => string.IsNullOrWhiteSpace(s) ? null : s;
}
