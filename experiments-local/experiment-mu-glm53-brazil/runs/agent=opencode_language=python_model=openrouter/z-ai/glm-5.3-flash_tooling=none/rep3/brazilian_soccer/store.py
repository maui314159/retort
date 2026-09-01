"""In-memory knowledge store: indexes over matches/players + queries.

``SoccerStore`` is the single query surface shared by the MCP tools and
the tests.  It loads the datasets once (about 0.6 s for ~17k matches and
18k players) and keeps O(1) lookup indexes:

- ``matches_by_team``      canonical team key -> matches it played
- ``matches_by_comp_season`` (competition, season) -> matches
- ``matches_by_stage``     (competition, stage) -> matches (finals etc.)
- ``players_by_club``      canonical club key -> players
- ``players_sorted``       all players sorted by FIFA Overall

Fuzzy resolution helpers make natural-language-style arguments work:
``resolve_team("Flamengo")`` and ``resolve_team("Flamengo-RJ")`` return
the same canonical key; ``resolve_competition("brasileirao")`` returns
``Brasileirão Serie A``.  Traditional rivalries (derbies) are defined in
``DERBIES`` and drive ``derbies()`` and derby detection.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from .analytics import (
    aggregate_stats,
    best_venues,
    biggest_wins,
    h2h_record,
    season_comparison,
    standings_table,
    team_record,
)
from .loader import load_all
from .models import (
    COPA_DO_BRASIL,
    LEAGUE_COMPETITIONS,
    LIBERTADORES,
    BRASILEIRAO_A,
    Match,
    Player,
)
from .normalize import parse_date, strip_accents

DEFAULT_LIMIT = 25
MAX_LIMIT = 100

# Traditional rivalries: (derby name, aliases, raw team names).
DERBIES: list[tuple[str, list[str], tuple[str, str]]] = [
    ("Fla-Flu", ["fla flu", "fla-flu"], ("Flamengo-RJ", "Fluminense-RJ")),
    ("Clássico dos Milhões", ["classico dos milhoes"],
     ("Flamengo-RJ", "Vasco da Gama-RJ")),
    ("Clássico da Rivalidade", ["classico da rivalidade"],
     ("Botafogo-RJ", "Flamengo-RJ")),
    ("Clássico Vovô", ["classico vovo"], ("Botafogo-RJ", "Fluminense-RJ")),
    ("Dérbi Paulista", ["derbi paulista", "derby paulista"],
     ("Corinthians-SP", "Palmeiras-SP")),
    ("Majestoso", ["majestoso"], ("Corinthians-SP", "São Paulo-SP")),
    ("Choque-Rei", ["choque rei", "choque-rei"], ("Palmeiras-SP", "São Paulo-SP")),
    ("San-São", ["san sao"], ("Santos-SP", "São Paulo-SP")),
    ("Grenal", ["grenal"], ("Grêmio-RS", "Internacional-RS")),
    ("Atletiba", ["atletiba"], ("Athletico-PR", "Coritiba-PR")),
    ("Ba-Vi", ["ba vi", "ba-vi"], ("Bahia-BA", "Vitória-BA")),
    ("Clássico Mineiro", ["classico mineiro"], ("Atlético-MG", "Cruzeiro-MG")),
    ("Clássico-Rei", ["classico rei"], ("Ceará-CE", "Fortaleza-CE")),
    ("Clássico das Multidões", ["classico das multidoes"],
     ("Sport-PE", "Santa Cruz-PE")),
    ("Clássico Emoção", ["classico emocao"], ("Sport-PE", "Náutico-PE")),
]

COMPETITION_ALIASES = {
    "brasileirao": BRASILEIRAO_A,
    "brasileirao serie a": BRASILEIRAO_A,
    "serie a": BRASILEIRAO_A,
    "brasileirao serie b": "Brasileirão Serie B",
    "serie b": "Brasileirão Serie B",
    "brasileirao serie c": "Brasileirão Serie C",
    "serie c": "Brasileirão Serie C",
    "copa do brasil": COPA_DO_BRASIL,
    "brazilian cup": COPA_DO_BRASIL,
    "copa brasil": COPA_DO_BRASIL,
    "libertadores": LIBERTADORES,
    "copa libertadores": LIBERTADORES,
}


class NotFound(LookupError):
    """Raised when a team/competition/player cannot be resolved."""


class SoccerStore:
    """Query engine over the six Brazilian soccer datasets."""

    def __init__(self) -> None:
        self.registry, self.matches, self.players = load_all()
        self._build_indexes()

    # ------------------------------------------------------------------
    # indexes
    # ------------------------------------------------------------------

    def _build_indexes(self) -> None:
        self.matches_by_team: dict[str, list[Match]] = defaultdict(list)
        self.matches_by_comp_season: dict[tuple[str, int], list[Match]] = defaultdict(list)
        self.matches_by_stage: dict[tuple[str, str], list[Match]] = defaultdict(list)
        for m in self.matches:
            self.matches_by_team[m.home_key].append(m)
            self.matches_by_team[m.away_key].append(m)
            self.matches_by_comp_season[(m.competition, m.season)].append(m)
            if m.stage:
                self.matches_by_stage[(m.competition, m.stage)].append(m)
        self.players_by_club: dict[str, list[Player]] = defaultdict(list)
        for p in self.players:
            if p.club_key:
                self.players_by_club[p.club_key].append(p)
        self.players_sorted = sorted(self.players, key=lambda p: -p.overall)

        # Derby pairs in canonical key space.
        self.derby_pairs: list[tuple[str, tuple[str, str]]] = []
        for name, _aliases, (a, b) in DERBIES:
            self.derby_pairs.append(
                (name, (self.registry.key_for(a), self.registry.key_for(b))))

        # Team popularity: matches played (used to pick fuzzy best match).
        self._team_popularity: dict[str, int] = {
            k: len(v) for k, v in self.matches_by_team.items()}

    # ------------------------------------------------------------------
    # resolution helpers
    # ------------------------------------------------------------------

    def resolve_team(self, name: str) -> str:
        """Canonical key for a team name; fuzzy-falls back to displays."""
        if not name or not name.strip():
            raise NotFound("Empty team name")
        raw = name.strip()
        key = self.registry.key_for(raw)
        if key in self._team_popularity or key in self.players_by_club:
            return key
        # substring match over display names (accent-insensitive)
        q = strip_accents(raw).lower()
        cands = {k: d for k, d in self.registry.display_names().items()
                 if q in strip_accents(d).lower()}
        if not cands:
            raise NotFound(
                f"Team {name!r} not found; dataset covers "
                f"{len(self.registry.display_names())} clubs")
        # prefer the candidate with the most matches (famous club wins)
        return max(cands, key=lambda k: self._team_popularity.get(k, 0))

    def resolve_competition(self, name: str | None) -> str | None:
        """Canonical competition label (None matches everything)."""
        if name is None or not str(name).strip():
            return None
        q = strip_accents(str(name)).strip().lower()
        if q in COMPETITION_ALIASES:
            return COMPETITION_ALIASES[q]
        all_names = set(COMPETITION_ALIASES.values())
        for label in all_names:
            if q in strip_accents(label).lower():
                return label
        raise NotFound(
            f"Competition {name!r} not found; known: {sorted(all_names)}")

    def team_display(self, key: str) -> str:
        return self.registry.display(key)

    def derby_of(self, home_key: str, away_key: str) -> str | None:
        """Derby name if the fixture is a traditional rivalry."""
        for name, (a, b) in self.derby_pairs:
            if {home_key, away_key} == {a, b}:
                return name
        return None

    # ------------------------------------------------------------------
    # generic filters
    # ------------------------------------------------------------------

    @staticmethod
    def _filters_apply(m: Match, competition: str | None, season: int | None,
                       date_from, date_to) -> bool:
        if competition and m.competition != competition:
            return False
        if season is not None and m.season != season:
            return False
        if date_from and (m.date is None or m.date < date_from):
            return False
        if date_to and (m.date is None or m.date > date_to):
            return False
        return True

    @staticmethod
    def match_dict(m: Match, store: "SoccerStore") -> dict:
        """JSON-ready representation of a match."""
        home = store.registry.display(m.home_key)
        away = store.registry.display(m.away_key)
        return {
            "date": m.date.isoformat() if m.date else None,
            "time": m.time,
            "competition": m.competition,
            "season": m.season,
            "round": m.round,
            "stage": m.stage,
            "home": home,
            "away": away,
            "home_goal": m.home_goal,
            "away_goal": m.away_goal,
            "score": (f"{home} {m.home_goal}-{m.away_goal} {away}"
                      if m.has_result() else None),
            "winner": (store.registry.display(m.winner_key())
                       if m.winner_key() else ("Draw" if m.has_result() else None)),
            "arena": m.arena,
            "source": m.source,
        }

    # ------------------------------------------------------------------
    # match queries
    # ------------------------------------------------------------------

    def search_matches(self, team: str | None = None,
                       opponent: str | None = None,
                       competition: str | None = None,
                       season: int | None = None,
                       stage: str | None = None,
                       date_from: str | None = None,
                       date_to: str | None = None,
                       limit: int = DEFAULT_LIMIT,
                       order: str = "asc") -> dict:
        comp = self.resolve_competition(competition)
        season = _as_int(season)
        d_from = parse_date(date_from) if date_from else None
        d_to = parse_date(date_to) if date_to else None
        stage_q = strip_accents(stage).lower() if stage else None

        team_key = self.resolve_team(team) if team else None
        opp_key = self.resolve_team(opponent) if opponent else None

        if team_key and opp_key:
            pool = [m for m in self.matches_by_team[team_key]
                    if opp_key in (m.home_key, m.away_key)]
        elif team_key:
            pool = self.matches_by_team[team_key]
        elif opp_key:
            pool = self.matches_by_team[opp_key]
        else:
            pool = self.matches

        selected = [
            m for m in pool
            if self._filters_apply(m, comp, season, d_from, d_to)
            and (not stage_q or (m.stage or "").lower() == stage_q)
        ]
        selected.sort(key=lambda m: (m.date is None, m.date),
                      reverse=(order == "desc"))
        return {
            "total": len(selected),
            "matches": [self.match_dict(m, self) for m in selected[:_clamp(limit)]],
        }

    def head_to_head(self, team_a: str, team_b: str,
                     competition: str | None = None,
                     limit: int = DEFAULT_LIMIT) -> dict:
        a = self.resolve_team(team_a)
        b = self.resolve_team(team_b)
        if a == b:
            raise NotFound("Head-to-head needs two different teams")
        comp = self.resolve_competition(competition)
        pool = [m for m in self.matches_by_team[a] if b in (m.home_key, m.away_key)]
        selected = [m for m in pool if self._filters_apply(m, comp, None, None, None)]
        selected.sort(key=lambda m: (m.date is None, m.date))
        rec = h2h_record(selected, a, b)
        return {
            "team_a": self.team_display(a),
            "team_b": self.team_display(b),
            "competition": comp,
            "team_a_wins": rec["team_a_wins"],
            "team_b_wins": rec["team_b_wins"],
            "draws": rec["draws"],
            "team_a_goals": rec["team_a_goals"],
            "team_b_goals": rec["team_b_goals"],
            "derby": self.derby_of(a, b),
            "total_matches": len(selected),
            "total": len(selected),          # alias shared with search_matches
            "matches": [self.match_dict(m, self) for m in selected[-_clamp(limit):]],
        }

    # ------------------------------------------------------------------
    # team queries
    # ------------------------------------------------------------------

    def team_stats(self, team: str, season: int | None = None,
                   competition: str | None = None,
                   venue: str | None = None) -> dict:
        key = self.resolve_team(team)
        comp = self.resolve_competition(competition)
        season = _as_int(season)
        pool = [m for m in self.matches_by_team[key]
                if self._filters_apply(m, comp, season, None, None)]
        venue_n = (venue or "").strip().lower()
        if venue_n in ("home", "away"):
            pool = [m for m in pool
                    if (m.home_key == key) == (venue_n == "home")]
        rec = team_record(pool, key)
        return {
            "team": self.team_display(key),
            "competition": comp,
            "season": season,
            "venue": venue_n or "all",
            **rec,
        }

    def team_history(self, team: str) -> dict:
        key = self.resolve_team(team)
        per_comp: dict[str, set[int]] = defaultdict(set)
        for m in self.matches_by_team[key]:
            per_comp[m.competition].add(m.season)
        return {
            "team": self.team_display(key),
            "total_matches": len(self.matches_by_team[key]),
            "overall_record": team_record(self.matches_by_team[key], key),
            "competitions": {
                comp: sorted(seasons) for comp, seasons in sorted(per_comp.items())
            },
        }

    def list_teams(self, competition: str | None = None,
                   season: int | None = None) -> dict:
        comp = self.resolve_competition(competition)
        season = _as_int(season)
        teams = {}
        for m in self.matches:
            if not self._filters_apply(m, comp, season, None, None):
                continue
            for k in (m.home_key, m.away_key):
                teams[k] = teams.get(k, 0) + 1
        return {
            "total": len(teams),
            "teams": [
                {"team": self.team_display(k), "matches": n}
                for k, n in sorted(teams.items(), key=lambda kv: -kv[1])
            ],
        }

    # ------------------------------------------------------------------
    # competition queries
    # ------------------------------------------------------------------

    def competitions(self) -> dict:
        catalog = defaultdict(lambda: {"seasons": set(), "matches": 0})
        for m in self.matches:
            entry = catalog[m.competition]
            entry["seasons"].add(m.season)
            entry["matches"] += 1
        return {
            "competitions": [
                {
                    "competition": comp,
                    "seasons": f"{min(ss)}-{max(ss)}" if ss else "-",
                    "season_count": len(ss),
                    "matches": e["matches"],
                }
                for comp, e in sorted(catalog.items())
                for ss in [e["seasons"]]
            ]
        }

    def standings(self, competition: str, season: int,
                  top: int | None = None) -> dict:
        comp = self.resolve_competition(competition)
        season = _as_int(season)
        if season is None:
            raise NotFound("Standings need a season (year)")
        if comp not in LEAGUE_COMPETITIONS:
            raise NotFound(
                f"Standings are only computed for league competitions "
                f"({sorted(LEAGUE_COMPETITIONS)}), not {comp!r}")
        matches = self.matches_by_comp_season.get((comp, season), [])
        table = standings_table(matches)
        if top:
            table = table[:top]
        rows = []
        for r in table:
            rows.append({
                "position": r["position"],
                "team": self.team_display(r["team"]),
                "matches": r["matches"],
                "wins": r["wins"],
                "draws": r["draws"],
                "losses": r["losses"],
                "goals_for": r["goals_for"],
                "goals_against": r["goals_against"],
                "goal_difference": r["goal_difference"],
                "points": r["points"],
            })
        response = {
            "competition": comp,
            "season": season,
            "total_matches_used": len(matches),
            "table": rows,
            "champion": rows[0]["team"] if rows else None,
        }
        if comp == BRASILEIRAO_A and len(rows) >= 4:
            response["relegation_zone"] = [r["team"] for r in rows[-4:]]
        return response

    # ------------------------------------------------------------------
    # player queries
    # ------------------------------------------------------------------

    @staticmethod
    def _player_dict(p: Player, with_skills: bool = False) -> dict:
        d = {
            "id": p.id,
            "name": p.name,
            "nationality": p.nationality,
            "overall": p.overall,
            "potential": p.potential,
            "club": p.club_display,
            "position": p.position,
            "age": p.age,
            "preferred_foot": p.preferred_foot,
        }
        if with_skills:
            d.update({
                "height_cm": p.height_cm,
                "weight_kg": p.weight_kg,
                "jersey": p.jersey,
                "value": p.value,
                "wage": p.wage,
                "skills": p.skills,
            })
        return d

    def search_players(self, name: str | None = None,
                       nationality: str | None = None,
                       club: str | None = None,
                       position: str | None = None,
                       min_overall: int | None = None,
                       max_overall: int | None = None,
                       limit: int = DEFAULT_LIMIT) -> dict:
        club_key = None
        if club:
            try:
                club_key = self.resolve_team(club)
            except NotFound:
                club_key = None
        name_q = strip_accents(name or "").lower()
        nat_q = (nationality or "").strip().lower()
        pos_q = (position or "").strip().upper()
        min_o = _as_int(min_overall)
        max_o = _as_int(max_overall)

        hits = []
        for p in self.players_sorted:
            if club_key and p.club_key != club_key:
                continue
            if nat_q and nat_q not in p.nationality.lower():
                continue
            if pos_q and p.position != pos_q:
                continue
            if min_o is not None and p.overall < min_o:
                continue
            if max_o is not None and p.overall > max_o:
                continue
            if name_q and name_q not in strip_accents(p.name).lower():
                continue
            hits.append(p)
        return {
            "total": len(hits),
            "players": [self._player_dict(p) for p in hits[:_clamp(limit)]],
        }

    def get_player(self, name: str) -> dict:
        q = strip_accents(name).strip().lower()
        if not q:
            raise NotFound("Empty player name")
        # exact normalized match first
        for p in self.players_sorted:
            if strip_accents(p.name).lower() == q:
                return self._player_dict(p, with_skills=True)
        # then token-set match ("gabriel barbosA" ~ "Gabriel Barbosa")
        q_tokens = set(re.split(r"[^a-z0-9]+", q)) - {""}
        best, best_score = None, 0
        for p in self.players_sorted:
            tokens = set(re.split(r"[^a-z0-9]+", strip_accents(p.name).lower())) - {""}
            if tokens and q_tokens and q_tokens <= tokens:
                score = len(tokens)
                if score > best_score:
                    best, best_score = p, score
        if best is None:
            partial = [p for p in self.players_sorted
                       if q in strip_accents(p.name).lower()]
            if partial:
                best = max(partial, key=lambda p: p.overall)
        if best is None:
            raise NotFound(f"Player {name!r} not found in the FIFA dataset")
        return self._player_dict(best, with_skills=True)

    def players_at_club(self, club: str, limit: int = DEFAULT_LIMIT) -> dict:
        key = self.resolve_team(club)
        members = self.players_by_club.get(key, [])
        members.sort(key=lambda p: -p.overall)
        avg = round(sum(p.overall for p in members) / len(members), 1) if members else 0.0
        response = {
            "club": self.team_display(key),
            "total_players": len(members),
            "total": len(members),           # alias shared with search_players
            "average_overall": avg,
            "players": [self._player_dict(p) for p in members[:_clamp(limit)]],
        }
        if not members:
            response["note"] = (
                "The bundled FIFA dataset (FIFA 19 edition) does not include "
                "squad data for every Brazilian club; try clubs like "
                "Cruzeiro, Santos, Fluminense, Grêmio or Atlético Mineiro.")
        return response

    # ------------------------------------------------------------------
    # statistics
    # ------------------------------------------------------------------

    def statistics(self, competition: str | None = None,
                   season: int | None = None) -> dict:
        comp = self.resolve_competition(competition)
        season = _as_int(season)
        pool = [m for m in self.matches
                if self._filters_apply(m, comp, season, None, None)]
        stats = aggregate_stats(pool)
        return {
            "scope": {"competition": comp, "season": season},
            **stats,
            "biggest_wins": [
                {
                    "date": x["match"].date.isoformat() if x["match"].date else None,
                    "winner": self.team_display(x["winner"]),
                    "score": f"{x['winner_goals']}-{x['loser_goals']}",
                    "loser": self.team_display(x["loser"]),
                    "competition": x["match"].competition,
                }
                for x in biggest_wins(pool, top=10)
            ],
            "best_home_records": [
                {"team": self.team_display(x["team"]), **x["record"]}
                for x in best_venues(pool, "home", top=5)
            ],
            "best_away_records": [
                {"team": self.team_display(x["team"]), **x["record"]}
                for x in best_venues(pool, "away", top=5)
            ],
        }

    def compare_seasons(self, competition: str, season_a: int,
                        season_b: int) -> dict:
        comp = self.resolve_competition(competition)
        season_a, season_b = _as_int(season_a), _as_int(season_b)
        per = {s: self.matches_by_comp_season.get((comp, s), [])
               for s in (season_a, season_b)}
        return {
            "competition": comp,
            "seasons": season_comparison(per),
            "champions": {
                s: (self.team_display(standings_table(ms)[0]["team"])
                    if ms else None)
                for s, ms in per.items()
            },
        }

    # ------------------------------------------------------------------
    # derbies
    # ------------------------------------------------------------------

    def derbies(self, season: int | None = None,
                competition: str | None = None) -> dict:
        season = _as_int(season)
        comp = self.resolve_competition(competition)
        out = []
        for name, (a, b) in self.derby_pairs:
            pool = [m for m in self.matches_by_team[a]
                    if b in (m.home_key, m.away_key)
                    and self._filters_apply(m, comp, season, None, None)]
            if not pool:
                continue
            rec = h2h_record(pool, a, b)
            out.append({
                "derby": name,
                "team_a": self.team_display(a),
                "team_b": self.team_display(b),
                "team_a_wins": rec["team_a_wins"],
                "team_b_wins": rec["team_b_wins"],
                "draws": rec["draws"],
                "total_matches": len(pool),
                "recent": [self.match_dict(m, self)
                           for m in sorted(pool, key=lambda m: m.date or date.min)][-3:],
            })
        return {"season": season, "derbies": out}

    # ------------------------------------------------------------------
    # status / catalog
    # ------------------------------------------------------------------

    def status(self) -> dict:
        sources = defaultdict(int)
        for m in self.matches:
            sources[m.source] += 1
        return {
            "matches": len(self.matches),
            "players": len(self.players),
            "teams": len(self.registry.display_names()),
            "competitions": sorted({m.competition for m in self.matches}),
            "sources": dict(sorted(sources.items())),
        }


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _as_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clamp(limit) -> int:
    n = _as_int(limit) or DEFAULT_LIMIT
    return max(1, min(n, MAX_LIMIT))
