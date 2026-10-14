"""Persist successful Strava export times alongside the matching CSV."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile


def metadata_path(csv_path):
    return Path(csv_path).with_suffix(".export.json")


def csv_digest(csv_path):
    return hashlib.sha256(Path(csv_path).read_bytes()).hexdigest()


def write_export_metadata(csv_path, exported_at=None, source_url=None):
    timestamp = exported_at or datetime.now(timezone.utc)
    metadata = {"exported_at": timestamp.astimezone(timezone.utc).isoformat(timespec="seconds"),
                "csv_sha256": csv_digest(csv_path)}
    if source_url:
        metadata["source_url"] = source_url
    path = metadata_path(csv_path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=path.parent,
                                         encoding="utf-8", delete=False) as handle:
            temporary_path = Path(handle.name)
            json.dump(metadata, handle, indent=2)
            handle.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def load_export_timestamp(csv_path):
    try:
        metadata = json.loads(metadata_path(csv_path).read_text(encoding="utf-8"))
        if not isinstance(metadata, dict) or metadata.get("csv_sha256") != csv_digest(csv_path):
            return None
        timestamp = datetime.fromisoformat(metadata["exported_at"])
        return timestamp if timestamp.utcoffset() is not None else None
    except (OSError, ValueError, TypeError, KeyError):
        return None
