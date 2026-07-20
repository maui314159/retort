// BrazilianSoccerMcp.Core / Data / CsvLoaders.cs
// -----------------------------------------------------------------------------
// Context: Brazilian Soccer MCP server. Loads all six source CSVs from
// data/kaggle/ (see TASK.md "Provided Data") into the unified Match / Player
// model types.
// Design notes:
//   * Field access is by column INDEX, not header name. Two reasons: (a) the FIFA
//     file has an unnamed leading index column and a BOM on the first header,
//     which breaks name-based mapping; (b) index access is immune to header
//     spelling drift across file revisions. The index contract per file is
//     documented inline at each loader.
//   * Rows whose essential cells are blank (e.g. a Brasileirão row with no home
//     team) are skipped, not thrown on, so a single bad line never fails a query.
//   * Every loader opens with an explicit Encoding.UTF8 + detectEncodingFromBOM
//     so accented Portuguese ("São Paulo", "Avaí", "Grêmio") round-trips correctly
//     (TASK.md "Character Encoding" note).
// -----------------------------------------------------------------------------

using System.Globalization;
using System.Text;
using BrazilianSoccerMcp.Core.Models;
using BrazilianSoccerMcp.Core.Normalization;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Core.Data;

/// <summary>
/// Static per-file CSV loaders. Each method is independent and tolerant of malformed
/// rows so loading never aborts on a single bad line.
/// </summary>
public static class CsvLoaders
{
    // ----- match files -------------------------------------------------------

    /// <summary>
    /// Brasileirao_Matches.csv. Columns (0-indexed):
    /// 0 datetime, 1 home_team, 2 home_team_state, 3 away_team, 4 away_team_state,
    /// 5 home_goal, 6 away_goal, 7 season, 8 round.
    /// </summary>
    public static IReadOnlyList<Match> LoadBrasileirao(string path) =>
        ReadRows(path, (csv, row) =>
        {
            var home = csv.GetFieldOrNull(1);
            var away = csv.GetFieldOrNull(3);
            if (string.IsNullOrWhiteSpace(home) || string.IsNullOrWhiteSpace(away)) return null;
            return BuildMatch(
                competition: CompetitionKind.BrasileiraoSerieA,
                label: "Brasileirão Série A",
                date: DateParser.Parse(csv.GetFieldOrNull(0)),
                homeOriginal: home, awayOriginal: away,
                homeState: csv.GetFieldOrNull(2), awayState: csv.GetFieldOrNull(4),
                homeGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(5)),
                awayGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(6)),
                season: ParseHelpers.ParseInt(csv.GetFieldOrNull(7)),
                round: csv.GetFieldOrNull(8));
        });

    /// <summary>
    /// Brazilian_Cup_Matches.csv. Columns: 0 round, 1 datetime, 2 home_team,
    /// 3 away_team, 4 home_goal, 5 away_goal, 6 season.
    /// </summary>
    public static IReadOnlyList<Match> LoadCopaDoBrasil(string path) =>
        ReadRows(path, (csv, row) =>
        {
            var home = csv.GetFieldOrNull(2);
            var away = csv.GetFieldOrNull(3);
            if (string.IsNullOrWhiteSpace(home) || string.IsNullOrWhiteSpace(away)) return null;
            return BuildMatch(
                competition: CompetitionKind.CopaDoBrasil,
                label: "Copa do Brasil",
                date: DateParser.Parse(csv.GetFieldOrNull(1)),
                homeOriginal: home, awayOriginal: away,
                homeState: null, awayState: null,
                homeGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(4)),
                awayGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(5)),
                season: ParseHelpers.ParseInt(csv.GetFieldOrNull(6)),
                round: csv.GetFieldOrNull(0));
        });

    /// <summary>
    /// Libertadores_Matches.csv. Columns: 0 datetime, 1 home_team, 2 away_team,
    /// 3 home_goal, 4 away_goal, 5 season, 6 stage.
    /// </summary>
    public static IReadOnlyList<Match> LoadLibertadores(string path) =>
        ReadRows(path, (csv, row) =>
        {
            var home = csv.GetFieldOrNull(1);
            var away = csv.GetFieldOrNull(2);
            if (string.IsNullOrWhiteSpace(home) || string.IsNullOrWhiteSpace(away)) return null;
            return BuildMatch(
                competition: CompetitionKind.CopaLibertadores,
                label: "Copa Libertadores",
                date: DateParser.Parse(csv.GetFieldOrNull(0)),
                homeOriginal: home, awayOriginal: away,
                homeState: null, awayState: null,
                homeGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(3)),
                awayGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(4)),
                season: ParseHelpers.ParseInt(csv.GetFieldOrNull(5)),
                round: null,
                stage: csv.GetFieldOrNull(6));
        });

    /// <summary>
    /// novo_campeonato_brasileiro.csv (2003-2019). Columns: 0 ID, 1 Data,
    /// 2 Ano, 3 Rodada, 4 Equipe_mandante, 5 Equipe_visitante, 6 Gols_mandante,
    /// 7 Gols_visitante, 8 Mandante_UF, 9 Visitante_UF, 10 Vencedor, 11 Arena.
    /// </summary>
    public static IReadOnlyList<Match> LoadHistoricalBrasileirao(string path) =>
        ReadRows(path, (csv, row) =>
        {
            var home = csv.GetFieldOrNull(4);
            var away = csv.GetFieldOrNull(5);
            if (string.IsNullOrWhiteSpace(home) || string.IsNullOrWhiteSpace(away)) return null;
            return BuildMatch(
                competition: CompetitionKind.HistoricoBrasileirao,
                label: "Brasileirão (2003-2019)",
                date: DateParser.Parse(csv.GetFieldOrNull(1)),
                homeOriginal: home, awayOriginal: away,
                homeState: csv.GetFieldOrNull(8), awayState: csv.GetFieldOrNull(9),
                homeGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(6)),
                awayGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(7)),
                season: ParseHelpers.ParseInt(csv.GetFieldOrNull(2)),
                round: csv.GetFieldOrNull(3),
                stadium: csv.GetFieldOrNull(11));
        });

    /// <summary>
    /// BR-Football-Dataset.csv (extended, mixed tournaments). Columns: 0 tournament,
    /// 1 home, 2 home_goal, 3 away_goal, 4 away, 5 home_corner, 6 away_corner,
    /// 7 home_attack, 8 away_attack, 9 home_shots, 10 away_shots, 11 time, 12 date,
    /// 13 ht_diff, 14 at_diff, 15 ht_result, 16 at_result, 17 total_corners.
    /// </summary>
    public static IReadOnlyList<Match> LoadExtended(string path) =>
        ReadRows(path, (csv, row) =>
        {
            var home = csv.GetFieldOrNull(1);
            var away = csv.GetFieldOrNull(4);
            if (string.IsNullOrWhiteSpace(home) || string.IsNullOrWhiteSpace(away)) return null;
            var tournament = csv.GetFieldOrNull(0) ?? "Unknown";
            var comp = CompetitionResolver.Resolve(tournament);
            return BuildMatch(
                competition: comp,
                label: tournament,
                date: DateParser.Parse(csv.GetFieldOrNull(12)),
                homeOriginal: home, awayOriginal: away,
                homeState: null, awayState: null,
                homeGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(2)),
                awayGoals: ParseHelpers.ParseGoal(csv.GetFieldOrNull(3)),
                season: null,
                round: null,
                extra: new MatchExtraStats
                {
                    HomeCorners = ParseHelpers.ParseInt(csv.GetFieldOrNull(5)),
                    AwayCorners = ParseHelpers.ParseInt(csv.GetFieldOrNull(6)),
                    HomeAttacks = ParseHelpers.ParseInt(csv.GetFieldOrNull(7)),
                    AwayAttacks = ParseHelpers.ParseInt(csv.GetFieldOrNull(8)),
                    HomeShots = ParseHelpers.ParseInt(csv.GetFieldOrNull(9)),
                    AwayShots = ParseHelpers.ParseInt(csv.GetFieldOrNull(10)),
                    HalfTimeResult = csv.GetFieldOrNull(15),
                    TotalCorners = ParseHelpers.ParseInt(csv.GetFieldOrNull(17)),
                });
        });

    // ----- player file -------------------------------------------------------

    /// <summary>
    /// fifa_data.csv. Columns (0-indexed; column 0 is an unnamed row index that
    /// we skip): 1 ID, 2 Name, 3 Age, 5 Nationality, 7 Overall, 8 Potential,
    /// 9 Club, 14 Preferred Foot, 21 Position, 22 Jersey Number, 26 Height,
    /// 27 Weight, 54 Crossing, 55 Finishing, 57 ShortPassing, 59 Dribbling,
    /// 62 LongPassing, 69 ShotPower, 81 StandingTackle, 82 SlidingTackle.
    /// </summary>
    public static IReadOnlyList<Player> LoadPlayers(string path)
    {
        var players = new List<Player>();
        ReadRows(path, (csv, row) =>
        {
            var name = csv.GetFieldOrNull(2);
            if (string.IsNullOrWhiteSpace(name)) return null;
            players.Add(new Player
            {
                Id = ParseHelpers.ParseInt(csv.GetFieldOrNull(1)) ?? row,
                Name = name,
                Age = ParseHelpers.ParseInt(csv.GetFieldOrNull(3)),
                Nationality = ParseHelpers.ParseText(csv.GetFieldOrNull(5)),
                Overall = ParseHelpers.ParseRating(csv.GetFieldOrNull(7)) ?? 0,
                Potential = ParseHelpers.ParseRating(csv.GetFieldOrNull(8)),
                Club = ParseHelpers.ParseText(csv.GetFieldOrNull(9)),
                PreferredFoot = ParseHelpers.ParseText(csv.GetFieldOrNull(14)),
                Position = ParseHelpers.ParseText(csv.GetFieldOrNull(21)),
                JerseyNumber = ParseHelpers.ParseInt(csv.GetFieldOrNull(22)),
                Height = ParseHelpers.ParseText(csv.GetFieldOrNull(26)),
                Weight = ParseHelpers.ParseText(csv.GetFieldOrNull(27)),
                Crossing = ParseHelpers.ParseRating(csv.GetFieldOrNull(54)),
                Finishing = ParseHelpers.ParseRating(csv.GetFieldOrNull(55)),
                ShortPassing = ParseHelpers.ParseRating(csv.GetFieldOrNull(57)),
                Dribbling = ParseHelpers.ParseRating(csv.GetFieldOrNull(59)),
                LongPassing = ParseHelpers.ParseRating(csv.GetFieldOrNull(62)),
                ShotPower = ParseHelpers.ParseRating(csv.GetFieldOrNull(69)),
                StandingTackle = ParseHelpers.ParseRating(csv.GetFieldOrNull(81)),
                SlidingTackle = ParseHelpers.ParseRating(csv.GetFieldOrNull(82)),
            });
            return null; // return value unused for the player loader
        });
        return players;
    }

    // ----- shared plumbing ---------------------------------------------------

    private static Match BuildMatch(
        CompetitionKind competition,
        string label,
        DateTime? date,
        string homeOriginal,
        string awayOriginal,
        string? homeState,
        string? awayState,
        int? homeGoals,
        int? awayGoals,
        int? season,
        string? round,
        string? stage = null,
        string? stadium = null,
        MatchExtraStats? extra = null) =>
        new()
        {
            Competition = competition,
            CompetitionLabel = label,
            Date = date,
            HomeTeamOriginal = homeOriginal,
            HomeTeam = TeamNormalizer.Normalize(homeOriginal),
            HomeTeamState = ParseHelpers.ParseText(homeState),
            AwayTeamOriginal = awayOriginal,
            AwayTeam = TeamNormalizer.Normalize(awayOriginal),
            AwayTeamState = ParseHelpers.ParseText(awayState),
            HomeGoals = homeGoals,
            AwayGoals = awayGoals,
            Season = season,
            Round = ParseHelpers.ParseText(round),
            Stage = ParseHelpers.ParseText(stage),
            Stadium = ParseHelpers.ParseText(stadium),
            ExtraStats = extra,
        };

    /// <summary>
    /// Reads every data row of <paramref name="path"/> and maps it via
    /// <paramref name="map"/>. Malformed rows (parse exceptions) are skipped, so a
    /// single bad line never aborts the load. The CSV culture is invariant and the
    /// stream reader detects a UTF-8 BOM so accented team names round-trip.
    /// </summary>
    private static IReadOnlyList<Match> ReadRows(
        string path,
        Func<CsvReader, int, Match?> map)
    {
        var results = new List<Match>();
        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            BadDataFound = null,
            MissingFieldFound = null,
            HeaderValidated = null,
            TrimOptions = TrimOptions.Trim,
        };

        using var reader = new StreamReader(path, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false),
            detectEncodingFromByteOrderMarks: true);
        using var csv = new CsvReader(reader, config);

        // Consume the header row.
        if (!csv.Read() || !csv.ReadHeader())
            return results;

        int rowIndex = 0;
        while (csv.Read())
        {
            rowIndex++;
            try
            {
                var mapped = map(csv, rowIndex);
                if (mapped is not null)
                    results.Add(mapped);
            }
            catch
            {
                // Skip malformed row; loading must be resilient.
            }
        }
        return results;
    }

    /// <summary>
    /// Safe field accessor: returns null instead of throwing when the column index
    /// is out of range or the cell is missing.
    /// </summary>
    internal static string? GetFieldOrNull(this CsvReader csv, int index)
    {
        try
        {
            return csv.GetField(index);
        }
        catch
        {
            return null;
        }
    }
}
