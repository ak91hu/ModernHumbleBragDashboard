"""Dashboard views. All values come from the retained Strava dataset."""
import math
import pandas as pd
from dash import html
from analytics import RUN_TYPES, RIDE_TYPES, activity_time_profile, calendar_cells, pace_label, streaks, summarize
import charts
from charts import COLORS, SPORT_COLORS, graph, sport_name
from ui import icon, number, panel, stat, tr
from records import personal_records


def time_brief(dff, lang):
    profile = activity_time_profile(dff)
    if not profile["count"]:
        return None
    dominant = " / ".join(charts.daypart_name(key, lang) for key in profile["dominant"])
    hours = ", ".join(f"{hour:02d}:00" for hour in profile["peak_hours"])
    share = max(band["share"] for band in profile["bands"])
    return html.Div([html.Div(icon("moon" if profile["dominant"][0] in {"night", "evening"} else "sun"), className="time-brief-icon"),
                     html.Div([html.Strong(tr(lang, "Jellemző napszak: ", "Typical time of day: ") + dominant),
                               html.P(f"{share:.0f}% " + tr(lang, "edzés ebben a napszakban", "of activities in this daypart") + (tr(lang, " (napszakonként)", " (each)") if len(profile["dominant"]) > 1 else "") + " · " + tr(lang, "Leggyakoribb kezdési óra: ", "Most common start hour: ") + hours)]),
                     html.Span(tr(lang, "Részletek a Trendek és elemzés nézetben", "Details in Trends & analysis"), className="time-brief-note")], className="time-brief")


def time_analysis(dff, lang, theme):
    profile = activity_time_profile(dff)
    cards = []
    for index, band in enumerate(profile["bands"]):
        key = band["key"]
        cards.append(html.Div([html.Div([icon("moon" if key in {"night", "evening"} else "sun"), html.Span(charts.daypart_name(key, lang)), html.Small(f"{index*6:02d}:00–{(index+1)*6-1:02d}:59")], className="daypart-heading"),
                               html.Div([html.Strong(str(band["count"])), html.Span(tr(lang, "edzés", "activities")), html.B(f"{band['share']:.0f}%")], className="daypart-value"),
                               html.Div(html.Div(style={"width": f"{band['share']}%"}), className="progress-track"),
                               html.Small(f"{number(band['distance'],1)} km · {number(band['hours'],1)} h", className="daypart-totals")], className="daypart-card" + (" dominant" if key in profile["dominant"] else "")))
    sports = []
    for sport in profile["sports"]:
        names = " / ".join(charts.daypart_name(key, lang) for key in sport["dominant"])
        sports.append(html.Div([html.Span([icon(sport_icon(sport["type"])), sport_name(sport["type"],lang)]), html.Strong(names),
                                html.Small(f"{sport['share']:.0f}%" + (tr(lang, " / napszak", " / daypart") if len(sport["dominant"]) > 1 else "") + f" · {sport['count']} " + tr(lang, "edzés", "activities"))], className="sport-time-row"))
    return html.Div([
        panel(tr(lang, "Mikor indul a mozgás?", "When does your movement start?"),
              tr(lang, "A szűrt edzések rögzített helyi kezdési ideje alapján. Minden edzés egyszer szerepel.", "Based on recorded local start times of filtered activities. Every activity is counted once."),
              [html.Div(cards, className="daypart-grid"), html.Div(sports, className="sport-time-list")]),
        html.Div([panel(tr(lang, "A kedvenc óráid", "Your favorite hours"), tr(lang, "Edzéskezdések óránként · a világos oszlopok a leggyakoribb órák", "Activity starts by hour · lighter bars mark the most frequent hours"), graph(charts.start_hours(profile,lang,theme),"start-hours")),
                  panel(tr(lang, "Napszakok és sportágak", "Dayparts & sports"), tr(lang, "Edzésdarabszám sportáganként", "Activity counts by sport"), graph(charts.daypart_sports(profile,lang,theme),"daypart-sports"))], className="grid-equal"),
        panel(tr(lang, "A heted, óráról órára", "Your week, hour by hour"), tr(lang, "A sötétebb cellák több edzéskezdést jelentenek. Mutass egy cellára a részletekhez.", "Darker cells mean more activity starts. Hover over a cell for details."), graph(charts.weekday_hours(profile,lang,theme),"weekday-hours")),
    ])


def sport_icon(kind):
    return "run" if kind in RUN_TYPES else "ride" if kind in RIDE_TYPES else "walk" if kind in {"Walk", "Hike"} else "activity"


def empty_state(lang):
    return html.Div([icon("search"), html.H3(tr(lang, "Itt most nincs edzés", "No activities here yet")),
                     html.P(tr(lang, "Válassz másik időszakot vagy sportágat, illetve töröld a keresést.", "Try another date range or sport, or clear your search."))], className="empty-state")


def activity_rows(dff, lang, favorites=None, slot="main"):
    rows = []
    for _, row in dff.iterrows():
        pace, unit = pace_label(row)
        saved = row["id"] in (favorites or [])
        rows.append(html.Div([
            html.Div(icon(sport_icon(row["type"])), className=f"sport-bubble sport-{sport_icon(row['type'])}"),
            html.Button([html.Strong(row["name"]), html.Small(f"{row['start_date']:%Y.%m.%d.} · {sport_name(row['type'], lang)}")], id={"kind": "detail", "id": row["id"], "slot": slot}, className="activity-name"),
            html.Div([html.Strong(number(row["distance_km"], 1)), html.Small("km")], className="activity-number"),
            html.Div([html.Strong(number(row["moving_time_min"])), html.Small("min")], className="activity-number time-col"),
            html.Div([html.Strong(pace), html.Small(unit)], className="activity-number pace-col"),
            html.Div([html.Strong(number(row["elevation_m"])), html.Small("m ↗")], className="activity-number elevation-col"),
            html.Button(icon("star"), id={"kind": "favorite", "id": row["id"], "slot": slot}, className="icon-button favorite" + (" selected" if saved else ""),
                        title=tr(lang, "Kedvenc váltása", "Toggle favorite"), **{"aria-label": tr(lang, "Kedvenc váltása", "Toggle favorite"), "aria-pressed": str(saved).lower()})
        ], className="activity-row"))
    return html.Div(rows, className="activity-list") if rows else empty_state(lang)


def goal_progress(all_data, goals, lang):
    goals = goals or {}
    year = int(goals.get("year", pd.Timestamp.today().year))
    totals = summarize(all_data[all_data["year"] == year])
    rows = []
    for key, hu, en, unit, default, ico in [("distance", "Távolság", "Distance", "km", 2000, "distance"), ("elevation", "Szintemelkedés", "Elevation", "m", 15000, "mountain"), ("count", "Edzések", "Activities", "", 300, "activity")]:
        target = max(1, float(goals.get(key, default)))
        percent = min(100, totals[key] / target * 100)
        rows.append(html.Div([html.Div([html.Span([icon(ico), tr(lang, hu, en)]), html.Strong(f"{percent:.0f}%")], className="goal-label"),
                              html.Div(html.Div(style={"width": f"{percent}%"}), className="progress-track", role="progressbar", **{"aria-valuenow": round(percent), "aria-valuemin": 0, "aria-valuemax": 100, "aria-label": tr(lang, hu, en)}),
                              html.Small(f"{number(totals[key])} / {number(target)} {unit}")], className="goal-row"))
    return html.Div([html.Div([html.Span(str(year), className="year-tag"), html.Span(tr(lang, "Minden sportág · éves célok", "All sports · annual goals"), className="muted small")], className="goal-year"), *rows])


def overview(dff, previous, start, end, metric, lang, theme, all_data, goals, favorites):
    s, p = summarize(dff), summarize(previous)
    _, longest = streaks(dff)
    delta = (s["distance"] - p["distance"]) / p["distance"] * 100 if p["distance"] else None
    hero = html.Div([
        html.Div([html.Span([html.Span(className="live-dot"), tr(lang, "A TE MOZGÁSOD. A TE TÖRTÉNETED.", "YOUR MOVEMENT. YOUR STORY.")], className="hero-eyebrow"),
                  html.H2([tr(lang, "A kis lépésekből", "Small steps."), html.Br(), html.Span(tr(lang, "nagy dolgok lesznek.", "Big things ahead."))]),
                  html.P(tr(lang, "Minden kilométer egy újabb ok a büszkeségre.", "Every kilometer is another reason to be proud.")),
                  html.Div([html.Span([icon("fire"), f"{longest} ", tr(lang, "napos rekord sorozat", "day best streak")]), html.Span([icon("calendar"), f"{s['active_days']} ", tr(lang, "aktív nap", "active days")])], className="hero-pills")], className="hero-copy"),
        html.Div([html.Img(src="/assets/summit.svg", className="hero-art", alt=""), html.Div([html.Span(tr(lang, "MEGTETT TÁVOLSÁG", "DISTANCE COVERED")), html.Strong(number(s["distance"])), html.Small(tr(lang, "kilométer", "kilometers"))], className="hero-distance")], className="hero-visual")
    ], className="hero")
    stats = html.Div([
        stat(tr(lang, "Távolság", "Total distance"), number(s["distance"], 1), "km", "distance", tr(lang, "az előző időszakhoz", "vs. comparison") if delta is not None else tr(lang, "a kiválasztott időszakban", "in the selected period"), f"{'↗' if delta >= 0 else '↘'} {abs(delta):.1f}%" if delta is not None else None),
        stat(tr(lang, "Szintemelkedés", "Elevation gain"), number(s["elevation"]), "m", "mountain", f"{s['elevation']/1014:.1f} × Kékes-tető"),
        stat(tr(lang, "Mozgásban töltött idő", "Moving time"), number(s["time"], 1), "h", "clock", f"{s['efficiency']:.0f}% " + tr(lang, "mozgási arány", "moving efficiency")),
        stat(tr(lang, "Edzések", "Activities"), str(s["count"]), "", "activity", f"{s['active_days']} " + tr(lang, "aktív nap", "active days")),
    ], className="stats-grid")
    mix = dff.groupby("type")["moving_time_min"].sum().sort_values(ascending=False)
    legend = html.Div([html.Div([html.Span(style={"background": SPORT_COLORS.get(kind, COLORS[i % len(COLORS)])}, className="legend-dot"), html.Span(sport_name(kind, lang)), html.Strong(f"{value/mix.sum()*100:.0f}%" if mix.sum() else "0%")], className="sport-legend-row") for i, (kind, value) in enumerate(mix.items())], className="sport-legend")
    pstart, pend = charts.comparison_range(start, end, "year" if pd.Timestamp(start).month == 1 and pd.Timestamp(start).day == 1 else "previous")
    comparison_note = tr(lang, "Összehasonlítás: ", "Compared with: ") + f"{pstart:%Y.%m.%d.} – {pend:%Y.%m.%d.}"
    cumulative = panel(tr(lang, "Kilométerről kilométerre", "One kilometer at a time") if metric == "distance" else tr(lang, "Így épül a teljesítményed", "Your progress, adding up"), comparison_note,
                       [html.Div([html.Span([html.I(className="legend-dot green"), tr(lang, "Kiválasztott időszak", "Selected period")]), html.Span([html.I(className="legend-dot pale"), tr(lang, "Összehasonlítás", "Comparison")])], className="chart-legend"), graph(charts.cumulative(dff, previous, start, end, metric, lang, theme), "cumulative")])
    return html.Div([hero, stats, time_brief(dff, lang),
        html.Div([cumulative, panel(tr(lang, "A mozgásod színei", "Your movement mix"), tr(lang, "Mozgási idő sportáganként", "Moving time by sport"), [graph(charts.sports(dff, lang, theme), "sports"), legend])], className="grid-main"),
        html.Div([panel(tr(lang, "Heti lendület", "Weekly momentum"), tr(lang, "Az időszak utolsó 12 hete · pontozott vonal: átlag", "Last 12 weeks of the period · dotted line: average"), graph(charts.weekly(dff, start, end, metric, lang, theme), "weekly")),
                  panel(tr(lang, "A következő mérföldkő", "Your next milestone"), tr(lang, "Egy lépéssel közelebb, minden nap", "A little closer, every day"), goal_progress(all_data, goals, lang), extra=html.Button(icon("arrow"), id="open-goals-card", className="icon-button", title=tr(lang, "Célok szerkesztése", "Edit goals"), **{"aria-label": tr(lang, "Célok szerkesztése", "Edit goals")}))], className="grid-main"),
        panel(tr(lang, "Legutóbbi mozdulatok", "Your latest moves"), tr(lang, "A számok mögött ott az élmény", "The experiences behind the numbers"), activity_rows(dff.sort_values("start_date", ascending=False).head(4), lang, favorites), extra=html.Button([tr(lang, "Teljes napló", "View all"), icon("arrow")], id="view-all", className="text-button")),
    ])


def trends(dff, previous, start, end, metric, lang, theme):
    heart = charts.heart_rate(dff, lang, theme)
    return html.Div([
        panel(tr(lang, "Haladás, perspektívában", "Progress in perspective"), tr(lang, "Évkezdés esetén előző év, egyébként az előző azonos hosszú időszak", "Compared with the previous year for Jan 1 starts, otherwise the preceding equal-length period"), graph(charts.cumulative(dff, previous, start, end, metric, lang, theme), "trend-cumulative")),
        html.Div([panel(tr(lang, "Heti edzésmennyiség", "Weekly volume"), tr(lang, "Az időszak utolsó 12 hete", "Last 12 weeks of the period"), graph(charts.weekly(dff, start, end, metric, lang, theme), "trend-weekly")), panel(tr(lang, "Mikor mozdulsz?", "When do you move?"), tr(lang, "Mozgási idő a hét napjai szerint", "Moving time by day of the week"), graph(charts.routine(dff, lang, theme), "routine"))], className="grid-equal"),
        time_analysis(dff, lang, theme),
        html.Div([panel(tr(lang, "Táv és sebesség", "Distance & speed"), tr(lang, "A nagyobb pont több szintemelkedést jelent", "Larger dots represent more elevation gain"), graph(charts.scatter(dff, lang, theme), "scatter")),
                  panel(tr(lang, "Pulzuseloszlás", "Heart rate distribution"), tr(lang, "Edzésenkénti átlagpulzus · csak mért adatok", "Average heart rate per activity · measured values only"), graph(heart, "heart") if heart is not None else html.P(tr(lang, "Ebben az időszakban nincs pulzusadat.", "No heart rate data for this period."), className="empty-state"))], className="grid-equal")])


def heatmap(dff, year, lang):
    cells = calendar_cells(year, dff)
    peak = max([c["distance"] for c in cells], default=0)
    days = ["H", "K", "Sze", "Cs", "P", "Szo", "V"] if lang == "HU" else ["M", "T", "W", "T", "F", "S", "S"]
    squares = []
    for cell in cells:
        intensity = 0 if not cell["distance"] else min(4, max(1, math.ceil(cell["distance"] / max(peak, 1) * 4)))
        day = cell["date"].strftime("%Y-%m-%d")
        squares.append(html.Button(className=f"heat-cell level-{intensity}" + (" outside" if not cell["in_year"] else ""), title=f"{day} · {cell['distance']:.1f} km", id={"kind": "day", "date": day, "year": int(year)}, disabled=not cell["in_year"], **{"aria-label": f"{day}: {cell['distance']:.1f} km"}))
    months = ["jan", "feb", "márc", "ápr", "máj", "jún", "júl", "aug", "szept", "okt", "nov", "dec"] if lang == "HU" else ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return html.Div([html.Div([html.Div([html.Span(month) for month in months], className="heat-months"), html.Div([html.Div([html.Span(d) for d in days], className="heat-days"), html.Div(squares, className="heat-grid")], className="heat-body")], className="heat-scroll"),
                     html.Div([html.Span(tr(lang, "Kattints egy napra az edzésekhez", "Click a day to see its activities")), html.Div([tr(lang, "Kevesebb", "Less"), *[html.Span(className=f"heat-sample level-{i}") for i in range(5)], tr(lang, "Több", "More")])], className="heat-legend")], className="heatmap")


def calendar_view(dff, lang):
    current, longest = streaks(dff)
    return html.Div([html.Div([stat(tr(lang, "Aktív napok", "Active days"), str(dff["date"].nunique()), "", "calendar", tr(lang, "a kiválasztott időszakban", "in the selected period")),
                              stat(tr(lang, "Leghosszabb sorozat", "Best streak"), str(longest), tr(lang, "nap", "days"), "fire", tr(lang, "egymást követő aktív nap", "consecutive active days")),
                              stat(tr(lang, "Jelenlegi sorozat", "Current streak"), str(current), tr(lang, "nap", "days"), "activity", tr(lang, "a mai vagy tegnapi napig", "ending today or yesterday"))], className="stats-grid three"),
                     *[panel(str(year), tr(lang, "A szűrt edzések napi távolsága", "Daily distance from filtered activities"), heatmap(dff[dff["year"] == year], year, lang)) for year in sorted(dff["year"].unique(), reverse=True)]])


def goals_view(dff, all_data, goals, lang):
    totals = summarize(dff)
    mountains = []
    for name, height, caption in [("Kékes-tető", 1014, tr(lang, "Magyarország teteje", "The top of Hungary")), ("Mont Blanc", 4808, tr(lang, "Az Alpok csúcsa", "The roof of the Alps")), ("Everest", 8848, tr(lang, "A világ teteje", "The top of the world"))]:
        value = totals["elevation"] / height
        mountains.append(html.Div([html.Img(src="/assets/summit.svg", alt="", className="mountain-art"), html.Span(number(height) + " m", className="mountain-altitude"), html.H3(name), html.P(caption), html.Strong(f"{value:.1f} ×"), html.Div(html.Div(style={"width": f"{min(value*100,100)}%"}), className="progress-track"), html.Small(tr(lang, "A szűrt időszak összes szintemelkedése", "Total elevation in the filtered period"))], className="mountain-card"))
    foods = [("🍕", tr(lang, "pizzaszelet", "pizza slices"), 285), ("🍺", tr(lang, "korsó sör", "pints of beer"), 215), ("🍔", tr(lang, "hamburger", "burgers"), 550), ("🍩", tr(lang, "fánk", "donuts"), 250)]
    return html.Div([panel(tr(lang, "A te céljaid, a te tempódban", "Your goals, at your pace"), tr(lang, "A célok ebben a böngészőben mentődnek", "Goals are saved in this browser"), goal_progress(all_data, goals, lang), extra=html.Button([tr(lang, "Célok beállítása", "Edit goals"), icon("arrow")], id="open-goals-card", className="primary-button")),
                     html.Div(mountains, className="mountain-grid"),
                     panel(tr(lang, "Egy kis humblebrag", "A little humblebrag"), tr(lang, "Játékos energiaátváltás · nem táplálkozási ajánlás", "A playful energy conversion · not dietary advice"),
                           [html.Div([html.Div([html.Span(emoji), html.Strong(number(totals["calories"] / kcal)), html.Small(label)], className="food-card") for emoji, label, kcal in foods], className="food-grid"), html.P(tr(lang, "Becsült energia: ", "Estimated energy: ") + number(totals["calories"]) + " kcal · " + tr(lang, "Távolságon és kerékpáros munkán alapuló közelítés, nem mért kalória.", "An approximation based on distance and cycling work, not measured calories."), className="energy-note")])])


def records_view(dff, lang):
    sections = personal_records(dff)
    if not sections:
        return empty_state(lang)
    count = sum(len(section["items"]) for section in sections)
    output = [html.Div([html.Div([icon("records"), html.Strong(str(count))], className="record-count"),
                        html.Div([html.H3(tr(lang, "Több ok a büszkeségre.", "More reasons to be proud.")),
                                  html.P(tr(lang, "A kiválasztott időszak és sportágak rekordjai. Az összes eddigi rekordhoz válaszd az Összes időszakot.", "Records for the selected dates and sports. Select All time to see your lifetime bests."))])], className="records-intro")]
    for section in sections:
        cards = []
        for record in section["items"]:
            if record["format"] == "pace":
                seconds = round(record["value"])
                value = f"{seconds // 60}:{seconds % 60:02d}"
            else:
                value = number(record["value"], record["digits"])
            unit = {"days": tr(lang, "nap", "days"), "activities": tr(lang, "edzés", "activities")}.get(record["unit"], record["unit"])
            if record["activity_id"]:
                link = html.Button(record["name"], id={"kind": "detail", "id": record["activity_id"], "slot": record["key"]}, className="text-button")
                source = f"{record['start']:%Y.%m.%d.} · {sport_name(record['sport'], lang)}"
            else:
                source = f"{record['start']:%Y.%m.%d.}" + (f" – {record['end']:%Y.%m.%d.}" if record["end"] != record["start"] else "")
                link = html.Button([tr(lang, "Az edzések megtekintése", "View these activities"), icon("arrow")],
                                   id={"kind": "period-detail", "start": record["start"].strftime("%Y-%m-%d"), "end": record["end"].strftime("%Y-%m-%d"), "key": record["key"]}, className="text-button")
            cards.append(html.Div([icon(record["icon"]), html.Small(tr(lang, *record["label"])), html.H2([value, html.Span(" " + unit)]),
                                   html.Div(tr(lang, *record["note"]) if record["note"] else tr(lang, "A szűrt edzések alapján", "Based on filtered activities"), className="record-note"),
                                   link, html.P(source)], className="record-card"))
        title = sport_name(section["sport"], lang) if section["sport"] else tr(lang, *section["label"])
        output.append(html.Section([html.Div([html.Span([icon(section["icon"]), html.H3(title)]), html.Small(f"{len(cards)} " + tr(lang, "rekord", "records"))], className="record-section-heading"),
                                    html.Div(cards, className="records-grid")], className="record-section"))
    output.append(html.P(tr(lang, "A futótempó-rekordok a teljes edzés átlagából számolódnak. Az összesítő CSV nem tartalmaz hiteles 5 km-es vagy 10 km-es részidőket.", "Running pace records use the complete activity average. The summary CSV does not contain verified 5 km or 10 km splits."), className="records-method"))
    return html.Div(output)
