export interface BrasileiraoMatch {
  datetime: string;
  home_team: string;
  home_team_state: string;
  away_team: string;
  away_team_state: string;
  home_goal: number;
  away_goal: number;
  season: number;
  round: number;
  competition: "Brasileirão";
}

export interface BrazilianCupMatch {
  round: string;
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  competition: "Copa do Brasil";
}

export interface LibertadoresMatch {
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  stage: string;
  competition: "Libertadores";
}

export interface BRFootballMatch {
  tournament: string;
  home: string;
  home_goal: number;
  away_goal: number;
  away: string;
  home_corner: number | null;
  away_corner: number | null;
  home_attack: number | null;
  away_attack: number | null;
  home_shots: number | null;
  away_shots: number | null;
  time: string;
  date: string;
  ht_result: string;
  at_result: string;
  total_corners: number | null;
  competition: string;
}

export interface NovoCampeonatoMatch {
  ID: string;
  Data: string;
  Ano: number;
  Rodada: number;
  Equipe_mandante: string;
  Equipe_visitante: string;
  Gols_mandante: number;
  Gols_visitante: number;
  Mandante_UF: string;
  Visitante_UF: string;
  Vencedor: string;
  Arena: string;
  OBS: string;
  competition: "Brasileirão Histórico";
}

export interface FifaPlayer {
  ID: number;
  Name: string;
  Age: number;
  Nationality: string;
  Overall: number;
  Potential: number;
  Club: string;
  Position: string;
  Jersey_Number: string | null;
  Height: string | null;
  Weight: string | null;
}

export type Match =
  | BrasileiraoMatch
  | BrazilianCupMatch
  | LibertadoresMatch
  | BRFootballMatch
  | NovoCampeonatoMatch;

export interface TeamStats {
  team: string;
  season?: number;
  competition?: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

export interface HeadToHeadMatchSummary {
  date: string;
  homeTeam: string;
  awayTeam: string;
  homeGoal: number;
  awayGoal: number;
  competition: string;
  season?: number;
}

export interface HeadToHead {
  team1: string;
  team2: string;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  matches: HeadToHeadMatchSummary[];
}
