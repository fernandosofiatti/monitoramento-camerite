import streamlit as st
import pandas as pd
import os
import sqlite3
import io
import json
import re
import unicodedata
import math
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
import glob
import html
import time

THEME_OPTIONS = {
    "theme.base": "light",
    "theme.primaryColor": "#0088cc",
    "theme.backgroundColor": "#f5f8fb",
    "theme.secondaryBackgroundColor": "#ffffff",
    "theme.textColor": "#102a3f",
    "theme.dataframeHeaderBackgroundColor": "#e8f7fc",
    "theme.font": "sans serif",
}

for option, value in THEME_OPTIONS.items():
    try:
        st._config.set_option(option, value)
    except Exception:
        pass

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Camerite BI · Monitoramento",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background-color: #f5f8fb !important;
    color: #12263a !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stHeader"]          { background: transparent !important; }
[data-testid="stSidebar"]         { background: #ffffff !important; border-right: 1px solid #dbe8f2 !important; }
[data-testid="block-container"]   { padding: 2rem 2.5rem !important; max-width: 1600px; }
section[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }

/* ── Sidebar ── */
.sidebar-logo {
    display: flex; align-items: center; gap: 10px;
    padding: 0 0 1.5rem; border-bottom: 1px solid #dbe8f2; margin-bottom: 1.5rem;
}
.sidebar-logo-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #0088cc, #00bcd4);
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 18px; flex-shrink: 0;
}
.sidebar-logo-img { height: 30px; width: auto; }
.sidebar-logo-text { font-size: 15px; font-weight: 700; color: #102a3f; line-height: 1; }
.sidebar-logo-sub  { font-size: 10px; color: #0088cc; margin-top: 2px; }
.nav-section {
    font-size: 10px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; color: #0088cc; margin: 1.2rem 0 .5rem;
}

/* ── Page header ── */
.page-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #dbe8f2;
}
.page-title { font-size: 24px; font-weight: 700; color: #102a3f; letter-spacing: -.4px; }
.page-sub   { font-size: 13px; color: #4f6f85; margin-top: 3px; }
.page-badge {
    font-family: 'DM Mono', monospace; font-size: 11px; color: #007ab8;
    background: #e8f7fc; padding: 6px 14px; border-radius: 8px;
    border: 1px solid #b9e7f4; white-space: nowrap;
}

/* ── KPI cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 1.5rem; }
.kpi-card {
    background: #ffffff; border: 1px solid #dbe8f2; border-radius: 8px;
    padding: 20px 20px 16px; position: relative; overflow: hidden;
    box-shadow: 0 10px 28px rgba(16, 42, 63, .06);
}
.kpi-card::after {
    content:''; position:absolute; top:0; left:0; right:0; height:3px; border-radius:8px 8px 0 0;
}
.kpi-alert::after   { background: linear-gradient(90deg,#ef4444,#dc2626); }
.kpi-warn::after    { background: linear-gradient(90deg,#f59e0b,#d97706); }
.kpi-ok::after      { background: linear-gradient(90deg,#14b8a6,#059669); }
.kpi-neutral::after { background: linear-gradient(90deg,#0088cc,#00bcd4); }

/* SELETOR DEFINITIVO: Altera textos secundarios do card, exceto o valor principal */
.kpi-card *:not(.kpi-value):not(.val-alert):not(.val-warn):not(.val-ok):not(.val-purple) {
    color: #4f6f85 !important;
    -webkit-text-fill-color: #4f6f85 !important;
    opacity: 1 !important;
}

/* Garante que o valor principal (os números grandes) mantenha a cor de status */
.kpi-value, .val-alert, .val-warn, .val-ok, .val-purple {
    font-size: 40px !important;
    font-weight: 700 !important;
    font-family: 'DM Mono', monospace !important;
    -webkit-text-fill-color: currentColor !important; /* Impede o texto secundario de sobrescrever o status */
}

.val-alert  { color: #f87171 !important; }
.val-warn   { color: #fbbf24 !important; }
.val-ok     { color: #14b8a6 !important; }
.val-purple { color: #0088cc !important; }
            
/* ── Unit cards ── */
.unit-card {
    background: #ffffff; border: 1px solid #dbe8f2; border-radius: 8px;
    padding: 14px 12px 12px; position: relative; overflow: hidden;
    box-shadow: 0 8px 22px rgba(16, 42, 63, .05);
    display: flex; flex-direction: column; height: 100%;
}
.unit-card::before {
    content:''; position:absolute; top:0; left:0; right:0;
    height:3px; border-radius:8px 8px 0 0;
}
.card-red::before    { background: linear-gradient(90deg,#ef4444,#dc2626); }
.card-yellow::before { background: linear-gradient(90deg,#f59e0b,#d97706); }
.card-ok::before     { background: linear-gradient(90deg,#14b8a6,#059669); }
.unit-name {
    font-size:9px; font-weight:600; letter-spacing:.8px; text-transform:uppercase;
    color:#007ab8; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.unit-count { font-size:28px; font-weight:700; line-height:1.1; font-family:'DM Mono',monospace; margin-top:4px; margin-bottom:2px; }
.count-red    { color:#f87171; }
.count-yellow { color:#fbbf24; }
.count-ok     { color:#14b8a6; }
.unit-label { font-size:9px; margin-top:2px; margin-bottom:6px; font-weight:500; letter-spacing:.3px; color:#4f6f85; line-height:1.3; }
.label-red    { color:#ff8e8e; }
.label-yellow { color:#c98500; }
.label-ok     { color:#0f9f8f; }
.prog-track { margin: 6px 0 6px 0; height:3px; background:#dbe8f2; border-radius:99px; overflow:hidden; }
.prog-fill  { height:100%; border-radius:99px; }
.trend-badge {
    display:flex; align-items:center; gap:3px;
    font-size:8px; font-weight:600; padding:2px 6px; border-radius:99px; margin-top:4px; margin-bottom:4px; width: 100%;
}
.trend-up   { background:rgba(248,113,113,.12); color:#f87171; }
.trend-down { background:rgba(20,184,166,.12);  color:#0f9f8f; }
.trend-same { background:rgba(0,136,204,.12); color:#007ab8; }

/* ── Tabelas ── */
.stTable table { background:transparent !important; font-family:'DM Sans',sans-serif !important;
    font-size:13px !important; width:100% !important; border-collapse:collapse !important; }
.stTable thead th { background:#f5f8fb !important; color:#007ab8 !important;
    font-size:10px !important; font-weight:600 !important; letter-spacing:.7px !important;
    text-transform:uppercase !important; padding:10px 14px !important; border-bottom:1px solid #dbe8f2 !important; }
.stTable tbody tr { background:#ffffff !important; }
.stTable tbody td { padding:10px 14px !important; border-bottom:1px solid #edf3f8 !important; color:#102a3f !important; }

/* ── Botões ── */
[data-testid="stDataFrame"] {
    background:#ffffff !important;
    border:1px solid #dbe8f2 !important;
    border-radius:8px !important;
    overflow:hidden !important;
    box-shadow:0 8px 22px rgba(16,42,63,.05) !important;
}
[data-testid="stDataFrame"] div,
[data-testid="stDataFrame"] span,
[data-testid="stDataFrame"] button,
[data-testid="stDataFrame"] svg {
    color:#102a3f !important;
    -webkit-text-fill-color:#102a3f !important;
}
[data-testid="stDataFrame"] canvas,
[data-testid="stDataFrame"] [role="grid"],
[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {
    background:#ffffff !important;
}

.stButton > button {
    width:100% !important; margin-top:8px !important; background:#ffffff !important;
    border:1px solid #b9d7e8 !important; color:#007ab8 !important; border-radius:8px !important;
    font-family:'DM Sans',sans-serif !important; font-size:11px !important;
    font-weight:500 !important; padding:5px 10px !important; transition:all .2s !important;
}
.stButton > button:hover:not(:disabled) {
    background:#e8f7fc !important; border-color:#00a6d6 !important; color:#005f91 !important;
}

/* ── Abas ── */
/* Formularios e filtros */
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label,
[data-testid="stDateInput"] label,
[data-testid="stFileUploader"] label {
    color:#102a3f !important;
    -webkit-text-fill-color:#102a3f !important;
    font-family:'DM Sans',sans-serif !important;
    font-size:12px !important;
    font-weight:600 !important;
}
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] * {
    color:#102a3f !important;
    -webkit-text-fill-color:#102a3f !important;
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
    color:#4f6f85 !important;
    -webkit-text-fill-color:#4f6f85 !important;
}
[data-testid="stWidgetLabel"] {
    min-height:22px !important;
}
[data-testid="stTextInput"] [data-baseweb="input"] > div,
[data-testid="stDateInput"] [data-baseweb="input"] > div {
    background:#ffffff !important;
    border:1px solid #b9d7e8 !important;
    border-radius:8px !important;
    box-shadow:none !important;
}
[data-testid="stTextInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea {
    background:#ffffff !important;
    border:1px solid #b9d7e8 !important;
    border-radius:8px !important;
    color:#102a3f !important;
    -webkit-text-fill-color:#102a3f !important;
    box-shadow:none !important;
    caret-color:#0088cc !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stDateInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color:#0088cc !important;
    box-shadow:0 0 0 1px #0088cc !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color:#6b8496 !important;
    -webkit-text-fill-color:#6b8496 !important;
    opacity:1 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background:#ffffff !important;
    border:1px solid #b9d7e8 !important;
    border-radius:8px !important;
    box-shadow:none !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
    border-color:#0088cc !important;
    box-shadow:0 0 0 1px #0088cc !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stSelectbox"] [data-baseweb="select"] svg,
[data-testid="stSelectbox"] [data-baseweb="select"] div {
    color:#102a3f !important;
    -webkit-text-fill-color:#102a3f !important;
}
[data-testid="stFileUploader"] section {
    background:#ffffff !important;
    border:1px dashed #b9d7e8 !important;
    border-radius:8px !important;
    color:#102a3f !important;
}
[data-baseweb="popover"] [role="listbox"] {
    background:#ffffff !important;
    border:1px solid #b9d7e8 !important;
    border-radius:8px !important;
    box-shadow:0 16px 36px rgba(16,42,63,.14) !important;
}
[data-baseweb="popover"] [role="option"] {
    background:#ffffff !important;
    color:#102a3f !important;
    -webkit-text-fill-color:#102a3f !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [aria-selected="true"] {
    background:#e8f7fc !important;
}

[data-testid="stTabs"] [role="tablist"] { border-bottom:1px solid #dbe8f2 !important; gap:2px !important; }
[data-testid="stTabs"] [role="tab"] {
    background:transparent !important; border:1px solid transparent !important;
    border-radius:8px 8px 0 0 !important; color:#4f6f85 !important;
    font-family:'DM Sans',sans-serif !important; font-size:13px !important;
    font-weight:500 !important; padding:8px 18px !important; transition:all .2s !important;
}
[data-testid="stTabContent"] { padding-top:1.5rem !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background:#ffffff !important; border:1px solid #dbe8f2 !important;
    border-radius:8px !important; margin-bottom:8px !important;
}
[data-testid="stExpander"] summary { font-weight:500 !important; color:#007ab8 !important; font-size:13px !important; }

/* ── Misc ── */
hr { border-color:#dbe8f2 !important; margin:1.5rem 0 !important; }
[data-testid="stAlert"] {
    background:#ffffff !important; border:1px solid #dbe8f2 !important;
    border-radius:8px !important; color:#12263a !important;
}

/* ── Download buttons ── */
.stDownloadButton > button {
    background:linear-gradient(135deg,rgba(0,136,204,.12),rgba(0,188,212,.12)) !important;
    border:1px solid rgba(0,136,204,.25) !important; color:#007ab8 !important;
    border-radius:8px !important; font-size:12px !important; font-weight:600 !important;
    padding:8px 16px !important; width:auto !important; margin-top:0 !important; transition:all .2s !important;
}

/* ── Tempo Offline badges ── */
.tempo-critico  { background:rgba(220,38,38,.10);  color:#dc2626; font-weight:700; padding:2px 8px; border-radius:6px; font-size:11px; }
.tempo-atencao  { background:rgba(217,119,6,.10);  color:#d97706; font-weight:700; padding:2px 8px; border-radius:6px; font-size:11px; }
.tempo-ok       { background:rgba(5,150,105,.10);  color:#059669; font-weight:700; padding:2px 8px; border-radius:6px; font-size:11px; }
.tempo-nd       { background:rgba(107,132,150,.10);color:#6b8496; font-weight:600; padding:2px 8px; border-radius:6px; font-size:11px; }

/* Auditoria operacional */
.audit-hero {
    background:#ffffff; border:1px solid #d5e3ec; border-radius:8px;
    padding:18px 20px; margin-bottom:14px; box-shadow:0 10px 24px rgba(16,42,63,.05);
}
.audit-hero-top {
    display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap;
}
.audit-title {
    font-size:22px; font-weight:700; color:#102a3f; line-height:1.15; margin-bottom:4px;
}
.audit-sub {
    font-size:12px; color:#4f6f85; max-width:880px; line-height:1.45;
}
.audit-badges { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.audit-badge {
    font-family:'DM Mono',monospace; font-size:10px; font-weight:700; text-transform:uppercase;
    padding:6px 10px; border-radius:6px; border:1px solid currentColor; white-space:nowrap;
}
.audit-strip {
    display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:12px 0 16px;
}
.audit-card {
    background:#ffffff; border:1px solid #dbe8f2; border-radius:8px; padding:12px 14px;
    min-height:92px; box-shadow:0 8px 18px rgba(16,42,63,.04);
}
.audit-card-label {
    font-size:10px; color:#60798d; font-weight:700; text-transform:uppercase; letter-spacing:.6px;
    margin-bottom:7px;
}
.audit-card-value {
    font-family:'DM Mono',monospace; font-size:24px; line-height:1.05; color:#102a3f; font-weight:700;
}
.audit-card-note { font-size:11px; color:#60798d; margin-top:7px; line-height:1.35; }
.audit-riskbar {
    display:grid; grid-template-columns:minmax(0,1fr) auto; gap:12px; align-items:center;
    background:#f8fbfd; border:1px solid #dbe8f2; border-radius:8px; padding:12px 14px; margin-bottom:16px;
}
.audit-risk-track { height:10px; background:#e3edf4; border-radius:99px; overflow:hidden; }
.audit-risk-fill { height:100%; border-radius:99px; }
.audit-risk-label { font-family:'DM Mono',monospace; font-size:12px; font-weight:700; white-space:nowrap; }
.audit-section-title {
    display:flex; align-items:center; justify-content:space-between; gap:12px; margin:18px 0 8px;
}
.audit-section-title strong { font-size:14px; color:#102a3f; }
.audit-section-title span { font-size:11px; color:#60798d; }
.audit-action-note {
    background:#fffaf0; border:1px solid #fde3a7; border-radius:8px; padding:10px 12px;
    color:#7a5200; font-size:12px; margin:8px 0 12px;
}

@media (max-width: 1100px) {
    .audit-strip { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media (max-width: 700px) {
    [data-testid="block-container"] { padding:1rem !important; }
    .audit-strip, .kpi-grid { grid-template-columns:1fr !important; }
    .audit-riskbar { grid-template-columns:1fr; }
    .audit-badges { justify-content:flex-start; }
}

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
PASTA                     = os.getenv("CAMERITE_MONITORAMENTO_PASTA", r"C:\Users\FernandoHenriqueSofi\Desktop\Monitoramento")
CSV_GOV                   = os.path.join(PASTA, "GOV_extracao_cameras.csv")
XLSX_CLIENTES             = os.path.join(PASTA, "nome_clientes.xlsx")
IMPORTACAO_INDIVIDUAL_DIR = os.path.join(PASTA, "importacao_individual")
DB_PATH                   = os.path.join(PASTA, "historico.db")
GEO_CACHE_PATH            = os.path.join(PASTA, "geocode_cache.json")
BRAZIL_STATES_GEOJSON_URL = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
BRAZIL_STATES_GEOJSON_PATH = os.path.join(PASTA, "brazil_states.geojson")
COLUNAS_PAINEL            = 4
DATA_PARSE_VERSION = "2026-05-15-br-date-v1"

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

STATUS_CLIENTE = [
    "Todos",
    "Crítico (>15%)",
    "Atenção (10-15%)",
    "Saudável (<10%)",
]


# ─────────────────────────────────────────────
# HELPERS DE COR
# ─────────────────────────────────────────────
def cor_hex(pct: float) -> str:
    if pct < 10:     return "#14b8a6"
    elif pct <= 15: return "#f59e0b"
    else:           return "#ef4444"

def classe_card(pct: float):
    if pct < 10:     return ("card-ok",    "count-ok",    "label-ok")
    elif pct <= 15: return ("card-yellow","count-yellow","label-yellow")
    else:           return ("card-red",   "count-red",   "label-red")

def fmt_tempo(delta: timedelta) -> str:
    """Formata um timedelta em texto legível."""
    s = int(delta.total_seconds())
    if s < 0:    return "N/D"
    if s < 3600: return f"{s//60}min"
    if s < 86400:return f"{s//3600}h {(s%3600)//60}min"
    d = s // 86400; h = (s % 86400) // 3600
    return f"{d}d {h}h"

def classe_tempo(delta: timedelta) -> str:
    h = delta.total_seconds() / 3600
    if h >= 24:  return "tempo-critico"
    if h >= 6:   return "tempo-atencao"
    return "tempo-ok"

def normalizar_coluna(valor: str) -> str:
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", texto)


def encontrar_coluna_por_chaves(df: pd.DataFrame, chaves: tuple[str, ...], default=None):
    cols = list(df.columns)
    normalized = [normalizar_coluna(c) for c in cols]

    # Prefer exact matches first
    for chave in chaves:
        for col, norm in zip(cols, normalized):
            if norm == chave:
                return col

    # Then substring matches
    for chave in chaves:
        for col, norm in zip(cols, normalized):
            if chave in norm:
                return col

    return default


def faixa_tempo_horas(horas: float) -> str:
    if horas < 0:   return "Sem data"
    if horas < 1:   return "Menos de 1h"
    if horas < 6:   return "1h a 6h"
    if horas < 24:  return "6h a 24h"
    if horas < 72:  return "1 a 3 dias"
    if horas < 168: return "3 a 7 dias"
    return "Mais de 7 dias"

def status_cliente(pct: float, offline: int) -> str:
    if offline == 0: return "Sem offline"
    if pct > 15:    return "Crítico (>15%)"
    if pct >= 10:   return "Atenção (10-15%)"
    return "Saudável (<10%)"


def escape_html(valor) -> str:
    return html.escape(str(valor or ""), quote=True)


def classificar_auditoria(pct_global: float, n_critico: int, n_atencao: int, saude: dict) -> tuple[str, str, str]:
    if saude.get("colunas_faltando"):
        return "Bloqueado", "#dc2626", "Colunas obrigatórias ausentes"
    if saude.get("datas_futuras", 0):
        return "Revisar fonte", "#d97706", "Há datas futuras no arquivo"
    if saude.get("datas_invalidas", 0):
        return "Revisar fonte", "#d97706", "Há datas inválidas no arquivo"
    if pct_global > 15 or n_critico > 0:
        return "Ação imediata", "#dc2626", "Clientes acima do limite crítico"
    if pct_global >= 10 or n_atencao > 0:
        return "Monitorar", "#d97706", "Há clientes na faixa de atenção"
    return "Conforme", "#059669", "Operação dentro da tolerância"


def classificar_fonte(saude: dict) -> tuple[str, str]:
    if saude.get("colunas_faltando"):
        return "Incompleta", "#dc2626"
    if saude.get("datas_futuras", 0):
        return "Com ressalvas", "#d97706"
    if saude.get("datas_invalidas", 0):
        return "Com ressalvas", "#d97706"
    if saude.get("linhas_processadas", 0) == 0:
        return "Sem amostra", "#6b8496"
    return "Auditável", "#059669"


def recomendacao_auditoria(n_critico: int, n_atencao: int, saude: dict) -> tuple[str, str]:
    if saude.get("colunas_faltando"):
        return "Validar fonte", "Corrigir colunas obrigatórias antes de avaliar a operação"
    if saude.get("datas_futuras", 0) or saude.get("datas_invalidas", 0):
        return "Revisar fonte", "Conferir a coluna Ultima_Atualizacao e o formato dd/mm/aaaa"
    if n_critico > 0:
        return "Acionar", "Cobrar responsáveis dos clientes críticos e registrar prazo de normalização"
    if n_atencao > 0:
        return "Acompanhar", "Monitorar clientes em atenção e cobrar prevenção de reincidência"
    return "Manter rotina", "Registrar evidência e seguir acompanhamento periódico"


# ─────────────────────────────────────────────
# LEITURA DO CSV + CLIENTES
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def carregar_clientes() -> dict:
    """Carrega nome_clientes.xlsx e retorna dict {ID_Whitelabel: nome_cliente}."""
    if not os.path.exists(XLSX_CLIENTES):
        return {}
    try:
        df = pd.read_excel(XLSX_CLIENTES, engine="openpyxl")
        # Aceitar qualquer variação de nome de coluna
        col_id = next((c for c in df.columns if "whitelabel" in c.lower() or "id" in c.lower()), df.columns[0])
        col_nom = next((c for c in df.columns if "nome" in c.lower() or "client" in c.lower()), df.columns[1] if len(df.columns) > 1 else df.columns[0])
        return dict(zip(df[col_id].astype(str).str.strip(), df[col_nom].astype(str).str.strip()))
    except Exception:
        return {}

@st.cache_data(ttl=60)
def carregar_clientes_prefeitura() -> dict:
    """Carrega nome_clientes.xlsx e retorna dict {ID_Whitelabel: Prefeitura / cidade-estado}."""
    if not os.path.exists(XLSX_CLIENTES):
        return {}
    try:
        df = pd.read_excel(XLSX_CLIENTES, engine="openpyxl")
        col_id = next((c for c in df.columns if "whitelabel" in c.lower() or "id" in c.lower()), df.columns[0])
        col_city = next((c for c in df.columns if any(k in c.lower() for k in ("prefeitura", "cidade", "municipio", "city"))), None)
        if col_city is None:
            col_city = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        return dict(zip(df[col_id].astype(str).str.strip(), df[col_city].astype(str).str.strip()))
    except Exception:
        return {}


def parse_prefeitura_localidade(valor: str) -> tuple[str | None, str | None]:
    valor = str(valor or "").strip()
    if not valor:
        return None, None
    partes = re.split(r"\s*[-–]\s*", valor)
    if len(partes) == 1:
        return valor, None
    ultima = partes[-1].strip()
    if re.fullmatch(r"[A-Za-z]{2}", ultima):
        cidade = "-".join(partes[:-1]).strip()
        return (cidade or None, ultima.upper())
    return valor, None


def preencher_cidade_estado_por_clientes(df: pd.DataFrame, clientes_prefeitura: dict) -> pd.DataFrame:
    if df is None or df.empty or not clientes_prefeitura:
        return df

    city_col = encontrar_coluna_por_chaves(df, ("cidade", "municipio", "city"), default="cidade")
    state_col = encontrar_coluna_por_chaves(df, ("estado", "uf", "state"), default="estado")

    if city_col not in df.columns:
        df[city_col] = ""

    if state_col is None:
        state_col = "estado"
    if state_col not in df.columns:
        df[state_col] = ""

    cidade_valores = []
    estado_valores = []

    for _, row in df.iterrows():
        wl_id = str(row.get(COL_WL, "")).strip()
        cidade = str(row.get(city_col, "")).strip()
        estado = str(row.get(state_col, "")).strip() if state_col else ""

        if not cidade and wl_id in clientes_prefeitura:
            cidade_extra, estado_extra = parse_prefeitura_localidade(clientes_prefeitura[wl_id])
            if cidade_extra:
                cidade = cidade_extra
            if state_col and not estado and estado_extra:
                estado = estado_extra

        cidade_valores.append(cidade)
        if state_col:
            estado_valores.append(estado)

    df[city_col] = cidade_valores
    if state_col:
        df[state_col] = estado_valores

    return df

def ler_csv_gov(path: str) -> pd.DataFrame | None:
    melhor_candidato = None
    for enc in ("utf-8", "latin-1", "cp1252"):
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(
                    path, encoding=enc, sep=sep,
                    on_bad_lines="skip",   # pula linhas malformadas
                    engine="python",        # parser mais tolerante
                    quoting=0,              # respeita aspas normais
                )
                df.columns = [c.strip() for c in df.columns]
                if {COL_STATUS, COL_WL}.issubset(df.columns):
                    return df
                if melhor_candidato is None or len(df.columns) > len(melhor_candidato.columns):
                    melhor_candidato = df
            except UnicodeDecodeError:
                break   # tenta próximo encoding
            except Exception:
                continue
    return melhor_candidato


# ─────────────────────────────────────────────
# FALLBACK XLSX INDIVIDUAIS
# ─────────────────────────────────────────────
def carregar_xlsx_individuais(pasta: str) -> tuple[pd.DataFrame | None, list]:

    arquivos = glob.glob(
        os.path.join(pasta, "*.xlsx")
    )

    arquivos = [
        a for a in arquivos
        if "nome_clientes" not in os.path.basename(a).lower()
        and not os.path.basename(a).startswith("~$")
    ]

    if not arquivos:
        return None, ["Nenhum XLSX individual encontrado"]

    dfs = []

    erros = []

    for arquivo in arquivos:
        arquivo_base = os.path.basename(arquivo)

        try:

            df = pd.read_excel(
                arquivo,
                engine="openpyxl"
            )

            if df is None or df.empty:
                erros.append(f"{arquivo_base}: arquivo vazio ou sem dados válidos")
                continue

            df.columns = [
                str(c).strip()
                for c in df.columns
            ]

            rename_map = {}

            for col in df.columns:
                nome = normalizar_coluna(col)

                if "whitelabel" in nome or ("id" in nome and "whitelabel" in col.lower()):
                    rename_map[col] = COL_WL
                elif "status" in nome:
                    rename_map[col] = COL_STATUS
                elif "empresa" in nome or "company" in nome:
                    rename_map[col] = COL_EMPRESA
                elif "camera" in nome and "id" in nome:
                    rename_map[col] = COL_ID_CAM
                elif "camera" in nome and ("nome" in nome or "name" in nome):
                    rename_map[col] = COL_NOME_CAM
                elif "ultim" in nome or "atualiz" in nome or "update" in nome:
                    rename_map[col] = COL_ULT_ATU
                elif "obs" in nome or "observ" in nome:
                    rename_map[col] = COL_OBS

            df.rename(
                columns=rename_map,
                inplace=True
            )

            if COL_WL not in df.columns:
                erros.append(f"{arquivo_base}: coluna '{COL_WL}' não encontrada")
                continue

            if COL_STATUS not in df.columns:
                erros.append(f"{arquivo_base}: coluna '{COL_STATUS}' não encontrada")
                continue

            if COL_EMPRESA not in df.columns:
                df[COL_EMPRESA] = ""

            if COL_ID_CAM not in df.columns:
                df[COL_ID_CAM] = ""

            if COL_NOME_CAM not in df.columns:
                df[COL_NOME_CAM] = ""

            if COL_ULT_ATU not in df.columns:
                df[COL_ULT_ATU] = ""

            if COL_OBS not in df.columns:
                df[COL_OBS] = ""

            dfs.append(df)

        except PermissionError:
            erros.append(
                f"{arquivo_base}: Permissão negada (arquivo em uso ou inacessível)."
            )
            continue
        except Exception as e:
            erros.append(
                f"{arquivo_base}: {str(e)}"
            )

    if not dfs:
        if not erros:
            erros = ["Arquivos XLSX encontrados, mas nenhum passou na validação de dados."]
        return None, erros

    df_final = pd.concat(
        dfs,
        ignore_index=True
    )

    return df_final, erros

def parse_ultima_atualizacao(coluna: pd.Series) -> pd.Series:
    """
    Converte a data da Camerite preservando o formato brasileiro do CSV.
    Datas com barra são tratadas primeiro como dd/mm/aaaa; ISO continua aceito.
    """
    valores = coluna.astype("string").str.strip()
    parsed = pd.Series(pd.NaT, index=coluna.index, dtype="datetime64[ns]")

    formatos = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    )

    for fmt in formatos:
        mask = parsed.isna() & valores.notna() & (valores != "")
        if not mask.any():
            break
        parsed.loc[mask] = pd.to_datetime(valores.loc[mask], errors="coerce", format=fmt)

    mask = parsed.isna() & valores.notna() & (valores != "")
    if mask.any():
        parsed.loc[mask] = valores.loc[mask].apply(
            lambda valor: pd.to_datetime(valor, errors="coerce", dayfirst=True)
        )

    return parsed

def formatar_ultima_atualizacao(coluna: pd.Series) -> pd.Series:
    return parse_ultima_atualizacao(coluna).dt.strftime("%d/%m/%Y %H:%M").fillna("N/D")

def processar_df_gov(df: pd.DataFrame, clientes_map: dict) -> dict:
    """
    Processa um DataFrame já carregado do CSV e retorna o dict padrão do BI.
    Se clientes_map não estiver vazio, filtra SOMENTE os IDs presentes nele.
    """
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # ── Filtrar apenas clientes do xlsx (se xlsx foi carregado) ──
    if clientes_map:
        ids_validos = set(clientes_map.keys())
        df = df[df[COL_WL].astype(str).str.strip().isin(ids_validos)]

    if df.empty:
        return {}

    # Parsear data da última atualização
    agora = datetime.now()
    if COL_ULT_ATU in df.columns:
        df[COL_ULT_ATU] = parse_ultima_atualizacao(df[COL_ULT_ATU])
        df["_tempo_off"] = df[COL_ULT_ATU].apply(
            lambda x: agora - x if pd.notna(x) else timedelta(seconds=-1)
        )
    else:
        df["_tempo_off"] = pd.Series([timedelta(seconds=-1)] * len(df), index=df.index)

    resultado = {}
    for wl_id, grupo in df.groupby(df[COL_WL].astype(str).str.strip()):
        nome_cliente = clientes_map.get(wl_id, f"ID {wl_id}")
        nome_empresa = grupo[COL_EMPRESA].iloc[0] if COL_EMPRESA in grupo.columns else ""
        df_off = grupo[grupo[COL_STATUS].astype(str).str.strip().str.upper() == "OFFLINE"].copy()
        if "_tempo_off" in df_off.columns:
            df_off = df_off.sort_values("_tempo_off", ascending=False)
        resultado[wl_id] = {
            "nome_cliente": nome_cliente,
            "nome_empresa": nome_empresa,
            "offline": df_off,
            "total": len(grupo),
        }
    return resultado

_GEO_CACHE = None

def carregar_cache_geocode() -> dict:
    global _GEO_CACHE
    if _GEO_CACHE is not None:
        return _GEO_CACHE
    if os.path.exists(GEO_CACHE_PATH):
        try:
            with open(GEO_CACHE_PATH, "r", encoding="utf-8") as f:
                _GEO_CACHE = json.load(f)
        except Exception:
            _GEO_CACHE = {}
    else:
        _GEO_CACHE = {}
    return _GEO_CACHE


def salvar_cache_geocode(cache: dict) -> None:
    try:
        with open(GEO_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def carregar_geojson_estados() -> dict | None:
    if os.path.exists(BRAZIL_STATES_GEOJSON_PATH):
        try:
            with open(BRAZIL_STATES_GEOJSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    try:
        resp = requests.get(BRAZIL_STATES_GEOJSON_URL, timeout=10,
                             headers={"User-Agent": "Camerite BI/1.0"})
        if resp.ok:
            geojson = resp.json()
            with open(BRAZIL_STATES_GEOJSON_PATH, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False)
            return geojson
    except Exception:
        pass
    return None


def obter_nome_estado(valor: str) -> str | None:
    chave = normalizar_coluna(valor)
    return BRAZIL_STATE_NAME_MAP.get(chave)


def geocode_cidade(nome: str, estado: str | None = None) -> tuple[float, float] | None:
    nome = str(nome or "").strip()
    if not nome:
        return None
    chave = f"{nome}|{estado or ''}"
    cache = carregar_cache_geocode()
    if chave in cache:
        coord_cache = cache[chave]
        if not coord_cache:
            return None
        lat, lon = coord_cache
        return (lat, lon)

    query = nome
    if estado:
        query += f", {estado}"
    query += ", Brasil"

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "br"},
            headers={"User-Agent": "Camerite BI/1.0"},
            timeout=10,
        )
        if response.ok:
            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                cache[chave] = [lat, lon]
                salvar_cache_geocode(cache)
                return lat, lon
    except Exception:
        pass
    cache[chave] = None
    salvar_cache_geocode(cache)
    return None

def montar_mapa_cidades(df: pd.DataFrame) -> tuple[go.Figure | None, str]:
    if df is None or df.empty:
        return None, "Sem dados de origem para criar o mapa."
        
    df_map = df.copy()
    
    # 1. Identifica as colunas de localização do seu Excel mestre
    city_col = encontrar_coluna_por_chaves(df_map, ("cidade", "municipio", "city", "prefeitura"), default=None)
    state_col = encontrar_coluna_por_chaves(df_map, ("estado", "uf", "state"), default=None)
    
    # 2. Agrupamento idêntico ao gráfico de barras (Consolidado por Cliente)
    df_group = df_map.groupby(COL_WL, as_index=False).agg(
        total=(COL_STATUS, 'size'),
        offline=(COL_STATUS, lambda x: (x.astype(str).str.strip().str.upper() == 'OFFLINE').sum()),
        nome_empresa=(COL_EMPRESA, 'first') if COL_EMPRESA in df_map.columns else (COL_WL, 'first'),
        city=(city_col, 'first') if city_col in df_map.columns else (COL_WL, 'first'),
        uf=(state_col, 'first') if state_col in df_map.columns else (COL_WL, 'first'),
    )
    
    df_group["Pct"] = (df_group["offline"] / df_group["total"]) * 100
    
    # 3. DICIONÁRIO DE COORDENADAS FIXAS (Garante o carregamento mesmo se o Excel individual falhar)
    COORDENADAS_FIXAS = {
        "traipú": (-9.9702, -36.9388), "traipu": (-9.9702, -36.9388),
        "carmo de cachoeira": (-21.5173, -45.1906),
        "sete lagoas": (-19.4651, -44.2464),
        "jandaíra": (-5.3524, -35.6191), "jandaira": (-5.3524, -35.6191),
        "upanema": (-5.6429, -37.2557),
        "ibiraci": (-20.4566, -47.1235),
        "pitangueiras": (-21.0097, -48.2222),
        "santo augusto": (-27.8504, -53.7801),
        "astorga": (-23.2325, -51.6644),
        "pirai do sul": (-24.5322, -49.9442),
        "machado": (-21.6750, -45.9194),
        "aparecida do taboado": (-20.0844, -51.0911),
        "joaquim távora": (-23.4975, -49.9239), "joaquim tavora": (-23.4975, -49.9239),
        "rebouças": (-25.6208, -50.6917), "reboucas": (-25.6208, -50.6917),
        "naviraí": (-23.0642, -54.1919), "navirai": (-23.0642, -54.1919),
        "jandaia do sul": (-23.6026, -51.6441),
        "camapuã": (-19.5314, -53.2172), "camapua": (-19.5314, -53.2172),
        "cassilândia": (-19.1118, -51.7342), "cassilandia": (-19.1118, -51.7342),
        "inocência": (-19.7275, -51.9292), "inocencia": (-19.7275, -51.9292),
        "terenos": (-20.4422, -54.8601),
        "godoy moreira": (-24.1678, -51.9161),
        "palmital": (-24.8944, -52.2017),
        "paiçandu": (-23.4578, -52.0153), "paicandu": (-23.4578, -52.0153),
        "viçosa": (-20.7539, -42.8814), "vicosa": (-20.7539, -42.8814),
        "esperantina": (-3.9011, -42.2356),
        "lindóia": (-22.5244, -46.6508), "lindoia": (-22.5244, -46.6508),
        "nossa senhora da glória": (-10.2183, -37.4203), "nossa senhora da gloria": (-10.2183, -37.4203),
        "tobias barreto": (-11.1856, -37.9953),
        "tomar do geru": (-11.3725, -37.8406),
        "anastácio": (-20.4839, -55.8114), "anastacio": (-20.4839, -55.8114),
        "joinville": (-26.3045, -48.8434)
    }
    
    df_group["lat"] = pd.NA
    df_group["lon"] = pd.NA
    
    # 4. Mapeamento
    for idx, row in df_group.iterrows():
        cidade_bruta = str(row["city"]).strip().lower()
        uf_nome = str(row["uf"]).strip().upper()
        cliente_nome = str(row["nome_empresa"]).strip()
        
        # Limpa o nome para buscar no nosso dicionário estático
        chave_cache = cidade_bruta.replace("prefeitura de ", "").replace("prefeitura ", "").strip()
        
        if chave_cache in COORDENADAS_FIXAS:
            df_group.at[idx, "lat"] = COORDENADAS_FIXAS[chave_cache][0]
            df_group.at[idx, "lon"] = COORDENADAS_FIXAS[chave_cache][1]
        else:
            # TRAVA DE SEGURANÇA SE FOREM IDs CONVERGIDOS ERRADOS OU NOVOS:
            # Joga provisoriamente em Joinville para o mapa nunca exibir tela em branco/erro
            df_group.at[idx, "lat"] = -26.3045
            df_group.at[idx, "lon"] = -48.8434
            if cidade_bruta == "nan" or cidade_bruta.isdigit():
                df_group.at[idx, "city"] = f"{cliente_nome} (Ajustar colunas no Excel)"
            else:
                df_group.at[idx, "city"] = f"{row['city']} (Posicionamento Provisório)"
    
    df_group = df_group.dropna(subset=["lat", "lon"]).copy()
    
    # Lógica do Jittering (Evita pontos totalmente sobrepostos)
    coord_counts = df_group.groupby(["lat", "lon"]).size().reset_index(name="count")
    df_group = df_group.merge(coord_counts, on=["lat", "lon"], how="left")
    df_group["dup_index"] = df_group.groupby(["lat", "lon"]).cumcount()
    
    def _jitter_row(row):
        if row["count"] <= 1 or pd.isna(row["lat"]) or pd.isna(row["lon"]):
            return pd.Series([row["lat"], row["lon"]])
        radius = 0.04 + min(row["count"] - 1, 6) * 0.005
        angle = 2 * math.pi * row["dup_index"] / row["count"]
        return pd.Series([
            row["lat"] + math.cos(angle) * radius,
            row["lon"] + math.sin(angle) * radius,
        ])
        
    df_group[["lat_jit", "lon_jit"]] = df_group.apply(_jitter_row, axis=1)
    
    # 5. Rótulo do Pop-up do Mapa de Calor
    df_group["label"] = (
        "<b>" + df_group["nome_empresa"].astype(str) + "</b><br>" +
        "Cidade: " + df_group["city"].astype(str) + " - " + df_group["uf"].astype(str) + "<br>" +
        "Status: <b>" + df_group["Pct"].round(1).astype(str) + "% Offline</b><br>" +
        "Câmeras: " + df_group["offline"].astype(str) + " de " + df_group["total"].astype(str) + " desconectadas"
    )
    
    fig = go.Figure()
    
    # Desenha o Brasil de fundo
    geojson = carregar_geojson_estados()
    if geojson is not None:
        state_names = [
            feature.get("properties", {}).get("name") 
            for feature in geojson.get("features", []) 
            if feature.get("properties", {}).get("name")
        ]
        if state_names:
            fig.add_trace(go.Choropleth(
                geojson=geojson,
                locations=state_names,
                z=[0] * len(state_names),
                featureidkey="properties.name",
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                marker_line_color="#bdc3c7",
                marker_line_width=0.6,
                showscale=False,
                hoverinfo="skip",
            ))
            
    # 6. Adiciona os Marcadores Térmicos
    fig.add_trace(go.Scattergeo(
        lon=df_group["lon_jit"],
        lat=df_group["lat_jit"],
        text=df_group["label"],  
        mode="markers",
        marker=dict(
            size=(8 + df_group["Pct"] * 0.35).clip(8, 32),
            color=df_group["Pct"],
            colorscale=[[0, "#14b8a6"], [0.15, "#f59e0b"], [1, "#ef4444"]],
            cmin=0,
            cmax=100,
            showscale=True,
            colorbar=dict(
                title="Gravidade (% Offline)", 
                thickness=15, 
                len=0.6, 
                tickfont=dict(size=10, color="#6b8496"),
                ticksuffix="%"
            ),
            line_color="white",
            line_width=0.8,
        ),
        hovertemplate="%{text}<extra></extra>"  
    ))
    
    fig.update_geos(
        visible=False,
        showcountries=True,
        countrycolor="#bdc3c7",
        fitbounds="locations",
        projection_type="mercator",
    )
    fig.update_layout(**pdefaults(), height=550, margin=dict(l=10, r=10, t=30, b=20))
    
    return fig, "Mapa de calor carregado com segurança."   

    fig = go.Figure(go.Choropleth(
        geojson=geojson,
        locations=df_group["state_name"],
        z=df_group["Pct"],
        featureidkey="properties.name",
        colorscale=[[0, "#14b8a6"], [0.5, "#f59e0b"], [1, "#ef4444"]],
        colorbar=dict(title="% offline", thickness=12, len=0.4, tickfont=dict(size=10)),
        marker_line_color="white",
        marker_line_width=0.5,
        hovertemplate="<b>%{location}</b><br>%{z:.1f}% offline<br>%{customdata[0]} offline de %{customdata[1]}<extra></extra>",
        customdata=df_group[["offline", "total"]].values,
    ))
    fig.update_geos(
        visible=False,
        showcountries=False,
        fitbounds="locations",
        projection_type="mercator",
    )
    fig.update_layout(**pdefaults(), height=450, margin=dict(l=10, r=10, t=30, b=20))
    return fig, f"Mapa de estados exibindo {len(df_group)} estados com dados de offline."

@st.cache_data(ttl=60)
def carregar_dados(pasta: str, parse_version: str = DATA_PARSE_VERSION) -> tuple[dict, str, pd.DataFrame | None]:

    """
    Prioridade:
    1 - GOV_extracao_cameras.csv
    2 - XLSX individuais
    """

    if not os.path.exists(pasta):
        return {}, f"Pasta não encontrada: `{pasta}`", None

    clientes_map = carregar_clientes()
    clientes_prefeitura = carregar_clientes_prefeitura()

    # ============================================================
    # 1) CSV PRINCIPAL
    # ============================================================
    if os.path.exists(CSV_GOV):

        df = ler_csv_gov(CSV_GOV)

        if df is None:
            return {}, "Não foi possível ler o CSV (erro de encoding ou arquivo corrompido).", None

        df = preencher_cidade_estado_por_clientes(df, clientes_prefeitura)

        cols_faltando = [c for c in [COL_STATUS, COL_WL] if c not in df.columns]

        if cols_faltando:
            return {}, (
                f"Colunas obrigatórias não encontradas: "
                f"`{'`, `'.join(cols_faltando)}`\n"
                f"Colunas presentes no CSV: "
                f"`{'`, `'.join(df.columns.tolist())}`"
            ), df

        return processar_df_gov(df, clientes_map), "", df

    # ============================================================
    # 2) FALLBACK XLSX EM importacao_individual
    # ============================================================
    df_xlsx, erros = carregar_xlsx_individuais(IMPORTACAO_INDIVIDUAL_DIR)

    if df_xlsx is None:
        if not os.path.exists(IMPORTACAO_INDIVIDUAL_DIR):
            return {}, (
                "CSV principal não encontrado.\n\n"
                f"Pasta de fallback não existe: `{IMPORTACAO_INDIVIDUAL_DIR}`"
            ), None

        erro_txt = "\n".join(erros[:20])

        return {}, (
            "CSV principal não encontrado.\n\n"
            f"Também não foi possível carregar os XLSX individuais de `{IMPORTACAO_INDIVIDUAL_DIR}`.\n\n"
            f"Erros encontrados:\n{erro_txt}"
        ), None

    df_xlsx = preencher_cidade_estado_por_clientes(df_xlsx, clientes_prefeitura)

    if erros:
            warning_txt = "\n".join(erros[:20])
            return processar_df_gov(df_xlsx, clientes_map), (
                "Alguns arquivos XLSX foram ignorados por erro:\n" + warning_txt
            ), df_xlsx

    return processar_df_gov(df_xlsx, clientes_map), "", df_xlsx
def calcular_saude_dataframe(df: pd.DataFrame | None, clientes_map: dict, origem: str = "Arquivo local") -> dict:
    if df is None or df.empty:
        return {
            "origem": origem, "linhas_csv": 0, "linhas_processadas": 0,
            "linhas_fora_escopo": 0,
            "clientes_xlsx": len(clientes_map), "datas_invalidas": 0,
            "datas_futuras": 0, "sem_data": 0, "ultima_data": "N/D", "arquivo_atualizado": "N/D",
            "colunas_faltando": [],
        }

    df_meta = df.copy()
    df_meta.columns = [c.strip() for c in df_meta.columns]
    faltando = [c for c in [COL_STATUS, COL_WL, COL_ULT_ATU] if c not in df_meta.columns]
    linhas_csv = len(df_meta)
    linhas_processadas = linhas_csv
    linhas_fora_escopo = 0
    df_escopo = df_meta

    if clientes_map and COL_WL in df_meta.columns:
        ids_validos = set(clientes_map.keys())
        mask_escopo = df_meta[COL_WL].astype(str).str.strip().isin(ids_validos)
        df_escopo = df_meta[mask_escopo].copy()
        linhas_processadas = len(df_escopo)
        linhas_fora_escopo = linhas_csv - linhas_processadas

    datas_invalidas = 0
    datas_futuras = 0
    sem_data = 0
    ultima_data = "N/D"
    if COL_ULT_ATU in df_escopo.columns:
        valores = df_escopo[COL_ULT_ATU].astype("string").str.strip()
        parsed = parse_ultima_atualizacao(df_escopo[COL_ULT_ATU])
        sem_data = (valores.isna() | (valores == "")).sum()
        datas_invalidas = (parsed.isna() & valores.notna() & (valores != "")).sum()
        datas_futuras = (parsed > datetime.now()).sum()
        if parsed.notna().any():
            ultima_data = parsed.max().strftime("%d/%m/%Y %H:%M")

    arquivo_atualizado = "N/D"
    if os.path.exists(CSV_GOV):
        arquivo_atualizado = datetime.fromtimestamp(os.path.getmtime(CSV_GOV)).strftime("%d/%m/%Y %H:%M")

    return {
        "origem": origem,
        "linhas_csv": int(linhas_csv),
        "linhas_processadas": int(linhas_processadas),
        "linhas_fora_escopo": int(linhas_fora_escopo),
        "clientes_xlsx": len(clientes_map),
        "datas_invalidas": int(datas_invalidas),
        "datas_futuras": int(datas_futuras),
        "sem_data": int(sem_data),
        "ultima_data": ultima_data,
        "arquivo_atualizado": arquivo_atualizado,
        "colunas_faltando": faltando,
    }

@st.cache_data(ttl=60)
def calcular_saude_dados(pasta: str, parse_version: str = DATA_PARSE_VERSION) -> dict:
    clientes_map = carregar_clientes()
    if os.path.exists(CSV_GOV):
        return calcular_saude_dataframe(ler_csv_gov(CSV_GOV), clientes_map, "Arquivo local")

    if os.path.exists(IMPORTACAO_INDIVIDUAL_DIR):
        df_xlsx, _ = carregar_xlsx_individuais(IMPORTACAO_INDIVIDUAL_DIR)
        return calcular_saude_dataframe(df_xlsx, clientes_map, "Pasta importacao_individual")

    return calcular_saude_dataframe(None, clientes_map, "Arquivo local")


# ─────────────────────────────────────────────
# BANCO SQLite
# ─────────────────────────────────────────────
def abrir_conexao():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with abrir_conexao() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                label      TEXT NOT NULL,
                gravado_em TEXT NOT NULL,
                notas      TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS snapshot_clientes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                wl_id       TEXT NOT NULL,
                nome_cliente TEXT NOT NULL,
                total       INTEGER NOT NULL,
                offline     INTEGER NOT NULL,
                pct_offline REAL NOT NULL
            );
        """)

def salvar_snapshot(label: str, notas: str, dados: dict) -> str:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with abrir_conexao() as con:
        cur = con.cursor()
        cur.execute("INSERT INTO snapshots (label,gravado_em,notas) VALUES (?,?,?)", (label, agora, notas))
        sid = cur.lastrowid
        for wl_id, v in dados.items():
            total = v["total"]; off = len(v["offline"])
            pct   = round(off/total*100, 2) if total else 0
            cur.execute(
                "INSERT INTO snapshot_clientes (snapshot_id,wl_id,nome_cliente,total,offline,pct_offline) VALUES (?,?,?,?,?,?)",
                (sid, wl_id, v["nome_cliente"], total, off, pct)
            )
    return agora

def listar_snapshots() -> pd.DataFrame:
    with abrir_conexao() as con:
        return pd.read_sql_query("SELECT id,label,gravado_em,notas FROM snapshots ORDER BY id DESC", con)

def carregar_snapshot(sid: int) -> pd.DataFrame:
    with abrir_conexao() as con:
        return pd.read_sql_query(
            "SELECT wl_id,nome_cliente,total,offline,pct_offline FROM snapshot_clientes WHERE snapshot_id=?",
            con, params=(sid,)
        )

def deletar_snapshot(sid: int):
    with abrir_conexao() as con:
        con.execute("DELETE FROM snapshots WHERE id=?", (sid,))

def snapshot_referencia() -> pd.DataFrame | None:
    with abrir_conexao() as con:
        df_s = pd.read_sql_query("SELECT id FROM snapshots ORDER BY id DESC LIMIT 1", con)
    if df_s.empty:
        return None
    return carregar_snapshot(int(df_s.iloc[0]["id"]))

def salvar_snapshot_automatico(dados: dict) -> str:
    hoje = datetime.now().strftime("%Y-%m-%d")
    with abrir_conexao() as con:
        existe = con.execute(
            "SELECT id FROM snapshots WHERE date(gravado_em)=? AND label LIKE 'Auto %' LIMIT 1",
            (hoje,),
        ).fetchone()
    if existe:
        return ""
    return salvar_snapshot(
        f"Auto {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "Snapshot automático diário",
        dados,
    )

def carregar_historico_clientes(dias: int = 30) -> pd.DataFrame:
    limite = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    with abrir_conexao() as con:
        return pd.read_sql_query(
            """
            SELECT s.id AS snapshot_id, s.label, s.gravado_em,
                   sc.wl_id, sc.nome_cliente, sc.total, sc.offline, sc.pct_offline
            FROM snapshots s
            JOIN snapshot_clientes sc ON sc.snapshot_id = s.id
            WHERE s.gravado_em >= ?
            ORDER BY s.gravado_em DESC
            """,
            con,
            params=(limite,),
        )

def calcular_recorrencia(dias: int = 30) -> dict:
    df_hist = carregar_historico_clientes(dias)
    if df_hist.empty:
        return {}

    df_hist["dia"] = pd.to_datetime(df_hist["gravado_em"], errors="coerce").dt.date
    rows = []
    for wl_id, grupo in df_hist.groupby("wl_id"):
        dias_off = grupo.loc[grupo["offline"] > 0, "dia"].nunique()
        dias_crit = grupo.loc[grupo["pct_offline"] > 15, "dia"].nunique()
        rows.append({
            "wl_id": wl_id,
            "dias_offline": int(dias_off),
            "dias_criticos": int(dias_crit),
            "pior_pct": float(grupo["pct_offline"].max()),
            "maior_offline": int(grupo["offline"].max()),
        })
    return {r["wl_id"]: r for r in rows}

def montar_df_tempo(dados: dict) -> pd.DataFrame:
    rows = []
    for wl_id, v in dados.items():
        df_off = v["offline"]
        if df_off.empty:
            continue
        for _, row in df_off.iterrows():
            td = row.get("_tempo_off", timedelta(seconds=-1))
            if not isinstance(td, timedelta):
                td = timedelta(seconds=-1)
            horas = td.total_seconds() / 3600 if td.total_seconds() >= 0 else -1
            rows.append({
                "ID do Cliente": wl_id,
                "Nome Cliente": v["nome_cliente"],
                "Nome Franqueado": v["nome_empresa"],
                "ID da Câmera": row.get(COL_ID_CAM, "N/D"),
                "Nome da Câmera": row.get(COL_NOME_CAM, "N/D"),
                "Última vez Online": row.get(COL_ULT_ATU, pd.NaT),
                "Observações": row.get(COL_OBS, ""),
                "Faixa": faixa_tempo_horas(horas),
                "_horas": horas,
                "_td": td,
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("_horas", ascending=False)

def montar_df_clientes(dados: dict, tendencias: dict | None = None, delta_offs: dict | None = None,
                       recorrencia: dict | None = None) -> pd.DataFrame:
    tendencias = tendencias or {}
    delta_offs = delta_offs or {}
    recorrencia = recorrencia or {}
    rows = []
    for wl_id, v in dados.items():
        total = v["total"]
        offline = len(v["offline"])
        pct = round(offline / total * 100, 2) if total else 0
        validos = pd.Series(dtype="timedelta64[ns]")
        if offline and "_tempo_off" in v["offline"].columns:
            validos = v["offline"]["_tempo_off"][v["offline"]["_tempo_off"].dt.total_seconds() >= 0]
        max_h = validos.max().total_seconds() / 3600 if not validos.empty else -1
        media_h = validos.mean().total_seconds() / 3600 if not validos.empty else -1
        acima_24h = int((validos.dt.total_seconds() >= 86400).sum()) if not validos.empty else 0
        rec = recorrencia.get(wl_id, {})
        score = (offline * 6) + (pct * 2) + max(max_h, 0) / 12 + (acima_24h * 8) + (rec.get("dias_criticos", 0) * 5)
        rows.append({
            "ID": wl_id,
            "Cliente": v["nome_cliente"],
            "Franqueado": v["nome_empresa"],
            "Total": total,
            "Online": total - offline,
            "Offline": offline,
            "% Offline": pct,
            "Status": status_cliente(pct, offline),
            "Maior Tempo": fmt_tempo(timedelta(hours=max_h)) if max_h >= 0 else "N/D",
            "Tempo Médio": fmt_tempo(timedelta(hours=media_h)) if media_h >= 0 else "N/D",
            "Acima 24h": acima_24h,
            "Delta Offline": delta_offs.get(wl_id),
            "Delta %": tendencias.get(wl_id),
            "Dias Offline": rec.get("dias_offline", 0),
            "Dias Críticos": rec.get("dias_criticos", 0),
            "_max_horas": max_h,
            "_score": round(score, 2),
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────
# EXPORTAÇÃO EXCEL
# ─────────────────────────────────────────────
def gerar_excel(dados: dict) -> bytes:
    rows_resumo = []
    rows_offline = []
    agora = datetime.now()

    for wl_id, v in dados.items():
        total = v["total"]; off = len(v["offline"])
        pct   = round(off/total*100, 2) if total else 0
        rows_resumo.append({
            "ID do Cliente": wl_id,
            "Nome Franqueado": v["nome_empresa"],
            "Nome Cliente": v["nome_cliente"],
            "Total Câmeras": total,
            "Offline": off,
            "Online": total - off,
            "% Offline": pct,
            "Status": "Crítico" if pct > 15 else ("Atenção" if pct >= 10 else "Saudável"),
        })
        df_off = v["offline"].copy()
        if not df_off.empty:
            df_off.insert(0, "ID do Cliente", wl_id)
            df_off.insert(1, "Nome Franqueado", v["nome_empresa"])
            rows_offline.append(df_off)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(rows_resumo).sort_values("% Offline", ascending=False).to_excel(
            writer, index=False, sheet_name="Resumo Geral")
        if rows_offline:
            pd.concat(rows_offline, ignore_index=True).to_excel(
                writer, index=False, sheet_name="Câmeras Offline")
    return buf.getvalue()


# ─────────────────────────────────────────────
# PLOTLY — DEFAULTS
# ─────────────────────────────────────────────
def pdefaults() -> dict:
    return dict(
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="DM Sans", color="#4f6f85"),
    )


# ─────────────────────────────────────────────
# RENDER CARD DE CLIENTE
# ─────────────────────────────────────────────
def tabela_clara(df: pd.DataFrame):
    return (
        df.style
        .set_properties(**{
            "background-color": "#ffffff",
            "color": "#102a3f",
            "border-color": "#edf3f8",
        })
        .set_table_styles([
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#e8f7fc"),
                    ("color", "#007ab8"),
                    ("border-color", "#dbe8f2"),
                    ("font-weight", "700"),
                ],
            },
            {
                "selector": "tbody th",
                "props": [
                    ("background-color", "#f5f8fb"),
                    ("color", "#4f6f85"),
                    ("border-color", "#edf3f8"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("background-color", "#ffffff"),
                    ("color", "#102a3f"),
                    ("border-color", "#edf3f8"),
                ],
            },
        ])
    )


def render_dataframe(df: pd.DataFrame, height: int):
    st.dataframe(tabela_clara(df), use_container_width=True, height=height)


def render_card(col, wl_id, v, tendencia, delta_off):
    nome_display = escape_html(v["nome_cliente"])
    nome_empresa = escape_html(v["nome_empresa"])
    wl_id_html = escape_html(wl_id)
    count  = len(v["offline"])
    total  = v["total"]
    pct    = count/total*100 if total else 0
    card_c, count_c, label_c = classe_card(pct)
    cor    = cor_hex(pct)
    prog_w = min(pct, 100)
    label_txt = f"OPERACIONAL · {total} CÂMERAS" if count == 0 else f"OFFLINE DE {total} ({pct:.1f}%)"

    if tendencia is None or delta_off is None:
        trend_html = ""
    elif tendencia > 0.5:
        trend_html = f'<div class="trend-badge trend-up">▲ +{int(delta_off)} câmeras offline vs anterior</div>'
    elif tendencia < -0.5:
        trend_html = f'<div class="trend-badge trend-down">▼ {int(delta_off)} câmeras offline vs anterior</div>'
    else:
        trend_html = '<div class="trend-badge trend-same">→ Estável vs anterior</div>'

    sub_html = f'<div style="font-size:9px;color:#6b8496;margin-bottom:6px">{nome_empresa}</div>' if nome_empresa else ""
    id_html  = f'<div style="font-size:9px;color:#6b8496">ID: {wl_id_html}</div>'

    with col:
        card_html = f'<div class="unit-card {card_c}"><div class="unit-name">{nome_display}</div>{sub_html}<div class="unit-count {count_c}">{count}</div><div class="unit-label {label_c}">{label_txt}</div><div class="prog-track"><div class="prog-fill" style="width:{prog_w}%;background:{cor}"></div></div>{trend_html}{id_html}</div>'
        st.write(card_html, unsafe_allow_html=True)

        if count > 0:
            if st.button("🔎 Ver detalhes do cliente", key=f"btn_{wl_id}"):
                st.session_state["detalhe"] = wl_id
                st.rerun()
        else:
            st.button("✓ Operacional", key=f"btn_{wl_id}", disabled=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar(dados, total_cameras, total_offline, pct_global):
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo">
            <img src="https://framerusercontent.com/images/YQ4euyeSqXxIJm99xQGGCBYWYpg.png" style="height:30px;width:auto" alt="Camerite">
            <div>
                <div class="sidebar-logo-text">Camerite BI</div>
                <div class="sidebar-logo-sub">Auditoria Operacional</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="nav-section">Governança</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:1rem">
            <div style="background:#e8f7fc;border:1px solid #b9e7f4;border-radius:8px;padding:12px 14px">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Total Câmeras</div>
                <div style="font-size:24px;font-weight:700;color:#0088cc;font-family:'DM Mono',monospace">{total_cameras}</div>
            </div>
            <div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:8px;padding:12px 14px">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Offline</div>
                <div style="font-size:24px;font-weight:700;color:#ef4444;font-family:'DM Mono',monospace">{total_offline}</div>
                <div style="font-size:11px;color:#6b8496">{pct_global:.1f}% da frota</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="nav-section">Ações</div>', unsafe_allow_html=True)

        if st.button("🔄 Atualizar dados"):
            st.cache_data.clear(); st.rerun()

        st.markdown("---")
        st.markdown('<div class="nav-section">Salvar Snapshot</div>', unsafe_allow_html=True)
        lbl  = st.text_input("Rótulo", value=f"Snapshot {datetime.now().strftime('%d/%m %H:%M')}", key="snap_lbl")
        nota = st.text_area("Observações (opcional)", key="snap_nota", height=60)
        if st.button("💾 Salvar snapshot"):
            salvar_snapshot(lbl, nota, dados)
            st.success("Snapshot salvo!")

        st.markdown("---")
        if st.download_button(
            "⬇ Exportar Excel",
            data=gerar_excel(dados),
            file_name=f"camerite_bi_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ):
            pass


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    init_db()

    # ── Carregar dados: tenta pasta, fallback para upload ──
    dados, erro, df_origem = carregar_dados(PASTA)
    clientes_map = carregar_clientes()
    saude = calcular_saude_dados(PASTA)
    origem_local = True

    if not dados:
        # Mostrar diagnóstico e oferecer upload manual
        with st.sidebar:
            st.markdown('''
            <div class="sidebar-logo">
                <img src="https://framerusercontent.com/images/YQ4euyeSqXxIJm99xQGGCBYWYpg.png" style="height:30px;width:auto" alt="Camerite">
                <div>
                    <div class="sidebar-logo-text">Camerite BI</div>
                    <div class="sidebar-logo-sub">Auditoria Operacional</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

        st.markdown("""
        <div class="page-header">
            <div>
                <div class="page-title">Central de Monitoramento</div>
                <div class="page-sub">Configure a fonte de dados abaixo</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_err, col_up = st.columns([1, 1], gap="large")

        with col_err:
            st.error(f"**Arquivo não carregado automaticamente**\n\n{erro}" if erro else "Nenhum dado carregado.")
            st.info(
                f"**Caminho configurado:** `{CSV_GOV}`\n\n"
                "Verifique se o arquivo existe nesse caminho e se o nome está exatamente como "
                "`GOV_extracao_cameras.csv`."
            )

        with col_up:
            st.markdown("#### 📂 Upload manual do CSV")
            st.caption("Se o arquivo não está sendo lido automaticamente, faça o upload aqui:")
            arq_csv = st.file_uploader("GOV_extracao_cameras.csv", type=["csv"], key="upload_gov_csv")
            arq_xlsx = st.file_uploader("nome_clientes.xlsx (opcional)", type=["xlsx"], key="upload_clientes")

            if arq_csv is not None:
                try:
                    df_up = None
                    for enc in ("utf-8", "latin-1", "cp1252"):
                        for sep in (",", ";", "\t"):
                            try:
                                arq_csv.seek(0)
                                df_up = pd.read_csv(
                                    arq_csv, encoding=enc, sep=sep,
                                    on_bad_lines="skip",
                                    engine="python",
                                    quoting=0,
                                )
                                df_up.columns = [c.strip() for c in df_up.columns]
                                if len(df_up.columns) >= 2:
                                    break
                                df_up = None
                            except UnicodeDecodeError:
                                break
                            except Exception:
                                continue
                        if df_up is not None:
                            break

                    if df_up is None:
                        st.error("Não foi possível ler o CSV. Tente salvar como UTF-8.")
                        return

                    cols_faltando = [c for c in [COL_STATUS, COL_WL] if c not in df_up.columns]
                    if cols_faltando:
                        st.error(f"Colunas não encontradas: `{'`, `'.join(cols_faltando)}`\n\nColunas no arquivo: `{'`, `'.join(df_up.columns.tolist())}`")
                        return

                    cl_map_up = {}
                    if arq_xlsx is not None:
                        try:
                            df_cl = pd.read_excel(arq_xlsx, engine="openpyxl")
                            col_id  = next((c for c in df_cl.columns if "whitelabel" in c.lower() or "id" in c.lower()), df_cl.columns[0])
                            col_nom = next((c for c in df_cl.columns if "nome" in c.lower() or "client" in c.lower()), df_cl.columns[1])
                            cl_map_up = dict(zip(df_cl[col_id].astype(str).str.strip(), df_cl[col_nom].astype(str).str.strip()))
                        except Exception as e:
                            st.warning(f"Não foi possível ler o XLSX de clientes: {e}")

                    dados = processar_df_gov(df_up, cl_map_up)
                    saude = calcular_saude_dataframe(df_up, cl_map_up, "Upload manual")
                    origem_local = False
                    st.success(f"CSV carregado! {len(df_up)} linhas · {len(dados)} clientes encontrados.")
                    # Não há st.rerun aqui — o código continua abaixo com dados preenchidos
                except Exception as e:
                    st.error(f"Erro ao processar o arquivo: {e}")
                    return
            else:
                st.caption("Aguardando upload do CSV…")
                return

    if erro:
        st.warning(erro)

    # ── Métricas globais ──
    total_clientes = len(dados)
    total_cameras  = sum(v["total"] for v in dados.values())
    total_offline  = sum(len(v["offline"]) for v in dados.values())
    pct_global     = round(total_offline/total_cameras*100, 2) if total_cameras else 0
    n_critico      = sum(1 for v in dados.values() if (len(v["offline"])/v["total"]*100 if v["total"] else 0) > 15)
    n_atencao      = sum(1 for v in dados.values() if 10 <= (len(v["offline"])/v["total"]*100 if v["total"] else 0) <= 15)
    clientes_alert = sum(1 for v in dados.values() if len(v["offline"]) > 0)
    n_saudavel     = total_clientes - n_critico - n_atencao
    audit_label, audit_color, audit_reason = classificar_auditoria(pct_global, n_critico, n_atencao, saude)
    fonte_label, fonte_color = classificar_fonte(saude)
    acao_curta, acao_detalhe = recomendacao_auditoria(n_critico, n_atencao, saude)
    pct_clientes_criticos = round(n_critico / total_clientes * 100, 1) if total_clientes else 0
    pct_clientes_atencao = round(n_atencao / total_clientes * 100, 1) if total_clientes else 0

    # Comparar com o snapshot mais recente antes de gravar o automático do dia.
    df_ult = snapshot_referencia()
    if df_ult is not None:
        ref_pct = df_ult.set_index("wl_id")["pct_offline"].to_dict()
        ref_off = df_ult.set_index("wl_id")["offline"].to_dict()
        tendencias = {wl: round((len(v["offline"])/v["total"]*100 if v["total"] else 0) - ref_pct.get(wl, 0), 2)
                      for wl, v in dados.items()}
        delta_offs = {wl: len(v["offline"]) - ref_off.get(wl, 0)
                      for wl, v in dados.items()}
    else:
        tendencias = {wl: None for wl in dados}
        delta_offs = {wl: None for wl in dados}

    snapshot_auto_msg = salvar_snapshot_automatico(dados) if origem_local else ""

    recorrencia = calcular_recorrencia(30)
    df_clientes_ops = montar_df_clientes(dados, tendencias, delta_offs, recorrencia)
    df_tempo_global = montar_df_tempo(dados)
    delta_global = sum(v for v in delta_offs.values() if isinstance(v, (int, float)))
    clientes_melhoraram = sum(1 for v in delta_offs.values() if isinstance(v, (int, float)) and v < 0)
    clientes_pioraram = sum(1 for v in delta_offs.values() if isinstance(v, (int, float)) and v > 0)

    # ── Sidebar ──
    render_sidebar(dados, total_cameras, total_offline, pct_global)

    # ── Page header ──
    st.markdown(f"""
    <div class="page-header">
        <div>
            <div class="page-title">Sala de Auditoria Operacional</div>
            <div class="page-sub">{total_clientes} clientes · {total_cameras} câmeras monitoradas · foco em evidência, risco e responsabilização</div>
        </div>
        <div class="page-badge" style="color:{audit_color};background:#ffffff;border-color:{audit_color}">Status: {audit_label} · {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── ABAS ──
    tabs = st.tabs([
        "Auditoria",
        "Clientes",
        "Tempo offline",
        "% por cliente",
        "Ranking de risco",
        "Evidências",
    ])

    # ════════════════════════════════════════════
    # ABA 0 — VISÃO EXECUTIVA
    # ════════════════════════════════════════════
    with tabs[0]:
        st.markdown(f"""
        <div class="audit-hero">
            <div class="audit-hero-top">
                <div>
                    <div class="audit-title">Ação imediata</div>
                    <div class="audit-sub">
                        {acao_detalhe}
                    </div>
                </div>
                <div class="audit-badges">
                    <div class="audit-badge" style="color:{audit_color}">{audit_label}</div>
                    <div class="audit-badge" style="color:{fonte_color}">Fonte {fonte_label}</div>
                </div>
            </div>
        </div>
        <div class="audit-strip">
            <div class="audit-card">
                <div class="audit-card-label">Clientes críticos</div>
                <div class="audit-card-value" style="color:#dc2626">{n_critico}/{total_clientes}</div>
                <div class="audit-card-note">{pct_clientes_criticos:.1f}% da carteira auditada acima de 15% offline</div>
            </div>
            <div class="audit-card">
                <div class="audit-card-label">Clientes em atenção</div>
                <div class="audit-card-value" style="color:#d97706">{n_atencao}</div>
                <div class="audit-card-note">{pct_clientes_atencao:.1f}% da carteira auditada entre 10% e 15% offline</div>
            </div>
            <div class="audit-card">
                <div class="audit-card-label">Registros auditados</div>
                <div class="audit-card-value">{saude.get("linhas_processadas",0)}</div>
                <div class="audit-card-note">{saude.get("linhas_fora_escopo",0)} fora do escopo · {saude.get("linhas_csv",0)} na origem</div>
            </div>
            <div class="audit-card">
                <div class="audit-card-label">Alertas de data</div>
                <div class="audit-card-value" style="color:{'#d97706' if (saude.get('datas_invalidas',0) or saude.get('datas_futuras',0)) else '#059669'}">{saude.get("datas_invalidas",0) + saude.get("datas_futuras",0)}</div>
                <div class="audit-card-note">{saude.get("datas_invalidas",0)} inválidas · {saude.get("datas_futuras",0)} futuras</div>
            </div>
        </div>
        <div class="audit-riskbar">
            <div>
                <div style="font-size:11px;color:#60798d;font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:7px">Carteira acima do limite crítico</div>
                <div class="audit-risk-track"><div class="audit-risk-fill" style="width:{pct_clientes_criticos}%;background:{audit_color}"></div></div>
            </div>
            <div class="audit-risk-label" style="color:{audit_color}">{pct_clientes_criticos:.1f}% dos clientes</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="audit-section-title">
            <strong>Indicadores de controle</strong>
            <span>Base para reunião de acompanhamento e cobrança de responsáveis</span>
        </div>
        """, unsafe_allow_html=True)

        # Top KPIs: apenas 3 cards conforme solicitado
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card kpi-neutral">
                <div class="kpi-label">Total de Câmeras</div>
                <div class="kpi-value val-purple">{total_cameras}</div>
                <div class="kpi-sub">{total_clientes} clientes monitorados</div>
            </div>
            <div class="kpi-card kpi-alert">
                <div class="kpi-label">Câmeras Offline</div>
                <div class="kpi-value val-alert">{total_offline}</div>
                <div class="kpi-sub">{pct_global:.1f}% da frota total</div>
            </div>
            <div class="kpi-card kpi-ok">
                <div class="kpi-label">Câmeras Online</div>
                <div class="kpi-value val-ok">{total_cameras - total_offline}</div>
                <div class="kpi-sub">{100-pct_global:.1f}% operacionais</div>
            </div>
            <div class="kpi-card kpi-neutral">
                <div class="kpi-label">Variação vs anterior</div>
                <div class="kpi-value" style="font-size:28px;font-weight:700;color:{'#ef4444' if delta_global > 0 else ('#14b8a6' if delta_global < 0 else '#0088cc')};">{delta_global:+.0f}</div>
                <div class="kpi-sub">{clientes_melhoraram} melhoraram · {clientes_pioraram} pioraram</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Lower cards: novos cartões de categoria + Variação e Data CSV
        if "audit_categoria" not in st.session_state:
            st.session_state["audit_categoria"] = None

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.markdown(f"""
                <div class="kpi-card kpi-ok" style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#6b8496;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes abaixo de 10% offline</div>
                    <div style="font-size:24px;color:#14b8a6;font-family:'DM Mono',monospace;font-weight:700">{n_saudavel}</div>
                    <div style="font-size:11px;color:#6b8496">{n_saudavel} clientes &lt; 10%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_saudavel"):
                st.session_state["audit_categoria"] = "Saudável (<10%)"
        with col_b:
            st.markdown(f"""
                <div class="kpi-card kpi-warn" style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#6b8496;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes entre 10 e 15% offline</div>
                    <div style="font-size:24px;color:#f59e0b;font-family:'DM Mono',monospace;font-weight:700">{n_atencao}</div>
                    <div style="font-size:11px;color:#6b8496">{n_atencao} clientes · 10–15%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_atencao"):
                st.session_state["audit_categoria"] = "Atenção (10-15%)"
        with col_c:
            st.markdown(f"""
                <div class="kpi-card kpi-alert" style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#6b8496;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes acima de 15% offline</div>
                    <div style="font-size:24px;color:#ef4444;font-family:'DM Mono',monospace;font-weight:700">{n_critico}</div>
                    <div style="font-size:11px;color:#6b8496">{n_critico} clientes · &gt;15%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_critico"):
                st.session_state["audit_categoria"] = "Crítico (>15%)"
        with col_d:
            st.markdown(f"""
                <div style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#6b8496;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Data CSV</div>
                    <div style="font-size:16px;color:#102a3f;font-family:'DM Mono',monospace;font-weight:700">{saude.get("ultima_data","N/D")}</div>
                    <div style="font-size:11px;color:#6b8496">Arquivo: {saude.get("arquivo_atualizado","N/D")}</div>
                </div>
            """, unsafe_allow_html=True)

        if st.session_state["audit_categoria"]:
            categoria = st.session_state["audit_categoria"]
            df_audit = df_clientes_ops.copy()
            if categoria == "Saudável (<10%)":
                mask = df_audit["% Offline"] < 10
            elif categoria == "Atenção (10-15%)":
                mask = (df_audit["% Offline"] >= 10) & (df_audit["% Offline"] <= 15)
            else:
                mask = df_audit["% Offline"] > 15

            df_audit = df_audit.loc[mask, ["Cliente", "Franqueado", "% Offline"]].copy()
            df_audit["% Offline"] = df_audit["% Offline"].round(1)
            df_audit = df_audit.sort_values("% Offline", ascending=False).reset_index(drop=True)
            st.markdown(f"### Clientes na faixa: {categoria}")
            if df_audit.empty:
                st.info("Nenhum cliente encontrado nessa faixa.")
            else:
                render_dataframe(df_audit, height=min(500, (len(df_audit)+1)*35 + 3))
            if st.button("Limpar seleção", key="audit_clear"):
                st.session_state["audit_categoria"] = None

        if saude.get("colunas_faltando"):
            st.warning(f"Colunas ausentes no CSV: {', '.join(saude['colunas_faltando'])}")
        elif saude.get("datas_futuras", 0):
            st.warning(f"{saude['datas_futuras']} registros têm data futura. Revise o formato de data da extração.")
        elif saude.get("datas_invalidas", 0):
            st.warning(f"{saude['datas_invalidas']} registros têm data inválida e foram marcados como N/D.")

        if snapshot_auto_msg:
            st.caption(f"Snapshot automático registrado às {snapshot_auto_msg}.")

        st.markdown("""
        <div class="audit-section-title">
            <strong>Evidências visuais</strong>
            <span>Distribuição do risco e clientes com maior exposição</span>
        </div>
        """, unsafe_allow_html=True)

        col_gauge, col_pie, col_top = st.columns([1,1,1], gap="large")

        with col_gauge:
            st.markdown("**Índice de criticidade global**")
            cor_g = cor_hex(pct_global)
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pct_global,
                number=dict(suffix="%", font=dict(color=cor_g, size=48, family="DM Mono")),
                gauge=dict(
                    shape="angular",
                    axis=dict(range=[0,100], showticklabels=False, ticks="", visible=False),
                    bar=dict(color=cor_g, thickness=0.34),
                    bgcolor="#f5f8fb",
                    borderwidth=0,
                    steps=[
                        dict(range=[0,10],   color="#ecfdf5"),
                        dict(range=[10,15],  color="#fffbeb"),
                        dict(range=[15,100], color="#fef2f2"),
                    ],
                    threshold=dict(line=dict(color="#475569", width=4), thickness=0.75, value=pct_global),
                ),
            ))
            layout_defaults = {k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]}
            fig_g.update_layout(
                **layout_defaults,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
                margin=dict(l=0,r=0,t=10,b=0),
                annotations=[
                    dict(
                        text=f"<span style='font-size:12px;color:#6b8496;font-family:DM Sans'>Nível de risco</span>",
                        x=0.5, y=0.08, showarrow=False, xanchor="center"
                    )
                ],
            )
            st.plotly_chart(fig_g, use_container_width=True)

        with col_pie:
            st.markdown("**Distribuição por faixa de saúde**")
            fig_pie = go.Figure(go.Pie(
                labels=["Crítico >15%","Atenção 10–15%","Saudável <10%"],
                values=[n_critico, n_atencao, n_saudavel],
                hole=0.56,
                sort=False,
                marker=dict(colors=["#dc2626","#d97706","#059669"], line=dict(color="#ffffff", width=2)),
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>%{value} clientes (%{percent})<extra></extra>",
            ))
            fig_pie.update_traces(rotation=45, pull=[0.05, 0.03, 0], textposition="inside", insidetextorientation="radial",
                                   textfont=dict(color="#ffffff", size=12, family="DM Sans"))
            fig_pie.add_annotation(
                text=f"<span style='font-size:13px;font-weight:700;color:#102a3f;font-family:DM Mono'>{total_clientes}</span><br><span style='font-size:11px;color:#6b8496;font-family:DM Sans'>clientes</span>",
                x=0.5, y=0.5, showarrow=False,
            )
            layout_defaults = {k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]}
            fig_pie.update_layout(
                **layout_defaults,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
                legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center", font=dict(size=11, color="#6b8496")),
                margin=dict(l=10,r=10,t=20,b=40),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_top:
            st.markdown("**Top 5 clientes mais críticos**")
            rows_top = [
                {"Cliente": v["nome_cliente"],
                 "Franqueado": v["nome_empresa"],
                 "Pct": round(len(v["offline"])/v["total"]*100, 1) if v["total"] else 0,
                 "Off": len(v["offline"]), "Tot": v["total"]}
                for v in dados.values() if len(v["offline"]) > 0
            ]
            df_top = (
                pd.DataFrame(rows_top).sort_values("Pct", ascending=False).head(5)
                if rows_top else pd.DataFrame()
            )

            if df_top.empty:
                st.success("🎉 Todos os clientes estão operacionais!")
            else:
                for _, row in df_top.iterrows():
                    cor = cor_hex(row["Pct"])
                    cliente_html = escape_html(row["Cliente"])
                    franqueado_html = escape_html(row["Franqueado"])
                    pct_html = f"{row['Pct']:.1f}%"
                    width_pct = min(row["Pct"], 100)
                    offline_text = f"{int(row['Off'])} offline de {int(row['Tot'])}"
                    st.markdown(f"""
                    <div style="margin-bottom:14px">
                        <div style="display:flex;justify-content:space-between;margin-bottom:2px">
                            <span style="font-size:12px;color:#102a3f;font-weight:600">{cliente_html}</span>
                            <span style="font-family:'DM Mono',monospace;font-size:12px;color:{cor};font-weight:700">{pct_html}</span>
                        </div>
                        <div style="font-size:10px;color:#6b8496;margin-bottom:4px">{franqueado_html}</div>
                        <div style="height:5px;background:#dbe8f2;border-radius:99px;overflow:hidden">
                            <div style="height:100%;width:{width_pct}%;background:{cor};border-radius:99px"></div>
                        </div>
                        <div style="font-size:10px;color:#6b8496;margin-top:3px">{offline_text}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("**Mapa de calor — % offline por cliente**")
        # Inclui todos os clientes cadastrados no nome_clientes.xlsx,
        # mesmo aqueles sem câmeras no CSV (aparecem com 0%).
        rows_heat = []
        for v in dados.values():
            rows_heat.append({
                "Cliente": v["nome_cliente"],
                "Pct": round(len(v["offline"]) / v["total"] * 100, 2) if v["total"] else 0,
            })
        clientes_no_csv = {v["nome_cliente"] for v in dados.values()}
        for wl_id, nome in clientes_map.items():
            if nome not in clientes_no_csv:
                rows_heat.append({"Cliente": nome, "Pct": 0.0})
        df_heat = pd.DataFrame(rows_heat).sort_values("Pct", ascending=False)

        fig_map, mapa_msg = montar_mapa_cidades(df_origem)
        if fig_map is not None:
            st.plotly_chart(fig_map, use_container_width=True)
            st.caption(mapa_msg)
        else:
            st.info(mapa_msg)

        fig_heat = go.Figure(go.Bar(
            x=df_heat["Cliente"], y=df_heat["Pct"],
            marker=dict(
                color=df_heat["Pct"],
                colorscale=[[0,"#dff8f3"],[0.10,"#14b8a6"],[0.15,"#f59e0b"],[1,"#ef4444"]],
                cmin=0, cmax=100, line=dict(width=0),
            ),
            hovertemplate="<b>%{x}</b><br>%{y:.1f}% offline<extra></extra>",
        ))
        layout_defaults = {k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]}
        _heat_height = max(300, min(len(df_heat) * 22, 600))
        fig_heat.update_layout(
            **layout_defaults,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=_heat_height,
            xaxis=dict(tickfont=dict(color="#6b8496",size=10), tickangle=-45),
            yaxis=dict(ticksuffix="%", gridcolor="#dbe8f2",
                       tickfont=dict(color="#6b8496",size=10),
                       range=[0, max(df_heat["Pct"].max()*1.2, 10)]),
            margin=dict(l=10,r=10,t=10,b=110),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # ════════════════════════════════════════════
    # ABA 1 — PAINEL DE CLIENTES
    # ════════════════════════════════════════════
    with tabs[1]:
        franqueados = ["Todos"] + sorted([x for x in df_clientes_ops["Franqueado"].dropna().unique().tolist() if str(x).strip()])
        if "status_filter" not in st.session_state:
            st.session_state["status_filter"] = "Todos"

        st.caption("Clique no grupo para filtrar os clientes conforme a faixa de % offline.")
        btns = st.columns([1,1,1,1])
        if btns[0].button("Todos"):
            st.session_state["status_filter"] = "Todos"
        if btns[1].button("Saudável (<10%)"):
            st.session_state["status_filter"] = "Saudável (<10%)"
        if btns[2].button("Atenção (10-15%)"):
            st.session_state["status_filter"] = "Atenção (10-15%)"
        if btns[3].button("Crítico (>15%)"):
            st.session_state["status_filter"] = "Crítico (>15%)"

        col_search, col_franq, col_min = st.columns([2,2,1])
        with col_search:
            busca = st.text_input("Buscar", placeholder="Buscar cliente ou franqueado…")
        with col_franq:
            filtro_franq = st.selectbox("Franqueado", franqueados)
        with col_min:
            min_cameras = st.selectbox("Min. câmeras", [0, 10, 50, 100, 200])

        filtro = st.session_state["status_filter"]

        def passa_filtro(wl_id, v):
            row = df_clientes_ops[df_clientes_ops["ID"] == wl_id].iloc[0]
            termo = busca.upper()
            if busca and termo not in v["nome_cliente"].upper() and termo not in v["nome_empresa"].upper() and termo not in wl_id.upper():
                return False
            if filtro_franq != "Todos" and row["Franqueado"] != filtro_franq:
                return False
            if filtro != "Todos" and row["Status"] != filtro:
                return False
            if row["Total"] < min_cameras:
                return False
            return True

        ids_ord = df_clientes_ops.sort_values("% Offline", ascending=False)["ID"].tolist()
        ids_f = [wl for wl in ids_ord if passa_filtro(wl, dados[wl])]

        if not ids_f:
            st.info("Nenhum cliente encontrado com os filtros aplicados.")
        else:
            df_filtrado = df_clientes_ops[df_clientes_ops["ID"].isin(ids_f)].copy()
            c_res, c_dl = st.columns([4,1])
            c_res.caption(f"{len(ids_f)} clientes no recorte · {int(df_filtrado['Offline'].sum())} câmeras offline")
            buf_filtro = io.BytesIO()
            df_filtrado.drop(columns=["_score","_max_horas"], errors="ignore").to_excel(buf_filtro, index=False, engine="openpyxl")
            c_dl.download_button(
                "⬇ Exportar recorte",
                data=buf_filtro.getvalue(),
                file_name=f"clientes_filtrados_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            for linha in [ids_f[i:i+COLUNAS_PAINEL] for i in range(0, len(ids_f), COLUNAS_PAINEL)]:
                cols = st.columns(COLUNAS_PAINEL)
                for col, wl_id in zip(cols, linha):
                    render_card(col, wl_id, dados[wl_id], tendencias.get(wl_id), delta_offs.get(wl_id))

        # ── Detalhe de um cliente ──
        if "detalhe" in st.session_state:
            wl_id  = st.session_state["detalhe"]
            v      = dados.get(wl_id, {"nome_cliente":"?","nome_empresa":"","offline":pd.DataFrame(),"total":0})
            df_det = v["offline"].copy()
            total_u= v["total"]
            pct_d  = round(len(df_det)/total_u*100, 1) if total_u else 0
            cor_d  = cor_hex(pct_d)
            agora  = datetime.now()
            nome_cliente_html = escape_html(v["nome_cliente"])
            nome_empresa_html = escape_html(v["nome_empresa"])
            wl_id_html = escape_html(wl_id)

            st.markdown("<hr>", unsafe_allow_html=True)
            html_det = (
                '<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;flex-wrap:wrap">'
                '<div style="background:rgba(0,136,204,.12);border:1px solid rgba(0,136,204,.22);'
                'border-radius:8px;padding:6px 14px;font-size:11px;font-weight:600;'
                'color:#007ab8;text-transform:uppercase;letter-spacing:.5px">📍 Detalhamento</div>'
                '<div>'
                + f'<div style="font-size:20px;font-weight:700;color:#0088cc">{nome_cliente_html}</div>'
                + f'<div style="font-size:12px;color:#6b8496">{nome_empresa_html} · ID: {wl_id_html}</div>'
                + '</div>'
                + f'<div style="margin-left:auto;font-size:13px;font-weight:700;color:{cor_d}">'
                + f'{len(df_det)} offline de {total_u} câmeras ({pct_d}%)'
                + '</div>'
                + '</div>'
            )
            st.markdown(html_det, unsafe_allow_html=True)

            df_cli_row = df_clientes_ops[df_clientes_ops["ID"] == wl_id]
            if not df_cli_row.empty:
                cli_row = df_cli_row.iloc[0]
                delta_txt = "N/D" if pd.isna(cli_row["Delta Offline"]) else f"{int(cli_row['Delta Offline']):+d}"
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total", int(cli_row["Total"]))
                m2.metric("Offline", int(cli_row["Offline"]), delta=delta_txt if delta_txt != "N/D" else None)
                m3.metric("% Offline", f"{cli_row['% Offline']:.1f}%")
                m4.metric("Maior tempo", cli_row["Maior Tempo"])
                m5.metric("Dias críticos", int(cli_row["Dias Críticos"]))

            if df_det.empty:
                st.success("Nenhuma câmera offline.")
            else:
                # Selecionar colunas relevantes e renomear para exibição
                col_map = {
                    COL_ID_CAM:   "ID da Câmera",
                    COL_NOME_CAM: "Nome da Câmera",
                    COL_ULT_ATU:  "Última vez Online",
                    COL_OBS:      "Observações",
                }
                internal_cols = {COL_WL, COL_EMPRESA, COL_STATUS, "_tempo_off"}
                base_cols = [COL_ID_CAM, COL_NOME_CAM, COL_ULT_ATU, COL_OBS]
                cols_ex = [c for c in base_cols if c in df_det.columns] + [c for c in df_det.columns if c not in internal_cols and c not in base_cols]

                if COL_ULT_ATU in df_det.columns:
                    # Já vem ordenado por tempo offline (mais antigo primeiro)
                    df_show = df_det[cols_ex].copy()
                    df_show = df_show.rename(columns=col_map)

                    # Adicionar coluna de tempo offline calculado
                    if "Última vez Online" in df_show.columns:
                        df_show.insert(
                            df_show.columns.get_loc("Última vez Online") + 1,
                            "Tempo Offline",
                            df_det["_tempo_off"].apply(
                                lambda td: fmt_tempo(td) if td.total_seconds() >= 0 else "N/D"
                            ).values
                        )

                    # Formatar data
                    if "Última vez Online" in df_show.columns:
                        df_show["Última vez Online"] = formatar_ultima_atualizacao(df_show["Última vez Online"])
                else:
                    df_show = df_det[cols_ex].copy().rename(columns=col_map)

                df_show = df_show.reset_index(drop=True)
                df_show.index += 1
                st.caption(f"⬆ Ordenado por tempo offline — quem está há mais tempo sem sinal aparece primeiro")
                render_dataframe(df_show, height=min(500,(len(df_show)+1)*35+3))

                # Mini-métricas de tempo
                if "_tempo_off" in df_det.columns:
                    validos = df_det["_tempo_off"][df_det["_tempo_off"].dt.total_seconds() >= 0]
                    if not validos.empty:
                        col_t1, col_t2, col_t3 = st.columns(3)
                        mais_antigo = validos.max()
                        media_td    = validos.mean()
                        acima_24h   = (validos.dt.total_seconds() >= 86400).sum()
                        col_t1.metric("⏱️ Mais tempo offline", fmt_tempo(mais_antigo))
                        col_t2.metric("📊 Tempo médio offline", fmt_tempo(media_td))
                        col_t3.metric("🔴 Acima de 24h", f"{acima_24h} câmeras")

            if st.button("← Voltar ao painel"):
                del st.session_state["detalhe"]; st.rerun()

    # ════════════════════════════════════════════
    # ABA 2 — TEMPO OFFLINE
    # ════════════════════════════════════════════
    with tabs[2]:
        st.markdown("#### Câmeras offline por tempo sem sinal")
        st.caption("Identifique as câmeras que estão há mais tempo sem atualização — ordenadas do mais crítico ao menos crítico")

        # Montar DataFrame global com todas as câmeras offline
        rows_tempo = []
        agora = datetime.now()
        for wl_id, v in dados.items():
            df_off = v["offline"]
            if df_off.empty: continue
            for _, row in df_off.iterrows():
                td = row.get("_tempo_off", timedelta(seconds=-1))
                if not isinstance(td, timedelta): td = timedelta(seconds=-1)
                horas = td.total_seconds()/3600 if td.total_seconds() >= 0 else -1
                rows_tempo.append({
                    "ID do Cliente": wl_id,
                    "Nome Cliente":  v["nome_cliente"],
                    "Nome Franqueado": v["nome_empresa"],
                    "ID da Câmera":  row.get(COL_ID_CAM,  "N/D"),
                    "Nome da Câmera":row.get(COL_NOME_CAM,"N/D"),
                    "Última vez Online": row.get(COL_ULT_ATU, pd.NaT),
                    "Observações":   row.get(COL_OBS, ""),
                    "Faixa":         faixa_tempo_horas(horas),
                    "_horas":        horas,
                    "_td":           td,
                })

        if not rows_tempo:
            st.success("🎉 Nenhuma câmera offline no momento!")
        else:
            df_tempo = pd.DataFrame(rows_tempo).sort_values("_horas", ascending=False)

            # KPIs de tempo
            validos    = df_tempo[df_tempo["_horas"] >= 0]
            acima_24h  = (validos["_horas"] >= 24).sum()
            acima_6h   = ((validos["_horas"] >= 6) & (validos["_horas"] < 24)).sum()
            abaixo_6h  = (validos["_horas"] < 6).sum()
            nd_count   = (df_tempo["_horas"] < 0).sum()

            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(f'''<div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Acima de 24h</div>
                <div style="font-size:32px;font-weight:700;color:#ef4444;font-family:DM Mono,monospace">{acima_24h}</div>
                <div style="font-size:11px;color:#6b8496">câmeras críticas</div></div>''', unsafe_allow_html=True)
            k2.markdown(f'''<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Entre 6h e 24h</div>
                <div style="font-size:32px;font-weight:700;color:#f59e0b;font-family:DM Mono,monospace">{acima_6h}</div>
                <div style="font-size:11px;color:#6b8496">câmeras em atenção</div></div>''', unsafe_allow_html=True)
            k3.markdown(f'''<div style="background:#ecfdf5;border:1px solid #99f6e4;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Menos de 6h</div>
                <div style="font-size:32px;font-weight:700;color:#14b8a6;font-family:DM Mono,monospace">{abaixo_6h}</div>
                <div style="font-size:11px;color:#6b8496">câmeras recentes</div></div>''', unsafe_allow_html=True)
            k4.markdown(f'''<div style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Sem data</div>
                <div style="font-size:32px;font-weight:700;color:#6b8496;font-family:DM Mono,monospace">{nd_count}</div>
                <div style="font-size:11px;color:#6b8496">sem informação</div></div>''', unsafe_allow_html=True)

            faixa_counts = df_tempo["Faixa"].value_counts().to_dict()
            st.markdown(
                " · ".join([f"**{fx}:** {faixa_counts.get(fx, 0)}" for fx in FAIXAS_TEMPO if fx != "Todas"])
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # Filtros
            col_f1, col_f2, col_f3 = st.columns([2,2,1])
            with col_f1:
                busca_t = st.text_input("Buscar", key="busca_tempo",
                                        placeholder="Buscar câmera ou cliente…")
            with col_f2:
                faixa = st.selectbox("Faixa de tempo", FAIXAS_TEMPO,
                                     key="faixa_tempo")
            with col_f3:
                top_n_t = st.selectbox("Exibir", ["Top 50","Top 100","Top 200","Todas"],
                                       key="top_n_tempo")

            df_exib = df_tempo.copy()
            if busca_t:
                termo = busca_t.upper()
                df_exib = df_exib[
                    df_exib["Nome da Câmera"].astype(str).str.upper().str.contains(termo) |
                    df_exib["Nome Cliente"].str.upper().str.contains(termo) |
                    df_exib["Nome Franqueado"].astype(str).str.upper().str.contains(termo) |
                    df_exib["ID do Cliente"].astype(str).str.upper().str.contains(termo) |
                    df_exib["ID da Câmera"].astype(str).str.upper().str.contains(termo)
                ]
            if faixa != "Todas":
                df_exib = df_exib[df_exib["Faixa"] == faixa]

            lim = {"Top 50":50,"Top 100":100,"Top 200":200}.get(top_n_t, len(df_exib))
            df_exib = df_exib.head(lim)

            if df_exib.empty:
                st.info("Nenhuma câmera encontrada com os filtros aplicados.")
            else:
                # Gráfico de barras horizontais — Top 30 por horas
                df_graf = df_exib[df_exib["_horas"] >= 0].head(30)
                if not df_graf.empty:
                    st.markdown(f"**Top {min(30,len(df_graf))} câmeras — tempo offline (horas)**")
                    cores_t = ["#dc2626" if h>=24 else ("#d97706" if h>=6 else "#059669") for h in df_graf["_horas"]]
                    labels_t = [f"{r['Nome da Câmera']} · {r['Nome Cliente']}" for _, r in df_graf.iterrows()]
                    fig_t = go.Figure(go.Bar(
                        y=labels_t, x=df_graf["_horas"],
                        orientation="h",
                        marker=dict(color=cores_t, line=dict(width=0)),
                        text=[fmt_tempo(td) for td in df_graf["_td"]],
                        textposition="outside",
                        textfont=dict(size=10, color="#6b8496", family="DM Mono"),
                        hovertemplate="<b>%{y}</b><br>%{x:.1f}h offline<extra></extra>",
                    ))
                    fig_t.add_vline(x=6,  line_dash="dot", line_color="#d97706", line_width=1,
                                    annotation_text="6h", annotation_font=dict(color="#d97706",size=10))
                    fig_t.add_vline(x=24, line_dash="dot", line_color="#dc2626", line_width=1,
                                    annotation_text="24h", annotation_font=dict(color="#dc2626",size=10))
                    fig_t.update_layout(
                        **pdefaults(), height=max(400, len(df_graf)*30), showlegend=False,
                        xaxis=dict(title="Horas offline", gridcolor="#dbe8f2",
                                   tickfont=dict(color="#6b8496",size=10), zeroline=False),
                        yaxis=dict(tickfont=dict(color="#4f6f85",size=10)),
                        margin=dict(l=10, r=80, t=20, b=20),
                    )
                    st.plotly_chart(fig_t, use_container_width=True)

                # Tabela detalhada
                st.markdown(f"**Lista detalhada — {len(df_exib)} câmeras**")
                df_tbl_t = df_exib[["Nome Cliente","Nome Franqueado","ID da Câmera","Nome da Câmera","Faixa","Última vez Online","Observações","_horas","_td"]].copy()
                df_tbl_t["Tempo Offline"] = df_tbl_t["_td"].apply(lambda td: fmt_tempo(td) if isinstance(td,timedelta) and td.total_seconds()>=0 else "N/D")
                df_tbl_t["Última vez Online"] = formatar_ultima_atualizacao(df_tbl_t["Última vez Online"])
                df_tbl_t["Criticidade"] = df_tbl_t["_horas"].apply(
                    lambda h: "🔴 Crítico (>24h)" if h>=24 else ("🟡 Atenção (6–24h)" if h>=6 else ("🟢 Recente (<6h)" if h>=0 else "⚫ Sem data"))
                )
                df_tbl_t = df_tbl_t.drop(columns=["_horas","_td"]).reset_index(drop=True)
                df_tbl_t.index += 1
                # Reordenar colunas
                df_tbl_t = df_tbl_t[["Criticidade","Faixa","Tempo Offline","Nome da Câmera","ID da Câmera","Nome Cliente","Nome Franqueado","Última vez Online","Observações"]]

                # Download
                buf_t = io.BytesIO()
                df_tbl_t.to_excel(buf_t, index=True, engine="openpyxl")
                st.download_button("⬇ Exportar lista",
                    data=buf_t.getvalue(),
                    file_name=f"tempo_offline_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                render_dataframe(df_tbl_t, height=min(600,(len(df_tbl_t)+1)*35+3))

    # ════════════════════════════════════════════
    # ABA 3 — % OFFLINE POR CLIENTE
    # ════════════════════════════════════════════
    with tabs[3]:
        st.markdown("#### Percentual de câmeras offline por cliente")
        st.caption("Escala 0–100% · Verde <10% · Amarelo 10–15% · Vermelho >15%")

        df_bar = pd.DataFrame([
            {"Cliente": v["nome_cliente"], "Offline": len(v["offline"]),
             "Total": v["total"],
             "Pct": round(len(v["offline"])/v["total"]*100, 2) if v["total"] else 0}
            for v in dados.values()
        ]).sort_values("Pct", ascending=True)

        fig_bar = go.Figure()
        fig_bar.add_vrect(x0=0,   x1=10,  fillcolor="rgba(5,150,105,0.06)",  layer="below", line_width=0)
        fig_bar.add_vrect(x0=10,  x1=15,  fillcolor="rgba(217,119,6,0.06)",  layer="below", line_width=0)
        fig_bar.add_vrect(x0=15,  x1=100, fillcolor="rgba(220,38,38,0.06)",  layer="below", line_width=0)
        for xv, lbl in [(10,"10%"),(15,"15%")]:
            fig_bar.add_vline(x=xv, line_dash="dot", line_color="#b9d7e8", line_width=1.5,
                annotation_text=lbl, annotation_position="top",
                annotation_font=dict(color="#6b8496", size=10))
        fig_bar.add_trace(go.Bar(
            y=df_bar["Cliente"], x=df_bar["Pct"], orientation="h",
            marker=dict(color=[cor_hex(p) for p in df_bar["Pct"]], line=dict(width=0)),
            text=[f"{p:.1f}% ({o}/{t})" for p,o,t in zip(df_bar["Pct"],df_bar["Offline"],df_bar["Total"])],
            textposition="outside", textfont=dict(color="#6b8496",size=10,family="DM Mono"),
            hovertemplate="<b>%{y}</b><br>%{x:.1f}% offline<extra></extra>",
        ))
        fig_bar.update_layout(
            **pdefaults(), height=max(360, len(df_bar)*34), showlegend=False,
            xaxis=dict(range=[0,100], ticksuffix="%", gridcolor="#dbe8f2",
                       tickfont=dict(color="#6b8496",size=10), zeroline=False),
            yaxis=dict(tickfont=dict(color="#4f6f85",size=10), gridcolor="#f5f8fb"),
            margin=dict(l=10, r=80, t=30, b=10),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ════════════════════════════════════════════
    # ABA 4 — RANKING DE CRITICIDADE
    # ════════════════════════════════════════════
    with tabs[4]:
        st.markdown("#### Ranking de criticidade")
        st.caption("Online (verde) + Offline (vermelho) · Ordenado por % offline")

        df_rank = pd.DataFrame([
            {"Cliente": v["nome_cliente"], "Franqueado": v["nome_empresa"],
             "Offline": len(v["offline"]), "Total": v["total"],
             "% Offline": round(len(v["offline"])/v["total"]*100,2) if v["total"] else 0,
             "Online": v["total"]-len(v["offline"])}
            for v in dados.values() if len(v["offline"]) > 0
        ]).sort_values("% Offline", ascending=False).reset_index(drop=True)
        df_rank.index += 1

        if df_rank.empty:
            st.success("🎉 Nenhum cliente com câmeras offline no momento!")
        else:
            fig_rank = go.Figure()
            fig_rank.add_trace(go.Bar(
                name="Online", y=df_rank["Cliente"], x=df_rank["Online"],
                orientation="h", marker_color="#14b8a6",
                hovertemplate="%{y}<br>Online: %{x}<extra></extra>",
            ))
            fig_rank.add_trace(go.Bar(
                name="Offline", y=df_rank["Cliente"], x=df_rank["Offline"],
                orientation="h", marker_color="#ef4444",
                text=[f'{p:.1f}%' for p in df_rank["% Offline"]],
                textposition="outside", textfont=dict(color="#6b8496",size=10,family="DM Mono"),
                hovertemplate="%{y}<br>Offline: %{x} (%{text})<extra></extra>",
            ))
            fig_rank.update_layout(
                **pdefaults(), barmode="stack",
                height=max(360, len(df_rank)*40),
                xaxis=dict(title="Quantidade de câmeras", gridcolor="#dbe8f2",
                           tickfont=dict(color="#6b8496",size=10), zeroline=False),
                yaxis=dict(tickfont=dict(color="#4f6f85",size=10),
                           categoryorder="array",
                           categoryarray=df_rank["Cliente"].tolist()[::-1]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            font=dict(color="#6b8496",size=11), bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=10, r=80, t=50, b=10),
            )
            st.plotly_chart(fig_rank, use_container_width=True)

            st.markdown("---")
            col_tbl, col_dl = st.columns([5,1])
            col_tbl.markdown("**Tabela resumo**")
            buf_r = io.BytesIO()
            df_rank.to_excel(buf_r, index=True, engine="openpyxl")
            col_dl.download_button("⬇ Excel", data=buf_r.getvalue(),
                file_name=f"ranking_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            df_show = df_rank[["Cliente","Franqueado","Offline","Total","% Offline"]].copy()
            df_show["% Offline"] = df_show["% Offline"].apply(lambda x: f"{x:.1f}%")
            render_dataframe(df_show, height=min(400,(len(df_show)+1)*35+3))

            st.markdown("---")
            st.markdown("**Ranking de recorrência nos últimos 30 dias**")
            df_rec = df_clientes_ops[df_clientes_ops["Dias Offline"] > 0].copy()
            if df_rec.empty:
                st.info("Ainda não há histórico suficiente para recorrência.")
            else:
                df_rec = df_rec.sort_values(["Dias Críticos", "Dias Offline", "% Offline"], ascending=False)
                df_rec_show = df_rec[["Cliente","Franqueado","Dias Offline","Dias Críticos","Offline","% Offline","Maior Tempo"]].head(20).copy()
                df_rec_show["% Offline"] = df_rec_show["% Offline"].apply(lambda x: f"{x:.1f}%")
                render_dataframe(df_rec_show, height=min(520,(len(df_rec_show)+1)*35+3))

    # ════════════════════════════════════════════
    # ABA 5 — HISTÓRICO & COMPARATIVO
    # ════════════════════════════════════════════
    with tabs[5]:
        st.markdown("#### Histórico de snapshots")
        df_snaps = listar_snapshots()

        if df_snaps.empty:
            st.info("Nenhum snapshot gravado ainda. Use o painel lateral para salvar o estado atual.")
        else:
            df_snaps["gravado_dt"] = pd.to_datetime(df_snaps["gravado_em"])
            data_min = df_snaps["gravado_dt"].min().date()
            data_max = df_snaps["gravado_dt"].max().date()

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                data_inicio = st.date_input("📅 Data inicial", value=data_min,
                                            min_value=data_min, max_value=data_max,
                                            format="DD/MM/YYYY", key="hist_data_ini")
            with col_d2:
                data_fim = st.date_input("📅 Data final", value=data_max,
                                         min_value=data_min, max_value=data_max,
                                         format="DD/MM/YYYY", key="hist_data_fim")

            df_snaps_filtrado = df_snaps[
                (df_snaps["gravado_dt"].dt.date >= data_inicio) &
                (df_snaps["gravado_dt"].dt.date <= data_fim)
            ]

            if df_snaps_filtrado.empty:
                st.warning("Nenhum snapshot encontrado no período selecionado.")
            else:
                opcoes = {f"{r['label']}  ({r['gravado_em']})": {"id": r["id"], "gravado_em": r["gravado_em"]}
                          for _, r in df_snaps_filtrado.iterrows()}

                col_a, col_b, col_dl_h = st.columns([2,2,1])
                with col_a:
                    sel_a = st.selectbox("📅 Snapshot A (base)", list(opcoes.keys()),
                                         index=min(1,len(opcoes)-1))
                with col_b:
                    sel_b = st.selectbox("📅 Snapshot B (recente)", list(opcoes.keys()), index=0)

                id_a = opcoes[sel_a]["id"]
                id_b = opcoes[sel_b]["id"]

                def fmt_dt(s):
                    try: return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                    except: return s

                leg_a = fmt_dt(opcoes[sel_a]["gravado_em"])
                leg_b = fmt_dt(opcoes[sel_b]["gravado_em"])

                df_a = carregar_snapshot(id_a).rename(columns={"offline":"off_a","total":"tot_a","pct_offline":"pct_a","nome_cliente":"nc_a"})
                df_b = carregar_snapshot(id_b).rename(columns={"offline":"off_b","total":"tot_b","pct_offline":"pct_b","nome_cliente":"nc_b"})
                df_comp = pd.merge(df_a, df_b, on="wl_id", how="outer").fillna(0)
                # Usar nome do snapshot B como display
                df_comp["cliente"] = df_comp["nc_b"].where(df_comp["nc_b"] != 0, df_comp["nc_a"])
                df_comp["delta_pct"] = df_comp["pct_b"] - df_comp["pct_a"]
                df_comp["delta_off"] = df_comp["off_b"] - df_comp["off_a"]
                df_comp = df_comp.sort_values("pct_b", ascending=False)

                melhoraram = (df_comp["delta_pct"] < -0.5).sum()
                pioraram   = (df_comp["delta_pct"] >  0.5).sum()
                estaveis   = len(df_comp) - melhoraram - pioraram

                with col_dl_h:
                    st.markdown("<br>", unsafe_allow_html=True)
                    buf_h = io.BytesIO()
                    df_comp.to_excel(buf_h, index=False, engine="openpyxl")
                    st.download_button("⬇ Comparativo", data=buf_h.getvalue(),
                        file_name=f"comparativo_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True)

                st.markdown(f"""
                <div style="display:flex;gap:10px;margin:1rem 0">
                    <div style="background:#ecfdf5;border:1px solid #99f6e4;border-radius:8px;padding:12px 20px;flex:1;text-align:center">
                        <div style="font-size:10px;color:#6b8496;font-weight:600;letter-spacing:.7px;text-transform:uppercase">Melhoraram</div>
                        <div style="font-size:28px;font-weight:700;color:#14b8a6;font-family:'DM Mono',monospace">{melhoraram}</div>
                    </div>
                    <div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:8px;padding:12px 20px;flex:1;text-align:center">
                        <div style="font-size:10px;color:#6b8496;font-weight:600;letter-spacing:.7px;text-transform:uppercase">Pioraram</div>
                        <div style="font-size:28px;font-weight:700;color:#ef4444;font-family:'DM Mono',monospace">{pioraram}</div>
                    </div>
                    <div style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:12px 20px;flex:1;text-align:center">
                        <div style="font-size:10px;color:#6b8496;font-weight:600;letter-spacing:.7px;text-transform:uppercase">Estáveis</div>
                        <div style="font-size:28px;font-weight:700;color:#6b8496;font-family:'DM Mono',monospace">{estaveis}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("**Comparativo % offline por cliente**")
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Bar(
                    name=leg_a, y=df_comp["cliente"], x=df_comp["pct_a"],
                    orientation="h", marker_color="#0088cc", opacity=0.75,
                    hovertemplate="%{y}<br>%{x:.1f}%<extra>A</extra>",
                ))
                fig_comp.add_trace(go.Bar(
                    name=leg_b, y=df_comp["cliente"], x=df_comp["pct_b"],
                    orientation="h", marker_color="#00bcd4",
                    hovertemplate="%{y}<br>%{x:.1f}%<extra>B</extra>",
                ))
                fig_comp.update_layout(
                    **pdefaults(), barmode="group",
                    height=max(400, len(df_comp)*44),
                    xaxis=dict(range=[0,100], ticksuffix="%", gridcolor="#dbe8f2",
                               tickfont=dict(color="#6b8496",size=10), zeroline=False),
                    yaxis=dict(tickfont=dict(color="#4f6f85",size=10)),
                    legend=dict(font=dict(size=11,color="#6b8496"), bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig_comp, use_container_width=True)

                st.markdown("**Variação (B − A) em número de câmeras offline**")
                st.caption("🟢 Reduziu câmeras offline · 🔴 Aumentou câmeras offline")
                df_delta = df_comp.sort_values("delta_off", ascending=True)
                cores_d  = ["#ef4444" if d > 0 else ("#14b8a6" if d < 0 else "#b9d7e8") for d in df_delta["delta_off"]]
                fig_d = go.Figure(go.Bar(
                    y=df_delta["cliente"], x=df_delta["delta_off"], orientation="h",
                    marker=dict(color=cores_d, line=dict(width=0)),
                    text=[f"{'+' if d>0 else ''}{int(d)} câm." for d in df_delta["delta_off"]],
                    textposition="outside", textfont=dict(color="#6b8496",size=10,family="DM Mono"),
                    hovertemplate="%{y}<br>Δ %{x:+d} câmeras<extra></extra>",
                ))
                fig_d.add_vline(x=0, line_color="#b9d7e8", line_width=1)
                fig_d.update_layout(
                    **pdefaults(), height=max(400, len(df_delta)*34), showlegend=False,
                    xaxis=dict(gridcolor="#dbe8f2", tickfont=dict(color="#6b8496",size=10), zeroline=False),
                    yaxis=dict(tickfont=dict(color="#4f6f85",size=10)),
                    margin=dict(l=10, r=80, t=20, b=10),
                )
                st.plotly_chart(fig_d, use_container_width=True)

                st.markdown("---")
                st.markdown("**Tabela comparativa detalhada**")
                df_tbl = df_comp[["cliente","tot_a","off_a","pct_a","tot_b","off_b","pct_b","delta_pct","delta_off"]].copy()
                df_tbl.columns = ["Cliente","Total A","Off A","% A","Total B","Off B","% B","Δ% (pp)","Δ Off"]
                df_tbl["% A"]     = df_tbl["% A"].apply(lambda x: f"{x:.1f}%")
                df_tbl["% B"]     = df_tbl["% B"].apply(lambda x: f"{x:.1f}%")
                df_tbl["Δ% (pp)"] = df_tbl["Δ% (pp)"].apply(lambda x: f"{'+' if x>0 else ''}{x:.1f}")
                df_tbl["Δ Off"]   = df_tbl["Δ Off"].apply(lambda x: f"{'+' if x>0 else ''}{int(x)}")
                df_tbl = df_tbl.reset_index(drop=True); df_tbl.index += 1
                render_dataframe(df_tbl, height=min(500,(len(df_tbl)+1)*35+3))

                row_b = df_snaps_filtrado[df_snaps_filtrado["id"] == id_b].iloc[0]
                if str(row_b.get("notas","")).strip():
                    st.markdown("---")
                    st.markdown(f"📝 **Observações do snapshot B:** {row_b['notas']}")

            st.markdown("---")
            with st.expander("🗑️  Gerenciar snapshots gravados"):
                for _, row in df_snaps.iterrows():
                    c1, c2 = st.columns([5,1])
                    notas_txt = f" · *{str(row['notas'])[:60]}…*" if str(row.get("notas","")).strip() else ""
                    c1.markdown(f"**{row['label']}** · `{row['gravado_em']}`{notas_txt}")
                    if c2.button("Excluir", key=f"del_{row['id']}"):
                        deletar_snapshot(row["id"]); st.rerun()


if __name__ == "__main__":
    main()