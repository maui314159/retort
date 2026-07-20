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
  competition: "Brasileirao";
}

export interface CupMatch {
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
  id: string;
  date: string;
  year: number;
  round: number;
  home_team: string;
  away_team: string;
  home_goals: number;
  away_goals: number;
  home_state: string;
  away_state: string;
  winner: string;
  arena: string;
  competition: "Brasileirao";
}

export type AnyMatch = BrasileiraoMatch | CupMatch | LibertadoresMatch;

export interface NormalizedMatch {
  datetime: string;
  home_team: string;
  home_team_normalized: string;
  away_team: string;
  away_team_normalized: string;
  home_goal: number;
  away_goal: number;
  season: number;
  competition: string;
  round?: string | number;
  stage?: string;
  arena?: string;
}

export interface FifaPlayer {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jersey_number: number;
  height: string;
  weight: string;
  crossing: number;
  finishing: number;
  dribbling: number;
  pace?: number;
  shooting?: number;
  passing?: number;
  defending?: number;
  physicality?: number;
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
  win_rate: number;
}

export interface HeadToHeadResult {
  team1: string;
  team2: string;
  total_matches: number;
  team1_wins: number;
  team2_wins: number;
  draws: number;
  team1_goals: number;
  team2_goals: number;
  matches: NormalizedMatch[];
}
