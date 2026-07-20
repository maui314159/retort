namespace BrazilianSoccerMcp;

public class SoccerDatabase
{
    public List<Match> AllMatches { get; private set; } = [];
    public List<Player> Players { get; private set; } = [];

    private bool _loaded = false;
    private readonly Lock _lock = new();
    private string _dataDir = "";

    public void Initialize(string dataDir)
    {
        lock (_lock)
        {
            if (_loaded) return;
            _dataDir = dataDir;
            Load();
            _loaded = true;
        }
    }

    private void Load()
    {
        var matches = new List<Match>();

        var brasilFile = Path.Combine(_dataDir, "Brasileirao_Matches.csv");
        if (File.Exists(brasilFile))
            matches.AddRange(DataLoader.LoadBrasileiraoMatches(brasilFile));

        var cupFile = Path.Combine(_dataDir, "Brazilian_Cup_Matches.csv");
        if (File.Exists(cupFile))
            matches.AddRange(DataLoader.LoadCupMatches(cupFile));

        var libFile = Path.Combine(_dataDir, "Libertadores_Matches.csv");
        if (File.Exists(libFile))
            matches.AddRange(DataLoader.LoadLibertadoresMatches(libFile));

        var brFile = Path.Combine(_dataDir, "BR-Football-Dataset.csv");
        if (File.Exists(brFile))
            matches.AddRange(DataLoader.LoadBrFootballDataset(brFile));

        var histFile = Path.Combine(_dataDir, "novo_campeonato_brasileiro.csv");
        if (File.Exists(histFile))
            matches.AddRange(DataLoader.LoadHistoricalBrasileirao(histFile));

        AllMatches = matches;

        var fifaFile = Path.Combine(_dataDir, "fifa_data.csv");
        if (File.Exists(fifaFile))
            Players = DataLoader.LoadFifaData(fifaFile);
    }

    public IEnumerable<Match> SearchMatches(
        string? team = null,
        string? homeTeam = null,
        string? awayTeam = null,
        int? season = null,
        string? competition = null,
        DateTime? fromDate = null,
        DateTime? toDate = null)
    {
        return AllMatches.Where(m =>
        {
            if (team != null && !DataLoader.TeamMatches(m.HomeTeam, team) && !DataLoader.TeamMatches(m.AwayTeam, team))
                return false;
            if (homeTeam != null && !DataLoader.TeamMatches(m.HomeTeam, homeTeam))
                return false;
            if (awayTeam != null && !DataLoader.TeamMatches(m.AwayTeam, awayTeam))
                return false;
            if (season.HasValue && m.Season != season.Value)
                return false;
            if (competition != null && !m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase))
                return false;
            if (fromDate.HasValue && m.Date < fromDate.Value)
                return false;
            if (toDate.HasValue && m.Date > toDate.Value)
                return false;
            return true;
        });
    }

    public TeamStats CalculateTeamStats(
        string team,
        int? season = null,
        string? competition = null,
        bool? homeOnly = null)
    {
        var matches = AllMatches.Where(m =>
        {
            bool isHome = DataLoader.TeamMatches(m.HomeTeam, team);
            bool isAway = DataLoader.TeamMatches(m.AwayTeam, team);
            if (!isHome && !isAway) return false;
            if (homeOnly == true && !isHome) return false;
            if (homeOnly == false && !isAway) return false;
            if (season.HasValue && m.Season != season.Value) return false;
            if (competition != null && !m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase)) return false;
            return true;
        }).ToList();

        int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var m in matches)
        {
            bool isHome = DataLoader.TeamMatches(m.HomeTeam, team);
            int teamGoals = isHome ? m.HomeGoals : m.AwayGoals;
            int oppGoals = isHome ? m.AwayGoals : m.HomeGoals;
            gf += teamGoals; ga += oppGoals;
            if (teamGoals > oppGoals) wins++;
            else if (teamGoals == oppGoals) draws++;
            else losses++;
        }

        return new TeamStats
        {
            Team = team,
            Matches = matches.Count,
            Wins = wins,
            Draws = draws,
            Losses = losses,
            GoalsFor = gf,
            GoalsAgainst = ga,
        };
    }

    public List<TeamStats> GetStandings(int season, string competition = "Brasileirão")
    {
        var matches = AllMatches
            .Where(m => m.Season == season && m.Competition.Contains(competition, StringComparison.OrdinalIgnoreCase))
            .ToList();

        var teams = matches
            .SelectMany(m => new[] { m.HomeTeam, m.AwayTeam })
            .Distinct()
            .OrderBy(t => t)
            .ToList();

        return teams.Select(team =>
        {
            int wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
            foreach (var m in matches)
            {
                bool isHome = m.HomeTeam == team;
                bool isAway = m.AwayTeam == team;
                if (!isHome && !isAway) continue;
                int teamGoals = isHome ? m.HomeGoals : m.AwayGoals;
                int oppGoals = isHome ? m.AwayGoals : m.HomeGoals;
                gf += teamGoals; ga += oppGoals;
                if (teamGoals > oppGoals) wins++;
                else if (teamGoals == oppGoals) draws++;
                else losses++;
            }
            return new TeamStats
            {
                Team = team,
                Matches = wins + draws + losses,
                Wins = wins,
                Draws = draws,
                Losses = losses,
                GoalsFor = gf,
                GoalsAgainst = ga,
            };
        })
        .OrderByDescending(s => s.Points)
        .ThenByDescending(s => s.GoalDiff)
        .ThenByDescending(s => s.GoalsFor)
        .ToList();
    }

    public IEnumerable<Player> SearchPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? minRating = null,
        int? maxRating = null,
        int? limit = null)
    {
        var query = Players.AsEnumerable();
        if (name != null) query = query.Where(p => p.Name.Contains(name, StringComparison.OrdinalIgnoreCase));
        if (nationality != null) query = query.Where(p => p.Nationality.Contains(nationality, StringComparison.OrdinalIgnoreCase));
        if (club != null) query = query.Where(p => p.Club.Contains(club, StringComparison.OrdinalIgnoreCase));
        if (position != null) query = query.Where(p => p.Position.Contains(position, StringComparison.OrdinalIgnoreCase));
        if (minRating.HasValue) query = query.Where(p => p.Overall >= minRating.Value);
        if (maxRating.HasValue) query = query.Where(p => p.Overall <= maxRating.Value);
        query = query.OrderByDescending(p => p.Overall);
        if (limit.HasValue) query = query.Take(limit.Value);
        return query;
    }
}
