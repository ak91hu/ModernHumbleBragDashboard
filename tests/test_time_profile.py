import json
from unittest import TestCase

import pandas as pd
from plotly.utils import PlotlyJSONEncoder

import charts
from analytics import activity_time_profile, filter_data, normalize_data
import test_dashboard


def starts(times):
    return normalize_data(pd.DataFrame([{"id": str(index), "name": "Start-time check", "type": "Run" if index % 2 else "Ride",
                                        "start_date": timestamp, "distance_km": 1, "moving_time_min": 30, "elapsed_time": 45}
                                       for index, timestamp in enumerate(times)]))


class TimeProfileTests(TestCase):
    def test_daypart_boundaries_count_every_activity_once(self):
        frame = starts([f"2026-01-01 {time}" for time in ["00:00:00", "05:59:59", "06:00:00", "11:59:59", "12:00:00", "17:59:59", "18:00:00", "23:59:59"]])
        result = activity_time_profile(frame)
        self.assertEqual([band["count"] for band in result["bands"]], [2, 2, 2, 2])
        self.assertEqual([band["share"] for band in result["bands"]], [25, 25, 25, 25])
        self.assertEqual(sum(result["hours"]), 8)
        self.assertEqual(sum(sum(row) for row in result["grid"]), 8)

    def test_local_start_time_is_not_shifted_by_the_offset(self):
        result = activity_time_profile(starts(["2026-01-01T23:30:00-02:00"]))
        self.assertEqual(result["bands"][3]["count"], 1)
        self.assertEqual(result["hours"][23], 1)

    def test_long_sessions_are_classified_by_start_once(self):
        frame = starts(["2026-01-01 05:50:00"])
        frame.loc[0, "moving_time_min"] = 120
        result = activity_time_profile(frame)
        self.assertEqual(result["bands"][0]["count"], 1)
        self.assertEqual(result["bands"][0]["hours"], 2)
        self.assertEqual(result["bands"][1]["count"], 0)

    def test_sport_and_date_filters_apply_before_classification(self):
        frame = starts(["2026-01-01 08:00:00", "2026-01-02 19:00:00"])
        result = activity_time_profile(filter_data(frame, "2026-01-02", "2026-01-02", ["Run"]))
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["sports"][0]["type"], "Run")
        self.assertEqual(result["sports"][0]["dominant"], ["evening"])

    def test_tied_hours_and_bands_are_all_reported(self):
        result = activity_time_profile(starts(["2026-01-01 08:00:00", "2026-01-02 19:00:00"]))
        self.assertEqual(result["peak_hours"], [8, 19])
        self.assertEqual(result["dominant"], ["morning", "evening"])

    def test_empty_profile_has_no_invented_preferred_time(self):
        result = activity_time_profile(normalize_data(pd.DataFrame()))
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["dominant"], [])
        self.assertEqual(result["peak_hours"], [])
        self.assertEqual(result["hours"], [0] * 24)
        self.assertEqual(result["grid"], [[0] * 24 for _ in range(7)])

    def test_new_charts_have_plain_serializable_arrays_and_fixed_heights(self):
        profile = activity_time_profile(starts(["2026-01-01 08:00:00", "2026-01-02 19:00:00"]))
        for theme in ["light", "dark"]:
            for lang in ["HU", "EN"]:
                for builder in [charts.start_hours, charts.daypart_sports, charts.weekday_hours]:
                    with self.subTest(theme=theme, lang=lang, chart=builder.__name__):
                        figure = builder(profile, lang, theme)
                        payload = json.dumps(figure, cls=PlotlyJSONEncoder)
                        self.assertNotIn('"bdata"', payload)
                        self.assertGreaterEqual(int(charts.graph(figure, "time-test").style["height"][:-2]), 245)

    def test_trends_callback_includes_all_time_of_day_charts(self):
        harness = test_dashboard.DashboardTests()
        harness.setUp()
        result = harness.call("render", ["trends", "HU", "2026-01-01", "2026-10-13", [], "distance", "light", test_dashboard.app.DEFAULT_GOALS, [], "", "newest", [], 0])
        ids = test_dashboard.component_ids(result["page-content"]["children"])
        for graph_id in ["chart-start-hours", "chart-daypart-sports", "chart-weekday-hours"]:
            self.assertIn(json.dumps(graph_id), ids)
