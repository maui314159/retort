import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { loadData } from "./dataLoader.js";
import { normalizeTeamName, parseDate } from "./utils.js";
import { Match, TeamStats, HeadToHead } from "./types.js";

export function registerTools(server: McpServer) {
  server.tool(
    "search_matches",
    "Search for matches by team, competition, season, or date range.",
    {
      team: z.string().optional().describe("Team name to search for (home or away)"),
      competition: z.string().optional().describe("Competition name (e.g., Brasileirão, Copa do Brasil, Libertadores)"),
      season: z.number().optional().describe("Year of the season"),
      startDate: z.string().optional().describe("Start date in YYYY-MM-DD format"),
      endDate: z.string().optional().describe("End date in YYYY-MM-DD format"),
      limit: z.number().optional().default(50).describe("Maximum number of results to return"),
    },
    async ({ team, competition, season, startDate, endDate, limit }) => {
      const data = loadData();
      const allMatches: Match[] = [
        ...data.brasileiraoMatches,
        ...data.cupMatches,
        ...data.libertadoresMatches,
        ...data.brFootballMatches,
        ...data.novoCampeonatoMatches,
      ];

      let results = allMatches;

      if (team) {
        const normalizedTeam = normalizeTeamName(team);
        results = results.filter((match) => {
          const home = normalizeTeamName("home_team" in match ? match.home_team : "home" in match ? match.home : "Equipe_mandante" in match ? match.Equipe_mandante : "");
          const away = normalizeTeamName("away_team" in match ? match.away_team : "away" in match ? match.away : "Equipe_visitante" in match ? match.Equipe_visitante : "");
          return home.includes(normalizedTeam) || away.includes(normalizedTeam);
        });
      }

      if (competition) {
        const normalizedComp = normalizeTeamName(competition);
        results = results.filter((match) => normalizeTeamName(match.competition).includes(normalizedComp));
      }

      if (season) {
        results = results.filter((match) => {
          const matchSeason = "season" in match ? match.season : "Ano" in match ? match.Ano : undefined;
          return matchSeason === season;
        });
      }

      if (startDate || endDate) {
        const start = startDate ? parseDate(startDate) : null;
        const end = endDate ? parseDate(endDate) : null;

        results = results.filter((match) => {
          const dateStr = "datetime" in match ? match.datetime : "date" in match ? match.date : "Data" in match ? match.Data : "";
          const matchDate = parseDate(dateStr);
          if (!matchDate) return false;
          if (start && matchDate < start) return false;
          if (end && matchDate > end) return false;
          return true;
        });
      }

      // Sort by date descending
      results.sort((a, b) => {
        const dateA = parseDate("datetime" in a ? a.datetime : "date" in a ? a.date : "Data" in a ? a.Data : "")?.getTime() || 0;
        const dateB = parseDate("datetime" in b ? b.datetime : "date" in b ? b.date : "Data" in b ? b.Data : "")?.getTime() || 0;
        return dateB - dateA;
      });

      const limited = results.slice(0, limit);

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              totalMatches: results.length,
              returnedMatches: limited.length,
              matches: limited.map((m) => {
                if ("home_team" in m) {
                  return {
                    date: m.datetime,
                    homeTeam: m.home_team,
                    awayTeam: m.away_team,
                    homeGoal: m.home_goal,
                    awayGoal: m.away_goal,
                    competition: m.competition,
                    season: "season" in m ? m.season : undefined,
                  };
                }
                if ("home" in m) {
                  return {
                    date: `${m.date} ${m.time}`,
                    homeTeam: m.home,
                    awayTeam: m.away,
                    homeGoal: m.home_goal,
                    awayGoal: m.away_goal,
                    competition: m.competition,
                  };
                }
                return {
                  date: m.Data,
                  homeTeam: m.Equipe_mandante,
                  awayTeam: m.Equipe_visitante,
                  homeGoal: m.Gols_mandante,
                  awayGoal: m.Gols_visitante,
                  competition: m.competition,
                  season: m.Ano,
                };
              }),
            }, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "get_team_statistics",
    "Get win/loss/draw records and goals for/against for a specific team, optionally filtered by season or competition.",
    {
      team: z.string().describe("Team name to get statistics for"),
      season: z.number().optional().describe("Year of the season"),
      competition: z.string().optional().describe("Competition name"),
    },
    async ({ team, season, competition }) => {
      const data = loadData();
      const allMatches: Match[] = [
        ...data.brasileiraoMatches,
        ...data.cupMatches,
        ...data.libertadoresMatches,
        ...data.brFootballMatches,
        ...data.novoCampeonatoMatches,
      ];

      const normalizedTeam = normalizeTeamName(team);
      let matches = allMatches.filter((match) => {
        const home = normalizeTeamName("home_team" in match ? match.home_team : "home" in match ? match.home : "Equipe_mandante" in match ? match.Equipe_mandante : "");
        const away = normalizeTeamName("away_team" in match ? match.away_team : "away" in match ? match.away : "Equipe_visitante" in match ? match.Equipe_visitante : "");
        return home.includes(normalizedTeam) || away.includes(normalizedTeam);
      });

      if (season) {
        matches = matches.filter((match) => {
          const matchSeason = "season" in match ? match.season : "Ano" in match ? match.Ano : undefined;
          return matchSeason === season;
        });
      }

      if (competition) {
        const normalizedComp = normalizeTeamName(competition);
        matches = matches.filter((match) => normalizeTeamName(match.competition).includes(normalizedComp));
      }

      let wins = 0;
      let draws = 0;
      let losses = 0;
      let goalsFor = 0;
      let goalsAgainst = 0;

      for (const match of matches) {
        let isHome = false;
        let homeGoals = 0;
        let awayGoals = 0;

        if ("home_team" in match) {
          isHome = normalizeTeamName(match.home_team).includes(normalizedTeam);
          homeGoals = match.home_goal;
          awayGoals = match.away_goal;
        } else if ("home" in match) {
          isHome = normalizeTeamName(match.home).includes(normalizedTeam);
          homeGoals = match.home_goal;
          awayGoals = match.away_goal;
        } else {
          isHome = normalizeTeamName(match.Equipe_mandante).includes(normalizedTeam);
          homeGoals = match.Gols_mandante;
          awayGoals = match.Gols_visitante;
        }

        if (isHome) {
          goalsFor += homeGoals;
          goalsAgainst += awayGoals;
          if (homeGoals > awayGoals) wins++;
          else if (homeGoals === awayGoals) draws++;
          else losses++;
        } else {
          goalsFor += awayGoals;
          goalsAgainst += homeGoals;
          if (awayGoals > homeGoals) wins++;
          else if (awayGoals === homeGoals) draws++;
          else losses++;
        }
      }

      const winRate = matches.length > 0 ? ((wins / matches.length) * 100).toFixed(1) : "0.0";

      const stats: TeamStats = {
        team,
        season,
        competition,
        matches: matches.length,
        wins,
        draws,
        losses,
        goalsFor,
        goalsAgainst,
        winRate: parseFloat(winRate),
      };

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(stats, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "search_players",
    "Search for players by name, nationality, club, or position, and filter by minimum overall rating.",
    {
      name: z.string().optional().describe("Player name or part of the name"),
      nationality: z.string().optional().describe("Player nationality (e.g., 'Brazil')"),
      club: z.string().optional().describe("Club name"),
      position: z.string().optional().describe("Playing position (e.g., 'ST', 'GK')"),
      minOverall: z.number().optional().describe("Minimum overall rating"),
      limit: z.number().optional().default(50).describe("Maximum number of results to return"),
    },
    async ({ name, nationality, club, position, minOverall, limit }) => {
      const data = loadData();
      let players = data.fifaPlayers;

      if (name) {
        const normalizedName = normalizeTeamName(name);
        players = players.filter((p) => normalizeTeamName(p.Name).includes(normalizedName));
      }

      if (nationality) {
        const normalizedNat = normalizeTeamName(nationality);
        players = players.filter((p) => normalizeTeamName(p.Nationality).includes(normalizedNat));
      }

      if (club) {
        const normalizedClub = normalizeTeamName(club);
        players = players.filter((p) => normalizeTeamName(p.Club).includes(normalizedClub));
      }

      if (position) {
        const normalizedPos = normalizeTeamName(position);
        players = players.filter((p) => normalizeTeamName(p.Position).includes(normalizedPos));
      }

      if (minOverall !== undefined) {
        players = players.filter((p) => p.Overall >= minOverall);
      }

      players.sort((a, b) => b.Overall - a.Overall);
      const limited = players.slice(0, limit);

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              totalPlayers: players.length,
              returnedPlayers: limited.length,
              players: limited.map((p) => ({
                name: p.Name,
                age: p.Age,
                nationality: p.Nationality,
                club: p.Club,
                position: p.Position,
                overall: p.Overall,
                potential: p.Potential,
              })),
            }, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "get_head_to_head",
    "Get head-to-head match history and statistics between two specific teams.",
    {
      team1: z.string().describe("First team name"),
      team2: z.string().describe("Second team name"),
      limit: z.number().optional().default(20).describe("Maximum number of matches to return"),
    },
    async ({ team1, team2, limit }) => {
      const data = loadData();
      const allMatches: Match[] = [
        ...data.brasileiraoMatches,
        ...data.cupMatches,
        ...data.libertadoresMatches,
        ...data.brFootballMatches,
        ...data.novoCampeonatoMatches,
      ];

      const normTeam1 = normalizeTeamName(team1);
      const normTeam2 = normalizeTeamName(team2);

      const matches = allMatches.filter((match) => {
        let home = "";
        let away = "";
        if ("home_team" in match) {
          home = normalizeTeamName(match.home_team);
          away = normalizeTeamName(match.away_team);
        } else if ("home" in match) {
          home = normalizeTeamName(match.home);
          away = normalizeTeamName(match.away);
        } else {
          home = normalizeTeamName(match.Equipe_mandante);
          away = normalizeTeamName(match.Equipe_visitante);
        }

        const hasTeam1 = home.includes(normTeam1) || away.includes(normTeam1);
        const hasTeam2 = home.includes(normTeam2) || away.includes(normTeam2);
        return hasTeam1 && hasTeam2;
      });

      let team1Wins = 0;
      let team2Wins = 0;
      let draws = 0;

      for (const match of matches) {
        let homeGoals = 0;
        let awayGoals = 0;
        let homeTeamNorm = "";
        let awayTeamNorm = "";

        if ("home_team" in match) {
          homeGoals = match.home_goal;
          awayGoals = match.away_goal;
          homeTeamNorm = normalizeTeamName(match.home_team);
          awayTeamNorm = normalizeTeamName(match.away_team);
        } else if ("home" in match) {
          homeGoals = match.home_goal;
          awayGoals = match.away_goal;
          homeTeamNorm = normalizeTeamName(match.home);
          awayTeamNorm = normalizeTeamName(match.away);
        } else {
          homeGoals = match.Gols_mandante;
          awayGoals = match.Gols_visitante;
          homeTeamNorm = normalizeTeamName(match.Equipe_mandante);
          awayTeamNorm = normalizeTeamName(match.Equipe_visitante);
        }

        const isTeam1Home = homeTeamNorm.includes(normTeam1);
        if (homeGoals > awayGoals) {
          if (isTeam1Home) team1Wins++;
          else team2Wins++;
        } else if (awayGoals > homeGoals) {
          if (isTeam1Home) team2Wins++;
          else team1Wins++;
        } else {
          draws++;
        }
      }

      matches.sort((a, b) => {
        const dateA = parseDate("datetime" in a ? a.datetime : "date" in a ? a.date : "Data" in a ? a.Data : "")?.getTime() || 0;
        const dateB = parseDate("datetime" in b ? b.datetime : "date" in b ? b.date : "Data" in b ? b.Data : "")?.getTime() || 0;
        return dateB - dateA;
      });

      const limited = matches.slice(0, limit);

      const h2h: HeadToHead = {
        team1,
        team2,
        team1Wins,
        team2Wins,
        draws,
        matches: limited.map((m) => {
          if ("home_team" in m) {
            return { date: m.datetime, homeTeam: m.home_team, awayTeam: m.away_team, homeGoal: m.home_goal, awayGoal: m.away_goal, competition: m.competition };
          }
          if ("home" in m) {
            return { date: `${m.date} ${m.time}`, homeTeam: m.home, awayTeam: m.away, homeGoal: m.home_goal, awayGoal: m.away_goal, competition: m.competition };
          }
          return { date: m.Data, homeTeam: m.Equipe_mandante, awayTeam: m.Equipe_visitante, homeGoal: m.Gols_mandante, awayGoal: m.Gols_visitante, competition: m.competition, season: m.Ano };
        }),
      };

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(h2h, null, 2),
          },
        ],
      };
    }
  );
  server.tool(
    "get_competition_standings",
    "Calculate and return league standings for a specific competition and season based on match results.",
    {
      competition: z.string().describe("Competition name (e.g., 'Brasileirão', 'Copa do Brasil')"),
      season: z.number().describe("Year of the season"),
    },
    async ({ competition, season }) => {
      const data = loadData();
      const allMatches: Match[] = [
        ...data.brasileiraoMatches,
        ...data.cupMatches,
        ...data.libertadoresMatches,
        ...data.brFootballMatches,
        ...data.novoCampeonatoMatches,
      ];

      const normalizedComp = normalizeTeamName(competition);
      const matches = allMatches.filter((m) => {
        const matchSeason = "season" in m ? m.season : "Ano" in m ? m.Ano : undefined;
        return normalizeTeamName(m.competition).includes(normalizedComp) && matchSeason === season;
      });

      interface Standing {
        team: string;
        matches: number;
        wins: number;
        draws: number;
        losses: number;
        goalsFor: number;
        goalsAgainst: number;
        goalDifference: number;
        points: number;
      }

      const standingsMap = new Map<string, Standing>();

      const getOrCreate = (teamName: string): Standing => {
        if (!standingsMap.has(teamName)) {
          standingsMap.set(teamName, { team: teamName, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0 });
        }
        return standingsMap.get(teamName)!;
      };

      for (const match of matches) {
        let homeTeam = "";
        let awayTeam = "";
        let homeGoals = 0;
        let awayGoals = 0;

        if ("home_team" in match) {
          homeTeam = match.home_team;
          awayTeam = match.away_team;
          homeGoals = match.home_goal;
          awayGoals = match.away_goal;
        } else if ("home" in match) {
          homeTeam = match.home;
          awayTeam = match.away;
          homeGoals = match.home_goal;
          awayGoals = match.away_goal;
        } else {
          homeTeam = match.Equipe_mandante;
          awayTeam = match.Equipe_visitante;
          homeGoals = match.Gols_mandante;
          awayGoals = match.Gols_visitante;
        }

        const home = getOrCreate(homeTeam);
        const away = getOrCreate(awayTeam);

        home.matches++;
        away.matches++;
        home.goalsFor += homeGoals;
        home.goalsAgainst += awayGoals;
        away.goalsFor += awayGoals;
        away.goalsAgainst += homeGoals;

        if (homeGoals > awayGoals) {
          home.wins++;
          home.points += 3;
          away.losses++;
        } else if (awayGoals > homeGoals) {
          away.wins++;
          away.points += 3;
          home.losses++;
        } else {
          home.draws++;
          away.draws++;
          home.points += 1;
          away.points += 1;
        }
      }

      const finalStandings = Array.from(standingsMap.values()).map((s) => ({
        ...s,
        goalDifference: s.goalsFor - s.goalsAgainst,
      }));

      finalStandings.sort((a, b) => {
        if (b.points !== a.points) return b.points - a.points;
        if (b.goalDifference !== a.goalDifference) return b.goalDifference - a.goalDifference;
        return b.goalsFor - a.goalsFor;
      });

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({ competition, season, standings: finalStandings }, null, 2),
          },
        ],
      };
    }
  );
}
