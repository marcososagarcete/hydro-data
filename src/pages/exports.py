"""Página em branco para futuras exportações."""
from dash import html
import dash


dash.register_page(__name__, path="/exports", name="Exportações (breve)")


layout = html.Div(
    [
        html.H1("Exportações — Em breve"),
        html.P("Esta página será desenvolvida futuramente."),
    ]
)

