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
}

export interface CupMatch {
  round: string;
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
}

export interface LibertadoresMatch {
  datetime: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  stage: string;
}

export interface ExtendedMatch {
  tournament: string;
  home: string;
  away: string;
  home_goal: number;
  away_goal: number;
  home_corner: number;
  away_corner: number;
  home_attack: number;
  away_attack: number;
  home_shots: number;
  away_shots: number;
  time: string;
  date: string;
  ht_result: string;
  at_result: string;
  total_corners: number;
}

export interface HistoricalMatch {
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
  JerseyNumber: string;
  Height: string;
  Weight: string;
  Crossing: number;
  Finishing: number;
  Dribbling: number;
  Value: string;
  Wage: string;
}

export interface NormalizedMatch {
  date: string;
  home_team: string;
  away_team: string;
  home_goal: number;
  away_goal: number;
  season: number;
  competition: string;
  round?: string | number;
  stage?: string;
  extra?: Record<string, unknown>;
}

export interface TeamStats {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
}
