/**
 * Quick smoke test for the data loader. Run with:
 *   npx tsx scripts/smoke.ts
 * (or use `node --import tsx scripts/smoke.ts`).
 */
import { loadDataset } from '../src/data/loader.js';

const snap = loadDataset();
console.log('matches:', snap.matches.length);
console.log('players:', snap.players.length);
console.log('teams:', snap.teams.length);
console.log('first 3 teams:', snap.teams.slice(0, 3));
console.log('Flamengo alias:', snap.teamAliases.get('Flamengo'));
console.log('Sample Brasileirao match:', snap.matches.find(m => m.competition === 'brasileirao' && m.season === 2022 && m.homeTeam === 'Flamengo'));
console.log('Sample historical match:', snap.matches.find(m => m.competition === 'brasileirao_historical' && m.season === 2019));
console.log('Sample BR Football match:', snap.matches.find(m => m.competition === 'libertadores' && m.homeTeam === 'Flamengo'));
