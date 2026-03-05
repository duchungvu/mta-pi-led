"""Board configuration loader for LED runtime settings."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_STATIONS = ["B10"]
DEFAULT_ROTATION_SECONDS = 10
DEFAULT_REFRESH_SECONDS = 30
DEFAULT_CITIBIKE_STATION_ID = "66dbc551-0aca-11e7-82f6-3863bb44ef7c"
CONFIG_READ_RETRY_ATTEMPTS = 4
CONFIG_READ_RETRY_DELAY_SECONDS = 0.12


@dataclass(frozen=True)
class BoardConfig:
    """Validated board runtime configuration."""

    stations: list[str]
    rotation_seconds: int
    refresh_seconds: int
    citibike_station_id: str

    @property
    def primary_station(self) -> str:
        return self.stations[0]


def load_board_config(config_path: str | Path | None = None) -> BoardConfig:
    """Load board config from JSON with validation and safe defaults."""
    path = resolve_board_config_path(config_path)
    payload = _load_payload_with_retry(path)

    return BoardConfig(
        stations=_as_station_list(payload.get("stations")),
        rotation_seconds=_as_positive_int(
            payload.get("rotation_seconds"), DEFAULT_ROTATION_SECONDS
        ),
        refresh_seconds=_as_positive_int(
            payload.get("refresh_seconds"), DEFAULT_REFRESH_SECONDS
        ),
        citibike_station_id=_as_non_empty_str(
            payload.get("citibike_station_id"), DEFAULT_CITIBIKE_STATION_ID
        ),
    )


def resolve_board_config_path(config_path: str | Path | None = None) -> Path:
    """Resolve board config path from argument, env var, or repo default."""
    if config_path is not None:
        return Path(config_path).expanduser()

    env_path = os.getenv("BOARD_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()

    return Path(__file__).resolve().parents[3] / "config" / "board.json"


def _load_payload_with_retry(path: Path) -> dict[str, Any]:
    """Read config JSON with small retries to tolerate concurrent writes."""
    last_error: Exception | None = None

    for attempt in range(CONFIG_READ_RETRY_ATTEMPTS):
        try:
            if not path.exists():
                return {}

            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if isinstance(payload, dict):
                return payload
            return {}
        except (FileNotFoundError, PermissionError, json.JSONDecodeError, OSError) as exc:
            last_error = exc
            if attempt < CONFIG_READ_RETRY_ATTEMPTS - 1:
                time.sleep(CONFIG_READ_RETRY_DELAY_SECONDS)

    if last_error is not None:
        raise last_error
    return {}


def _as_station_list(value: Any) -> list[str]:
    if isinstance(value, list):
        stations = [item.strip().upper() for item in value if isinstance(item, str) and item.strip()]
        if stations:
            return stations
    return DEFAULT_STATIONS.copy()


def _as_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except (TypeError, ValueError):
        pass
    return default


def _as_non_empty_str(value: Any, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default
