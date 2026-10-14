import json
from unittest import TestCase

import pandas as pd
from plotly.utils import PlotlyJSONEncoder

import app
import charts
from analytics import filter_data, normalize_data
from records import personal_records
import test_dashboard
from test_dashboard import sample


class ChartRegressionTests(TestCase):
    def test_every_trend_chart_has_an_explicit_responsive_container(self):
        frame = app.df_global
        previous = filter_data(frame, "2025-01-01", "2025-10-13")
        frame = filter_data(frame, "2026-01-01", "2026-10-13")
        figures = [charts.cumulative(frame, previous, "2026-01-01", "2026-10-13", "distance", "HU", "light"),
                   charts.weekly(frame, "2026-01-01", "2026-10-13", "distance", "HU", "light"),
                   charts.routine(frame, "HU", "light"), charts.scatter(frame, "HU", "light"), charts.heart_rate(frame, "HU", "light")]
        for index, figure in enumerate(figures):
            with self.subTest(chart=index):
                component = charts.graph(figure, str(index))
                self.assertTrue(component.responsive)
                self.assertEqual(component.style["height"], f"{figure.layout.height}px")
                self.assertEqual(component.style["minHeight"], component.style["height"])
                self.assertGreaterEqual(int(component.style["height"][:-2]), 205)

    def test_trend_payloads_have_plain_data_arrays(self):
        frame = sample()
        for figure in [charts.cumulative(frame, frame.iloc[:0], "2025-12-31", "2026-01-01", "distance", "EN", "dark"),
                       charts.weekly(frame, "2025-12-31", "2026-01-01", "elevation", "EN", "dark"),
                       charts.routine(frame, "EN", "dark"), charts.scatter(frame, "EN", "dark")]:
            serialized = json.loads(json.dumps(figure, cls=PlotlyJSONEncoder))
            self.assertNotIn('"bdata"', json.dumps(serialized))
            for trace in serialized["data"]:
                self.assertIsInstance(trace["y"], list)
                self.assertEqual(len(trace["x"]), len(trace["y"]))

    def test_nonfinite_source_values_do_not_poison_progress(self):
        frame = normalize_data(pd.DataFrame([{"id": "1", "start_date": "2026-01-01", "type": "Run", "distance_km": float("inf"), "average_speed_kmh": float("nan")}]))
        figure = charts.cumulative(frame, frame.iloc[:0], "2026-01-01", "2026-01-02", "distance", "HU", "light")
        self.assertEqual(list(figure.data[0].y), [0, 0])


class PersonalRecordTests(TestCase):
    def records(self, frame):
        return {record["key"]: record for section in personal_records(frame) for record in section["items"]}

    def test_daily_records_sum_all_activities_and_weeks_start_on_monday(self):
        records = self.records(sample())
        self.assertEqual(records["period.day-distance"]["value"], 25)
        self.assertEqual(records["period.day-count"]["value"], 2)
        self.assertEqual(records["period.week-distance"]["value"], 35)
        self.assertEqual(records["period.week-distance"]["start"], pd.Timestamp("2025-12-29"))
        self.assertEqual(records["period.week-distance"]["end"], pd.Timestamp("2026-01-04"))
        self.assertEqual(records["period.streak"]["value"], 2)

    def test_running_and_cycling_records_do_not_mix(self):
        records = self.records(sample())
        self.assertEqual(records["sport.Run.distance"]["value"], 10)
        self.assertEqual(records["sport.Ride.distance"]["value"], 20)
        self.assertEqual(records["sport.Run.pace-5"]["value"], 360)
        self.assertEqual(records["sport.Run.pace-10"]["value"], 360)
        self.assertNotIn("sport.Run.pace-21.0975", records)
        self.assertEqual(records["sport.Ride.speed"]["activity_id"], "2")

    def test_peak_speed_converts_meters_per_second(self):
        frame = sample()
        frame.loc[frame["id"] == "2", "max_speed"] = 10
        self.assertEqual(self.records(frame)["sport.Ride.peak-speed"]["value"], 36)

    def test_missing_metrics_do_not_create_fake_zero_records(self):
        records = self.records(sample())
        self.assertNotIn("overall.segment-pr", records)
        self.assertNotIn("overall.kudos", records)
        self.assertEqual(personal_records(normalize_data(pd.DataFrame())), [])

    def test_records_respect_sport_and_date_filters(self):
        records = self.records(filter_data(sample(), "2026-01-01", "2026-01-01", ["Run"]))
        self.assertEqual(records["overall.distance"]["value"], 5)
        self.assertEqual(records["period.day-distance"]["value"], 5)
        self.assertFalse(any(key.startswith("sport.Ride") for key in records))

    def test_default_year_has_many_records_with_unique_keys(self):
        sections = personal_records(filter_data(app.df_global, "2026-01-01", "2026-10-13"))
        keys = [record["key"] for section in sections for record in section["items"]]
        self.assertGreater(len(keys), 20)
        self.assertEqual(len(keys), len(set(keys)))


class PeriodRecordCallbackTests(TestCase):
    def test_record_period_opens_matching_activities(self):
        harness = test_dashboard.DashboardTests()
        harness.setUp()
        changed = json.dumps({"kind": "period-detail", "key": "period.month-distance", "start": "2026-10-01", "end": "2026-10-31"}, sort_keys=True, separators=(",", ":")) + ".n_clicks"
        result = harness.call("show_detail", [[], [], [1], None], ["HU", "2026-01-01", "2026-10-13", ["Walk"], []], changed)
        self.assertEqual(result["detail-dialog"]["style"]["display"], "flex")
        self.assertEqual(result["detail-title"]["children"], "2026-10-01 – 2026-10-31")
        payload = json.dumps(result, ensure_ascii=False)
        expected = filter_data(app.df_global, "2026-10-01", "2026-10-13", ["Walk"])
        for name in expected["name"]:
            self.assertIn(name, payload)
