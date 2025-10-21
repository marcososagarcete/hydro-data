"""
Séries históricas mensais por produto (Importações PR)

Produtos: Ureia; Metano/Metanol; Amônia/Amoníaco; Outra Ureia (incl. sol. aquosa)
Período: jan/2013 a set/2025

Gráficos por produto selecionado:
- Quilograma Líquido (kg) por mês
- Valor US$ CIF por mês
- Proporção kg / US$ FOB por mês
- Proporção kg / US$ CIF por mês

Também exibe os últimos valores das proporções (kg/US$) e em toneladas/US$.
"""
from pathlib import Path
from typing import Dict, List
import pandas as pd
import numpy as np
from dash import html, dcc, Input, Output, callback
import dash
import plotly.express as px
import plotly.graph_objects as go


# Registra a página
dash.register_page(__name__, path="/allimports", name="Séries Históricas (Import.)")


# -------------------------
# Carga de dados
# -------------------------
DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "allimports.csv"

df = pd.read_csv(
    DATA_PATH,
    sep=";",
    encoding="utf-8-sig",
    engine="python",
    dtype=str,
)

# Normalização numérica
NUM_COLS = [
    "Valor US$ FOB",
    "US$ Frete",
    "US$ Seguro",
    "Valor US$ CIF",
    "Quilograma Líquido",
    "Quantidade Estatística",
]
for c in NUM_COLS:
    if c in df.columns:
        s = df[c].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df[c] = pd.to_numeric(s, errors="coerce")

# Datas
df["Ano"] = pd.to_numeric(df.get("Ano"), errors="coerce").astype("Int64")
mes_num = (
    df.get("Mês", "")
    .astype(str)
    .str.extract(r"^(\d{2})")[0]
    .astype(float)
)
mes_num = mes_num.fillna(1).astype(int)
df["date"] = pd.to_datetime(
    {
        "year": df["Ano"].astype("float").astype("Int64"),
        "month": mes_num,
        "day": 1,
    },
    errors="coerce",
)

# Intervalo solicitado: jan/2013 a set/2025
mask_periodo = (df["date"] >= pd.Timestamp(2013, 1, 1)) & (df["date"] <= pd.Timestamp(2025, 9, 30))
df = df.loc[mask_periodo].copy()


# -------------------------
# Mapeamento de produtos (por NCM)
# -------------------------
# Observações do dataset (exemplos encontrados):
# - Ureia (N>45%): Código NCM 31021010
# - Outra ureia, mesmo em solução aquosa: Código NCM 31021090
# - Metanol (álcool metílico): Código NCM 29051100
# - Amoníaco: já identificado "Amoníaco em solução aquosa (amônia)": 28142000
#   (incluímos também 28141000 se houver dados no período)

PRODUCTS: Dict[str, List[str]] = {
    "Ureia": ["31021010"],
    "Metanol": ["29051100"],  # Metanol (álcool metílico)
    "Ammonia": ["28142000", "28141000"],
    "Outra Ureia (incl. sol. aquosa)": ["31021090"],
}


# -------------------------
# Layout
# -------------------------
layout = html.Div(
    [
        html.H1("Séries históricas — Importações por produto (PR)"),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Produto"),
                        dcc.Dropdown(
                            id="ai_produto",
                            options=[{"label": k, "value": k} for k in PRODUCTS.keys()],
                            value="Ureia",
                            clearable=False,
                        ),
                    ],
                    style={"width": "320px", "marginRight": "24px"},
                ),
            ],
            style={"display": "flex", "flexWrap": "wrap", "alignItems": "center"},
        ),
        html.Div(id="ai_resumo", style={"marginTop": "8px", "color": "#444"}),
        html.Hr(),
        html.Div(
            [
                html.Div([dcc.Graph(id="ai_fig_kg")], style={"flex": 1, "minWidth": "320px"}),
                html.Div([dcc.Graph(id="ai_fig_cif")], style={"flex": 1, "minWidth": "320px"}),
            ],
            style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
        ),
        html.Div(
            [
                html.Div([dcc.Graph(id="ai_fig_ratio_fob")], style={"flex": 1, "minWidth": "320px"}),
                html.Div([dcc.Graph(id="ai_fig_ratio_cif")], style={"flex": 1, "minWidth": "320px"}),
            ],
            style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginTop": "8px"},
        ),
        html.Div(
            "Fonte: COMEX (MDIC/SECEX). Valores em US$ e kg (Quilograma Líquido).",
            style={"marginTop": "12px", "fontSize": "12px", "color": "#555"},
        ),
    ],
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "12px"},
)


def _build_monthly(dfp: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "date",
        "Quilograma Líquido",
        "Valor US$ FOB",
        "Valor US$ CIF",
    ]
    for c in cols:
        if c not in dfp.columns:
            dfp[c] = np.nan
    g = (
        dfp.groupby("date", as_index=False, sort=True)[
            ["Quilograma Líquido", "Valor US$ FOB", "Valor US$ CIF"]
        ]
        .sum(min_count=1)
        .sort_values("date")
    )
    # Proporções (kg / US$) e (US$ / kg) — evitar divisão por zero
    g["kg_per_usd_fob"] = g["Quilograma Líquido"] / g["Valor US$ FOB"].replace(0, np.nan)
    g["kg_per_usd_cif"] = g["Quilograma Líquido"] / g["Valor US$ CIF"].replace(0, np.nan)
    g["usd_per_kg_fob"] = g["Valor US$ FOB"] / g["Quilograma Líquido"].replace(0, np.nan)
    g["usd_per_kg_cif"] = g["Valor US$ CIF"] / g["Quilograma Líquido"].replace(0, np.nan)
    return g


def _style_time_axis(fig: go.Figure) -> go.Figure:
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))
    # Eixo X com anos (não mostrar meses)
    fig.update_xaxes(dtick="M12", tickformat="%Y")
    return fig


@callback(
    Output("ai_fig_kg", "figure"),
    Output("ai_fig_cif", "figure"),
    Output("ai_fig_ratio_fob", "figure"),
    Output("ai_fig_ratio_cif", "figure"),
    Output("ai_resumo", "children"),
    Input("ai_produto", "value"),
)
def atualizar_series(produto):
    # Filtro por NCM(s)
    cods = PRODUCTS.get(produto, [])
    dsel = df.loc[df["Código NCM"].astype(str).isin(cods)].copy()

    if dsel.empty:
        vazio = go.Figure()
        vazio.update_layout(title=f"Sem dados para '{produto}' no período")
        resumo = "Sem dados."
        return (_style_time_axis(vazio),) * 4 + (resumo,)

    monthly = _build_monthly(dsel)

    # Figuras
    fig_kg = px.line(
        monthly,
        x="date",
        y="Quilograma Líquido",
        title=f"{produto}: Quilograma Líquido por mês",
        markers=True,
    )
    fig_kg.update_yaxes(title="kg", tickformat=",")
    fig_kg = _style_time_axis(fig_kg)

    fig_cif = px.line(
        monthly,
        x="date",
        y="Valor US$ CIF",
        title=f"{produto}: Valor US$ CIF por mês",
        markers=True,
    )
    fig_cif.update_yaxes(title="US$", tickformat=",")
    fig_cif = _style_time_axis(fig_cif)

    fig_ratio_fob = px.line(
        monthly,
        x="date",
        y="usd_per_kg_fob",
        title=f"{produto}: US$ por kg (FOB)",
        markers=True,
    )
    fig_ratio_fob.update_yaxes(title="US$/kg")
    fig_ratio_fob = _style_time_axis(fig_ratio_fob)

    fig_ratio_cif = px.line(
        monthly,
        x="date",
        y="usd_per_kg_cif",
        title=f"{produto}: US$ por kg (CIF)",
        markers=True,
    )
    fig_ratio_cif.update_yaxes(title="US$/kg")
    fig_ratio_cif = _style_time_axis(fig_ratio_cif)

    # Resumo: último valor disponível
    last_row = monthly.dropna(subset=["kg_per_usd_fob", "kg_per_usd_cif", "usd_per_kg_fob", "usd_per_kg_cif"]).tail(1)
    if last_row.empty:
        # Usa a última data mesmo que uma das proporções seja NaN
        last_row = monthly.tail(1)
    last_dt = last_row["date"].iloc[0]
    last_fob = last_row["kg_per_usd_fob"].iloc[0]
    last_cif = last_row["kg_per_usd_cif"].iloc[0]
    last_price_ton_fob = last_row["usd_per_kg_fob"].iloc[0] * 1000 if not pd.isna(last_row["usd_per_kg_fob"].iloc[0]) else np.nan
    last_price_ton_cif = last_row["usd_per_kg_cif"].iloc[0] * 1000 if not pd.isna(last_row["usd_per_kg_cif"].iloc[0]) else np.nan

    def _fmt_ratio(v):
        if pd.isna(v) or np.isinf(v):
            return "-"
        return f"{v:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_money(v):
        if pd.isna(v) or np.isinf(v):
            return "-"
        # Formata em US$ com separador de milhar BR
        return "US$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    resumo = html.Div(
        [
            html.Span(
                f"Último mês: {last_dt.strftime('%b/%Y')} — kg/US$ FOB: {_fmt_ratio(last_fob)}; preço por tonelada (FOB): {_fmt_money(last_price_ton_fob)}; ",
            ),
            html.Span(
                f"kg/US$ CIF: {_fmt_ratio(last_cif)}; preço por tonelada (CIF): {_fmt_money(last_price_ton_cif)}"
            ),
        ]
    )

    return fig_kg, fig_cif, fig_ratio_fob, fig_ratio_cif, resumo
