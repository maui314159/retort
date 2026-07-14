/**
 * Player query helpers over the FIFA dataset.
 */

import type { DatasetSnapshot, Player } from '../data/types.js';
import { teamMatches } from '../data/normalizer.js';

export interface PlayerQuery {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  limit?: number;
  sortBy?: 'overall' | 'potential' | 'age' | 'name';
  order?: 'asc' | 'desc';
}

function norm(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

export function findPlayers(snap: DatasetSnapshot, q: PlayerQuery): Player[] {
  const limit = q.limit ?? Number.POSITIVE_INFINITY;
  const nameNeedle = q.name ? norm(q.name) : undefined;
  const natNeedle = q.nationality ? norm(q.nationality) : undefined;
  const posNeedle = q.position ? norm(q.position) : undefined;

  const out: Player[] = [];
  for (const p of snap.players) {
    if (nameNeedle && !norm(p.name).includes(nameNeedle)) continue;
    if (natNeedle && !norm(p.nationality).includes(natNeedle)) continue;
    if (posNeedle && !norm(p.position).includes(posNeedle)) continue;
    if (q.club && !teamMatches(p.club, q.club)) continue;
    if (q.minOverall !== undefined && (p.overall ?? 0) < q.minOverall) continue;
    out.push(p);
  }

  const sortBy = q.sortBy ?? 'overall';
  const order = q.order ?? 'desc';
  out.sort((a, b) => {
    const av = a[sortBy] ?? 0;
    const bv = b[sortBy] ?? 0;
    if (av === bv) return 0;
    return order === 'desc' ? (bv as number) - (av as number) : (av as number) - (bv as number);
  });
  return out.slice(0, limit);
}

export interface ClubRosterStats {
  club: string;
  players: number;
  avgOverall: number;
  topPlayers: Player[];
}

export function clubRoster(snap: DatasetSnapshot, club: string, limit = 10): ClubRosterStats {
  const list = findPlayers(snap, { club, sortBy: 'overall' });
  const avg = list.length === 0 ? 0 : list.reduce((s, p) => s + (p.overall ?? 0), 0) / list.length;
  return { club, players: list.length, avgOverall: Math.round(avg * 10) / 10, topPlayers: list.slice(0, limit) };
}

export function clubsByNationality(snap: DatasetSnapshot, nationality: string, minPlayers = 1): ClubRosterStats[] {
  const players = findPlayers(snap, { nationality, sortBy: 'overall' });
  const groups = new Map<string, Player[]>();
  for (const p of players) {
    if (!p.club) continue;
    const list = groups.get(p.club) ?? [];
    list.push(p);
    groups.set(p.club, list);
  }
  const out: ClubRosterStats[] = [];
  for (const [club, list] of groups.entries()) {
    if (list.length < minPlayers) continue;
    const avg = list.reduce((s, p) => s + (p.overall ?? 0), 0) / list.length;
    out.push({
      club, players: list.length,
      avgOverall: Math.round(avg * 10) / 10,
      topPlayers: list.slice(0, 5)
    });
  }
  out.sort((a, b) => b.players - a.players || b.avgOverall - a.avgOverall);
  return out;
}
