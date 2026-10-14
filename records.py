"""Personal bests from activity summaries, without inventing segment times."""
import pandas as pd
from analytics import RUN_TYPES, RIDE_TYPES


def activity_best(frame, column, key, label, unit, icon, digits=0, scale=1, lower_is_better=False, note=None, value_format="number"):
    eligible = frame[frame[column] > 0]
    if eligible.empty:
        return None
    # Prefer the newest activity when two measured values tie.
    row = eligible.sort_values([column, "start_date"], ascending=[lower_is_better, False]).iloc[0]
    return {"key": key, "label": label, "value": float(row[column]) * scale, "unit": unit,
            "icon": icon, "digits": digits, "format": value_format, "note": note,
            "activity_id": str(row["id"]), "name": row["name"], "sport": row["type"],
            "start": row["date"], "end": row["date"]}


def period_best(frame, frequency, column, operation, key, label, unit, icon, digits=0):
    grouped = frame.groupby(frame["date"].dt.to_period(frequency))
    values = grouped.size() if operation == "count" else grouped[column].nunique() if operation == "nunique" else grouped[column].sum()
    positive = values[values > 0]
    if positive.empty:
        return None
    maximum = positive.max()
    period = max(positive[positive == maximum].index)
    return {"key": key, "label": label, "value": float(maximum), "unit": unit,
            "icon": icon, "digits": digits, "format": "number", "note": None,
            "activity_id": None, "name": None, "sport": None,
            "start": period.start_time.normalize(), "end": period.end_time.normalize()}


def streak_best(frame):
    days = sorted(frame["date"].unique())
    best, run, start, best_start, best_end, previous = 0, 0, None, None, None, None
    for day in days:
        if previous is not None and (day - previous).days == 1:
            run += 1
        else:
            start, run = day, 1
        if run >= best:
            best, best_start, best_end = run, start, day
        previous = day
    if not best:
        return None
    return {"key": "period.streak", "label": ("Leghosszabb aktív sorozat", "Longest active streak"),
            "value": best, "unit": "days", "icon": "fire", "digits": 0, "format": "number", "note": None,
            "activity_id": None, "name": None, "sport": None, "start": best_start, "end": best_end}


def basic_records(frame, prefix):
    definitions = [
        ("distance_km", "distance", ("Leghosszabb táv", "Longest distance"), "km", "distance", 1, 1),
        ("elevation_m", "elevation", ("Legtöbb szintemelkedés", "Most elevation gain"), "m", "mountain", 0, 1),
        ("moving_time_min", "duration", ("Leghosszabb mozgási idő", "Longest moving time"), "h", "clock", 1, 1 / 60),
        ("kudos", "kudos", ("Legtöbb kudos", "Most kudos"), "kudos", "heart", 0, 1),
        ("pr_count", "segment-pr", ("Legtöbb Strava szegmens-PR", "Most Strava segment PRs"), "PR", "records", 0, 1),
    ]
    return [result for column, key, label, unit, icon, digits, scale in definitions
            if (result := activity_best(frame, column, f"{prefix}.{key}", label, unit, icon, digits, scale)) is not None]


def personal_records(frame):
    if frame.empty:
        return []
    sections = [{"key": "overall", "label": ("Egy edzés, nagy teljesítmény", "One activity, a big achievement"),
                 "icon": "records", "sport": None, "items": basic_records(frame, "overall")}]
    definitions = [
        ("D", "distance_km", "sum", "day-distance", ("Legtöbb kilométer egy nap", "Biggest distance in a day"), "km", "distance", 1),
        ("W-SUN", "distance_km", "sum", "week-distance", ("Legtöbb kilométer egy héten", "Biggest distance in a week"), "km", "trends", 1),
        ("M", "distance_km", "sum", "month-distance", ("Legtöbb kilométer egy hónapban", "Biggest distance in a month"), "km", "calendar", 1),
        ("D", "elevation_m", "sum", "day-elevation", ("Legtöbb szint egy nap", "Biggest elevation in a day"), "m", "mountain", 0),
        ("W-SUN", "elevation_m", "sum", "week-elevation", ("Legtöbb szint egy héten", "Biggest elevation in a week"), "m", "mountain", 0),
        ("D", "id", "count", "day-count", ("Legtöbb edzés egy nap", "Most activities in a day"), "activities", "activity", 0),
        ("M", "date", "nunique", "month-active", ("Legtöbb aktív nap egy hónapban", "Most active days in a month"), "days", "calendar", 0),
    ]
    period_records = [result for frequency, column, operation, key, label, unit, icon, digits in definitions
                      if (result := period_best(frame, frequency, column, operation, f"period.{key}", label, unit, icon, digits)) is not None]
    longest = streak_best(frame)
    if longest:
        period_records.append(longest)
    sections.append({"key": "period", "label": ("A következetesség rekordjai", "Consistency personal bests"),
                     "icon": "calendar", "sport": None, "items": period_records})
    # Keep each exact Strava sport separate, including road/trail/virtual types.
    priority = ["Run", "TrailRun", "Ride", "MountainBikeRide", "Walk", "Hike"]
    kinds = sorted(frame["type"].unique(), key=lambda kind: (priority.index(kind) if kind in priority else len(priority), kind))
    for kind in kinds:
        group = frame[frame["type"] == kind].copy()
        prefix = f"sport.{kind}"
        items = basic_records(group, prefix)
        is_run, is_ride = kind in RUN_TYPES, kind in RIDE_TYPES
        if is_run:
            group["pace_seconds"] = group["moving_time_min"] * 60 / group["distance_km"].replace(0, float("nan"))
            for threshold, label in [
                (5, ("Legjobb átlagtempó · 5+ km", "Best average pace · 5+ km")),
                (10, ("Legjobb átlagtempó · 10+ km", "Best average pace · 10+ km")),
                (21.0975, ("Legjobb átlagtempó · félmaraton+", "Best average pace · half marathon+")),
                (42.195, ("Legjobb átlagtempó · maraton+", "Best average pace · marathon+")),
            ]:
                eligible = group[(group["distance_km"] >= threshold) & (group["moving_time_min"] > 0)]
                result = activity_best(eligible, "pace_seconds", f"{prefix}.pace-{threshold}", label, "min/km", "run",
                                       lower_is_better=True, value_format="pace",
                                       note=("A teljes edzés átlagtempója", "Average pace of the complete activity"))
                if result:
                    items.append(result)
        else:
            threshold = 10 if is_ride else 2
            eligible = group[group["distance_km"] >= threshold]
            result = activity_best(eligible, "average_speed_kmh", f"{prefix}.speed", ("Leggyorsabb átlagsebesség", "Fastest average speed"), "km/h", "activity", 1,
                                   note=(f"Legalább {threshold} km-es edzés", f"Activity of at least {threshold} km"))
            if result:
                items.append(result)
        if is_run or is_ride:
            result = activity_best(group, "max_speed", f"{prefix}.peak-speed", ("Rögzített csúcssebesség", "Recorded peak speed"), "km/h", "activity", 1, 3.6)
            if result:
                items.append(result)
        if is_ride or kind in {"Hike", "Walk", "TrailRun"}:
            eligible = group[group["distance_km"] >= (10 if is_ride else 2)]
            result = activity_best(eligible, "gradient", f"{prefix}.climb-density", ("Legtöbb szint kilométerenként", "Most elevation per kilometer"), "m/km", "mountain", 1,
                                   note=("Szintemelkedés / teljes távolság", "Elevation gain / complete distance"))
            if result:
                items.append(result)
        if items:
            sections.append({"key": prefix, "label": None, "sport": kind,
                             "icon": "run" if is_run else "ride" if is_ride else "walk" if kind in {"Walk", "Hike"} else "activity", "items": items})
    return [section for section in sections if section["items"]]
