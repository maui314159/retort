using System.Globalization;
using BrazilianSoccerMcp.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace BrazilianSoccerMcp.Data;

public sealed class PlayerDataLoader
{
    private List<Player>? _players;

    public IReadOnlyList<Player> Players => _players ??= LoadPlayers();

    private List<Player> LoadPlayers()
    {
        var dataDir = FindDataDirectory();
        var path = Path.Combine(dataDir, "fifa_data.csv");
        if (!File.Exists(path)) return [];

        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            MissingFieldFound = null,
            BadDataFound = null,
            HeaderValidated = null,
            PrepareHeaderForMatch = args => (args.Header ?? "").Trim('"').Replace(" ", ""),
        });

        var players = new List<Player>();
        foreach (var r in csv.GetRecords<FifaRow>())
        {
            players.Add(new Player
            {
                Id = int.TryParse(r.ID, out var id) ? id : 0,
                Name = r.Name ?? "",
                Age = int.TryParse(r.Age, out var age) ? age : 0,
                Nationality = r.Nationality ?? "",
                Overall = int.TryParse(r.Overall, out var ov) ? ov : 0,
                Potential = int.TryParse(r.Potential, out var pot) ? pot : 0,
                Club = r.Club ?? "",
                Position = r.Position ?? "",
                JerseyNumber = int.TryParse(r.JerseyNumber, out var jn) ? jn : null,
                Height = r.Height ?? "",
                Weight = r.Weight ?? "",
                Crossing = int.TryParse(r.Crossing, out var cr) ? cr : 0,
                Finishing = int.TryParse(r.Finishing, out var fi) ? fi : 0,
                HeadingAccuracy = int.TryParse(r.HeadingAccuracy, out var ha) ? ha : 0,
                ShortPassing = int.TryParse(r.ShortPassing, out var sp) ? sp : 0,
                Dribbling = int.TryParse(r.Dribbling, out var dr) ? dr : 0,
                Curve = int.TryParse(r.Curve, out var cu) ? cu : 0,
                LongPassing = int.TryParse(r.LongPassing, out var lp) ? lp : 0,
                BallControl = int.TryParse(r.BallControl, out var bc) ? bc : 0,
                Acceleration = int.TryParse(r.Acceleration, out var ac) ? ac : 0,
                SprintSpeed = int.TryParse(r.SprintSpeed, out var ss) ? ss : 0,
                Agility = int.TryParse(r.Agility, out var ag) ? ag : 0,
                Reactions = int.TryParse(r.Reactions, out var re) ? re : 0,
                Stamina = int.TryParse(r.Stamina, out var st) ? st : 0,
                Strength = int.TryParse(r.Strength, out var str) ? str : 0,
                ShotPower = int.TryParse(r.ShotPower, out var shp) ? shp : 0,
                Interceptions = int.TryParse(r.Interceptions, out var @in) ? @in : 0,
                Positioning = int.TryParse(r.Positioning, out var po) ? po : 0,
                Vision = int.TryParse(r.Vision, out var vi) ? vi : 0,
                StandingTackle = int.TryParse(r.StandingTackle, out var stt) ? stt : 0,
                SlidingTackle = int.TryParse(r.SlidingTackle, out var slt) ? slt : 0,
            });
        }
        return players;
    }

    private static string FindDataDirectory()
    {
        var dir = Directory.GetCurrentDirectory();
        for (int i = 0; i < 6; i++)
        {
            var candidate = Path.Combine(dir, "data", "kaggle");
            if (Directory.Exists(candidate))
                return candidate;
            var parent = Directory.GetParent(dir);
            if (parent is null) break;
            dir = parent.FullName;
        }
        throw new DirectoryNotFoundException("Could not find data/kaggle directory");
    }

    private sealed class FifaRow
    {
        public string? ID { get; set; }
        public string? Name { get; set; }
        public string? Age { get; set; }
        public string? Nationality { get; set; }
        public string? Overall { get; set; }
        public string? Potential { get; set; }
        public string? Club { get; set; }
        public string? Position { get; set; }
        public string? JerseyNumber { get; set; }
        public string? Height { get; set; }
        public string? Weight { get; set; }
        public string? Crossing { get; set; }
        public string? Finishing { get; set; }
        public string? HeadingAccuracy { get; set; }
        public string? ShortPassing { get; set; }
        public string? Dribbling { get; set; }
        public string? Curve { get; set; }
        public string? LongPassing { get; set; }
        public string? BallControl { get; set; }
        public string? Acceleration { get; set; }
        public string? SprintSpeed { get; set; }
        public string? Agility { get; set; }
        public string? Reactions { get; set; }
        public string? Stamina { get; set; }
        public string? Strength { get; set; }
        public string? ShotPower { get; set; }
        public string? Interceptions { get; set; }
        public string? Positioning { get; set; }
        public string? Vision { get; set; }
        public string? StandingTackle { get; set; }
        public string? SlidingTackle { get; set; }
    }
}
