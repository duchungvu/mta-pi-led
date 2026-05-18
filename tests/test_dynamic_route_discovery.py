import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from google.transit import gtfs_realtime_pb2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mta_pi_led.services import mta_arrivals as mta_app  # noqa: E402


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def build_feed(route_id: str, stop_updates: list[tuple[str, int]]) -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = f"{route_id}-trip"
    entity.trip_update.trip.route_id = route_id
    for stop_id, arrival_time in stop_updates:
        stop_time_update = entity.trip_update.stop_time_update.add()
        stop_time_update.stop_id = stop_id
        stop_time_update.arrival.time = arrival_time
    return feed.SerializeToString()


class DynamicRouteDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.current_time = 1000
        self.station_routes = {"B10": ["F", "M"]}
        self.route_times = mta_app._initialize_route_times_by_station(
            self.station_routes
        )
        self.stop_to_stations = {"B10N": ["B10"], "B10S": ["B10"]}
        self.route_targets = mta_app._build_route_targets(self.station_routes)

    def process_feed(self, route_id, stop_updates, discover_routes=False):
        feed_bytes = build_feed(route_id, stop_updates)
        with patch(
            "mta_pi_led.services.mta_arrivals.requests.get",
            return_value=FakeResponse(feed_bytes),
        ):
            return mta_app._process_feed_for_batch(
                "https://example.test/feed",
                self.current_time,
                self.stop_to_stations,
                self.route_targets,
                self.route_times,
                discover_routes=discover_routes,
            )

    def test_static_baseline_only_processes_configured_routes(self):
        active_routes = self.process_feed("F", [("B10N", 1120)])

        self.assertEqual(active_routes["B10"], {"F"})
        self.assertEqual(self.route_times["B10"]["F"]["uptown"], {1120})
        self.assertEqual(self.route_times["B10"]["M"]["uptown"], set())

    def test_discovery_mode_scans_all_configured_feeds(self):
        self.assertEqual(
            mta_app._get_needed_feed_keys(
                self.station_routes,
                discover_routes=True,
            ),
            sorted(mta_app.FEEDS.keys()),
        )

    def test_unconfigured_route_is_discovered_when_it_stops_at_station(self):
        active_routes = self.process_feed(
            "E",
            [("B10S", 1180)],
            discover_routes=True,
        )

        self.assertEqual(active_routes["B10"], {"E"})
        self.assertEqual(self.route_times["B10"]["E"]["downtown"], {1180})

    def test_unconfigured_route_is_ignored_when_stop_does_not_match_station(self):
        active_routes = self.process_feed(
            "E",
            [("D14S", 1180)],
            discover_routes=True,
        )

        self.assertEqual(active_routes["B10"], set())
        self.assertNotIn("E", self.route_times["B10"])

    def test_dynamic_routes_are_ordered_after_static_routes(self):
        route_times = {
            "E": {"uptown": {1180}, "downtown": set()},
            "M": {"uptown": {1240}, "downtown": set()},
            "D": {"uptown": {1120}, "downtown": set()},
            "F": {"uptown": {1060}, "downtown": set()},
        }

        route_order = mta_app._build_route_order(["F", "M"], route_times)
        train_status = mta_app.process_route_times(
            route_times,
            self.current_time,
            "B10",
            route_order=route_order,
        )

        self.assertEqual(route_order, ["F", "M", "D", "E"])
        self.assertEqual(list(train_status.keys()), ["F", "M", "D", "E"])


if __name__ == "__main__":
    unittest.main()
