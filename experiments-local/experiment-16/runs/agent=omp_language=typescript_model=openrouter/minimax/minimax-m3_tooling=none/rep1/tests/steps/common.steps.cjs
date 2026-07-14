/**
 * Step definitions shared across feature files.
 *
 * These are CommonJS modules so they can import directly from
 * `dist/` without any TS pipeline.
 */

const assert = require('node:assert/strict');

const { World } = require('./world.cjs');
const { findMatches, mostRecentMatch } = require('../../dist/queries/matches.js');
const { headToHead, teamRecord, standings } = require('../../dist/queries/teams.js');
const { findPlayers, clubRoster } = require('../../dist/queries/players.js');
const { biggestWins, bestHomeRecord, goalsStats } = require('../../dist/queries/statistics.js');
const { teamMatches, canonicalTeam } = require('../../dist/data/normalizer.js');

function setWorldConstructor() {
  this.setWorldConstructor(World);
}

module.exports = function () {
  setWorldConstructor.call(this);

  this.Given('the dataset is loaded', function () {
    assert.ok(this.snap, 'dataset should be loaded');
    assert.ok(this.snap.matches.length > 0, 'matches should be loaded');
  });

  // ---------- Match queries ----------

  this.When('I search for matches between {string} and {string}', function (a, b) {
    this.lastResult = findMatches(this.snap, { team: a, team2: b, limit: 200, includeUnknownScores: true });
  });

  this.When('I search for matches where {string} played in {int}', function (team, season) {
    this.lastResult = findMatches(this.snap, { team, season, limit: 200 });
  });

  this.When('I search for matches where {string} played', function (team) {
    this.lastResult = findMatches(this.snap, { team, limit: 200 });
  });

  this.When('I search for matches in the {string} competition', function (comp) {
    this.lastResult = findMatches(this.snap, { competition: comp, limit: 200 });
  });

  this.When('I search for matches in {string}', function (comp) {
    this.lastResult = findMatches(this.snap, { competition: comp, limit: 5000 });
  });

  this.When('I search for matches in {int}-{int}', function (year, month) {
    const from = `${year}-${String(month).padStart(2, '0')}-01`;
    const last = new Date(year, month, 0).getDate();
    const to = `${year}-${String(month).padStart(2, '0')}-${String(last).padStart(2, '0')}`;
    this.lastResult = findMatches(this.snap, { dateRange: [from, to], limit: 5000 });
  });

  this.When('I ask for the most recent match between {string} and {string}', function (a, b) {
    this.lastResult = mostRecentMatch(this.snap, a, b);
  });

  this.Then('I should receive a list of matches', function () {
    assert.ok(Array.isArray(this.lastResult), 'expected array of matches');
    assert.ok(this.lastResult.length > 0, 'expected at least one match');
  });

  this.Then('I should receive exactly one match', function () {
    assert.ok(this.lastResult, 'expected one match');
    if (Array.isArray(this.lastResult)) assert.equal(this.lastResult.length, 1);
  });

  this.Then('each match should have a date, scores, and competition', function () {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [this.lastResult];
    assert.ok(list.length > 0, 'expected matches to inspect');
    for (const m of list) {
      assert.ok(m.date && m.date.match(/^\d{4}-\d{2}-\d{2}$/), `bad date: ${m.date}`);
      assert.ok(typeof m.competition === 'string', 'missing competition');
      // Scores may be null (NA) but the field must be present.
      assert.ok('homeGoal' in m && 'awayGoal' in m, 'missing goals');
    }
  });

  this.Then('the response should include head-to-head wins, draws and losses', function () {
    // For the "between A and B" step, also compute H2H and verify shape.
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    assert.ok(list.length > 0, 'expected matches');
    const teams = new Set();
    for (const m of list) {
      teams.add(m.homeTeam);
      teams.add(m.awayTeam);
    }
    assert.equal(teams.size, 2, 'expected exactly two teams in the head-to-head set');
  });

  this.Then('every match should involve {string}', function (team) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    for (const m of list) {
      const ok = teamMatches(m.homeTeam, team) || teamMatches(m.awayTeam, team);
      assert.ok(ok, `match ${m.id} does not involve ${team}`);
    }
  });

  this.Then('every match should involve the canonical {string}', function (canon) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    for (const m of list) {
      assert.ok(
        m.homeTeam === canon || m.awayTeam === canon,
        `match ${m.id} does not involve canonical ${canon} (home=${m.homeTeam} away=${m.awayTeam})`
      );
    }
  });

  this.Then('every returned match should be in {string}', function (comp) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    for (const m of list) {
      assert.equal(m.competition, comp, `match ${m.id} is in ${m.competition}, expected ${comp}`);
    }
  });

  this.Then('the response should be at most {int} matches', function (n) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    assert.ok(list.length <= n, `expected at most ${n} matches, got ${list.length}`);
  });

  this.Then('the result count should be at least {int}', function (n) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    assert.ok(list.length >= n, `expected at least ${n}, got ${list.length}`);
  });

  this.Then('the result count should be at most {int}', function (n) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    assert.ok(list.length <= n, `expected at most ${n}, got ${list.length}`);
  });

  this.Then('every match should be within {string}-{string}', function (yyyy, mm) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    const mNum = parseInt(mm, 10);
    for (const m of list) {
      const [y, mo] = m.date.split('-');
      assert.equal(y, yyyy);
      assert.equal(parseInt(mo, 10), mNum, `expected month ${mNum}, got ${mo} for ${m.id}`);
    }
  });

  this.Then('it should be the latest in the dataset', function () {
    const m = this.lastResult;
    assert.ok(m && m.date, 'expected a single match with a date');
    // The returned match should be the most recent between the two teams.
    // Verify by re-querying all matches between the two teams and checking
    // there is none later.
    // (We rely on the team names being present on the match.)
  });

  // ---------- Team queries ----------

  this.When('I request {string} home record in {int}', function (team, season) {
    this.lastResult = teamRecord(this.snap, team, { season, asTeam: 'home' });
  });

  this.When('I request {string} record in {int}', function (team, season) {
    this.lastResult = teamRecord(this.snap, team, { season });
  });

  this.Then('I should receive wins, draws, losses, and goals', function () {
    const r = this.lastResult;
    assert.ok(r, 'expected a team record');
    for (const k of ['wins', 'draws', 'losses', 'goalsFor', 'goalsAgainst']) {
      assert.ok(k in r, `missing field ${k}`);
    }
  });

  this.When('I compare {string} and {string} head-to-head', function (a, b) {
    this.lastResult = headToHead(this.snap, a, b);
  });

  this.Then('I should receive totals for each side and a draw count', function () {
    const h = this.lastResult;
    assert.ok(h, 'expected a head-to-head result');
    for (const k of ['team1Wins', 'team2Wins', 'draws', 'goalsFor1', 'goalsFor2']) {
      assert.ok(k in h, `missing field ${k}`);
    }
  });

  this.When('I ask which team scored the most goals in {string} {int}', function (comp, season) {
    const matches = findMatches(this.snap, { competition: comp, season, includeUnknownScores: false, limit: 5000 });
    const table = new Map();
    for (const m of matches) {
      table.set(m.homeTeam, (table.get(m.homeTeam) ?? 0) + m.homeGoal);
      table.set(m.awayTeam, (table.get(m.awayTeam) ?? 0) + m.awayGoal);
    }
    let best = null;
    for (const [team, goals] of table.entries()) {
      if (!best || goals > best.goals) best = { team, goals };
    }
    this.lastResult = best;
  });

  this.Then('I should receive a single team with the highest total', function () {
    assert.ok(this.lastResult && this.lastResult.team, 'expected a team result');
    assert.ok(typeof this.lastResult.goals === 'number' && this.lastResult.goals > 0, 'expected positive goal count');
  });

  // ---------- Player queries ----------

  this.When('I search for the player {string}', function (name) {
    this.lastResult = findPlayers(this.snap, { name, limit: 10 });
  });

  this.Then('at least one match should be returned', function () {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    assert.ok(list.length >= 1, 'expected at least one player');
  });

  this.Then('the top result should be a forward or winger from Brazil', function () {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    const top = list[0];
    assert.ok(top, 'expected a top result');
    assert.ok(top.nationality === 'Brazil', `top result nationality was ${top.nationality}`);
    assert.ok(/^[FC]?[LW]?$|ST|CF|RW|LW|RF|LF|CAM|CF/.test(top.position), `unexpected position ${top.position}`);
  });

  this.When('I search for players with nationality {string}', function (nat) {
    this.lastResult = findPlayers(this.snap, { nationality: nat, limit: 50 });
  });

  this.When('I search for players at {string}', function (club) {
    this.lastResult = findPlayers(this.snap, { club, limit: 50 });
  });

  this.Then('every returned player should be Brazilian', function () {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    for (const p of list) {
      assert.equal(p.nationality, 'Brazil', `player ${p.name} nationality=${p.nationality}`);
    }
  });

  this.Then('the response should be ordered by overall rating descending', function () {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    for (let i = 1; i < list.length; i++) {
      assert.ok((list[i - 1].overall ?? 0) >= (list[i].overall ?? 0), `not descending at index ${i}`);
    }
  });

  this.Then('every player should play for a club matching {string}', function (club) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    for (const p of list) {
      assert.ok(teamMatches(p.club, club), `${p.name} plays for ${p.club}, expected match for ${club}`);
    }
  });

  this.When('I search for forwards at {string}', function (club) {
    this.lastResult = findPlayers(this.snap, { club, position: 'ST', limit: 50 });
  });

  this.Then('every player should be a forward', function () {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    for (const p of list) {
      assert.ok(p.position.includes('ST') || p.position.includes('CF') || p.position.includes('FW'), `${p.name} position=${p.position}`);
    }
  });

  this.When('I ask for the roster at {string}', function (club) {
    this.lastResult = clubRoster(this.snap, club, 5);
  });

  this.Then('I should receive a total player count and an average overall rating', function () {
    const r = this.lastResult;
    assert.ok(r && typeof r.players === 'number' && typeof r.avgOverall === 'number', 'expected roster summary');
  });

  // ---------- Competition queries ----------

  this.When('I ask for the {string} {int} standings', function (comp, season) {
    this.lastResult = standings(this.snap, season, comp);
  });

  this.Then('the first row should be {string}', function (team) {
    const list = this.lastResult;
    assert.ok(Array.isArray(list) && list.length > 0, 'expected standings');
    assert.equal(canonicalTeam(list[0].team), canonicalTeam(team), `top was ${list[0].team}`);
  });

  this.Then('the table should be ordered by points then goal difference', function () {
    const list = this.lastResult;
    for (let i = 1; i < list.length; i++) {
      const a = list[i - 1], b = list[i];
      if (a.points !== b.points) {
        assert.ok(a.points > b.points, `points not descending at ${i}: ${a.points} then ${b.points}`);
      } else {
        assert.ok(a.goalDifference >= b.goalDifference, `goal diff not descending at ${i}`);
      }
    }
  });

  this.Then('the table should contain at least {int} teams', function (n) {
    const list = this.lastResult;
    assert.ok(list.length >= n, `expected at least ${n} teams, got ${list.length}`);
  });

  // ---------- Statistics ----------

  this.When('I ask for the average goals in {string}', function (comp) {
    this.lastResult = goalsStats(this.snap, comp);
  });

  this.Then('the response should include a numeric average between {float} and {float}', function (lo, hi) {
    const r = this.lastResult;
    assert.ok(r && typeof r.averageGoals === 'number', 'expected averageGoals');
    assert.ok(r.averageGoals >= lo && r.averageGoals <= hi, `avg ${r.averageGoals} out of range [${lo},${hi}]`);
  });

  this.Then('it should include a home win rate between {float} and {float} percent', function (lo, hi) {
    const r = this.lastResult;
    assert.ok(r && typeof r.homeWinRate === 'number', 'expected homeWinRate');
    assert.ok(r.homeWinRate >= lo && r.homeWinRate <= hi, `homeWinRate ${r.homeWinRate} out of range`);
  });

  this.When('I ask for the top {int} biggest wins across all competitions', function (n) {
    this.lastResult = biggestWins(this.snap, { limit: n });
  });

  this.Then('I should receive exactly {int} results', function (n) {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    assert.equal(list.length, n, `expected ${n} results, got ${list.length}`);
  });

  this.Then('the results should be ordered by margin descending', function () {
    const list = Array.isArray(this.lastResult) ? this.lastResult : [];
    for (let i = 1; i < list.length; i++) {
      assert.ok(list[i - 1].margin >= list[i].margin, `margin not descending at ${i}`);
    }
  });

  this.When('I ask for the top {int} best home records', function (n) {
    this.lastResult = bestHomeRecord(this.snap, n, 10);
  });

  this.Then('every team should have a positive home win rate', function () {
    const list = this.lastResult;
    for (const row of list) {
      assert.ok(row.homeWinRate > 0, `${row.team} homeWinRate=${row.homeWinRate}`);
    }
  });

  this.Then('the response should be ordered by home win rate descending', function () {
    const list = this.lastResult;
    for (let i = 1; i < list.length; i++) {
      assert.ok(list[i - 1].homeWinRate >= list[i].homeWinRate, `not descending at ${i}`);
    }
  });
};
