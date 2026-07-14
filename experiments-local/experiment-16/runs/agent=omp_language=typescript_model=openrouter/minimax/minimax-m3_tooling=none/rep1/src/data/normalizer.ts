/**
 * Team name normalization.
 *
 * The Kaggle datasets use wildly different naming conventions:
 *   - "Palmeiras-SP"
 *   - "Palmeiras"
 *   - "Sport Club Corinthians Paulista"
 *   - "Sao Paulo" (BR-Football-Dataset, no diacritics)
 *   - "São Paulo" (Brasileirao with diacritics)
 *   - "América - MG"
 *   - "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
 *
 * For head-to-head queries we want a single canonical id per club so the
 * server can answer "Flamengo vs Fluminense" regardless of the source row
 * shape. The strategy is:
 *   1. Lowercase + remove diacritics.
 *   2. Strip known noise (parentheticals, " - UF" suffixes, state codes).
 *   3. Map well-known aliases to a stable canonical id ("Flamengo",
 *      "Palmeiras", etc).
 *   4. Fall back to a deterministic Title Case form.
 */

const ALIAS_MAP: Record<string, string> = {
  // Big clubs with multiple historical spellings in the data.
  'flamengo': 'Flamengo',
  'flamengo rj': 'Flamengo',
  'clube de regatas do flamengo': 'Flamengo',
  'palmeiras': 'Palmeiras',
  'palmeiras sp': 'Palmeiras',
  'sociedade esportiva palmeiras': 'Palmeiras',
  'corinthians': 'Corinthians',
  'sport club corinthians paulista': 'Corinthians',
  'corinthians sp': 'Corinthians',
  'sao paulo': 'São Paulo',
  'sao paulo sp': 'São Paulo',
  'são paulo': 'São Paulo',
  'são paulo fc': 'São Paulo',
  'sao paulo fc': 'São Paulo',
  'santos': 'Santos',
  'santos fc': 'Santos',
  'santos sp': 'Santos',
  'atletico mg': 'Atlético Mineiro',
  'atletico-mg': 'Atlético Mineiro',
  'atlético mineiro': 'Atlético Mineiro',
  'atlético-mg': 'Atlético Mineiro',
  'clube atlético mineiro': 'Atlético Mineiro',
  'gremio': 'Grêmio',
  'grêmio': 'Grêmio',
  'gremio rs': 'Grêmio',
  'internacional': 'Internacional',
  'internacional rs': 'Internacional',
  'sport club internacional': 'Internacional',
  'vasco': 'Vasco da Gama',
  'vasco da gama': 'Vasco da Gama',
  'botafogo': 'Botafogo',
  'botafogo rj': 'Botafogo',
  'botafogo fr': 'Botafogo',
  'fluminense': 'Fluminense',
  'athletico pr': 'Athletico Paranaense',
  'athletico-pr': 'Athletico Paranaense',
  'atletico pr': 'Athletico Paranaense',
  'atletico-paranaense': 'Athletico Paranaense',
  'athletico paranaense': 'Athletico Paranaense',
  'curitiba': 'Athletico Paranaense',
  'coritiba': 'Coritiba',
  'coritiba fc': 'Coritiba',
  'bahia': 'Bahia',
  'sport': 'Sport Recife',
  'sport recife': 'Sport Recife',
  'sport pe': 'Sport Recife',
  'sport clube recife': 'Sport Recife',
  'santa cruz': 'Santa Cruz',
  'nautico': 'Náutico',
  'náutico': 'Náutico',
  'cruzeiro': 'Cruzeiro',
  'cruzeiro mg': 'Cruzeiro',
  'america mg': 'América Mineiro',
  'america-mg': 'América Mineiro',
  'américa mineiro': 'América Mineiro',
  'america rn': 'América de Natal',
  'fortaleza': 'Fortaleza',
  'fortaleza ec': 'Fortaleza',
  'fortaleza esporte clube': 'Fortaleza',
  'ceara': 'Ceará',
  'ceará': 'Ceará',
  'ceara sc': 'Ceará',
  'goias': 'Goiás',
  'goiás': 'Goiás',
  'goianiense': 'Atlético Goianiense',
  'chapecoense sc': 'Chapecoense',
  'avaí': 'Avaí',
  'avai': 'Avaí',
  'criciuma': 'Criciúma',
  'criciúma': 'Criciúma',
  'juventude': 'Juventude',
  'bragantino': 'Red Bull Bragantino',
  'red bull bragantino': 'Red Bull Bragantino',
  'mirassol': 'Mirassol',
  'botafogo sp': 'Botafogo-SP',
  'botafogo-sp': 'Botafogo-SP',
  'santos laguna': 'Santos Laguna',
};

/** Brazilian state codes that sometimes appear as a " - XX" tail. */
const STATE_TAILS: Record<string, true> = {
  AC: true, AL: true, AM: true, AP: true, BA: true, CE: true,
  DF: true, ES: true, GO: true, MA: true, MG: true, MS: true,
  MT: true, PA: true, PB: true, PE: true, PI: true, PR: true,
  RJ: true, RN: true, RO: true, RR: true, RS: true, SC: true,
  SE: true, SP: true, TO: true
};

/** Strip diacritics from a string. */
export function stripDiacritics(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function noisePass(raw: string): string {
  let s = raw;
  // Drop parenthetical historical names, e.g.
  //   "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"
  s = s.replace(/\([^)]*\)/g, '');
  // Drop the " - XX" state tail when the suffix is a known UF code.
  const tailMatch = s.match(/\s*-\s*([A-Za-z]{2})\s*$/);
  if (tailMatch && STATE_TAILS[tailMatch[1].toUpperCase()]) {
    s = s.slice(0, tailMatch.index);
  }
  return s.replace(/\s+/g, ' ').trim();
}

function titleCase(s: string): string {
  return s
    .toLowerCase()
    .split(' ')
    .filter(Boolean)
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

/**
 * Return the canonical team id for a raw name. The canonical id is
 * Title Case, may keep diacritics (so user output looks right), and is
 * stable across all dataset shapes.
 */
export function canonicalTeam(raw: string): string {
  if (!raw) return '';
  const noised = noisePass(raw);
  const lowered = stripDiacritics(noised).toLowerCase();
  const direct = ALIAS_MAP[lowered];
  if (direct) return direct;
  if (lowered.length === 0) return '';
  return titleCase(noised);
}

/**
 * Test whether a candidate team name matches a user-supplied query.
 * The query is also normalized, and a hit is recorded when the candidate
 * appears as a substring of the query or vice versa, so that
 * "Flamengo" matches "Clube de Regatas do Flamengo".
 */
export function teamMatches(canonical: string, query: string): boolean {
  if (!canonical || !query) return false;
  const a = stripDiacritics(canonical).toLowerCase();
  const b = stripDiacritics(canonicalTeam(query)).toLowerCase();
  if (!a || !b) return false;
  return a === b || a.includes(b) || b.includes(a);
}
