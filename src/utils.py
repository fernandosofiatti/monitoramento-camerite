"""Helpers puros reutilizáveis (datas, normalização de colunas, parsing de datas BR).

Extraído de monitoramento_V3.py (Fase 3). Módulo-folha: depende apenas de
stdlib e pandas — não importa nada de dentro do projeto, para evitar ciclos.
"""

import re
import unicodedata
from datetime import datetime, timedelta

import pandas as pd


def agora_sao_paulo() -> datetime:
    """Retorna horário local de São Paulo, mesmo quando o app roda em servidor UTC."""
    return datetime.utcnow() - timedelta(hours=3)


def agora_sao_paulo_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return agora_sao_paulo().strftime(fmt)


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
