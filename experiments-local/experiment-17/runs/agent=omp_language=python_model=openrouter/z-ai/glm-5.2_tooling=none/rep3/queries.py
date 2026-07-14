"""Query engine for the Brazilian Soccer MCP server.

Context: TASK.md defines five query categories — match, team, player,
competition and statistical analysis. Each function here returns plain Python
data structures (dicts/lists of primitives) so the MCP tool layer in
:mod:`server` can render text for the LLM while the BDD test suite can assert
on the structured payload without parsing prose.

Team matching always goes through :mod:`normalize` so "Palmeiras-SP",
"Palmeiras" and "Palmeiras - SP" collapse to the same base key. When the
caller supplies a state (e.g. "Atlético-MG") it is used to disambiguate
same-base clubs (Atlético-MG vs Atlético-PR). Matches whose goals are missing
in the source CSV are carried through match listings but excluded from
win/loss/goal aggregates.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Canonical club resolver
# ---------------------------------------------------------------------------
# Maps a (base_key, state) lookup to a canonical club key. This is what lets
# full-form names ("Atletico Mineiro") merge with suffixed short forms
# ("Atletico-MG") and disambiguates same-base clubs ("Atletico-MG" vs
# "Atletico-PR"). Only clubs with genuinely ambiguous or multi-word names
# need an entry; everything else falls through to the primary-state rule.
CLUB_CANON: dict[tuple[str, str], str] = {
    # Atlético clubs (base "atletico" is shared across MG/PR/GO).
    ("atletico", "MG"): "atletico-mg",
    ("atletico mineiro", ""): "atletico-mg",
    ("atletico", "PR"): "atletico-pr",
    ("atletico paranaense", ""): "atletico-pr",
    ("athletico paranaense", ""): "atletico-pr",
    ("atletico", "GO"): "atletico-go",
    ("vasco", "RJ"): "vasco",
    ("vasco da gama", "RJ"): "vasco",
    ("vasco da gama", ""): "vasco",
    # Bahia / Vitória appear with "EC " prefixes in the stats file.
    ("ec bahia", ""): "bahia",
    ("bahia", ""): "bahia",
    ("bahia", "BA"): "bahia",
    ("ec vitoria", ""): "vitoria",
    ("vitoria", ""): "vitoria",
    ("vitoria", "BA"): "vitoria",
    # Botafogo (RJ) vs Botafogo (PB): keep the RJ form canonical when stated.
    ("botafogo", "RJ"): "botafogo",
    ("botafogo", ""): "botafogo",
    ("botafogo", "PB"): "botafogo-pb",
    ("botafogo paraiba", ""): "botafogo-pb",
}

# Preferred display label for canonical keys whose source variants are messy.
CLUB_DISPLAY: dict[str, str] = {
    "atletico-mg": "Atlético Mineiro",
    "atletico-pr": "Athletico Paranaense",
    "atletico-go": "Atlético Goianiense",
    "vasco": "Vasco da Gama",
    "bahia": "Bahia",
    "vitoria": "Vitória",
    "botafogo": "Botafogo",
    "botafogo-pb": "Botafogo (PB)",
}

import re
from collections import defaultdict
from typing import Optional

import normalize as norm
from data_loader import DataStore, Match, Player


# ---------------------------------------------------------------------------
# Derby definitions
# ---------------------------------------------------------------------------
# Each group is a set of (base_key, state) tokens. A match is a derby when
# both sides map to *different* tokens inside the same group. State is required
# for the Atlético clubs so MG and PR do not cross-match.
_DERBY_GROUPS: list[set[tuple[str, str]]] = [
    {("flamengo", "RJ"), ("fluminense", "RJ")},          # Fla-Flu
    {("flamengo", "RJ"), ("vasco", "RJ")},               # Clássico das Multidões
    {("corinthians", "SP"), ("palmeiras", "SP")},        # Paulista / Choque-Rei
    {("corinthians", "SP"), ("sao paulo", "SP")},        # Majestoso
    {("palmeiras", "SP"), ("sao paulo", "SP")},          # Choque Rei
    {("santos", "SP"), ("sao paulo", "SP")},             # San-São
    {("santos", "SP"), ("corinthians", "SP")},           # Clássico da Saudade
    {("gremio", "RS"), ("internacional", "RS")},         # Gre-Nal
    {("atletico", "PR"), ("coritiba", "PR")},            # Atletiba
    {("bahia", "BA"), ("vitoria", "BA")},               # Ba-Vi
    {("cruzeiro", "MG"), ("atletico", "MG")},           # Clássico Mineiro
    {("fortaleza", "CE"), ("ceara", "CE")},             # Clássico-Rei
]


def _side_token(match: Match, home: bool) -> tuple[str, Optional[str]]:
    if home:
        return match.home_key, match.home_state
    return match.away_key, match.away_state


def _token_in_group(token: tuple[str, Optional[str]],
                    group: set[tuple[str, str]]) -> Optional[tuple[str, str]]:
    """Return the group token a side matches, or None.

    A side matches a group token when base keys agree and states are
    compatible (equal, or either is unknown).
    """
    base, state = token
    if not base:
        return None
    for gbase, gstate in group:
        if base != gbase:
            continue
        if state is None or gstate is None or state == gstate:
            return (gbase, gstate)
    return None


def _is_derby(match: Match) -> bool:
    home_token = _side_token(match, True)
    away_token = _side_token(match, False)
    if home_token[0] == away_token[0] and home_token[1] == away_token[1]:
        return False
    for group in _DERBY_GROUPS:
        if _token_in_group(home_token, group) and _token_in_group(away_token, group):
            return True
    return False


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------
class _TeamSpec:
    """A parsed team query: base key plus optional state disambiguator."""

    __slots__ = ("raw", "base", "state")

    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.base, self.state = norm.normalize_team(raw)

    def matches(self, match: Match, *, home: bool) -> bool:
        if not self.base:
            return False
        if home:
            key, state = match.home_key, match.home_state
        else:
            key, state = match.away_key, match.away_state
        if key != self.base:
            return False
        if self.state and state and self.state != state:
            return False
        return True

    def side(self, match: Match) -> Optional[str]:
        """Return "home"/"away" if the team played, else None."""
        if self.matches(match, home=True):
            return "home"
        if self.matches(match, home=False):
            return "away"
        return None


def _venue_ok(spec_side: Optional[str], venue: Optional[str]) -> bool:
    if venue is None or venue == "either":
        return True
    return spec_side == venue


def _competition_ok(match: Match, competition: Optional[str]) -> bool:
    if competition is None:
        return True
    return norm.normalize_competition(competition) == match.competition


def _season_ok(match: Match, season: Optional[int]) -> bool:
    if season is None:
        return True
    return match.season == season


def _date_ok(match: Match, date_from=None, date_to=None) -> bool:
    if match.date is None:
        return date_from is None and date_to is None
    if date_from is not None and match.date < date_from:
        return False
    if date_to is not None and match.date > date_to:
        return False
    return True


def _match_dict(m: Match, team_spec: Optional[_TeamSpec] = None) -> dict:
    d = {
        "date": m.date.isoformat() if m.date else None,
        "season": m.season,
        "competition": m.competition,
        "stage": m.stage,
        "home_team": m.home_team,
        "away_team": m.away_team,
        "home_goal": m.home_goal,
        "away_goal": m.away_goal,
        "source": m.source_file,
    }
    if m.stats:
        d["stats"] = {k: v for k, v in m.stats.items() if v not in (None, "")}
    if team_spec is not None:
        d["team_side"] = team_spec.side(m)
    return d


def _has_score(m: Match) -> bool:
    return m.home_goal is not None and m.away_goal is not None


def _result_for(m: Match, spec: _TeamSpec) -> Optional[str]:
    """Return "win"/"loss"/"draw" for *spec* in *m*, or None if unscoring."""
    if not _has_score(m):
        return None
    side = spec.side(m)
    if side is None:
        return None
    hg, ag = m.home_goal, m.away_goal
    if hg == ag:
        return "draw"
    home_win = hg > ag
    if side == "home":
        return "win" if home_win else "loss"
    return "loss" if home_win else "win"


def _identity(match: Match, home: bool,
              primary_state: Optional[dict] = None) -> tuple[object, str]:
    """Canonical (key, display-variant) for a side, merging name variants.

    "Flamengo-RJ" (Brasileirao_Matches) and "Flamengo" (BR-Football-Dataset)
    collapse to one identity so standings do not split a single club. The
    resolution order is:
      1. :data:`CLUB_CANON` — fixes full-name vs short-form clubs
         ("Atletico Mineiro" == "Atletico-MG") and ambiguous bases
         ("Atletico-MG" vs "Atletico-PR").
      2. A per-base *primary state* (when a base maps to exactly one
         non-empty UF across the dataset) so empty-state variants merge with
         the suffixed form.
      3. The base plus the variant's own state (keeps MG/PR apart when both
         are genuinely present).
    """
    if home:
        base, state, raw = match.home_key, match.home_state, match.home_team
    else:
        base, state, raw = match.away_key, match.away_state, match.away_team
    canon = CLUB_CANON.get((base, state or ""))
    if canon is not None:
        return canon, raw
    if primary_state and base in primary_state:
        return (base, primary_state[base]), raw
    return (base, state or ""), raw


def _pick_display(variants: set[str], canonical: object = None) -> str:
    """Choose the cleanest display name for a (possibly canonical) identity.

    Canonical string keys (from :data:`CLUB_CANON`) get their curated label;
    otherwise the cleanest source variant is chosen — preferring names
    without a state suffix or parenthetical, then the shortest. Any trailing
    ``-UF`` state suffix is stripped from the result so standings show
    "Flamengo" rather than "Flamengo-RJ".
    """
    if isinstance(canonical, str) and canonical in CLUB_DISPLAY:
        return CLUB_DISPLAY[canonical]
    if not variants:
        return ""
    clean = [v for v in variants if "-" not in v and "(" not in v]
    pool = clean or list(variants)
    chosen = sorted(pool, key=lambda v: (len(v), v))[0]
    return re.sub(r"\s*[-–—]\s*[A-Z]{2}\s*$", "", chosen)
# ---------------------------------------------------------------------------
class QueryEngine:
    """Stateless query facade over a :class:`DataStore`."""

    def __init__(self, store: DataStore) -> None:
        self.store = store
        self._primary_state = self._compute_primary_state()
        # Deduplicated match stream: the Brasileirao_Matches and
        # BR-Football "Serie A" files describe the same fixtures for
        # overlapping seasons, so without dedup every standings row, win
        # rate and goal average would be counted twice. We collapse to one
        # record per (competition, date, canonical home, canonical away),
        # preferring a record that actually carries a score.
        self._matches = self._build_dedup()

    def _build_dedup(self) -> list[Match]:
        # Key on competition + canonical identity of each side. The two
        # Brasileirão sources (Brasileirao_Matches.csv and BR-Football's
        # "Serie A") sometimes disagree on the exact kick-off date by one
        # day (timezone/time-of-day rounding), so the date part of the key
        # is matched against an existing entry's date ±1 day. When both rows
        # describe the same fixture we keep the one carrying a score, then
        # the one already seen.
        seen: dict = {}
        for m in self.store.matches:
            hkey, _ = self._identity(m, True)
            akey, _ = self._identity(m, False)
            existing = self._find_existing(seen, m.competition, m.date,
                                           hkey, akey)
            if existing is None:
                seen[(m.competition, m.date, hkey, akey)] = m
            elif (existing.home_goal is None or existing.away_goal is None) \
                    and m.home_goal is not None and m.away_goal is not None:
                seen[(m.competition, m.date, hkey, akey)] = m
        return list(seen.values())

    @staticmethod
    def _find_existing(seen: dict, competition: str, d, hkey, akey):
        if d is None:
            return seen.get((competition, None, hkey, akey))
        import datetime as _dt
        for delta in (0, -1, 1):
            probe = d + _dt.timedelta(days=delta)
            key = (competition, probe, hkey, akey)
            if key in seen:
                return seen[key]
        return None

    def _compute_primary_state(self) -> dict:
        """Map each base key to its dominant state, when one is overwhelming.

        Returns the most frequent non-empty UF per base only when that UF
        accounts for >= 80% of the base's occurrences. This lets an empty-
        state variant ("Internacional" in BR-Football) merge with its
        dominant club ("Internacional-RS") while genuinely split bases
        ("atletico" -> MG vs PR, roughly 50/50) stay unassigned so rival
        clubs are never collapsed. Bases resolved by :data:`CLUB_CANON`
        upstream are handled before this rule, so they never reach here.
        """
        counts: dict[str, dict[str, int]] = {}
        for m in self.store.matches:
            for base, state in ((m.home_key, m.home_state),
                                (m.away_key, m.away_state)):
                if base and state:
                    counts.setdefault(base, {})[state] = (
                        counts.setdefault(base, {}).get(state, 0) + 1)
        primary: dict[str, str] = {}
        for base, tally in counts.items():
            total = sum(tally.values())
            top_state, top_n = max(tally.items(), key=lambda kv: kv[1])
            if top_n / total >= 0.8:
                primary[base] = top_state
        return primary

    def _identity(self, match: Match, home: bool) -> tuple[object, str]:
        return _identity(match, home, self._primary_state)

    # -- match queries -----------------------------------------------------
    def search_matches(self, team: Optional[str] = None,
                       opponent: Optional[str] = None,
                       competition: Optional[str] = None,
                       season: Optional[int] = None,
                       venue: Optional[str] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None,
                       limit: Optional[int] = None) -> dict:
        team_spec = _TeamSpec(team) if team else None
        opp_spec = _TeamSpec(opponent) if opponent else None
        d_from = norm.parse_date(date_from)
        d_to = norm.parse_date(date_to)
        results: list[dict] = []
        for m in self._matches:
            if not _competition_ok(m, competition):
                continue
            if not _season_ok(m, season):
                continue
            if not _date_ok(m, d_from, d_to):
                continue
            if team_spec is not None:
                side = team_spec.side(m)
                if side is None or not _venue_ok(side, venue):
                    continue
                if opp_spec is not None and not opp_spec.matches(
                        m, home=(side == "away")):
                    continue
            elif opp_spec is not None:
                if opp_spec.side(m) is None:
                    continue
            results.append(_match_dict(m, team_spec))
        results.sort(key=lambda r: (r["date"] or "0000", r["competition"]))
        total = len(results)
        if limit is not None:
            results = results[:limit]
        return {"count": total, "returned": len(results), "matches": results}

    def head_to_head(self, team_a: str, team_b: str,
                     competition: Optional[str] = None,
                     season: Optional[int] = None) -> dict:
        spec_a = _TeamSpec(team_a)
        spec_b = _TeamSpec(team_b)
        matches: list[dict] = []
        wins_a = wins_b = draws = 0
        gf_a = gf_b = 0
        for m in self._matches:
            if not _competition_ok(m, competition) or not _season_ok(m, season):
                continue
            side_a = spec_a.side(m)
            if side_a is None:
                continue
            if not spec_b.matches(m, home=(side_a == "away")):
                continue
            res = _result_for(m, spec_a)
            matches.append(_match_dict(m, spec_a))
            if res == "win":
                wins_a += 1
            elif res == "loss":
                wins_b += 1
            elif res == "draw":
                draws += 1
            if _has_score(m):
                if side_a == "home":
                    gf_a += m.home_goal; gf_b += m.away_goal
                else:
                    gf_a += m.away_goal; gf_b += m.home_goal
        matches.sort(key=lambda r: r["date"] or "0000")
        return {
            "team_a": spec_a.raw, "team_b": spec_b.raw,
            "matches_played": len(matches),
            "team_a_wins": wins_a, "team_b_wins": wins_b, "draws": draws,
            "team_a_goals": gf_a, "team_b_goals": gf_b,
            "matches": matches,
        }

    # -- team queries ------------------------------------------------------
    def team_stats(self, team: str, season: Optional[int] = None,
                   competition: Optional[str] = None,
                   venue: Optional[str] = None) -> dict:
        spec = _TeamSpec(team)
        wins = losses = draws = 0
        gf = ga = 0
        by_competition: dict[str, dict] = defaultdict(
            lambda: {"wins": 0, "draws": 0, "losses": 0, "matches": 0})
        played = 0
        for m in self._matches:
            if not _competition_ok(m, competition) or not _season_ok(m, season):
                continue
            side = spec.side(m)
            if side is None or not _venue_ok(side, venue):
                continue
            played += 1
            res = _result_for(m, spec)
            bucket = by_competition[m.competition]
            bucket["matches"] += 1
            if res == "win":
                wins += 1; bucket["wins"] += 1
            elif res == "loss":
                losses += 1; bucket["losses"] += 1
            elif res == "draw":
                draws += 1; bucket["draws"] += 1
            if _has_score(m):
                if side == "home":
                    gf += m.home_goal; ga += m.away_goal
                else:
                    gf += m.away_goal; ga += m.home_goal
        win_rate = round(wins / played * 100, 1) if played else 0.0
        return {
            "team": spec.raw, "matches": played,
            "wins": wins, "draws": draws, "losses": losses,
            "goals_for": gf, "goals_against": ga,
            "win_rate": win_rate,
            "venue": venue or "either",
            "season": season,
            "by_competition": dict(by_competition),
        }

    def team_competitions(self, team: str) -> dict:
        spec = _TeamSpec(team)
        comps: dict[str, int] = defaultdict(int)
        seasons_by_comp: dict[str, set] = defaultdict(set)
        for m in self._matches:
            if spec.side(m) is not None:
                comps[m.competition] += 1
                if m.season:
                    seasons_by_comp[m.competition].add(m.season)
        return {
            "team": spec.raw,
            "competitions": {c: {"matches": n,
                                  "seasons": sorted(seasons_by_comp[c])}
                             for c, n in sorted(comps.items())},
        }

    # -- player queries ----------------------------------------------------
    def search_players(self, name: Optional[str] = None,
                       nationality: Optional[str] = None,
                       club: Optional[str] = None,
                       position: Optional[str] = None,
                       min_overall: Optional[int] = None,
                       limit: Optional[int] = None) -> dict:
        name_l = name.lower() if name else None
        nat_l = norm.deaccent(nationality).lower() if nationality else None
        club_l = club.lower() if club else None
        pos = position.upper() if position else None
        out: list[dict] = []
        for p in self.store.players:
            if name_l and name_l not in p.name.lower():
                continue
            if nat_l and norm.deaccent(p.nationality).lower() != nat_l:
                continue
            if club_l and club_l not in p.club.lower():
                continue
            if pos and p.position != pos:
                continue
            if min_overall is not None and (p.overall is None
                                            or p.overall < min_overall):
                continue
            out.append(self._player_dict(p))
        out.sort(key=lambda r: (-(r["overall"] or 0), r["name"]))
        total = len(out)
        if limit is not None:
            out = out[:limit]
        return {"count": total, "returned": len(out), "players": out}

    def top_players(self, nationality: Optional[str] = None,
                    club: Optional[str] = None, limit: int = 10) -> dict:
        res = self.search_players(nationality=nationality, club=club,
                                  limit=limit)
        res["sort"] = "overall desc"
        return res

    def brazilian_players_by_club(self, limit: Optional[int] = None) -> dict:
        buckets: dict[str, list[Player]] = defaultdict(list)
        for p in self.store.players:
            if norm.deaccent(p.nationality).lower() == "brazil" and p.club:
                buckets[p.club].append(p)
        rows = []
        for club, players in buckets.items():
            overalls = [p.overall for p in players if p.overall is not None]
            avg = round(sum(overalls) / len(overalls), 1) if overalls else 0.0
            rows.append({"club": club, "players": len(players),
                         "avg_overall": avg,
                         "top": max(players, key=lambda p: p.overall or 0).name
                         if players else None})
        rows.sort(key=lambda r: (-r["players"], -r["avg_overall"]))
        if limit is not None:
            rows = rows[:limit]
        return {"clubs": rows}

    def _player_dict(self, p: Player) -> dict:
        return {
            "id": p.id, "name": p.name, "age": p.age,
            "nationality": p.nationality, "overall": p.overall,
            "potential": p.potential, "club": p.club, "position": p.position,
            "jersey": p.jersey, "height": p.height, "weight": p.weight,
            "value": p.value, "wage": p.wage, "preferred_foot": p.preferred_foot,
        }

    # -- competition queries ----------------------------------------------
    def competition_standings(self, competition: str,
                              season: Optional[int] = None,
                              top: Optional[int] = None) -> dict:
        target = norm.normalize_competition(competition)
        points: dict[tuple, int] = defaultdict(int)
        played: dict[tuple, int] = defaultdict(int)
        wins: dict[tuple, int] = defaultdict(int)
        draws: dict[tuple, int] = defaultdict(int)
        losses: dict[tuple, int] = defaultdict(int)
        gf: dict[tuple, int] = defaultdict(int)
        ga: dict[tuple, int] = defaultdict(int)
        variants: dict[tuple, set] = defaultdict(set)
        for m in self._matches:
            if m.competition != target:
                continue
            if season is not None and m.season != season:
                continue
            if not _has_score(m):
                continue
            home_key, home_raw = self._identity(m, True)
            away_key, away_raw = self._identity(m, False)
            variants[home_key].add(home_raw)
            variants[away_key].add(away_raw)
            played[home_key] += 1; played[away_key] += 1
            gf[home_key] += m.home_goal; ga[home_key] += m.away_goal
            gf[away_key] += m.away_goal; ga[away_key] += m.home_goal
            if m.home_goal > m.away_goal:
                wins[home_key] += 1; losses[away_key] += 1
                points[home_key] += 3
            elif m.home_goal < m.away_goal:
                wins[away_key] += 1; losses[home_key] += 1
                points[away_key] += 3
            else:
                draws[home_key] += 1; draws[away_key] += 1
                points[home_key] += 1; points[away_key] += 1
        teams = sorted(variants.keys(),
                       key=lambda t: (-points[t], -wins[t],
                                       -(gf[t] - ga[t]), -gf[t], str(t)))
        if top is not None:
            teams = teams[:top]
        table = [{
            "position": i + 1,
            "team": _pick_display(variants[t], t),
            "points": points[t],
            "played": played[t],
            "wins": wins[t], "draws": draws[t], "losses": losses[t],
            "goals_for": gf[t], "goals_against": ga[t],
            "goal_difference": gf[t] - ga[t],
        } for i, t in enumerate(teams)]
        return {
            "competition": target, "season": season,
            "champion": table[0]["team"] if table else None,
            "standings": table,
        }

    def competition_seasons(self, competition: str) -> dict:
        target = norm.normalize_competition(competition)
        seasons = sorted({m.season for m in self._matches
                          if m.competition == target and m.season})
        return {"competition": target, "seasons": seasons}

    # -- statistical analysis ---------------------------------------------
    def biggest_wins(self, competition: Optional[str] = None,
                     season: Optional[int] = None,
                     limit: int = 10) -> dict:
        target = norm.normalize_competition(competition) if competition else None
        scored = []
        for m in self._matches:
            if target and m.competition != target:
                continue
            if season is not None and m.season != season:
                continue
            if not _has_score(m):
                continue
            diff = abs(m.home_goal - m.away_goal)
            scored.append((diff, m))
        scored.sort(key=lambda x: (-x[0],
                                   x[1].date or __import__("datetime").date.max))
        out = []
        for diff, m in scored[:limit]:
            if m.home_goal > m.away_goal:
                winner, loser, wg, lg = m.home_team, m.away_team, m.home_goal, m.away_goal
            else:
                winner, loser, wg, lg = m.away_team, m.home_team, m.away_goal, m.home_goal
            out.append({
                "date": m.date.isoformat() if m.date else None,
                "winner": winner, "loser": loser,
                "winner_goals": wg, "loser_goals": lg,
                "margin": diff, "competition": m.competition,
            })
        return {"count": len(out), "biggest_wins": out}

    def average_goals(self, competition: Optional[str] = None,
                      season: Optional[int] = None) -> dict:
        target = norm.normalize_competition(competition) if competition else None
        total_goals = 0
        matches = 0
        home_wins = away_wins = draws = 0
        for m in self._matches:
            if target and m.competition != target:
                continue
            if season is not None and m.season != season:
                continue
            if not _has_score(m):
                continue
            matches += 1
            total_goals += m.home_goal + m.away_goal
            if m.home_goal > m.away_goal:
                home_wins += 1
            elif m.home_goal < m.away_goal:
                away_wins += 1
            else:
                draws += 1
        avg = round(total_goals / matches, 2) if matches else 0.0
        home_rate = round(home_wins / matches * 100, 1) if matches else 0.0
        away_rate = round(away_wins / matches * 100, 1) if matches else 0.0
        draw_rate = round(draws / matches * 100, 1) if matches else 0.0
        return {
            "competition": target or "all",
            "season": season,
            "matches": matches,
            "total_goals": total_goals,
            "average_goals_per_match": avg,
            "home_win_rate": home_rate,
            "away_win_rate": away_rate,
            "draw_rate": draw_rate,
        }

    def best_record(self, venue: str = "home",
                    competition: Optional[str] = None,
                    season: Optional[int] = None,
                    limit: int = 10) -> dict:
        """Rank teams by win rate for a given venue (home/away)."""
        target = norm.normalize_competition(competition) if competition else None
        stats: dict[tuple, dict] = defaultdict(
            lambda: {"wins": 0, "draws": 0, "losses": 0, "matches": 0})
        variants: dict[tuple, set] = defaultdict(set)
        for m in self._matches:
            if target and m.competition != target:
                continue
            if season is not None and m.season != season:
                continue
            if not _has_score(m):
                continue
            if venue == "home":
                key, raw, gf, ga = *self._identity(m, True), m.home_goal, m.away_goal
            else:
                key, raw, gf, ga = *self._identity(m, False), m.away_goal, m.home_goal
            variants[key].add(raw)
            bucket = stats[key]
            bucket["matches"] += 1
            if gf > ga:
                bucket["wins"] += 1
            elif gf < ga:
                bucket["losses"] += 1
            else:
                bucket["draws"] += 1
        rows = []
        for key, b in stats.items():
            if b["matches"] == 0:
                continue
            rows.append({
                "team": _pick_display(variants[key], key),
                "matches": b["matches"],
                "wins": b["wins"], "draws": b["draws"], "losses": b["losses"],
                "win_rate": round(b["wins"] / b["matches"] * 100, 1),
            })
        rows.sort(key=lambda r: (-r["win_rate"], -r["matches"], r["team"]))
        return {"venue": venue, "count": len(rows),
                "teams": rows[:limit]}

    def derbies(self, season: Optional[int] = None,
                competition: Optional[str] = None,
                limit: Optional[int] = None) -> dict:
        out = []
        for m in self._matches:
            if not _competition_ok(m, competition) or not _season_ok(m, season):
                continue
            if _is_derby(m):
                out.append(_match_dict(m))
        out.sort(key=lambda r: r["date"] or "0000")
        total = len(out)
        if limit is not None:
            out = out[:limit]
        return {"count": total, "returned": len(out), "derbies": out}

    # -- catalog -----------------------------------------------------------
    def catalog(self) -> dict:
        return {
            "competitions": self.store.competitions(),
            "seasons_by_competition": {
                c: self.store.seasons(c) for c in self.store.competitions()
            },
            "team_count": len(self.store.team_names()),
            "player_count": len(self.store.players),
            "match_count": len(self._matches),
        }
