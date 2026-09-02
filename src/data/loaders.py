"""Leitura e processamento de dados (CSV GOV, xlsx individuais, clientes, saúde).

Extraído de monitoramento_V3.py (Fase 3, extração 2).
Depende de src.constants, src.utils e src.db.supabase (módulos já extraídos).
O bloco de geocode/mapa continua no arquivo principal (extração futura).
"""

import os
import re
import glob
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from src.constants import (
    COL_WL, COL_EMPRESA, COL_ID_CAM, COL_NOME_CAM, COL_STATUS,
    COL_ULT_ATU, COL_OBS, COL_DATA_CAD, COL_PLANO, COL_DATA_INAT,
    PASTA, XLSX_CLIENTES, CSV_GOV, IMPORTACAO_INDIVIDUAL_DIR,
    DATA_PARSE_VERSION, caminho_xlsx_clientes,
)
from src.utils import (
    agora_sao_paulo,
    encontrar_coluna_por_chaves,
    normalizar_coluna,
    parse_ultima_atualizacao,
)
from src.db.supabase import (
    supabase_configurado,
    carregar_cameras_supabase,
    converter_supabase_para_df_gov,
    carregar_ultima_atualizacao_base,
)


# ── Trecho A: clientes + leitura CSV/xlsx + processamento ──
@st.cache_data
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

@st.cache_data
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


@st.cache_data
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

# parse_ultima_atualizacao / formatar_ultima_atualizacao movidas para src/utils.py

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


# ── Trecho B: carregar_dados + calculo de saude ──
@st.cache_data
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

@st.cache_data
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


