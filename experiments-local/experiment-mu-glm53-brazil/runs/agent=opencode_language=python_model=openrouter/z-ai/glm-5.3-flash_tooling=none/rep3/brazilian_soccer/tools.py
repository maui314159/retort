"""MCP tool layer: natural-language router + tool implementations.

The MCP server exposes structured tools (see ``server.py``); an LLM client
is expected to choose the right tool and parameters.  ``answer_question``
additionally provides a deterministic best-effort router so simple
questions can be answered without an LLM: it detects years, team names,
competition words and intent keywords, and dispatches to the matching
``SoccerStore`` method.

Router intent order (first match wins):
1. head-to-head   - two team names + "vs"/"against"/"x"
2. standings      - "standings"/"table"/"champion"/"won"/"relegated" + year
3. derbies        - "derby"/"rivalry"/"clássico"
4. players        - "player"/"who is"/"rating"/"squad"
5. statistics     - "average goals"/"biggest win"/"best home"/"best away"
6. team stats     - "record"/"wins" + one team
7. matches        - fallback: match search with detected teams/season
"""

from __future__ import annotations

import re

from .normalize import strip_accents
from .store import NotFound, SoccerStore

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _detect_years(question: str) -> list[int]:
    return [int(y) for y in _YEAR_RE.findall(question)]


def _match_forms(display: str) -> list[str]:
    """Text forms a team display name can match in a question.

    "Flamengo-RJ" matches "Flamengo" too; "Atlético-MG" matches
    "Atlético" (popularity disambiguates collisions).
    """
    forms = {strip_accents(display).lower()}
    base = re.split(r"\s*[-–]\s*", display)[0]
    base = strip_accents(base).lower()
    if len(base) >= 4:
        forms.add(base)
    return sorted(forms, key=len, reverse=True)


def _detect_teams(store: SoccerStore, question: str) -> list[str]:
    """Find team mentions by scanning display names (longest first)."""
    q = strip_accents(question).lower()
    found: list[tuple[int, str]] = []
    for key, display in store.registry.display_names().items():
        for form in _match_forms(display):
            idx = q.find(form)
            if idx >= 0:
                found.append((idx, display))
                break
    # Longest display name at each position wins; keep reading order.
    found.sort(key=lambda t: (t[0], -len(t[1])))
    picked: list[str] = []
    last_end = -1
    for idx, display in found:
        if idx >= last_end:
            picked.append(display)
            last_end = idx + len(display)
        if len(picked) == 2:
            break
    return picked


def _detect_competition(store: SoccerStore, question: str) -> str | None:
    q = strip_accents(question).lower()
    if "libertadores" in q:
        return "Copa Libertadores"
    if "copa do brasil" in q or "brazilian cup" in q:
        return "Copa do Brasil"
    if "serie b" in q:
        return "Brasileirão Serie B"
    if "serie c" in q:
        return "Brasileirão Serie C"
    if "serie a" in q or "brasileirao" in q or "brasileirão" in q:
        return "Brasileirão Serie A"
    return None


def answer_question(store: SoccerStore, question: str) -> dict:
    """Best-effort deterministic routing of a natural-language question."""
    q = strip_accents(question).lower()
    years = _detect_years(question)
    year = years[-1] if years else None
    competition = _detect_competition(store, question)
    teams = _detect_teams(store, question)

    # 1. head-to-head
    if len(teams) == 2 and any(w in q for w in (" vs ", " x ", " against", " head-to-head", " head to head")):
        return {"tool": "get_head_to_head",
                "result": store.head_to_head(teams[0], teams[1], competition)}

    # 2. standings / champion / relegation
    if any(w in q for w in ("standings", "table", "champion", " who won",
                            "relegat", "won the")):
        comp = competition or "Brasileirão Serie A"
        if year is None:
            raise NotFound("Which season (year)? e.g. 'Who won the 2019 Brasileirão?'")
        result = store.standings(comp, year, top=6)
        if "relegat" in q:
            result = {"relegation_zone": result.get("relegation_zone")}
        elif any(w in q for w in ("who won", "champion")):
            result = {"champion": result["champion"]}
        return {"tool": "get_standings", "result": result}

    # 3. derbies
    if any(w in q for w in ("derby", "derbies", "rivalry", "classico", "clássico")):
        return {"tool": "get_derbies",
                "result": store.derbies(season=year, competition=competition)}

    # 3b. season comparison ("compare the 2018 and 2019 seasons")
    if "compare" in q and len(years) >= 2:
        comp = competition or "Brasileirão Serie A"
        return {"tool": "compare_seasons",
                "result": store.compare_seasons(comp, years[0], years[1])}

    # 3c. club participation ("what competitions has X played in?")
    if "competition" in q and len(teams) == 1:
        return {"tool": "get_team_history",
                "result": store.team_history(teams[0])}

    # 4. players
    if any(w in q for w in ("player", "who is", "rating", "overall", "squad", "forwards")):
        if len(teams) == 1:
            return {"tool": "search_players_at_club",
                    "result": store.players_at_club(teams[0])}
        m = re.search(r"who\s+is\s+(.+?)[\?\.!]?$", question.strip(), re.I)
        if m:
            try:
                return {"tool": "get_player",
                        "result": store.get_player(m.group(1).strip())}
            except NotFound as exc:
                return {"tool": "get_player",
                        "result": {"found": False, "message": str(exc)}}
        if "brazil" in q:
            return {"tool": "search_players",
                    "result": store.search_players(nationality="brazil",
                                                   min_overall=75, limit=10)}
        return {"tool": "search_players",
                "result": store.search_players(name=question, limit=5)}

    # 5. statistics
    if any(w in q for w in ("average goals", "goals per match", "biggest win",
                            "best home", "best away", "home win")):
        return {"tool": "get_statistics",
                "result": store.statistics(competition=competition, season=year)}

    # 6. team stats
    if len(teams) == 1 and any(w in q for w in ("record", "wins", "won how", "how many")):
        venue = None
        if "home" in q:
            venue = "home"
        elif "away" in q:
            venue = "away"
        return {"tool": "get_team_stats",
                "result": store.team_stats(teams[0], season=year,
                                           competition=competition, venue=venue)}

    # 7. match search fallback
    if teams:
        kwargs = {"team": teams[0]}
        if len(teams) == 2:
            kwargs["opponent"] = teams[1]
        if year:
            kwargs["season"] = year
        if competition:
            kwargs["competition"] = competition
        if "last" in q or "when did" in q:
            kwargs["limit"] = 5
            kwargs["order"] = "desc"
        return {"tool": "search_matches", "result": store.search_matches(**kwargs)}

    raise NotFound(
        "Could not route the question. Structured tools are available for "
        "match search, head-to-head, team stats, standings, players, "
        "statistics and derbies.")
