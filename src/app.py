import os
from pathlib import Path
from dash import Dash, html, dcc
import dash


# Create the Dash app with built-in pages support
ASSETS_PATH = str(Path(__file__).resolve().parent.parent / "assets")

app = Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title="Importa PR",
    assets_folder=ASSETS_PATH,
)

# Expose Flask server for deployment (e.g., gunicorn)
server = app.server


def _navbar():
    links = []
    for page in dash.page_registry.values():
        links.append(
            html.Li(
                dcc.Link(page.get("name", page["module"]), href=page["path"]),
                style={"display": "inline", "marginRight": "16px"},
            )
        )
    return html.Nav(
        [
            html.Ul(links, style={"listStyle": "none", "padding": 0, "margin": 0}),
            html.Hr(),
        ]
    )


def _layout():
    return html.Div(
        [
            html.H1("DataFer • PR Dashboard", style={"marginBottom": "4px"}),
            html.Div(
                "Navegue pelas páginas abaixo.",
                style={"color": "#555", "marginBottom": "12px"},
            ),
            _navbar(),
            dash.page_container,
        ],
        style={"maxWidth": "1200px", "margin": "0 auto", "padding": "12px"},
    )

app.layout = _layout


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)
