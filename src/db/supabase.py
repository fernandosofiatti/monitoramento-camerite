"""Camada de acesso ao Supabase / BD online.

Extraído de monitoramento_V3.py (Fase 3, extração 1).
Depende apenas de src.constants e src.utils (módulos-folha), evitando ciclos.
"""

import os
import re
import math
import requests
from datetime import datetime

import pandas as pd
import streamlit as st

from src.constants import (
    COL_WL, COL_EMPRESA, COL_ID_CAM, COL_NOME_CAM, COL_STATUS,
    COL_ULT_ATU, COL_OBS, COL_DATA_CAD, COL_PLANO, COL_DATA_INAT,
    SUPABASE_TABLE, SUPABASE_PAGE_SIZE, CSV_GOV,
)
from src.utils import (
    agora_sao_paulo_str,
    encontrar_coluna_por_chaves,
    parse_ultima_atualizacao,
)


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


@st.cache_data
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


@st.cache_data
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
