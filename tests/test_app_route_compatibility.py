import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import app as legacy_app  # noqa: E402


class AppRouteCompatibilityTest(unittest.TestCase):
    def test_ajax_index_preserves_top_level_payload(self):
        station_payloads = {
            "B10": {
                "status": "success",
                "timestamp": "2026-05-18 00:00:00 UTC",
                "trains": {
                    "F": {
                        "uptown": {"next_arrivals": ["2 min"]},
                        "downtown": {"next_arrivals": ["4 min"]},
                    }
                },
                "active_routes": ["F"],
                "station_name": "57 St",
            }
        }

        with patch("app.get_train_status_batch", return_value=station_payloads):
            client = legacy_app.app.test_client()
            response = client.get("/?ajax=true&stations=B10")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(set(payload.keys()), {"station_data", "stations"})
        self.assertEqual(
            set(payload["station_data"].keys()),
            {"status", "timestamp", "trains"},
        )
        self.assertIn("B10", payload["stations"])
        self.assertEqual(
            payload["station_data"]["trains"]["F"]["uptown"]["next_arrivals"],
            ["2 min"],
        )


if __name__ == "__main__":
    unittest.main()
