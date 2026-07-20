import { parse } from "csv-parse/sync";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import type {
  BrasileiraoMatch,
  CupMatch,
  LibertadoresMatch,
  ExtendedMatch,
  HistoricalMatch,
  FifaPlayer,
  NormalizedMatch,
} from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, "../data/kaggle");

export function normalizeTeamName(name: string): string {
  return name
    .replace(/-[A-Z]{2}$/, "")
    .replace(/\s*-\s*[A-Z]{2}\s*$/, "")
    .replace(/\s*\([^)]+\)/g, "")
    .replace(/\s*-\s*$/, "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ");
}

export function teamsMatch(a: string, b: string): boolean {
  const na = normalizeTeamName(a);
  const nb = normalizeTeamName(b);
  return na === nb || na.includes(nb) || nb.includes(na);
}

function parseNumber(val: unknown): number {
  const n = Number(val);
  return isNaN(n) ? 0 : n;
}

function loadCsv(filename: string): Record<string, string>[] {
  const content = readFileSync(join(DATA_DIR, filename), "utf-8");
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
  }) as Record<string, string>[];
}

function normalizeMatch(
  home: string,
  away: string,
  home_goal: number,
  away_goal: number,
  datetime: string,
  season: number,
  competition: string,
  extra: Partial<NormalizedMatch> = {}
): NormalizedMatch {
  return {
    datetime,
    home_team: home,
    home_team_normalized: normalizeTeamName(home),
    away_team: away,
    away_team_normalized: normalizeTeamName(away),
    home_goal,
    away_goal,
    season,
    competition,
    ...extra,
  };
}

let cachedMatches: NormalizedMatch[] | null = null;
let cachedPlayers: FifaPlayer[] | null = null;

export function loadAllMatches(): NormalizedMatch[] {
  if (cachedMatches) return cachedMatches;

  const matches: NormalizedMatch[] = [];

  // Brasileirao Series A
  const brasileirao = loadCsv("Brasileirao_Matches.csv") as unknown as BrasileiraoMatch[];
  for (const row of brasileirao) {
    matches.push(
      normalizeMatch(
        row.home_team,
        row.away_team,
        parseNumber(row.home_goal),
        parseNumber(row.away_goal),
        String(row.datetime),
        parseNumber(row.season),
        "Brasileirao",
        { round: parseNumber(row.round) }
      )
    );
  }

  // Copa do Brasil
  const cup = loadCsv("Brazilian_Cup_Matches.csv") as unknown as CupMatch[];
  for (const row of cup) {
    matches.push(
      normalizeMatch(
        row.home_team,
        row.away_team,
        parseNumber(row.home_goal),
        parseNumber(row.away_goal),
        String(row.datetime),
        parseNumber(row.season),
        "Copa do Brasil",
        { round: row.round }
      )
    );
  }

  // Copa Libertadores
  const lib = loadCsv("Libertadores_Matches.csv") as unknown as LibertadoresMatch[];
  for (const row of lib) {
    matches.push(
      normalizeMatch(
        row.home_team,
        row.away_team,
        parseNumber(row.home_goal),
        parseNumber(row.away_goal),
        String(row.datetime),
        parseNumber(row.season),
        "Libertadores",
        { stage: row.stage }
      )
    );
  }

  // Extended dataset
  const extended = loadCsv("BR-Football-Dataset.csv") as unknown as ExtendedMatch[];
  for (const row of extended) {
    // Skip if already covered (check tournament name mapping)
    const competition =
      row.tournament === "Brasileirao" || row.tournament === "Brasileiro"
        ? "Brasileirao"
        : row.tournament;
    matches.push(
      normalizeMatch(
        row.home,
        row.away,
        parseNumber(row.home_goal),
        parseNumber(row.away_goal),
        row.date,
        parseNumber(row.date?.split("-")?.[0] ?? "0"),
        competition
      )
    );
  }

  // Historical Brasileirao 2003-2019
  const historical = loadCsv("novo_campeonato_brasileiro.csv") as unknown as Array<{
    ID: string;
    Data: string;
    Ano: string;
    Rodada: string;
    Equipe_mandante: string;
    Equipe_visitante: string;
    Gols_mandante: string;
    Gols_visitante: string;
    Mandante_UF: string;
    Visitante_UF: string;
    Vencedor: string;
    Arena: string;
  }>;

  for (const row of historical) {
    // Convert DD/MM/YYYY to ISO
    const parts = row.Data?.split("/");
    const datetime =
      parts?.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : row.Data;
    matches.push(
      normalizeMatch(
        row.Equipe_mandante,
        row.Equipe_visitante,
        parseNumber(row.Gols_mandante),
        parseNumber(row.Gols_visitante),
        datetime,
        parseNumber(row.Ano),
        "Brasileirao",
        { round: parseNumber(row.Rodada), arena: row.Arena }
      )
    );
  }

  cachedMatches = matches;
  return matches;
}

export function loadFifaPlayers(): FifaPlayer[] {
  if (cachedPlayers) return cachedPlayers;

  const rows = loadCsv("fifa_data.csv");
  cachedPlayers = rows.map((row, i) => ({
    id: parseNumber(row["ID"] ?? i),
    name: row["Name"] ?? "",
    age: parseNumber(row["Age"]),
    nationality: row["Nationality"] ?? "",
    overall: parseNumber(row["Overall"]),
    potential: parseNumber(row["Potential"]),
    club: row["Club"] ?? "",
    position: row["Position"] ?? "",
    jersey_number: parseNumber(row["Jersey Number"]),
    height: row["Height"] ?? "",
    weight: row["Weight"] ?? "",
    crossing: parseNumber(row["Crossing"]),
    finishing: parseNumber(row["Finishing"]),
    dribbling: parseNumber(row["Dribbling"]),
  }));

  return cachedPlayers;
}

export function clearCache(): void {
  cachedMatches = null;
  cachedPlayers = null;
}
