"""Helpers de interface compartilhados entre as abas.

Extraído de monitoramento_V3.py (Fase 4, passo 4a). Módulo-folha de UI:
depende apenas de stdlib, pandas e streamlit — sem estado do app nem CFG globais.
"""

import html
import uuid

import pandas as pd
import streamlit as st


def escape_html(valor) -> str:
    return html.escape(str(valor or ""), quote=True)


def _rgba(hexcor: str, a: float) -> str:
    h = hexcor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


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
