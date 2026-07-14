// =============================================================================
// File:    DataLoaderTests.cs
// Project: BrazilianSoccer.Tests
// Purpose: BDD tests for parsing and cross-source deduplication, exercised
//          against synthetic CSVs written to a temp directory (fast, isolated)
//          and against the real corpus via the shared fixture.
// Context: Verifies the spec's data-quality requirements: multiple date
//          formats parse, every source maps onto the unified Match model, and
//          overlapping Série A sources collapse to a single fixture (3pts/win
//          standings stay sane). Synthetic CSVs keep the dedup assertion exact.
// =============================================================================

using BrazilianSoccer.Core;

namespace BrazilianSoccer.Tests;

public class DataLoaderTests : IDisposable
{
    private readonly string _dir;

    public DataLoaderTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "soccer_test_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_dir);
    }

    public void Dispose() => Directory.Delete(_dir, recursive: true);

    private void Write(string file, string content) =>
        File.WriteAllText(Path.Combine(_dir, file), content);

    [Fact]
    public void Given_SameFixtureInThreeSources_When_Loaded_Then_CollapsedToOne()
    {
        // Given the same Série A fixture in all three overlapping sources,
        // with the +/-1 day date drift the real data exhibits.
        Write("Brasileirao_Matches.csv",
            "\"datetime\",\"home_team\",\"home_team_state\",\"away_team\",\"away_team_state\",\"home_goal\",\"away_goal\",\"season\",\"round\"\n" +
            "2019-05-26 16:00:00,\"Flamengo-RJ\",\"RJ\",\"Atletico-PR\",\"PR\",3,2,2019,7\n");
        Write("novo_campeonato_brasileiro.csv",
            "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n" +
            "2019.07.0001,26/05/2019,2019,7,Flamengo,Athletico-PR,3,2,RJ,PR,Mandante,Maracana,\n");
        Write("BR-Football-Dataset.csv",
            "tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners\n" +
            "Serie A,Flamengo,3.0,2.0,Athletico Paranaense,5.0,3.0,100.0,80.0,12.0,7.0,16:00:00,2019-05-27,1.0,-1.0,WON,LOST,8.0\n");

        // When
        var dataset = DataLoader.LoadAll(_dir);

        // Then a single merged match remains, carrying the extended stats from
        // BR-Football and the venue from the historical source.
        Assert.Single(dataset.Matches);
        var m = dataset.Matches[0];
        Assert.Equal(3, m.HomeGoals);
        Assert.Equal(2, m.AwayGoals);
        Assert.Equal(12, m.HomeShots);     // merged from BR-Football
        Assert.Equal("Maracana", m.Venue); // merged from historical
    }

    [Fact]
    public void Given_TwoLegCupTie_When_Loaded_Then_BothLegsKept()
    {
        // Given a home-and-away cup tie (reversed home/away), which must NOT
        // be treated as one fixture.
        Write("Brazilian_Cup_Matches.csv",
            "\"round\",\"datetime\",\"home_team\",\"away_team\",\"home_goal\",\"away_goal\",\"season\"\n" +
            "\"1\",2012-03-07 16:00:00,\"Gama - DF\",\"Ceará - CE\",0,2,2012\n" +
            "\"1\",2012-03-14 20:30:00,\"Ceará - CE\",\"Gama - DF\",1,0,2012\n");

        // When
        var dataset = DataLoader.LoadAll(_dir);

        // Then
        Assert.Equal(2, dataset.Matches.Count);
    }

    [Theory]
    [InlineData("29/03/2003", 2003, 3, 29)]
    [InlineData("2019-05-26 16:00:00", 2019, 5, 26)]
    public void Given_VariousDateFormats_When_Loaded_Then_Parsed(string raw, int y, int mo, int d)
    {
        if (raw.Contains('/'))
            Write("novo_campeonato_brasileiro.csv",
                "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n" +
                $"x,{raw},{y},1,Guarani,Vasco,4,2,SP,RJ,Mandante,Arena,\n");
        else
            Write("Brasileirao_Matches.csv",
                "\"datetime\",\"home_team\",\"home_team_state\",\"away_team\",\"away_team_state\",\"home_goal\",\"away_goal\",\"season\",\"round\"\n" +
                $"{raw},\"Santos-SP\",\"SP\",\"Bahia-BA\",\"BA\",1,0,{y},1\n");

        // When
        var dataset = DataLoader.LoadAll(_dir);

        // Then
        var date = Assert.Single(dataset.Matches).Date;
        Assert.NotNull(date);
        Assert.Equal(new DateTime(y, mo, d), date!.Value.Date);
    }

    [Fact]
    public void Given_MissingGoals_When_Loaded_Then_ScoreIsNullNotZero()
    {
        // Given a row with blank goals
        Write("Libertadores_Matches.csv",
            "\"datetime\",\"home_team\",\"away_team\",\"home_goal\",\"away_goal\",\"season\",\"stage\"\n" +
            "2013-02-12 20:15:00,\"Nacional (URU)\",\"Barcelona-EQU\",\"\",\"\",2013,\"group stage\"\n");

        // When
        var m = Assert.Single(DataLoader.LoadAll(_dir).Matches);

        // Then null score, excluded from aggregation by HasScore
        Assert.Null(m.HomeGoals);
        Assert.False(m.HasScore);
    }
}

[Collection("database")]
public class CorpusLoadTests
{
    private readonly DatabaseFixture _fx;
    public CorpusLoadTests(DatabaseFixture fx) => _fx = fx;

    [Fact]
    public void Given_AllProvidedFiles_When_Loaded_Then_MatchesAndPlayersPresent()
    {
        // Then all six files contributed data.
        Assert.True(_fx.Db.AllMatches.Count > 15000,
            $"expected a large match corpus, got {_fx.Db.AllMatches.Count}");
        Assert.Equal(18207, _fx.Db.AllPlayers.Count);
    }

    [Fact]
    public void Given_AllCompetitions_When_Loaded_Then_EachIsRepresented()
    {
        var comps = _fx.Db.AllMatches.Select(m => m.Competition).ToHashSet();
        Assert.Contains(Competition.BrasileiraoSerieA, comps);
        Assert.Contains(Competition.CopaDoBrasil, comps);
        Assert.Contains(Competition.Libertadores, comps);
    }
}
