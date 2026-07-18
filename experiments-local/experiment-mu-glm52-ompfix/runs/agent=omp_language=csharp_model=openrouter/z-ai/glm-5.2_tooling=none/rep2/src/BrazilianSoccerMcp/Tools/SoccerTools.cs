// ============================================================================
// BrazilianSoccerMcp - Tools/SoccerTools.cs
//
// Context block:
//   The MCP surface. Each [McpServerTool] method validates its inputs, calls
//   SoccerQueryService, and returns a human-readable string formatted like the
//   "Example answer format" blocks in TASK.md. Tools are thin on purpose:
//   all analytics live in SoccerQueryService so tests exercise them directly
//   without the MCP host.
//
//   Competition params are free-form strings ("brasileirao", "Copa do Brasil",
//   "libertadores", "br-football", "historico") parsed case-insensitively by
//   ParseCompetition; an empty/null value means "across all competitions".
//
//   Venue params: "home", "away", or empty for either.
// ============================================================================

using System.ComponentModel;
using System.Globalization;
using BrazilianSoccerMcp.Data;
using BrazilianSoccerMcp.Models;
using ModelContextProtocol.Server;

namespace BrazilianSoccerMcp.Tools;

[McpServerToolType]
public sealed class SoccerTools
{
    private readonly SoccerQueryService _svc;
    public SoccerTools(SoccerQueryService svc) => _svc = svc;

    // ----------------------------------------------------------------------
    // Match queries
    // ----------------------------------------------------------------------

    [McpServerTool(Name = "search_matches"),
     Description("Find matches by team, opponent, competition, season and/or date range. " +
                 "competition: 'brasileirao' | 'copa_do_brasil' | 'libertadores' | 'br_football' | 'historico' (optional). " +
                 "Dates as ISO yyyy-MM-dd. team matches home or away.")]
    public string SearchMatches(
        [Description("Team name (matches home or away), e.g. 'Flamengo'. Optional.")] string? team = null,
        [Description("Opponent team name. Optional.")] string? opponent = null,
        [Description("Competition key. Optional.")] string? competition = null,
        [Description("Season year, e.g. 2023. Optional.")] int? season = null,
        [Description("From date (ISO yyyy-MM-dd). Optional.")] string? fromDate = null,
        [Description("To date (ISO yyyy-MM-dd). Optional.")] string? toDate = null,
        [Description("Max number of matches to return. Default 25.")] int limit = 25)
    {
        var matches = _svc.QueryMatches(
            team: team, opponent: opponent,
            competition: ParseCompetition(competition),
            season: season,
            fromDate: ParseDate(fromDate), toDate: ParseDate(toDate))
            .OrderByDescending(m => m.Date)
            .Take(Math.Clamp(limit, 1, 500))
            .ToList();

        if (matches.Count == 0)
            return "No matches found for the given criteria.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Found {matches.Count} match(es) (showing up to {Math.Min(matches.Count, limit)}):");
        foreach (var m in matches)
            sb.AppendLine(FormatMatch(m));
        return sb.ToString();
    }

    [McpServerTool(Name = "head_to_head"),
     Description("Head-to-head record between two teams across the dataset, with win/draw counts.")]
    public string HeadToHead(
        [Description("First team, e.g. 'Flamengo'.")] string teamA,
        [Description("Second team, e.g. 'Fluminense'.")] string teamB,
        [Description("Competition key. Optional.")] string? competition = null,
        [Description("Max matches to list. Default 50.")] int limit = 50)
    {
        if (string.IsNullOrWhiteSpace(teamA) || string.IsNullOrWhiteSpace(teamB))
            return "Both teamA and teamB are required.";

        var h2h = _svc.GetHeadToHead(teamA, teamB, ParseCompetition(competition));
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Head-to-head: {teamA} vs {teamB} ({h2h.Total} matches in dataset)");
        sb.AppendLine($"- {teamA} wins: {h2h.WinsA}");
        sb.AppendLine($"- {teamB} wins: {h2h.WinsB}");
        sb.AppendLine($"- Draws: {h2h.Draws}");
        sb.AppendLine("Matches:");
        foreach (var m in h2h.Matches.OrderByDescending(m => m.Date).Take(Math.Clamp(limit, 1, 200)))
            sb.AppendLine("  " + FormatMatch(m));
        return sb.ToString();
    }

    // ----------------------------------------------------------------------
    // Team statistics
    // ----------------------------------------------------------------------

    [McpServerTool(Name = "team_statistics"),
     Description("Win/loss/draw record and goals for a team, optionally filtered by season, competition and venue.")]
    public string TeamStatistics(
        [Description("Team name, e.g. 'Corinthians'.")] string team,
        [Description("Season year. Optional.")] int? season = null,
        [Description("Competition key. Optional.")] string? competition = null,
        [Description("Venue: 'home', 'away', or empty for either.")] string? venue = null)
    {
        if (string.IsNullOrWhiteSpace(team))
            return "Team name is required.";

        var stats = _svc.GetTeamStatistics(team, season, ParseCompetition(competition), ParseVenue(venue));
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Statistics for {stats.Team}" +
            (stats.Season.HasValue ? $" ({stats.Season})" : "") +
            (stats.Competition.HasValue ? $" [{stats.Competition}]" : "") +
            (stats.Venue != Venue.Either ? $" ({stats.Venue})" : "") + ":");
        sb.AppendLine($"- Matches: {stats.Matches}");
        sb.AppendLine($"- Wins: {stats.Wins}, Draws: {stats.Draws}, Losses: {stats.Losses}");
        sb.AppendLine($"- Goals For: {stats.GoalsFor}, Goals Against: {stats.GoalsAgainst}");
        sb.AppendLine($"- Win rate: {stats.WinRate:F1}%");
        return sb.ToString();
    }

    // ----------------------------------------------------------------------
    // Competition queries
    // ----------------------------------------------------------------------

    [McpServerTool(Name = "competition_standings"),
     Description("Calculate and return the standings for one competition season, with champion and relegation flags.")]
    public string CompetitionStandings(
        [Description("Competition key: 'brasileirao' | 'copa_do_brasil' | 'libertadores' | 'br_football' | 'historico'.")] string competition,
        [Description("Season year, e.g. 2019.")] int season)
    {
        var comp = ParseCompetition(competition);
        if (comp == null)
            return $"Unknown competition '{competition}'. Use brasileirao, copa_do_brasil, libertadores, br_football or historico.";

        var rows = _svc.GetStandings(comp.Value, season);
        if (rows.Count == 0)
            return $"No scored matches found for {comp} season {season}.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"{comp} {season} standings ({rows.Count} teams):");
        foreach (var r in rows)
        {
            var tag = r.IsChampion ? " - Champion" : r.Relegated ? " - Relegated" : "";
            sb.AppendLine($"{r.Position,2}. {r.Team,-22} {r.Points,3} pts " +
                          $"({r.Wins}W {r.Draws}D {r.Losses}L) GF {r.GoalsFor} GA {r.GoalsAgainst}{tag}");
        }
        return sb.ToString();
    }

    // ----------------------------------------------------------------------
    // Statistical analysis
    // ----------------------------------------------------------------------

    [McpServerTool(Name = "biggest_wins"),
     Description("Return the matches with the largest goal-difference margin, optionally filtered by competition.")]
    public string BiggestWins(
        [Description("Competition key. Optional.")] string? competition = null,
        [Description("Max number of results. Default 10.")] int limit = 10)
    {
        var wins = _svc.GetBiggestWins(ParseCompetition(competition), Math.Clamp(limit, 1, 200));
        if (wins.Count == 0)
            return "No scored matches found.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Biggest victories in dataset:");
        for (int i = 0; i < wins.Count; i++)
        {
            var m = wins[i];
            sb.AppendLine($"{i + 1}. {FormatDate(m.Date)}: {m.HomeTeamRaw} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeamRaw} ({m.Competition})");
        }
        return sb.ToString();
    }

    [McpServerTool(Name = "goals_overview"),
     Description("Average goals per match and home/away/draw win rates, optionally for one competition.")]
    public string GoalsOverview(
        [Description("Competition key. Optional.")] string? competition = null)
    {
        var o = _svc.GetGoalsOverview(ParseCompetition(competition));
        if (o.Matches == 0)
            return "No scored matches found for the given filter.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Goals overview{(o.Competition.HasValue ? $" ({o.Competition})" : "")}:");
        sb.AppendLine($"- Matches: {o.Matches}");
        sb.AppendLine($"- Average goals per match: {o.AverageGoalsPerMatch:F2}");
        sb.AppendLine($"- Home win rate: {o.HomeWinRate:F1}%");
        sb.AppendLine($"- Away win rate: {o.AwayWinRate:F1}%");
        sb.AppendLine($"- Draw rate: {o.DrawRate:F1}%");
        return sb.ToString();
    }

    // ----------------------------------------------------------------------
    // Player queries
    // ----------------------------------------------------------------------

    [McpServerTool(Name = "search_players"),
     Description("Search FIFA player data by name, nationality, club, position and/or overall rating range.")]
    public string SearchPlayers(
        [Description("Player name (substring, accent-insensitive). Optional.")] string? name = null,
        [Description("Nationality, e.g. 'Brazil'. Optional.")] string? nationality = null,
        [Description("Club name. Optional.")] string? club = null,
        [Description("Position code, e.g. 'ST', 'LW', 'GK', 'CDM'. Optional.")] string? position = null,
        [Description("Minimum overall rating. Optional.")] int? minOverall = null,
        [Description("Maximum overall rating. Optional.")] int? maxOverall = null,
        [Description("Max number of players to return. Default 25.")] int limit = 25)
    {
        var players = _svc.QueryPlayers(name, nationality, club, position, minOverall, maxOverall)
            .OrderByDescending(p => p.Overall ?? -1)
            .Take(Math.Clamp(limit, 1, 500))
            .ToList();

        if (players.Count == 0)
            return "No players found for the given criteria.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Found {players.Count} player(s):");
        foreach (var p in players)
            sb.AppendLine($"- {p.Name} (OVR {p.Overall?.ToString() ?? "-"}) {p.Position} | {p.Nationality} | {p.Club}");
        return sb.ToString();
    }

    [McpServerTool(Name = "top_players"),
     Description("Return the highest-rated players, optionally filtered by nationality, club and/or position.")]
    public string TopPlayers(
        [Description("Max number of players. Default 10.")] int limit = 10,
        [Description("Nationality filter, e.g. 'Brazil'. Optional.")] string? nationality = null,
        [Description("Club filter. Optional.")] string? club = null,
        [Description("Position code, e.g. 'ST'. Optional.")] string? position = null)
    {
        var players = _svc.GetTopPlayers(Math.Clamp(limit, 1, 200), nationality, club, position);
        if (players.Count == 0)
            return "No players found for the given criteria.";

        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Top-rated players:");
        for (int i = 0; i < players.Count; i++)
        {
            var p = players[i];
            sb.AppendLine($"{i + 1}. {p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}");
        }
        return sb.ToString();
    }

    // ----------------------------------------------------------------------
    // Listing helpers
    // ----------------------------------------------------------------------

    [McpServerTool(Name = "list_competitions"),
     Description("List the competitions available in the dataset with their loaded match counts.")]
    public string ListCompetitions()
    {
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Competitions available:");
        foreach (Competition c in Enum.GetValues<Competition>())
        {
            if (c == Competition.Unknown) continue;
            var count = _svc.Store.MatchCounts.TryGetValue(c, out var n) ? n : 0;
            sb.AppendLine($"- {c} (key '{CompetitionKey(c)}'): {count} matches");
        }
        sb.AppendLine($"- Players: {_svc.Store.Players.Count}");
        return sb.ToString();
    }

    [McpServerTool(Name = "list_seasons"),
     Description("List seasons available for a competition.")]
    public string ListSeasons(
        [Description("Competition key.")] string competition)
    {
        var comp = ParseCompetition(competition);
        if (comp == null) return $"Unknown competition '{competition}'.";
        var seasons = _svc.ListSeasons(comp.Value);
        return seasons.Count == 0
            ? $"No seasons found for {comp}."
            : $"Seasons for {comp}: {string.Join(", ", seasons)}";
    }

    [McpServerTool(Name = "list_teams"),
     Description("List known team names (canonical) for a competition or across all competitions.")]
    public string ListTeams(
        [Description("Competition key. Optional.")] string? competition = null,
        [Description("Substring filter. Optional.")] string? contains = null)
    {
        var teams = _svc.ListTeams(ParseCompetition(competition));
        if (!string.IsNullOrWhiteSpace(contains))
        {
            var c = contains.ToLowerInvariant();
            teams = teams.Where(t => t.Contains(c, StringComparison.OrdinalIgnoreCase)).ToList();
        }
        if (teams.Count == 0) return "No teams found.";
        var shown = teams.Take(300).ToList();
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Teams ({teams.Count} total, showing {shown.Count}):");
        foreach (var t in shown) sb.AppendLine($"- {t}");
        return sb.ToString();
    }

    // ----------------------------------------------------------------------
    // Formatting / parsing helpers
    // ----------------------------------------------------------------------

    private static string FormatMatch(Match m)
    {
        var comp = m.Competition.ToString();
        var extra = !string.IsNullOrEmpty(m.Tournament) ? $" [{m.Tournament}]" : "";
        var round = !string.IsNullOrEmpty(m.Round) ? $" R{m.Round}" :
                    !string.IsNullOrEmpty(m.Stage) ? $" {m.Stage}" : "";
        var stadium = !string.IsNullOrEmpty(m.Stadium) ? $" @ {m.Stadium}" : "";
        return $"- {FormatDate(m.Date)}: {m.HomeTeamRaw} {m.HomeGoals}-{m.AwayGoals} {m.AwayTeamRaw} ({comp}{round}{extra}{stadium})";
    }

    private static string FormatDate(DateTime? d) =>
        d.HasValue ? d.Value.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) : "date?";

    private static DateTime? ParseDate(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return DateTime.TryParseExact(s.Trim(), "yyyy-MM-dd", CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var d) ? d : null;
    }

    public static Competition? ParseCompetition(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return null;
        return s.Trim().ToLowerInvariant() switch
        {
            "brasileirao" or "serie a" or "serie-a" or "brasileirão" => Competition.Brasileirao,
            "copa_do_brasil" or "copa do brasil" or "cup" or "copa-do-brasil" => Competition.CopaDoBrasil,
            "libertadores" => Competition.Libertadores,
            "br_football" or "br-football" or "brfootball" or "br football" => Competition.BrFootball,
            "historico" or "histórico" or "historico_brasileirao" => Competition.HistoricoBrasileirao,
            _ => null,
        };
    }

    private static Venue ParseVenue(string? s)
    {
        if (string.IsNullOrWhiteSpace(s)) return Venue.Either;
        return s.Trim().ToLowerInvariant() switch
        {
            "home" or "mandante" => Venue.Home,
            "away" or "visitante" => Venue.Away,
            _ => Venue.Either,
        };
    }

    private static string CompetitionKey(Competition c) => c switch
    {
        Competition.Brasileirao => "brasileirao",
        Competition.CopaDoBrasil => "copa_do_brasil",
        Competition.Libertadores => "libertadores",
        Competition.BrFootball => "br_football",
        Competition.HistoricoBrasileirao => "historico",
        _ => "unknown",
    };
}
