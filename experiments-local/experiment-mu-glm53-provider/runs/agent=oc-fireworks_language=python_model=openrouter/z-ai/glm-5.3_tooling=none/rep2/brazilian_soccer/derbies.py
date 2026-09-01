"""Registry of famous Brazilian derby (clássico) rivalries.

Used by the ``derby_matches`` tool so that questions like "Show me all
derbies in 2023" or "When was the last Gre-Nal?" map to concrete team pairs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Derby:
    name: str          # popular name, e.g. "Fla-Flu"
    team_a: str        # canonical team key
    team_b: str
    region: str        # "Rio de Janeiro", "São Paulo", ...


DERBIES: list[Derby] = [
    Derby("Fla-Flu", "flamengorj", "fluminenserj", "Rio de Janeiro"),
    Derby("Clássico dos Milhões", "flamengorj", "vascodagamarj", "Rio de Janeiro"),
    Derby("Clássico Vovô", "botafogorj", "vascodagamarj", "Rio de Janeiro"),
    Derby("Clássico dos Gigantes", "fluminenserj", "vascodagamarj", "Rio de Janeiro"),
    Derby("Derby Paulista", "corinthianssp", "palmeirassp", "São Paulo"),
    Derby("Majestoso", "corinthianssp", "saopaulosp", "São Paulo"),
    Derby("Choque-Rei", "palmeirassp", "saopaulosp", "São Paulo"),
    Derby("Gre-Nal", "gremiors", "internacionalrs", "Rio Grande do Sul"),
    Derby("Ba-Vi", "bahiaba", "vitoriaba", "Bahia"),
    Derby("Atletiba", "atleticopr", "coritibapr", "Paraná"),
]


def find_derby(query: str) -> Derby | None:
    """Match a derby by popular name (case/accent-insensitive substring)."""
    from .normalize import fold

    if not query:
        return None
    key = fold(query)
    best: Derby | None = None
    for derby in DERBIES:
        name_key = fold(derby.name)
        if key == name_key:
            return derby
        if key in name_key or name_key in key:
            best = best or derby
    return best
