// =============================================================================
// Context: Brazilian Soccer MCP Server — query engine.
//
// The analytical core sitting over SoccerData. Implements the five capability
// groups from the spec: match search (by team/date/competition/season), team
// records and per-competition stats, player search (name/nationality/club),
// competition standings calculated from match results, and aggregate statistics
// (goals per match, home win rate, biggest wins, head-to-head). All team lookups
// use normalized keys (TeamName) so naming variants resolve to the same team.
//
// Methods return plain data records; the MCP layer formats them into text. This
// keeps the engine independently testable (the BDD tests target it directly).
// =============================================================================
namespace BrazilianSoccer.Core;

/// <summary>Optional competition filter for match/stat queries.</summary>
public enum CompetitionFilter
{
    Any,
    BrasileiraoSerieA,
    BrasileiraoSerieB,
    BrasileiraoSerieC,
    CopaDoBrasil,
    Libertadores,
}

public sealed class QueryEngine
{
    private readonly SoccerData _data;

    public QueryEngine(SoccerData data) => _data = data;

    public int MatchCount => _data.Matches.Count;
    public int PlayerCount => _data.Players.Count;

    // ---- match queries ----------------------------------------------------

    /// <summary>
    /// Find matches matching the given filters. A team filter matches home OR away.
    /// When two teams are given, only matches between those two teams are returned.
    /// Results are ordered by date descending (unknown dates sort last).
    /// </summary>
    public IReadOnlyList<Match> FindMatches(
        string? team = null,
        string? opponent = null,
        int? season = null,
        DateOnly? from = null,
        DateOnly? to = null,
        CompetitionFilter competition = CompetitionFilter.Any,
        int? limit = null)
    {
        var teamKey = team is null ? null : TeamName.Key(team);
        var oppKey = opponent is null ? null : TeamName.Key(opponent);

        IEnumerable<Match> q = _data.Matches;

        if (competition != CompetitionFilter.Any)
            q = q.Where(m => m.Competition == ToCompetition(competition));

        if (season.HasValue)
            q = q.Where(m => m.Season == season.Value);

        if (from.HasValue)
            q = q.Where(m => m.Date.HasValue && m.Date.Value >= from.Value);

        if (to.HasValue)
            q = q.Where(m => m.Date.HasValue && m.Date.Value <= to.Value);

        if (teamKey is { Length: > 0 } && oppKey is { Length: > 0 })
        {
            q = q.Where(m =>
                (TeamName.Matches(m.HomeTeamKey, teamKey) && TeamName.Matches(m.AwayTeamKey, oppKey)) ||
                (TeamName.Matches(m.HomeTeamKey, oppKey) && TeamName.Matches(m.AwayTeamKey, teamKey)));
        }
        else if (teamKey is { Length: > 0 })
        {
            q = q.Where(m =>
                TeamName.Matches(m.HomeTeamKey, teamKey) || TeamName.Matches(m.AwayTeamKey, teamKey));
        }

        var result = q
            .OrderByDescending(m => m.Date ?? DateOnly.MinValue)
            .ToList();

        if (limit is > 0 && result.Count > limit)
            result = result.GetRange(0, limit.Value);

        return result;
    }

    // ---- team queries -----------------------------------------------------

    /// <summary>Aggregate a team's W/D/L and goals over the filtered match set (results-only).</summary>
    public TeamRecord TeamRecordFor(
        string team,
        int? season = null,
        CompetitionFilter competition = CompetitionFilter.Any,
        HomeAway venue = HomeAway.Both)
    {
        var key = TeamName.Key(team);
        int matches = 0, w = 0, d = 0, l = 0, gf = 0, ga = 0;
        string display = team;

        foreach (var m in _data.Matches)
        {
            if (!m.HasResult) continue;
            if (season.HasValue && m.Season != season.Value) continue;
            if (competition != CompetitionFilter.Any && m.Competition != ToCompetition(competition)) continue;

            bool isHome = TeamName.Matches(m.HomeTeamKey, key);
            bool isAway = TeamName.Matches(m.AwayTeamKey, key);
            if (!isHome && !isAway) continue;
            if (venue == HomeAway.Home && !isHome) continue;
            if (venue == HomeAway.Away && !isAway) continue;
            // A team can't be both sides; pick home if home.
            if (isHome && venue != HomeAway.Away)
            {
                display = m.HomeTeam;
                matches++;
                gf += m.HomeGoal!.Value;
                ga += m.AwayGoal!.Value;
                if (m.HomeGoal > m.AwayGoal) w++;
                else if (m.HomeGoal < m.AwayGoal) l++;
                else d++;
            }
            else if (isAway)
            {
                display = m.AwayTeam;
                matches++;
                gf += m.AwayGoal!.Value;
                ga += m.HomeGoal!.Value;
                if (m.AwayGoal > m.HomeGoal) w++;
                else if (m.AwayGoal < m.HomeGoal) l++;
                else d++;
            }
        }

        return new TeamRecord
        {
            Team = display, Matches = matches,
            Wins = w, Draws = d, Losses = l,
            GoalsFor = gf, GoalsAgainst = ga,
        };
    }

    /// <summary>Head-to-head summary between two teams across the filtered set.</summary>
    public HeadToHead HeadToHeadFor(
        string teamA, string teamB,
        int? season = null, CompetitionFilter competition = CompetitionFilter.Any)
    {
        var ka = TeamName.Key(teamA);
        var kb = TeamName.Key(teamB);
        int matches = 0, aw = 0, bw = 0, dr = 0, ag = 0, bg = 0;
        string nameA = teamA, nameB = teamB;

        foreach (var m in _data.Matches)
        {
            if (!m.HasResult) continue;
            if (season.HasValue && m.Season != season.Value) continue;
            if (competition != CompetitionFilter.Any && m.Competition != ToCompetition(competition)) continue;

            bool aHome = TeamName.Matches(m.HomeTeamKey, ka) && TeamName.Matches(m.AwayTeamKey, kb);
            bool bHome = TeamName.Matches(m.HomeTeamKey, kb) && TeamName.Matches(m.AwayTeamKey, ka);
            if (!aHome && !bHome) continue;

            matches++;
            int aGoals = aHome ? m.HomeGoal!.Value : m.AwayGoal!.Value;
            int bGoals = aHome ? m.AwayGoal!.Value : m.HomeGoal!.Value;
            if (aHome) { nameA = m.HomeTeam; nameB = m.AwayTeam; }
            else { nameA = m.AwayTeam; nameB = m.HomeTeam; }

            ag += aGoals; bg += bGoals;
            if (aGoals > bGoals) aw++;
            else if (aGoals < bGoals) bw++;
            else dr++;
        }

        return new HeadToHead
        {
            TeamA = nameA, TeamB = nameB, Matches = matches,
            TeamAWins = aw, TeamBWins = bw, Draws = dr,
            TeamAGoals = ag, TeamBGoals = bg,
        };
    }

    // ---- player queries ---------------------------------------------------

    /// <summary>Search players by name substring, nationality, and/or club, sorted by Overall desc.</summary>
    public IReadOnlyList<Player> FindPlayers(
        string? name = null,
        string? nationality = null,
        string? club = null,
        string? position = null,
        int? limit = null)
    {
        var nameKey = name is null ? null : TeamName.FoldAccents(name).ToLowerInvariant().Trim();
        var clubKey = club is null ? null : TeamName.Key(club);
        var natLower = nationality?.Trim().ToLowerInvariant();
        var posLower = position?.Trim().ToLowerInvariant();

        IEnumerable<Player> q = _data.Players;

        if (nameKey is { Length: > 0 })
            q = q.Where(p => p.NameKey.Contains(nameKey, StringComparison.Ordinal));

        if (natLower is { Length: > 0 })
            q = q.Where(p => TeamName.FoldAccents(p.Nationality).ToLowerInvariant() == natLower
                          || TeamName.FoldAccents(p.Nationality).ToLowerInvariant().Contains(natLower, StringComparison.Ordinal));

        if (clubKey is { Length: > 0 })
            q = q.Where(p => p.ClubKey is not null && TeamName.Matches(p.ClubKey, clubKey));

        if (posLower is { Length: > 0 })
            q = q.Where(p => p.Position is not null && p.Position.ToLowerInvariant() == posLower);

        var result = q
            .OrderByDescending(p => p.Overall ?? 0)
            .ThenBy(p => p.Name, StringComparer.Ordinal)
            .ToList();

        if (limit is > 0 && result.Count > limit)
            result = result.GetRange(0, limit.Value);

        return result;
    }

    // ---- competition queries ---------------------------------------------

    /// <summary>
    /// League table for a competition+season, computed from results.
    /// Sorted by points, then goal difference, then goals for, then name.
    /// </summary>
    public IReadOnlyList<StandingRow> Standings(int season, CompetitionFilter competition = CompetitionFilter.BrasileiraoSerieA)
    {
        var comp = ToCompetition(competition);
        var agg = new Dictionary<string, MutableRecord>(StringComparer.Ordinal);

        foreach (var m in _data.Matches)
        {
            if (m.Competition != comp) continue;
            if (m.Season != season) continue;
            if (!m.HasResult) continue;

            var home = GetOrAdd(agg, m.HomeTeam);
            var away = GetOrAdd(agg, m.AwayTeam);

            home.Matches++; away.Matches++;
            home.GoalsFor += m.HomeGoal!.Value; home.GoalsAgainst += m.AwayGoal!.Value;
            away.GoalsFor += m.AwayGoal!.Value; away.GoalsAgainst += m.HomeGoal!.Value;

            if (m.HomeGoal > m.AwayGoal) { home.Wins++; away.Losses++; }
            else if (m.HomeGoal < m.AwayGoal) { away.Wins++; home.Losses++; }
            else { home.Draws++; away.Draws++; }
        }

        var rows = agg.Values
            .Select(v => v.ToRecord())
            .OrderByDescending(r => r.Points)
            .ThenByDescending(r => r.GoalDifference)
            .ThenByDescending(r => r.GoalsFor)
            .ThenBy(r => r.Team, StringComparer.Ordinal)
            .Select((r, i) => new StandingRow { Team = r.Team, Position = i + 1, Record = r })
            .ToList();

        return rows;
    }

    /// <summary>Distinct seasons present for a competition, ascending.</summary>
    public IReadOnlyList<int> SeasonsFor(CompetitionFilter competition = CompetitionFilter.Any)
    {
        IEnumerable<Match> q = _data.Matches;
        if (competition != CompetitionFilter.Any)
            q = q.Where(m => m.Competition == ToCompetition(competition));
        return q.Where(m => m.Season.HasValue)
                .Select(m => m.Season!.Value)
                .Distinct()
                .OrderBy(s => s)
                .ToList();
    }

    // ---- statistics -------------------------------------------------------

    /// <summary>Aggregate statistics over the filtered match set (results only).</summary>
    public CompetitionStats Stats(int? season = null, CompetitionFilter competition = CompetitionFilter.Any)
    {
        int matches = 0, totalGoals = 0, homeWins = 0, awayWins = 0, draws = 0;
        foreach (var m in _data.Matches)
        {
            if (!m.HasResult) continue;
            if (season.HasValue && m.Season != season.Value) continue;
            if (competition != CompetitionFilter.Any && m.Competition != ToCompetition(competition)) continue;

            matches++;
            totalGoals += m.HomeGoal!.Value + m.AwayGoal!.Value;
            if (m.HomeGoal > m.AwayGoal) homeWins++;
            else if (m.HomeGoal < m.AwayGoal) awayWins++;
            else draws++;
        }

        return new CompetitionStats
        {
            Matches = matches,
            TotalGoals = totalGoals,
            HomeWins = homeWins,
            AwayWins = awayWins,
            Draws = draws,
        };
    }

    /// <summary>The biggest victories (by goal margin) in the filtered set.</summary>
    public IReadOnlyList<Match> BiggestWins(int? season = null, CompetitionFilter competition = CompetitionFilter.Any, int limit = 10)
    {
        IEnumerable<Match> q = _data.Matches.Where(m => m.HasResult);
        if (season.HasValue) q = q.Where(m => m.Season == season.Value);
        if (competition != CompetitionFilter.Any) q = q.Where(m => m.Competition == ToCompetition(competition));

        return q
            .OrderByDescending(m => Math.Abs(m.HomeGoal!.Value - m.AwayGoal!.Value))
            .ThenByDescending(m => m.HomeGoal!.Value + m.AwayGoal!.Value)
            .ThenByDescending(m => m.Date ?? DateOnly.MinValue)
            .Take(limit <= 0 ? 10 : limit)
            .ToList();
    }

    /// <summary>Teams ranked by total goals scored in the filtered set.</summary>
    public IReadOnlyList<TeamRecord> TopScorers(int? season = null, CompetitionFilter competition = CompetitionFilter.Any, int limit = 10)
    {
        var agg = new Dictionary<string, MutableRecord>(StringComparer.Ordinal);
        foreach (var m in _data.Matches)
        {
            if (!m.HasResult) continue;
            if (season.HasValue && m.Season != season.Value) continue;
            if (competition != CompetitionFilter.Any && m.Competition != ToCompetition(competition)) continue;

            var home = GetOrAdd(agg, m.HomeTeam);
            var away = GetOrAdd(agg, m.AwayTeam);
            home.Matches++; away.Matches++;
            home.GoalsFor += m.HomeGoal!.Value; home.GoalsAgainst += m.AwayGoal!.Value;
            away.GoalsFor += m.AwayGoal!.Value; away.GoalsAgainst += m.HomeGoal!.Value;
            if (m.HomeGoal > m.AwayGoal) { home.Wins++; away.Losses++; }
            else if (m.HomeGoal < m.AwayGoal) { away.Wins++; home.Losses++; }
            else { home.Draws++; away.Draws++; }
        }

        return agg.Values
            .Select(v => v.ToRecord())
            .OrderByDescending(r => r.GoalsFor)
            .ThenByDescending(r => r.GoalDifference)
            .Take(limit <= 0 ? 10 : limit)
            .ToList();
    }

    /// <summary>Teams ranked by away win rate (minimum match threshold to avoid tiny samples).</summary>
    public IReadOnlyList<TeamRecord> BestAwayRecords(int? season = null, CompetitionFilter competition = CompetitionFilter.Any, int minMatches = 5, int limit = 10)
    {
        // Aggregate away results directly, grouped by IdentityKey so distinct clubs
        // sharing a loose key (Atletico MG/PR) are not merged.
        var agg = new Dictionary<string, MutableRecord>(StringComparer.Ordinal);
        foreach (var m in _data.Matches)
        {
            if (!m.HasResult) continue;
            if (season.HasValue && m.Season != season.Value) continue;
            if (competition != CompetitionFilter.Any && m.Competition != ToCompetition(competition)) continue;

            var away = GetOrAdd(agg, m.AwayTeam);
            away.Matches++;
            away.GoalsFor += m.AwayGoal!.Value;
            away.GoalsAgainst += m.HomeGoal!.Value;
            if (m.AwayGoal > m.HomeGoal) away.Wins++;
            else if (m.AwayGoal < m.HomeGoal) away.Losses++;
            else away.Draws++;
        }

        return agg.Values
            .Select(v => v.ToRecord())
            .Where(r => r.Matches >= minMatches)
            .OrderByDescending(r => r.WinRate)
            .ThenByDescending(r => r.GoalDifference)
            .Take(limit <= 0 ? 10 : limit)
            .ToList();
    }

    // Aggregation groups by IdentityKey (keeps state/country suffix) so distinct
    // clubs that share a loose key — "Atletico-MG" vs "Atletico-PR" — stay separate.
    private static MutableRecord GetOrAdd(Dictionary<string, MutableRecord> agg, string display)
    {
        var key = TeamName.IdentityKey(display);
        if (!agg.TryGetValue(key, out var rec))
        {
            rec = new MutableRecord { Team = display };
            agg[key] = rec;
        }
        return rec;
    }

    public static Competition ToCompetition(CompetitionFilter f) => f switch
    {
        CompetitionFilter.BrasileiraoSerieA => Competition.BrasileiraoSerieA,
        CompetitionFilter.BrasileiraoSerieB => Competition.BrasileiraoSerieB,
        CompetitionFilter.BrasileiraoSerieC => Competition.BrasileiraoSerieC,
        CompetitionFilter.CopaDoBrasil => Competition.CopaDoBrasil,
        CompetitionFilter.Libertadores => Competition.Libertadores,
        _ => Competition.Other,
    };

    private sealed class MutableRecord
    {
        public string Team = "";
        public int Matches, Wins, Draws, Losses, GoalsFor, GoalsAgainst;

        public TeamRecord ToRecord() => new()
        {
            Team = Team, Matches = Matches, Wins = Wins, Draws = Draws, Losses = Losses,
            GoalsFor = GoalsFor, GoalsAgainst = GoalsAgainst,
        };
    }
}

public enum HomeAway { Both, Home, Away }

public sealed record CompetitionStats
{
    public int Matches { get; init; }
    public int TotalGoals { get; init; }
    public int HomeWins { get; init; }
    public int AwayWins { get; init; }
    public int Draws { get; init; }

    public double GoalsPerMatch => Matches == 0 ? 0d : (double)TotalGoals / Matches;
    public double HomeWinRate => Matches == 0 ? 0d : (double)HomeWins / Matches;
    public double AwayWinRate => Matches == 0 ? 0d : (double)AwayWins / Matches;
    public double DrawRate => Matches == 0 ? 0d : (double)Draws / Matches;
}
