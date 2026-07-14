import { normalize } from 'node:path';

export function normalizeTeamName(name: string): string {
  if (!name) return '';
  // Remove state suffix like -SP, -RJ, etc.
  let normalized = name
    .replace(/\s*[-–]\s*(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\s*$/i, '')
    .trim();
  // Remove extra parenthetical like (antigo ...)
  normalized = normalized.replace(/\s*\(.*?\)\s*$/, '').trim();
  // Normalize common name variations
  const aliases: Record<string, string> = {
    'sao paulo': 'São Paulo',
    'sao paulo fc': 'São Paulo',
    'sport club corinthians paulista': 'Corinthians',
    'cr flamengo': 'Flamengo',
    'clube de regatas do flamengo': 'Flamengo',
    'fluminense football club': 'Fluminense',
    'sociedade esportiva palmeiras': 'Palmeiras',
    'santos fc': 'Santos',
    'santos futebol clube': 'Santos',
    'gremio foot-ball porto alegrense': 'Grêmio',
    'gremio': 'Grêmio',
    'gremio rs': 'Grêmio',
    'sport club internacional': 'Internacional',
    'athletico-pr': 'Athletico Paranaense',
    'athletico paranaense': 'Athletico Paranaense',
    'atletico-pr': 'Athletico Paranaense',
    'atletico paranaense': 'Athletico Paranaense',
    'atletico mineiro': 'Atlético Mineiro',
    'atletico-mg': 'Atlético Mineiro',
    'atletico goianiense': 'Atlético Goianiense',
    'atletico-go': 'Atlético Goianiense',
    'avai': 'Avaí',
    'ceara': 'Ceará',
    'fortaleza': 'Fortaleza',
    'goias': 'Goiás',
    'parana': 'Paraná',
    'vasco da gama': 'Vasco da Gama',
    'cr vasco da gama': 'Vasco da Gama',
    'botafogo': 'Botafogo',
    'botafogo de futebol e regatas': 'Botafogo',
    'cruzeiro': 'Cruzeiro',
    'cruzeiro esporte clube': 'Cruzeiro',
    'bahia': 'Bahia',
    'ec bahia': 'Bahia',
    'esporte clube bahia': 'Bahia',
    'flamengo rj': 'Flamengo',
    'flamengo-rj': 'Flamengo',
    'fluminense rj': 'Fluminense',
    'fluminense-rj': 'Fluminense',
    'vasco rj': 'Vasco da Gama',
    'vasco-rj': 'Vasco da Gama',
    'botafogo rj': 'Botafogo',
    'botafogo-rj': 'Botafogo',
    'corinthians sp': 'Corinthians',
    'corinthians-sp': 'Corinthians',
    'palmeiras sp': 'Palmeiras',
    'palmeiras-sp': 'Palmeiras',
    'sao paulo sp': 'São Paulo',
    'sao paulo-sp': 'São Paulo',
    'santos sp': 'Santos',
    'santos-sp': 'Santos',
    'portuguesa sp': 'Portuguesa',
    'portuguesa-sp': 'Portuguesa',
    'ponte preta': 'Ponte Preta',
    'guarani': 'Guarani',
    'ituano': 'Ituano',
    'juventude': 'Juventude',
  };
  const lower = normalized.toLowerCase();
  if (aliases[lower]) return aliases[lower];
  return normalized;
}

export function canonicalTeamKey(name: string): string {
  return normalizeTeamName(name).toLowerCase();
}

export function normalizeCompetition(name: string): string {
  if (!name) return 'Unknown';
  const lower = name.toLowerCase();
  if (lower.includes('libertadores')) return 'Copa Libertadores';
  if (lower.includes('cop') && lower.includes('brasil')) return 'Copa do Brasil';
  if (lower.includes('brasileirao') || lower.includes('serie a') || lower.includes('campeonato brasileiro')) return 'Brasileirão';
  return name;
}

export function parseNumber(value: unknown): number | undefined {
  if (value === undefined || value === null || value === '') return undefined;
  if (typeof value === 'number') return Number.isNaN(value) ? undefined : value;
  const parsed = Number(String(value).trim());
  return Number.isNaN(parsed) ? undefined : parsed;
}

export function parseDate(value: string | undefined): Date | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();
  // Try ISO / datetime format
  const iso = new Date(trimmed);
  if (!Number.isNaN(iso.getTime())) return iso;
  // Brazilian format DD/MM/YYYY
  const parts = trimmed.split('/');
  if (parts.length === 3) {
    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const year = parseInt(parts[2], 10);
    const date = new Date(year, month, day);
    if (!Number.isNaN(date.getTime())) return date;
  }
  return undefined;
}

export function formatDate(date: Date | undefined): string | undefined {
  if (!date) return undefined;
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
