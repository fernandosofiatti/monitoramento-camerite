import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
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

from src.theme import injetar_css_global
from src.constants import *  # noqa: F401,F403 (paths, COL_*, SUPABASE_*, mapas de estados)
from src.utils import (
    agora_sao_paulo,
    agora_sao_paulo_str,
    normalizar_coluna,
    encontrar_coluna_por_chaves,
    parse_ultima_atualizacao,
    formatar_ultima_atualizacao,
)

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


# CSS global extraído para src/theme.py (Fase 2 da modularização)
injetar_css_global()
# Constantes (paths, COL_*, SUPABASE_*, mapas de estados) movidas para src/constants.py

# ─────────────────────────────────────────────
# HELPERS DE COR
# ─────────────────────────────────────────────
def _pct_offline_vec(offline, total, casas: int | None = None):
    """% offline vetorizado (NumPy), seguro contra divisão por zero.

    Substitui os vários `.apply(lambda r: r.offline/r.total*100 ..., axis=1)` —
    resultado idêntico, porém sem loop linha a linha.
    """
    off = np.asarray(offline, dtype=float)
    tot = np.asarray(total, dtype=float)
    pct = np.where(tot > 0, off / np.where(tot > 0, tot, 1.0) * 100.0, 0.0)
    return np.round(pct, casas) if casas is not None else pct


# ── Parâmetros configuráveis (editáveis na aba Configuração) ──
SLA_META = 90.0        # meta de SLA da operação (%)
PESO_LPR = 3.0         # peso das câmeras LPR no SLA (LPR parada = dinheiro parado)
LPR_KEYWORD = "LPR"    # como identificar uma câmera LPR (texto no nome)
CFG_ATENCAO_PCT = 5.0  # limite superior de "Saudável" / início de "Atenção" (%)
CFG_CRITICO_PCT = 10.0 # início de "Crítico" (%)
CFG_ACIMA_HORAS = 24   # horas para contar como câmera offline "há muito tempo"
# Pesos do score de criticidade (usado no Top 5 e ordenações)
CFG_W_OFFLINE = 6.0
CFG_W_PCT = 2.0
CFG_W_HORAS_DIV = 12.0
CFG_W_ACIMA = 8.0
CFG_W_DIASCRIT = 5.0
CFG_TEND_JANELA_DIAS = 7   # janela (dias) para a "Tendência" dos KPIs (recente, sobre média móvel)

CONFIG_DEFAULTS = {
    "SLA_META": 90.0, "PESO_LPR": 3.0, "LPR_KEYWORD": "LPR",
    "CFG_ATENCAO_PCT": 5.0, "CFG_CRITICO_PCT": 10.0, "CFG_ACIMA_HORAS": 24,
    "CFG_W_OFFLINE": 6.0, "CFG_W_PCT": 2.0, "CFG_W_HORAS_DIV": 12.0,
    "CFG_W_ACIMA": 8.0, "CFG_W_DIASCRIT": 5.0,
    "CFG_TEND_JANELA_DIAS": 7,
}
CONFIG_PATH = os.path.join(BASE_DIR, "config_painel.json")


def _config_atual() -> dict:
    """Config vigente lida dos globais do módulo."""
    g = globals()
    return {k: g.get(k, v) for k, v in CONFIG_DEFAULTS.items()}


def aplicar_config(cfg: dict) -> None:
    """Aplica um dicionário de config aos globais do módulo (usado a cada rerun)."""
    g = globals()
    for k, default in CONFIG_DEFAULTS.items():
        val = cfg.get(k, default)
        try:
            val = str(val) if isinstance(default, str) else type(default)(val)
        except Exception:
            val = default
        g[k] = val


def carregar_config() -> dict:
    """Lê a config do arquivo JSON (se existir), completando com os padrões."""
    cfg = dict(CONFIG_DEFAULTS)
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update({k: v for k, v in json.load(f).items() if k in CONFIG_DEFAULTS})
    except Exception:
        pass
    return cfg


def salvar_config(cfg: dict) -> bool:
    """Persiste a config em JSON. Retorna True se gravou."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({k: cfg.get(k, d) for k, d in CONFIG_DEFAULTS.items()}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def calcular_sla_operacao(df_origem, peso: float | None = None, wl_validos=None) -> dict:
    """SLA ponderado: câmeras LPR (nome contém a palavra-chave) pesam `peso`× as comuns.

    SLA = (LPR_no_ar*peso + comuns_no_ar) / (LPR_total*peso + comuns_total) * 100
    Se `wl_validos` for informado, considera só as câmeras desses clientes (mesmo
    universo do painel), evitando contar câmeras fora do recorte.
    """
    peso = float(PESO_LPR if peso is None else peso)
    base = {"sla": 0.0, "peso": peso, "lpr_total": 0, "lpr_online": 0, "lpr_off": 0,
            "reg_total": 0, "reg_online": 0, "reg_off": 0}
    if df_origem is None or getattr(df_origem, "empty", True):
        return base
    df = df_origem.copy()
    df.columns = [str(c).strip() for c in df.columns]
    if COL_NOME_CAM not in df.columns or COL_STATUS not in df.columns:
        return base
    # Restringe ao universo de clientes do painel (se informado).
    if wl_validos and COL_WL in df.columns:
        validos = {str(x).strip() for x in wl_validos if str(x).strip()}
        df = df[df[COL_WL].astype(str).str.strip().isin(validos)]
        if df.empty:
            return base
    nome = df[COL_NOME_CAM].astype(str)
    status = df[COL_STATUS].astype(str).str.strip().str.upper()
    is_lpr = nome.str.contains(LPR_KEYWORD, case=False, na=False).to_numpy()
    is_off = status.eq("OFFLINE").to_numpy()
    lpr_total = int(is_lpr.sum())
    lpr_off = int((is_lpr & is_off).sum())
    reg_total = int((~is_lpr).sum())
    reg_off = int((~is_lpr & is_off).sum())
    lpr_on = lpr_total - lpr_off
    reg_on = reg_total - reg_off
    denom = lpr_total * peso + reg_total
    sla = ((lpr_on * peso + reg_on) / denom * 100.0) if denom else 0.0
    return {"sla": round(float(sla), 1), "peso": peso,
            "lpr_total": lpr_total, "lpr_online": lpr_on, "lpr_off": lpr_off,
            "reg_total": reg_total, "reg_online": reg_on, "reg_off": reg_off}


@st.cache_data(ttl=1800, show_spinner=False)
def kpi_historico_30d(dias: int = 30) -> pd.DataFrame:
    """Série por snapshot dos KPIs simples (dos resumos por cliente): offline, disponibilidade, críticos."""
    df = carregar_historico_clientes(dias)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["gravado_dt"] = pd.to_datetime(df["gravado_em"], errors="coerce")
    df = df[df["gravado_dt"].notna()]
    for c in ["offline", "total", "pct_offline"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    if df.empty:
        return pd.DataFrame()
    g = (df.groupby(["snapshot_id", "gravado_dt"], as_index=False)
           .agg(offline=("offline", "sum"), total=("total", "sum")))
    g["online"] = g["total"] - g["offline"]
    g["disp"] = _pct_offline_vec(g["online"], g["total"])
    g["pct_off"] = _pct_offline_vec(g["offline"], g["total"])
    crit = (df.assign(_c=(df["pct_offline"] > CFG_CRITICO_PCT).astype(int))
              .groupby("snapshot_id", as_index=False)["_c"].sum()
              .rename(columns={"_c": "criticos"}))
    g = g.merge(crit, on="snapshot_id", how="left")
    return g.sort_values("gravado_dt").reset_index(drop=True)


@st.cache_data(ttl=1800, show_spinner=False)
def sla_historico_30d(dias: int = 30, peso: float | None = None) -> pd.DataFrame:
    """Série do SLA ponderado por snapshot.

    Faz UMA consulta trazendo só (snapshot_id, nome_camera, status_camera) de todos
    os snapshots do período e agrega vetorizado — bem mais rápido que 1 consulta por snapshot.
    """
    peso = float(PESO_LPR if peso is None else peso)
    hist = carregar_historico_clientes(dias)
    if hist is None or hist.empty:
        return pd.DataFrame()
    hist = hist.copy()
    hist["gravado_dt"] = pd.to_datetime(hist["gravado_em"], errors="coerce")
    hist = hist[hist["gravado_dt"].notna()]
    if hist.empty:
        return pd.DataFrame()
    datas = hist.groupby("snapshot_id", as_index=False)["gravado_dt"].first()
    ids = [int(s) for s in datas["snapshot_id"].tolist()]
    if not ids:
        return pd.DataFrame()

    # Uma única consulta (só as colunas necessárias) para todos os snapshots do período.
    ids_str = ",".join(str(i) for i in ids)
    df, erro = _supabase_select_all(
        SNAPSHOT_TABLE,
        params={"select": "snapshot_id,nome_camera,status_camera", "snapshot_id": f"in.({ids_str})"},
        page_size=5000,
    )
    if erro or df is None or df.empty:
        return pd.DataFrame()

    nome = df["nome_camera"].astype(str)
    status = df["status_camera"].astype(str).str.upper()
    df["_lpr"] = nome.str.contains(LPR_KEYWORD, case=False, na=False)
    df["_off"] = status.eq("OFFLINE")
    # Agregação vetorizada por snapshot.
    df["_lpr_off"] = df["_lpr"] & df["_off"]
    df["_reg"] = ~df["_lpr"]
    df["_reg_off"] = df["_reg"] & df["_off"]
    ga = df.groupby("snapshot_id").agg(
        lpr_t=("_lpr", "sum"), lpr_off=("_lpr_off", "sum"),
        reg_t=("_reg", "sum"), reg_off=("_reg_off", "sum"),
    )
    lpr_on = ga["lpr_t"] - ga["lpr_off"]
    reg_on = ga["reg_t"] - ga["reg_off"]
    denom = ga["lpr_t"] * peso + ga["reg_t"]
    ga["sla"] = np.where(denom > 0, (lpr_on * peso + reg_on) / np.where(denom > 0, denom, 1) * 100.0, 0.0).round(1)

    mapa_data = dict(zip(datas["snapshot_id"].astype(int), datas["gravado_dt"]))
    ga = ga.reset_index()
    ga["snapshot_id"] = ga["snapshot_id"].astype(int)
    ga["gravado_dt"] = ga["snapshot_id"].map(mapa_data)
    out = ga[["gravado_dt", "sla"]].dropna(subset=["gravado_dt"]).sort_values("gravado_dt").reset_index(drop=True)
    return out


def cor_hex(pct: float) -> str:
    if pct <= CFG_ATENCAO_PCT:  return "#14b8a6"
    elif pct <= CFG_CRITICO_PCT: return "#f59e0b"
    else:                        return "#ef4444"

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


# agora_sao_paulo / agora_sao_paulo_str movidas para src/utils.py

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
    if pct > CFG_CRITICO_PCT:  return f"Crítico (>{CFG_CRITICO_PCT:g}%)"
    if pct > CFG_ATENCAO_PCT:  return f"Atenção ({CFG_ATENCAO_PCT:g}-{CFG_CRITICO_PCT:g}%)"
    return f"Saudável (0-{CFG_ATENCAO_PCT:g}%)"


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
# HELPERS SUPABASE / BD ONLINE  → movidos para src/db/supabase.py
# ─────────────────────────────────────────────
from src.ui.helpers import escape_html, _rgba, tabela_clara, render_dataframe
from src.db.supabase import (
    get_secret_value,
    supabase_configurado,
    get_supabase_key,
    supabase_headers,
    supabase_table_url,
    supabase_base_url,
    preparar_df_para_supabase,
    limpar_valor_json,
    df_para_registros_json,
    converter_supabase_para_df_gov,
    carregar_cameras_supabase,
    formatar_data_hora_br,
    carregar_ultima_atualizacao_base,
    registrar_historico_importacao,
    _postgrest_in_filter_text,
    _postgrest_in_filter_int,
    apagar_cameras_origem_por_whitelabel,
    enviar_df_supabase,
    sql_criacao_supabase,
    erro_supabase_amigavel,
)


# Central de Ações descontinuada (feature removida a pedido).

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
# Leitura/processamento de dados → movidos para src/data/loaders.py
from src.data.loaders import (
    carregar_clientes,
    carregar_clientes_prefeitura,
    carregar_clientes_franqueado,
    parse_prefeitura_localidade,
    preencher_cidade_estado_por_clientes,
    ler_csv_gov,
    carregar_xlsx_individuais,
    processar_df_gov,
    carregar_dados,
    calcular_saude_dataframe,
    calcular_saude_dados,
)

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

@st.cache_data(ttl=120, show_spinner=False)
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
        df_group["Pct"] = _pct_offline_vec(df_group["offline"], df_group["total"])
    
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

# carregar_dados / calcular_saude_* movidos para src/data/loaders.py (importados acima)
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

    wl = df_cam[COL_WL].astype(str).str.strip()

    # Mapeamentos a partir de `dados` (evita lookup por linha).
    d = dados or {}
    mapa_cidade = {str(k): (v.get("cidade_estado") or v.get("nome_cliente", f"ID {k}")) for k, v in d.items()}
    mapa_empresa = {str(k): str(v.get("nome_empresa", "") or "") for k, v in d.items()}

    nome_cliente = wl.map(mapa_cidade)
    nome_cliente = nome_cliente.where(nome_cliente.notna(), "ID " + wl)

    empresa_col = df_cam[COL_EMPRESA].astype(str).replace({"nan": ""}).fillna("").str.strip()
    empresa_fallback = wl.map(mapa_empresa).fillna("")
    nome_empresa = empresa_col.where(empresa_col != "", empresa_fallback)

    def _limpa(serie) -> pd.Series:
        return serie.astype(str).replace({"nan": ""}).fillna("")

    df_out = pd.DataFrame({
        "wl_id": wl.to_numpy(),
        "nome_cliente": nome_cliente.astype(str).to_numpy(),
        "nome_empresa": nome_empresa.astype(str).to_numpy(),
        "id_camera": df_cam[COL_ID_CAM].astype(str).str.strip().to_numpy(),
        "nome_camera": _limpa(df_cam[COL_NOME_CAM]).to_numpy(),
        "ultima_atualizacao": pd.Series(ultima_fmt).astype(str).replace({"nan": ""}).fillna("").to_numpy(),
        "data_cadastro": pd.Series(cadastro_fmt).astype(str).replace({"nan": ""}).fillna("").to_numpy(),
        "status_camera": _limpa(df_cam[COL_STATUS]).str.upper().to_numpy(),
    })
    return df_out.drop_duplicates(subset=["wl_id", "id_camera"], keep="last").reset_index(drop=True)


@st.cache_data(ttl=120)
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


@st.cache_data(ttl=120)
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


@st.cache_data(ttl=600)
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


@st.cache_data(ttl=120)
def obter_datas_snapshots(snapshot_ids: list[int]) -> pd.DataFrame:
    df = listar_snapshots()
    if df.empty:
        return pd.DataFrame(columns=["id", "gravado_em"])
    ids = [int(x) for x in snapshot_ids]
    return df[df["id"].astype(int).isin(ids)][["id", "gravado_em"]].copy()

@st.cache_data(ttl=120)
def calcular_recorrencia(dias: int = 30) -> dict:
    df_hist = carregar_historico_clientes(dias)
    if df_hist.empty:
        return {}

    df_hist["dia"] = pd.to_datetime(df_hist["gravado_em"], errors="coerce").dt.date
    rows = []
    for wl_id, grupo in df_hist.groupby("wl_id"):
        dias_off = grupo.loc[grupo["offline"] > 0, "dia"].nunique()
        dias_crit = grupo.loc[grupo["pct_offline"] > CFG_CRITICO_PCT, "dia"].nunique()
        rows.append({
            "wl_id": wl_id,
            "dias_offline": int(dias_off),
            "dias_criticos": int(dias_crit),
            "pior_pct": float(grupo["pct_offline"].max()),
            "maior_offline": int(grupo["offline"].max()),
        })
    return {r["wl_id"]: r for r in rows}

@st.cache_data(ttl=120, show_spinner=False)
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
        acima_24h = int((validos.dt.total_seconds() >= CFG_ACIMA_HORAS * 3600).sum()) if not validos.empty else 0
        rec = recorrencia.get(wl_id, {})
        score = (offline * CFG_W_OFFLINE) + (pct * CFG_W_PCT) + max(max_h, 0) / CFG_W_HORAS_DIV + (acima_24h * CFG_W_ACIMA) + (rec.get("dias_criticos", 0) * CFG_W_DIASCRIT)
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
# escape_html / _rgba / tabela_clara / render_dataframe movidos para src/ui/helpers.py


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
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        wl_sel = st.selectbox(
            "Cliente",
            options=opcoes_ids,
            format_func=lambda wl: clientes_hist.get(wl, wl),
            key="tend_cliente",
        )
    with col_c2:
        opcoes_comp = ["—"] + [w for w in opcoes_ids if str(w) != str(wl_sel)]
        wl_comp = st.selectbox(
            "Comparar com (opcional)",
            options=opcoes_comp,
            format_func=lambda wl: "—" if wl == "—" else clientes_hist.get(wl, wl),
            key="tend_cliente_comp",
        )

    agrupar_dia = st.toggle("Agrupar por dia (média diária)", value=False, key="tend_agrupar_dia")

    def _serie_cliente(wl) -> pd.DataFrame:
        s = df_hist[df_hist["wl_id"].astype(str) == str(wl)].sort_values("gravado_dt").copy()
        if s.empty:
            return s
        for c in ["offline", "total", "pct_offline"]:
            s[c] = pd.to_numeric(s[c], errors="coerce").fillna(0)
        if agrupar_dia:
            s["dia"] = s["gravado_dt"].dt.floor("D")
            g = s.groupby("dia", as_index=False).agg(
                offline=("offline", "sum"), total=("total", "sum"),
                gravado_dt=("gravado_dt", "last"),
            )
            g["pct_offline"] = _pct_offline_vec(g["offline"], g["total"])
            g["label"] = g["dia"].dt.strftime("%d/%m")
            return g.sort_values("gravado_dt").reset_index(drop=True)
        return s.reset_index(drop=True)

    df_cli = _serie_cliente(wl_sel)
    if df_cli.empty:
        st.warning(f"Nenhum snapshot encontrado para **{clientes_hist.get(wl_sel, wl_sel)}** no período.")
        return

    nome_cliente = clientes_hist.get(wl_sel, wl_sel)
    y = df_cli["pct_offline"].astype(float).reset_index(drop=True)
    x_dt = df_cli["gravado_dt"].reset_index(drop=True)
    n = len(y)
    pct_atual = float(y.iloc[-1])
    pct_inicio = float(y.iloc[0])
    pct_max = float(y.max())
    pct_min = float(y.min())
    pct_medio = float(y.mean())
    variacao = pct_atual - pct_inicio

    # Regressão linear via NumPy (mínimos quadrados) → inclinação em p.p./dia.
    x_days = (x_dt - x_dt.iloc[0]).dt.total_seconds() / 86400.0
    slope = 0.0
    intercept = pct_medio
    if n >= 2 and float(x_days.iloc[-1]) > float(x_days.iloc[0]):
        try:
            slope, intercept = np.polyfit(x_days.to_numpy(dtype=float), y.to_numpy(dtype=float), 1)
            slope, intercept = float(slope), float(intercept)
        except Exception:
            slope, intercept = 0.0, pct_medio
    if slope > 0.05:
        tend_txt, tend_cor = "▲ Piorando", "#dc2626"
    elif slope < -0.05:
        tend_txt, tend_cor = "▼ Melhorando", "#059669"
    else:
        tend_txt, tend_cor = "= Estável", "#8B7AA3"

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("% Offline atual", f"{pct_atual:.1f}%")
    m2.metric("Variação", f"{variacao:+.1f} p.p.")
    m3.metric("Pior momento", f"{pct_max:.1f}%")
    m4.metric("Melhor momento", f"{pct_min:.1f}%")
    m5.metric("Média", f"{pct_medio:.1f}%")
    m6.metric("Tendência", tend_txt)

    # Controles de sobreposição.
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1.3, 1.1])
    show_mm = c1.toggle("Média móvel", value=True, key="tend_mm")
    show_trend = c2.toggle("Linha de tendência", value=True, key="tend_reg")
    show_meta = c3.toggle("Meta (SLA)", value=False, key="tend_meta")
    with c4:
        meta_disp = st.number_input(
            "Disponibilidade alvo (%)", min_value=80.0, max_value=100.0, value=98.0, step=0.5,
            key="tend_meta_val", disabled=not show_meta,
        )
    with c5:
        projecao_dias = st.number_input(
            "Projetar (dias)", min_value=0, max_value=30, value=0, step=1,
            key="tend_proj", help="Estende a linha de tendência N dias à frente (0 = desligado).",
        )
    meta_offline = max(0.0, 100.0 - float(meta_disp))

    fig = go.Figure()
    fig.add_hrect(y0=0, y1=5, fillcolor="#dff8f3", opacity=0.25, line_width=0, layer="below")
    fig.add_hrect(y0=5, y1=10, fillcolor="#fef9c3", opacity=0.25, line_width=0, layer="below")
    fig.add_hrect(y0=10, y1=100, fillcolor="#fee2e2", opacity=0.20, line_width=0, layer="below")

    # Série principal.
    fig.add_trace(go.Scatter(
        x=x_dt,
        y=y.tolist(),
        mode="lines+markers",
        line=dict(color="#7C3AED", width=2.4, shape="spline", smoothing=0.6),
        marker=dict(color=[cor_hex(v) for v in y], size=8, line=dict(color="#ffffff", width=1)),
        text=[
            f"<b>{escape_html(r['label'])}</b><br>{r['gravado_dt'].strftime('%d/%m/%Y %H:%M')}<br>"
            f"% Offline: <b>{r['pct_offline']:.1f}%</b><br>Offline: {int(r['offline'])} de {int(r['total'])}"
            for _, r in df_cli.iterrows()
        ],
        hovertemplate="%{text}<extra></extra>",
        name="% Offline",
    ))

    # Série de comparação (outro cliente).
    if wl_comp and wl_comp != "—":
        df_comp = _serie_cliente(wl_comp)
        if not df_comp.empty:
            nome_comp = clientes_hist.get(wl_comp, wl_comp)
            fig.add_trace(go.Scatter(
                x=df_comp["gravado_dt"],
                y=df_comp["pct_offline"].tolist(),
                mode="lines+markers",
                line=dict(color="#f59e0b", width=2, dash="solid", shape="spline", smoothing=0.6),
                marker=dict(size=5, color="#f59e0b"),
                opacity=0.85,
                name=f"{nome_comp[:20]} (comparação)",
                hovertemplate=f"<b>{escape_html(nome_comp)}</b><br>%{{x|%d/%m/%Y %H:%M}}<br>% Offline: %{{y:.1f}}%<extra></extra>",
            ))

    # Média móvel.
    if show_mm and n >= 3:
        janela = max(2, min(7, n // 3))
        mm = y.rolling(janela, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=x_dt, y=mm.tolist(), mode="lines",
            line=dict(color="#0ea5e9", width=2, dash="solid"),
            opacity=0.9, name=f"Média móvel ({janela})",
            hovertemplate="Média móvel: %{y:.1f}%<extra></extra>",
        ))

    # Linha de tendência (regressão).
    if show_trend and n >= 2 and float(x_days.iloc[-1]) > 0:
        y0 = intercept + slope * float(x_days.iloc[0])
        y1 = intercept + slope * float(x_days.iloc[-1])
        fig.add_trace(go.Scatter(
            x=[x_dt.iloc[0], x_dt.iloc[-1]], y=[max(0, y0), max(0, y1)], mode="lines",
            line=dict(color=tend_cor, width=2, dash="dash"),
            name=f"Tendência ({slope:+.2f} p.p./dia)",
            hovertemplate="Tendência<extra></extra>",
        ))

        # Projeção N dias à frente (continuação pontilhada + valor projetado).
        if projecao_dias and projecao_dias > 0:
            x_fim_days = float(x_days.iloc[-1]) + float(projecao_dias)
            y_proj = intercept + slope * x_fim_days
            y_proj_clip = min(100.0, max(0.0, y_proj))
            x_proj_dt = x_dt.iloc[-1] + pd.Timedelta(days=int(projecao_dias))
            fig.add_trace(go.Scatter(
                x=[x_dt.iloc[-1], x_proj_dt],
                y=[max(0, y1), y_proj_clip],
                mode="lines+markers+text",
                line=dict(color=tend_cor, width=2, dash="dot"),
                marker=dict(size=[0, 9], color=tend_cor, symbol="diamond"),
                text=["", f"  ~{y_proj_clip:.1f}%"],
                textposition="top center",
                textfont=dict(color=tend_cor, size=11),
                name=f"Projeção +{int(projecao_dias)}d",
                hovertemplate=f"Projeção em +{int(projecao_dias)} dias: <b>{y_proj_clip:.1f}%</b><extra></extra>",
            ))

    # Meta / SLA.
    if show_meta:
        fig.add_hline(
            y=meta_offline, line_dash="dashdot", line_color="#059669", line_width=1.6,
            annotation_text=f"Meta ≤ {meta_offline:.1f}% offline ({meta_disp:.1f}% disp.)",
            annotation_position="top left",
            annotation_font=dict(color="#059669", size=11),
        )

    fig.add_hline(y=5, line_dash="dot", line_color="#14b8a6", line_width=1)
    fig.add_hline(y=10, line_dash="dot", line_color="#f59e0b", line_width=1)
    candidatos_top = [pct_max * 1.25, 12.0]
    if show_meta:
        candidatos_top.append(meta_offline * 1.3)
    if wl_comp and wl_comp != "—":
        _dc = _serie_cliente(wl_comp)
        if not _dc.empty:
            candidatos_top.append(float(_dc["pct_offline"].max()) * 1.15)
    if show_trend and projecao_dias and projecao_dias > 0 and n >= 2 and float(x_days.iloc[-1]) > 0:
        candidatos_top.append(min(100.0, max(0.0, intercept + slope * (float(x_days.iloc[-1]) + float(projecao_dias)))) * 1.15)
    y_top = min(100.0, max(candidatos_top))
    fig.update_layout(
        **{k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=10, r=30, t=20, b=70),
        xaxis=dict(tickangle=-35, gridcolor="#F3E8FF", tickformat="%d/%m %H:%M"),
        yaxis=dict(ticksuffix="%", gridcolor="#F3E8FF", range=[0, y_top]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
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
    agg["pct_offline"] = _pct_offline_vec(agg["offline"], agg["total"])

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
    # Valores em negrito.
    dfp["_texto"] = dfp.apply(formato_texto, axis=1).map(lambda t: f"<b>{t}</b>")

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
    grp["Pct"] = _pct_offline_vec(grp["Offline"], grp["Total"], casas=1)

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


# render_aba_padrao_quedas removida (feature Padrão de Quedas descontinuada)
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


@st.cache_data(ttl=600, show_spinner=False)
def _png_variacao_liquida(barras: tuple, titulo: str = "Variação líquida de offline") -> bytes | None:
    """Gera um PNG em alta resolução (4x, fundo branco) do gráfico de variação líquida.

    Retorna None se o kaleido não estiver disponível (aí o app orienta usar o ícone 📷).
    Cacheado pela assinatura das barras para não regerar a cada rerun.
    """
    try:
        import plotly.io as pio
    except Exception:
        return None
    clientes = [b[0] for b in barras]
    deltas = [float(b[1]) for b in barras]
    if not clientes:
        return None
    cores = ["#f43f5e" if d > 0 else ("#14b8a6" if d < 0 else "#cbb9e6") for d in deltas]
    fig = go.Figure(go.Bar(
        y=clientes, x=deltas, orientation="h",
        marker=dict(color=cores, line=dict(width=0)),
        text=[f"{'+' if d > 0 else ''}{int(d)}" for d in deltas],
        textposition="outside", textfont=dict(color="#4A3D5C", size=13, family="DM Mono"),
        cliponaxis=False, width=0.62,
    ))
    try:
        fig.update_traces(marker_cornerradius=8)
    except Exception:
        pass
    fig.add_vline(x=0, line_color="#D9CDEF", line_width=1.5)
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=22, color="#171126", family="DM Sans"), x=0.01, y=0.985),
        paper_bgcolor="white", plot_bgcolor="white", showlegend=False,
        font=dict(family="DM Sans", size=13),
        xaxis=dict(gridcolor="#E9D5FF", tickfont=dict(color="#6B5A7A", size=12), zeroline=False),
        yaxis=dict(tickfont=dict(color="#3A3550", size=12)),
        margin=dict(l=10, r=100, t=64, b=34),
    )
    altura = max(560, len(clientes) * 36)
    try:
        return pio.to_image(fig, format="png", scale=4, width=1500, height=altura, engine="kaleido")
    except Exception:
        return None


# _rgba movido para src/ui/helpers.py


def _area_kpi_fig(x_dt, y, cor: str, sufixo: str = "", nome: str = "") -> "go.Figure":
    y = list(y)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(x_dt), y=y, mode="lines",
        line=dict(color=cor, width=2.6, shape="spline", smoothing=0.6),
        fill="tozeroy", fillcolor=_rgba(cor, 0.14),
        hovertemplate="%{x|%d/%m %H:%M}<br><b>%{y}" + sufixo + "</b><extra></extra>",
        name=nome,
    ))
    try:
        fig.update_traces(fillgradient=dict(type="vertical",
            colorscale=[[0.0, _rgba(cor, 0.02)], [1.0, _rgba(cor, 0.22)]]))
    except Exception:
        pass
    if x_dt is not None and len(list(x_dt)):
        fig.add_trace(go.Scatter(
            x=[list(x_dt)[-1]], y=[y[-1]], mode="markers",
            marker=dict(color=cor, size=9, line=dict(color="#ffffff", width=2)),
            showlegend=False, hoverinfo="skip",
        ))
    fig.update_layout(
        **{k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=260, margin=dict(l=10, r=16, t=10, b=30), showlegend=False,
        xaxis=dict(tickformat="%d/%m", gridcolor="#F1E9FC", tickfont=dict(color="#B8A9CC", size=10), showline=False, zeroline=False),
        yaxis=dict(ticksuffix=sufixo, gridcolor="#F1E9FC", tickfont=dict(color="#B8A9CC", size=10), rangemode="tozero"),
    )
    return fig


def _tendencia_recente(valores, datas=None, dias: int | None = None) -> tuple[float, str]:
    """Tendência recente: inclinação sobre a MÉDIA MÓVEL, só nos últimos `dias`.

    Evita que um pico isolado (ex.: um dia de 494) ou o período inteiro contradiga
    o que o fim do gráfico mostra. Retorna (slope_por_dia, rótulo).
    """
    dias = int(CFG_TEND_JANELA_DIAS if dias is None else dias)
    s = pd.to_numeric(pd.Series(list(valores)), errors="coerce")
    if datas is not None:
        d = pd.to_datetime(pd.Series(list(datas)), errors="coerce")
        base = pd.DataFrame({"y": s.values, "dt": d.values}).dropna()
    else:
        base = pd.DataFrame({"y": s.values})
        base["dt"] = pd.NaT
    base = base.dropna(subset=["y"]).reset_index(drop=True)
    if len(base) < 2:
        return 0.0, "estável"

    # Suaviza com média móvel curta (reduz o efeito de picos isolados).
    jan = max(2, min(5, len(base) // 3))
    base["ym"] = base["y"].rolling(jan, min_periods=1).mean()

    # Recorta a janela recente.
    if base["dt"].notna().all():
        corte = base["dt"].max() - pd.Timedelta(days=dias)
        janela = base[base["dt"] >= corte]
        if len(janela) < 2:
            janela = base.tail(max(2, dias))
        x = (janela["dt"] - janela["dt"].iloc[0]).dt.total_seconds().to_numpy() / 86400.0
    else:
        janela = base.tail(max(2, dias))
        x = np.arange(len(janela), dtype=float)

    y = janela["ym"].to_numpy(dtype=float)
    if len(y) < 2 or float(x[-1]) <= float(x[0]):
        return 0.0, "estável"
    slope = float(np.polyfit(x, y, 1)[0])   # variação por dia

    # Limiar relativo à escala da série (evita ruído virar "tendência").
    escala = float(np.nanmean(np.abs(base["y"].to_numpy()))) or 1.0
    span = float(x[-1] - x[0]) or 1.0
    variacao_rel = (slope * span) / escala   # variação modelada na janela, relativa
    if variacao_rel > 0.01:
        return slope, "▲ subindo"
    if variacao_rel < -0.01:
        return slope, "▼ caindo"
    return slope, "estável"


def _kpi_stats_row(s, suf: str = "", datas=None) -> None:
    s2 = pd.to_numeric(pd.Series(list(s)), errors="coerce").dropna()
    if s2.empty:
        return
    atual, media, pico, melhor = s2.iloc[-1], s2.mean(), s2.max(), s2.min()
    _, tend = _tendencia_recente(s, datas=datas)
    fmt = (lambda v: f"{v:.1f}{suf}") if suf == "%" else (lambda v: f"{v:.0f}")
    c = st.columns(5)
    c[0].metric("Atual", fmt(atual))
    c[1].metric("Média 30d", fmt(media))
    c[2].metric("Pico", fmt(pico))
    c[3].metric("Melhor", fmt(melhor))
    c[4].metric(f"Tendência ({int(CFG_TEND_JANELA_DIAS)}d)", tend)


def _render_kpi_hist(sel: str) -> None:
    cfg = {
        "offline": ("offline", "Câmeras offline", "#e11d48", ""),
        "disp": ("disp", "Disponibilidade GOV", "#0f766e", "%"),
        "criticos": ("criticos", "Clientes críticos", "#f59e0b", ""),
    }
    st.markdown("---")
    if sel == "sla":
        with st.spinner("Calculando SLA dos últimos 30 dias..."):
            g = sla_historico_30d(30)
        if g is None or g.empty:
            st.info("Sem histórico suficiente para o SLA de 30 dias (é preciso ter snapshots com câmeras salvas).")
            return
        st.markdown("#### 📈 SLA da Operação — últimos 30 dias")
        fig = _area_kpi_fig(g["gravado_dt"], g["sla"], "#7C3AED", "%", "SLA")
        fig.add_hline(y=SLA_META, line_dash="dash", line_color="#0f766e", line_width=1.4,
                      annotation_text=f"Meta {SLA_META:.0f}%", annotation_position="top left",
                      annotation_font=dict(color="#0f766e", size=11))
        st.plotly_chart(fig, use_container_width=True, key="kpihist_sla")
        _kpi_stats_row(g["sla"], "%", datas=g["gravado_dt"])
    elif sel in cfg:
        col, label, cor, suf = cfg[sel]
        g = kpi_historico_30d(30)
        if g is None or g.empty:
            st.info("Sem histórico suficiente nos últimos 30 dias.")
            return
        st.markdown(f"#### 📈 {label} — últimos 30 dias")
        fig = _area_kpi_fig(g["gravado_dt"], g[col], cor, suf, label)
        st.plotly_chart(fig, use_container_width=True, key=f"kpihist_{sel}")
        _kpi_stats_row(g[col], suf, datas=g["gravado_dt"])


def _sparkline_svg(vals, cor: str, w: int = 118, h: int = 32) -> str:
    v = [float(x) for x in vals if x is not None and not pd.isna(x)]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    rng = (hi - lo) or 1.0
    n = len(v)
    pts = [f"{i/(n-1)*w:.1f},{h-3-((val-lo)/rng)*(h-6):.1f}" for i, val in enumerate(v)]
    lastx, lasty = pts[-1].split(",")
    return (f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}' style='display:block;margin-top:6px'>"
            f"<polyline fill='none' stroke='{cor}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' points='{' '.join(pts)}'/>"
            f"<circle cx='{lastx}' cy='{lasty}' r='2.8' fill='{cor}'/></svg>")


def _chip_delta(delta, good_is_up: bool, suf: str = "") -> str:
    if delta is None or pd.isna(delta):
        return ""
    lim = 0.05 if suf == "%" else 0.5
    if abs(delta) < lim:
        return ("<span style='display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;"
                "padding:3px 9px;border-radius:99px;background:#F1ECFA;color:#7c6a91;margin-top:8px'>estável</span>")
    up = delta > 0
    good = (up == good_is_up)
    cor = "#0f766e" if good else "#e11d48"
    bg = "#EAFBF6" if good else "#FDECEF"
    arrow = "▲" if up else "▼"
    txt = (f"{'+' if up else ''}{delta:.1f}{suf}") if suf == "%" else (f"{'+' if up else ''}{int(delta)}")
    return (f"<span style='display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;"
            f"padding:3px 9px;border-radius:99px;background:{bg};color:{cor};margin-top:8px'>{arrow} {txt} "
            f"<span style='color:#B8A9CC;font-weight:600'>vs ant.</span></span>")


@st.fragment
def render_resumo_operacional(dados: dict, df_origem, df_clientes_ops, total_cameras: int, total_offline: int) -> None:
    """Bloco de KPIs clicáveis (SLA ponderado + offline + disponibilidade + críticos) com histórico de 30 dias.

    Em st.fragment: clicar em "Últimos 30 dias" rerroda só este bloco (rápido), não o app inteiro.
    """
    sla = calcular_sla_operacao(df_origem, wl_validos=set(dados.keys()) if dados else None)
    total_online = int(total_cameras - total_offline)
    disp = round(total_online / total_cameras * 100, 1) if total_cameras else 0.0
    n_clientes = int(len(df_clientes_ops)) if df_clientes_ops is not None else 0
    criticos = 0
    if df_clientes_ops is not None and not df_clientes_ops.empty and "% Offline" in df_clientes_ops.columns:
        criticos = int((pd.to_numeric(df_clientes_ops["% Offline"], errors="coerce") > CFG_CRITICO_PCT).sum())
    pct_frota = round(total_offline / total_cameras * 100, 1) if total_cameras else 0.0

    # Histórico (cacheado, barato) para sparkline + variação dos 3 KPIs simples.
    hist = kpi_historico_30d(30)

    def _serie(col):
        if hist is None or hist.empty or col not in hist.columns:
            return [], None
        s = pd.to_numeric(hist[col], errors="coerce").dropna().tolist()
        delta = (s[-1] - s[-2]) if len(s) >= 2 else None
        return s, delta

    s_off, d_off = _serie("offline")
    s_disp, d_disp = _serie("disp")
    s_crit, d_crit = _serie("criticos")

    # Série do SLA (cacheada) — para chip + sparkline, no mesmo padrão dos demais.
    sla_hist = sla_historico_30d(30)
    s_sla = pd.to_numeric(sla_hist["sla"], errors="coerce").dropna().tolist() if (sla_hist is not None and not sla_hist.empty) else []
    d_sla = (s_sla[-1] - s_sla[-2]) if len(s_sla) >= 2 else None

    # (chave, rótulo, valor, cor, ícone, subtexto, série, delta, good_is_up, sufixo)
    metrics = [
        ("sla", "SLA da Operação", f"{sla['sla']:.1f}%", "#7C3AED", "🎯", None, None, None, None, ""),
        ("offline", "Câmeras offline", f"{total_offline}", "#e11d48", "📴",
         f"{pct_frota:.1f}% da frota", s_off, d_off, False, ""),
        ("disp", "Disponibilidade GOV", f"{disp:.1f}%", "#0f766e", "📶",
         f"{total_online} de {total_cameras} online", s_disp, d_disp, True, "%"),
        ("criticos", "Clientes críticos", f"{criticos}", "#f59e0b", "🔥",
         f"de {n_clientes} clientes monitorados", s_crit, d_crit, False, ""),
    ]

    cols = st.columns(4)
    for m, c in zip(metrics, cols):
        mkey, label, val, cor, icone, sub, serie, delta, good_up, suf = m
        with c:
            if mkey == "sla":
                denom = sla["lpr_total"] * sla["peso"] + sla["reg_total"]
                w_lpr = (sla["lpr_online"] * sla["peso"] / denom * 100) if denom else 0
                w_reg = (sla["reg_online"] / denom * 100) if denom else 0
                dentro = sla["sla"] >= SLA_META
                meta_cor = "#0f766e" if dentro else "#e11d48"
                chip_sla = _chip_delta(d_sla, True, "%")   # SLA subir = bom
                spark_sla = _sparkline_svg(s_sla, "#7C3AED")
                corpo = (
                    f"<div style='font-size:10px;margin-top:8px;color:{meta_cor};font-weight:700'>"
                    f"meta {SLA_META:.0f}% · {'dentro' if dentro else 'abaixo'}</div>"
                    f"<div style='display:flex;height:7px;background:#F1ECFA;border-radius:99px;margin-top:8px;overflow:hidden'>"
                    f"<div style='width:{w_lpr:.2f}%;background:linear-gradient(90deg,#7c3aed,#22d3ee)'></div>"
                    f"<div style='width:{w_reg:.2f}%;background:#c9bcea'></div></div>"
                    f"{chip_sla}"
                    f"<div style='margin-top:auto'>{spark_sla}"
                    f"<div style='font-size:9px;color:#9A92AD;margin-top:4px'>"
                    f"LPR {sla['lpr_online']}/{sla['lpr_total']} (peso {sla['peso']:.0f}×) · comuns {sla['reg_online']}/{sla['reg_total']}</div></div>"
                )
            else:
                chip = _chip_delta(delta, good_up, suf)
                spark = _sparkline_svg(serie, cor)
                corpo = (
                    f"{chip}"
                    f"<div style='margin-top:auto'>{spark}"
                    f"<div style='font-size:10px;color:#9A92AD;margin-top:4px'>{sub}</div></div>"
                )
            st.markdown(
                f"<div style=\"background:#fff;border:1px solid #ECE8F5;border-top:3px solid {cor};"
                f"border-radius:16px;padding:14px 16px;box-shadow:0 6px 20px rgba(23,17,38,.05);"
                f"height:210px;display:flex;flex-direction:column;overflow:hidden\">"
                f"<div style=\"display:flex;align-items:center;justify-content:space-between\">"
                f"<span style=\"font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#9A92AD\">{label}</span>"
                f"<span style=\"font-size:15px;opacity:.9\">{icone}</span></div>"
                f"<div style=\"font-family:'DM Mono',monospace;font-size:30px;font-weight:600;color:{cor};letter-spacing:-1px;margin-top:6px\">{val}</div>"
                f"{corpo}</div>",
                unsafe_allow_html=True,
            )
            if st.button("📈 Últimos 30 dias", key=f"kpi30_{mkey}", use_container_width=True):
                atual = st.session_state.get("kpi_hist_sel")
                st.session_state["kpi_hist_sel"] = None if atual == mkey else mkey

    sel = st.session_state.get("kpi_hist_sel")
    if sel:
        _render_kpi_hist(sel)


def render_aba_configuracao() -> None:
    st.markdown("### ⚙️ Configuração")
    st.caption("Parâmetros do painel. As alterações são salvas em arquivo e aplicadas a todos os cálculos (SLA, faixas de status, score de criticidade).")

    cfg = _config_atual()

    st.markdown("#### 🎯 SLA da Operação")
    c1, c2, c3 = st.columns(3)
    with c1:
        v_meta = st.number_input("Meta de SLA (%)", min_value=50.0, max_value=100.0,
                                 value=float(cfg["SLA_META"]), step=0.5, key="cfg_sla_meta")
    with c2:
        v_peso = st.number_input("Peso da câmera LPR (×)", min_value=1.0, max_value=20.0,
                                 value=float(cfg["PESO_LPR"]), step=0.5, key="cfg_peso_lpr",
                                 help="Quanto uma LPR pesa em relação a uma câmera comum no SLA.")
    with c3:
        v_kw = st.text_input("Palavra-chave da LPR (no nome)", value=str(cfg["LPR_KEYWORD"]), key="cfg_lpr_kw")

    st.markdown("#### 🚦 Faixas de status (% offline)")
    c4, c5 = st.columns(2)
    with c4:
        v_at = st.number_input("Limite Saudável → Atenção (%)", min_value=0.0, max_value=100.0,
                               value=float(cfg["CFG_ATENCAO_PCT"]), step=0.5, key="cfg_atencao")
    with c5:
        v_cr = st.number_input("Limite Atenção → Crítico (%)", min_value=0.0, max_value=100.0,
                               value=float(cfg["CFG_CRITICO_PCT"]), step=0.5, key="cfg_critico")
    if v_cr <= v_at:
        st.warning("O limite de Crítico deve ser maior que o de Atenção.")

    st.markdown("#### ⏱️ Operacional")
    o1, o2 = st.columns(2)
    with o1:
        v_horas = st.number_input("Horas para considerar offline 'há muito tempo'", min_value=1, max_value=240,
                                  value=int(cfg["CFG_ACIMA_HORAS"]), step=1, key="cfg_horas",
                                  help="Usado na contagem 'Acima 24h' e no score de criticidade.")
    with o2:
        v_tend = st.number_input("Janela da Tendência dos KPIs (dias)", min_value=2, max_value=30,
                                 value=int(cfg["CFG_TEND_JANELA_DIAS"]), step=1, key="cfg_tend",
                                 help="A Tendência (▲/▼) é medida só nos últimos N dias, sobre a média móvel — reflete o movimento recente, não o mês inteiro.")

    with st.expander("🧮 Pesos do score de criticidade (avançado)"):
        st.caption("Score = offline×A + %offline×B + horas_offline/C + acima_limite×D + dias_críticos×E")
        w1, w2, w3, w4, w5 = st.columns(5)
        v_wo = w1.number_input("A · nº offline", 0.0, 50.0, float(cfg["CFG_W_OFFLINE"]), 0.5, key="cfg_wo")
        v_wp = w2.number_input("B · % offline", 0.0, 50.0, float(cfg["CFG_W_PCT"]), 0.5, key="cfg_wp")
        v_wh = w3.number_input("C · divisor horas", 1.0, 100.0, float(cfg["CFG_W_HORAS_DIV"]), 1.0, key="cfg_wh")
        v_wa = w4.number_input("D · acima do limite", 0.0, 50.0, float(cfg["CFG_W_ACIMA"]), 0.5, key="cfg_wa")
        v_wd = w5.number_input("E · dias críticos", 0.0, 50.0, float(cfg["CFG_W_DIASCRIT"]), 0.5, key="cfg_wd")

    nova = {
        "SLA_META": v_meta, "PESO_LPR": v_peso, "LPR_KEYWORD": (v_kw or "LPR").strip() or "LPR",
        "CFG_ATENCAO_PCT": v_at, "CFG_CRITICO_PCT": v_cr, "CFG_ACIMA_HORAS": int(v_horas),
        "CFG_TEND_JANELA_DIAS": int(v_tend),
        "CFG_W_OFFLINE": v_wo, "CFG_W_PCT": v_wp, "CFG_W_HORAS_DIV": v_wh,
        "CFG_W_ACIMA": v_wa, "CFG_W_DIASCRIT": v_wd,
    }

    st.markdown("")
    b1, b2 = st.columns([1, 1])
    with b1:
        if st.button("💾 Salvar configurações", type="primary", use_container_width=True, key="cfg_salvar"):
            ok = salvar_config(nova)
            st.session_state["config"] = nova
            aplicar_config(nova)
            st.cache_data.clear()
            if ok:
                st.success("Configurações salvas e aplicadas.")
            else:
                st.warning("Aplicado nesta sessão, mas não foi possível gravar o arquivo (ambiente somente leitura). Os valores voltam ao padrão ao reiniciar.")
            st.rerun()
    with b2:
        if st.button("↩️ Restaurar padrões", use_container_width=True, key="cfg_reset"):
            salvar_config(dict(CONFIG_DEFAULTS))
            st.session_state["config"] = dict(CONFIG_DEFAULTS)
            aplicar_config(dict(CONFIG_DEFAULTS))
            st.cache_data.clear()
            st.rerun()

    st.caption(f"Arquivo de configuração: `{CONFIG_PATH}`")


def main():
    init_db()

    # Aplica a configuração persistida (uma vez por sessão) aos parâmetros do painel.
    if "config" not in st.session_state:
        st.session_state["config"] = carregar_config()
    aplicar_config(st.session_state["config"])

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
    abas_principais = ["Auditoria", "Clientes"]
    abas_principais += ["Evidências", "Atualizar Base", "Configuração"]
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
                # Resumo operacional: KPIs clicáveis (SLA ponderado + histórico 30 dias).
                render_resumo_operacional(dados, df_origem, df_clientes_ops, total_cameras, total_offline)
                st.markdown("")
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

                if st.button("← Voltar ao painel", key="btn_voltar_painel_detalhe_cliente_v1"):
                    del st.session_state["detalhe"]; st.rerun()

        with clientes_subtabs[1]:
            render_relatorio_por_franquia(df_clientes_ops, dados, key_prefix="clientes_relatorio_franquia")

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
                cores_d = ["#f43f5e" if d > 0 else ("#14b8a6" if d < 0 else "#cbb9e6") for d in df_delta["delta_off"]]
                _dmax = float(df_delta["delta_off"].abs().max()) or 1.0
                fig_d = go.Figure(go.Bar(
                    y=df_delta["cliente"], x=df_delta["delta_off"], orientation="h",
                    marker=dict(color=cores_d, line=dict(width=0)),
                    text=[f"{'+' if d > 0 else ''}{int(d)}" for d in df_delta["delta_off"]],
                    textposition="outside",
                    textfont=dict(color="#4A3D5C", size=11, family="DM Mono"),
                    cliponaxis=False,
                    width=0.62,
                    hovertemplate="<b>%{y}</b><br>Δ %{x:+.0f} câmeras<extra></extra>",
                ))
                # Cantos arredondados (seguro em versões antigas do Plotly).
                try:
                    fig_d.update_traces(marker_cornerradius=7)
                except Exception:
                    pass
                fig_d.add_vline(x=0, line_color="#D9CDEF", line_width=1.5)
                fig_d.update_layout(
                    **{k: v for k, v in pdefaults().items() if k not in ["paper_bgcolor", "plot_bgcolor"]},
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    height=max(440, len(df_delta) * 34),
                    showlegend=False, bargap=0.34,
                    xaxis=dict(
                        showgrid=False, zeroline=False, showline=False,
                        tickfont=dict(color="#B8A9CC", size=10),
                        range=[-_dmax * 1.18, _dmax * 1.18],
                    ),
                    yaxis=dict(
                        tickfont=dict(color="#4A3D5C", size=11, family="DM Sans"),
                        showgrid=False,
                    ),
                    margin=dict(l=10, r=60, t=10, b=20),
                    uniformtext=dict(mode="show", minsize=9),
                )
                altura_d = int(max(420, len(df_delta) * 32))
                st.plotly_chart(
                    fig_d, use_container_width=True, key="hist_delta_off_cliente",
                    config={
                        "displaylogo": False,
                        "toImageButtonOptions": {
                            "format": "png",
                            "filename": "variacao_liquida_offline",
                            "scale": 3,
                            "width": 1400,
                            "height": altura_d,
                        },
                    },
                )

                # Exportação em alta resolução.
                barras_exp = tuple((str(c), float(d)) for c, d in zip(df_delta["cliente"], df_delta["delta_off"]))
                png_hd = _png_variacao_liquida(barras_exp)
                if png_hd:
                    st.download_button(
                        "⬇ Baixar gráfico em alta resolução (PNG)",
                        data=png_hd,
                        file_name="variacao_liquida_offline.png",
                        mime="image/png",
                        use_container_width=True,
                        key="dl_delta_off_png",
                    )
                else:
                    st.caption(
                        "Para exportar em alta qualidade, passe o mouse sobre o gráfico e clique no ícone 📷 "
                        "(canto superior direito) — agora ele salva em resolução 3×."
                    )

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

    with tabs["Configuração"]:
        render_aba_configuracao()

if __name__ == "__main__":
    main()
