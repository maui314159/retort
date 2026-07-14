import { parse } from 'csv-parse/sync';
import fs from 'fs';
import path from 'path';
import { MatchRow, PlayerRow, TeamStats, HeadToHead, StandingRow } from './types.js';

export function cleanForSearch(name: string): string {
  return name
    .replace(/-\s*[A-Z]{2,3}\s*$/, '') // Remove state suffix like "-SP"
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // Remove accents
    .toLowerCase()
    .trim();
}

function parseNumber(val: unknown): number {
  if (typeof val === 'number') return val;
  if (typeof val === 'string') {
    const parsed = parseFloat(val.replace(',', '.'));
    return isNaN(parsed) ? 0 : parsed;
  }
  return 0;
}

function loadCsv(filePath: string): Record<string, string>[] {
  const content = fs.readFileSync(filePath, 'utf-8');
  return parse(content, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
    bom: true,
  }) as Record<string, string>[];
}

export class DataManager {
  private matches: MatchRow[] = [];
  private players: PlayerRow[] = [];

  constructor(private dataDir: string) {}

  public async load() {
    // 1. Brasileirao Matches
    const brasileirao = loadCsv(path.join(this.dataDir, 'Brasileirao_Matches.csv'));
    for (const r of brasileirao) {
      this.matches.push({
        date: r.datetime || '',
        homeTeam: r.home_team || '',
        awayTeam: r.away_team || '',
        homeTeamClean: cleanForSearch(r.home_team || ''),
        awayTeamClean: cleanForSearch(r.away_team || ''),
        homeGoals: parseNumber(r.home_goal),
        awayGoals: parseNumber(r.away_goal),
        season: r.season || '',
        competition: 'Brasileirao',
        round: r.round || '',
      });
    }

    // 2. Brazilian Cup Matches
    const cup = loadCsv(path.join(this.dataDir, 'Brazilian_Cup_Matches.csv'));
    for (const r of cup) {
      this.matches.push({
        date: r.datetime || '',
        homeTeam: r.home_team || '',
        awayTeam: r.away_team || '',
        homeTeamClean: cleanForSearch(r.home_team || ''),
        awayTeamClean: cleanForSearch(r.away_team || ''),
        homeGoals: parseNumber(r.home_goal),
        awayGoals: parseNumber(r.away_goal),
        season: r.season || '',
        competition: 'Copa do Brasil',
        round: r.round || '',
      });
    }

    // 3. Libertadores Matches
    const libertadores = loadCsv(path.join(this.dataDir, 'Libertadores_Matches.csv'));
    for (const r of libertadores) {
      this.matches.push({
        date: r.datetime || '',
        homeTeam: r.home_team || '',
        awayTeam: r.away_team || '',
        homeTeamClean: cleanForSearch(r.home_team || ''),
        awayTeamClean: cleanForSearch(r.away_team || ''),
        homeGoals: parseNumber(r.home_goal),
        awayGoals: parseNumber(r.away_goal),
        season: r.season || '',
        competition: 'Libertadores',
        stage: r.stage || '',
      });
    }

    // 4. BR-Football-Dataset
    const extended = loadCsv(path.join(this.dataDir, 'BR-Football-Dataset.csv'));
    for (const r of extended) {
      this.matches.push({
        date: r.date || '',
        homeTeam: r.home || '',
        awayTeam: r.away || '',
        homeTeamClean: cleanForSearch(r.home || ''),
        awayTeamClean: cleanForSearch(r.away || ''),
        homeGoals: parseNumber(r.home_goal),
        awayGoals: parseNumber(r.away_goal),
        season: r.date ? new Date(r.date).getFullYear().toString() : '',
        competition: r.tournament || 'Other',
      });
    }

    // 5. Historic Brasileirao
    const historic = loadCsv(path.join(this.dataDir, 'novo_campeonato_brasileiro.csv'));
    for (const r of historic) {
      this.matches.push({
        date: r.Data || '',
        homeTeam: r.Equipe_mandante || '',
        awayTeam: r.Equipe_visitante || '',
        homeTeamClean: cleanForSearch(r.Equipe_mandante || ''),
        awayTeamClean: cleanForSearch(r.Equipe_visitante || ''),
        homeGoals: parseNumber(r.Gols_mandante),
        awayGoals: parseNumber(r.Gols_visitante),
        season: r.Ano || '',
        competition: 'Brasileirao Historico',
        round: r.Rodada || '',
      });
    }

    // 6. FIFA Data
    const fifa = loadCsv(path.join(this.dataDir, 'fifa_data.csv'));
    for (const r of fifa) {
      this.players.push({
        id: r.ID || '',
        name: r.Name || '',
        age: parseNumber(r.Age),
        nationality: r.Nationality || '',
        overall: parseNumber(r.Overall),
        potential: parseNumber(r.Potential),
        club: r.Club || '',
        position: r.Position || '',
      });
    }
  }

  public searchMatches(params: {
    team?: string;
    team1?: string;
    team2?: string;
    competition?: string;
    season?: string;
  }): MatchRow[] {
    let results = this.matches;

    if (params.team) {
      const cleanTeam = cleanForSearch(params.team);
      results = results.filter(m => m.homeTeamClean.includes(cleanTeam) || m.awayTeamClean.includes(cleanTeam));
    }

    if (params.team1 && params.team2) {
      const cleanTeam1 = cleanForSearch(params.team1);
      const cleanTeam2 = cleanForSearch(params.team2);
      results = results.filter(m => 
        (m.homeTeamClean.includes(cleanTeam1) && m.awayTeamClean.includes(cleanTeam2)) ||
        (m.homeTeamClean.includes(cleanTeam2) && m.awayTeamClean.includes(cleanTeam1))
      );
    } else if (params.team1) {
      const cleanTeam1 = cleanForSearch(params.team1);
      results = results.filter(m => m.homeTeamClean.includes(cleanTeam1) || m.awayTeamClean.includes(cleanTeam1));
    }

    if (params.competition) {
      const cleanComp = params.competition.toLowerCase();
      results = results.filter(m => m.competition.toLowerCase().includes(cleanComp));
    }

    if (params.season) {
      results = results.filter(m => m.season === params.season);
    }

    return results;
  }

  public getTeamStats(team: string, season?: string, competition?: string): TeamStats {
    const cleanTeam = cleanForSearch(team);
    let matches = this.matches.filter(m => m.homeTeamClean.includes(cleanTeam) || m.awayTeamClean.includes(cleanTeam));

    if (season) {
      matches = matches.filter(m => m.season === season);
    }
    if (competition) {
      const cleanComp = competition.toLowerCase();
      matches = matches.filter(m => m.competition.toLowerCase().includes(cleanComp));
    }

    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;

    for (const m of matches) {
      const isHome = m.homeTeamClean.includes(cleanTeam);
      const teamGoals = isHome ? m.homeGoals : m.awayGoals;
      const oppGoals = isHome ? m.awayGoals : m.homeGoals;

      goalsFor += teamGoals;
      goalsAgainst += oppGoals;

      if (teamGoals > oppGoals) wins++;
      else if (teamGoals === oppGoals) draws++;
      else losses++;
    }

    const totalMatches = matches.length;
    return {
      team,
      matches: totalMatches,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      winRate: totalMatches > 0 ? (wins / totalMatches) * 100 : 0,
    };
  }

  public searchPlayers(params: {
    name?: string;
    nationality?: string;
    club?: string;
    minOverall?: number;
  }): PlayerRow[] {
    let results = this.players;

    if (params.name) {
      const cleanName = cleanForSearch(params.name);
      results = results.filter(p => cleanForSearch(p.name).includes(cleanName));
    }

    if (params.nationality) {
      const cleanNat = cleanForSearch(params.nationality);
      results = results.filter(p => cleanForSearch(p.nationality).includes(cleanNat));
    }

    if (params.club) {
      const cleanClub = cleanForSearch(params.club);
      results = results.filter(p => cleanForSearch(p.club).includes(cleanClub));
    }

    if (params.minOverall !== undefined) {
      results = results.filter(p => p.overall >= params.minOverall!);
    }

    return results.sort((a, b) => b.overall - a.overall).slice(0, 50);
  }

  public getHeadToHead(team1: string, team2: string, season?: string, competition?: string): HeadToHead {
    const cleanTeam1 = cleanForSearch(team1);
    const cleanTeam2 = cleanForSearch(team2);
    
    let matches = this.matches.filter(m => 
      (m.homeTeamClean.includes(cleanTeam1) && m.awayTeamClean.includes(cleanTeam2)) ||
      (m.homeTeamClean.includes(cleanTeam2) && m.awayTeamClean.includes(cleanTeam1))
    );

    if (season) {
      matches = matches.filter(m => m.season === season);
    }
    if (competition) {
      const cleanComp = competition.toLowerCase();
      matches = matches.filter(m => m.competition.toLowerCase().includes(cleanComp));
    }

    let team1Wins = 0;
    let team2Wins = 0;
    let draws = 0;

    for (const m of matches) {
      const isTeam1Home = m.homeTeamClean.includes(cleanTeam1);
      const team1Goals = isTeam1Home ? m.homeGoals : m.awayGoals;
      const team2Goals = isTeam1Home ? m.awayGoals : m.homeGoals;

      if (team1Goals > team2Goals) team1Wins++;
      else if (team1Goals < team2Goals) team2Wins++;
      else draws++;
    }

    return {
      team1,
      team2,
      matches: matches.length,
      team1Wins,
      team2Wins,
      draws,
      recentMatches: matches.slice(-10).reverse(),
    };
  }

  public getCompetitionStandings(competition: string, season: string): StandingRow[] {
    const cleanComp = competition.toLowerCase();
    const matches = this.matches.filter(m => 
      m.competition.toLowerCase().includes(cleanComp) && m.season === season
    );

    const standingsMap = new Map<string, StandingRow>();

    for (const m of matches) {
      if (!standingsMap.has(m.homeTeam)) {
        standingsMap.set(m.homeTeam, { team: m.homeTeam, points: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 });
      }
      if (!standingsMap.has(m.awayTeam)) {
        standingsMap.set(m.awayTeam, { team: m.awayTeam, points: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 });
      }

      const home = standingsMap.get(m.homeTeam)!;
      const away = standingsMap.get(m.awayTeam)!;

      home.goalsFor += m.homeGoals;
      home.goalsAgainst += m.awayGoals;
      away.goalsFor += m.awayGoals;
      away.goalsAgainst += m.homeGoals;

      if (m.homeGoals > m.awayGoals) {
        home.wins++;
        home.points += 3;
        away.losses++;
      } else if (m.homeGoals < m.awayGoals) {
        away.wins++;
        away.points += 3;
        home.losses++;
      } else {
        home.draws++;
        home.points += 1;
        away.draws++;
        away.points += 1;
      }
    }

    return Array.from(standingsMap.values())
      .sort((a, b) => {
        if (b.points !== a.points) return b.points - a.points;
        const gdA = a.goalsFor - a.goalsAgainst;
        const gdB = b.goalsFor - b.goalsAgainst;
        if (gdB !== gdA) return gdB - gdA;
        return b.goalsFor - a.goalsFor;
      });
  }
}
