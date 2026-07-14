export type Competition =
  | "Brasileirao"
  | "CopaDoBrasil"
  | "Libertadores"
  | "BRFootball"
  | "BrasileiraoHistorico";

export interface NormalizedMatch {
  id: string;
  competition: Competition;
  competitionLabel: string;
  season: number;
  date: string;
  dateObj: Date | null;
  homeTeam: string;
  awayTeam: string;
  homeTeamRaw: string;
  awayTeamRaw: string;
  homeGoals: number | null;
  awayGoals: number | null;
  round?: string;
  stage?: string;
  stadium?: string;
  homeState?: string;
  awayState?: string;
  halfTimeHome?: number | null;
  halfTimeAway?: number | null;
  corners?: { home: number | null; away: number | null; total: number | null } | null;
  shots?: { home: number | null; away: number | null } | null;
  attacks?: { home: number | null; away: number | null } | null;
  winner: "home" | "away" | "draw" | null;
}

export interface PlayerRecord {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  position: string;
  jerseyNumber: number | null;
  height: string | null;
  weight: string | null;
  preferredFoot: string | null;
  value: string | null;
  wage: string | null;
  skills: Record<string, number>;
}

export interface TeamStats {
  team: string;
  competition: Competition | "All";
  season: number | "All";
  venue: "home" | "away" | "all";
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

export interface HeadToHeadRecord {
  teamA: string;
  teamB: string;
  matches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matchesList: NormalizedMatch[];
}

export interface StandingRow {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
}

export interface StandingResult {
  competition: Competition;
  season: number;
  rows: StandingRow[];
}
