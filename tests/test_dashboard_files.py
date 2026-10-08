import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardFilesTests(unittest.TestCase):
    def test_dashboard_shows_one_pressure_and_two_doors(self):
        html = (ROOT / "templates/monitoring/dashboard.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('id="pressure"'), 1)
        self.assertNotIn('id="vacuum"', html)
        self.assertIn('<small>бар</small>', html)
        self.assertIn('id="door-1"', html)
        self.assertIn('id="door-2"', html)
        self.assertIn('data-dashboard-version="average-bar-v2"', html)
        self.assertEqual(html.count("?v=average-bar-v2"), 2)

    def test_javascript_reads_door_states(self):
        script = (ROOT / "monitoring/static/monitoring/dashboard.js").read_text(encoding="utf-8")
        self.assertIn("measurement.doors_closed?.door_1", script)
        self.assertIn("measurement.doors_closed?.door_2", script)
        self.assertIn("pressureBar(measurement.absolute_pressure_kpa)", script)
        self.assertIn("values.reduce((sum, value) => sum + value, 0) / values.length", script)


if __name__ == "__main__":
    unittest.main()
