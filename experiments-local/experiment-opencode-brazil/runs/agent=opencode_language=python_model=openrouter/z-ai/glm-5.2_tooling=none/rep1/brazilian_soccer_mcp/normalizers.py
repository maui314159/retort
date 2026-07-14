import re
import unicodedata
from datetime import date, datetime

STATES = {
    "SP", "RJ", "MG", "RS", "PR", "SC", "PE", "BA", "GO", "CE", "DF", "ES",
    "MS", "MT", "PA", "PB", "PI", "RN", "TO", "SE", "AL", "AM", "AP", "RR",
    "RO", "AC", "MA",
}

_STATES_NAMES = {
    "sao paulo", "rio de janeiro", "minas gerais", "rio grande do sul",
    "parana", "santa catarina", "pernambuco", "bahia", "goias", "ceara",
    "distrito federal", "espirito santo", "mato grosdo do sul", "mato grosso",
    "para", "paraiba", "piaui", "rio grande do norte", "tocantins", "sergipe",
    "alagoas", "amazonas", "amapa", "roraima", "rondonia", "acre", "maranhao",
    "mineiro", "paranaense", "goianiense", "recife", "natal", "feira",
    "de pelotas", "da conquista",
}


def _strip_accents(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(ch)
    )


def _clean(name: str) -> str:
    n = str(name)
    n = re.sub(r"\([^)]*\)", " ", n)
    n = _strip_accents(n)
    n = n.lower()
    n = n.replace("-", " ")
    n = n.replace("/", " ")
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


_CANONICAL_ALIASES = [
    ("flamengo", ["flamengo", "flamengo rj"]),
    ("fluminense", ["fluminense", "fluminense rj"]),
    ("palmeiras", ["palmeiras", "palmeiras sp"]),
    ("corinthians", [
        "corinthians", "corinthians sp", "sport club corinthians paulista",
        "corinthians paulista",
    ]),
    ("sao_paulo", ["sao paulo", "sao paulo sp"]),
    ("santos", ["santos", "santos sp"]),
    ("vasco", ["vasco", "vasco da gama", "vasco da gama rj"]),
    ("botafogo", ["botafogo", "botafogo rj", "botafogo de futebol e regatas"]),
    ("gremio", ["gremio", "gremio rs"]),
    ("internacional", ["internacional", "internacional rs", "inter porto alegre"]),
    ("cruzeiro", ["cruzeiro", "cruzeiro mg"]),
    ("atletico_mg", [
        "atletico mg", "atletico mineiro", "atletico mineiro mg",
        "athletic club mg",
    ]),
    ("athletico_pr", [
        "athletico pr", "athletico paranaense", "athletico paranaense pr",
        "atletico pr", "atletico paranaense", "atletico paranaense pr",
        "ca parana",
    ]),
    ("atletico_go", ["atletico go", "atletico goianiense", "atletico goianiense go"]),
    ("coritiba", ["coritiba", "coritiba pr"]),
    ("bahia", ["bahia", "bahia ba", "ec bahia", "esporte clube bahia"]),
    ("sport", ["sport", "sport pe", "sport recife", "sport club do recife"]),
    ("nautico", ["nautico", "nautico pe", "nautico capibaribe"]),
    ("figueirense", ["figueirense", "figueirense sc"]),
    ("ponte_preta", ["ponte preta", "ponte preta sp", "ponte pretas"]),
    ("portuguesa", ["portuguesa", "portuguesa sp", "portuguesa santista"]),
    ("portuguesa_rj", ["portuguesa rj", "portuguesa desportos", "portuguesa carioca"]),
    ("goias", ["goias", "goias go", "goias ec"]),
    ("paysandu", ["paysandu", "paysandu pa"]),
    ("guarani", ["guarani", "guarani sp"]),
    ("vitoria_ba", ["vitoria", "vitoria ba", "ec vitoria", "vitoria ec", "esporte clube vitoria"]),
    ("vitoria_es", ["vitoria es", "vitoria f c", "vitoria da conquista vitoria"]),
    ("fortaleza", ["fortaleza", "fortaleza ce", "fortaleza ec", "fortaleza fc"]),
    ("juventude", ["juventude", "juventude rs", "ec juventude"]),
    ("criciuma", ["criciuma", "criciuma sc"]),
    ("avai", ["avai", "avai sc"]),
    ("chapecoense", ["chapecoense", "chapecoense sc"]),
    ("america_mg", [
        "america mg", "america mineiro", "america mineiro mg",
        "america belo horizonte",
    ]),
    ("america_rn", [
        "america rn", "america de natal", "america de natal rn",
        "america fc natal", "america rn ec",
    ]),
    ("cuiaba", ["cuiaba", "cuiaba mt", "cuiaba ec", "cuiaba fc"]),
    ("bragantino", [
        "bragantino", "bragantino sp", "rb bragantino", "red bull bragantino",
        "red bull bragantino sp",
    ]),
    ("santa_cruz", ["santa cruz pe", "santa cruz recife"]),
    ("csa", ["csa", "csa al", "csa alagoas"]),
    ("ceara", ["ceara", "ceara ce", "ceara sporting"]),
    ("parana_clube", ["parana", "parana pr", "parana clube"]),
    ("joinville", ["joinville", "joinville sc"]),
    ("santo_andre", ["santo andre", "santo andre sp"]),
    ("ipatinga", ["ipatinga", "ipatinga mg"]),
    ("vila_nova", ["vila nova", "vila nova go", "vila nova goiania"]),
    ("athletico", ["athletico"]),
]

_DISPLAY = {
    "flamengo": "Flamengo",
    "fluminense": "Fluminense",
    "palmeiras": "Palmeiras",
    "corinthians": "Corinthians",
    "sao_paulo": "Sao Paulo",
    "santos": "Santos",
    "vasco": "Vasco da Gama",
    "botafogo": "Botafogo",
    "gremio": "Gremio",
    "internacional": "Internacional",
    "cruzeiro": "Cruzeiro",
    "atletico_mg": "Atletico-MG",
    "athletico_pr": "Athletico-PR",
    "atletico_go": "Atletico-GO",
    "coritiba": "Coritiba",
    "bahia": "Bahia",
    "sport": "Sport",
    "nautico": "Nautico",
    "figueirense": "Figueirense",
    "ponte_preta": "Ponte Preta",
    "portuguesa": "Portuguesa",
    "portuguesa_rj": "Portuguesa-RJ",
    "goias": "Goias",
    "paysandu": "Paysandu",
    "guarani": "Guarani",
    "vitoria_ba": "Vitoria",
    "vitoria_es": "Vitoria-ES",
    "fortaleza": "Fortaleza",
    "juventude": "Juventude",
    "criciuma": "Criciuma",
    "avai": "Avai",
    "chapecoense": "Chapecoense",
    "america_mg": "America-MG",
    "america_rn": "America-RN",
    "cuiaba": "Cuiaba",
    "bragantino": "Bragantino",
    "athletico": "Athletico",
}

_ALIASES: dict[str, str] = {}
for canonical_id, aliases in _CANONICAL_ALIASES:
    for alias in aliases:
        _ALIASES[alias] = canonical_id

_BASE_STATES: dict[str, set] = {}


def set_base_states(mapping: dict) -> None:
    global _BASE_STATES
    _BASE_STATES = mapping


def canonical_team_id(name: str) -> str:
    cleaned = _clean(name)
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    tokens = cleaned.split()
    if len(tokens) >= 2 and tokens[-1] in STATES:
        base = " ".join(tokens[:-1])
        states = _BASE_STATES.get(base)
        if states is not None and len(states) == 1:
            return base
    return cleaned


def team_display_name(canonical_id: str) -> str:
    if canonical_id in _DISPLAY:
        return _DISPLAY[canonical_id]
    return " ".join(part.capitalize() for part in canonical_id.split())


_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M")


def parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


DERBIES = [
    ("flamengo", "fluminense", "Fla-Flu"),
    ("gremio", "internacional", "Gre-Nal"),
    ("santos", "palmeiras", "San-Pal"),
    ("corinthians", "sao_paulo", "Majestoso"),
    ("vasco", "botafogo", "Vasco-Bota"),
    ("cruzeiro", "atletico_mg", "Clube do Mai"),
    ("bahia", "vitoria_ba", "Ba-Vi"),
    ("sport", "nautico", "Classico dos Classicos Recife"),
    ("ceara", "fortaleza", "Ce-Fort"),
]
