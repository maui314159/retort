export interface Match {
  id: string;
  date: Date;
  season: number;
  competition: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  round?: string;
  stage?: string;
  arena?: string;
}

export interface Player {
  id: string;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  height?: string;
  weight?: string;
}