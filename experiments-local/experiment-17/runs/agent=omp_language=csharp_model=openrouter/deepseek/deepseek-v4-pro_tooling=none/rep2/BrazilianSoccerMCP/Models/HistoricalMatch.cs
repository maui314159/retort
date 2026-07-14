using CsvHelper.Configuration.Attributes;

namespace BrazilianSoccerMCP.Models;

public record HistoricalMatch
{
    [Name("ID")]
    public string Id { get; init; } = "";

    [Name("Data")]
    public string Data { get; init; } = "";

    [Name("Ano")]
    public int Ano { get; init; }

    [Name("Rodada")]
    public int Rodada { get; init; }

    [Name("Equipe_mandante")]
    public string EquipeMandante { get; init; } = "";

    [Name("Equipe_visitante")]
    public string EquipeVisitante { get; init; } = "";

    [Name("Gols_mandante")]
    public int? GolsMandante { get; init; }

    [Name("Gols_visitante")]
    public int? GolsVisitante { get; init; }

    [Name("Mandante_UF")]
    public string MandanteUf { get; init; } = "";

    [Name("Visitante_UF")]
    public string VisitanteUf { get; init; } = "";

    [Name("Vencedor")]
    public string Vencedor { get; init; } = "";

    [Name("Arena")]
    public string Arena { get; init; } = "";

    [Name("OBS")]
    public string Obs { get; init; } = "";
}