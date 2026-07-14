import { loadData } from "./dataLoader.js";
import { normalizeTeamName, parseDate } from "./utils.js";

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`ASSERTION FAILED: ${message}`);
  }
}

async function runTests() {
  console.log("Running Brazilian Soccer MCP Tests...");

  // Test 1: Data Loading
  console.log("Test 1: Data Loading");
  const data = loadData();
  assert(data.brasileiraoMatches.length > 0, "Brasileirão matches should be loaded");
  assert(data.cupMatches.length > 0, "Cup matches should be loaded");
  assert(data.libertadoresMatches.length > 0, "Libertadores matches should be loaded");
  assert(data.brFootballMatches.length > 0, "BR Football matches should be loaded");
  assert(data.novoCampeonatoMatches.length > 0, "Novo Campeonato matches should be loaded");
  assert(data.fifaPlayers.length > 0, "FIFA players should be loaded");
  console.log("  ✓ All datasets loaded successfully");

  // Test 2: Normalize Team Names
  console.log("Test 2: Normalize Team Names");
  assert(normalizeTeamName("Palmeiras-SP") === "palmeiras", "Should remove state suffix");
  assert(normalizeTeamName("São Paulo") === "sao paulo", "Should remove accents");
  assert(normalizeTeamName("Sport Club Corinthians Paulista") === "corinthians paulista", "Should handle full names");
  console.log("  ✓ Team name normalization works correctly");

  // Test 3: Parse Dates
  console.log("Test 3: Parse Dates");
  const date1 = parseDate("29/03/2003");
  assert(date1 !== null && date1.getFullYear() === 2003, "Should parse DD/MM/YYYY format");
  const date2 = parseDate("2012-05-19 18:30:00");
  assert(date2 !== null && date2.getFullYear() === 2012, "Should parse ISO format with time");
  console.log("  ✓ Date parsing works correctly");

  // Test 4: Head-to-Head Query Simulation
  console.log("Test 4: Head-to-Head Query Simulation");
  const allMatches = [
    ...data.brasileiraoMatches,
    ...data.cupMatches,
    ...data.libertadoresMatches,
    ...data.brFootballMatches,
    ...data.novoCampeonatoMatches,
  ];
  const normFlamengo = normalizeTeamName("Flamengo");
  const normFluminense = normalizeTeamName("Fluminense");
  const flaFluMatches = allMatches.filter((match) => {
    let home = "";
    let away = "";
    if ("home_team" in match) { home = normalizeTeamName(match.home_team); away = normalizeTeamName(match.away_team); }
    else if ("home" in match) { home = normalizeTeamName(match.home); away = normalizeTeamName(match.away); }
    else { home = normalizeTeamName(match.Equipe_mandante); away = normalizeTeamName(match.Equipe_visitante); }
    return (home.includes(normFlamengo) || away.includes(normFlamengo)) &&
           (home.includes(normFluminense) || away.includes(normFluminense));
  });
  assert(flaFluMatches.length > 0, "Should find Fla-Flu matches");
  console.log(`  ✓ Found ${flaFluMatches.length} Fla-Flu matches`);

  // Test 5: Player Search Simulation
  console.log("Test 5: Player Search Simulation");
  const brazilianPlayers = data.fifaPlayers.filter((p) => normalizeTeamName(p.Nationality).includes("brazil"));
  assert(brazilianPlayers.length > 0, "Should find Brazilian players");
  assert(brazilianPlayers.some((p) => normalizeTeamName(p.Name).includes("neymar")), "Should find Neymar");
  console.log(`  ✓ Found ${brazilianPlayers.length} Brazilian players, including Neymar`);

  // Test 6: Competition Standings Simulation
  console.log("Test 6: Competition Standings Simulation");
  const normalizedBrasileirao = normalizeTeamName("Brasileirão");
  const serieAMatches2012 = allMatches.filter((m) => {
    const matchSeason = "season" in m ? m.season : "Ano" in m ? m.Ano : undefined;
    return normalizeTeamName(m.competition).includes(normalizedBrasileirao) && matchSeason === 2012;
  });
  assert(serieAMatches2012.length > 0, "Should find 2012 Brasileirão matches");
  console.log(`  ✓ Found ${serieAMatches2012.length} 2012 Brasileirão matches for standings calculation`);

  console.log("\n✅ All tests passed!");
}

runTests().catch((error) => {
  console.error("\n❌ Test failed:", error);
  process.exit(1);
});
