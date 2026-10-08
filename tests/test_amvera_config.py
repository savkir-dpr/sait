import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AmveraConfigTests(unittest.TestCase):
    def test_amvera_runs_production_entry_point(self):
        config = (ROOT / "amvera.yml").read_text(encoding="utf-8")
        self.assertIn("scriptName: start.py", config)
        self.assertNotIn("scriptName: app.py", config)

    def test_entry_point_uses_persistent_database_and_gunicorn(self):
        script = (ROOT / "start.py").read_text(encoding="utf-8")
        self.assertIn('/data/db.sqlite3', script)
        self.assertIn('sensor_site.wsgi:application', script)
        self.assertIn('collectstatic', script)


if __name__ == "__main__":
    unittest.main()
