/**
 * Team-name and date normalization utilities.
 *
 * The six source datasets use inconsistent naming conventions:
 *   - state suffixes:   "Palmeiras-SP", "Flamengo - RJ", "Audax SP"
 *   - accent variants:  "São Paulo" vs "Sao Paulo", "Grêmio" vs "Gremio"
 *   - punctuation:      "A.b.c. - RN" vs "Abc - RN"
 *   - full legal names: "Sport Club Corinthians Paulista"
 *
 * Matching is done on a *simplified* form (lower-case, accent-free, no dots)
 * plus, when known, the Brazilian state code, so that distinct same-named
 * clubs (e.g. "Botafogo-RJ" vs "Botafogo PB") stay separate while spelling
 * variants of the same club collapse into one identity.
 */

/** Brazilian state (UF) codes used as team-name suffixes. */
export const STATE_CODES = new Set([
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
  'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE',
  'TO',
]);

/**
 * Simplify a string for comparison: strip accents, lower-case, remove dots,
 * collapse whitespace. "São Paulo - SP" -> "sao paulo - sp".
 */
export function simplify(raw: string): string {
  return raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\./g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export interface ParsedTeamName {
  /** Simplified base name without state suffix, e.g. "atletico mineiro". */
  base: string;
  /** State code when present/derivable, e.g. "MG". */
  state?: string;
}

interface Alias {
  base: string;
  state?: string;
}

/**
 * Explicit aliases for well-known clubs, keyed by the *simplified* full raw
 * name. These exist because naive state-stripping loses information
 * ("Atletico-MG" would become "atletico") or because clubs are known by
 * several legal/commercial names ("Red Bull Bragantino" == "Bragantino").
 */
const TEAM_ALIASES: Record<string, Alias> = {
  // Atlético Mineiro
  'atletico-mg': { base: 'atletico mineiro', state: 'MG' },
  'atletico - mg': { base: 'atletico mineiro', state: 'MG' },
  'atletico mg': { base: 'atletico mineiro', state: 'MG' },
  'atletico mineiro - mg': { base: 'atletico mineiro', state: 'MG' },
  'clube atletico mineiro': { base: 'atletico mineiro', state: 'MG' },
  // Athletico Paranaense
  'athletico-pr': { base: 'athletico paranaense', state: 'PR' },
  'atletico-pr': { base: 'athletico paranaense', state: 'PR' },
  'atletico - pr': { base: 'athletico paranaense', state: 'PR' },
  'athletico - pr': { base: 'athletico paranaense', state: 'PR' },
  'athletico paranaense - pr': { base: 'athletico paranaense', state: 'PR' },
  'atletico paranaense - pr': { base: 'athletico paranaense', state: 'PR' },
  'atletico paranaense': { base: 'athletico paranaense', state: 'PR' },
  athletico: { base: 'athletico paranaense', state: 'PR' },
  'club athletico paranaense': { base: 'athletico paranaense', state: 'PR' },
  // Atlético Goianiense
  'atletico-go': { base: 'atletico goianiense', state: 'GO' },
  'atletico - go': { base: 'atletico goianiense', state: 'GO' },
  'atletico goianiense - go': { base: 'atletico goianiense', state: 'GO' },
  // América Mineiro
  'america-mg': { base: 'america mineiro', state: 'MG' },
  'america - mg': { base: 'america mineiro', state: 'MG' },
  'america mg': { base: 'america mineiro', state: 'MG' },
  'america fc (minas gerais)': { base: 'america mineiro', state: 'MG' },
  // América de Natal (RN)
  'america-rn': { base: 'america de natal', state: 'RN' },
  'america - rn': { base: 'america de natal', state: 'RN' },
  'america rn': { base: 'america de natal', state: 'RN' },
  'america de natal - rn': { base: 'america de natal', state: 'RN' },
  'america fc natal': { base: 'america de natal', state: 'RN' },
  // Sport Recife
  'sport recife': { base: 'sport', state: 'PE' },
  'sport club do recife': { base: 'sport', state: 'PE' },
  // Vasco
  'vasco da gama': { base: 'vasco', state: 'RJ' },
  'vasco da gama - rj': { base: 'vasco', state: 'RJ' },
  'vasco da gama rj': { base: 'vasco', state: 'RJ' },
  'clube de regatas vasco da gama': { base: 'vasco', state: 'RJ' },
  // Corinthians
  'sport club corinthians paulista': { base: 'corinthians', state: 'SP' },
  'corinthians - sp': { base: 'corinthians', state: 'SP' },
  // Flamengo
  'clube de regatas do flamengo': { base: 'flamengo', state: 'RJ' },
  // Bragantino / Red Bull Bragantino
  bragantino: { base: 'bragantino', state: 'SP' },
  'red bull bragantino': { base: 'bragantino', state: 'SP' },
  'red bull bragantino - sp': { base: 'bragantino', state: 'SP' },
  'bragantino - sp': { base: 'bragantino', state: 'SP' },
  'bragantino sp': { base: 'bragantino', state: 'SP' },
  // Náutico
  'nautico capibaribe': { base: 'nautico', state: 'PE' },
  // Boavista (RJ)
  'boavista sport club (antigo esporte clube barreira) - rj': {
    base: 'boavista',
    state: 'RJ',
  },
  'boavista sc saquarema': { base: 'boavista', state: 'RJ' },
  'boavista rj': { base: 'boavista', state: 'RJ' },
  // Fortaleza
  'fortaleza ec': { base: 'fortaleza', state: 'CE' },
  'fortaleza fc': { base: 'fortaleza', state: 'CE' },
  'fortaleza esporte clube': { base: 'fortaleza', state: 'CE' },
  // Vitória (BA) — bare "Vitória" is always the BA club; the ES club always
  // carries an explicit "ES" suffix. Also works around wrong UF="ES" values
  // in the historico file's home-team state column.
  vitoria: { base: 'vitoria', state: 'BA' },
  'ec vitoria': { base: 'vitoria', state: 'BA' },
  'vitoria ec': { base: 'vitoria', state: 'BA' },
  'esporte clube vitoria': { base: 'vitoria', state: 'BA' },
  // Bahia
  'ec bahia': { base: 'bahia', state: 'BA' },
  'esporte clube bahia': { base: 'bahia', state: 'BA' },
  // Juventude (RS)
  'ec juventude': { base: 'juventude', state: 'RS' },
  // Caxias (RS)
  'ser caxias - rs': { base: 'caxias', state: 'RS' },
  // São José (RS) — "São José - POA" uses the Porto Alegre abbreviation
  'sao jose - poa': { base: 'sao jose', state: 'RS' },
  'sao jose rs': { base: 'sao jose', state: 'RS' },
  // Brasil de Pelotas
  'brasil de pelotas': { base: 'brasil', state: 'RS' },
  'brasil - rs': { base: 'brasil', state: 'RS' },
  // Guarani de Juazeiro (CE) vs Guarani (SP)
  'guarani de juazeiro': { base: 'guarani', state: 'CE' },
  'guarani de juazeiro - ce': { base: 'guarani', state: 'CE' },
  // EC/FC suffix variants that would otherwise create duplicate identities
  'globo fc': { base: 'globo', state: 'RN' },
  'santa cruz fc': { base: 'santa cruz', state: 'PE' },
  'campinense clube': { base: 'campinense', state: 'PB' },
  'retro fc brasil': { base: 'retro', state: 'PE' },
  'nova mutum ec': { base: 'nova mutum', state: 'MT' },
  'vilhenense ec': { base: 'vilhenense', state: 'RO' },
  'amadense ec': { base: 'amadense', state: 'SE' },
  'cordino ec': { base: 'cordino', state: 'MA' },
  'floresta ec': { base: 'floresta', state: 'CE' },
  'tocantinopolis ec': { base: 'tocantinopolis', state: 'TO' },
  'tuntum ec': { base: 'tuntum', state: 'MA' },
  'sousa ec': { base: 'sousa', state: 'PB' },
  'souza - pb': { base: 'sousa', state: 'PB' },
  'toledo ec': { base: 'toledo', state: 'PR' },
  'porto velho ec': { base: 'porto velho', state: 'RO' },
  'duque de caxias fc': { base: 'duque de caxias', state: 'RJ' },
  'duque de caxias rj': { base: 'duque de caxias', state: 'RJ' },
  'macae esporte fc': { base: 'macae esporte', state: 'RJ' },
  'macae esporte rj': { base: 'macae esporte', state: 'RJ' },
  'cuiaba mt': { base: 'cuiaba', state: 'MT' },
  'remo pa': { base: 'remo', state: 'PA' },
  'paysandu - pa': { base: 'paysandu', state: 'PA' },
  'parana-pr': { base: 'parana', state: 'PR' },
  'parana - pr': { base: 'parana', state: 'PR' },
  'ce aimore': { base: 'aimore', state: 'RS' },
  'aimore - rs': { base: 'aimore', state: 'RS' },
  '4 de julho ec': { base: '4 de julho', state: 'PI' },
  '4 de julho - pi': { base: '4 de julho', state: 'PI' },
  'goias-go': { base: 'goias', state: 'GO' },
  'goias - go': { base: 'goias', state: 'GO' },
  'vila nova - go': { base: 'vila nova', state: 'GO' },
  'villa nova - mg': { base: 'villa nova', state: 'MG' },
  'criciuma-sc': { base: 'criciuma', state: 'SC' },
  'criciuma - sc': { base: 'criciuma', state: 'SC' },
  'figueirense-sc': { base: 'figueirense', state: 'SC' },
  'figueirense - sc': { base: 'figueirense', state: 'SC' },
  'chapecoense-sc': { base: 'chapecoense', state: 'SC' },
  'chapecoense - sc': { base: 'chapecoense', state: 'SC' },
  'joinville-sc': { base: 'joinville', state: 'SC' },
  'joinville - sc': { base: 'joinville', state: 'SC' },
  'avai-sc': { base: 'avai', state: 'SC' },
  'avai - sc': { base: 'avai', state: 'SC' },
  'coritiba-pr': { base: 'coritiba', state: 'PR' },
  'coritiba - pr': { base: 'coritiba', state: 'PR' },
  'coritiba pr': { base: 'coritiba', state: 'PR' },
  'londrina - pr': { base: 'londrina', state: 'PR' },
  'santos-sp': { base: 'santos', state: 'SP' },
  'santos - sp': { base: 'santos', state: 'SP' },
  'ponte preta-sp': { base: 'ponte preta', state: 'SP' },
  'ponte preta - sp': { base: 'ponte preta', state: 'SP' },
  'guarani-sp': { base: 'guarani', state: 'SP' },
  'guarani - sp': { base: 'guarani', state: 'SP' },
  'guarani sp': { base: 'guarani', state: 'SP' },
  'portuguesa-sp': { base: 'portuguesa', state: 'SP' },
  'portuguesa - sp': { base: 'portuguesa', state: 'SP' },
  'portuguesa desportos': { base: 'portuguesa', state: 'SP' },
  'ad confianca': { base: 'confianca', state: 'SE' },
  'clube do remo': { base: 'remo', state: 'PA' },
  'palmeiras-sp': { base: 'palmeiras', state: 'SP' },
  'palmeiras - sp': { base: 'palmeiras', state: 'SP' },
  'sao paulo-sp': { base: 'sao paulo', state: 'SP' },
  'sao paulo - sp': { base: 'sao paulo', state: 'SP' },
  'sao caetano - sp': { base: 'sao caetano', state: 'SP' },
  'sao bento - sp': { base: 'sao bento', state: 'SP' },
  'mirassol - sp': { base: 'mirassol', state: 'SP' },
  'ituano - sp': { base: 'ituano', state: 'SP' },
  'novorizontino - sp': { base: 'novorizontino', state: 'SP' },
  'gremio novorizontino': { base: 'novorizontino', state: 'SP' },
  'inter de limeira': { base: 'inter de limeira', state: 'SP' },
  'inter de limeira - sp': { base: 'inter de limeira', state: 'SP' },
  'flamengo-rj': { base: 'flamengo', state: 'RJ' },
  'flamengo - rj': { base: 'flamengo', state: 'RJ' },
  'fluminense-rj': { base: 'fluminense', state: 'RJ' },
  'fluminense - rj': { base: 'fluminense', state: 'RJ' },
  'fluminense rj': { base: 'fluminense', state: 'RJ' },
  'botafogo-rj': { base: 'botafogo', state: 'RJ' },
  'botafogo - rj': { base: 'botafogo', state: 'RJ' },
  'botafogo rj': { base: 'botafogo', state: 'RJ' },
  'botafogo sp': { base: 'botafogo', state: 'SP' },
  'botafogo - sp': { base: 'botafogo', state: 'SP' },
  'botafogo pb': { base: 'botafogo', state: 'PB' },
  'botafogo - pb': { base: 'botafogo', state: 'PB' },
  'cruzeiro-mg': { base: 'cruzeiro', state: 'MG' },
  'cruzeiro - mg': { base: 'cruzeiro', state: 'MG' },
  'gremio-rs': { base: 'gremio', state: 'RS' },
  'gremio - rs': { base: 'gremio', state: 'RS' },
  'gremio rs': { base: 'gremio', state: 'RS' },
  'internacional-rs': { base: 'internacional', state: 'RS' },
  'internacional - rs': { base: 'internacional', state: 'RS' },
  'internacional rs': { base: 'internacional', state: 'RS' },
  'juventude-rs': { base: 'juventude', state: 'RS' },
  'juventude - rs': { base: 'juventude', state: 'RS' },
  'juventude rs': { base: 'juventude', state: 'RS' },
  'juventude ma': { base: 'juventude', state: 'MA' },
  'sport-pe': { base: 'sport', state: 'PE' },
  'sport - pe': { base: 'sport', state: 'PE' },
  'nautico-pe': { base: 'nautico', state: 'PE' },
  'nautico - pe': { base: 'nautico', state: 'PE' },
  'santa cruz - pe': { base: 'santa cruz', state: 'PE' },
  'santa cruz-pe': { base: 'santa cruz', state: 'PE' },
  'santa cruz rn': { base: 'santa cruz', state: 'RN' },
  'santa cruz rs': { base: 'santa cruz', state: 'RS' },
  'bahia - ba': { base: 'bahia', state: 'BA' },
  'bahia-ba': { base: 'bahia', state: 'BA' },
  'vitoria - ba': { base: 'vitoria', state: 'BA' },
  'vitoria-ba': { base: 'vitoria', state: 'BA' },
  'vitoria es': { base: 'vitoria', state: 'ES' },
  'vitoria f c - es': { base: 'vitoria', state: 'ES' },
  'ceara - ce': { base: 'ceara', state: 'CE' },
  'ceara-ce': { base: 'ceara', state: 'CE' },
  'fortaleza - ce': { base: 'fortaleza', state: 'CE' },
  'fortaleza-ce': { base: 'fortaleza', state: 'CE' },
  'goias-go ': { base: 'goias', state: 'GO' },
};

/** Preferred display names for the most-queried clubs. */
const DISPLAY_NAMES: Record<string, string> = {
  'atletico mineiro#MG': 'Atlético Mineiro',
  'athletico paranaense#PR': 'Athletico Paranaense',
  'atletico goianiense#GO': 'Atlético Goianiense',
  'america mineiro#MG': 'América Mineiro',
  'america de natal#RN': 'América de Natal',
  'sport#PE': 'Sport Recife',
  'vasco#RJ': 'Vasco da Gama',
  'corinthians#SP': 'Corinthians',
  'palmeiras#SP': 'Palmeiras',
  'sao paulo#SP': 'São Paulo',
  'santos#SP': 'Santos',
  'flamengo#RJ': 'Flamengo',
  'fluminense#RJ': 'Fluminense',
  'botafogo#RJ': 'Botafogo',
  'vasco da gama#RJ': 'Vasco da Gama',
  'gremio#RS': 'Grêmio',
  'internacional#RS': 'Internacional',
  'cruzeiro#MG': 'Cruzeiro',
  'bahia#BA': 'Bahia',
  'vitoria#BA': 'Vitória',
  'fortaleza#CE': 'Fortaleza',
  'ceara#CE': 'Ceará',
  'sport recife#PE': 'Sport Recife',
  'nautico#PE': 'Náutico',
  'santa cruz#PE': 'Santa Cruz',
  'goias#GO': 'Goiás',
  'coritiba#PR': 'Coritiba',
  'avai#SC': 'Avaí',
  'figueirense#SC': 'Figueirense',
  'criciuma#SC': 'Criciúma',
  'chapecoense#SC': 'Chapecoense',
  'juventude#RS': 'Juventude',
  'brasil#RS': 'Brasil de Pelotas',
  'parana#PR': 'Paraná',
  'ponte preta#SP': 'Ponte Preta',
  'guarani#SP': 'Guarani',
  'portuguesa#SP': 'Portuguesa',
  'bragantino#SP': 'Red Bull Bragantino',
  'cuiaba#MT': 'Cuiabá',
  'vila nova#GO': 'Vila Nova',
  'remo#PA': 'Remo',
  'paysandu#PA': 'Paysandu',
};

/** Build the identity key for a base+state pair. */
export function teamKey(base: string, state?: string): string {
  return state ? `${base}#${state.toUpperCase()}` : base;
}

/** Curated display name for a base+state pair, when one exists. */
export function curatedDisplayName(base: string, state?: string): string | undefined {
  return DISPLAY_NAMES[teamKey(base, state)];
}

/** Title-case a simplified base name, keeping Portuguese connectives lower-case. */
export function titleCase(base: string): string {
  const small = new Set(['de', 'da', 'do', 'das', 'dos', 'e']);
  return base
    .split(' ')
    .map((w, i) => (i > 0 && small.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ');
}

/** Human-friendly label for a key, e.g. "Flamengo (RJ)". */
export function displayNameFor(base: string, state?: string, rawFallback?: string): string {
  const curated = DISPLAY_NAMES[teamKey(base, state)];
  if (curated) return curated;
  if (rawFallback) return rawFallback;
  const titled = titleCase(base);
  return state ? `${titled} (${state.toUpperCase()})` : titled;
}

const TRAILING_PAREN = /^(.*?)\s*\(([^)]{2,5})\)\s*$/;
const TRAILING_STATE = /^(.*?)\s*[-–]\s*([A-Za-z]{2})\s*$/;
const TRAILING_STATE_SPACE = /^(.*?)\s+([A-Za-z]{2})\s*$/;

/**
 * Parse a raw team name into { base, state }.
 *
 * Order of operations:
 *  1. simplify the raw string
 *  2. consult the explicit alias table
 *  3. extract a trailing "(XX)" state/country tag or "- XX" / " XX" state code
 *  4. consult the alias table again with the stripped base
 *
 * `stateHint` (from a dedicated state column, when the dataset has one) wins
 * over a state parsed from the name only when the name had none.
 */
export function parseTeamName(raw: string, stateHint?: string): ParsedTeamName {
  const s = simplify(raw);
  const hint = stateHint && STATE_CODES.has(stateHint.toUpperCase()) ? stateHint.toUpperCase() : undefined;

  const alias = TEAM_ALIASES[s];
  if (alias) return { base: alias.base, state: alias.state ?? hint };

  let base = s;
  let state = hint;

  const paren = TRAILING_PAREN.exec(s);
  if (paren) {
    const inner = paren[2].toUpperCase();
    if (STATE_CODES.has(inner)) {
      state = state ?? inner;
      base = paren[1].trim();
    }
    // non-state parentheticals (country tags like URU/PAR) stay in the base
  } else {
    const dashed = TRAILING_STATE.exec(s);
    const spaced = dashed ?? TRAILING_STATE_SPACE.exec(s);
    if (spaced && STATE_CODES.has(spaced[2].toUpperCase())) {
      state = state ?? spaced[2].toUpperCase();
      base = spaced[1].trim();
    }
  }

  const alias2 = TEAM_ALIASES[base] ?? TEAM_ALIASES[`${base}#${state ?? ''}`];
  if (alias2) return { base: alias2.base, state: alias2.state ?? state };

  return { base, state };
}

// ---------------------------------------------------------------------------
// Dates
// ---------------------------------------------------------------------------

const ISO_DATETIME = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/;
const BR_DATE = /^(\d{1,2})\/(\d{1,2})\/(\d{4})/;

export interface ParsedDate {
  /** ISO date "yyyy-mm-dd". */
  date: string;
  /** "HH:MM" when present in the source. */
  time?: string;
}

/**
 * Parse the three date formats used across the datasets:
 *   - "2023-09-24"               (ISO)
 *   - "2012-05-19 18:30:00"      (ISO datetime)
 *   - "29/03/2003"               (Brazilian DD/MM/YYYY)
 * Returns undefined for unparseable values ("NA", "", "-").
 */
export function parseDate(raw: string | undefined | null): ParsedDate | undefined {
  if (!raw) return undefined;
  const s = raw.trim();
  if (!s || s === 'NA' || s === '-') return undefined;

  const iso = ISO_DATETIME.exec(s);
  if (iso) {
    const [, y, m, d, hh, mm] = iso;
    return {
      date: `${y}-${m}-${d}`,
      time: hh !== undefined ? `${hh}:${mm ?? '00'}` : undefined,
    };
  }
  const br = BR_DATE.exec(s);
  if (br) {
    const [, d, m, y] = br;
    return { date: `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}` };
  }
  return undefined;
}

// ---------------------------------------------------------------------------
// Competitions
// ---------------------------------------------------------------------------

/** Aliases mapping user phrasing to canonical competition names. */
const COMPETITION_ALIASES: Record<string, string> = {
  'brasileirao serie a': 'Brasileirão Série A',
  'brasileirao': 'Brasileirão Série A',
  'brasileirao a': 'Brasileirão Série A',
  'serie a': 'Brasileirão Série A',
  'seria a': 'Brasileirão Série A',
  'campeonato brasileiro': 'Brasileirão Série A',
  'campeonato brasileiro serie a': 'Brasileirão Série A',
  'brazilian serie a': 'Brasileirão Série A',
  'brazilian championship': 'Brasileirão Série A',
  'brasileirao serie b': 'Brasileirão Série B',
  'serie b': 'Brasileirão Série B',
  'brasileirao serie c': 'Brasileirão Série C',
  'serie c': 'Brasileirão Série C',
  'copa do brasil': 'Copa do Brasil',
  'brazilian cup': 'Copa do Brasil',
  'copa libertadores': 'Copa Libertadores',
  'libertadores': 'Copa Libertadores',
  'copa libertadores da america': 'Copa Libertadores',
  'copa conmebol libertadores': 'Copa Libertadores',
};

/** Resolve a free-text competition name to the canonical one, or undefined. */
export function normalizeCompetition(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  const s = simplify(raw);
  return COMPETITION_ALIASES[s] ?? undefined;
}
