/**
 * Text normalization utilities: handle Brazilian Portuguese accents,
 * cedillas, casing and whitespace so names match across datasets
 * (e.g. "São Paulo", "Sao Paulo-SP", "SÃO PAULO" all compare equal).
 */

/** Lowercase, strip diacritics (ã, é, ç, ...), collapse whitespace. */
export function normalizeText(input: string): string {
  return input
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[.,''`"]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Split a raw team name into base name and state/region suffix.
 * Handles "Palmeiras-SP", "América - MG", "Barcelona-EQU", "Nacional (URU)".
 */
export function splitTeamSuffix(raw: string): { base: string; uf: string | null } {
  let s = raw.trim();
  // Parenthesised region, e.g. "Nacional (URU)".
  const paren = s.match(/^(.*)\(([A-Z]{2,3})\)\s*$/);
  if (paren) return { base: paren[1].trim(), uf: paren[2] };
  // Dashed suffix, e.g. "Palmeiras-SP", "Ceará - CE", "Barcelona-EQU".
  const dash = s.match(/^(.*?)\s*-\s*([A-Z]{2,3})\s*$/);
  if (dash && dash[1].trim().length > 0) {
    return { base: dash[1].trim(), uf: dash[2] };
  }
  return { base: s, uf: null };
}
