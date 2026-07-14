import fs from "node:fs";
import path from "node:path";
import { parse } from "csv-parse/sync";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Competition =
  | "brasileirao" // Brasileirao_Matches.csv — 2012-present
  | "copa_brasil" // Brazilian_Cup_Matches.csv
  | "libertadores" // Libertadores_Matches.csv
  | "extended" // BR-Football-Dataset.csv — has richer stats
  | "historical"; // novo_campeonato_brasileiro.csv — 2003-2019

export interface Match {
  date: string; // YYYY-MM-DD
  homeTeam: string; // raw name from source
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  competition: Competition;
  tournament?: string; // for extended dataset (e.g. "Copa do Brasil")
  season: number;
  round?: string;
  stage?: string; // for Libertadores
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
}

export interface Player {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  value?: string;
  wage?: string;
  crossing?: number;
  finishing?: number;
  dribbling?: number;
  shortPassing?: number;
  longPassing?: number;
  ballControl?: number;
  acceleration?: number;
  sprintSpeed?: number;
  agility?: number;
  reactions?: number;
  strength?: number;
  stamina?: number;
  longShots?: number;
  composure?: number;
  marking?: number;
  standingTackle?: number;
  gkDiving?: number;
  gkHandling?: number;
  gkKicking?: number;
  gkPositioning?: number;
  gkReflexes?: number;
}

// ---------------------------------------------------------------------------
// Name normalization
// ---------------------------------------------------------------------------

/**
 * Strips state suffixes (e.g. "-SP", "- RJ"), removes accents, lowercases.
 * Used for fuzzy matching only — raw names are preserved in Match.homeTeam.
 */
export function normalizeTeam(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s*[-–]\s*[a-z]{2}$/i, "") // strip state suffix: "- SP", "-RJ"
    .replace(/[áàâãä]/g, "a")
    .replace(/[éèêë]/g, "e")
    .replace(/[íìîï]/g, "i")
    .replace(/[óòôõö]/g, "o")
    .replace(/[úùûü]/g, "u")
    .replace(/[ç]/g, "c")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Returns true if teamName matches the query string (both normalized, substring check).
 * "Flamengo-RJ" matches "Flamengo"; "Atletico-MG" matches "Atletico Mineiro".
 */
export function teamMatchesQuery(teamName: string, query: string): boolean {
  const n = normalizeTeam(teamName);
  const q = normalizeTeam(query);
  if (!q) return true;
  return n.includes(q) || q.includes(n);
}

// ---------------------------------------------------------------------------
// CSV helpers
// ---------------------------------------------------------------------------

const DATA_DIR = path.join(process.cwd(), "data", "kaggle");

type Row = Record<string, string>;

function readCsv(filename: string): Row[] {
  const content = fs.readFileSync(path.join(DATA_DIR, filename), "utf-8");
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    relax_column_count: true,
    bom: true,
  }) as Row[];
}

function safeInt(v: string | undefined): number {
  const n = parseInt(v ?? "", 10);
  return isNaN(n) ? 0 : n;
}

function safeFloat(v: string | undefined): number {
  const n = parseFloat(v ?? "");
  return isNaN(n) ? 0 : n;
}

function safeOptInt(v: string | undefined): number | undefined {
  if (!v?.trim()) return undefined;
  const n = parseInt(v, 10);
  return isNaN(n) ? undefined : n;
}

function safeOptFloat(v: string | undefined): number | undefined {
  if (!v?.trim()) return undefined;
  const n = parseFloat(v);
  return isNaN(n) ? undefined : n;
}

function parseDateStr(s: string): string {
  const ddmmyyyy = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (ddmmyyyy) return `${ddmmyyyy[3]}-${ddmmyyyy[2]}-${ddmmyyyy[1]}`;
  return (s.split(" ")[0] ?? s).trim(); // strip time from "YYYY-MM-DD HH:MM:SS"
}

// ---------------------------------------------------------------------------
// Data loading (lazy, cached)
// ---------------------------------------------------------------------------

let _matches: Match[] | null = null;
let _players: Player[] | null = null;

export function loadMatches(): Match[] {
  if (_matches) return _matches;
  const all: Match[] = [];

  // 1. Brasileirão Série A (2012–present)
  for (const r of readCsv("Brasileirao_Matches.csv")) {
    const season = safeInt(r.season);
    if (!season) continue;
    all.push({
      date: parseDateStr(r.datetime ?? ""),
      homeTeam: r.home_team ?? "",
      awayTeam: r.away_team ?? "",
      homeGoals: safeInt(r.home_goal),
      awayGoals: safeInt(r.away_goal),
      competition: "brasileirao",
      season,
      round: r.round != null ? String(r.round) : undefined,
    });
  }

  // 2. Copa do Brasil
  for (const r of readCsv("Brazilian_Cup_Matches.csv")) {
    const season = safeInt(r.season);
    if (!season) continue;
    all.push({
      date: parseDateStr(r.datetime ?? ""),
      homeTeam: r.home_team ?? "",
      awayTeam: r.away_team ?? "",
      homeGoals: safeInt(r.home_goal),
      awayGoals: safeInt(r.away_goal),
      competition: "copa_brasil",
      season,
      round: r.round != null ? String(r.round) : undefined,
    });
  }

  // 3. Copa Libertadores
  for (const r of readCsv("Libertadores_Matches.csv")) {
    const season = safeInt(r.season);
    if (!season) continue;
    all.push({
      date: parseDateStr(r.datetime ?? ""),
      homeTeam: r.home_team ?? "",
      awayTeam: r.away_team ?? "",
      homeGoals: safeInt(r.home_goal),
      awayGoals: safeInt(r.away_goal),
      competition: "libertadores",
      season,
      stage: r.stage || undefined,
    });
  }

  // 4. BR-Football-Dataset (extended stats, 2021–2023)
  for (const r of readCsv("BR-Football-Dataset.csv")) {
    const dateStr = r.date ?? "";
    const season = safeInt(dateStr.split("-")[0]);
    if (!season) continue;
    all.push({
      date: dateStr,
      homeTeam: r.home ?? "",
      awayTeam: r.away ?? "",
      homeGoals: Math.round(safeFloat(r.home_goal)),
      awayGoals: Math.round(safeFloat(r.away_goal)),
      competition: "extended",
      tournament: r.tournament || undefined,
      season,
      homeCorners: safeOptFloat(r.home_corner),
      awayCorners: safeOptFloat(r.away_corner),
      homeShots: safeOptFloat(r.home_shots),
      awayShots: safeOptFloat(r.away_shots),
    });
  }

  // 5. Historical Brasileirão (2003–2019)
  for (const r of readCsv("novo_campeonato_brasileiro.csv")) {
    const season = safeInt(r.Ano);
    if (!season) continue;
    all.push({
      date: parseDateStr(r.Data ?? ""),
      homeTeam: r.Equipe_mandante ?? "",
      awayTeam: r.Equipe_visitante ?? "",
      homeGoals: safeInt(r.Gols_mandante),
      awayGoals: safeInt(r.Gols_visitante),
      competition: "historical",
      season,
      round: r.Rodada != null ? String(r.Rodada) : undefined,
    });
  }

  _matches = all;
  return all;
}

export function loadPlayers(): Player[] {
  if (_players) return _players;
  const all: Player[] = [];

  for (const r of readCsv("fifa_data.csv")) {
    const overall = safeInt(r.Overall);
    if (!overall) continue;
    all.push({
      id: safeInt(r.ID),
      name: r.Name ?? "",
      age: safeInt(r.Age),
      nationality: r.Nationality ?? "",
      overall,
      potential: safeInt(r.Potential) || overall,
      club: r.Club ?? "",
      position: r.Position ?? "",
      jerseyNumber: safeOptInt(r["Jersey Number"]),
      height: r.Height || undefined,
      weight: r.Weight || undefined,
      value: r.Value || undefined,
      wage: r.Wage || undefined,
      crossing: safeOptInt(r.Crossing),
      finishing: safeOptInt(r.Finishing),
      dribbling: safeOptInt(r.Dribbling),
      shortPassing: safeOptInt(r.ShortPassing),
      longPassing: safeOptInt(r.LongPassing),
      ballControl: safeOptInt(r.BallControl),
      acceleration: safeOptInt(r.Acceleration),
      sprintSpeed: safeOptInt(r.SprintSpeed),
      agility: safeOptInt(r.Agility),
      reactions: safeOptInt(r.Reactions),
      strength: safeOptInt(r.Strength),
      stamina: safeOptInt(r.Stamina),
      longShots: safeOptInt(r.LongShots),
      composure: safeOptInt(r.Composure),
      marking: safeOptInt(r.Marking),
      standingTackle: safeOptInt(r.StandingTackle),
      gkDiving: safeOptInt(r.GKDiving),
      gkHandling: safeOptInt(r.GKHandling),
      gkKicking: safeOptInt(r.GKKicking),
      gkPositioning: safeOptInt(r.GKPositioning),
      gkReflexes: safeOptInt(r.GKReflexes),
    });
  }

  _players = all;
  return all;
}

// ---------------------------------------------------------------------------
// Competition filtering helper
// ---------------------------------------------------------------------------

/**
 * Maps a user-supplied competition name to a predicate on Match.competition.
 * "brasileirao" covers both 'brasileirao' and 'historical' (both are Série A).
 * "copa_brasil" covers 'copa_brasil' and 'extended' records with Copa do Brasil tournament.
 * "all" accepts everything.
 */
export function matchesCompetition(match: Match, filter: string): boolean {
  const f = filter.toLowerCase().replace(/[-_]/g, " ");
  if (f === "all") return true;

  switch (match.competition) {
    case "brasileirao":
      return ["brasileirao", "serie a", "campeonato brasileiro"].some((k) =>
        f.includes(k) || k.includes(f)
      );
    case "historical":
      return ["brasileirao", "serie a", "campeonato brasileiro", "historical"].some((k) =>
        f.includes(k) || k.includes(f)
      );
    case "copa_brasil":
      return ["copa brasil", "copa do brasil"].some((k) =>
        f.includes(k) || k.includes(f)
      );
    case "libertadores":
      return ["libertadores", "copa libertadores"].some((k) =>
        f.includes(k) || k.includes(f)
      );
    case "extended": {
      const t = (match.tournament ?? "").toLowerCase();
      if (
        ["brasileirao", "serie a", "campeonato brasileiro"].some((k) => f.includes(k) || k.includes(f)) &&
        ["campeonato brasileiro", "brasileirao", "serie a"].some((k) => t.includes(k))
      ) {
        return true;
      }
      if (
        ["copa brasil", "copa do brasil"].some((k) => f.includes(k) || k.includes(f)) &&
        t.includes("copa do brasil")
      ) {
        return true;
      }
      if (f === "extended") return true;
      return false;
    }
  }
}
