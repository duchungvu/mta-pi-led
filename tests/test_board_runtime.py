import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mta_pi_led.board import runtime  # noqa: E402
from mta_pi_led.board.settings import Config  # noqa: E402
from mta_pi_led.services.display_scheduler import (  # noqa: E402
    DisplaySchedule,
    DisplayView,
)


class FakeDisplay:
    def __init__(self, station_id="B10", realtime_result=None):
        self.station_id = station_id
        self.realtime_result = realtime_result or ("F", ["2 min"], ["4 min"])
        self.realtime_calls = 0
        self.rendered = []
        self.station_switches = []

    def set_station(self, station_id):
        self.station_id = station_id
        self.station_switches.append(station_id)

    def get_realtime_data(self, routes, station_data=None):
        self.realtime_calls += 1
        return self.realtime_result

    def _get_station_name_window(self):
        return "57 St"

    def show_mta_station_info(self, route, directions, station_name_window=None):
        self.rendered.append(("station", route, tuple(directions), station_name_window))

    def show_mta_arrival_times(self, route, uptown_times, downtown_times):
        self.rendered.append(("arrivals", route, tuple(uptown_times), tuple(downtown_times)))

    def clear(self):
        pass


def make_schedule(routes=("F", "M"), interval_seconds=10):
    return DisplaySchedule(
        views=[DisplayView(station_id="B10", route_id=route) for route in routes],
        interval_seconds=interval_seconds,
    )


class BoardRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.previous_refresh = Config.Display.REFRESH_INTERVAL
        self.previous_rotation = Config.Display.ROTATION_INTERVAL
        self.previous_station = Config.MTA.STATION
        self.previous_citibike_station = Config.CitiBike.STATION_ID

    def tearDown(self):
        Config.Display.REFRESH_INTERVAL = self.previous_refresh
        Config.Display.ROTATION_INTERVAL = self.previous_rotation
        Config.MTA.STATION = self.previous_station
        Config.CitiBike.STATION_ID = self.previous_citibike_station

    def test_cached_arrivals_are_reused_before_stale_interval(self):
        Config.Display.REFRESH_INTERVAL = 30
        display = FakeDisplay()
        schedule = make_schedule(routes=("F",))
        state = runtime.RuntimeState(
            schedule=schedule,
            configured_schedule=schedule,
            active_index=0,
            current_route="F",
            next_rotation_ts=130.0,
            last_config_reload_check_ts=100,
            arrival_cache={("B10", "F"): (100, ["2 min"], ["4 min"])},
        )

        arrivals = runtime.get_arrivals_for_active_view(
            display,
            state,
            now=110.0,
            now_ts=110,
        )

        self.assertEqual(arrivals, (["2 min"], ["4 min"]))
        self.assertEqual(display.realtime_calls, 0)

    def test_unavailable_route_is_skipped_until_refresh_interval(self):
        Config.Display.REFRESH_INTERVAL = 30
        display = FakeDisplay(realtime_result=(None, [], []))
        schedule = make_schedule(routes=("F", "M"))
        state = runtime.RuntimeState(
            schedule=schedule,
            configured_schedule=schedule,
            active_index=0,
            current_route="F",
            next_rotation_ts=130.0,
            last_config_reload_check_ts=100,
            station_feed_cache={"B10": (100, {"status": "success", "trains": {}})},
        )

        arrivals = runtime.get_arrivals_for_active_view(
            display,
            state,
            now=100.0,
            now_ts=100,
        )

        self.assertIsNone(arrivals)
        self.assertEqual(state.unavailable_until[("B10", "F")], 130)
        self.assertEqual(state.active_index, 1)
        self.assertEqual(state.next_rotation_ts, 110.0)

    def test_rotation_advances_to_next_available_view(self):
        schedule = make_schedule(routes=("F", "M"))
        state = runtime.RuntimeState(
            schedule=schedule,
            configured_schedule=schedule,
            active_index=0,
            current_route="F",
            next_rotation_ts=100.0,
            last_config_reload_check_ts=90,
        )

        runtime.maybe_rotate_display_view(state, now=101.0, now_ts=101)

        self.assertEqual(state.active_index, 1)
        self.assertEqual(state.next_rotation_ts, 111.0)

    def test_config_reload_clears_caches_and_resets_schedule(self):
        old_schedule = make_schedule(routes=("F",), interval_seconds=10)
        arrival_cache = {("B10", "F"): (100, ["2 min"], ["4 min"])}
        station_feed_cache = {"B10": (100, {"status": "success"})}
        unavailable_until = {("B10", "F"): 130}
        dynamic_route_expiry = {("B10", "E"): 160}

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "board.json"
            config_path.write_text(
                json.dumps(
                    {
                        "stations": ["B10"],
                        "rotation_seconds": 15,
                        "refresh_seconds": 45,
                        "citibike_station_id": "citibike-test",
                    }
                ),
                encoding="utf-8",
            )

            new_schedule, new_index, changed = runtime.reload_runtime_config(
                config_path=config_path,
                configured_schedule=old_schedule,
                active_index=0,
                now_ts=100,
                arrival_cache=arrival_cache,
                station_feed_cache=station_feed_cache,
                unavailable_until=unavailable_until,
                dynamic_route_expiry=dynamic_route_expiry,
            )

        self.assertTrue(changed)
        self.assertEqual(new_schedule.interval_seconds, 15)
        self.assertEqual(new_index, 0)
        self.assertEqual(Config.Display.REFRESH_INTERVAL, 45)
        self.assertEqual(Config.Display.ROTATION_INTERVAL, 15)
        self.assertEqual(Config.CitiBike.STATION_ID, "citibike-test")
        self.assertEqual(arrival_cache, {})
        self.assertEqual(station_feed_cache, {})
        self.assertEqual(unavailable_until, {})
        self.assertEqual(dynamic_route_expiry, {})


if __name__ == "__main__":
    unittest.main()
