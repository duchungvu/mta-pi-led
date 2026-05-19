#!/usr/bin/env python3
"""Compatibility entrypoint for the MTA LED board runtime."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mta_pi_led.board.display import MTALEDDisplay
from mta_pi_led.board.runtime import (
    RuntimeState,
    build_display_schedule,
    get_arrivals_for_active_view,
    get_available_view_index,
    get_static_station_routes,
    get_station_feed_data,
    is_cache_stale,
    main,
    maybe_refresh_citibike,
    maybe_refresh_station_feeds,
    maybe_reload_board_config,
    maybe_render_view,
    maybe_rotate_display_view,
    refresh_view_arrivals,
    reload_runtime_config,
    should_run_interval,
    sync_display_view,
)
from mta_pi_led.board.settings import (
    ArrivalCacheValue,
    CacheKey,
    Config,
    DIRECTION_LABELS,
    RenderSignature,
    StationFeedCacheValue,
    apply_board_config,
)

__all__ = [
    "ArrivalCacheValue",
    "CacheKey",
    "Config",
    "DIRECTION_LABELS",
    "MTALEDDisplay",
    "RenderSignature",
    "RuntimeState",
    "StationFeedCacheValue",
    "apply_board_config",
    "build_display_schedule",
    "get_arrivals_for_active_view",
    "get_available_view_index",
    "get_static_station_routes",
    "get_station_feed_data",
    "is_cache_stale",
    "main",
    "maybe_refresh_citibike",
    "maybe_refresh_station_feeds",
    "maybe_reload_board_config",
    "maybe_render_view",
    "maybe_rotate_display_view",
    "refresh_view_arrivals",
    "reload_runtime_config",
    "should_run_interval",
    "sync_display_view",
]


if __name__ == "__main__":
    main()
