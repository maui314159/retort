// =============================================================================
// Context: Brazilian Soccer MCP Server — dataset loader and in-memory store.
//
// Loads all six provided CSVs from data/kaggle into normalized Match and Player
// collections held in memory. Each match CSV has its own column layout, mapped
// here into the common Match shape:
//   - Brasileirao_Matches.csv      -> Serie A, has state suffixes + round
//   - Brazilian_Cup_Matches.csv    -> Copa do Brasil, cup round
//   - Libertadores_Matches.csv     -> Libertadores, stage; country-suffixed names
//   - BR-Football-Dataset.csv      -> tournament column maps to Serie A/B/C / Copa
//   - novo_campeonato_brasileiro   -> historical Serie A, Brazilian date + arena
//   - fifa_data.csv                -> Player rows
//
// Construction is via SoccerData.Load(dataRoot); FindDataRoot() walks up from a
// start directory to locate the data/kaggle folder so the loader works from the
// MCP host, the test runner, or an arbitrary cwd.
// =============================================================================
namespace BrazilianSoccer.Core;

public sealed class SoccerData
{
    public IReadOnlyList<Match> Matches { get; }
    public IReadOnlyList<Player> Players { get; }

    private SoccerData(IReadOnlyList<Match> matches, IReadOnlyList<Player> players)
    {
        Matches = matches;
        Players = players;
    }

    public static SoccerData Load(string dataRoot)
    {
        var kaggle = ResolveKaggleDir(dataRoot);
        var matches = new List<Match>(24_000);

        LoadBrasileirao(Path.Combine(kaggle, "Brasileirao_Matches.csv"), matches);
        LoadCup(Path.Combine(kaggle, "Brazilian_Cup_Matches.csv"), matches);
        LoadLibertadores(Path.Combine(kaggle, "Libertadores_Matches.csv"), matches);
        LoadBrFootball(Path.Combine(kaggle, "BR-Football-Dataset.csv"), matches);
        LoadNovo(Path.Combine(kaggle, "novo_campeonato_brasileiro.csv"), matches);

        var deduped = Deduplicate(matches);
        var players = LoadPlayers(Path.Combine(kaggle, "fifa_data.csv"));
        return new SoccerData(deduped, players);
    }

    /// <summary>
    /// The five match CSVs overlap heavily: the same Série A / Copa do Brasil
    /// season appears in up to three files (e.g. 2019 Série A is in
    /// Brasileirao_Matches, novo_campeonato, AND BR-Football). Worse, the sources
    /// disagree on both team naming ("Atletico-MG" / "Atletico Mineiro" /
    /// "Atlético-MG") and on match dates (scheduled vs played, off by months), and
    /// distinct clubs collapse to the same key ("Atletico" MG vs PR). So per-match
    /// dedup is unreliable. Instead, for each (competition, season) bucket we keep
    /// rows from only the single highest-priority source that covers it. Dedicated
    /// per-competition files win; the historical file fills earlier seasons; the
    /// generic multi-competition file fills whatever neither covers. Each dedicated
    /// source is internally complete (Série A = exactly 380 matches/season), so this
    /// yields full, non-overlapping coverage without inflating standings.
    /// </summary>
    private static List<Match> Deduplicate(List<Match> matches)
    {
        // Choose the winning source per (competition, season).
        var bestRank = new Dictionary<(Competition, int), int>();
        foreach (var m in matches)
        {
            if (!m.Season.HasValue) continue;
            var bucket = (m.Competition, m.Season.Value);
            var rank = SourceRank(m.Source);
            if (!bestRank.TryGetValue(bucket, out var cur) || rank < cur)
                bestRank[bucket] = rank;
        }

        var result = new List<Match>(matches.Count);
        foreach (var m in matches)
        {
            // Seasonless rows (rare; e.g. one malformed Libertadores row) are kept as-is.
            if (!m.Season.HasValue)
            {
                result.Add(m);
                continue;
            }
            var bucket = (m.Competition, m.Season.Value);
            if (SourceRank(m.Source) == bestRank[bucket])
                result.Add(m);
        }
        return result;
    }

    /// <summary>Source preference (lower wins): dedicated per-competition files,
    /// then the historical Série A file, then the generic multi-competition file.</summary>
    private static int SourceRank(string source) => source switch
    {
        "Brasileirao_Matches.csv" => 0,
        "Brazilian_Cup_Matches.csv" => 0,
        "Libertadores_Matches.csv" => 0,
        "novo_campeonato_brasileiro.csv" => 1,
        "BR-Football-Dataset.csv" => 2,
        _ => 3,
    };

    private static string ResolveKaggleDir(string dataRoot)
    {
        // Accept either the repo root, the data dir, or the kaggle dir directly.
        foreach (var candidate in new[]
                 {
                     Path.Combine(dataRoot, "data", "kaggle"),
                     Path.Combine(dataRoot, "kaggle"),
                     dataRoot,
                 })
        {
            if (File.Exists(Path.Combine(candidate, "fifa_data.csv")))
                return candidate;
        }
        throw new DirectoryNotFoundException(
            $"Could not locate data/kaggle (with fifa_data.csv) under '{dataRoot}'.");
    }

    /// <summary>Walk up from <paramref name="start"/> (default: cwd) to find the repo data folder.</summary>
    public static string FindDataRoot(string? start = null)
    {
        var dir = new DirectoryInfo(start ?? Directory.GetCurrentDirectory());
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "data", "kaggle", "fifa_data.csv")))
                return dir.FullName;
            dir = dir.Parent;
        }
        throw new DirectoryNotFoundException(
            "Could not locate a 'data/kaggle' directory in any ancestor of " +
            (start ?? Directory.GetCurrentDirectory()));
    }

    // ---- per-file mappers -------------------------------------------------

    private static void LoadBrasileirao(string path, List<Match> outp)
    {
        if (!File.Exists(path)) return;
        var t = Csv.Load(path);
        int dt = t.Col("datetime"), h = t.Col("home_team"), a = t.Col("away_team");
        int hg = t.Col("home_goal"), ag = t.Col("away_goal"), se = t.Col("season"), rd = t.Col("round");
        foreach (var r in t.Rows)
        {
            var home = CsvTable.Cell(r, h);
            var away = CsvTable.Cell(r, a);
            if (home is null || away is null) continue;
            outp.Add(new Match
            {
                Competition = Competition.BrasileiraoSerieA,
                Date = Parsing.Date(CsvTable.Cell(r, dt)),
                Season = Parsing.Int(CsvTable.Cell(r, se)),
                Round = CsvTable.Cell(r, rd),
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamName.Key(home), AwayTeamKey = TeamName.Key(away),
                HomeGoal = Parsing.Goal(CsvTable.Cell(r, hg)),
                AwayGoal = Parsing.Goal(CsvTable.Cell(r, ag)),
                Source = "Brasileirao_Matches.csv",
            });
        }
    }

    private static void LoadCup(string path, List<Match> outp)
    {
        if (!File.Exists(path)) return;
        var t = Csv.Load(path);
        int dt = t.Col("datetime"), h = t.Col("home_team"), a = t.Col("away_team");
        int hg = t.Col("home_goal"), ag = t.Col("away_goal"), se = t.Col("season"), rd = t.Col("round");
        foreach (var r in t.Rows)
        {
            var home = CsvTable.Cell(r, h);
            var away = CsvTable.Cell(r, a);
            if (home is null || away is null) continue;
            outp.Add(new Match
            {
                Competition = Competition.CopaDoBrasil,
                Date = Parsing.Date(CsvTable.Cell(r, dt)),
                Season = Parsing.Int(CsvTable.Cell(r, se)),
                Round = CsvTable.Cell(r, rd),
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamName.Key(home), AwayTeamKey = TeamName.Key(away),
                HomeGoal = Parsing.Goal(CsvTable.Cell(r, hg)),
                AwayGoal = Parsing.Goal(CsvTable.Cell(r, ag)),
                Source = "Brazilian_Cup_Matches.csv",
            });
        }
    }

    private static void LoadLibertadores(string path, List<Match> outp)
    {
        if (!File.Exists(path)) return;
        var t = Csv.Load(path);
        int dt = t.Col("datetime"), h = t.Col("home_team"), a = t.Col("away_team");
        int hg = t.Col("home_goal"), ag = t.Col("away_goal"), se = t.Col("season"), st = t.Col("stage");
        foreach (var r in t.Rows)
        {
            var home = CsvTable.Cell(r, h);
            var away = CsvTable.Cell(r, a);
            if (home is null || away is null) continue;
            outp.Add(new Match
            {
                Competition = Competition.Libertadores,
                Date = Parsing.Date(CsvTable.Cell(r, dt)),
                Season = Parsing.Int(CsvTable.Cell(r, se)),
                Stage = CsvTable.Cell(r, st),
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamName.Key(home), AwayTeamKey = TeamName.Key(away),
                HomeGoal = Parsing.Goal(CsvTable.Cell(r, hg)),
                AwayGoal = Parsing.Goal(CsvTable.Cell(r, ag)),
                Source = "Libertadores_Matches.csv",
            });
        }
    }

    private static void LoadBrFootball(string path, List<Match> outp)
    {
        if (!File.Exists(path)) return;
        var t = Csv.Load(path);
        int tn = t.Col("tournament"), h = t.Col("home"), a = t.Col("away");
        int hg = t.Col("home_goal"), ag = t.Col("away_goal"), dt = t.Col("date");
        foreach (var r in t.Rows)
        {
            var home = CsvTable.Cell(r, h);
            var away = CsvTable.Cell(r, a);
            if (home is null || away is null) continue;
            var tour = CsvTable.Cell(r, tn);
            var date = Parsing.Date(CsvTable.Cell(r, dt));
            outp.Add(new Match
            {
                Competition = CompetitionFromTournament(tour),
                Date = date,
                Season = date?.Year,
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamName.Key(home), AwayTeamKey = TeamName.Key(away),
                HomeGoal = Parsing.Goal(CsvTable.Cell(r, hg)),
                AwayGoal = Parsing.Goal(CsvTable.Cell(r, ag)),
                Source = "BR-Football-Dataset.csv",
            });
        }
    }

    private static void LoadNovo(string path, List<Match> outp)
    {
        if (!File.Exists(path)) return;
        var t = Csv.Load(path);
        int da = t.Col("Data"), an = t.Col("Ano"), rd = t.Col("Rodada");
        int h = t.Col("Equipe_mandante"), a = t.Col("Equipe_visitante");
        int hg = t.Col("Gols_mandante"), ag = t.Col("Gols_visitante"), ar = t.Col("Arena");
        foreach (var r in t.Rows)
        {
            var home = CsvTable.Cell(r, h);
            var away = CsvTable.Cell(r, a);
            if (home is null || away is null) continue;
            outp.Add(new Match
            {
                Competition = Competition.BrasileiraoSerieA,
                Date = Parsing.Date(CsvTable.Cell(r, da)),
                Season = Parsing.Int(CsvTable.Cell(r, an)),
                Round = CsvTable.Cell(r, rd),
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamName.Key(home), AwayTeamKey = TeamName.Key(away),
                HomeGoal = Parsing.Goal(CsvTable.Cell(r, hg)),
                AwayGoal = Parsing.Goal(CsvTable.Cell(r, ag)),
                Source = "novo_campeonato_brasileiro.csv",
                Arena = CsvTable.Cell(r, ar),
            });
        }
    }

    private static Competition CompetitionFromTournament(string? tour)
    {
        if (tour is null) return Competition.Other;
        var s = tour.Trim();
        if (s.Equals("Serie A", StringComparison.OrdinalIgnoreCase)) return Competition.BrasileiraoSerieA;
        if (s.Equals("Serie B", StringComparison.OrdinalIgnoreCase)) return Competition.BrasileiraoSerieB;
        if (s.Equals("Serie C", StringComparison.OrdinalIgnoreCase)) return Competition.BrasileiraoSerieC;
        if (s.Contains("Copa do Brasil", StringComparison.OrdinalIgnoreCase)) return Competition.CopaDoBrasil;
        if (s.Contains("Libertadores", StringComparison.OrdinalIgnoreCase)) return Competition.Libertadores;
        return Competition.Other;
    }

    private static List<Player> LoadPlayers(string path)
    {
        var players = new List<Player>(18_500);
        if (!File.Exists(path)) return players;
        var t = Csv.Load(path);
        int id = t.Col("ID"), nm = t.Col("Name"), ag = t.Col("Age"), nat = t.Col("Nationality");
        int ov = t.Col("Overall"), pot = t.Col("Potential"), cl = t.Col("Club"), pos = t.Col("Position");
        int jn = t.Col("Jersey Number"), ht = t.Col("Height"), wt = t.Col("Weight");
        foreach (var r in t.Rows)
        {
            var name = CsvTable.Cell(r, nm);
            if (name is null) continue;
            var club = CsvTable.Cell(r, cl);
            players.Add(new Player
            {
                Id = Parsing.Int(CsvTable.Cell(r, id)) ?? 0,
                Name = name,
                NameKey = TeamName.FoldAccents(name).ToLowerInvariant(),
                Age = Parsing.Int(CsvTable.Cell(r, ag)),
                Nationality = CsvTable.Cell(r, nat) ?? "Unknown",
                Overall = Parsing.Int(CsvTable.Cell(r, ov)),
                Potential = Parsing.Int(CsvTable.Cell(r, pot)),
                Club = club,
                ClubKey = club is null ? null : TeamName.Key(club),
                Position = CsvTable.Cell(r, pos),
                JerseyNumber = CsvTable.Cell(r, jn),
                Height = CsvTable.Cell(r, ht),
                Weight = CsvTable.Cell(r, wt),
            });
        }
        return players;
    }
}
