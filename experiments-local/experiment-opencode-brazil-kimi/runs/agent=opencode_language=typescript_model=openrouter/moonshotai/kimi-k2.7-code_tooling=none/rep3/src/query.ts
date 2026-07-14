import { Match, Player, StandingRecord, TeamStats } from "./types.js";
import { sameTeam, teamKey, normalizeTeamName, formatPercent } from "./normalize.js";

export interface MatchFilters {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  teamA?: string;
  teamB?: string;
  competition?: string;
  season?: number;
  startDate?: string;
  endDate?: string;
  round?: string;
  stage?: string;
}

export interface QueryResult {
  text: string;
  data: unknown;
}

function matchCompetition(competition: string, filter?: string): boolean {
  if (!filter) return true;
  const keyComp = competition.toLowerCase();
  const keyFilter = filter.toLowerCase();
  if (keyComp.includes(keyFilter)) return true;
  if (keyFilter === "brasileirão" || keyFilter === "brasileirao") {
    return keyComp.includes("brasileir") || keyComp === "serie a" || keyComp === "serie b";
  }
  if (keyFilter === "libertadores") return keyComp.includes("libertadores");
  if (keyFilter === "copa do brasil") return keyComp.includes("copa do brasil");
  return false;
}

export class QueryEngine {
  constructor(private matches: Match[], private players: Player[]) {}

  private filterMatches(filters: MatchFilters, matches?: Match[]): Match[] {
    const source = matches ?? this.matches;
    return source.filter((m) => {
      if (filters.team && !sameTeam(m.homeTeam, filters.team) && !sameTeam(m.awayTeam, filters.team)) return false;
      if (filters.homeTeam && !sameTeam(m.homeTeam, filters.homeTeam)) return false;
      if (filters.awayTeam && !sameTeam(m.awayTeam, filters.awayTeam)) return false;
      if (filters.teamA && !sameTeam(m.homeTeam, filters.teamA) && !sameTeam(m.awayTeam, filters.teamA)) return false;
      if (filters.teamB && !sameTeam(m.homeTeam, filters.teamB) && !sameTeam(m.awayTeam, filters.teamB)) return false;
      if (filters.competition && !matchCompetition(m.competition, filters.competition)) return false;
      if (filters.season !== undefined && m.season !== filters.season) return false;
      if (filters.startDate && m.date && m.date < filters.startDate) return false;
      if (filters.endDate && m.date && m.date > filters.endDate) return false;
      if (filters.round && m.round !== filters.round) return false;
      if (filters.stage && m.stage !== filters.stage) return false;
      return true;
    });
  }

  private filterHeadToHead(teamA: string, teamB: string, filters?: Omit<MatchFilters, "teamA" | "teamB">): Match[] {
    const candidates = this.filterMatches({ ...filters, teamA, teamB });
    return candidates.filter(
      (m) =>
        (sameTeam(m.homeTeam, teamA) && sameTeam(m.awayTeam, teamB)) ||
        (sameTeam(m.homeTeam, teamB) && sameTeam(m.awayTeam, teamA))
    );
  }

  private sortMatchesByDate(matches: Match[]): Match[] {
    return [...matches].sort((a, b) => b.date.localeCompare(a.date));
  }

  private formatMatchLine(m: Match): string {
    const compParts = [m.competition];
    if (m.round) compParts.push(`Round ${m.round}`);
    if (m.stage) compParts.push(m.stage);
    return `${m.date}: ${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam} (${compParts.join(", ")})`;
  }

  findMatchesBetweenTeams(teamA: string, teamB: string, limit = 10): QueryResult {
    const matches = this.sortMatchesByDate(this.filterHeadToHead(teamA, teamB));
    let [winsA, winsB, draws] = [0, 0, 0];
    for (const m of matches) {
      if (m.homeGoal === m.awayGoal) draws++;
      else if (sameTeam(m.homeTeam, teamA) && m.homeGoal > m.awayGoal) winsA++;
      else if (sameTeam(m.awayTeam, teamA) && m.awayGoal > m.homeGoal) winsA++;
      else winsB++;
    }
    const lines = matches.slice(0, limit).map((m) => `- ${this.formatMatchLine(m)}`);
    const more = matches.length > limit ? `\n... (${matches.length - limit} more matches in dataset)` : "";
    const text = `${teamA} vs ${teamB}:\n${lines.join("\n")}${more}\n\nHead-to-head in dataset: ${teamA} ${winsA} wins, ${teamB} ${winsB} wins, ${draws} draws`;
    return { text, data: { matches, winsA, winsB, draws } };
  }

  findMatches(filters: MatchFilters, limit = 20): QueryResult {
    const matches = this.sortMatchesByDate(this.filterMatches(filters));
    const lines = matches.slice(0, limit).map((m) => `- ${this.formatMatchLine(m)}`);
    const more = matches.length > limit ? `\n... (${matches.length - limit} more matches)` : "";
    const text = `Found ${matches.length} matches:\n${lines.join("\n")}${more}`;
    return { text, data: matches.slice(0, limit) };
  }

  getTeamStats(team: string, filters?: Omit<MatchFilters, "team">): QueryResult {
    const relevant = this.filterMatches({ team, ...filters });
    const stats: TeamStats = {
      team,
      matches: 0,
      wins: 0,
      draws: 0,
      losses: 0,
      goalsFor: 0,
      goalsAgainst: 0,
      goalDifference: 0,
      homeMatches: 0,
      awayMatches: 0,
      homeWins: 0,
      awayWins: 0,
    };
    for (const m of relevant) {
      const isHome = sameTeam(m.homeTeam, team);
      const goalsFor = isHome ? m.homeGoal : m.awayGoal;
      const goalsAgainst = isHome ? m.awayGoal : m.homeGoal;
      if (isNaN(goalsFor) || isNaN(goalsAgainst)) continue;
      stats.matches++;
      stats.goalsFor += goalsFor;
      stats.goalsAgainst += goalsAgainst;
      if (isHome) {
        stats.homeMatches++;
        if (goalsFor > goalsAgainst) stats.homeWins++;
      } else {
        stats.awayMatches++;
        if (goalsFor > goalsAgainst) stats.awayWins++;
      }
      if (goalsFor > goalsAgainst) stats.wins++;
      else if (goalsFor === goalsAgainst) stats.draws++;
      else stats.losses++;
    }
    stats.goalDifference = stats.goalsFor - stats.goalsAgainst;
    const winRate = stats.matches ? stats.wins / stats.matches : 0;
    const context = filters?.season ? ` (${filters.season}${filters.competition ? ` ${filters.competition}` : ""})` : "";
    const homeOnly = filters?.homeTeam ? " home" : "";
    const awayOnly = filters?.awayTeam ? " away" : "";
    const text = `${team}${homeOnly}${awayOnly} record${context}:\n- Matches: ${stats.matches}\n- Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}\n- Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst}\n- Win rate: ${formatPercent(winRate)}`;
    return { text, data: stats };
  }

  findPlayers(filters: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    limit?: number;
  }): QueryResult {
    const limit = filters.limit ?? 20;
    const normalizedClub = filters.club ? normalizeTeamName(filters.club) : undefined;
    let result = this.players.filter((p) => {
      if (filters.name && !p.name.toLowerCase().includes(filters.name.toLowerCase())) return false;
      if (filters.nationality && !p.nationality.toLowerCase().includes(filters.nationality.toLowerCase())) return false;
      if (filters.club) {
        const clubKey = teamKey(p.club);
        const filterKey = teamKey(normalizedClub ?? filters.club);
        if (clubKey !== filterKey && !clubKey.includes(filterKey) && !filterKey.includes(clubKey)) return false;
      }
      if (filters.position && !p.position.toLowerCase().includes(filters.position.toLowerCase())) return false;
      if (filters.minOverall !== undefined && p.overall < filters.minOverall) return false;
      return true;
    });
    result = result.sort((a, b) => b.overall - a.overall).slice(0, limit);
    const lines = result.map(
      (p, i) => `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club}, Nationality: ${p.nationality}`
    );
    const text = `Found ${result.length} players:\n${lines.join("\n")}`;
    return { text, data: result };
  }

  getPlayerByName(name: string): QueryResult {
    const matches = this.players
      .filter(
        (p) =>
          p.name.toLowerCase().includes(name.toLowerCase()) ||
          normalizeTeamName(p.name).toLowerCase().includes(name.toLowerCase())
      )
      .sort((a, b) => b.overall - a.overall);
    if (matches.length === 0) return { text: `No player found matching "${name}".`, data: [] };
    const p = matches[0];
    const text = `${p.name}: Age ${p.age}, Nationality: ${p.nationality}, Overall: ${p.overall}, Potential: ${p.potential}, Club: ${p.club}, Position: ${p.position}`;
    return { text, data: p };
  }

  getStandings(competition?: string, season?: number): QueryResult {
    const relevant = this.filterMatches({ competition, season });
    const table = new Map<string, StandingRecord>();
    for (const m of relevant) {
      if (isNaN(m.homeGoal) || isNaN(m.awayGoal)) continue;
      for (const [team, gf, ga, isHome] of [
        [m.homeTeam, m.homeGoal, m.awayGoal, true],
        [m.awayTeam, m.awayGoal, m.homeGoal, false],
      ] as [string, number, number, boolean][]) {
        const rec = table.get(team) ?? {
          team,
          points: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          goalDifference: 0,
          matches: 0,
        };
        rec.matches++;
        rec.goalsFor += gf;
        rec.goalsAgainst += ga;
        if (gf > ga) {
          rec.wins++;
          rec.points += 3;
        } else if (gf === ga) {
          rec.draws++;
          rec.points += 1;
        } else {
          rec.losses++;
        }
        rec.goalDifference = rec.goalsFor - rec.goalsAgainst;
        table.set(team, rec);
      }
    }
    const sorted = Array.from(table.values()).sort(
      (a, b) => b.points - a.points || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor
    );
    const lines = sorted.map(
      (r, i) =>
        `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L)${
          i === 0 ? " - Champion" : ""
        }`
    );
    const title = `${season ?? "All seasons"}${competition ? ` ${competition}` : ""} Final Standings`;
    const text = `${title} (calculated from matches):\n${lines.slice(0, 20).join("\n")}`;
    return { text, data: sorted };
  }

  getTopScoringTeams(competition?: string, season?: number, limit = 5): QueryResult {
    const stats = new Map<string, { goals: number; matches: number }>();
    for (const m of this.filterMatches({ competition, season })) {
      if (isNaN(m.homeGoal) || isNaN(m.awayGoal)) continue;
      for (const [team, goals] of [
        [m.homeTeam, m.homeGoal],
        [m.awayTeam, m.awayGoal],
      ] as [string, number][]) {
        const entry = stats.get(team) ?? { goals: 0, matches: 0 };
        entry.goals += goals;
        entry.matches++;
        stats.set(team, entry);
      }
    }
    const sorted = Array.from(stats.entries())
      .sort((a, b) => b[1].goals - a[1].goals)
      .slice(0, limit);
    const lines = sorted.map(([team, s]) => `- ${team}: ${s.goals} goals in ${s.matches} matches`);
    const text = `Top scoring teams:\n${lines.join("\n")}`;
    return { text, data: sorted };
  }

  getBiggestWins(competition?: string, limit = 5): QueryResult {
    const matches = this.filterMatches({ competition });
    const withDiff = matches
      .filter((m) => !isNaN(m.homeGoal) && !isNaN(m.awayGoal) && Math.abs(m.homeGoal - m.awayGoal) > 0)
      .map((m) => ({ m, diff: Math.abs(m.homeGoal - m.awayGoal) }))
      .sort((a, b) => b.diff - a.diff)
      .slice(0, limit);
    const lines = withDiff.map(({ m }) => `- ${m.date}: ${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam} (${m.competition})`);
    const text = `Biggest victories${competition ? ` in ${competition}` : ""}:\n${lines.join("\n")}`;
    return { text, data: withDiff.map((x) => x.m) };
  }

  getOverallStats(competition?: string): QueryResult {
    const matches = this.filterMatches({ competition });
    const valid = matches.filter((m) => !isNaN(m.homeGoal) && !isNaN(m.awayGoal));
    const totalGoals = valid.reduce((sum, m) => sum + m.homeGoal + m.awayGoal, 0);
    const avgGoals = valid.length ? totalGoals / valid.length : 0;
    const homeWins = valid.filter((m) => m.homeGoal > m.awayGoal).length;
    const homeWinRate = valid.length ? homeWins / valid.length : 0;
    const text = `Average goals per match${competition ? ` in ${competition}` : ""}: ${avgGoals.toFixed(2)}\nHome win rate: ${formatPercent(
      homeWinRate
    )}\nTotal matches analyzed: ${valid.length}`;
    return { text, data: { avgGoals, homeWinRate, totalMatches: valid.length } };
  }

  getTeamRankings(): QueryResult {
    const allStats = new Map<string, TeamStats>();
    for (const m of this.matches) {
      if (isNaN(m.homeGoal) || isNaN(m.awayGoal)) continue;
      for (const [team, gf, ga, isHome] of [
        [m.homeTeam, m.homeGoal, m.awayGoal, true],
        [m.awayTeam, m.awayGoal, m.homeGoal, false],
      ] as [string, number, number, boolean][]) {
        const s = allStats.get(team) ?? {
          team,
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
          goalDifference: 0,
          homeMatches: 0,
          awayMatches: 0,
          homeWins: 0,
          awayWins: 0,
        };
        s.matches++;
        s.goalsFor += gf;
        s.goalsAgainst += ga;
        if (gf > ga) {
          s.wins++;
          if (isHome) s.homeWins++;
          else s.awayWins++;
        } else if (gf === ga) s.draws++;
        else s.losses++;
        if (isHome) s.homeMatches++;
        else s.awayMatches++;
        s.goalDifference = s.goalsFor - s.goalsAgainst;
        allStats.set(team, s);
      }
    }
    const sorted = Array.from(allStats.values()).sort((a, b) =>
      b.wins / Math.max(b.matches, 1) - a.wins / Math.max(a.matches, 1) !== 0
        ? b.wins / Math.max(b.matches, 1) - a.wins / Math.max(a.matches, 1)
        : b.matches - a.matches
    );
    const bestHome = [...allStats.values()].sort(
      (a, b) => b.homeWins / Math.max(b.homeMatches, 1) - a.homeWins / Math.max(a.homeMatches, 1)
    )[0];
    const bestAway = [...allStats.values()].sort(
      (a, b) => b.awayWins / Math.max(b.awayMatches, 1) - a.awayWins / Math.max(a.awayMatches, 1)
    )[0];
    const lines = sorted.slice(0, 10).map(
      (s, i) => `${i + 1}. ${s.team}: ${s.wins}W/${s.draws}D/${s.losses}L in ${s.matches} matches`
    );
    const text = `Best home record: ${bestHome?.team ?? "N/A"} (${bestHome?.homeWins} home wins)\nBest away record: ${bestAway?.team ?? "N/A"} (${bestAway?.awayWins} away wins)\n\nTop teams overall:\n${lines.join(
      "\n"
    )}`;
    return { text, data: { bestHome, bestAway, topTeams: sorted.slice(0, 10) } };
  }

  compareTeams(teamA: string, teamB: string): QueryResult {
    const h2h = this.findMatchesBetweenTeams(teamA, teamB, 5);
    const statsA = this.getTeamStats(teamA);
    const statsB = this.getTeamStats(teamB);
    const text = `${teamA} vs ${teamB} Comparison\n\n${statsA.text}\n\n${statsB.text}\n\n${h2h.text}`;
    return { text, data: { statsA: statsA.data, statsB: statsB.data, h2h: h2h.data } };
  }
}
