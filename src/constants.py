"""Constantes globais do painel (paths, colunas, Supabase, mapas de estados).

Extraído de monitoramento_V3.py (Fase 3). Módulo-folha: depende apenas de os/glob.
"""

import os
import glob

# BASE_DIR = raiz do projeto (este arquivo vive em src/, por isso sobe um nível).
BASE_DIR                  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA                     = os.getenv("CAMERITE_MONITORAMENTO_PASTA", BASE_DIR)

CSV_GOV                   = os.path.join(PASTA, "GOV_extracao_cameras.csv")
XLSX_CLIENTES             = os.path.join(PASTA, "nome_clientes.xlsx")


def caminho_xlsx_clientes() -> str | None:
    """Localiza a base de clientes, aceitando nome_clientes.xlsx ou variações como nome_clientes(1).xlsx."""
    candidatos = [XLSX_CLIENTES]
    candidatos.extend(sorted(glob.glob(os.path.join(PASTA, "nome_clientes*.xlsx")), key=lambda p: os.path.getmtime(p), reverse=True))
    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    return None
IMPORTACAO_INDIVIDUAL_DIR = os.path.join(PASTA, "_BKPS_importacao_individual")
DB_PATH                   = os.path.join(PASTA, "historico.db")
GEO_CACHE_PATH            = os.path.join(PASTA, "geocode_cache.json")
BRAZIL_STATES_GEOJSON_URL = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
BRAZIL_STATES_GEOJSON_PATH = os.path.join(PASTA, "brazil_states.geojson")
COLUNAS_PAINEL            = 4
DATA_PARSE_VERSION = "2026-05-15-br-date-v1"
AJUSTES_REVISAO_COMPARATIVO_2026_05_27 = True

BRAZIL_STATE_NAME_MAP = {
    "ac": "Acre", "acre": "Acre",
    "al": "Alagoas", "alagoas": "Alagoas",
    "ap": "Amapá", "amapa": "Amapá",
    "am": "Amazonas", "amazonas": "Amazonas",
    "ba": "Bahia", "bahia": "Bahia",
    "ce": "Ceará", "ceara": "Ceará",
    "df": "Distrito Federal", "distritofederal": "Distrito Federal",
    "es": "Espírito Santo", "espiritosanto": "Espírito Santo",
    "go": "Goiás", "goias": "Goiás",
    "ma": "Maranhão", "maranhao": "Maranhão",
    "mt": "Mato Grosso", "matogrosso": "Mato Grosso",
    "ms": "Mato Grosso do Sul", "matogrossodosul": "Mato Grosso do Sul",
    "mg": "Minas Gerais", "minasgerais": "Minas Gerais",
    "pa": "Pará", "para": "Pará",
    "pb": "Paraíba", "paraiba": "Paraíba",
    "pr": "Paraná", "parana": "Paraná",
    "pe": "Pernambuco", "pernambuco": "Pernambuco",
    "pi": "Piauí", "piaui": "Piauí",
    "rj": "Rio de Janeiro", "riodejaneiro": "Rio de Janeiro",
    "rn": "Rio Grande do Norte", "riograndedonorte": "Rio Grande do Norte",
    "rs": "Rio Grande do Sul", "riograndedosul": "Rio Grande do Sul",
    "ro": "Rondônia", "rondonia": "Rondônia",
    "rr": "Roraima", "roraima": "Roraima",
    "sc": "Santa Catarina", "santacatarina": "Santa Catarina",
    "sp": "São Paulo", "saopaulo": "São Paulo",
    "se": "Sergipe", "sergipe": "Sergipe",
    "to": "Tocantins", "tocantins": "Tocantins",
}

BRAZIL_STATE_CAPITAIS = {
    "Acre": {"city": "Rio Branco", "lat": -9.97499, "lon": -67.8243},
    "Alagoas": {"city": "Maceió", "lat": -9.66599, "lon": -35.7350},
    "Amapá": {"city": "Macapá", "lat": 0.03494, "lon": -51.06939},
    "Amazonas": {"city": "Manaus", "lat": -3.10194, "lon": -60.0250},
    "Bahia": {"city": "Salvador", "lat": -12.9714, "lon": -38.5014},
    "Ceará": {"city": "Fortaleza", "lat": -3.71722, "lon": -38.5434},
    "Distrito Federal": {"city": "Brasília", "lat": -15.7939, "lon": -47.8828},
    "Espírito Santo": {"city": "Vitória", "lat": -20.3155, "lon": -40.3128},
    "Goiás": {"city": "Goiânia", "lat": -16.6869, "lon": -49.2648},
    "Maranhão": {"city": "São Luís", "lat": -2.53874, "lon": -44.2825},
    "Mato Grosso": {"city": "Cuiabá", "lat": -15.6010, "lon": -56.0979},
    "Mato Grosso do Sul": {"city": "Campo Grande", "lat": -20.4428, "lon": -54.6464},
    "Minas Gerais": {"city": "Belo Horizonte", "lat": -19.9167, "lon": -43.9345},
    "Pará": {"city": "Belém", "lat": -1.45583, "lon": -48.5044},
    "Paraíba": {"city": "João Pessoa", "lat": -7.11533, "lon": -34.8631},
    "Paraná": {"city": "Curitiba", "lat": -25.4284, "lon": -49.2733},
    "Pernambuco": {"city": "Recife", "lat": -8.05389, "lon": -34.8811},
    "Piauí": {"city": "Teresina", "lat": -5.09194, "lon": -42.8034},
    "Rio de Janeiro": {"city": "Rio de Janeiro", "lat": -22.9099, "lon": -43.2095},
    "Rio Grande do Norte": {"city": "Natal", "lat": -5.79448, "lon": -35.2110},
    "Rio Grande do Sul": {"city": "Porto Alegre", "lat": -30.0346, "lon": -51.2177},
    "Rondônia": {"city": "Porto Velho", "lat": -8.76077, "lon": -63.8999},
    "Roraima": {"city": "Boa Vista", "lat": 2.82092, "lon": -60.6733},
    "Santa Catarina": {"city": "Florianópolis", "lat": -27.5954, "lon": -48.5480},
    "São Paulo": {"city": "São Paulo", "lat": -23.5505, "lon": -46.6333},
    "Sergipe": {"city": "Aracaju", "lat": -10.9111, "lon": -37.0717},
    "Tocantins": {"city": "Palmas", "lat": -10.1846, "lon": -48.3336},
}

# Mapeamento de colunas do CSV para nomes internos
COL_STATUS     = "Status_da_Camera"
COL_WL         = "ID_Whitelabel"
COL_EMPRESA    = "Nome_Empresa"
COL_ID_CAM     = "ID_da_Camera"
COL_NOME_CAM   = "Nome_da_Camera"
COL_ULT_ATU    = "Ultima_Atualizacao"
COL_OBS        = "Observacoes"
COL_DATA_CAD   = "Data_de_Cadastro"
COL_PLANO      = "Plano_Contratado"
COL_DATA_INAT  = "Data_de_Inativacao"

# ─────────────────────────────────────────────
# SUPABASE / BD ONLINE
# ─────────────────────────────────────────────
# Configure no Streamlit Cloud em Settings > Secrets:
# SUPABASE_URL = "https://xxxx.supabase.co"
# SUPABASE_KEY = "sua-chave-publishable"
# Também aceita SUPABASE_ANON_KEY, caso você prefira esse nome.
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "cameras_origem")
SUPABASE_PAGE_SIZE = 1000

FAIXAS_TEMPO = [
    "Todas",
    "Menos de 1h",
    "1h a 6h",
    "6h a 24h",
    "1 a 3 dias",
    "3 a 7 dias",
    "Mais de 7 dias",
    "Sem data",
]

FAIXAS_TEMPO_OFFLINE = [
    "Todas",
    "Menos de 1 dia",
    "Entre 1 e 3 dias",
    "3 a 7 dias",
    "Acima de 7 dias",
    "Sem data",
]

STATUS_CLIENTE = [
    "Todos",
    "Crítico (>10%)",
    "Atenção (5-10%)",
    "Saudável (0-5%)",
]
