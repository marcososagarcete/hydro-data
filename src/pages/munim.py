"""
Página: Importações por Município (PR)

Replica a funcionalidade do script original `src/munimp.py` como
uma página do Dash Pages.
"""
import os
from pathlib import Path
import re
import numpy as np
import pandas as pd
from dash import html, dcc, dash_table, Input, Output, callback
import dash
import plotly.express as px


# Registra a página (página inicial)
dash.register_page(__name__, path="/", name="Importações Municípios PR")


# -------------------------
# Caminhos e utilitários
# -------------------------
DATA_DIR = Path(
    os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data")
).resolve()
CSV_PATH = DATA_DIR / "importmunicipio.csv"
FALLBACK_LOCAL = Path(__file__).resolve().parent / "cpimportmun.csv"

if CSV_PATH.exists():
    CSV_TO_USE = CSV_PATH
elif FALLBACK_LOCAL.exists():
    CSV_TO_USE = FALLBACK_LOCAL
else:
    raise FileNotFoundError(
        "Arquivo de dados não encontrado. Verifique estes caminhos:"
        f"\n - {CSV_PATH}\n - {FALLBACK_LOCAL}\n"
        "Dica: defina a variável de ambiente DATA_DIR ou coloque o CSV no caminho indicado."
    )


def _to_float(x):
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
    try:
        n = int(round(float(v)))
    except Exception:
        return "-"
    return "US$ " + f"{n:,}".replace(",", ".")


# -------------------------
# Carga & limpeza
# -------------------------
df = pd.read_csv(
    CSV_TO_USE,
    sep=";",
    encoding="utf-8-sig",
    quotechar='"',
    engine="python",
)

df["Valor US$ FOB"] = df["Valor US$ FOB"].apply(_to_float)
df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").astype("Int64")
df["Município"] = (
    df["Município"]
    .astype(str)
    .str.strip()
    .str.replace(r"\s*-\s*PR$", "", regex=True)
)

df_base = df.copy()
anos = sorted([int(a) for a in df_base["Ano"].dropna().unique()])


# -------------------------
# Layout
# -------------------------
layout = html.Div(
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
                            options=[{"label": "Filtrar Paranaguá", "value": "ignore_paranagua"}],
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
    ]
)


# -------------------------
# Callbacks
# -------------------------
@callback(
    Output("fig_main", "figure"),
    Output("tbl", "columns"),
    Output("tbl", "data"),
    Input("modo", "value"),
    Input("ano", "value"),
    Input("top_n", "value"),
    Input("ignorar_paranagua", "value"),
)
def atualizar(modo, ano, top_n, ignorar_paranagua):
    dbase = df_base.copy()

    if "ignore_paranagua" in (ignorar_paranagua or []):
        dbase = dbase.loc[
            ~dbase["Município"].str.lower().isin(["paranaguá", "paranagua"])
        ].copy()

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

    dados = dados.sort_values("Valor US$ FOB", ascending=False).head(int(top_n)).copy()

    total = float(dados["Valor US$ FOB"].sum()) or 1.0
    dados["Participação"] = dados["Valor US$ FOB"] / total

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
    dados_tbl = dados.sort_values("Valor US$ FOB", ascending=False).copy()
    return fig, cols, dados_tbl.to_dict("records")

