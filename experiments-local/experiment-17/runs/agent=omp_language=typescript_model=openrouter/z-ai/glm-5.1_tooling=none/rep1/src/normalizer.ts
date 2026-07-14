/**
 * Brazilian Soccer MCP Server - Team Name Normalizer
 *
 * Handles the multiple naming conventions across datasets:
 *   - "Palmeiras-SP" (Brasileirão with state suffix)
 *   - "Palmeiras - SP" (Copa do Brasil with spaced suffix)
 *   - "Palmeiras" (Libertadores, historical, FIFA)
 *   - "SE Palmeiras" (full name variants)
 *
 * All names are normalized to a canonical form (e.g., "Palmeiras")
 * for consistent cross-dataset matching.
 */

/** Map from known variant → canonical name */
const ALIAS_MAP: Map<string, string> = new Map([
  // State-suffixed names from Brasileirão
  ["Atletico-MG", "Atlético Mineiro"],
  ["Atletico-GO", "Atlético Goianiense"],
  ["Athletico-PR", "Athletico Paranaense"],
  ["Bahia-BA", "Bahia"],
  ["Botafogo-RJ", "Botafogo"],
  ["Corinthians-SP", "Corinthians"],
  ["Coritiba-PR", "Coritiba"],
  ["Cruzeiro-MG", "Cruzeiro"],
  ["Flamengo-RJ", "Flamengo"],
  ["Fluminense-RJ", "Fluminense"],
  ["Gremio-RS", "Grêmio"],
  ["Internacional-RS", "Internacional"],
  ["Palmeiras-SP", "Palmeiras"],
  ["Ponte Preta-SP", "Ponte Preta"],
  ["Santos-SP", "Santos"],
  ["Sao Paulo-SP", "São Paulo"],
  ["Sport-PE", "Sport"],
  ["Vasco da Gama-RJ", "Vasco da Gama"],
  ["Nautico-PE", "Náut