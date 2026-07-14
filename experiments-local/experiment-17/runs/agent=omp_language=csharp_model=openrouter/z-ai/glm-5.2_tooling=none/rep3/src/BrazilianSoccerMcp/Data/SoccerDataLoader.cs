// Brazilian Soccer MCP Server - Data loader
// Context: Loads all six bundled Kaggle CSVs into the unified Match/Player model
// objects, applying team-name normalisation and defensive parsing of the varied
// date formats (ISO "2012-05-19 18:30:00", Brazilian "29/03/2003", ISO date
// "2023-09-24") and score columns (ints and quoted strings like "2"). Loading
// is lazy and cached per SoccerDataLoader instance so the MCP server pays the
// parse cost once and tests can point at the real data directory.

using System.Globalization;
using BrazilianSoccerMcp.Models;

namespace BrazilianSoccerMcp.Data;

/// <summary>Loads and caches the match and player datasets from a directory.</summary>
public sealed class SoccerDataLoader
{
    private readonly string _dataDirectory;
    private IReadOnlyList<Match>? _matches;
    private IReadOnlyList<Player>? _players;

    public SoccerDataLoader(string dataDirectory)
    {
        _dataDirectory = dataDirectory;
    }

    /// <summary>All unified matches across the five match CSV files.</summary>
    public IReadOnlyList<Match> Matches => _matches ??= LoadMatches();

    /// <summary>All FIFA player records.</summary>
    public IReadOnlyList<Player> Players => _players ??= LoadPlayers();

    /// <summary>Distinct canonical team keys present in the match data.</summary>
    public IEnumerable<string> TeamKeys => Matches
        .SelectMany(m => new[] { m.HomeTeamKey, m.AwayTeamKey })
        .Where(k => !string.IsNullOrEmpty(k))
        .Distinct();

    // ---------------------------------------------------------------------
    // Match loading
    // ---------------------------------------------------------------------

    private IReadOnlyList<Match> LoadMatches()
    {
        var matches = new List<Match>();

        matches.AddRange(LoadBrasileirao());
        matches.AddRange(LoadBrazilianCup());
        matches.AddRange(LoadLibertadores());
        matches.AddRange(LoadHistoricalBrasileirao());
        matches.AddRange(LoadBrFootballDataset());

        return matches;
    }

    private static int IndexOf(string[] headers, string name)
    {
        for (int i = 0; i < headers.Length; i++)
            if (string.Equals(headers[i].Trim(), name, StringComparison.OrdinalIgnoreCase))
                return i;
        return -1;
    }

    private static string Field(string[] row, int idx) =>
        idx >= 0 && idx < row.Length ? row[idx].Trim().Trim('"') : string.Empty;

    private static int? ParseInt(string s)
    {
        if (string.IsNullOrWhiteSpace(s))
            return null;
        if (int.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var v))
            return v;
        return null;
    }

    private static DateOnly? ParseDate(string s)
    {
        if (string.IsNullOrWhiteSpace(s))
            return null;
        // ISO date-time or ISO date.
        if (DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var dt))
            return DateOnly.FromDateTime(dt);
        // Brazilian DD/MM/YYYY.
        if (DateOnly.TryParseExact(s, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out var br))
            return br;
        return null;
    }

    private IEnumerable<Match> LoadBrasileirao()
    {
        var (headers, rows) = CsvReader.Read(Path.Combine(_dataDirectory, "Brasileirao_Matches.csv"));
        int iDt = IndexOf(headers, "datetime"), iHome = IndexOf(headers, "home_team");
        int iAway = IndexOf(headers, "away_team"), iHg = IndexOf(headers, "home_goal");
        int iAg = IndexOf(headers, "away_goal"), iSeason = IndexOf(headers, "season"), iRound = IndexOf(headers, "round");

        foreach (var row in rows)
        {
            var home = Field(row, iHome); var away = Field(row, iAway);
            if (home.Length == 0 && away.Length == 0) continue;
            yield return new Match
            {
                Competition = Competition.Brasileirao,
                CompetitionLabel = "Brasileirão Serie A",
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamNormalizer.Normalize(home), AwayTeamKey = TeamNormalizer.Normalize(away),
                HomeGoal = ParseInt(Field(row, iHg)) ?? 0,
                AwayGoal = ParseInt(Field(row, iAg)) ?? 0,
                Season = ParseInt(Field(row, iSeason)),
                Date = ParseDate(Field(row, iDt)),
                Round = Field(row, iRound),
            };
        }
    }

    private IEnumerable<Match> LoadBrazilianCup()
    {
        var (headers, rows) = CsvReader.Read(Path.Combine(_dataDirectory, "Brazilian_Cup_Matches.csv"));
        int iRound = IndexOf(headers, "round"), iDt = IndexOf(headers, "datetime");
        int iHome = IndexOf(headers, "home_team"), iAway = IndexOf(headers, "away_team");
        int iHg = IndexOf(headers, "home_goal"), iAg = IndexOf(headers, "away_goal"), iSeason = IndexOf(headers, "season");

        foreach (var row in rows)
        {
            var home = Field(row, iHome); var away = Field(row, iAway);
            if (home.Length == 0 && away.Length == 0) continue;
            yield return new Match
            {
                Competition = Competition.CopaDoBrasil,
                CompetitionLabel = "Copa do Brasil",
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamNormalizer.Normalize(home), AwayTeamKey = TeamNormalizer.Normalize(away),
                HomeGoal = ParseInt(Field(row, iHg)) ?? 0,
                AwayGoal = ParseInt(Field(row, iAg)) ?? 0,
                Season = ParseInt(Field(row, iSeason)),
                Date = ParseDate(Field(row, iDt)),
                Round = Field(row, iRound),
            };
        }
    }

    private IEnumerable<Match> LoadLibertadores()
    {
        var (headers, rows) = CsvReader.Read(Path.Combine(_dataDirectory, "Libertadores_Matches.csv"));
        int iDt = IndexOf(headers, "datetime"), iHome = IndexOf(headers, "home_team");
        int iAway = IndexOf(headers, "away_team"), iHg = IndexOf(headers, "home_goal");
        int iAg = IndexOf(headers, "away_goal"), iSeason = IndexOf(headers, "season"), iStage = IndexOf(headers, "stage");

        foreach (var row in rows)
        {
            var home = Field(row, iHome); var away = Field(row, iAway);
            if (home.Length == 0 && away.Length == 0) continue;
            yield return new Match
            {
                Competition = Competition.Libertadores,
                CompetitionLabel = "Copa Libertadores",
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamNormalizer.Normalize(home), AwayTeamKey = TeamNormalizer.Normalize(away),
                HomeGoal = ParseInt(Field(row, iHg)) ?? 0,
                AwayGoal = ParseInt(Field(row, iAg)) ?? 0,
                Season = ParseInt(Field(row, iSeason)),
                Date = ParseDate(Field(row, iDt)),
                Round = Field(row, iStage),
            };
        }
    }

    private IEnumerable<Match> LoadHistoricalBrasileirao()
    {
        var (headers, rows) = CsvReader.Read(Path.Combine(_dataDirectory, "novo_campeonato_brasileiro.csv"));
        int iData = IndexOf(headers, "Data"), iHome = IndexOf(headers, "Equipe_mandante");
        int iAway = IndexOf(headers, "Equipe_visitante"), iHg = IndexOf(headers, "Gols_mandante");
        int iAg = IndexOf(headers, "Gols_visitante"), iSeason = IndexOf(headers, "Ano");
        int iRound = IndexOf(headers, "Rodada"), iArena = IndexOf(headers, "Arena");

        foreach (var row in rows)
        {
            var home = Field(row, iHome); var away = Field(row, iAway);
            if (home.Length == 0 && away.Length == 0) continue;
            yield return new Match
            {
                Competition = Competition.BrasileiraoHistorico,
                CompetitionLabel = "Brasileirão (2003-2019)",
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamNormalizer.Normalize(home), AwayTeamKey = TeamNormalizer.Normalize(away),
                HomeGoal = ParseInt(Field(row, iHg)) ?? 0,
                AwayGoal = ParseInt(Field(row, iAg)) ?? 0,
                Season = ParseInt(Field(row, iSeason)),
                Date = ParseDate(Field(row, iData)),
                Round = Field(row, iRound),
                Arena = Field(row, iArena),
            };
        }
    }

    private IEnumerable<Match> LoadBrFootballDataset()
    {
        var (headers, rows) = CsvReader.Read(Path.Combine(_dataDirectory, "BR-Football-Dataset.csv"));
        int iTourn = IndexOf(headers, "tournament"), iHome = IndexOf(headers, "home");
        int iAway = IndexOf(headers, "away"), iHg = IndexOf(headers, "home_goal");
        int iAg = IndexOf(headers, "away_goal"), iDate = IndexOf(headers, "date");

        foreach (var row in rows)
        {
            var home = Field(row, iHome); var away = Field(row, iAway);
            if (home.Length == 0 && away.Length == 0) continue;
            var tournament = Field(row, iTourn);
            // Derive season from date when present.
            var date = ParseDate(Field(row, iDate));
            int? season = date?.Year;
            yield return new Match
            {
                Competition = Competition.Other,
                CompetitionLabel = tournament.Length > 0 ? tournament : "Other",
                HomeTeam = home, AwayTeam = away,
                HomeTeamKey = TeamNormalizer.Normalize(home), AwayTeamKey = TeamNormalizer.Normalize(away),
                HomeGoal = ParseInt(Field(row, iHg)) ?? 0,
                AwayGoal = ParseInt(Field(row, iAg)) ?? 0,
                Season = season,
                Date = date,
            };
        }
    }

    // ---------------------------------------------------------------------
    // Player loading
    // ---------------------------------------------------------------------

    private IReadOnlyList<Player> LoadPlayers()
    {
        var (headers, rows) = CsvReader.Read(Path.Combine(_dataDirectory, "fifa_data.csv"));
        int iId = IndexOf(headers, "ID"), iName = IndexOf(headers, "Name"), iAge = IndexOf(headers, "Age");
        int iNat = IndexOf(headers, "Nationality"), iOvr = IndexOf(headers, "Overall"), iPot = IndexOf(headers, "Potential");
        int iClub = IndexOf(headers, "Club"), iPos = IndexOf(headers, "Position"), iJersey = IndexOf(headers, "Jersey Number");
        int iFoot = IndexOf(headers, "Preferred Foot"), iHt = IndexOf(headers, "Height"), iWt = IndexOf(headers, "Weight");
        int iVal = IndexOf(headers, "Value"), iWage = IndexOf(headers, "Wage");

        var players = new List<Player>(rows.Count);
        foreach (var row in rows)
        {
            var name = Field(row, iName);
            if (name.Length == 0) continue;
            var club = Field(row, iClub);
            players.Add(new Player
            {
                Id = ParseInt(Field(row, iId)) ?? 0,
                Name = name,
                Age = ParseInt(Field(row, iAge)) ?? 0,
                Nationality = Field(row, iNat),
                Overall = ParseInt(Field(row, iOvr)) ?? 0,
                Potential = ParseInt(Field(row, iPot)) ?? 0,
                Club = club.Length > 0 ? club : null,
                Position = Optional(Field(row, iPos)),
                JerseyNumber = ParseInt(Field(row, iJersey)),
                PreferredFoot = Optional(Field(row, iFoot)),
                Height = Optional(Field(row, iHt)),
                Weight = Optional(Field(row, iWt)),
                Value = Optional(Field(row, iVal)),
                Wage = Optional(Field(row, iWage)),
                ClubKey = club.Length > 0 ? TeamNormalizer.Normalize(club) : null,
            });
        }
        return players;
    }

    private static string? Optional(string s) => string.IsNullOrWhiteSpace(s) ? null : s;
}
