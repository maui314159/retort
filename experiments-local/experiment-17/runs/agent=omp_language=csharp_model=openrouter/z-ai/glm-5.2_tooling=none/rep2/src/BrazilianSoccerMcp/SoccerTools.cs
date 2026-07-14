using System.Globalization;
using System.Text.Json;
using BrazilianSoccerCore.Data;
using BrazilianSoccerCore.Models;
using BrazilianSoccerCore.Queries;

namespace BrazilianSoccerMcp;

/// <summary>
/// Facade over the data layer + query engines, exposing the MCP tool set.
/// Each tool returns a human-readable text response (per the spec's answer formats).
/// </summary>
public sealed class SoccerTools
{
    private readonly MatchQueryEngine _matches;
    private readonly PlayerQueryEngine _players;
    private readonly CompetitionQueryEngine _competitions;
    private readonly StatisticsEngine _stats;

    public SoccerTools(string dataDirectory)
    {
        var loader = new DataLoader(dataDirectory);
        _matches = new MatchQueryEngine(loader.Matches);
        _players = new PlayerQueryEngine(loader.Players);
        _competitions = new CompetitionQueryEngine(loader.Matches);
        _stats = new StatisticsEngine(loader.Matches);
        TotalMatches = loader.Matches.Count;
        TotalPlayers = loader.Players.Count;
    }

    public SoccerTools(DataLoader loader)
    {
        _matches = new MatchQueryEngine(loader.Matches);
        _players = new PlayerQueryEngine(loader.Players);
        _competitions = new CompetitionQueryEngine(loader.Matches);
        _stats = new StatisticsEngine(loader.Matches);
        TotalMatches = loader.Matches.Count;
        TotalPlayers = loader.Players.Count;
    }

    public int TotalMatches { get; }
    public int TotalPlayers { get; }

    public List<ToolDef> Tools() => new()
    {
        new("search_matches", "Search matches by team, opponent, date range, competition, and/or season.", Schema.SearchMatches, SearchMatches),
        new("head_to_head", "Compare two teams head-to-head: matches, wins, draws, goals.", Schema.HeadToHead, HeadToHead),
        new("last_match", "Most recent match involving a team (or between two teams).", Schema.LastMatch, LastMatch),
        new("team_stats", "Win/draw/loss record and goals for a team, optionally by venue/competition/season.", Schema.TeamStats, TeamStats),
        new("best_home_record", "Team with the best home win rate (min 10 matches).", Schema.BestRecord, BestHomeRecord),
        new("best_away_record", "Team with the best away win rate (min 10 matches).", Schema.BestRecord, BestAwayRecord),
        new("team_competitions", "Competitions a team has appeared in across all datasets.", Schema.SingleTeam, TeamCompetitions),
        new("biggest_wins", "Biggest victories (by goal difference) in the dataset.", Schema.BiggestWins, BiggestWins),
        new("search_players", "Search FIFA players by name, nationality, club, position, min overall.", Schema.SearchPlayers, SearchPlayers),
        new("top_players", "Top-rated players, optionally filtered by nationality or club.", Schema.TopPlayers, TopPlayers),
        new("brazilians_at_brazilian_clubs", "Brazilian players grouped by Brazilian club with counts and avg rating.", Schema.NoArgs, BraziliansAtBrazilianClubs),
        new("standings", "Compute league standings (3-1-0 points) for a competition + season.", Schema.Standings, Standings),
        new("champion", "Champion (top of standings) for a competition + season.", Schema.Standings, Champion),
        new("relegated", "Bottom N teams (relegation zone) for a competition + season.", Schema.Relegated, Relegated),
        new("average_goals", "Average goals per match and home/away win rates, with optional filters.", Schema.Aggregate, AverageGoals),
        new("season_comparison", "Compare average goals and home-win rate across seasons for a competition.", Schema.SeasonComparison, SeasonComparison),
        new("top_scoring_teams", "Teams that scored the most goals in a competition + season.", Schema.Standings, TopScoringTeams),
    };

    // ---------- Handlers ----------

    private string SearchMatches(JsonElement args)
    {
        var team = args.Get("team")?.GetString();
        var opponent = args.Get("opponent")?.GetString();
        var competition = args.Get("competition")?.GetString();
        var season = args.GetInt("season");
        var limit = args.GetInt("limit") ?? 100;
        var from = args.GetDate("from_date");
        var to = args.GetDate("to_date");

        var results = _matches.SearchMatches(team, opponent, from, to, competition, season, limit);
        if (results.Count == 0)
            return "No matches found matching the criteria.";

        var lines = new List<string> { $"Found {results.Count} match(es):" };
        foreach (var m in results)
            lines.Add(FormatMatch(m));
        return string.Join('\n', lines);
    }

    private string HeadToHead(JsonElement args)
    {
        var a = args.GetStr("team_a");
        var b = args.GetStr("team_b");
        var h2h = _matches.CompareTeams(a, b);
        var recent = _matches.HeadToHeadMatches(a, b).Take(10).ToList();

        var lines = new List<string>
        {
            $"{a} vs {b} — head-to-head:",
            $"Matches: {h2h.Matches}",
            $"{a}: {h2h.TeamAWins} wins ({h2h.TeamAGoals} goals)",
            $"{b}: {h2h.TeamBWins} wins ({h2h.TeamBGoals} goals)",
            $"Draws: {h2h.Draws}",
            "",
            "Recent meetings:"
        };
        if (recent.Count == 0)
            lines.Add("  (none in dataset)");
        else
            foreach (var m in recent)
                lines.Add("  " + FormatMatch(m));
        return string.Join('\n', lines);
    }

    private string LastMatch(JsonElement args)
    {
        var team = args.Get("team")?.GetString();
        var opponent = args.Get("opponent")?.GetString();

        Match? m = team is not null && opponent is not null
            ? _matches.LastMatchBetween(team, opponent)
            : team is not null ? _matches.LastMatch(team) : null;

        if (m is null)
            return "No match found.";
        return $"Last match:\n{FormatMatch(m)}";
    }

    private string TeamStats(JsonElement args)
    {
        var team = args.GetStr("team");
        var venue = args.Get("venue")?.GetString();
        var competition = args.Get("competition")?.GetString();
        var season = args.GetInt("season");

        var s = _matches.GetTeamStats(team, venue, competition, season);
        var label = team;
        if (competition is not null) label += $" ({competition})";
        if (season is not null) label += $" {season}";
        if (venue is not null) label += $", {venue}";

        return $"{label}:\n" +
               $"- Matches: {s.Matches}\n" +
               $"- Wins: {s.Wins}, Draws: {s.Draws}, Losses: {s.Losses}\n" +
               $"- Goals For: {s.GoalsFor}, Goals Against: {s.GoalsAgainst}\n" +
               $"- Win rate: {s.WinRate}%";
    }

    private string BestHomeRecord(JsonElement args)
    {
        var competition = args.Get("competition")?.GetString();
        var season = args.GetInt("season");
        var s = _matches.BestHomeRecord(competition, season);
        return s is null
            ? "No team with enough home matches found."
            : $"Best home record: {s.Team} — {s.Wins}W {s.Draws}D {s.Losses}L in {s.Matches} home matches (win rate {s.WinRate}%).";
    }

    private string BestAwayRecord(JsonElement args)
    {
        var competition = args.Get("competition")?.GetString();
        var season = args.GetInt("season");
        var s = _matches.BestAwayRecord(competition, season);
        return s is null
            ? "No team with enough away matches found."
            : $"Best away record: {s.Team} — {s.Wins}W {s.Draws}D {s.Losses}L in {s.Matches} away matches (win rate {s.WinRate}%).";
    }

    private string TeamCompetitions(JsonElement args)
    {
        var team = args.GetStr("team");
        var comps = _matches.CompetitionsForTeam(team);
        if (comps.Count == 0)
            return $"{team} not found in any dataset.";
        return $"{team} has appeared in: {string.Join(", ", comps)}";
    }

    private string BiggestWins(JsonElement args)
    {
        var competition = args.Get("competition")?.GetString();
        var season = args.GetInt("season");
        var limit = args.GetInt("limit") ?? 10;
        var wins = _matches.BiggestWins(competition, season, limit);
        if (wins.Count == 0)
            return "No scored matches found.";

        var lines = new List<string> { "Biggest victories:" };
        for (var i = 0; i < wins.Count; i++)
        {
            var m = wins[i];
            lines.Add($"{i + 1}. {m.Date:yyyy-MM-dd}: {m.HomeTeam} {m.HomeGoal}-{m.AwayGoal} {m.AwayTeam} ({m.Competition})");
        }
        return string.Join('\n', lines);
    }

    private string SearchPlayers(JsonElement args)
    {
        var name = args.Get("name")?.GetString();
        var nationality = args.Get("nationality")?.GetString();
        var club = args.Get("club")?.GetString();
        var position = args.Get("position")?.GetString();
        var minOverall = args.GetInt("min_overall") ?? 0;
        var limit = args.GetInt("limit") ?? 50;

        List<Player> results;
        if (name is not null)
            results = _players.SearchByName(name, limit);
        else
            results = _players.SearchPlayers(nationality, club, position, minOverall, limit);

        if (results.Count == 0)
            return "No players found.";
        return string.Join('\n', results.Select(FormatPlayer));
    }

    private string TopPlayers(JsonElement args)
    {
        var limit = args.GetInt("limit") ?? 10;
        var nationality = args.Get("nationality")?.GetString();
        var club = args.Get("club")?.GetString();
        var results = _players.TopRated(limit, nationality, club);
        if (results.Count == 0)
            return "No players found.";
        var lines = new List<string> { "Top-rated players:" };
        for (var i = 0; i < results.Count; i++)
            lines.Add($"{i + 1}. {FormatPlayer(results[i])}");
        return string.Join('\n', lines);
    }

    private string BraziliansAtBrazilianClubs(JsonElement _)
    {
        var groups = _players.BrazilianPlayersAtBrazilianClubs();
        if (groups.Count == 0)
            return "No Brazilian players at Brazilian clubs found in dataset.";
        var lines = new List<string> { "Brazilian players at Brazilian clubs:" };
        foreach (var g in groups)
            lines.Add($"- {g.Club}: {g.Count} players (avg rating: {g.AvgRating})");
        return string.Join('\n', lines);
    }

    private string Standings(JsonElement args)
    {
        var competition = args.GetStr("competition");
        var season = args.GetInt("season") ?? 0;
        var table = _competitions.Standings(competition, season);
        if (table.Count == 0)
            return $"No standings data for {competition} {season}.";

        var lines = new List<string> { $"{season} {competition} Standings:" };
        foreach (var r in table)
        {
            var champ = r.Position == 1 ? " - Champion" : "";
            lines.Add($"{r.Position}. {r.Team} - {r.Points} pts ({r.Wins}W, {r.Draws}D, {r.Losses}L){champ}");
        }
        return string.Join('\n', lines);
    }

    private string Champion(JsonElement args)
    {
        var competition = args.GetStr("competition");
        var season = args.GetInt("season") ?? 0;
        var champ = _competitions.Champion(competition, season);
        return champ is null
            ? $"No standings data for {competition} {season}."
            : $"{season} {competition} champion: {champ.Team} ({champ.Points} pts, {champ.Wins}W {champ.Draws}D {champ.Losses}L)";
    }

    private string Relegated(JsonElement args)
    {
        var competition = args.GetStr("competition");
        var season = args.GetInt("season") ?? 0;
        var count = args.GetInt("count") ?? 4;
        var bottom = _competitions.Relegated(competition, season, count);
        if (bottom.Count == 0)
            return $"No standings data for {competition} {season}.";
        var lines = new List<string> { $"Relegation zone ({season} {competition}):" };
        foreach (var r in bottom)
            lines.Add($"{r.Position}. {r.Team} - {r.Points} pts");
        return string.Join('\n', lines);
    }

    private string TopScoringTeams(JsonElement args)
    {
        var competition = args.GetStr("competition");
        var season = args.GetInt("season") ?? 0;
        var limit = args.GetInt("limit") ?? 10;
        var teams = _competitions.TopScoringTeams(competition, season, limit);
        if (teams.Count == 0)
            return $"No data for {competition} {season}.";
        var lines = new List<string> { $"Top scoring teams ({season} {competition}):" };
        for (var i = 0; i < teams.Count; i++)
            lines.Add($"{i + 1}. {teams[i].Team} - {teams[i].Goals} goals");
        return string.Join('\n', lines);
    }

    private string AverageGoals(JsonElement args)
    {
        var competition = args.Get("competition")?.GetString();
        var season = args.GetInt("season");
        var agg = _stats.Aggregate(competition, season);
        if (agg.Matches == 0)
            return "No scored matches found for the given filters.";
        var label = competition ?? "all competitions";
        if (season is not null) label += $" {season}";
        return $"{label}:\n" +
               $"- Matches: {agg.Matches}\n" +
               $"- Average goals per match: {agg.AverageGoalsPerMatch}\n" +
               $"- Home win rate: {agg.HomeWinRate}%\n" +
               $"- Away win rate: {agg.AwayWinRate}%\n" +
               $"- Draw rate: {agg.DrawRate}%";
    }

    private string SeasonComparison(JsonElement args)
    {
        var competition = args.GetStr("competition");
        var from = args.GetInt("from_season") ?? 0;
        var to = args.GetInt("to_season") ?? 0;
        var seasons = _stats.SeasonComparison(competition, from, to);
        if (seasons.Count == 0)
            return $"No data for {competition} between {from} and {to}.";
        var lines = new List<string> { $"{competition} season comparison:" };
        foreach (var (season, avgGoals, homeRate) in seasons)
            lines.Add($"- {season}: avg {avgGoals} goals/match, home win rate {homeRate}%");
        return string.Join('\n', lines);
    }

    // ---------- Formatting ----------

    private static string FormatMatch(Match m)
    {
        var date = m.Date == DateTime.MinValue ? "unknown date" : m.Date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        var score = m.HomeGoal is not null && m.AwayGoal is not null
            ? $"{m.HomeGoal}-{m.AwayGoal}"
            : "vs";
        var ctx = !string.IsNullOrEmpty(m.Round) ? $" Round {m.Round}" : "";
        if (!string.IsNullOrEmpty(m.Stage)) ctx = $" {m.Stage}";
        return $"- {date}: {m.HomeTeam} {score} {m.AwayTeam} ({m.Competition}{ctx})";
    }

    private static string FormatPlayer(Player p) =>
        $"{p.Name} - Overall: {p.Overall}, Position: {p.Position}, Club: {p.Club}, Nationality: {p.Nationality}";
}

/// <summary>A single MCP tool definition.</summary>
public sealed record ToolDef(
    string Name,
    string Description,
    JsonElement InputSchema,
    Func<JsonElement, string> Handler);