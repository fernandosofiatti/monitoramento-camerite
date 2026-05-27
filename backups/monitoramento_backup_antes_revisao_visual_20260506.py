import streamlit as st
import pandas as pd
import os
import sqlite3
import io
from datetime import datetime, timedelta
import plotly.graph_objects as go

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
    padding: 16px 14px 12px; position: relative; overflow: hidden;
    box-shadow: 0 8px 22px rgba(16, 42, 63, .05);
}
.unit-card::before {
    content:''; position:absolute; top:0; left:0; right:0;
    height:3px; border-radius:8px 8px 0 0;
}
.card-red::before    { background: linear-gradient(90deg,#ef4444,#dc2626); }
.card-yellow::before { background: linear-gradient(90deg,#f59e0b,#d97706); }
.card-ok::before     { background: linear-gradient(90deg,#14b8a6,#059669); }
.unit-name {
    font-size:10px; font-weight:600; letter-spacing:.8px; text-transform:uppercase;
    color:#007ab8; margin-bottom:8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.unit-count { font-size:32px; font-weight:700; line-height:1; font-family:'DM Mono',monospace; }
.count-red    { color:#f87171; }
.count-yellow { color:#fbbf24; }
.count-ok     { color:#14b8a6; }
.unit-label { font-size:10px; margin-top:3px; font-weight:500; letter-spacing:.4px; color:#4f6f85; }
.label-red    { color:#ff8e8e; }
.label-yellow { color:#c98500; }
.label-ok     { color:#0f9f8f; }
.prog-track { margin-top:10px; height:3px; background:#dbe8f2; border-radius:99px; overflow:hidden; }
.prog-fill  { height:100%; border-radius:99px; }
.trend-badge {
    display:inline-flex; align-items:center; gap:4px;
    font-size:10px; font-weight:600; padding:2px 7px; border-radius:99px; margin-top:6px;
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

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
PASTA          = r"C:\Users\FernandoHenriqueSofi\Desktop\Monitoramento"
CSV_GOV        = os.path.join(PASTA, "GOV_extracao_cameras.csv")
XLSX_CLIENTES  = os.path.join(PASTA, "nome_clientes.xlsx")
DB_PATH        = os.path.join(PASTA, "historico.db")
COLUNAS_PAINEL = 4

# Mapeamento de colunas do CSV para nomes internos
COL_STATUS     = "Status_da_Camera"
COL_WL         = "ID_Whitelabel"
COL_EMPRESA    = "Nome_Empresa"
COL_ID_CAM     = "ID_da_Camera"
COL_NOME_CAM   = "Nome_da_Camera"
COL_ULT_ATU    = "Ultima_Atualizacao"
COL_OBS        = "Observacoes"


# ─────────────────────────────────────────────
# HELPERS DE COR
# ─────────────────────────────────────────────
def cor_hex(pct: float) -> str:
    if pct < 5:     return "#14b8a6"
    elif pct <= 10: return "#f59e0b"
    else:           return "#ef4444"

def classe_card(pct: float):
    if pct < 5:     return ("card-ok",    "count-ok",    "label-ok")
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
        col_id  = next((c for c in df.columns if "whitelabel" in c.lower() or "id" in c.lower()), df.columns[0])
        col_nom = next((c for c in df.columns if "nome" in c.lower() or "client" in c.lower()), df.columns[1])
        return dict(zip(df[col_id].astype(str).str.strip(), df[col_nom].astype(str).str.strip()))
    except Exception:
        return {}

def ler_csv_gov(path: str) -> pd.DataFrame | None:
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
                # Aceitar só se tiver pelo menos 2 colunas (arquivo válido)
                if len(df.columns) >= 2:
                    return df
            except UnicodeDecodeError:
                break   # tenta próximo encoding
            except Exception:
                continue
    return None

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
        df[COL_ULT_ATU] = pd.to_datetime(df[COL_ULT_ATU], errors="coerce", dayfirst=True)
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

@st.cache_data(ttl=60)
def carregar_dados(pasta: str) -> tuple[dict, str]:
    """
    Tenta carregar GOV_extracao_cameras.csv da pasta.
    Retorna (dados, erro) — erro é string vazia se OK.
    """
    if not os.path.exists(pasta):
        return {}, f"Pasta não encontrada: `{pasta}`"
    if not os.path.exists(CSV_GOV):
        # Listar o que existe na pasta para diagnóstico
        try:
            arquivos = os.listdir(pasta)
            lista = ", ".join(arquivos[:10]) if arquivos else "(pasta vazia)"
        except Exception:
            lista = "(não foi possível listar)"
        return {}, f"Arquivo `GOV_extracao_cameras.csv` não encontrado em `{pasta}`.\nArquivos encontrados: {lista}"

    df = ler_csv_gov(CSV_GOV)
    if df is None:
        return {}, "Não foi possível ler o CSV (erro de encoding ou arquivo corrompido)."

    cols_faltando = [c for c in [COL_STATUS, COL_WL] if c not in df.columns]
    if cols_faltando:
        return {}, (
            f"Colunas obrigatórias não encontradas: `{'`, `'.join(cols_faltando)}`\n"
            f"Colunas presentes no CSV: `{'`, `'.join(df.columns.tolist())}`"
        )

    clientes_map = carregar_clientes()
    return processar_df_gov(df, clientes_map), ""


# ─────────────────────────────────────────────
# BANCO SQLite
# ─────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            label      TEXT NOT NULL,
            gravado_em TEXT NOT NULL,
            notas      TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS snapshot_clientes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
            wl_id       TEXT NOT NULL,
            nome_cliente TEXT NOT NULL,
            total       INTEGER NOT NULL,
            offline     INTEGER NOT NULL,
            pct_offline REAL NOT NULL
        );
    """)
    con.commit(); con.close()

def salvar_snapshot(label: str, notas: str, dados: dict) -> str:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO snapshots (label,gravado_em,notas) VALUES (?,?,?)", (label, agora, notas))
    sid = cur.lastrowid
    for wl_id, v in dados.items():
        total = v["total"]; off = len(v["offline"])
        pct   = round(off/total*100, 2) if total else 0
        cur.execute(
            "INSERT INTO snapshot_clientes (snapshot_id,wl_id,nome_cliente,total,offline,pct_offline) VALUES (?,?,?,?,?,?)",
            (sid, wl_id, v["nome_cliente"], total, off, pct)
        )
    con.commit(); con.close()
    return agora

def listar_snapshots() -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    df  = pd.read_sql_query("SELECT id,label,gravado_em,notas FROM snapshots ORDER BY id DESC", con)
    con.close(); return df

def carregar_snapshot(sid: int) -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    df  = pd.read_sql_query(
        "SELECT wl_id,nome_cliente,total,offline,pct_offline FROM snapshot_clientes WHERE snapshot_id=?",
        con, params=(sid,)
    )
    con.close(); return df

def deletar_snapshot(sid: int):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM snapshot_clientes WHERE snapshot_id=?", (sid,))
    cur.execute("DELETE FROM snapshots WHERE id=?", (sid,))
    con.commit(); con.close()

def ultimo_snapshot() -> pd.DataFrame | None:
    con  = sqlite3.connect(DB_PATH)
    df_s = pd.read_sql_query("SELECT id FROM snapshots ORDER BY id DESC LIMIT 2", con)
    con.close()
    if len(df_s) < 2: return None
    return carregar_snapshot(int(df_s.iloc[1]["id"]))


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
            "Status": "Crítico" if pct > 10 else ("Atenção" if pct >= 5 else "Saudável"),
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
def render_card(col, wl_id, v, tendencia, delta_off):
    nome_display = v["nome_cliente"]
    nome_empresa = v["nome_empresa"]
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

    sub_html = f'<div style="font-size:9px;color:#6b8496;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{nome_empresa}</div>' if nome_empresa else ""
    id_html  = f'<div style="font-size:9px;color:#6b8496;font-family:\'DM Mono\',monospace">ID: {wl_id}</div>'

    with col:
        st.markdown(f"""
        <div class="unit-card {card_c}">
            <div class="unit-name" title="{nome_display}">{nome_display}</div>
            {sub_html}
            <div class="unit-count {count_c}">{count}</div>
            <div class="unit-label {label_c}">{label_txt}</div>
            <div class="prog-track"><div class="prog-fill" style="width:{prog_w}%;background:{cor}"></div></div>
            {trend_html}
            {id_html}
        </div>
        """, unsafe_allow_html=True)

        if count > 0:
            if st.button("Ver detalhes", key=f"btn_{wl_id}"):
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
                <div class="sidebar-logo-sub">Central de Monitoramento</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="nav-section">Visão Geral</div>', unsafe_allow_html=True)
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
    dados, erro = carregar_dados(PASTA)
    clientes_map = carregar_clientes()

    if not dados:
        # Mostrar diagnóstico e oferecer upload manual
        with st.sidebar:
            st.markdown('''
            <div class="sidebar-logo">
                <img src="https://framerusercontent.com/images/YQ4euyeSqXxIJm99xQGGCBYWYpg.png" style="height:30px;width:auto" alt="Camerite">
                <div>
                    <div class="sidebar-logo-text">Camerite BI</div>
                    <div class="sidebar-logo-sub">Central de Monitoramento</div>
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
                    st.success(f"CSV carregado! {len(df_up)} linhas · {len(dados)} clientes encontrados.")
                    # Não há st.rerun aqui — o código continua abaixo com dados preenchidos
                except Exception as e:
                    st.error(f"Erro ao processar o arquivo: {e}")
                    return
            else:
                st.caption("Aguardando upload do CSV…")
                return

    # ── Métricas globais ──
    total_clientes = len(dados)
    total_cameras  = sum(v["total"] for v in dados.values())
    total_offline  = sum(len(v["offline"]) for v in dados.values())
    pct_global     = round(total_offline/total_cameras*100, 2) if total_cameras else 0
    n_critico      = sum(1 for v in dados.values() if (len(v["offline"])/v["total"]*100 if v["total"] else 0) > 10)
    n_atencao      = sum(1 for v in dados.values() if 5 <= (len(v["offline"])/v["total"]*100 if v["total"] else 0) <= 10)
    clientes_alert = sum(1 for v in dados.values() if len(v["offline"]) > 0)

    # ── Tendências vs penúltimo snapshot ──
    df_ult = ultimo_snapshot()
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

    # ── Sidebar ──
    render_sidebar(dados, total_cameras, total_offline, pct_global)

    # ── Page header ──
    st.markdown(f"""
    <div class="page-header">
        <div>
            <div class="page-title">Central de Monitoramento</div>
            <div class="page-sub">{total_clientes} clientes · {total_cameras} câmeras monitoradas</div>
        </div>
        <div class="page-badge">🟢 Live · {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── ABAS ──
    tabs = st.tabs([
        "🎯  Visão Executiva",
        "📋  Painel de Clientes",
        "⏱️  Tempo Offline",
        "📊  % Offline por Cliente",
        "🏆  Ranking de Criticidade",
        "📈  Histórico & Comparativo",
    ])

    # ════════════════════════════════════════════
    # ABA 0 — VISÃO EXECUTIVA
    # ════════════════════════════════════════════
    with tabs[0]:
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
            <div class="kpi-card kpi-warn">
                <div class="kpi-label">Clientes em Alerta</div>
                <div class="kpi-value val-warn">{clientes_alert}</div>
                <div class="kpi-sub">{n_critico} críticos · {n_atencao} em atenção</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_gauge, col_pie, col_top = st.columns([1,1,1], gap="large")

        with col_gauge:
            st.markdown("**Índice de criticidade global**")
            cor_g = cor_hex(pct_global)
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pct_global,
                number=dict(suffix="%", font=dict(color=cor_g, size=52, family="DM Mono")),
                gauge=dict(
                    axis=dict(range=[0,100], tickfont=dict(color="#6b8496", size=10), nticks=6),
                    bar=dict(color=cor_g, thickness=0.28),
                    bgcolor="#f5f8fb", bordercolor="#dbe8f2",
                    steps=[
                        dict(range=[0,5],    color="#dff8f3"),
                        dict(range=[5,10],   color="#fef3c7"),
                        dict(range=[10,100], color="#fee2e2"),
                    ],
                    threshold=dict(line=dict(color="#6b8496", width=2), thickness=0.75, value=pct_global),
                ),
            ))
            fig_g.update_layout(**pdefaults(), height=280, margin=dict(l=20,r=20,t=30,b=10))
            st.plotly_chart(fig_g, use_container_width=True)

        with col_pie:
            st.markdown("**Distribuição por faixa de saúde**")
            n_saudavel = total_clientes - n_critico - n_atencao
            fig_pie = go.Figure(go.Pie(
                labels=["Crítico >10%","Atenção 5–10%","Saudável <5%"],
                values=[n_critico, n_atencao, n_saudavel],
                hole=0.6,
                marker=dict(colors=["#dc2626","#d97706","#059669"],
                            line=dict(color="#ffffff", width=3)),
                textfont=dict(size=11, family="DM Sans"),
                hovertemplate="<b>%{label}</b><br>%{value} clientes (%{percent})<extra></extra>",
            ))
            fig_pie.add_annotation(
                text=f"<b>{total_clientes}</b><br>clientes",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#0088cc", family="DM Mono"),
            )
            fig_pie.update_layout(
                **pdefaults(), height=280,
                legend=dict(font=dict(size=11,color="#6b8496"), bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=10,r=10,t=20,b=10),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_top:
            st.markdown("**Top 5 clientes mais críticos**")
            df_top = pd.DataFrame([
                {"Cliente": v["nome_cliente"],
                 "Franqueado": v["nome_empresa"],
                 "Pct": round(len(v["offline"])/v["total"]*100, 1) if v["total"] else 0,
                 "Off": len(v["offline"]), "Tot": v["total"]}
                for v in dados.values() if len(v["offline"]) > 0
            ]).sort_values("Pct", ascending=False).head(5)

            if df_top.empty:
                st.success("🎉 Todos os clientes estão operacionais!")
            else:
                for _, row in df_top.iterrows():
                    cor = cor_hex(row["Pct"])
                    st.markdown(f"""
                    <div style="margin-bottom:14px">
                        <div style="display:flex;justify-content:space-between;margin-bottom:2px">
                            <span style="font-size:12px;color:#102a3f;font-weight:600">{row['Cliente']}</span>
                            <span style="font-family:'DM Mono',monospace;font-size:12px;color:{cor};font-weight:700">{row['Pct']:.1f}%</span>
                        </div>
                        <div style="font-size:10px;color:#6b8496;margin-bottom:4px">{row['Franqueado']}</div>
                        <div style="height:5px;background:#dbe8f2;border-radius:99px;overflow:hidden">
                            <div style="height:100%;width:{min(row['Pct'],100)}%;background:{cor};border-radius:99px"></div>
                        </div>
                        <div style="font-size:10px;color:#6b8496;margin-top:3px">{int(row['Off'])} offline de {int(row['Tot'])}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("**Mapa de calor — % offline por cliente**")
        df_heat = pd.DataFrame([
            {"Cliente": v["nome_cliente"],
             "Pct": round(len(v["offline"])/v["total"]*100, 2) if v["total"] else 0}
            for v in dados.values()
        ]).sort_values("Pct", ascending=False)

        fig_heat = go.Figure(go.Bar(
            x=df_heat["Cliente"], y=df_heat["Pct"],
            marker=dict(
                color=df_heat["Pct"],
                colorscale=[[0,"#dff8f3"],[0.05,"#14b8a6"],[0.1,"#f59e0b"],[1,"#ef4444"]],
                cmin=0, cmax=100, line=dict(width=0),
            ),
            hovertemplate="<b>%{x}</b><br>%{y:.1f}% offline<extra></extra>",
        ))
        fig_heat.update_layout(
            **pdefaults(), height=300,
            xaxis=dict(tickfont=dict(color="#6b8496",size=10), tickangle=-45),
            yaxis=dict(ticksuffix="%", gridcolor="#dbe8f2",
                       tickfont=dict(color="#6b8496",size=10),
                       range=[0, max(df_heat["Pct"].max()*1.2, 10)]),
            margin=dict(l=10,r=10,t=10,b=90),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # ════════════════════════════════════════════
    # ABA 1 — PAINEL DE CLIENTES
    # ════════════════════════════════════════════
    with tabs[1]:
        col_search, col_filtro = st.columns([3,1])
        with col_search:
            busca = st.text_input("🔍", placeholder="Buscar cliente ou franqueado…", label_visibility="collapsed")
        with col_filtro:
            filtro = st.selectbox("Filtro", ["Todos","Crítico (>10%)","Atenção (5–10%)","Saudável (<5%)"],
                                  label_visibility="collapsed")

        def passa_filtro(wl_id, v):
            pct = len(v["offline"])/v["total"]*100 if v["total"] else 0
            termo = busca.upper()
            if busca and termo not in v["nome_cliente"].upper() and termo not in v["nome_empresa"].upper() and termo not in wl_id.upper():
                return False
            if filtro == "Crítico (>10%)"  and pct <= 10:            return False
            if filtro == "Atenção (5–10%)" and not (5 <= pct <= 10): return False
            if filtro == "Saudável (<5%)"  and pct >= 5:             return False
            return True

        ids_ord = sorted(dados.keys(),
                         key=lambda wl: (len(dados[wl]["offline"])/dados[wl]["total"]) if dados[wl]["total"] else 0,
                         reverse=True)
        ids_f = [wl for wl in ids_ord if passa_filtro(wl, dados[wl])]

        if not ids_f:
            st.info("Nenhum cliente encontrado com os filtros aplicados.")
        else:
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

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;flex-wrap:wrap">
                <div style="background:rgba(0,136,204,.12);border:1px solid rgba(0,136,204,.22);
                    border-radius:8px;padding:6px 14px;font-size:11px;font-weight:600;
                    color:#007ab8;text-transform:uppercase;letter-spacing:.5px">📍 Detalhamento</div>
                <div>
                    <div style="font-size:20px;font-weight:700;color:#0088cc">{v["nome_cliente"]}</div>
                    <div style="font-size:12px;color:#6b8496">{v["nome_empresa"]} · ID: {wl_id}</div>
                </div>
                <div style="margin-left:auto;font-size:13px;font-weight:700;color:{cor_d}">
                    {len(df_det)} offline de {total_u} câmeras ({pct_d}%)
                </div>
            </div>
            """, unsafe_allow_html=True)

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
                cols_ex = [c for c in col_map if c in df_det.columns]

                if COL_ULT_ATU in df_det.columns:
                    # Já vem ordenado por tempo offline (mais antigo primeiro)
                    df_show = df_det[cols_ex].copy()
                    df_show = df_show.rename(columns=col_map)

                    # Adicionar coluna de tempo offline calculado
                    df_show.insert(
                        df_show.columns.get_loc("Última vez Online") + 1,
                        "Tempo Offline",
                        df_det["_tempo_off"].apply(
                            lambda td: fmt_tempo(td) if td.total_seconds() >= 0 else "N/D"
                        ).values
                    )

                    # Formatar data
                    if "Última vez Online" in df_show.columns:
                        df_show["Última vez Online"] = pd.to_datetime(df_show["Última vez Online"], errors="coerce")\
                            .dt.strftime("%d/%m/%Y %H:%M").fillna("N/D")
                else:
                    df_show = df_det[cols_ex].copy().rename(columns=col_map)

                df_show = df_show.reset_index(drop=True)
                df_show.index += 1
                st.caption(f"⬆ Ordenado por tempo offline — quem está há mais tempo sem sinal aparece primeiro")
                st.dataframe(df_show, use_container_width=True, height=min(500,(len(df_show)+1)*35+3))

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
            k1.markdown(f"""<div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Acima de 24h</div>
                <div style="font-size:32px;font-weight:700;color:#ef4444;font-family:'DM Mono',monospace">{acima_24h}</div>
                <div style="font-size:11px;color:#6b8496">câmeras críticas</div></div>""", unsafe_allow_html=True)
            k2.markdown(f"""<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Entre 6h e 24h</div>
                <div style="font-size:32px;font-weight:700;color:#f59e0b;font-family:'DM Mono',monospace">{acima_6h}</div>
                <div style="font-size:11px;color:#6b8496">câmeras em atenção</div></div>""", unsafe_allow_html=True)
            k3.markdown(f"""<div style="background:#ecfdf5;border:1px solid #99f6e4;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Menos de 6h</div>
                <div style="font-size:32px;font-weight:700;color:#14b8a6;font-family:'DM Mono',monospace">{abaixo_6h}</div>
                <div style="font-size:11px;color:#6b8496">câmeras recentes</div></div>""", unsafe_allow_html=True)
            k4.markdown(f"""<div style="background:#ffffff;border:1px solid #dbe8f2;border-radius:8px;padding:16px;text-align:center">
                <div style="font-size:10px;color:#6b8496;font-weight:600;text-transform:uppercase;letter-spacing:.7px">Sem data</div>
                <div style="font-size:32px;font-weight:700;color:#6b8496;font-family:'DM Mono',monospace">{nd_count}</div>
                <div style="font-size:11px;color:#6b8496">sem informação</div></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Filtros
            col_f1, col_f2, col_f3 = st.columns([2,2,1])
            with col_f1:
                busca_t = st.text_input("🔍 Buscar câmera ou cliente", key="busca_tempo", label_visibility="collapsed",
                                        placeholder="Buscar câmera ou cliente…")
            with col_f2:
                faixa = st.selectbox("Faixa de tempo", ["Todas","Acima de 24h","Entre 6h e 24h","Menos de 6h","Sem data"],
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
                    df_exib["ID da Câmera"].astype(str).str.upper().str.contains(termo)
                ]
            if faixa == "Acima de 24h":    df_exib = df_exib[df_exib["_horas"] >= 24]
            elif faixa == "Entre 6h e 24h": df_exib = df_exib[(df_exib["_horas"] >= 6) & (df_exib["_horas"] < 24)]
            elif faixa == "Menos de 6h":    df_exib = df_exib[(df_exib["_horas"] >= 0) & (df_exib["_horas"] < 6)]
            elif faixa == "Sem data":       df_exib = df_exib[df_exib["_horas"] < 0]

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
                df_tbl_t = df_exib[["Nome Cliente","Nome Franqueado","ID da Câmera","Nome da Câmera","Última vez Online","Observações","_horas","_td"]].copy()
                df_tbl_t["Tempo Offline"] = df_tbl_t["_td"].apply(lambda td: fmt_tempo(td) if isinstance(td,timedelta) and td.total_seconds()>=0 else "N/D")
                df_tbl_t["Última vez Online"] = pd.to_datetime(df_tbl_t["Última vez Online"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M").fillna("N/D")
                df_tbl_t["Criticidade"] = df_tbl_t["_horas"].apply(
                    lambda h: "🔴 Crítico (>24h)" if h>=24 else ("🟡 Atenção (6–24h)" if h>=6 else ("🟢 Recente (<6h)" if h>=0 else "⚫ Sem data"))
                )
                df_tbl_t = df_tbl_t.drop(columns=["_horas","_td"]).reset_index(drop=True)
                df_tbl_t.index += 1
                # Reordenar colunas
                df_tbl_t = df_tbl_t[["Criticidade","Tempo Offline","Nome da Câmera","ID da Câmera","Nome Cliente","Nome Franqueado","Última vez Online","Observações"]]

                # Download
                buf_t = io.BytesIO()
                df_tbl_t.to_excel(buf_t, index=True, engine="openpyxl")
                st.download_button("⬇ Exportar lista",
                    data=buf_t.getvalue(),
                    file_name=f"tempo_offline_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                st.dataframe(df_tbl_t, use_container_width=True, height=min(600,(len(df_tbl_t)+1)*35+3))

    # ════════════════════════════════════════════
    # ABA 3 — % OFFLINE POR CLIENTE
    # ════════════════════════════════════════════
    with tabs[3]:
        st.markdown("#### Percentual de câmeras offline por cliente")
        st.caption("Escala 0–100% · Verde <5% · Amarelo 5–10% · Vermelho >10%")

        df_bar = pd.DataFrame([
            {"Cliente": v["nome_cliente"], "Offline": len(v["offline"]),
             "Total": v["total"],
             "Pct": round(len(v["offline"])/v["total"]*100, 2) if v["total"] else 0}
            for v in dados.values()
        ]).sort_values("Pct", ascending=True)

        fig_bar = go.Figure()
        fig_bar.add_vrect(x0=0,  x1=5,   fillcolor="rgba(5,150,105,0.06)",  layer="below", line_width=0)
        fig_bar.add_vrect(x0=5,  x1=10,  fillcolor="rgba(217,119,6,0.06)",  layer="below", line_width=0)
        fig_bar.add_vrect(x0=10, x1=100, fillcolor="rgba(220,38,38,0.06)",  layer="below", line_width=0)
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
            st.dataframe(df_show, use_container_width=True, height=min(400,(len(df_show)+1)*35+3))

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
                st.dataframe(df_tbl, use_container_width=True, height=min(500,(len(df_tbl)+1)*35+3))

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
