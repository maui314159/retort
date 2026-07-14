export function normalizeTeamName(name: string | null | undefined): string {
  if (!name) return "";

  let normalized = name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();

  normalized = normalized.replace(/\s*-\s*[A-Z]{2}$/, "");
  normalized = normalized.replace(/\s*\([^)]*\)/g, "");

  normalized = normalized.replace(/\b(SP|RJ|MG|RS|PR|BA|SC|PE|CE|GO|PA|MT|MS|RN|PB|AL|SE|PI|MA|TO|RO|AC|RR|AP|DF|ES)\b/gi, "");
  normalized = normalized.replace(/\bF\.C\.\b/gi, "").replace(/\bE\.C\.\b/gi, "").replace(/\bS\.C\.\b/gi, "");
  normalized = normalized.replace(/\s+/g, " ").trim();

  const lower = normalized.toLowerCase();
  const aliases: Record<string, string> = {
    "athletico pr": "Athletico Paranaense",
    "athletico-paranaense": "Athletico Paranaense",
    atleticopr: "Athletico Paranaense",
    "atletico mg": "Atletico Mineiro",
    "atletico-mg": "Atletico Mineiro",
    "atletico mineiro": "Atletico Mineiro",
    atleticomg: "Atletico Mineiro",
    "atletico go": "Atletico Goianiense",
    "atletico-go": "Atletico Goianiense",
    atleticogo: "Atletico Goianiense",
    "vasco da gama": "Vasco",
    vascodagama: "Vasco",
    gremio: "Gremio",
    "sao paulo": "Sao Paulo",
    saopaulo: "Sao Paulo",
    "corinthians paulista": "Corinthians",
    "sport club corinthians paulista": "Corinthians",
    palmeiras: "Palmeiras",
    flamengo: "Flamengo",
    fluminense: "Fluminense",
    botafogo: "Botafogo",
    santos: "Santos",
    cruzeiro: "Cruzeiro",
    internacional: "Internacional",
    "coritiba fc": "Coritiba",
    coritiba: "Coritiba",
    "fortaleza esporte clube": "Fortaleza",
    fortaleza: "Fortaleza",
    bahia: "Bahia",
    "atletico paranaense": "Athletico Paranaense",
    "parana clube": "Parana",
    "ponte preta": "Ponte Preta",
    figueirense: "Figueirense",
    "sport recife": "Sport",
    sport: "Sport",
    "america mg": "America Mineiro",
    "america-mg": "America Mineiro",
    americamg: "America Mineiro",
    "america mineiro": "America Mineiro",
    "avai fc": "Avai",
    avai: "Avai",
    "ceara sporting": "Ceara",
    ceara: "Ceara",
    chapecoense: "Chapecoense",
    "santa cruz fc": "Santa Cruz",
    "santa cruz": "Santa Cruz",
    "vitoria es": "Vitoria",
    vitoria: "Vitoria",
    "goias esporte clube": "Goias",
    goias: "Goias",
    nautico: "Nautico",
    "botafogo fr": "Botafogo",
    "botafogo rj": "Botafogo",
    "botafogo sp": "Botafogo SP",
    paysandu: "Paysandu",
    juventude: "Juventude",
    guarani: "Guarani",
    criciuma: "Criciuma",
    londrina: "Londrina",
    remo: "Remo",
    "abc rn": "ABC",
    abc: "ABC",
    bragantino: "Red Bull Bragantino",
    "red bull bragantino": "Red Bull Bragantino",
  };

  if (aliases[lower]) {
    return aliases[lower];
  }

  normalized = normalized
    .split(" ")
    .map((word) => (word.length > 0 ? word[0].toUpperCase() + word.slice(1).toLowerCase() : ""))
    .join(" ");

  return normalized;
}

export function teamMatches(a: string, b: string): boolean {
  const na = normalizeTeamName(a);
  const nb = normalizeTeamName(b);
  if (!na || !nb) return false;
  if (na === nb) return true;
  if (na.includes(nb) || nb.includes(na)) return true;

  const stripArticles = (s: string) => s.replace(/\b(de|do|da|dos|das|e)\b/gi, "").replace(/\s+/g, " ").trim();
  const sa = stripArticles(na).toLowerCase();
  const sb = stripArticles(nb).toLowerCase();
  return sa === sb || sa.includes(sb) || sb.includes(sa);
}

export function canonicalizeTeamName(name: string): string {
  return normalizeTeamName(name);
}
