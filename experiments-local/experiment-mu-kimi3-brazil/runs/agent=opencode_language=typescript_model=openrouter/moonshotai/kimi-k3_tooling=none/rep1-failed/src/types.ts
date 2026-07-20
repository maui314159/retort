/**
 * Domain model for the Brazilian Soccer knowledge graph.
 *
 * All six Kaggle CSVs are normalized into these unified types so that
 * queries can run across files without caring about the source schema.
 */

/** Competition identifiers used across the normalized dataset. */
export type Competition =
  | "Brasileirão Série A"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | "Brasileirão Série B"
  | "Brasileirão Série C"
  | string;

/** Which CSV file a record was loaded from (provenance). */
export type SourceFile =
  | "Brasileirao_Matches.csv"
  | "Brazilian_Cup_Matches.csv"
  | "Libertadores_Matches.csv"
  | "BR-Football-Dataset.csv"
  | "novo_campeonato_brasileiro.csv"
  | "fifa_data.csv";

/** A normalized match record. */
export interface Match {
  /** Unique id: `${source}#${rowIndex}` */
  id: string;
  /** ISO date (YYYY-MM-DD). Null when the source date is unparseable. */
  date: string | null;
  /** Season year (e.g. 2019). Null when unknown. */
  season: number | null;
  competition: Competition;
  /** Home team, normalized display name (state suffix stripped). */
  homeTeam: string;
  /** Away team, normalized display name. */
  awayTeam: string;
  /** Raw names as found in the file (kept for provenance/debug). */
  homeTeamRaw: string;
  awayTeamRaw: string;
  /** Canonical club keys (cross-file identity, see normalize.ts). */
  homeKey: string;
  awayKey: string;
  homeGoals: number;
  awayGoals: number;
  /** Round/stage label when present (e.g. "22", "group stage", "final"). */
  round: string | null;
  stage: string | null;
  /** Stadium when present. */
  arena: string | null;
  source: SourceFile;
  /** Extra per-source statistics (corners, shots, attacks) when available. */
  stats?: {
    homeCorners?: number;
    awayCorners?: number;
    homeShots?: number;
    awayShots?: number;
    homeAttacks?: number;
    awayAttacks?: number;
  };
}

/** A normalized player record from the FIFA database. */
export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string | null;
  position: string | null;
  jerseyNumber: number | null;
  height: string | null;
  weight: string | null;
  preferredFoot: string | null;
  /** Selected skill ratings (the CSV has ~30; we keep the headline ones). */
  skills: {
    crossing?: number;
    finishing?: number;
    dribbling?: number;
    shortPassing?: number;
    ballControl?: number;
    sprintSpeed?: number;
    shotPower?: number;
    longShots?: number;
    gkDiving?: number;
  };
}

/** The in-memory knowledge store: every record plus lookup indexes. */
export interface Dataset {
  matches: Match[];
  players: Player[];
  /** normalizedTeamName -> match ids (team played home OR away). */
  teamIndex: Map<string, number[]>;
  /** lowercase substring-searchable player index built lazily by services. */
  loadedFiles: { file: SourceFile; rows: number }[];
}

/** Win/draw/loss record with goals. */
export interface Record {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}
