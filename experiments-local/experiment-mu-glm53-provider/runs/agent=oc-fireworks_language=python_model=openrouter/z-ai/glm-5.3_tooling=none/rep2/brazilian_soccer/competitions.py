"""Canonical competition ids, display names and query aliases."""

from __future__ import annotations

from .normalize import fold

COMPETITIONS: dict[str, str] = {
    "brasileirao": "Brasileirão Serie A",
    "serie_b": "Brasileirão Serie B",
    "serie_c": "Brasileirão Serie C",
    "copa_do_brasil": "Copa do Brasil",
    "libertadores": "Copa Libertadores",
}

_LEAGUES = {"brasileirao", "serie_b", "serie_c"}

COMP_ALIASES: dict[str, str] = {}
for _key in COMPETITIONS:
    _display = COMPETITIONS[_key]
    COMP_ALIASES[fold(_key)] = _key
    COMP_ALIASES[fold(_display)] = _key
COMP_ALIASES.update(
    {
        fold("serie a"): "brasileirao",
        fold("seriea"): "brasileirao",
        fold("série a"): "brasileirao",
        fold("brasileirao serie a"): "brasileirao",
        fold("campeonato brasileiro"): "brasileirao",
        fold("serieb"): "serie_b",
        fold("serie b"): "serie_b",
        fold("seriec"): "serie_c",
        fold("serie c"): "serie_c",
        fold("copa"): "copa_do_brasil",
        fold("cup"): "copa_do_brasil",
        fold("brazilian cup"): "copa_do_brasil",
        fold("copa brasil"): "copa_do_brasil",
        fold("libertadores"): "libertadores",
        fold("conmebol libertadores"): "libertadores",
        fold("copa libertadores"): "libertadores",
    }
)


def resolve_competition(query: str | None) -> str | None:
    """Resolve a user-supplied competition name to a canonical id."""
    if not query:
        return None
    key = fold(query)
    if key in COMPETITIONS:
        return key
    return COMP_ALIASES.get(key)


def is_league(competition: str) -> bool:
    return competition in _LEAGUES
