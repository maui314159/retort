/**
 * Brazilian Soccer MCP Server
 * Data loading and normalization module.
 *
 * Loads all provided CSV datasets from data/kaggle/ and exposes a single
 * typed repository for players, matches, and competitions.
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { parse } from 'csv-parse/sync';

export type Competition =
  | 'Brasileirão'
  | 'Copa do Brasil'
  | 'Copa Libertadores'
  | 'BR-Football-Dataset'
  | 'Historical Brasileirão';

export interface Match {
  competition: Competition;
  season: number | null;
  round: string | null;
  stage: string | null;
  datetime: Date | null;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number | null;
  awayGoals: number | null;
  homeTeamState: string | null;
  awayTeamState: string | null;
  venue: string | null;
  sourceFile: string;
}

export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string | null;
  overall: number | null;
  potential: number | null;
  club: string | null;
  position: string | null;
  jerseyNumber: number | null;
  height: string | null;
  weight: string | null;
}

export interface SoccerRepository {
  players: Player[];
  matches: Match[];
  competitions: Competition[];
}

const DATA_DIR = path.resolve('data/kaggle');

function cleanValue(value: unknown): string {
  if (value === undefined || value === null) return '';
  const trimmed = String(value).trim();
  return trimmed === '""' ? '' : trimmed;
}

function parseNumber(value: unknown): number | null {
  const cleaned = cleanValue(value);
  if (cleaned === '') return null;
  const normalized = cleaned.replace(',', '.');
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseIntNumber(value: unknown): number | null {
  const n = parseNumber(value);
  return n === null ? null : Math.trunc(n);
}

function parseDate(value: unknown): Date | null {
  const raw = cleanValue(value);
  if (!raw) return null;

  // Brazilian format: DD/MM/YYYY
  const brMatch = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (brMatch) {
    const [, d, m, y] = brMatch;
    const date = new Date(Number(y), Number(m) - 1, Number(d));
    return Number.isNaN(date.getTime()) ? null : date;
  }

  // ISO / datetime with time
  const iso = raw.replace(' ', 'T');
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

function normalizeTeamName(name: string): string {
  return name
    .replace(/\s+/g, ' ')
    .replace(/\s*-\s*(SP|RJ|MG|PR|RS|SC|BA|CE|PE|GO|PA|MT|MS|AM|RN|PB|AL|SE|PI|TO|AC|AP|RR|RO|DF|ES|Vitoria)$/gi, '')
    .replace(/\s*(FC|EC|AC|AD|CA)\.?$/i, '')
    .replace(/Futebol Clube$/i, '')
    .replace(/Esporte Clube$/i, '')
    .replace(/Atlético$/i, '')
    .replace(/Sport Club$/i, '')
    .replace(/Sociedade Esportiva$/i, '')
    .replace(/Clube de Regatas do$/i, '')
    .replace(/Clube de Regatas$/i, '')
    .trim();
}

export function canonicalizeTeamName(name: string): string {
  const normalized = normalizeTeamName(name);
  const lower = normalized.toLowerCase();
  const unaccented = removeAccents(lower);
  const variations: Record<string, string> = {
    'atletico': 'Atlético Mineiro',
    'athletico pr': 'Athletico Paranaense',
    'athletico-paranaense': 'Athletico Paranaense',
    'athletico paranaense': 'Athletico Paranaense',
    'atletico pr': 'Athletico Paranaense',
    'atletico mg': 'Atlético Mineiro',
    'atletico-mg': 'Atlético Mineiro',
    'atletico mineiro': 'Atlético Mineiro',
    'atletico go': 'Atlético Goianiense',
    'gremio': 'Grêmio',
    'sao paulo': 'São Paulo',
    'flamengo': 'Flamengo',
    'fluminense': 'Fluminense',
    'palmeiras': 'Palmeiras',
    'corinthians': 'Corinthians',
    'santos': 'Santos',
    'vasco': 'Vasco da Gama',
    'vasco da gama': 'Vasco da Gama',
    'botafogo': 'Botafogo',
    'internacional': 'Internacional',
    'cruzeiro': 'Cruzeiro',
    'bahia': 'Bahia',
    'sport': 'Sport Recife',
    'sport recife': 'Sport Recife',
    'fortaleza': 'Fortaleza',
    'ceara': 'Ceará',
    'goias': 'Goiás',
    'coritiba': 'Coritiba',
    'pontepreta': 'Ponte Preta',
    'ponte preta': 'Ponte Preta',
    'nautico': 'Náutico',
    'figueirense': 'Figueirense',
    'vitoria': 'Vitória',
    'avai': 'Avaí',
    'chapecoense': 'Chapecoense',
    'america': 'América Mineiro',
    'america mg': 'América Mineiro',
    'america mineiro': 'América Mineiro',
    'america rj': 'América RJ',
    'america rn': 'América RN',
    'parana': 'Paraná',
    'juventude': 'Juventude',
    'cuiaba': 'Cuiabá',
    'bragantino': 'Bragantino',
    'red bull bragantino': 'Red Bull Bragantino',
    'londrina': 'Londrina',
    'remo': 'Remo',
    'paysandu': 'Paysandu',
    'santa cruz': 'Santa Cruz',
    'criciuma': 'Criciúma',
    'guarani': 'Guarani',
    'portuguesa': 'Portuguesa',
  };

  for (const [pattern, canonical] of Object.entries(variations)) {
    if (lower === pattern || unaccented === pattern) {
      return canonical;
    }
  }

  return normalized.replace(/\b\w/g, (c) => c.toUpperCase());
}

function removeAccents(input: string): string {
  return input.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

export function matchesTeam(candidate: string, query: string): boolean {
  const c = removeAccents(candidate.toLowerCase());
  const q = removeAccents(query.toLowerCase());
  if (c.includes(q) || q.includes(c)) return true;
  const canonicalCandidate = removeAccents(canonicalizeTeamName(candidate).toLowerCase());
  const canonicalQuery = removeAccents(canonicalizeTeamName(query).toLowerCase());
  return canonicalCandidate === canonicalQuery || canonicalCandidate.includes(canonicalQuery);
}

function stripBom(buffer: Buffer): string {
  return buffer.toString('utf-8').replace(/^\uFEFF/, '');
}

async function loadCsv(fileName: string): Promise<Record<string, string>[]> {
  const filePath = path.join(DATA_DIR, fileName);
  const buffer = await fs.readFile(filePath);
  const content = stripBom(buffer);
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
  }) as Record<string, string>[];
}

async function loadBrasileirao(): Promise<Match[]> {
  const rows = await loadCsv('Brasileirao_Matches.csv');
  return rows.map((row) => ({
    competition: 'Brasileirão' as const,
    season: parseIntNumber(row['season']),
    round: cleanValue(row['round']),
    stage: null,
    datetime: parseDate(row['datetime']),
    homeTeam: canonicalizeTeamName(cleanValue(row['home_team'])),
    awayTeam: canonicalizeTeamName(cleanValue(row['away_team'])),
    homeGoals: parseIntNumber(row['home_goal']),
    awayGoals: parseIntNumber(row['away_goal']),
    homeTeamState: cleanValue(row['home_team_state']) || null,
    awayTeamState: cleanValue(row['away_team_state']) || null,
    venue: null,
    sourceFile: 'Brasileirao_Matches.csv',
  }));
}

async function loadCopaDoBrasil(): Promise<Match[]> {
  const rows = await loadCsv('Brazilian_Cup_Matches.csv');
  return rows.map((row) => ({
    competition: 'Copa do Brasil' as const,
    season: parseIntNumber(row['season']),
    round: cleanValue(row['round']),
    stage: null,
    datetime: parseDate(row['datetime']),
    homeTeam: canonicalizeTeamName(cleanValue(row['home_team'])),
    awayTeam: canonicalizeTeamName(cleanValue(row['away_team'])),
    homeGoals: parseIntNumber(row['home_goal']),
    awayGoals: parseIntNumber(row['away_goal']),
    homeTeamState: null,
    awayTeamState: null,
    venue: null,
    sourceFile: 'Brazilian_Cup_Matches.csv',
  }));
}

async function loadLibertadores(): Promise<Match[]> {
  const rows = await loadCsv('Libertadores_Matches.csv');
  return rows.map((row) => ({
    competition: 'Copa Libertadores' as const,
    season: parseIntNumber(row['season']),
    round: null,
    stage: cleanValue(row['stage']),
    datetime: parseDate(row['datetime']),
    homeTeam: canonicalizeTeamName(cleanValue(row['home_team'])),
    awayTeam: canonicalizeTeamName(cleanValue(row['away_team'])),
    homeGoals: parseIntNumber(row['home_goal']),
    awayGoals: parseIntNumber(row['away_goal']),
    homeTeamState: null,
    awayTeamState: null,
    venue: null,
    sourceFile: 'Libertadores_Matches.csv',
  }));
}

async function loadBrFootballDataset(): Promise<Match[]> {
  const rows = await loadCsv('BR-Football-Dataset.csv');
  return rows.map((row) => {
    const competitionName = cleanValue(row['tournament']);
    let competition: Competition = 'BR-Football-Dataset';
    if (/brasileir/i.test(competitionName)) competition = 'Brasileirão';
    else if (/copabrasil|copa do brasil/i.test(competitionName)) competition = 'Copa do Brasil';
    else if (/libertadores/i.test(competitionName)) competition = 'Copa Libertadores';

    return {
      competition,
      season: parseDate(row['date'])?.getFullYear() ?? null,
      round: null,
      stage: null,
      datetime: parseDate(`${cleanValue(row['date'])} ${cleanValue(row['time'])}`),
      homeTeam: canonicalizeTeamName(cleanValue(row['home'])),
      awayTeam: canonicalizeTeamName(cleanValue(row['away'])),
      homeGoals: parseIntNumber(row['home_goal']),
      awayGoals: parseIntNumber(row['away_goal']),
      homeTeamState: null,
      awayTeamState: null,
      venue: null,
      sourceFile: 'BR-Football-Dataset.csv',
    };
  });
}

async function loadHistoricalBrasileirao(): Promise<Match[]> {
  const rows = await loadCsv('novo_campeonato_brasileiro.csv');
  return rows.map((row) => ({
    competition: 'Brasileirão' as const,
    season: parseIntNumber(row['Ano']),
    round: cleanValue(row['Rodada']),
    stage: null,
    datetime: parseDate(row['Data']),
    homeTeam: canonicalizeTeamName(cleanValue(row['Equipe_mandante'])),
    awayTeam: canonicalizeTeamName(cleanValue(row['Equipe_visitante'])),
    homeGoals: parseIntNumber(row['Gols_mandante']),
    awayGoals: parseIntNumber(row['Gols_visitante']),
    homeTeamState: cleanValue(row['Mandante_UF']) || null,
    awayTeamState: cleanValue(row['Visitante_UF']) || null,
    venue: cleanValue(row['Arena']) || null,
    sourceFile: 'novo_campeonato_brasileiro.csv',
  }));
}

async function loadPlayers(): Promise<Player[]> {
  const rows = await loadCsv('fifa_data.csv');
  const dedupe = new Set<string>();
  const players: Player[] = [];
  for (const row of rows) {
    const id = parseIntNumber(row['ID']);
    const name = cleanValue(row['Name']);
    if (id === null || !name) continue;
    const key = `${id}-${name}`;
    if (dedupe.has(key)) continue;
    dedupe.add(key);
    players.push({
      id,
      name,
      age: parseIntNumber(row['Age']),
      nationality: cleanValue(row['Nationality']) || null,
      overall: parseIntNumber(row['Overall']),
      potential: parseIntNumber(row['Potential']),
      club: cleanValue(row['Club']) || null,
      position: cleanValue(row['Position']) || null,
      jerseyNumber: parseIntNumber(row['Jersey Number']),
      height: cleanValue(row['Height']) || null,
      weight: cleanValue(row['Weight']) || null,
    });
  }
  return players;
}

export async function loadRepository(): Promise<SoccerRepository> {
  const [brasileirao, copa, libertadores, brFootball, historical, players] = await Promise.all([
    loadBrasileirao(),
    loadCopaDoBrasil(),
    loadLibertadores(),
    loadBrFootballDataset(),
    loadHistoricalBrasileirao(),
    loadPlayers(),
  ]);

  const matches = [
    ...brasileirao,
    ...copa,
    ...libertadores,
    ...brFootball,
    ...historical,
  ];

  const competitionSet = new Set<Competition>();
  for (const m of matches) competitionSet.add(m.competition);
  const competitions = Array.from(competitionSet);

  return { matches, players, competitions };
}
