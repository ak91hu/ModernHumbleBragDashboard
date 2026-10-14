import pandas as pd
import plotly.graph_objects as go
from dash import dcc
from analytics import comparison_range
from ui import tr


def daypart_name(key, lang):
    return {"night": tr(lang, "Éjjel", "Night"), "morning": tr(lang, "Reggel", "Morning"),
            "afternoon": tr(lang, "Délután", "Afternoon"), "evening": tr(lang, "Este", "Evening")}[key]


def weekday_names(lang):
    return ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"] if lang == "HU" else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

COLORS = ["#31785b", "#b4d94c", "#70b8a4", "#e7b868", "#8e94c7", "#cf7c88"]
SPORT_COLORS = {"Run": "#31785b", "Ride": "#b4d94c", "Walk": "#70b8a4", "Hike": "#e7b868"}
METRICS = {"distance": ("distance_km", "km"), "time": ("moving_time_min", "min"), "elevation": ("elevation_m", "m")}


def sport_name(kind, lang):
    return {"Run": tr(lang, "Futás", "Running"), "Ride": tr(lang, "Kerékpár", "Cycling"),
            "Walk": tr(lang, "Séta", "Walking"), "Hike": tr(lang, "Túra", "Hiking"),
            "TrailRun": tr(lang, "Terepfutás", "Trail running"), "VirtualRide": tr(lang, "Virtuális kerékpár", "Virtual cycling"),
            "Swim": tr(lang, "Úszás", "Swimming"), "Workout": tr(lang, "Edzés", "Workout"),
            "WeightTraining": tr(lang, "Erősítés", "Weight training"), "Canoeing": tr(lang, "Kenuzás", "Canoeing")}.get(kind, kind)


def graph(fig, name):
    # Responsive Graph removes layout.height. Keep an explicit DOM height so
    # graphs mounted during page navigation cannot collapse to a zero-size box.
    height = int(fig.layout.height or 245)
    return dcc.Graph(id=f"chart-{name}", figure=fig, responsive=True,
                     config={"displayModeBar": False, "responsive": True}, className="chart",
                     style={"height": f"{height}px", "minHeight": f"{height}px", "width": "100%"})


def style_chart(fig, theme="light", height=245):
    ink, grid = ("#bbc8bf", "#2c3b33") if theme == "dark" else ("#7d8980", "#edf0e9")
    fig.update_layout(template="none", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font={"family": "DM Sans, Arial, sans-serif", "size": 11, "color": ink},
                      margin={"l": 45, "r": 16, "t": 25, "b": 36}, height=height,
                      hovermode="x unified", hoverlabel={"bgcolor": "#18392b", "font_color": "#fff"},
                      legend={"orientation": "h", "y": 1.16, "x": 0, "font_size": 11})
    fig.update_xaxes(showgrid=False, zeroline=False, ticklen=0, automargin=True)
    fig.update_yaxes(gridcolor=grid, zeroline=False, ticklen=0, automargin=True)
    return fig


def cumulative(dff, previous, start, end, metric, lang, theme):
    column, unit = METRICS[metric]
    dates = pd.date_range(start, end)
    values = dff.groupby("date")[column].sum().reindex(dates, fill_value=0).cumsum()
    fig = go.Figure()
    x = dates.strftime("%Y-%m-%d").tolist()
    fig.add_trace(go.Scatter(x=x, y=values.tolist(), mode="lines", name=tr(lang, "Kiválasztott időszak", "Selected period"),
                             line={"color": "#438a64", "width": 3, "shape": "hv"}, fill="tozeroy", fillcolor="rgba(84,155,103,.12)",
                             hovertemplate=f"%{{y:,.1f}} {unit}<extra></extra>"))
    if not previous.empty:
        pstart, pend = comparison_range(start, end, "year" if pd.Timestamp(start).month == 1 and pd.Timestamp(start).day == 1 else "previous")
        # Align leap-year comparisons by calendar date rather than shifting all
        # dates after February 29 by a day.
        previous_daily = previous.groupby("date")[column].sum().reindex(pd.date_range(pstart, pend), fill_value=0).cumsum()
        aligned = [day - pd.DateOffset(years=1) for day in dates] if pd.Timestamp(start).month == 1 and pd.Timestamp(start).day == 1 else pd.date_range(pstart, pend)
        fig.add_trace(go.Scatter(x=x, y=previous_daily.reindex(aligned).tolist(), mode="lines", name=tr(lang, "Összehasonlítás", "Comparison"),
                                 line={"color": "#a7b59c", "width": 2, "dash": "dot"}, hovertemplate=f"%{{y:,.1f}} {unit}<extra></extra>"))
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="date")
    fig.update_yaxes(ticksuffix=f" {unit}")
    return style_chart(fig, theme, 248)


def weekly(dff, start, end, metric, lang, theme):
    column, unit = METRICS[metric]
    daily = dff.groupby("date")[column].sum().reindex(pd.date_range(start, end), fill_value=0)
    values = daily.resample("W-SUN").sum().tail(12)
    fig = go.Figure(go.Bar(x=values.index.strftime("%Y-%m-%d").tolist(), y=values.tolist(), marker={"color": ["#b7d963" if i == len(values)-1 else "#397b5c" for i in range(len(values))], "cornerradius": 4},
                           hovertemplate=f"%{{x|%Y.%m.%d.}}<br>%{{y:,.1f}} {unit}<extra></extra>"))
    if len(values) and values.mean() > 0:
        fig.add_hline(y=values.mean(), line_dash="dot", line_color="#a9b6a4")
    fig.update_layout(bargap=.45)
    fig.update_xaxes(type="date")
    fig.update_yaxes(ticksuffix=f" {unit}")
    return style_chart(fig, theme, 210)


def sports(dff, lang, theme):
    mix = dff.groupby("type")["moving_time_min"].sum().sort_values(ascending=False)
    fig = go.Figure(go.Pie(labels=[sport_name(kind, lang) for kind in mix.index], values=mix.tolist(),
                           hole=.77, sort=False, textinfo="none", marker={"colors": [SPORT_COLORS.get(k, COLORS[i % len(COLORS)]) for i, k in enumerate(mix.index)], "line": {"width": 4, "color": "#18271f" if theme == "dark" else "#ffffff"}},
                           hovertemplate="%{label}<br>%{value:.0f} min · %{percent}<extra></extra>"))
    fig.update_layout(showlegend=False, annotations=[{"text": f"<b>{len(dff)}</b>", "x": .5, "y": .55, "showarrow": False, "font": {"size": 35, "color": "#e8eee6" if theme == "dark" else "#20362a"}},
                                                    {"text": tr(lang, "EDZÉS", "ACTIVITIES"), "x": .5, "y": .35, "showarrow": False, "font_size": 10}])
    return style_chart(fig, theme, 205)


def scatter(dff, lang, theme):
    fig = go.Figure()
    for i, (kind, group) in enumerate(dff.groupby("type")):
        fig.add_trace(go.Scatter(x=group["distance_km"].tolist(), y=group["average_speed_kmh"].tolist(), mode="markers", name=sport_name(kind, lang), text=group["name"].tolist(),
                                marker={"size": (group["elevation_m"].clip(0, 600) / 35 + 7).tolist(), "color": SPORT_COLORS.get(kind, COLORS[i % len(COLORS)]), "opacity": .7},
                                hovertemplate="%{text}<br>%{x:.1f} km · %{y:.1f} km/h<extra></extra>"))
    fig.update_xaxes(title="km")
    fig.update_yaxes(title="km/h")
    fig = style_chart(fig, theme)
    fig.update_layout(hovermode="closest")
    return fig


def heart_rate(dff, lang, theme):
    measured = dff[dff["average_heartrate"] > 0]
    if measured.empty:
        return None
    fig = go.Figure()
    for i, (kind, group) in enumerate(measured.groupby("type")):
        fig.add_trace(go.Box(y=group["average_heartrate"].tolist(), name=sport_name(kind, lang), marker_color=COLORS[i % len(COLORS)], boxpoints="all", jitter=.3, pointpos=0))
    fig.update_layout(showlegend=False, hovermode="closest")
    fig.update_yaxes(ticksuffix=" bpm")
    fig = style_chart(fig, theme)
    fig.update_layout(hovermode="closest")
    return fig


def routine(dff, lang, theme):
    values = dff.groupby(dff["start_date"].dt.dayofweek)["moving_time_min"].sum().reindex(range(7), fill_value=0) / 60
    labels = ["H", "K", "Sze", "Cs", "P", "Szo", "V"] if lang == "HU" else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    fig = go.Figure(go.Bar(x=labels, y=values.tolist(), marker_color="#397b5c", marker_cornerradius=6, hovertemplate="%{x}: %{y:.1f} h<extra></extra>"))
    fig.update_xaxes(type="category")
    fig.update_yaxes(ticksuffix=" h")
    return style_chart(fig, theme, 210)


def start_hours(profile, lang, theme):
    fig = go.Figure(go.Bar(x=list(range(24)), y=profile["hours"],
                           marker={"color": ["#b7d963" if hour in profile["peak_hours"] else "#397b5c" for hour in range(24)], "cornerradius": 4},
                           hovertemplate="%{x:02d}:00–%{x:02d}:59<br>%{y} " + tr(lang, "edzés", "activities") + "<extra></extra>"))
    fig.update_xaxes(type="linear", tickmode="array", tickvals=list(range(0, 24, 3)), ticktext=[f"{hour:02d}:00" for hour in range(0, 24, 3)], range=[-.5, 23.5])
    fig.update_yaxes(title=tr(lang, "Edzések", "Activities"), rangemode="tozero", tickformat="d")
    fig.update_layout(bargap=.25)
    return style_chart(fig, theme, 245)


def daypart_sports(profile, lang, theme):
    fig = go.Figure()
    labels = [daypart_name(band["key"], lang) for band in profile["bands"]]
    for index, sport in enumerate(profile["sports"]):
        fig.add_trace(go.Bar(x=labels, y=sport["bands"], name=sport_name(sport["type"], lang),
                             marker_color=SPORT_COLORS.get(sport["type"], COLORS[index % len(COLORS)]),
                             hovertemplate="%{x}<br>%{y} " + tr(lang, "edzés", "activities") + "<extra>%{fullData.name}</extra>"))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=labels)
    fig.update_yaxes(title=tr(lang, "Edzések", "Activities"), rangemode="tozero", tickformat="d")
    fig = style_chart(fig, theme, 245)
    fig.update_layout(barmode="stack", bargap=.5, legend={"y": 1.23, "font_size": 9})
    return fig


def weekday_hours(profile, lang, theme):
    fig = go.Figure(go.Heatmap(x=list(range(24)), y=weekday_names(lang), z=profile["grid"],
                               colorscale=[[0, "#273a2c" if theme == "dark" else "#edf2e7"], [.35, "#c3d99d"], [.7, "#75a563"], [1, "#31754d"]],
                               zmin=0, zmax=max(1, max((max(row) for row in profile["grid"]), default=0)), xgap=3, ygap=3,
                               colorbar={"title": tr(lang, "Edzés", "Activities"), "thickness": 9, "len": .8, "tickformat": "d"},
                               hovertemplate="%{y} · %{x:02d}:00–%{x:02d}:59<br>%{z} " + tr(lang, "edzés", "activities") + "<extra></extra>"))
    fig = style_chart(fig, theme, 285)
    fig.update_layout(hovermode="closest", margin={"l": 85, "r": 55, "t": 10, "b": 35})
    fig.update_xaxes(type="linear", tickmode="array", tickvals=list(range(0, 24, 2)), ticktext=[f"{hour:02d}:00" for hour in range(0, 24, 2)], range=[-.5, 23.5])
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig
