"""Data normalization and calculations shared by the dashboard and tests."""
from pathlib import Path
import math
import re

import pandas as pd

DATA_FILE = Path(__file__).resolve().parent / "data" / "activities.csv"
NUMERIC_COLUMNS = ["distance_km", "elevation_m", "average_speed_kmh", "max_speed",
                   "moving_time_min", "elapsed_time", "kudos", "kilojoules",
                   "average_heartrate", "max_heartrate", "pr_count"]
RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}
RIDE_TYPES = {"Ride", "MountainBikeRide", "GravelRide", "VirtualRide", "EBikeRide"}
DAYPARTS = ("night", "morning", "afternoon", "evening")


def normalize_data(raw):
    df = raw.copy()
    for col in ["id", "name", "start_date", "type"]:
        if col not in df:
            df[col] = pd.Series(index=df.index, dtype="str")
    for col in NUMERIC_COLUMNS:
        values = df[col] if col in df else pd.Series(0, index=df.index)
        df[col] = pd.to_numeric(values, errors="coerce").replace([math.inf, -math.inf], 0).fillna(0).clip(lower=0)
    # The sync stores start_date_local. Preserve that wall-clock date, even when
    # older Strava exports include an offset. UTC conversion would shift days.
    df["start_date"] = pd.to_datetime(df["start_date"].map(
        lambda value: pd.to_datetime(str(value)[:19], errors="coerce")
    ))
    df = df.dropna(subset=["start_date"])
    df["type"] = df["type"].fillna("Other").astype(str).map(
        lambda value: re.sub(r"^root=", "", value).strip(" '\"<>") or "Other"
    )
    df["id"] = df["id"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
    df["name"] = df["name"].fillna("Activity")
    df = df.drop_duplicates(subset=["id", "start_date"])
    df["date"] = df["start_date"].dt.normalize()
    df["year"] = df["start_date"].dt.year
    df["day_of_year"] = df["start_date"].dt.dayofyear
    # Energy is an estimate: cycling mechanical kJ roughly approximate kcal;
    # otherwise use a fixed distance-based estimate rather than pretend precision.
    factors = df["type"].map(lambda kind: 75 if kind in RUN_TYPES else 25 if kind in RIDE_TYPES else 40)
    df["calories"] = df["distance_km"] * factors
    cycling_energy = df["type"].isin(RIDE_TYPES) & (df["kilojoules"] > 0)
    df.loc[cycling_energy, "calories"] = df.loc[cycling_energy, "kilojoules"]
    df["gradient"] = df["elevation_m"].div(df["distance_km"].replace(0, float("nan"))).fillna(0)
    return df.sort_values("start_date").reset_index(drop=True)


def load_data(path=DATA_FILE):
    try:
        return normalize_data(pd.read_csv(path, dtype={"id": str}))
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return normalize_data(pd.DataFrame())


def filter_data(df, start=None, end=None, types=None, query="", favorites=None, only_favorites=False):
    mask = pd.Series(True, index=df.index)
    if start:
        mask &= df["date"] >= pd.Timestamp(start).normalize()
    if end:
        mask &= df["date"] <= pd.Timestamp(end).normalize()
    if types:
        mask &= df["type"].isin(types)
    if query:
        mask &= df["name"].str.contains(query.strip(), case=False, regex=False, na=False)
    if only_favorites:
        mask &= df["id"].isin(favorites or [])
    return df.loc[mask].copy()


def summarize(df):
    moving = float(df["moving_time_min"].sum())
    elapsed = float(df["elapsed_time"].sum())  # Both columns are minutes.
    return {"distance": float(df["distance_km"].sum()),
            "elevation": float(df["elevation_m"].sum()), "time": moving / 60,
            "count": len(df), "calories": float(df["calories"].sum()),
            "efficiency": min(100, moving / elapsed * 100) if elapsed else 0,
            "active_days": int(df["date"].nunique())}


def streaks(df, today=None):
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    days = sorted(set(df["date"]))
    longest = run = 0
    previous = None
    for day in days:
        run = run + 1 if previous is not None and (day - previous).days == 1 else 1
        longest = max(longest, run)
        previous = day
    current = 0
    day_set = set(days)
    cursor = today if today in day_set else today - pd.Timedelta(days=1)
    while cursor in day_set:
        current += 1
        cursor -= pd.Timedelta(days=1)
    return current, longest


def comparison_range(start, end, mode="previous"):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if mode == "year":
        return start - pd.DateOffset(years=1), end - pd.DateOffset(years=1)
    return start - pd.Timedelta(days=(end - start).days + 1), start - pd.Timedelta(days=1)


def calendar_cells(year, df):
    """Use sequential Monday-based weeks; ISO week numbers merge year edges."""
    first, last = pd.Timestamp(year=year, month=1, day=1), pd.Timestamp(year=year, month=12, day=31)
    monday = first - pd.Timedelta(days=first.dayofweek)
    sunday = last + pd.Timedelta(days=6 - last.dayofweek)
    daily = df.groupby("date")["distance_km"].sum()
    return [{"date": day, "week": (day - monday).days // 7, "weekday": day.dayofweek,
             "distance": float(daily.get(day, 0)), "in_year": day.year == year}
            for day in pd.date_range(monday, sunday)]


def pace_label(row):
    distance = float(row["distance_km"])
    if row["type"] in RUN_TYPES and distance > 0:
        seconds = round(float(row["moving_time_min"]) / distance * 60)
        return f"{seconds // 60}:{seconds % 60:02d}", "min/km"
    if row["average_speed_kmh"] > 0:
        return f"{row['average_speed_kmh']:.1f}", "km/h"
    return "—", ""


def activity_time_profile(df):
    """Classify activities by their recorded local start time, not duration.

    Bands are [00,06), [06,12), [12,18), [18,24). Every activity is counted
    exactly once, including sessions that continue across a band boundary.
    """
    frame = df.copy()
    frame["start_hour"] = frame["start_date"].dt.hour
    frame["start_weekday"] = frame["start_date"].dt.dayofweek
    frame["daypart"] = frame["start_hour"].map(lambda hour: DAYPARTS[int(hour) // 6])
    count = len(frame)
    band_counts = frame.groupby("daypart").size().reindex(DAYPARTS, fill_value=0)
    hour_counts = frame.groupby("start_hour").size().reindex(range(24), fill_value=0)
    weekday_counts = frame.groupby("start_weekday").size().reindex(range(7), fill_value=0)
    grid = frame.groupby(["start_weekday", "start_hour"]).size().unstack(fill_value=0)
    grid = grid.reindex(index=range(7), columns=range(24), fill_value=0)
    bands = []
    for key in DAYPARTS:
        group = frame[frame["daypart"] == key]
        bands.append({"key": key, "count": int(band_counts[key]), "share": float(band_counts[key] / count * 100) if count else 0,
                      "distance": float(group["distance_km"].sum()), "hours": float(group["moving_time_min"].sum() / 60)})
    sports = []
    for kind, group in frame.groupby("type"):
        counts = group.groupby("daypart").size().reindex(DAYPARTS, fill_value=0)
        sports.append({"type": kind, "count": len(group), "bands": counts.astype(int).tolist(),
                       "dominant": counts[counts == counts.max()].index.tolist(), "share": float(counts.max() / len(group) * 100)})
    return {"count": count, "bands": bands, "hours": hour_counts.astype(int).tolist(), "grid": grid.astype(int).values.tolist(),
            "sports": sorted(sports, key=lambda sport: (-sport["count"], sport["type"])),
            "dominant": band_counts[band_counts == band_counts.max()].index.tolist() if count else [],
            "peak_hours": hour_counts[hour_counts == hour_counts.max()].index.astype(int).tolist() if count else [],
            "peak_weekdays": weekday_counts[weekday_counts == weekday_counts.max()].index.astype(int).tolist() if count else [],
            "peak_hour_count": int(hour_counts.max()) if count else 0}
