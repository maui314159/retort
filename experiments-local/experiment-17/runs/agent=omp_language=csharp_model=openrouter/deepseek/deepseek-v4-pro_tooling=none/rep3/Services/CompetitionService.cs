using System.Text;
using BrazilianSoccerMCP.Models;

namespace BrazilianSoccerMCP.Services;

/// <summary>
/// Competition queries: league standings, season champions, relegation.
/// </summary>
public class CompetitionService
{
    private readonly List<Match> _matches;

    public CompetitionService(List<Match> matches) => _matches = matches;

    /// <summary>
    /// Calculate league standings for a given competition and season.
    /// Uses standard 3 points for win, 1 for draw.
    /// </summary>
    public List<StandingEntry> GetStandings(string competition, int season)
    {
        var matches = _matches
            .Where(m => m.Competition.Equals(competition, StringComparison.OrdinalIgnoreCase) &&
                        m.Season == season)
            .ToList();

        var teams = new Dictionary<string, StandingEntry>(StringComparer.OrdinalIgnoreCase);

        foreach (var m in matches)
        {
            if (!teams.ContainsKey(m.HomeTeam))
                teams[m.HomeTeam] = new StandingEntry { Team = m.HomeTeam };
            if (!teams.ContainsKey(m.AwayTeam))
                teams[m.AwayTeam] = new StandingEntry { Team = m.AwayTeam };

            var home = teams[m.HomeTeam];
            var away = teams[m.AwayTeam];

            home.Played++; away.Played++;
            home.GoalsFor += m.HomeGoal; home.GoalsAgainst += m.AwayGoal;
            away.GoalsFor += m.AwayGoal; away.GoalsAgainst += m.HomeGoal;

            if (m.HomeGoal > m.AwayGoal)
            {
                home.Wins++; home.Points += 3;
                away.Losses++;
            }
            else if (m.AwayGoal > m.HomeGoal)
            {
                away.Wins++; away.Points += 3;
                home.Losses++;
            }
            else
            {
                home.Draws++; home.Points++;
                away.Draws++; away.Points++;
            }
        }

        return teams.Values
            .OrderByDescending(t => t.Points)
            .ThenByDescending(t => t.GoalDifference)
            .ThenByDescending(t => t.GoalsFor)
            .ThenBy(t => t.Team)
            .Select((t, i) => { t.Position = i + 1; return t; })
            .ToList();
    }

    /// <summary>
    /// Find the champion(s) for a competition and season.
    /// </summary>
    public string? GetChampion(string competition, int season)
    {
        var standings = GetStandings(competition, season);
        return standings.FirstOrDefault()?.Team;
    }

    /// <summary>
    /// Get teams that would be relegated (bottom 4 for Brasileirão).
    /// </summary>
    public List<StandingEntry> GetRelegated(string competition, int season, int relegationSpots = 4)
    {
        var standings = GetStandings(competition, season);
        return standings.OrderBy(t => t.Position).TakeLast(relegationSpots).ToList();
    }
}

public class StandingEntry
{
    public int Position { get; set; }
    public string Team { get; set; } = "";
    public int Played { get; set; }
    public int Wins { get; set; }
    public int Draws { get; set; }
    public int Losses { get; set; }
    public int GoalsFor { get; set; }
    public int GoalsAgainst { get; set; }
    public int GoalDifference => GoalsFor - GoalsAgainst;
    public int Points { get; set; }
}