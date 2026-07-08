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
import base64

THEME_OPTIONS = {
    "theme.base": "light",
    "theme.primaryColor": "#7C3AED",
    "theme.backgroundColor": "#FAF7FF",
    "theme.secondaryBackgroundColor": "#ffffff",
    "theme.textColor": "#171126",
    "theme.dataframeHeaderBackgroundColor": "#F3E8FF",
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
    background-color: #FAF7FF !important;
    color: #171126 !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stHeader"]          { background: transparent !important; }
[data-testid="stSidebar"]         { background: #ffffff !important; border-right: 1px solid #E9D5FF !important; }
[data-testid="block-container"]   { padding: 2rem 2.5rem !important; max-width: 1600px; }
section[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }

/* ── Sidebar ── */
.sidebar-logo {
    display: flex; align-items: center; gap: 10px;
    padding: 0 0 1.5rem; border-bottom: 1px solid #E9D5FF; margin-bottom: 1.5rem;
}
.sidebar-logo-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #7C3AED, #A855F7);
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 18px; flex-shrink: 0;
}
.sidebar-logo-img { height: 30px; width: auto; }
.sidebar-logo-text { font-size: 15px; font-weight: 700; color: #171126; line-height: 1; }
.sidebar-logo-sub  { font-size: 10px; color: #7C3AED; margin-top: 2px; }
.nav-section {
    font-size: 10px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; color: #7C3AED; margin: 1.2rem 0 .5rem;
}

/* ── Page header ── */
.page-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #E9D5FF;
}
.page-title { font-size: 24px; font-weight: 700; color: #171126; letter-spacing: -.4px; }
.page-sub   { font-size: 13px; color: #6B5A7A; margin-top: 3px; }
.page-badge {
    font-family: 'DM Mono', monospace; font-size: 11px; color: #6D28D9;
    background: #F3E8FF; padding: 6px 14px; border-radius: 8px;
    border: 1px solid #DDD6FE; white-space: nowrap;
}

/* ── KPI cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 1.5rem; }
.kpi-card {
    background: #ffffff; border: 1px solid #E9D5FF; border-radius: 8px;
    padding: 20px 20px 16px; position: relative; overflow: hidden;
    box-shadow: 0 10px 28px rgba(16, 42, 63, .06);
}
.kpi-card::after {
    content:''; position:absolute; top:0; left:0; right:0; height:3px; border-radius:8px 8px 0 0;
}
.kpi-alert::after   { background: linear-gradient(90deg,#ef4444,#dc2626); }
.kpi-warn::after    { background: linear-gradient(90deg,#f59e0b,#d97706); }
.kpi-ok::after      { background: linear-gradient(90deg,#14b8a6,#059669); }
.kpi-neutral::after { background: linear-gradient(90deg,#7C3AED,#A855F7); }

/* SELETOR DEFINITIVO: Altera textos secundarios do card, exceto o valor principal */
.kpi-card *:not(.kpi-value):not(.val-alert):not(.val-warn):not(.val-ok):not(.val-purple) {
    color: #6B5A7A !important;
    -webkit-text-fill-color: #6B5A7A !important;
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
.val-purple { color: #7C3AED !important; }
            
/* ── Unit cards ── */
.unit-card {
    background: #ffffff; border: 1px solid #E9D5FF; border-radius: 8px;
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
    color:#6D28D9; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.unit-count { font-size:28px; font-weight:700; line-height:1.1; font-family:'DM Mono',monospace; margin-top:4px; margin-bottom:2px; }
.count-red    { color:#f87171; }
.count-yellow { color:#fbbf24; }
.count-ok     { color:#14b8a6; }
.unit-label { font-size:9px; margin-top:2px; margin-bottom:6px; font-weight:500; letter-spacing:.3px; color:#6B5A7A; line-height:1.3; }
.label-red    { color:#ff8e8e; }
.label-yellow { color:#c98500; }
.label-ok     { color:#0f9f8f; }
.prog-track { margin: 6px 0 6px 0; height:3px; background:#E9D5FF; border-radius:99px; overflow:hidden; }
.prog-fill  { height:100%; border-radius:99px; }
.trend-badge {
    display:flex; align-items:center; gap:3px;
    font-size:8px; font-weight:600; padding:2px 6px; border-radius:99px; margin-top:4px; margin-bottom:4px; width: 100%;
}
.trend-up   { background:rgba(248,113,113,.12); color:#f87171; }
.trend-down { background:rgba(20,184,166,.12);  color:#0f9f8f; }
.trend-same { background:rgba(0,136,204,.12); color:#6D28D9; }

/* ── Tabelas ── */
.stTable table { background:transparent !important; font-family:'DM Sans',sans-serif !important;
    font-size:13px !important; width:100% !important; border-collapse:collapse !important; }
.stTable thead th { background:#FAF7FF !important; color:#6D28D9 !important;
    font-size:10px !important; font-weight:600 !important; letter-spacing:.7px !important;
    text-transform:uppercase !important; padding:10px 14px !important; border-bottom:1px solid #E9D5FF !important; }
.stTable tbody tr { background:#ffffff !important; }
.stTable tbody td { padding:10px 14px !important; border-bottom:1px solid #F5F3FF !important; color:#171126 !important; }

/* ── Botões ── */
[data-testid="stDataFrame"] {
    background:#ffffff !important;
    border:1px solid #E9D5FF !important;
    border-radius:8px !important;
    overflow:hidden !important;
    box-shadow:0 8px 22px rgba(16,42,63,.05) !important;
}
[data-testid="stDataFrame"] div,
[data-testid="stDataFrame"] span,
[data-testid="stDataFrame"] button,
[data-testid="stDataFrame"] svg {
    color:#171126 !important;
    -webkit-text-fill-color:#171126 !important;
}
[data-testid="stDataFrame"] canvas,
[data-testid="stDataFrame"] [role="grid"],
[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {
    background:#ffffff !important;
}

.stButton > button {
    width:100% !important; margin-top:8px !important; background:#ffffff !important;
    border:1px solid #C4B5FD !important; color:#6D28D9 !important; border-radius:8px !important;
    font-family:'DM Sans',sans-serif !important; font-size:11px !important;
    font-weight:500 !important; padding:5px 10px !important; transition:all .2s !important;
}
.stButton > button:hover:not(:disabled) {
    background:#F3E8FF !important; border-color:#8B5CF6 !important; color:#5B21B6 !important;
}

/* ── Abas ── */
/* Formularios e filtros */
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label,
[data-testid="stDateInput"] label,
[data-testid="stFileUploader"] label {
    color:#171126 !important;
    -webkit-text-fill-color:#171126 !important;
    font-family:'DM Sans',sans-serif !important;
    font-size:12px !important;
    font-weight:600 !important;
}
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] * {
    color:#171126 !important;
    -webkit-text-fill-color:#171126 !important;
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
    color:#6B5A7A !important;
    -webkit-text-fill-color:#6B5A7A !important;
}
[data-testid="stWidgetLabel"] {
    min-height:22px !important;
}
[data-testid="stTextInput"] [data-baseweb="input"] > div,
[data-testid="stDateInput"] [data-baseweb="input"] > div {
    background:#ffffff !important;
    border:1px solid #C4B5FD !important;
    border-radius:8px !important;
    box-shadow:none !important;
}
[data-testid="stTextInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea {
    background:#ffffff !important;
    border:1px solid #C4B5FD !important;
    border-radius:8px !important;
    color:#171126 !important;
    -webkit-text-fill-color:#171126 !important;
    box-shadow:none !important;
    caret-color:#7C3AED !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stDateInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color:#7C3AED !important;
    box-shadow:0 0 0 1px #7C3AED !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color:#8B7AA3 !important;
    -webkit-text-fill-color:#8B7AA3 !important;
    opacity:1 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background:#ffffff !important;
    border:1px solid #C4B5FD !important;
    border-radius:8px !important;
    box-shadow:none !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
    border-color:#7C3AED !important;
    box-shadow:0 0 0 1px #7C3AED !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stSelectbox"] [data-baseweb="select"] svg,
[data-testid="stSelectbox"] [data-baseweb="select"] div {
    color:#171126 !important;
    -webkit-text-fill-color:#171126 !important;
}
[data-testid="stFileUploader"] section {
    background:#ffffff !important;
    border:1px dashed #C4B5FD !important;
    border-radius:8px !important;
    color:#171126 !important;
}
[data-baseweb="popover"] [role="listbox"] {
    background:#ffffff !important;
    border:1px solid #C4B5FD !important;
    border-radius:8px !important;
    box-shadow:0 16px 36px rgba(16,42,63,.14) !important;
}
[data-baseweb="popover"] [role="option"] {
    background:#ffffff !important;
    color:#171126 !important;
    -webkit-text-fill-color:#171126 !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [aria-selected="true"] {
    background:#F3E8FF !important;
}

[data-testid="stTabs"] [role="tablist"] { border-bottom:1px solid #E9D5FF !important; gap:2px !important; }
[data-testid="stTabs"] [role="tab"] {
    background:transparent !important; border:1px solid transparent !important;
    border-radius:8px 8px 0 0 !important; color:#6B5A7A !important;
    font-family:'DM Sans',sans-serif !important; font-size:13px !important;
    font-weight:500 !important; padding:8px 18px !important; transition:all .2s !important;
}
[data-testid="stTabContent"] { padding-top:1.5rem !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background:#ffffff !important; border:1px solid #E9D5FF !important;
    border-radius:8px !important; margin-bottom:8px !important;
}
[data-testid="stExpander"] summary { font-weight:500 !important; color:#6D28D9 !important; font-size:13px !important; }

/* ── Misc ── */
hr { border-color:#E9D5FF !important; margin:1.5rem 0 !important; }
[data-testid="stAlert"] {
    background:#ffffff !important; border:1px solid #E9D5FF !important;
    border-radius:8px !important; color:#171126 !important;
}

/* ── Download buttons ── */
.stDownloadButton > button {
    background:linear-gradient(135deg,rgba(0,136,204,.12),rgba(0,188,212,.12)) !important;
    border:1px solid rgba(0,136,204,.25) !important; color:#6D28D9 !important;
    border-radius:8px !important; font-size:12px !important; font-weight:600 !important;
    padding:8px 16px !important; width:auto !important; margin-top:0 !important; transition:all .2s !important;
}

/* ── Tempo Offline badges ── */
.tempo-critico  { background:rgba(220,38,38,.10);  color:#dc2626; font-weight:700; padding:2px 8px; border-radius:6px; font-size:11px; }
.tempo-atencao  { background:rgba(217,119,6,.10);  color:#d97706; font-weight:700; padding:2px 8px; border-radius:6px; font-size:11px; }
.tempo-ok       { background:rgba(5,150,105,.10);  color:#059669; font-weight:700; padding:2px 8px; border-radius:6px; font-size:11px; }
.tempo-nd       { background:rgba(107,132,150,.10);color:#8B7AA3; font-weight:600; padding:2px 8px; border-radius:6px; font-size:11px; }

/* Auditoria operacional */
.audit-hero {
    background:#ffffff; border:1px solid #E9D5FF; border-radius:8px;
    padding:18px 20px; margin-bottom:14px; box-shadow:0 10px 24px rgba(16,42,63,.05);
}
.audit-hero-top {
    display:flex; align-items:flex-start; justify-content:space-between; gap:16px; flex-wrap:wrap;
}
.audit-title {
    font-size:22px; font-weight:700; color:#171126; line-height:1.15; margin-bottom:4px;
}
.audit-sub {
    font-size:12px; color:#6B5A7A; max-width:880px; line-height:1.45;
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
    background:#ffffff; border:1px solid #E9D5FF; border-radius:8px; padding:12px 14px;
    min-height:92px; box-shadow:0 8px 18px rgba(16,42,63,.04);
}
.audit-card-label {
    font-size:10px; color:#7C6A91; font-weight:700; text-transform:uppercase; letter-spacing:.6px;
    margin-bottom:7px;
}
.audit-card-value {
    font-family:'DM Mono',monospace; font-size:24px; line-height:1.05; color:#171126; font-weight:700;
}
.audit-card-note { font-size:11px; color:#7C6A91; margin-top:7px; line-height:1.35; }
.audit-riskbar {
    display:grid; grid-template-columns:minmax(0,1fr) auto; gap:12px; align-items:center;
    background:#FCFAFF; border:1px solid #E9D5FF; border-radius:8px; padding:12px 14px; margin-bottom:16px;
}
.audit-risk-track { height:10px; background:#EDE9FE; border-radius:99px; overflow:hidden; }
.audit-risk-fill { height:100%; border-radius:99px; }
.audit-risk-label { font-family:'DM Mono',monospace; font-size:12px; font-weight:700; white-space:nowrap; }
.audit-section-title {
    display:flex; align-items:center; justify-content:space-between; gap:12px; margin:18px 0 8px;
}
.audit-section-title strong { font-size:14px; color:#171126; }
.audit-section-title span { font-size:11px; color:#7C6A91; }
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
    border:1px solid #E9D5FF !important;
    border-radius:8px !important;
    padding:12px 14px !important;
    box-shadow:0 6px 18px rgba(16,42,63,.04) !important;
}
.sidebar-stat-card.offline-card {
    background:#ffffff !important;
    border-color:#E9D5FF !important;
}
.sidebar-stat-card .stat-label {
    font-size:10px;color:#8B7AA3;font-weight:600;text-transform:uppercase;letter-spacing:.7px;
}
.sidebar-stat-card .stat-value {
    font-size:24px;font-weight:700;color:#7C3AED;font-family:'DM Mono',monospace;
}
.sidebar-stat-card.offline-card .stat-value {
    color:#dc2626 !important;
    -webkit-text-fill-color:#dc2626 !important;
}
.sidebar-stat-card .stat-note { font-size:11px;color:#8B7AA3; }

.compare-hero {
    background:linear-gradient(135deg,#ffffff 0%,#FBF7FF 100%);
    border:1px solid #E9D5FF;border-radius:14px;padding:18px 20px;margin:10px 0 16px;
    box-shadow:0 12px 30px rgba(16,42,63,.07);
}
.compare-title { font-size:24px;font-weight:800;color:#171126;letter-spacing:-.4px; }
.compare-sub { font-size:13px;color:#6B5A7A;margin-top:4px;line-height:1.45; }
.compare-pill {
    display:inline-flex;align-items:center;gap:6px;margin-top:10px;
    font-family:'DM Mono',monospace;font-size:11px;color:#6D28D9;background:#F3E8FF;
    border:1px solid #DDD6FE;border-radius:999px;padding:6px 10px;
}
.compare-grid { display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:12px 0 18px; }
.compare-card {
    background:#ffffff !important;border:1px solid #E9D5FF;border-radius:12px;padding:15px 16px;
    box-shadow:0 10px 24px rgba(16,42,63,.055);position:relative;overflow:hidden;
}
.compare-card:before { content:'';position:absolute;left:0;right:0;top:0;height:4px;background:#7C3AED; }
.compare-card.good:before { background:linear-gradient(90deg,#22c55e,#059669); }
.compare-card.bad:before { background:linear-gradient(90deg,#ff1744,#dc2626); }
.compare-card.warn:before { background:linear-gradient(90deg,#facc15,#f59e0b); }
.compare-card.neutral:before { background:linear-gradient(90deg,#7C3AED,#A855F7); }
.compare-label { font-size:10px;color:#8B7AA3;font-weight:800;text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px; }
.compare-value { font-family:'DM Mono',monospace;font-size:30px;font-weight:800;color:#171126;line-height:1; }
.compare-note { font-size:11px;color:#7C6A91;margin-top:8px;line-height:1.35; }
.compare-status-box {
    margin-top:12px;padding:12px 14px;border-radius:10px;background:#ffffff;border:1px solid #E9D5FF;
    display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
}
.compare-status-text { font-size:13px;color:#6B5A7A; }
.compare-status-tag { font-family:'DM Mono',monospace;font-size:11px;font-weight:800;border-radius:999px;padding:6px 10px;border:1px solid currentColor; }
@media(max-width:1100px){ .compare-grid{grid-template-columns:repeat(2,minmax(0,1fr));} }
@media(max-width:700px){ .compare-grid{grid-template-columns:1fr;} }



/* ─────────────────────────────────────────────
   Identidade visual Camerite · Roxo
   Somente aparência: não altera regras, filtros ou funções.
   ───────────────────────────────────────────── */
:root {
    --cam-primary: #7C3AED;
    --cam-primary-dark: #5B21B6;
    --cam-primary-soft: #A855F7;
    --cam-bg: #FAF7FF;
    --cam-card: #FFFFFF;
    --cam-border: #E9D5FF;
    --cam-text: #171126;
    --cam-muted: #6B5A7A;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #FAF7FF 100%) !important;
    border-right: 1px solid var(--cam-border) !important;
}

.sidebar-logo-icon {
    background: linear-gradient(135deg, #5B21B6 0%, #7C3AED 45%, #A855F7 100%) !important;
    box-shadow: 0 10px 24px rgba(124,58,237,.24) !important;
}

.sidebar-logo-text,
.page-title,
.audit-title,
.compare-title {
    color: var(--cam-text) !important;
}

.sidebar-logo-sub,
.nav-section,
.unit-name,
[data-testid="stExpander"] summary {
    color: var(--cam-primary) !important;
    -webkit-text-fill-color: var(--cam-primary) !important;
}

.page-badge,
.compare-pill {
    color: var(--cam-primary-dark) !important;
    background: #F3E8FF !important;
    border-color: #DDD6FE !important;
}

.kpi-card,
.unit-card,
.audit-hero,
.audit-card,
.compare-card,
.sidebar-stat-card,
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stAlert"] {
    border-color: var(--cam-border) !important;
    box-shadow: 0 14px 34px rgba(91,33,182,.08) !important;
}

.kpi-neutral::after,
.compare-card.neutral:before {
    background: linear-gradient(90deg, #5B21B6, #7C3AED, #A855F7) !important;
}

.val-purple,
.sidebar-stat-card .stat-value,
.compare-card.neutral .compare-value {
    color: var(--cam-primary) !important;
    -webkit-text-fill-color: var(--cam-primary) !important;
}

.stButton > button,
.stDownloadButton > button {
    background: linear-gradient(135deg, #7C3AED, #8B5CF6) !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border: 1px solid rgba(124,58,237,.35) !important;
    border-radius: 10px !important;
    box-shadow: 0 10px 22px rgba(124,58,237,.18) !important;
}

.stButton > button:hover:not(:disabled),
.stDownloadButton > button:hover:not(:disabled) {
    background: linear-gradient(135deg, #5B21B6, #7C3AED) !important;
    border-color: #7C3AED !important;
    transform: translateY(-1px);
}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: #F3E8FF !important;
    color: var(--cam-primary-dark) !important;
    border-color: #DDD6FE !important;
    font-weight: 700 !important;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stDateInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
    border-color: var(--cam-primary) !important;
    box-shadow: 0 0 0 1px var(--cam-primary) !important;
}

[data-testid="stTextInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stFileUploader"] section {
    border-color: #C4B5FD !important;
}

[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [aria-selected="true"] {
    background: #F3E8FF !important;
}

.prog-fill,
.audit-risk-fill {
    background: linear-gradient(90deg, #7C3AED, #A855F7) !important;
}

hr,
.page-header {
    border-color: var(--cam-border) !important;
}

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


def agora_sao_paulo() -> datetime:
    """Retorna horário local de São Paulo, mesmo quando o app roda em servidor UTC."""
    return datetime.utcnow() - timedelta(hours=3)


def agora_sao_paulo_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return agora_sao_paulo().strftime(fmt)

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
        return "Sem amostra", "#8B7AA3"
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

    colunas_padrao = [COL_WL, COL_EMPRESA, COL_ID_CAM, COL_NOME_CAM, COL_STATUS, COL_ULT_ATU, COL_OBS, COL_DATA_CAD, COL_PLANO, COL_DATA_INAT]
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
    out["data_cadastro"] = parse_ultima_atualizacao(df_valid[COL_DATA_CAD]).dt.strftime("%Y-%m-%d %H:%M:%S")
    out["data_cadastro"] = out["data_cadastro"].where(out["data_cadastro"].notna(), None)
    out["plano_contratado"] = df_valid[COL_PLANO].astype(str).replace({"nan": ""}).str.strip()
    out["data_inativacao"] = parse_ultima_atualizacao(df_valid[COL_DATA_INAT]).dt.strftime("%Y-%m-%d %H:%M:%S")
    out["data_inativacao"] = out["data_inativacao"].where(out["data_inativacao"].notna(), None)
    out["cidade"] = df_valid[city_col].astype(str).replace({"nan": ""}).str.strip()
    out["estado"] = df_valid[estado_col].astype(str).replace({"nan": ""}).str.strip()
    out["updated_at"] = agora_sao_paulo_str()

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
    out[COL_DATA_CAD] = df["data_cadastro"].astype(str) if "data_cadastro" in df.columns else ""
    out[COL_PLANO] = df["plano_contratado"].astype(str) if "plano_contratado" in df.columns else ""
    out[COL_DATA_INAT] = df["data_inativacao"].astype(str) if "data_inativacao" in df.columns else ""
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


def formatar_data_hora_br(valor) -> str:
    """Formata datas/timestamps para dd/mm/aaaa hh:mm, com fallback seguro."""
    if valor is None:
        return "N/D"
    try:
        if pd.isna(valor):
            return "N/D"
    except Exception:
        pass

    try:
        dt = pd.to_datetime(valor, errors="coerce")
        if pd.isna(dt):
            return "N/D"
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "N/D"


@st.cache_data(ttl=60)
def carregar_ultima_atualizacao_base() -> str:
    """
    Retorna quando a base foi atualizada pela última vez.
    Prioridade:
    1) tabela historico_importacoes.data_importacao;
    2) maior updated_at da tabela cameras_origem;
    3) data de modificação do CSV local.
    """
    if supabase_configurado():
        try:
            resp = requests.get(
                supabase_table_url("historico_importacoes"),
                headers=supabase_headers(),
                params={
                    "select": "data_importacao",
                    "order": "data_importacao.desc",
                    "limit": "1",
                },
                timeout=20,
            )
            if resp.status_code in (200, 206):
                dados = resp.json()
                if dados:
                    data_hist = formatar_data_hora_br(dados[0].get("data_importacao"))
                    if data_hist != "N/D":
                        return data_hist
        except Exception:
            pass

        try:
            resp = requests.get(
                supabase_base_url(),
                headers=supabase_headers(),
                params={
                    "select": "updated_at",
                    "order": "updated_at.desc",
                    "limit": "1",
                },
                timeout=20,
            )
            if resp.status_code in (200, 206):
                dados = resp.json()
                if dados:
                    data_updated = formatar_data_hora_br(dados[0].get("updated_at"))
                    if data_updated != "N/D":
                        return data_updated
        except Exception:
            pass

    if os.path.exists(CSV_GOV):
        return datetime.fromtimestamp(os.path.getmtime(CSV_GOV)).strftime("%d/%m/%Y %H:%M")

    return "N/D"


def registrar_historico_importacao(df_envio: pd.DataFrame, arquivo_nome: str = "upload_streamlit") -> None:
    """Registra um resumo da importação. Se falhar, não bloqueia a atualização principal."""
    try:
        qtd_registros = int(len(df_envio))
        status = df_envio.get("status_camera", pd.Series(dtype=str)).astype(str).str.upper()
        payload = {
            "data_importacao": agora_sao_paulo_str(),
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


def _postgrest_in_filter_text(valores: list[str]) -> str:
    """Monta filtro in.(...) seguro para colunas text do PostgREST/Supabase."""
    limpos = []
    for valor in valores:
        texto = str(valor or "").strip()
        if not texto:
            continue
        # Os whitelabels são numéricos na base atual. Mantemos suporte a letras,
        # hífen e underline caso surja algum código diferente.
        texto = re.sub(r"[^A-Za-z0-9_-]", "", texto)
        if texto:
            limpos.append(texto)
    return "in.(" + ",".join(sorted(set(limpos))) + ")"


def _postgrest_in_filter_int(valores) -> str:
    limpos = []
    for valor in valores:
        try:
            limpos.append(str(int(valor)))
        except Exception:
            continue
    return "in.(" + ",".join(sorted(set(limpos), key=lambda x: int(x))) + ")"


def apagar_cameras_origem_por_whitelabel(ids_whitelabel: list[str], progress_callback=None, total_registros: int = 0) -> tuple[bool, str]:
    """Remove da cameras_origem todos os registros dos whitelabels importados.

    Isso força a base online a refletir exatamente o CSV mais recente.
    Sem este passo, uma câmera que mudou de status ou saiu do arquivo pode
    continuar aparecendo em dashboards caso o upsert não substitua tudo.
    """
    ids = sorted({str(x).strip() for x in ids_whitelabel if str(x).strip()})
    if not ids:
        return True, ""

    tamanho_lote = 100
    for i in range(0, len(ids), tamanho_lote):
        lote_ids = ids[i:i + tamanho_lote]
        filtro = _postgrest_in_filter_text(lote_ids)
        if filtro == "in.()":
            continue
        if progress_callback:
            progress_callback(0, max(total_registros, 1), f"Limpando registros antigos da cameras_origem... lote {i // tamanho_lote + 1}")
        resp = requests.delete(
            supabase_base_url(),
            headers=supabase_headers("return=minimal"),
            params={"id_whitelabel": filtro},
            timeout=60,
        )
        if resp.status_code not in (200, 202, 204):
            return False, f"Erro ao limpar cameras_origem: {resp.status_code} - {resp.text[:500]}"
    return True, ""


def enviar_df_supabase(df_csv: pd.DataFrame, progress_callback=None) -> tuple[bool, str, int]:
    if not supabase_configurado():
        return False, "Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY nos Secrets.", 0

    df_envio = preparar_df_para_supabase(df_csv)
    if df_envio.empty:
        return False, "Nenhuma linha válida para importar. Verifique ID_Whitelabel e ID_da_Camera.", 0

    # Importante: a atualização agora é uma SINCRONIZAÇÃO completa dos clientes
    # presentes no CSV filtrado. Primeiro apaga a cameras_origem desses
    # whitelabels e depois reinsere a foto atual do CSV. Isso elimina registros
    # antigos/órfãos e garante que status como ONLINE/OFFLINE sejam substituídos.
    ids_wl_importados = df_envio["id_whitelabel"].astype(str).str.strip().dropna().unique().tolist()
    qtd_total = len(df_envio)

    try:
        ok_limpeza, msg_limpeza = apagar_cameras_origem_por_whitelabel(
            ids_wl_importados,
            progress_callback=progress_callback,
            total_registros=qtd_total,
        )
        if not ok_limpeza:
            return False, msg_limpeza, 0
    except Exception as e:
        return False, f"Erro ao limpar registros antigos da cameras_origem: {e}", 0

    registros = df_para_registros_json(df_envio)
    total = 0
    tamanho_lote = 1000
    try:
        for i in range(0, qtd_total, tamanho_lote):
            lote = registros[i:i + tamanho_lote]
            if progress_callback:
                progress_callback(total, qtd_total, "Inserindo foto atual do CSV na cameras_origem...")
            resp = requests.post(
                supabase_base_url(),
                # Mantemos upsert como proteção contra duplicidade dentro do lote,
                # embora a tabela já tenha sido limpa para os whitelabels importados.
                headers=supabase_headers("resolution=merge-duplicates,return=minimal"),
                params={"on_conflict": "id_camera"},
                json=lote,
                timeout=60,
            )
            if resp.status_code not in (200, 201, 204):
                return False, f"Erro ao importar para o Supabase: {resp.status_code} - {resp.text[:500]}", total
            total += len(lote)
            if progress_callback:
                progress_callback(total, qtd_total, f"Sincronizando base online... {total}/{qtd_total} registros gravados")
    except Exception as e:
        return False, f"Erro ao enviar dados ao Supabase: {e}", total

    if progress_callback:
        progress_callback(total, qtd_total, "Registrando histórico da importação...")
    registrar_historico_importacao(df_envio)

    # Não limpamos os caches aqui para a barra não chegar em 100% antes da
    # gravação do snapshot e da recarga dos dashboards. Esse controle fica na tela.
    return True, "Base online sincronizada com sucesso.", total


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

create table if not exists public.acoes_clientes (
    id uuid default gen_random_uuid() primary key,
    id_whitelabel text not null,
    nome_cliente text,
    o_que_foi_feito text not null,
    prazo_ajustes date,
    status_acao text default 'Pendente',
    data_criacao timestamp default now(),
    data_atualizacao timestamp default now()
);

create index if not exists idx_acoes_clientes_whitelabel
    on public.acoes_clientes (id_whitelabel);

create index if not exists idx_acoes_clientes_status
    on public.acoes_clientes (status_acao);

-- IMPORTANTE PARA O APP STREAMLIT:
-- Se a tabela estiver com RLS habilitado e o app usa SUPABASE_KEY/ANON_KEY,
-- é necessário liberar as operações abaixo. Sem isso o INSERT retorna 401/403
-- ou "new row violates row-level security policy".
alter table public.acoes_clientes enable row level security;

drop policy if exists "acoes_clientes_select" on public.acoes_clientes;
create policy "acoes_clientes_select"
    on public.acoes_clientes for select
    using (true);

drop policy if exists "acoes_clientes_insert" on public.acoes_clientes;
create policy "acoes_clientes_insert"
    on public.acoes_clientes for insert
    with check (true);

drop policy if exists "acoes_clientes_update" on public.acoes_clientes;
create policy "acoes_clientes_update"
    on public.acoes_clientes for update
    using (true)
    with check (true);
""".strip()


def erro_supabase_amigavel(resp) -> str:
    """Traduz erros comuns do Supabase/PostgREST para uma mensagem prática."""
    texto = ""
    try:
        texto = resp.text or ""
    except Exception:
        texto = ""

    msg_base = f"Supabase retornou {getattr(resp, 'status_code', 'N/D')}"
    detalhe = texto[:700]
    texto_lower = texto.lower()

    if "row-level security" in texto_lower or "rls" in texto_lower or getattr(resp, "status_code", None) in (401, 403):
        return (
            f"{msg_base}. Parece ser bloqueio de permissão/RLS na tabela acoes_clientes. "
            "No Supabase, execute o SQL exibido na aba Atualizar Base/Central de Ações, "
            "ou crie policies de SELECT, INSERT e UPDATE para a chave usada pelo Streamlit. "
            f"Detalhe: {detalhe}"
        )

    if "schema cache" in texto_lower or "pgrst" in texto_lower:
        return (
            f"{msg_base}. O PostgREST ainda não reconheceu a tabela/coluna no cache de schema. "
            "No Supabase, recarregue o schema cache ou aguarde alguns segundos e tente novamente. "
            f"Detalhe: {detalhe}"
        )

    if getattr(resp, "status_code", None) == 404:
        return f"{msg_base}. Tabela acoes_clientes não encontrada/exposta na API. Detalhe: {detalhe}"

    return f"{msg_base}. Detalhe: {detalhe}"


def limpar_cache_acoes() -> None:
    """Limpa caches relacionados à tela depois de inserir/atualizar ações."""
    for func in (carregar_acoes_cliente, carregar_todas_acoes):
        try:
            func.clear()
        except Exception:
            pass

def carregar_acoes_cliente(id_whitelabel: str) -> pd.DataFrame | None:
    """Carrega todas as ações de um cliente do Supabase."""
    if not supabase_configurado():
        return None

    id_whitelabel = str(id_whitelabel or "").strip()
    if not id_whitelabel:
        return pd.DataFrame()

    try:
        resp = requests.get(
            supabase_table_url("acoes_clientes"),
            headers=supabase_headers(),
            params={
                "select": "*",
                "id_whitelabel": f"eq.{id_whitelabel}",
                "order": "data_criacao.desc",
            },
            timeout=20,
        )
        if resp.status_code in (200, 206):
            return pd.DataFrame(resp.json() or [])
        st.error(erro_supabase_amigavel(resp))
        return None
    except Exception as e:
        st.error(f"Erro ao carregar ações do cliente: {e}")
        return None


def salvar_acao_cliente(id_whitelabel: str, nome_cliente: str, o_que_foi_feito: str, prazo_ajustes: str | None = None, status_acao: str = "Pendente") -> tuple[bool, str]:
    """Salva uma nova ação para um cliente no Supabase."""
    if not supabase_configurado():
        return False, "Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY nos Secrets."

    id_whitelabel = str(id_whitelabel or "").strip()
    nome_cliente = str(nome_cliente or "").strip()
    o_que_foi_feito = str(o_que_foi_feito or "").strip()
    status_acao = str(status_acao or "Pendente").strip()

    if not id_whitelabel:
        return False, "Não foi possível identificar o ID_Whitelabel do cliente."
    if not o_que_foi_feito:
        return False, "Descreva a ação antes de registrar."

    payload = {
        "id_whitelabel": id_whitelabel,
        "nome_cliente": nome_cliente,
        "o_que_foi_feito": o_que_foi_feito,
        "status_acao": status_acao,
        "data_atualizacao": agora_sao_paulo_str(),
    }
    if prazo_ajustes:
        payload["prazo_ajustes"] = str(prazo_ajustes)

    try:
        url = supabase_table_url("acoes_clientes")
        headers = supabase_headers("return=minimal")
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=20,
        )
        if resp.status_code in (200, 201, 204):
            limpar_cache_acoes()
            return True, "Ação registrada com sucesso!"

        # Fallback: caso a tabela tenha sido criada manualmente sem alguma coluna opcional,
        # tenta gravar apenas os campos essenciais. Isso evita perder o cadastro por
        # diferença pequena de schema como data_atualizacao ausente.
        if resp.status_code == 400:
            payload_minimo = {
                "id_whitelabel": id_whitelabel,
                "nome_cliente": nome_cliente,
                "o_que_foi_feito": o_que_foi_feito,
                "status_acao": status_acao,
            }
            if prazo_ajustes:
                payload_minimo["prazo_ajustes"] = str(prazo_ajustes)
            resp2 = requests.post(
                url,
                headers=headers,
                json=payload_minimo,
                timeout=20,
            )
            if resp2.status_code in (200, 201, 204):
                limpar_cache_acoes()
                return True, "Ação registrada com sucesso!"
            return False, erro_supabase_amigavel(resp2)

        return False, erro_supabase_amigavel(resp)
    except Exception as e:
        return False, f"Erro ao salvar ação no Supabase: {e}"


def atualizar_status_acao(id_acao: str, novo_status: str) -> tuple[bool, str]:
    """Atualiza o status de uma ação no Supabase."""
    if not supabase_configurado():
        return False, "Supabase não configurado"

    id_acao = str(id_acao or "").strip()
    if not id_acao:
        return False, "ID da ação inválido."

    try:
        resp = requests.patch(
            supabase_table_url("acoes_clientes"),
            headers=supabase_headers("return=minimal"),
            params={"id": f"eq.{id_acao}"},
            json={
                "status_acao": novo_status,
                "data_atualizacao": agora_sao_paulo_str(),
            },
            timeout=20,
        )
        if resp.status_code in (200, 204):
            limpar_cache_acoes()
            return True, "Status atualizado!"
        return False, erro_supabase_amigavel(resp)
    except Exception as e:
        return False, f"Erro ao atualizar ação no Supabase: {e}"




def atualizar_acao_cliente(id_acao: str, o_que_foi_feito: str | None = None, prazo_ajustes: str | None = None, status_acao: str | None = None) -> tuple[bool, str]:
    """Atualiza descrição, prazo e status de uma ação no Supabase."""
    if not supabase_configurado():
        return False, "Supabase não configurado"

    id_acao = str(id_acao or "").strip()
    if not id_acao:
        return False, "ID da ação inválido."

    payload = {"data_atualizacao": agora_sao_paulo_str()}

    if o_que_foi_feito is not None:
        texto = str(o_que_foi_feito or "").strip()
        if not texto:
            return False, "A descrição da ação não pode ficar vazia."
        payload["o_que_foi_feito"] = texto

    if status_acao is not None:
        payload["status_acao"] = str(status_acao or "Pendente").strip()

    # DateInput sem data volta None. Enviamos null para limpar o prazo quando necessário.
    payload["prazo_ajustes"] = prazo_ajustes

    try:
        resp = requests.patch(
            supabase_table_url("acoes_clientes"),
            headers=supabase_headers("return=minimal"),
            params={"id": f"eq.{id_acao}"},
            json=payload,
            timeout=20,
        )
        if resp.status_code in (200, 204):
            limpar_cache_acoes()
            return True, "Ação atualizada com sucesso!"
        return False, erro_supabase_amigavel(resp)
    except Exception as e:
        return False, f"Erro ao atualizar ação no Supabase: {e}"

def carregar_todas_acoes() -> pd.DataFrame | None:
    """Carrega todas as ações de todos os clientes do Supabase."""
    if not supabase_configurado():
        return None

    try:
        resp = requests.get(
            supabase_table_url("acoes_clientes"),
            headers=supabase_headers(),
            params={
                "select": "*",
                "order": "data_criacao.desc",
            },
            timeout=20,
        )
        if resp.status_code in (200, 206):
            return pd.DataFrame(resp.json() or [])
        st.error(erro_supabase_amigavel(resp))
        return None
    except Exception as e:
        st.error(f"Erro ao carregar Central de Ações: {e}")
        return None


def criar_tabela_acoes_se_nao_existir() -> tuple[bool, str]:
    """Verifica se a tabela acoes_clientes está acessível pela API do Supabase."""
    if not supabase_configurado():
        return False, "Supabase não configurado"

    try:
        resp = requests.get(
            supabase_table_url("acoes_clientes"),
            headers=supabase_headers(),
            params={"select": "id", "limit": "1"},
            timeout=20,
        )
        if resp.status_code in (200, 206):
            return True, "Tabela acoes_clientes acessível"
        return False, erro_supabase_amigavel(resp)
    except Exception as e:
        return False, f"Erro ao verificar tabela acoes_clientes: {e}"




def calcular_metricas_cliente_info(info: dict) -> tuple[int, int, float]:
    """Retorna total, offline e % offline usando a mesma fonte dos cards de Clientes."""
    total = int(info.get("total", 0) or 0)
    df_off = info.get("offline")
    try:
        offline = int(len(df_off)) if df_off is not None else int(info.get("offline_count", 0) or 0)
    except Exception:
        offline = int(info.get("offline_count", 0) or 0)
    pct = round((offline / total * 100), 2) if total else 0.0
    return total, offline, pct


def status_operacional_visual(pct: float, offline: int) -> tuple[str, str, str]:
    """Rótulo, cor e emoji para a visão executiva."""
    if offline == 0:
        return "Saudável", "#059669", "🟢"
    if pct > 10:
        return "Crítico", "#dc2626", "🔴"
    if pct > 5:
        return "Atenção", "#d97706", "🟡"
    return "Saudável", "#059669", "🟢"


def status_acao_cor(status: str) -> tuple[str, str, str]:
    texto = str(status or "Pendente").strip()
    normal = normalizar_coluna(texto)
    if normal in ("concluido", "concluida", "resolvido", "resolvida", "finalizado", "finalizada"):
        return texto or "Concluído", "#059669", "✅"
    if normal in ("emandamento", "andamento", "execucao", "emexecucao"):
        return texto, "#7C3AED", "🟣"
    if normal in ("aguardandocliente", "cliente", "aguardando"):
        return texto, "#d97706", "🟠"
    if normal in ("cancelado", "cancelada"):
        return texto, "#8B7AA3", "⚪"
    return texto or "Pendente", "#d97706", "🟡"


def formatar_data_curta(valor) -> str:
    if valor is None or str(valor).strip() in ("", "None", "NaT", "nan"):
        return "N/D"
    try:
        dt = pd.to_datetime(valor, errors="coerce")
        if pd.isna(dt):
            return "N/D"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return "N/D"


def dias_desde_data(valor) -> str:
    try:
        dt = pd.to_datetime(valor, errors="coerce")
        if pd.isna(dt):
            return "Sem data"
        dias = (agora_sao_paulo().date() - dt.date()).days
        if dias <= 0:
            return "Hoje"
        if dias == 1:
            return "há 1 dia"
        return f"há {dias} dias"
    except Exception:
        return "Sem data"


def montar_opcoes_clientes_acoes(dados: dict) -> list[dict]:
    """Monta uma lista leve de clientes para cadastro direto na Central de Ações."""
    opcoes = []
    for wl_id, v in (dados or {}).items():
        total, offline, pct = calcular_metricas_cliente_info(v)
        nome_cliente = str(v.get("cidade_estado") or v.get("nome_cliente") or v.get("nome_empresa") or wl_id).strip()
        nome_empresa = str(v.get("nome_empresa") or "").strip()
        status_label, _, emoji = status_operacional_visual(pct, offline)
        label = f"{emoji} {nome_cliente} · ID {wl_id} · {offline}/{total} offline ({pct:.1f}%)"
        opcoes.append({
            "id_whitelabel": str(wl_id),
            "nome_cliente": nome_cliente,
            "nome_empresa": nome_empresa,
            "total": total,
            "offline": offline,
            "pct": pct,
            "status": status_label,
            "label": label,
            "busca": f"{nome_cliente} {nome_empresa} {wl_id}".upper(),
        })
    return sorted(opcoes, key=lambda x: (-x["pct"], -x["offline"], x["nome_cliente"].upper()))


def render_form_cadastro_acao(dados: dict, prefixo_key: str = "central") -> None:
    """Formulário único e rápido para cadastrar ações sem abrir a aba Clientes."""
    st.markdown("#### ➕ Registrar acompanhamento")
    st.caption("Escolha o cliente, registre a ação e defina status/prazo sem precisar abrir a aba Clientes.")

    opcoes_clientes = montar_opcoes_clientes_acoes(dados)
    if not opcoes_clientes:
        st.warning("Não encontrei clientes carregados para vincular a ação.")
        return

    termo = st.text_input(
        "Buscar cliente",
        placeholder="Digite parte do nome, cidade ou ID_Whitelabel...",
        key=f"{prefixo_key}_busca_cliente_acao",
    ).strip().upper()

    opcoes_filtradas = [o for o in opcoes_clientes if not termo or termo in o["busca"]]
    if not opcoes_filtradas:
        st.warning("Nenhum cliente encontrado com esse filtro.")
        return

    opcoes_filtradas = opcoes_filtradas[:80]
    labels = [o["label"] for o in opcoes_filtradas]

    with st.form(f"{prefixo_key}_form_nova_acao", clear_on_submit=True):
        label_escolhido = st.selectbox("Cliente", labels, key=f"{prefixo_key}_cliente_acao_select")
        cliente_sel = opcoes_filtradas[labels.index(label_escolhido)]
        status_label, status_cor, status_emoji = status_operacional_visual(cliente_sel["pct"], cliente_sel["offline"])
        st.markdown(f"""
        <div style="background:#ffffff;border:1px solid #E9D5FF;border-radius:14px;padding:14px 16px;margin:8px 0 14px;box-shadow:0 10px 24px rgba(91,33,182,.07)">
            <div style="display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap">
                <div>
                    <div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase;letter-spacing:.8px">Cliente selecionado</div>
                    <div style="font-size:18px;color:#171126;font-weight:800;margin-top:4px">{escape_html(cliente_sel['nome_cliente'])}</div>
                    <div style="font-size:12px;color:#6B5A7A;margin-top:2px">ID {escape_html(cliente_sel['id_whitelabel'])} · {escape_html(cliente_sel.get('nome_empresa',''))}</div>
                </div>
                <div style="text-align:right">
                    <div style="font-family:'DM Mono',monospace;font-size:24px;color:{status_cor};font-weight:900">{cliente_sel['pct']:.1f}%</div>
                    <div style="font-size:12px;color:{status_cor};font-weight:800">{status_emoji} {status_label} · {cliente_sel['offline']}/{cliente_sel['total']} offline</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        acao_texto = st.text_area(
            "Ação realizada / ação combinada",
            placeholder="Ex.: Cliente acionado; reunião realizada; técnico abriu chamado; prazo combinado para limpeza/ajuste...",
            height=120,
            key=f"{prefixo_key}_acao_texto",
        )

        col_prazo, col_status = st.columns(2)
        with col_prazo:
            prazo = st.date_input("Prazo para ajuste", value=None, format="DD/MM/YYYY", key=f"{prefixo_key}_prazo_acao")
        with col_status:
            status_acao = st.selectbox(
                "Status da ação",
                ["Pendente", "Em andamento", "Aguardando Cliente", "Concluído", "Cancelado"],
                key=f"{prefixo_key}_status_acao",
            )

        submitted = st.form_submit_button(f"💾 Salvar ação · {prefixo_key}", use_container_width=True)

    if submitted:
        if not str(acao_texto or "").strip():
            st.error("Descreva a ação antes de salvar.")
            return
        prazo_str = prazo.strftime("%Y-%m-%d") if prazo else None
        sucesso, msg = salvar_acao_cliente(
            id_whitelabel=cliente_sel["id_whitelabel"],
            nome_cliente=cliente_sel["nome_cliente"],
            o_que_foi_feito=acao_texto,
            prazo_ajustes=prazo_str,
            status_acao=status_acao,
        )
        if sucesso:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)
            with st.expander("Como resolver no Supabase", expanded=True):
                st.markdown("Verifique se a tabela `acoes_clientes` está exposta na API e se as policies de RLS permitem INSERT/SELECT/UPDATE para a chave usada no Streamlit.")
                st.code(sql_criacao_supabase(), language="sql")


def status_prazo_acao(row) -> str:
    status_txt, _, _ = status_acao_cor(row.get("status_acao", ""))
    if normalizar_coluna(status_txt) in ("concluido", "concluida", "resolvido", "resolvida", "finalizado", "finalizada", "cancelado", "cancelada"):
        return "✅ Concluído" if "conclu" in normalizar_coluna(status_txt) else "⚪ Encerrado"

    prazo_str = row.get("prazo_ajustes")
    if prazo_str is None or str(prazo_str).strip() in ("", "None", "NaT", "nan"):
        return "⏳ Sem prazo"

    try:
        prazo = pd.to_datetime(prazo_str, errors="coerce").date()
        hoje = agora_sao_paulo().date()
        dias_restantes = (prazo - hoje).days
        if dias_restantes < 0:
            return f"🚨 Vencido ({abs(dias_restantes)}d)"
        if dias_restantes == 0:
            return "⚠️ Vence hoje"
        if dias_restantes <= 3:
            return f"⚠️ {dias_restantes}d restantes"
        return f"✓ {dias_restantes}d restantes"
    except Exception:
        return "⏳ Sem prazo"


def preparar_acoes_view(df_todas_acoes: pd.DataFrame | None) -> pd.DataFrame:
    if df_todas_acoes is None or df_todas_acoes.empty:
        return pd.DataFrame()
    df = df_todas_acoes.copy()
    for col in ["id", "id_whitelabel", "nome_cliente", "status_acao", "prazo_ajustes", "o_que_foi_feito", "data_criacao", "data_atualizacao"]:
        if col not in df.columns:
            df[col] = ""
    df["id_whitelabel"] = df["id_whitelabel"].astype(str).str.strip()
    df["_data_sort"] = pd.to_datetime(df["data_atualizacao"].where(df["data_atualizacao"].astype(str).str.strip().ne(""), df["data_criacao"]), errors="coerce")
    df["_data_criacao_sort"] = pd.to_datetime(df["data_criacao"], errors="coerce")
    df["_prazo_sort"] = pd.to_datetime(df["prazo_ajustes"], errors="coerce")
    df["status_prazo_calc"] = df.apply(status_prazo_acao, axis=1)
    return df.sort_values("_data_sort", ascending=False, na_position="last")


def montar_df_clientes_central_acoes(dados: dict, df_todas_acoes: pd.DataFrame | None = None) -> pd.DataFrame:
    """Base executiva por cliente: 1 linha por cliente, com a última ação como resumo."""
    df_acoes = preparar_acoes_view(df_todas_acoes)
    ultimas = {}
    pendencias = {}
    vencidos = {}

    if not df_acoes.empty:
        df_ord = df_acoes.sort_values("_data_sort", ascending=False, na_position="last")
        for wl, g in df_ord.groupby("id_whitelabel", sort=False):
            if not str(wl).strip():
                continue
            ultimas[str(wl)] = g.iloc[0].to_dict()
            pend = g[~g["status_acao"].astype(str).map(lambda x: normalizar_coluna(x) in ("concluido", "concluida", "resolvido", "resolvida", "cancelado", "cancelada"))]
            pendencias[str(wl)] = len(pend)
            vencidos[str(wl)] = int(pend["status_prazo_calc"].astype(str).str.contains("Vencido", na=False).sum()) if not pend.empty else 0

    rows = []
    for wl_id, info in (dados or {}).items():
        wl = str(wl_id).strip()
        total, offline, pct = calcular_metricas_cliente_info(info)
        nome_cliente = str(info.get("cidade_estado") or info.get("nome_cliente") or f"ID {wl}").strip()
        nome_empresa = str(info.get("nome_empresa") or "").strip()
        op_label, op_cor, op_emoji = status_operacional_visual(pct, offline)
        ultima = ultimas.get(wl, {})
        status_ult, status_cor, status_emoji = status_acao_cor(ultima.get("status_acao", "Sem ação")) if ultima else ("Sem ação", "#8B7AA3", "⚪")
        ultima_acao = str(ultima.get("o_que_foi_feito", "") or "").strip() if ultima else ""
        rows.append({
            "ID": wl,
            "Cliente": nome_cliente,
            "Franqueado": nome_empresa,
            "Total": total,
            "Offline": offline,
            "% Offline": pct,
            "Situação": f"{op_emoji} {op_label}",
            "Situação Cor": op_cor,
            "Última ação": ultima_acao[:160] if ultima_acao else "Sem ação registrada",
            "Data última ação": formatar_data_curta(ultima.get("data_atualizacao") or ultima.get("data_criacao")) if ultima else "N/D",
            "Dias sem atualização": dias_desde_data(ultima.get("data_atualizacao") or ultima.get("data_criacao")) if ultima else "Sem acompanhamento",
            "Status da ação": f"{status_emoji} {status_ult}",
            "Status Cor": status_cor,
            "Prazo": formatar_data_curta(ultima.get("prazo_ajustes")) if ultima else "N/D",
            "Prazo Status": ultima.get("status_prazo_calc", "Sem ação") if ultima else "Sem ação",
            "Pendências": int(pendencias.get(wl, 0) or 0),
            "Vencidas": int(vencidos.get(wl, 0) or 0),
            "Tem ação": bool(ultima),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()
    return df.sort_values(["% Offline", "Offline", "Cliente"], ascending=[False, False, True]).reset_index(drop=True)


def card_executivo(titulo: str, valor: str, subtitulo: str, cor: str = "#7C3AED", icone: str = "📌") -> None:
    st.markdown(f"""
    <div style="background:#ffffff;border:1px solid #E9D5FF;border-radius:16px;padding:18px 18px 16px;box-shadow:0 12px 30px rgba(91,33,182,.08);height:132px;position:relative;overflow:hidden">
        <div style="position:absolute;top:0;left:0;right:0;height:5px;background:{cor}"></div>
        <div style="font-size:11px;color:#8B7AA3;font-weight:900;text-transform:uppercase;letter-spacing:.8px">{icone} {escape_html(titulo)}</div>
        <div style="font-family:'DM Mono',monospace;font-size:36px;line-height:1;color:{cor};font-weight:900;margin-top:12px">{escape_html(str(valor))}</div>
        <div style="font-size:12px;color:#6B5A7A;margin-top:10px;line-height:1.35">{escape_html(subtitulo)}</div>
    </div>
    """, unsafe_allow_html=True)


def render_dashboard_acoes(df_todas_acoes: pd.DataFrame, dados: dict) -> None:
    """Dashboard executivo orientado a clientes, não a quantidade de ações."""
    df_clientes = montar_df_clientes_central_acoes(dados, df_todas_acoes)
    if df_clientes.empty:
        st.info("Nenhum cliente carregado.")
        return

    criticos = df_clientes[df_clientes["% Offline"] > 10].copy()
    atencao = df_clientes[(df_clientes["% Offline"] > 5) & (df_clientes["% Offline"] <= 10)].copy()
    precisa_acomp = df_clientes[(df_clientes["% Offline"] > 5) & (~df_clientes["Tem ação"])].copy()
    vencidos = df_clientes[df_clientes["Vencidas"] > 0].copy()
    acompanhamento = df_clientes[(df_clientes["% Offline"] > 5) & (df_clientes["Tem ação"])].copy()

    st.markdown("#### 📊 Resumo executivo")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card_executivo("Clientes críticos", str(len(criticos)), "Acima de 10% offline", "#dc2626", "🔴")
    with c2:
        card_executivo("Clientes em atenção", str(len(atencao)), "Entre 5% e 10% offline", "#d97706", "🟡")
    with c3:
        card_executivo("Sem acompanhamento", str(len(precisa_acomp)), "Críticos/atenção sem ação", "#7C3AED", "📌")
    with c4:
        card_executivo("Prazo vencido", str(len(vencidos)), "Clientes com pendência vencida", "#ef4444", "🚨")

    st.markdown("#### 🏢 Clientes para reunião")
    st.caption("Uma linha por cliente, focando situação atual, última ação e status do acompanhamento.")
    prioridade = df_clientes[(df_clientes["% Offline"] > 5) | (df_clientes["Tem ação"])].copy()
    prioridade = prioridade.sort_values(["% Offline", "Vencidas", "Pendências"], ascending=[False, False, False]).head(20)
    if prioridade.empty:
        st.success("Nenhum cliente crítico/em atenção ou com ação registrada no momento.")
    else:
        show = prioridade[["Cliente", "Offline", "% Offline", "Situação", "Última ação", "Data última ação", "Status da ação", "Prazo Status"]].copy()
        show["% Offline"] = show["% Offline"].map(lambda v: f"{float(v):.1f}%")
        render_dataframe(show, height=min(650, (len(show)+1)*42 + 3))

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("#### 🚨 Sem acompanhamento")
        if precisa_acomp.empty:
            st.success("Todos os clientes em atenção/críticos têm acompanhamento registrado.")
        else:
            aux = precisa_acomp[["Cliente", "Offline", "% Offline", "Situação"]].head(12).copy()
            aux["% Offline"] = aux["% Offline"].map(lambda v: f"{float(v):.1f}%")
            render_dataframe(aux, height=min(430, (len(aux)+1)*38 + 3))
    with col_b:
        st.markdown("#### ⏱️ Prazos vencidos")
        if vencidos.empty:
            st.success("Nenhum cliente com prazo vencido.")
        else:
            aux = vencidos[["Cliente", "% Offline", "Última ação", "Prazo", "Prazo Status"]].head(12).copy()
            aux["% Offline"] = aux["% Offline"].map(lambda v: f"{float(v):.1f}%")
            render_dataframe(aux, height=min(430, (len(aux)+1)*38 + 3))


def render_cards_reuniao_clientes(df_clientes: pd.DataFrame) -> None:
    if df_clientes.empty:
        st.info("Nenhum cliente para exibir.")
        return
    for _, row in df_clientes.iterrows():
        pct = float(row.get("% Offline", 0) or 0)
        situacao = str(row.get("Situação", ""))
        cor = row.get("Situação Cor", "#7C3AED")
        status = str(row.get("Status da ação", "Sem ação"))
        status_cor = row.get("Status Cor", "#8B7AA3")
        ultima = str(row.get("Última ação", "Sem ação registrada") or "Sem ação registrada")
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#ffffff 0%,#FBF7FF 100%);border:1px solid #E9D5FF;border-left:6px solid {cor};border-radius:18px;padding:18px 20px;margin:0 0 14px;box-shadow:0 14px 34px rgba(91,33,182,.09)">
            <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap">
                <div style="min-width:280px;flex:1">
                    <div style="font-size:11px;color:#8B7AA3;font-weight:900;text-transform:uppercase;letter-spacing:.8px">Cliente</div>
                    <div style="font-size:21px;color:#171126;font-weight:900;margin-top:3px">{escape_html(row.get('Cliente','N/D'))}</div>
                    <div style="font-size:12px;color:#6B5A7A;margin-top:3px">ID {escape_html(row.get('ID',''))} · {escape_html(row.get('Franqueado',''))}</div>
                </div>
                <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end">
                    <div style="background:#ffffff;border:1px solid #E9D5FF;border-radius:12px;padding:10px 14px;text-align:center;min-width:116px">
                        <div style="font-size:10px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Offline</div>
                        <div style="font-family:'DM Mono',monospace;font-size:24px;color:{cor};font-weight:900">{pct:.1f}%</div>
                        <div style="font-size:11px;color:#6B5A7A">{int(row.get('Offline',0))}/{int(row.get('Total',0))} câmeras</div>
                    </div>
                    <div style="background:#ffffff;border:1px solid #E9D5FF;border-radius:12px;padding:10px 14px;text-align:center;min-width:140px">
                        <div style="font-size:10px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Situação</div>
                        <div style="font-size:13px;color:{cor};font-weight:900;margin-top:8px">{escape_html(situacao)}</div>
                    </div>
                    <div style="background:#ffffff;border:1px solid #E9D5FF;border-radius:12px;padding:10px 14px;text-align:center;min-width:160px">
                        <div style="font-size:10px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Acompanhamento</div>
                        <div style="font-size:13px;color:{status_cor};font-weight:900;margin-top:8px">{escape_html(status)}</div>
                    </div>
                </div>
            </div>
            <div style="margin-top:14px;background:#ffffff;border:1px solid #F1E8FF;border-radius:12px;padding:13px 14px">
                <div style="font-size:10px;color:#8B7AA3;font-weight:900;text-transform:uppercase;letter-spacing:.7px">Última ação</div>
                <div style="font-size:14px;color:#171126;line-height:1.45;margin-top:5px">{escape_html(ultima)}</div>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">
                <span style="background:#F3E8FF;color:#5B21B6;border:1px solid #DDD6FE;border-radius:999px;padding:6px 10px;font-size:11px;font-weight:800">Data: {escape_html(row.get('Data última ação','N/D'))}</span>
                <span style="background:#F3E8FF;color:#5B21B6;border:1px solid #DDD6FE;border-radius:999px;padding:6px 10px;font-size:11px;font-weight:800">{escape_html(row.get('Dias sem atualização',''))}</span>
                <span style="background:#F3E8FF;color:#5B21B6;border:1px solid #DDD6FE;border-radius:999px;padding:6px 10px;font-size:11px;font-weight:800">Prazo: {escape_html(row.get('Prazo Status','N/D'))}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_lista_acoes(df_todas_acoes: pd.DataFrame, dados: dict | None = None) -> None:
    """Visão moderna das ações: apresentação por cliente + histórico operacional."""
    df_acoes = preparar_acoes_view(df_todas_acoes)
    if df_acoes.empty:
        st.info("Nenhuma ação registrada ainda. Cadastre a primeira na sub-aba “Cadastrar ação”.")
        return

    tab_reuniao, tab_historico = st.tabs(["🎯 Visão para reunião", "📚 Histórico de ações"])

    with tab_reuniao:
        df_clientes = montar_df_clientes_central_acoes(dados or {}, df_todas_acoes) if dados is not None else pd.DataFrame()
        if df_clientes.empty:
            st.info("Não foi possível cruzar ações com a base de clientes carregada.")
        else:
            st.markdown("#### 🎯 Acompanhamento por cliente")
            st.caption("Visual pronto para apresentar: foco no cliente, % offline, última ação, status e prazo.")
            col_f1, col_f2, col_f3 = st.columns([1.1, 1.1, 2])
            with col_f1:
                filtro_situacao = st.selectbox("Situação", ["Críticos e atenção", "Todos com ação", "Críticos", "Atenção", "Sem acompanhamento", "Prazo vencido"], key="filtro_reuniao_situacao_v4")
            with col_f2:
                limite = st.selectbox("Quantidade", [10, 15, 25, 50], index=1, key="filtro_reuniao_limite_v4")
            with col_f3:
                termo = st.text_input("Buscar", placeholder="Cliente, franqueado ou ID...", key="filtro_reuniao_busca_v4").strip().upper()

            df_view = df_clientes.copy()
            if filtro_situacao == "Críticos e atenção":
                df_view = df_view[df_view["% Offline"] > 5]
            elif filtro_situacao == "Todos com ação":
                df_view = df_view[df_view["Tem ação"]]
            elif filtro_situacao == "Críticos":
                df_view = df_view[df_view["% Offline"] > 10]
            elif filtro_situacao == "Atenção":
                df_view = df_view[(df_view["% Offline"] > 5) & (df_view["% Offline"] <= 10)]
            elif filtro_situacao == "Sem acompanhamento":
                df_view = df_view[(df_view["% Offline"] > 5) & (~df_view["Tem ação"])]
            elif filtro_situacao == "Prazo vencido":
                df_view = df_view[df_view["Vencidas"] > 0]

            if termo:
                busca = (df_view["Cliente"].astype(str) + " " + df_view["Franqueado"].astype(str) + " " + df_view["ID"].astype(str)).str.upper()
                df_view = df_view[busca.str.contains(re.escape(termo), na=False)].copy()

            df_view = df_view.sort_values(["% Offline", "Vencidas", "Pendências"], ascending=[False, False, False]).head(int(limite))
            render_cards_reuniao_clientes(df_view)

    with tab_historico:
        st.markdown("#### 📚 Histórico operacional")
        col_filtro1, col_filtro2, col_filtro3 = st.columns([1.2, 2, 1.4])
        with col_filtro1:
            statuses = sorted(set([str(x or "Pendente") for x in df_acoes["status_acao"].dropna().tolist()]))
            filtro_status = st.selectbox("Status", ["Todos"] + statuses, key="central_acoes_status_v4")
        with col_filtro2:
            filtro_cliente = st.text_input("Filtrar ações", placeholder="Cliente, ID ou texto da ação...", key="central_acoes_cliente_v4")
        with col_filtro3:
            ordem = st.selectbox("Ordenar por", ["Mais recente", "Prazo mais próximo", "Cliente A-Z"], key="central_acoes_ordem_v4")

        mask = pd.Series(True, index=df_acoes.index)
        if filtro_status != "Todos":
            mask &= df_acoes["status_acao"].astype(str).eq(filtro_status)
        if filtro_cliente.strip():
            termo = filtro_cliente.upper().strip()
            campo_busca = (df_acoes["nome_cliente"].astype(str) + " " + df_acoes["id_whitelabel"].astype(str) + " " + df_acoes["o_que_foi_feito"].astype(str)).str.upper()
            mask &= campo_busca.str.contains(re.escape(termo), na=False)

        df_filtrado = df_acoes[mask].copy()
        if ordem == "Mais recente":
            df_filtrado = df_filtrado.sort_values("_data_sort", ascending=False, na_position="last")
        elif ordem == "Prazo mais próximo":
            df_filtrado = df_filtrado.sort_values("_prazo_sort", na_position="last")
        else:
            df_filtrado = df_filtrado.sort_values("nome_cliente", ascending=True)

        if df_filtrado.empty:
            st.info("Nenhuma ação encontrada com os filtros aplicados.")
            return

        for _, acao in df_filtrado.iterrows():
            status_texto, status_cor, status_emoji = status_acao_cor(acao.get("status_acao", "Pendente"))
            status_prazo = str(acao.get("status_prazo_calc", "⏳ Sem prazo"))
            if "Vencido" in status_prazo:
                cor_borda, cor_bg = "#ef4444", "#fff7f7"
            elif "Concluído" in status_prazo or "Encerrado" in status_prazo:
                cor_borda, cor_bg = "#14b8a6", "#f0fdfa"
            elif "⚠️" in status_prazo:
                cor_borda, cor_bg = "#f59e0b", "#fffbeb"
            else:
                cor_borda, cor_bg = "#7C3AED", "#fbf7ff"

            acao_id = str(acao.get("id") or uuid.uuid4())
            st.markdown(f"""
            <div style="background:{cor_bg};border:1px solid #E9D5FF;border-left:5px solid {cor_borda};border-radius:16px;padding:16px 18px;margin-bottom:8px;box-shadow:0 10px 24px rgba(91,33,182,.07)">
                <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap">
                    <div>
                        <div style="font-size:11px;color:#8B7AA3;font-weight:900;text-transform:uppercase;letter-spacing:.7px">🏢 Cliente</div>
                        <div style="font-size:17px;color:#171126;font-weight:900;margin-top:3px">{escape_html(acao.get('nome_cliente', 'N/D'))}</div>
                        <div style="font-size:12px;color:#6B5A7A;margin-top:3px">ID {escape_html(acao.get('id_whitelabel',''))}</div>
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end">
                        <span style="background:#ffffff;color:{status_cor};border:1px solid #E9D5FF;border-radius:999px;padding:7px 10px;font-size:11px;font-weight:900">{status_emoji} {escape_html(status_texto)}</span>
                        <span style="background:#ffffff;color:{cor_borda};border:1px solid #E9D5FF;border-radius:999px;padding:7px 10px;font-size:11px;font-weight:900">{escape_html(status_prazo)}</span>
                    </div>
                </div>
                <div style="background:#ffffff;border:1px solid #F1E8FF;border-radius:12px;padding:12px 13px;margin-top:13px;color:#171126;font-size:14px;line-height:1.45">{escape_html(acao.get('o_que_foi_feito', ''))}</div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">
                    <span style="background:#F3E8FF;color:#5B21B6;border:1px solid #DDD6FE;border-radius:999px;padding:6px 10px;font-size:11px;font-weight:800">Criada: {escape_html(formatar_data_curta(acao.get('data_criacao')))}</span>
                    <span style="background:#F3E8FF;color:#5B21B6;border:1px solid #DDD6FE;border-radius:999px;padding:6px 10px;font-size:11px;font-weight:800">Atualizada: {escape_html(formatar_data_curta(acao.get('data_atualizacao') or acao.get('data_criacao')))}</span>
                    <span style="background:#F3E8FF;color:#5B21B6;border:1px solid #DDD6FE;border-radius:999px;padding:6px 10px;font-size:11px;font-weight:800">Prazo: {escape_html(formatar_data_curta(acao.get('prazo_ajustes')))}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("🛠️ Manutenção / atualizar esta ação", expanded=False):
                opcoes_status = ["Pendente", "Em andamento", "Aguardando Cliente", "Concluído", "Cancelado"]
                idx = opcoes_status.index(status_texto) if status_texto in opcoes_status else 0
                prazo_atual = pd.to_datetime(acao.get("prazo_ajustes"), errors="coerce")
                prazo_valor = prazo_atual.date() if pd.notna(prazo_atual) else None

                with st.form(f"form_editar_acao_{acao_id}"):
                    novo_texto = st.text_area(
                        "Descrição da ação",
                        value=str(acao.get("o_que_foi_feito") or ""),
                        height=120,
                        key=f"edit_texto_{acao_id}",
                    )
                    col_edit_1, col_edit_2 = st.columns(2)
                    with col_edit_1:
                        novo_prazo = st.date_input(
                            "Prazo",
                            value=(prazo_valor or agora_sao_paulo().date()),
                            format="DD/MM/YYYY",
                            key=f"edit_prazo_{acao_id}",
                        )
                    with col_edit_2:
                        novo_status = st.selectbox(
                            "Status",
                            opcoes_status,
                            index=idx,
                            key=f"edit_status_{acao_id}",
                        )
                    salvar_edicao = st.form_submit_button(f"💾 Atualizar ação · {acao_id}", use_container_width=True)

                if salvar_edicao:
                    prazo_str = novo_prazo.strftime("%Y-%m-%d") if novo_prazo else None
                    sucesso, msg = atualizar_acao_cliente(
                        id_acao=acao.get("id", ""),
                        o_que_foi_feito=novo_texto,
                        prazo_ajustes=prazo_str,
                        status_acao=novo_status,
                    )
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)



def render_manutencao_acoes(df_todas_acoes: pd.DataFrame | None) -> None:
    """Tela simples e estável para manutenção de ações já cadastradas."""
    st.markdown("#### 🛠️ Manutenção de ações")
    st.caption("Use esta área para atualizar status, prazo ou descrição sem abrir o Supabase.")

    df_acoes = preparar_acoes_view(df_todas_acoes)
    if df_acoes.empty:
        st.info("Nenhuma ação cadastrada para manutenção.")
        return

    col_busca, col_status = st.columns([2, 1])
    with col_busca:
        termo = st.text_input(
            "Buscar ação",
            placeholder="Digite cliente, ID_Whitelabel ou parte da ação...",
            key="manut_acoes_busca_v1",
        ).strip().upper()
    with col_status:
        statuses = sorted(set([str(x or "Pendente") for x in df_acoes["status_acao"].dropna().tolist()]))
        filtro_status = st.selectbox("Status", ["Todos"] + statuses, key="manut_acoes_status_v1")

    df_filtrado = df_acoes.copy()
    if filtro_status != "Todos":
        df_filtrado = df_filtrado[df_filtrado["status_acao"].astype(str).eq(filtro_status)].copy()
    if termo:
        campo_busca = (
            df_filtrado["nome_cliente"].astype(str) + " " +
            df_filtrado["id_whitelabel"].astype(str) + " " +
            df_filtrado["o_que_foi_feito"].astype(str)
        ).str.upper()
        df_filtrado = df_filtrado[campo_busca.str.contains(re.escape(termo), na=False)].copy()

    df_filtrado = df_filtrado.sort_values("_data_sort", ascending=False, na_position="last").head(100)
    if df_filtrado.empty:
        st.warning("Nenhuma ação encontrada com esse filtro.")
        return

    def montar_label(row) -> str:
        data = formatar_data_curta(row.get("data_criacao"))
        cliente = str(row.get("nome_cliente") or "Cliente sem nome")[:70]
        status = str(row.get("status_acao") or "Pendente")
        texto = str(row.get("o_que_foi_feito") or "")[:80].replace("\n", " ")
        return f"{data} · {cliente} · {status} · {texto}"

    labels = [montar_label(row) for _, row in df_filtrado.iterrows()]
    label_sel = st.selectbox("Selecione a ação para atualizar", labels, key="manut_acoes_select_v1")
    acao = df_filtrado.iloc[labels.index(label_sel)]
    acao_id = str(acao.get("id") or "").strip()

    if not acao_id:
        st.error("Esta ação está sem ID. Não consigo atualizar com segurança.")
        return

    status_texto, status_cor, status_emoji = status_acao_cor(acao.get("status_acao", "Pendente"))
    st.markdown(f"""
    <div style="background:#ffffff;border:1px solid #E9D5FF;border-radius:16px;padding:16px 18px;margin:12px 0 16px;box-shadow:0 10px 24px rgba(91,33,182,.07)">
        <div style="font-size:11px;color:#8B7AA3;font-weight:900;text-transform:uppercase;letter-spacing:.7px">Ação selecionada</div>
        <div style="font-size:18px;color:#171126;font-weight:900;margin-top:4px">{escape_html(acao.get('nome_cliente','N/D'))}</div>
        <div style="font-size:12px;color:#6B5A7A;margin-top:4px">ID {escape_html(acao.get('id_whitelabel',''))} · Criada em {escape_html(formatar_data_curta(acao.get('data_criacao')))}</div>
        <div style="margin-top:10px"><span style="background:#F3E8FF;color:{status_cor};border:1px solid #DDD6FE;border-radius:999px;padding:6px 10px;font-size:11px;font-weight:900">{status_emoji} {escape_html(status_texto)}</span></div>
    </div>
    """, unsafe_allow_html=True)

    opcoes_status = ["Pendente", "Em andamento", "Aguardando Cliente", "Concluído", "Cancelado"]
    idx_status = opcoes_status.index(status_texto) if status_texto in opcoes_status else 0

    prazo_atual = pd.to_datetime(acao.get("prazo_ajustes"), errors="coerce")
    tem_prazo_atual = pd.notna(prazo_atual)
    prazo_default = prazo_atual.date() if tem_prazo_atual else agora_sao_paulo().date()

    with st.form(f"form_manut_acao_{acao_id}"):
        novo_texto = st.text_area(
            "Descrição da ação",
            value=str(acao.get("o_que_foi_feito") or ""),
            height=140,
            key=f"manut_texto_{acao_id}",
        )
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            novo_status = st.selectbox("Status", opcoes_status, index=idx_status, key=f"manut_status_{acao_id}")
        with col2:
            manter_prazo = st.checkbox("Usar prazo", value=bool(tem_prazo_atual), key=f"manut_tem_prazo_{acao_id}")
        with col3:
            novo_prazo_data = st.date_input("Prazo", value=prazo_default, format="DD/MM/YYYY", key=f"manut_prazo_{acao_id}")

        salvar = st.form_submit_button(f"💾 Atualizar ação · manutenção", use_container_width=True)

    if salvar:
        prazo_str = novo_prazo_data.strftime("%Y-%m-%d") if manter_prazo else None
        sucesso, msg = atualizar_acao_cliente(
            id_acao=acao_id,
            o_que_foi_feito=novo_texto,
            prazo_ajustes=prazo_str,
            status_acao=novo_status,
        )
        if sucesso:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

def render_clientes_central_acoes(dados: dict, df_todas_acoes: pd.DataFrame | None) -> None:
    """Lista de clientes da Central de Ações com valores reais de offline e última ação."""
    st.markdown("#### 🏢 Clientes da Central")
    st.caption("Uma linha por cliente, com % offline real e o último acompanhamento registrado.")
    df_clientes = montar_df_clientes_central_acoes(dados, df_todas_acoes)
    if df_clientes.empty:
        st.info("Nenhum cliente carregado.")
        return

    col_b, col_s = st.columns([2, 1])
    with col_b:
        termo = st.text_input("Buscar cliente na central", placeholder="Nome, franqueado ou ID...", key="central_clientes_busca_v4").strip().upper()
    with col_s:
        filtro = st.selectbox("Filtro", ["Todos", "Críticos", "Atenção", "Sem acompanhamento", "Com prazo vencido"], key="central_clientes_filtro_v4")

    df_view = df_clientes.copy()
    if filtro == "Críticos":
        df_view = df_view[df_view["% Offline"] > 10]
    elif filtro == "Atenção":
        df_view = df_view[(df_view["% Offline"] > 5) & (df_view["% Offline"] <= 10)]
    elif filtro == "Sem acompanhamento":
        df_view = df_view[(df_view["% Offline"] > 5) & (~df_view["Tem ação"])]
    elif filtro == "Com prazo vencido":
        df_view = df_view[df_view["Vencidas"] > 0]

    if termo:
        busca = (df_view["Cliente"].astype(str) + " " + df_view["Franqueado"].astype(str) + " " + df_view["ID"].astype(str)).str.upper()
        df_view = df_view[busca.str.contains(re.escape(termo), na=False)].copy()

    show = df_view[["ID", "Cliente", "Franqueado", "Total", "Offline", "% Offline", "Situação", "Última ação", "Data última ação", "Status da ação", "Prazo Status"]].copy()
    show["% Offline"] = show["% Offline"].map(lambda v: f"{float(v):.1f}%")
    render_dataframe(show, height=min(720, (len(show)+1)*38 + 3))


def render_central_acoes(dados: dict) -> None:
    st.markdown("### 📋 Central de Ações")
    st.caption("Visão executiva para reunião + cadastro rápido + histórico operacional, usando a tabela `acoes_clientes`.")

    if not supabase_configurado():
        st.warning("⚠️ Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY nos Secrets.")
        return

    tabela_existe, msg_tabela = criar_tabela_acoes_se_nao_existir()
    if not tabela_existe:
        st.error("🚨 Não foi possível acessar a tabela acoes_clientes no Supabase.")
        st.info(msg_tabela)
        with st.expander("SQL recomendado para recriar/ajustar a tabela", expanded=True):
            st.code(sql_criacao_supabase(), language="sql")
        return

    df_todas_acoes = carregar_todas_acoes()

    sub_dash, sub_cadastro, sub_manutencao, sub_acoes, sub_clientes = st.tabs([
        "📊 Resumo executivo",
        "➕ Cadastrar ação",
        "🛠️ Manutenção",
        "🎯 Ações registradas",
        "🏢 Clientes",
    ])

    with sub_dash:
        render_dashboard_acoes(df_todas_acoes, dados)

    with sub_cadastro:
        render_form_cadastro_acao(dados, prefixo_key="central_acoes_v5")

    with sub_manutencao:
        render_manutencao_acoes(df_todas_acoes)

    with sub_acoes:
        render_lista_acoes(df_todas_acoes, dados)

    with sub_clientes:
        render_clientes_central_acoes(dados, df_todas_acoes)

def render_aba_atualizar_base(df_origem: pd.DataFrame | None = None):
    st.markdown("### Atualizar base online")
    st.caption("Importe o CSV novo para o Supabase. A importação atualiza câmeras existentes e insere câmeras novas, sem duplicar pelo ID_da_Camera.")

    ultima_importacao_msg = st.session_state.pop("ultima_importacao_msg", None)
    if ultima_importacao_msg:
        st.success(ultima_importacao_msg)

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

        df_preview_geral = preparar_df_para_supabase(df_csv)
        df_preview = preparar_df_para_supabase(df_csv_filtrado)
        clientes_geral = int(df_preview_geral["id_whitelabel"].nunique()) if not df_preview_geral.empty else 0
        clientes_filtro = int(df_preview["id_whitelabel"].nunique()) if not df_preview.empty else 0
        offline_geral = int((df_preview_geral["status_camera"] == "OFFLINE").sum()) if not df_preview_geral.empty else 0
        online_geral = int((df_preview_geral["status_camera"] == "ONLINE").sum()) if not df_preview_geral.empty else 0
        offline_filtro = int((df_preview["status_camera"] == "OFFLINE").sum()) if not df_preview.empty else 0
        online_filtro = int((df_preview["status_camera"] == "ONLINE").sum()) if not df_preview.empty else 0
        ignorados_filtro = total_csv_bruto - total_csv_filtro

        def fmt_card_num(valor: int) -> str:
            return f"{int(valor):,}".replace(",", ".")

        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card kpi-neutral">
                <div class="kpi-label">CSV Completo</div>
                <div class="kpi-value val-purple">{fmt_card_num(total_csv_bruto)}</div>
                <div class="kpi-sub">linhas recebidas no arquivo</div>
            </div>
            <div class="kpi-card kpi-neutral">
                <div class="kpi-label">Clientes no CSV</div>
                <div class="kpi-value val-purple">{fmt_card_num(clientes_geral)}</div>
                <div class="kpi-sub">IDs únicos com câmera válida</div>
            </div>
            <div class="kpi-card kpi-ok">
                <div class="kpi-label">Online no CSV</div>
                <div class="kpi-value val-ok">{fmt_card_num(online_geral)}</div>
                <div class="kpi-sub">{fmt_card_num(len(df_preview_geral))} válidas para importar</div>
            </div>
            <div class="kpi-card kpi-alert">
                <div class="kpi-label">Offline no CSV</div>
                <div class="kpi-value val-alert">{fmt_card_num(offline_geral)}</div>
                <div class="kpi-sub">base completa, antes do filtro</div>
            </div>
        </div>
        <div class="kpi-grid">
            <div class="kpi-card kpi-neutral">
                <div class="kpi-label">CSV Filtrado</div>
                <div class="kpi-value val-purple">{fmt_card_num(total_csv_filtro)}</div>
                <div class="kpi-sub">{fmt_card_num(ignorados_filtro)} linhas fora do filtro</div>
            </div>
            <div class="kpi-card kpi-neutral">
                <div class="kpi-label">Clientes no Filtro</div>
                <div class="kpi-value val-purple">{fmt_card_num(clientes_filtro)}</div>
                <div class="kpi-sub">clientes da lista do painel</div>
            </div>
            <div class="kpi-card kpi-ok">
                <div class="kpi-label">Online no Filtro</div>
                <div class="kpi-value val-ok">{fmt_card_num(online_filtro)}</div>
                <div class="kpi-sub">{fmt_card_num(len(df_preview))} válidas para importar</div>
            </div>
            <div class="kpi-card kpi-alert">
                <div class="kpi-label">Offline no Filtro</div>
                <div class="kpi-value val-alert">{fmt_card_num(offline_filtro)}</div>
                <div class="kpi-sub">universo usado na atualização</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(
            f"Filtro aplicado pela lista de clientes do painel (`nome_clientes.xlsx`). "
            f"Ignorados fora do filtro: {ignorados_filtro}. Online no filtro: {online_filtro}."
        )

        st.markdown("#### Prévia da importação filtrada")

        # Verificação dos campos novos — torna visível se o plano/datas vão preenchidos
        # ANTES de gravar (evita descobrir só depois que a base ficou nula).
        def _preenchidos(col: str) -> int:
            if col not in df_preview.columns:
                return -1  # coluna ausente => código antigo rodando
            s = df_preview[col].astype(str).str.strip().str.lower()
            return int((~s.isin(["", "nan", "none", "null", "nat", "<na>"])).sum())

        n_prev = len(df_preview)
        chk = {
            "plano_contratado": _preenchidos("plano_contratado"),
            "data_cadastro": _preenchidos("data_cadastro"),
            "data_inativacao": _preenchidos("data_inativacao"),
        }
        ausentes = [c for c, v in chk.items() if v == -1]
        if ausentes:
            st.error(
                "⚠️ A versão do app em execução está **sem** o mapeamento dos campos "
                f"`{'`, `'.join(ausentes)}` (eles não aparecem no envio). "
                "O código publicado está desatualizado — atualize o deploy antes de importar."
            )
        else:
            cols_chk = st.columns(3)
            rotulos = {
                "plano_contratado": "Plano contratado",
                "data_cadastro": "Data de cadastro",
                "data_inativacao": "Data de inativação",
            }
            for (campo, valor), col in zip(chk.items(), cols_chk):
                pct = (valor / n_prev * 100) if n_prev else 0
                col.metric(rotulos[campo], f"{fmt_card_num(valor)}/{fmt_card_num(n_prev)}", f"{pct:.0f}%")
            if chk["plano_contratado"] == 0:
                st.warning(
                    "O campo `plano_contratado` está zerado no envio: confira se o CSV tem a coluna "
                    "`Plano_Contratado` preenchida. Sem isso, a aba de Padrão de Armazenamento fica vazia."
                )

        render_dataframe(df_preview.head(100), height=320)

        # Diagnóstico de escopo: quantos clientes/linhas do CSV ficam FORA do filtro do painel.
        def _norm_wl(serie):
            return set(serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True))
        wl_csv = _norm_wl(df_csv[COL_WL]) if COL_WL in df_csv.columns else set()
        wl_filtro = _norm_wl(df_csv_filtrado[COL_WL]) if COL_WL in df_csv_filtrado.columns else set()
        wl_fora = wl_csv - wl_filtro
        if wl_fora:
            st.info(
                f"**Escopo da importação:** {fmt_card_num(total_csv_filtro)} linhas de "
                f"{len(wl_filtro)} clientes entram (presentes em `nome_clientes.xlsx`). "
                f"{len(wl_fora)} clientes do CSV "
                f"({fmt_card_num(total_csv_bruto - total_csv_filtro)} linhas) ficam **de fora** do filtro — "
                "é por isso que a base pode não refletir tudo que está no CSV."
            )

        importar_tudo = st.checkbox(
            "Importar todos os clientes do CSV (ignorar filtro do painel)",
            value=False,
            key="importar_csv_completo",
            help="Por padrão a importação grava apenas os whitelabels listados em nome_clientes.xlsx. "
                 "Marque para sincronizar a base online com o CSV inteiro.",
        )
        df_para_enviar = df_csv if importar_tudo else df_csv_filtrado
        if importar_tudo:
            st.caption(f"Modo CSV completo: {fmt_card_num(len(df_csv))} linhas serão sincronizadas.")


        if st.button("🚀 Atualizar base online", type="primary", use_container_width=True, key="btn_atualizar_base_online_v1"):
            status_box = st.empty()
            progress_bar = st.progress(0)
            percent_box = st.empty()

            def atualizar_barra(percentual: int, mensagem: str, tipo: str = "info"):
                percentual = int(max(0, min(100, percentual)))
                progress_bar.progress(percentual)
                percent_box.markdown(f"**{percentual}%** · {mensagem}")
                if tipo == "success":
                    status_box.success(f"✅ {mensagem}")
                elif tipo == "warning":
                    status_box.warning(f"⚠️ {mensagem}")
                elif tipo == "error":
                    status_box.error(f"❌ {mensagem}")
                else:
                    status_box.info(f"⏳ {mensagem}")

            def atualizar_upload(enviados: int, total_registros: int, mensagem: str):
                # Upload ocupa somente a faixa de 15% a 80%.
                # Assim a barra não finaliza antes de snapshot/cache/rerun.
                if total_registros <= 0:
                    percentual = 80
                else:
                    fracao = min(max(enviados / total_registros, 0), 1)
                    percentual = 15 + int(fracao * 65)
                atualizar_barra(percentual, mensagem)

            atualizar_barra(5, "Validando CSV e filtros selecionados...")
            atualizar_barra(10, "Preparando registros filtrados para importação...")
            atualizar_barra(15, "Iniciando atualização da base online. Não feche esta página.")

            ok, msg, total = enviar_df_supabase(df_para_enviar, progress_callback=atualizar_upload)
            if ok:
                atualizar_barra(85, "Base online atualizada. Registrando histórico da importação...")
                try:
                    atualizar_barra(90, "Gravando snapshot automático da nova importação...")
                    df_snapshot = preencher_cidade_estado_por_clientes(
                        df_para_enviar.copy(),
                        carregar_clientes_prefeitura(),
                    )
                    dados_snapshot = processar_df_gov(df_snapshot, clientes_map)
                    gravado_em = salvar_snapshot_automatico(
                        dados_snapshot,
                        df_snapshot,
                        total_importado=total,
                    )
                    if gravado_em:
                        st.success(f"Snapshot automático gravado em {pd.to_datetime(gravado_em).strftime('%d/%m/%Y %H:%M')}.")
                    else:
                        st.warning("A importação terminou, mas não havia dados válidos para gravar snapshot automático.")
                except Exception as e:
                    st.warning(f"A importação terminou, mas o snapshot automático não foi gravado: {e}")

                atualizar_barra(95, "Limpando cache para remover dados antigos...")
                try:
                    carregar_cameras_supabase.clear()
                except Exception:
                    pass
                try:
                    carregar_dados.clear()
                except Exception:
                    pass
                try:
                    calcular_saude_dados.clear()
                except Exception:
                    pass
                st.cache_data.clear()

                atualizar_barra(98, "Recarregando dados usados pelos dashboards...")
                try:
                    carregar_cameras_supabase()
                except Exception:
                    pass
                try:
                    carregar_dados()
                except Exception:
                    pass

                atualizar_barra(100, f"Importação concluída: {total} registros enviados/atualizados. Atualizando dashboards...", tipo="success")
                st.session_state["ultima_importacao_msg"] = (
                    f"Base online atualizada com sucesso: {total} registros enviados/atualizados. "
                    f"Offline no filtro: {offline_filtro}."
                )
                time.sleep(0.8)
                st.rerun()
            else:
                atualizar_barra(0, "A importação não foi concluída.", tipo="error")
                st.error(msg)

    st.markdown("---")
    st.markdown("#### Status da base online (filtrados)")
    st.caption("Os números abaixo consideram somente os clientes existentes na lista do painel (`nome_clientes.xlsx`).")
    if supabase_configurado():
        df_online, erro_online = carregar_cameras_supabase()
        if erro_online:
            st.error(erro_online)
        elif df_online is not None:
            df_online_filtrado = df_online.copy()
            clientes_map_status = carregar_clientes()

            if clientes_map_status and "id_whitelabel" in df_online_filtrado.columns:
                ids_validos_status = set(str(k).strip() for k in clientes_map_status.keys())
                df_online_filtrado = df_online_filtrado[
                    df_online_filtrado["id_whitelabel"].astype(str).str.strip().isin(ids_validos_status)
                ].copy()

            status_online = df_online_filtrado.get("status_camera", pd.Series(dtype=str)).astype(str).str.upper()
            registros_bd_filtrados = int(len(df_online_filtrado))
            clientes_bd_filtrados = int(df_online_filtrado["id_whitelabel"].nunique()) if "id_whitelabel" in df_online_filtrado.columns else 0
            online_bd_filtrados = int((status_online == "ONLINE").sum())
            offline_bd_filtrados = int((status_online == "OFFLINE").sum())
            total_bd_geral = int(len(df_online))
            fora_filtro_bd = max(total_bd_geral - registros_bd_filtrados, 0)

            def fmt_card_num(valor: int) -> str:
                return f"{int(valor):,}".replace(",", ".")

            st.markdown(f"""
            <div class="kpi-grid">
                <div class="kpi-card kpi-ok">
                    <div class="kpi-label">Status da base online (filtrados)</div>
                    <div class="kpi-value val-ok">{fmt_card_num(online_bd_filtrados)}</div>
                    <div class="kpi-sub">câmeras online dentro do filtro</div>
                </div>
                <div class="kpi-card kpi-neutral">
                    <div class="kpi-label">Registros no BD (filtrados)</div>
                    <div class="kpi-value val-purple">{fmt_card_num(registros_bd_filtrados)}</div>
                    <div class="kpi-sub">{fmt_card_num(fora_filtro_bd)} registros fora do filtro</div>
                </div>
                <div class="kpi-card kpi-neutral">
                    <div class="kpi-label">Clientes (filtrados)</div>
                    <div class="kpi-value val-purple">{fmt_card_num(clientes_bd_filtrados)}</div>
                    <div class="kpi-sub">clientes da lista do painel</div>
                </div>
                <div class="kpi-card kpi-alert">
                    <div class="kpi-label">Offline (filtrados)</div>
                    <div class="kpi-value val-alert">{fmt_card_num(offline_bd_filtrados)}</div>
                    <div class="kpi-sub">câmeras offline dentro do filtro</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            render_dataframe(converter_supabase_para_df_gov(df_online_filtrado).head(200), height=360)

# ─────────────────────────────────────────────
# LEITURA DO CSV + CLIENTES
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def carregar_clientes() -> dict:
    """Carrega nome_clientes.xlsx e retorna dict {ID_Whitelabel: nome_cliente}."""
    caminho_clientes = caminho_xlsx_clientes()
    if not caminho_clientes:
        return {}
    try:
        df = pd.read_excel(caminho_clientes, engine="openpyxl")
        # Aceitar qualquer variação de nome de coluna
        col_id = next((c for c in df.columns if "whitelabel" in c.lower() or "id" in c.lower()), df.columns[0])
        col_nom = next((c for c in df.columns if "nome" in c.lower() or "client" in c.lower()), df.columns[1] if len(df.columns) > 1 else df.columns[0])
        chaves = df[col_id].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        return dict(zip(chaves, df[col_nom].astype(str).str.strip()))
    except Exception:
        return {}

@st.cache_data(ttl=60)
def carregar_clientes_prefeitura() -> dict:
    """Carrega nome_clientes.xlsx e retorna dict {ID_Whitelabel: Prefeitura / cidade-estado}."""
    caminho_clientes = caminho_xlsx_clientes()
    if not caminho_clientes:
        return {}
    try:
        df = pd.read_excel(caminho_clientes, engine="openpyxl")
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


@st.cache_data(ttl=60)
def carregar_clientes_franqueado() -> dict:
    """Carrega nome_clientes.xlsx e retorna dict {ID_Whitelabel: Franqueado}."""
    caminho_clientes = caminho_xlsx_clientes()
    if not caminho_clientes:
        return {}
    try:
        df = pd.read_excel(caminho_clientes, engine="openpyxl")
        if df.empty:
            return {}
        col_id = next((c for c in df.columns if "whitelabel" in str(c).lower() or str(c).lower().strip() in ("id", "id_cliente")), df.columns[0])
        col_franq = next((c for c in df.columns if "franqueado" in str(c).lower() or "franquia" in str(c).lower()), None)
        if col_franq is None:
            return {}
        return dict(zip(df[col_id].astype(str).str.strip(), df[col_franq].astype(str).replace({"nan": ""}).str.strip()))
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
    franqueados_map = carregar_clientes_franqueado()

    # ── Filtrar apenas clientes do xlsx (se xlsx foi carregado) ──
    if clientes_map:
        ids_validos = set(clientes_map.keys())
        df = df[df[COL_WL].astype(str).str.strip().isin(ids_validos)]

    if df.empty:
        return {}

    city_col = encontrar_coluna_por_chaves(df, ("cidade", "municipio", "city", "prefeitura"), default=None)
    state_col = encontrar_coluna_por_chaves(df, ("estado", "uf", "state"), default=None)

    # Parsear data da última atualização
    agora = agora_sao_paulo()
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
        nome_empresa_csv = grupo[COL_EMPRESA].iloc[0] if COL_EMPRESA in grupo.columns else ""
        nome_empresa = franqueados_map.get(wl_id, nome_empresa_csv) or nome_empresa_csv
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
        total_grupo = int(len(grupo))
        offline_grupo = int(len(df_off))
        pct_grupo = round((offline_grupo / total_grupo * 100), 2) if total_grupo else 0.0
        resultado[wl_id] = {
            "nome_cliente": nome_cliente,
            "nome_empresa": nome_empresa,
            "cidade": cidade,
            "uf": estado,
            "cidade_estado": cidade_estado,
            "offline": df_off,
            "offline_count": offline_grupo,
            "total": total_grupo,
            "pct": pct_grupo,
            "pct_offline": pct_grupo,
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
                tickfont=dict(size=10, color="#8B7AA3"),
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
            "ultima_atualizacao_base": carregar_ultima_atualizacao_base(),
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
        datas_futuras = (parsed > agora_sao_paulo()).sum()
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
        "ultima_atualizacao_base": carregar_ultima_atualizacao_base(),
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
    total_conhecido = None
    # Avança pelo nº real de linhas retornadas e só encerra num lote vazio (ou ao
    # atingir o total do Content-Range). Assim continua correto mesmo quando o
    # servidor aplica um teto (db-max-rows) menor que o page_size pedido — antes,
    # um lote menor que page_size encerrava o laço cedo e cortava os snapshots
    # mais recentes (ordem asc), fazendo a última importação sumir da tendência.
    max_iter = 100000  # trava de segurança contra laço infinito
    try:
        for _ in range(max_iter):
            headers = supabase_headers()
            headers["Range-Unit"] = "items"
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
            got = len(lote)
            offset += got

            # Content-Range: "inicio-fim/total" (total pode ser "*", ou seja, desconhecido).
            cr = resp.headers.get("Content-Range") or resp.headers.get("content-range")
            if cr and "/" in cr:
                tail = cr.rsplit("/", 1)[-1].strip()
                if tail.isdigit():
                    total_conhecido = int(tail)

            if total_conhecido is not None and offset >= total_conhecido:
                break
            # Sem total conhecido: segue paginando até vir um lote vazio.
    except Exception as e:
        return pd.DataFrame(), f"Erro ao consultar {tabela}: {e}"

    return pd.DataFrame(todos), ""


@st.cache_data(ttl=120)
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


def _status_label_camera(valor) -> str:
    """Rótulo amigável de status de câmera (Online/Offline) com sinal visual."""
    s = str(valor or "").strip().upper()
    if s == "ONLINE":
        return "🟢 Online"
    if s == "OFFLINE":
        return "🔴 Offline"
    if s in ("", "NAN", "NONE"):
        return "N/D"
    return s.title()


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

    for col in [COL_NOME_CAM, COL_ULT_ATU, COL_STATUS, COL_EMPRESA, COL_DATA_CAD]:
        if col not in df_cam.columns:
            df_cam[col] = ""

    try:
        ultima_fmt = parse_ultima_atualizacao(df_cam[COL_ULT_ATU]).dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
    except Exception:
        ultima_fmt = df_cam[COL_ULT_ATU].astype(str).fillna("")

    try:
        cadastro_fmt = parse_ultima_atualizacao(df_cam[COL_DATA_CAD]).dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
    except Exception:
        cadastro_fmt = df_cam[COL_DATA_CAD].astype(str).fillna("")

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
            "data_cadastro": str(cadastro_fmt.loc[idx_row] if idx_row in cadastro_fmt.index else ""),
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
    # Campos opcionais (podem não existir em snapshots antigos): lidos de forma defensiva.
    out["data_cadastro"] = df.get("data_cadastro", "").astype(str).replace({"nan": ""}).str.strip() if "data_cadastro" in df.columns else ""
    out["data_snapshot"] = df.get("data_snapshot", "").astype(str).replace({"nan": ""}).str.strip() if "data_snapshot" in df.columns else ""

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
    agora = agora_sao_paulo_str()

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
            "data_cadastro": limpar_valor_json(r.get("data_cadastro")),
        })

    def _postar_cameras(regs: list) -> "requests.Response | None":
        for i in range(0, len(regs), 500):
            lote = regs[i:i + 500]
            if not lote:
                continue
            resp = requests.post(
                supabase_table_url(SNAPSHOT_TABLE),
                headers=supabase_headers("return=minimal"),
                json=lote,
                timeout=60,
            )
            if resp.status_code not in (200, 201, 204):
                return resp
        return None

    resp_err = _postar_cameras(registros)
    if resp_err is not None:
        # Se a tabela ainda não tem a coluna opcional 'data_cadastro', regrava sem ela
        # em vez de falhar o snapshot inteiro. (Adicione a coluna no Supabase para
        # preservar a Data de Cadastro das câmeras removidas em comparativos futuros.)
        if "data_cadastro" in (resp_err.text or "").lower():
            registros_sem = [{k: v for k, v in reg.items() if k != "data_cadastro"} for reg in registros]
            resp_err2 = _postar_cameras(registros_sem)
            if resp_err2 is not None:
                raise RuntimeError(f"Erro ao salvar câmeras do snapshot no Supabase: {resp_err2.status_code} - {resp_err2.text[:500]}")
        else:
            raise RuntimeError(f"Erro ao salvar câmeras do snapshot no Supabase: {resp_err.status_code} - {resp_err.text[:500]}")

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


def salvar_snapshot_automatico(
    dados: dict,
    df_origem: pd.DataFrame | None = None,
    total_importado: int | None = None,
) -> str:
    if not dados:
        return ""

    agora = agora_sao_paulo()
    label = f"Importação CSV {agora.strftime('%d/%m/%Y %H:%M')}"
    notas = "Snapshot automático criado após atualização da base online por CSV."
    if total_importado is not None:
        notas += f" {int(total_importado)} registros enviados/atualizados."

    return salvar_snapshot(label, notas, dados, df_origem)


@st.cache_data(ttl=120)
def carregar_historico_clientes(dias: int = 30) -> pd.DataFrame:
    limite = agora_sao_paulo() - timedelta(days=dias)
    df_snaps = listar_snapshots()
    if df_snaps.empty:
        return pd.DataFrame(columns=["snapshot_id", "label", "gravado_em", "wl_id", "nome_cliente", "total", "offline", "pct_offline"])

    df_snaps["gravado_dt"] = pd.to_datetime(df_snaps["gravado_em"], errors="coerce")
    df_snaps = df_snaps[df_snaps["gravado_dt"] >= limite].copy()
    if df_snaps.empty:
        return pd.DataFrame(columns=["snapshot_id", "label", "gravado_em", "wl_id", "nome_cliente", "total", "offline", "pct_offline"])

    snapshot_ids = df_snaps["id"].astype(int).tolist()
    filtro_ids = _postgrest_in_filter_int(snapshot_ids)
    if filtro_ids != "in.()":
        df_cli, erro = _supabase_select_all(
            SNAPSHOT_CLIENTES_TABLE,
            params={
                "select": "snapshot_id,id_whitelabel,nome_cliente,total_cameras,total_offline,pct_offline",
                "snapshot_id": filtro_ids,
                "order": "snapshot_id.asc,id_whitelabel.asc",
            },
            page_size=5000,
        )
        if not erro and not df_cli.empty:
            meta = df_snaps[["id", "label", "gravado_em"]].copy()
            meta["id"] = pd.to_numeric(meta["id"], errors="coerce").astype("Int64")

            out = pd.DataFrame()
            out["snapshot_id"] = pd.to_numeric(df_cli.get("snapshot_id", 0), errors="coerce").astype("Int64")
            out["wl_id"] = df_cli.get("id_whitelabel", "").astype(str).str.strip()
            out["nome_cliente"] = df_cli.get("nome_cliente", "").astype(str).replace({"nan": ""}).str.strip()
            out["total"] = pd.to_numeric(df_cli.get("total_cameras", 0), errors="coerce").fillna(0).astype(int)
            out["offline"] = pd.to_numeric(df_cli.get("total_offline", 0), errors="coerce").fillna(0).astype(int)
            out["pct_offline"] = pd.to_numeric(df_cli.get("pct_offline", 0), errors="coerce").fillna(0.0)
            out = out[(out["snapshot_id"].notna()) & (out["wl_id"] != "")].copy()
            out = out.merge(meta, left_on="snapshot_id", right_on="id", how="left")
            out = out.drop(columns=["id"], errors="ignore")
            out["snapshot_id"] = out["snapshot_id"].astype(int)
            out = out[["snapshot_id", "label", "gravado_em", "wl_id", "nome_cliente", "total", "offline", "pct_offline"]]
            return out.sort_values(["snapshot_id", "wl_id"]).reset_index(drop=True)

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


def slug_arquivo(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "relatorio")).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9_-]+", "_", texto).strip("_").lower()
    return texto or "relatorio"


def _status_relatorio_franquia(pct: float, offline: int) -> tuple[str, str, str]:
    if offline <= 0:
        return "Saudável", "#059669", "#D1FAE5"
    if pct > 10:
        return "Crítico", "#DC2626", "#FEE2E2"
    if pct > 5:
        return "Atenção", "#D97706", "#FEF3C7"
    return "Saudável", "#059669", "#D1FAE5"


def gerar_relatorio_franquia_html(nome_franquia: str, df_clientes_franquia: pd.DataFrame, dados: dict) -> str:
    """Gera HTML pronto para colar no corpo do e-mail da franquia."""
    nome_franquia = str(nome_franquia or "Sem franquia").strip()
    df_rel = df_clientes_franquia.copy()
    total_clientes_rel = int(len(df_rel))
    total_cameras_rel = int(pd.to_numeric(df_rel.get("Total", 0), errors="coerce").fillna(0).sum()) if not df_rel.empty else 0
    total_offline_rel = int(pd.to_numeric(df_rel.get("Offline", 0), errors="coerce").fillna(0).sum()) if not df_rel.empty else 0
    pct_rel = round(total_offline_rel / total_cameras_rel * 100, 2) if total_cameras_rel else 0.0
    data_ref = carregar_ultima_atualizacao_base()
    data_geracao = agora_sao_paulo_str("%d/%m/%Y %H:%M")
    status_geral, status_cor, status_bg = _status_relatorio_franquia(pct_rel, total_offline_rel)

    linhas_clientes = []
    linhas_offline = []
    if not df_rel.empty:
        df_rel = df_rel.sort_values(["% Offline", "Offline", "Cliente"], ascending=[False, False, True])
        for _, row in df_rel.iterrows():
            cliente = str(row.get("Cliente", ""))
            wl_id = str(row.get("ID", ""))
            total = int(row.get("Total", 0) or 0)
            offline = int(row.get("Offline", 0) or 0)
            online = int(row.get("Online", max(total - offline, 0)) or 0)
            pct = float(row.get("% Offline", 0) or 0)
            status_txt, status_cor_linha, status_bg_linha = _status_relatorio_franquia(pct, offline)
            linhas_clientes.append(
                f'<tr>'
                f'<td style="padding:10px 12px;border-bottom:1px solid #E9D5FF;color:#171126;font-weight:700">{escape_html(cliente)}<br><span style="font-size:11px;color:#8B7AA3;font-weight:500">ID {escape_html(wl_id)}</span></td>'
                f'<td style="padding:10px 12px;border-bottom:1px solid #E9D5FF;text-align:right;color:#171126">{total}</td>'
                f'<td style="padding:10px 12px;border-bottom:1px solid #E9D5FF;text-align:right;color:#059669;font-weight:700">{online}</td>'
                f'<td style="padding:10px 12px;border-bottom:1px solid #E9D5FF;text-align:right;color:#DC2626;font-weight:700">{offline}</td>'
                f'<td style="padding:10px 12px;border-bottom:1px solid #E9D5FF;text-align:right;color:#171126;font-weight:700">{pct:.1f}%</td>'
                f'<td style="padding:10px 12px;border-bottom:1px solid #E9D5FF;text-align:center"><span style="display:inline-block;background:{status_bg_linha};color:{status_cor_linha};border-radius:999px;padding:4px 9px;font-size:11px;font-weight:800">{status_txt}</span></td>'
                f'</tr>'
            )
            info = dados.get(wl_id, {})
            df_off = info.get("offline", pd.DataFrame())
            if df_off is not None and not df_off.empty:
                for _, cam in df_off.head(80).iterrows():
                    td = cam.get("_tempo_off", timedelta(seconds=-1))
                    tempo = fmt_tempo(td) if isinstance(td, timedelta) and td.total_seconds() >= 0 else "N/D"
                    ult = cam.get(COL_ULT_ATU, "")
                    ult_txt = ult.strftime("%d/%m/%Y %H:%M") if isinstance(ult, pd.Timestamp) else str(ult or "N/D")
                    linhas_offline.append(
                        f'<tr>'
                        f'<td style="padding:9px 10px;border-bottom:1px solid #F3E8FF;color:#171126;font-weight:700">{escape_html(cliente)}</td>'
                        f'<td style="padding:9px 10px;border-bottom:1px solid #F3E8FF;color:#171126">{escape_html(cam.get(COL_ID_CAM, ""))}</td>'
                        f'<td style="padding:9px 10px;border-bottom:1px solid #F3E8FF;color:#171126">{escape_html(cam.get(COL_NOME_CAM, ""))}</td>'
                        f'<td style="padding:9px 10px;border-bottom:1px solid #F3E8FF;color:#6B5A7A">{escape_html(ult_txt)}</td>'
                        f'<td style="padding:9px 10px;border-bottom:1px solid #F3E8FF;color:#DC2626;font-weight:700">{escape_html(tempo)}</td>'
                        f'</tr>'
                    )

    tabela_offline = '<div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:12px;padding:14px;color:#047857;font-weight:700;margin-top:18px">Nenhuma câmera offline identificada para esta franquia.</div>'
    if linhas_offline:
        tabela_offline = (
            '<h2 style="font-size:18px;color:#171126;margin:26px 0 10px">Câmeras offline</h2>'
            '<table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;background:#FFFFFF;border:1px solid #E9D5FF;border-radius:12px;overflow:hidden">'
            '<thead><tr style="background:#F3E8FF">'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Cliente</th>'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">ID Câmera</th>'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Nome da Câmera</th>'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Última vez online</th>'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Tempo offline</th>'
            '</tr></thead><tbody>' + ''.join(linhas_offline) + '</tbody></table>'
            '<p style="font-size:11px;color:#8B7AA3;margin-top:8px">Obs.: quando houver muitas câmeras offline, o relatório limita a listagem a 80 câmeras por cliente para manter o e-mail leve.</p>'
        )

    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#FAF7FF;font-family:Arial,Helvetica,sans-serif;color:#171126">
<div style="max-width:980px;margin:0 auto;padding:24px">
    <div style="background:linear-gradient(135deg,#5B21B6,#7C3AED,#A855F7);border-radius:18px;padding:24px;color:#FFFFFF">
        <div style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;opacity:.9">Camerite BI · Monitoramento</div>
        <h1 style="font-size:26px;line-height:1.2;margin:8px 0 4px">Relatório por franquia</h1>
        <div style="font-size:16px;font-weight:700">{escape_html(nome_franquia)}</div>
        <div style="font-size:12px;margin-top:12px;opacity:.9">Base: {escape_html(data_ref)} · Gerado em: {escape_html(data_geracao)}</div>
    </div>
    <div style="display:block;background:#FFFFFF;border:1px solid #E9D5FF;border-radius:16px;padding:18px;margin-top:16px">
        <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse"><tr>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Clientes</div><div style="font-size:28px;font-weight:900;color:#7C3AED">{total_clientes_rel}</div></td>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Câmeras</div><div style="font-size:28px;font-weight:900;color:#171126">{total_cameras_rel}</div></td>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Online</div><div style="font-size:28px;font-weight:900;color:#059669">{total_cameras_rel-total_offline_rel}</div></td>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Offline</div><div style="font-size:28px;font-weight:900;color:#DC2626">{total_offline_rel}</div></td>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">% Offline</div><div style="font-size:28px;font-weight:900;color:{status_cor}">{pct_rel:.1f}%</div><span style="display:inline-block;background:{status_bg};color:{status_cor};border-radius:999px;padding:4px 9px;font-size:11px;font-weight:800">{status_geral}</span></td>
        </tr></table>
    </div>
    <h2 style="font-size:18px;color:#171126;margin:26px 0 10px">Resumo por cliente</h2>
    <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;background:#FFFFFF;border:1px solid #E9D5FF;border-radius:12px;overflow:hidden">
        <thead><tr style="background:#F3E8FF">
            <th align="left" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Cliente</th><th align="right" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Total</th><th align="right" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Online</th><th align="right" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Offline</th><th align="right" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">% Offline</th><th align="center" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Status</th>
        </tr></thead><tbody>{''.join(linhas_clientes)}</tbody>
    </table>
    {tabela_offline}
    <p style="font-size:12px;color:#6B5A7A;margin-top:22px;line-height:1.5">Este relatório foi gerado automaticamente a partir da base atual do monitoramento. Para tratativas, priorizar clientes com maior percentual offline e câmeras com maior tempo sem atualização.</p>
</div></body></html>"""


def html_para_pdf_bytes(html: str) -> bytes | None:
    """Converte HTML (CSS inline / tabelas) em PDF. Retorna None se a lib não estiver disponível."""
    try:
        import io
        from xhtml2pdf import pisa
    except Exception:
        return None
    try:
        buf = io.BytesIO()
        resultado = pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
        if resultado.err:
            return None
        return buf.getvalue()
    except Exception:
        return None


def gerar_relatorio_armazenamento_html(nome_franquia: str, df_resumo_fr: pd.DataFrame, df_det_fr: pd.DataFrame, dom_min: float) -> str:
    """Gera o HTML do relatório de Padrão de Armazenamento de uma franquia (ou geral)."""
    nome_franquia = str(nome_franquia or "Todas as franquias").strip()
    data_ref = carregar_ultima_atualizacao_base()
    data_geracao = agora_sao_paulo_str("%d/%m/%Y %H:%M")

    total_clientes = int(len(df_resumo_fr))
    total_cameras = int(pd.to_numeric(df_resumo_fr.get("Câmeras", 0), errors="coerce").fillna(0).sum()) if not df_resumo_fr.empty else 0
    fora_total = int(pd.to_numeric(df_resumo_fr.get("Fora", 0), errors="coerce").fillna(0).sum()) if not df_resumo_fr.empty else 0
    clientes_afetados = int((pd.to_numeric(df_resumo_fr.get("Fora", 0), errors="coerce").fillna(0) > 0).sum()) if not df_resumo_fr.empty else 0
    conformidade = round((1 - fora_total / total_cameras) * 100, 1) if total_cameras else 100.0
    cor_conf = "#059669" if conformidade >= 95 else ("#D97706" if conformidade >= 85 else "#DC2626")

    # Resumo por cliente (ordena pelos com mais câmeras fora)
    linhas_clientes = []
    if not df_resumo_fr.empty:
        df_ord = df_resumo_fr.sort_values("Fora", ascending=False)
        for _, row in df_ord.iterrows():
            situacao = str(row.get("Situação", ""))
            if situacao == "Fora do padrão":
                cor_s, bg_s = "#DC2626", "#FEE2E2"
            elif situacao == "Conforme":
                cor_s, bg_s = "#059669", "#D1FAE5"
            else:
                cor_s, bg_s = "#6B5A7A", "#F3E8FF"
            dom_txt = f"{float(row.get('_dom', 0))*100:.0f}%" if pd.notna(row.get("_dom")) else "—"
            linhas_clientes.append(
                '<tr>'
                f'<td style="padding:9px 12px;border-bottom:1px solid #E9D5FF;color:#171126;font-weight:700">{escape_html(str(row.get("Cliente","")))}<br><span style="font-size:11px;color:#8B7AA3;font-weight:500">ID {escape_html(str(row.get("_wl","")))}</span></td>'
                f'<td style="padding:9px 12px;border-bottom:1px solid #E9D5FF;text-align:center;color:#5B21B6;font-weight:800">{escape_html(str(row.get("Plano padrão","")))}</td>'
                f'<td style="padding:9px 12px;border-bottom:1px solid #E9D5FF;text-align:right;color:#6B5A7A">{dom_txt}</td>'
                f'<td style="padding:9px 12px;border-bottom:1px solid #E9D5FF;text-align:right;color:#171126">{int(row.get("Câmeras",0) or 0)}</td>'
                f'<td style="padding:9px 12px;border-bottom:1px solid #E9D5FF;text-align:right;color:#DC2626;font-weight:700">{int(row.get("Fora",0) or 0)}</td>'
                f'<td style="padding:9px 12px;border-bottom:1px solid #E9D5FF;text-align:center"><span style="display:inline-block;background:{bg_s};color:{cor_s};border-radius:999px;padding:4px 9px;font-size:11px;font-weight:800">{escape_html(situacao)}</span></td>'
                '</tr>'
            )

    # Câmeras fora do padrão
    linhas_fora = []
    if df_det_fr is not None and not df_det_fr.empty:
        for _, row in df_det_fr.sort_values(["Cliente", "Câmera"]).iterrows():
            linhas_fora.append(
                '<tr>'
                f'<td style="padding:8px 10px;border-bottom:1px solid #F3E8FF;color:#171126;font-weight:700">{escape_html(str(row.get("Cliente","")))}</td>'
                f'<td style="padding:8px 10px;border-bottom:1px solid #F3E8FF;color:#6B5A7A">{escape_html(str(row.get("Cidade","")))}</td>'
                f'<td style="padding:8px 10px;border-bottom:1px solid #F3E8FF;color:#171126">{escape_html(str(row.get("Câmera","")))}</td>'
                f'<td style="padding:8px 10px;border-bottom:1px solid #F3E8FF;text-align:center;color:#DC2626;font-weight:700">{escape_html(str(row.get("Plano atual","")))}</td>'
                f'<td style="padding:8px 10px;border-bottom:1px solid #F3E8FF;text-align:center;color:#5B21B6;font-weight:700">{escape_html(str(row.get("Plano padrão","")))}</td>'
                f'<td style="padding:8px 10px;border-bottom:1px solid #F3E8FF;color:#171126">{escape_html(str(row.get("Divergência","")))}</td>'
                '</tr>'
            )

    if linhas_fora:
        tabela_fora = (
            '<h2 style="font-size:18px;color:#171126;margin:26px 0 10px">Câmeras fora do padrão</h2>'
            '<table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;background:#FFFFFF;border:1px solid #E9D5FF;border-radius:12px;overflow:hidden">'
            '<thead><tr style="background:#F3E8FF">'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Cliente</th>'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Cidade</th>'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Câmera</th>'
            '<th align="center" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Plano atual</th>'
            '<th align="center" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Plano padrão</th>'
            '<th align="left" style="padding:10px;color:#5B21B6;font-size:11px;text-transform:uppercase">Divergência</th>'
            '</tr></thead><tbody>' + "".join(linhas_fora) + '</tbody></table>'
        )
    else:
        tabela_fora = '<div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:12px;padding:14px;color:#047857;font-weight:700;margin-top:18px">Nenhuma câmera fora do padrão de armazenamento nesta franquia.</div>'

    return f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#FAF7FF;font-family:Arial,Helvetica,sans-serif;color:#171126">
<div style="max-width:980px;margin:0 auto;padding:24px">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" bgcolor="#5B21B6" style="background-color:#5B21B6;border-radius:18px"><tr><td bgcolor="#5B21B6" style="background-color:#5B21B6;padding:24px;color:#FFFFFF;border-radius:18px">
        <div style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;opacity:.9;color:#FFFFFF">Camerite BI · Monitoramento</div>
        <h1 style="font-size:26px;line-height:1.2;margin:8px 0 4px;color:#FFFFFF">Relatório de Padrão de Armazenamento</h1>
        <div style="font-size:16px;font-weight:700;color:#FFFFFF">{escape_html(nome_franquia)}</div>
        <div style="font-size:12px;margin-top:12px;opacity:.9;color:#FFFFFF">Base: {escape_html(data_ref)} · Gerado em: {escape_html(data_geracao)}</div>
    </td></tr></table>
    <div style="display:block;background:#FFFFFF;border:1px solid #E9D5FF;border-radius:16px;padding:18px;margin-top:16px">
        <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse"><tr>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Clientes</div><div style="font-size:28px;font-weight:900;color:#7C3AED">{total_clientes}</div></td>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Câmeras</div><div style="font-size:28px;font-weight:900;color:#171126">{total_cameras}</div></td>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Fora do padrão</div><div style="font-size:28px;font-weight:900;color:#DC2626">{fora_total}</div></td>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Clientes afetados</div><div style="font-size:28px;font-weight:900;color:#D97706">{clientes_afetados}</div></td>
            <td style="width:20%;padding:8px"><div style="font-size:11px;color:#8B7AA3;font-weight:800;text-transform:uppercase">Conformidade</div><div style="font-size:28px;font-weight:900;color:{cor_conf}">{conformidade:.1f}%</div></td>
        </tr></table>
    </div>
    <h2 style="font-size:18px;color:#171126;margin:26px 0 10px">Resumo por cliente</h2>
    <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;background:#FFFFFF;border:1px solid #E9D5FF;border-radius:12px;overflow:hidden">
        <thead><tr style="background:#F3E8FF">
            <th align="left" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Cliente</th>
            <th align="center" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Plano padrão</th>
            <th align="right" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Dominância</th>
            <th align="right" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Câmeras</th>
            <th align="right" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Fora</th>
            <th align="center" style="padding:10px 12px;color:#5B21B6;font-size:11px;text-transform:uppercase">Situação</th>
        </tr></thead><tbody>{''.join(linhas_clientes)}</tbody>
    </table>
    {tabela_fora}
    <p style="font-size:12px;color:#6B5A7A;margin-top:22px;line-height:1.5">O “plano padrão” de cada cliente é o plano de retenção com mais câmeras (maioria por quantidade). Câmeras em plano diferente são listadas como fora do padrão. Clientes sem maioria clara (dominância abaixo de {int(dom_min*100)}%) ou com empate são tratados como “sem padrão definido”.</p>
</div></body></html>"""


def _cidade_relatorio_franquia(wl_id: str, row: pd.Series | None, dados: dict) -> str:
    """Define a cidade usada para separar os anexos XLSX do e-mail."""
    info = dados.get(str(wl_id), {}) if isinstance(dados, dict) else {}
    cidade = str(info.get("cidade_estado") or "").strip()
    if not cidade:
        cidade = str(info.get("cidade") or "").strip()
        uf = str(info.get("uf") or "").strip()
        if cidade and uf:
            cidade = f"{cidade} - {uf}"
    if not cidade and row is not None:
        for col in ("Cidade", "Prefeitura", "Município", "Municipio", "Cliente"):
            if col in row.index:
                cidade = str(row.get(col) or "").strip()
                if cidade:
                    break
    return cidade or "Sem cidade"


def _df_excel_seguro(df: pd.DataFrame) -> pd.DataFrame:
    """Remove tipos que costumam quebrar ou ficar ruins no Excel gerado em memória."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_timedelta64_dtype(out[col]):
            out[col] = out[col].apply(lambda x: fmt_tempo(x) if isinstance(x, timedelta) and x.total_seconds() >= 0 else "N/D")
        elif col == "_tempo_off":
            out[col] = out[col].apply(lambda x: fmt_tempo(x) if isinstance(x, timedelta) and x.total_seconds() >= 0 else "N/D")
        elif pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%d/%m/%Y %H:%M").fillna("N/D")
    return out.astype(object).where(pd.notna(out), "")


def gerar_xlsx_cidade_franquia(nome_franquia: str, nome_cidade: str, df_cidade: pd.DataFrame, dados: dict) -> bytes:
    """Gera um XLSX de uma cidade da franquia, com resumo e câmeras offline."""
    resumo_rows = []
    offline_rows = []

    for _, row in df_cidade.iterrows():
        wl_id = str(row.get("ID", "")).strip()
        info = dados.get(wl_id, {})
        total = int(row.get("Total", info.get("total", 0)) or 0)
        offline = int(row.get("Offline", len(info.get("offline", pd.DataFrame()))) or 0)
        online = int(row.get("Online", max(total - offline, 0)) or max(total - offline, 0))
        pct = float(row.get("% Offline", (offline / total * 100 if total else 0)) or 0)
        resumo_rows.append({
            "Franqueado": nome_franquia,
            "Cidade": nome_cidade,
            "ID Cliente": wl_id,
            "Cliente": row.get("Cliente", info.get("nome_cliente", "")),
            "Total Câmeras": total,
            "Online": online,
            "Offline": offline,
            "% Offline": round(pct, 2),
            "Status": row.get("Status", status_cliente(pct, offline)),
        })

        df_off = info.get("offline", pd.DataFrame())
        if df_off is not None and not df_off.empty:
            df_tmp = df_off.copy()
            for _, cam in df_tmp.iterrows():
                td = cam.get("_tempo_off", timedelta(seconds=-1))
                tempo = fmt_tempo(td) if isinstance(td, timedelta) and td.total_seconds() >= 0 else "N/D"
                ult = cam.get(COL_ULT_ATU, "")
                ult_txt = ult.strftime("%d/%m/%Y %H:%M") if isinstance(ult, pd.Timestamp) else str(ult or "N/D")
                offline_rows.append({
                    "Franqueado": nome_franquia,
                    "Cidade": nome_cidade,
                    "ID Cliente": wl_id,
                    "Cliente": row.get("Cliente", info.get("nome_cliente", "")),
                    "ID Câmera": cam.get(COL_ID_CAM, ""),
                    "Nome da Câmera": cam.get(COL_NOME_CAM, ""),
                    "Status": cam.get(COL_STATUS, "OFFLINE"),
                    "Última vez online": ult_txt,
                    "Tempo offline": tempo,
                    "Observações": cam.get(COL_OBS, ""),
                })

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(resumo_rows).to_excel(writer, index=False, sheet_name="Resumo")
        pd.DataFrame(offline_rows or [{"Mensagem": "Nenhuma câmera offline nesta cidade."}]).to_excel(
            writer, index=False, sheet_name="Cameras Offline"
        )
    buf.seek(0)
    return buf.getvalue()


def gerar_anexos_xlsx_cidades_franquia(nome_franquia: str, df_franquia: pd.DataFrame, dados: dict) -> list[tuple[str, bytes]]:
    """Cria um XLSX por cidade para ser anexado no .eml da franquia."""
    if df_franquia is None or df_franquia.empty:
        return []
    df_tmp = df_franquia.copy()
    df_tmp["_Cidade Anexo"] = df_tmp.apply(lambda r: _cidade_relatorio_franquia(str(r.get("ID", "")), r, dados), axis=1)
    anexos = []
    carimbo = agora_sao_paulo_str('%Y%m%d_%H%M')
    for cidade, df_cidade in df_tmp.groupby("_Cidade Anexo", dropna=False):
        cidade = str(cidade or "Sem cidade").strip() or "Sem cidade"
        nome_arquivo = f"cameras_{slug_arquivo(nome_franquia)}_{slug_arquivo(cidade)}_{carimbo}.xlsx"
        conteudo = gerar_xlsx_cidade_franquia(nome_franquia, cidade, df_cidade.drop(columns=["_Cidade Anexo"], errors="ignore"), dados)
        anexos.append((nome_arquivo, conteudo))
    return anexos


def gerar_eml_relatorio_franquia(nome_franquia: str, html_body: str, anexos: list[tuple[str, bytes]] | None = None) -> bytes:
    """Gera .eml com corpo HTML e, opcionalmente, anexos XLSX por cidade."""
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.header import Header
    from email.utils import formatdate

    assunto = f"Relatório de Monitoramento - {nome_franquia}"
    msg = MIMEMultipart("mixed")
    msg["Subject"] = str(Header(assunto, "utf-8"))
    msg["MIME-Version"] = "1.0"
    msg["Date"] = formatdate(localtime=True)

    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(msg_alt)

    for nome_arquivo, conteudo in anexos or []:
        part = MIMEApplication(
            conteudo,
            _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        part.add_header("Content-Disposition", "attachment", filename=nome_arquivo)
        msg.attach(part)

    return msg.as_bytes()

def render_relatorio_por_franquia(df_clientes_ops: pd.DataFrame, dados: dict, key_prefix: str = "relatorio_franquia") -> None:
    st.markdown("#### 📧 Relatório por franquia")
    st.caption("Gere um HTML pronto para colar no corpo do e-mail ou um arquivo .eml para abrir no Outlook. O .eml já vai com anexos XLSX separados por cidade da franquia.")
    if df_clientes_ops is None or df_clientes_ops.empty or "Franqueado" not in df_clientes_ops.columns:
        st.info("Nenhum dado de franquia encontrado. Confira se o arquivo nome_clientes.xlsx possui a coluna Franqueado.")
        return
    df_base = df_clientes_ops.copy()
    df_base["Franqueado"] = df_base["Franqueado"].fillna("").astype(str).str.strip()
    df_base = df_base[df_base["Franqueado"] != ""].copy()
    if df_base.empty:
        st.info("Nenhuma franquia preenchida na base de clientes.")
        return
    resumo = df_base.groupby("Franqueado", as_index=False).agg(Clientes=("ID", "count"), Total=("Total", "sum"), Offline=("Offline", "sum")).sort_values(["Offline", "Clientes", "Franqueado"], ascending=[False, False, True]).reset_index(drop=True)
    resumo["Online"] = resumo["Total"] - resumo["Offline"]
    resumo["% Offline"] = (resumo["Offline"] / resumo["Total"].replace({0: pd.NA}) * 100).fillna(0).round(1)
    col_sel, col_busca = st.columns([2, 1])
    with col_busca:
        termo = st.text_input("Buscar franquia", key=f"{key_prefix}_busca", placeholder="Digite parte do nome…").strip()
    resumo_view = resumo[resumo["Franqueado"].str.upper().str.contains(re.escape(termo.upper()), na=False)].copy() if termo else resumo.copy()
    with col_sel:
        opcoes = resumo_view["Franqueado"].tolist()
        franquia_preview = st.selectbox("Pré-visualizar franquia", opcoes, key=f"{key_prefix}_preview") if opcoes else None
    if resumo_view.empty:
        st.info("Nenhuma franquia encontrada para a busca.")
        return
    st.markdown("##### Franquias disponíveis")
    render_dataframe(resumo_view, height=min(420, (len(resumo_view) + 1) * 35 + 3))
    st.markdown("##### Gerar arquivos")
    for _, row in resumo_view.iterrows():
        franquia = str(row["Franqueado"])
        df_franquia = df_base[df_base["Franqueado"].eq(franquia)].copy()
        html_rel = gerar_relatorio_franquia_html(franquia, df_franquia, dados)
        anexos_xlsx = gerar_anexos_xlsx_cidades_franquia(franquia, df_franquia, dados)
        nome_base = f"relatorio_monitoramento_{slug_arquivo(franquia)}_{agora_sao_paulo_str('%Y%m%d_%H%M')}"
        st.markdown(f"""
        <div style="background:#ffffff;border:1px solid #E9D5FF;border-radius:12px;padding:12px 14px;margin:8px 0;box-shadow:0 8px 22px rgba(91,33,182,.06)">
            <div style="font-size:14px;font-weight:800;color:#171126">{escape_html(franquia)}</div>
            <div style="font-size:12px;color:#6B5A7A">{int(row['Clientes'])} clientes · {int(row['Total'])} câmeras · {int(row['Offline'])} offline · {float(row['% Offline']):.1f}% offline · {len(anexos_xlsx)} anexo(s) XLSX por cidade</div>
        </div>
        """, unsafe_allow_html=True)
        c_html, c_eml = st.columns(2)
        c_html.download_button("⬇ Baixar HTML", data=html_rel.encode("utf-8"), file_name=f"{nome_base}.html", mime="text/html", use_container_width=True, key=f"{key_prefix}_dl_html_{slug_arquivo(franquia)}")
        c_eml.download_button("✉ Baixar Outlook (.eml + XLSX por cidade)", data=gerar_eml_relatorio_franquia(franquia, html_rel, anexos_xlsx), file_name=f"{nome_base}.eml", mime="message/rfc822", use_container_width=True, key=f"{key_prefix}_dl_eml_{slug_arquivo(franquia)}")
    if franquia_preview:
        st.markdown("##### Prévia do HTML")
        html_preview = gerar_relatorio_franquia_html(franquia_preview, df_base[df_base["Franqueado"].eq(franquia_preview)].copy(), dados)
        st.components.v1.html(html_preview, height=650, scrolling=True)

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
    agora = agora_sao_paulo()

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
        font=dict(family="DM Sans", color="#6B5A7A"),
    )


# ─────────────────────────────────────────────
# RENDER CARD DE CLIENTE
# ─────────────────────────────────────────────
def tabela_clara(df: pd.DataFrame):
    return (
        df.style
        .set_properties(**{
            "background-color": "#ffffff",
            "color": "#171126",
            "border-color": "#F5F3FF",
        })
        .set_table_styles([
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#F3E8FF"),
                    ("color", "#6D28D9"),
                    ("border-color", "#E9D5FF"),
                    ("font-weight", "700"),
                ],
            },
            {
                "selector": "tbody th",
                "props": [
                    ("background-color", "#FAF7FF"),
                    ("color", "#6B5A7A"),
                    ("border-color", "#F5F3FF"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("background-color", "#ffffff"),
                    ("color", "#171126"),
                    ("border-color", "#F5F3FF"),
                ],
            },
        ])
    )


def render_dataframe(df: pd.DataFrame, height: int):
    st.dataframe(tabela_clara(df), use_container_width=True, height=height, key=f"df_{uuid.uuid4().hex}")


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

    sub_html = f'<div style="font-size:9px;color:#8B7AA3;margin-bottom:6px">{nome_empresa}</div>' if nome_empresa else ""
    id_html  = f'<div style="font-size:9px;color:#8B7AA3">ID: {wl_id_html}</div>'

    with col:
        card_html = f'<div class="unit-card {card_c}"><div class="unit-name">{nome_display}</div>{sub_html}<div class="unit-count {count_c}">{count}</div><div class="unit-label {label_c}">{label_txt}</div><div class="prog-track"><div class="prog-fill" style="width:{prog_w}%;background:{cor}"></div></div>{trend_html}{id_html}</div>'
        st.write(card_html, unsafe_allow_html=True)

        if count > 0:
            if st.button("🔎 Ver detalhes do cliente", key=f"btn_detalhe_cliente_{str(wl_id)}"):
                st.session_state["detalhe"] = wl_id
        else:
            st.button("✓ Operacional", key=f"btn_operacional_cliente_{str(wl_id)}", disabled=True)


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

        if st.button("🔄 Atualizar dados", key="sidebar_atualizar_dados_v1"):
            st.cache_data.clear(); st.rerun()

        st.markdown("---")
        st.markdown('<div class="nav-section">Salvar Snapshot</div>', unsafe_allow_html=True)
        lbl  = st.text_input("Rótulo", value=f"Snapshot {agora_sao_paulo_str('%d/%m %H:%M')}", key="snap_lbl")
        nota = st.text_area("Observações (opcional)", key="snap_nota", height=60)
        if st.button("💾 Salvar snapshot", key="sidebar_salvar_snapshot_v1"):
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
            file_name=f"camerite_bi_{agora_sao_paulo_str('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="sidebar_exportar_excel_v1",
        ):
            pass


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# DETALHE RÁPIDO DE CLIENTE
# ─────────────────────────────────────────────
def render_cliente_detalhe_rapido(wl_id: str, dados: dict):
    """Renderiza somente o detalhe do cliente aberto, sem montar todos os cards/tabs."""
    v = dados.get(wl_id, {"nome_cliente": "?", "nome_empresa": "", "offline": pd.DataFrame(), "total": 0})
    df_det = v.get("offline", pd.DataFrame()).copy()
    total_u = int(v.get("total", 0) or 0)
    offline_u = int(len(df_det))
    pct_d = round(offline_u / total_u * 100, 1) if total_u else 0
    cor_d = cor_hex(pct_d)

    nome_cliente_html = escape_html(v.get("cidade_estado") or v.get("nome_cliente", "?"))
    nome_empresa_html = escape_html(v.get("nome_empresa", ""))
    wl_id_html = escape_html(wl_id)

    topo_voltar, topo_titulo = st.columns([1, 5])
    with topo_voltar:
        if st.button("← Voltar", key="voltar_cliente_top", use_container_width=True):
            st.session_state.pop("detalhe", None)
            st.rerun()

    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.2rem;flex-wrap:wrap">'
        '<div style="background:rgba(0,136,204,.12);border:1px solid rgba(0,136,204,.22);'
        'border-radius:8px;padding:6px 14px;font-size:11px;font-weight:600;'
        'color:#6D28D9;text-transform:uppercase;letter-spacing:.5px">📍 Detalhamento rápido</div>'
        '<div>'
        + f'<div style="font-size:20px;font-weight:700;color:#7C3AED">{nome_cliente_html}</div>'
        + f'<div style="font-size:12px;color:#8B7AA3">{nome_empresa_html} · ID: {wl_id_html}</div>'
        + '</div>'
        + f'<div style="margin-left:auto;font-size:13px;font-weight:700;color:{cor_d}">'
        + f'{offline_u} offline de {total_u} câmeras ({pct_d}%)'
        + '</div>'
        + '</div>',
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", total_u)
    m2.metric("Offline", offline_u)
    m3.metric("% Offline", f"{pct_d:.1f}%")

    maior_tempo_txt = "N/D"
    if not df_det.empty and "_tempo_off" in df_det.columns:
        try:
            validos = df_det["_tempo_off"][df_det["_tempo_off"].dt.total_seconds() >= 0]
            if not validos.empty:
                maior_tempo_txt = fmt_tempo(validos.max())
        except Exception:
            maior_tempo_txt = "N/D"
    m4.metric("Maior tempo", maior_tempo_txt)

    if df_det.empty:
        st.success("Nenhuma câmera offline.")
        return

    col_map = {
        COL_ID_CAM: "ID da Câmera",
        COL_NOME_CAM: "Nome da Câmera",
        COL_ULT_ATU: "Última vez Online",
        COL_OBS: "Observações",
    }
    internal_cols = {COL_WL, COL_EMPRESA, COL_STATUS, "_tempo_off"}
    base_cols = [COL_ID_CAM, COL_NOME_CAM, COL_ULT_ATU, COL_OBS]
    cols_ex = [c for c in base_cols if c in df_det.columns] + [c for c in df_det.columns if c not in internal_cols and c not in base_cols]

    df_show = df_det[cols_ex].copy().rename(columns=col_map)

    if "_tempo_off" in df_det.columns and "Última vez Online" in df_show.columns:
        df_show.insert(
            df_show.columns.get_loc("Última vez Online") + 1,
            "Tempo Offline",
            df_det["_tempo_off"].apply(lambda td: fmt_tempo(td) if hasattr(td, "total_seconds") and td.total_seconds() >= 0 else "N/D").values,
        )

    if "Última vez Online" in df_show.columns:
        df_show["Última vez Online"] = formatar_ultima_atualizacao(df_show["Última vez Online"])

    df_show = df_show.reset_index(drop=True)
    df_show.index += 1
    st.caption("⬆ Ordenado por tempo offline — quem está há mais tempo sem sinal aparece primeiro")
    render_dataframe(df_show, height=min(520, (len(df_show) + 1) * 35 + 3))

    buf_xlsx = io.BytesIO()
    df_show.to_excel(buf_xlsx, index=True, engine="openpyxl")
    buf_xlsx.seek(0)

    buf_csv = io.StringIO()
    df_show.to_csv(buf_csv, index=True)
    buf_csv.seek(0)

    dl_col1, dl_col2 = st.columns([1, 1])
    with dl_col1:
        st.download_button(
            label="⬇ Exportar detalhe (.xlsx)",
            data=buf_xlsx.getvalue(),
            file_name=f"detalhe_cliente_{wl_id}_{agora_sao_paulo_str('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_detalhe_cliente_xlsx_{str(wl_id)}_top",
        )
    with dl_col2:
        st.download_button(
            label="⬇ Exportar detalhe (.csv)",
            data=buf_csv.getvalue(),
            file_name=f"detalhe_cliente_{wl_id}_{agora_sao_paulo_str('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"dl_detalhe_cliente_csv_{str(wl_id)}_top",
        )


def _injetar_css_abas_visiveis() -> None:
    """Evita que abas principais fiquem escondidas quando a barra passa da largura da tela."""
    st.markdown(
        """
        <style>
        div[data-baseweb="tab-list"] {
            flex-wrap: wrap;
            gap: 6px 8px;
        }
        div[data-baseweb="tab-list"] button[role="tab"] {
            flex: 0 0 auto;
            max-width: 100%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


PLANO_DIAS_MAP = {
    "aovivo": 0, "1dia": 1, "3dias": 3, "5dias": 5, "7dias": 7,
    "10dias": 10, "15dias": 15, "30dias": 30, "60dias": 60, "90dias": 90,
}


def _plano_normalizado(valor) -> str:
    return str(valor).strip().lower().replace(" ", "")


def _plano_em_dias(valor):
    return PLANO_DIAS_MAP.get(_plano_normalizado(valor))


def render_aba_padrao_armazenamento(df_origem: pd.DataFrame | None, dados: dict) -> None:
    """Sub-aba de Clientes: detecta câmeras cujo plano de armazenamento foge do padrão do cliente.

    O 'padrão' de cada cliente é o plano majoritário (moda). Câmeras em qualquer outro
    plano são marcadas como fora do padrão, indicando provável configuração errada de
    retenção (ex.: cliente com 25 câmeras de 30 dias e 5 de 7 dias → 5 fora do padrão).
    """
    st.markdown("### 🗄️ Padrão de Armazenamento")
    st.caption(
        "Detecta câmeras com plano de retenção divergente do padrão (plano majoritário) "
        "do cliente — provável configuração errada de armazenamento."
    )

    df_base = df_origem.copy() if df_origem is not None else pd.DataFrame()
    if df_base.empty:
        st.info("Sem dados carregados para avaliar planos de armazenamento.")
        return
    df_base.columns = [str(c).strip() for c in df_base.columns]

    # ── Coluna de plano ──
    if COL_PLANO in df_base.columns:
        plano_col = COL_PLANO
    else:
        plano_col = encontrar_coluna_por_chaves(
            df_base,
            ("planocontratado", "plano", "plan", "retencao", "retention",
             "armazenamento", "storage", "diasarmazenamento"),
            default=None,
        )
    if not plano_col or plano_col not in df_base.columns:
        st.warning(
            "Não encontrei a coluna de plano de armazenamento (`Plano_Contratado`). "
            "Se você lê da base do Supabase, rode o ALTER e reimporte para popular `plano_contratado`."
        )
        return

    # ── Mesmo universo do painel ──
    _tokens_vazios = {"", "nan", "none", "null", "nat", "<na>"}
    # Snapshot do universo completo (antes de qualquer filtro) p/ diagnóstico.
    _serie_plano_full = df_base[plano_col].astype(str).str.strip()
    n_full = len(df_base)
    n_full_plano = int((~_serie_plano_full.str.lower().isin(_tokens_vazios)).sum())

    clientes_map = carregar_clientes()
    if clientes_map and COL_WL in df_base.columns:
        df_base[COL_WL] = df_base[COL_WL].astype(str).str.strip()
        df_base = df_base[df_base[COL_WL].isin(set(clientes_map.keys()))].copy()
    n_apos_clientes = len(df_base)
    if df_base.empty:
        st.info("Nenhuma câmera dos clientes monitorados foi encontrada na base.")
        return

    # ── Filtro opcional: apenas câmeras ativas (ignora inativadas) ──
    col_inat = COL_DATA_INAT if COL_DATA_INAT in df_base.columns else None
    inat_ativa = None
    tem_inat = False
    if col_inat is not None:
        _raw_inat = df_base[col_inat]
        _txt_inat = _raw_inat.astype(str).str.strip().str.lower()
        # "ativa" = SEM data de inativação: null/NaN, vazio, ou tokens de nulo ("nan"/"none"/"nat"...).
        inat_ativa = _raw_inat.isna() | _txt_inat.isin(_tokens_vazios)
        tem_inat = bool((~inat_ativa).any())
    if tem_inat:
        apenas_ativas = st.checkbox(
            "Considerar apenas câmeras ativas (ignora inativadas)",
            value=True,
            key="pad_arm_apenas_ativas",
        )
        if apenas_ativas:
            df_base = df_base[inat_ativa].copy()
    n_apos_ativas = len(df_base)

    # ── Limpeza do plano ──
    df_base["_plano"] = df_base[plano_col].astype(str).str.strip()
    serie_plano_raw = df_base["_plano"].copy()
    df_base = df_base[~df_base["_plano"].str.lower().isin(_tokens_vazios)].copy()
    if df_base.empty:
        st.warning(f"A coluna **{plano_col}** não tem planos preenchidos para avaliar.")
        with st.expander("🔎 Diagnóstico da coluna de plano", expanded=True):
            st.write(f"**No `df_origem` completo (antes de filtros):** {n_full_plano} de {n_full} linhas têm plano preenchido.")
            st.write(f"**Após filtro de clientes** (`nome_clientes.xlsx`): {n_apos_clientes} linhas.")
            st.write(f"**Após filtro de ativas:** {n_apos_ativas} linhas.")
            vc = serie_plano_raw.replace({"": "(vazio)"}).value_counts().head(10)
            if not vc.empty:
                st.write("Valores na coluna de plano (após filtros):")
                st.dataframe(vc.rename("ocorrências"))
            if n_full_plano == 0:
                st.error(
                    "O app **não enxerga plano em nenhuma linha**, mesmo a base tendo o dado. "
                    "Isso é **cache / leitura antiga**: clique em **🔄 Atualizar dados** na barra lateral "
                    "(limpa o cache) e reabra esta aba. Se persistir, o deploy do código de leitura "
                    "(`converter_supabase_para_df_gov`) ainda está desatualizado."
                )
            else:
                st.warning(
                    f"O plano **existe** no `df_origem` ({n_full_plano} linhas), mas **nenhum** dos clientes "
                    "do `nome_clientes.xlsx` (ou das câmeras ativas) tem plano preenchido. "
                    "Ou seja, os clientes do painel não foram reimportados com plano. "
                    "Reimporte marcando **“Importar todos os clientes do CSV”**, "
                    "ou desmarque “apenas câmeras ativas” acima."
                )
        return

    # Nome do cliente e cidade
    if clientes_map:
        df_base["_cliente"] = df_base[COL_WL].map(clientes_map).fillna(
            df_base[COL_WL].apply(lambda x: f"ID {x}")
        )
    elif COL_EMPRESA in df_base.columns:
        df_base["_cliente"] = df_base[COL_EMPRESA].astype(str)
    else:
        df_base["_cliente"] = df_base[COL_WL].astype(str)
    city_col = encontrar_coluna_por_chaves(df_base, ("cidade", "municipio", "city", "prefeitura"), default=None)
    df_base["_cidade"] = df_base[city_col].astype(str).replace({"nan": ""}).str.strip() if city_col else ""

    # ── Controle de dominância mínima ──
    dom_min = st.slider(
        "Dominância mínima para definir o plano padrão (%)",
        min_value=50, max_value=100, value=60, step=5,
        key="pad_arm_dominancia",
        help="Abaixo desse percentual o cliente é tratado como 'sem padrão definido' (planos muito divididos).",
    ) / 100.0

    # ── Cálculo por cliente ──
    resumo = []
    detalhe_rows = []
    sem_padrao = 0
    for wl, g in df_base.groupby(COL_WL):
        vc = g["_plano"].value_counts()
        total = int(vc.sum())
        nome_cli = str(g["_cliente"].iloc[0])
        if len(vc) == 1:
            resumo.append((wl, nome_cli, vc.index[0], 1.0, total, 0, "Conforme"))
            continue
        top_count = int(vc.max())
        candidatos = [p for p in vc.index if int(vc[p]) == top_count]
        # Padrão = plano com MAIS câmeras no cliente (puro por quantidade, sem viés de duração).
        # Em empate na contagem do topo, não há vencedor por quantidade → sem padrão definido.
        if len(candidatos) > 1:
            sem_padrao += 1
            resumo.append((wl, nome_cli, "— (empate)", top_count / total, total, 0, "Sem padrão definido"))
            continue
        plano_padrao = candidatos[0]
        dom = top_count / total
        if dom < dom_min:
            sem_padrao += 1
            resumo.append((wl, nome_cli, "—", dom, total, 0, "Sem padrão definido"))
            continue
        fora = total - top_count
        resumo.append((wl, nome_cli, plano_padrao, dom, total, fora, "Fora do padrão" if fora else "Conforme"))
        if fora:
            dias_padrao = _plano_em_dias(plano_padrao)
            g_fora = g[g["_plano"] != plano_padrao]
            for _, row in g_fora.iterrows():
                dias_atual = _plano_em_dias(row["_plano"])
                if dias_atual is None or dias_padrao is None:
                    direcao = "Diferente"
                elif dias_atual < dias_padrao:
                    direcao = "⬇️ Abaixo do padrão"
                elif dias_atual > dias_padrao:
                    direcao = "⬆️ Acima do padrão"
                else:
                    direcao = "Diferente"
                detalhe_rows.append({
                    "Cliente": nome_cli,
                    "Cidade": row["_cidade"],
                    "Câmera": str(row.get(COL_NOME_CAM, "")),
                    "Plano atual": row["_plano"],
                    "Plano padrão": plano_padrao,
                    "Divergência": direcao,
                    "Status": str(row.get(COL_STATUS, "")).lower(),
                    "_wl": wl,
                })

    df_resumo = pd.DataFrame(resumo, columns=["_wl", "Cliente", "Plano padrão", "_dom", "Câmeras", "Fora", "Situação"])
    df_det = pd.DataFrame(detalhe_rows)

    total_cameras = int(df_resumo["Câmeras"].sum())
    fora_total = int(df_resumo["Fora"].sum())
    clientes_afetados = int((df_resumo["Fora"] > 0).sum())
    conformidade = (1 - fora_total / total_cameras) * 100 if total_cameras else 100.0
    if fora_total and not df_det.empty:
        plano_padrao_comum = df_resumo[df_resumo["Fora"] > 0]["Plano padrão"].mode()
        plano_padrao_comum = plano_padrao_comum.iloc[0] if not plano_padrao_comum.empty else "—"
    else:
        plano_padrao_comum = "—"

    # ── KPIs ──
    st.markdown(f"""
    <div class="compare-hero">
        <div class="compare-title">🗄️ Conformidade de armazenamento por cliente</div>
        <div class="compare-sub">Câmeras cujo plano de retenção difere do plano majoritário do cliente.</div>
    </div>
    <div class="compare-grid">
        <div class="compare-card bad">
            <div class="compare-label">Câmeras fora do padrão</div>
            <div class="compare-value" style="color:#dc2626">{fora_total}</div>
            <div class="compare-note">de {total_cameras} câmeras avaliadas</div>
        </div>
        <div class="compare-card warn">
            <div class="compare-label">Clientes afetados</div>
            <div class="compare-value" style="color:#d97706">{clientes_afetados}</div>
            <div class="compare-note">{sem_padrao} sem padrão definido (&lt; {int(dom_min*100)}%)</div>
        </div>
        <div class="compare-card good">
            <div class="compare-label">Conformidade global</div>
            <div class="compare-value" style="color:#059669">{conformidade:.1f}%</div>
            <div class="compare-note">câmeras no plano padrão</div>
        </div>
        <div class="compare-card neutral">
            <div class="compare-label">Plano padrão mais comum</div>
            <div class="compare-value">{escape_html(str(plano_padrao_comum))}</div>
            <div class="compare-note">entre os clientes afetados</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Relatório por franquia (HTML + PDF) — sempre visível, no topo da aba ──
    st.markdown("#### 📄 Relatório por franquia")
    franq_map = carregar_clientes_franqueado()
    df_resumo["_franqueado"] = (
        df_resumo["_wl"].map(franq_map).fillna("Sem franquia").replace({"": "Sem franquia", "nan": "Sem franquia"})
    )
    if not df_det.empty:
        df_det["_franqueado"] = (
            df_det["_wl"].map(franq_map).fillna("Sem franquia").replace({"": "Sem franquia", "nan": "Sem franquia"})
        )

    franquias = sorted(df_resumo["_franqueado"].astype(str).unique().tolist())
    opcoes_fr = ["Todas as franquias"] + franquias
    sel_fr = st.selectbox("Franquia do relatório", options=opcoes_fr, index=0, key="pad_arm_franquia_rel")

    if sel_fr == "Todas as franquias":
        resumo_fr, det_fr, nome_fr = df_resumo, df_det, "Todas as franquias"
    else:
        resumo_fr = df_resumo[df_resumo["_franqueado"] == sel_fr].copy()
        det_fr = df_det[df_det["_franqueado"] == sel_fr].copy() if not df_det.empty else df_det
        nome_fr = sel_fr

    html_rel = gerar_relatorio_armazenamento_html(nome_fr, resumo_fr, det_fr, dom_min)
    slug = slug_arquivo(nome_fr)
    nome_base = f"relatorio_armazenamento_{slug}_{agora_sao_paulo_str('%Y%m%d')}"

    c_html, c_pdf = st.columns(2)
    c_html.download_button(
        "⬇ Baixar HTML",
        data=html_rel.encode("utf-8"),
        file_name=f"{nome_base}.html",
        mime="text/html",
        use_container_width=True,
        key=f"pad_arm_dl_html_{slug}",
    )
    with c_pdf:
        if st.button("🧾 Gerar PDF", use_container_width=True, key=f"pad_arm_btn_pdf_{slug}"):
            with st.spinner("Gerando PDF..."):
                st.session_state[f"pad_arm_pdf_bytes_{slug}"] = html_para_pdf_bytes(html_rel)
        pdf_bytes = st.session_state.get(f"pad_arm_pdf_bytes_{slug}")
        if pdf_bytes:
            st.download_button(
                "⬇ Baixar PDF",
                data=pdf_bytes,
                file_name=f"{nome_base}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"pad_arm_dl_pdf_{slug}",
            )
        elif pdf_bytes is None and f"pad_arm_pdf_bytes_{slug}" in st.session_state:
            st.warning("Não consegui gerar o PDF. Adicione `xhtml2pdf` ao requirements.txt e reinicie o app.")

    with st.expander("👁 Pré-visualizar relatório"):
        st.components.v1.html(html_rel, height=600, scrolling=True)

    st.divider()

    if fora_total == 0:
        st.success("✅ Nenhuma câmera fora do padrão de armazenamento com os critérios atuais.")
        return

    # ── Ranking de clientes com mais câmeras fora ──
    st.markdown("#### Clientes com mais câmeras fora do padrão")
    df_rank = df_resumo[df_resumo["Fora"] > 0].copy()
    qtd_max = st.slider(
        "Clientes no gráfico",
        min_value=5,
        max_value=max(5, min(40, len(df_rank))),
        value=min(15, len(df_rank)),
        key="pad_arm_qtd_clientes",
    )
    top_rank = df_rank.sort_values("Fora", ascending=False).head(int(qtd_max)).sort_values("Fora", ascending=True)
    max_x = max(2, int(top_rank["Fora"].max()) + 1)
    altura = max(360, min(720, 40 * len(top_rank) + 130))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top_rank["Fora"],
        y=top_rank["Cliente"].astype(str),
        orientation="h",
        marker=dict(color="#dc2626", line=dict(color="#ffffff", width=0.5)),
        text=top_rank["Fora"],
        textposition="outside",
        customdata=top_rank[["Plano padrão", "Câmeras"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Fora do padrão: %{x}<br>"
            "Plano padrão: %{customdata[0]}<br>"
            "Total de câmeras: %{customdata[1]}<extra></extra>"
        ),
    ))
    fig.update_layout(
        **pdefaults(),
        height=altura,
        margin=dict(l=10, r=60, t=10, b=35),
        xaxis=dict(
            title="Câmeras fora do padrão",
            range=[0, max_x],
            gridcolor="#E9D5FF",
            tickfont=dict(color="#8B7AA3", size=10),
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            type="category",
            categoryorder="array",
            categoryarray=top_rank["Cliente"].astype(str).tolist(),
            tickfont=dict(color="#6B5A7A", size=11),
            automargin=True,
        ),
        showlegend=False,
        bargap=0.35,
    )
    st.plotly_chart(fig, use_container_width=True, key="padrao_armazenamento_ranking")

    # ── Drilldown por cliente ──
    st.markdown("#### Detalhe por cliente")
    opcoes = df_rank.sort_values("Fora", ascending=False)["Cliente"].astype(str).tolist()
    cliente_sel = st.selectbox("Cliente", options=opcoes, index=0, key="pad_arm_cliente_sel")
    df_cli = df_det[df_det["Cliente"] == cliente_sel].copy()
    info_cli = df_rank[df_rank["Cliente"] == cliente_sel].iloc[0]
    st.markdown(
        f"**{escape_html(cliente_sel)}** — plano padrão **{escape_html(str(info_cli['Plano padrão']))}** "
        f"· {int(info_cli['Fora'])} de {int(info_cli['Câmeras'])} câmeras fora do padrão "
        f"({info_cli['_dom']*100:.0f}% de dominância)."
    )
    render_dataframe(
        df_cli.drop(columns=["_wl"], errors="ignore").reset_index(drop=True),
        height=min(420, 80 + 38 * max(1, len(df_cli))),
    )

    # ── Tabela completa + download ──
    st.markdown("#### Todas as câmeras fora do padrão")
    df_full = df_det.drop(columns=["_wl"], errors="ignore").sort_values(["Cliente", "Câmera"]).reset_index(drop=True)
    render_dataframe(df_full, height=480)
    csv_out = df_full.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "📥 Baixar câmeras fora do padrão (CSV)",
        data=csv_out,
        file_name=f"padrao_armazenamento_{agora_sao_paulo_str('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_padrao_armazenamento_csv_v1",
    )


def render_aba_ultima_camera_cadastrada(df_origem: pd.DataFrame | None, dados: dict) -> None:
    """Sub-aba de Clientes: ranking por cidade do tempo desde o último cadastro de câmera.

    Para cada cidade pegamos a câmera com a DATA DE CADASTRO mais recente e calculamos
    há quanto tempo isso aconteceu. O gráfico de área (mesmo estilo do 'LPRs Offline')
    lista do topo (mais tempo sem cadastrar) para a base (cadastrou recentemente).
    """
    st.markdown("### 🆕 Última Câmera Cadastrada")
    st.caption(
        "Ranking por cidade pelo tempo desde o cadastro da câmera mais recente — "
        "do topo (há mais tempo sem cadastrar) para a base (cadastrou há menos tempo)."
    )

    df_base = df_origem.copy() if df_origem is not None else pd.DataFrame()
    if df_base.empty:
        st.info("Sem dados carregados para avaliar cadastros de câmeras.")
        return

    df_base.columns = [str(c).strip() for c in df_base.columns]

    # Mantém o mesmo universo do painel: apenas clientes do nome_clientes.xlsx.
    clientes_map = carregar_clientes()
    if clientes_map and COL_WL in df_base.columns:
        df_base[COL_WL] = df_base[COL_WL].astype(str).str.strip()
        df_base = df_base[df_base[COL_WL].isin(set(clientes_map.keys()))].copy()

    if df_base.empty:
        st.info("Nenhuma câmera dos clientes monitorados foi encontrada na base.")
        return

    # ── 1) Detecta a coluna com a DATA DE CADASTRO da câmera ──
    if COL_DATA_CAD in df_base.columns:
        col_cad_auto = COL_DATA_CAD
    else:
        col_cad_auto = encontrar_coluna_por_chaves(
            df_base,
            (
                "datadecadastro", "datacadastro", "data_cadastro", "cadastro",
                "datacriacao", "data_criacao", "criacao", "criada", "created",
                "createdat", "datainclusao", "inclusao", "datainstalacao", "instalacao",
            ),
            default=None,
        )
    colunas_disp = list(df_base.columns)
    idx_default = colunas_disp.index(col_cad_auto) if col_cad_auto in colunas_disp else 0
    col_cadastro = st.selectbox(
        "Coluna com a DATA DE CADASTRO da câmera",
        options=colunas_disp,
        index=idx_default,
        key="ultima_cam_col_cadastro",
        help="Detectada automaticamente pelo nome. Ajuste aqui se a coluna tiver outro nome.",
    )

    # ── 2) Detecta a coluna de cidade ──
    city_col = encontrar_coluna_por_chaves(
        df_base, ("cidade", "municipio", "city", "prefeitura"), default=None
    )
    if not city_col or city_col not in df_base.columns:
        st.warning("Não encontrei uma coluna de cidade na base para agrupar os cadastros.")
        return

    # ── 3) Parse das datas (reaproveita o parser do CSV da Camerite) ──
    df_base["_data_cadastro"] = parse_ultima_atualizacao(df_base[col_cadastro])
    df_validas = df_base[df_base["_data_cadastro"].notna()].copy()
    if df_validas.empty:
        st.warning(
            f"A coluna **{col_cadastro}** não tem datas reconhecíveis. "
            "Selecione a coluna correta de data de cadastro acima."
        )
        return

    df_validas["_cidade"] = df_validas[city_col].astype(str).replace({"nan": ""}).str.strip()
    df_validas = df_validas[df_validas["_cidade"] != ""].copy()
    if df_validas.empty:
        st.warning("Nenhuma cidade preenchida nas linhas com data de cadastro válida.")
        return

    agora = agora_sao_paulo()

    # ── 4) Por cidade: câmera MAIS recente (max da data de cadastro) ──
    grp = df_validas.groupby("_cidade", as_index=False).agg(
        ultimo_cadastro=("_data_cadastro", "max"),
        cameras=("_data_cadastro", "count"),
    )
    grp["_delta"] = grp["ultimo_cadastro"].apply(
        lambda d: max(agora - d, timedelta(seconds=0)) if pd.notna(d) else timedelta(seconds=0)
    )
    grp["dias_sem_cadastrar"] = grp["_delta"].apply(lambda x: int(x.total_seconds() // 86400))
    grp["tempo_sem_cadastrar"] = grp["_delta"].apply(fmt_tempo)
    grp["ultimo_cadastro_fmt"] = grp["ultimo_cadastro"].dt.strftime("%d/%m/%Y")

    # Linha mais recente por cidade (para mostrar nome da câmera / cliente).
    idx_recent = df_validas.groupby("_cidade")["_data_cadastro"].idxmax()
    df_recent = df_validas.loc[idx_recent].copy()
    if clientes_map:
        df_recent["_cliente"] = df_recent[COL_WL].map(clientes_map).fillna(
            df_recent[COL_WL].apply(lambda x: f"ID {x}")
        )
    elif COL_EMPRESA in df_recent.columns:
        df_recent["_cliente"] = df_recent[COL_EMPRESA].astype(str)
    else:
        df_recent["_cliente"] = ""
    nomes_cam = df_recent[COL_NOME_CAM].astype(str) if COL_NOME_CAM in df_recent.columns else ""
    mapa_cam = dict(zip(df_recent["_cidade"], nomes_cam)) if COL_NOME_CAM in df_recent.columns else {}
    mapa_cli = dict(zip(df_recent["_cidade"], df_recent["_cliente"].astype(str)))
    grp["camera_recente"] = grp["_cidade"].map(mapa_cam).fillna("")
    grp["cliente_recente"] = grp["_cidade"].map(mapa_cli).fillna("")

    grp = grp.sort_values("dias_sem_cadastrar", ascending=False).reset_index(drop=True)

    # ── 5) KPIs (mesmo visual do Radar LPR Offline) ──
    total_cidades = int(len(grp))
    pior = grp.iloc[0] if total_cidades else None
    melhor = grp.iloc[-1] if total_cidades else None
    media_dias = int(grp["dias_sem_cadastrar"].mean()) if total_cidades else 0
    cidades_30d = int((grp["dias_sem_cadastrar"] > 30).sum())

    st.markdown(f"""
    <div class="compare-hero">
        <div class="compare-title">🆕 Tempo desde o último cadastro por cidade</div>
        <div class="compare-sub">Baseado na câmera com cadastro mais recente em cada cidade da carteira filtrada.</div>
    </div>
    <div class="compare-grid">
        <div class="compare-card bad">
            <div class="compare-label">Há mais tempo sem cadastrar</div>
            <div class="compare-value" style="color:#dc2626">{(pior['tempo_sem_cadastrar'] if pior is not None else 'N/D')}</div>
            <div class="compare-note">{escape_html(str(pior['_cidade'])) if pior is not None else '—'}</div>
        </div>
        <div class="compare-card warn">
            <div class="compare-label">Cidades &gt; 30 dias</div>
            <div class="compare-value" style="color:#d97706">{cidades_30d}</div>
            <div class="compare-note">de {total_cidades} cidades com cadastro datado</div>
        </div>
        <div class="compare-card neutral">
            <div class="compare-label">Média sem cadastrar</div>
            <div class="compare-value">{media_dias} dias</div>
            <div class="compare-note">média entre as {total_cidades} cidades</div>
        </div>
        <div class="compare-card good">
            <div class="compare-label">Cadastro mais recente</div>
            <div class="compare-value" style="color:#059669">{(melhor['tempo_sem_cadastrar'] if melhor is not None else 'N/D')}</div>
            <div class="compare-note">{escape_html(str(melhor['_cidade'])) if melhor is not None else '—'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 6) Gráfico de área (idêntico ao 'LPRs Offline') ──
    st.markdown("#### Ranking por cidade")
    qtd_max = st.slider(
        "Cidades no gráfico",
        min_value=5,
        max_value=max(5, min(40, total_cidades)),
        value=min(15, total_cidades),
        key="ultima_cam_qtd_cidades",
    )

    top_area = grp.head(int(qtd_max)).sort_values("dias_sem_cadastrar", ascending=True).copy()
    top_area["Cidade eixo"] = top_area["_cidade"].astype(str)
    max_area = max(3, int(top_area["dias_sem_cadastrar"].max()) + 1) if not top_area.empty else 3
    altura_area = max(380, min(720, 42 * len(top_area) + 140))

    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(
        name="Dias sem cadastrar",
        x=top_area["dias_sem_cadastrar"],
        y=top_area["Cidade eixo"],
        mode="lines+markers+text",
        fill="tozerox",
        line=dict(color="#dc2626", width=3.0, shape="spline", smoothing=0.65),
        marker=dict(color="#dc2626", size=9, line=dict(color="#ffffff", width=1)),
        fillcolor="rgba(220, 38, 38, 0.18)",
        text=top_area["tempo_sem_cadastrar"],
        textposition="middle right",
        customdata=top_area[["cliente_recente", "camera_recente", "ultimo_cadastro_fmt", "cameras"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Cliente: %{customdata[0]}<br>"
            "Última câmera: %{customdata[1]}<br>"
            "Cadastrada em: %{customdata[2]}<br>"
            "Câmeras com data: %{customdata[3]}<br>"
            "Dias sem cadastrar: %{x}<extra></extra>"
        ),
    ))
    fig_area.update_layout(
        **pdefaults(),
        height=altura_area,
        margin=dict(l=10, r=70, t=10, b=35),
        xaxis=dict(
            title="Dias desde o último cadastro",
            range=[0, max_area],
            gridcolor="#E9D5FF",
            tickfont=dict(color="#8B7AA3", size=10),
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            type="category",
            categoryorder="array",
            categoryarray=top_area["Cidade eixo"].tolist(),
            tickfont=dict(color="#6B5A7A", size=11),
            automargin=True,
        ),
        showlegend=False,
        hovermode="closest",
    )
    st.plotly_chart(fig_area, use_container_width=True, key="ultima_camera_cadastrada_area_horizontal")

    # ── 7) Detalhamento + download ──
    st.markdown("#### Detalhamento por cidade")
    busca = st.text_input(
        "Buscar por cidade, cliente ou câmera",
        key="busca_ultima_camera_cadastrada",
    )
    df_lista = grp.copy()
    if busca.strip():
        termo = busca.strip().lower()
        texto_busca = (
            df_lista["_cidade"].astype(str) + " " +
            df_lista["cliente_recente"].astype(str) + " " +
            df_lista["camera_recente"].astype(str)
        ).str.lower()
        df_lista = df_lista[texto_busca.str.contains(re.escape(termo), na=False)].copy()

    df_lista = df_lista[[
        "_cidade", "tempo_sem_cadastrar", "dias_sem_cadastrar",
        "ultimo_cadastro_fmt", "cliente_recente", "camera_recente", "cameras",
    ]].rename(columns={
        "_cidade": "Cidade",
        "tempo_sem_cadastrar": "Tempo sem cadastrar",
        "dias_sem_cadastrar": "Dias",
        "ultimo_cadastro_fmt": "Último cadastro",
        "cliente_recente": "Cliente",
        "camera_recente": "Última câmera",
        "cameras": "Câmeras c/ data",
    })
    render_dataframe(df_lista, height=480)

    csv_out = df_lista.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "📥 Baixar ranking de cadastros em CSV",
        data=csv_out,
        file_name=f"ultima_camera_cadastrada_{agora_sao_paulo_str('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
        key="dl_ultima_camera_cadastrada_csv_v1",
    )


def render_aba_tendencia(dados: dict) -> None:
    """Aba Tendencia: evolucao do percentual offline por cliente ou franquia ao longo dos snapshots."""
    st.markdown("### 📈 Tendência")
    st.caption("Evolução do percentual offline a partir dos snapshots salvos.")

    _render_tendencia_alertas(dados)
    st.divider()

    col_periodo, col_modo, col_refresh = st.columns([1, 1.7, 0.7])
    with col_periodo:
        dias = st.selectbox(
            "Período",
            options=[7, 14, 30, 60, 90],
            index=2,
            format_func=lambda d: f"Últimos {d} dias",
            key="tend_periodo",
        )
    with col_modo:
        modo = st.radio(
            "Filtrar por",
            options=["Cliente", "Franquia"],
            horizontal=True,
            key="tend_modo",
        )
    with col_refresh:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", key="tend_refresh", use_container_width=True,
                     help="Recarrega os snapshots do Supabase (ignora o cache), trazendo a importação mais recente."):
            for _fn in (carregar_historico_clientes, _snapshot_datas_df):
                try:
                    _fn.clear()
                except Exception:
                    pass
            st.rerun()

    with st.spinner("Carregando histórico de snapshots..."):
        df_hist = carregar_historico_clientes(dias)

    if df_hist.empty:
        st.info(f"Nenhum snapshot encontrado nos últimos {dias} dias.")
        return

    df_hist["gravado_dt"] = pd.to_datetime(df_hist["gravado_em"], errors="coerce")
    df_hist = df_hist[df_hist["gravado_dt"].notna()].copy()
    if df_hist.empty:
        st.info("Os snapshots encontrados não possuem data válida para montar a tendência.")
        return

    # Diagnóstico de atualização: mostra o snapshot mais recente efetivamente carregado.
    _ult_dt = df_hist["gravado_dt"].max()
    _n_snaps = df_hist["snapshot_id"].nunique()
    if pd.notna(_ult_dt):
        st.caption(
            f"Snapshot mais recente carregado: **{_ult_dt.strftime('%d/%m/%Y %H:%M')}** "
            f"· {_n_snaps} snapshots no período. Se a última importação não aparece aqui, clique em **Atualizar**."
        )

    if modo == "Franquia":
        _render_tendencia_por_franquia(df_hist, dados)
    else:
        _render_tendencia_por_cliente(df_hist, dados)


def _render_tendencia_alertas(dados: dict, dias: int = 14, top_n: int = 5) -> None:
    """Destaca as tendências mais preocupantes: maiores aumentos de offline nas últimas 2 semanas.

    Compara o primeiro e o último snapshot de cada cliente dentro da janela e ranqueia
    pela piora (aumento) em pontos percentuais e em número absoluto de câmeras offline.
    """
    semanas = dias // 7
    if semanas >= 1 and dias % 7 == 0:
        janela_txt = f"últimas {semanas} semana{'s' if semanas > 1 else ''}"
    else:
        janela_txt = f"últimos {dias} dias"
    st.markdown(f"#### 🚨 Tendências mais preocupantes ({janela_txt})")

    with st.spinner("Analisando piora recente..."):
        df = carregar_historico_clientes(dias)

    if df is None or df.empty:
        st.info("Sem histórico suficiente para calcular as tendências recentes.")
        return

    df = df.copy()
    df["gravado_dt"] = pd.to_datetime(df["gravado_em"], errors="coerce")
    df = df[df["gravado_dt"].notna()].copy()
    df["wl_id"] = df["wl_id"].astype(str).str.strip()
    for col in ["pct_offline", "offline", "total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df.sort_values("gravado_dt")
    if df.empty:
        st.info("Sem histórico com data válida para calcular as tendências recentes.")
        return

    # Nome de exibição por cliente.
    nomes = (
        df[["wl_id", "nome_cliente"]].drop_duplicates("wl_id").set_index("wl_id")["nome_cliente"].to_dict()
    )

    def nome_de(wl: str) -> str:
        v = (dados or {}).get(wl) or (dados or {}).get(str(wl))
        if isinstance(v, dict):
            return str(v.get("cidade_estado") or v.get("nome_cliente") or nomes.get(wl) or f"ID {wl}")
        return str(nomes.get(wl) or f"ID {wl}")

    # Resumo por cliente: primeiro x último snapshot da janela.
    linhas = []
    for wl, grupo in df.groupby("wl_id"):
        if grupo["gravado_dt"].nunique() < 2:
            continue  # precisa de ao menos dois pontos para medir aumento
        primeiro = grupo.iloc[0]
        ultimo = grupo.iloc[-1]
        linhas.append({
            "wl_id": wl,
            "nome": nome_de(wl),
            "delta_pct": float(ultimo["pct_offline"] - primeiro["pct_offline"]),
            "delta_off": int(ultimo["offline"] - primeiro["offline"]),
            "pct_fim": float(ultimo["pct_offline"]),
            "off_fim": int(ultimo["offline"]),
            "total_fim": int(ultimo["total"]),
        })

    if not linhas:
        st.info("Ainda não há dois snapshots por cliente na janela para medir tendência de piora.")
        return

    resumo = pd.DataFrame(linhas)
    top_pct = resumo[resumo["delta_pct"] > 0].nlargest(top_n, "delta_pct")
    top_off = resumo[resumo["delta_off"] > 0].nlargest(top_n, "delta_off")

    def _grafico_trajetoria(top_df: pd.DataFrame, valor_col: str, delta_col: str,
                            titulo: str, sufixo: str, key: str, faixas: bool) -> None:
        if top_df.empty:
            st.success("Nenhum cliente com piora nesse critério na janela. 🎉")
            return
        fig = go.Figure()
        if faixas:
            fig.add_hrect(y0=0, y1=5, fillcolor="#dff8f3", opacity=0.20, line_width=0, layer="below")
            fig.add_hrect(y0=5, y1=10, fillcolor="#fef9c3", opacity=0.20, line_width=0, layer="below")
            fig.add_hrect(y0=10, y1=100, fillcolor="#fee2e2", opacity=0.16, line_width=0, layer="below")
        for _, r in top_df.iterrows():
            grupo = df[df["wl_id"] == r["wl_id"]].sort_values("gravado_dt")
            delta = r[delta_col]
            if delta_col == "delta_pct":
                rotulo_delta = f"+{delta:.1f} p.p."
            else:
                rotulo_delta = f"+{int(delta)} câm"
            nome_leg = f"{r['nome']} ({rotulo_delta})"
            fig.add_trace(go.Scatter(
                x=grupo["gravado_dt"],
                y=grupo[valor_col],
                mode="lines+markers",
                line=dict(width=2.4, shape="spline", smoothing=0.6),
                marker=dict(size=6),
                name=nome_leg[:34],
                text=[
                    f"<b>{escape_html(r['nome'])}</b><br>{d.strftime('%d/%m/%Y %H:%M')}<br>"
                    f"{titulo}: <b>{v:.1f}{sufixo}</b>" if sufixo else
                    f"<b>{escape_html(r['nome'])}</b><br>{d.strftime('%d/%m/%Y %H:%M')}<br>"
                    f"{titulo}: <b>{int(v)}</b>"
                    for d, v in zip(grupo["gravado_dt"], grupo[valor_col])
                ],
                hovertemplate="%{text}<extra></extra>",
            ))
        layout = {k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]}
        fig.update_layout(
            **layout,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=360,
            margin=dict(l=10, r=20, t=10, b=60),
            xaxis=dict(tickangle=-35, gridcolor="#F3E8FF", tickformat="%d/%m %H:%M"),
            yaxis=dict(ticksuffix=sufixo, gridcolor="#F3E8FF", rangemode="tozero"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        st.plotly_chart(fig, use_container_width=True, key=key)

    st.markdown("**Maior aumento em % offline (p.p.)**")
    _grafico_trajetoria(top_pct, "pct_offline", "delta_pct", "% Offline", "%", "tend_alerta_pct", faixas=True)

    st.markdown("**Maior aumento em câmeras offline (unidades)**")
    _grafico_trajetoria(top_off, "offline", "delta_off", "Câmeras offline", "", "tend_alerta_off", faixas=False)


def _render_tendencia_por_cliente(df_hist: pd.DataFrame, dados: dict) -> None:
    """Tendência de um cliente (whitelabel) individual ao longo dos snapshots."""
    clientes_hist = (
        df_hist[["wl_id", "nome_cliente"]]
        .drop_duplicates("wl_id")
        .set_index("wl_id")["nome_cliente"]
        .to_dict()
    )
    for wl_id, v in (dados or {}).items():
        clientes_hist.setdefault(str(wl_id), v.get("cidade_estado") or v.get("nome_cliente", f"ID {wl_id}"))

    opcoes_ids = sorted(clientes_hist.keys(), key=lambda wl: clientes_hist.get(wl, wl))
    wl_sel = st.selectbox(
        "Cliente",
        options=opcoes_ids,
        format_func=lambda wl: clientes_hist.get(wl, wl),
        key="tend_cliente",
    )

    df_cli = (
        df_hist[df_hist["wl_id"].astype(str) == str(wl_sel)]
        .sort_values("gravado_dt")
        .copy()
    )
    if df_cli.empty:
        st.warning(f"Nenhum snapshot encontrado para **{clientes_hist.get(wl_sel, wl_sel)}** no período.")
        return

    nome_cliente = clientes_hist.get(wl_sel, wl_sel)
    pct_atual = float(df_cli["pct_offline"].iloc[-1])
    pct_inicio = float(df_cli["pct_offline"].iloc[0])
    pct_max = float(df_cli["pct_offline"].max())
    pct_min = float(df_cli["pct_offline"].min())
    pct_medio = float(df_cli["pct_offline"].mean())
    variacao = pct_atual - pct_inicio

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("% Offline atual", f"{pct_atual:.1f}%")
    m2.metric("Variação", f"{variacao:+.1f} p.p.")
    m3.metric("Pior momento", f"{pct_max:.1f}%")
    m4.metric("Melhor momento", f"{pct_min:.1f}%")
    m5.metric("Média", f"{pct_medio:.1f}%")

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=5, fillcolor="#dff8f3", opacity=0.25, line_width=0, layer="below")
    fig.add_hrect(y0=5, y1=10, fillcolor="#fef9c3", opacity=0.25, line_width=0, layer="below")
    fig.add_hrect(y0=10, y1=100, fillcolor="#fee2e2", opacity=0.20, line_width=0, layer="below")
    fig.add_trace(go.Scatter(
        x=df_cli["gravado_dt"],
        y=df_cli["pct_offline"].tolist(),
        mode="lines+markers",
        line=dict(color="#7C3AED", width=2.4, shape="spline", smoothing=0.6),
        marker=dict(color=[cor_hex(v) for v in df_cli["pct_offline"]], size=8, line=dict(color="#ffffff", width=1)),
        text=[
            f"<b>{escape_html(r['label'])}</b><br>{r['gravado_dt'].strftime('%d/%m/%Y %H:%M')}<br>"
            f"% Offline: <b>{r['pct_offline']:.1f}%</b><br>Offline: {int(r['offline'])} de {int(r['total'])}"
            for _, r in df_cli.iterrows()
        ],
        hovertemplate="%{text}<extra></extra>",
        name=nome_cliente[:28],
    ))
    fig.add_hline(y=5, line_dash="dot", line_color="#14b8a6", line_width=1)
    fig.add_hline(y=10, line_dash="dot", line_color="#f59e0b", line_width=1)
    fig.update_layout(
        **{k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=10, r=30, t=20, b=70),
        xaxis=dict(tickangle=-35, gridcolor="#F3E8FF", tickformat="%d/%m %H:%M"),
        yaxis=dict(ticksuffix="%", gridcolor="#F3E8FF", range=[0, max(pct_max * 1.25, 12)]),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"tend_line_{wl_sel}")

    with st.expander("Ver tabela de dados brutos"):
        df_tabela = df_cli[["gravado_dt", "label", "total", "offline", "pct_offline"]].copy()
        df_tabela["gravado_dt"] = df_tabela["gravado_dt"].dt.strftime("%d/%m/%Y %H:%M")
        df_tabela.columns = ["Data", "Rótulo", "Total", "Offline", "% Offline"]
        df_tabela["% Offline"] = df_tabela["% Offline"].apply(lambda v: f"{v:.1f}%")
        render_dataframe(df_tabela, height=min(400, (len(df_tabela) + 1) * 35 + 3))


def _render_tendencia_por_franquia(df_hist: pd.DataFrame, dados: dict) -> None:
    """Tendência consolidada de uma franquia: linha total + uma linha por cidade."""
    franqueados_map = carregar_clientes_franqueado()  # {wl_id: Franqueado}
    if not franqueados_map:
        st.info(
            "Nenhum dado de franquia encontrado. Confira se o arquivo "
            "**nome_clientes.xlsx** possui a coluna *Franqueado*."
        )
        return

    df = df_hist.copy()
    df["wl_id"] = df["wl_id"].astype(str).str.strip()
    df["franquia"] = df["wl_id"].map(lambda w: (franqueados_map.get(w, "") or "").strip())
    df = df[df["franquia"] != ""].copy()
    if df.empty:
        st.info("Nenhum snapshot do período possui cliente vinculado a uma franquia.")
        return

    franquias = sorted(df["franquia"].unique(), key=lambda s: s.lower())
    fr_sel = st.selectbox("Franquia", options=franquias, key="tend_franquia")

    df_fr = df[df["franquia"] == fr_sel].sort_values("gravado_dt").copy()
    if df_fr.empty:
        st.warning(f"Nenhum snapshot encontrado para **{fr_sel}** no período.")
        return

    # Nome de exibição de cada cidade (whitelabel) da franquia.
    nomes_cidade: dict[str, str] = {}
    for wl in df_fr["wl_id"].unique():
        v = (dados or {}).get(wl) or (dados or {}).get(str(wl))
        if isinstance(v, dict):
            nomes_cidade[wl] = str(v.get("cidade_estado") or v.get("nome_cliente") or f"ID {wl}")
        else:
            nome = df_fr.loc[df_fr["wl_id"] == wl, "nome_cliente"].iloc[-1]
            nomes_cidade[wl] = str(nome or f"ID {wl}")

    n_cidades = df_fr["wl_id"].nunique()

    # Agregado da franquia por snapshot: soma total e offline de todas as cidades.
    agg = (
        df_fr.groupby(["snapshot_id", "gravado_dt"], as_index=False)
        .agg(total=("total", "sum"), offline=("offline", "sum"), label=("label", "first"))
        .sort_values("gravado_dt")
        .reset_index(drop=True)
    )
    agg["pct_offline"] = agg.apply(
        lambda r: (float(r["offline"]) / float(r["total"]) * 100.0) if r["total"] else 0.0,
        axis=1,
    )

    pct_atual = float(agg["pct_offline"].iloc[-1])
    pct_inicio = float(agg["pct_offline"].iloc[0])
    pct_max = float(agg["pct_offline"].max())
    pct_min = float(agg["pct_offline"].min())
    variacao = pct_atual - pct_inicio

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("% Offline atual (franquia)", f"{pct_atual:.1f}%")
    m2.metric("Variação", f"{variacao:+.1f} p.p.")
    m3.metric("Pior momento", f"{pct_max:.1f}%")
    m4.metric("Melhor momento", f"{pct_min:.1f}%")
    m5.metric("Cidades", f"{n_cidades}")

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=5, fillcolor="#dff8f3", opacity=0.25, line_width=0, layer="below")
    fig.add_hrect(y0=5, y1=10, fillcolor="#fef9c3", opacity=0.25, line_width=0, layer="below")
    fig.add_hrect(y0=10, y1=100, fillcolor="#fee2e2", opacity=0.20, line_width=0, layer="below")

    # Uma linha por cidade (finas, para leitura individual da tendência).
    for wl, grupo in df_fr.groupby("wl_id"):
        grupo = grupo.sort_values("gravado_dt")
        nome_cid = nomes_cidade.get(wl, wl)
        fig.add_trace(go.Scatter(
            x=grupo["gravado_dt"],
            y=grupo["pct_offline"].tolist(),
            mode="lines+markers",
            line=dict(width=1.8, shape="spline", smoothing=0.6),
            marker=dict(size=5),
            opacity=0.8,
            name=nome_cid[:24],
            text=[
                f"<b>{escape_html(nome_cid)}</b><br>{r['gravado_dt'].strftime('%d/%m/%Y %H:%M')}<br>"
                f"% Offline: <b>{r['pct_offline']:.1f}%</b><br>Offline: {int(r['offline'])} de {int(r['total'])}"
                for _, r in grupo.iterrows()
            ],
            hovertemplate="%{text}<extra></extra>",
        ))

    # Linha agregada da franquia (destaque).
    fig.add_trace(go.Scatter(
        x=agg["gravado_dt"],
        y=agg["pct_offline"].tolist(),
        mode="lines+markers",
        line=dict(color="#171126", width=3, shape="spline", smoothing=0.6),
        marker=dict(color=[cor_hex(v) for v in agg["pct_offline"]], size=9, line=dict(color="#ffffff", width=1)),
        name="Franquia (total)",
        text=[
            f"<b>Franquia · {escape_html(fr_sel)}</b><br>{r['gravado_dt'].strftime('%d/%m/%Y %H:%M')}<br>"
            f"% Offline: <b>{r['pct_offline']:.1f}%</b><br>Offline: {int(r['offline'])} de {int(r['total'])}"
            for _, r in agg.iterrows()
        ],
        hovertemplate="%{text}<extra></extra>",
    ))

    fig.add_hline(y=5, line_dash="dot", line_color="#14b8a6", line_width=1)
    fig.add_hline(y=10, line_dash="dot", line_color="#f59e0b", line_width=1)
    y_top = max(pct_max * 1.25, float(df_fr["pct_offline"].max()) * 1.1, 12)
    fig.update_layout(
        **{k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=440,
        margin=dict(l=10, r=30, t=20, b=70),
        xaxis=dict(tickangle=-35, gridcolor="#F3E8FF", tickformat="%d/%m %H:%M"),
        yaxis=dict(ticksuffix="%", gridcolor="#F3E8FF", range=[0, y_top]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"tend_fr_{slug_arquivo(fr_sel)}")

    with st.expander("Ver tabela consolidada da franquia"):
        df_tab = agg[["gravado_dt", "label", "total", "offline", "pct_offline"]].copy()
        df_tab["gravado_dt"] = df_tab["gravado_dt"].dt.strftime("%d/%m/%Y %H:%M")
        df_tab.columns = ["Data", "Rótulo", "Total", "Offline", "% Offline"]
        df_tab["% Offline"] = df_tab["% Offline"].apply(lambda v: f"{v:.1f}%")
        render_dataframe(df_tab, height=min(400, (len(df_tab) + 1) * 35 + 3))

    with st.expander("Ver tabela por cidade"):
        df_cid = df_fr[["gravado_dt", "wl_id", "total", "offline", "pct_offline"]].copy()
        df_cid["Cidade"] = df_cid["wl_id"].map(lambda w: nomes_cidade.get(w, w))
        df_cid["gravado_dt"] = df_cid["gravado_dt"].dt.strftime("%d/%m/%Y %H:%M")
        df_cid = df_cid[["gravado_dt", "Cidade", "total", "offline", "pct_offline"]]
        df_cid.columns = ["Data", "Cidade", "Total", "Offline", "% Offline"]
        df_cid["% Offline"] = df_cid["% Offline"].apply(lambda v: f"{v:.1f}%")
        df_cid = df_cid.sort_values(["Cidade", "Data"])
        render_dataframe(df_cid, height=min(500, (len(df_cid) + 1) * 35 + 3))


def _area_horizontal_franquia(
    df_plot: pd.DataFrame,
    valor_col: str,
    label_col: str,
    cor: str,
    cor_fill: str,
    titulo_eixo: str,
    key: str,
    sufixo: str = "",
    formato_texto=None,
) -> None:
    """Renderiza um gráfico de área horizontal (padrão 'LPRs Offline') para franquias.

    formato_texto recebe a linha (pd.Series) e devolve o rótulo exibido no ponto.
    """
    dfp = df_plot.sort_values(valor_col, ascending=True).copy()
    dfp["Franquia eixo"] = dfp["Franqueado"].astype(str)
    if formato_texto is None:
        formato_texto = lambda r: f"{r[valor_col]:g}{sufixo}"
    dfp["_texto"] = dfp.apply(formato_texto, axis=1)

    max_x = float(dfp[valor_col].max()) if not dfp.empty else 0.0
    max_x = max(max_x * 1.28, 1.0)
    altura = max(320, min(760, 44 * len(dfp) + 130))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name=titulo_eixo,
        x=dfp[valor_col],
        y=dfp["Franquia eixo"],
        mode="lines+markers+text",
        fill="tozerox",
        line=dict(color=cor, width=3.0, shape="spline", smoothing=0.65),
        marker=dict(color=cor, size=9, line=dict(color="#ffffff", width=1)),
        fillcolor=cor_fill,
        text=dfp["_texto"],
        textposition="middle right",
        textfont=dict(color="#6B5A7A", size=11),
        customdata=dfp[["Cidades", "Total", "Offline", "Online", "Pct"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Cidades: %{customdata[0]}<br>"
            "Total de câmeras: %{customdata[1]}<br>"
            "Offline: %{customdata[2]}<br>"
            "Online: %{customdata[3]}<br>"
            "Perc. Offline: %{customdata[4]:.1f}%<extra></extra>"
        ),
    ))
    fig.update_layout(
        **pdefaults(),
        height=altura,
        margin=dict(l=10, r=110, t=10, b=35),
        xaxis=dict(
            title=titulo_eixo,
            range=[0, max_x],
            ticksuffix=sufixo,
            gridcolor="#E9D5FF",
            tickfont=dict(color="#8B7AA3", size=10),
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            type="category",
            categoryorder="array",
            categoryarray=dfp["Franquia eixo"].tolist(),
            tickfont=dict(color="#6B5A7A", size=11),
            automargin=True,
        ),
        showlegend=False,
        hovermode="closest",
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_aba_total_por_franquia(df_clientes_ops: pd.DataFrame) -> None:
    """Total por Franquia: câmeras offline e % offline consolidados por franquia (todas as cidades somadas)."""
    st.markdown("### 🏆 Total por Franquia")
    st.caption("Consolidação por franquia: total de câmeras offline e percentual offline, somando todas as cidades de cada franquia.")

    if df_clientes_ops is None or df_clientes_ops.empty or "Franqueado" not in df_clientes_ops.columns:
        st.info("Nenhum dado de franquia disponível.")
        return

    df = df_clientes_ops.copy()
    df["Franqueado"] = df["Franqueado"].fillna("").astype(str).str.strip()
    df = df[df["Franqueado"] != ""].copy()
    if df.empty:
        st.info("Nenhum cliente possui franquia definida.")
        return

    for col in ["Total", "Offline"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0)

    grp = (
        df.groupby("Franqueado", as_index=False)
        .agg(Total=("Total", "sum"), Offline=("Offline", "sum"), Cidades=("ID", "nunique"))
    )
    grp["Online"] = grp["Total"] - grp["Offline"]
    grp["Pct"] = grp.apply(
        lambda r: round(r["Offline"] / r["Total"] * 100, 1) if r["Total"] else 0.0,
        axis=1,
    )

    # Só as franquias que têm ao menos uma câmera offline.
    grp_off = grp[grp["Offline"] > 0].copy()
    if grp_off.empty:
        st.success("Nenhuma câmera offline nas franquias no momento. 🎉")
        return

    total_franquias = int(grp_off["Franqueado"].nunique())
    total_offline = int(grp_off["Offline"].sum())
    total_cameras = int(grp_off["Total"].sum())
    pct_geral = round(total_offline / total_cameras * 100, 1) if total_cameras else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Franquias com offline", f"{total_franquias}")
    m2.metric("Câmeras offline (total)", f"{total_offline}")
    m3.metric("Câmeras monitoradas", f"{total_cameras}")
    m4.metric("% Offline geral", f"{pct_geral:.1f}%")

    if total_franquias > 5:
        qtd_max = st.slider(
            "Franquias nos gráficos",
            min_value=5,
            max_value=int(min(40, total_franquias)),
            value=int(min(15, total_franquias)),
            key="total_franquia_qtd",
        )
    else:
        qtd_max = total_franquias

    st.markdown("#### Câmeras offline por franquia")
    top_qtd = grp_off.sort_values("Offline", ascending=False).head(int(qtd_max)).copy()
    _area_horizontal_franquia(
        top_qtd,
        valor_col="Offline",
        label_col="Franqueado",
        cor="#7B2FFF",
        cor_fill="rgba(123, 47, 255, 0.16)",
        titulo_eixo="Câmeras offline",
        key="total_franquia_area_qtd",
        sufixo="",
        formato_texto=lambda r: f"{int(r['Offline'])}",
    )

    st.markdown("#### % Offline por franquia")
    top_pct = grp_off.sort_values("Pct", ascending=False).head(int(qtd_max)).copy()
    _area_horizontal_franquia(
        top_pct,
        valor_col="Pct",
        label_col="Franqueado",
        cor="#dc2626",
        cor_fill="rgba(220, 38, 38, 0.16)",
        titulo_eixo="% Offline",
        key="total_franquia_area_pct",
        sufixo="%",
        formato_texto=lambda r: f"{r['Pct']:.1f}% ({int(r['Offline'])}/{int(r['Total'])})",
    )

    with st.expander("Ver tabela consolidada por franquia"):
        df_tab = grp_off.sort_values("Offline", ascending=False)[
            ["Franqueado", "Cidades", "Total", "Online", "Offline", "Pct"]
        ].copy()
        df_tab.columns = ["Franquia", "Cidades", "Total", "Online", "Offline", "% Offline"]
        df_tab["% Offline"] = df_tab["% Offline"].apply(lambda v: f"{v:.1f}%")
        render_dataframe(df_tab, height=min(560, (len(df_tab) + 1) * 35 + 3))

        csv_out = grp_off.sort_values("Offline", ascending=False)[
            ["Franqueado", "Cidades", "Total", "Online", "Offline", "Pct"]
        ].to_csv(index=False, sep=";", encoding="utf-8-sig")
        st.download_button(
            "📥 Baixar total por franquia em CSV",
            data=csv_out,
            file_name=f"total_por_franquia_{agora_sao_paulo_str('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_total_por_franquia_csv",
        )


def render_aba_detalhe_cliente_snap(dados: dict) -> None:
    """Aba Detalhe Cliente Snap: consulta de cliente dentro de um snapshot salvo."""
    st.markdown("### 📈 Detalhe Cliente Snap")
    st.caption("Consulte o resumo e, quando disponível, as câmeras de um cliente em um snapshot salvo.")

    df_snaps = listar_snapshots()
    if df_snaps.empty:
        st.info("Nenhum snapshot gravado ainda.")
        return

    df_snaps = df_snaps.copy()
    df_snaps["gravado_dt"] = pd.to_datetime(df_snaps["gravado_em"], errors="coerce")
    df_snaps = df_snaps.sort_values("gravado_dt", ascending=False)

    def fmt_snap(sid: int) -> str:
        row = df_snaps[df_snaps["id"].astype(int) == int(sid)].iloc[0]
        data = row["gravado_dt"].strftime("%d/%m/%Y %H:%M") if pd.notna(row["gravado_dt"]) else str(row["gravado_em"])
        return f"{data} - {row.get('label', 'Snapshot')}"

    snap_ids = df_snaps["id"].astype(int).tolist()
    snap_id = st.selectbox("Snapshot", snap_ids, format_func=fmt_snap, key="det_snap_id")

    wl_ids_validos = {str(k).strip() for k in (dados or {}).keys()}
    df_cli = carregar_snapshot(int(snap_id), wl_ids_validos=wl_ids_validos)
    if df_cli.empty:
        st.warning("Nenhum cliente encontrado nesse snapshot.")
        return

    nomes_atuais = {
        str(wl): (v.get("cidade_estado") or v.get("nome_cliente", f"ID {wl}"))
        for wl, v in (dados or {}).items()
    }
    df_cli["nome_exibicao"] = df_cli["wl_id"].astype(str).map(nomes_atuais).fillna(df_cli["nome_cliente"].astype(str))
    df_cli = df_cli.sort_values("nome_exibicao").copy()

    wl_sel = st.selectbox(
        "Cliente",
        df_cli["wl_id"].astype(str).tolist(),
        format_func=lambda wl: df_cli.loc[df_cli["wl_id"].astype(str) == str(wl), "nome_exibicao"].iloc[0],
        key="det_snap_cliente",
    )

    row_cli = df_cli[df_cli["wl_id"].astype(str) == str(wl_sel)].iloc[0]
    total = int(row_cli.get("total", 0) or 0)
    offline = int(row_cli.get("offline", 0) or 0)
    pct = float(row_cli.get("pct_offline", 0) or 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", total)
    c2.metric("Offline", offline)
    c3.metric("% Offline", f"{pct:.1f}%")

    df_cams = carregar_snapshot_cameras(int(snap_id), wl_ids_validos={str(wl_sel)})
    if df_cams.empty:
        st.info("Esse snapshot possui apenas o resumo por cliente; o detalhamento por câmera não está disponível.")
        return

    df_show = df_cams.copy()
    if "status_camera" in df_show.columns:
        df_show = df_show.sort_values(["status_camera", "nome_camera"], ascending=[True, True])
    df_show = df_show.rename(columns={
        "wl_id": "ID Whitelabel",
        "nome_cliente": "Cliente",
        "nome_empresa": "Franqueado",
        "id_camera": "ID da Câmera",
        "nome_camera": "Nome da Câmera",
        "ultima_atualizacao": "Última vez Online",
        "status_camera": "Status",
    })
    cols = [c for c in ["Cliente", "Franqueado", "ID da Câmera", "Nome da Câmera", "Última vez Online", "Status"] if c in df_show.columns]
    render_dataframe(df_show[cols], height=min(620, (len(df_show) + 1) * 35 + 3))


@st.fragment
def render_top5_criticos(df_clientes_ops: pd.DataFrame) -> None:
    """Top 5 clientes mais críticos.

    Isolado em st.fragment: trocar o critério de ordenação rerroda apenas este
    bloco (reordena e redesenha as 5 linhas), sem reprocessar o app inteiro.
    """
    st.markdown("**Top 5 clientes mais críticos**")

    ordenar_por = st.radio(
        "Ordenar por",
        options=["Criticidade", "% Offline", "Nº offline"],
        horizontal=True,
        key="top5_ordenar",
        label_visibility="collapsed",
    )
    col_ordem = {"Criticidade": "_score", "% Offline": "% Offline", "Nº offline": "Offline"}[ordenar_por]

    df_crit = df_clientes_ops[df_clientes_ops["Offline"] > 0].copy() if not df_clientes_ops.empty else pd.DataFrame()
    df_top = df_crit.sort_values(col_ordem, ascending=False).head(5) if not df_crit.empty else pd.DataFrame()

    if ordenar_por == "Criticidade":
        st.caption("Score de criticidade: combina nº offline, %, tempo offline e recorrência.")

    if df_top.empty:
        st.success("🎉 Todos os clientes estão operacionais!")
        return

    for pos, (_, row) in enumerate(df_top.iterrows(), start=1):
        pct = float(row["% Offline"])
        cor = cor_hex(pct)
        cliente_html = escape_html(str(row["Cliente"]))
        franqueado_html = escape_html(str(row["Franqueado"]))
        width_pct = min(pct, 100)
        off_i, tot_i = int(row["Offline"]), int(row["Total"])

        # Seta de tendência a partir do snapshot anterior.
        d = row.get("Delta Offline")
        if d is None or (isinstance(d, float) and pd.isna(d)):
            trend_html = "<span style='font-size:10px;color:#B8A9CC'>sem histórico</span>"
        elif d > 0:
            trend_html = f"<span style='font-size:11px;color:#dc2626;font-weight:700'>▲ +{int(d)}</span>"
        elif d < 0:
            trend_html = f"<span style='font-size:11px;color:#059669;font-weight:700'>▼ {int(d)}</span>"
        else:
            trend_html = "<span style='font-size:11px;color:#8B7AA3;font-weight:700'>estável</span>"

        # Contexto extra (persistência).
        extras = []
        acima24 = int(row.get("Acima 24h", 0) or 0)
        if acima24 > 0:
            extras.append(f"{acima24} há +24h")
        maior = str(row.get("Maior Tempo", "") or "")
        if maior and maior != "N/D":
            extras.append(f"máx {maior}")
        extras_html = (" · " + " · ".join(extras)) if extras else ""

        st.markdown(f"""
        <div style="display:flex;gap:10px;align-items:flex-start;background:#ffffff;
                    border:1px solid #EFE7FB;border-left:4px solid {cor};border-radius:12px;
                    padding:10px 12px;margin-bottom:8px">
            <div style="flex:0 0 auto;width:24px;height:24px;border-radius:8px;background:{cor}18;
                        color:{cor};font-family:'DM Mono',monospace;font-weight:800;font-size:12px;
                        display:flex;align-items:center;justify-content:center;margin-top:1px">{pos}</div>
            <div style="flex:1;min-width:0">
                <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">
                    <span style="font-size:12px;color:#171126;font-weight:700;white-space:nowrap;
                                 overflow:hidden;text-overflow:ellipsis">{cliente_html}</span>
                    <span style="font-family:'DM Mono',monospace;font-size:14px;color:{cor};font-weight:800">{pct:.1f}%</span>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:5px">
                    <span style="font-size:10px;color:#8B7AA3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{franqueado_html}</span>
                    {trend_html}
                </div>
                <div style="height:5px;background:#F1ECFA;border-radius:99px;overflow:hidden">
                    <div style="height:100%;width:{width_pct}%;background:{cor};border-radius:99px"></div>
                </div>
                <div style="font-size:10px;color:#8B7AA3;margin-top:4px">{off_i} de {tot_i} offline{extras_html}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


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


    # Modo detalhe rápido: evita carregar comparativos, gráficos e todas as abas ao abrir um cliente.
    # Isso reduz bastante o tempo de resposta do botão "Ver detalhes do cliente".
    if "detalhe" in st.session_state:
        render_sidebar(dados, total_cameras, total_offline, pct_global, df_origem)
        st.markdown(f"""
        <div class="page-header">
            <div>
                <div class="page-title">Detalhe do Cliente</div>
                <div class="page-sub">Consulta direta sem carregar todos os dashboards</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        render_cliente_detalhe_rapido(str(st.session_state["detalhe"]), dados)
        return

    # Comparar os snapshots escolhidos no Histórico quando houver seleção.
    # Se ainda não houver seleção, usa os dois últimos snapshots manuais.
    df_base_delta = pd.DataFrame()
    df_base_cameras_novas = pd.DataFrame()
    df_base_cameras_removidas = pd.DataFrame()
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

            # Data da importação/remoção = data do snapshot RECENTE (snapshot_ids[0]).
            ref_recente = _snapshot_ref_por_id(snapshot_ids[0]) or {}
            data_recente = str(ref_recente.get("gravado_em", "") or "")

            # Mapa de Data de Cadastro a partir da base atual (df_origem), por câmera.
            mapa_cadastro = {}
            try:
                if df_origem is not None and not df_origem.empty:
                    dfo = df_origem.copy()
                    dfo.columns = [str(c).strip() for c in dfo.columns]
                    if COL_WL in dfo.columns and COL_ID_CAM in dfo.columns and COL_DATA_CAD in dfo.columns:
                        cad_fmt = parse_ultima_atualizacao(dfo[COL_DATA_CAD]).dt.strftime("%Y-%m-%d %H:%M:%S")
                        for wlv, idv, cadv in zip(
                            dfo[COL_WL].astype(str).str.strip(),
                            dfo[COL_ID_CAM].astype(str).str.strip().str.replace(r"\.0$", "", regex=True),
                            cad_fmt,
                        ):
                            if wlv and idv:
                                mapa_cadastro[f"{wlv}||{idv}"] = "" if pd.isna(cadv) else str(cadv)
            except Exception:
                mapa_cadastro = {}

            def _cadastro_de(row) -> str:
                # 1) base atual; 2) o que estiver salvo no snapshot; senão N/D.
                chave = f"{str(row.get('wl_id','')).strip()}||{str(row.get('id_camera','')).strip()}"
                val = mapa_cadastro.get(chave) or str(row.get("data_cadastro", "") or "")
                return val if val else "N/D"

            def _fmt_dt(valor: str) -> str:
                if not valor:
                    return "N/D"
                dt = pd.to_datetime(valor, errors="coerce")
                return dt.strftime("%d/%m/%Y %H:%M") if pd.notna(dt) else str(valor)

            chaves_antigas = set(df_cams_old["chave_camera"])
            chaves_novas = set(df_cams_new["chave_camera"])

            # ── Câmeras NOVAS: presentes no recente, ausentes na base ──
            df_novas = df_cams_new[~df_cams_new["chave_camera"].isin(chaves_antigas)].copy()
            if not df_novas.empty:
                df_novas["Cliente"] = df_novas["nome_cliente"]
                df_novas["Franqueado"] = df_novas["nome_empresa"]
                df_novas["ID da Câmera"] = df_novas["id_camera"]
                df_novas["Nome da Câmera"] = df_novas["nome_camera"]
                df_novas["Status"] = df_novas["status_camera"].map(_status_label_camera)
                df_novas["Data Cadastro"] = df_novas.apply(lambda r: _fmt_dt(_cadastro_de(r)), axis=1)
                df_base_cameras_novas = df_novas[[
                    "Cliente", "Franqueado", "ID da Câmera", "Nome da Câmera", "Status", "Data Cadastro",
                ]].sort_values(["Cliente", "Nome da Câmera", "ID da Câmera"]).reset_index(drop=True)

            # ── Câmeras REMOVIDAS: presentes na base, ausentes no recente ──
            df_removidas = df_cams_old[~df_cams_old["chave_camera"].isin(chaves_novas)].copy()
            if not df_removidas.empty:
                df_removidas["Cliente"] = df_removidas["nome_cliente"]
                df_removidas["Franqueado"] = df_removidas["nome_empresa"]
                df_removidas["ID da Câmera"] = df_removidas["id_camera"]
                df_removidas["Nome da Câmera"] = df_removidas["nome_camera"]
                df_removidas["Data Cadastro"] = df_removidas.apply(lambda r: _fmt_dt(_cadastro_de(r)), axis=1)
                df_removidas["Data da Remoção"] = _fmt_dt(data_recente)
                df_base_cameras_removidas = df_removidas[[
                    "Cliente", "Franqueado", "ID da Câmera", "Nome da Câmera", "Data Cadastro", "Data da Remoção",
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
        cor_delta_base = "#7C3AED"
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
    _injetar_css_abas_visiveis()
    abas_principais = [
        "Auditoria",
        "Clientes",
        "Central de Ações",
        "Evidências",
        "Atualizar Base",
    ]
    tabs = dict(zip(abas_principais, st.tabs(abas_principais)))

    with tabs["Auditoria"]:
        auditoria_subtabs = st.tabs(["📋 Visão Geral", "🕐 Tempo offline", "📊 % por cliente", "🚘 LPRs Offline"])
    tabs["Auditoria"] = auditoria_subtabs[0]
    tabs["Tempo offline"] = auditoria_subtabs[1]
    tabs["% por cliente"] = auditoria_subtabs[2]
    tabs["LPRs Offline"] = auditoria_subtabs[3]

    # ════════════════════════════════════════════
    # ABA 0 — VISÃO EXECUTIVA
    # ════════════════════════════════════════════
    with tabs["Auditoria"]:
        st.markdown(f"""
        <div class="audit-hero">
            <div class="audit-hero-top">
                <div>
                    <div class="audit-title">Auditoria Clientes GOV</div>
                    <div class="audit-sub">
                        {acao_detalhe}<br>
                        <span style="display:inline-block;margin-top:6px;font-family:'DM Mono',monospace;color:#6D28D9;background:#F3E8FF;border:1px solid #DDD6FE;border-radius:6px;padding:5px 8px">📅 {datas_comparativo_txt}</span>
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
                <div class="audit-card-label">Data da Última Atualização</div>
                <div class="audit-card-value" style="font-size:20px;color:#171126">{saude.get("ultima_atualizacao_base","N/D")}</div>
                <div class="audit-card-note">Última importação/atualização registrada</div>
            </div>
        </div>
        <div class="audit-riskbar">
            <div>
                <div style="font-size:11px;color:#7C6A91;font-weight:700;text-transform:uppercase;letter-spacing:.6px;margin-bottom:7px">Carteira acima do limite crítico</div>
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
						border-color:#E9D5FF !important;">
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
                <div class="kpi-value" style="font-size:28px;font-weight:700;color:{'#ef4444' if delta_global > 0 else ('#14b8a6' if delta_global < 0 else '#7C3AED')};">{delta_global:+.0f}</div>
                <div class="kpi-sub">{clientes_melhoraram} melhoraram · {clientes_pioraram} pioraram</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Lower cards: novos cartões de categoria + Variação e Data da Última Atualização
        if "audit_categoria" not in st.session_state:
            st.session_state["audit_categoria"] = None

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.markdown(f"""
                <div class="kpi-card kpi-ok" style="background:#ffffff;border:1px solid #E9D5FF;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#8B7AA3;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes até 5% offline</div>
                    <div style="font-size:24px;color:#14b8a6;font-family:'DM Mono',monospace;font-weight:700">{n_saudavel}</div>
                    <div style="font-size:11px;color:#8B7AA3">{n_saudavel} clientes · 0–5%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_saudavel"):
                st.session_state["audit_categoria"] = "Saudável (0-5%)"
                st.session_state["mostrar_base_delta"] = False
        with col_b:
            st.markdown(f"""
                <div class="kpi-card kpi-warn" style="background:#ffffff;border:1px solid #E9D5FF;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#8B7AA3;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes em atenção (5 a 10% offline)</div>
                    <div style="font-size:24px;color:#f59e0b;font-family:'DM Mono',monospace;font-weight:700">{n_atencao}</div>
                    <div style="font-size:11px;color:#8B7AA3">{n_atencao} clientes · 5–10%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_atencao"):
                st.session_state["audit_categoria"] = "Atenção (5-10%)"
                st.session_state["mostrar_base_delta"] = False
        with col_c:
            st.markdown(f"""
                <div class="kpi-card kpi-neutral" style="background:#ffffff !important;border:1px solid #E9D5FF;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#8B7AA3;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Clientes acima de 10% offline</div>
                    <div style="font-size:24px;color:#ef4444;font-family:'DM Mono',monospace;font-weight:700">{n_critico}</div>
                    <div style="font-size:11px;color:#8B7AA3">{n_critico} clientes · &gt;10%</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("Ver clientes", key="audit_critico"):
                st.session_state["audit_categoria"] = "Crítico (>10%)"
                st.session_state["mostrar_base_delta"] = False
        with col_d:
            st.markdown(f"""
                <div class="kpi-card kpi-neutral" style="background:#ffffff;border:1px solid #E9D5FF;border-radius:8px;padding:14px 16px">
                    <div style="font-size:10px;color:#8B7AA3;font-weight:700;text-transform:uppercase;letter-spacing:.7px">Crescimento da Base</div>
                    <div style="font-size:24px;color:{cor_delta_base};font-family:'DM Mono',monospace;font-weight:700">{texto_delta_base}</div>
                    <div style="font-size:11px;color:#8B7AA3">{detalhe_delta_base} · Recente: {total_cameras_recente_comparativo} · Base: {total_cameras_anterior}</div>
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

            tem_novas = not df_base_cameras_novas.empty
            tem_removidas = not df_base_cameras_removidas.empty

            if tem_novas:
                st.markdown(f"#### 🟢 Câmeras adicionadas ({len(df_base_cameras_novas)})")
                render_dataframe(
                    df_base_cameras_novas,
                    height=min(700, (len(df_base_cameras_novas) + 1) * 35 + 3)
                )

            if tem_removidas:
                st.markdown(f"#### 🔴 Câmeras removidas ({len(df_base_cameras_removidas)})")
                st.caption("Câmeras que existiam no snapshot base e não estão no snapshot recente. Data da Remoção = data da importação/snapshot recente.")
                render_dataframe(
                    df_base_cameras_removidas,
                    height=min(700, (len(df_base_cameras_removidas) + 1) * 35 + 3)
                )

            if tem_novas or tem_removidas:
                buffer_cams = io.BytesIO()
                with pd.ExcelWriter(buffer_cams, engine="openpyxl") as writer:
                    if tem_novas:
                        df_base_cameras_novas.to_excel(writer, index=False, sheet_name="Cameras Adicionadas")
                    if tem_removidas:
                        df_base_cameras_removidas.to_excel(writer, index=False, sheet_name="Cameras Removidas")
                st.download_button(
                    "⬇ Baixar alterações da base em Excel",
                    key="dl_cameras_alteracoes_excel_v1",
                    data=buffer_cams.getvalue(),
                    file_name=f"alteracoes_base_{agora_sao_paulo_str('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            elif len(snapshot_ids) == 2 and detalhe_cameras_disponivel:
                st.info("Nenhuma câmera foi adicionada ou removida entre o snapshot base e o recente (a variação veio apenas de alteração no total por cliente).")
            elif len(snapshot_ids) == 2:
                st.warning(
                    "O resumo de crescimento existe, mas o detalhamento por ID de câmera ainda não está disponível "
                    "para esses snapshots antigos. Salve um novo snapshot com esta versão e, na próxima comparação, "
                    "o sistema exibirá Cliente, ID da Câmera, Nome da Câmera, Data de Cadastro e Data da Remoção."
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
            # Anel de progresso (radial) com o percentual ONLINE do GOV.
            # Ex.: 8% offline = 92% online.
            pct_online_global = round(100 - pct_global, 2) if total_cameras else 0
            total_online = int(total_cameras - total_offline)

            if pct_online_global >= 95:
                cor_g, cor_track, faixa_txt = "#14b8a6", "#d5f5ee", "Operação saudável"
            elif pct_online_global >= 90:
                cor_g, cor_track, faixa_txt = "#f59e0b", "#fdeccb", "Requer atenção"
            else:
                cor_g, cor_track, faixa_txt = "#ef4444", "#fbd7d7", "Situação crítica"

            st.markdown("**% Total de Câmeras ONLINE GOV**")

            fig_g = go.Figure(go.Pie(
                values=[pct_online_global, max(0.0, 100 - pct_online_global)],
                hole=0.80,
                sort=False,
                direction="clockwise",
                rotation=0,
                marker=dict(colors=[cor_g, cor_track], line=dict(color="#ffffff", width=0)),
                textinfo="none",
                hoverinfo="skip",
            ))
            fig_g.add_annotation(
                text=(
                    f"<span style='font-size:46px;font-weight:800;color:{cor_g};font-family:DM Mono'>"
                    f"{pct_online_global:.1f}<span style='font-size:22px'>%</span></span>"
                    f"<br><span style='font-size:11px;color:#8B7AA3;font-family:DM Sans;"
                    f"letter-spacing:1px;text-transform:uppercase'>câmeras online</span>"
                ),
                x=0.5, y=0.5, showarrow=False,
            )
            layout_defaults = {k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]}
            fig_g.update_layout(
                **layout_defaults,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=250,
                showlegend=False,
                margin=dict(l=8, r=8, t=8, b=8),
            )
            st.plotly_chart(fig_g, use_container_width=True, key="gauge_online_gov")

            st.markdown(f"""
                <div style="display:flex;justify-content:center;margin-top:-8px;margin-bottom:8px">
                    <span style="display:inline-flex;align-items:center;gap:6px;background:{cor_g}14;
                                 border:1px solid {cor_g}40;color:{cor_g};font-size:11px;font-weight:800;
                                 padding:4px 12px;border-radius:99px;letter-spacing:.3px">
                        <span style="width:7px;height:7px;border-radius:99px;background:{cor_g};display:inline-block"></span>{faixa_txt}
                    </span>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
                    <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:10px;padding:9px 8px;text-align:center">
                        <div style="font-size:10px;color:#0f766e;font-weight:800;text-transform:uppercase">Online</div>
                        <div style="font-size:20px;color:#14b8a6;font-family:'DM Mono',monospace;font-weight:800">{total_online}</div>
                    </div>
                    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:9px 8px;text-align:center">
                        <div style="font-size:10px;color:#b91c1c;font-weight:800;text-transform:uppercase">Offline</div>
                        <div style="font-size:20px;color:#ef4444;font-family:'DM Mono',monospace;font-weight:800">{total_offline}</div>
                    </div>
                </div>
                <div style="text-align:center;font-size:10px;color:#8B7AA3;margin-top:6px">de {total_cameras} câmeras monitoradas</div>
            """, unsafe_allow_html=True)

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

            st.markdown("**Saúde da base de clientes**")

            # Donut com as 3 faixas e o % de cada uma puxado para fora (leader lines).
            fig_pie = go.Figure(go.Pie(
                labels=["Saudável", "Atenção", "Crítico"],
                values=[n_saudavel, n_atencao, n_critico],
                text=[
                    f"Saudável<br><b>{pct_saudavel_card:.0f}%</b>",
                    f"Atenção<br><b>{pct_atencao_card:.0f}%</b>",
                    f"Crítico<br><b>{pct_critico_card:.0f}%</b>",
                ],
                textinfo="text",
                textposition="outside",
                hole=0.68,
                sort=False,
                direction="clockwise",
                rotation=0,
                marker=dict(colors=["#14b8a6", "#f59e0b", "#dc2626"], line=dict(color="#ffffff", width=3)),
                outsidetextfont=dict(color="#4A3D5C", size=12, family="DM Sans"),
                automargin=True,
                hovertemplate="<b>%{label}</b><br>%{value} clientes · %{percent}<extra></extra>",
            ))
            fig_pie.add_annotation(
                text=(
                    f"<span style='font-size:34px;font-weight:800;color:#171126;font-family:DM Mono'>{total_clientes}</span>"
                    f"<br><span style='font-size:11px;color:#8B7AA3;font-family:DM Sans;"
                    f"letter-spacing:1px;text-transform:uppercase'>clientes</span>"
                ),
                x=0.5, y=0.5, showarrow=False,
            )
            layout_defaults = {k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]}
            fig_pie.update_layout(
                **layout_defaults,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=270,
                showlegend=False,
                margin=dict(l=40, r=40, t=24, b=24),
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="pie_clientes_faixa_saude_moderno")

            st.markdown(f"""
                <div style="display:flex;justify-content:center;margin-top:-8px;margin-bottom:8px">
                    <span style="display:inline-flex;align-items:center;gap:6px;background:{status_saude_cor}14;
                                 border:1px solid {status_saude_cor}40;color:{status_saude_cor};font-size:11px;
                                 font-weight:800;padding:4px 12px;border-radius:99px;letter-spacing:.3px">
                        <span style="width:7px;height:7px;border-radius:99px;background:{status_saude_cor};display:inline-block"></span>{status_saude_titulo}
                    </span>
                </div>
                <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">
                    <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:10px;padding:9px 8px;text-align:center">
                        <div style="font-size:10px;color:#0f766e;font-weight:800;text-transform:uppercase">Saudável</div>
                        <div style="font-size:20px;color:#14b8a6;font-family:'DM Mono',monospace;font-weight:800">{n_saudavel}</div>
                        <div style="font-size:10px;color:#7C6A91">0–5% · {pct_saudavel_card:.1f}%</div>
                    </div>
                    <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:9px 8px;text-align:center">
                        <div style="font-size:10px;color:#b45309;font-weight:800;text-transform:uppercase">Atenção</div>
                        <div style="font-size:20px;color:#f59e0b;font-family:'DM Mono',monospace;font-weight:800">{n_atencao}</div>
                        <div style="font-size:10px;color:#7C6A91">5–10% · {pct_atencao_card:.1f}%</div>
                    </div>
                    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:9px 8px;text-align:center">
                        <div style="font-size:10px;color:#b91c1c;font-weight:800;text-transform:uppercase">Crítico</div>
                        <div style="font-size:20px;color:#dc2626;font-family:'DM Mono',monospace;font-weight:800">{n_critico}</div>
                        <div style="font-size:10px;color:#7C6A91">&gt;10% · {pct_critico_card:.1f}%</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_top:
            render_top5_criticos(df_clientes_ops)

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
            st.plotly_chart(fig_map, use_container_width=True, key="mapa_cidades_operacao_v1")
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
            xaxis=dict(tickfont=dict(color="#8B7AA3",size=10), tickangle=-45),
            yaxis=dict(ticksuffix="%", gridcolor="#E9D5FF",
                       tickfont=dict(color="#8B7AA3",size=10),
                       range=[0, max(df_heat["Pct"].max()*1.2, 10)]),
            margin=dict(l=10,r=10,t=10,b=110),
        )
        st.plotly_chart(fig_heat, use_container_width=True, key="heatmap_clientes_operacao_v1")

    # ════════════════════════════════════════════
    # ABA 1 — PAINEL DE CLIENTES
    # ════════════════════════════════════════════
    with tabs["Clientes"]:
        st.markdown("### 🏢 Clientes")
        st.caption("Painel operacional dos clientes e geração de relatórios em HTML por franquia para envio por e-mail.")
        clientes_subtabs = st.tabs(["📊 Painel de clientes", "✉️ Relatório por franquia", "📈 Tendência", "🏆 Total por Franquia"])
        with clientes_subtabs[0]:
            # Quando um cliente está aberto, não renderiza todos os cards novamente.
            # Isso deixa o clique em "Ver detalhes" muito mais rápido.
            if "detalhe" not in st.session_state:
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
                            key="clientes_busca_input",
                        )
                    with col_franq:
                        filtro_franq_input = st.selectbox(
                            "Franqueado",
                            franqueados,
                            index=franqueados.index(st.session_state.get("clientes_franq", "Todos"))
                            if st.session_state.get("clientes_franq", "Todos") in franqueados else 0,
                            key="clientes_franq_input",
                        )
                    with col_min:
                        min_opcoes = [0, 10, 50, 100, 200]
                        min_cameras_input = st.selectbox(
                            "Min. câmeras",
                            min_opcoes,
                            index=min_opcoes.index(st.session_state.get("clientes_min", 0))
                            if st.session_state.get("clientes_min", 0) in min_opcoes else 0,
                            key="clientes_min_input",
                        )
                    aplicar_filtros = st.form_submit_button("Aplicar filtros · Clientes", use_container_width=True)
    
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
                        key="dl_clientes_filtrados_recorte_v1",
                        data=buf_filtro.getvalue(),
                        file_name=f"clientes_filtrados_{agora_sao_paulo_str('%Y%m%d_%H%M')}.xlsx",
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
                agora  = agora_sao_paulo()
                nome_cliente_html = escape_html(v.get("cidade_estado") or v["nome_cliente"])
                nome_empresa_html = escape_html(v["nome_empresa"])
                wl_id_html = escape_html(wl_id)

                st.markdown("<hr>", unsafe_allow_html=True)
                html_det = (
                    '<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;flex-wrap:wrap">'
                    '<div style="background:rgba(0,136,204,.12);border:1px solid rgba(0,136,204,.22);'
                    'border-radius:8px;padding:6px 14px;font-size:11px;font-weight:600;'
                    'color:#6D28D9;text-transform:uppercase;letter-spacing:.5px">📍 Detalhamento</div>'
                    '<div>'
                    + f'<div style="font-size:20px;font-weight:700;color:#7C3AED">{nome_cliente_html}</div>'
                    + f'<div style="font-size:12px;color:#8B7AA3">{nome_empresa_html} · ID: {wl_id_html}</div>'
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
                            file_name=f"detalhe_cliente_{wl_id}_{agora_sao_paulo_str('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            key=f"dl_detalhe_cliente_xlsx_{str(wl_id)}_aba",
                        )
                    with dl_col2:
                        st.download_button(
                            label="⬇ Exportar detalhe (.csv)",
                            data=buf_csv.getvalue(),
                            file_name=f"detalhe_cliente_{wl_id}_{agora_sao_paulo_str('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key=f"dl_detalhe_cliente_csv_{str(wl_id)}_aba",
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

                # ─────────────────────────────────────────────
                # SEÇÃO DE AÇÕES DO CLIENTE
                # ─────────────────────────────────────────────
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("### 📋 Ações a realizar")
            
                # Verificar configuração
                if not supabase_configurado():
                    st.warning("⚠️ Supabase não configurado. As ações não podem ser salvas.")
                else:
                    tabela_existe, msg_tabela = criar_tabela_acoes_se_nao_existir()
                    if not tabela_existe:
                        st.error("🚨 Não foi possível acessar a tabela acoes_clientes")
                        st.info(msg_tabela)
            
                with st.expander("✏️ Gerenciar ações", expanded=False):
                    # Carregar ações existentes
                    df_acoes = carregar_acoes_cliente(wl_id)
                
                    if df_acoes is not None and not df_acoes.empty:
                        st.subheader("Ações registradas")
                        for idx_acao, (_, acao) in enumerate(df_acoes.iterrows()):
                            col_acao_data, col_acao_status, col_acao_del = st.columns([3, 1.5, 1])
                        
                            data_criacao = acao.get("data_criacao", "N/D")
                            if isinstance(data_criacao, str) and "T" in data_criacao:
                                data_criacao = data_criacao.split("T")[0]
                        
                            status_atual = acao.get("status_acao", "Pendente")
                        
                            with col_acao_data:
                                st.markdown(f"""
                                <div style="padding:12px 14px;background:#f8fafc;border:1px solid #E9D5FF;border-radius:8px">
                                    <div style="font-size:11px;color:#8B7AA3;font-weight:700;text-transform:uppercase;margin-bottom:4px">Ação</div>
                                    <div style="font-size:13px;color:#171126;margin-bottom:8px"><strong>{acao.get('o_que_foi_feito', 'N/D')}</strong></div>
                                    <div style="font-size:10px;color:#8B7AA3">📅 {data_criacao}</div>
                                    {f"<div style='font-size:10px;color:#8B7AA3'>⏰ Prazo: {acao.get('prazo_ajustes', 'Sem prazo')}</div>" if acao.get('prazo_ajustes') else ""}
                                </div>
                                """, unsafe_allow_html=True)
                        
                            with col_acao_status:
                                novo_status = st.selectbox(
                                    "Status",
                                    ["Pendente", "Concluído"],
                                    index=0 if status_atual == "Pendente" else 1,
                                    key=f"status_{acao.get('id', idx_acao)}_{idx_acao}"
                                )
                                if novo_status != status_atual:
                                    sucesso, msg = atualizar_status_acao(acao.get("id", ""), novo_status)
                                    if sucesso:
                                        st.success("Atualizado!", icon="✅")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        
                            with col_acao_del:
                                st.write("")  # spacing
                    else:
                        st.info("Nenhuma ação registrada para este cliente.")
                
                    st.divider()
                    st.subheader("Adicionar nova ação")
                
                    with st.form(f"form_acao_{wl_id}", clear_on_submit=True):
                        acao_texto = st.text_area(
                            "O que foi feito",
                            placeholder="Descreva a ação tomada (ex: Abrir chamado com técnico, Enviar comunicado, etc.)",
                            height=100,
                            key=f"acao_texto_{wl_id}"
                        )
                    
                        col_prazo, col_status = st.columns(2)
                        with col_prazo:
                            prazo = st.date_input(
                                "Prazo para ajustes",
                                value=None,
                                format="DD/MM/YYYY",
                                key=f"prazo_acao_{wl_id}"
                            )
                        with col_status:
                            status_acao = st.selectbox(
                                "Status",
                                ["Pendente", "Concluído"],
                                key=f"status_nova_acao_{wl_id}"
                            )
                    
                        if st.form_submit_button(f"➕ Registrar ação · {wl_id}", use_container_width=True):
                            if not acao_texto.strip():
                                st.error("Descreva a ação a ser realizada")
                            else:
                                prazo_str = prazo.strftime("%Y-%m-%d") if prazo else None
                                sucesso, msg = salvar_acao_cliente(
                                    id_whitelabel=wl_id,
                                    nome_cliente=v.get("nome_cliente", ""),
                                    o_que_foi_feito=acao_texto,
                                    prazo_ajustes=prazo_str,
                                    status_acao=status_acao
                                )
                                if sucesso:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

                if st.button("← Voltar ao painel", key="btn_voltar_painel_detalhe_cliente_v1"):
                    del st.session_state["detalhe"]; st.rerun()

        with clientes_subtabs[1]:
            render_relatorio_por_franquia(df_clientes_ops, dados, key_prefix="clientes_relatorio_franquia")

    # ════════════════════════════════════════════
    # ABA 2 — CENTRAL DE AÇÕES
    # ════════════════════════════════════════════
    with tabs["Central de Ações"]:
        render_central_acoes(dados)

    with clientes_subtabs[2]:
        render_aba_tendencia(dados)

    with clientes_subtabs[3]:
        render_aba_total_por_franquia(df_clientes_ops)

    # ════════════════════════════════════════════
    # ABA 3 — TEMPO OFFLINE
    # ════════════════════════════════════════════
    with tabs["Tempo offline"]:
        st.markdown("#### Câmeras offline por tempo sem sinal")
        st.caption("Identifique as câmeras que estão há mais tempo sem atualização — ordenadas do mais crítico ao menos crítico")

        # Montar DataFrame global com todas as câmeras offline
        rows_tempo = []
        agora = agora_sao_paulo()
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
                    border:1px solid #E9D5FF;
                    border-radius:14px;
                    padding:18px 18px 16px;
                    text-align:center;
                    box-shadow:0 10px 26px rgba(16,42,63,.06);
                    position:relative;
                    overflow:hidden;
                    min-height:118px;
                ">
                    <div style="position:absolute;top:0;left:0;right:0;height:4px;background:{cor};"></div>
                    <div style="font-size:10px;color:#7C6A91;font-weight:800;text-transform:uppercase;letter-spacing:.8px;margin-top:4px">{titulo}</div>
                    <div style="font-size:34px;font-weight:800;color:{cor};font-family:DM Mono,monospace;line-height:1.15;margin-top:10px">{valor}</div>
                    <div style="font-size:11px;color:#7C6A91;margin-top:6px">{subtitulo}</div>
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
                            tickfont=dict(color="#8B7AA3", size=9),
                            tickangle=-45,
                            zeroline=False,
                            range=[0.5, len(df_graf) + 0.5],
                        ),
                        yaxis=dict(
                            title="Dias offline",
                            gridcolor="rgba(148,163,184,.16)",
                            tickfont=dict(color="#8B7AA3", size=10),
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
                    file_name=f"tempo_offline_{agora_sao_paulo_str('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_tempo_offline_lista_v1")

                render_dataframe(df_tbl_t, height=min(600,(len(df_tbl_t)+1)*35+3))

    # ════════════════════════════════════════════
    # ABA 4 — % OFFLINE POR CLIENTE
    # ════════════════════════════════════════════
    with tabs["% por cliente"]:
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
            fig_bar.add_vline(x=xv, line_dash="dot", line_color="#C4B5FD", line_width=1.5,
                annotation_text=lbl, annotation_position="top",
                annotation_font=dict(color="#8B7AA3", size=10))
        fig_bar.add_trace(go.Bar(
            y=df_bar["Cliente"], x=df_bar["Pct"], orientation="h",
            marker=dict(color=[cor_hex(p) for p in df_bar["Pct"]], line=dict(width=0)),
            text=[f"{p:.1f}% ({o}/{t})" for p,o,t in zip(df_bar["Pct"],df_bar["Offline"],df_bar["Total"])],
            textposition="outside", textfont=dict(color="#8B7AA3",size=10,family="DM Mono"),
            hovertemplate="<b>%{y}</b><br>%{x:.1f}% offline<extra></extra>",
        ))
        fig_bar.update_layout(
            **pdefaults(), height=max(360, len(df_bar)*34), showlegend=False,
            xaxis=dict(range=[0,100], ticksuffix="%", gridcolor="#E9D5FF",
                       tickfont=dict(color="#8B7AA3",size=10), zeroline=False),
            yaxis=dict(tickfont=dict(color="#6B5A7A",size=10), gridcolor="#FAF7FF"),
            margin=dict(l=10, r=80, t=30, b=10),
        )
        st.plotly_chart(fig_bar, use_container_width=True, key="pct_offline_por_cliente_bar_v1")

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
                textposition="outside", textfont=dict(color="#8B7AA3",size=10,family="DM Mono"),
                hovertemplate="%{y}<br>Offline: %{x} (%{text})<extra></extra>",
            ))
            fig_rank.update_layout(
                **pdefaults(), barmode="stack",
                height=max(360, len(df_rank)*40),
                xaxis=dict(title="Quantidade de câmeras", gridcolor="#E9D5FF",
                           tickfont=dict(color="#8B7AA3",size=10), zeroline=False),
                yaxis=dict(tickfont=dict(color="#6B5A7A",size=10),
                           categoryorder="array",
                           categoryarray=df_rank["Cliente"].tolist()[::-1]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            font=dict(color="#8B7AA3",size=11), bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=10, r=80, t=50, b=10),
            )
            st.plotly_chart(fig_rank, use_container_width=True, key="ranking_criticidade_stack_v1")

            st.markdown("---")
            col_tbl, col_dl = st.columns([5,1])
            col_tbl.markdown("**Tabela resumo**")
            buf_r = io.BytesIO()
            df_rank.to_excel(buf_r, index=True, engine="openpyxl")
            col_dl.download_button("⬇ Excel", data=buf_r.getvalue(),
                file_name=f"ranking_{agora_sao_paulo_str('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_ranking_criticidade_excel_v1")

            df_show = df_rank[["Cliente","Franqueado","Offline","Total","% Offline"]].copy()
            df_show["% Offline"] = df_show["% Offline"].apply(lambda x: f"{x:.1f}%")
            render_dataframe(df_show, height=min(400,(len(df_show)+1)*35+3))


    # ════════════════════════════════════════════
    # ABA 5 — HISTÓRICO & COMPARATIVO
    # ════════════════════════════════════════════
    with tabs["Evidências"]:
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
                        file_name=f"comparativo_{agora_sao_paulo_str('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="dl_comparativo_historico_excel_v1")

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
                    resumo_cor = "#6D28D9"
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
                    <div class="compare-status-tag" style="color:#6D28D9">Resumo executivo</div>
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
                            xaxis=dict(gridcolor="#E9D5FF", tickfont=dict(color="#8B7AA3",size=10), zeroline=False),
                            yaxis=dict(autorange="reversed", tickfont=dict(color="#6B5A7A",size=10)),
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
                            xaxis=dict(gridcolor="#E9D5FF", tickfont=dict(color="#8B7AA3",size=10), zeroline=False),
                            yaxis=dict(autorange="reversed", tickfont=dict(color="#6B5A7A",size=10)),
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
                        gridcolor="#E9D5FF",
                        tickfont=dict(color="#8B7AA3", size=10),
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
                        tickfont=dict(color="#6B5A7A", size=10),
                    ),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                font=dict(size=11, color="#8B7AA3"), bgcolor="rgba(0,0,0,0)"),
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
                        gridcolor="#E9D5FF",
                        tickfont=dict(color="#8B7AA3", size=10),
                        zeroline=False,
                    ),
                    yaxis=dict(tickfont=dict(color="#6B5A7A", size=10)),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                font=dict(size=11, color="#8B7AA3"), bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=10, r=20, t=45, b=10),
                )
                st.plotly_chart(fig_comp, use_container_width=True, key="hist_comp_offline_cliente")

                st.markdown("#### Variação líquida de offline")
                st.caption("Valores positivos indicam piora; valores negativos indicam melhora.")
                df_delta = df_comp.copy().sort_values("delta_off", ascending=True)
                cores_d  = ["#dc2626" if d > 0 else ("#059669" if d < 0 else "#8B7AA3") for d in df_delta["delta_off"]]
                fig_d = go.Figure(go.Bar(
                    y=df_delta["cliente"], x=df_delta["delta_off"], orientation="h",
                    marker=dict(color=cores_d, line=dict(width=0)),
                    text=[f"{'+' if d>0 else ''}{int(d)}" for d in df_delta["delta_off"]],
                    textposition="outside", textfont=dict(color="#8B7AA3",size=10,family="DM Mono"),
                    hovertemplate="%{y}<br>Δ %{x:+.0f} câmeras<extra></extra>",
                ))
                fig_d.add_vline(x=0, line_color="#C4B5FD", line_width=1)
                fig_d.update_layout(
                    **pdefaults(), height=max(420, len(df_delta)*32), showlegend=False,
                    xaxis=dict(gridcolor="#E9D5FF", tickfont=dict(color="#8B7AA3",size=10), zeroline=False),
                    yaxis=dict(tickfont=dict(color="#6B5A7A",size=10)),
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
    # ABA 6 — LPRS OFFLINE
    # ════════════════════════════════════════════
    with tabs["LPRs Offline"]:
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
                    lambda x: fmt_tempo(agora_sao_paulo() - x) if pd.notna(x) else "N/D"
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

                st.markdown("#### Clientes com mais LPRs offline")
                top_lpr_area = df_lpr_cli.head(15).sort_values("lprs_offline", ascending=True).copy()
                top_lpr_area["Cliente eixo"] = top_lpr_area["Cliente"].astype(str)
                max_lpr_area = max(3, int(top_lpr_area["lprs_offline"].max()) + 1) if not top_lpr_area.empty else 3
                altura_lpr_area = max(380, min(680, 42 * len(top_lpr_area) + 140))

                fig_lpr_area = go.Figure()
                fig_lpr_area.add_trace(go.Scatter(
                    name="LPRs offline",
                    x=top_lpr_area["lprs_offline"],
                    y=top_lpr_area["Cliente eixo"],
                    mode="lines+markers+text",
                    fill="tozerox",
                    line=dict(color="#dc2626", width=3.0, shape="spline", smoothing=0.65),
                    marker=dict(color="#dc2626", size=9, line=dict(color="#ffffff", width=1)),
                    fillcolor="rgba(220, 38, 38, 0.18)",
                    text=top_lpr_area["lprs_offline"],
                    textposition="middle right",
                    customdata=top_lpr_area[["Cliente", "Franqueado"]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Franqueado: %{customdata[1]}<br>"
                        "LPRs offline: %{x}<extra></extra>"
                    ),
                ))
                fig_lpr_area.update_layout(
                    **pdefaults(),
                    height=altura_lpr_area,
                    margin=dict(l=10, r=55, t=10, b=35),
                    xaxis=dict(
                        title="LPRs offline",
                        range=[0, max_lpr_area],
                        gridcolor="#E9D5FF",
                        tickfont=dict(color="#8B7AA3", size=10),
                        zeroline=False,
                    ),
                    yaxis=dict(
                        title="",
                        type="category",
                        categoryorder="array",
                        categoryarray=top_lpr_area["Cliente eixo"].tolist(),
                        tickfont=dict(color="#6B5A7A", size=11),
                        automargin=True,
                    ),
                    showlegend=False,
                    hovermode="closest",
                )
                st.plotly_chart(fig_lpr_area, use_container_width=True, key="lprs_offline_top_clientes_area_horizontal")

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
                    file_name=f"lprs_offline_{agora_sao_paulo_str('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="dl_lprs_offline_csv_v1",
                )


    # ════════════════════════════════════════════
    # ABA 7 — ATUALIZAR BASE ONLINE
    # ════════════════════════════════════════════
    with tabs["Atualizar Base"]:
        render_aba_atualizar_base(df_origem)

if __name__ == "__main__":
    main()
