export const normalizeTeamName = (raw: string | null | undefined): string => {
  if (raw == null) return "";
  let s = String(raw).trim();
  if (!s) return "";
  s = s.normalize("NFC");
  s = s.replace(/\s*\((antigo[^)]*)\)\s*/gi, " ");
  const lower = s.toLowerCase();
  const canonicalMap: Record<string, string> = {
    "sport club corinthians paulista": "Corinthians",
    "corinthians": "Corinthians",
    "sc corinthians paulista": "Corinthians",
    "sao paulo fc": "Sao Paulo",
    "sao paulo": "Sao Paulo",
    "são paulo": "Sao Paulo",
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "palmeiras": "Palmeiras",
    "santos fc": "Santos",
    "santos": "Santos",
    "cruzeiro": "Cruzeiro",
    "atletico-mg": "Atletico-MG",
    "atletico mineiro": "Atletico-MG",
    "atlético-mg": "Atletico-MG",
    "athletico-pr": "Athletico-PR",
    "atletico-pr": "Athletico-PR",
    "club de regatas vasco da gama": "Vasco",
    "vasco da gama": "Vasco",
    "vasco": "Vasco",
    "gremio": "Gremio",
    "grêmio": "Gremio",
    "internacional": "Internacional",
    "botafogo": "Botafogo",
    "fortaleza": "Fortaleza",
    "ceara": "Ceara",
    "bahia": "Bahia",
    "vitoria": "Vitoria",
    "vitória": "Vitoria",
    "goias": "Goias",
    "goiás": "Goias",
    "atletico-go": "Atletico-GO",
    "atletico goianiense": "Atletico-GO",
    "avai": "Avai",
    "avaí": "Avai",
    "chapecoense": "Chapecoense",
    "coritiba": "Coritiba",
    "parana": "Parana",
    "paraná": "Parana",
    "américa-mg": "America-MG",
    "america-mg": "America-MG",
    "américa-rn": "America-RN",
    "america-rn": "America-RN",
    "sport recife": "Sport",
    "sport": "Sport",
    "cuiaba": "Cuiaba",
    "cuiabá": "Cuiaba",
    "juventude": "Juventude",
    "bragantino": "Bragantino",
    "red bull bragantino": "Bragantino",
  };
  if (canonicalMap[lower]) return canonicalMap[lower];
  s = s.replace(/\s*-\s*([A-Z]{2})\s*$/i, "");
  s = s.replace(/\s+-\s+([A-Z]{2})$/i, "");
  s = s.replace(/\s+/g, " ").trim();
  return s;
};

export const normalizeForMatch = (raw: string | null | undefined): string => {
  return normalizeTeamName(raw)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
};

export const teamMatches = (
  candidate: string,
  target: string
): boolean => {
  const a = normalizeForMatch(candidate);
  const b = normalizeForMatch(target);
  if (!a || !b) return false;
  if (a === b) return true;
  if (a.includes(b) || b.includes(a)) return true;
  const stripParen = (x: string) => x.replace(/\s*\(.*?\)\s*/g, " ").trim();
  const a2 = stripParen(a);
  const b2 = stripParen(b);
  if (a2 === b2) return true;
  if (a2.length > 3 && b2.length > 3) {
    if (a2.startsWith(b2) || b2.startsWith(a2)) return true;
  }
  return false;
};

export const parseDate = (input: string | null | undefined): Date | null => {
  if (input == null) return null;
  const s = String(input).trim();
  if (!s) return null;
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})([ T]\d{2}:\d{2}(:\d{2})?)?$/);
  if (m) {
    return new Date(`${m[1]}-${m[2]}-${m[3]}T${(m[4] || "00:00:00").replace(" ", "T").replace(/^T/, "")}`);
  }
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) {
    const day = m[1].padStart(2, "0");
    const month = m[2].padStart(2, "0");
    return new Date(`${m[3]}-${month}-${day}T00:00:00`);
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
};

export const toISODate = (input: string | null | undefined): string => {
  const d = parseDate(input);
  if (!d) return input ? String(input).trim() : "";
  return d.toISOString().slice(0, 10);
};

export const toNumber = (v: unknown): number | null => {
  if (v == null || v === "") return null;
  if (typeof v === "number") return isNaN(v) ? null : v;
  const s = String(v).trim().replace(/,/g, ".");
  const n = Number(s);
  return isNaN(n) ? null : n;
};
