# -*- coding: utf-8 -*-
"""
Dashboard (Dash + Plotly) — Importações por Município (PR)

Este app usa o conjunto de dados completo (sem filtrar por SH4) e permite:
 - Visualizar Top N municípios por US$ FOB (por ano ou em todos os anos);
 - Excluir opcionalmente o município de Paranaguá do resultado;
 - Ver a tabela dos dados exibidos no gráfico.

Entrada padrão: DATA_DIR/importmunicipio.csv (padrão: ../data/importmunicipio.csv)
Fallback local: cpimportmun.csv (se o arquivo padrão não existir)
Colunas: "Ano";"Mês";"UF do Município";"Município";"Código SH4";"Descrição SH4";"Valor US$ FOB"

Requisitos: dash, pandas, numpy, plotly
    pip install dash pandas numpy plotly
"""
import os
from pathlib import Path
import re
import numpy as np
import pandas as pd
from dash import Dash, html, dcc, dash_table, Input, Output
import plotly.express as px

# -------------------------
# Caminhos e utilitários
# -------------------------
DATA_DIR = Path(
    os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data")
).resolve()
# Caminho padrão esperado pelo projeto
CSV_PATH = DATA_DIR / "importmunicipio.csv"
# Fallback local (conforme informado pelo usuário): arquivo na mesma pasta
FALLBACK_LOCAL = Path(__file__).resolve().parent / "cpimportmun.csv"

if CSV_PATH.exists():
    CSV_TO_USE = CSV_PATH
elif FALLBACK_LOCAL.exists():
    CSV_TO_USE = FALLBACK_LOCAL
else:
    raise FileNotFoundError(
        "Arquivo de dados não encontrado. Verifique estes caminhos:"\
        f"\n - {CSV_PATH}\n - {FALLBACK_LOCAL}\n"\
        "Dica: defina a variável de ambiente DATA_DIR ou coloque o CSV no caminho indicado."
    )

def _to_float(x):
    """Converte strings tipo '1.234.567,89' ou '1234567.89' para float."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if re.search(r",\d{1,2}$", s) and s.count(",") == 1:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan

def _fmt_usd_br(v):
    """Formata número como US$ com separador de milhar em estilo BR."""
    try:
        n = int(round(float(v)))
    except Exception:
        return "-"
    return "US$ " + f"{n:,}".replace(",", ".")

# -------------------------
# Carga & limpeza
# -------------------------
df = pd.read_csv(
    CSV_TO_USE,  # usa o arquivo padrão ou o fallback local
    sep=";",
    encoding="utf-8-sig",
    quotechar='"',
    engine="python",
)

df["Valor US$ FOB"] = df["Valor US$ FOB"].apply(_to_float)
df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")
# Normaliza o nome do município: remove sufixo "- PR" e espaços extras
df["Município"] = (
    df["Município"]
    .astype(str)
    .str.strip()
    .str.replace(r"\s*-\s*PR$", "", regex=True)
)

# A pedido do usuário, NÃO filtramos por SH4: usamos todos os registros
df_base = df.copy()

# Anos disponíveis no conjunto completo
anos = sorted([int(a) for a in df_base["Ano"].dropna().unique()])

# -------------------------
# App
# -------------------------
app = Dash(__name__)
app.title = "Importa"

app.layout = html.Div(
    [
        html.H1("Importações Fertilizante — Municípios do Paraná"),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Modo de exibição"),
                        dcc.RadioItems(
                            id="modo",
                            options=[
                                {"label": "Por ano", "value": "ano"},
                                {"label": "Todos os anos", "value": "todos"},
                            ],
                            value="ano",
                            inline=True,
                        ),
                    ],
                    style={"marginRight": "24px"},
                ),
                html.Div(
                    [
                        html.Label("Ano"),
                        dcc.Dropdown(
                            id="ano",
                            options=[{"label": str(a), "value": int(a)} for a in anos],
                            value=anos[-1] if anos else None,
                            clearable=False,
                            placeholder="Selecione o ano",
                        ),
                    ],
                    style={"width": "200px", "marginRight": "24px"},
                ),
                html.Div(
                    [
                        html.Label("Top N municípios"),
                        dcc.Slider(
                            id="top_n",
                            min=5,
                            max=30,
                            step=1,
                            value=15,
                            marks={5: "5", 10: "10", 15: "15", 20: "20", 30: "30"},
                            tooltip={"placement": "bottom"},
                        ),
                    ],
                    style={"width": "300px", "marginRight": "24px"},
                ),
                html.Div(
                    [
                        html.Label("Excluir cidade"),
                        dcc.Checklist(
                            id="ignorar_paranagua",
                            options=[{"label": "Ignorar Paranaguá", "value": "ignore_paranagua"}],
                            value=[],
                            inline=True,
                        ),
                    ],
                ),
            ],
            style={"display": "flex", "flexWrap": "wrap", "alignItems": "center", "gap": "8px"},
        ),
        html.Hr(),
        dcc.Graph(id="fig_main"),
        html.H2("Tabela (dados do gráfico)"),
        dash_table.DataTable(
            id="tbl",
            page_size=15,
            sort_action="native",
            filter_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"fontFamily": "sans-serif", "fontSize": "14px", "padding": "6px"},
            style_header={"fontWeight": "bold"},
        ),
        html.Div(
            "Fonte: COMEX (MDIC/SECEX). Valores em US$ FOB.",
            style={"marginTop": "12px", "fontSize": "12px", "color": "#555"},
        ),
    ],
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "12px"},
)

# -------------------------
# Callbacks
# -------------------------
@app.callback(
    Output("fig_main", "figure"),
    Output("tbl", "columns"),
    Output("tbl", "data"),
    Input("modo", "value"),
    Input("ano", "value"),
    Input("top_n", "value"),
    Input("ignorar_paranagua", "value"),
)
def atualizar(modo, ano, top_n, ignorar_paranagua):
    # Base: todos os registros (sem filtro por SH4)
    dbase = df_base.copy()

    # Opcional: excluir Paranaguá (considera com e sem acento)
    if "ignore_paranagua" in (ignorar_paranagua or []):
        dbase = dbase.loc[
            ~dbase["Município"].str.lower().isin(["paranaguá", "paranagua"])
        ].copy()

    # Agregações conforme modo
    if modo == "ano":
        if ano is None or pd.isna(ano):
            ano_sel = anos[-1] if anos else None
        else:
            ano_sel = int(ano)
        dados = (
            dbase.loc[dbase["Ano"] == ano_sel]
            .groupby("Município", as_index=False, sort=False)["Valor US$ FOB"]
            .sum()
        )
        titulo = f"Top municípios por importação — {ano_sel}"
    else:
        dados = (
            dbase.groupby("Município", as_index=False, sort=False)["Valor US$ FOB"].sum()
        )
        titulo = "Top municípios por importação — todos os anos"

    # Ordenação + Top N (mantém os N maiores valores)
    dados = dados.sort_values("Valor US$ FOB", ascending=False).head(int(top_n)).copy()

    # Participação dentro do Top N
    total = float(dados["Valor US$ FOB"].sum()) or 1.0
    dados["Participação"] = dados["Valor US$ FOB"] / total

    # Importante: gerar um dataframe já na mesma ordem usada pelo gráfico.
    # Isso evita desalinhamento entre rótulos/valores quando ordenamos para exibição.
    plot_df = dados.sort_values("Valor US$ FOB", ascending=True).copy()

    fig = px.bar(
        plot_df,
        x="Valor US$ FOB",
        y="Município",
        orientation="h",
        title=titulo,
        labels={"Valor US$ FOB": "US$ FOB", "Município": "Município"},
    )
    fig.update_traces(
        hovertemplate=(
            "Município: %{y}<br>"
            "US$ FOB: %{x:.0f}<br>"
            "Participação (Top N): %{customdata:.1%}<extra></extra>"
        ),
        customdata=plot_df["Participação"].values,
        text=[_fmt_usd_br(v) for v in plot_df["Valor US$ FOB"].values],
        textposition="outside",
        cliponaxis=False,
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(title="US$ FOB", tickformat=","),
        yaxis=dict(title=None),
    )

    cols = [
        {"name": "Município", "id": "Município"},
        {"name": "US$ FOB", "id": "Valor US$ FOB", "type": "numeric"},
        {"name": "Participação (Top N)", "id": "Participação", "type": "numeric"},
    ]
    # Tabela: mantém Top N em ordem decrescente por valor
    dados_tbl = dados.sort_values("Valor US$ FOB", ascending=False).copy()
    return fig, cols, dados_tbl.to_dict("records")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)
