"""Central de Ações: CRUD (Supabase), helpers e renderização das abas.

Extraído de monitoramento_V3.py (Fase 4, passo 4b). Feature autocontida:
não usa os CFG globais dinâmicos, então pôde sair sem refatorar a config.
Depende de src.utils, src.ui.helpers e src.db.supabase.
"""

import re
import uuid
import requests

import pandas as pd
import streamlit as st

from src.utils import agora_sao_paulo, agora_sao_paulo_str, normalizar_coluna
from src.ui.helpers import escape_html, render_dataframe
from src.db.supabase import (
    supabase_configurado,
    supabase_headers,
    supabase_table_url,
    erro_supabase_amigavel,
    sql_criacao_supabase,
)


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

