/**
 * Brazilian Soccer MCP Server - Team Name Normalizer
 *
 * Handles team name variations across datasets:
 * - With state suffix: "Palmeiras-SP", "Flamengo-RJ"
 * - Without suffix: "Palmeiras", "Flamengo"
 * - Full names: "Sport Club Corinthians Paulista"
 * - Accented names: "São Paulo", "Grêmio", "Avaí"
 * - Cedilla: "Fortaleza Esporte Clube"
 */

const TEAM_NAME_MAP: Map<string, string> = new Map();

// Initialize known Brazilian team name mappings
const BRAZILIAN_CLUBS: Record<string, string[]> = {
  "Flamengo": ["Flamengo", "Flamengo-RJ", "Clube de Regatas do Flamengo"],
  "Fluminense": ["Fluminense", "Fluminense-RJ", "Fluminense Football Club"],
  "Vasco": ["Vasco", "Vasco da Gama", "Vasco da Gama-RJ", "Club de Regatas Vasco da Gama"],
  "Botafogo": ["Botafogo", "Botafogo-RJ", "Botafogo RJ", "Botafogo de Futebol e Regatas"],
  "Palmeiras": ["Palmeiras", "Palmeiras-SP", "Sociedade Esportiva Palmeiras"],
  "Corinthians": ["Corinthians", "Corinthians-SP", "Sport Club Corinthians Paulista"],
  "São Paulo": ["São Paulo", "Sao Paulo", "São Paulo-SP", "Sao Paulo-SP",
    "São Paulo FC", "São Paulo Futebol Clube"],
  "Santos": ["Santos", "Santos-SP", "Santos FC", "Santos Futebol Clube"],
  "Grêmio": ["Grêmio", "Gremio", "Grêmio-RS", "Gremio-RS", "Grêmio Foot-Ball Porto Alegrense",
    "Grêmio - RS"],
  "Internacional": ["Internacional", "Internacional-RS", "Sport Club Internacional"],
  "Atlético-MG": ["Atlético-MG", "Atletico-MG", "Atlético Mineiro", "Atletico Mineiro",
    "Atlético - MG", "Atletico - MG", "Clube Atlético Mineiro"],
  "Cruzeiro": ["Cruzeiro", "Cruzeiro-MG", "Cruzeiro - MG", "Cruzeiro Esporte Clube"],
  "Athletico-PR": ["Athletico-PR", "Athletico Paranaense", "Atlético Paranaense", "Atlético-PR",
    "Atlético - PR", "Atletico Paranaense", "Atletico-PR", "Athletico Paranaense"],
  "Coritiba": ["Coritiba", "Coritiba-PR", "Coritiba - PR", "Coritiba Foot Ball Club"],
  "Bahia": ["Bahia", "Bahia-BA", "Bahia - BA", "EC Bahia", "Esporte Clube Bahia"],
  "Vitória": ["Vitória", "Vitoria", "Vitória-BA", "Vitória - BA", "Vitória EC",
    "Vitoria EC", "Esporte Clube Vitória"],
  "Ceará": ["Ceará", "Ceara", "Ceará - CE"],
  "Fortaleza": ["Fortaleza", "Fortaleza FC", "Fortaleza - CE",
    "Fortaleza Esporte Clube"],
  "Sport": ["Sport", "Sport-PE", "Sport Recife", "Sport-PE", "Sport Club do Recife"],
  "Náutico": ["Náutico", "Nautico", "Náutico-PE", "Nautico Capibaribe",
    "Clube Náutico Capibaribe"],
  "Goiás": ["Goiás", "Goias", "Goiás - GO", "Goiás Esporte Clube"],
  "Atlético-GO": ["Atlético-GO", "Atletico-GO", "Atlético - GO", "Atletico Goianiense",
    "Atlético Goianiense"],
  "Ponte Preta": ["Ponte Preta", "Ponte Preta-SP", "Associação Atlética Ponte Preta"],
  "Guarani": ["Guarani", "Guarani-SP", "Guarani SP", "Guarani Futebol Clube"],
  "Portuguesa": ["Portuguesa", "Portuguesa-SP", "Portuguesa RJ",
    "Associação Portuguesa de Desportos"],
  "Figueirense": ["Figueirense", "Figueirense-SC", "Figueirense - SC",
    "Figueirense Futebol Clube"],
  "Paraná": ["Paraná", "Parana", "Paraná - PR", "Paraná Clube"],
  "Juventude": ["Juventude", "Juventude-RS", "EC Juventude", "Esporte Clube Juventude"],
  "Criciúma": ["Criciúma", "Criciuma", "Criciuma - SC", "Criciúma Esporte Clube"],
  "Avaí": ["Avaí", "Avai", "Avaí - SC", "Avaí Futebol Clube"],
  "Joinville": ["Joinville", "Joinville - SC", "Joinville Esporte Clube"],
  "Chapecoense": ["Chapecoense", "Chapecoense - SC", "Associação Chapecoense de Futebol"],
  "Bragantino": ["Bragantino", "Bragantino - SP", "RB Bragantino",
    "Red Bull Bragantino", "Clube Atlético Bragantino"],
  "América-MG": ["América-MG", "America MG", "América - MG", "América Mineiro",
    "América Futebol Clube"],
  "São Caetano": ["São Caetano", "Sao Caetano", "Associação Desportiva São Caetano"],
  "Paysandu": ["Paysandu", "Paysandu - PA", "Paysandu Sport Club"],
  "Santa Cruz": ["Santa Cruz", "Santa Cruz FC", "Santa Cruz - PE",
    "Santa Cruz Futebol Clube"],
  "Cuiabá": ["Cuiabá", "Cuiaba", "Cuiabá - MT", "Cuiabá Esporte Clube"],
};

// Build reverse lookup map
for (const [canonical, variants] of Object.entries(BRAZILIAN_CLUBS)) {
  for (const variant of variants) {
    TEAM_NAME_MAP.set(normalizeKey(variant), canonical);
  }
}

function normalizeKey(name: string): string {
  return name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // strip accents
    .replace(/[^a-z0-9]/g, "") // remove non-alphanumeric
    .trim();
}

/**
 * Normalize a team name to its canonical form.
 * Returns the canonical name if known, otherwise returns the cleaned input.
 */
export function normalizeTeam(name: string): string {
  if (!name) return "";
  const key = normalizeKey(name);
  return TEAM_NAME_MAP.get(key) || name.trim();
}

/**
 * Check if a team name (possibly with variations) matches a search query.
 * Both are normalized before comparison.
 */
export function teamMatches(teamName: string, query: string): boolean {
  const normalizedTeam = normalizeKey(normalizeTeam(teamName));
  const normalizedQuery = normalizeKey(query);
  return normalizedTeam.includes(normalizedQuery) || normalizedQuery.includes(normalizedTeam);
}

/**
 * Get the canonical name for display.
 */
export function getCanonicalName(name: string): string {
  return normalizeTeam(name);
}

/**
 * Get all known team names.
 */
export function getAllTeamNames(): string[] {
  return Array.from(new Set(TEAM_NAME_MAP.values())).sort();
}