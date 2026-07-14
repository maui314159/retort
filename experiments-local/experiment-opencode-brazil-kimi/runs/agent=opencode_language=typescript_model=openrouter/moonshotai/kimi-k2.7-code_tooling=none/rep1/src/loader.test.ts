/*
 * Brazilian Soccer MCP Server - Data loader integration tests
 */

import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { loadDataset } from './loader.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DATA_DIR = resolve(__dirname, '..', 'data', 'kaggle');

describe('DataLoader', () => {
  it('loads all six CSV files without errors', async () => {
    const store = await loadDataset(DATA_DIR);
    expect(store.matches.length).toBeGreaterThan(0);
    expect(store.players.length).toBeGreaterThan(0);
    expect(store.extendedStats.length).toBeGreaterThan(0);
  });

  it('loads at least the expected number of matches across all files', async () => {
    const store = await loadDataset(DATA_DIR);
    expect(store.matches.length).toBeGreaterThanOrEqual(15_000);
  });

  it('loads at least the expected number of players', async () => {
    const store = await loadDataset(DATA_DIR);
    expect(store.players.length).toBeGreaterThanOrEqual(18_000);
  });

  it('normalizes team names during loading', async () => {
    const store = await loadDataset(DATA_DIR);
    const palmeirasMatches = store.matches.filter(
      (m) => m.homeTeam === 'Palmeiras' || m.awayTeam === 'Palmeiras'
    );
    expect(palmeirasMatches.length).toBeGreaterThan(0);
  });

  it('parses ISO and Brazilian date formats', async () => {
    const store = await loadDataset(DATA_DIR);
    const historical = store.matches.filter(
      (m) => m.source === 'novo_campeonato_brasileiro.csv' && m.date === '2003-03-29'
    );
    expect(historical.length).toBeGreaterThan(0);
  });
});
