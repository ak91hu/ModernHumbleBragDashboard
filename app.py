"""Humblebrag: a bilingual, responsive Strava dashboard."""
from datetime import date
import math
import os
from zoneinfo import ZoneInfo

from dash import Dash, ALL, Input, Output, State, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate
import pandas as pd

from analytics import DATA_FILE, comparison_range, filter_data, load_data, pace_label
from charts import sport_name
from export_metadata import load_export_timestamp
from ui import icon, panel, tr
import views

app = Dash(__name__, title="Humblebrag · Every move counts", suppress_callback_exceptions=True,
           meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"},
                      {"name": "description", "content": "Your movement, beautifully put into perspective. Strava trends, goals and personal bests."}])
server = app.server
app._favicon = "favicon.svg"
df_global = load_data()
EXPORT_TIMESTAMP = load_export_timestamp(DATA_FILE)
YEARS = sorted(df_global["year"].unique().tolist(), reverse=True) or [date.today().year]
TYPES = sorted(df_global["type"].unique().tolist())
TODAY = pd.Timestamp.today().normalize()
DEFAULT_YEAR = YEARS[0]
START = pd.Timestamp(year=DEFAULT_YEAR, month=1, day=1)
END = min(TODAY, pd.Timestamp(year=DEFAULT_YEAR, month=12, day=31))
NAV = ["overview", "trends", "calendar", "goals", "records", "log"]
DEFAULT_GOALS = {"year": DEFAULT_YEAR, "distance": 2000, "elevation": 15000, "count": 300}


def nav_label(key, lang):
    return {"overview": tr(lang, "Áttekintés", "Overview"), "trends": tr(lang, "Trendek és elemzés", "Trends & analysis"),
            "calendar": tr(lang, "Aktivitásnaptár", "Activity calendar"), "goals": tr(lang, "Célok és kihívások", "Goals & challenges"),
            "records": tr(lang, "Személyes rekordok", "Personal bests"), "log": tr(lang, "Edzésnapló", "Activity log")}[key]


def close_button(id):
    return html.Button(icon("close"), id=id, className="icon-button", **{"aria-label": "Bezárás / Close"})


def export_status(lang):
    label = tr(lang, "Legutóbbi Strava-adatexport: ", "Last Strava data export: ")
    if EXPORT_TIMESTAMP is None:
        return label + tr(lang, "az időpont nincs rögzítve", "time not recorded")
    local_time = EXPORT_TIMESTAMP.astimezone(ZoneInfo("Europe/Budapest"))
    formatted = local_time.strftime("%Y.%m.%d. %H:%M" if lang == "HU" else "%Y-%m-%d %H:%M")
    return [html.Span(label), html.Time(formatted + " (" + tr(lang, "budapesti idő", "Budapest time") + ")",
                                        dateTime=local_time.isoformat())]


app.layout = html.Div([
    dcc.Store(id="active-view", data="overview"), dcc.Store(id="theme-store", data="light", storage_type="local"),
    dcc.Store(id="favorites-store", data=[], storage_type="local"), dcc.Store(id="goals-store", data=DEFAULT_GOALS, storage_type="local"),
    dcc.Store(id="page-store", data=0), dcc.Download(id="download-csv"),
    html.A("Ugrás a tartalomhoz / Skip to content", href="#main-content", className="skip-link"),
    html.Aside([
        html.A([html.Span([html.I(), html.I(), html.I()], className="brand-mark"), html.Span(["humblebrag", html.Span(".", className="brand-period")])], href="/", className="brand", **{"aria-label": "Humblebrag"}),
        html.Div("MAKE YOUR MOVES COUNT", className="brand-tagline"), html.Span("A TE TERED", id="nav-caption", className="sidebar-caption"),
        html.Nav([html.Button([icon(key), html.Span(nav_label(key, "HU"), id=f"nav-label-{key}")], id=f"nav-{key}", className="nav-item" + (" active" if key == "overview" else ""), n_clicks=0) for key in NAV], **{"aria-label": "Navigáció / Navigation"}),
        html.Div([html.Div([icon("goals"), html.Strong("SZŰRD A TÖRTÉNETED", id="filter-caption")], className="filter-caption"),
                  html.Label("Sportágak", id="sport-label", htmlFor="type-filter"),
                  dcc.Dropdown(id="type-filter", options=[{"label": sport_name(kind, "HU"), "value": kind} for kind in TYPES], value=[], multi=True, placeholder="Minden sportág", persistence=True, persistence_type="local"),
                  html.Label("Év", id="year-label", htmlFor="year-filter"),
                  dcc.Dropdown(id="year-filter", options=[{"label": str(y), "value": y} for y in YEARS], value=DEFAULT_YEAR, clearable=False, searchable=False),
                  html.P("Az üres sportválasztás minden sportágat mutat.", id="filter-hint", className="filter-hint")], className="sidebar-filters"),
        html.Div([html.Div([html.Span(className="sync-dot"), html.Span("STRAVA DATA")], className="sync-status"), html.P(id="last-sync"),
                  html.A(["View on Strava", icon("arrow")], href="https://www.strava.com/athlete/training", target="_blank", rel="noopener noreferrer", className="strava-link")], className="sidebar-bottom"),
        html.Div([html.Span("A", className="avatar"), html.Div([html.Strong("Ákos"), html.Small("A little better, every day.")]), html.Span("↗", className="profile-arrow")], className="profile")
    ], id="sidebar", className="sidebar"),
    html.Div([
        html.Header([html.Div([html.Button(icon("menu"), id="mobile-menu", className="icon-button mobile-toggle", **{"aria-label": "Menü / Menu"}), html.Span("Workspace", className="muted"), html.Span("/", className="breadcrumb-slash"), html.Span("Áttekintés", id="breadcrumb")], className="breadcrumb"),
                     html.Div([html.Span([html.Span(className="live-dot"), "STRAVA DATA"], className="data-badge"), dcc.Dropdown(id="lang-selector", options=[{"label": "HU", "value": "HU"}, {"label": "EN", "value": "EN"}], value="HU", clearable=False, searchable=False, className="lang-select", persistence=True, persistence_type="local"),
                               html.Button(icon("moon"), id="theme-toggle", className="icon-button", title="Téma váltása / Toggle theme", **{"aria-label": "Téma váltása / Toggle theme"})], className="topbar-actions")], className="topbar"),
        html.Main([
            html.Div([html.Div([html.Span("A MOZGÁS ÖRÖME, SZÁMOKBAN", id="page-eyebrow", className="eyebrow"), html.H1("Minden mozdulat számít.", id="page-title"), html.P("Egy új perspektíva az edzéseidre. Egy kis büszkeség a hétköznapokra.", id="page-subtitle")]),
                      html.Button([icon("download"), html.Span("CSV export", id="export-label")], id="export-button", className="secondary-button")], className="page-heading"),
            html.P(export_status("HU"), id="last-export", className="export-status"),
            html.Div([
                dcc.RadioItems(id="period-preset", options=[{"label": "30 nap", "value": "30"}, {"label": "90 nap", "value": "90"}, {"label": "Év", "value": "year"}, {"label": "Összes", "value": "all"}, {"label": "Egyéni", "value": "custom"}], value="year", className="period-switch"),
                dcc.DatePickerRange(id="date-range", start_date=START.date(), end_date=END.date(), display_format="YYYY.MM.DD", first_day_of_week=1, minimum_nights=0, clearable=False, show_outside_days=True),
                dcc.Dropdown(id="metric-selector", options=[{"label": "Távolság · km", "value": "distance"}, {"label": "Mozgási idő · min", "value": "time"}, {"label": "Szint · m", "value": "elevation"}], value="distance", clearable=False, searchable=False, className="metric-select"),
            ], className="filter-bar"),
            html.Div([html.Div([icon("search"), dcc.Input(id="activity-search", type="search", placeholder="Keresés az edzések között…", debounce=.35)], className="search-field"),
                      dcc.Checklist(id="only-favorites", options=[{"label": "Csak kedvencek", "value": "yes"}], value=[], className="favorites-filter"),
                      dcc.Dropdown(id="sort-selector", options=[{"label": "Legújabb elöl", "value": "newest"}, {"label": "Legrégebbi elöl", "value": "oldest"}, {"label": "Leghosszabb elöl", "value": "distance"}, {"label": "Legtöbb szint", "value": "elevation"}], value="newest", clearable=False, searchable=False, className="sort-select")], id="log-controls", className="log-controls", style={"display": "none"}),
            dcc.Loading(html.Div(id="page-content"), type="circle", color="#31785b", delay_show=350,
                        overlay_style={"visibility": "visible", "backgroundColor": "transparent"}),
            html.Div([html.Span(id="page-info"), html.Div([html.Button("←", id="prev-page", className="icon-button", **{"aria-label": "Előző oldal / Previous page"}), html.Button("→", id="next-page", className="icon-button", **{"aria-label": "Következő oldal / Next page"})])], id="pagination", className="pagination", style={"display": "none"}),
            html.Footer([html.Span([html.Strong("humblebrag."), " A little effort. A lot to be proud of."]), html.Span("Made with purpose by Ákos · Powered by Strava")], className="footer"),
        ], id="main-content", className="main-content", tabIndex=-1),
    ], className="workspace"),
    html.Div([html.Div([html.Div([html.H2("A következő céljaid", id="goal-modal-title"), close_button("cancel-goals")], className="modal-heading"),
                        html.P("Állíts be elérhető éves célokat. Bármikor változtathatsz rajtuk.", id="goal-modal-description"),
                        html.Label("Év / Year", htmlFor="goal-year"), dcc.Dropdown(id="goal-year", options=[{"label": str(y), "value": y} for y in sorted(set(YEARS + [date.today().year, date.today().year + 1]), reverse=True)], value=DEFAULT_YEAR, clearable=False),
                        html.Label("Távolság / Distance (km)", htmlFor="goal-distance"), dcc.Input(id="goal-distance", type="number", min=1, max=1000000, step=1, value=2000),
                        html.Label("Szintemelkedés / Elevation (m)", htmlFor="goal-elevation"), dcc.Input(id="goal-elevation", type="number", min=1, max=10000000, step=1, value=15000),
                        html.Label("Edzések / Activities", htmlFor="goal-count"), dcc.Input(id="goal-count", type="number", min=1, max=10000, step=1, value=300),
                        html.P(id="goal-validation", className="validation", role="alert"), html.Button("Célok mentése", id="save-goals", className="primary-button full-width")], className="modal-card", role="dialog", **{"aria-modal": "true", "aria-labelledby": "goal-modal-title"})], id="goal-dialog", className="modal-overlay", style={"display": "none"}),
    html.Div([html.Div([html.Div([html.H2(id="detail-title"), close_button("close-detail")], className="modal-heading"), html.Div(id="detail-body")], className="modal-card detail-card", role="dialog", **{"aria-modal": "true", "aria-labelledby": "detail-title"})], id="detail-dialog", className="modal-overlay", style={"display": "none"}),
], id="app-shell", className="app-shell")


@app.callback(Output("active-view", "data"), [Input(f"nav-{key}", "n_clicks") for key in NAV], Input("view-all", "n_clicks", allow_optional=True), prevent_initial_call=True)
def navigate(*clicks):
    if not ctx.triggered[0]["value"]:
        raise PreventUpdate
    return "log" if ctx.triggered_id == "view-all" else str(ctx.triggered_id).removeprefix("nav-")


@app.callback(Output("date-range", "start_date"), Output("date-range", "end_date"), Output("period-preset", "value"), Input("period-preset", "value"), Input("year-filter", "value"), Input("date-range", "start_date"), Input("date-range", "end_date"))
def set_dates(preset, year, start, end):
    if ctx.triggered_id == "date-range":
        return no_update, no_update, "custom"
    if ctx.triggered_id == "year-filter" or preset == "year":
        return f"{year}-01-01", min(TODAY, pd.Timestamp(year=int(year), month=12, day=31)).date().isoformat(), "year"
    if preset in {"30", "90"}:
        return (TODAY - pd.Timedelta(days=int(preset) - 1)).date().isoformat(), TODAY.date().isoformat(), preset
    if preset == "custom":
        raise PreventUpdate
    first = df_global["date"].min() if not df_global.empty else START
    return first.date().isoformat(), TODAY.date().isoformat(), "all"


@app.callback(Output("theme-store", "data"), Input("theme-toggle", "n_clicks"), State("theme-store", "data"), prevent_initial_call=True)
def toggle_theme(clicks, current):
    return "light" if current == "dark" else "dark"


@app.callback(Output("app-shell", "className"), Output("theme-toggle", "children"), Input("theme-store", "data"))
def apply_theme(theme):
    return "app-shell" + (" dark" if theme == "dark" else ""), icon("sun" if theme == "dark" else "moon")


@app.callback(Output("sidebar", "className"), Input("mobile-menu", "n_clicks"), Input("active-view", "data"), State("sidebar", "className"))
def mobile_navigation(clicks, view, current):
    return "sidebar open" if ctx.triggered_id == "mobile-menu" and "open" not in current else "sidebar"


@app.callback(Output("favorites-store", "data"), Input({"kind": "favorite", "id": ALL, "slot": ALL}, "n_clicks"), State("favorites-store", "data"), prevent_initial_call=True)
def toggle_favorite(clicks, favorites):
    if not ctx.triggered_id or not isinstance(ctx.triggered_id.get("id"), str) or not any(clicks):
        raise PreventUpdate
    activity_id = ctx.triggered_id["id"]
    saved = list(favorites or [])
    if activity_id in saved:
        saved.remove(activity_id)
    else:
        saved.append(activity_id)
    return saved


@app.callback(Output("page-store", "data"), Input("prev-page", "n_clicks"), Input("next-page", "n_clicks"), Input("activity-search", "value"), Input("sort-selector", "value"), Input("only-favorites", "value"), Input("date-range", "start_date"), Input("date-range", "end_date"), Input("type-filter", "value"), Input("favorites-store", "data"), State("page-store", "data"))
def paginate(prev, nex, query, sort, only, start, end, types, favorites, page):
    if ctx.triggered_id == "prev-page":
        return max(0, (page or 0) - 1)
    if ctx.triggered_id == "next-page":
        count = len(filter_data(df_global, start, end, types, query or "", favorites, bool(only)))
        return min(max(0, math.ceil(count / 12) - 1), (page or 0) + 1)
    return 0


STATIC_LABELS = {
    "nav-caption": ("A TE TERED", "YOUR WORKSPACE"), "filter-caption": ("SZŰRD A TÖRTÉNETED", "FILTER YOUR STORY"),
    "sport-label": ("Sportágak", "Sports"), "year-label": ("Év", "Year"), "filter-hint": ("Az üres sportválasztás minden sportágat mutat.", "An empty selection includes every sport."),
    "page-eyebrow": ("A MOZGÁS ÖRÖME, SZÁMOKBAN", "THE JOY OF MOVEMENT, IN NUMBERS"), "export-label": ("CSV export", "Export CSV"),
    "goal-modal-title": ("A következő céljaid", "Your next goals"), "goal-modal-description": ("Állíts be elérhető éves célokat. Bármikor változtathatsz rajtuk.", "Set achievable annual goals. You can change them any time."), "save-goals": ("Célok mentése", "Save goals"),
}


@app.callback([Output(key, "children") for key in STATIC_LABELS] + [Output(f"nav-label-{key}", "children") for key in NAV] +
              [Output("type-filter", "options"), Output("type-filter", "placeholder"), Output("period-preset", "options"), Output("metric-selector", "options"), Output("activity-search", "placeholder"), Output("only-favorites", "options"), Output("sort-selector", "options"), Output("last-sync", "children"), Output("last-export", "children")], Input("lang-selector", "value"))
def translate(lang):
    latest = df_global["start_date"].max().strftime("%Y.%m.%d.") if not df_global.empty else "—"
    return ([tr(lang, *labels) for labels in STATIC_LABELS.values()] + [nav_label(key, lang) for key in NAV] +
            [[{"label": sport_name(kind, lang), "value": kind} for kind in TYPES], tr(lang, "Minden sportág", "All sports"),
             [{"label": tr(lang, "30 nap", "30 days"), "value": "30"}, {"label": tr(lang, "90 nap", "90 days"), "value": "90"}, {"label": tr(lang, "Év", "Year"), "value": "year"}, {"label": tr(lang, "Összes", "All time"), "value": "all"}, {"label": tr(lang, "Egyéni", "Custom"), "value": "custom"}],
             [{"label": tr(lang, "Távolság · km", "Distance · km"), "value": "distance"}, {"label": tr(lang, "Mozgási idő · min", "Moving time · min"), "value": "time"}, {"label": tr(lang, "Szint · m", "Elevation · m"), "value": "elevation"}],
             tr(lang, "Keresés az edzések között…", "Search your activities…"), [{"label": tr(lang, "Csak kedvencek", "Favorites only"), "value": "yes"}],
             [{"label": tr(lang, "Legújabb elöl", "Newest first"), "value": "newest"}, {"label": tr(lang, "Legrégebbi elöl", "Oldest first"), "value": "oldest"}, {"label": tr(lang, "Leghosszabb elöl", "Longest first"), "value": "distance"}, {"label": tr(lang, "Legtöbb szint", "Most elevation"), "value": "elevation"}], tr(lang, "Legutóbbi edzés: ", "Latest activity: ") + latest, export_status(lang)])


@app.callback(Output("page-content", "children"), Output("page-title", "children"), Output("page-subtitle", "children"), Output("breadcrumb", "children"),
              [Output(f"nav-{key}", "className") for key in NAV], Output("log-controls", "style"), Output("pagination", "style"), Output("page-info", "children"), Output("prev-page", "disabled"), Output("next-page", "disabled"),
              Input("active-view", "data"), Input("lang-selector", "value"), Input("date-range", "start_date"), Input("date-range", "end_date"), Input("type-filter", "value"), Input("metric-selector", "value"), Input("theme-store", "data"), Input("goals-store", "data"), Input("favorites-store", "data"), Input("activity-search", "value"), Input("sort-selector", "value"), Input("only-favorites", "value"), Input("page-store", "data"))
def render(view, lang, start, end, types, metric, theme, goals, favorites, query, sort, only, page):
    view = view if view in NAV else "overview"
    start, end = start or START.date().isoformat(), end or END.date().isoformat()
    dff = filter_data(df_global, start, end, types)
    compare_mode = "year" if pd.Timestamp(start).month == 1 and pd.Timestamp(start).day == 1 else "previous"
    pstart, pend = comparison_range(start, end, compare_mode)
    previous = filter_data(df_global, pstart.date().isoformat(), pend.date().isoformat(), types)
    title = tr(lang, "Minden mozdulat számít.", "Every move counts.") if view == "overview" else nav_label(view, lang) + "."
    subtitles = {"overview": tr(lang, "Egy új perspektíva az edzéseidre. Egy kis büszkeség a hétköznapokra.", "A fresh perspective on your training. A little pride in your everyday."), "trends": tr(lang, "Ismerd meg a ritmusodat, és nézd meg, meddig jutottál.", "Find your rhythm and see how far you have come."), "calendar": tr(lang, "Apró négyzetek. Sok-sok következetesen megtett lépés.", "Small squares. A whole lot of showing up."), "goals": tr(lang, "Tűzz ki valamit, amiért jólesik elindulni.", "Set something worth getting out the door for."), "records": tr(lang, "Azok a napok, amikor egy kicsit túlléptél magadon.", "The days you went a little beyond yourself."), "log": tr(lang, "Minden edzésed egy helyen. Keress, rendezz, és éld át újra.", "Every activity in one place. Search, sort, and relive it.")}
    log_df = filter_data(dff, query=query or "", favorites=favorites, only_favorites=bool(only))
    count = len(log_df)
    max_page = max(0, math.ceil(count / 12) - 1)
    page = min(page or 0, max_page)
    if dff.empty and view != "goals":
        content = views.empty_state(lang)
    elif view == "overview":
        content = views.overview(dff, previous, start, end, metric, lang, theme, df_global, goals, favorites)
    elif view == "trends":
        content = views.trends(dff, previous, start, end, metric, lang, theme)
    elif view == "calendar":
        content = views.calendar_view(dff, lang)
    elif view == "goals":
        content = views.goals_view(dff, df_global, goals, lang)
    elif view == "records":
        content = views.records_view(dff, lang)
    else:
        sort_column = {"newest": "start_date", "oldest": "start_date", "distance": "distance_km", "elevation": "elevation_m"}.get(sort, "start_date")
        log_df = log_df.sort_values(sort_column, ascending=sort == "oldest")
        content = panel(tr(lang, "Az edzéseid", "Your activities"), f"{count} " + tr(lang, "találat · kattints egy edzésre a részletekhez", "results · click an activity for details"), views.activity_rows(log_df.iloc[page*12:(page+1)*12], lang, favorites))
    info = f"{page*12+1 if count else 0}–{min((page+1)*12,count)} / {count} " + tr(lang, "edzés", "activities")
    return [content, title, subtitles[view], nav_label(view, lang)] + ["nav-item" + (" active" if key == view else "") for key in NAV] + [{"display": "flex" if view == "log" else "none"}, {"display": "flex" if view == "log" else "none"}, info, page == 0, page >= max_page]


@app.callback(Output("goal-dialog", "style"), Output("goals-store", "data"), Output("goal-year", "value"), Output("goal-distance", "value"), Output("goal-elevation", "value"), Output("goal-count", "value"), Output("goal-validation", "children"),
              Input("open-goals-card", "n_clicks", allow_optional=True), Input("save-goals", "n_clicks"), Input("cancel-goals", "n_clicks"), State("goal-year", "value"), State("goal-distance", "value"), State("goal-elevation", "value"), State("goal-count", "value"), State("goals-store", "data"), State("lang-selector", "value"), prevent_initial_call=True)
def edit_goals(open_click, save, close, year, distance, elevation, count, goals, lang):
    if ctx.triggered_id == "open-goals-card":
        if not open_click:
            raise PreventUpdate
        goals = goals or DEFAULT_GOALS
        return {"display": "flex"}, no_update, goals["year"], goals["distance"], goals["elevation"], goals["count"], ""
    if ctx.triggered_id == "save-goals":
        values = [distance, elevation, count]
        if year not in YEARS + [date.today().year, date.today().year + 1] or any(value is None or not math.isfinite(float(value)) or value < 1 or int(value) != value for value in values) or distance > 1000000 or elevation > 10000000 or count > 10000:
            return {"display": "flex"}, no_update, no_update, no_update, no_update, no_update, tr(lang, "Adj meg érvényes, pozitív egész célértékeket.", "Enter valid positive whole-number goals.")
        return {"display": "none"}, {"year": year, "distance": distance, "elevation": elevation, "count": count}, no_update, no_update, no_update, no_update, ""
    return {"display": "none"}, no_update, no_update, no_update, no_update, no_update, ""


@app.callback(Output("detail-dialog", "style"), Output("detail-title", "children"), Output("detail-body", "children"),
              Input({"kind": "detail", "id": ALL, "slot": ALL}, "n_clicks"), Input({"kind": "day", "date": ALL, "year": ALL}, "n_clicks"), Input({"kind": "period-detail", "start": ALL, "end": ALL, "key": ALL}, "n_clicks"), Input("close-detail", "n_clicks"), State("lang-selector", "value"), State("date-range", "start_date"), State("date-range", "end_date"), State("type-filter", "value"), State("favorites-store", "data"), prevent_initial_call=True)
def show_detail(clicks, day_clicks, period_clicks, close, lang, start, end, types, favorites):
    trigger = ctx.triggered_id
    if trigger == "close-detail":
        return {"display": "none"}, no_update, []
    if not isinstance(trigger, dict) or not any(clicks + day_clicks + period_clicks):
        raise PreventUpdate
    if trigger.get("kind") == "period-detail":
        if not isinstance(trigger.get("start"), str) or not isinstance(trigger.get("end"), str):
            raise PreventUpdate
        matches = filter_data(filter_data(df_global, start, end, types), trigger["start"], trigger["end"])
        title = trigger["start"] + (" – " + trigger["end"] if trigger["start"] != trigger["end"] else "")
        body = [html.P(f"{len(matches)} " + tr(lang, "edzés a kiválasztott szűrők alapján", "activities matching your filters")),
                views.activity_rows(matches.sort_values("start_date", ascending=False), lang, favorites, slot="record-period")]
        return {"display": "flex"}, title, body
    if not isinstance(trigger.get("date") if trigger.get("kind") == "day" else trigger.get("id"), str):
        raise PreventUpdate
    if trigger["kind"] == "day":
        day = trigger["date"]
        matches = filter_data(df_global, start, end, types)
        matches = matches[matches["date"] == pd.Timestamp(day)]
        return {"display": "flex"}, day, views.activity_rows(matches.sort_values("start_date", ascending=False), lang, favorites, slot="day")
    matches = df_global[df_global["id"] == trigger["id"]]
    if matches.empty:
        raise PreventUpdate
    row = matches.iloc[0]
    pace, unit = pace_label(row)
    values = [(tr(lang, "Távolság", "Distance"), f"{row['distance_km']:.2f} km"), (tr(lang, "Mozgási idő", "Moving time"), f"{row['moving_time_min']:.0f} min"), (tr(lang, "Szintemelkedés", "Elevation"), f"{row['elevation_m']:.0f} m"), (tr(lang, "Tempó / sebesség", "Pace / speed"), f"{pace} {unit}"), (tr(lang, "Átlagpulzus", "Average heart rate"), f"{row['average_heartrate']:.0f} bpm" if row['average_heartrate'] > 0 else "—"), ("Kudos", str(int(row["kudos"])))]
    body = [html.P(f"{row['start_date']:%Y.%m.%d. %H:%M} · {sport_name(row['type'],lang)}"), html.Div([html.Div([html.Small(label), html.Strong(value)]) for label, value in values], className="detail-stats"),
            html.A([tr(lang, "Megnyitás a Straván", "Open on Strava"), icon("arrow")], href=f"https://www.strava.com/activities/{row['id']}" if row['id'].isdigit() else "https://www.strava.com", target="_blank", rel="noopener noreferrer", className="primary-button")]
    return {"display": "flex"}, row["name"], body


@app.callback(Output("download-csv", "data"), Input("export-button", "n_clicks"), State("date-range", "start_date"), State("date-range", "end_date"), State("type-filter", "value"), State("active-view", "data"), State("activity-search", "value"), State("only-favorites", "value"), State("favorites-store", "data"), prevent_initial_call=True)
def export_csv(clicks, start, end, types, view, query, only, favorites):
    dff = filter_data(df_global, start, end, types, (query or "") if view == "log" else "", favorites, bool(only) if view == "log" else False)
    columns = ["id", "name", "start_date", "type", "distance_km", "moving_time_min", "elapsed_time", "elevation_m", "average_speed_kmh", "average_heartrate", "kudos"]
    exported = dff[columns].copy()
    for column in ["name", "type"]:
        exported[column] = exported[column].map(lambda value: "'" + str(value) if str(value).lstrip().startswith(("=", "+", "-", "@")) else value)
    return dcc.send_string("\ufeff" + exported.to_csv(index=False), f"humblebrag-{start}-{end}.csv")


@server.get("/health")
def health():
    return {"status": "ok", "activities": len(df_global)}


if __name__ == "__main__":
    app.run(debug=os.getenv("DASH_DEBUG") == "1", host="127.0.0.1", port=int(os.getenv("PORT", "8050")))
