"""Board control helpers for the web controller API."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from mta_pi_led.services.board_config import (
    DEFAULT_CITIBIKE_STATION_ID,
    DEFAULT_REFRESH_SECONDS,
    DEFAULT_ROTATION_SECONDS,
    DEFAULT_STATIONS,
    resolve_board_config_path,
)
from mta_pi_led.services.display_scheduler import (
    DisplayView,
    create_display_schedule,
)
from station_data import (
    get_station_lines,
    get_station_name,
    is_valid_station,
    load_station_data,
)

DEFAULT_CONFIG_VERSION = 1
DEFAULT_STATUS_FILENAME = "board_runtime_status.json"


def resolve_status_path(status_path: str | Path | None = None) -> Path:
    """Resolve optional board runtime heartbeat path."""
    if status_path is not None:
        return Path(status_path).expanduser()

    env_path = os.getenv("BOARD_STATUS_PATH")
    if env_path:
        return Path(env_path).expanduser()

    return Path(__file__).resolve().parents[3] / "logs" / DEFAULT_STATUS_FILENAME


def load_config_payload(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load raw board config payload from disk."""
    path = resolve_board_config_path(config_path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        return {}
    return payload


def save_config_payload(
    payload: dict[str, Any], config_path: str | Path | None = None
) -> Path:
    """Save normalized board config payload to disk."""
    path = resolve_board_config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
            temp_path = Path(fh.name)

        # Ensure board runtime can read config regardless of writer umask.
        temp_path.chmod(0o644)
        os.replace(temp_path, path)
        path.chmod(0o644)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)

    return path


def normalize_config_payload(
    payload: dict[str, Any] | None,
    *,
    strict: bool,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Normalize payload and return (config, errors, warnings)."""
    source = payload if isinstance(payload, dict) else {}
    errors: list[str] = []
    warnings: list[str] = []

    raw_stations = source.get("stations")
    stations: list[str] = []
    invalid_stations: list[str] = []
    if isinstance(raw_stations, list):
        seen: set[str] = set()
        for item in raw_stations:
            if not isinstance(item, str):
                continue
            station_id = item.strip().upper()
            if not station_id:
                continue
            if station_id in seen:
                continue
            seen.add(station_id)
            if is_valid_station(station_id):
                stations.append(station_id)
            else:
                invalid_stations.append(station_id)
    elif raw_stations is not None:
        (errors if strict else warnings).append(
            "stations must be an array of station ids."
        )

    if invalid_stations:
        message = f"Invalid station ids: {', '.join(invalid_stations)}"
        if strict:
            errors.append(message)
        else:
            warnings.append(message)

    if not stations:
        if strict:
            errors.append("At least one valid station id is required.")
        else:
            stations = DEFAULT_STATIONS.copy()
            warnings.append(
                f"No valid stations found; defaulting to {', '.join(stations)}."
            )

    rotation_seconds, rotation_error = _parse_positive_int(
        source.get("rotation_seconds"),
        DEFAULT_ROTATION_SECONDS,
        field_name="rotation_seconds",
    )
    if rotation_error:
        (errors if strict else warnings).append(rotation_error)

    refresh_seconds, refresh_error = _parse_positive_int(
        source.get("refresh_seconds"),
        DEFAULT_REFRESH_SECONDS,
        field_name="refresh_seconds",
    )
    if refresh_error:
        (errors if strict else warnings).append(refresh_error)

    citibike_station_id = _as_non_empty_str(
        source.get("citibike_station_id"), DEFAULT_CITIBIKE_STATION_ID
    )
    if (
        strict
        and "citibike_station_id" in source
        and not _is_non_empty_string(source.get("citibike_station_id"))
    ):
        errors.append("citibike_station_id must be a non-empty string.")

    version = _parse_version(source.get("version"))
    if version is None:
        if strict and "version" in source:
            errors.append("version must be a positive integer.")
        version = DEFAULT_CONFIG_VERSION

    normalized = {
        "version": version,
        "stations": stations,
        "rotation_seconds": rotation_seconds,
        "refresh_seconds": refresh_seconds,
        "citibike_station_id": citibike_station_id,
    }
    return normalized, errors, warnings


def build_schedule_preview(config_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build station/line view sequence for current board config."""
    stations = config_payload.get("stations") or []
    if not stations:
        return []

    def _line_lookup(station_id: str) -> list[str]:
        if not is_valid_station(station_id):
            return []
        routes = get_station_lines(station_id)
        return [route.strip().upper() for route in routes if str(route).strip()]

    primary_station = stations[0]
    fallback_routes = _line_lookup(primary_station)
    fallback_route = fallback_routes[0] if fallback_routes else "F"

    schedule = create_display_schedule(
        station_ids=stations,
        line_lookup=_line_lookup,
        interval_seconds=int(config_payload.get("rotation_seconds", DEFAULT_ROTATION_SECONDS)),
        default_view=DisplayView(station_id=primary_station, route_id=fallback_route),
    )

    preview: list[dict[str, Any]] = []
    for index, view in enumerate(schedule.views):
        station_name = view.station_id
        if is_valid_station(view.station_id):
            station_name = get_station_name(view.station_id)
        preview.append(
            {
                "index": index,
                "station_id": view.station_id,
                "station_name": station_name,
                "route_id": view.route_id,
            }
        )
    return preview


def list_stations(query: str | None = None) -> list[dict[str, Any]]:
    """Return stations for picker/search."""
    needle = (query or "").strip().lower()
    stations = load_station_data()
    items: list[dict[str, Any]] = []
    for station_id, payload in stations.items():
        name = str(payload.get("name", station_id))
        lines = payload.get("lines", [])
        lines_list = [str(line).strip().upper() for line in lines if str(line).strip()]

        searchable = f"{station_id} {name}".lower()
        if needle and needle not in searchable:
            continue

        items.append(
            {
                "station_id": station_id,
                "name": name,
                "lines": lines_list,
            }
        )

    items.sort(key=lambda item: item["name"])
    return items


def load_board_runtime_status(
    status_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Load board runtime status heartbeat if it exists."""
    path = resolve_status_path(status_path)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(payload, dict):
        return None
    return payload


def _parse_positive_int(
    value: Any,
    default: int,
    *,
    field_name: str,
) -> tuple[int, str | None]:
    if value is None:
        return default, None
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed, None
    except (TypeError, ValueError):
        pass
    return default, f"{field_name} must be a positive integer."


def _parse_version(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except (TypeError, ValueError):
        return None
    return None


def _as_non_empty_str(value: Any, default: str) -> str:
    if _is_non_empty_string(value):
        return str(value).strip()
    return default


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
