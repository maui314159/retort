/**
 * Brazilian Soccer MCP Server — Dataset loader.
 *
 * Context block
 * -------------
 * Loads the six Kaggle CSVs from `data/kaggle/` into the unified in-memory
 * model (MatchRecord / Player) and indexes them for fast MCP-tool queries.
 *
 * Source files and their column dialects:
 *   - Brasileirao_Matches.csv: datetime,home_team,home_team_state,away_team,
 *       away_team_state,home_goal,away_goal,season,round
 *   - Brazilian_Cup_Matches.csv: round,datetime,home_team,away_team,home_goal,
 *       away_goal,season
 *   - Libertadores_Matches.csv: datetime,home_team,away_team,home_goal,away_goal,
 *       season,stage
 *   - BR-Football-Dataset.csv: tournament,home,home_goal,away_goal,away,
 *       home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,
 *       time,date,ht_diff,at_diff,ht_result,at_result,total_corners
 *   - novo_campeonato_brasileiro.csv: ID,Data,Ano,Rodada,Equipe_mandante,
 *       Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,
 *       Vencedor,Arena,OBS
 *   - fifa_data.csv: FIFA player DB (BOM-prefixed ID column, ~75 columns)
 *
 * The loader is tolerant: malformed numbers become null, unparseable dates
 * become null, and BOM/whitespace in headers is stripped. All team names are
 * run through a shared TeamRegistry so cross-file joins resolve to one node.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import type {
  Competition,
  MatchRecord,
  Player,
  StandingRow,
} from "./types.js";
import { parseDate } from "./dates.js";
import { TeamRegistry } from "./normalize.js";

/** Default data directory (relative to process cwd). */
export const DEFAULT_DATA_DIR = "data/kaggle";

/** Result of loading the full dataset. */
export interface Dataset {
  matches: MatchRecord[];
  players: Player[];
  teams: TeamRegistry;
  /** matches indexed by teamKey -> MatchRecord[]. */
  matchesByTeam: Map<string, MatchRecord[]>;
  /** players indexed by club key -> Player[]. */
  playersByClub: Map<string, Player[]>;
  /** matches indexed by competition -> MatchRecord[]. */
  matchesByCompetition: Map<Competition, MatchRecord[]>;
  /** Set of seasons present per competition. */
  seasonsByCompetition: Map<Competition, number[]>;
}

/** Strip a leading UTF-8 BOM and surrounding whitespace from a header name. */
function cleanHeader(h: string): string {
  return h.replace(/^\uFEFF/, "").trim();
}

/** Parse a possibly-empty numeric cell, tolerating "88+2" style skill values. */
function parseNumber(raw: unknown): number | null {
  if (raw === null || raw === undefined) return null;
  const s = String(raw).trim();
  if (s === "") return null;
  // Skill ratings in fifa_data look like "88+2"; keep the base value.
  const base = s.split("+")[0]?.trim() ?? s;
  const n = Number(base);
  return Number.isFinite(n) ? n : null;
}

/** Read and parse a CSV file into an array of record objects. */
function readCsv(path: string, opts?: Record<string, unknown>): Record<string, string>[] {
  const buf = readFileSync(path);
  const rows = parse(buf, {
    columns: (cols) => cols.map(cleanHeader),
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true,
    bom: true,
    ...opts,
  });
  return rows as Record<string, string>[];
}

/** Classify a BR-Football tournament string into a Competition. */
function classifyTournament(t: string): Competition {
  const k = t.toLowerCase();
  if (k.includes("copa do brasil")) return "Copa do Brasil";
  if (k === "serie a" || k.includes("série a")) return "Brasileirão";
  if (k.includes("libertadores")) return "Copa Libertadores";
  return "Other";
}

/** Load a single match CSV file into MatchRecord[]. */
function loadMatchFile(
  file: string,
  source: string,
  competition: Competition,
  teams: TeamRegistry,
  rowToMatch: (row: Record<string, string>, idx: number) => Omit<MatchRecord, "id" | "source" | "competition">,
): MatchRecord[] {
  const rows = readCsv(file);
  const out: MatchRecord[] = [];
  rows.forEach((row, idx) => {
    try {
      const partial = rowToMatch(row, idx);
      out.push({
        id: `${source}#${idx}`,
        source,
        competition,
        ...partial,
      });
    } catch {
      // Skip malformed rows silently — loaders are tolerant.
    }
  });
  return out;
}

/** Load all six datasets from the given directory. */
export function loadDataset(dataDir: string = DEFAULT_DATA_DIR): Dataset {
  const teams = new TeamRegistry();
  const matches: MatchRecord[] = [];
  const players: Player[] = [];

  // 1. Brasileirão Série A.
  matches.push(
    ...loadMatchFile(
      join(dataDir, "Brasileirao_Matches.csv"),
      "Brasileirao_Matches",
      "Brasileirão",
      teams,
      (row) => ({
        date: parseDate(row["datetime"]),
        rawDate: row["datetime"] ?? "",
        homeTeam: teams.resolve(row["home_team"] ?? ""),
        awayTeam: teams.resolve(row["away_team"] ?? ""),
        homeState: row["home_team_state"]?.trim() || undefined,
        awayState: row["away_team_state"]?.trim() || undefined,
        homeGoal: parseNumber(row["home_goal"]),
        awayGoal: parseNumber(row["away_goal"]),
        season: parseNumber(row["season"]),
        round: row["round"]?.trim() || undefined,
      }),
    ),
  );

  // 2. Copa do Brasil.
  matches.push(
    ...loadMatchFile(
      join(dataDir, "Brazilian_Cup_Matches.csv"),
      "Brazilian_Cup_Matches",
      "Copa do Brasil",
      teams,
      (row) => ({
        date: parseDate(row["datetime"]),
        rawDate: row["datetime"] ?? "",
        homeTeam: teams.resolve(row["home_team"] ?? ""),
        awayTeam: teams.resolve(row["away_team"] ?? ""),
        homeGoal: parseNumber(row["home_goal"]),
        awayGoal: parseNumber(row["away_goal"]),
        season: parseNumber(row["season"]),
        round: row["round"]?.replace(/^"|"$/g, "").trim() || undefined,
      }),
    ),
  );

  // 3. Copa Libertadores.
  matches.push(
    ...loadMatchFile(
      join(dataDir, "Libertadores_Matches.csv"),
      "Libertadores_Matches",
      "Copa Libertadores",
      teams,
      (row) => ({
        date: parseDate(row["datetime"]),
        rawDate: row["datetime"] ?? "",
        homeTeam: teams.resolve(row["home_team"] ?? ""),
        awayTeam: teams.resolve(row["away_team"] ?? ""),
        homeGoal: parseNumber(row["home_goal"]),
        awayGoal: parseNumber(row["away_goal"]),
        season: parseNumber(row["season"]),
        stage: row["stage"]?.trim() || undefined,
      }),
    ),
  );

  // 4. BR-Football extended stats.
  matches.push(
    ...loadMatchFile(
      join(dataDir, "BR-Football-Dataset.csv"),
      "BR-Football-Dataset",
      "Other",
      teams,
      (row) => {
        const tournament = row["tournament"] ?? "Other";
        const comp = classifyTournament(tournament);
        const home = row["home"] ?? "";
        const away = row["away"] ?? "";
        return {
          competition: comp,
          tournament,
          date: parseDate(row["date"]),
          rawDate: row["date"] ?? "",
          homeTeam: teams.resolve(home),
          awayTeam: teams.resolve(away),
          homeGoal: parseNumber(row["home_goal"]),
          awayGoal: parseNumber(row["away_goal"]),
          season: parseDate(row["date"])?.getUTCFullYear() ?? null,
          homeCorner: parseNumber(row["home_corner"]),
          awayCorner: parseNumber(row["away_corner"]),
          homeAttack: parseNumber(row["home_attack"]),
          awayAttack: parseNumber(row["away_attack"]),
          homeShots: parseNumber(row["home_shots"]),
          awayShots: parseNumber(row["away_shots"]),
        };
      },
    ),
  );

  // 5. Historical Brasileirão (2003-2019).
  matches.push(
    ...loadMatchFile(
      join(dataDir, "novo_campeonato_brasileiro.csv"),
      "novo_campeonato_brasileiro",
      "Brasileirão",
      teams,
      (row) => ({
        date: parseDate(row["Data"]),
        rawDate: row["Data"] ?? "",
        homeTeam: teams.resolve(row["Equipe_mandante"] ?? ""),
        awayTeam: teams.resolve(row["Equipe_visitante"] ?? ""),
        homeState: row["Mandante_UF"]?.trim() || undefined,
        awayState: row["Visitante_UF"]?.trim() || undefined,
        homeGoal: parseNumber(row["Gols_mandante"]),
        awayGoal: parseNumber(row["Gols_visitante"]),
        season: parseNumber(row["Ano"]),
        round: row["Rodada"]?.trim() || undefined,
        arena: row["Arena"]?.trim() || undefined,
      }),
    ),
  );

  // 6. FIFA players.
  const fifaRows = readCsv(join(dataDir, "fifa_data.csv"));
  // Skill columns we surface in the player's `skills` map.
  const SKILL_COLS = [
    "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
    "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
    "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
    "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
    "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
    "Composure", "Marking", "StandingTackle", "SlidingTackle",
    "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
  ];
  for (const row of fifaRows) {
    const skills: Record<string, number> = {};
    for (const c of SKILL_COLS) {
      const v = parseNumber(row[c]);
      if (v !== null) skills[c] = v;
    }
    const player: Player = {
      id: parseNumber(row["ID"]) ?? 0,
      name: (row["Name"] ?? "").trim(),
      age: parseNumber(row["Age"]),
      nationality: (row["Nationality"] ?? "").trim(),
      overall: parseNumber(row["Overall"]),
      potential: parseNumber(row["Potential"]),
      club: (row["Club"] ?? "").trim(),
      position: (row["Position"] ?? "").trim(),
      jerseyNumber: parseNumber(row["Jersey Number"]),
      preferredFoot: (row["Preferred Foot"] ?? "").trim() || undefined,
      height: (row["Height"] ?? "").trim() || undefined,
      weight: (row["Weight"] ?? "").trim() || undefined,
      value: (row["Value"] ?? "").trim() || undefined,
      wage: (row["Wage"] ?? "").trim() || undefined,
      skills,
    };
    if (player.name) players.push(player);
  }

  return indexDataset(dedupMatches(matches), players, teams);
}

/**
 * Remove duplicate matches that appear in more than one source file (e.g. a
 * Brasileirão round listed in both Brasileirao_Matches.csv and
 * BR-Football-Dataset.csv, or in novo_campeonato_brasileiro.csv). Two records
 * are considered the same match when they share season, competition, both
 * teams (in either order), and the same final score. The kickoff date is NOT
 * part of the signature because sources disagree by ±1 day (timezone/Kaggle
 * extraction differences); a given (competition, season, venue, score) tuple
 * is unique per season, so dropping the date is safe and reconciles the
 * off-by-one duplicates. The first-seen record is kept and enriched with any
 * missing extended stats (corners/shots/attacks/arena/tournament) from the
 * duplicate, preferring a non-null date when the kept record lacks one.
 */
function dedupMatches(matches: MatchRecord[]): MatchRecord[] {
  const seen = new Map<string, MatchRecord>();
  const out: MatchRecord[] = [];
  for (const m of matches) {
    if (m.homeGoal === null || m.awayGoal === null || m.season === null) {
      out.push(m);
      continue;
    }
    const hk = teamKeyOf(m.homeTeam);
    const ak = teamKeyOf(m.awayTeam);
    const sigA = `${m.season}|${m.competition}|${hk}|${ak}|${m.homeGoal}|${m.awayGoal}`;
    const sigB = `${m.season}|${m.competition}|${ak}|${hk}|${m.awayGoal}|${m.homeGoal}`;
    const existing = seen.get(sigA) ?? seen.get(sigB);
    if (existing) {
      mergeMatch(existing, m);
      continue;
    }
    seen.set(sigA, m);
    out.push(m);
  }
  return out;
}

/** teamKey without importing the full normalize surface (operates on display names). */
function teamKeyOf(display: string): string {
  return display.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

/** Merge optional enrichment fields from `src` into `dest` (in place). */
function mergeMatch(dest: MatchRecord, src: MatchRecord): void {
  const fields: (keyof MatchRecord)[] = [
    "homeCorner", "awayCorner", "homeAttack", "awayAttack",
    "homeShots", "awayShots", "arena", "tournament", "stage", "homeState", "awayState", "round",
  ];
  for (const f of fields) {
    const d = dest[f] as string | number | undefined | null;
    const s = src[f] as string | number | undefined | null;
    if ((d === undefined || d === null || d === "") && s !== undefined && s !== null && s !== "") {
      (dest as unknown as Record<string, unknown>)[f] = s;
    }
  }
  // Prefer a non-null date; if both present keep the earlier kickoff.
  if (!dest.date && src.date) dest.date = src.date;
  else if (dest.date && src.date && src.date.getTime() < dest.date.getTime()) dest.date = src.date;
}

/** Build lookup indexes over loaded matches and players. */
function indexDataset(
  matches: MatchRecord[],
  players: Player[],
  teams: TeamRegistry,
): Dataset {
  const matchesByTeam = new Map<string, MatchRecord[]>();
  const matchesByCompetition = new Map<Competition, MatchRecord[]>();
  const playersByClub = new Map<string, Player[]>();
  const seasonsByCompetition = new Map<Competition, number[]>();

  for (const m of matches) {
    for (const t of [m.homeTeam, m.awayTeam]) {
      const key = t.toLowerCase();
      const list = matchesByTeam.get(key);
      if (list) list.push(m);
      else matchesByTeam.set(key, [m]);
    }
    const cl = matchesByCompetition.get(m.competition) ?? [];
    cl.push(m);
    matchesByCompetition.set(m.competition, cl);

    if (m.season !== null) {
      const ss = seasonsByCompetition.get(m.competition) ?? [];
      if (!ss.includes(m.season)) ss.push(m.season);
      seasonsByCompetition.set(m.competition, ss);
    }
  }

  for (const p of players) {
    if (!p.club) continue;
    const key = p.club.toLowerCase();
    const list = playersByClub.get(key);
    if (list) list.push(p);
    else playersByClub.set(key, [p]);
  }

  return {
    matches,
    players,
    teams,
    matchesByTeam,
    playersByClub,
    matchesByCompetition,
    seasonsByCompetition,
  };
}

/** Compute standings for a competition+season from match results. */
export function computeStandings(
  matches: MatchRecord[],
  season: number | null,
  competition: Competition | "all",
): StandingRow[] {
  const rows = new Map<string, StandingRow>();
  const consider = matches.filter(
    (m) =>
      (competition === "all" || m.competition === competition) &&
      (season === null || m.season === season) &&
      m.homeGoal !== null &&
      m.awayGoal !== null,
  );
  for (const m of consider) {
    const home = rows.get(m.homeTeam) ?? blankRow(m.homeTeam);
    const away = rows.get(m.awayTeam) ?? blankRow(m.awayTeam);
    home.played++;
    away.played++;
    home.goalsFor += m.homeGoal!;
    home.goalsAgainst += m.awayGoal!;
    away.goalsFor += m.awayGoal!;
    away.goalsAgainst += m.homeGoal!;
    if (m.homeGoal! > m.awayGoal!) {
      home.wins++;
      away.losses++;
      home.points += 3;
    } else if (m.homeGoal! < m.awayGoal!) {
      away.wins++;
      home.losses++;
      away.points += 3;
    } else {
      home.draws++;
      away.draws++;
      home.points++;
      away.points++;
    }
    rows.set(m.homeTeam, home);
    rows.set(m.awayTeam, away);
  }
  const table = [...rows.values()];
  for (const r of table) r.goalDifference = r.goalsFor - r.goalsAgainst;
  table.sort(
    (a, b) =>
      b.points - a.points ||
      b.wins - a.wins ||
      b.goalDifference - a.goalDifference ||
      b.goalsFor - a.goalsFor ||
      a.team.localeCompare(b.team),
  );
  return table;
}

function blankRow(team: string): StandingRow {
  return {
    team,
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    goalDifference: 0,
    points: 0,
  };
}


