"""Small, dependency-free presentation helpers."""
from urllib.parse import quote
from dash import html

PATHS = {
    "overview": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "trends": '<path d="M3 3v18h18M6 15l5-5 4 3 6-8"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M8 15h2M14 15h2"/>',
    "goals": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "records": '<path d="M8 3h8v5a4 4 0 0 1-8 0V3ZM8 5H4v2a4 4 0 0 0 4 4m8-6h4v2a4 4 0 0 1-4 4M12 12v6M8 21h8M9 18h6"/>',
    "log": '<rect x="5" y="3" width="15" height="18" rx="2"/><path d="M9 8h7M9 12h7M9 16h4M3 6h4M3 11h4M3 16h4"/>',
    "arrow": '<path d="M7 17 17 7M7 7h10v10"/>',
    "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5"/>',
    "moon": '<path d="M21 13A9 9 0 0 1 11 3a9 9 0 1 0 10 10Z"/>',
    "distance": '<path d="M4 18c0-6 16-6 16-12"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="6" r="2"/>',
    "mountain": '<path d="m3 20 7-13 4 6 3-4 5 11H3ZM7 12l3 2 2-3"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "activity": '<path d="M2 12h5l3-8 4 16 3-8h5"/>',
    "fire": '<path d="M12 3c2 5 6 6 6 11a6 6 0 0 1-12 0c0-3 2-5 3-6 0 3 2 4 3 4 2-3 1-6 0-9Z"/>',
    "run": '<circle cx="15" cy="4" r="2"/><path d="m12 8 4 3 4 1M12 8l-4 4H4m8-4-1 7 5 5m-5-5-5 5"/>',
    "ride": '<circle cx="5" cy="17" r="4"/><circle cx="19" cy="17" r="4"/><path d="m5 17 5-9 5 9H5m5-9h6m-6 0-2-3H5m14 12-3-12h3"/>',
    "walk": '<circle cx="13" cy="4" r="2"/><path d="m12 8 4 4 4 1M12 8l-4 4H5m7-4-2 8-3 5m3-5 5 5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "star": '<path d="m12 3 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1 3-6Z"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "close": '<path d="m6 6 12 12M6 18 18 6"/>',
    "heart": '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
}


def icon(name):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name, PATHS["activity"])}</svg>'
    return html.Span(className="icon", style={"maskImage": f'url("data:image/svg+xml,{quote(svg)}")', "WebkitMaskImage": f'url("data:image/svg+xml,{quote(svg)}")'}, **{"aria-hidden": "true"})


def tr(lang, hu, en):
    return hu if lang == "HU" else en


def number(value, digits=0):
    return f"{value:,.{digits}f}".replace(",", " ")


def panel(title, subtitle, children, extra=None):
    return html.Section([html.Div([html.Div([html.H3(title), html.P(subtitle)]), extra], className="panel-heading"), children], className="panel")


def stat(label, value, unit, ico, detail, delta=None):
    return html.Div([html.Div([html.Span(label), icon(ico)], className="stat-top"),
                     html.Div([html.Strong(value), html.Span(unit)], className="stat-value"),
                     html.Div([html.Span(delta, className="delta") if delta else None, html.Span(detail)], className="stat-bottom")], className="stat-card")
