namespace BrazilianSoccerMcpServer.Models;

public record Match(
    string Competition,
    DateTime Date,
    int Season,
    string Round,
    string HomeTeam,
    string AwayTeam,
    int HomeGoal,
    int AwayGoal,
    string? HomeTeamState = null,
    string? AwayTeamState = null,
    string? Stage = null,
    string? Arena = null,
    int? HomeCorner = null,
    int? AwayCorner = null,
    int? HomeAttack = null,
    int? AwayAttack = null,
    int? HomeShot = null,
    int? AwayShot = null,
    string? HalfTimeResult = null,
    int? TotalCorners = null
)
{
    public string? Winner => HomeGoal > AwayGoal ? HomeTeam : (AwayGoal > HomeGoal ? AwayTeam : "Draw");
}

public record Player(
    int Id,
    string Name,
    int Age,
    string Nationality,
    int Overall,
    int Potential,
    string Club,
    string Position,
    int? JerseyNumber,
    string? Height,
    string? Weight
);

public record BrasileiraoMatchCsv(
    string datetime,
    string home_team,
    string home_team_state,
    string away_team,
    string away_team_state,
    string home_goal,
    string away_goal,
    string season,
    string round
);

public record BrazilianCupMatchCsv(
    string round,
    string datetime,
    string home_team,
    string away_team,
    string home_goal,
    string away_goal,
    string season
);

public record LibertadoresMatchCsv(
    string datetime,
    string home_team,
    string away_team,
    string home_goal,
    string away_goal,
    string season,
    string stage
);

public record BrFootballDatasetCsv(
    string tournament,
    string home,
    string home_goal,
    string away_goal,
    string away,
    string home_corner,
    string away_corner,
    string home_attack,
    string away_attack,
    string home_shots,
    string away_shots,
    string time,
    string date,
    string ht_diff,
    string at_diff,
    string ht_result,
    string at_result,
    string total_corners
);

public record NovoCampeonatoBrasileiroCsv(
    string ID,
    string Data,
    string Ano,
    string Rodada,
    string Equipe_mandante,
    string Equipe_visitante,
    string Gols_mandante,
    string Gols_visitante,
    string Mandante_UF,
    string Visitante_UF,
    string Vencedor,
    string Arena,
    string OBS
);

public record FifaDataCsv(
    string ID,
    string Name,
    string Age,
    string Nationality,
    string Overall,
    string Potential,
    string Club,
    string Position,
    string Jersey_Number,
    string Height,
    string Weight
);
