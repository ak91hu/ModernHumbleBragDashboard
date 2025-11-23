import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import os

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX], title="Humblebrag Dashboard")
server = app.server

TRANSLATIONS = {
    'EN': {
        'sidebar_title': "Filters",
        'lang_sel': "Language",
        'years': "Years",
        'types': "Activity Type",
        'page_title': "Humblebrag Dashboard",
        'kpi_dist': "Total Distance",
        'kpi_elev': "Total Elevation",
        'kpi_time': "Moving Time",
        'kpi_cal': "Calories",
        'kpi_count': "Activities",
        'kpi_eff': "Efficiency",
        'tab_trends': "Trends",
        'tab_analysis': "Deep Analysis",
        'tab_challenges': "Gamification",
        'tab_heatmap': "Calendar",
        'tab_records': "Records",
        'tab_log': "Log",
        'eff_tooltip': "Moving Time / Elapsed Time",
        'chal_mountain': "Climbing Challenges",
        'chal_gastro': "Gastro Conversion",
        'pizza': "Pizza Slices",
        'beer': "Pints of Beer",
        'burger': "Burgers",
        'donut': "Donuts",
        'kekes': "Kekes Peak (1014m)",
        'everest': "Mt. Everest (8848m)",
        'rec_longest': "Longest Dist",
        'rec_highest': "Highest Elev",
        'rec_fastest': "Fastest Avg",
        'rec_max_speed': "Max Speed",
        'rec_hr': "Max Heart Rate",
        'col_date': "Date",
        'col_name': "Name",
        'col_dist': "Dist (km)",
        'col_elev': "Elev (m)",
        'col_pace': "Speed (km/h)",
        'footer': "Made with ❤️ by Akos"
    },
    'HU': {
        'sidebar_title': "Szűrők",
        'lang_sel': "Nyelv",
        'years': "Évek",
        'types': "Mozgásforma",
        'page_title': "Humblebrag Dashboard",
        'kpi_dist': "Össz Távolság",
        'kpi_elev': "Össz Szint",
        'kpi_time': "Mozgási Idő",
        'kpi_cal': "Kalória",
        'kpi_count': "Edzések Száma",
        'kpi_eff': "Hatékonyság",
        'tab_trends': "Trendek",
        'tab_analysis': "Elemzés",
        'tab_challenges': "Kihívások",
        'tab_heatmap': "Naptár",
        'tab_records': "Rekordok",
        'tab_log': "Napló",
        'eff_tooltip': "Mozgási idő / Eltelt idő aránya",
        'chal_mountain': "Hegymászó Kihívás",
        'chal_gastro': "Gasztró Átváltás",
        'pizza': "Pizza szelet",
        'beer': "Korsó Sör",
        'burger': "Hamburger",
        'donut': "Fánk",
        'kekes': "Kékes-tető (1014m)",
        'everest': "Mt. Everest (8848m)",
        'rec_longest': "Leghosszabb",
        'rec_highest': "Legtöbb Szint",
        'rec_fastest': "Leggyorsabb Átlag",
        'rec_max_speed': "Max Sebesség",
        'rec_hr': "Max Pulzus",
        'col_date': "Dátum",
        'col_name': "Név",
        'col_dist': "Táv (km)",
        'col_elev': "Szint (m)",
        'col_pace': "Tempó (km/h)",
        'footer': "Made with ❤️ by Akos"
    }
}

def load_data():
    if not os.path.exists('data/activities.csv'): 
        return pd.DataFrame({'start_date': [], 'year': [], 'type': []})
    
    df = pd.read_csv('data/activities.csv')
    if df.empty: return pd.DataFrame()

    num_cols = ['distance_km', 'elevation_m', 'average_speed_kmh', 'max_speed', 'moving_time_min', 'elapsed_time', 'kudos', 'kilojoules', 'average_heartrate', 'max_heartrate']
    for col in num_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'type' in df.columns:
        df['type'] = df['type'].astype(str).str.replace(r'root=', '', regex=False).str.strip()
        df['type'] = df['type'].apply(lambda x: x.split('=')[-1].replace('>', '') if '=' in x else x)

    df['start_date'] = pd.to_datetime(df['start_date'], utc=True).dt.tz_localize(None)
    
    df['year'] = df['start_date'].dt.year
    df['month'] = df['start_date'].dt.month
    df['week'] = df['start_date'].dt.isocalendar().week
    df['day_of_year'] = df['start_date'].dt.dayofyear
    df['day_name'] = df['start_date'].dt.day_name()
    df['day_of_week'] = df['start_date'].dt.dayofweek 
    df['hour'] = df['start_date'].dt.hour
    
    if 'kilojoules' not in df.columns: df['kilojoules'] = 0
    def estimate_calories(row):
        if row['kilojoules'] > 0: return row['kilojoules']
        if row['type'] == 'Run': return row['distance_km'] * 75
        if row['type'] == 'Ride': return row['distance_km'] * 25
        return row['distance_km'] * 40
    
    df['calories'] = df.apply(estimate_calories, axis=1)
    df['gradient'] = df.apply(lambda x: (x['elevation_m'] / x['distance_km']) if x['distance_km'] > 0 else 0, axis=1)
    
    df = df.sort_values('start_date')
    df['cumulative_km'] = df.groupby('year')['distance_km'].cumsum()
    
    return df

df_global = load_data()
available_years = sorted(df_global['year'].unique(), reverse=True) if not df_global.empty else []
available_types = sorted(df_global['type'].unique()) if not df_global.empty else []

def build_sidebar():
    return dbc.Card(
        [
            html.H2("Filters", className="display-6", id="lbl-filters"),
            html.Hr(),
            html.Label(id="lbl-lang", className="fw-bold"),
            dbc.RadioItems(
                options=[{"label": "🇬🇧 EN", "value": "EN"}, {"label": "🇭🇺 HU", "value": "HU"}],
                value="EN",
                id="lang-selector",
                inline=True,
                className="mb-3"
            ),
            html.Label(id="lbl-years", className="fw-bold"),
            dcc.Dropdown(
                id="year-filter",
                options=[{'label': str(y), 'value': y} for y in available_years],
                value=available_years,
                multi=True,
                className="mb-3"
            ),
            html.Label(id="lbl-types", className="fw-bold"),
            dcc.Dropdown(
                id="type-filter",
                options=[{'label': t, 'value': t} for t in available_types],
                value=available_types,
                multi=True,
                className="mb-3"
            ),
        ],
        body=True,
        className="h-100 bg-light border-0"
    )

def build_kpi(id_title, id_val, icon, color="primary"):
    return dbc.Card(
        dbc.CardBody([
            html.H6(id=id_title, className="card-subtitle text-muted mb-1 small"),
            html.H3(id=id_val, className=f"card-title text-{color}"),
            html.Div(icon, className="position-absolute top-0 end-0 p-2 opacity-25 h4")
        ]),
        className="mb-3 border-0 shadow-sm"
    )

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(build_sidebar(), md=3, lg=2, className="d-none d-md-block bg-light p-3"),
        dbc.Col([
            html.H1(id="page-title", className="my-4 fw-bold"),
            
            dbc.Row([
                dbc.Col(build_kpi("kpi-lbl-dist", "kpi-val-dist", "📏"), width=6, lg=2),
                dbc.Col(build_kpi("kpi-lbl-elev", "kpi-val-elev", "⛰️"), width=6, lg=2),
                dbc.Col(build_kpi("kpi-lbl-time", "kpi-val-time", "⏱️"), width=6, lg=2),
                dbc.Col(build_kpi("kpi-lbl-cal", "kpi-val-cal", "🔥"), width=6, lg=2),
                dbc.Col(build_kpi("kpi-lbl-eff", "kpi-val-eff", "⚙️", "success"), width=6, lg=2),
                dbc.Col(build_kpi("kpi-lbl-count", "kpi-val-count", "#️⃣", "info"), width=6, lg=2),
            ], className="mb-2"),

            dbc.Tabs([
                dbc.Tab(label="Trends", tab_id="tab-trends", id="tab-lbl-trends"),
                dbc.Tab(label="Analysis", tab_id="tab-analysis", id="tab-lbl-analysis"),
                dbc.Tab(label="Gamification", tab_id="tab-challenges", id="tab-lbl-challenges"),
                dbc.Tab(label="Calendar", tab_id="tab-heatmap", id="tab-lbl-heatmap"),
                dbc.Tab(label="Records", tab_id="tab-records", id="tab-lbl-records"),
                dbc.Tab(label="Log", tab_id="tab-log", id="tab-lbl-log"),
            ], id="tabs", active_tab="tab-trends", className="mb-3"),

            html.Div(id="tab-content"),
            
            html.Hr(),
            html.Div([
                html.Span(id="footer-text"),
                html.A("Akos", href="https://discordapp.com/users/justakos91", target="_blank", className="fw-bold text-danger ms-1")
            ], className="text-center py-4 text-muted")

        ], md=9, lg=10, className="p-4")
    ])
], fluid=True, className="vh-100")

@app.callback(
    [Output("page-title", "children"),
     Output("lbl-filters", "children"), Output("lbl-lang", "children"), Output("lbl-years", "children"), Output("lbl-types", "children"),
     Output("kpi-lbl-dist", "children"), Output("kpi-lbl-elev", "children"), Output("kpi-lbl-time", "children"),
     Output("kpi-lbl-cal", "children"), Output("kpi-lbl-eff", "children"), Output("kpi-lbl-count", "children"),
     Output("tab-lbl-trends", "label"), Output("tab-lbl-analysis", "label"), Output("tab-lbl-challenges", "label"),
     Output("tab-lbl-heatmap", "label"), Output("tab-lbl-records", "label"), Output("tab-lbl-log", "label"),
     Output("footer-text", "children"),
     Output("kpi-val-dist", "children"), Output("kpi-val-elev", "children"), Output("kpi-val-time", "children"),
     Output("kpi-val-cal", "children"), Output("kpi-val-eff", "children"), Output("kpi-val-count", "children"),
     Output("tab-content", "children")],
    [Input("lang-selector", "value"), Input("year-filter", "value"), Input("type-filter", "value"), Input("tabs", "active_tab")]
)
def update_dashboard(lang, sel_years, sel_types, active_tab):
    T = TRANSLATIONS[lang]
    if df_global.empty: return [T['page_title']] + ["-"] * 24

    if not sel_years: sel_years = available_years
    if not sel_types: sel_types = available_types
    
    dff = df_global[df_global['year'].isin(sel_years) & df_global['type'].isin(sel_types)]

    tot_dist = dff['distance_km'].sum()
    tot_elev = dff['elevation_m'].sum()
    tot_time = dff['moving_time_min'].sum() / 60
    tot_cal = dff['calories'].sum()
    count = len(dff)
    
    elapsed_total = dff['elapsed_time'].sum() / 60
    efficiency = (dff['moving_time_min'].sum() / elapsed_total * 100) if elapsed_total > 0 else 0

    content = html.Div()
    
    if active_tab == "tab-trends":
        fig_cum = px.line(dff, x='day_of_year', y='cumulative_km', color='year', 
                          color_discrete_sequence=px.colors.qualitative.Bold, template="plotly_white")
        fig_bar = px.bar(dff.groupby('year')['distance_km'].sum().reset_index(), x='year', y='distance_km', template="plotly_white")
        content = dbc.Row([dbc.Col(dcc.Graph(figure=fig_cum), lg=8), dbc.Col(dcc.Graph(figure=fig_bar), lg=4)])

    elif active_tab == "tab-analysis":
        fig_scat = px.scatter(dff, x='distance_km', y='average_speed_kmh', size='elevation_m', color='type', 
                              hover_data=['name'], template="plotly_white", opacity=0.7)
        fig_grad = px.histogram(dff, x='gradient', nbins=30, color='type', template="plotly_white", title="Elevation/km")
        
        hr_row = html.Div()
        if 'average_heartrate' in dff.columns and dff['average_heartrate'].sum() > 0:
            fig_hr = px.box(dff[dff['average_heartrate']>0], x='type', y='average_heartrate', points="all", template="plotly_white")
            hr_row = dcc.Graph(figure=fig_hr)

        content = html.Div([
            dbc.Row([dbc.Col(dcc.Graph(figure=fig_scat), lg=6), dbc.Col(dcc.Graph(figure=fig_grad), lg=6)]),
            hr_row
        ])

    elif active_tab == "tab-challenges":
        kekes_val = min((tot_elev / 1014) * 100, 100)
        everest_val = min((tot_elev / 8848) * 100, 100)
        
        cards = dbc.Row([
            dbc.Col(dbc.Card([html.H2("🍕"), html.P(f"{T['pizza']}: {tot_cal/285:.0f}")], body=True, className="text-center shadow-sm"), width=6, lg=3),
            dbc.Col(dbc.Card([html.H2("🍺"), html.P(f"{T['beer']}: {tot_cal/215:.0f}")], body=True, className="text-center shadow-sm"), width=6, lg=3),
            dbc.Col(dbc.Card([html.H2("🍔"), html.P(f"{T['burger']}: {tot_cal/550:.0f}")], body=True, className="text-center shadow-sm"), width=6, lg=3),
            dbc.Col(dbc.Card([html.H2("🍩"), html.P(f"{T['donut']}: {tot_cal/250:.0f}")], body=True, className="text-center shadow-sm"), width=6, lg=3),
        ], className="mb-4")

        content = html.Div([
            html.H4(T['chal_mountain'], className="mb-3"),
            html.Label(f"{T['kekes']} ({tot_elev/1014:.1f}x)"),
            dbc.Progress(value=kekes_val, color="success", className="mb-3", style={"height": "20px"}),
            html.Label(f"{T['everest']} ({tot_elev/8848:.1f}x)"),
            dbc.Progress(value=everest_val, color="info", className="mb-4", style={"height": "20px"}),
            html.Hr(),
            html.H4(T['chal_gastro'], className="mb-3"),
            cards
        ])

    elif active_tab == "tab-heatmap":
        graphs = []
        for year in sorted(dff['year'].unique(), reverse=True):
            ydf = dff[dff['year'] == year]
            if ydf.empty: continue
            fr = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31')
            daily = ydf.set_index('start_date')['distance_km'].resample('D').sum().reindex(fr, fill_value=0).to_frame()
            daily['week'] = daily.index.isocalendar().week
            daily['day'] = daily.index.dayofweek
            piv = daily.pivot_table(index='day', columns='week', values='distance_km', fill_value=0)
            
            fig = px.imshow(piv, labels=dict(x="Week", y="Day", color="Km"), y=['M','T','W','T','F','S','S'],
                            title=str(year), color_continuous_scale=[(0,"#eee"),(1,"#2E7D32")], aspect="equal", template="plotly_white")
            fig.update_layout(height=200, xaxis={'showgrid':False}, yaxis={'showgrid':False})
            graphs.append(dcc.Graph(figure=fig))
        content = html.Div(graphs)

    elif active_tab == "tab-records":
        if not dff.empty:
            def rec_card(val, title):
                return dbc.Col(dbc.Card([html.H3(val, className="text-primary"), html.Small(title)], body=True, className="text-center shadow-sm bg-light"), width=6, lg=2)
            
            content = dbc.Row([
                rec_card(f"{dff['distance_km'].max():.1f} km", T['rec_longest']),
                rec_card(f"{dff['elevation_m'].max():.0f} m", T['rec_highest']),
                rec_card(f"{dff[dff['distance_km']>5]['average_speed_kmh'].max():.1f} km/h", T['rec_fastest']),
                rec_card(f"{dff.get('max_speed', pd.Series([0])).max()*3.6:.1f} km/h", T['rec_max_speed']),
                rec_card(f"{dff.get('max_heartrate', pd.Series([0])).max():.0f} bpm", T['rec_hr']),
            ])
        else:
            content = html.Div("No Data")

    elif active_tab == "tab-log":
        last_10 = dff.sort_values('start_date', ascending=False).head(15).copy()
        last_10['date'] = last_10['start_date'].dt.strftime('%Y-%m-%d')
        last_10['link'] = "[Strava](https://www.strava.com/activities/" + last_10['id'].astype(str) + ")"
        
        cols = [
            {'name': T['col_date'], 'id': 'date'},
            {'name': T['col_name'], 'id': 'name'},
            {'name': T['col_dist'], 'id': 'distance_km', 'type': 'numeric', 'format': {'specifier': '.1f'}},
            {'name': T['col_elev'], 'id': 'elevation_m'},
            {'name': T['col_pace'], 'id': 'average_speed_kmh', 'format': {'specifier': '.1f'}},
            {'name': 'Link', 'id': 'link', 'presentation': 'markdown'}
        ]
        content = dash_table.DataTable(
            data=last_10.to_dict('records'), columns=cols,
            style_as_list_view=True, style_cell={'padding': '10px'},
            style_header={'fontWeight': 'bold'}, markdown_options={"html": True}
        )

    return (
        f"{T['page_title']} {min(sel_years)}-{max(sel_years)}", T['sidebar_title'], T['lang_sel'], T['years'], T['types'],
        T['kpi_dist'], T['kpi_elev'], T['kpi_time'], T['kpi_cal'], T['kpi_eff'], T['kpi_count'],
        T['tab_trends'], T['tab_analysis'], T['tab_challenges'], T['tab_heatmap'], T['tab_records'], T['tab_log'],
        T['footer'],
        f"{tot_dist:,.0f} km".replace(",", " "), f"{tot_elev:,.0f} m".replace(",", " "),
        f"{tot_time:,.0f} h", f"{tot_cal:,.0f}", f"{efficiency:.1f}%", str(count),
        content
    )

if __name__ == "__main__":
    app.run_server(debug=True)
