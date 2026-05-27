import streamlit as st
import pandas as pd
import os
import re
import sqlite3
import io
from datetime import datetime
import plotly.graph_objects as go


# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Camerite BI · Monitoramento",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background-color: #080a0f !important;
    color: #e2e4ea !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stHeader"]          { background: transparent !important; }
[data-testid="stSidebar"]         { background: #0d0f16 !important; border-right: 1px solid #1a1d2e !important; }
[data-testid="block-container"]   { padding: 2rem 2.5rem !important; max-width: 1600px; }
section[data-testid="stSidebar"] > div { padding: 1.5rem 1rem !important; }

/* ── Sidebar ── */
.sidebar-logo {
    display: flex; align-items: center; gap: 10px;
    padding: 0 0 1.5rem; border-bottom: 1px solid #1a1d2e; margin-bottom: 1.5rem;
}
.sidebar-logo-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #7c3aed, #4f46e5);
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 18px; flex-shrink: 0;
}
.sidebar-logo-text { font-size: 15px; font-weight: 700; color: #f0f1f5; line-height: 1; }
.sidebar-logo-sub  { font-size: 10px; color: #a78bfa; margin-top: 2px; }
.nav-section {
    font-size: 10px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; color: #a78bfa; margin: 1.2rem 0 .5rem;
}

/* ── Page header ── */
.page-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #1a1d2e;
}
.page-title { font-size: 24px; font-weight: 700; color: #f0f1f5; letter-spacing: -.4px; }
.page-sub   { font-size: 13px; color: #a78bfa; margin-top: 3px; }
.page-badge {
    font-family: 'DM Mono', monospace; font-size: 11px; color: #a78bfa;
    background: #0d0f16; padding: 6px 14px; border-radius: 8px;
    border: 1px solid #1a1d2e; white-space: nowrap;
}

/* ── KPI cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 1.5rem; }
.kpi-card {
    background: #0d0f16; border: 1px solid #1a1d2e; border-radius: 14px;
    padding: 20px 20px 16px; position: relative; overflow: hidden;
}
.kpi-card::after {
    content:''; position:absolute; top:0; left:0; right:0; height:2px; border-radius:14px 14px 0 0;
}
.kpi-alert::after   { background: linear-gradient(90deg,#ef4444,#dc2626); }
.kpi-warn::after    { background: linear-gradient(90deg,#f59e0b,#d97706); }
.kpi-ok::after      { background: linear-gradient(90deg,#10b981,#059669); }
.kpi-neutral::after { background: linear-gradient(90deg,#7c3aed,#4f46e5); }

/* SELETOR DEFINITIVO: Altera TUDO que for texto dentro do card para Roxo Claro, exceto o valor principal */
.kpi-card *:not(.kpi-value):not(.val-alert):not(.val-warn):not(.val-ok):not(.val-purple) {
    color: #c4b5fd !important;
    -webkit-text-fill-color: #c4b5fd !important;
    opacity: 1 !important;
}

/* Garante que o valor principal (os números grandes) mantenha a cor de status */
.kpi-value, .val-alert, .val-warn, .val-ok, .val-purple {
    font-size: 40px !important;
    font-weight: 700 !important;
    font-family: 'DM Mono', monospace !important;
    -webkit-text-fill-color: currentColor !important; /* Impede o roxo de sobrescrever o status */
}

.val-alert  { color: #f87171 !important; }
.val-warn   { color: #fbbf24 !important; }
.val-ok     { color: #34d399 !important; }
.val-purple { color: #a78bfa !important; }
            
/* ── Unit cards ── */
.unit-card {
    background: #0d0f16; border: 1px solid #1a1d2e; border-radius: 14px;
    padding: 16px 14px 12px; position: relative; overflow: hidden;
}
.unit-card::before {
    content:''; position:absolute; top:0; left:0; right:0;
    height:3px; border-radius:14px 14px 0 0;
}
.card-red::before    { background: linear-gradient(90deg,#ef4444,#dc2626); }
.card-yellow::before { background: linear-gradient(90deg,#f59e0b,#d97706); }
.card-ok::before     { background: linear-gradient(90deg,#10b981,#059669); }
.unit-name {
    font-size:10px; font-weight:600; letter-spacing:.8px; text-transform:uppercase;
    color:#a78bfa; margin-bottom:8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.unit-count { font-size:32px; font-weight:700; line-height:1; font-family:'DM Mono',monospace; }
.count-red    { color:#f87171; }
.count-yellow { color:#fbbf24; }
.count-ok     { color:#34d399; }
.unit-label { font-size:10px; margin-top:3px; font-weight:500; letter-spacing:.4px; color:#a78bfa; }
.label-red    { color:#ff8e8e; }
.label-yellow { color:#ffe66d; }
.label-ok     { color:#95ffcd; }
.prog-track { margin-top:10px; height:3px; background:#1a1d2e; border-radius:99px; overflow:hidden; }
.prog-fill  { height:100%; border-radius:99px; }
.trend-badge {
    display:inline-flex; align-items:center; gap:4px;
    font-size:10px; font-weight:600; padding:2px 7px; border-radius:99px; margin-top:6px;
}
.trend-up   { background:rgba(248,113,113,.12); color:#f87171; }
.trend-down { background:rgba(52,211,153,.12);  color:#34d399; }
.trend-same { background:rgba(167,139,250,.12); color:#a78bfa; }

/* ── Tabelas ── */
.stTable table { background:transparent !important; font-family:'DM Sans',sans-serif !important;
    font-size:13px !important; width:100% !important; border-collapse:collapse !important; }
.stTable thead th { background:#080a0f !important; color:#a78bfa !important;
    font-size:10px !important; font-weight:600 !important; letter-spacing:.7px !important;
    text-transform:uppercase !important; padding:10px 14px !important; border-bottom:1px solid #1a1d2e !important; }
.stTable tbody tr { background:#0d0f16 !important; }
.stTable tbody td { padding:10px 14px !important; border-bottom:1px solid #12151f !important; color:#f0f1f5 !important; }

/* ── Botões ── */
.stButton > button {
    width:100% !important; margin-top:8px !important; background:#13161f !important;
    border:1px solid #1e2130 !important; color:#a78bfa !important; border-radius:8px !important;
    font-family:'DM Sans',sans-serif !important; font-size:11px !important;
    font-weight:500 !important; padding:5px 10px !important; transition:all .2s !important;
}
.stButton > button:hover:not(:disabled) {
    background:#1a1e30 !important; border-color:#7c3aed !important; color:#c4b5fd !important;
}

/* ── Abas ── */
[data-testid="stTabs"] [role="tablist"] { border-bottom:1px solid #1a1d2e !important; gap:2px !important; }
[data-testid="stTabs"] [role="tab"] {
    background:transparent !important; border:1px solid transparent !important;
    border-radius:8px 8px 0 0 !important; color:#a78bfa !important;
    font-family:'DM Sans',sans-serif !important; font-size:13px !important;
    font-weight:500 !important; padding:8px 18px !important; transition:all .2s !important;
}
[data-testid="stTabContent"] { padding-top:1.5rem !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background:#0d0f16 !important; border:1px solid #1a1d2e !important;
    border-radius:12px !important; margin-bottom:8px !important;
}
[data-testid="stExpander"] summary { font-weight:500 !important; color:#a78bfa !important; font-size:13px !important; }

/* ── Misc ── */
hr { border-color:#1a1d2e !important; margin:1.5rem 0 !important; }
[data-testid="stAlert"] {
    background:#0d0f16 !important; border:1px solid #1a1d2e !important;
    border-radius:10px !important; color:#a78bfa !important;
}

/* ── Download buttons ── */
.stDownloadButton > button {
    background:linear-gradient(135deg,rgba(124,58,237,.13),rgba(79,70,229,.13)) !important;
    border:1px solid rgba(79,70,229,.25) !important; color:#a78bfa !important;
    border-radius:8px !important; font-size:12px !important; font-weight:600 !important;
    padding:8px 16px !important; width:auto !important; margin-top:0 !important; transition:all .2s !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
PASTA         = r"C:\Users\FernandoHenriqueSofi\Desktop\Monitoramento"
DB_PATH       = os.path.join(PASTA, "historico.db")
COLUNAS_PAINEL = 5


# ─────────────────────────────────────────────
# HELPERS DE COR
# ─────────────────────────────────────────────
def cor_hex(pct: float) -> str:
    if pct <= 0:    return "#34d399"
    elif pct < 5:   return "#34d399"
    elif pct <= 10: return "#fbbf24"
    else:           return "#f87171"

def classe_card(pct: float):
    if pct < 5:     return ("card-ok",    "count-ok",    "label-ok")
    elif pct <= 10: return ("card-yellow","count-yellow","label-yellow")
    else:           return ("card-red",   "count-red",   "label-red")


# ─────────────────────────────────────────────
# LEITURA DE DADOS
# ─────────────────────────────────────────────
def limpar_nome(nome_arquivo: str) -> str:
    match = re.search(r"relatorio_(.*?)(\d+)", nome_arquivo)
    nome_puro = match.group(1) if match else nome_arquivo.replace("relatorio_","").replace(".csv","")
    return nome_puro.replace("&"," ").strip().upper()

def ler_csv(path: str):
    for enc in ("utf-8","latin-1","cp1252"):
        try:    return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError: continue
        except: return None
    return None

@st.cache_data(ttl=60)
def carregar_dados(pasta: str) -> dict:
    arquivos = sorted([f for f in os.listdir(pasta) if f.startswith("relatorio_") and f.endswith(".csv")])
    resultado = {}
    for arq in arquivos:
        df = ler_csv(os.path.join(pasta, arq))
        if df is None or "Status" not in df.columns:
            continue
        df_off = df[df["Status"].str.strip().str.upper() == "OFFLINE"]
        resultado[limpar_nome(arq)] = {"offline": df_off, "total": len(df)}
    return resultado


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
        CREATE TABLE IF NOT EXISTS snapshot_cidades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
            cidade      TEXT NOT NULL,
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
    for cidade, v in dados.items():
        total = v["total"]; off = len(v["offline"])
        pct   = round(off/total*100, 2) if total else 0
        cur.execute(
            "INSERT INTO snapshot_cidades (snapshot_id,cidade,total,offline,pct_offline) VALUES (?,?,?,?,?)",
            (sid, cidade, total, off, pct)
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
        "SELECT cidade,total,offline,pct_offline FROM snapshot_cidades WHERE snapshot_id=?",
        con, params=(sid,)
    )
    con.close(); return df

def deletar_snapshot(sid: int):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM snapshot_cidades WHERE snapshot_id=?", (sid,))
    cur.execute("DELETE FROM snapshots WHERE id=?", (sid,))
    con.commit(); con.close()

def ultimo_snapshot():
    """Retorna o snapshot ANTERIOR ao mais recente, para comparacao nos cards."""
    con  = sqlite3.connect(DB_PATH)
    df_s = pd.read_sql_query("SELECT id FROM snapshots ORDER BY id DESC LIMIT 2", con)
    con.close()
    if len(df_s) < 2: return None
    return carregar_snapshot(int(df_s.iloc[1]["id"]))


# ─────────────────────────────────────────────
# EXPORTAÇÃO EXCEL
# ─────────────────────────────────────────────
def gerar_excel(dados: dict) -> bytes:
    rows = []
    for cidade, v in dados.items():
        total = v["total"]; off = len(v["offline"])
        pct   = round(off/total*100, 2) if total else 0
        rows.append({
            "Cidade": cidade, "Total": total, "Offline": off,
            "Online": total-off, "% Offline": pct,
            "Status": "Crítico" if pct > 10 else ("Atenção" if pct >= 5 else "Saudável")
        })
    df_exp = pd.DataFrame(rows).sort_values("% Offline", ascending=False)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_exp.to_excel(writer, index=False, sheet_name="Resumo Geral")
        frames = []
        for cidade, v in dados.items():
            if len(v["offline"]) > 0:
                tmp = v["offline"].copy(); tmp.insert(0,"Cidade",cidade)
                frames.append(tmp)
        if frames:
            pd.concat(frames, ignore_index=True).to_excel(writer, index=False, sheet_name="Câmeras Offline")
    return buf.getvalue()


# ─────────────────────────────────────────────
# PLOTLY — DEFAULTS
# ─────────────────────────────────────────────
def pdefaults() -> dict:
    return dict(
        paper_bgcolor="#080a0f", plot_bgcolor="#080a0f",
        font=dict(family="DM Sans", color="#9195a8"),
        # Margem removida daqui para evitar erro de múltiplos valores no update_layout[cite: 1]
    )


# ─────────────────────────────────────────────
# RENDER CARD DE UNIDADE
# ─────────────────────────────────────────────
def render_card(col, nome, count, total, pct, tendencia, delta_off=None):
    card_c, count_c, label_c = classe_card(pct)
    cor    = cor_hex(pct)
    prog_w = min(pct, 100)
    label_txt = f"OPERACIONAL · {total} CÂMERAS" if count == 0 else f"OFFLINE DE {total}  ({pct:.1f}%)"

    if tendencia is None or delta_off is None:
        trend_html = ""
    elif tendencia > 0.5:
        trend_html = f'<div class="trend-badge trend-up">▲ +{int(delta_off)} câmeras offline vs anterior</div>'
    elif tendencia < -0.5:
        trend_html = f'<div class="trend-badge trend-down">▼ {int(delta_off)} câmeras offline vs anterior</div>'
    else:
        trend_html = '<div class="trend-badge trend-same">→ Estável vs anterior</div>'

    with col:
        st.markdown(f"""
        <div class="unit-card {card_c}">
            <div class="unit-name" title="{nome}">{nome}</div>
            <div class="unit-count {count_c}">{count}</div>
            <div class="unit-label {label_c}">{label_txt}</div>
            <div class="prog-track"><div class="prog-fill" style="width:{prog_w}%;background:{cor}"></div></div>
            {trend_html}
        </div>
        """, unsafe_allow_html=True)

        if count > 0:
            if st.button("Ver detalhes", key=f"btn_{nome}"):
                st.session_state["detalhe"] = nome
                st.rerun()
        else:
            st.button("✓ Operacional", key=f"btn_{nome}", disabled=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar(dados, total_cameras, total_offline, pct_global):
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo">
            <div class="sidebar-logo-icon">📡</div>
            <div>
                <div class="sidebar-logo-text">Camerite BI</div>
                <div class="sidebar-logo-sub">Central de Monitoramento</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        cor = cor_hex(pct_global)
        st.markdown('<div class="nav-section">Saúde da rede</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#080a0f;border:1px solid #1a1d2e;border-radius:12px;padding:16px;margin-bottom:8px">
            <div style="font-size:10px;color:#2a2f45;font-weight:600;letter-spacing:.7px;
                text-transform:uppercase;margin-bottom:6px">% OFFLINE GLOBAL</div>
            <div style="font-size:36px;font-weight:700;font-family:'DM Mono',monospace;
                color:{cor};line-height:1">{pct_global:.1f}%</div>
            <div style="font-size:11px;color:#2a2f45;margin-top:4px">{total_offline} de {total_cameras} câmeras</div>
            <div style="margin-top:10px;height:4px;background:#1a1d2e;border-radius:99px;overflow:hidden">
                <div style="height:100%;width:{min(pct_global,100):.1f}%;background:{cor};border-radius:99px"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="nav-section">Salvar Snapshot</div>', unsafe_allow_html=True)
        label_snap = st.text_input(
            "Rótulo", value=f"Semana {datetime.now().strftime('%d/%m/%Y')}",
            label_visibility="collapsed", key="snap_label",
            placeholder="Ex: Semana 01/05/2025"
        )
        notas_snap = st.text_area(
            "Observações", placeholder="Deixe uma observação",
            label_visibility="collapsed", height=68, key="snap_notas"
        )
        if st.button("💾  Salvar snapshot", use_container_width=True):
            ts = salvar_snapshot(label_snap, notas_snap, dados)
            st.success(f"Gravado em {ts}")
            st.cache_data.clear()

        st.markdown('<div class="nav-section">Exportar</div>', unsafe_allow_html=True)
        st.download_button(
            label="⬇  Baixar Excel (.xlsx)",
            data=gerar_excel(dados),
            file_name=f"camerite_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.markdown('<div class="nav-section">Dados</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#2a2f45;
            background:#080a0f;border:1px solid #1a1d2e;border-radius:8px;padding:8px 12px;margin-bottom:6px">
            {datetime.now().strftime('%d/%m/%Y  %H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄  Recarregar dados", use_container_width=True):
            st.cache_data.clear(); st.rerun()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    init_db()

    if not os.path.exists(PASTA):
        st.error(f"Pasta não encontrada: `{PASTA}`")
        return

    dados = carregar_dados(PASTA)
    if not dados:
        st.warning("Nenhum relatório `relatorio_*.csv` encontrado.")
        return

    # ── Métricas globais ──
    total_unidades = len(dados)
    total_cameras  = sum(v["total"]        for v in dados.values())
    total_offline  = sum(len(v["offline"]) for v in dados.values())
    unidades_alert = sum(1 for v in dados.values() if len(v["offline"]) > 0)
    unidades_ok    = total_unidades - unidades_alert
    pct_global     = round(total_offline/total_cameras*100, 2) if total_cameras else 0
    n_critico      = sum(1 for v in dados.values()
                        if (len(v["offline"])/v["total"]*100 if v["total"] else 0) > 10)
    n_atencao      = sum(1 for v in dados.values()
                        if 5 <= (len(v["offline"])/v["total"]*100 if v["total"] else 0) <= 10)

    # ── Tendências vs último snapshot ──
    df_ult = ultimo_snapshot()
    if df_ult is not None:
        ref_pct = df_ult.set_index("cidade")["pct_offline"].to_dict()
        ref_off = df_ult.set_index("cidade")["offline"].to_dict()
        tendencias = {c: round((len(v["offline"])/v["total"]*100 if v["total"] else 0) - ref_pct.get(c, 0), 2)
                      for c, v in dados.items()}
        delta_offs = {c: len(v["offline"]) - ref_off.get(c, 0)
                      for c, v in dados.items()}
    else:
        tendencias = {c: None for c in dados}
        delta_offs = {c: None for c in dados}

    # ── Sidebar ──
    render_sidebar(dados, total_cameras, total_offline, pct_global)

    # ── Page header ──
    st.markdown(f"""
    <div class="page-header">
        <div>
            <div class="page-title">Central de Monitoramento</div>
            <div class="page-sub">{total_unidades} unidades · {total_cameras} câmeras monitoradas</div>
        </div>
        <div class="page-badge">🟢 Live · {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── ABAS ──
    tabs = st.tabs([
        "🎯  Visão Executiva",
        "📋  Painel de Unidades",
        "📊  % Offline por Cidade",
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
                <div class="kpi-sub">{total_unidades} unidades monitoradas</div>
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
                <div class="kpi-label">Unidades em Alerta</div>
                <div class="kpi-value val-warn">{unidades_alert}</div>
                <div class="kpi-sub">{n_critico} críticas · {n_atencao} em atenção</div>
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
                    axis=dict(range=[0,100], tickcolor="#1a1d2e",
                              tickfont=dict(color="#2a2f45", size=10), nticks=6),
                    bar=dict(color=cor_g, thickness=0.28),
                    bgcolor="#0d0f16", bordercolor="#1a1d2e",
                    steps=[
                        dict(range=[0,5],    color="#071510"),
                        dict(range=[5,10],   color="#1a1305"),
                        dict(range=[10,100], color="#1a0808"),
                    ],
                    threshold=dict(
                        line=dict(color="rgba(255,255,255,0.1)", width=2),
                        thickness=0.75, value=pct_global,
                    ),
                ),
            ))
            # Ajuste de margem manual[cite: 1]
            fig_g.update_layout(**pdefaults(), height=280, margin=dict(l=20,r=20,t=30,b=10))
            st.plotly_chart(fig_g, use_container_width=True)

        with col_pie:
            st.markdown("**Distribuição por faixa de saúde**")
            n_saudavel = total_unidades - n_critico - n_atencao
            fig_pie = go.Figure(go.Pie(
                labels=["Crítico >10%","Atenção 5–10%","Saudável <5%"],
                values=[n_critico, n_atencao, n_saudavel],
                hole=0.6,
                marker=dict(colors=["#f87171","#fbbf24","#34d399"],
                            line=dict(color="#080a0f", width=3)),
                textfont=dict(size=11, family="DM Sans"),
                hovertemplate="<b>%{label}</b><br>%{value} unidades (%{percent})<extra></extra>",
            ))
            fig_pie.add_annotation(
                text=f"<b>{total_unidades}</b><br>unidades",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#e2e4ea", family="DM Mono"),
            )
            # Ajuste de margem manual[cite: 1]
            fig_pie.update_layout(
                **pdefaults(), height=280,
                legend=dict(font=dict(size=11,color="#5a5f73"), bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=10,r=10,t=20,b=10),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_top:
            st.markdown("**Top 5 unidades mais críticas**")
            df_top = pd.DataFrame([
                {"Unidade": n,
                 "Pct": round(len(v["offline"])/v["total"]*100, 1) if v["total"] else 0,
                 "Off": len(v["offline"]), "Tot": v["total"]}
                for n, v in dados.items() if len(v["offline"]) > 0
            ]).sort_values("Pct", ascending=False).head(5)

            if df_top.empty:
                st.success("🎉 Todas as unidades estão operacionais!")
            else:
                for _, row in df_top.iterrows():
                    cor = cor_hex(row["Pct"])
                    st.markdown(f"""
                    <div style="margin-bottom:14px">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                            <span style="font-size:12px;color:#9195a8;font-weight:500">{row['Unidade']}</span>
                            <span style="font-family:'DM Mono',monospace;font-size:12px;color:{cor};font-weight:700">{row['Pct']:.1f}%</span>
                        </div>
                        <div style="height:5px;background:#1a1d2e;border-radius:99px;overflow:hidden">
                            <div style="height:100%;width:{min(row['Pct'],100)}%;background:{cor};border-radius:99px"></div>
                        </div>
                        <div style="font-size:10px;color:#2a2f45;margin-top:3px">{int(row['Off'])} offline de {int(row['Tot'])}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # Heatmap de colunas
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("**Mapa de calor — % offline por unidade**")
        df_heat = pd.DataFrame([
            {"Cidade": n, "Pct": round(len(v["offline"])/v["total"]*100, 2) if v["total"] else 0}
            for n, v in dados.items()
        ]).sort_values("Pct", ascending=False)

        fig_heat = go.Figure(go.Bar(
            x=df_heat["Cidade"], y=df_heat["Pct"],
            marker=dict(
                color=df_heat["Pct"],
                colorscale=[[0,"#071510"],[0.05,"#34d399"],[0.1,"#fbbf24"],[1,"#f87171"]],
                cmin=0, cmax=100, line=dict(width=0),
            ),
            hovertemplate="<b>%{x}</b><br>%{y:.1f}% offline<extra></extra>",
        ))
        # Ajuste de margem manual[cite: 1]
        fig_heat.update_layout(
            **pdefaults(), height=300,
            xaxis=dict(tickfont=dict(color="#3d4257",size=10), gridcolor="#0d0f16", tickangle=-45),
            yaxis=dict(ticksuffix="%", gridcolor="#1a1d2e",
                       tickfont=dict(color="#3d4257",size=10),
                       range=[0, max(df_heat["Pct"].max()*1.2, 10)]),
            margin=dict(l=10,r=10,t=10,b=90),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # ════════════════════════════════════════════
    # ABA 1 — PAINEL DE UNIDADES
    # ════════════════════════════════════════════
    with tabs[1]:
        col_search, col_filtro = st.columns([3,1])
        with col_search:
            busca = st.text_input("🔍", placeholder="Buscar cidade…", label_visibility="collapsed")
        with col_filtro:
            filtro = st.selectbox("Filtro", ["Todos","Crítico (>10%)","Atenção (5–10%)","Saudável (<5%)"],
                                  label_visibility="collapsed")

        def passa_filtro(nome, v):
            pct = len(v["offline"])/v["total"]*100 if v["total"] else 0
            if busca and busca.upper() not in nome: return False
            if filtro == "Crítico (>10%)"  and pct <= 10:             return False
            if filtro == "Atenção (5–10%)" and not (5 <= pct <= 10):  return False
            if filtro == "Saudável (<5%)"  and pct >= 5:              return False
            return True

        nomes = sorted(dados.keys(),
                       key=lambda n: (len(dados[n]["offline"])/dados[n]["total"]) if dados[n]["total"] else 0,
                       reverse=True)
        nomes_f = [n for n in nomes if passa_filtro(n, dados[n])]

        if not nomes_f:
            st.info("Nenhuma unidade encontrada com os filtros aplicados.")
        else:
            for linha in [nomes_f[i:i+COLUNAS_PAINEL] for i in range(0, len(nomes_f), COLUNAS_PAINEL)]:
                cols = st.columns(COLUNAS_PAINEL)
                for col, nome in zip(cols, linha):
                    v = dados[nome]; count = len(v["offline"]); total = v["total"]
                    pct = count/total*100 if total else 0
                    render_card(col, nome, count, total, pct, tendencias.get(nome), delta_offs.get(nome))

        # Detalhe
        if "detalhe" in st.session_state:
            cidade = st.session_state["detalhe"]
            entry  = dados.get(cidade, {"offline": pd.DataFrame(), "total": 0})
            df_det = entry["offline"]; total_u = entry["total"]
            pct_d  = round(len(df_det)/total_u*100, 1) if total_u else 0
            cor_d  = cor_hex(pct_d)
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem">
                <div style="background:rgba(124,58,237,.1);border:1px solid rgba(79,70,229,.3);
                    border-radius:8px;padding:6px 14px;font-size:11px;font-weight:600;
                    color:#a78bfa;text-transform:uppercase;letter-spacing:.5px">📍 Detalhamento</div>
                <div style="font-size:20px;font-weight:700;color:#f0f1f5">{cidade}</div>
                <div style="margin-left:auto;font-size:13px;font-weight:700;color:{cor_d}">
                    {len(df_det)} offline de {total_u} câmeras ({pct_d}%)
                </div>
            </div>
            """, unsafe_allow_html=True)

            if df_det.empty:
                st.success("Nenhuma câmera offline.")
            else:
                col_u  = next((c for c in df_det.columns if c.strip().lower() in ("usuário","usuario","user")), None)
                cols_t = [c for c in ["ID","Título","Observações"] if c in df_det.columns]
                if col_u:
                    for cliente in sorted(df_det[col_u].dropna().unique()):
                        sub = df_det[df_det[col_u] == cliente]
                        with st.expander(f"👤  {cliente}  —  {len(sub)} câmera(s)", expanded=True):
                            t = (sub[cols_t] if cols_t else sub).reset_index(drop=True)
                            t.index += 1; st.table(t)
                else:
                    t = (df_det[cols_t] if cols_t else df_det).reset_index(drop=True)
                    st.table(t)

            if st.button("← Voltar ao painel"):
                del st.session_state["detalhe"]; st.rerun()

    # ════════════════════════════════════════════
    # ABA 2 — % OFFLINE POR CIDADE
    # ════════════════════════════════════════════
    with tabs[2]:
        st.markdown("#### Percentual de câmeras offline por unidade")
        st.caption("Escala 0–100% · Verde <5% · Amarelo 5–10% · Vermelho >10%")

        df_bar = pd.DataFrame([
            {"Cidade": n, "Offline": len(v["offline"]), "Total": v["total"],
             "Pct": round(len(v["offline"])/v["total"]*100, 2) if v["total"] else 0}
            for n, v in dados.items()
        ]).sort_values("Pct", ascending=True)

        fig_bar = go.Figure()
        fig_bar.add_vrect(x0=0,  x1=5,   fillcolor="rgba(52,211,153,0.05)",  layer="below", line_width=0)
        fig_bar.add_vrect(x0=5,  x1=10,  fillcolor="rgba(251,191,36,0.05)",  layer="below", line_width=0)
        fig_bar.add_vrect(x0=10, x1=100, fillcolor="rgba(248,113,113,0.05)", layer="below", line_width=0)
        for xv, lbl in [(5,"5%"),(10,"10%")]:
            fig_bar.add_vline(x=xv, line_dash="dot", line_color="#1a1d2e", line_width=1.5,
                annotation_text=lbl, annotation_position="top",
                annotation_font=dict(color="#2a2f45", size=10))
        fig_bar.add_trace(go.Bar(
            y=df_bar["Cidade"], x=df_bar["Pct"], orientation="h",
            marker=dict(color=[cor_hex(p) for p in df_bar["Pct"]], line=dict(width=0)),
            text=[f"{p:.1f}%  ({o}/{t})" for p,o,t in zip(df_bar["Pct"],df_bar["Offline"],df_bar["Total"])],
            textposition="outside", textfont=dict(color="#3d4257",size=10,family="DM Mono"),
            hovertemplate="<b>%{y}</b><br>%{x:.1f}% offline<extra></extra>",
        ))
        fig_bar.update_layout(
            **pdefaults(), height=max(360, len(df_bar)*34), showlegend=False,
            xaxis=dict(range=[0,100], ticksuffix="%", gridcolor="#1a1d2e",
                       tickfont=dict(color="#2a2f45",size=10), zeroline=False),
            yaxis=dict(tickfont=dict(color="#9195a8",size=10,family="DM Sans"), gridcolor="#080a0f"),
            margin=dict(l=10, r=10, t=30, b=10), # Adicionado manual[cite: 1]
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ════════════════════════════════════════════
    # ABA 3 — RANKING DE CRITICIDADE
    # ════════════════════════════════════════════
    with tabs[3]:
        st.markdown("#### Ranking de criticidade")
        st.caption("Online (verde escuro) + Offline (vermelho) · Ordenado por % offline")

        df_rank = pd.DataFrame([
            {"Unidade": n, "Offline": len(v["offline"]), "Total": v["total"],
             "% Offline": round(len(v["offline"])/v["total"]*100,2) if v["total"] else 0,
             "Online": v["total"]-len(v["offline"])}
            for n, v in dados.items() if len(v["offline"]) > 0
        ]).sort_values("% Offline", ascending=False).reset_index(drop=True)
        df_rank.index += 1

        if df_rank.empty:
            st.success("🎉 Nenhuma unidade com câmeras offline no momento!")
        else:
            fig_rank = go.Figure()
            fig_rank.add_trace(go.Bar(
                name="Online", y=df_rank["Unidade"], x=df_rank["Online"],
                orientation="h", marker_color="#0d2e20",
                hovertemplate="%{y}<br>Online: %{x}<extra></extra>",
            ))
            fig_rank.add_trace(go.Bar(
                name="Offline", y=df_rank["Unidade"], x=df_rank["Offline"],
                orientation="h", marker_color="#f87171",
                text=[f'{p:.1f}%' for p in df_rank["% Offline"]],
                textposition="outside", textfont=dict(color="#5a5f73",size=10,family="DM Mono"),
                hovertemplate="%{y}<br>Offline: %{x} (%{text})<extra></extra>",
            ))
            fig_rank.update_layout(
                **pdefaults(), barmode="stack",
                height=max(360, len(df_rank)*40),
                xaxis=dict(title="Quantidade de câmeras", gridcolor="#1a1d2e",
                           tickfont=dict(color="#2a2f45",size=10), zeroline=False),
                yaxis=dict(tickfont=dict(color="#9195a8",size=10), gridcolor="#080a0f",
                           categoryorder="array",
                           categoryarray=df_rank["Unidade"].tolist()[::-1]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            font=dict(color="#5a5f73",size=11), bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=10, r=10, t=50, b=10), # Adicionado manual[cite: 1]
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

            df_show = df_rank[["Unidade","Offline","Total","% Offline"]].copy()
            df_show["% Offline"] = df_show["% Offline"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(df_show, use_container_width=True, height=min(400,(len(df_show)+1)*35+3))

    # ════════════════════════════════════════════
    # ABA 4 — HISTÓRICO & COMPARATIVO
    # ════════════════════════════════════════════
    with tabs[4]:
        st.markdown("#### Histórico de snapshots")
        df_snaps = listar_snapshots()

        if df_snaps.empty:
            st.info("Nenhum snapshot gravado ainda. Use o painel lateral para salvar o estado atual.")
        else:
            # ── Filtro por intervalo de datas ──
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
                opcoes = {f"{r['label']}  ({r['gravado_em']})": {"id": r["id"], "gravado_em": r["gravado_em"]} for _, r in df_snaps_filtrado.iterrows()}

                col_a, col_b, col_dl_h = st.columns([2,2,1])
                with col_a:
                    sel_a = st.selectbox("📅 Snapshot A (base)", list(opcoes.keys()),
                                         index=min(1,len(opcoes)-1))
                with col_b:
                    sel_b = st.selectbox("📅 Snapshot B (recente)", list(opcoes.keys()), index=0)

                id_a  = opcoes[sel_a]["id"]
                id_b  = opcoes[sel_b]["id"]
                # Formatar data gravada como DD/MM/YYYY HH:MM para legenda
                def fmt_dt(s):
                    try: return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                    except: return s
                leg_a = fmt_dt(opcoes[sel_a]["gravado_em"])
                leg_b = fmt_dt(opcoes[sel_b]["gravado_em"])
                df_a = carregar_snapshot(id_a).rename(columns={"offline":"off_a","total":"tot_a","pct_offline":"pct_a"})
                df_b = carregar_snapshot(id_b).rename(columns={"offline":"off_b","total":"tot_b","pct_offline":"pct_b"})
                df_comp = pd.merge(df_a, df_b, on="cidade", how="outer").fillna(0)
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
                    <div style="background:#0d0f16;border:1px solid #1a1d2e;border-radius:10px;
                        padding:12px 20px;flex:1;text-align:center">
                        <div style="font-size:10px;color:#2a2f45;font-weight:600;letter-spacing:.7px;
                            text-transform:uppercase">Melhoraram</div>
                        <div style="font-size:28px;font-weight:700;color:#34d399;
                            font-family:'DM Mono',monospace">{melhoraram}</div>
                    </div>
                    <div style="background:#0d0f16;border:1px solid #1a1d2e;border-radius:10px;
                        padding:12px 20px;flex:1;text-align:center">
                        <div style="font-size:10px;color:#2a2f45;font-weight:600;letter-spacing:.7px;
                            text-transform:uppercase">Pioraram</div>
                        <div style="font-size:28px;font-weight:700;color:#f87171;
                            font-family:'DM Mono',monospace">{pioraram}</div>
                    </div>
                    <div style="background:#0d0f16;border:1px solid #1a1d2e;border-radius:10px;
                        padding:12px 20px;flex:1;text-align:center">
                        <div style="font-size:10px;color:#2a2f45;font-weight:600;letter-spacing:.7px;
                            text-transform:uppercase">Estáveis</div>
                        <div style="font-size:28px;font-weight:700;color:#3d4257;
                            font-family:'DM Mono',monospace">{estaveis}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Gráfico A vs B
                st.markdown("**Comparativo % offline por cidade**")
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Bar(
                    name=leg_a, y=df_comp["cidade"], x=df_comp["pct_a"],
                    orientation="h", marker_color="#4f46e5", opacity=0.7,
                    hovertemplate="%{y}<br>%{x:.1f}%<extra>A</extra>",
                ))
                fig_comp.add_trace(go.Bar(
                    name=leg_b, y=df_comp["cidade"], x=df_comp["pct_b"],
                    orientation="h", marker_color="#7c3aed",
                    hovertemplate="%{y}<br>%{x:.1f}%<extra>B</extra>",
                ))
                fig_comp.update_layout(
                    **pdefaults(), barmode="group",
                    height=max(400, len(df_comp)*44),
                    xaxis=dict(range=[0,100], ticksuffix="%", gridcolor="#1a1d2e",
                               tickfont=dict(color="#2a2f45",size=10), zeroline=False),
                    yaxis=dict(tickfont=dict(color="#9195a8",size=10)),
                    legend=dict(font=dict(size=11,color="#5a5f73"), bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig_comp, use_container_width=True)

                # Gráfico delta — variação em câmeras (não pp)
                st.markdown("**Variação (B − A) em número de câmeras offline**")
                st.caption("🟢 Reduziu câmeras offline · 🔴 Aumentou câmeras offline · ⚫ Estável")
                df_delta = df_comp.sort_values("delta_off", ascending=True)
                cores_d  = ["#f87171" if d > 0 else ("#34d399" if d < 0 else "#1a1d2e")
                            for d in df_delta["delta_off"]]
                fig_d = go.Figure(go.Bar(
                    y=df_delta["cidade"], x=df_delta["delta_off"], orientation="h",
                    marker=dict(color=cores_d, line=dict(width=0)),
                    text=[f"{'+' if d>0 else ''}{int(d)} câm." for d in df_delta["delta_off"]],
                    textposition="outside", textfont=dict(color="#3d4257",size=10,family="DM Mono"),
                    hovertemplate="%{y}<br>Δ %{x:+d} câmeras<extra></extra>",
                ))
                fig_d.add_vline(x=0, line_color="#1a1d2e", line_width=1)
                fig_d.update_layout(
                    **pdefaults(), height=max(400, len(df_delta)*34), showlegend=False,
                    xaxis=dict(gridcolor="#1a1d2e", tickfont=dict(color="#2a2f45",size=10), zeroline=False),
                    yaxis=dict(tickfont=dict(color="#9195a8",size=10)),
                    margin=dict(l=10, r=70, t=20, b=10),
                )
                st.plotly_chart(fig_d, use_container_width=True)

                # Tabela comparativa
                st.markdown("---")
                st.markdown("**Tabela comparativa detalhada**")
                df_tbl = df_comp[["cidade","tot_a","off_a","pct_a","tot_b","off_b","pct_b","delta_pct","delta_off"]].copy()
                df_tbl.columns = ["Cidade","Total A","Off A","% A","Total B","Off B","% B","Δ% (pp)","Δ Off"]
                df_tbl["% A"]     = df_tbl["% A"].apply(lambda x: f"{x:.1f}%")
                df_tbl["% B"]     = df_tbl["% B"].apply(lambda x: f"{x:.1f}%")
                df_tbl["Δ% (pp)"] = df_tbl["Δ% (pp)"].apply(lambda x: f"{'+' if x>0 else ''}{x:.1f}")
                df_tbl["Δ Off"]   = df_tbl["Δ Off"].apply(lambda x: f"{'+' if x>0 else ''}{int(x)}")
                df_tbl = df_tbl.reset_index(drop=True); df_tbl.index += 1
                st.dataframe(df_tbl, use_container_width=True, height=min(500,(len(df_tbl)+1)*35+3))

                # Notas do snapshot B
                row_b = df_snaps_filtrado[df_snaps_filtrado["id"] == id_b].iloc[0]
                if str(row_b.get("notas","")).strip():
                    st.markdown("---")
                    st.markdown(f"📝 **Observações do snapshot B:** {row_b['notas']}")

            # Gerenciar snapshots (sempre visível, mostra todos)
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