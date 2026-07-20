import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const transport = new StdioClientTransport({
  command: 'node',
  args: ['/Users/maui/.retort/work/retort-local-_9x4xpns/retort-daa82c57fce7/dist/index.js'],
});
const client = new Client({ name: 'e2e-client', version: '1.0.0' });
const t0 = Date.now();
await client.connect(transport);
console.log('connect+load ms:', Date.now() - t0);

const { tools } = await client.listTools();
console.log('tools:', tools.length);

async function timed(name, args) {
  const t = Date.now();
  const r = await client.callTool({ name, arguments: args });
  const ms = Date.now() - t;
  console.log(`--- ${name} (${ms}ms)`);
  console.log(r.content[0].text.split('\n').slice(0, 6).join('\n'));
  return ms;
}

const t1 = await timed('search_matches', { team: 'Flamengo', opponent: 'Fluminense', limit: 5 });
const t2 = await timed('head_to_head', { team_a: 'Palmeiras', team_b: 'Santos' });
const t3 = await timed('competition_standings', { competition: 'Brasileirão', season: 2019 });
const t4 = await timed('search_players', { nationality: 'Brazil', club: 'Santos', position: 'forward' });
const t5 = await timed('biggest_wins', {});
console.log('PERF', JSON.stringify({ lookup: t1, h2h: t2, standings: t3, players: t4, biggest: t5 }));
await client.close();
process.exit(0);
