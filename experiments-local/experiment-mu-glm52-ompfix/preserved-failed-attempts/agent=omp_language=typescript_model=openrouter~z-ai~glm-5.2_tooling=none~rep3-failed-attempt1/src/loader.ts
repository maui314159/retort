/**
 * brazilian-soccer-mcp — Dataset loader and in-memory store.
 *
 * Context: This module reads all six Kaggle CSV files, projects each row into
 * the normalized `Match`/`Player` types, and builds the indexes the query
 * engine needs:
 *
 *   - matches by competition, by season, by team key, and by (teamKey, teamKey)
 *     pair for head-to-head lookups,
 *   - players by exact club name, by team key (club normalized), and by
 *     nationality,
 *   - a global team-key → canonical display-name registry.
 *
 * Loading is performed once at server startup (~4.1k + ~10k + ~6.9k + ~1.3k +
 * ~1.2k match rows + ~18k player rows; well under the 2s/5s latency budget).
 */

import { readCsv, field } from "./csv.js";
import {
  normalizeTeamName,
  teamKey,
  parseDate,
  parseNumber,
  parseSkill,
} from "./normalize.js";
import type { Match, Player } from "./types.js";

/** FIFA skill columns we expose as ratings. */
const SKILL_COLUMNS = [
  "Crossing",
  "Finishing",
  "HeadingAccuracy",
  "ShortPassing",
  "Volleys",
  "Dribbling",
  "Curve",
  "FKAccuracy",
  "LongPassing",
  "BallControl",
  "Acceleration",
  "SprintSpeed",
  "Agility",
  "Reactions",
  "Balance",
  "ShotPower",
  "Jumping",
  "Stamina",
  "Strength",
  "LongShots",
  "Aggression",
  "Interceptions",
  "Positioning",
  "Vision",
  "Penalties",
  "Composure",
  "Marking",
  "StandingTackle",
  "SlidingTackle",
  "GKDiving",
  "GKHandling",
  "GKKicking",
  "GKPositioning",
  "GKReflexes",
];

const PLAYING_POSITIONS = new Set([
  "GK",
  "RB",
  "RWB",
  "LB",
  "LWB",
  "CB",
  "CDM",
  "CM",
  "CAM",
  "RM",
  "LM",
  "RW",
  "LW",
  "RF",
  "LF",
  "CF",
  "ST",
  "RS",
  "LS",
]);

/** Canonicalize a FIFA position: keep valid short codes, else return the raw value trimmed. */
function canonPosition(raw: string | undefined): string {
  const p = (raw ?? "").trim();
  return PLAYING_POSITIONS.has(p) ? p : p;
}

/** Map BR-Football tournament names to canonical competition names. */
const TOURNAMENT_CANON: Record<string, string> = {
  "Serie A": "Brasileirão Serie A",
  "Serie B": "Serie B",
  "Serie C": "Serie C",
  "Copa do Brasil": "Copa do Brasil",
};

/** Canonicalize a competition name so overlapping datasets align. */
function canonCompetition(raw: string): string {
  return TOURNAMENT_CANON[raw] ?? raw;
}

/** The in-memory store returned by `loadDatasets`. */
export interface Store {
  matches: Match[];
  players: Player[];
  /** teamKey -> Set of match indices (for fast team queries). */
  matchesByTeam: Map<string, Set<number>>;
  /** sorted "keyA|keyB" (both orderings) -> Set of match indices. */
  matchesByPair: Map<string, Set<number>>;
  /** competition -> Set of match indices. */
  matchesByCompetition: Map<string, Set<number>>;
  /** club name (raw) -> Player indices. */
  playersByClub: Map<string, Set<number>>;
  /** teamKey(club) -> Player indices. */
  playersByClubKey: Map<string, Set<number>>;
  /** nationality -> Player indices. */
  playersByNationality: Map<string, Set<number>>;
  /** teamKey -> preferred display name (longest seen wins, to prefer accented form). */
  teamDisplay: Map<string, string>;
}

function addIndex<T>(map: Map<T, Set<number>>, key: T, idx: number): void {
  let set = map.get(key);
  if (!set) {
    set = new Set();
    map.set(key, set);
  }
  set.add(idx);
}

function pairKey(a: string, b: string): string[] {
  return [`${a}|${b}`, `${b}|${a}`];
}

function preferDisplay(reg: Map<string, string>, key: string, display: string): void {
  const cur = reg.get(key);
  if (!cur || display.length > cur.length) reg.set(key, display);
}

/** Load and normalize all datasets from `data/kaggle/`. */
export function loadDatasets(dataDir: string): Store {
  const matches: Match[] = [];
  const players: Player[] = [];
  const matchesByTeam = new Map<string, Set<number>>();
  const matchesByPair = new Map<string, Set<number>>();
  const matchesByCompetition = new Map<string, Set<number>>();
  const playersByClub = new Map<string, Set<number>>();
  const playersByClubKey = new Map<string, Set<number>>();
  const playersByNationality = new Map<string, Set<number>>();
  const teamDisplay = new Map<string, string>();

  // --- 1. Brasileirão Serie A matches ---
  for (const row of readCsv(`${dataDir}/Brasileirao_Matches.csv`)) {
    const homeRaw = field(row, "home_team") ?? "";
    const awayRaw = field(row, "away_team") ?? "";
    const home = normalizeTeamName(homeRaw);
    const away = normalizeTeamName(awayRaw);
    const hk = teamKey(home);
    const ak = teamKey(away);
    const season = parseNumber(field(row, "season"));
    const m: Match = {
      id: `bras-${matches.length}`,
      competition: "Brasileirão Serie A",
      tournamentRaw: "Brasileirão Serie A",
      season,
      date: parseDate(field(row, "datetime") ?? ""),
      dateRaw: field(row, "datetime") ?? "",
      homeTeam: home,
      homeTeamRaw: homeRaw,
      homeTeamKey: hk,
      awayTeam: away,
      awayTeamRaw: awayRaw,
      awayTeamKey: ak,
      homeGoals: parseNumber(field(row, "home_goal")),
      awayGoals: parseNumber(field(row, "away_goal")),
      round: field(row, "round") ?? null,
      stage: null,
      venue: null,
      homeCorners: null,
      awayCorners: null,
      homeShots: null,
      awayShots: null,
      homeAttacks: null,
      awayAttacks: null,
      halfTimeResult: null,
      totalCorners: null,
    };
    pushMatch(m);
  }

  // --- 2. Copa do Brasil matches ---
  for (const row of readCsv(`${dataDir}/Brazilian_Cup_Matches.csv`)) {
    const homeRaw = field(row, "home_team") ?? "";
    const awayRaw = field(row, "away_team") ?? "";
    const home = normalizeTeamName(homeRaw);
    const away = normalizeTeamName(awayRaw);
    const m: Match = {
      id: `cup-${matches.length}`,
      competition: "Copa do Brasil",
      tournamentRaw: "Copa do Brasil",
      season: parseNumber(field(row, "season")),
      date: parseDate(field(row, "datetime") ?? ""),
      dateRaw: field(row, "datetime") ?? "",
      homeTeam: home,
      homeTeamRaw: homeRaw,
      homeTeamKey: teamKey(home),
      awayTeam: away,
      awayTeamRaw: awayRaw,
      awayTeamKey: teamKey(away),
      homeGoals: parseNumber(field(row, "home_goal")),
      awayGoals: parseNumber(field(row, "away_goal")),
      round: field(row, "round") ?? null,
      stage: null,
      venue: null,
      homeCorners: null,
      awayCorners: null,
      homeShots: null,
      awayShots: null,
      homeAttacks: null,
      awayAttacks: null,
      halfTimeResult: null,
      totalCorners: null,
    };
    pushMatch(m);
  }

  // --- 3. Copa Libertadores matches ---
  for (const row of readCsv(`${dataDir}/Libertadores_Matches.csv`)) {
    const homeRaw = field(row, "home_team") ?? "";
    const awayRaw = field(row, "away_team") ?? "";
    const home = normalizeTeamName(homeRaw);
    const away = normalizeTeamName(awayRaw);
    const m: Match = {
      id: `lib-${matches.length}`,
      competition: "Copa Libertadores",
      tournamentRaw: "Copa Libertadores",
      season: parseNumber(field(row, "season")),
      date: parseDate(field(row, "datetime") ?? ""),
      dateRaw: field(row, "datetime") ?? "",
      homeTeam: home,
      homeTeamRaw: homeRaw,
      homeTeamKey: teamKey(home),
      awayTeam: away,
      awayTeamRaw: awayRaw,
      awayTeamKey: teamKey(away),
      homeGoals: parseNumber(field(row, "home_goal")),
      awayGoals: parseNumber(field(row, "away_goal")),
      round: null,
      stage: field(row, "stage") ?? null,
      venue: null,
      homeCorners: null,
      awayCorners: null,
      homeShots: null,
      awayShots: null,
      homeAttacks: null,
      awayAttacks: null,
      halfTimeResult: null,
      totalCorners: null,
    };
    pushMatch(m);
  }

  // --- 4. BR-Football extended stats ---
  for (const row of readCsv(`${dataDir}/BR-Football-Dataset.csv`)) {
    const homeRaw = field(row, "home") ?? "";
    const awayRaw = field(row, "away") ?? "";
    const home = normalizeTeamName(homeRaw);
    const away = normalizeTeamName(awayRaw);
    const tournamentRaw = field(row, "tournament") ?? "";
    const m: Match = {
      id: `brf-${matches.length}`,
      competition: canonCompetition(tournamentRaw),
      tournamentRaw,
      season: parseDate(field(row, "date") ?? "")?.getUTCFullYear() ?? null,
      date: parseDate(field(row, "date") ?? ""),
      dateRaw: field(row, "date") ?? "",
      homeTeam: home,
      homeTeamRaw: homeRaw,
      homeTeamKey: teamKey(home),
      awayTeam: away,
      awayTeamRaw: awayRaw,
      awayTeamKey: teamKey(away),
      homeGoals: parseNumber(field(row, "home_goal")),
      awayGoals: parseNumber(field(row, "away_goal")),
      round: null,
      stage: null,
      venue: null,
      homeCorners: parseNumber(field(row, "home_corner")),
      awayCorners: parseNumber(field(row, "away_corner")),
      homeShots: parseNumber(field(row, "home_shots")),
      awayShots: parseNumber(field(row, "away_shots")),
      homeAttacks: parseNumber(field(row, "home_attack")),
      awayAttacks: parseNumber(field(row, "away_attack")),
      halfTimeResult: field(row, "ht_result") ?? null,
      totalCorners: parseNumber(field(row, "total_corners")),
    };
    pushMatch(m);
  }

  // --- 5. Historical Brasileirão (2003-2019) ---
  for (const row of readCsv(`${dataDir}/novo_campeonato_brasileiro.csv`)) {
    const homeRaw = field(row, "Equipe_mandante") ?? "";
    const awayRaw = field(row, "Equipe_visitante") ?? "";
    const home = normalizeTeamName(homeRaw);
    const away = normalizeTeamName(awayRaw);
    const m: Match = {
      id: `hist-${field(row, "ID") ?? matches.length}`,
      competition: "Brasileirão (2003-2019)",
      tournamentRaw: "Brasileirão (2003-2019)",
      season: parseNumber(field(row, "Ano")),
      date: parseDate(field(row, "Data") ?? ""),
      dateRaw: field(row, "Data") ?? "",
      homeTeam: home,
      homeTeamRaw: homeRaw,
      homeTeamKey: teamKey(home),
      awayTeam: away,
      awayTeamRaw: awayRaw,
      awayTeamKey: teamKey(away),
      homeGoals: parseNumber(field(row, "Gols_mandante")),
      awayGoals: parseNumber(field(row, "Gols_visitante")),
      round: field(row, "Rodada") ?? null,
      stage: null,
      venue: field(row, "Arena") ?? null,
      homeCorners: null,
      awayCorners: null,
      homeShots: null,
      awayShots: null,
      homeAttacks: null,
      awayAttacks: null,
      halfTimeResult: null,
      totalCorners: null,
    };
    pushMatch(m);
  }

  // --- 6. FIFA player database ---
  for (const row of readCsv(`${dataDir}/fifa_data.csv`)) {
    const idNum = parseNumber(field(row, "ID"));
    if (idNum === null) continue;
    const club = (field(row, "Club") ?? "").trim();
    const skills: Record<string, number> = {};
    for (const sc of SKILL_COLUMNS) {
      const v = parseSkill(field(row, sc));
      if (v !== null) skills[sc] = v;
    }
    const p: Player = {
      id: idNum,
      name: (field(row, "Name") ?? "").trim(),
      age: parseNumber(field(row, "Age")),
      nationality: (field(row, "Nationality") ?? "").trim(),
      overall: parseSkill(field(row, "Overall")),
      potential: parseSkill(field(row, "Potential")),
      club,
      position: canonPosition(field(row, "Position")),
      jerseyNumber: parseNumber(field(row, "Jersey Number")),
      height: field(row, "Height") ?? null,
      weight: field(row, "Weight") ?? null,
      preferredFoot: field(row, "Preferred Foot") ?? null,
      internationalReputation: parseNumber(field(row, "International Reputation")),
      value: field(row, "Value") ?? null,
      wage: field(row, "Wage") ?? null,
      skills,
    };
    const idx = players.length;
    players.push(p);
    if (club) {
      addIndex(playersByClub, club, idx);
      addIndex(playersByClubKey, teamKey(club), idx);
    }
    if (p.nationality) addIndex(playersByNationality, p.nationality, idx);
  }

  function pushMatch(m: Match): void {
    const idx = matches.length;
    matches.push(m);
    if (m.homeTeamKey) {
      addIndex(matchesByTeam, m.homeTeamKey, idx);
      preferDisplay(teamDisplay, m.homeTeamKey, m.homeTeam);
    }
    if (m.awayTeamKey) {
      addIndex(matchesByTeam, m.awayTeamKey, idx);
      preferDisplay(teamDisplay, m.awayTeamKey, m.awayTeam);
    }
    if (m.homeTeamKey && m.awayTeamKey && m.homeTeamKey !== m.awayTeamKey) {
      for (const pk of pairKey(m.homeTeamKey, m.awayTeamKey)) {
        addIndex(matchesByPair, pk, idx);
      }
    }
    if (m.competition) addIndex(matchesByCompetition, m.competition, idx);
  }

  return {
    matches,
    players,
    matchesByTeam,
    matchesByPair,
    matchesByCompetition,
    playersByClub,
    playersByClubKey,
    playersByNationality,
    teamDisplay,
  };
}
