"""Incremental Strava sync. Publish only a complete, successful download."""
import argparse
from datetime import timedelta
import logging
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from stravalib.client import Client

from export_metadata import write_export_metadata

ACTIVITIES_FILE = Path(__file__).resolve().parent.parent / "data" / "activities.csv"
COLUMNS = ["id", "name", "start_date", "distance_km", "moving_time_min", "elapsed_time", "elevation_m", "type", "average_speed_kmh", "max_speed", "pr_count", "kudos", "kilojoules", "average_heartrate", "max_heartrate"]


def get_client():
    client = Client()
    token = client.refresh_access_token(client_id=int(os.environ["STRAVA_CLIENT_ID"]),
                                        client_secret=os.environ["STRAVA_CLIENT_SECRET"],
                                        refresh_token=os.environ["STRAVA_REFRESH_TOKEN"])
    client.access_token = token["access_token"]
    return client


def get_safe_value(value):
    if value is None:
        return 0
    if hasattr(value, "total_seconds"):
        return value.total_seconds()
    for attribute in ["magnitude", "num"]:
        if hasattr(value, attribute):
            return float(getattr(value, attribute))
    return float(value)


def activity_record(activity):
    kind = getattr(activity.type, "root", activity.type)
    return {"id": str(activity.id), "name": activity.name, "start_date": activity.start_date_local,
            "distance_km": get_safe_value(activity.distance) / 1000,
            "moving_time_min": get_safe_value(activity.moving_time) / 60,
            "elapsed_time": get_safe_value(activity.elapsed_time) / 60,
            "elevation_m": get_safe_value(activity.total_elevation_gain), "type": str(kind),
            "average_speed_kmh": get_safe_value(activity.average_speed) * 3.6,
            "max_speed": get_safe_value(activity.max_speed),
            "pr_count": getattr(activity, "pr_count", 0) or 0,
            "kudos": getattr(activity, "kudos_count", 0) or 0,
            "kilojoules": get_safe_value(getattr(activity, "kilojoules", None)),
            "average_heartrate": get_safe_value(getattr(activity, "average_heartrate", None)),
            "max_heartrate": get_safe_value(getattr(activity, "max_heartrate", None))}


def update_activities(client=None, full=False, path=ACTIVITIES_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = pd.read_csv(path, dtype={"id": str}) if path.exists() and path.stat().st_size else pd.DataFrame(columns=COLUMNS)
    after = None
    if not full and not existing.empty:
        latest = pd.to_datetime(existing["start_date"], utc=True, errors="coerce").max()
        if pd.notna(latest):
            after = latest.to_pydatetime() - timedelta(days=7)
    client = client if client is not None else get_client()
    logging.info("Fetching %s activities", "all" if full else "new and recent")
    # Generator/network/serialization failures propagate before the existing
    # file is touched. Recent rows are fetched again to refresh kudos and edits.
    records = [activity_record(activity) for activity in client.get_activities(after=after, limit=None)]
    if not records and not existing.empty:
        if full:
            raise RuntimeError("An empty full-sync response would erase existing data; keeping the previous file.")
        write_export_metadata(path)
        logging.info("No updates; retained %s activities", len(existing))
        return existing
    downloaded = pd.DataFrame(records, columns=COLUMNS)
    merged = downloaded if full else pd.concat([existing, downloaded], ignore_index=True)
    merged = merged.drop_duplicates(subset="id", keep="last")
    merged = merged.sort_values("start_date", ascending=False, key=lambda values: pd.to_datetime(values, utc=True, errors="coerce"))
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", dir=path.parent, encoding="utf-8", newline="", delete=False) as handle:
            temporary_path = Path(handle.name)
            merged.to_csv(handle, index=False)
        os.replace(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
    write_export_metadata(path)
    logging.info("Saved %s activities (%s fetched)", len(merged), len(records))
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Refresh the full history instead of only recent activities")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    update_activities(full=args.full)
