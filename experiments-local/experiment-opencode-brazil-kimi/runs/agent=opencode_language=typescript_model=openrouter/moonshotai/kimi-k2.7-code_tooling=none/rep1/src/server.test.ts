/*
 * Brazilian Soccer MCP Server - MCP server smoke tests
 *
 * Verifies the server exposes tools and responds to calls using the SDK's
 * in-memory transport, avoiding the need to spawn a stdio subprocess.
 */

import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { loadDataset } from './loader.js';
import { QueryEngine } from './engine.js';
import { createServer } from './server.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DATA_DIR = resolve(__dirname, '..', 'data', 'kaggle');

describe('MCP Server', () => {
  let client: Client;

  beforeAll(async () => {
    const store = await loadDataset(DATA_DIR);
    const engine = new QueryEngine(store);
    const server = createServer(engine);

    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    const clientInstance = new Client({ name: 'test-client', version: '1.0.0' });

    await server.connect(serverTransport);
    await clientInstance.connect(clientTransport);

    client = clientInstance;
  });

  afterAll(async () => {
    await client.close();
  });

  it('lists the expected tools', async () => {
    const tools = await client.listTools();
    const names = tools.tools.map((t) => t.name).sort();
    expect(names).toEqual(
      [
        'search_matches',
        'get_team_record',
        'get_head_to_head',
        'search_players',
        'get_standings',
        'get_statistics',
        'list_metadata',
        'player_clubs_summary'
      ].sort()
    );
  });

  it('returns Flamengo vs Fluminense matches', async () => {
    const result = await client.callTool({
      name: 'search_matches',
      arguments: { teamA: 'Flamengo', teamB: 'Fluminense' }
    });
    const text = extractText(result);
    expect(text).toContain('Flamengo vs Fluminense');
    expect(text).toContain('wins');
  });

  it('returns 2019 Brasileirão standings with Flamengo champion', async () => {
    const result = await client.callTool({
      name: 'get_standings',
      arguments: { competition: 'Brasileirão', season: 2019 }
    });
    const text = extractText(result);
    expect(text).toContain('Flamengo');
    expect(text).toContain('Champion');
  });

  it('returns Brazilian players', async () => {
    const result = await client.callTool({
      name: 'search_players',
      arguments: { nationality: 'Brazil', limit: 5 }
    });
    const text = extractText(result);
    expect(text).toContain('Brazil');
    expect(text.split('\n').length).toBeGreaterThan(1);
  });
});

function extractText(result: unknown): string {
  const content = (result as { content?: Array<{ type: string; text: string }> }).content;
  return content?.find((c) => c.type === 'text')?.text ?? '';
}
