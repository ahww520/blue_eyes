import unittest
import json
import os
import tempfile

import mainpro


class FormattingTests(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(mainpro._format_bytes(None), "\u2014")
        self.assertEqual(mainpro._format_bytes(0), "0 B")
        self.assertEqual(mainpro._format_bytes(1536), "1.5 KB")
        self.assertEqual(mainpro._format_bytes(-1), "\u2014")

    def test_format_uptime(self):
        self.assertEqual(mainpro._format_uptime(None), "\u2014")
        self.assertEqual(mainpro._format_uptime(0), "0\u5206")
        self.assertEqual(mainpro._format_uptime(3660), "1\u65f6 01\u5206")
        self.assertEqual(mainpro._format_uptime(90061), "1\u5929 01\u65f6")

    def test_percent(self):
        self.assertEqual(mainpro._percent(25), 25.0)
        self.assertEqual(mainpro._percent(5, 10), 50.0)
        self.assertEqual(mainpro._percent(10, 0), None)
        self.assertEqual(mainpro._percent(None, 10), None)
        self.assertEqual(mainpro._percent(120), 100.0)

    def test_bounded_values_and_position(self):
        self.assertEqual(mainpro._bounded_int(float("nan"), 7, 0, 10), 7)
        self.assertEqual(mainpro._bounded_int(99, 7, 0, 10), 10)
        self.assertEqual(mainpro._bounded_float(float("inf"), 0.5, 0, 1), 0.5)
        self.assertEqual(mainpro._parse_position([12.9, -4.2]), [12, -4])
        self.assertIsNone(mainpro._parse_position([float("nan"), 2]))


class MetricsTests(unittest.TestCase):
    def test_cpu_delta(self):
        calc = mainpro.SystemMetricsCollector._calculate_cpu_percent
        self.assertEqual(calc((10, 20, 30), (20, 40, 50)), 75.0)
        self.assertEqual(calc((10, 20, 30), (20, 30, 30)), 0.0)
        self.assertIsNone(calc((1, 2), (3, 4)))
        self.assertIsNone(calc((3, 2, 1), (1, 2, 3)))

    def test_unavailable_collector_degrades(self):
        collector = mainpro.SystemMetricsCollector.__new__(
            mainpro.SystemMetricsCollector
        )
        collector._kernel32 = None
        collector._previous_cpu = None
        snapshot = collector.sample_fast()
        self.assertEqual(snapshot.cpu_state, "unavailable")
        self.assertIsNone(snapshot.cpu_percent)
        self.assertIsNone(snapshot.memory_total)
        self.assertIsNone(snapshot.uptime_seconds)

    def test_disk_snapshot_has_a_root(self):
        snapshot = mainpro.SystemMetricsCollector().sample_disk()
        self.assertTrue(snapshot.root)


class StatisticsTests(unittest.TestCase):
    def test_rollover_archives_previous_day(self):
        app = mainpro.CareEyesApp.__new__(mainpro.CareEyesApp)
        previous = mainpro.date.today() - mainpro.timedelta(days=1)
        today = mainpro.date.today().isoformat()
        app._stat_date = previous.isoformat()
        app.today_minutes = 42
        app.break_count = 3
        app.week_data = {}
        app.session_start = mainpro.datetime.now()

        changed = app._rollover_stats_if_needed(today)

        self.assertTrue(changed)
        self.assertEqual(app.week_data[previous.isoformat()], 42)
        self.assertEqual(app.today_minutes, 0)
        self.assertEqual(app.break_count, 0)
        self.assertEqual(app._stat_date, today)

    def test_invalid_or_future_stat_days_are_rejected(self):
        cutoff = mainpro.date.today() - mainpro.timedelta(days=31)
        self.assertFalse(mainpro.CareEyesApp._valid_stat_day("not-a-date", cutoff))
        self.assertFalse(
            mainpro.CareEyesApp._valid_stat_day(
                (mainpro.date.today() + mainpro.timedelta(days=1)).isoformat(),
                cutoff,
            )
        )

    def test_load_settings_recovers_previous_day_snapshot(self):
        previous = mainpro.date.today() - mainpro.timedelta(days=1)
        config = dict(mainpro.CareEyesApp._DEFAULTS)
        config.update({
            "stat_date": previous.isoformat(),
            "today_minutes": 37,
            "break_count": 2,
        })
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        old_config = mainpro.CONFIG_FILE
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(config, handle)
            mainpro.CONFIG_FILE = path
            app = mainpro.CareEyesApp.__new__(mainpro.CareEyesApp)
            app.load_settings()
            self.assertEqual(app.week_data[previous.isoformat()], 37)
            self.assertEqual(app.today_minutes, 0)
            self.assertEqual(app.break_count, 0)
        finally:
            mainpro.CONFIG_FILE = old_config
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    unittest.main()
