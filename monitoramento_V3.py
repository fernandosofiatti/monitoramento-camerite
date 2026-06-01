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
import uuid

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


/* ── Ajustes finais solicitados ── */
.sidebar-stat-card {
    background:#ffffff !important;
    border:1px solid #dbe8f2 !important;
    border-radius:8px !important;
    padding:12px 14px !important;
    box-shadow:0 6px 18px rgba(16,42,63,.04) !important;
}
.sidebar-stat-card.offline-card {
    background:#ffffff !important;
    border-color:#dbe8f2 !important;
}
.sidebar-stat-card .stat-label {
    font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px;
}
.sidebar-stat-card .stat-value {
    font-size:24px;font-weight:700;color:#0088cc;font-family:'DM Mono',monospace;
}
.sidebar-stat-card.offline-card .stat-value {
    color:#dc2626 !important;
    -webkit-text-fill-color:#dc2626 !important;
}
.sidebar-stat-card .stat-note { font-size:11px;color:#6b8496; }

.compare-hero {
    background:linear-gradient(135deg,#ffffff 0%,#f6fbff 100%);
    border:1px solid #dbe8f2;border-radius:14px;padding:18px 20px;margin:10px 0 16px;
    box-shadow:0 12px 30px rgba(16,42,63,.07);
}
.compare-title { font-size:24px;font-weight:800;color:#102a3f;letter-spacing:-.4px; }
.compare-sub { font-size:13px;color:#4f6f85;margin-top:4px;line-height:1.45; }
.compare-pill {
    display:inline-flex;align-items:center;gap:6px;margin-top:10px;
    font-family:'DM Mono',monospace;font-size:11px;color:#006da3;background:#e8f7fc;
    border:1px solid #b9e7f4;border-radius:999px;padding:6px 10px;
}
.compare-grid { display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:12px 0 18px; }
.compare-card {
    background:#ffffff !important;border:1px solid #dbe8f2;border-radius:12px;padding:15px 16px;
    box-shadow:0 10px 24px rgba(16,42,63,.055);position:relative;overflow:hidden;
}
.compare-card:before { content:'';position:absolute;left:0;right:0;top:0;height:4px;background:#0088cc; }
.compare-card.good:before { background:linear-gradient(90deg,#22c55e,#059669); }
.compare-card.bad:before { background:linear-gradient(90deg,#ff1744,#dc2626); }
.compare-card.warn:before { background:linear-gradient(90deg,#facc15,#f59e0b); }
.compare-card.neutral:before { background:linear-gradient(90deg,#0088cc,#00bcd4); }
.compare-label { font-size:10px;color:#6b8496;font-weight:800;text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px; }
.compare-value { font-family:'DM Mono',monospace;font-size:30px;font-weight:800;color:#102a3f;line-height:1; }
.compare-note { font-size:11px;color:#60798d;margin-top:8px;line-height:1.35; }
.compare-status-box {
    margin-top:12px;padding:12px 14px;border-radius:10px;background:#ffffff;border:1px solid #dbe8f2;
    display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
}
.compare-status-text { font-size:13px;color:#4f6f85; }
.compare-status-tag { font-family:'DM Mono',monospace;font-size:11px;font-weight:800;border-radius:999px;padding:6px 10px;border:1px solid currentColor; }
@media(max-width:1100px){ .compare-grid{grid-template-columns:repeat(2,minmax(0,1fr));} }
@media(max-width:700px){ .compare-grid{grid-template-columns:1fr;} }

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
# Caminhos preparados para publicação no Streamlit Cloud/GitHub.
# Por padrão, o app usa a própria pasta do arquivo monitoramento_V3.py.
# Se precisar rodar localmente em outra pasta, ainda é possível usar a variável
# de ambiente CAMERITE_MONITORAMENTO_PASTA.
BASE_DIR                  = os.path.dirname(os.path.abspath(__file__))
PASTA                     = os.getenv("CAMERITE_MONITORAMENTO_PASTA", BASE_DIR)

CSV_GOV                   = os.path.join(PASTA, "GOV_extracao_cameras.csv")
XLSX_CLIENTES             = os.path.join(PASTA, "nome_clientes.xlsx")
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


# ─────────────────────────────────────────────
# HELPERS DE COR
# ─────────────────────────────────────────────
def cor_hex(pct: float) -> str:
    if pct <= 5:     return "#14b8a6"
    elif pct <= 10: return "#f59e0b"
    else:           return "#ef4444"

def classe_card(pct: float):
    if pct <= 5:     return ("card-ok",    "count-ok",    "label-ok")
    elif pct <= 10: return ("card-yellow","count-yellow","label-yellow")
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

def faixa_tempo_dias(horas: float) -> str:
    if horas < 0:   return "Sem data"
    if horas < 24:  return "Menos de 1 dia"
    if horas < 72:  return "Entre 1 e 3 dias"
    if horas < 168: return "3 a 7 dias"
    return "Acima de 7 dias"

def status_cliente(pct: float, offline: int) -> str:
    if offline == 0: return "Sem offline"
    if pct > 10:    return "Crítico (>10%)"
    if pct > 5:     return "Atenção (5-10%)"
    return "Saudável (0-5%)"


def escape_html(valor) -> str:
    return html.escape(str(valor or ""), quote=True)


def classificar_auditoria(pct_global: float, n_critico: int, n_atencao: int, saude: dict) -> tuple[str, str, str]:
    if saude.get("colunas_faltando"):
        return "Bloqueado", "#dc2626", "Colunas obrigatórias ausentes"
    if saude.get("datas_futuras", 0):
        return "Revisar fonte", "#d97706", "Há datas futuras no arquivo"
    if saude.get("datas_invalidas", 0):
        return "Revisar fonte", "#d97706", "Há datas inválidas no arquivo"
    if pct_global > 10 or n_critico > 0:
        return "Cobrar Clientes Críticos", "#dc2626", "Clientes acima do limite crítico"
    if pct_global > 5 or n_atencao > 0:
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
# HELPERS SUPABASE / BD ONLINE
# ─────────────────────────────────────────────
def get_secret_value(nome: str, default: str = "") -> str:
    """Lê configuração por variável de ambiente ou Streamlit Secrets."""
    valor = os.getenv(nome, default)
    if valor:
        return str(valor).strip()
    try:
        return str(st.secrets.get(nome, default)).strip()
    except Exception:
        return default


def supabase_configurado() -> bool:
    return bool(get_secret_value("SUPABASE_URL") and get_supabase_key())


def get_supabase_key() -> str:
    """Aceita SUPABASE_KEY, SUPABASE_ANON_KEY ou SUPABASE_PUBLISHABLE_KEY."""
    return (
        get_secret_value("SUPABASE_KEY")
        or get_secret_value("SUPABASE_ANON_KEY")
        or get_secret_value("SUPABASE_PUBLISHABLE_KEY")
    )


def supabase_headers(prefer: str | None = None) -> dict:
    key = get_supabase_key()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def supabase_table_url(tabela: str | None = None) -> str:
    tabela = tabela or SUPABASE_TABLE
    return get_secret_value("SUPABASE_URL").rstrip("/") + f"/rest/v1/{tabela}"


def supabase_base_url() -> str:
    return supabase_table_url(SUPABASE_TABLE)


def preparar_df_para_supabase(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza o CSV para a tabela cameras_origem criada no Supabase."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    colunas_padrao = [COL_WL, COL_EMPRESA, COL_ID_CAM, COL_NOME_CAM, COL_STATUS, COL_ULT_ATU, COL_OBS]
    for col in colunas_padrao:
        if col not in df.columns:
            df[col] = ""

    city_col = encontrar_coluna_por_chaves(df, ("cidade", "municipio", "city", "prefeitura"), default="Cidade")
    estado_col = encontrar_coluna_por_chaves(df, ("estado", "uf", "state"), default="Estado")
    if city_col not in df.columns:
        df[city_col] = ""
    if estado_col not in df.columns:
        df[estado_col] = ""

    out = pd.DataFrame()
    out["id_camera"] = pd.to_numeric(df[COL_ID_CAM].astype(str).str.strip(), errors="coerce")
    out = out[out["id_camera"].notna()].copy()
    out["id_camera"] = out["id_camera"].astype("int64")

    # Reindexa o df original para manter apenas as linhas válidas de id_camera.
    df_valid = df.loc[out.index].copy()

    out["id_whitelabel"] = df_valid[COL_WL].astype(str).str.strip()
    out["nome_empresa"] = df_valid[COL_EMPRESA].astype(str).replace({"nan": ""}).str.strip()
    out["nome_camera"] = df_valid[COL_NOME_CAM].astype(str).replace({"nan": ""}).str.strip()
    out["status_camera"] = df_valid[COL_STATUS].astype(str).str.strip().str.upper()
    out["ultima_atualizacao"] = parse_ultima_atualizacao(df_valid[COL_ULT_ATU]).dt.strftime("%Y-%m-%d %H:%M:%S")
    out["ultima_atualizacao"] = out["ultima_atualizacao"].where(out["ultima_atualizacao"].notna(), None)
    out["observacoes"] = df_valid[COL_OBS].astype(str).replace({"nan": ""}).str.strip()
    out["cidade"] = df_valid[city_col].astype(str).replace({"nan": ""}).str.strip()
    out["estado"] = df_valid[estado_col].astype(str).replace({"nan": ""}).str.strip()
    out["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out = out[(out["id_whitelabel"] != "") & (out["status_camera"] != "")].copy()
    out = out.drop_duplicates(subset=["id_camera"], keep="last")
    return out


def limpar_valor_json(valor):
    """Converte valores que JSON/Supabase não aceitam, como NaN/NaT/pd.NA, para None."""
    try:
        if pd.isna(valor):
            return None
    except Exception:
        pass

    if isinstance(valor, float):
        try:
            if math.isnan(valor) or math.isinf(valor):
                return None
        except Exception:
            pass

    if isinstance(valor, (pd.Timestamp, datetime)):
        if pd.isna(valor):
            return None
        return valor.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(valor, str):
        texto = valor.strip()
        if texto.lower() in ("nan", "nat", "none", "null", "<na>"):
            return None
        return texto

    return valor


def df_para_registros_json(df: pd.DataFrame) -> list[dict]:
    """Gera registros 100% compatíveis com JSON, removendo NaN antes do request."""
    df_limpo = df.astype(object).where(pd.notna(df), None)
    registros = []
    for row in df_limpo.to_dict(orient="records"):
        registros.append({k: limpar_valor_json(v) for k, v in row.items()})
    return registros

def converter_supabase_para_df_gov(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = pd.DataFrame()
    out[COL_WL] = df.get("id_whitelabel", "").astype(str)
    out[COL_EMPRESA] = df.get("nome_empresa", "").astype(str)
    out[COL_ID_CAM] = df.get("id_camera", "").astype(str)
    out[COL_NOME_CAM] = df.get("nome_camera", "").astype(str)
    out[COL_STATUS] = df.get("status_camera", "").astype(str)
    out[COL_ULT_ATU] = df.get("ultima_atualizacao", "").astype(str)
    out[COL_OBS] = df.get("observacoes", "").astype(str)
    out["Cidade"] = df.get("cidade", "").astype(str)
    out["UF"] = df.get("estado", "").astype(str)
    return out


@st.cache_data(ttl=60)
def carregar_cameras_supabase() -> tuple[pd.DataFrame | None, str]:
    if not supabase_configurado():
        return None, "Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY nos Secrets."

    todos = []
    offset = 0
    try:
        while True:
            headers = supabase_headers()
            headers["Range"] = f"{offset}-{offset + SUPABASE_PAGE_SIZE - 1}"
            resp = requests.get(
                supabase_base_url(),
                headers=headers,
                params={"select": "*", "order": "id_whitelabel.asc,id_camera.asc"},
                timeout=30,
            )
            if resp.status_code not in (200, 206):
                return None, f"Erro ao consultar Supabase: {resp.status_code} - {resp.text[:300]}"
            lote = resp.json()
            if not lote:
                break
            todos.extend(lote)
            if len(lote) < SUPABASE_PAGE_SIZE:
                break
            offset += SUPABASE_PAGE_SIZE
    except Exception as e:
        return None, f"Erro ao conectar no Supabase: {e}"

    return pd.DataFrame(todos), ""


def registrar_historico_importacao(df_envio: pd.DataFrame, arquivo_nome: str = "upload_streamlit") -> None:
    """Registra um resumo da importação. Se falhar, não bloqueia a atualização principal."""
    try:
        qtd_registros = int(len(df_envio))
        status = df_envio.get("status_camera", pd.Series(dtype=str)).astype(str).str.upper()
        payload = {
            "arquivo_nome": arquivo_nome,
            "qtd_registros": qtd_registros,
            "qtd_online": int((status == "ONLINE").sum()),
            "qtd_offline": int((status == "OFFLINE").sum()),
            "observacao": "Importação realizada pelo Streamlit",
        }
        requests.post(
            supabase_table_url("historico_importacoes"),
            headers=supabase_headers("return=minimal"),
            json=payload,
            timeout=20,
        )
    except Exception:
        pass


def enviar_df_supabase(df_csv: pd.DataFrame, progress_callback=None) -> tuple[bool, str, int]:
    if not supabase_configurado():
        return False, "Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY nos Secrets.", 0

    df_envio = preparar_df_para_supabase(df_csv)
    if df_envio.empty:
        return False, "Nenhuma linha válida para importar. Verifique ID_Whitelabel e ID_da_Camera.", 0

    registros = df_para_registros_json(df_envio)
    total = 0
    qtd_total = len(registros)
    try:
        for i in range(0, qtd_total, 500):
            lote = registros[i:i + 500]
            if progress_callback:
                progress_callback(total, qtd_total, "Enviando dados para o Supabase...")
            resp = requests.post(
                supabase_base_url(),
                headers=supabase_headers("resolution=merge-duplicates"),
                params={"on_conflict": "id_camera"},
                json=lote,
                timeout=60,
            )
            if resp.status_code not in (200, 201, 204):
                return False, f"Erro ao importar para o Supabase: {resp.status_code} - {resp.text[:500]}", total
            total += len(lote)
            if progress_callback:
                progress_callback(total, qtd_total, f"Atualizando base online... {total}/{qtd_total} registros enviados")
    except Exception as e:
        return False, f"Erro ao enviar dados ao Supabase: {e}", total

    if progress_callback:
        progress_callback(total, qtd_total, "Registrando histórico da importação...")
    registrar_historico_importacao(df_envio)

    carregar_cameras_supabase.clear()
    carregar_dados.clear()
    calcular_saude_dados.clear()
    if progress_callback:
        progress_callback(total, qtd_total, "Importação finalizada.")
    return True, "Base online atualizada com sucesso.", total


def sql_criacao_supabase() -> str:
    return f"""
create table if not exists public.{SUPABASE_TABLE} (
    id_camera bigint primary key,
    id_whitelabel text,
    nome_empresa text,
    nome_camera text,
    status_camera text,
    ultima_atualizacao timestamp,
    observacoes text,
    cidade text,
    estado text,
    created_at timestamp default now(),
    updated_at timestamp default now()
);

create table if not exists public.historico_importacoes (
    id bigint generated by default as identity primary key,
    data_importacao timestamp default now(),
    arquivo_nome text,
    qtd_registros integer default 0,
    qtd_online integer default 0,
    qtd_offline integer default 0,
    qtd_novas integer default 0,
    qtd_atualizadas integer default 0,
    observacao text
);

create index if not exists idx_cameras_origem_whitelabel
    on public.{SUPABASE_TABLE} (id_whitelabel);

create index if not exists idx_cameras_origem_status
    on public.{SUPABASE_TABLE} (status_camera);

create index if not exists idx_cameras_origem_ultima_atualizacao
    on public.{SUPABASE_TABLE} (ultima_atualizacao);
""".strip()

def render_aba_atualizar_base(df_origem: pd.DataFrame | None = None):
    st.markdown("### Atualizar base online")
    st.caption("Importe o CSV novo para o Supabase. A importação atualiza câmeras existentes e insere câmeras novas, sem duplicar pelo ID_da_Camera.")

    if supabase_configurado():
        st.success(f"Supabase configurado · tabela `{SUPABASE_TABLE}`")
    else:
        st.warning("Supabase ainda não configurado nos Secrets do Streamlit Cloud.")
        with st.expander("SQL para criar a tabela no Supabase", expanded=True):
            st.code(sql_criacao_supabase(), language="sql")
        st.info("Depois de criar a tabela, configure SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit Cloud.")

    arq = st.file_uploader("CSV de câmeras", type=["csv"], key="csv_supabase_upload")
    if arq is not None:
        df_csv = None
        for enc in ("utf-8", "latin-1", "cp1252"):
            for sep in (",", ";", "\t"):
                try:
                    arq.seek(0)
                    tmp = pd.read_csv(arq, encoding=enc, sep=sep, on_bad_lines="skip", engine="python", quoting=0)
                    tmp.columns = [str(c).strip() for c in tmp.columns]
                    if {COL_STATUS, COL_WL}.issubset(tmp.columns):
                        df_csv = tmp
                        break
                    if df_csv is None and len(tmp.columns) > 2:
                        df_csv = tmp
                except UnicodeDecodeError:
                    break
                except Exception:
                    continue
            if df_csv is not None and {COL_STATUS, COL_WL}.issubset(df_csv.columns):
                break

        if df_csv is None:
            st.error("Não consegui ler o CSV. Tente salvar como CSV UTF-8.")
            return

        faltando = [c for c in [COL_STATUS, COL_WL] if c not in df_csv.columns]
        if faltando:
            st.error(f"Colunas obrigatórias ausentes: {', '.join(faltando)}")
            st.caption(f"Colunas encontradas: {', '.join(df_csv.columns.astype(str))}")
            return

        clientes_map = carregar_clientes()
        df_csv_filtrado = df_csv.copy()
        total_csv_bruto = len(df_csv)
        total_csv_filtro = total_csv_bruto

        if clientes_map and COL_WL in df_csv_filtrado.columns:
            ids_validos = set(str(k).strip() for k in clientes_map.keys())
            df_csv_filtrado = df_csv_filtrado[
                df_csv_filtrado[COL_WL].astype(str).str.strip().isin(ids_validos)
            ].copy()
            total_csv_filtro = len(df_csv_filtrado)

        df_preview = preparar_df_para_supabase(df_csv_filtrado)
        offline_filtro = int((df_preview["status_camera"] == "OFFLINE").sum()) if not df_preview.empty else 0
        online_filtro = int((df_preview["status_camera"] == "ONLINE").sum()) if not df_preview.empty else 0
        ignorados_filtro = total_csv_bruto - total_csv_filtro

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Linhas no CSV", total_csv_bruto)
        col2.metric("Linhas no filtro", total_csv_filtro)
        col3.metric("Válidas para importar", len(df_preview))
        col4.metric("Offline no filtro", offline_filtro)

        st.caption(
            f"Filtro aplicado pela lista de clientes do painel (`nome_clientes.xlsx`). "
            f"Ignorados fora do filtro: {ignorados_filtro}. Online no filtro: {online_filtro}."
        )

        st.markdown("#### Prévia da importação filtrada")
        render_dataframe(df_preview.head(100), height=320)

        if st.button("🚀 Atualizar base online", type="primary", use_container_width=True):
            status_box = st.empty()
            progress_bar = st.progress(0)

            def atualizar_progresso(enviados: int, total_registros: int, mensagem: str):
                pct = 1.0 if total_registros <= 0 else min(max(enviados / total_registros, 0), 1)
                progress_bar.progress(pct)
                status_box.info(f"⏳ {mensagem}")

            atualizar_progresso(0, len(df_preview), "Atualizando base online. Não feche esta página.")
            ok, msg, total = enviar_df_supabase(df_csv_filtrado, progress_callback=atualizar_progresso)
            if ok:
                progress_bar.progress(1.0)
                status_box.success(f"✅ Importação finalizada: {total} registros enviados/atualizados no Supabase.")
                st.success(f"{msg} {total} registros enviados/atualizados. Offline no filtro: {offline_filtro}.")
                st.cache_data.clear()
                st.info("A base foi atualizada. Use o botão 🔄 Atualizar dados no menu lateral para recarregar o painel quando quiser.")
            else:
                status_box.error("❌ A importação não foi concluída.")
                st.error(msg)

    st.markdown("---")
    st.markdown("#### Status da base online")
    if supabase_configurado():
        df_online, erro_online = carregar_cameras_supabase()
        if erro_online:
            st.error(erro_online)
        elif df_online is not None:
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Registros no BD", len(df_online))
            col_b.metric("Clientes", df_online["id_whitelabel"].nunique() if "id_whitelabel" in df_online.columns else 0)
            col_c.metric("Offline", int((df_online.get("status_camera", pd.Series(dtype=str)).astype(str).str.upper() == "OFFLINE").sum()))
            render_dataframe(converter_supabase_para_df_gov(df_online).head(200), height=360)

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
        col_state = next((c for c in df.columns if any(k in c.lower() for k in ("estado", "uf", "state"))), None)
        if col_city is None:
            col_city = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        if col_state and col_state != col_city:
            valores = df[col_city].astype(str).str.strip() + " - " + df[col_state].astype(str).str.strip()
        else:
            valores = df[col_city].astype(str).str.strip()
        return dict(zip(df[col_id].astype(str).str.strip(), valores))
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

    def valor_texto(v):
        if pd.isna(v):
            return ""
        return str(v).strip()

    cidade_valores = []
    estado_valores = []

    for _, row in df.iterrows():
        wl_id = valor_texto(row.get(COL_WL, ""))
        cidade = valor_texto(row.get(city_col, ""))
        estado = valor_texto(row.get(state_col, "")) if state_col else ""

        if wl_id in clientes_prefeitura:
            cidade_extra, estado_extra = parse_prefeitura_localidade(clientes_prefeitura[wl_id])
            if not cidade or cidade.lower() == "nan":
                cidade = cidade_extra or cidade
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

    city_col = encontrar_coluna_por_chaves(df, ("cidade", "municipio", "city", "prefeitura"), default=None)
    state_col = encontrar_coluna_por_chaves(df, ("estado", "uf", "state"), default=None)

    # Parsear data da última atualização
    agora = datetime.now()
    if COL_ULT_ATU in df.columns:
        df[COL_ULT_ATU] = parse_ultima_atualizacao(df[COL_ULT_ATU])
        df["_tempo_off"] = df[COL_ULT_ATU].apply(
            lambda x: max(agora - x, timedelta(seconds=0)) if pd.notna(x) else timedelta(seconds=-1)
        )
    else:
        df["_tempo_off"] = pd.Series([timedelta(seconds=-1)] * len(df), index=df.index)

    resultado = {}
    for wl_id, grupo in df.groupby(df[COL_WL].astype(str).str.strip()):
        nome_cliente = clientes_map.get(wl_id, f"ID {wl_id}")
        nome_empresa = grupo[COL_EMPRESA].iloc[0] if COL_EMPRESA in grupo.columns else ""
        cidade = grupo[city_col].iloc[0] if city_col in grupo.columns else ""
        estado = grupo[state_col].iloc[0] if state_col in grupo.columns else ""
        cidade_estado = ""
        if cidade and estado:
            cidade_estado = f"{cidade} - {estado}"
        elif cidade:
            cidade_estado = str(cidade)
        elif estado:
            cidade_estado = str(estado)
        df_off = grupo[grupo[COL_STATUS].astype(str).str.strip().str.upper() == "OFFLINE"].copy()
        if "_tempo_off" in df_off.columns:
            df_off = df_off.sort_values("_tempo_off", ascending=False)
        resultado[wl_id] = {
            "nome_cliente": nome_cliente,
            "nome_empresa": nome_empresa,
            "cidade": cidade,
            "uf": estado,
            "cidade_estado": cidade_estado,
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

    # Normalizar colunas de XLSX individuais para a estrutura esperada
    status_col = encontrar_coluna_por_chaves(df_map, ("status", "status_da_camera", "situacao"), default=None)
    wl_col = encontrar_coluna_por_chaves(df_map, ("whitelabel", "idwhitelabel", "wl", "id_cliente", "idcliente"), default=None)
    empresa_col = encontrar_coluna_por_chaves(df_map, ("empresa", "company", "usuario", "user", "franqueado"), default=None)

    rename_map = {}
    if status_col and status_col != COL_STATUS:
        rename_map[status_col] = COL_STATUS
    if wl_col and wl_col != COL_WL:
        rename_map[wl_col] = COL_WL
    if empresa_col and empresa_col != COL_EMPRESA:
        rename_map[empresa_col] = COL_EMPRESA
    if rename_map:
        df_map = df_map.rename(columns=rename_map)

    if COL_WL in df_map.columns:
        df_map[COL_WL] = df_map[COL_WL].astype(str).str.strip()

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
    # Usar nome_clientes.xlsx como lista mestre — incluir apenas esses clientes no mapa
    try:
        clientes_prefeitura = carregar_clientes_prefeitura()
        clientes_map = carregar_clientes()
    except Exception:
        clientes_prefeitura = {}
        clientes_map = {}

    if clientes_prefeitura:
        master_rows = []
        for wl_id, loc in clientes_prefeitura.items():
            wl_id_str = str(wl_id).strip()
            cidade_extra, estado_extra = parse_prefeitura_localidade(loc)
            master_rows.append({
                COL_WL: wl_id_str,
                "city": cidade_extra or "",
                "uf": estado_extra or "",
                "nome_cliente": clientes_map.get(wl_id_str, ""),
            })
        df_master = pd.DataFrame(master_rows)
        df_master[COL_WL] = df_master[COL_WL].astype(str).str.strip()
        df_group[COL_WL] = df_group[COL_WL].astype(str).str.strip()
        # Mescla com os dados agregados das câmeras (se existirem), mantendo apenas IDs do master
        df_group = pd.merge(
            df_master,
            df_group.drop(columns=["city", "uf"], errors="ignore"),
            on=COL_WL,
            how="left"
        )
        # Garante valores numéricos corretos para total/offline e nomes
        df_group["total"] = df_group["total"].fillna(0).astype(int)
        df_group["offline"] = df_group["offline"].fillna(0).astype(int)
        df_group["nome_empresa"] = df_group["nome_empresa"].fillna(df_group["nome_cliente"]) 
        # Recalcula Pct com segurança (0 quando total==0)
        df_group["Pct"] = df_group.apply(lambda r: (r["offline"]/r["total"]*100) if r["total"] else 0.0, axis=1)
    
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
            # Tenta geocodificar pelo Nominatim quando não há coordenada fixa
            coords = None
            try:
                if row.get("city") and str(row.get("city")).strip():
                    coords = geocode_cidade(row.get("city"), row.get("uf"))
            except Exception:
                coords = None

            if coords:
                df_group.at[idx, "lat"] = coords[0]
                df_group.at[idx, "lon"] = coords[1]
            else:
                # TRAVA DE SEGURANÇA: posicionamento provisório em Joinville
                df_group.at[idx, "lat"] = -26.3045
                df_group.at[idx, "lon"] = -48.8434
                if cidade_bruta == "nan" or cidade_bruta.isdigit() or not cidade_bruta:
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
        "Cidade: " + df_group["city"].astype(str) + " - " + df_group["uf"].astype(str) + "<br>" +
        "Franqueado: <b>" + df_group["nome_empresa"].astype(str) + "</b><br>" +
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
            colorscale=[
                [0.0, "#7ff3a2"],
                [0.05, "#14b8a6"],
                [0.07, "#fde047"],
                [0.10, "#f59e0b"],
                [0.35, "#ef4444"],
                [1.0, "#b91c1c"],
            ],
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
        colorscale=[
            [0.0, "#dff8f3"],
            [0.05, "#14b8a6"],
            [0.07, "#fde047"],
            [0.10, "#f59e0b"],
            [0.35, "#ef4444"],
            [1.0, "#b91c1c"],
        ],
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
    1 - Supabase / BD online, quando configurado e com dados
    2 - GOV_extracao_cameras.csv local
    3 - XLSX individuais
    """

    if not os.path.exists(pasta):
        return {}, f"Pasta não encontrada: `{pasta}`", None

    clientes_map = carregar_clientes()
    clientes_prefeitura = carregar_clientes_prefeitura()

    # ============================================================
    # 1) BD ONLINE - SUPABASE
    # ============================================================
    if supabase_configurado():
        df_supabase, erro_supabase = carregar_cameras_supabase()
        if df_supabase is not None and not df_supabase.empty:
            df = converter_supabase_para_df_gov(df_supabase)
            df = preencher_cidade_estado_por_clientes(df, clientes_prefeitura)
            return processar_df_gov(df, clientes_map), "", df
        elif erro_supabase:
            # Não bloqueia o app: mantém fallback local para facilitar manutenção.
            pass

    # ============================================================
    # 2) CSV PRINCIPAL
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
    if supabase_configurado():
        df_supabase, erro_supabase = carregar_cameras_supabase()
        if df_supabase is not None and not df_supabase.empty:
            return calcular_saude_dataframe(converter_supabase_para_df_gov(df_supabase), clientes_map, "Supabase / BD online")
    if os.path.exists(CSV_GOV):
        return calcular_saude_dataframe(ler_csv_gov(CSV_GOV), clientes_map, "Arquivo local")

    if os.path.exists(IMPORTACAO_INDIVIDUAL_DIR):
        df_xlsx, _ = carregar_xlsx_individuais(IMPORTACAO_INDIVIDUAL_DIR)
        return calcular_saude_dataframe(df_xlsx, clientes_map, "Pasta importacao_individual")

    return calcular_saude_dataframe(None, clientes_map, "Arquivo local")


# ─────────────────────────────────────────────
# SNAPSHOTS ONLINE - SUPABASE
# ─────────────────────────────────────────────
SNAPSHOT_TABLE = os.getenv("SUPABASE_SNAPSHOT_TABLE", "snapshot_cameras")
SNAPSHOT_MASTER_TABLE = os.getenv("SUPABASE_SNAPSHOT_MASTER_TABLE", "snapshots")
SNAPSHOT_CLIENTES_TABLE = os.getenv("SUPABASE_SNAPSHOT_CLIENTES_TABLE", "snapshot_clientes")


def init_db():
    """Mantido para compatibilidade com o fluxo antigo do app.

    Nesta versão, os snapshots não usam mais SQLite/historico.db.
    Eles são gravados no Supabase, na tabela snapshot_cameras.
    """
    return None


def _supabase_select_all(tabela: str, params: dict | None = None, page_size: int = 1000) -> tuple[pd.DataFrame, str]:
    if not supabase_configurado():
        return pd.DataFrame(), "Supabase não configurado."

    todos = []
    offset = 0
    try:
        while True:
            headers = supabase_headers()
            headers["Range"] = f"{offset}-{offset + page_size - 1}"
            resp = requests.get(
                supabase_table_url(tabela),
                headers=headers,
                params=params or {},
                timeout=60,
            )
            if resp.status_code not in (200, 206):
                return pd.DataFrame(), f"Erro ao consultar {tabela}: {resp.status_code} - {resp.text[:500]}"
            lote = resp.json()
            if not lote:
                break
            todos.extend(lote)
            if len(lote) < page_size:
                break
            offset += page_size
    except Exception as e:
        return pd.DataFrame(), f"Erro ao consultar {tabela}: {e}"

    return pd.DataFrame(todos), ""


def _snapshot_datas_df() -> pd.DataFrame:
    """Lista snapshots a partir da tabela mestre public.snapshots.

    Cada clique no botão Salvar snapshot cria 1 linha aqui e N linhas em
    snapshot_cameras. Isso evita sobrescrever ou confundir lotes.
    """
    df, erro = _supabase_select_all(
        SNAPSHOT_MASTER_TABLE,
        params={
            "select": "id,label,gravado_em,notas",
            "order": "id.desc",
        },
        page_size=1000,
    )
    if erro or df.empty:
        return pd.DataFrame(columns=["id", "snapshot_uuid", "label", "gravado_em", "notas"])

    for col in ["id", "label", "gravado_em", "notas"]:
        if col not in df.columns:
            df[col] = ""

    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df[df["id"].notna()].copy()
    df["id"] = df["id"].astype(int)
    df["snapshot_uuid"] = df["id"].astype(str)
    df["gravado_em"] = pd.to_datetime(df["gravado_em"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").fillna(df["gravado_em"].astype(str))
    df["label"] = df["label"].astype(str).replace({"nan": ""})
    df["notas"] = df["notas"].astype(str).replace({"nan": ""})
    return df[["id", "snapshot_uuid", "label", "gravado_em", "notas"]].sort_values("id", ascending=False).reset_index(drop=True)


def _snapshot_ref_por_id(sid: int) -> dict | None:
    df = _snapshot_datas_df()
    if df.empty:
        return None
    row = df[df["id"].astype(int) == int(sid)]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def montar_df_clientes_snapshot(dados: dict) -> pd.DataFrame:
    """Monta o resumo por cliente exatamente a partir dos mesmos dados usados nos cards do dashboard."""
    rows = []
    for wl_id, info in (dados or {}).items():
        wl = str(wl_id).strip()
        if not wl:
            continue
        total = int(info.get("total", 0) or 0)
        df_off = info.get("offline")
        try:
            offline = int(len(df_off)) if df_off is not None else int(info.get("offline_count", 0) or 0)
        except Exception:
            offline = int(info.get("offline_count", 0) or 0)
        pct = round((offline / total * 100), 2) if total else 0.0
        rows.append({
            "wl_id": wl,
            "nome_cliente": str(info.get("cidade_estado") or info.get("nome_cliente") or f"ID {wl}"),
            "nome_empresa": str(info.get("nome_empresa") or ""),
            "total": total,
            "offline": offline,
            "pct_offline": pct,
        })
    return pd.DataFrame(rows, columns=["wl_id", "nome_cliente", "nome_empresa", "total", "offline", "pct_offline"])


def carregar_snapshot_clientes(sid: int, wl_ids_validos: set[str] | None = None) -> pd.DataFrame:
    """Lê o resumo salvo por cliente. Esta é a fonte oficial do comparativo."""
    params = {
        "select": "*",
        "snapshot_id": f"eq.{int(sid)}",
        "order": "id_whitelabel.asc",
    }
    df, erro = _supabase_select_all(SNAPSHOT_CLIENTES_TABLE, params=params, page_size=5000)
    if erro or df.empty:
        return pd.DataFrame(columns=["wl_id", "nome_cliente", "total", "offline", "pct_offline"])

    out = pd.DataFrame()
    out["wl_id"] = df.get("id_whitelabel", "").astype(str).str.strip()
    out["nome_cliente"] = df.get("nome_cliente", "").astype(str).replace({"nan": ""}).str.strip()
    out["total"] = pd.to_numeric(df.get("total_cameras", 0), errors="coerce").fillna(0).astype(int)
    out["offline"] = pd.to_numeric(df.get("total_offline", 0), errors="coerce").fillna(0).astype(int)
    out["pct_offline"] = pd.to_numeric(df.get("pct_offline", 0), errors="coerce").fillna(0.0)

    if wl_ids_validos:
        wl_ids_validos = {str(x).strip() for x in wl_ids_validos if str(x).strip()}
        out = out[out["wl_id"].isin(wl_ids_validos)].copy()

    out = out[out["wl_id"] != ""].copy()
    # Se por qualquer motivo houver duplicidade, fica a última linha salva para aquele cliente.
    out = out.drop_duplicates(subset=["wl_id"], keep="last").reset_index(drop=True)
    return out[["wl_id", "nome_cliente", "total", "offline", "pct_offline"]]


def montar_df_cameras_snapshot(df_origem: pd.DataFrame | None, dados: dict) -> pd.DataFrame:
    """Monta a base de câmeras do snapshot atual para identificar novas câmeras futuramente."""
    if df_origem is None or df_origem.empty:
        return pd.DataFrame(columns=[
            "wl_id", "nome_cliente", "nome_empresa", "id_camera",
            "nome_camera", "ultima_atualizacao", "status_camera"
        ])

    df_cam = df_origem.copy()
    df_cam.columns = [str(c).strip() for c in df_cam.columns]

    if COL_WL not in df_cam.columns or COL_ID_CAM not in df_cam.columns:
        return pd.DataFrame(columns=[
            "wl_id", "nome_cliente", "nome_empresa", "id_camera",
            "nome_camera", "ultima_atualizacao", "status_camera"
        ])

    df_cam[COL_WL] = df_cam[COL_WL].astype(str).str.strip()
    df_cam[COL_ID_CAM] = df_cam[COL_ID_CAM].astype(str).str.strip()
    df_cam = df_cam[df_cam[COL_ID_CAM].notna() & (df_cam[COL_ID_CAM] != "") & (df_cam[COL_ID_CAM].str.lower() != "nan")].copy()

    ids_validos = set(str(k).strip() for k in (dados or {}).keys()) or set(df_cam[COL_WL].astype(str).str.strip())
    df_cam = df_cam[df_cam[COL_WL].isin(ids_validos)].copy()

    if df_cam.empty:
        return pd.DataFrame(columns=[
            "wl_id", "nome_cliente", "nome_empresa", "id_camera",
            "nome_camera", "ultima_atualizacao", "status_camera"
        ])

    for col in [COL_NOME_CAM, COL_ULT_ATU, COL_STATUS, COL_EMPRESA]:
        if col not in df_cam.columns:
            df_cam[col] = ""

    try:
        ultima_fmt = parse_ultima_atualizacao(df_cam[COL_ULT_ATU]).dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
    except Exception:
        ultima_fmt = df_cam[COL_ULT_ATU].astype(str).fillna("")

    rows = []
    for idx_row, row in df_cam.iterrows():
        wl = str(row.get(COL_WL, "")).strip()
        info_cliente = dados.get(wl, {}) if isinstance(dados, dict) else {}
        rows.append({
            "wl_id": wl,
            "nome_cliente": info_cliente.get("cidade_estado") or info_cliente.get("nome_cliente", f"ID {wl}"),
            "nome_empresa": str(row.get(COL_EMPRESA, "") or info_cliente.get("nome_empresa", "")),
            "id_camera": str(row.get(COL_ID_CAM, "")).strip(),
            "nome_camera": str(row.get(COL_NOME_CAM, "") or ""),
            "ultima_atualizacao": str(ultima_fmt.loc[idx_row] if idx_row in ultima_fmt.index else ""),
            "status_camera": str(row.get(COL_STATUS, "") or "").upper(),
        })

    df_out = pd.DataFrame(rows)
    return df_out.drop_duplicates(subset=["wl_id", "id_camera"], keep="last").reset_index(drop=True)


def carregar_snapshot_cameras(sid: int, wl_ids_validos: set[str] | None = None) -> pd.DataFrame:
    params = {
        "select": "*",
        "snapshot_id": f"eq.{int(sid)}",
        "order": "id_camera.asc",
    }
    df, erro = _supabase_select_all(
        SNAPSHOT_TABLE,
        params=params,
        page_size=5000,
    )
    if erro or df.empty:
        return pd.DataFrame(columns=[
            "wl_id", "nome_cliente", "nome_empresa", "id_camera",
            "nome_camera", "ultima_atualizacao", "status_camera"
        ])

    clientes_map = carregar_clientes()
    out = pd.DataFrame()
    out["wl_id"] = df.get("id_whitelabel", "").astype(str).str.strip()
    out["nome_cliente"] = out["wl_id"].map(clientes_map).fillna("ID " + out["wl_id"].astype(str))
    out["nome_empresa"] = df.get("nome_empresa", "").astype(str).replace({"nan": ""}).str.strip()
    out["id_camera"] = df.get("id_camera", "").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    out["nome_camera"] = df.get("nome_camera", "").astype(str).replace({"nan": ""}).str.strip()
    out["ultima_atualizacao"] = df.get("ultima_atualizacao", "").astype(str).replace({"nan": ""}).str.strip()
    out["status_camera"] = df.get("status_camera", "").astype(str).str.strip().str.upper()

    # Mantém o mesmo universo de clientes do painel/nome_clientes.xlsx.
    if wl_ids_validos:
        wl_ids_validos = {str(x).strip() for x in wl_ids_validos if str(x).strip()}
        out = out[out["wl_id"].isin(wl_ids_validos)].copy()

    # Segurança contra duplicidade dentro do mesmo snapshot.
    # O comparativo precisa contar cada câmera uma única vez.
    out = out[(out["wl_id"] != "") & (out["id_camera"] != "") & (out["id_camera"].str.lower() != "nan")].copy()
    out = out.drop_duplicates(subset=["wl_id", "id_camera"], keep="last").reset_index(drop=True)
    return out


def salvar_snapshot(label: str, notas: str, dados: dict, df_origem: pd.DataFrame | None = None) -> str:
    """Salva snapshot acumulado no Supabase: 1 cabeçalho + N câmeras.

    Não usa UPSERT. Não apaga snapshot anterior. Cada clique cria um novo ID.
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1) Cria o cabeçalho do snapshot e pega o ID gerado.
    payload_master = {
        "label": limpar_valor_json(label),
        "gravado_em": agora,
        "notas": limpar_valor_json(notas),
    }
    resp_master = requests.post(
        supabase_table_url(SNAPSHOT_MASTER_TABLE),
        headers=supabase_headers("return=representation"),
        json=payload_master,
        timeout=30,
    )
    if resp_master.status_code not in (200, 201):
        raise RuntimeError(f"Erro ao criar cabeçalho do snapshot no Supabase: {resp_master.status_code} - {resp_master.text[:500]}")

    data_master = resp_master.json()
    if not data_master or "id" not in data_master[0]:
        raise RuntimeError("Snapshot criado, mas o Supabase não retornou o ID do cabeçalho.")
    snapshot_id = int(data_master[0]["id"])

    # 2) Grava o RESUMO POR CLIENTE, exatamente igual ao dashboard.
    # Esta passa a ser a fonte oficial dos cards/comparativos, evitando divergência
    # quando df_origem tiver filtros, colunas ou conversões diferentes.
    df_clientes_snap = montar_df_clientes_snapshot(dados)
    registros_clientes = []
    for _, r in df_clientes_snap.iterrows():
        registros_clientes.append({
            "snapshot_id": snapshot_id,
            "data_snapshot": agora,
            "id_whitelabel": limpar_valor_json(r.get("wl_id")),
            "nome_cliente": limpar_valor_json(r.get("nome_cliente")),
            "nome_empresa": limpar_valor_json(r.get("nome_empresa")),
            "total_cameras": int(r.get("total", 0) or 0),
            "total_offline": int(r.get("offline", 0) or 0),
            "pct_offline": float(r.get("pct_offline", 0) or 0),
        })

    for i in range(0, len(registros_clientes), 500):
        lote_cli = registros_clientes[i:i + 500]
        if not lote_cli:
            continue
        resp_cli = requests.post(
            supabase_table_url(SNAPSHOT_CLIENTES_TABLE),
            headers=supabase_headers("return=minimal"),
            json=lote_cli,
            timeout=60,
        )
        if resp_cli.status_code not in (200, 201, 204):
            raise RuntimeError(f"Erro ao salvar resumo de clientes do snapshot no Supabase: {resp_cli.status_code} - {resp_cli.text[:500]}")

    # 3) Grava as câmeras vinculadas ao snapshot_id para detalhamento de novas/removidas.
    df_cameras_snap = montar_df_cameras_snapshot(df_origem, dados)
    registros = []
    for _, r in df_cameras_snap.iterrows():
        id_camera = limpar_valor_json(r.get("id_camera"))
        try:
            id_camera = int(float(str(id_camera))) if id_camera not in (None, "") else None
        except Exception:
            id_camera = None
        if id_camera is None:
            continue

        registros.append({
            "snapshot_id": snapshot_id,
            "data_snapshot": agora,
            "snapshot_uuid": str(snapshot_id),
            "label": limpar_valor_json(label),
            "notas": limpar_valor_json(notas),
            "id_camera": id_camera,
            "id_whitelabel": limpar_valor_json(r.get("wl_id")),
            "nome_empresa": limpar_valor_json(r.get("nome_empresa")),
            "nome_camera": limpar_valor_json(r.get("nome_camera")),
            "status_camera": limpar_valor_json(str(r.get("status_camera", "")).upper()),
            "ultima_atualizacao": limpar_valor_json(r.get("ultima_atualizacao")),
        })

    for i in range(0, len(registros), 500):
        lote = registros[i:i + 500]
        resp = requests.post(
            supabase_table_url(SNAPSHOT_TABLE),
            headers=supabase_headers("return=minimal"),
            json=lote,
            timeout=60,
        )
        if resp.status_code not in (200, 201, 204):
            raise RuntimeError(f"Erro ao salvar câmeras do snapshot no Supabase: {resp.status_code} - {resp.text[:500]}")

    try:
        st.cache_data.clear()
    except Exception:
        pass

    return agora


def listar_snapshots() -> pd.DataFrame:
    return _snapshot_datas_df()


def carregar_snapshot(sid: int, wl_ids_validos: set[str] | None = None) -> pd.DataFrame:
    # Fonte oficial do comparativo: resumo por cliente salvo junto com o snapshot.
    # Assim o total offline do snapshot bate com o total que estava na tela no momento do salvamento.
    df_clientes = carregar_snapshot_clientes(int(sid), wl_ids_validos=wl_ids_validos)
    if not df_clientes.empty:
        return df_clientes

    # Fallback para snapshots antigos, salvos antes da tabela snapshot_clientes existir.
    df_cams = carregar_snapshot_cameras(int(sid), wl_ids_validos=wl_ids_validos)
    if df_cams.empty:
        return pd.DataFrame(columns=["wl_id", "nome_cliente", "total", "offline", "pct_offline"])

    rows = []
    for wl_id, grupo in df_cams.groupby(df_cams["wl_id"].astype(str).str.strip()):
        grupo = grupo.drop_duplicates(subset=["wl_id", "id_camera"], keep="last")
        total = int(len(grupo))
        offline = int((grupo["status_camera"].astype(str).str.strip().str.upper() == "OFFLINE").sum())
        pct = round(offline / total * 100, 2) if total else 0.0
        nome_cliente = str(grupo["nome_cliente"].iloc[0]) if "nome_cliente" in grupo.columns and len(grupo) else f"ID {wl_id}"
        rows.append({
            "wl_id": str(wl_id).strip(),
            "nome_cliente": nome_cliente,
            "total": total,
            "offline": offline,
            "pct_offline": pct,
        })
    return pd.DataFrame(rows, columns=["wl_id", "nome_cliente", "total", "offline", "pct_offline"])


def montar_snapshot_atual_df(dados: dict) -> pd.DataFrame:
    linhas = []
    for wl_id, info in (dados or {}).items():
        total = int(info.get("total", 0) or 0)
        offline = int(len(info.get("offline", [])) or 0)
        pct = (offline / total * 100) if total else 0.0
        linhas.append({
            "wl_id": str(wl_id),
            "nome_cliente": info.get("nome_cliente", f"ID {wl_id}"),
            "total": total,
            "offline": offline,
            "pct_offline": pct,
        })
    return pd.DataFrame(linhas, columns=["wl_id", "nome_cliente", "total", "offline", "pct_offline"])


def deletar_snapshot(sid: int):
    sid = int(sid)

    resp_cam = requests.delete(
        supabase_table_url(SNAPSHOT_TABLE),
        headers=supabase_headers("return=minimal"),
        params={"snapshot_id": f"eq.{sid}"},
        timeout=60,
    )
    if resp_cam.status_code not in (200, 202, 204):
        st.error(f"Erro ao excluir câmeras do snapshot: {resp_cam.status_code} - {resp_cam.text[:500]}")
        return

    resp_snap = requests.delete(
        supabase_table_url(SNAPSHOT_MASTER_TABLE),
        headers=supabase_headers("return=minimal"),
        params={"id": f"eq.{sid}"},
        timeout=60,
    )
    if resp_snap.status_code not in (200, 202, 204):
        st.error(f"Erro ao excluir cabeçalho do snapshot: {resp_snap.status_code} - {resp_snap.text[:500]}")
        return

    try:
        st.cache_data.clear()
    except Exception:
        pass


def snapshot_referencia() -> pd.DataFrame | None:
    ids = carregar_ultimos_snapshots_ids(1)
    if not ids:
        return None
    return carregar_snapshot(int(ids[0]))


def carregar_ultimos_snapshots_ids(limit: int = 2) -> list[int]:
    df = listar_snapshots()
    if df.empty:
        return []
    return df["id"].astype(int).head(limit).tolist()


def salvar_snapshot_automatico(dados: dict) -> str:
    return ""


def carregar_historico_clientes(dias: int = 30) -> pd.DataFrame:
    limite = datetime.now() - timedelta(days=dias)
    df_snaps = listar_snapshots()
    if df_snaps.empty:
        return pd.DataFrame(columns=["snapshot_id", "label", "gravado_em", "wl_id", "nome_cliente", "total", "offline", "pct_offline"])

    df_snaps["gravado_dt"] = pd.to_datetime(df_snaps["gravado_em"], errors="coerce")
    df_snaps = df_snaps[df_snaps["gravado_dt"] >= limite].copy()

    rows = []
    for _, snap in df_snaps.iterrows():
        df_cli = carregar_snapshot(int(snap["id"]))
        for _, r in df_cli.iterrows():
            rows.append({
                "snapshot_id": int(snap["id"]),
                "label": snap["label"],
                "gravado_em": snap["gravado_em"],
                "wl_id": r["wl_id"],
                "nome_cliente": r["nome_cliente"],
                "total": int(r["total"]),
                "offline": int(r["offline"]),
                "pct_offline": float(r["pct_offline"]),
            })
    return pd.DataFrame(rows)


def obter_datas_snapshots(snapshot_ids: list[int]) -> pd.DataFrame:
    df = listar_snapshots()
    if df.empty:
        return pd.DataFrame(columns=["id", "gravado_em"])
    ids = [int(x) for x in snapshot_ids]
    return df[df["id"].astype(int).isin(ids)][["id", "gravado_em"]].copy()

def calcular_recorrencia(dias: int = 30) -> dict:
    df_hist = carregar_historico_clientes(dias)
    if df_hist.empty:
        return {}

    df_hist["dia"] = pd.to_datetime(df_hist["gravado_em"], errors="coerce").dt.date
    rows = []
    for wl_id, grupo in df_hist.groupby("wl_id"):
        dias_off = grupo.loc[grupo["offline"] > 0, "dia"].nunique()
        dias_crit = grupo.loc[grupo["pct_offline"] > 10, "dia"].nunique()
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
                "Cidade": v.get("cidade_estado") or v.get("cidade") or v["nome_cliente"],
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
            "Status": "Crítico" if pct > 10 else ("Atenção" if pct > 5 else "Saudável"),
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
    nome_display = escape_html(v.get("cidade_estado") or v["nome_cliente"])
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
def render_sidebar(dados, total_cameras, total_offline, pct_global, df_origem=None):
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo" style="display:flex;flex-direction:column;align-items:center;gap:10px;margin-bottom:1rem;text-align:center;">
            <img src="https://i.ibb.co/YFxRMYzB/image-removebg-preview.png" style="height:250px;width:auto;display:block" alt="Camerite">
            <div class="sidebar-logo-text">Monitoramento Franquias GOV</div>
            <div class="sidebar-logo-sub">Auditoria Operacional</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="nav-section">Governança</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:1rem">
            <div class="sidebar-stat-card">
                <div class="stat-label">Total Câmeras</div>
                <div class="stat-value">{total_cameras}</div>
            </div>
            <div class="sidebar-stat-card offline-card">
                <div class="stat-label">Offline</div>
                <div class="stat-value">{total_offline}</div>
                <div class="stat-note">{pct_global:.1f}% da frota</div>
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
            try:
                salvar_snapshot(lbl, nota, dados, df_origem)
                st.success("Snapshot salvo!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erro ao salvar snapshot no Supabase: {e}")
                st.info("Confira se a tabela snapshot_cameras existe e se o RLS dela está desativado.")

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
    n_critico      = sum(1 for v in dados.values() if (len(v["offline"])/v["total"]*100 if v["total"] else 0) > 10)
    n_atencao      = sum(1 for v in dados.values() if 5 < (len(v["offline"])/v["total"]*100 if v["total"] else 0) <= 10)
    clientes_alert = sum(1 for v in dados.values() if len(v["offline"]) > 0)
    n_saudavel     = total_clientes - n_critico - n_atencao
    audit_label, audit_color, audit_reason = classificar_auditoria(pct_global, n_critico, n_atencao, saude)
    acao_curta, acao_detalhe = recomendacao_auditoria(n_critico, n_atencao, saude)
    pct_clientes_criticos = round(n_critico / total_clientes * 100, 1) if total_clientes else 0
    pct_clientes_atencao = round(n_atencao / total_clientes * 100, 1) if total_clientes else 0

    # Comparar os snapshots escolhidos no Histórico quando houver seleção.
    # Se ainda não houver seleção, usa os dois últimos snapshots manuais.
    df_base_delta = pd.DataFrame()
    df_base_cameras_novas = pd.DataFrame()
    total_cameras_anterior = 0
    total_cameras_recente_comparativo = total_cameras
    total_offline_recente_comparativo = total_offline
    delta_total_cameras = 0
    clientes_base_nova = 0
    clientes_base_reduzida = 0
    detalhe_cameras_disponivel = False

    snap_base_sel = st.session_state.get("comparativo_snapshot_a_id", st.session_state.get("hist_snap_a"))
    snap_recente_sel = st.session_state.get("comparativo_snapshot_b_id", st.session_state.get("hist_snap_b"))
    snapshot_ids = []
    try:
        if snap_base_sel is not None and snap_recente_sel is not None and int(snap_base_sel) != int(snap_recente_sel):
            # Usa exatamente os snapshots selecionados na aba Comparativo.
            # Ordem interna: [recente/B, base/A].
            snapshot_ids = [int(snap_recente_sel), int(snap_base_sel)]
    except Exception:
        snapshot_ids = []
    if len(snapshot_ids) != 2:
        snapshot_ids = carregar_ultimos_snapshots_ids(2)
    datas_comparativo_txt = st.session_state.get("comparativo_datas_txt", "Comparativo: snapshots insuficientes")
    if len(snapshot_ids) == 2:
        try:
            df_datas_comp = obter_datas_snapshots(snapshot_ids)
            data_map_comp = dict(zip(df_datas_comp["id"].astype(int), df_datas_comp["gravado_em"].astype(str)))
            data_atual_comp = pd.to_datetime(data_map_comp.get(snapshot_ids[0], ""), errors="coerce").strftime("%d/%m/%Y %H:%M")
            data_ant_comp = pd.to_datetime(data_map_comp.get(snapshot_ids[1], ""), errors="coerce").strftime("%d/%m/%Y %H:%M")
            datas_comparativo_txt = f"Comparando {data_ant_comp} → {data_atual_comp}"
        except Exception:
            datas_comparativo_txt = "Comparativo: não foi possível identificar as datas dos snapshots"
    if len(snapshot_ids) == 2:
        # Comparativo correto: quando o usuário seleciona dois snapshots,
        # os dois lados precisam vir do histórico salvo no Supabase.
        # Não usamos a base atual carregada em tela aqui, porque isso gera
        # divergência quando a base atual é diferente do snapshot B selecionado.
        wl_ids_validos_comp = {str(wl).strip() for wl in (dados or {}).keys()}
        df_new = carregar_snapshot(snapshot_ids[0], wl_ids_validos=wl_ids_validos_comp)
        df_old = carregar_snapshot(snapshot_ids[1], wl_ids_validos=wl_ids_validos_comp)

        new_map = df_new.set_index("wl_id")[['offline','pct_offline','total']].to_dict(orient='index')
        old_map = df_old.set_index("wl_id")[['offline','pct_offline','total']].to_dict(orient='index')

        tendencias = {}
        delta_offs = {}
        delta_totais = {}

        for wl in dados:
            pct_new = new_map.get(wl, {}).get('pct_offline', 0.0)
            off_new = new_map.get(wl, {}).get('offline', 0)
            pct_old = old_map.get(wl, {}).get('pct_offline', 0.0)
            off_old = old_map.get(wl, {}).get('offline', 0)

            total_new = int(new_map.get(wl, {}).get("total", dados.get(wl, {}).get("total", 0)) or 0)
            total_old = int(old_map.get(wl, {}).get("total", 0) or 0)

            tendencias[wl] = round(pct_new - pct_old, 2)
            delta_offs[wl] = off_new - off_old
            delta_totais[wl] = total_new - total_old

        # Cards do comparativo usam o snapshot B selecionado como recente.
        total_cameras_anterior = int(df_old["total"].sum()) if "total" in df_old.columns else 0
        total_cameras_recente_comparativo = int(df_new["total"].sum()) if "total" in df_new.columns else 0
        total_offline_recente_comparativo = int(df_new["offline"].sum()) if "offline" in df_new.columns else 0
        delta_total_cameras = total_cameras_recente_comparativo - total_cameras_anterior

        linhas_base_delta = []
        for wl, delta_total in delta_totais.items():
            if not isinstance(delta_total, (int, float)) or int(delta_total) == 0:
                continue

            total_atual_cliente = int(new_map.get(wl, {}).get("total", dados.get(wl, {}).get("total", 0)) or 0)
            total_anterior_cliente = int(old_map.get(wl, {}).get("total", 0) or 0)

            linhas_base_delta.append({
                "Cliente": dados.get(wl, {}).get("cidade_estado") or dados.get(wl, {}).get("nome_cliente", f"ID {wl}"),
                "Franqueado": dados.get(wl, {}).get("nome_empresa", ""),
                "Anterior": total_anterior_cliente,
                "Atual": total_atual_cliente,
                "Variação": int(delta_total),
            })

        df_base_delta = pd.DataFrame(linhas_base_delta)
        if not df_base_delta.empty:
            df_base_delta = df_base_delta.sort_values("Variação", ascending=False).reset_index(drop=True)

        clientes_base_nova = sum(1 for v in delta_totais.values() if isinstance(v, (int, float)) and v > 0)
        clientes_base_reduzida = sum(1 for v in delta_totais.values() if isinstance(v, (int, float)) and v < 0)

        # Detalhamento das câmeras novas: só fica disponível quando ambos os snapshots
        # foram salvos por esta versão ou posterior, que grava snapshot_cameras.
        df_cams_new = carregar_snapshot_cameras(snapshot_ids[0], wl_ids_validos=wl_ids_validos_comp)
        df_cams_old = carregar_snapshot_cameras(snapshot_ids[1], wl_ids_validos=wl_ids_validos_comp)

        if not df_cams_new.empty and not df_cams_old.empty:
            detalhe_cameras_disponivel = True

            df_cams_new["chave_camera"] = (
                df_cams_new["wl_id"].astype(str).str.strip() + "||" +
                df_cams_new["id_camera"].astype(str).str.strip()
            )
            df_cams_old["chave_camera"] = (
                df_cams_old["wl_id"].astype(str).str.strip() + "||" +
                df_cams_old["id_camera"].astype(str).str.strip()
            )

            chaves_antigas = set(df_cams_old["chave_camera"])
            df_novas = df_cams_new[~df_cams_new["chave_camera"].isin(chaves_antigas)].copy()

            if not df_novas.empty:
                df_base_cameras_novas = df_novas.rename(columns={
                    "nome_cliente": "Cliente",
                    "nome_empresa": "Franqueado",
                    "id_camera": "ID da Câmera",
                    "nome_camera": "Nome da Câmera",
                    "ultima_atualizacao": "Última Vez Online",
                    "status_camera": "Status",
                })[[
                    "Cliente",
                    "Franqueado",
                    "ID da Câmera",
                    "Nome da Câmera",
                    "Última Vez Online",
                    "Status",
                ]].sort_values(["Cliente", "Nome da Câmera", "ID da Câmera"]).reset_index(drop=True)
    else:
        tendencias = {wl: None for wl in dados}
        delta_offs = {wl: None for wl in dados}
        delta_totais = {wl: None for wl in dados}

    recorrencia = calcular_recorrencia(30)
    df_clientes_ops = montar_df_clientes(dados, tendencias, delta_offs, recorrencia)
    df_tempo_global = montar_df_tempo(dados)
    total_offline_anterior = 0
    if len(snapshot_ids) == 2:
        try:
            total_offline_anterior = int(df_old["offline"].sum())
        except Exception:
            total_offline_anterior = total_offline

    delta_global = total_offline - total_offline_anterior

    if delta_total_cameras > 0:
        texto_delta_base = f"+{delta_total_cameras}"
        cor_delta_base = "#14b8a6"
        detalhe_delta_base = f"{delta_total_cameras} câmeras novas"
    elif delta_total_cameras < 0:
        texto_delta_base = str(delta_total_cameras)
        cor_delta_base = "#ef4444"
        detalhe_delta_base = f"{abs(delta_total_cameras)} câmeras removidas"
    else:
        texto_delta_base = "+0"
        cor_delta_base = "#0088cc"
        detalhe_delta_base = "Sem alteração na base"

    clientes_melhoraram = sum(1 for v in delta_offs.values() if isinstance(v, (int, float)) and v < 0)
    clientes_pioraram = sum(1 for v in delta_offs.values() if isinstance(v, (int, float)) and v > 0)

    # ── Sidebar ──
    render_sidebar(dados, total_cameras, total_offline, pct_global, df_origem)

    # ── Page header ──
    st.markdown(f"""
    <div class="page-header">
        <div>
            <div class="page-title">Monitoramento Operacional</div>
            <div class="page-sub">{total_clientes} clientes · {total_cameras} câmeras monitoradas</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ABAS ──
    tabs = st.tabs([
        "Auditoria",
        "Clientes",
        "Tempo offline",
        "% por cliente",
        "Evidências",
        "LPRs Offline",
        "Atualizar Base",
    ])

    # ════════════════════════════════════════════
    # ABA 0 — VISÃO EXECUTIVA
    # ════════════════════════════════════════════
    with tabs[0]:
        st.markdown(f"""
        <div class="audit-hero">
            <div class="audit-hero-top">
                <div>
                    <div class="audit-title">Auditoria Clientes GOV</div>
                    <div class="audit-sub">
                        {acao_detalhe}<br>
                        <span style="display:inline-block;margin-top:6px;font-family:'DM Mono',monospace;color:#007ab8;background:#e8f7fc;border:1px solid #b9e7f4;border-radius:6px;padding:5px 8px">📅 {datas_comparativo_txt}</span>
                    </div>
                </div>
                <div class="audit-badges">
                    <div class="audit-badge" style="color:{audit_color}">{audit_label}</div>
                </div>
            </div>
        </div>
        <div class="audit-strip">
            <div class="audit-card">
                <div class="audit-card-label">Clientes críticos</div>
                <div class="audit-card-value" style="color:#dc2626">{n_critico}/{total_clientes}</div>
                <div class="audit-card-note">{pct_clientes_criticos:.1f}% da carteira auditada acima de 10% offline</div>
            </div>
            <div class="audit-card">
                <div class="audit-card-label">Clientes em atenção</div>
                <div class="audit-card-value" style="color:#d97706">{n_atencao}/{total_clientes}</div>
                <div class="audit-card-note">{pct_clientes_atencao:.1f}% da carteira auditada entre 5% e 10% offline</div>
            </div>
            <div class="audit-card">
                <div class="audit-card-label">Registros auditados</div>
                <div class="audit-card-value">{saude.get("linhas_processadas",0)}</div>
            </div>
            <div class="audit-card">
                <div class="audit-card-label">Data CSV</div>
                <div class="audit-card-value" style="font-size:20px;color:#102a3f">{saude.get("ultima_data","N/D")}</div>
                <div class="audit-card-note">Arquivo: {saude.get("arquivo_atualizado","N/D")}</div>
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
			<div class="kpi-card kpi-alert"
				 style="background:#ffffff !important;
						border-color:#dbe8f2 !important;">
				<div class="kpi-label">
					Câmeras Offline
				</div>
				<div class="kpi-value val-alert">
					{total_offline}
				</div>
				<div class="kpi-sub">
					{pct_global:.1f}% da frota total
				</div>
			</div>
            <div class="kpi-card kpi-ok">
                <div class="kpi-label">Câmeras Online</div>
                <div class="kpi-value val-ok">{total_cameras - total_offline}</div>
                <div class="kpi-sub">{100-pct_global:.1f}% operacionais</div>
            </div>
            <div class="kpi-card kpi-neutral">
                <div class="kpi-label">Variação de Câmeras Offline</div>
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
                    <div style="font-size:10px;color:#6b8496;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes até 5% offline</div>
                    <div style="font-size:24px;color:#14b8a6;font-family:'DM Mono',monospace;font-weight:700">{n_saudavel}</div>
                    <div style="font-size:11px;color:#6b8496">{n_saudavel} clientes · 0–5%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_saudavel"):
                st.session_state["audit_categoria"] = "Saudável (0-5%)"
                st.session_state["mostrar_base_delta"] = False
        with col_b:
            st.markdown(f"""
                <div class="kpi-card kpi-warn" style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#6b8496;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes em atenção (5 a 10% offline)</div>
                    <div style="font-size:24px;color:#f59e0b;font-family:'DM Mono',monospace;font-weight:700">{n_atencao}</div>
                    <div style="font-size:11px;color:#6b8496">{n_atencao} clientes · 5–10%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_atencao"):
                st.session_state["audit_categoria"] = "Atenção (5-10%)"
                st.session_state["mostrar_base_delta"] = False
        with col_c:
            st.markdown(f"""
                <div class="kpi-card kpi-neutral" style="background:#ffffff !important;border:1px solid #dbe8f2;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#6b8496;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes acima de 10% offline</div>
                    <div style="font-size:24px;color:#ef4444;font-family:'DM Mono',monospace;font-weight:700">{n_critico}</div>
                    <div style="font-size:11px;color:#6b8496">{n_critico} clientes · &gt;10%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_critico"):
                st.session_state["audit_categoria"] = "Crítico (>10%)"
                st.session_state["mostrar_base_delta"] = False
        with col_d:
            st.markdown(f"""
                <div class="kpi-card kpi-neutral" style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#6b8496;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Crescimento da Base</div>
                    <div style="font-size:24px;color:{cor_delta_base};font-family:'DM Mono',monospace;font-weight:700">{texto_delta_base}</div>
                    <div style="font-size:11px;color:#6b8496">{detalhe_delta_base} · Recente: {total_cameras_recente_comparativo} · Base: {total_cameras_anterior}</div>
                </div>
            """, unsafe_allow_html=True)

            if st.button("Ver clientes", key="base_delta_ver_clientes"):
                st.session_state["mostrar_base_delta"] = True
                st.session_state["audit_categoria"] = None


        if st.session_state.get("mostrar_base_delta", False):
            st.markdown("<hr>", unsafe_allow_html=True)

            st.markdown("""
            <div class="audit-section-title">
                <strong>Clientes com alteração na base de câmeras</strong>
                <span>Comparação entre o snapshot atual e o anterior</span>
            </div>
            """, unsafe_allow_html=True)

            col_base_a, col_base_b, col_base_c = st.columns(3)
            col_base_a.metric("Clientes com novas câmeras", int(clientes_base_nova))
            col_base_b.metric("Clientes com redução de base", int(clientes_base_reduzida))
            col_base_c.metric("Variação total", f"{delta_total_cameras:+d}")

            if not df_base_cameras_novas.empty:
                st.markdown("#### Câmeras novas identificadas")
                render_dataframe(
                    df_base_cameras_novas,
                    height=min(700, (len(df_base_cameras_novas) + 1) * 35 + 3)
                )

                buffer_cams = io.BytesIO()
                with pd.ExcelWriter(buffer_cams, engine="openpyxl") as writer:
                    df_base_cameras_novas.to_excel(writer, index=False, sheet_name="Cameras Novas")
                st.download_button(
                    "⬇ Baixar câmeras novas em Excel",
                    data=buffer_cams.getvalue(),
                    file_name=f"cameras_novas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            elif len(snapshot_ids) == 2 and detalhe_cameras_disponivel:
                st.info("Nenhuma câmera nova foi identificada entre o snapshot atual e o anterior.")
            elif len(snapshot_ids) == 2:
                st.warning(
                    "O resumo de crescimento existe, mas o detalhamento por ID de câmera ainda não está disponível "
                    "para esses snapshots antigos. Salve um novo snapshot com esta versão e, na próxima comparação, "
                    "o sistema exibirá Cliente, Franqueado, ID da Câmera, Nome da Câmera e Última Vez Online."
                )

                if not df_base_delta.empty:
                    st.markdown("#### Resumo por cliente disponível")
                    df_base_show = df_base_delta.copy()
                    df_base_show["Variação"] = df_base_show["Variação"].apply(lambda v: f"{v:+d}")
                    render_dataframe(
                        df_base_show,
                        height=min(620, (len(df_base_show) + 1) * 35 + 3)
                    )
            else:
                st.info("Salve ao menos dois snapshots para comparar o crescimento da base.")

            if st.button("Ocultar detalhamento", key="base_delta_ocultar"):
                st.session_state["mostrar_base_delta"] = False
                st.rerun()

        if st.session_state["audit_categoria"]:
            categoria = st.session_state["audit_categoria"]
            df_audit = df_clientes_ops.copy()
            if categoria == "Saudável (0-5%)":
                mask = df_audit["% Offline"] <= 5
            elif categoria == "Atenção (5-10%)":
                mask = (df_audit["% Offline"] > 5) & (df_audit["% Offline"] <= 10)
            else:
                mask = df_audit["% Offline"] > 10

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

        st.markdown("""
        <div class="audit-section-title">
            <strong>Evidências visuais</strong>
            <span>Distribuição do risco e clientes com maior exposição</span>
        </div>
        """, unsafe_allow_html=True)

        col_gauge, col_pie, col_top = st.columns([1,1,1], gap="large")

        with col_gauge:
            # Gauge invertido: agora exibe o percentual ONLINE do GOV.
            # Exemplo: 8% offline = 92% online.
            pct_online_global = round(100 - pct_global, 2) if total_cameras else 0

            st.markdown("**% Total de Câmeras ONLINE GOV**")

            # Para o gauge online, quanto maior o percentual, melhor.
            if pct_online_global >= 95:
                cor_g = "#14b8a6"
            elif pct_online_global >= 90:
                cor_g = "#f59e0b"
            else:
                cor_g = "#ef4444"

            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pct_online_global,
                number=dict(suffix="%", font=dict(color=cor_g, size=48, family="DM Mono")),
                gauge=dict(
                    shape="angular",
                    axis=dict(range=[0,100], showticklabels=False, ticks="", visible=False),
                    bar=dict(color=cor_g, thickness=0.34),
                    bgcolor="#f5f8fb",
                    borderwidth=0,
                    steps=[
                        dict(range=[0,90],   color="#fecaca"),
                        dict(range=[90,95],  color="#fde68a"),
                        dict(range=[95,100], color="#a7f3d0"),
                    ],
                    threshold=dict(line=dict(color="#475569", width=4), thickness=0.75, value=pct_online_global),
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
                        text=f"<span style='font-size:12px;color:#6b8496;font-family:DM Sans'>Câmeras operacionais</span>",
                        x=0.5, y=0.08, showarrow=False, xanchor="center"
                    )
                ],
            )
            st.plotly_chart(fig_g, use_container_width=True, key="gauge_online_gov")

        with col_pie:
            pct_saudavel_card = round(n_saudavel / total_clientes * 100, 1) if total_clientes else 0
            pct_atencao_card = round(n_atencao / total_clientes * 100, 1) if total_clientes else 0
            pct_critico_card = round(n_critico / total_clientes * 100, 1) if total_clientes else 0

            if n_critico > 0:
                status_saude_titulo = "Atenção crítica"
                status_saude_cor = "#dc2626"
                status_saude_msg = f"{n_critico} cliente(s) acima de 10% offline"
            elif n_atencao > 0:
                status_saude_titulo = "Monitoramento"
                status_saude_cor = "#d97706"
                status_saude_msg = f"{n_atencao} cliente(s) entre 5% e 10% offline"
            else:
                status_saude_titulo = "Saudável"
                status_saude_cor = "#059669"
                status_saude_msg = "Todos os clientes até 5% offline"

            st.markdown("**% Total de Câmeras ONLINE GOV**")

            fig_pie = go.Figure(go.Pie(
                labels=["Crítico", "Atenção", "Saudável"],
                values=[n_critico, n_atencao, n_saudavel],
                hole=0.68,
                sort=False,
                direction="clockwise",
                marker=dict(
                    colors=["#dc2626", "#f59e0b", "#14b8a6"],
                    line=dict(color="#ffffff", width=4)
                ),
                textinfo="none",
                hovertemplate="<b>%{label}</b><br>%{value} clientes<br>%{percent}<extra></extra>",
            ))
            fig_pie.update_traces(
                rotation=90,
                pull=[0.055 if n_critico else 0, 0.035 if n_atencao else 0, 0],
            )
            fig_pie.add_annotation(
                text=(
                    f"<span style='font-size:26px;font-weight:800;color:#102a3f;font-family:DM Mono'>{total_clientes}</span>"
                    f"<br><span style='font-size:11px;color:#6b8496;font-family:DM Sans'>clientes</span>"
                    f"<br><span style='font-size:10px;color:#4f6f85;font-family:DM Sans;font-weight:700'>{pct_saudavel_card:.1f}% saudáveis</span>"
                ),
                x=0.5, y=0.5, showarrow=False,
            )
            layout_defaults = {k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]}
            fig_pie.update_layout(
                **layout_defaults,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=250,
                showlegend=False,
                margin=dict(l=4, r=4, t=8, b=4),
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="pie_clientes_faixa_saude_moderno")

            st.markdown(f"""
                <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:-8px">
                    <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:10px;padding:9px 8px;text-align:center">
                        <div style="font-size:10px;color:#0f766e;font-weight:800;text-transform:uppercase">Saudável</div>
                        <div style="font-size:20px;color:#14b8a6;font-family:'DM Mono',monospace;font-weight:800">{n_saudavel}</div>
                        <div style="font-size:10px;color:#60798d">0–5% · {pct_saudavel_card:.1f}%</div>
                    </div>
                    <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:9px 8px;text-align:center">
                        <div style="font-size:10px;color:#b45309;font-weight:800;text-transform:uppercase">Atenção</div>
                        <div style="font-size:20px;color:#f59e0b;font-family:'DM Mono',monospace;font-weight:800">{n_atencao}</div>
                        <div style="font-size:10px;color:#60798d">5–10% · {pct_atencao_card:.1f}%</div>
                    </div>
                    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:9px 8px;text-align:center">
                        <div style="font-size:10px;color:#b91c1c;font-weight:800;text-transform:uppercase">Crítico</div>
                        <div style="font-size:20px;color:#dc2626;font-family:'DM Mono',monospace;font-weight:800">{n_critico}</div>
                        <div style="font-size:10px;color:#60798d">&gt;10% · {pct_critico_card:.1f}%</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

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
                colorscale=[
                    [0.0, "#dff8f3"],
                    [0.10, "#14b8a6"],
                    [0.12, "#fde047"],
                    [0.15, "#f59e0b"],
                    [0.40, "#ef4444"],
                    [1.0, "#b91c1c"],
                ],
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
        # Filtros vetorizados.
        # Agora a aba renderiza todos os clientes do recorte na mesma tela, sem paginação.
        df_clientes_view = df_clientes_ops.copy()
        if "ID" in df_clientes_view.columns:
            df_clientes_view["ID"] = df_clientes_view["ID"].astype(str)
        for col_txt in ["Cliente", "Franqueado", "Status"]:
            if col_txt in df_clientes_view.columns:
                df_clientes_view[col_txt] = df_clientes_view[col_txt].fillna("").astype(str)

        franqueados = ["Todos"] + sorted([
            x for x in df_clientes_view["Franqueado"].dropna().unique().tolist()
            if str(x).strip()
        ])

        if "status_filter" not in st.session_state:
            st.session_state["status_filter"] = "Todos"

        st.caption("Clique no grupo para filtrar os clientes conforme a faixa de % offline.")
        btns = st.columns([1, 1, 1, 1])
        status_anterior = st.session_state.get("status_filter", "Todos")
        if btns[0].button("Todos", key="clientes_status_todos"):
            st.session_state["status_filter"] = "Todos"
        if btns[1].button("Saudável (0-5%)", key="clientes_status_saudavel"):
            st.session_state["status_filter"] = "Saudável (0-5%)"
        if btns[2].button("Atenção (5-10%)", key="clientes_status_atencao"):
            st.session_state["status_filter"] = "Atenção (5-10%)"
        if btns[3].button("Crítico (>10%)", key="clientes_status_critico"):
            st.session_state["status_filter"] = "Crítico (>10%)"

        # Os filtros abaixo ficam dentro de um form para evitar recarregar a aba a cada tecla digitada.
        with st.form("form_filtros_clientes", clear_on_submit=False):
            col_search, col_franq, col_min = st.columns([2, 2, 1])
            with col_search:
                busca_input = st.text_input(
                    "Buscar",
                    value=st.session_state.get("clientes_busca", ""),
                    placeholder="Buscar cliente, franqueado ou ID…",
                )
            with col_franq:
                filtro_franq_input = st.selectbox(
                    "Franqueado",
                    franqueados,
                    index=franqueados.index(st.session_state.get("clientes_franq", "Todos"))
                    if st.session_state.get("clientes_franq", "Todos") in franqueados else 0,
                )
            with col_min:
                min_opcoes = [0, 10, 50, 100, 200]
                min_cameras_input = st.selectbox(
                    "Min. câmeras",
                    min_opcoes,
                    index=min_opcoes.index(st.session_state.get("clientes_min", 0))
                    if st.session_state.get("clientes_min", 0) in min_opcoes else 0,
                )
            aplicar_filtros = st.form_submit_button("Aplicar filtros", use_container_width=True)

        if aplicar_filtros:
            st.session_state["clientes_busca"] = busca_input
            st.session_state["clientes_franq"] = filtro_franq_input
            st.session_state["clientes_min"] = min_cameras_input

        busca = st.session_state.get("clientes_busca", "").strip()
        filtro_franq = st.session_state.get("clientes_franq", "Todos")
        min_cameras = st.session_state.get("clientes_min", 0)
        filtro = st.session_state.get("status_filter", "Todos")

        # Filtro vetorizado: evita loop com df_clientes_ops[df_clientes_ops['ID'] == wl_id].iloc[0].
        mask = pd.Series(True, index=df_clientes_view.index)
        if busca:
            termo = busca.upper()
            texto_busca = (
                df_clientes_view.get("Cliente", pd.Series("", index=df_clientes_view.index)).astype(str).str.upper()
                + " " + df_clientes_view.get("Franqueado", pd.Series("", index=df_clientes_view.index)).astype(str).str.upper()
                + " " + df_clientes_view.get("ID", pd.Series("", index=df_clientes_view.index)).astype(str).str.upper()
            )
            mask &= texto_busca.str.contains(re.escape(termo), na=False)
        if filtro_franq != "Todos":
            mask &= df_clientes_view["Franqueado"].eq(filtro_franq)
        if filtro != "Todos":
            mask &= df_clientes_view["Status"].eq(filtro)
        if min_cameras:
            mask &= pd.to_numeric(df_clientes_view["Total"], errors="coerce").fillna(0).ge(min_cameras)

        df_filtrado = df_clientes_view.loc[mask].copy()
        if not df_filtrado.empty:
            df_filtrado = df_filtrado.sort_values("% Offline", ascending=False).reset_index(drop=True)

        if df_filtrado.empty:
            st.info("Nenhum cliente encontrado com os filtros aplicados.")
        else:
            total_clientes_recorte = len(df_filtrado)

            c_res, c_dl = st.columns([4, 1.4])
            c_res.caption(
                f"{total_clientes_recorte} clientes no recorte · "
                f"{int(df_filtrado['Offline'].sum())} câmeras offline · "
                f"exibindo todos os clientes"
            )

            buf_filtro = io.BytesIO()
            df_filtrado.drop(columns=["_score", "_max_horas"], errors="ignore").to_excel(
                buf_filtro, index=False, engine="openpyxl"
            )
            c_dl.download_button(
                "⬇ Exportar recorte",
                data=buf_filtro.getvalue(),
                file_name=f"clientes_filtrados_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

            ids_f = df_filtrado["ID"].astype(str).tolist()

            for linha in [ids_f[i:i + COLUNAS_PAINEL] for i in range(0, len(ids_f), COLUNAS_PAINEL)]:
                cols = st.columns(COLUNAS_PAINEL)
                for col, wl_id in zip(cols, linha):
                    if wl_id in dados:
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
            nome_cliente_html = escape_html(v.get("cidade_estado") or v["nome_cliente"])
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

                # Botões de exportação do detalhe (XLSX e CSV)
                buf_xlsx = io.BytesIO()
                df_show.to_excel(buf_xlsx, index=True, engine="openpyxl")
                buf_xlsx.seek(0)

                buf_csv = io.StringIO()
                df_show.to_csv(buf_csv, index=True)
                buf_csv.seek(0)

                dl_col1, dl_col2 = st.columns([1,1])
                with dl_col1:
                    st.download_button(
                        label="⬇ Exportar detalhe (.xlsx)",
                        data=buf_xlsx.getvalue(),
                        file_name=f"detalhe_cliente_{wl_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                with dl_col2:
                    st.download_button(
                        label="⬇ Exportar detalhe (.csv)",
                        data=buf_csv.getvalue(),
                        file_name=f"detalhe_cliente_{wl_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

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
                    "Cidade": v.get("cidade_estado") or v.get("cidade") or v["nome_cliente"],
                    "Nome Franqueado": v["nome_empresa"],
                    "ID da Câmera":  row.get(COL_ID_CAM,  "N/D"),
                    "Nome da Câmera":row.get(COL_NOME_CAM,"N/D"),
                    "Última vez Online": row.get(COL_ULT_ATU, pd.NaT),
                    "Observações":   row.get(COL_OBS, ""),
                    "Faixa":         faixa_tempo_dias(horas),
                    "_horas":        horas,
                    "_td":           td,
                })

        if not rows_tempo:
            st.success("🎉 Nenhuma câmera offline no momento!")
        else:
            df_tempo = pd.DataFrame(rows_tempo).sort_values("_horas", ascending=False)

            # KPIs de tempo
            validos       = df_tempo[df_tempo["_horas"] >= 0]
            menos_1d      = (validos["_horas"] < 24).sum()
            entre_1_3d    = ((validos["_horas"] >= 24) & (validos["_horas"] < 72)).sum()
            entre_3_7d    = ((validos["_horas"] >= 72) & (validos["_horas"] < 168)).sum()
            acima_7d      = (validos["_horas"] >= 168).sum()
            nd_count      = (df_tempo["_horas"] < 0).sum()

            k1, k2, k3, k4 = st.columns(4)

            def card_tempo_moderno(titulo, valor, subtitulo, cor):
                return f'''
                <div style="
                    background:#ffffff;
                    border:1px solid #dbe8f2;
                    border-radius:14px;
                    padding:18px 18px 16px;
                    text-align:center;
                    box-shadow:0 10px 26px rgba(16,42,63,.06);
                    position:relative;
                    overflow:hidden;
                    min-height:118px;
                ">
                    <div style="position:absolute;top:0;left:0;right:0;height:4px;background:{cor};"></div>
                    <div style="font-size:10px;color:#60798d;font-weight:800;text-transform:uppercase;letter-spacing:.8px;margin-top:4px">{titulo}</div>
                    <div style="font-size:34px;font-weight:800;color:{cor};font-family:DM Mono,monospace;line-height:1.15;margin-top:10px">{valor}</div>
                    <div style="font-size:11px;color:#60798d;margin-top:6px">{subtitulo}</div>
                </div>
                '''

            k1.markdown(card_tempo_moderno("Menos de 1 dia", menos_1d, "câmeras recentes", "#10b981"), unsafe_allow_html=True)
            k2.markdown(card_tempo_moderno("Entre 1 e 3 dias", entre_1_3d, "câmeras em atenção", "#f59e0b"), unsafe_allow_html=True)
            k3.markdown(card_tempo_moderno("3 a 7 dias", entre_3_7d, "câmeras críticas", "#ef4444"), unsafe_allow_html=True)
            k4.markdown(card_tempo_moderno("Acima de 7 dias", acima_7d, "câmeras mais antigas", "#ef4444"), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if "tempo_offline_categoria" not in st.session_state:
                st.session_state["tempo_offline_categoria"] = "Todas"

            st.markdown("#### Filtrar por faixa de tempo")
            cards = [
                ("Menos de 1 dia", menos_1d),
                ("Entre 1 e 3 dias", entre_1_3d),
                ("3 a 7 dias", entre_3_7d),
                ("Acima de 7 dias", acima_7d),
                ("Sem data", nd_count),
            ]
            cols_cat = st.columns(len(cards))
            for (label, count), col in zip(cards, cols_cat):
                with col:
                    if st.button(f"{label} ({count})", key=f"tempo_cat_{label}"):
                        st.session_state["tempo_offline_categoria"] = label

            selected = st.session_state["tempo_offline_categoria"]
            if selected != "Todas":
                st.markdown(f"**Filtro ativo:** {selected}")
                if st.button("Limpar filtro", key="tempo_cat_clear"):
                    st.session_state["tempo_offline_categoria"] = "Todas"

            col_f1, col_f2 = st.columns([3,1])
            with col_f1:
                busca_t = st.text_input("Buscar", key="busca_tempo",
                                        placeholder="Buscar câmera ou cliente…")
            with col_f2:
                top_n_t = st.selectbox("Exibir", ["Top 50","Top 100","Top 200","Todas"],
                                       key="top_n_tempo")

            df_exib = df_tempo.copy()
            if selected != "Todas":
                if selected == "Sem data":
                    df_exib = df_exib[df_exib["_horas"] < 0]
                elif selected == "Menos de 1 dia":
                    df_exib = df_exib[(df_exib["_horas"] >= 0) & (df_exib["_horas"] < 24)]
                elif selected == "Entre 1 e 3 dias":
                    df_exib = df_exib[(df_exib["_horas"] >= 24) & (df_exib["_horas"] < 72)]
                elif selected == "3 a 7 dias":
                    df_exib = df_exib[(df_exib["_horas"] >= 72) & (df_exib["_horas"] < 168)]
                elif selected == "Acima de 7 dias":
                    df_exib = df_exib[df_exib["_horas"] >= 168]

            if busca_t:
                termo = busca_t.upper()
                df_exib = df_exib[
                    df_exib["Nome da Câmera"].astype(str).str.upper().str.contains(termo) |
                    df_exib["Nome Cliente"].str.upper().str.contains(termo) |
                    df_exib["Nome Franqueado"].astype(str).str.upper().str.contains(termo) |
                    df_exib["ID do Cliente"].astype(str).str.upper().str.contains(termo) |
                    df_exib["ID da Câmera"].astype(str).str.upper().str.contains(termo)
                ]

            lim = {"Top 50":50,"Top 100":100,"Top 200":200}.get(top_n_t, len(df_exib))
            df_exib = df_exib.head(lim)

            if df_exib.empty:
                st.info("Nenhuma câmera encontrada com os filtros aplicados.")
            else:
                # Gráfico executivo — Top 30 por dias offline
                df_graf = df_exib[df_exib["_horas"] >= 0].copy()
                df_graf = df_graf.sort_values("_horas", ascending=False).head(30).copy()
                if not df_graf.empty:
                    df_graf["_dias"] = (df_graf["_horas"] / 24).round(1)
                    df_graf["_rank"] = range(1, len(df_graf) + 1)
                    df_graf["_y"] = list(range(len(df_graf), 0, -1))

                    def _truncar_label_top30(id_camera, cidade, limite=34):
                        id_camera = str(id_camera or "N/D").strip()
                        cidade = str(cidade or "N/D").replace("\n", " ").strip()
                        label = f"{id_camera} · {cidade}"
                        return label if len(label) <= limite else label[:limite - 1].rstrip() + "…"

                    if "Cidade" not in df_graf.columns:
                        df_graf["Cidade"] = df_graf["Nome Cliente"]

                    df_graf["_label_curto"] = df_graf.apply(
                        lambda r: _truncar_label_top30(r["ID da Câmera"], r["Cidade"]), axis=1
                    )
                    df_graf["_tempo_fmt"] = df_graf["_td"].apply(lambda td: fmt_tempo(td))
                    df_graf["_criticidade"] = df_graf["_horas"].apply(
                        lambda h: "Crítico · acima de 7 dias" if h >= 168 else (
                            "Alto · 3 a 7 dias" if h >= 72 else (
                                "Atenção · 1 a 3 dias" if h >= 24 else "Recente · menos de 1 dia"
                            )
                        )
                    )
                    df_graf["_cor"] = df_graf["_horas"].apply(
                        lambda h: "#dc2626" if h >= 168 else (
                            "#ea580c" if h >= 72 else (
                                "#d97706" if h >= 24 else "#059669"
                            )
                        )
                    )

                    st.markdown(f"**Top {len(df_graf)} câmeras — tempo offline em dias**")
                    st.caption("Visão em área por ID da câmera e cidade. Passe o mouse para ver o nome completo da câmera, cliente e tempo detalhado.")

                    max_dias = float(df_graf["_dias"].max()) if not df_graf.empty else 1.0

                    # Visão de área moderna — ranking por tempo offline em dias.
                    # Mantém o gráfico limpo: eixo X por posição no ranking e detalhes completos no hover.
                    fig_t = go.Figure()
                    x_rank = df_graf["_rank"].tolist()
                    y_dias = df_graf["_dias"].tolist()

                    fig_t.add_trace(go.Scatter(
                        x=x_rank,
                        y=y_dias,
                        mode="lines",
                        line=dict(color="#dc2626", width=0),
                        fill="tozeroy",
                        fillcolor="rgba(220, 38, 38, 0.14)",
                        hoverinfo="skip",
                        showlegend=False,
                    ))

                    fig_t.add_trace(go.Scatter(
                        x=x_rank,
                        y=y_dias,
                        mode="lines+markers",
                        line=dict(color="#991b1b", width=3, shape="spline", smoothing=0.65),
                        marker=dict(
                            size=8,
                            color=df_graf["_cor"],
                            line=dict(color="#ffffff", width=1.5),
                        ),
                        customdata=df_graf[["_rank", "ID da Câmera", "Cidade", "Nome da Câmera", "Nome Cliente", "_tempo_fmt", "_criticidade"]].values,
                        hovertemplate=(
                            "<b>ID %{customdata[1]} · %{customdata[2]}</b><br>"
                            "Nome da câmera: %{customdata[3]}<br>"
                            "Cliente: %{customdata[4]}<br>"
                            "Ranking: #%{customdata[0]}<br>"
                            "Tempo offline: <b>%{y:.1f} dias</b><br>"
                            "Tempo detalhado: %{customdata[5]}<br>"
                            "Status: %{customdata[6]}"
                            "<extra></extra>"
                        ),
                        name="Dias offline",
                    ))

                    # Labels fixos removidos para evitar caixas sobrepostas nos pontos.
                    # A identificação completa permanece no eixo X e no hover.

                    layout_padrao_top30 = {
                        k: v for k, v in pdefaults().items()
                        if k not in ["plot_bgcolor", "paper_bgcolor", "margin"]
                    }
                    tickvals = df_graf["_rank"].tolist()
                    ticktext = df_graf["_label_curto"].tolist()
                    fig_t.update_layout(
                        **layout_padrao_top30,
                        height=560,
                        showlegend=False,
                        plot_bgcolor="#ffffff",
                        paper_bgcolor="#ffffff",
                        hovermode="closest",
                        xaxis=dict(
                            title="ID da câmera · Cidade",
                            tickmode="array",
                            tickvals=tickvals,
                            ticktext=ticktext,
                            gridcolor="rgba(148,163,184,.10)",
                            tickfont=dict(color="#64748b", size=9),
                            tickangle=-45,
                            zeroline=False,
                            range=[0.5, len(df_graf) + 0.5],
                        ),
                        yaxis=dict(
                            title="Dias offline",
                            gridcolor="rgba(148,163,184,.16)",
                            tickfont=dict(color="#64748b", size=10),
                            zeroline=False,
                            rangemode="tozero",
                            ticksuffix="d",
                        ),
                        margin=dict(l=70, r=35, t=44, b=145),
                    )
                    st.plotly_chart(fig_t, use_container_width=True, key="top30_cameras_tempo_offline_area_moderno")

                # Tabela detalhada
                st.markdown(f"**Lista detalhada — {len(df_exib)} câmeras**")
                df_tbl_t = df_exib[["Nome Cliente","Nome Franqueado","ID da Câmera","Nome da Câmera","Faixa","Última vez Online","Observações","_horas","_td"]].copy()
                df_tbl_t["Tempo Offline"] = df_tbl_t["_td"].apply(lambda td: fmt_tempo(td) if isinstance(td,timedelta) and td.total_seconds()>=0 else "N/D")
                df_tbl_t["Última vez Online"] = formatar_ultima_atualizacao(df_tbl_t["Última vez Online"])
                df_tbl_t["Criticidade"] = df_tbl_t["_horas"].apply(
                    lambda h: "🔴 Crítico (>7 dias)" if h>=168 else (
                        "🟠 Alto (3–7 dias)" if h>=72 else (
                            "🟡 Atenção (1–3 dias)" if h>=24 else (
                                "🟢 Recente (<1 dia)" if h>=0 else "⚫ Sem data"
                            )
                        )
                    )
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
        st.caption("Escala 0–100% · Verde 0–5% · Amarelo >5–10% · Vermelho >10%")

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
        for xv, lbl in [(5,"5%"),(10,"10%")]:
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

        st.markdown("---")
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


    # ════════════════════════════════════════════
    # ABA 4 — HISTÓRICO & COMPARATIVO
    # ════════════════════════════════════════════
    with tabs[4]:
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
                opcoes = {
                    int(r["id"]): f"{r['label']}  ({r['gravado_em']})"
                    for _, r in df_snaps_filtrado.iterrows()
                }
                datas_snap = {
                    int(r["id"]): r["gravado_em"]
                    for _, r in df_snaps_filtrado.iterrows()
                }
                ids_opcoes = list(opcoes.keys())

                col_a, col_b, col_dl_h = st.columns([2,2,1])
                with col_a:
                    sel_a = st.selectbox(
                        "📅 Snapshot A (base)",
                        ids_opcoes,
                        index=min(1, len(ids_opcoes)-1),
                        format_func=lambda sid: opcoes.get(sid, str(sid)),
                        key="hist_snap_a",
                    )
                with col_b:
                    sel_b = st.selectbox(
                        "📅 Snapshot B (recente)",
                        ids_opcoes,
                        index=0,
                        format_func=lambda sid: opcoes.get(sid, str(sid)),
                        key="hist_snap_b",
                    )

                id_a = int(sel_a)
                id_b = int(sel_b)

                def fmt_dt(s):
                    try: return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                    except: return s

                leg_a = fmt_dt(datas_snap.get(id_a, ""))
                leg_b = fmt_dt(datas_snap.get(id_b, ""))

                # Comparativo histórico real: A e B vêm dos snapshots salvos,
                # mas respeitando o mesmo universo de clientes usado no painel.
                wl_ids_validos_hist = {str(wl).strip() for wl in (dados or {}).keys()}
                df_a = carregar_snapshot(id_a, wl_ids_validos=wl_ids_validos_hist).rename(columns={"offline":"off_a","total":"tot_a","pct_offline":"pct_a","nome_cliente":"nc_a"})
                df_b = carregar_snapshot(id_b, wl_ids_validos=wl_ids_validos_hist).rename(columns={"offline":"off_b","total":"tot_b","pct_offline":"pct_b","nome_cliente":"nc_b"})
                df_comp = pd.merge(df_a, df_b, on="wl_id", how="outer").fillna(0)
                # Usar nome do snapshot B como display
                df_comp["cliente"] = df_comp["nc_b"].where(df_comp["nc_b"] != 0, df_comp["nc_a"])
                df_comp["delta_pct"] = df_comp["pct_b"] - df_comp["pct_a"]
                df_comp["delta_off"] = df_comp["off_b"] - df_comp["off_a"]
                df_comp = df_comp.sort_values("pct_b", ascending=False)

                melhoraram = (df_comp["delta_off"] < 0).sum()
                pioraram   = (df_comp["delta_off"] > 0).sum()
                estaveis   = len(df_comp) - melhoraram - pioraram

                with col_dl_h:
                    st.markdown("<br>", unsafe_allow_html=True)
                    buf_h = io.BytesIO()
                    df_comp.to_excel(buf_h, index=False, engine="openpyxl")
                    st.download_button("⬇ Comparativo", data=buf_h.getvalue(),
                        file_name=f"comparativo_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True)

                total_off_a = int(df_comp["off_a"].sum())
                total_off_b = int(df_comp["off_b"].sum())
                total_cam_a = int(df_comp["tot_a"].sum())
                total_cam_b = int(df_comp["tot_b"].sum())
                pct_a_global = (total_off_a / total_cam_a * 100) if total_cam_a else 0
                pct_b_global = (total_off_b / total_cam_b * 100) if total_cam_b else 0
                delta_off_global = total_off_b - total_off_a
                delta_pct_global = pct_b_global - pct_a_global
                delta_base_global = total_cam_b - total_cam_a
                novos_clientes = int(((df_comp["tot_a"] == 0) & (df_comp["tot_b"] > 0)).sum())
                removidos_clientes = int(((df_comp["tot_a"] > 0) & (df_comp["tot_b"] == 0)).sum())
                clientes_analisados = int(len(df_comp))
                clientes_com_variacao_offline = int((df_comp["delta_off"] != 0).sum())
                clientes_com_variacao_base = int((df_comp["tot_b"] - df_comp["tot_a"] != 0).sum())

                if delta_off_global > 0:
                    resumo_cor = "#dc2626"
                    resumo_status = "Piora operacional"
                    resumo_texto = f"A base teve aumento de {delta_off_global} câmeras offline no período."
                elif delta_off_global < 0:
                    resumo_cor = "#059669"
                    resumo_status = "Melhora operacional"
                    resumo_texto = f"A base reduziu {abs(delta_off_global)} câmeras offline no período."
                else:
                    resumo_cor = "#007ab8"
                    resumo_status = "Operação estável"
                    resumo_texto = "O total de câmeras offline ficou estável no período."

                cor_card_delta = "bad" if delta_off_global > 0 else ("good" if delta_off_global < 0 else "neutral")
                cor_card_pct = "bad" if delta_pct_global > 0 else ("good" if delta_pct_global < 0 else "neutral")

                st.markdown(f"""
                <div class="compare-hero">
                    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap">
                        <div>
                            <div class="compare-title">Painel executivo de comparativo</div>
                            <div class="compare-sub">
                                Comparação real entre os dois snapshots selecionados, mostrando impacto em câmeras offline, percentual da frota e movimento da carteira.
                            </div>
                            <div class="compare-pill">📅 Snapshot A/Base: {leg_a} &nbsp; → &nbsp; Snapshot B/Recente: {leg_b}</div>
                        </div>
                        <div class="compare-status-tag" style="color:{resumo_cor}">{resumo_status}</div>
                    </div>
                    <div class="compare-status-box">
                        <div class="compare-status-text">{resumo_texto}</div>
                        <div class="compare-status-text"><b>Delta:</b> {delta_off_global:+d} offline · {delta_pct_global:+.1f} p.p. · Base {delta_base_global:+d}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="compare-grid">
                    <div class="compare-card neutral">
                        <div class="compare-label">Snapshot A · Base</div>
                        <div class="compare-value">{total_off_a}</div>
                        <div class="compare-note">{pct_a_global:.1f}% da frota · {total_cam_a} câmeras totais</div>
                    </div>
                    <div class="compare-card {cor_card_pct}">
                        <div class="compare-label">Snapshot B · Recente</div>
                        <div class="compare-value" style="color:{resumo_cor}">{total_off_b}</div>
                        <div class="compare-note">{pct_b_global:.1f}% da frota · {total_cam_b} câmeras totais</div>
                    </div>
                    <div class="compare-card {cor_card_delta}">
                        <div class="compare-label">Variação de offline</div>
                        <div class="compare-value" style="color:{resumo_cor}">{delta_off_global:+d}</div>
                        <div class="compare-note">{delta_pct_global:+.1f} p.p. em relação ao snapshot A</div>
                    </div>
                    <div class="compare-card neutral">
                        <div class="compare-label">Carteira analisada</div>
                        <div class="compare-value" style="font-size:30px">{clientes_analisados}</div>
                        <div class="compare-note">{clientes_com_variacao_offline} com variação offline · {melhoraram} melhoraram · {pioraram} pioraram</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Resumo visual da carteira — substitui métricas soltas por cards executivos
                pct_movimento = (clientes_com_variacao_offline / clientes_analisados * 100) if clientes_analisados else 0
                pct_melhoraram = (melhoraram / clientes_analisados * 100) if clientes_analisados else 0
                pct_pioraram = (pioraram / clientes_analisados * 100) if clientes_analisados else 0
                pct_estaveis = (estaveis / clientes_analisados * 100) if clientes_analisados else 0
                pct_base_alterada = (clientes_com_variacao_base / clientes_analisados * 100) if clientes_analisados else 0

                st.markdown("#### Resumo da carteira")
                st.markdown(f"""
                <div class="compare-grid">
                    <div class="compare-card neutral">
                        <div class="compare-label">📈 Movimento</div>
                        <div class="compare-value">{clientes_com_variacao_offline}</div>
                        <div class="compare-note">{pct_movimento:.1f}% da carteira · {clientes_analisados} clientes analisados</div>
                    </div>
                    <div class="compare-card good">
                        <div class="compare-label">🟢 Melhoraram</div>
                        <div class="compare-value" style="color:#059669">{melhoraram}</div>
                        <div class="compare-note">{pct_melhoraram:.1f}% da carteira reduziu offline</div>
                    </div>
                    <div class="compare-card bad">
                        <div class="compare-label">🔴 Pioraram</div>
                        <div class="compare-value" style="color:#dc2626">{pioraram}</div>
                        <div class="compare-note">{pct_pioraram:.1f}% da carteira aumentou offline</div>
                    </div>
                    <div class="compare-card neutral">
                        <div class="compare-label">📊 Estabilidade</div>
                        <div class="compare-value">{pct_estaveis:.1f}%</div>
                        <div class="compare-note">{estaveis} clientes sem alteração offline</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="compare-status-box" style="margin-top:-4px;margin-bottom:16px">
                    <div class="compare-status-text">
                        <b>Carteira analisada:</b> {clientes_analisados} clientes · 
                        <b>Com variação offline:</b> {clientes_com_variacao_offline} · 
                        <b>Estáveis:</b> {estaveis}
                    </div>
                    <div class="compare-status-tag" style="color:#007ab8">Resumo executivo</div>
                </div>
                <div class="compare-grid" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-top:8px">
                    <div class="compare-card neutral">
                        <div class="compare-label">🆕 Novos clientes</div>
                        <div class="compare-value" style="font-size:26px">{novos_clientes}</div>
                        <div class="compare-note">Entraram no snapshot recente</div>
                    </div>
                    <div class="compare-card warn">
                        <div class="compare-label">🚫 Clientes removidos</div>
                        <div class="compare-value" style="font-size:26px">{removidos_clientes}</div>
                        <div class="compare-note">Existiam na base anterior e não aparecem na recente</div>
                    </div>
                    <div class="compare-card neutral">
                        <div class="compare-label">🔄 Base alterada</div>
                        <div class="compare-value" style="font-size:26px">{clientes_com_variacao_base}</div>
                        <div class="compare-note">{pct_base_alterada:.1f}% da carteira teve mudança no total de câmeras</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                df_top_piora = df_comp[df_comp["delta_off"] > 0].sort_values("delta_off", ascending=False).head(10)
                df_top_melhora = df_comp[df_comp["delta_off"] < 0].sort_values("delta_off", ascending=True).head(10)

                st.markdown("#### Maiores variações de câmeras offline")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.caption("🔴 Clientes que mais pioraram")
                    if df_top_piora.empty:
                        st.info("Nenhum cliente piorou neste comparativo.")
                    else:
                        fig_piora = go.Figure(go.Bar(
                            y=df_top_piora["cliente"],
                            x=df_top_piora["delta_off"],
                            orientation="h",
                            marker=dict(color="#dc2626"),
                            text=[f"+{int(v)}" for v in df_top_piora["delta_off"]],
                            textposition="outside",
                            hovertemplate="%{y}<br>+%{x:.0f} câmeras offline<extra></extra>",
                        ))
                        fig_piora.update_layout(
                            **pdefaults(), height=max(320, len(df_top_piora)*34), showlegend=False,
                            xaxis=dict(gridcolor="#dbe8f2", tickfont=dict(color="#6b8496",size=10), zeroline=False),
                            yaxis=dict(autorange="reversed", tickfont=dict(color="#4f6f85",size=10)),
                            margin=dict(l=10, r=60, t=10, b=10),
                        )
                        st.plotly_chart(fig_piora, use_container_width=True, key="hist_top_piora")

                with col_g2:
                    st.caption("🟢 Clientes que mais melhoraram")
                    if df_top_melhora.empty:
                        st.info("Nenhum cliente melhorou neste comparativo.")
                    else:
                        df_m_plot = df_top_melhora.copy()
                        df_m_plot["melhora_abs"] = df_m_plot["delta_off"].abs()
                        fig_melhora = go.Figure(go.Bar(
                            y=df_m_plot["cliente"],
                            x=df_m_plot["melhora_abs"],
                            orientation="h",
                            marker=dict(color="#059669"),
                            text=[f"-{int(v)}" for v in df_m_plot["melhora_abs"]],
                            textposition="outside",
                            hovertemplate="%{y}<br>-%{x:.0f} câmeras offline<extra></extra>",
                        ))
                        fig_melhora.update_layout(
                            **pdefaults(), height=max(320, len(df_m_plot)*34), showlegend=False,
                            xaxis=dict(gridcolor="#dbe8f2", tickfont=dict(color="#6b8496",size=10), zeroline=False),
                            yaxis=dict(autorange="reversed", tickfont=dict(color="#4f6f85",size=10)),
                            margin=dict(l=10, r=60, t=10, b=10),
                        )
                        st.plotly_chart(fig_melhora, use_container_width=True, key="hist_top_melhora")

                cor_snap_base = "#f97316"   # laranja
                cor_snap_atual = "#7c3aed"  # roxo

                st.markdown("#### Visão de área comparativa")
                st.caption("Área horizontal: Snap Antigo/Base em laranja e Snap Novo/Atual em roxo. Todas as cidades/clientes ficam listadas no eixo Y.")
                df_area = df_comp.copy().sort_values("pct_b", ascending=True).reset_index(drop=True)
                df_area["cliente_eixo"] = df_area["cliente"].astype(str)

                max_pct_area = max(15, float(df_area[["pct_a", "pct_b"]].max().max()) + 5)
                altura_area = max(560, 190 + len(df_area) * 34)

                fig_area = go.Figure()

                # Faixas de referência no fundo: saudável, atenção e crítico.
                fig_area.add_vrect(x0=0, x1=5, fillcolor="#059669", opacity=0.05, line_width=0)
                fig_area.add_vrect(x0=5, x1=10, fillcolor="#f59e0b", opacity=0.06, line_width=0)
                fig_area.add_vrect(x0=10, x1=max_pct_area, fillcolor="#dc2626", opacity=0.05, line_width=0)

                # Snap antigo/base em laranja.
                fig_area.add_trace(go.Scatter(
                    name=f"Snap Antigo/Base · {leg_a}",
                    y=df_area["cliente_eixo"],
                    x=df_area["pct_a"],
                    mode="lines+markers",
                    fill="tozerox",
                    line=dict(color=cor_snap_base, width=2.5, shape="spline", smoothing=0.65),
                    marker=dict(color=cor_snap_base, size=6, line=dict(color="#ffffff", width=1)),
                    fillcolor="rgba(249, 115, 22, 0.18)",
                    customdata=df_area[["cliente", "off_a", "tot_a"]],
                    hovertemplate="%{customdata[0]}<br>%{x:.1f}% offline<br>%{customdata[1]:.0f} de %{customdata[2]:.0f} câmeras<extra>Snap Antigo/Base</extra>",
                ))

                # Snap novo/atual em roxo.
                fig_area.add_trace(go.Scatter(
                    name=f"Snap Novo/Atual · {leg_b}",
                    y=df_area["cliente_eixo"],
                    x=df_area["pct_b"],
                    mode="lines+markers",
                    fill="tozerox",
                    line=dict(color=cor_snap_atual, width=2.8, shape="spline", smoothing=0.65),
                    marker=dict(color=cor_snap_atual, size=7, line=dict(color="#ffffff", width=1)),
                    fillcolor="rgba(124, 58, 237, 0.20)",
                    customdata=df_area[["cliente", "off_b", "tot_b"]],
                    hovertemplate="%{customdata[0]}<br>%{x:.1f}% offline<br>%{customdata[1]:.0f} de %{customdata[2]:.0f} câmeras<extra>Snap Novo/Atual</extra>",
                ))

                fig_area.add_vline(x=5, line_color="#059669", line_dash="dot", line_width=1)
                fig_area.add_vline(x=10, line_color="#dc2626", line_dash="dot", line_width=1)

                fig_area.update_layout(
                    **pdefaults(),
                    height=altura_area,
                    xaxis=dict(
                        title="% offline",
                        range=[0, max_pct_area],
                        ticksuffix="%",
                        gridcolor="#dbe8f2",
                        tickfont=dict(color="#6b8496", size=10),
                        zeroline=False,
                    ),
                    yaxis=dict(
                        title="",
                        type="category",
                        categoryorder="array",
                        categoryarray=df_area["cliente_eixo"].tolist(),
                        tickmode="array",
                        tickvals=df_area["cliente_eixo"].tolist(),
                        ticktext=df_area["cliente_eixo"].tolist(),
                        showticklabels=True,
                        automargin=True,
                        tickfont=dict(color="#4f6f85", size=10),
                    ),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                font=dict(size=11, color="#6b8496"), bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=10, r=20, t=45, b=40),
                    hovermode="closest",
                )
                st.caption(f"Renderizando {len(df_area)} cidades/clientes na visão de área.")
                st.plotly_chart(fig_area, use_container_width=True, key="hist_area_pct_cliente")

                st.markdown("#### Comparativo por cliente · câmeras offline")
                st.caption("Comparação da quantidade de câmeras offline por cidade/cliente. 🟧 Snap Antigo/Base · 🟪 Snap Novo/Atual")
                df_comp_graf = df_comp.copy().sort_values("off_b", ascending=True)

                max_offline_cliente = max(1, float(df_comp_graf[["off_a", "off_b"]].max().max()))
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Bar(
                    name=f"Snap Antigo/Base · {leg_a}",
                    y=df_comp_graf["cliente"],
                    x=df_comp_graf["off_a"],
                    orientation="h",
                    marker_color=cor_snap_base,
                    opacity=0.88,
                    customdata=df_comp_graf[["tot_a", "pct_a"]],
                    hovertemplate="%{y}<br>%{x:.0f} câmeras offline<br>%{customdata[1]:.1f}% da frota · %{customdata[0]:.0f} câmeras totais<extra>Snap Antigo/Base</extra>",
                ))
                fig_comp.add_trace(go.Bar(
                    name=f"Snap Novo/Atual · {leg_b}",
                    y=df_comp_graf["cliente"],
                    x=df_comp_graf["off_b"],
                    orientation="h",
                    marker_color=cor_snap_atual,
                    opacity=0.92,
                    customdata=df_comp_graf[["tot_b", "pct_b"]],
                    hovertemplate="%{y}<br>%{x:.0f} câmeras offline<br>%{customdata[1]:.1f}% da frota · %{customdata[0]:.0f} câmeras totais<extra>Snap Novo/Atual</extra>",
                ))
                fig_comp.update_layout(
                    **pdefaults(),
                    barmode="group",
                    height=max(420, len(df_comp_graf) * 42),
                    xaxis=dict(
                        title="Quantidade de câmeras offline",
                        range=[0, max_offline_cliente * 1.18],
                        gridcolor="#dbe8f2",
                        tickfont=dict(color="#6b8496", size=10),
                        zeroline=False,
                    ),
                    yaxis=dict(tickfont=dict(color="#4f6f85", size=10)),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                font=dict(size=11, color="#6b8496"), bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=10, r=20, t=45, b=10),
                )
                st.plotly_chart(fig_comp, use_container_width=True, key="hist_comp_offline_cliente")

                st.markdown("#### Variação líquida de offline")
                st.caption("Valores positivos indicam piora; valores negativos indicam melhora.")
                df_delta = df_comp.copy().sort_values("delta_off", ascending=True)
                cores_d  = ["#dc2626" if d > 0 else ("#059669" if d < 0 else "#64748b") for d in df_delta["delta_off"]]
                fig_d = go.Figure(go.Bar(
                    y=df_delta["cliente"], x=df_delta["delta_off"], orientation="h",
                    marker=dict(color=cores_d, line=dict(width=0)),
                    text=[f"{'+' if d>0 else ''}{int(d)}" for d in df_delta["delta_off"]],
                    textposition="outside", textfont=dict(color="#6b8496",size=10,family="DM Mono"),
                    hovertemplate="%{y}<br>Δ %{x:+.0f} câmeras<extra></extra>",
                ))
                fig_d.add_vline(x=0, line_color="#b9d7e8", line_width=1)
                fig_d.update_layout(
                    **pdefaults(), height=max(420, len(df_delta)*32), showlegend=False,
                    xaxis=dict(gridcolor="#dbe8f2", tickfont=dict(color="#6b8496",size=10), zeroline=False),
                    yaxis=dict(tickfont=dict(color="#4f6f85",size=10)),
                    margin=dict(l=10, r=70, t=20, b=10),
                )
                st.plotly_chart(fig_d, use_container_width=True, key="hist_delta_off_cliente")

                st.markdown("---")
                st.markdown("#### Tabela comparativa detalhada")
                df_tbl = df_comp[["cliente","tot_a","off_a","pct_a","tot_b","off_b","pct_b","delta_pct","delta_off"]].copy()
                df_tbl["Situação"] = df_tbl["delta_off"].apply(lambda v: "Piorou" if v > 0 else ("Melhorou" if v < 0 else "Estável"))
                df_tbl.columns = ["Cliente","Total A","Off A","% A","Total B","Off B","% B","Δ% (pp)","Δ Off","Situação"]
                df_tbl["% A"]     = df_tbl["% A"].apply(lambda x: f"{x:.1f}%")
                df_tbl["% B"]     = df_tbl["% B"].apply(lambda x: f"{x:.1f}%")
                df_tbl["Δ% (pp)"] = df_tbl["Δ% (pp)"].apply(lambda x: f"{'+' if x>0 else ''}{x:.1f}")
                df_tbl["Δ Off"]   = df_tbl["Δ Off"].apply(lambda x: f"{'+' if x>0 else ''}{int(x)}")
                df_tbl = df_tbl.sort_values(["Situação", "Δ Off"], ascending=[True, False]).reset_index(drop=True)
                df_tbl.index += 1
                render_dataframe(df_tbl, height=min(620,(len(df_tbl)+1)*35+3))

                row_b = df_snaps_filtrado[df_snaps_filtrado["id"] == id_b].iloc[0]
                if str(row_b.get("notas","")).strip():
                    st.markdown("---")
                    st.markdown(f"📝 **Observações do snapshot B TESTE:** {row_b['notas']}")

            st.markdown("---")
            with st.expander("🗑️  Gerenciar snapshots gravados"):
                for _, row in df_snaps.iterrows():
                    c1, c2 = st.columns([5,1])
                    notas_txt = f" · *{str(row['notas'])[:60]}…*" if str(row.get("notas","")).strip() else ""
                    c1.markdown(f"**{row['label']}** · `{row['gravado_em']}`{notas_txt}")
                    if c2.button("Excluir", key=f"del_{row['id']}"):
                        deletar_snapshot(row["id"]); st.rerun()


    # ════════════════════════════════════════════
    # ABA 5 — LPRS OFFLINE
    # ════════════════════════════════════════════
    with tabs[5]:
        st.markdown("### LPRs Offline")
        st.caption("Câmeras com status OFFLINE e com 'LPR' no nome da câmera, respeitando a base filtrada do painel.")

        df_lpr_base = df_origem.copy() if df_origem is not None else pd.DataFrame()
        if df_lpr_base.empty:
            st.info("Sem dados carregados para validar LPRs offline.")
        else:
            for col in [COL_WL, COL_EMPRESA, COL_ID_CAM, COL_NOME_CAM, COL_STATUS, COL_ULT_ATU]:
                if col not in df_lpr_base.columns:
                    df_lpr_base[col] = ""

            df_lpr_base[COL_WL] = df_lpr_base[COL_WL].astype(str).str.strip()
            df_lpr_base[COL_STATUS] = df_lpr_base[COL_STATUS].astype(str).str.strip().str.upper()
            df_lpr_base[COL_NOME_CAM] = df_lpr_base[COL_NOME_CAM].astype(str).fillna("")

            # Garante o mesmo universo do dashboard: se existir mapa de clientes, considera apenas esses IDs.
            clientes_map_lpr = carregar_clientes()
            if clientes_map_lpr:
                df_lpr_base = df_lpr_base[df_lpr_base[COL_WL].isin(set(clientes_map_lpr.keys()))].copy()

            mask_lpr = df_lpr_base[COL_NOME_CAM].str.contains("LPR", case=False, na=False)
            mask_off = df_lpr_base[COL_STATUS].eq("OFFLINE")
            df_lprs_total = df_lpr_base[mask_lpr].copy()
            df_lprs_off = df_lpr_base[mask_lpr & mask_off].copy()

            total_lprs = int(len(df_lprs_total))
            total_lprs_off = int(len(df_lprs_off))
            clientes_lpr_total = int(df_lprs_total[COL_WL].nunique()) if not df_lprs_total.empty else 0
            clientes_lpr_off = int(df_lprs_off[COL_WL].nunique()) if not df_lprs_off.empty else 0
            pct_lpr_off = (total_lprs_off / total_lprs * 100) if total_lprs else 0

            if not df_lprs_off.empty:
                df_lprs_off["Cliente"] = df_lprs_off[COL_WL].map(clientes_map_lpr).fillna(df_lprs_off[COL_WL].apply(lambda x: f"ID {x}"))
                df_lprs_off["Franqueado"] = df_lprs_off[COL_EMPRESA].astype(str).replace({"nan": ""}).str.strip()
                df_lprs_off["Última atualização"] = formatar_ultima_atualizacao(df_lprs_off[COL_ULT_ATU])
                df_lprs_off["Tempo offline"] = parse_ultima_atualizacao(df_lprs_off[COL_ULT_ATU]).apply(
                    lambda x: fmt_tempo(datetime.now() - x) if pd.notna(x) else "N/D"
                )

            st.markdown(f"""
            <div class="compare-hero">
                <div class="compare-title">🚘 Radar LPR Offline</div>
                <div class="compare-sub">Validação operacional das câmeras LPR desconectadas na carteira filtrada.</div>
            </div>
            <div class="compare-grid">
                <div class="compare-card neutral">
                    <div class="compare-label">Total de LPRs</div>
                    <div class="compare-value">{total_lprs}</div>
                    <div class="compare-note">câmeras LPR encontradas na base</div>
                </div>
                <div class="compare-card bad">
                    <div class="compare-label">LPRs offline</div>
                    <div class="compare-value" style="color:#dc2626">{total_lprs_off}</div>
                    <div class="compare-note">{pct_lpr_off:.1f}% das LPRs estão offline</div>
                </div>
                <div class="compare-card warn">
                    <div class="compare-label">Clientes afetados</div>
                    <div class="compare-value" style="color:#d97706">{clientes_lpr_off}</div>
                    <div class="compare-note">de {clientes_lpr_total} clientes com LPR</div>
                </div>
                <div class="compare-card good">
                    <div class="compare-label">LPRs online</div>
                    <div class="compare-value" style="color:#059669">{max(total_lprs - total_lprs_off, 0)}</div>
                    <div class="compare-note">câmeras LPR sem alerta offline</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if df_lprs_off.empty:
                st.success("Nenhuma câmera LPR offline encontrada na carteira filtrada.")
            else:
                df_lpr_cli = (
                    df_lprs_off.groupby([COL_WL, "Cliente", "Franqueado"], as_index=False)
                    .agg(lprs_offline=(COL_ID_CAM, "count"))
                    .sort_values("lprs_offline", ascending=False)
                )

                col_g1, col_g2 = st.columns([1.1, 1])
                with col_g1:
                    st.markdown("#### Clientes com mais LPRs offline")
                    top_lpr = df_lpr_cli.head(15).sort_values("lprs_offline", ascending=True)
                    fig_lpr_cli = go.Figure(go.Bar(
                        x=top_lpr["lprs_offline"],
                        y=top_lpr["Cliente"],
                        orientation="h",
                        text=top_lpr["lprs_offline"],
                        textposition="outside",
                        hovertemplate="<b>%{y}</b><br>LPRs offline: %{x}<extra></extra>",
                    ))
                    fig_lpr_cli.update_layout(
                        **pdefaults(),
                        height=max(320, min(620, 40 * len(top_lpr) + 120)),
                        margin=dict(l=10, r=40, t=10, b=30),
                        xaxis=dict(title="LPRs offline", gridcolor="#dbe8f2"),
                        yaxis=dict(title=""),
                    )
                    st.plotly_chart(fig_lpr_cli, use_container_width=True)

                with col_g2:
                    st.markdown("#### Distribuição por franqueado")
                    df_lpr_franq = (
                        df_lprs_off.assign(Franqueado=df_lprs_off["Franqueado"].replace("", "Sem franqueado"))
                        .groupby("Franqueado", as_index=False)
                        .agg(lprs_offline=(COL_ID_CAM, "count"))
                        .sort_values("lprs_offline", ascending=False)
                        .head(12)
                        .sort_values("lprs_offline", ascending=True)
                    )
                    fig_lpr_franq = go.Figure(go.Bar(
                        x=df_lpr_franq["lprs_offline"],
                        y=df_lpr_franq["Franqueado"],
                        orientation="h",
                        text=df_lpr_franq["lprs_offline"],
                        textposition="outside",
                        hovertemplate="<b>%{y}</b><br>LPRs offline: %{x}<extra></extra>",
                    ))
                    fig_lpr_franq.update_layout(
                        **pdefaults(),
                        height=max(320, min(620, 40 * len(df_lpr_franq) + 120)),
                        margin=dict(l=10, r=40, t=10, b=30),
                        xaxis=dict(title="LPRs offline", gridcolor="#dbe8f2"),
                        yaxis=dict(title=""),
                    )
                    st.plotly_chart(fig_lpr_franq, use_container_width=True)

                st.markdown("#### Detalhamento das LPRs offline")
                busca_lpr = st.text_input("Buscar por cliente, franqueado, ID ou nome da câmera", key="busca_lprs_offline")
                df_lpr_lista = df_lprs_off.copy()
                if busca_lpr.strip():
                    termo = busca_lpr.strip().lower()
                    texto_busca = (
                        df_lpr_lista["Cliente"].astype(str) + " " +
                        df_lpr_lista["Franqueado"].astype(str) + " " +
                        df_lpr_lista[COL_ID_CAM].astype(str) + " " +
                        df_lpr_lista[COL_NOME_CAM].astype(str)
                    ).str.lower()
                    df_lpr_lista = df_lpr_lista[texto_busca.str.contains(re.escape(termo), na=False)].copy()

                cols_lpr = ["Cliente", "Franqueado", COL_ID_CAM, COL_NOME_CAM, "Última atualização", "Tempo offline"]
                df_lpr_lista = df_lpr_lista[cols_lpr].rename(columns={
                    COL_ID_CAM: "ID da Câmera",
                    COL_NOME_CAM: "Nome da Câmera",
                }).sort_values(["Cliente", "Nome da Câmera"])
                render_dataframe(df_lpr_lista, height=520)

                csv_lpr = df_lpr_lista.to_csv(index=False, sep=";", encoding="utf-8-sig")
                st.download_button(
                    "📥 Baixar LPRs offline em CSV",
                    data=csv_lpr,
                    file_name=f"lprs_offline_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )


    # ════════════════════════════════════════════
    # ABA 6 — ATUALIZAR BASE ONLINE
    # ════════════════════════════════════════════
    with tabs[6]:
        render_aba_atualizar_base(df_origem)


if __name__ == "__main__":
    main()
