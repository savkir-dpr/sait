import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from telemetry import TelemetryConfig, TelemetryPublisher


class TelemetryPublisherTests(unittest.TestCase):
    def test_measurements_are_limited_to_one_per_minute(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            queue_path = Path(temporary_directory) / "queue.jsonl"
            config = TelemetryConfig("pi-01", "", "", interval_seconds=60, queue_path=str(queue_path))
            publisher = TelemetryPublisher(config)

            self.assertTrue(publisher.publish_measurement(
                temperatures_c={"t0": 20.0}, vacuum_kpa=10.0, absolute_pressure_kpa=91.0, monotonic_seconds=10.0
            ))
            self.assertFalse(publisher.publish_measurement(
                temperatures_c={"t0": 21.0}, vacuum_kpa=11.0, absolute_pressure_kpa=90.0, monotonic_seconds=69.0
            ))
            self.assertTrue(publisher.publish_measurement(
                temperatures_c={"t0": 22.0}, vacuum_kpa=12.0, absolute_pressure_kpa=89.0, monotonic_seconds=70.0
            ))

            messages = [json.loads(line) for line in queue_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([message["temperatures_c"]["t0"] for message in messages], [20.0, 22.0])

    def test_successful_delivery_removes_message_from_queue(self):
        delivered = []
        delivered_event = threading.Event()

        def transport(endpoint, payload, headers, timeout):
            delivered.append((endpoint, json.loads(payload), headers, timeout))
            delivered_event.set()

        with tempfile.TemporaryDirectory() as temporary_directory:
            queue_path = Path(temporary_directory) / "queue.jsonl"
            config = TelemetryConfig("pi-01", "https://server.example/telemetry", "secret", queue_path=str(queue_path))
            publisher = TelemetryPublisher(config, transport=transport)
            publisher.publish_measurement(
                temperatures_c={"t0": None, "t1": 20.0}, vacuum_kpa=None, absolute_pressure_kpa=101.3, monotonic_seconds=1.0
            )

            self.assertTrue(delivered_event.wait(timeout=1))
            deadline = time.monotonic() + 1
            while queue_path.exists() and queue_path.read_text(encoding="utf-8") and time.monotonic() < deadline:
                time.sleep(0.01)

            self.assertEqual(delivered[0][1]["device_id"], "pi-01")
            self.assertEqual(delivered[0][1]["temperatures_c"]["t0"], None)
            self.assertEqual(delivered[0][2]["Authorization"], "Bearer secret")
            self.assertEqual(queue_path.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
