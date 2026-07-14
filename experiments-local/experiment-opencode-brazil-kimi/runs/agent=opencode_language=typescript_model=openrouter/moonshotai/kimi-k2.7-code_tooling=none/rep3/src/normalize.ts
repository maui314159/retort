/**
 * Normalize a team name by stripping common suffixes, accents, and lowercasing.
 * Supports variations like "Palmeiras-SP", "Palmeiras", "Sport Club Corinthians Paulista".
 */
export function normalizeTeamName(name: string): string {
  if (!name) return "";
  let normalized = name.trim();

  // Remove parenthetical suffixes like (URU), (EQU), (antigo ...)
  normalized = normalized.replace(/\s*\([^)]*\)/g, "").trim();

  // Common full-name mappings (before state suffix stripping)
  const lowerPre = normalized.toLowerCase();
  const fullMappings: Record<string, string> = {
    "sport club corinthians paulista": "Corinthians",
    "sao paulo fc": "Sao Paulo",
    "são paulo fc": "Sao Paulo",
    "sao paulo": "Sao Paulo",
    "são paulo": "Sao Paulo",
    "sociedade esportiva palmeiras": "Palmeiras",
    "palmeiras": "Palmeiras",
    "clube de regatas do flamengo": "Flamengo",
    "flamengo": "Flamengo",
    "fluminense football club": "Fluminense",
    "fluminense": "Fluminense",
    "clube atlético mineiro": "Atletico-MG",
    "atlético mineiro": "Atletico-MG",
    "atletico mineiro": "Atletico-MG",
    "atletico-mg": "Atletico-MG",
    "atlético-mg": "Atletico-MG",
    "grêmio foot-ball portoalegrense": "Gremio",
    "gremio foot-ball portoalegrense": "Gremio",
    "grêmio": "Gremio",
    "gremio": "Gremio",
    "sport club internacional": "Internacional",
    "internacional": "Internacional",
    "sport club do recife": "Sport",
    "sport": "Sport",
    "coritiba foot ball club": "Coritiba",
    "coritiba": "Coritiba",
    "associação chapecoense de futebol": "Chapecoense",
    "chapecoense": "Chapecoense",
    "botafogo de futebol e regatas": "Botafogo",
    "botafogo": "Botafogo",
    "cr vasco da gama": "Vasco",
    "vasco da gama": "Vasco",
    "vasco": "Vasco",
    "cruzeiro esporte clube": "Cruzeiro",
    "cruzeiro": "Cruzeiro",
    "santos fc": "Santos",
    "santos": "Santos",
    "esporte clube bahia": "Bahia",
    "bahia": "Bahia",
    "fortaleza esporte clube": "Fortaleza",
    "fortaleza": "Fortaleza",
    "ceará sporting club": "Ceara",
    "ceará": "Ceara",
    "avaí futebol clube": "Avai",
    "avaí": "Avai",
    "goiás esporte clube": "Goias",
    "goiás": "Goias",
    "atlético goianiense": "Atletico-GO",
    "atletico goianiense": "Atletico-GO",
    "red bull bragantino": "Bragantino",
    "bragantino": "Bragantino",
    "clube athletico paranaense": "Athletico-PR",
    "athletico paranaense": "Athletico-PR",
    "atlético paranaense": "Athletico-PR",
    "atletico paranaense": "Athletico-PR",
    "atletico-pr": "Athletico-PR",
    "athletico-pr": "Athletico-PR",
    "cuiabá esporte clube": "Cuiaba",
    "cuiabá": "Cuiaba",
    "boavista sport club": "Boavista",
    "boavista": "Boavista",
    "américa futebol clube": "America-MG",
    "américa - mg": "America-MG",
    "america - mg": "America-MG",
    "américa-mg": "America-MG",
    "america-mg": "America-MG",
    "centro sportivo alagoano": "CSA",
    "paysandu sport club": "Paysandu",
    "ponte preta": "Ponte Preta",
    "ec bahia": "Bahia",
    "fortaleza fc": "Fortaleza",
    "botafogo rj": "Botafogo",
    "vasco da gama rj": "Vasco",
  };

  if (fullMappings[lowerPre]) {
    return fullMappings[lowerPre];
  }

  // Remove state suffixes like -SP, -RJ, -MG, -PR, -RS, etc.
  // But preserve suffixes that are required to distinguish clubs.
  const stateMatch = normalized.match(/-\s*([A-Z]{2})$/);
  if (stateMatch) {
    const withoutState = normalized.replace(/-\s*[A-Z]{2}$/, "").trim();
    const base = withoutState.toLowerCase();
    const ambiguousBases = new Set([
      "atletico",
      "athletico",
      "america",
      "america-mg",
    ]);
    if (!ambiguousBases.has(base)) {
      normalized = withoutState;
    }
  }

  normalized = normalized.trim();

  // Check short-form mappings again after suffix stripping
  const lowerPost = normalized.toLowerCase();
  if (fullMappings[lowerPost]) {
    return fullMappings[lowerPost];
  }

  return normalized;
}

/**
 * Creates a comparable canonical key for a team name.
 */
export function teamKey(name: string): string {
  return normalizeTeamName(name)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]/g, "");
}

/**
 * Check whether two team names likely refer to the same team.
 */
export function sameTeam(a: string, b: string): boolean {
  return teamKey(a) === teamKey(b);
}

/**
 * Convert known date formats to ISO YYYY-MM-DD.
 */
export function parseDate(value: string): string | undefined {
  if (!value) return undefined;
  const trimmed = value.trim();

  // ISO-ish with optional time: 2012-05-19 18:30:00 or 2023-09-24
  const isoMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`;
  }

  // Brazilian format: 29/03/2003
  const brMatch = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (brMatch) {
    return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
  }

  // US format fallback: 03/29/2003
  const usMatch = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (usMatch) {
    return `${usMatch[3]}-${usMatch[1]}-${usMatch[2]}`;
  }

  const parsed = new Date(trimmed);
  if (!isNaN(parsed.getTime())) {
    return parsed.toISOString().slice(0, 10);
  }

  return undefined;
}

export function parseNumber(value: string | number | undefined): number {
  if (value === undefined || value === null || value === "") return NaN;
  if (typeof value === "number") return value;
  const cleaned = String(value).replace(/,/g, "").trim();
  const num = Number(cleaned);
  return isNaN(num) ? NaN : num;
}

export function parseIntOrNaN(value: string | number | undefined): number {
  const num = parseNumber(value);
  return isNaN(num) ? NaN : Math.floor(num);
}

export function safeString(value: unknown): string {
  if (value === undefined || value === null) return "";
  return String(value).trim();
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
