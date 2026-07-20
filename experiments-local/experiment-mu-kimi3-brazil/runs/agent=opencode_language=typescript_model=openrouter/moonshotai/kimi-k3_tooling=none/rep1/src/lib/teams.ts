/**
 * Canonical team registry.
 *
 * Datasets name the same club in many ways: "Palmeiras-SP" / "Palmeiras" /
 * "Palmeiras - SP", "Vasco-RJ" / "Vasco da Gama - RJ" / "Vasco Da Gama RJ",
 * "Atletico-PR" / "Athletico-PR" / "Athletico Paranaense". The registry
 * canonicalizes every raw spelling to a single Team node via three mapping
 * layers (full raw name, suffix-less base, base+UF pair) and resolves
 * free-text user queries back to that node, handling accents, state
 * suffixes, full official names and FIFA-dataset club spellings.
 */
import { Team } from "./types.js";
import { normalizeText, splitTeamSuffix } from "./text.js";

interface Canonical {
  base: string;
  uf: string | null;
}

/**
 * Layer 1 — full normalized raw spellings mapped to a canonical base+UF.
 * Covers BR-Football's "Botafogo RJ" style (no dash, so suffix splitting
 * fails) and bare names whose base is shared by several clubs ("Santos"
 * could be Santos-SP or Santos-AP; in these datasets it is always the
 * famous Santos FC).
 */
const CANONICAL_FULL: Record<string, Canonical> = {
  // BR-Football "Name UF" style (no dash).
  "vasco da gama rj": { base: "vasco", uf: "RJ" },
  "botafogo rj": { base: "botafogo", uf: "RJ" },
  "botafogo pb": { base: "botafogo", uf: "PB" },
  "botafogo sp": { base: "botafogo", uf: "SP" },
  "atletico mg": { base: "atletico", uf: "MG" },
  "america mg": { base: "america", uf: "MG" },
  "gremio rs": { base: "gremio", uf: "RS" },
  "internacional rs": { base: "internacional", uf: "RS" },
  "coritiba pr": { base: "coritiba", uf: "PR" },
  "cuiaba mt": { base: "cuiaba", uf: "MT" },
  "santos ap": { base: "santos", uf: "AP" },
  "fluminense rj": { base: "fluminense", uf: "RJ" },
  "fluminense pi": { base: "fluminense", uf: "PI" },
  "nautico rr": { base: "nautico", uf: "RR" },
  "guarani sp": { base: "guarani", uf: "SP" },
  "juventude ma": { base: "juventude", uf: "MA" },
  "bragantino pa": { base: "bragantino", uf: "PA" },
  "tombense mg": { base: "tombense", uf: "MG" },
  "remo pa": { base: "remo", uf: "PA" },
  "operario pr": { base: "operario", uf: "PR" },
  "operario ms": { base: "operario", uf: "MS" },
  "operario fc ms": { base: "operario", uf: "MS" },
  "operario mt": { base: "operario", uf: "MT" },
  "vitoria es": { base: "vitoria", uf: "ES" },
  "vitoria f. c. - es": { base: "vitoria", uf: "ES" },
  "america rn": { base: "america", uf: "RN" },
  "americano rj": { base: "americano", uf: "RJ" },
  "macae esporte rj": { base: "macae", uf: "RJ" },
  "macae esporte fc": { base: "macae", uf: "RJ" },
  "santa cruz rs": { base: "santa cruz", uf: "RS" },
  "santa cruz rn": { base: "santa cruz", uf: "RN" },
  // Bare names whose base is ambiguous across clubs (always the big club).
  santos: { base: "santos", uf: "SP" },
  flamengo: { base: "flamengo", uf: "RJ" },
  botafogo: { base: "botafogo", uf: "RJ" },
  guarani: { base: "guarani", uf: "SP" },
  vitoria: { base: "vitoria", uf: "BA" },
  juventude: { base: "juventude", uf: "RS" },
  bragantino: { base: "bragantino", uf: "SP" },
  nautico: { base: "nautico", uf: "PE" },
  america: { base: "america", uf: "MG" },
  internacional: { base: "internacional", uf: "RS" },
  fluminense: { base: "fluminense", uf: "RJ" },
  vasco: { base: "vasco", uf: "RJ" },
  athletico: { base: "athletico", uf: "PR" },
  // Long/odd cup spellings.
  "iv de julho - pi": { base: "4 de julho", uf: "PI" },
  "4 de julho ec": { base: "4 de julho", uf: "PI" },
};

/**
 * Layer 2 — normalized base (after suffix splitting) mapped to a canonical
 * base (+ default UF). Applied when the raw UF is absent or matches.
 */
const CANONICAL_BASE: Record<string, Canonical> = {
  "vasco da gama": { base: "vasco", uf: "RJ" },
  "athletico paranaense": { base: "athletico", uf: "PR" },
  "atletico paranaense": { base: "athletico", uf: "PR" },
  "atletico mineiro": { base: "atletico", uf: "MG" },
  "atletico goianiense": { base: "atletico", uf: "GO" },
  "america mineiro": { base: "america", uf: "MG" },
  "america de natal": { base: "america", uf: "RN" },
  "america fc natal": { base: "america", uf: "RN" },
  "sport recife": { base: "sport", uf: "PE" },
  "nautico capibaribe": { base: "nautico", uf: "PE" },
  "guarani de juazeiro": { base: "guarani", uf: "CE" },
  "gremio novorizontino": { base: "novorizontino", uf: "SP" },
  "red bull bragantino": { base: "bragantino", uf: "SP" },
  "desportiva ferroviaria": { base: "desportiva", uf: "ES" },
  "esportivo bento goncalves": { base: "esportivo", uf: "RS" },
  "flamengo do piaui": { base: "flamengo", uf: "PI" },
  "atletico alagoinhas": { base: "atletico", uf: "BA" },
  "atletico acreano": { base: "atletico", uf: "AC" },
  "boavista sport club (antigo esporte clube barreira)": { base: "boavista", uf: "RJ" },
  "operario ferroviario esporte c": { base: "operario", uf: "PR" },
  "clube do remo": { base: "remo", uf: "PA" },
  "portuguesa desportos": { base: "portuguesa", uf: "SP" },
  "ec vitoria": { base: "vitoria", uf: "BA" },
  "vitoria ec": { base: "vitoria", uf: "BA" },
  "ec juventude": { base: "juventude", uf: "RS" },
  "ec bahia": { base: "bahia", uf: "BA" },
  "ec internacional sc": { base: "internacional", uf: "SC" },
  "ca parana": { base: "parana", uf: "PR" },
  "fc atletico cearense": { base: "atletico cearense", uf: "CE" },
  "fortaleza ec": { base: "fortaleza", uf: "CE" },
  "fortaleza fc": { base: "fortaleza", uf: "CE" },
  "santa cruz fc": { base: "santa cruz", uf: "PE" },
  "arapongas esporte clube": { base: "arapongas", uf: "PR" },
  "atletico cearense": { base: "atletico cearense", uf: "CE" },
};

/** Layer 3 — base+UF pairs needing a different canonical base. */
const CANONICAL_BASE_UF: Record<string, string> = {
  // Atlético Paranaense officially changed spelling to "Athletico" in 2019;
  // datasets straddle both spellings.
  "atletico|PR": "athletico",
};

/** Known wrong state codes in the source files (mapped to the correct UF). */
const UF_CORRECTIONS: Record<string, string> = {
  // novo_campeonato_brasileiro.csv records every Bahia match with UF "BH"
  // (Belo Horizonte is a city, not a state) instead of "BA".
  BH: "BA",
};

/** Preferred display names for canonical keys (fallback: first-seen spelling). */
const CANONICAL_DISPLAY: Record<string, string> = {
  "athletico-pr": "Athletico Paranaense",
  "atletico-mg": "Atlético Mineiro",
  "atletico-go": "Atlético Goianiense",
  "america-mg": "América Mineiro",
  "america-rn": "América de Natal",
  "vasco-rj": "Vasco da Gama",
  "sport-pe": "Sport Recife",
  "bahia-ba": "Bahia",
  "fortaleza-ce": "Fortaleza",
  "vitoria-ba": "Vitória",
  "gremio-rs": "Grêmio",
  "sao paulo-sp": "São Paulo",
  "internacional-rs": "Internacional",
  "flamengo-rj": "Flamengo",
  "fluminense-rj": "Fluminense",
  "palmeiras-sp": "Palmeiras",
  "corinthians-sp": "Corinthians",
  "santos-sp": "Santos",
  "cruzeiro-mg": "Cruzeiro",
  "botafogo-rj": "Botafogo",
  "ceara-ce": "Ceará",
  "goias-go": "Goiás",
  "coritiba-pr": "Coritiba",
  "chapecoense-sc": "Chapecoense",
  "figueirense-sc": "Figueirense",
  "avai-sc": "Avaí",
  "ponte preta-sp": "Ponte Preta",
  "nautico-pe": "Náutico",
  "guarani-sp": "Guarani",
  "cuiaba-mt": "Cuiabá",
  "juventude-rs": "Juventude",
  "bragantino-sp": "Red Bull Bragantino",
  "parana-pr": "Paraná",
  "criciuma-sc": "Criciúma",
  "remo-pa": "Remo",
  "paysandu-pa": "Paysandu",
  "4 de julho-pi": "4 de Julho",
};

/**
 * Hand-maintained aliases for free-text queries (common names, full
 * official names and FIFA-dataset club spellings).
 */
const KNOWN_ALIASES: Record<string, Canonical> = {
  "clube atletico mineiro": { base: "atletico", uf: "MG" },
  galo: { base: "atletico", uf: "MG" },
  "athletico paranaense": { base: "athletico", uf: "PR" },
  "atletico paranaense": { base: "athletico", uf: "PR" },
  "atletico goianiense": { base: "atletico", uf: "GO" },
  "america mineiro": { base: "america", uf: "MG" },
  "america fc": { base: "america", uf: "MG" },
  "america fc (minas gerais)": { base: "america", uf: "MG" },
  "america de natal": { base: "america", uf: "RN" },
  "sport club corinthians paulista": { base: "corinthians", uf: "SP" },
  "sao paulo fc": { base: "sao paulo", uf: "SP" },
  "sociedade esportiva palmeiras": { base: "palmeiras", uf: "SP" },
  "se palmeiras": { base: "palmeiras", uf: "SP" },
  "santos fc": { base: "santos", uf: "SP" },
  "sport club do recife": { base: "sport", uf: "PE" },
  "sport recife": { base: "sport", uf: "PE" },
  "clube de regatas vasco da gama": { base: "vasco", uf: "RJ" },
  "vasco da gama": { base: "vasco", uf: "RJ" },
  "clube de regatas do flamengo": { base: "flamengo", uf: "RJ" },
  "fluminense fc": { base: "fluminense", uf: "RJ" },
  "fluminense football club": { base: "fluminense", uf: "RJ" },
  "botafogo de futebol e regatas": { base: "botafogo", uf: "RJ" },
  "gremio foot-ball porto alegrense": { base: "gremio", uf: "RS" },
  "sport club internacional": { base: "internacional", uf: "RS" },
  "ceara sporting club": { base: "ceara", uf: "CE" },
  "ceara sc": { base: "ceara", uf: "CE" },
  "associacao chapecoense de futebol": { base: "chapecoense", uf: "SC" },
  "esporte clube vitoria": { base: "vitoria", uf: "BA" },
  "esporte clube bahia": { base: "bahia", uf: "BA" },
  "coritiba foot ball club": { base: "coritiba", uf: "PR" },
  "goias esporte clube": { base: "goias", uf: "GO" },
  "figueirense fc": { base: "figueirense", uf: "SC" },
  "associacao atletica ponte preta": { base: "ponte preta", uf: "SP" },
  "avai fc": { base: "avai", uf: "SC" },
  "clube nautico capibaribe": { base: "nautico", uf: "PE" },
  "parana clube": { base: "parana", uf: "PR" },
  "guarani fc": { base: "guarani", uf: "SP" },
  "esporte clube juventude": { base: "juventude", uf: "RS" },
  "cuiaba esporte clube": { base: "cuiaba", uf: "MT" },
  "fortaleza esporte clube": { base: "fortaleza", uf: "CE" },
  "red bull bragantino": { base: "bragantino", uf: "SP" },
  "rb bragantino": { base: "bragantino", uf: "SP" },
  "atletico mg": { base: "atletico", uf: "MG" },
  "athletico pr": { base: "athletico", uf: "PR" },
  "atletico go": { base: "atletico", uf: "GO" },
  "america mg": { base: "america", uf: "MG" },
};

export interface TeamResolution {
  team: Team | null;
  /** Candidate teams when the query is ambiguous. */
  ambiguous: Team[];
}

export class TeamRegistry {
  private teams = new Map<string, Team>();
  /** Normalized base name -> canonical keys with that base. */
  private baseIndex = new Map<string, Set<string>>();
  /** Normalized alias -> canonical key. */
  private aliasIndex = new Map<string, string>();

  private makeKey(base: string, uf: string | null): string {
    return uf ? `${base}-${uf.toLowerCase()}` : base;
  }

  /** Map a raw spelling to its canonical (base, uf) via the three layers. */
  private canonicalize(rawName: string, uf?: string | null): Canonical {
    const full = CANONICAL_FULL[normalizeText(rawName)];
    if (full) return full;

    const split = splitTeamSuffix(rawName);
    let base = normalizeText(split.base);
    let region = (uf ?? split.uf)?.toUpperCase() ?? null;
    if (region && UF_CORRECTIONS[region]) region = UF_CORRECTIONS[region];

    if (region) {
      const remapped = CANONICAL_BASE_UF[`${base}|${region}`];
      if (remapped) base = remapped;
    }
    const baseAlias = CANONICAL_BASE[base];
    if (baseAlias && (region === null || baseAlias.uf === null || baseAlias.uf === region)) {
      base = baseAlias.base;
      region ??= baseAlias.uf;
    }
    return { base, uf: region };
  }

  /**
   * Register a raw team spelling and return its canonical Team.
   * Merges with an existing team when the canonical base (+UF) matches.
   */
  register(rawName: string, uf?: string | null): Team {
    const { base, uf: region } = this.canonicalize(rawName, uf);

    const exactKey = this.makeKey(base, region);
    const exact = this.teams.get(exactKey);
    if (exact) {
      exact.aliases.add(normalizeText(rawName));
      return exact;
    }

    // Same base already registered: reuse when compatible.
    const withBase = this.baseIndex.get(base);
    if (withBase) {
      for (const key of withBase) {
        const t = this.teams.get(key)!;
        // Same UF, or one side lacks a UF and the base is unambiguous.
        if (t.uf === region || t.uf === null || region === null) {
          if (t.uf === region || withBase.size === 1) {
            t.aliases.add(normalizeText(rawName));
            if (t.uf === null && region !== null) {
              t.uf = region;
              // Re-key under base-uf now that the UF is known.
              this.rekey(t, this.makeKey(base, region));
              return this.teams.get(t.key)!;
            }
            return t;
          }
        }
      }
    }

    const team: Team = {
      key: exactKey,
      name: CANONICAL_DISPLAY[exactKey] ?? splitTeamSuffix(rawName).base,
      uf: region,
      aliases: new Set([normalizeText(rawName), base]),
    };
    this.teams.set(team.key, team);
    if (!this.baseIndex.has(base)) this.baseIndex.set(base, new Set());
    this.baseIndex.get(base)!.add(team.key);
    return team;
  }

  /** Move a team to a new canonical key, keeping indexes consistent. */
  private rekey(team: Team, newKey: string): void {
    if (this.teams.has(newKey) || team.key === newKey) return;
    this.teams.delete(team.key);
    const base = team.key.split("-")[0];
    for (const [, set] of this.baseIndex) {
      if (set.delete(team.key)) set.add(newKey);
    }
    team.key = newKey;
    if (CANONICAL_DISPLAY[newKey]) team.name = CANONICAL_DISPLAY[newKey];
    this.teams.set(newKey, team);
    void base;
  }

  /** Register an explicit alias for an already-registered team. */
  addAlias(team: Team, alias: string): void {
    const n = normalizeText(alias);
    team.aliases.add(n);
    this.aliasIndex.set(n, team.key);
  }

  /** Resolve a free-text team query to a canonical team. */
  resolve(query: string): TeamResolution {
    const n = normalizeText(query);
    if (n.length === 0) return { team: null, ambiguous: [] };

    // 1. Hand-maintained alias table.
    const known = KNOWN_ALIASES[n];
    if (known) {
      const key = this.findKeyFor(known.base, known.uf);
      if (key) return { team: this.teams.get(key)!, ambiguous: [] };
    }

    // 2. Canonicalize the query like a registration (covers "Vasco Da Gama RJ",
    //    "Botafogo RJ", suffix forms, etc.).
    const { base, uf } = this.canonicalize(query, null);
    const canonicalKey = this.findKeyFor(base, uf);
    if (canonicalKey) return { team: this.teams.get(canonicalKey)!, ambiguous: [] };

    // 3. Registered alias (all raw spellings ever seen).
    const aliasKey = this.aliasIndex.get(n);
    if (aliasKey) return { team: this.teams.get(aliasKey)!, ambiguous: [] };

    // 4. Unique team with this base name.
    const withBase = this.baseIndex.get(base);
    if (withBase) {
      if (withBase.size === 1) {
        return { team: this.teams.get([...withBase][0])!, ambiguous: [] };
      }
      return {
        team: null,
        ambiguous: [...withBase].map((k) => this.teams.get(k)!),
      };
    }

    // 5. Unique word-boundary prefix match over keys and aliases.
    const candidates = new Set<string>();
    for (const [key, team] of this.teams) {
      const names = [key, ...team.aliases];
      if (
        names.some(
          (name) =>
            name === n ||
            (name.startsWith(n) && (name.length === n.length || name[n.length] === " ")) ||
            (n.startsWith(name) && (n.length === name.length || n[name.length] === " ")),
        )
      ) {
        candidates.add(key);
      }
    }
    if (candidates.size === 1) {
      return { team: this.teams.get([...candidates][0])!, ambiguous: [] };
    }
    if (candidates.size > 1 && candidates.size <= 8) {
      return { team: null, ambiguous: [...candidates].map((k) => this.teams.get(k)!) };
    }

    return { team: null, ambiguous: [] };
  }

  private findKeyFor(base: string, uf: string | null): string | null {
    const withBase = this.baseIndex.get(base);
    if (!withBase) return null;
    if (uf) {
      const keyed = this.makeKey(base, uf);
      if (withBase.has(keyed)) return keyed;
    }
    if (withBase.size === 1) return [...withBase][0];
    return null;
  }

  get(key: string): Team | undefined {
    return this.teams.get(key);
  }

  all(): Team[] {
    return [...this.teams.values()];
  }

  get size(): number {
    return this.teams.size;
  }
}
