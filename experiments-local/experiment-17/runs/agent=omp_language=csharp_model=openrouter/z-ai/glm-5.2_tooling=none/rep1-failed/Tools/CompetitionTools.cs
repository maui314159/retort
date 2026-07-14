// ============================================================================
// File: Tools/CompetitionTools.cs
// ----------------------------------------------------------------------------
// Context: MCP tools for the "Competition Queries" category: standings
// (points table calculated from match results), season summary, champion, and
// relegated teams. Standings are meaningful for round-robin leagues
// (Brasileirão Serie A); for cups we list matches by stage instead.
// ============================================================================

using System.ComponentModel;
using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Data;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class CompetitionTools
{
    private readonly SoccerDataStore _store;
    public CompetitionTools(SoccerDataStore store) => _store = store;

    /// <summary>Standings table for a league competition season.</summary>
    [McpServerTool, Description(
        "Calculate standings for a league competition season (e.g. Brasileirão 2019) " +
        "from match results. 3 points per win, 1 per draw. Marks champion and " +
        "relegated teams. For cup competitions, lists matches by stage instead.")]
    public string Standings(
        [Description("Competition, e.g. Brasileirão.")] string competition,
        [Description("Season year, e.g. 2019.")] int season)
    {
        var standings = _store.Standings(competition, season);
        if (standings.Count == 0)
        {
            // Fall back to listing the season's matches grouped by stage/round.
            return ListSeasonMatches(competition, season);
        }
        return Formatting.FormatStandings(standings,
            $"{season} {competition} Standings (calculated from matches):");
    }

    /// <summary>Who won a league season.</summary>
    [McpServerTool, Description(
        "Return the champion of a league competition season (top of the calculated standings).")]
    public string Champion(
        [Description("Competition, e.g. Brasileirão.")] string competition,
        [Description("Season year.")] int season)
    {
        var standings = _store.Standings(competition, season);
        if (standings.Count == 0)
            return $"No standings data for {competition} {season}.";
        var champ = standings[0];
        return $"The {season} {competition} champion (by calculated standings) is {champ.Team} " +
               $"with {champ.Points} pts ({champ.Wins}W, {champ.Draws}D, {champ.Losses}L).";
    }

    /// <summary>Relegated teams (bottom 4) of a league season.</summary>
    [McpServerTool, Description(
        "Return the bottom four teams of a league competition season (the relegated teams).")]
    public string RelegatedTeams(
        [Description("Competition, e.g. Brasileirão.")] string competition,
        [Description("Season year.")] int season)
    {
        var standings = _store.Standings(competition, season);
        if (standings.Count < 4)
            return $"Not enough teams in {competition} {season} to determine relegation.";
        var relegated = standings.TakeLast(4).Reverse().ToList();
        var sb = new StringBuilder();
        sb.AppendLine($"Relegated from {competition} {season}:");
        foreach (var r in relegated)
            sb.AppendLine($"- {r.Team} ({r.Points} pts, {r.Wins}W {r.Draws}D {r.Losses}L)");
        return sb.ToString().TrimEnd();
    }

    private string ListSeasonMatches(string competition, int season)
    {
        var matches = _store.Matches
            .Where(m => SoccerDataStore.CompetitionMatches(m.Competition, competition) && m.Season == season)
            .OrderBy(m => m.Date)
            .ToList();

        if (matches.Count == 0)
            return $"No matches found for {competition} {season}.";

        var sb = new StringBuilder();
        sb.AppendLine($"{season} {competition} ({matches.Count} matches on file):");
        var byStage = matches.GroupBy(m => m.Stage ?? m.Round ?? "Match");
        foreach (var grp in byStage)
        {
            sb.AppendLine($"  [{grp.Key}]");
            foreach (var m in grp.Take(30))
                sb.AppendLine("  " + Formatting.FormatMatch(m));
        }
        return sb.ToString().TrimEnd();
    }
}
