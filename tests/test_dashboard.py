import io
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import pandas as pd
from plotly.utils import PlotlyJSONEncoder

import app
from analytics import calendar_cells, comparison_range, filter_data, load_data, normalize_data, pace_label, streaks, summarize
from charts import cumulative
from export_metadata import load_export_timestamp, metadata_path, write_export_metadata
from scripts.update_data import update_activities


def sample():
    return normalize_data(pd.DataFrame([
        {"id": "1", "name": "Evening run", "type": "root='Run'", "start_date": "2025-12-31T23:30:00-02:00", "distance_km": 10, "moving_time_min": 60, "elapsed_time": 75, "elevation_m": 100, "average_speed_kmh": 10},
        {"id": "2", "name": "Morning ride", "type": "Ride", "start_date": "2026-01-01 06:00:00+00:00", "distance_km": 20, "moving_time_min": 60, "elapsed_time": 60, "elevation_m": 200, "average_speed_kmh": 20},
        {"id": "3", "name": "Afternoon run", "type": "Run", "start_date": "2026-01-01 17:00:00+00:00", "distance_km": 5, "moving_time_min": 30, "elapsed_time": 30, "elevation_m": 50, "average_speed_kmh": 10},
    ]))


def component_ids(value):
    serialized = json.loads(json.dumps(value, cls=PlotlyJSONEncoder))
    ids = []
    def visit(node):
        if isinstance(node, dict):
            if "props" in node and "id" in node["props"]:
                ids.append(json.dumps(node["props"]["id"], sort_keys=True))
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(serialized)
    return ids


class AnalyticsTests(TestCase):
    def test_elapsed_minutes_are_not_converted_twice(self):
        self.assertAlmostEqual(summarize(sample())["efficiency"], 150 / 165 * 100)

    def test_local_calendar_date_is_preserved(self):
        self.assertEqual(sample().iloc[0]["date"], pd.Timestamp("2025-12-31"))
        self.assertEqual(sample().iloc[0]["type"], "Run")

    def test_missing_and_empty_data_have_usable_schema(self):
        for frame in [normalize_data(pd.DataFrame()), load_data("missing-test-file.csv")]:
            self.assertEqual(summarize(frame)["count"], 0)
            self.assertEqual(streaks(frame), (0, 0))

    def test_filter_is_inclusive_and_search_is_literal(self):
        frame = sample()
        self.assertEqual(len(filter_data(frame, "2026-01-01", "2026-01-01")), 2)
        self.assertEqual(len(filter_data(frame, types=["Run"])), 2)
        self.assertEqual(len(filter_data(frame, query="[")), 0)
        self.assertEqual(len(filter_data(frame, query="MORNING")), 1)
        self.assertEqual(len(filter_data(frame, favorites=["2"], only_favorites=True)), 1)

    def test_multiple_activities_on_a_day_do_not_extend_streak(self):
        self.assertEqual(streaks(sample(), "2026-01-02"), (2, 2))
        self.assertEqual(streaks(sample(), "2026-01-03"), (0, 2))

    def test_iso_year_edges_have_separate_columns(self):
        cells = calendar_cells(2025, sample())
        jan = next(c for c in cells if c["date"] == pd.Timestamp("2025-01-01"))
        dec = next(c for c in cells if c["date"] == pd.Timestamp("2025-12-31"))
        self.assertNotEqual(jan["week"], dec["week"])
        self.assertEqual(dec["distance"], 10)

    def test_comparison_period_has_equal_inclusive_length(self):
        start, end = comparison_range("2026-03-01", "2026-03-30")
        self.assertEqual(start, pd.Timestamp("2026-01-30"))
        self.assertEqual(end, pd.Timestamp("2026-02-28"))

    def test_cumulative_is_recomputed_after_sport_filtering(self):
        frame = filter_data(sample(), "2026-01-01", "2026-01-01", ["Run"])
        fig = cumulative(frame, frame.iloc[0:0], "2026-01-01", "2026-01-01", "distance", "EN", "light")
        self.assertEqual(fig.data[0].y[-1], 5)

    def test_run_pace_uses_minutes_per_kilometer(self):
        self.assertEqual(pace_label(sample().iloc[0]), ("6:00", "min/km"))


class DashboardTests(TestCase):
    def setUp(self):
        self.client = app.server.test_client()

    def call(self, function_name, values, states=None, changed=None):
        key, metadata = next((key, value) for key, value in app.app.callback_map.items() if value["callback"].__name__ == function_name)
        outputs = metadata["output"]
        output_payload = [{"id": o.component_id, "property": o.component_property} for o in outputs] if isinstance(outputs, list) else {"id": outputs.component_id, "property": outputs.component_property}
        payload = {"output": key, "outputs": output_payload,
                   "inputs": [dict(meta, value=value) for meta, value in zip(metadata["inputs"], values)],
                   "state": [dict(meta, value=value) for meta, value in zip(metadata["state"], states or [])],
                   "changedPropIds": [changed or f"{metadata['inputs'][0]['id']}.{metadata['inputs'][0]['property']}"]}
        # allow_optional is server metadata rather than a request field.
        for item in payload["inputs"]:
            item.pop("allow_optional", None)
        response = self.client.post("/_dash-update-component", json=payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:1500])
        return response.get_json()["response"]

    def test_routes_and_assets(self):
        for path in ["/", "/_dash-layout", "/_dash-dependencies", "/health", "/assets/style.css", "/assets/summit.svg", "/assets/fonts/font-1.ttf", "/assets/accessibility.js"]:
            with self.subTest(path=path):
                with self.client.get(path) as response:
                    self.assertEqual(response.status_code, 200)
        self.assertGreater(self.client.get("/health").json["activities"], 0)

    def test_export_status_uses_budapest_time_and_translates(self):
        for timestamp, hu, en in [
            ("2026-10-13T12:29:18+00:00", "2026.10.13. 14:29", "2026-10-13 14:29"),
            ("2026-01-13T12:29:18+00:00", "2026.01.13. 13:29", "2026-01-13 13:29"),
        ]:
            with patch.object(app, "EXPORT_TIMESTAMP", datetime.fromisoformat(timestamp)):
                for lang, expected in [("HU", hu), ("EN", en)]:
                    with self.subTest(timestamp=timestamp, lang=lang):
                        result = self.call("translate", [lang])
                        status = result["last-export"]["children"]
                        self.assertIn(expected, status[1]["props"]["children"])
                        self.assertIn("Strava", status[0]["props"]["children"])
                        self.assertEqual(result["last-sync"]["children"].startswith("Legutóbbi edzés:"), lang == "HU")
        with patch.object(app, "EXPORT_TIMESTAMP", None):
            self.assertIn("nincs rögzítve", self.call("translate", ["HU"])["last-export"]["children"])
            self.assertIn("not recorded", self.call("translate", ["EN"])["last-export"]["children"])

    def test_all_views_languages_themes_and_unique_ids(self):
        for view in app.NAV:
            for lang, theme in [("HU", "light"), ("EN", "dark")]:
                with self.subTest(view=view, lang=lang, theme=theme):
                    values = [view, lang, "2022-01-01", "2026-10-13", [], "distance", theme, app.DEFAULT_GOALS, [], "", "newest", [], 0]
                    result = self.call("render", values)
                    content = result["page-content"]["children"]
                    ids = component_ids([app.app.layout, content])
                    self.assertEqual(len(ids), len(set(ids)))

    def test_empty_filter_and_missing_csv_do_not_break_views(self):
        for view in app.NAV:
            with self.subTest(view=view):
                self.call("render", [view, "EN", "2000-01-01", "2000-01-02", [], "distance", "light", app.DEFAULT_GOALS, [], "", "newest", [], 0])
        with patch.object(app, "df_global", normalize_data(pd.DataFrame())):
            self.call("render", ["overview", "HU", "2026-01-01", "2026-10-13", [], "distance", "light", app.DEFAULT_GOALS, [], "", "newest", [], 0])

    def test_log_search_sort_pagination_and_favorites(self):
        activity_id = app.df_global.iloc[0]["id"]
        result = self.call("render", ["log", "HU", "2022-01-01", "2026-10-13", [], "distance", "light", app.DEFAULT_GOALS, [activity_id], "", "distance", ["yes"], 99])
        self.assertEqual(result["page-info"]["children"], "1–1 / 1 edzés")
        self.assertTrue(result["next-page"]["disabled"])
        result = self.call("render", ["log", "HU", "2022-01-01", "2026-10-13", [], "distance", "light", app.DEFAULT_GOALS, [], "not-an-activity-xyz", "newest", [], 0])
        self.assertEqual(result["page-info"]["children"], "0–0 / 0 edzés")

    def test_goal_save_and_validation(self):
        result = self.call("edit_goals", [None, 1, None], [2026, 3000, 20000, 400, app.DEFAULT_GOALS, "HU"], "save-goals.n_clicks")
        self.assertEqual(result["goals-store"]["data"]["distance"], 3000)
        self.assertEqual(result["goal-dialog"]["style"]["display"], "none")
        invalid = self.call("edit_goals", [None, 2, None], [2026, 0, 20000, 400, app.DEFAULT_GOALS, "HU"], "save-goals.n_clicks")
        self.assertNotIn("goals-store", invalid)
        self.assertTrue(invalid["goal-validation"]["children"])

    def test_date_presets_and_custom_range_stay_in_sync(self):
        result = self.call("set_dates", ["year", 2025, "2026-01-01", "2026-10-13"], changed="year-filter.value")
        self.assertEqual(result["date-range"]["start_date"], "2025-01-01")
        self.assertEqual(result["date-range"]["end_date"], "2025-12-31")
        self.assertEqual(result["period-preset"]["value"], "year")
        result = self.call("set_dates", ["year", 2026, "2026-05-01", "2026-05-31"], changed="date-range.start_date")
        self.assertEqual(result["period-preset"]["value"], "custom")
        self.assertNotIn("date-range", result)

    def test_favorite_toggle_and_activity_detail(self):
        activity_id = app.df_global.iloc[-1]["id"]
        changed = json.dumps({"kind": "favorite", "id": activity_id, "slot": "main"}, sort_keys=True, separators=(",", ":")) + ".n_clicks"
        result = self.call("toggle_favorite", [[1]], [[]], changed)
        self.assertEqual(result["favorites-store"]["data"], [activity_id])
        result = self.call("toggle_favorite", [[2]], [[activity_id]], changed)
        self.assertEqual(result["favorites-store"]["data"], [])
        changed = json.dumps({"kind": "detail", "id": activity_id, "slot": "main"}, sort_keys=True, separators=(",", ":")) + ".n_clicks"
        result = self.call("show_detail", [[1], [], [], None], ["HU", "2022-01-01", "2026-10-13", [], []], changed)
        self.assertEqual(result["detail-dialog"]["style"]["display"], "flex")
        self.assertEqual(result["detail-title"]["children"], app.df_global.iloc[-1]["name"])

    def test_csv_export_matches_current_log_filters(self):
        activity_id = app.df_global.iloc[0]["id"]
        result = self.call("export_csv", [1], ["2022-01-01", "2026-10-13", [], "log", "", ["yes"], [activity_id]])
        data = result["download-csv"]["data"]
        exported = pd.read_csv(io.StringIO(data["content"]), dtype={"id": str})
        self.assertEqual(exported["id"].tolist(), [activity_id])


class SyncTests(TestCase):
    def test_failed_download_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "activities.csv"
            sample().to_csv(path, index=False)
            write_export_metadata(path, datetime(2026, 10, 12, tzinfo=timezone.utc))
            before = path.read_bytes()
            metadata_before = metadata_path(path).read_bytes()
            def interrupted(**kwargs):
                raise RuntimeError("network error")
            client = SimpleNamespace(get_activities=interrupted)
            with self.assertRaises(RuntimeError):
                update_activities(client=client, path=path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(metadata_path(path).read_bytes(), metadata_before)

    def test_empty_incremental_sync_retains_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "activities.csv"
            sample().to_csv(path, index=False)
            write_export_metadata(path, datetime(2026, 10, 12, tzinfo=timezone.utc))
            before = path.read_bytes()
            metadata_before = metadata_path(path).read_bytes()
            client = Mock()
            client.get_activities.return_value = []
            result = update_activities(client=client, path=path)
            self.assertEqual(len(result), 3)
            self.assertIsNotNone(client.get_activities.call_args.kwargs["after"])
            self.assertEqual(path.read_bytes(), before)
            self.assertNotEqual(metadata_path(path).read_bytes(), metadata_before)
            self.assertIsNotNone(load_export_timestamp(path))

    def test_recent_edits_replace_rows_without_losing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "activities.csv"
            sample().to_csv(path, index=False)
            client = Mock()
            client.get_activities.return_value = [SimpleNamespace(id=2, name="Updated ride", type="Ride", start_date_local=pd.Timestamp("2026-01-01 06:00:00"), distance=22000, moving_time=3600, elapsed_time=3900, total_elevation_gain=240, average_speed=6, max_speed=10, kudos_count=42)]
            result = update_activities(client=client, path=path)
            self.assertEqual(len(result), 3)
            self.assertEqual(result[result["id"] == "2"].iloc[0]["kudos"], 42)
            self.assertEqual(len(pd.read_csv(path)), 3)
            self.assertIsNotNone(load_export_timestamp(path))

    def test_missing_or_mismatched_export_metadata_does_not_show_a_false_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "activities.csv"
            sample().to_csv(path, index=False)
            self.assertIsNone(load_export_timestamp(path))
            write_export_metadata(path)
            self.assertIsNotNone(load_export_timestamp(path))
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            self.assertIsNone(load_export_timestamp(path))
            write_export_metadata(path)
            metadata = json.loads(metadata_path(path).read_text(encoding="utf-8"))
            for bad_timestamp in ["invalid", "2026-10-13T12:29:18", None]:
                with self.subTest(timestamp=bad_timestamp):
                    metadata["exported_at"] = bad_timestamp
                    metadata_path(path).write_text(json.dumps(metadata), encoding="utf-8")
                    self.assertIsNone(load_export_timestamp(path))

    def test_empty_full_sync_preserves_previous_export_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "activities.csv"
            sample().to_csv(path, index=False)
            write_export_metadata(path)
            before = path.read_bytes(), metadata_path(path).read_bytes()
            client = Mock()
            client.get_activities.return_value = []
            with self.assertRaises(RuntimeError):
                update_activities(client=client, full=True, path=path)
            self.assertEqual((path.read_bytes(), metadata_path(path).read_bytes()), before)
