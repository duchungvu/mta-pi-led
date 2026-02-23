"""Display scheduling primitives shared across board/web/mobile surfaces."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass(frozen=True)
class DisplayView:
    """A single displayable view (station + line)."""

    station_id: str
    route_id: str


@dataclass(frozen=True)
class DisplaySchedule:
    """Ordered display views with a fixed rotation interval."""

    views: list[DisplayView]
    interval_seconds: int


def create_display_schedule(
    station_ids: Sequence[str],
    line_lookup: Callable[[str], Sequence[str]],
    interval_seconds: int,
    default_view: DisplayView | None = None,
) -> DisplaySchedule:
    """Build a schedule from stations and their available lines."""
    ordered_views: list[DisplayView] = []
    seen: set[tuple[str, str]] = set()

    for station_id in station_ids:
        normalized_station = station_id.strip().upper()
        if not normalized_station:
            continue
        for route_id in line_lookup(normalized_station):
            normalized_route = route_id.strip().upper()
            key = (normalized_station, normalized_route)
            if not normalized_station or not normalized_route or key in seen:
                continue
            seen.add(key)
            ordered_views.append(
                DisplayView(station_id=normalized_station, route_id=normalized_route)
            )

    if not ordered_views and default_view is not None:
        ordered_views = [default_view]

    return DisplaySchedule(
        views=ordered_views,
        interval_seconds=_as_positive_interval(interval_seconds),
    )


def get_active_view(
    schedule: DisplaySchedule, now_ts: int | None = None
) -> DisplayView | None:
    """Return currently active view based on Unix timestamp."""
    if not schedule.views:
        return None

    current_ts = int(now_ts if now_ts is not None else time.time())
    index = (current_ts // schedule.interval_seconds) % len(schedule.views)
    return schedule.views[index]


def _as_positive_interval(value: int) -> int:
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except (TypeError, ValueError):
        pass
    return 10
