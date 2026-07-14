/**
 * Brazilian Soccer MCP Server - Team Name Normalization
 *
 * Datasets use inconsistent team names:
 *   - With state suffix: "Palmeiras-SP", "Flamengo-RJ"
 *   - Without suffix: "Palmeiras", "Flamengo"
 *   - Full club names: "Sport Club Corinthians Paulista"
 *   - Mangled: "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
 *
 * Strategy:
 *   1. Strip state suffix ( -XX, -XX, or just -XX at end)
 *   2. Strip parenthetical asides like "(antigo ...)"
 *   3. Map known full names to short names
 *   4. Lowercase and trim for matching
 *   5. Keep the original display name for output
 */


// Known full-to-short name mappings (lowercase)
const NAME_MAP: Record<string, string> = {
  'sport club corinthians paulista': 'corinthians',
  'sociedade esportiva palmeiras': 'palmeiras',
  'são paulo futebol clube': 'são paulo',
  'clube de regatas do flamengo': 'flamengo',
  'fluminense football club': 'fluminense',
  'cruzeiro esporte clube': 'cruzeiro',
  'clube atlético mineiro': 'atlético-mg',
  'grêmio foot-ball porto alegrense': 'grêmio',
  'sport club internacional': 'internacional',
  'santos futebol clube': 'santos',
  'botafogo de futebol e regatas': 'botafogo',
  'club de regatas vasco da gama': 'vasco',
  'club athletico paranaense': 'athletico-pr',
  'fortaleza esporte clube': 'fortaleza',
  'esporte clube bahia': 'bahia',
  'sport club do recife': 'sport',
  'ceará sporting club': 'ceará',
  'goiás esporte clube': 'goiás',
  'coritiba foot ball club': 'coritiba',
  'américa futebol clube': 'américa-mg',
  'atlético paranaense': 'athletico-pr',
  'atlético mineiro': 'atlético-mg',
};

// State suffix patterns to strip: " -XX" or "-XX" at end
const STATE_SUFFIX_RE = /\s*-\s*[A-Z]{2}\s*$/i;

// Parenthetical aside: "(antigo ...)"
const PARENTHETICAL_RE = /\s*\([^)]*\)\s*/g;

/**
 * Normalize a team name for matching.
 * Returns both the normalized key and the display name.
 */
export function normalizeTeam(raw: string | undefined | null): { key: string; display: string } {
  if (!raw) return { key: '', display: '' };
  let cleaned = raw.trim();

  // Remove parenthetical asides
  cleaned = cleaned.replace(PARENTHETICAL_RE, ' ').trim();

  // Remove state suffix
  let display = cleaned;
  cleaned = cleaned.replace(STATE_SUFFIX_RE, '').trim();

  // If after stripping suffix we have the shortened name, update display too
  if (cleaned !== display) {
    display = cleaned;
  }

  const key = cleaned.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  // Look up full name mapping
  if (NAME_MAP[key]) {
    return { key: NAME_MAP[key], display };
  }

  // If key is actually the full name, check if we mapped it
  return { key, display };
}

/**
 * Check if two normalized team names match (fuzzy comparison).
 * Handles cases like "São Paulo" vs "sao paulo" vs "sao_paulo".
 */
export function teamsMatch(a: string, b: string): boolean {
  return a === b;
}

/**
 * Strip accents from a string.
 */
export function stripAccents(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}
