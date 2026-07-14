export type Competition =
  | 'Brasileirão Serie A'
  | 'Copa do Brasil'
  | 'Copa Libertadores'
  | 'Serie B'
  | 'Serie C'
  | 'Unknown';

export type DataSource =
  | 'brasileirao'
  | 'copa_brasil'
  | 'libertadores'
  | 'br_football'
  | 'historico';

export type Venue = 'home' | 'away' | 'all';

export interface Match {
  /** ISO date YYYY-MM-DD */
  date: string;
  homeTeam: string;
  homeTeamNormalized: string;
  awayTeam: string;
  awayTeamNormalized: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: Competition;
  /** Round number or name */
  round?: string;
  /** For Libertadores: group stage / knockout etc. */
  stage?: string;
  /** Stadium name (historico dataset) */
  arena?: string;
  /** Extended stats from BR-Football-Dataset */
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
  source: DataSource;
}

export interface Player {
  id: string;
  name: string;
  age?: number;
  nationality?: string;
  overall?: number;
  potential?: number;
  club?: string;
  position?: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  /** Selected skill ratings */
  skills: Partial<{
    crossing: number;
    finishing: number;
    dribbling: number;
    shortPassing: number;
    longPassing: number;
    ballControl: number;
    acceleration: number;
    sprintSpeed: number;
    agility: number;
    reactions: number;
    shotPower: number;
    jumping: number;
    stamina: number;
    strength: number;
    longShots: number;
    aggression: number;
    interceptions: number;
    positioning: number;
    vision: number;
    composure: number;
    marking: number;
    standingTackle: number;
    slidingTackle: number;
    gkDiving: number;
    gkHandling: number;
    gkKicking: number;
    gkReflexes: number;
  }>;
}

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  points: number;
  winRate: number;
}

export interface Database {
  matches: Match[];
  players: Player[];
}
