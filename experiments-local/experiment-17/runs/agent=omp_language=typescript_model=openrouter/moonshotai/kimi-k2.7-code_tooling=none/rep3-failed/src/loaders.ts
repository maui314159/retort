/**
 * CSV loaders and the SoccerRepository.
 *
 * The repository is the single source of truth for matches and players.
 * It normalizes every row from the six Kaggle datasets into the shared
 * {@link Match} / {@link Player} models so the query engine does not
 * need to know anything about the original file schemas.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Papa from "papaparse";
import type { Match, Player } from "./models.js";
import { canonicalTeamName, fold } from "./normalize.js";
import { parseDate } from "./dates.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.resolve(__dirname, "..", "data", "kaggle");

function toNumber(value: unknown): number | undefined {
  if (value === "" || value === undefined || value === null) return undefined;
  const n = typeof value === "number" ? value : Number(String(value).trim());
  return Number.isNaN(n) ? undefined : n;
}

function readCsv(fileName: string): Papa.ParseResult<Record<string, unknown>> {
  const filePath = path.join(DATA_DIR, fileName);
  const text = fs.readFileSync(filePath, "utf-8");
  return Papa.parse<Record<string, unknown>>(text, {
    header: true,
    dynamicTyping: false,
    skipEmptyLines: true,
  });
}

function competitionFromTournament(tournament: unknown): string {
  const t = String(tournament).toLowerCase();
  if (t.includes("libertadores")) return "Copa Libertadores";
  if (t.includes("cop") && t.includes("brasil")) return "Copa do Brasil";
  if (t.includes("brasileir") || t.includes("serie a")) return "Brasileirão";
  return String(tournament);
}

function loadBrasileirao(): Match[] {
  const result = readCsv("Brasileirao_Matches.csv");
  return result.data
    .map((row, idx): Match | undefined => {
      const date = parseDate(String(row.datetime ?? row.date ?? ""));
      if (!date) return undefined;
      return {
        id: `brasileirao-${row.season ?? "?"}-${idx}`,
        date,
        datetime: row.datetime ? String(row.datetime) : undefined,
        season: toNumber(row.season) ?? 0,
        competition: "Brasileirão",
        round: toNumber(row.round),
        homeTeam: canonicalTeamName(String(row.home_team ?? "")),
        awayTeam: canonicalTeamName(String(row.away_team ?? "")),
        homeTeamState: String(row.home_team_state ?? ""),
        awayTeamState: String(row.away_team_state ?? ""),
        homeGoal: toNumber(row.home_goal) ?? 0,
        awayGoal: toNumber(row.away_goal) ?? 0,
      };
    })
    .filter((m): m is Match => m !== undefined);
}

function loadBrazilianCup(): Match[] {
  const result = readCsv("Brazilian_Cup_Matches.csv");
  return result.data
    .map((row, idx): Match | undefined => {
      const date = parseDate(String(row.datetime ?? ""));
      if (!date) return undefined;
      return {
        id: `copa-brasil-${row.season ?? "?"}-${idx}`,
        date,
        datetime: row.datetime ? String(row.datetime) : undefined,
        season: toNumber(row.season) ?? 0,
        competition: "Copa do Brasil",
        round: String(row.round ?? ""),
        homeTeam: canonicalTeamName(String(row.home_team ?? "")),
        awayTeam: canonicalTeamName(String(row.away_team ?? "")),
        homeGoal: toNumber(row.home_goal) ?? 0,
        awayGoal: toNumber(row.away_goal) ?? 0,
      };
    })
    .filter((m): m is Match => m !== undefined);
}

function loadLibertadores(): Match[] {
  const result = readCsv("Libertadores_Matches.csv");
  return result.data
    .map((row, idx): Match | undefined => {
      const date = parseDate(String(row.datetime ?? ""));
      if (!date) return undefined;
      return {
        id: `libertadores-${row.season ?? "?"}-${idx}`,
        date,
        datetime: row.datetime ? String(row.datetime) : undefined,
        season: toNumber(row.season) ?? 0,
        competition: "Copa Libertadores",
        stage: String(row.stage ?? ""),
        homeTeam: canonicalTeamName(String(row.home_team ?? "")),
        awayTeam: canonicalTeamName(String(row.away_team ?? "")),
        homeGoal: toNumber(row.home_goal) ?? 0,
        awayGoal: toNumber(row.away_goal) ?? 0,
      };
    })
    .filter((m): m is Match => m !== undefined);
}

function loadExtendedStats(): Match[] {
  const result = readCsv("BR-Football-Dataset.csv");
  return result.data
    .map((row, idx): Match | undefined => {
      const rawDate = String(row.date ?? "");
      const rawTime = String(row.time ?? "");
      const date = parseDate(rawDate);
      if (!date) return undefined;
      return {
        id: `br-stats-${idx}`,
        date,
        datetime: rawTime ? `${rawDate} ${rawTime}` : rawDate,
        season: toNumber(rawDate.split("-")[0]) ?? 0,
        competition: competitionFromTournament(row.tournament),
        homeTeam: canonicalTeamName(String(row.home ?? "")),
        awayTeam: canonicalTeamName(String(row.away ?? "")),
        homeGoal: toNumber(row.home_goal) ?? 0,
        awayGoal: toNumber(row.away_goal) ?? 0,
        homeCorner: toNumber(row.home_corner),
        awayCorner: toNumber(row.away_corner),
        homeAttack: toNumber(row.home_attack),
        awayAttack: toNumber(row.away_attack),
        homeShots: toNumber(row.home_shots),
        awayShots: toNumber(row.away_shots),
      };
    })
    .filter((m): m is Match => m !== undefined);
}

function loadHistorical(): Match[] {
  const result = readCsv("novo_campeonato_brasileiro.csv");
  return result.data
    .map((row): Match | undefined => {
      const date = parseDate(String(row.Data ?? ""));
      if (!date) return undefined;
      return {
        id: String(row.ID ?? ""),
        date,
        season: toNumber(row.Ano) ?? 0,
        competition: "Brasileirão",
        round: toNumber(row.Rodada),
        homeTeam: canonicalTeamName(String(row.Equipe_mandante ?? "")),
        awayTeam: canonicalTeamName(String(row.Equipe_visitante ?? "")),
        homeTeamState: String(row.Mandante_UF ?? ""),
        awayTeamState: String(row.Visitante_UF ?? ""),
        homeGoal: toNumber(row.Gols_mandante) ?? 0,
        awayGoal: toNumber(row.Gols_visitante) ?? 0,
        stadium: String(row.Arena ?? ""),
      };
    })
    .filter((m): m is Match => m !== undefined && m.id !== "");
}

function loadPlayers(): Player[] {
  const result = readCsv("fifa_data.csv");
  return result.data
    .map((row): Player | undefined => {
      const id = toNumber(row.ID);
      if (id === undefined) return undefined;
      return {
        id,
        name: String(row.Name ?? ""),
        age: toNumber(row.Age) ?? 0,
        nationality: String(row.Nationality ?? ""),
        overall: toNumber(row.Overall) ?? 0,
        potential: toNumber(row.Potential) ?? 0,
        club: String(row.Club ?? ""),
        position: String(row.Position ?? ""),
        jerseyNumber: toNumber(row["Jersey Number"]),
        height: String(row.Height ?? ""),
        weight: String(row.Weight ?? ""),
      };
    })
    .filter((p): p is Player => p !== undefined && p.name !== "");
}

export class SoccerRepository {
  readonly matches: Match[];
  readonly players: Player[];

  constructor(matches: Match[], players: Player[]) {
    this.matches = matches;
    this.players = players;
  }

  static load(): SoccerRepository {
    const matches = [
      ...loadBrasileirao(),
      ...loadBrazilianCup(),
      ...loadLibertadores(),
      ...loadExtendedStats(),
      ...loadHistorical(),
    ];

    // Deduplicate by a stable key so overlapping sources do not inflate counts.
    const seen = new Set<string>();
    const deduped: Match[] = [];
    for (const m of matches) {
      const key = `${m.date}|${fold(m.homeTeam)}|${fold(m.awayTeam)}|${m.homeGoal}|${m.awayGoal}|${m.competition}`;
      if (seen.has(key)) continue;
      seen.add(key);
      deduped.push(m);
    }

    const players = loadPlayers();
    return new SoccerRepository(deduped, players);
  }

  allCompetitions(): string[] {
    const set = new Set(this.matches.map((m) => m.competition));
    return Array.from(set).sort();
  }

  allTeams(): string[] {
    const set = new Set<string>();
    for (const m of this.matches) {
      set.add(m.homeTeam);
      set.add(m.awayTeam);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }
}
