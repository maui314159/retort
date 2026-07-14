/**
 * Normalizes a team name for consistent matching across datasets.
 * Removes state suffixes, parentheticals, and common club designations.
 */
export function normalizeTeamName(name: string): string {
  if (!name) return "";
  return name
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // Remove accents
    .replace(/\s*[-–]\s*[a-z]{2}\s*$/i, "") // Remove state suffix like " - SP" or "-RJ"
    .replace(/\(.*?\)/g, "") // Remove parentheticals
    .replace(/sport club|futebol clube|esporte clube|associação atlética|clube de regatas/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Safely parses a value into a number, returning null if invalid.
 */
export function parseNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const num = typeof value === "string" ? parseFloat(value) : value;
  return Number.isNaN(num) ? null : num;
}

/**
 * Parses various date string formats into a Date object.
 * Supports ISO formats and DD/MM/YYYY.
 */
export function parseDate(dateStr: string): Date | null {
  if (!dateStr) return null;
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateStr)) {
    const [day, month, year] = dateStr.split("/");
    const parsed = new Date(`${year}-${month}-${day}`);
    if (!Number.isNaN(parsed.getTime())) return parsed;
  }
  const parsed = new Date(dateStr);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
