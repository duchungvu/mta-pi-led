"""Board display runtime loop and schedule/cache helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple

from mta_pi_led.board.display import MTALEDDisplay
from mta_pi_led.board.settings import (
    ArrivalCacheValue,
    CacheKey,
    Config,
    DIRECTION_LABELS,
    RenderSignature,
    StationFeedCacheValue,
    apply_board_config,
)
from mta_pi_led.services.board_config import (
    load_board_config,
    resolve_board_config_path,
)
from mta_pi_led.services.citibike import get_station_data
from mta_pi_led.services.display_scheduler import (
    DisplaySchedule,
    DisplayView,
    create_display_schedule,
)
from mta_pi_led.services.mta_arrivals import get_train_status_batch
from station_data import get_station_lines, get_station_name, is_valid_station


class BoardDisplay(Protocol):
    """Runtime-facing display surface used by tests and hardware display."""

    station_id: str

    def set_station(self, station_id: str):
        ...

    def get_realtime_data(
        self,
        routes: Sequence[str],
        station_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], List[str], List[str]]:
        ...

    def _get_station_name_window(self) -> str:
        ...

    def show_mta_station_info(
        self,
        route: str,
        directions: Sequence[str],
        station_name_window: Optional[str] = None,
    ):
        ...

    def show_mta_arrival_times(
        self,
        route: str,
        uptown_times: List[str],
        downtown_times: List[str],
    ):
        ...

    def clear(self):
        ...


@dataclass
class RuntimeState:
    """Mutable runtime state for the display loop."""

    schedule: DisplaySchedule
    configured_schedule: DisplaySchedule
    active_index: int
    current_route: str
    next_rotation_ts: float
    last_config_reload_check_ts: int
    last_station_feed_refresh_ts: int = 0
    last_citibike_fetch_ts: int = 0
    last_render_signature: Optional[RenderSignature] = None
    arrival_cache: Dict[CacheKey, ArrivalCacheValue] = field(default_factory=dict)
    station_feed_cache: Dict[str, StationFeedCacheValue] = field(default_factory=dict)
    unavailable_until: Dict[CacheKey, int] = field(default_factory=dict)
    dynamic_route_expiry: Dict[CacheKey, int] = field(default_factory=dict)


def get_static_station_routes(station_id: str) -> List[str]:
    """Return configured station routes from local station metadata."""
    if not is_valid_station(station_id):
        print(f"⚠️ Skipping invalid station in schedule: {station_id}")
        return []

    merged: List[str] = []
    seen: set[str] = set()
    for route in get_station_lines(station_id):
        route = str(route).strip().upper()
        if not route or route in seen:
            continue
        seen.add(route)
        merged.append(route)
    return merged


def build_display_schedule(station_ids: List[str]) -> DisplaySchedule:
    """Build station/line rotation schedule from configured stations."""
    fallback_route = Config.MTA.ROUTES[0] if Config.MTA.ROUTES else "F"
    if is_valid_station(Config.MTA.STATION):
        fallback_lines = get_static_station_routes(Config.MTA.STATION)
        if fallback_lines:
            fallback_route = fallback_lines[0]

    valid_station_ids = [
        station_id for station_id in station_ids if is_valid_station(station_id)
    ]
    if not valid_station_ids:
        valid_station_ids = [Config.MTA.STATION]

    schedule = create_display_schedule(
        station_ids=valid_station_ids,
        line_lookup=get_static_station_routes,
        interval_seconds=Config.Display.ROTATION_INTERVAL,
        default_view=DisplayView(
            station_id=Config.MTA.STATION,
            route_id=fallback_route,
        ),
    )
    schedule_label = ", ".join(
        f"{view.station_id}:{view.route_id}" for view in schedule.views
    )
    print(
        f"📋 Display schedule ({schedule.interval_seconds}s): "
        f"{schedule_label if schedule_label else '[empty]'}"
    )
    return schedule


def get_available_view_index(
    schedule: DisplaySchedule,
    start_index: int,
    unavailable_until: Dict[CacheKey, int],
    now_ts: int,
) -> Optional[int]:
    """Get next available schedule index, skipping unavailable routes."""
    if not schedule.views:
        return None

    normalized_start = start_index % len(schedule.views)

    for offset in range(len(schedule.views)):
        idx = (normalized_start + offset) % len(schedule.views)
        candidate = schedule.views[idx]
        key = (candidate.station_id, candidate.route_id)
        if unavailable_until.get(key, 0) <= now_ts:
            return idx

    return None


def should_run_interval(last_run_ts: int, now_ts: int, interval_seconds: int) -> bool:
    """Return True when interval has elapsed."""
    return (now_ts - last_run_ts) >= interval_seconds


def is_cache_stale(
    cached_arrivals: Optional[ArrivalCacheValue],
    now_ts: int,
) -> bool:
    """Return True when cached arrivals need refresh."""
    return (
        cached_arrivals is None
        or (now_ts - cached_arrivals[0]) >= Config.Display.REFRESH_INTERVAL
    )


def get_station_feed_data(
    display: BoardDisplay,
    station_feed_cache: Dict[str, StationFeedCacheValue],
) -> Optional[Dict[str, Any]]:
    """Return the latest cached station feed snapshot for the station."""
    cached_station_feed = station_feed_cache.get(display.station_id)
    if cached_station_feed is None:
        return None
    return cached_station_feed[1]


def _schedule_station_ids(schedule: DisplaySchedule) -> List[str]:
    station_ids: List[str] = []
    seen: set[str] = set()
    for view in schedule.views:
        if view.station_id in seen:
            continue
        seen.add(view.station_id)
        station_ids.append(view.station_id)
    return station_ids


def _preferred_routes_by_station(schedule: DisplaySchedule) -> Dict[str, List[str]]:
    routes_by_station: Dict[str, List[str]] = {}
    for view in schedule.views:
        routes = routes_by_station.setdefault(view.station_id, [])
        if view.route_id not in routes:
            routes.append(view.route_id)
    return routes_by_station


def _normalize_route_sequence(routes: Sequence[Any]) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for route in routes or []:
        route_id = str(route).strip().upper()
        if not route_id or route_id in seen:
            continue
        seen.add(route_id)
        normalized.append(route_id)
    return normalized


def _remember_dynamic_routes(
    dynamic_route_expiry: Dict[CacheKey, int],
    station_ids: Sequence[str],
    static_routes_by_station: Dict[str, List[str]],
    station_payloads: Dict[str, Dict[str, Any]],
    now_ts: int,
):
    configured_station_ids = set(station_ids)
    for key, expires_at in list(dynamic_route_expiry.items()):
        if key[0] not in configured_station_ids or expires_at <= now_ts:
            del dynamic_route_expiry[key]

    ttl_seconds = (
        Config.Display.REFRESH_INTERVAL
        * Config.Display.DYNAMIC_ROUTE_STALE_REFRESHES
    )
    for station_id, station_payload in station_payloads.items():
        static_routes = set(static_routes_by_station.get(station_id, []))
        for route_id in _normalize_route_sequence(
            station_payload.get("active_routes", [])
        ):
            if route_id in static_routes:
                continue
            dynamic_route_expiry[(station_id, route_id)] = now_ts + ttl_seconds


def _routes_with_dynamic_discovery(
    station_ids: Sequence[str],
    static_routes_by_station: Dict[str, List[str]],
    dynamic_route_expiry: Dict[CacheKey, int],
    now_ts: int,
) -> Dict[str, List[str]]:
    routes_by_station: Dict[str, List[str]] = {}
    for station_id in station_ids:
        static_routes = _normalize_route_sequence(
            static_routes_by_station.get(station_id, [])
        )
        static_route_set = set(static_routes)
        dynamic_routes = sorted(
            route_id
            for (dynamic_station_id, route_id), expires_at in dynamic_route_expiry.items()
            if (
                dynamic_station_id == station_id
                and expires_at > now_ts
                and route_id not in static_route_set
            )
        )
        routes_by_station[station_id] = static_routes + dynamic_routes
    return routes_by_station


def _build_schedule_from_route_map(
    station_ids: Sequence[str],
    routes_by_station: Dict[str, List[str]],
) -> DisplaySchedule:
    default_view: Optional[DisplayView] = None
    for station_id in station_ids:
        routes = routes_by_station.get(station_id, [])
        if routes:
            default_view = DisplayView(station_id=station_id, route_id=routes[0])
            break

    return create_display_schedule(
        station_ids=station_ids,
        line_lookup=lambda station_id: routes_by_station.get(station_id, []),
        interval_seconds=Config.Display.ROTATION_INTERVAL,
        default_view=default_view,
    )


def _log_schedule(label: str, schedule: DisplaySchedule):
    schedule_label = ", ".join(
        f"{view.station_id}:{view.route_id}" for view in schedule.views
    )
    print(
        f"📋 {label} ({schedule.interval_seconds}s): "
        f"{schedule_label if schedule_label else '[empty]'}"
    )


def _sync_live_schedule(
    state: RuntimeState,
    station_ids: Sequence[str],
    static_routes_by_station: Dict[str, List[str]],
    station_payloads: Dict[str, Dict[str, Any]],
    now: float,
    now_ts: int,
):
    previous_view = None
    if 0 <= state.active_index < len(state.schedule.views):
        previous_view = state.schedule.views[state.active_index]

    _remember_dynamic_routes(
        state.dynamic_route_expiry,
        station_ids,
        static_routes_by_station,
        station_payloads,
        now_ts,
    )
    live_routes = _routes_with_dynamic_discovery(
        station_ids,
        static_routes_by_station,
        state.dynamic_route_expiry,
        now_ts,
    )
    live_schedule = _build_schedule_from_route_map(station_ids, live_routes)
    if not live_schedule.views or live_schedule == state.schedule:
        return

    state.schedule = live_schedule
    if previous_view in live_schedule.views:
        state.active_index = live_schedule.views.index(previous_view)
    else:
        next_index = get_available_view_index(
            schedule=live_schedule,
            start_index=0,
            unavailable_until=state.unavailable_until,
            now_ts=now_ts,
        )
        state.active_index = next_index if next_index is not None else 0
        state.next_rotation_ts = now + live_schedule.interval_seconds

    state.last_render_signature = None
    _log_schedule("Live display schedule", live_schedule)


def maybe_refresh_station_feeds(state: RuntimeState, now: float, now_ts: int):
    """Refresh all configured station feeds once per refresh interval."""
    if not should_run_interval(
        state.last_station_feed_refresh_ts,
        now_ts,
        Config.Display.REFRESH_INTERVAL,
    ):
        return

    station_ids = _schedule_station_ids(state.configured_schedule)
    if not station_ids:
        state.last_station_feed_refresh_ts = now_ts
        return

    preferred_routes = _preferred_routes_by_station(state.configured_schedule)
    station_labels = ", ".join(
        f"{get_station_name(station_id)} ({station_id})" for station_id in station_ids
    )
    print(f"🔄 Refreshing station feeds: {station_labels}")

    station_payloads = get_train_status_batch(
        station_ids,
        preferred_routes_by_station=preferred_routes,
        discover_routes=True,
    )

    state.station_feed_cache.clear()
    for station_id in station_ids:
        station_payload = station_payloads.get(station_id)
        if station_payload is None:
            continue
        state.station_feed_cache[station_id] = (now_ts, station_payload)

    _sync_live_schedule(
        state,
        station_ids,
        preferred_routes,
        station_payloads,
        now,
        now_ts,
    )
    state.last_station_feed_refresh_ts = now_ts
    state.arrival_cache.clear()
    state.unavailable_until.clear()


def refresh_view_arrivals(
    display: BoardDisplay,
    current_route: str,
    now_ts: int,
    arrival_cache: Dict[CacheKey, ArrivalCacheValue],
    station_feed_cache: Dict[str, StationFeedCacheValue],
    unavailable_until: Dict[CacheKey, int],
) -> Tuple[List[str], List[str], bool]:
    """Refresh arrivals for active view; return times and availability."""
    station_data = get_station_feed_data(display, station_feed_cache)
    if station_data is None:
        print(
            f"⚠️ No station feed snapshot available for "
            f"{get_station_name(display.station_id)}"
        )
        route, uptown, downtown = None, [], []
    else:
        route, uptown, downtown = display.get_realtime_data(
            [current_route],
            station_data=station_data,
        )
    if not route:
        uptown, downtown = [], []

    cache_key = (display.station_id, current_route)
    if not uptown and not downtown:
        unavailable_until[cache_key] = now_ts + Config.Display.REFRESH_INTERVAL
        arrival_cache.pop(cache_key, None)
        print(
            f"⚠️ Skipping unavailable view {cache_key[0]}:{cache_key[1]} "
            f"for {Config.Display.REFRESH_INTERVAL}s"
        )
        return uptown, downtown, False

    arrival_cache[cache_key] = (now_ts, uptown, downtown)
    unavailable_until.pop(cache_key, None)
    return uptown, downtown, True


def reload_runtime_config(
    config_path: Path,
    configured_schedule: DisplaySchedule,
    active_index: int,
    now_ts: int,
    arrival_cache: Dict[CacheKey, ArrivalCacheValue],
    station_feed_cache: Dict[str, StationFeedCacheValue],
    unavailable_until: Dict[CacheKey, int],
    dynamic_route_expiry: Dict[CacheKey, int],
) -> Tuple[DisplaySchedule, int, bool]:
    """Reload config and schedule from board.json."""
    previous_refresh = Config.Display.REFRESH_INTERVAL
    previous_rotation = Config.Display.ROTATION_INTERVAL
    previous_citibike = Config.CitiBike.STATION_ID

    try:
        board_config = load_board_config(config_path)
        apply_board_config(board_config)
        reloaded_schedule = build_display_schedule(board_config.stations)
    except Exception as exc:
        print(f"⚠️ Config reload failed: {exc}")
        return configured_schedule, active_index, False

    if not reloaded_schedule.views:
        print("⚠️ Config reload ignored: empty schedule.")
        return configured_schedule, active_index, False

    schedule_changed = reloaded_schedule != configured_schedule
    settings_changed = (
        previous_refresh != Config.Display.REFRESH_INTERVAL
        or previous_rotation != Config.Display.ROTATION_INTERVAL
        or previous_citibike != Config.CitiBike.STATION_ID
    )
    if not schedule_changed and not settings_changed:
        return configured_schedule, active_index, False

    arrival_cache.clear()
    station_feed_cache.clear()
    unavailable_until.clear()
    dynamic_route_expiry.clear()

    next_index = get_available_view_index(
        schedule=reloaded_schedule,
        start_index=active_index,
        unavailable_until=unavailable_until,
        now_ts=now_ts,
    )
    if next_index is None:
        next_index = 0

    print(f"♻️ Reloaded board config from {config_path}")
    return reloaded_schedule, next_index, True


def maybe_reload_board_config(
    config_path: Path,
    state: RuntimeState,
    now: float,
    now_ts: int,
):
    """Apply board.json changes on refresh cadence."""
    if not should_run_interval(
        state.last_config_reload_check_ts,
        now_ts,
        Config.Display.REFRESH_INTERVAL,
    ):
        return

    reloaded_schedule, reloaded_index, config_reloaded = reload_runtime_config(
        config_path=config_path,
        configured_schedule=state.configured_schedule,
        active_index=state.active_index,
        now_ts=now_ts,
        arrival_cache=state.arrival_cache,
        station_feed_cache=state.station_feed_cache,
        unavailable_until=state.unavailable_until,
        dynamic_route_expiry=state.dynamic_route_expiry,
    )
    state.last_config_reload_check_ts = now_ts

    if not config_reloaded:
        return

    state.configured_schedule = reloaded_schedule
    state.schedule = reloaded_schedule
    state.active_index = reloaded_index
    state.next_rotation_ts = now + state.schedule.interval_seconds
    state.last_render_signature = None
    state.last_station_feed_refresh_ts = 0


def maybe_rotate_display_view(state: RuntimeState, now: float, now_ts: int):
    """Advance to next available station/line view on rotation cadence."""
    if now < state.next_rotation_ts:
        return

    next_index = get_available_view_index(
        schedule=state.schedule,
        start_index=state.active_index + 1,
        unavailable_until=state.unavailable_until,
        now_ts=now_ts,
    )
    if next_index is not None:
        state.active_index = next_index

    state.next_rotation_ts = now + state.schedule.interval_seconds


def sync_display_view(display: BoardDisplay, state: RuntimeState):
    """Ensure display object tracks active schedule view."""
    active_view = state.schedule.views[state.active_index]
    if display.station_id != active_view.station_id:
        display.set_station(active_view.station_id)

    if state.current_route != active_view.route_id:
        state.current_route = active_view.route_id
        print(f"🔁 Switching line to {state.current_route}")


def get_arrivals_for_active_view(
    display: BoardDisplay,
    state: RuntimeState,
    now: float,
    now_ts: int,
) -> Optional[Tuple[List[str], List[str]]]:
    """Return arrivals for active view or None when view should be skipped."""
    cache_key = (display.station_id, state.current_route)
    cached_arrivals = state.arrival_cache.get(cache_key)
    if is_cache_stale(cached_arrivals, now_ts):
        uptown, downtown, has_arrivals = refresh_view_arrivals(
            display=display,
            current_route=state.current_route,
            now_ts=now_ts,
            arrival_cache=state.arrival_cache,
            station_feed_cache=state.station_feed_cache,
            unavailable_until=state.unavailable_until,
        )
        if not has_arrivals:
            next_index = get_available_view_index(
                schedule=state.schedule,
                start_index=state.active_index + 1,
                unavailable_until=state.unavailable_until,
                now_ts=now_ts,
            )
            if next_index is not None and next_index != state.active_index:
                state.active_index = next_index
                state.next_rotation_ts = now + state.schedule.interval_seconds
            return None
        return uptown, downtown

    assert cached_arrivals is not None
    _, uptown, downtown = cached_arrivals
    return uptown, downtown


def maybe_render_view(
    display: BoardDisplay,
    state: RuntimeState,
    uptown: List[str],
    downtown: List[str],
):
    """Render view only when content changes."""
    station_name_window = display._get_station_name_window()
    render_signature = (
        display.station_id,
        state.current_route,
        tuple(uptown),
        tuple(downtown),
        station_name_window,
    )
    if render_signature == state.last_render_signature:
        return

    display.show_mta_station_info(
        state.current_route,
        DIRECTION_LABELS,
        station_name_window=station_name_window,
    )
    display.show_mta_arrival_times(state.current_route, uptown, downtown)
    state.last_render_signature = render_signature


def maybe_refresh_citibike(now_ts: int, state: RuntimeState):
    """Refresh Citi Bike data on refresh cadence."""
    if not Config.CitiBike.ENABLED:
        return

    if not should_run_interval(
        state.last_citibike_fetch_ts,
        now_ts,
        Config.Display.REFRESH_INTERVAL,
    ):
        return

    try:
        get_station_data(Config.CitiBike.STATION_ID)
    except Exception as exc:
        print(f"Error getting citibike data: {exc}")
    state.last_citibike_fetch_ts = now_ts


def main():
    """Run real-time MTA display."""
    config_path = resolve_board_config_path()
    board_config = load_board_config(config_path)
    apply_board_config(board_config)
    schedule = build_display_schedule(board_config.stations)
    if not schedule.views:
        print("✗ No display views available. Exiting.")
        return

    initial_index = get_available_view_index(
        schedule=schedule,
        start_index=0,
        unavailable_until={},
        now_ts=int(time.time()),
    )
    if initial_index is None:
        print("✗ No available display views. Exiting.")
        return
    active_view = schedule.views[initial_index]

    print(
        f"🚇 Starting MTA display scheduler @ {schedule.interval_seconds}s "
        f"rotation, {Config.Display.REFRESH_INTERVAL}s refresh"
    )
    display = MTALEDDisplay(active_view.station_id)
    start_ts = time.time()
    state = RuntimeState(
        schedule=schedule,
        configured_schedule=schedule,
        active_index=initial_index,
        current_route=active_view.route_id,
        next_rotation_ts=start_ts + schedule.interval_seconds,
        last_config_reload_check_ts=int(start_ts),
    )

    print(
        f"🧩 Hot reload enabled for {config_path} "
        f"(every {Config.Display.REFRESH_INTERVAL}s refresh)"
    )

    try:
        display.clear()

        while True:
            now = time.time()
            now_ts = int(now)

            maybe_reload_board_config(config_path, state, now, now_ts)
            maybe_refresh_station_feeds(state, now, now_ts)
            maybe_rotate_display_view(state, now, now_ts)
            sync_display_view(display, state)

            arrivals = get_arrivals_for_active_view(display, state, now, now_ts)
            if arrivals is None:
                time.sleep(Config.Display.UI_TICK_INTERVAL)
                continue
            uptown, downtown = arrivals

            maybe_render_view(display, state, uptown, downtown)
            maybe_refresh_citibike(now_ts, state)

            time.sleep(max(0.2, Config.Display.UI_TICK_INTERVAL))

    except KeyboardInterrupt:
        display.clear()
        print("\n🛑 Display stopped.")
