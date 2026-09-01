"""Curated knowledge about classic Brazilian soccer derbies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Derby:
    """A traditional rivalry between two clubs."""

    name: str
    description: str
    team_a: str
    team_b: str


DERBIES = [
    Derby(
        name="Fla-Flu",
        description="Flamengo vs Fluminense, the classic Rio de Janeiro derby",
        team_a="flamengo-rj",
        team_b="fluminense-rj",
    ),
    Derby(
        name="Clássico dos Milhões",
        description="Flamengo vs Vasco da Gama, Rio de Janeiro",
        team_a="flamengo-rj",
        team_b="vasco da gama",
    ),
    Derby(
        name="Gre-Nal",
        description="Grêmio vs Internacional, the Porto Alegre derby",
        team_a="gremio",
        team_b="internacional-rs",
    ),
    Derby(
        name="Choque-Rei",
        description="Palmeiras vs São Paulo, São Paulo derby",
        team_a="palmeiras",
        team_b="sao paulo",
    ),
    Derby(
        name="Majestoso",
        description="Corinthians vs Palmeiras, the Paulista derby",
        team_a="corinthians",
        team_b="palmeiras",
    ),
    Derby(
        name="San-São",
        description="Santos vs São Paulo, São Paulo derby",
        team_a="santos-sp",
        team_b="sao paulo",
    ),
    Derby(
        name="Clássico Mineiro",
        description="Atlético Mineiro vs Cruzeiro, the Minas Gerais derby",
        team_a="atletico-mg",
        team_b="cruzeiro",
    ),
    Derby(
        name="Ba-Vi",
        description="Bahia vs Vitória, the Bahia derby",
        team_a="bahia",
        team_b="vitoria-ba",
    ),
    Derby(
        name="Atletiba",
        description="Athletico Paranaense vs Coritiba, the Paraná derby",
        team_a="atletico-pr",
        team_b="coritiba",
    ),
    Derby(
        name="Clássico dos Gigantes",
        description="Fluminense vs Vasco da Gama, Rio de Janeiro",
        team_a="fluminense-rj",
        team_b="vasco da gama",
    ),
]


def find_derby(query: str) -> Derby | None:
    """Match a derby by name or by one of its team keys."""
    from brazilian_soccer_mcp.normalize import clean_name, strip_accents

    cleaned = clean_name(query)
    for derby in DERBIES:
        if clean_name(derby.name) == cleaned:
            return derby
        if strip_accents(derby.name).lower().replace("-", " ") == cleaned.replace("-", " "):
            return derby
    return None
