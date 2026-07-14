import { createReadStream } from "node:fs";
import { resolve } from "node:path";
import csv from "csv-parser";
import { Match, Player } from "./types.js";
import { normalizeTeamName } from "./normalize.js";

function parseDate(value: string): string {
  if (!value) return "";

  if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
    return value.split(" ")[0];
  }

  if (/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
    const [day, month, year] = value.split("/");
    return `${year}-${month}-${day}`;
  }

  return value;
}

function parseNumber(value: string | number | undefined | null): number | null {
  if (value === undefined || value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function loadCsv(path: string): Promise<Record<string, string>[]> {
  const { promise, resolve, reject } = Promise.withResolvers<Record<string, string>[]>();
  const rows: Record<string, string>[] = [];

  createReadStream(path)
    .pipe(csv())
    .on("data", (row: Record<string, string>) => rows.push(row))
    .on("end", () => resolve(rows))
    .on("error", reject);

  return promise;
}

export async function loadAllData(dataDir: string): Promise<{ matches: Match[]; players: Player[] }> {
  const [brasileirao, cup, libertadores, extended, historical, fifa] = await Promise.all([
    loadCsv(resolve(dataDir, "Brasileirao_Matches.csv")),
    loadCsv(resolve(dataDir, "Brazilian_Cup_Matches.csv")),
    loadCsv(resolve(dataDir, "Libertadores_Matches.csv")),
    loadCsv(resolve(dataDir, "BR-Football-Dataset.csv")),
    loadCsv(resolve(dataDir, "novo_campeonato_brasileiro.csv")),
    loadCsv(resolve(dataDir, "fifa_data.csv")),
  ]);

  const matches: Match[] = [];

  for (const row of brasileirao) {
    const home = normalizeTeamName(row.home_team);
    const away = normalizeTeamName(row.away_team);
    if (!home || !away) continue;
    matches.push({
      date: parseDate(row.datetime),
      home,
      away,
      homeGoals: parseNumber(row.home_goal),
      awayGoals: parseNumber(row.away_goal),
      season: parseNumber(row.season),
      competition: "Brasileirao",
      round: row.round || null,
      stage: null,
      sourceFile: "Brasileirao_Matches.csv",
      originalDate: row.datetime,
    });
  }

  for (const row of cup) {
    const home = normalizeTeamName(row.home_team);
    const away = normalizeTeamName(row.away_team);
    if (!home || !away) continue;
    matches.push({
      date: parseDate(row.datetime),
      home,
      away,
      homeGoals: parseNumber(row.home_goal),
      awayGoals: parseNumber(row.away_goal),
      season: parseNumber(row.season),
      competition: "Copa do Brasil",
      round: row.round || null,
      stage: null,
      sourceFile: "Brazilian_Cup_Matches.csv",
      originalDate: row.datetime,
    });
  }

  for (const row of libertadores) {
    const home = normalizeTeamName(row.home_team);
    const away = normalizeTeamName(row.away_team);
    if (!home || !away) continue;
    matches.push({
      date: parseDate(row.datetime),
      home,
      away,
      homeGoals: parseNumber(row.home_goal),
      awayGoals: parseNumber(row.away_goal),
      season: parseNumber(row.season),
      competition: "Copa Libertadores",
      round: null,
      stage: row.stage || null,
      sourceFile: "Libertadores_Matches.csv",
      originalDate: row.datetime,
    });
  }

  for (const row of extended) {
    const home = normalizeTeamName(row.home);
    const away = normalizeTeamName(row.away);
    if (!home || !away) continue;
    const date = parseDate(row.date);
    const season = date ? parseNumber(date.split("-")[0]) : null;
    matches.push({
      date,
      home,
      away,
      homeGoals: parseNumber(row.home_goal),
      awayGoals: parseNumber(row.away_goal),
      season,
      competition: normalizeCompetition(row.tournament),
      round: null,
      stage: null,
      sourceFile: "BR-Football-Dataset.csv",
      originalDate: row.date,
    });
  }

  for (const row of historical) {
    const home = normalizeTeamName(row.Equipe_mandante);
    const away = normalizeTeamName(row.Equipe_visitante);
    if (!home || !away) continue;
    matches.push({
      date: parseDate(row.Data),
      home,
      away,
      homeGoals: parseNumber(row.Gols_mandante),
      awayGoals: parseNumber(row.Gols_visitante),
      season: parseNumber(row.Ano),
      competition: "Brasileirao",
      round: row.Rodada || null,
      stage: null,
      sourceFile: "novo_campeonato_brasileiro.csv",
      originalDate: row.Data,
    });
  }

  const players: Player[] = fifa.map((row) => ({
    id: row.ID,
    name: row.Name,
    age: parseNumber(row.Age),
    nationality: row.Nationality || null,
    overall: parseNumber(row.Overall),
    potential: parseNumber(row.Potential),
    club: row.Club || null,
    position: row.Position || null,
    jerseyNumber: row["Jersey Number"] || null,
  }));

  return { matches, players };
}

function normalizeCompetition(value: string): string {
  if (!value) return "Unknown";
  const lower = value.toLowerCase();
  if (lower.includes("brasileirao") || lower.includes("brasileirão") || lower.includes("serie a")) return "Brasileirao";
  if (lower.includes("copa do brasil")) return "Copa do Brasil";
  if (lower.includes("libertadores")) return "Copa Libertadores";
  return value;
}
