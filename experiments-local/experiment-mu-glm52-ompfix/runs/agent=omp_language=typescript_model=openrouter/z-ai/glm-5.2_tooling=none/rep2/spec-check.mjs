import { loadAll } from "./dist/loader.js";
import { queryMatches, headToHead, standings, queryPlayers } from "./dist/queries.js";

const ds = loadAll();

const pal = queryMatches(ds, { team: "Palmeiras", limit: 1000 });
const comps = [...new Set(pal.map(m => m.competition))].sort();
console.log("Palmeiras competitions:", comps);

const h2h = headToHead(ds, "Flamengo", "Fluminense");
console.log("Fla-Flu H2H:", JSON.stringify(h2h));

const table2019 = standings(ds, { competition: "Brasileirão", season: 2019 });
console.log("2019 Brasileirão top 3:");
table2019.slice(0,3).forEach(r => console.log(`  ${r.position}. ${r.teamDisplay} - ${r.points} pts (${r.wins}W ${r.draws}D ${r.losses}L)`));

const gab = queryPlayers(ds, { name: "Gabriel Barbosa" });
console.log("Gabriel Barbosa:", gab.length ? `${gab[0].name} ${gab[0].overall} OVR ${gab[0].club}` : "not found");

const flaBr = queryPlayers(ds, { nationality: "Brazil", club: "Flamengo", sortBy: "overall", limit: 5 });
console.log("Brazilian players at Flamengo:", flaBr.map(p => `${p.name}(${p.overall})`).join(", "));
