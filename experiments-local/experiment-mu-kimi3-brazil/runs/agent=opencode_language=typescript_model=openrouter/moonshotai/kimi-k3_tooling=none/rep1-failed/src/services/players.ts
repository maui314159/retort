/**
 * Player-query service over the FIFA database: name search plus filters
 * for nationality, club and position, sorted by rating.
 */
import type { Dataset, Player } from "../types.js";
import { foldAccents } from "../normalize.js";

export interface PlayerFilter {
  /** Substring of the player name (accent-insensitive). */
  name?: string;
  /** Substring of nationality, e.g. "Brazil". */
  nationality?: string;
  /** Substring of club, e.g. "Flamengo". */
  club?: string;
  /** Position code ("ST", "LW", "GK") or position group ("forward", "midfielder", "defender", "goalkeeper"). */
  position?: string;
  /** Minimum FIFA overall rating. */
  minOverall?: number;
  /** Max results (default 20). */
  limit?: number;
}

const POSITION_GROUPS: Record<string, Set<string>> = {
  forward: new Set(["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"]),
  midfielder: new Set(["CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM", "LCM", "RCM", "LDM", "RDM"]),
  defender: new Set(["CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"]),
  goalkeeper: new Set(["GK"]),
};

const norm = (s: string) => foldAccents(s).toLowerCase();

/** Search players; results sorted by overall rating desc, then name. */
export function searchPlayers(ds: Dataset, f: PlayerFilter): Player[] {
  const limit = f.limit ?? 20;
  const nameQ = f.name ? norm(f.name) : null;
  const natQ = f.nationality ? norm(f.nationality) : null;
  const clubQ = f.club ? norm(f.club) : null;
  const posQ = f.position ? f.position.trim().toLowerCase() : null;
  const group = posQ ? POSITION_GROUPS[posQ] : undefined;

  const hits = ds.players.filter((p) => {
    if (nameQ && !norm(p.name).includes(nameQ)) return false;
    if (natQ && !norm(p.nationality).includes(natQ)) return false;
    if (clubQ && !(p.club && norm(p.club).includes(clubQ))) return false;
    if (posQ) {
      const pos = (p.position ?? "").toUpperCase();
      if (group) {
        if (!group.has(pos)) return false;
      } else if (pos !== posQ.toUpperCase()) return false;
    }
    if (f.minOverall !== undefined && (p.overall ?? 0) < f.minOverall) return false;
    return true;
  });

  hits.sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name));
  return hits.slice(0, limit);
}

/** Aggregate: players per club for a nationality (e.g. Brazilians per club). */
export function playersPerClub(
  ds: Dataset,
  opts: { nationality?: string; minPlayers?: number; limit?: number } = {},
): { club: string; players: number; avgOverall: number }[] {
  const natQ = opts.nationality ? norm(opts.nationality) : null;
  const acc = new Map<string, { club: string; players: number; total: number }>();
  for (const p of ds.players) {
    if (natQ && !norm(p.nationality).includes(natQ)) continue;
    if (!p.club) continue;
    const cur = acc.get(p.club) ?? { club: p.club, players: 0, total: 0 };
    cur.players++;
    cur.total += p.overall ?? 0;
    acc.set(p.club, cur);
  }
  return [...acc.values()]
    .filter((c) => c.players >= (opts.minPlayers ?? 1))
    .map((c) => ({ club: c.club, players: c.players, avgOverall: c.players ? c.total / c.players : 0 }))
    .sort((a, b) => b.players - a.players || b.avgOverall - a.avgOverall)
    .slice(0, opts.limit ?? 20);
}
