/*
 * Brazilian Soccer MCP Server - Data normalization utilities
 *
 * Normalization handles the well-known inconsistencies in the provided CSV
 * datasets: team name variants, heterogeneous date formats and decimal number
 * strings, while preserving the raw display form for presentation.
 */

import { Match, ExtendedMatchStats, Player } from './types.js';

export interface LoaderOptions {
  dataDir: string;
}

const STATE_CODES = [
  'SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'GO', 'BA', 'PE', 'CE',
  'RN', 'PB', 'AL', 'SE', 'PI', 'MA', 'PA', 'AM', 'AP', 'AC',
  'RO', 'RR', 'TO', 'DF', 'ES', 'MT', 'MS'
];

const REMOVABLE_SUFFIXES: string[] = [
  ...STATE_CODES.map((code) => `-${code}`),
  ...STATE_CODES.map((code) => ` ${code}`),
  ' RJ',
  ' MG',
  ' SP',
  '(ANTIGO ESPORTE CLUBE BARREIRA)',
  ' (ANTIGO ESPORTE CLUBE BARREIRA)',
  '-(ANTIGO ESPORTE CLUBE BARREIRA)'
];

const NORMALIZATION_OVERRIDES_RAW: Record<string, string> = {
  'SÃO PAULO': 'Sao Paulo',
  'SAO PAULO': 'Sao Paulo',
  'SÃO PAULO FC': 'Sao Paulo',
  'SÃO PAULO FUTEBOL CLUBE': 'Sao Paulo',
  'CRUZEIRO': 'Cruzeiro',
  'CORINTHIANS': 'Corinthians',
  'SPORT CLUB CORINTHIANS PAULISTA': 'Corinthians',
  'PALMEIRAS': 'Palmeiras',
  'SOCIEDADE ESPORTIVA PALMEIRAS': 'Palmeiras',
  'FLAMENGO': 'Flamengo',
  'CLUBE DE REGATAS DO FLAMENGO': 'Flamengo',
  'FLUMINENSE': 'Fluminense',
  'FLUMINENSE FOOTBALL CLUB': 'Fluminense',
  'GRÊMIO': 'Gremio',
  'GRÊMIO FOOT-BALL PORTO-ALEGRENSE': 'Gremio',
  'INTERNACIONAL': 'Internacional',
  'SPORT CLUB INTERNACIONAL': 'Internacional',
  'ATLÉTICO MINEIRO': 'Atletico Mineiro',
  'CLUBE ATLÉTICO MINEIRO': 'Atletico Mineiro',
  'ATLÉTICO-MG': 'Atletico Mineiro',
  'ATLÉTICO MG': 'Atletico Mineiro',
  'ATLÉTICO CLUBE GOIANIENSE': 'Atletico Goianiense',
  'ATLÉTICO GOIANIENSE': 'Atletico Goianiense',
  'ATLÉTICO-GO': 'Atletico Goianiense',
  'ATLÉTICO PARANAENSE': 'Athletico Paranaense',
  'CLUBE ATLÉTICO PARANAENSE': 'Athletico Paranaense',
  'ATLÉTICO PR': 'Athletico Paranaense',
  'ATLÉTICO-PR': 'Athletico Paranaense',
  'ATHLÉTICO-PR': 'Athletico Paranaense',
  'ATHLETICO-PR': 'Athletico Paranaense',
  'ATHLETICO PARANAENSE': 'Athletico Paranaense',
  'SANTOS': 'Santos',
  'SANTOS FC': 'Santos',
  'SANTOS FUTEBOL CLUBE': 'Santos',
  'BOTAFOGO': 'Botafogo',
  'BOTAFOGO DE FUTEBOL E REGATAS': 'Botafogo',
  'BOTAFOGO FR': 'Botafogo',
  'VASCO': 'Vasco',
  'VASCO DA GAMA': 'Vasco',
  'CR VGAMA': 'Vasco',
  'CLUB DE REGATAS VASCO DA GAMA': 'Vasco',
  'BAHIA': 'Bahia',
  'ESPORTE CLUBE BAHIA': 'Bahia',
  'EC BAHIA': 'Bahia',
  'SPORT': 'Sport',
  'SPORT CLUB DO RECIFE': 'Sport',
  'SPORT RECIFE': 'Sport',
  'CEARÁ': 'Ceara',
  'CEARÁ SPORTING CLUB': 'Ceara',
  'FORTALEZA': 'Fortaleza',
  'FORTALEZA ESPORTE CLUBE': 'Fortaleza',
  'FORTALEZA FC': 'Fortaleza',
  'GOIÁS': 'Goias',
  'GOIÁS ESPORTE CLUBE': 'Goias',
  'CORITIBA': 'Coritiba',
  'CORITIBA FOOT BALL CLUB': 'Coritiba',
  'CSA': 'CSA',
  'AVAÍ': 'Avai',
  'AVAÍ FUTEBOL CLUBE': 'Avai',
  'CHAPECOENSE': 'Chapecoense',
  'ASSOCIAÇÃO CHAPECOENSE DE FUTEBOL': 'Chapecoense',
  'BOLÍVAR': 'Bolivar',
  'CLUB BOLÍVAR': 'Bolivar',
  'NACIONAL (URU)': 'Nacional',
  'CLUB NACIONAL DE FOOTBALL': 'Nacional',
  'BARCELONA-EQU': 'Barcelona SC',
  'BARCELONA SPORTING CLUB': 'Barcelona SC',
  'BAVISTA SPORT CLUB': 'Boavista',
  'BOAVISTA': 'Boavista',
  'AMÉRICA MINEIRO': 'America Mineiro',
  'AMÉRICA MG': 'America Mineiro',
  'AMÉRICA-MG': 'America Mineiro',
  'AMERICA MG': 'America Mineiro',
  'AMERICA-MG': 'America Mineiro',
  'AMÉRICA-RN': 'America RN',
  'ATLÉTICO': 'Atletico Mineiro',
  'ATLETICO': 'Atletico Mineiro',
  'PONTE PRETA': 'Ponte Preta',
  'ASSOCIAÇÃO ATLÉTICA PONTE PRETA': 'Ponte Preta',
  'FLAMENGO RJ': 'Flamengo',
  'BOTAFOGO RJ': 'Botafogo',
  'VASCO DA GAMA RJ': 'Vasco',
  'CORINTHIANS PAULISTA': 'Corinthians',
  'FERROVIÁRIA': 'Ferroviaria',
  'REMO': 'Clube Do Remo',
  'CLUBE DO REMO': 'Clube Do Remo',
  'FIGUEIRENSE': 'Figueirense',
  'JOINVILLE': 'Joinville'
};

const NORMALIZATION_OVERRIDES: Record<string, string> = Object.fromEntries(
  Object.entries(NORMALIZATION_OVERRIDES_RAW).map(([key, value]) => [
    removeDiacritics(key).toUpperCase().trim(),
    value
  ])
);

export function removeDiacritics(input: string): string {
  return input
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

export function normalizeTeamName(raw: string): string {
  if (!raw || typeof raw !== 'string') return raw || '';
  let normalized = raw.trim();

  const tryOverride = (value: string): string | undefined => {
    const lookupKey = removeDiacritics(value).toUpperCase().trim();
    return NORMALIZATION_OVERRIDES[lookupKey] ?? NORMALIZATION_OVERRIDES[value.toUpperCase().trim()];
  };

  // Try overrides on the raw name first (e.g., "Atlético-MG").
  const rawOverride = tryOverride(normalized);
  if (rawOverride) return rawOverride;

  // Strip common dataset suffixes such as "-SP" or " (antigo ...)".
  const upper = normalized.toUpperCase();
  for (const suffix of REMOVABLE_SUFFIXES) {
    if (upper.endsWith(suffix.toUpperCase())) {
      normalized = normalized.slice(0, -suffix.length).trim();
      break;
    }
  }

  // Try overrides again after suffix removal (e.g., "Atlético").
  const strippedOverride = tryOverride(normalized);
  return strippedOverride ?? normalized;
}

export function normalizeCompetition(raw: string): string {
  if (!raw) return 'Unknown';
  const normalized = removeDiacritics(raw).toUpperCase().trim();
  if (normalized.includes('SERIE A') || normalized.includes('CAMPEONATO BRASILEIRO') || normalized === 'BRASILEIRAO') {
    return 'Brasileirão';
  }
  if (normalized.includes('COPA DO BRASIL')) return 'Copa do Brasil';
  if (normalized.includes('LIBERTADORES')) return 'Copa Libertadores';
  return raw;
}

export function normalizeForSearch(raw: string): string {
  return removeDiacritics(raw).toLowerCase().replace(/[^a-z0-9]/g, '');
}

export function teamNamesMatch(a: string, b: string): boolean {
  if (!a || !b) return false;
  return normalizeTeamName(a).toLowerCase() === normalizeTeamName(b).toLowerCase();
}

export function teamNameContains(haystack: string, needle: string): boolean {
  if (!haystack || !needle) return false;
  const normalizedNeedle = normalizeTeamName(needle).toLowerCase();
  const normalizedHaystack = normalizeTeamName(haystack).toLowerCase();
  return normalizedHaystack.includes(normalizedNeedle);
}

export function parseBrazilianDate(value: string | number | undefined): Date | null {
  if (value === undefined || value === null || value === '') return null;
  const str = String(value).trim();

  // Plain ISO date: 2023-09-24 -> parse as local date.
  const isoDateMatch = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (isoDateMatch) {
    const [, year, month, day] = isoDateMatch;
    const parsed = new Date(Number(year), Number(month) - 1, Number(day));
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  // ISO-like date-time: 2012-05-19 18:30:00 or 2012-05-19T18:30:00.
  if (/^\d{4}-\d{2}-\d{2}[ T]/.test(str)) {
    const iso = str.replace(' ', 'T');
    const parsed = new Date(iso);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  // Brazilian format: 29/03/2003.
  const brMatch = str.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (brMatch) {
    const [, day, month, year] = brMatch;
    const parsed = new Date(Number(year), Number(month) - 1, Number(day));
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  return null;
}

export function formatDateISO(date: Date | null): string {
  if (!date || Number.isNaN(date.getTime())) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function parseNumber(value: string | number | undefined): number | null {
  if (value === undefined || value === null || value === '') return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  const cleaned = String(value)
    .replace(/,/g, '')
    .replace(/€/g, '')
    .replace(/M$/g, '')
    .replace(/K$/g, '')
    .trim();
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

export function parseIntSafe(value: string | number | undefined): number | null {
  const num = parseNumber(value);
  return num === null ? null : Math.floor(num);
}

export function parseYear(value: string | number | undefined): number | null {
  const num = parseNumber(value);
  if (num === null) return null;
  if (num >= 1900 && num <= 2100) return num;
  return null;
}

export function inferResult(match: Match): 'home' | 'away' | 'draw' | null {
  if (match.homeGoal === null || match.awayGoal === null) return null;
  if (match.homeGoal > match.awayGoal) return 'home';
  if (match.awayGoal > match.homeGoal) return 'away';
  return 'draw';
}

export function winnerTeam(match: Match): string | null {
  const result = inferResult(match);
  if (result === 'home') return match.homeTeam;
  if (result === 'away') return match.awayTeam;
  if (result === 'draw') return null;
  return null;
}

export function matchesSameFixture(m1: Match, m2: Match): boolean {
  return (
    m1.date === m2.date &&
    teamNamesMatch(m1.homeTeam, m2.homeTeam) &&
    teamNamesMatch(m1.awayTeam, m2.awayTeam) &&
    m1.competition === m2.competition
  );
}
