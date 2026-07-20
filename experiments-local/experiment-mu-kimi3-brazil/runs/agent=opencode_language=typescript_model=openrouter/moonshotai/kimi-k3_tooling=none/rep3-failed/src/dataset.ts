/**
 * CSV loading and in-memory store construction.
 *
 * Loads the six Kaggle datasets, normalizes team identities, deduplicates
 * matches that appear in several overlapping files (keeping the most
 * authoritative source), and builds the indexes used by the query layer.
 */
import { readFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'csv-parse/sync';
import {
  Competition,
  DatasetStore,
  Match,
  Player,
  SourceDataset,
  TeamIdentity,
} from './types.js';
import {
  curatedDisplayName,
  displayNameFor,
  parseDate,
  parseTeamName,
  simplify,
  teamKey,
} from './normalize.js';

/** Source priority for deduplication (lower number wins). */
const SOURCE_PRIORITY: Record<SourceDataset, number> = {
  brasileirao: 1,
  cup: 1,
  libertadores: 1,
  historico: 2,
  brfootball: 3,
};

/** Registry of canonical team identities. */
class TeamRegistry {
  readonly teams = new Map<string, TeamIdentity>();
  /** identity key -> raw variant -> occurrence count */
  private readonly variantCounts = new Map<string, Map<string, number>>();

  resolve(rawName: string, stateHint?: string): TeamIdentity {
    const { base, state } = parseTeamName(rawName, stateHint);
    const key = teamKey(base, state);
    let identity = this.teams.get(key);
    if (!identity) {
      identity = {
        key,
        base,
        state,
        displayName: displayNameFor(base, state),
        variants: new Set(),
        matchCount: 0,
      };
      this.teams.set(key, identity);
    }
    const raw = rawName.trim();
    identity.variants.add(raw);
    let counts = this.variantCounts.get(key);
    if (!counts) {
      counts = new Map();
      this.variantCounts.set(key, counts);
    }
    counts.set(raw, (counts.get(raw) ?? 0) + 1);
    return identity;
  }

  /**
   * Pick a human-readable display name for identities without a curated one:
   * the most frequent raw variant that strips down to the base name (keeps
   * accents/casing, e.g. "CSA", "Grêmio"), else a title-cased base.
   */
  finalizeDisplayNames(): void {
    const stripSuffix = (raw: string): string =>
      raw
        .replace(/\s*\([^)]{2,5}\)\s*$/, '')
        .replace(/\s*[-–]\s*[A-Za-z]{2}\s*$/, '')
        .replace(/\s+[A-Za-z]{2}\s*$/, '')
        .trim();
    for (const t of this.teams.values()) {
      if (curatedDisplayName(t.base, t.state)) continue; // keep curated name
      const counts = this.variantCounts.get(t.key);
      if (!counts) continue;
      const ranked = [...counts.entries()]
        .map(([raw, count]) => ({ raw, stripped: stripSuffix(raw), count }))
        .filter((c) => c.stripped.length > 0 && simplify(c.stripped) === t.base)
        .sort((a, b) => b.count - a.count);
      if (ranked.length > 0) {
        // Prefer accented spellings when counts are close (proper PT-BR names).
        const best = ranked.find((r) => /[^ -~]/.test(r.stripped) && r.count >= ranked[0].count * 0.5) ?? ranked[0];
        t.displayName = t.state ? `${best.stripped} (${t.state})` : best.stripped;
      }
    }
  }

  /**
   * Redirect state-less identities to a same-base identity that has a state
   * (e.g. BR-Football's bare "Sao Paulo" -> sao paulo#SP). Two safe cases:
   *  1. the state-ful identity has at least as many matches (dominance), or
   *  2. there is exactly ONE state-ful candidate and the state-less identity
   *     never played an international match (Copa Libertadores) — a purely
   *     domestic state-less club must be that Brazilian club.
   * Case 2's international guard keeps foreign clubs ("River Plate") from
   * being absorbed into small same-named Brazilian clubs ("River Plate-SE").
   */
  computeStateRedirects(
    matchCounts: Map<string, number>,
    international: Set<string>,
  ): Map<string, TeamIdentity> {
    const redirects = new Map<string, TeamIdentity>();
    const byBase = new Map<string, TeamIdentity[]>();
    for (const t of this.teams.values()) {
      const list = byBase.get(t.base) ?? [];
      list.push(t);
      byBase.set(t.base, list);
    }
    for (const list of byBase.values()) {
      const stateless = list.filter((t) => !t.state);
      const withState = list.filter((t) => t.state);
      if (stateless.length === 0 || withState.length === 0) continue;
      const dominant = withState.sort(
        (a, b) => (matchCounts.get(b.key) ?? 0) - (matchCounts.get(a.key) ?? 0),
      )[0];
      const dominantCount = matchCounts.get(dominant.key) ?? 0;
      for (const t of stateless) {
        const c = matchCounts.get(t.key) ?? 0;
        if (c === 0) continue;
        const dominates = dominantCount >= c && dominantCount > 0;
        const singleDomesticCandidate =
          withState.length === 1 && !international.has(t.key);
        if (dominates || singleDomesticCandidate) redirects.set(t.key, dominant);
      }
    }
    return redirects;
  }
}

function parseGoals(raw: string | undefined): number | undefined {
  if (raw === undefined || raw === null) return undefined;
  const s = String(raw).trim();
  if (s === '' || s === 'NA' || s === '-' || s.toLowerCase() === 'nan') return undefined;
  const n = Number.parseInt(s, 10);
  return Number.isNaN(n) ? undefined : n;
}

function parseSeason(raw: string | undefined): number | undefined {
  if (!raw) return undefined;
  const s = String(raw).trim();
  if (s === '' || s === 'NA') return undefined;
  const n = Number.parseInt(s, 10);
  return Number.isNaN(n) ? undefined : n;
}

function readCsv(file: string): Record<string, string>[] {
  const content = readFileSync(file, { encoding: 'utf-8' });
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    relax_column_count: true,
    bom: true,
    trim: false,
  }) as Record<string, string>[];
}

function makeMatchId(m: {
  date?: string;
  season?: number;
  round?: string;
  homeKey: string;
  awayKey: string;
  source: SourceDataset;
}): string {
  if (m.date) return `${m.date}|${m.homeKey}|${m.awayKey}`;
  // No reliable date: fall back to a source-scoped key to avoid collisions.
  return `${m.source}|nodate|${m.season ?? '?'}|${m.round ?? '?'}|${m.homeKey}|${m.awayKey}`;
}

// ---------------------------------------------------------------------------
// Per-file loaders
// ---------------------------------------------------------------------------

function loadBrasileirao(dir: string, reg: TeamRegistry): Match[] {
  const rows = readCsv(join(dir, 'Brasileirao_Matches.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const home = reg.resolve(r.home_team, r.home_team_state);
    const away = reg.resolve(r.away_team, r.away_team_state);
    const dt = parseDate(r.datetime);
    const hg = parseGoals(r.home_goal);
    const ag = parseGoals(r.away_goal);
    const round = r.round && r.round !== 'NA' ? `Round ${r.round}` : undefined;
    const m: Match = {
      id: '',
      date: dt?.date,
      time: dt?.time,
      competition: 'Brasileirão Série A',
      season: parseSeason(r.season),
      round,
      homeTeam: home,
      awayTeam: away,
      homeGoals: hg,
      awayGoals: ag,
      played: hg !== undefined && ag !== undefined,
      source: 'brasileirao',
    };
    m.id = makeMatchId({ ...m, homeKey: home.key, awayKey: away.key });
    out.push(m);
  }
  return out;
}

function loadCup(dir: string, reg: TeamRegistry): Match[] {
  const rows = readCsv(join(dir, 'Brazilian_Cup_Matches.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const home = reg.resolve(r.home_team);
    const away = reg.resolve(r.away_team);
    const dt = parseDate(r.datetime);
    const hg = parseGoals(r.home_goal);
    const ag = parseGoals(r.away_goal);
    const round = r.round && r.round !== 'NA' ? `Round ${r.round}` : undefined;
    const m: Match = {
      id: '',
      date: dt?.date,
      time: dt?.time,
      competition: 'Copa do Brasil',
      season: parseSeason(r.season),
      round,
      homeTeam: home,
      awayTeam: away,
      homeGoals: hg,
      awayGoals: ag,
      played: hg !== undefined && ag !== undefined,
      source: 'cup',
    };
    m.id = makeMatchId({ ...m, homeKey: home.key, awayKey: away.key });
    out.push(m);
  }
  return out;
}

function stageLabel(stage: string | undefined): string | undefined {
  if (!stage) return undefined;
  const s = stage.trim();
  if (!s || s === 'NA') return undefined;
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

function loadLibertadores(dir: string, reg: TeamRegistry): Match[] {
  const rows = readCsv(join(dir, 'Libertadores_Matches.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const home = reg.resolve(r.home_team);
    const away = reg.resolve(r.away_team);
    const dt = parseDate(r.datetime);
    const hg = parseGoals(r.home_goal);
    const ag = parseGoals(r.away_goal);
    const m: Match = {
      id: '',
      date: dt?.date,
      time: dt?.time,
      competition: 'Copa Libertadores',
      season: parseSeason(r.season),
      round: stageLabel(r.stage),
      homeTeam: home,
      awayTeam: away,
      homeGoals: hg,
      awayGoals: ag,
      played: hg !== undefined && ag !== undefined,
      source: 'libertadores',
    };
    m.id = makeMatchId({ ...m, homeKey: home.key, awayKey: away.key });
    out.push(m);
  }
  return out;
}

function loadBrFootball(dir: string, reg: TeamRegistry): Match[] {
  const rows = readCsv(join(dir, 'BR-Football-Dataset.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const competition: Competition =
      r.tournament === 'Copa do Brasil'
        ? 'Copa do Brasil'
        : r.tournament === 'Serie B'
          ? 'Brasileirão Série B'
          : r.tournament === 'Serie C'
            ? 'Brasileirão Série C'
            : 'Brasileirão Série A';
    const home = reg.resolve(r.home);
    const away = reg.resolve(r.away);
    const dt = parseDate(r.date);
    const hg = parseGoals(r.home_goal);
    const ag = parseGoals(r.away_goal);
    const num = (v: string | undefined) => {
      const n = Number(v);
      return Number.isFinite(n) ? n : undefined;
    };
    const m: Match = {
      id: '',
      date: dt?.date,
      time: r.time ? r.time.slice(0, 5) : undefined,
      competition,
      season: dt ? Number(dt.date.slice(0, 4)) : undefined,
      homeTeam: home,
      awayTeam: away,
      homeGoals: hg,
      awayGoals: ag,
      played: hg !== undefined && ag !== undefined,
      source: 'brfootball',
      stats: {
        homeCorners: num(r.home_corner),
        awayCorners: num(r.away_corner),
        homeShots: num(r.home_shots),
        awayShots: num(r.away_shots),
        homeAttacks: num(r.home_attack),
        awayAttacks: num(r.away_attack),
        halfTimeResult: r.ht_result || undefined,
      },
    };
    m.id = makeMatchId({ ...m, homeKey: home.key, awayKey: away.key });
    out.push(m);
  }
  return out;
}

function loadHistorico(dir: string, reg: TeamRegistry): Match[] {
  const rows = readCsv(join(dir, 'novo_campeonato_brasileiro.csv'));
  const out: Match[] = [];
  for (const r of rows) {
    const home = reg.resolve(r.Equipe_mandante, r.Mandante_UF);
    const away = reg.resolve(r.Equipe_visitante, r.Visitante_UF);
    const dt = parseDate(r.Data);
    const hg = parseGoals(r.Gols_mandante);
    const ag = parseGoals(r.Gols_visitante);
    const round = r.Rodada && r.Rodada !== 'NA' ? `Round ${r.Rodada}` : undefined;
    const m: Match = {
      id: '',
      date: dt?.date,
      competition: 'Brasileirão Série A',
      season: parseSeason(r.Ano),
      round,
      homeTeam: home,
      awayTeam: away,
      homeGoals: hg,
      awayGoals: ag,
      played: hg !== undefined && ag !== undefined,
      stadium: r.Arena && r.Arena !== 'NA' ? r.Arena : undefined,
      source: 'historico',
    };
    m.id = makeMatchId({ ...m, homeKey: home.key, awayKey: away.key });
    out.push(m);
  }
  return out;
}

// ---------------------------------------------------------------------------
// FIFA players
// ---------------------------------------------------------------------------

const SKILL_COLUMNS = [
  'Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing', 'Volleys',
  'Dribbling', 'Curve', 'FKAccuracy', 'LongPassing', 'BallControl',
  'Acceleration', 'SprintSpeed', 'Agility', 'Reactions', 'Balance',
  'ShotPower', 'Jumping', 'Stamina', 'Strength', 'LongShots', 'Aggression',
  'Interceptions', 'Positioning', 'Vision', 'Penalties', 'Composure',
  'Marking', 'StandingTackle', 'SlidingTackle', 'GKDiving', 'GKHandling',
  'GKKicking', 'GKPositioning', 'GKReflexes',
];

function loadPlayers(dir: string): Player[] {
  const rows = readCsv(join(dir, 'fifa_data.csv'));
  const players: Player[] = [];
  for (const r of rows) {
    const skills: Record<string, number> = {};
    for (const col of SKILL_COLUMNS) {
      const n = Number.parseInt(r[col] ?? '', 10);
      if (!Number.isNaN(n)) skills[col] = n;
    }
    players.push({
      id: Number.parseInt(r.ID ?? '', 10),
      name: (r.Name ?? '').trim(),
      age: Number.parseInt(r.Age ?? '', 10) || undefined,
      nationality: r.Nationality || undefined,
      overall: Number.parseInt(r.Overall ?? '', 10) || undefined,
      potential: Number.parseInt(r.Potential ?? '', 10) || undefined,
      club: r.Club && r.Club.trim() !== '' ? r.Club.trim() : undefined,
      position: r.Position || undefined,
      jerseyNumber: Number.parseInt(r['Jersey Number'] ?? '', 10) || undefined,
      height: r.Height || undefined,
      weight: r.Weight || undefined,
      preferredFoot: r['Preferred Foot'] || undefined,
      value: r.Value || undefined,
      wage: r.Wage || undefined,
      skills,
    });
  }
  return players;
}

// ---------------------------------------------------------------------------
// Store assembly
// ---------------------------------------------------------------------------

/** Locate the data/kaggle directory (env override, cwd, or repo-relative). */
export function resolveDataDir(explicit?: string): string {
  const candidates = [
    explicit,
    process.env.SOCCER_DATA_DIR,
    join(process.cwd(), 'data', 'kaggle'),
    // two levels up from dist/ when running the compiled server
    join(resolve(fileURLToPath(import.meta.url), '..', '..', '..'), 'data', 'kaggle'),
  ].filter((c): c is string => !!c);
  for (const c of candidates) {
    if (existsSync(join(c, 'Brasileirao_Matches.csv'))) return c;
  }
  throw new Error(
    `Could not locate data/kaggle directory. Tried: ${candidates.join(', ')}`,
  );
}

const DAY_MS = 86_400_000;

function dateToMs(iso: string): number {
  return Date.parse(`${iso}T00:00:00Z`);
}

/** Pick the preferred duplicate: played beats unplayed, then source priority. */
function bestOf(cluster: Match[]): Match {
  return cluster.reduce((best, m) => {
    const score = (x: Match) => SOURCE_PRIORITY[x.source] * 10 + (x.played ? 0 : 1);
    return score(m) < score(best) ? m : best;
  });
}

/**
 * Deduplicate matches that appear in several overlapping source files.
 * The same fixture may carry dates one day apart across sources (late-evening
 * kick-offs recorded in local time vs UTC), so clustering is done per fixture
 * (home+away identities) with a tolerance of one day.
 */
function dedupe(matches: Match[]): Match[] {
  const byFixture = new Map<string, Match[]>();
  const undated = new Map<string, Match>();
  for (const m of matches) {
    if (!m.date) {
      const cur = undated.get(m.id);
      undated.set(m.id, cur ? bestOf([cur, m]) : m);
      continue;
    }
    const k = `${m.homeTeam.key}|${m.awayTeam.key}`;
    const list = byFixture.get(k);
    if (list) list.push(m);
    else byFixture.set(k, [m]);
  }

  const kept: Match[] = [...undated.values()];
  for (const group of byFixture.values()) {
    group.sort((a, b) => a.date!.localeCompare(b.date!));
    let cluster: Match[] = [];
    let lastDate = '';
    const flush = () => {
      if (cluster.length > 0) kept.push(bestOf(cluster));
      cluster = [];
    };
    for (const m of group) {
      // Chain: consecutive rows one day apart are the same match (sources
      // disagree on local-vs-UTC dates by a day at most).
      if (cluster.length > 0 && dateToMs(m.date!) - dateToMs(lastDate) > DAY_MS) {
        flush();
      }
      lastDate = m.date!;
      cluster.push(m);
    }
    flush();
  }

  // Post-pass: a scheduled-but-unplayed row ("NA" goals) and its actually
  // played twin may carry different dates (postponed games). Drop the
  // unplayed row when the same fixture exists played in the same
  // competition+season; keep it otherwise (cancelled games stay visible).
  const playedByFixture = new Map<string, Match>();
  const result: Match[] = [];
  const unplayedRows: Match[] = [];
  for (const m of kept) {
    if (m.played) {
      playedByFixture.set(
        `${m.homeTeam.key}|${m.awayTeam.key}|${m.competition}|${m.season ?? '?'}`,
        m,
      );
      result.push(m);
    } else {
      unplayedRows.push(m);
    }
  }
  for (const m of unplayedRows) {
    const k = `${m.homeTeam.key}|${m.awayTeam.key}|${m.competition}|${m.season ?? '?'}`;
    if (!playedByFixture.has(k)) result.push(m);
  }

  return result.sort((a, b) => {
    if (a.date && b.date) return a.date < b.date ? -1 : a.date > b.date ? 1 : 0;
    if (a.date) return -1;
    if (b.date) return 1;
    return 0;
  });
}

/** Load all six CSV files and build the in-memory store. */
export function loadDataset(dataDir?: string): DatasetStore {
  const dir = resolveDataDir(dataDir);
  const reg = new TeamRegistry();

  const all: Match[] = [
    ...loadBrasileirao(dir, reg),
    ...loadCup(dir, reg),
    ...loadLibertadores(dir, reg),
    ...loadBrFootball(dir, reg),
    ...loadHistorico(dir, reg),
  ];

  // First pass: count matches per identity, then redirect state-less
  // identities (mostly BR-Football rows) to their state-ful twins.
  const counts = new Map<string, number>();
  const international = new Set<string>();
  for (const m of all) {
    counts.set(m.homeTeam.key, (counts.get(m.homeTeam.key) ?? 0) + 1);
    counts.set(m.awayTeam.key, (counts.get(m.awayTeam.key) ?? 0) + 1);
    if (m.competition === 'Copa Libertadores') {
      international.add(m.homeTeam.key);
      international.add(m.awayTeam.key);
    }
  }
  const redirects = reg.computeStateRedirects(counts, international);
  for (const m of all) {
    const h = redirects.get(m.homeTeam.key);
    const a = redirects.get(m.awayTeam.key);
    if (h) m.homeTeam = h;
    if (a) m.awayTeam = a;
    if (h || a) {
      m.id = makeMatchId({
        date: m.date,
        season: m.season,
        round: m.round,
        homeKey: m.homeTeam.key,
        awayKey: m.awayTeam.key,
        source: m.source,
      });
    }
  }
  // Drop fully absorbed identities so they don't surface in find_teams.
  for (const key of redirects.keys()) reg.teams.delete(key);
  reg.finalizeDisplayNames();

  const dedupedMatches = dedupe(all);

  // Final per-identity match counts (deduped view).
  for (const t of reg.teams.values()) t.matchCount = 0;
  for (const m of dedupedMatches) {
    m.homeTeam.matchCount++;
    m.awayTeam.matchCount++;
  }

  const competitions = new Map<Competition, Set<number>>();
  for (const m of dedupedMatches) {
    let seasons = competitions.get(m.competition);
    if (!seasons) {
      seasons = new Set();
      competitions.set(m.competition, seasons);
    }
    if (m.season !== undefined) seasons.add(m.season);
  }

  const players = loadPlayers(dir);

  return {
    matches: all,
    dedupedMatches,
    players,
    teams: reg.teams,
    competitions,
    loadedAt: new Date(),
  };
}

/** Simplified-club-name index over FIFA player clubs (for club filtering). */
export function clubMatches(playerClub: string | undefined, queryBase: string): boolean {
  if (!playerClub) return false;
  const pc = parseTeamName(playerClub);
  return pc.base === queryBase || simplify(playerClub).includes(queryBase);
}
