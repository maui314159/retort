// Context block
// File: Services/TeamService.cs
// Purpose: Team-level queries for the Brazilian Soccer MCP server. Computes wins/losses/
// draws, goals for/against, win rates, and supports filtering by season, competition,
// and venue (home/away). Also produces head-to-head comparisons against the MatchService.
// Venue handling uses the TeamNameNormalizer so a team's home matches are correctly
// identified even when the raw spelling differs across files. Aggregations are O(n)
// over the in-memory match list and are well within the spec's < 2s / < 5s budgets.
// Language: C# (.NET 10). Owner: Brazilian Soccer MCP benchmark implementation.

using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Services;

/// <summary>Venue filter for team statistics.</summary>
public enum Venue
{
    All,
    Home,
    Away,
}

/// <summary>Team-level queries.</summary>
public sealed class TeamService
{
    private readonly SoccerDataStore _store;
    private readonly MatchService _matches;
    public TeamNameNormalizer Normalizer => _store.Normalizer;

    public TeamService(SoccerDataStore store, MatchService matches)
    {
        _store = store;
        _matches = matches;
    }

    /// <summary>Computes team statistics with optional filters.</summary>
    public TeamStats GetTeamStats(
        string team,
        int? season = null,
        Competition? competition = null,
        Venue venue = Venue.All)
    {
        var matches = _matches.SearchMatches(team: team, season: season, competition: competition);
        var norm = Normalizer.Normalize(team);
        int played = 0, wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
        foreach (var m in matches)
        {
            bool isHome = Normalizer.Matches(m.Home, norm);
            bool isAway = Normalizer.Matches(m.Away, norm);
            if (venue == Venue.Home && !isHome) continue;
            if (venue == Venue.Away && !isAway) continue;

            int teamGoals = isHome ? m.HomeGoal : m.AwayGoal;
            int oppGoals = isHome ? m.AwayGoal : m.HomeGoal;
            played++;
            gf += teamGoals;
            ga += oppGoals;
            if (teamGoals > oppGoals) wins++;
            else if (teamGoals < oppGoals) losses++;
            else draws++;
        }
        double winRate = played == 0 ? 0 : (double)wins / played * 100.0;
        return new TeamStats(norm, season, competition, venue, played, wins, draws, losses, gf, ga, winRate);
    }

    /// <summary>Compares two teams head-to-head plus their full records.</summary>
    public TeamComparison CompareTeams(string a, string b, int? season = null, Competition? competition = null)
    {
        var h2h = _matches.HeadToHead(a, b);
        var statsA = GetTeamStats(a, season, competition);
        var statsB = GetTeamStats(b, season, competition);
        return new TeamComparison(statsA, statsB, h2h);
    }
}

/// <summary>Aggregated team statistics.</summary>
public sealed record TeamStats(
    string Team,
    int? Season,
    Competition? Competition,
    Venue Venue,
    int Played,
    int Wins,
    int Draws,
    int Losses,
    int GoalsFor,
    int GoalsAgainst,
    double WinRate)
{
    public int GoalDifference => GoalsFor - GoalsAgainst;
}

/// <summary>Comparison of two teams.</summary>
public sealed record TeamComparison(
    TeamStats TeamA,
    TeamStats TeamB,
    HeadToHeadResult HeadToHead);
